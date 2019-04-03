# Derick Hess, Feb 2019

"""
Implements IRIS webservice style extent and query
for data availability in a PH5 archive.
"""

import os
import sys
import logging
import argparse
import datetime
from argparse import RawTextHelpFormatter
from ph5.core import ph5api, ph5utils, timedoy

PROG_VERSION = '2019.086'
LOGGER = logging.getLogger(__name__)

f_id = {'stat': 0, 'loc': 1, 'chan': 2,
        'earliest': 3, 'latest': 4, 'sRate': 5}


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
            self.netcode = self.ph5.Experiment_t['rows'][0]['net_code_s']
        self.array = None
        self.sta_len = 1
        self.tim_len = 27
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

        self.starttime = self.get_time(args.start_time)
        self.endtime = self.get_time(args.end_time)
        if -1 in [self.starttime, self.endtime]:
            return False

        self.array = args.array_t_
        if args.avail not in [0, 1, 2, 3, 4]:
            LOGGER.error("There is no avail option '%s'. Please run "
                         "ph5availability -h for more information.")
        self.avail = args.avail

        self.SR_included = False
        if args.samplerate:
            if self.avail in [2, 3]:
                self.SR_included = True

        if args.format:
            self.format = args.format

        # define OFILE to write output
        o_filename = args.output_file
        if o_filename is None:
            self.OFILE = None
        else:
            self.OFILE = open(o_filename, 'w')
        return True

    def get_time(self, time):
        if time is None:
            return None
        try:
            epoch_time = float(time)
        except Exception:
            try:
                if "T" not in time:
                    epoch_time = timedoy.passcal2epoch(time)
                else:
                    epoch_time = ph5utils.fdsntime_to_epoch(time)
            except Exception as e:
                print("error:", e)
                LOGGER.error("The input time %s is not in the right format."
                             % time)
                return - 1
        return epoch_time

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
        if len(ph5_seed_station) > self.sta_len:
            self.stat_len = len(ph5_seed_station)

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
            self.ph5.forget_das_t(das)
            if component is not None:
                Das_t = ph5api.filter_das_t(Das_t, component)
        new_das_t = sorted(Das_t, key=lambda k: k['time/epoch_l'])

        if not new_das_t:
            LOGGER.warning("No Das table found for " + das)
            return -1

        earliest_epoch = self.get_start(new_das_t[0])

        latest_epoch_start = self.get_start(new_das_t[-1])
        true_sample_rate = self.get_sample_rate(new_das_t[-1])
        latest_epoch = self.get_end(new_das_t[-1], latest_epoch_start,
                                    true_sample_rate)
        if end is not None and end < earliest_epoch:
            return -1
        if start is not None and start > latest_epoch:
            return -1

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
            if self.array is not None:
                a_n = int(array_name.split('_')[2])
                if self.array != a_n:
                    continue
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
            if self.array is not None:
                a_n = int(array_name.split('_')[2])
                if self.array != a_n:
                    continue
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
            if self.array is not None:
                a_n = int(array_name.split('_')[2])
                if self.array != a_n:
                    continue
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
                        if times is None:
                            continue
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
        allp = station + channel
        if '*' in allp or '?' in allp:
            LOGGER.error(
                "get_availability_percentage requires providing exact "
                "station/channel.")
            return
        sampleNo = 0
        expected_sampleNo = 0
        gapOverlap = 0
        array_names = sorted(self.ph5.Array_t_names)

        for array_name in array_names:
            if self.array is not None:
                a_n = int(array_name.split('_')[2])
                if self.array != a_n:
                    continue
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
            if self.array is not None:
                a_n = int(array_name.split('_')[2])
                if self.array != a_n:
                    continue
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

    def print_report(self, text):
        if self.OFILE is None:
            print(text)
        else:
            self.OFILE.write(text + '\n')

    def get_report(self, result, format):
        # print("print_info:", result)
        if self.avail != 2:
            LOGGER.warning("Report feature only apply for avail=2.")
            return result

        if format == 's':
            return self.get_sync_report(result)
        elif format == 'g':
            return self.get_geoCSV_report(result)
        elif format == 't':
            return self.get_text_report(result)
        elif format == 'j':
            return self.get_json_report(result)
        else:
            LOGGER.warning("The entered format %s is not supported." % format)
            return result

    def get_sync_report(self, result):
        """
        Link for Format:
        http://www.iris.washington.edu/bud_stuff/goat/syncformat.html
        """

        # header line
        today = datetime.datetime.now()
        year = today.year
        day_of_year = (today - datetime.datetime(today.year, 1, 1)).days + 1
        date = "%s,%s" % (year, day_of_year)
        s = "%s|%s" % ('PIC', date)

        # Time Span Lines
        template = [self.netcode] + [''] * 15
        for r in result:
            template[1] = r[f_id['stat']]
            template[2] = r[f_id['loc']]
            template[3] = r[f_id['chan']]
            t = timedoy.epoch2passcal(r[f_id['earliest']])
            template[4] = t[:-4].replace(":", ",", 2)
            t = timedoy.epoch2passcal(r[f_id['latest']])
            template[5] = t[:-4].replace(":", ",", 2)
            template[7] = str(r[f_id['sRate']])
            # template[13] = 'primary'

            s += "\n" + "|".join(template)
        return s

    def get_geoCSV_report(self, result):
        """
        Link for Format:
        http://geows.ds.iris.edu/documents/GeoCSV.pdf
        Example: Minimal IRIS Station Example
        """

        dataset = "#dataset: GeoCSV 2.0"
        delim = "#delimiter: |"
        field_unit = "#field_unit: unitless|unitless|unitless|unitless" + \
            "|unitless|unitless"
        field_type = "#field_type: string|string|string|string"
        header = "network|station|location|channel|repository|quality"

        if self.SR_included:
            field_unit += "|hertz"
            field_type += "|float"
            header += "|samplerate"

            field_unit += "|ISO_8601|ISO_8601"
            field_type += "|datetime|datetime"
            header += "|starttime|endtime"

        s = ""
        for r in result:
            r = list(r)
            r = self.convert_time(r)
            row = [self.netcode, r[f_id['stat']], r[f_id['loc']],
                   r[f_id['chan']], '', '', str(r[f_id['sRate']]),
                   r[f_id['earliest']], r[f_id['latest']]]

            s += "\n" + "|".join(row)

        ret = dataset + "\n" + delim + "\n" + field_unit + "\n" \
            + field_type + "\n" + header + s

        return ret

    def get_text_report(self, result):
        s = ""
        for r in result:
            r = list(r)
            r = self.convert_time(r)
            s += "\n" + self.netcode + " "

            s += r[f_id['stat']] + " "

            loc = r[f_id['loc']] if r[f_id['loc']] != '' else '--'
            s += loc + " "

            s += r[f_id['chan']] + " "

            s += "- "
            if self.SR_included:
                s += str(r[f_id['sRate']]).rjust(len('sample-rate')) + " "

            s += r[f_id['earliest']] + " "
            s += r[f_id['latest']]

        header = "#n " + "s".ljust(self.stat_len) + " l  c   q " + \
            "sample-rate " + "earliest".rjust(self.tim_len) + " " + \
            "latest".rjust(self.tim_len)

        ret = header + s
        return ret

    def get_json_report(self, result):
        header = '"created":"%s",'\
            '"repository":[{"repository_name":"","channels":' \
            % self.get_today_FdsnTime()
        rows = []
        tspan = []
        for i in range(len(result)):
            r = list(result[i])
            # get current spantime
            r = self.convert_time(r)
            tspan.append('["%s","%s"]' %
                         (r[f_id['earliest']], r[f_id['latest']]))

            if i != 0 and result[i-1][:3] != result[i][:3]:
                # add row for previous stat, loc, chan when channel changed
                r = result[i-1]
                row = '"net":"%(net)s",'\
                    '"sta":"%(stat)s",'\
                    '"loc":"%(loc)s",'\
                    '"cha":"%(chan)s",'\
                    '"quality":"",'
                v = {"net": self.netcode, "stat": r[f_id['stat']],
                     "loc": r[f_id['loc']], "chan": r[f_id['chan']]}
                if self.SR_included:
                    row += '"sample_rate":%(sRate)s,'
                    v['sRate'] = r[f_id['sRate']]
                v['tspan'] = tspan
                row += '"timespans":[%(tspan)s]'
                rows.append("{%s}" % row % v)
                tspan = []

        if tspan != []:
            r = result[-1]
            row = '"net":"%(net)s",'\
                '"sta":"%(stat)s",'\
                '"loc":"%(loc)s",'\
                '"cha":"%(chan)s",'\
                '"quality":"",'
            v = {"net": self.netcode, "stat": r[f_id['stat']],
                 "loc": r[f_id['loc']], "chan": r[f_id['chan']]}
            if self.SR_included:
                row += '"sample_rate":%(sRate)s,'
                v['sRate'] = r[f_id['sRate']]
            v['tspan'] = tspan
            row += '"timespans":[%(tspan)s]'

            rows.append("{%s}" % row % v)

        ret = '{%s\n[%s]}]}"' % (header, ',\n'.join(rows))

        return ret

    def get_today_FdsnTime(self):
        today = datetime.datetime.now()
        tdoy = timedoy.TimeDOY(
            year=today.year,
            hour=today.hour,
            minute=today.minute,
            second=today.second,
            doy=(today - datetime.datetime(today.year, 1, 1)).days + 1)
        return tdoy.getFdsnTime()

    def convert_time(self, r):
        """
        given a row in the result, if have earliest and latest,
        convert them to datetime
        """
        if self.avail not in [2, 3]:
            return r

        # availability/availability_extent
        earliest = timedoy.TimeDOY(epoch=r[f_id['earliest']])
        r[f_id['earliest']] = earliest.getFdsnTime() + "Z"
        latest = timedoy.TimeDOY(epoch=r[f_id['latest']])
        r[f_id['latest']] = latest.getFdsnTime() + "Z"

        return r

    def process_all(self):
        AVAIL = {0: self.has_data, 1: self.get_slc,
                 2: self.get_availability, 3: self.get_availability_extent,
                 4: self.get_availability_percentage}
        stations = self.station_ids if self.station_ids != [] \
            else self.stations
        if stations == []:
            stations = ['*']
        for st in stations:
            for ch in self.channels:
                for loc in self.locations:
                    report = self.get_report(
                        AVAIL[self.avail](st, loc, ch, self.starttime,
                                          self.endtime, self.SR_included),
                        format=self.format)

                    if report is not None:
                        if type(report) != 'str':
                            print(report)
                        else:
                            print(self.print_report(report))


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
        type=str, dest="start_time", metavar="start_time", default=None,
        help="Time formats are YYYY:DOY:HH:MM:SS.ss or epoch time")

    parser.add_argument(
        "-e", "--endtime", action="store",
        type=str, dest="end_time", metavar="end_time", default=None,
        help="Time formats are YYYY:DOY:HH:MM:SS.ss or epoch time")

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
        "-A", "--Array_t_", dest="array_t_", metavar="n", type=int,
        help=("Dump /Experiment_g/Sorts_g/Array_t_[n] to a kef file."),
        default=None)

    parser.add_argument(
        "--avail", action="store",
        type=int, dest="avail",
        help="Availability of data:\n  0: has_data, 1: slc, 2: availability,\
\n  3: availability_extent, 4: availability_percentage",
        metavar="avail", default=0, required=True)

    parser.add_argument(
        "-F", "-f", "--format", action="store", dest="format",
        help="Format for availability's report:\n  t: text, s: sync, \
g: geocsv, j: json",
        metavar="format", type=str, default="t")

    parser.add_argument("-o", "--outfile", dest="output_file",
                        help="The kef output file to be saved at.",
                        metavar="output_file", default=None)

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

        ret = availability.analyze_args(args)
        if not ret:
            return 1
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
