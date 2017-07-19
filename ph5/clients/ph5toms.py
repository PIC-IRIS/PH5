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
import copy
import itertools
from ph5.core import ph5utils
from ph5.core import ph5api
from ph5.core.timedoy import epoch2passcal, passcal2epoch


PROG_VERSION = "2017.192"


class StationCut(object):

    def __init__(self, net_code, station, seed_station, das, channel,
                 seed_channel, starttime, endtime,
                 sample_rate, sample_rate_multiplier,
                 notimecorrect, location, latitude, longitude):

        self.net_code = net_code
        self.station = station
        self.seed_station = seed_station
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
        
    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class PH5toMSAPIError(Exception):
    """Exception raised when there is a problem with the request.
    :param: message -- explanation of the error
    """
    def __init__(self, message):
        self.message = message


class PH5toMSeed(object):

    def __init__(self, ph5API_object, out_dir=".", reqtype="FDSN", netcode=None, station=[], 
                 station_id=[], channel=[], component=[], 
                 array=[], shotline=None, eventnumbers=None,
                 length=None, starttime=None, stoptime=None, offset=None, 
                 das_sn=None,  use_deploy_pickup=False, decimation=None,
                 sample_rate_keep=None, doy_keep=[], stream=False, 
                 reduction_velocity=-1., notimecorrect=False,  restricted=[]):

        self.chan_map = {1: 'Z', 2: 'N', 3: 'E', 4: 'Z', 5: 'N', 6: 'E'}
        self.reqtype = reqtype.upper()
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
        self.restricted = restricted
        
        if self.reqtype != "SHOT" and self.reqtype != "FDSN":
            raise PH5toMSAPIError("Error - Invalid request type {0}. "
                                  "Choose from FDSN or SHOT.".format(self.reqtype)) 
        
        if not self.ph5.Array_t_names:
            self.ph5.read_array_t_names()

        if not self.ph5.Experiment_t:
            self.ph5.read_experiment_t()
        
        if self.reqtype == "SHOT":    
            self.ph5.read_event_t_names()

        if not self.stream and not os.path.exists(self.out_dir):
            try:
                os.mkdir(self.out_dir)
            except Exception:
                raise PH5toMSAPIError("Error - Cannot create {0}.".format(self.out_dir))

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
    
    @classmethod
    def get_nonrestricted_segments(cls, station_to_cut_list, restricted, station_to_cut_segments=[]):
        """
        Recursively trim station_to_cut request to remove restricted segments. The result is a list of StationCut
        objects that contain only non-restricted data requests.
        
        :param station_to_cut: A StationCut object
        :type: StationCut
        :returns:
            Returns a list of non-restricted StationCut objects
        :type: list<StationCut>
        """
        if restricted:
            if station_to_cut_segments == []:
                station_to_cut_list = copy.deepcopy(station_to_cut_list)
                restricted = copy.deepcopy(restricted)
                station_to_cut_segments = copy.deepcopy(station_to_cut_segments)
            for seg_to_cut in station_to_cut_list:
                is_restricted_sncl = False
                for r in restricted:
                    if r.network == seg_to_cut.net_code and \
                       r.station == seg_to_cut.seed_station and \
                       r.location == seg_to_cut.location and \
                       r.channel == seg_to_cut.seed_channel:
                        is_restricted_sncl = True
                        # restricted-range-start <= station_to_cut <= restricted-range-end
                        # -- station_to_cut inside restricted-range
                        if (seg_to_cut.starttime >= r.starttime and \
                            seg_to_cut.starttime <= r.endtime) and \
                           (seg_to_cut.endtime >= r.starttime and \
                            seg_to_cut.endtime <= r.endtime):
                            continue # completely skip restricted request
                        # restricted-range-start > station_to_cut < restricted-range-end
                        # -- station_to_cut starts before restricted-range, ends inside restricted-range
                        elif(seg_to_cut.starttime <= r.starttime and \
                             seg_to_cut.starttime <= r.endtime) and \
                            (seg_to_cut.endtime >= r.starttime  and \
                             seg_to_cut.endtime <= r.endtime):
                            seg_to_cut.endtime = r.starttime-1
                            if seg_to_cut not in station_to_cut_segments:
                                station_to_cut_segments.append(seg_to_cut)
                            return PH5toMSeed.get_nonrestricted_segments(station_to_cut_segments,
                                                                   restricted,
                                                                   station_to_cut_segments)
                        # restricted-range-start < station_to_cut > restricted-range-end
                        # -- station_to_cut starts inside restricted-range, ends after restricted-range
                        elif(seg_to_cut.starttime >= r.starttime and \
                             seg_to_cut.starttime <= r.endtime) and \
                            (seg_to_cut.endtime >= r.starttime and \
                             seg_to_cut.endtime >= r.endtime):
                            seg_to_cut.starttime = r.endtime+1
                            if seg_to_cut not in station_to_cut_segments:
                                station_to_cut_segments.append(seg_to_cut)
                            return PH5toMSeed.get_nonrestricted_segments(station_to_cut_segments,
                                                                   restricted,
                                                                   station_to_cut_segments)
                        # restricted-range-start > station_to_cut > restricted-range-end 
                        # -- restricted-range inside station_to_cut
                        elif(seg_to_cut.starttime <= r.starttime and \
                             seg_to_cut.starttime <= r.endtime) and \
                            (seg_to_cut.endtime >= r.starttime and \
                             seg_to_cut.endtime >= r.endtime):
                            segment1 = seg_to_cut
                            segment2 = copy.deepcopy(seg_to_cut)
                            segment1.endtime = r.starttime-1
                            segment2.starttime = r.endtime+1
                            if segment1 not in station_to_cut_segments: 
                                station_to_cut_segments.append(segment1)
                            if segment2 not in station_to_cut_segments: 
                                station_to_cut_segments.append(segment2)
                            return PH5toMSeed.get_nonrestricted_segments(station_to_cut_segments, 
                                                                   restricted,
                                                                   station_to_cut_segments)
                        # -- restricted-range outside station_to_cut
                        else:
                            # entire segment is non-restricted
                            if seg_to_cut not in station_to_cut_segments:
                                station_to_cut_segments.append(seg_to_cut)
                if not is_restricted_sncl:
                    if seg_to_cut not in station_to_cut_segments:
                        station_to_cut_segments.append(seg_to_cut)
            return station_to_cut_segments
        else:
            return station_to_cut_list
    
    def create_trace(self, station_to_cut):
        
        station_to_cut_segments = PH5toMSeed.get_nonrestricted_segments([station_to_cut], self.restricted)
        obspy_stream = Stream()
        for stc in station_to_cut_segments:
            new_endtime= stc.endtime+(1/float(stc.sample_rate))
            self.ph5.read_das_t(stc.das, stc.starttime,
                                stc.endtime, reread=False)
    
            if not self.ph5.Das_t.has_key(stc.das):
                return
    
            Das_t = ph5api.filter_das_t(self.ph5.Das_t[stc.das]['rows'],
                                        stc.channel)
    
            das_t_start_no_micro = float(Das_t[0]['time/epoch_l'])
            das_t_start_micro_seconds = float(Das_t[0]['time/micro_seconds_i'])
            das_t_start = (float(Das_t[0]['time/epoch_l']) +
                           float(Das_t[0]['time/micro_seconds_i']) / 1000000)
    
            if float(das_t_start) > float(stc.starttime):
                start_time = das_t_start
                start_time_no_micro = int(das_t_start_no_micro)
                start_time_micro_seconds = int(das_t_start_micro_seconds)
 
    
            else:
                start_time = stc.starttime
                start_time_no_micro = stc.starttime
                start_time_micro_seconds = 0
    
            nt = stc.notimecorrect
            actual_sample_rate=float(stc.sample_rate)/float(stc.sample_rate_multiplier)

            traces = self.ph5.cut(stc.das, start_time,
                                  new_endtime,
                                  chan=stc.channel,
                                  sample_rate=actual_sample_rate,
                                  apply_time_correction=nt)
    
            if type(traces) is not list:
                return

            for trace in traces:
                if trace.nsamples == 0:
                    continue
                # if start time is before requested start time move up 1 sample and delete first sample of data
                if trace.start_time.epoch() < stc.starttime:
                    trace.start_time = trace.start_time+(1/float(stc.sample_rate))
                    trace.data=trace.data[1:]

                try:
                    obspy_trace = Trace(data=trace.data)
                except ValueError:
                    continue
                
                
                obspy_trace.stats.sampling_rate = actual_sample_rate
                obspy_trace.stats.location = stc.location
                obspy_trace.stats.station = stc.seed_station
                obspy_trace.stats.coordinates = AttribDict()
                obspy_trace.stats.coordinates.latitude = stc.latitude
                obspy_trace.stats.coordinates.longitude = stc.longitude
                obspy_trace.stats.channel = stc.seed_channel
                obspy_trace.stats.network = stc.net_code
                obspy_trace.stats.starttime = trace.start_time.getFdsnTime()
                if self.decimation:
                    obspy_trace.decimate(int(self.decimation))
                obspy_stream.append(obspy_trace)
    
        if len(obspy_stream.traces) < 1:
            return

        return obspy_stream
    
    def get_channel_and_component(self, station_list, deployment, st_num):
        if 'seed_band_code_s' in station_list[deployment][st_num]:
            band_code = station_list[deployment][
                st_num]['seed_band_code_s']
        else:
            band_code = "D"
        if 'seed_instrument_code_s' in station_list[deployment][st_num]:
            instrument_code = station_list[deployment][
                st_num]['seed_instrument_code_s']
        else:
            instrument_code = "P"
        if ('seed_orientation_code_s' in
                station_list[deployment][st_num]):
            orientation_code = station_list[deployment][
                st_num]['seed_orientation_code_s']
        else:
            orientation_code = "X"
        
        seed_cha_code = band_code + instrument_code + orientation_code
        component = station_list[deployment][st_num]['channel_number_i']
        
        return seed_cha_code, component
    
    def create_cut(self, seed_network, ph5_station, seed_station, 
                   start_times, station_list, deployment, st_num):
        deploy = station_list[deployment][st_num]['deploy_time/epoch_l']
        deploy_micro = station_list[deployment][st_num]['deploy_time/micro_seconds_i']
        pickup = station_list[deployment][st_num]['pickup_time/epoch_l']
        pickup_micro = station_list[deployment][st_num]['pickup_time/micro_seconds_i']
        location = station_list[deployment][
            st_num]['seed_location_code_s']
        das = station_list[deployment][st_num]['das/serial_number_s']
        
        if 'sample_rate_i' in station_list[deployment][0]:
            sample_rate = station_list[deployment][st_num]['sample_rate_i']
        sample_rate_multiplier = 1
        if ('sample_rate_multiplier_i' in
                station_list[deployment][st_num]):
            sample_rate_multiplier = station_list[
                deployment][st_num]['sample_rate_multiplier_i']
        
        if self.sample_rate_list:
            sample_list = self.sample_rate_list
            if not ph5utils.does_pattern_exists(sample_list, sample_rate):
                return
            
        seed_channel, component = self.get_channel_and_component(station_list, deployment, st_num)
        
        if self.component:
            component_list = self.component
            if not ph5utils.does_pattern_exists(component_list, component):
                return
        if self.channel:
            cha_patterns = self.channel
            if not ph5utils.does_pattern_exists(cha_patterns, seed_channel):
                return
        if self.das_sn and self.das_sn != das:
            return

        if self.reqtype == "FDSN":
            # trim user defined time range if it extends beyond the deploy/pickup times
            if self.start_time:    
                if "T" not in self.start_time:
                    check_start_time = passcal2epoch(self.start_time, fepoch=True)
                    if float(check_start_time) > float(deploy):
                        start_fepoch = self.start_time
                        start_times.append(passcal2epoch(start_fepoch, fepoch=True))
                    else:
                        start_times.append(deploy)
            
                else:
                    check_start_time = ph5utils.fdsntime_to_epoch(self.start_time)
                    if float(check_start_time) > float(deploy):
                        start_times.append(ph5utils.fdsntime_to_epoch(self.start_time))
                    else:
                        start_times.append(deploy)
                if float(check_start_time) > float(pickup):
                    return
            else:
                start_times.append(ph5api.fepoch(deploy,deploy_micro))
        
        for start_fepoch in start_times:
        
            if self.reqtype == "SHOT":
                if self.length:
                    stop_fepoch = start_fepoch + self.length
                else:
                    raise PH5toMSAPIError("Error - length is required for requst by shot.")
            elif self.reqtype == "FDSN":
                if self.end_time:
                    if "T" not in self.end_time:
                        check_end_time = passcal2epoch(self.end_time, fepoch=True)
                        
                        if float(check_end_time) < float(pickup):
            
                            stop_fepoch = self.end_time
                            stop_fepoch = passcal2epoch(stop_fepoch, fepoch=True)
                            
                        else:
                            stop_fepoch = pickup
            
                    else:
                        check_end_time = ph5utils.fdsntime_to_epoch(self.end_time)
                        if float(check_end_time) < float(pickup):
                            stop_fepoch = ph5utils.fdsntime_to_epoch(
                                self.end_time)
                        else:
                            stop_fepoch = pickup
            
                    if float(check_end_time) < float(deploy):
                        continue
                elif self.length:
                    stop_fepoch = start_fepoch + self.length  
                else:     
                    stop_fepoch = ph5api.fepoch(pickup, pickup_micro)                

            if (self.use_deploy_pickup is True and not
                    ((start_fepoch >= deploy and
                      stop_fepoch <= pickup))):
                # das not deployed within deploy/pickup time
                continue
            
            start_passcal = epoch2passcal(start_fepoch, sep=':')
            start_passcal_list = start_passcal.split(":")
            start_doy = start_passcal_list[1]
        
            if self.offset:
                # adjust starttime by an offset
                start_fepoch += int(self.offset)
        
            if self.doy_keep:
                if start_doy not in self.doy:
                    continue
        
            if (stop_fepoch - start_fepoch) > 86400:
                seconds_covered = 0
                total_seconds = stop_fepoch - start_fepoch
                times_to_cut = []
                stop_time, seconds = ph5utils.doy_breakup(start_fepoch)
                seconds_covered = seconds_covered + seconds
                times_to_cut.append([start_fepoch, stop_time])
                start_time = stop_time
        
                while seconds_covered < total_seconds:
                    stop_time, seconds = ph5utils.doy_breakup(start_time)
                    seconds_covered += seconds
                    if stop_time > stop_fepoch:
                        times_to_cut.append([start_time, stop_fepoch])
                        break;
                    times_to_cut.append([start_time, stop_time])
                    start_time = stop_time
            else:
                times_to_cut = [[start_fepoch, stop_fepoch]]
                times_to_cut[-1][-1] = stop_fepoch
        
            if int(times_to_cut[-1][-2]) == int(
                    times_to_cut[-1][-1]):
                del times_to_cut[-1]
        
            latitude = station_list[deployment][
                st_num]['location/Y/value_d']
            longitude = station_list[deployment][
                st_num]['location/X/value_d']
        
            for starttime, endtime in tuple(times_to_cut):
                
                self.ph5.read_das_t(das,
                                    starttime,
                                    endtime,
                                    reread=False)
                
                if not self.ph5.Das_t.has_key(das):
                    continue
                
                station_x = StationCut(
                    seed_network,
                    ph5_station,
                    seed_station,
                    das,
                    component,
                    seed_channel,
                    starttime,
                    endtime,
                    sample_rate,
                    sample_rate_multiplier,
                    self.notimecorrect,
                    location,
                    latitude,
                    longitude)

                yield station_x
                                
    def create_cut_list(self):
        cuts_generator = []

        experiment_t = self.ph5.Experiment_t['rows']
        
        try:
            seed_network = experiment_t[0]['net_code_s']
        except:
            raise PH5toMSAPIError("Error - No net_code_s entry in Experiment_t. "
                                  "Verify that this experiment is PH5 version >= PN4.")

        if self.netcode and self.netcode != seed_network:
            raise PH5toMSAPIError(
                    "Error - The requested SEED network code does "
                    "not match this PH5 experiment network code. "
                    "{0} != {1}".format(self.netcode, seed_network))
        
        array_names = self.ph5.Array_t_names
        array_names.sort()
        self.read_events(None)
        
        if self.reqtype == "SHOT":
            # create list of all matched shotlines and shot-ids for request by shot
            shot_lines = self.ph5.Event_t_names
            shot_lines.sort()
            matched_shot_lines = []
            matched_shots = []
            for shot_line in shot_lines:
                if not self.shotline or ph5utils.does_pattern_exists(self.shotline, shot_line[-3:]):
                    matched_shot_lines.append(shot_line)
                else:
                    continue
                event_t = self.ph5.Event_t[shot_line]['byid']
                for shot_id, _ in event_t.iteritems():
                    if not self.eventnumbers or ph5utils.does_pattern_exists(self.eventnumbers, shot_id):
                        matched_shots.append(shot_id)
                    else:
                        continue
            if self.shotline and not matched_shot_lines:
                raise PH5toMSAPIError("Error - requested shotline(s) do not exist.")
            elif self.eventnumbers and not matched_shots:
                raise PH5toMSAPIError("Error - requested shotid(s) do not exist.")

        for array_name in array_names:
            if self.array:
                array = array_name[-3:]
                array_patterns = self.array
                if not ph5utils.does_pattern_exists(array_patterns, str(array)):
                    continue

            self.read_arrays(array_name)

            arraybyid = self.ph5.Array_t[array_name]['byid']
            arrayorder = self.ph5.Array_t[array_name]['order']

            for ph5_station in arrayorder:
                if self.station_id:
                    sta_list = self.station_id
                    if not ph5utils.does_pattern_exists(sta_list, ph5_station):
                        continue

                station_list = arraybyid.get(ph5_station)

                for deployment in station_list:
                    start_times = []
                    station_len = len(station_list[deployment])
                    
                    for st_num in range(0,station_len):
                        
                        if station_list[deployment][st_num]['seed_station_name_s']:
                            seed_station = station_list[deployment][st_num]['seed_station_name_s']
                        else:
                            seed_station = station_list[deployment][st_num]['id_s']

                        if self.station:
                            sta_patterns = self.station
                            if not ph5utils.does_pattern_exists(sta_patterns, 
                                        seed_station):
                                continue
                        if self.reqtype == "SHOT":
                            # request by shot
                            for shotline in matched_shot_lines:
                                for shot in matched_shots:
                                    try:
                                        event_t = self.ph5.Event_t[
                                            shotline]['byid'][shot]
                                        start_times.append(event_t['time/epoch_l'])
                                        self.evt_lat = event_t['location/Y/value_d']
                                        self.evt_lon = event_t['location/X/value_d']
                                    except Exception:
                                        raise PH5toMSAPIError("Error reading events table.") 
                                cuts_generator.append(self.create_cut(seed_network, ph5_station, seed_station,
                                                       start_times, station_list, deployment, st_num))
                        elif self.reqtype == "FDSN":
                            # fdsn request
                            cuts_generator.append(self.create_cut(seed_network, ph5_station, seed_station,
                                                   start_times, station_list, deployment, st_num))
                            
        return itertools.chain.from_iterable(cuts_generator)

    def process_all(self):
        cuts = self.create_cut_list()
        for cut in cuts:
            stream = self.create_trace(cut)
            if stream is not None:
                yield stream


