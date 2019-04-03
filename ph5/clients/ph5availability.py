# Derick Hess, Feb 2019

"""
Implements IRIS webservice style extent and query
for data availability in a PH5 archive.
"""

import os
import sys
import logging
import argparse
from uuid import uuid4
from datetime import datetime
from argparse import RawTextHelpFormatter
from ph5.core import ph5api, ph5utils

PROG_VERSION = '2019.88'
LOGGER = logging.getLogger(__name__)


class PH5AvailabilityError(Exception):
    """Exception raised when there is a problem with the request.
    :param: message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class PH5Availability(object):
    """
    Availability methods for Ph5 archive
    """

    def __init__(self, ph5API_object):
        """
        Initializes PH5Availability
        :type  :class core.ph5api
        :param object containg PH5 instance
        TODO: ADD ALL PARAMATERS NEEDED

        """

        self.ph5 = ph5API_object
        if not self.ph5.Array_t_names:
            self.ph5.read_array_t_names()
        if not self.ph5.Experiment_t:
            self.ph5.read_experiment_t()
        return

    def analyze_args(self, args):

        self.station_ids = ph5utils.parse_ph5_componentid(args.sta_id_list)
        if self.station_ids:
            self.stations = self.station_ids
        else:
            self.stations = ph5utils.parse_seed_station(args.sta_list)
        if not self.stations:
            self.stations = ["*"]
        self.locations = ph5utils.parse_seed_location(args.location)
        if not self.locations:
            self.locations = ["*"]
        self.channels = ph5utils.parse_seed_channel(args.channel)
        if not self.channels:
            self.channels = ["*"]
        self.starttime = ph5utils.parse_date(args.start_time)
        if self.starttime:
            self.starttime = (self.starttime -
                              datetime.fromtimestamp(0)).total_seconds()
        self.endtime = ph5utils.parse_date(args.stop_time)
        if self.endtime:
            self.endtime = (self.endtime -
                            datetime.fromtimestamp(0)).total_seconds()

        self.avail = args.avail

        self.SR_included = False
        if args.samplerate:
            self.SR_included = True

        if args.format:
            self.format = args.format

    def get_channel(self, st_data):
        if 'seed_band_code_s' in st_data:
            band_code = st_data['seed_band_code_s']
        else:
            band_code = "D"
        if 'seed_instrument_code_s' in st_data:
            instrument_code = st_data['seed_instrument_code_s']
        else:
            instrument_code = "P"
        if 'seed_orientation_code_s' in st_data:
            orientation_code = st_data['seed_orientation_code_s']
        else:
            orientation_code = "X"

        seed_cha_code = band_code + instrument_code + orientation_code

        return seed_cha_code

    def get_slc_info(self, st_data, station, location, channel):
        ph5_seed_station = ''
        ph5_loc = ''
        ph5_channel = ''
        if st_data['seed_station_name_s']:
            ph5_seed_station = st_data['seed_station_name_s']
        else:
            ph5_seed_station = st_data['id_s']

        if not ph5utils.does_pattern_exists(
           [station], ph5_seed_station):
            return -1

        ph5_channel = self.get_channel(st_data)
        if not ph5utils.does_pattern_exists(
           [channel], ph5_channel):
            return -1

        ph5_loc = st_data['seed_location_code_s']
        if not ph5utils.does_pattern_exists(
           [location], ph5_loc):
            return -1
        return ph5_seed_station, ph5_loc, ph5_channel

    def get_array_order_id(self, array_name):
        if array_name is None:
            for n in self.ph5.Array_t_names:
                self.ph5.read_array_t(n)
        else:
            self.ph5.read_array_t(array_name)

        arraybyid = self.ph5.Array_t[array_name]['byid']
        arrayorder = self.ph5.Array_t[array_name]['order']
        return arrayorder, arraybyid

    def get_time_das_t(self, das, start, end,
                       component=None, sample_rate=None):
        s = 0 if start is None else start
        e = 32509613590 if end is None else end
        if sample_rate is not None:
            Das_t = self.ph5.query_das_t(
                das,
                chan=component,
                start_epoch=s,
                stop_epoch=e,
                sample_rate=sample_rate)
            if not Das_t:
                if (start is not None) and (end is not None):
                    LOGGER.warning(
                        "No Das table found for %s in range %s - %s for "
                        "component: %s, samplerate:%s"
                        % (das, start, end, component, sample_rate))
                return -1
        else:
            self.ph5.read_das_t(das, s, e, reread=False)
            if das not in self.ph5.Das_t:
                if (start is not None) and (end is not None):
                    LOGGER.warning("No Das table found for %s in range %s - %s"
                                   % (das, start, end))
                return -1
            Das_t = self.ph5.Das_t[das]['rows']
            if component is not None:
                Das_t = ph5api.filter_das_t(Das_t, component)
        new_das_t = sorted(Das_t, key=lambda k: k['time/epoch_l'])

        if not new_das_t:
            LOGGER.warning("No Das table found for " + das)
            self.ph5.forget_das_t(das)
            return -1

        earliest_epoch = self.get_start(new_das_t[0])

        latest_epoch_start = self.get_start(new_das_t[-1])
        true_sample_rate = self.get_sample_rate(new_das_t[-1])
        latest_epoch = self.get_end(new_das_t[-1], latest_epoch_start,
                                    true_sample_rate)
        if end is not None and end < earliest_epoch:
            self.ph5.forget_das_t(das)
            return -1
        if start is not None and start > latest_epoch:
            self.ph5.forget_das_t(das)
            return -1
        self.ph5.forget_das_t(das)
        return earliest_epoch, latest_epoch, true_sample_rate, new_das_t

    def get_slc(self, station='*', location='*', channel='*',
                starttime=None, endtime=None, include_sample_rate=False):
        """
        Get a list of tuples [(sta, loc, cha),...] containing information
        on what streams are included in PH5.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
            Wildcards '*' and '?' are supported.
        :type location: str
        :param location: Location code of requested data (e.g. "").
            Wildcards '*' and '?' are supported.
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
            Wildcards '*' and '?' are supported.
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :rtype: list(tuple(str, str, str, str))
        :returns: A list of tuples [(station, location, channel)...]
            containing information on what streams are included in PH5 archive.
        """
        slc = []

        array_names = sorted(self.ph5.Array_t_names)
        for array_name in array_names:
            arrayorder, arraybyid = self.get_array_order_id(array_name)

            for ph5_station in arrayorder:

                station_list = arraybyid.get(ph5_station)

                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        st = station_list[deployment][st_num]
                        ret = self.get_slc_info(st, station, location, channel)
                        if ret == -1:
                            continue
                        ph5_seed_station, ph5_loc, ph5_channel = ret

                        ph5_das = st['das/serial_number_s']
                        ph5_channum = st['channel_number_i']
                        ph5_sample_rate = self.get_sample_rate(st)
                        tup = (ph5_seed_station,
                               ph5_loc, ph5_channel)
                        if tup not in slc:
                            ret = self.get_time_das_t(
                                ph5_das, starttime, endtime,
                                ph5_channum, ph5_sample_rate)
                            if ret == -1:
                                continue
                            slc.append(tup)

        return slc

    def get_availability_extent(self, station='*', location='*',
                                channel='*', starttime=None, endtime=None,
                                include_sample_rate=False):
        """
        Get a list of tuples [(station, location, channel,
        earliest, latest)] containing data extent info for time series
        included in PH5.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
            Wildcards '*' and '?' are supported.
        :type location: str
        :param location: Location code of requested data (e.g. "").
            Wildcards '*' and '?' are supported.
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
            Wildcards '*' and '?' are supported.
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :rtype: list(tuple(str, str, str, str, float, float))
        :returns: A list of tuples [(station, location, channel,
            earliest, latest)...] containing data extent info for time series
            included in PH5 archive

        NOTE! ph5api as a get_extent() method that works on the channel level.
        Leverage this

        """
        availability_extents = []
        if starttime or endtime:
            if not (starttime and endtime):
                raise ValueError("if start or end, both are required")

        array_names = sorted(self.ph5.Array_t_names)

        for array_name in array_names:
            arrayorder, arraybyid = self.get_array_order_id(array_name)

            for ph5_station in arrayorder:

                station_list = arraybyid.get(ph5_station)

                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        st = station_list[deployment][st_num]

                        ret = self.get_slc_info(st, station, location, channel)
                        if ret == -1:
                            continue
                        ph5_seed_station, ph5_loc, ph5_channel = ret

                        ph5_das = st['das/serial_number_s']
                        ph5_channum = st['channel_number_i']
                        ph5_sample_rate = self.get_sample_rate(st)

                        earliest, latest = self.ph5.get_extent(
                            ph5_das, ph5_channum, ph5_sample_rate,
                            starttime, endtime)
                        if earliest is None:
                            continue

                        if not include_sample_rate:
                            tup = (ph5_seed_station, ph5_loc, ph5_channel,
                                   earliest, latest)
                        else:
                            tup = (ph5_seed_station, ph5_loc, ph5_channel,
                                   earliest, latest, ph5_sample_rate)

                        availability_extents.append(tup)

        return availability_extents

    def get_availability(self, station='*', location='*',
                         channel='*', starttime=None, endtime=None,
                         include_sample_rate=False):
        """
        Get a list of tuples [(station, location, channel,
        starttime, endtime),...] containing data availability info for
        time series included in the tsindex database.
        If ``include_sample_rate=True``, then a tuple containing the sample
        rate [(sta, loc, cha, start, end, sample_rate),...] is returned.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
            Wildcards '*' and '?' are supported.
        :type location: str
        :param location: Location code of requested data (e.g. "").
            Wildcards '*' and '?' are supported.
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
            Wildcards '*' and '?' are supported.
        :type starttime: :class:`~obspy.core.utcdatetime.UTCDateTime`
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :type include_sample_rate: bool
        :param include_sample_rate: If ``include_sample_rate=True``, then
            a tuple containing the sample rate [(sta, loc, cha,
            start, end, sample_rate),...] is returned.
        :rtype: list(tuple(str, str, str, str, str, str))
        :returns: A list of tuples [(station, location, channel,
            earliest, latest)...] representing contiguous time spans for
            selected channels and time ranges.

        NOTE! ph5api as a get_availability()
        method that works on the channel level. Leverage this
        """
        availability = []

        array_names = sorted(self.ph5.Array_t_names)

        for array_name in array_names:
            arrayorder, arraybyid = self.get_array_order_id(array_name)

            for ph5_station in arrayorder:

                station_list = arraybyid.get(ph5_station)

                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        st = station_list[deployment][st_num]

                        ret = self.get_slc_info(st, station, location, channel)

                        if ret == -1:
                            continue
                        ph5_seed_station, ph5_loc, ph5_channel = ret
                        ph5_das = st['das/serial_number_s']
                        ph5_channum = st['channel_number_i']
                        ph5_sample_rate = self.get_sample_rate(st)

                        times = self.ph5.get_availability(
                            ph5_das, ph5_sample_rate, ph5_channum,
                            starttime, endtime)
                        for T in times:
                            start = T[1] if T[1] > starttime \
                                or starttime is None else starttime
                            end = T[2] if T[2] < endtime \
                                or endtime is None else endtime
                            if include_sample_rate:
                                availability.append((
                                    ph5_seed_station, ph5_loc, ph5_channel,
                                    start, end, T[0]))
                            else:
                                availability.append((
                                    ph5_seed_station, ph5_loc, ph5_channel,
                                    start, end))

        return availability

    def get_start(self, das_t):
        return float(das_t['time/epoch_l']) + \
            float(das_t['time/micro_seconds_i'])/1000000

    def get_end(self, das_t, start, samplerate):
        if samplerate != 0:
            duration = float(das_t['sample_count_i']) / samplerate
        else:
            duration = 0
        return start + duration

    def get_sample_rate(self, st):
        if st['sample_rate_i'] == 0:
            return 0
        return float(st['sample_rate_i']) / \
            float(st['sample_rate_multiplier_i'])

    def get_sampleNos_gapOverlap(self, das_t, earliest, latest, start, end,
                                 sample_rate, st):

        if start is None:
            start = st['deploy_time/epoch_l']
        if end is None:
            end = st['pickup_time/epoch_l']
        # calculate expected_sampleNo
        gapOverlap = 0
        if start < earliest:
            gapOverlap += 1
        if latest < end:
            gapOverlap += 1
        else:
            latest = end

        expected_sampleNo = (end - start) * sample_rate

        sampleNo = 0
        i = -1
        for i in range(len(das_t) - 1):
            sampleNo += das_t[i]['sample_count_i']
            start_time = self.get_start(das_t[i])
            true_sample_rate = self.get_sample_rate(das_t[i])
            end_time = self.get_end(das_t[i], start_time, true_sample_rate)
            next_start_time = self.get_start(das_t[i+1])
            if end_time != next_start_time:
                gapOverlap += 1

        i += 1
        try:
            # the last trace may not be the whole trace
            start_time = self.get_start(das_t[i])
            if start_time < latest:
                sampleNo += sample_rate * (latest - start_time)
        except IndexError:
            pass

        return expected_sampleNo, sampleNo, gapOverlap

    def get_availability_percentage(self, station,
                                    location, channel,
                                    starttime, endtime,
                                    include_sample_rate=False):
        """
        Get percentage of available data.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
        :type location: str
        :param location: Location code of requested data (e.g. "").
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :rtype: tuple(float, int)
        :returns: Tuple of percentage of available data (``0.0`` to ``1.0``)
            and number of gaps/overlaps.
        """
        allp = station + location + channel
        if '*' in allp or '?' in allp:
            LOGGER.error(
                "get_availability_percentage does not support wildcard.")
            return
        sampleNo = 0
        expected_sampleNo = 0
        gapOverlap = 0
        array_names = sorted(self.ph5.Array_t_names)

        for array_name in array_names:
            arrayorder, arraybyid = self.get_array_order_id(array_name)

            for ph5_station in arrayorder:
                station_list = arraybyid.get(ph5_station)

                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        st = station_list[deployment][st_num]

                        ret = self.get_slc_info(st, station, location, channel)
                        if ret == -1:
                            continue

                        ph5_das = st['das/serial_number_s']
                        ph5_sample_rate = self.get_sample_rate(st)
                        ph5_channum = st['channel_number_i']

                        ret = self.get_time_das_t(
                            ph5_das, starttime, endtime,
                            ph5_channum, ph5_sample_rate)
                        if ret == -1:
                            continue
                        ph5_earliest, ph5_latest, sample_rate, das_t = ret

                        ret = self.get_sampleNos_gapOverlap(
                            das_t, ph5_earliest, ph5_latest,
                            starttime, endtime, sample_rate, st)
                        if ret == -1:
                            continue
                        expected_sampleNo += ret[0]
                        sampleNo += ret[1]
                        gapOverlap += ret[2]
        if sampleNo == 0:
            sampleResult = 0.0
        else:
            sampleResult = sampleNo / expected_sampleNo
        return (sampleResult, gapOverlap)

    def has_data(self, station='*', location='*',
                 channel='*', starttime=None, endtime=None,
                 include_sample_rate=False):
        """
        Return whether there is data for a specified station,
        location, channel, starttime, and endtime combination.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
            Wildcards '*' and '?' are supported.
        :type location: str
        :param location: Location code of requested data (e.g. "").
            Wildcards '*' and '?' are supported.
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
            Wildcards '*' and '?' are supported.
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :rtype: bool
        :returns: Returns ``True`` if there is data in Ph5 for a given
            station, location, channel, starttime, endtime.
        """
        array_names = sorted(self.ph5.Array_t_names)

        for array_name in array_names:
            arrayorder, arraybyid = self.get_array_order_id(array_name)

            for ph5_station in arrayorder:

                station_list = arraybyid.get(ph5_station)

                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        st = station_list[deployment][st_num]
                        ret = self.get_slc_info(st, station, location, channel)
                        if ret == -1:
                            continue

                        ph5_das = st['das/serial_number_s']
                        ph5_channum = st['channel_number_i']
                        if channel == "*":
                            ret = self.get_time_das_t(
                                ph5_das, starttime, endtime)
                        else:
                            ph5_sample_rate = self.get_sample_rate(st)
                            ret = self.get_time_das_t(
                                ph5_das, starttime, endtime,
                                component=ph5_channum,
                                sample_rate=ph5_sample_rate)
                        if ret == -1:
                            continue
                        ph5_earliest, ph5_latest, sample_rate, das_t = ret

                        for d in das_t:
                            if d['sample_count_i'] > 0:
                                return True
                            elif d['sample_rate_i'] == 0:
                                ref = self.ph5.ph5_g_receivers.\
                                    find_trace_ref(
                                        d['array_name_data_a'].strip())
                                if ref.nrows > 0:
                                    return True
                        self.ph5.forget_das_t(ph5_das)

        return False

    def process_all(self):
        AVAIL = {0: self.has_data, 1: self.get_slc,
                 2: self.get_availability, 3: self.get_availability_extent,
                 4: self.get_availability_percentage}
        for st in self.stations:
            for ch in self.channels:
                for loc in self.locations:
                    avail = AVAIL[self.avail](st, loc, ch, self.starttime,
                                              self.endtime, self.SR_included)
                    if avail:
                        print(avail)


def get_args():
    """
    Parses command line arguments and returns arg_parse object
    :rtype: :class argparse
    :returns: Returns arge parse class object
    """

    sentinel_dict = {}

    def _preprocess_sysargv(argv):
        inputs = []
        for arg in argv[1:]:
            # handles case where values contain --, otherwise they will
            # be interpreted as arguments.
            if '--,' in arg or ',--' in arg or arg == '--':
                sentinel = uuid4().hex
                key = '%s' % sentinel
                sentinel_dict[key] = arg
                inputs.append(sentinel)
            else:
                inputs.append(arg)
        return inputs

    def _postprocess_sysargv(v):
        if v in sentinel_dict:
            return sentinel_dict.get(v)
        else:
            return v

    parser = argparse.ArgumentParser(
        description='Get data availability form PH5',
        formatter_class=RawTextHelpFormatter,
        usage='Version: {0} ph5availability '
              '--nickname="Master_PH5_file" [options]'.format(PROG_VERSION))
    parser.add_argument(
        "-n", "--nickname", action="store",
        type=str, metavar="nickname", default="master.ph5")

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    parser.add_argument(
        "-s", "--start_time", action="store",
        type=str, dest="start_time", metavar="start_time", default=None,
        help="Time formats are YYYY:DOY:HH:MM:SS.ss or epoch time")

    parser.add_argument(
        "-t", "--stop_time", action="store",
        type=str, dest="stop_time", metavar="stop_time", default=None,
        help="Time formats are YYYY:DOY:HH:MM:SS.ss or epoch time")

    parser.add_argument(
        "--station", action="store", dest="sta_list",
        help="Comma separated list of SEED station id's",
        metavar="sta_list", type=str, default=[])

    parser.add_argument(
        "--station_id", action="store", dest="sta_id_list",
        help="Comma separated list of PH5 station id's",
        metavar="sta_id_list", type=str, default=[])

    parser.add_argument('--location', '--loc',
                        help="Select one or more SEED location identifier. "
                        "Use -- for 'Blank' location IDs (ID's containing 2 "
                        "spaces). Accepts wildcards and lists.",
                        type=_postprocess_sysargv)

    parser.add_argument(
        "--channel", action="store",
        type=str, dest="channel",
        help="Comma separated list of SEED channels to extract",
        metavar="channel", default=[])

    parser.add_argument(
        "-S", "--srate", action="store_true",
        dest="samplerate",
        help="Sample Rate included",
        default=False)

    parser.add_argument(
        "-a", "--avail", action="store",
        type=int, dest="avail",
        help=("Availability of data: 0: has_data, 1: slc, 2: availability, "
              "3: availability_extent, 4: availability_percentage"),
        metavar="avail", default=0, required=True)

    parser.add_argument(
        "-F", "-f", "--format", action="store", dest="format",
        help="text, sync, geocsv, json",
        metavar="format", type=str, default="text")

    return parser.parse_args(_preprocess_sysargv(sys.argv))


def main():
    """
    Main method for use for command line program
    """
    args = get_args()

    if args.nickname[-3:] == 'ph5':
        ph5file = os.path.join(args.ph5path, args.nickname)
    else:
        ph5file = os.path.join(args.ph5path, args.nickname + '.ph5')
        args.nickname += '.ph5'

    if not os.path.exists(ph5file):
        LOGGER.error("{0} not found.\n".format(ph5file))
        sys.exit(-1)
    try:
        ph5API_object = ph5api.PH5(path=args.ph5path, nickname=args.nickname)
        availability = PH5Availability(ph5API_object)

        availability.analyze_args(args)
        # stuff here
        availability.process_all()

        ph5API_object.close()
    except ph5api.APIError as err:
        LOGGER.error(err)
    except PH5AvailabilityError as err:
        LOGGER.error(err)
    except Exception as err:
        LOGGER.error(err)


if __name__ == '__main__':
    main()
