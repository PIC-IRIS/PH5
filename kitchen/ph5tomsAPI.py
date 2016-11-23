#!/usr/bin/env pnpython4
# Derick Hess, Oct 2016

"""
The MIT License (MIT)
Copyright (c) 2016 Derick Hess

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import sys
import os
from obspy import Trace
from obspy import Stream
from obspy.core.util import AttribDict
from obspy import UTCDateTime
import ph5API
import time
from TimeDOY import epoch2passcal
from TimeDOY import passcal2epoch
import fnmatch

from time import time as tm


PROG_VERSION = "2016.327b"


def fdsntimetoepoch(fdsn_time):

    pattern = "%Y-%m-%dT%H:%M:%S.%f"
    epoch = float(time.mktime(time.strptime(fdsn_time, pattern)))
    return epoch


def doy_breakup(start_fepoch):

    passcal_start = epoch2passcal(start_fepoch)
    start_passcal_list = passcal_start.split(":")
    start_doy = start_passcal_list[1]
    year = start_passcal_list[0]
    next_doy = int(start_doy) + 1
    if next_doy > 365:
        next_doy = 1
        year = int(year) + 1

    next_passcal_date = str(year) + ":" + str(next_doy) + ":00:00:00.000"
    stop_fepoch = passcal2epoch(next_passcal_date)

    seconds = stop_fepoch - start_fepoch
    return stop_fepoch, seconds


class StationCut(object):

    def __init__(self, net_code, station, das, channel,
                 seed_channel, starttime, endtime,
                 sample_rate, sample_rate_multiplier,
                 notimecorrect, location, latitude, longitude):

        self.net_code = net_code
        self.station = station
        self.seed_channel = seed_channel
        self.das = das
        self.starttime = starttime
        self.endtime = endtime
        self.channel = channel
        self.sample_rate = sample_rate
        self.sample_rate_multiplier = sample_rate_multiplier
        self.notimecorrect = notimecorrect
        self.location = location
        self.latitude = latitude
        self.longitude = longitude


class PH5toMSeed(object):

    def __init__(self, ph5API_object, array, length, offset, component=[],
                 station=[], netcode="XX", channel=[],
                 das_sn=None,  use_deploy_pickup=False, decimation=None,
                 sample_rate_keep=None, doy_keep=[], stream=False,
                 out_dir=".", starttime=None, stoptime=None,
                 reduction_velocity=-1., dasskip=None, shotline=None,
                 eventnumbers="", notimecorrect=False, station_id=[]):

        self.chan_map = {1: 'Z', 2: 'N', 3: 'E', 4: 'Z', 5: 'N', 6: 'E'}
        self.array = array
        self.notimecorrect = notimecorrect
        self.decimation = decimation
        self.component = component
        self.use_deploy_pickup = use_deploy_pickup
        self.offset = offset
        self.das_sn = das_sn
        self.station = station
        self.station_id = station_id
        self.sample_rate_list = sample_rate_keep
        self.doy_keep = doy_keep
        self.channel = channel
        self.netcode = netcode
        self.length = length
        self.out_dir = out_dir
        self.stream = stream
        self.start_time = starttime
        self.end_time = stoptime
        self.shotline = shotline
        self.eventnumbers = eventnumbers
        self.ph5 = ph5API_object

        if not os.path.exists(self.out_dir):
            try:
                os.mkdir(self.out_dir)
            except Exception:
                sys.stderr.write(
                    "Error: Can't create {0}.".format(self.out_dir))
                sys.exit()
        if dasskip is not None:
            self.dasskip = dasskip
        else:
            self.dasskip = dasskip

        # Check network code is 2 alphanum
        if (not self.netcode.isalnum()) or (len(self.netcode) != 2):
            sys.stderr.write(
                'Error parsing args: Netcode must 2 character alphanumeric')
            sys.exit(-2)

        if not self.ph5.Array_t_names:
            self.ph5.read_array_t_names()

        if not self.ph5.Experiment_t:
            self.ph5.read_experiment_t()

        if shotline:
            self.ph5.read_event_t_names()

    def read_arrays(self, name):

        if name is None:
            for n in self.ph5.Array_t_names:
                self.ph5.read_array_t(n)
        else:
            self.ph5.read_array_t(name)

    def read_events(self, name):

        if name is None:
            for n in self.ph5.Event_t_names:
                self.ph5.read_event_t(n)
        else:
            self.ph5.read_event_t(name)

    def filenamemseed_gen(self, stream):

        s = stream.traces[0].stats
        secs = int(s.starttime.timestamp)
        pre = epoch2passcal(secs, sep='_')
        ret = "{0}.{1}.{2}.{3}.{4}.ms".format(pre, s.network, s.station,
                                              s.location, s.channel)
        if not self.stream:
            ret = os.path.join(self.out_dir, ret)
        return ret

    def filenamesac_gen(self, stream):

        s = stream.traces[0].stats
        secs = int(s.starttime.timestamp)
        pre = epoch2passcal(secs, sep='.')
        ret = "{0}.{1}.{2}.{3}.{4}.SAC".format(
            s.network, s.station, s.location, s.channel, pre)
        if not self.stream:
            ret = os.path.join(self.out_dir, ret)
        return ret

    def filenamemsimg_gen(self, stream):

        s = stream.traces[0].stats
        secs = int(s.starttime.timestamp)
        pre = epoch2passcal(secs, sep='_')
        ret = "{0}.{1}.{2}.{3}.{4}.png".format(pre, s.network, s.station,
                                               s.location, s.channel)
        if not self.stream:
            if not os.path.exists(
                    os.path.join(self.out_dir, "preview_images")):
                os.makedirs(os.path.join(self.out_dir, "preview_images"))

            ret = os.path.join(self.out_dir, "preview_images", ret)
        return ret

    def filenamesacimg_gen(self, stream):

        s = stream.traces[0].stats
        secs = int(s.starttime.timestamp)
        pre = epoch2passcal(secs, sep='.')
        ret = "{0}.{1}.{2}.{3}.{4}.png".format(
            s.network, s.station, s.location, s.channel, pre)
        if not self.stream:
            if not self.stream:
                if not os.path.exists(
                        os.path.join(self.out_dir, "preview_images")):
                    os.makedirs(os.path.join(self.out_dir, "preview_images"))

            ret = os.path.join(self.out_dir, "preview_images", ret)
        return ret

    def create_trace(self, station_to_cut):

        self.ph5.read_das_t(station_to_cut.das, station_to_cut.starttime,
                            station_to_cut.endtime, reread=False)

        if not self.ph5.Das_t.has_key(station_to_cut.das):
            return

        Das_t = ph5API.filter_das_t(self.ph5.Das_t[station_to_cut.das]['rows'],
                                    station_to_cut.channel)

        das_t_start_no_micro = float(Das_t[0]['time/epoch_l'])
        das_t_start_micro_seconds = float(Das_t[0]['time/micro_seconds_i'])
        das_t_start = (float(Das_t[0]['time/epoch_l']) +
                       float(Das_t[0]['time/micro_seconds_i']) / 1000000)

        if float(das_t_start) > float(station_to_cut.starttime):
            start_time = das_t_start
            start_time_no_micro = int(das_t_start_no_micro)
            start_time_micro_seconds = int(das_t_start_micro_seconds)
            if start_time_micro_seconds > 0:
                station_to_cut.endtime += .0001

        else:
            start_time = station_to_cut.starttime
            start_time_no_micro = station_to_cut.starttime
            start_time_micro_seconds = 0

        nt = station_to_cut.notimecorrect
        traces = self.ph5.cut(station_to_cut.das, start_time,
                              station_to_cut.endtime,
                              chan=station_to_cut.channel,
                              sample_rate=station_to_cut.sample_rate,
                              apply_time_correction=nt)

        obspy_stream = Stream()

        if type(traces) is not list:
            return

        for trace in traces:
            if trace.nsamples == 0:
                continue

            try:
                obspy_trace = Trace(data=trace.data)
            except ValueError:
                print "error"
                continue

            obspy_trace.stats.sampling_rate = station_to_cut.sample_rate
            obspy_trace.stats.location = station_to_cut.location
            obspy_trace.stats.station = station_to_cut.station
            obspy_trace.stats.coordinates = AttribDict()
            obspy_trace.stats.coordinates.latitude = station_to_cut.latitude
            obspy_trace.stats.coordinates.longitude = station_to_cut.longitude
            obspy_trace.stats.channel = station_to_cut.seed_channel
            obspy_trace.stats.network = station_to_cut.net_code
            obspy_trace.stats.starttime = UTCDateTime(start_time_no_micro)

            obspy_trace.stats.starttime.microsecond = (
                start_time_micro_seconds)

            if self.decimation:
                obspy_trace.decimate(int(self.decimation))

            obspy_stream.append(obspy_trace)

        if len(obspy_stream.traces) < 1:
            return

        return obspy_stream

    def create_cut_list(self):

        experiment_t = self.ph5.Experiment_t['rows']
        array_names = self.ph5.Array_t_names
        array_names.sort()
        self.read_events(None)
        shot_lines = self.ph5.Event_t_names
        shot_lines.sort()
        matched_shot_line = None

        if self.shotline:
            for shot_line in shot_lines:
                if int(shot_line[-3:]) == int(self.shotline):
                    matched_shot_line = shot_line

        if self.shotline and not matched_shot_line:
            sys.exit(-1)

        if self.eventnumbers and not self.shotline:
            sys.exit(-1)

        for array_name in array_names:
            array = array_name[-3:]
            matched = 0

            if self.array:
                does_match = []
                array_patterns = self.array.split(',')
                for pattern in array_patterns:
                    if fnmatch.fnmatch(str(array), pattern):
                        does_match.append(1)
                if not does_match:
                    continue

            self.read_arrays(array_name)

            arraybyid = self.ph5.Array_t[array_name]['byid']
            arrayorder = self.ph5.Array_t[array_name]['order']

            for station in arrayorder:

                if self.station_id:
                    does_match = []
                    sta_list = self.station_id.split(',')
                    for x in sta_list:
                        if station == x:
                            does_match.append(1)
                    if not does_match:
                        continue

                station_list = arraybyid.get(station)
                for deployment in station_list:
                    start_times = []

                    station_list[deployment][0]['seed_station_name_s']
                    

                    if self.station:
                        does_match = []
                        sta_patterns = self.station.split(',')
                        for pattern in sta_patterns:
                            if fnmatch.fnmatch((station_list[deployment][0]
                                    ['seed_station_name_s']), pattern):
                                
                                does_match.append(1)
                        if not does_match:
                            continue
                    

                    if (self.eventnumbers and
                            self.shotline and matched_shot_line):
                        if not self.length:
                            # print "error: length must be specified.
                            # Use -l option"
                            sys.exit()
                        eventnumbers = self.eventnumbers.split(',')
                        for evt in eventnumbers:
                            try:
                                event_t = self.ph5.Event_t[
                                    matched_shot_line]['byid'][evt]
                                start_times.append(event_t['time/epoch_l'])
                                self.evt_lat = event_t['location/Y/value_d']
                                self.evt_lon = event_t['location/X/value_d']
                                # sys.exit()
                            except Exception:
                                error = 1

                    deploy = station_list[deployment][0]['deploy_time/epoch_l']
                    location = station_list[deployment][
                        0]['seed_location_code_s']
                    pickup = station_list[deployment][0]['pickup_time/epoch_l']
                    das = station_list[deployment][0]['das/serial_number_s']

                    if 'sample_rate_i' in station_list[deployment][0]:
                        sample_rate = station_list[deployment
                                                   ][0]['sample_rate_i']
                    sample_rate_multiplier = 1
                    if ('sample_rate_multiplier_i' in
                            station_list[deployment][0]):
                        sample_rate_multiplier = station_list[
                            deployment][0]['sample_rate_multiplier_i']

                    if self.sample_rate_list:
                        does_match = []
                        sample_list = self.sample_rate_list.split(',')
                        for x in sample_list:
                            if sample_rate == int(x):
                                does_match.append(1)
                        if not does_match:
                            continue

                    if 'seed_band_code_s' in station_list[deployment][0]:
                        band_code = station_list[deployment][
                            0]['seed_band_code_s']
                    else:
                        band_code = "D"
                    if 'seed_instrument_code_s' in station_list[deployment][0]:
                        instrument_code = station_list[deployment][
                            0]['seed_instrument_code_s']
                    else:
                        instrument_code = "P"
                    if ('seed_orientation_code_s' in
                            station_list[deployment][0]):
                        orientation_code = station_list[deployment][
                            0]['seed_orientation_code_s']
                    else:
                        orientation_code = "X"

                    c = station_list[deployment][0]['channel_number_i']

                    if self.component:
                        component_list = self.component.split(',')
                        if str(c) not in component_list:
                            continue

                    full_code = band_code + instrument_code + orientation_code
                    
                    if self.channel:
                        does_match = []
                        cha_patterns = self.channel.split(',')
                        for pattern in cha_patterns:
                            if fnmatch.fnmatch(full_code, pattern):
                                does_match.append(1)
                        if not does_match:
                            continue
                    if self.das_sn and self.das_sn != das:
                        continue

                    if self.start_time and not matched_shot_line:

                        if "T" not in self.start_time:
                            check_start_time = passcal2epoch(self.start_time)
                            if float(check_start_time) > float(deploy):
                                start_fepoch = self.start_time
                                start_times.append(passcal2epoch(start_fepoch))
                            else:
                                start_times.append(deploy)

                        else:
                            check_start_time = fdsntimetoepoch(self.start_time)
                            if float(check_start_time) > float(deploy):
                                start_times.append(fdsntimetoepoch(
                                    self.start_time))
                            else:
                                start_times.append(deploy)
                        if float(check_start_time) > float(pickup):
                            continue
                    elif not matched_shot_line:
                        start_times.append(ph5API.fepoch(station_list[
                            deployment][0]
                            ['deploy_time/epoch_l'],
                            station_list[deployment][0]
                            ['deploy_time/micro_seconds_i']))

                    for start_fepoch in start_times:

                        if self.length:
                            stop_fepoch = start_fepoch + self.length

                        elif self.end_time:

                            if "T" not in self.end_time:
                                check_end_time = passcal2epoch(self.end_time)

                                if float(check_end_time) < float(pickup):

                                    stop_fepoch = self.end_time
                                    stop_fepoch = passcal2epoch(stop_fepoch)
                                else:
                                    stop_fepoch = pickup

                            else:
                                check_end_time = fdsntimetoepoch(self.end_time)
                                if float(check_end_time) < float(pickup):
                                    stop_fepoch = fdsntimetoepoch(
                                        self.end_time)
                                else:
                                    stop_fepoch = pickup

                            if float(check_end_time) < float(deploy):
                                continue
                        else:
                            stop_fepoch = ph5API.fepoch(
                                station_list[deployment
                                             ][0]['pickup_time/epoch_l'],
                                station_list[deployment]
                                [0]['pickup_time/micro_seconds_i'])

                        if (self.use_deploy_pickup is True and not
                                ((start_fepoch >= deploy and
                                  stop_fepoch <= pickup))):
                            # das not deployed within deploy/pickup time
                            continue

                        start_passcal = epoch2passcal(start_fepoch, sep=':')
                        start_passcal_list = start_passcal.split(":")
                        start_doy = start_passcal_list[1]

                        if self.offset:
                            start_fepoch += int(self.offset)

                        if self.doy_keep:
                            if start_doy not in self.doy:
                                continue

                        if (stop_fepoch - start_fepoch) > 86400:
                            seconds_covered = 0
                            total_seconds = stop_fepoch - start_fepoch
                            times_to_cut = []
                            stop_time, seconds = doy_breakup(start_fepoch)
                            seconds_covered = seconds_covered + seconds
                            times_to_cut.append([start_fepoch, stop_time])
                            start_time = stop_time

                            while seconds_covered < total_seconds:
                                stop_time, seconds = doy_breakup(start_time)
                                seconds_covered += seconds
                                times_to_cut.append([start_time, stop_time])
                                start_time = stop_time
                        else:
                            times_to_cut = [[start_fepoch, stop_fepoch]]
                            times_to_cut[-1][-1] = stop_fepoch

                        if int(times_to_cut[-1][-2]) == int(
                                times_to_cut[-1][-1]):
                            del times_to_cut[-1]

                        latitude = station_list[deployment][
                            0]['location/Y/value_d']
                        longitude = station_list[deployment][
                            0]['location/X/value_d']

                        for x in times_to_cut:
                            station_x = StationCut(
                                experiment_t[0]['net_code_s'],
                                station,
                                das,
                                c,
                                full_code,
                                x[0],
                                x[1],
                                sample_rate,
                                sample_rate_multiplier,
                                self.notimecorrect,
                                location,
                                latitude,
                                longitude)

                            self.ph5.read_das_t(station_x.das,
                                                station_x.starttime,
                                                station_x.endtime,
                                                reread=False)

                            if not self.ph5.Das_t.has_key(station_x.das):
                                continue

                            yield station_x

        return

    def process_all(self):

        cuts = self.create_cut_list()
        # self.ph5.close()
        for cut in cuts:
            stream = self.create_trace(cut)
            if stream is not None:
                yield stream

        return


def get_args():

    import argparse

    parser = argparse.ArgumentParser(
        description='Return mseed from a PH5 file.',
        usage='Version: {0} ph5tomsAPI --nickname="Master_PH5_file" [options]'
        .format(PROG_VERSION))

    parser.add_argument(
        "-n", "--nickname", action="store", required=True,
        type=str, metavar="nickname")

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    parser.add_argument(
        '--network',
        help=argparse.SUPPRESS,
        default='XX')
    #   This should be SEED channel?
    parser.add_argument(
        "--channel", action="store",
        type=str, dest="channel",
        help="Comma separated list of SEED channels to extract",
        metavar="channel",
        default=[])

    parser.add_argument(
        "-e", "--eventnumbers", action="store",
        type=str, metavar="eventnumbers", default="")

    parser.add_argument(
        "--shotline", action="store",
        type=str, metavar="shotline", default=None)

    parser.add_argument(
        "--stream", action="store_true", default=False,
        help="Stream output to stdout.")

    parser.add_argument(
        "-s", "--starttime", action="store",
        type=str, dest="start_time", metavar="start_time",
        help="Time formats are YYYY:DOY:HH:MM:SS.ss or YYYY-mm-ddTHH:MM:SS.ss")

    parser.add_argument(
        "-t", "--stoptime", action="store",
        type=str, dest="stop_time", metavar="stop_time",
        help="Time formats are YYYY:DOY:HH:MM:SS.ss or YYYY-mm-ddTHH:MM:SS.ss")

    parser.add_argument(
        "-a", "--array", action="store",
        help="Comma separated list of arrays to extract",
        type=str, dest="array", metavar="array")

    parser.add_argument(
        "-O", "--offset", action="store",
        type=float, dest="offset", metavar="offset",
        help="Offset time in seconds")

    parser.add_argument(
        "-c", "--component", action="store",
        type=str, dest="component",
        help="Comma separated list of channel numbers to extract",
        metavar="component",
        default=[])

    parser.add_argument(
        "-d", "--decimation", action="store",
        choices=["2", "4", "5", "8", "10", "20"],
        metavar="decimation", default=None)

    parser.add_argument(
        "--station", action="store", dest="sta_list",
        help="Comma separated list of SEED station id's",
        metavar="sta_list", type=str, default=[])

    parser.add_argument(
        "--station_id", action="store", dest="sta_id_list",
        help="Comma separated list of PH5 station id's",
        metavar="sta_id_list", type=str, default=[])

    parser.add_argument(
        "-r", "--sample_rate_keep", action="store",
        dest="sample_rate",
        help="Comma separated list of sample rates to extract",
        metavar="sample_rate", type=str)

    parser.add_argument(
        "-V", "--reduction_velocity", action="store",
        dest="red_vel",
        metavar="red_vel",
        type=float, default="-1.", help=argparse.SUPPRESS)

    parser.add_argument(
        "-l", "--length", action="store",
        type=int, dest="length", metavar="length")

    parser.add_argument(
        "--notimecorrect",
        action="store_true",
        default=False)

    parser.add_argument(
        "-o", "--out_dir", action="store",
        metavar="out_dir", type=str, default=".")

    parser.add_argument(
        "--use_deploy_pickup", action="store_true", default=False,
        help="Use deploy/pickuop times to determine if data exists.",
        dest="deploy_pickup")

    parser.add_argument(
        '--dasskip',  metavar='dasskip',
        help=argparse.SUPPRESS)

    parser.add_argument(
        "-D", "--das", action="store", dest="das_sn",
        metavar="das_sn", type=str, help=argparse.SUPPRESS, default=None)

    parser.add_argument(
        "-Y", "--doy", action="store", dest="doy_keep",
        help=argparse.SUPPRESS,
        metavar="doy_keep", type=str)

    parser.add_argument(
        "-F", "-f", "--format", action="store", dest="format",
        help="SAC or MSEED",
        metavar="format", type=str)

    parser.add_argument(
        "--previewimages",
        help="produce png images of traces",
        action="store_true",
        default=False)

    the_args = parser.parse_args()

    return the_args


if __name__ == '__main__':

    from time import time as tm

    then = tm()

    args = get_args()

    # print PH5_PATH, PH5_FILE

    if args.nickname[-3:] == 'ph5':
        ph5file = os.path.join(args.ph5path, args.nickname)
    else:
        ph5file = os.path.join(args.ph5path, args.nickname + '.ph5')
        args.nickname += '.ph5'

    if not os.path.exists(ph5file):
        sys.stderr.write("Error: %s not found.\n" % ph5file)
        sys.exit(-1)

    ph5API_object = ph5API.ph5(path=args.ph5path, nickname=args.nickname)

    ph5ms = PH5toMSeed(
        ph5API_object, args.array, args.length, args.offset,
        args.component, args.sta_list, args.network,
        args.channel, args.das_sn,  args.deploy_pickup,
        args.decimation, args.sample_rate, args.doy_keep, args.stream,
        args.out_dir, args.start_time, args.stop_time, args.red_vel,
        args.dasskip, args.shotline, args.eventnumbers,
        args.notimecorrect, args.sta_id_list)

    streams = ph5ms.process_all()

    if args.format and args.format.upper() == "MSEED":
        for t in streams:
            if not args.stream:
                t.write(ph5ms.filenamemseed_gen(t), format='MSEED',
                        reclen=4096)
                if args.previewimages is True:
                    t.plot(outfile=ph5ms.filenamemsimg_gen(t),
                           bgcolor="#DCD3ED", color="#272727",
                           face_color="#DCD3ED")

            else:
                t.write(sys.stdout, format='MSEED', reclen=4096)

    elif args.format and args.format.upper() == "SAC":
        for t in streams:
            if not args.stream:
                t.write(ph5ms.filenamesac_gen(t), format='SAC')
                if args.previewimages is True:
                    t.plot(outfile=ph5ms.filenamesacimg_gen(t),
                           bgcolor="#DCD3ED", color="#272727",
                           face_color="#DCD3ED")

            else:
                t.write(sys.stdout, format='SAC')

    else:

        for t in streams:

            if not args.stream:
                t.write(ph5ms.filenamemseed_gen(t), format='MSEED',
                        reclen=4096)

                if args.previewimages is True:
                    t.plot(outfile=ph5ms.filenamemsimg_gen(t),
                           bgcolor="#DCD3ED", color="#272727",
                           face_color="#DCD3ED")
            else:
                t.write(sys.stdout, format='MSEED', reclen=4096)

    print tm() - then