def get_args():

    import argparse

    parser = argparse.ArgumentParser(
        description='Return mseed from a PH5 file.',
        usage='Version: {0} ph5toms --nickname="Master_PH5_file" [options]'
        .format(PROG_VERSION))

    parser.add_argument(
        "-n", "--nickname", action="store", required=True,
        type=str, metavar="nickname")

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")
    
    parser.add_argument(
        "-o", "--out_dir", action="store",
        metavar="out_dir", type=str, default=".")
    
    parser.add_argument(
        "--reqtype", action="store",
        type=str, default="FDSN")

    parser.add_argument(
        '--network',
        help=argparse.SUPPRESS,
        default=None)

    parser.add_argument(
        "--channel", action="store",
        type=str, dest="channel",
        help="Comma separated list of SEED channels to extract",
        metavar="channel",
        default=[])
    
    parser.add_argument(
        "-c", "--component", action="store",
        type=str, dest="component",
        help="Comma separated list of channel numbers to extract",
        metavar="component",
        default=[])

    parser.add_argument(
        "--shotline", action="store",
        type=str, metavar="shotline", default=[])
    
    parser.add_argument(
        "-e", "--eventnumbers", action="store",
        type=str, metavar="eventnumbers", default=[])

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
        type=float, default=-1., help=argparse.SUPPRESS)

    parser.add_argument(
        "-l", "--length", action="store", default=None,
        type=int, dest="length", metavar="length")

    parser.add_argument(
        "--notimecorrect",
        action="store_true",
        default=False)

    parser.add_argument(
        "--use_deploy_pickup", action="store_true", default=True,
        help="Use deploy/pickup times to determine if data exists.",
        dest="deploy_pickup")

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
        metavar="format", type=str, default="MSEED")

    parser.add_argument(
        "--previewimages",
        help="produce png images of traces",
        action="store_true",
        default=False)

    the_args = parser.parse_args()

    return the_args


