# Derick Hess, Feb 2019

"""
Implements IRIS webservice style extent and query
for data availability in a PH5 archive.
"""

import os
import sys
import logging
import argparse
from argparse import RawTextHelpFormatter
from ph5.core import ph5api, ph5utils, timedoy

PROG_VERSION = '2019.49'
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

        self.station_ids = args.sta_id_list.split(',') \
            if args.sta_id_list else []

        self.stations = args.sta_list.split(',') \
            if args.sta_list else []

        self.locations = args.location.split(',')\
            if args.location else ['*']

        self.channels = args.channel.split(',') \
            if args.channel else ['*']

        self.starttime = timedoy.passcal2epoch(args.start_time) \
            if args.start_time else None

        self.endtime = timedoy.passcal2epoch(args.stop_time) \
            if args.stop_time else None

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

    def get_time(self, st, starttime, endtime):
        if endtime is not None \
           and endtime < st['deploy_time/epoch_l']:
            return -1
        if starttime is not None \
           and starttime > st['pickup_time/epoch_l']:
            return -1

        ph5_starttime = starttime \
            if starttime is not None else st['deploy_time/epoch_l']
        ph5_endtime = endtime \
            if endtime is not None else st['pickup_time/epoch_l']
        return ph5_starttime, ph5_endtime

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

                        ret = self.get_time(st, starttime, endtime)
                        if ret == -1:
                            continue
                        tup = (ph5_seed_station,
                               ph5_loc, ph5_channel)

                        if tup not in slc:
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

                        ret = self.get_time(st, starttime, endtime)
                        if ret == -1:
                            continue
                        ph5_starttime, ph5_endtime = ret

                        earliest, latest = self.ph5.get_extent(
                            ph5_das, ph5_channum, ph5_starttime, ph5_endtime)
                        tup = (ph5_seed_station,
                               ph5_loc, ph5_channel, earliest, latest)
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
                        ph5_sample_rate = st['sample_rate_i']
                        ph5_channum = st['channel_number_i']
                        ret = self.get_time(st, starttime, endtime)
                        if ret == -1:
                            continue
                        ph5_starttime, ph5_endtime = ret

                        times = self.ph5.get_availability(
                            ph5_das, ph5_sample_rate, ph5_channum,
                            ph5_starttime, ph5_endtime)

                        if include_sample_rate:
                            for sample_rate, start, stop in times:
                                tup = (ph5_seed_station, ph5_loc, ph5_channel,
                                       start, stop, sample_rate)
                                availability.append(tup)

                        else:
                            START = None
                            STOP = None
                            for sample_rate, start, stop in times:
                                if START is None or START > start:
                                    START = start
                                if STOP is None or STOP < stop:
                                    STOP = stop
                            tup = (ph5_seed_station,
                                   ph5_loc, ph5_channel, START, STOP)
                            availability.append(tup)

        return availability

    def get_start(self, das_t):
        return float(das_t['time/epoch_l']) + \
            float(das_t['time/micro_seconds_i'])/1000000

    def get_end(self, das_t, start, samplerate):
        return (start + (float(das_t['sample_count_i']) / samplerate))

    def get_sampleNos_gapOverlap(self, das, component, start=None, end=None):
        self.ph5.read_das_t(das, start, end, reread=False)
        if das not in self.ph5.Das_t:
            LOGGER.warning("No Das table found for " + das)
            return -1
        Das_t = ph5api.filter_das_t(self.ph5.Das_t[das]['rows'], component)
        new_das_t = sorted(Das_t, key=lambda k: k['time/epoch_l'])
        if not new_das_t:
            LOGGER.warning("No Das table found for " + das)
            return -1

        # calculate expected_sampleNo
        true_sample_rate = (float(new_das_t[-1]['sample_rate_i']) /
                            float(new_das_t[-1]['sample_rate_multiplier_i']))

        latest_epoch_start = self.get_start(new_das_t[-1])
        latest_epoch = self.get_end(new_das_t[-1], latest_epoch_start,
                                    true_sample_rate)

        if latest_epoch > end:
            latest_epoch = end

        expected_sampleNo = (end - start) * true_sample_rate

        gapOverlap = 0
        sampleNo = 0
        i = -1
        for i in range(len(new_das_t) - 1):
            sampleNo += new_das_t[i]['sample_count_i']
            start_time = self.get_start(new_das_t[i])
            end_time = self.get_end(new_das_t[i], start_time, true_sample_rate)
            next_start_time = self.get_start(new_das_t[i+1])
            if end_time != next_start_time:
                gapOverlap += 1

        i += 1
        try:
            # the last trace may not be the whole trace
            start_time = self.get_start(new_das_t[i])
            if start_time < latest_epoch:
                sampleNo += true_sample_rate * (latest_epoch - start_time)
        except IndexError:
            pass
        self.ph5.forget_das_t(das)
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
                        ph5_channum = st['channel_number_i']
                        ret = self.get_time(st, starttime, endtime)
                        if ret == -1:
                            continue
                        ph5_starttime, ph5_endtime = ret

                        ret = self.get_sampleNos_gapOverlap(
                            ph5_das, ph5_channum, ph5_starttime, ph5_endtime)
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

                        ret = self.get_time(st, starttime, endtime)
                        if ret == -1:
                            continue
                        ph5_starttime, ph5_endtime = ret
                        self.ph5.read_das_t(ph5_das, ph5_starttime,
                                            ph5_endtime, reread=False)
                        if ph5_das not in self.ph5.Das_t:
                            LOGGER.warning(
                                "No Das table found for %s in "
                                "time range (%s - %s)"
                                % (ph5_das, ph5_starttime, ph5_endtime))
                            return -1
                        for d in self.ph5.Das_t[ph5_das]['rows']:
                            if d['sample_count_i'] > 0:
                                self.ph5.forget_das_t(ph5_das)
                                return True
                        self.ph5.forget_das_t(ph5_das)

        return False

    def process_all(self):
        AVAIL = {0: self.has_data, 1: self.get_nslc,
                 2: self.get_availability, 3: self.get_availability_extent,
                 4: self.get_availability_percentage}
        stations = self.station_ids if self.station_ids != [] \
            else self.stations
        if stations == []:
            stations = ['*']
        for st in stations:
            for ch in self.channels:
                for loc in self.locations:
                    print AVAIL[self.avail](
                        st, loc, ch,
                        self.starttime, self.endtime, self.SR_included)