def main():
    from time import time as tm

    then = tm()

    args = get_args()

    if args.nickname[-3:] == 'ph5':
        ph5file = os.path.join(args.ph5path, args.nickname)
    else:
        ph5file = os.path.join(args.ph5path, args.nickname + '.ph5')
        args.nickname += '.ph5'

    if not os.path.exists(ph5file):
        sys.stderr.write("Error - {0} not found.\n".format(ph5file))
        sys.exit(-1)

    ph5API_object = ph5api.PH5(path=args.ph5path, nickname=args.nickname)

    if args.array:
        args.array = args.array.split(',')
    if args.sta_id_list:
        args.sta_id_list=args.sta_id_list.split(',')
    if args.sta_list:
        args.sta_list=args.sta_list.split(',')
    if args.shotline:
        args.shotline = args.shotline.split(',')
    if args.eventnumbers:
        args.eventnumbers= args.eventnumbers.split(',')
    if args.sample_rate:
        args.sample_rate = args.sample_rate.split(',')
    if args.component:
        args.component = args.component.split(',')
    if args.channel:
        args.channel = args.channel.split(',')

    try:
        ph5ms = PH5toMSeed( ph5API_object, out_dir=args.out_dir, reqtype=args.reqtype, 
                 netcode=args.network, station=args.sta_list, station_id=args.sta_id_list, 
                 channel=args.channel, component=args.component, array=args.array, 
                 shotline=args.shotline, eventnumbers=args.eventnumbers, length=args.length, 
                 starttime=args.start_time, stoptime=args.stop_time, offset=args.offset, 
                 das_sn=args.das_sn,  use_deploy_pickup= args.deploy_pickup, 
                 decimation=args.decimation, sample_rate_keep=args.sample_rate, doy_keep=args.doy_keep, 
                 stream=args.stream, reduction_velocity=args.red_vel, notimecorrect=args.notimecorrect)

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

    except PH5toMSAPIError as err:
        sys.stderr.write("{0}\n".format(err.message))
        exit(-1)

    sys.stdout.write(str(tm() - then))
    
    ph5API_object.close()


if __name__ == '__main__':
    main()