def get_args():
    """
    Parses command line arguments and returns arg_parse object
    :rtype: :class argparse
    :returns: Returns arge parse class object

    TODO: ADD ALL COMMAND LINE ARGUMENTS NEEDED

    """

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
        "-s", "--starttime", action="store",
        type=str, dest="start_time", metavar="start_time",
        help="Time formats are YYYY:DOY:HH:MM:SS.ss")

    parser.add_argument(
        "-t", "--stoptime", action="store",
        type=str, dest="stop_time", metavar="stop_time",
        help="Time formats are YYYY:DOY:HH:MM:SS.ss")

    parser.add_argument(
        "--station", action="store", dest="sta_list",
        help="Comma separated list of SEED station id's",
        metavar="sta_list", type=str, default=[])

    parser.add_argument(
        "--station_id", action="store", dest="sta_id_list",
        help="Comma separated list of PH5 station id's",
        metavar="sta_id_list", type=str, default=[])

    parser.add_argument(
        "--channel", action="store",
        type=str, dest="channel",
        help="Comma separated list of SEED channels to extract",
        metavar="channel", default=[])

    parser.add_argument(
        "-l", "--location", action="store",
        type=str, dest="location",
        help="Comma separated list of SEED locations to extract",
        metavar="location", default=[])

    parser.add_argument(
        "-S", "--srate", action="store_true",
        dest="samplerate",
        help="Sample Rate included",
        default=False)

    parser.add_argument(
        "-a", "--avail", action="store",
        type=int, dest="avail",
        help="Availability of data:\n  0: has_data, 1: nslc, 2: availability,\
\n  3: availability_extent, 4: availability_percentage",
        metavar="avail", default=0, required=True)

    parser.add_argument(
        "-F", "-f", "--format", action="store", dest="format",
        help="text, sync, geocsv, json",
        metavar="format", type=str, default="text")

    the_args = parser.parse_args()
    return the_args


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
    except Exception as e:
        LOGGER.error(e)


if __name__ == '__main__':
    main()
