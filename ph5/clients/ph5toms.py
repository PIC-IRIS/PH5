# Derick Hess, Oct 2016

"""
Extracts data from PH5 in miniSEED and SAC formats.
Also allows for creation of preview png images of traces.
"""


import sys
import os
import logging
import copy
import itertools
import io
import datetime
from obspy.core.inventory.inventory import read_inventory as read_inventory
from obspy import Trace
from obspy import Stream
from obspy.core.util import AttribDict
from obspy.io.sac import SACTrace
from ph5.core import ph5utils, experiment
from ph5.core.ph5utils import PH5ResponseManager
from ph5.core import ph5api
from ph5.core.timedoy import epoch2passcal, passcal2epoch

PROG_VERSION = '2019.93'
LOGGER = logging.getLogger(__name__)


class StationCut(object):

    def __init__(self, net_code, experiment_id, station, seed_station,
                 array_code, das, das_manufacturer, das_model,
                 sensor_type, component, seed_channel,
                 starttime, endtime, sample_rate,
                 sample_rate_multiplier, notimecorrect,
                 location, latitude, longitude, elev,
                 receiver_n_i, response_n_i, shot_id=None,
                 shot_lat=None, shot_lng=None, shot_elevation=None):

        self.net_code = net_code
        self.experiment_id = experiment_id
        self.station = station
        self.seed_station = seed_station
        self.array_code = array_code
        self.location = location
        self.seed_channel = seed_channel
        self.component = component
        self.das = das
        self.das_manufacturer = das_manufacturer
        self.das_model = das_model
        self.sensor_type = sensor_type
        self.starttime = starttime
        self.endtime = endtime
        self.sample_rate = sample_rate
        self.sample_rate_multiplier = sample_rate_multiplier
        self.notimecorrect = notimecorrect
        self.latitude = latitude
        self.longitude = longitude
        self.elev = elev
        self.receiver_n_i = receiver_n_i
        self.response_n_i = response_n_i
        # optional attributes
        self.shot_id = shot_id
        self.shot_lat = shot_lat
        self.shot_lng = shot_lng
        self.shot_elevation = shot_elevation

    def __str__(self):
        return (
            "net_code: {}"
            "experiment_id: {}"
            "station: {}"
            "seed_station: {}"
            "array_code: {}"
            "location: {}"
            "seed_channel: {}"
            "component: {}"
            "das: {}"
            "das_manufacturer: {}"
            "das_model: {}"
            "sensor_type: {}"
            "starttime: {}"
            "endtime: {}"
            "sample_rate: {}"
            "sample_rate_multiplier: {}"
            "notimecorrect: {}"
            "latitude: {}"
            "longitude: {}"
            "elev: {}"
            "receiver_n_i: {}"
            "response_n_i: {}"
            "shot_id: {}"
            "shot_lat: {}"
            "shot_lng: {}"
            "shot_elevation: {}"
            .format(
                self.net_code, self.experiment_id, self.station,
                self.seed_station, self.array_code, self.location,
                self.seed_channel, self.component, self.das,
                self.das_manufacturer, self.das_model, self.sensor_type,
                self.starttime, self.endtime, self.sample_rate,
                self.sample_rate_multiplier, self.notimecorrect,
                self.latitude, self.longitude, self.elev,
                self.receiver_n_i, self.response_n_i, self.shot_id,
                self.shot_lat, self.shot_lng, self.shot_elevation,
            )
        )

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class StationCutTime(object):
    """
    Allows for the association of cut times with events. This comes in handy
    when writing SEG-Y since event information is sometimes included the SEG-Y
    Trace headers.
    """

    def __init__(self, time, shot_id=None, shot_lat=None, shot_lng=None,
                 shot_elevation=None):
        self.time = time
        self.shot_id = shot_id
        self.shot_lat = shot_lat
        self.shot_lng = shot_lng
        self.shot_elevation = shot_elevation


class PH5toMSAPIError(Exception):
    """Exception raised when there is a problem with the request.
    :param: message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class PH5toMSeed(object):

    def __init__(self, ph5API_object, out_dir=".", reqtype="FDSN",
                 netcode=None, station=[], station_id=[], channel=[],
                 component=[], array=[], shotline=None, eventnumbers=None,
                 length=None, starttime=None, stoptime=None, offset=None,
                 das_sn=None, use_deploy_pickup=False, decimation=None,
                 sample_rate_keep=None, doy_keep=[], stream=False,
                 reduction_velocity=-1., notimecorrect=False,
                 restricted=[], format='MSEED', cut_len=86400,
                 log_epoch=False):

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
        self.format = format
        self.cut_len = cut_len
        self.hash_list = []
        self.log_epoch = log_epoch

        self.resp_manager = PH5ResponseManager()

        if not self.ph5.Array_t_names:
            self.ph5.read_array_t_names()

        if not self.ph5.Experiment_t:
            self.ph5.read_experiment_t()

        if self.reqtype == "SHOT" or self.reqtype == "RECEIVER":
            self.ph5.read_event_t_names()

        if not self.stream and not os.path.exists(self.out_dir):
            try:
                os.mkdir(self.out_dir)
            except Exception:
                raise PH5toMSAPIError(
                    "Error - Cannot create {0}.".format(self.out_dir))

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
        new_start = s.starttime.isoformat()
        try:
            rounded = ph5utils.roundSeconds(
                datetime.datetime.strptime(
                    new_start,
                    "%Y-%m-%dT%H:%M:%S.%f"))
        except BaseException:
            rounded = ph5utils.roundSeconds(
                datetime.datetime.strptime(
                    new_start,
                    "%Y-%m-%dT%H:%M:%S"))
        ret = "{0}.{1}.{2}.{3}.{4}.ms".format(
            s.network, s.station, s.location,
            s.channel, rounded.strftime("%Y-%m-%dT%H.%M.%S"))
        if not self.stream:
            ret = os.path.join(self.out_dir, ret)
        return ret

    def filenamesac_gen(self, trace):
        s = trace.stats
        new_start = s.starttime.isoformat()
        try:
            rounded = ph5utils.roundSeconds(
                datetime.datetime.strptime(
                    new_start,
                    "%Y-%m-%dT%H:%M:%S.%f"))
        except BaseException:
            rounded = ph5utils.roundSeconds(
                datetime.datetime.strptime(
                    new_start,
                    "%Y-%m-%dT%H:%M:%S"))
        ret = "{0}.{1}.{2}.{3}.{4}.sac".format(
            s.network, s.station, s.location,
            s.channel, rounded.strftime("%Y-%m-%dT%H.%M.%S"))
        if not self.stream:
            ret = os.path.join(self.out_dir, ret)
        return ret

    def filenamegeocsv_gen(self, trace):
        s = trace.stats
        new_start = s.starttime.isoformat()
        try:
            rounded = ph5utils.roundSeconds(
                datetime.datetime.strptime(
                    new_start,
                    "%Y-%m-%dT%H:%M:%S.%f"))
        except BaseException:
            rounded = ph5utils.roundSeconds(
                datetime.datetime.strptime(
                    new_start,
                    "%Y-%m-%dT%H:%M:%S"))
        ret = "{0}.{1}.{2}.{3}.{4}.csv".format(
            s.network, s.station, s.location,
            s.channel, rounded.strftime("%Y-%m-%dT%H.%M.%S"))
        if not self.stream:
            ret = os.path.join(self.out_dir, ret)
        return ret

    def filenamemseed_nongen(self, stream):
        s = stream.traces[0].stats
        new_start = s.starttime.isoformat()
        try:
            rounded = ph5utils.roundSeconds(
                datetime.datetime.strptime(
                    new_start,
                    "%Y-%m-%dT%H:%M:%S.%f"))
        except BaseException:
            rounded = ph5utils.roundSeconds(
                datetime.datetime.strptime(
                    new_start,
                    "%Y-%m-%dT%H:%M:%S"))
        ret = "{0}.{1}.{2}.{3}.ms".format(
            s.array, s.station, s.channel,
            rounded.strftime("%Y-%m-%dT%H.%M.%S"))
        if not self.stream:
            ret = os.path.join(self.out_dir, ret)
        return ret

    def filenamesac_nongen(self, trace):
        s = trace.stats
        new_start = s.starttime.isoformat()
        try:
            rounded = ph5utils.roundSeconds(
                datetime.datetime.strptime(
                    new_start,
                    "%Y-%m-%dT%H:%M:%S.%f"))
        except BaseException:
            rounded = ph5utils.roundSeconds(
                datetime.datetime.strptime(
                    new_start,
                    "%Y-%m-%dT%H:%M:%S"))
        ret = "{0}.{1}.{2}.{3}.sac".format(
            s.array, s.station, s.channel,
            rounded.strftime("%Y-%m-%dT%H.%M.%S"))
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

    def filenamesacimg_gen(self, trace):

        s = trace.stats
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
    def get_nonrestricted_segments(
            cls, station_to_cut_list, restricted, station_to_cut_segments=[]):
        """
        Recursively trim station_to_cut request to remove restricted segments.
        The result is a list of StationCut
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
                station_to_cut_segments = copy.deepcopy(
                    station_to_cut_segments)
            for seg_to_cut in station_to_cut_list:
                is_restricted_sncl = False
                for r in restricted:
                    if r.network == seg_to_cut.net_code and \
                       r.station == seg_to_cut.seed_station and \
                       r.location == seg_to_cut.location and \
                       r.channel == seg_to_cut.seed_channel:
                        is_restricted_sncl = True
                        # restricted-range-start
                        # <= station_to_cut <= restricted-range-end
                        # -- station_to_cut inside restricted-range
                        if (seg_to_cut.starttime >= r.starttime and
                            seg_to_cut.starttime <= r.endtime) and \
                           (seg_to_cut.endtime >= r.starttime and
                                seg_to_cut.endtime <= r.endtime):
                            continue  # completely skip restricted request
                        # restricted-range-start > station_to_cut
                        # < restricted-range-end
                        # -- station_to_cut starts before restricted-range,
                        # ends inside restricted-range
                        elif(seg_to_cut.starttime <= r.starttime and
                             seg_to_cut.starttime <= r.endtime) and \
                            (seg_to_cut.endtime >= r.starttime and
                             seg_to_cut.endtime <= r.endtime):
                            seg_to_cut.endtime = r.starttime - 1
                            if seg_to_cut not in station_to_cut_segments:
                                station_to_cut_segments.append(seg_to_cut)
                            return PH5toMSeed.get_nonrestricted_segments(
                                station_to_cut_segments,
                                restricted,
                                station_to_cut_segments)
                        # restricted-range-start < station_to_cut >
                        # restricted-range-end
                        # -- station_to_cut starts inside restricted-range,
                        # ends after restricted-range
                        elif(seg_to_cut.starttime >= r.starttime and
                             seg_to_cut.starttime <= r.endtime) and \
                            (seg_to_cut.endtime >= r.starttime and
                             seg_to_cut.endtime >= r.endtime):
                            seg_to_cut.starttime = r.endtime + 1
                            if seg_to_cut not in station_to_cut_segments:
                                station_to_cut_segments.append(seg_to_cut)
                            return PH5toMSeed.get_nonrestricted_segments(
                                station_to_cut_segments,
                                restricted,
                                station_to_cut_segments)
                        # restricted-range-start > station_to_cut >
                        # restricted-range-end
                        # -- restricted-range inside station_to_cut
                        elif(seg_to_cut.starttime <= r.starttime and
                             seg_to_cut.starttime <= r.endtime) and \
                            (seg_to_cut.endtime >= r.starttime and
                             seg_to_cut.endtime >= r.endtime):
                            segment1 = seg_to_cut
                            segment2 = copy.deepcopy(seg_to_cut)
                            segment1.endtime = r.starttime - 1
                            segment2.starttime = r.endtime + 1
                            if segment1 not in station_to_cut_segments:
                                station_to_cut_segments.append(segment1)
                            if segment2 not in station_to_cut_segments:
                                station_to_cut_segments.append(segment2)
                            return PH5toMSeed.get_nonrestricted_segments(
                                station_to_cut_segments,
                                restricted, station_to_cut_segments)
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

    def get_response_obj(self, stc):
        sensor_keys = [stc.sensor_type]
        datalogger_keys = [stc.das_manufacturer,
                           stc.das_model,
                           stc.sample_rate]
        if not self.resp_manager.is_already_requested(sensor_keys,
                                                      datalogger_keys):
            self.ph5.read_response_t()
            Response_t = self.ph5.get_response_t_by_n_i(stc.response_n_i)
            response_file_das_a_name = Response_t.get('response_file_das_a',
                                                      None)
            response_file_sensor_a_name = Response_t.get(
                                                    'response_file_sensor_a',
                                                    None)
            # parse datalogger response
            if response_file_das_a_name:
                response_file_das_a = \
                    self.ph5.ph5_g_responses.get_response(
                                                    response_file_das_a_name
                                            )
                with io.BytesIO(response_file_das_a) as buf:
                    buf.seek(0, 0)
                    dl_resp = read_inventory(buf, format="RESP")
                dl_resp = dl_resp[0][0][0].response
            # parse sensor response if present
            if response_file_sensor_a_name:
                response_file_sensor_a = \
                    self.ph5.ph5_g_responses.get_response(
                                                response_file_sensor_a_name
                                            )
                with io.BytesIO(response_file_sensor_a) as buf:
                    buf.seek(0, 0)
                    sensor_resp = read_inventory(buf, format="RESP")
                sensor_resp = sensor_resp[0][0][0].response

            inv_resp = None
            if response_file_das_a_name and response_file_sensor_a_name:
                # both datalogger and sensor response
                dl_resp.response_stages.pop(0)
                dl_resp.response_stages.insert(0,
                                               sensor_resp.response_stages[0])
                dl_resp.recalculate_overall_sensitivity()
                inv_resp = dl_resp
            elif response_file_das_a_name:
                # only datalogger response
                inv_resp = dl_resp
            elif response_file_sensor_a_name:
                # only sensor response
                inv_resp = sensor_resp

            # Add addtional information that is in Response_t
            inv_resp.stats = AttribDict()
            inv_resp.stats.gain_value = Response_t["gain/value_i"]
            inv_resp.stats.gain_units = Response_t["gain/units_s"]
            inv_resp.stats.bitweight_value = Response_t["bit_weight/value_d"]
            inv_resp.stats.bitweight_units = Response_t["bit_weight/units_s"]

            if inv_resp:
                # update response manager and return response
                self.resp_manager.add_response(sensor_keys,
                                               datalogger_keys,
                                               inv_resp)
                return inv_resp
        else:
            return self.resp_manager.get_response(sensor_keys,
                                                  datalogger_keys)

    def create_trace(self, station_to_cut, mp=False):
        station_to_cut_segments = PH5toMSeed.get_nonrestricted_segments(
            [station_to_cut], self.restricted)
        obspy_stream = Stream()
        sr_mismatch = False
        empty_times = True
        for stc in station_to_cut_segments:
            das = self.ph5.query_das_t(stc.das, stc.component,
                                       stc.starttime,
                                       stc.endtime,
                                       stc.sample_rate,
                                       stc.sample_rate_multiplier,
                                       check_samplerate=False)
            if not das:
                return
            das = [x for x in das]
            Das_tf = next(iter(das or []), None)
            if Das_tf is None:
                return
            else:
                das_t_start = (float(Das_tf['time/epoch_l']) +
                               float(Das_tf['time/micro_seconds_i']) / 1000000)
            if float(das_t_start) > float(stc.starttime):
                start_time = das_t_start

            else:
                start_time = stc.starttime
            nt = stc.notimecorrect
            for das_inst in das:
                # Does Array.sr == DAS.sr? If so use sr
                if das_inst['sample_rate_i'] == stc.sample_rate:
                    if das_inst['sample_rate_i'] > 0:
                        actual_sample_rate = float(stc.sample_rate) /\
                                             float(stc.sample_rate_multiplier)
                        empty_times = False
                    else:
                        actual_sample_rate = 0
                        empty_times = False
                else:
                    continue
            if empty_times is True:
                for i, das_inst in enumerate(das):
                    # Checks to see if all DAS tables have same SR
                    sr_prev = das[i-1]['sample_rate_i']
                    if das_inst['sample_rate_i'] != sr_prev:
                        sr_mismatch = True
                try:
                    if sr_mismatch is True:
                        # Else fail with error
                        LOGGER.error('DAS and Array Table sample' +
                                     ' rates do not match, DAS table' +
                                     ' sample rates do not match.' +
                                     ' Data must be updated.')
                        return
                    else:
                        # Uses DAS SR if consistent
                        das_sr = das_inst['sample_rate_i']
                        das_srm = das_inst['sample_rate_multiplier_i']
                        LOGGER.warning('Using sample rate from' +
                                       ' DAS Table. Sample rates' +
                                       ' in DAS and Array tables' +
                                       ' are not consistent.')
                        if das_inst['sample_rate_i'] > 0:
                            actual_sample_rate = float(das_sr) / float(das_srm)
                        else:
                            actual_sample_rate = 0
                except(UnboundLocalError):
                    continue
            if actual_sample_rate != 0:
                traces = self.ph5.cut(stc.das, start_time,
                                      stc.endtime,
                                      chan=stc.component,
                                      sample_rate=actual_sample_rate,
                                      apply_time_correction=nt, das_t=das)

            else:
                traces = self.ph5.textural_cut(stc.das,
                                               start_time,
                                               stc.endtime,
                                               chan=stc.component,
                                               das_t=das)
            if not isinstance(traces, list):
                return

            for trace in traces:
                if trace.nsamples == 0:
                    continue
                try:
                    obspy_trace = Trace(data=trace.data)
                except ValueError:
                    continue
                if self.format == "SAC":
                    Receiver_t = \
                        self.ph5.get_receiver_t_by_n_i(stc.receiver_n_i)
                    azimuth = Receiver_t['orientation/azimuth/value_f']
                    dip = Receiver_t['orientation/dip/value_f']
                    # dip is below horizontal axis
                    # but SAC convention requires from vertical axis.
                    dip = float(dip)
                    if Receiver_t['orientation/description_s'] == 'Z':
                        dip = 90 + dip
                    else:
                        dip = 90 - dip
                    obspy_trace.stats.sac = {'kstnm': stc.seed_station,
                                             'kcmpnm': stc.seed_channel,
                                             'knetwk': stc.net_code,
                                             'stla': float(stc.latitude),
                                             'stlo': float(stc.longitude),
                                             'stel': float(stc.elev),
                                             'cmpaz': float(azimuth),
                                             'cmpinc': float(dip)}
                elif self.format == "GEOCSV":
                    Receiver_t = \
                        self.ph5.get_receiver_t_by_n_i(stc.receiver_n_i)
                    azimuth = Receiver_t['orientation/azimuth/value_f']
                    dip = Receiver_t['orientation/dip/value_f']
                    obspy_trace.stats.sensor_type = stc.sensor_type
                    obspy_trace.stats.elevation = float(stc.elev)
                    obspy_trace.stats.dip = float(dip)
                    obspy_trace.stats.depth = 0
                    obspy_trace.stats.back_azimuth = azimuth
                    obspy_trace.stats.experiment_id = stc.experiment_id
                    obspy_trace.stats.component = stc.component
                    obspy_trace.stats.response = self.get_response_obj(stc)
                    obspy_trace.stats.array = stc.array_code
                elif self.format.upper() == "SEGY1" or \
                        self.format.upper() == "SEGY2":
                    # These values are used to create the SEG-Y headers
                    obspy_trace.stats.receiver_id = stc.station
                    obspy_trace.stats.ttype = trace.ttype
                    obspy_trace.stats.byteorder = trace.byteorder
                    obspy_trace.stats.elevation = float(stc.elev)
                    obspy_trace.stats.component = stc.component
                    obspy_trace.stats.response = self.get_response_obj(stc)
                    obspy_trace.stats.array = stc.array_code
                    obspy_trace.stats.das = stc.das
                    obspy_trace.stats.shot_id = stc.shot_id
                    obspy_trace.stats.shot_lat = stc.shot_lat
                    obspy_trace.stats.shot_lng = stc.shot_lng
                    obspy_trace.stats.shot_elevation = stc.shot_elevation
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
                   station_cut_times, station_list, deployment, st_num,
                   array_code, experiment_id):
        deploy = station_list[deployment][st_num]['deploy_time/epoch_l']
        deploy_micro = station_list[deployment][
            st_num]['deploy_time/micro_seconds_i']
        pickup = station_list[deployment][st_num]['pickup_time/epoch_l']
        pickup_micro = station_list[deployment][
            st_num]['pickup_time/micro_seconds_i']
        location = station_list[deployment][
            st_num]['seed_location_code_s']
        das = station_list[deployment][st_num]['das/serial_number_s']
        das_manufacturer = station_list[deployment][st_num][
                                        'das/manufacturer_s']
        das_model = station_list[deployment][st_num][
                                        'das/model_s']
        sensor_type = " ".join([x for x in
                                [station_list[deployment][st_num][
                                                    'sensor/manufacturer_s'],
                                 station_list[deployment][st_num][
                                                    'sensor/model_s']] if x])

        receiver_n_i = station_list[deployment][st_num]['receiver_table_n_i']
        response_n_i = station_list[deployment][st_num]['response_table_n_i']

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

        seed_channel, component = self.get_channel_and_component(
            station_list, deployment, st_num)

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
            # trim user defined time range if it extends beyond the
            # deploy/pickup times
            if self.start_time:
                if "T" not in self.start_time:
                    check_start_time = passcal2epoch(
                        self.start_time, fepoch=True)
                    if float(check_start_time) > float(deploy):
                        start_fepoch = self.start_time
                        sct = StationCutTime(
                                passcal2epoch(start_fepoch, fepoch=True)
                        )
                        station_cut_times.append(sct)
                    else:
                        sct = StationCutTime(deploy)
                        station_cut_times.append(sct)
                else:
                    check_start_time = ph5utils.datestring_to_epoch(
                        self.start_time)
                    if float(check_start_time) > float(deploy):
                        sct = StationCutTime(
                                ph5utils.datestring_to_epoch(self.start_time))
                        station_cut_times.append(sct)
                    else:
                        sct = StationCutTime(deploy)
                        station_cut_times.append(sct)
                if float(check_start_time) > float(pickup):
                    return
            else:
                sct = StationCutTime(
                    ph5api.fepoch(deploy, deploy_micro)
                )
                station_cut_times.append(sct)

        for sct in station_cut_times:
            start_fepoch = sct.time
            if self.reqtype == "SHOT" or self.reqtype == "RECEIVER":
                if self.offset:
                    # adjust starttime by an offset
                    start_fepoch += int(self.offset)

                if self.length:
                    stop_fepoch = start_fepoch + self.length
                else:
                    raise PH5toMSAPIError(
                        "Error - length is required for request by shot.")
            elif self.reqtype == "FDSN":
                if self.end_time:
                    if "T" not in self.end_time:
                        check_end_time = passcal2epoch(
                            self.end_time, fepoch=True)

                        if float(check_end_time) < float(pickup):

                            stop_fepoch = self.end_time
                            stop_fepoch = passcal2epoch(
                                stop_fepoch, fepoch=True)

                        else:
                            stop_fepoch = pickup

                    else:
                        check_end_time = ph5utils.datestring_to_epoch(
                            self.end_time)
                        if float(check_end_time) < float(pickup):
                            stop_fepoch = ph5utils.datestring_to_epoch(
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
                    ((int(start_fepoch) >= deploy and
                      int(stop_fepoch) <= pickup))):
                # das not deployed within deploy/pickup time
                continue
            start_passcal = epoch2passcal(start_fepoch, sep=':')
            start_passcal_list = start_passcal.split(":")
            start_doy = start_passcal_list[1]

            if self.doy_keep:
                if start_doy not in self.doy:
                    continue

            midnight_fepoch, secondLeftInday = \
                ph5utils.inday_breakup(start_fepoch)

            # if (stop_fepoch - start_fepoch) > 86400:
            if (stop_fepoch - start_fepoch) > secondLeftInday:
                seconds_covered = 0
                total_seconds = stop_fepoch - start_fepoch
                times_to_cut = []
                if self.cut_len != 86400:
                    stop_time, seconds = ph5utils.doy_breakup(
                        start_fepoch, self.cut_len)
                else:
                    stop_time, seconds = ph5utils.inday_breakup(start_fepoch)
                seconds_covered = seconds_covered + seconds
                times_to_cut.append([start_fepoch, stop_time])
                start_time = stop_time

                while seconds_covered < total_seconds:
                    if self.cut_len != 86400:
                        stop_time, seconds = ph5utils.doy_breakup(
                            start_time, self.cut_len)
                    else:
                        stop_time, seconds = ph5utils.inday_breakup(start_time)

                    seconds_covered += seconds
                    if stop_time > stop_fepoch:
                        times_to_cut.append([start_time, stop_fepoch])
                        break
                    times_to_cut.append([start_time, stop_time])
                    start_time = stop_time
            else:
                times_to_cut = [[start_fepoch, stop_fepoch]]
                times_to_cut[-1][-1] = stop_fepoch

            latitude = station_list[deployment][
                st_num]['location/Y/value_d']
            longitude = station_list[deployment][
                st_num]['location/X/value_d']
            elev = station_list[deployment][
                st_num]['location/Z/value_d']

            for starttime, endtime in tuple(times_to_cut):
                try:
                    self.ph5.query_das_t(das,
                                         component,
                                         starttime,
                                         endtime,
                                         sample_rate,
                                         sample_rate_multiplier
                                         )
                except experiment.HDF5InteractionError:
                    continue

                station_cut = StationCut(
                    seed_network,
                    experiment_id,
                    ph5_station,
                    seed_station,
                    array_code,
                    das,
                    das_manufacturer,
                    das_model,
                    sensor_type,
                    component,
                    seed_channel,
                    starttime,
                    endtime,
                    sample_rate,
                    sample_rate_multiplier,
                    self.notimecorrect,
                    location,
                    latitude,
                    longitude,
                    elev,
                    receiver_n_i,
                    response_n_i,
                    shot_id=sct.shot_id,
                    shot_lat=sct.shot_lat,
                    shot_lng=sct.shot_lng,
                    shot_elevation=sct.shot_elevation)

                station_cut_hash = hash(str(station_cut))
                if station_cut_hash in self.hash_list:
                    continue
                else:
                    self.hash_list.append(station_cut_hash)
                    yield station_cut

    def create_cut_list(self):
        cuts_generator = []
        experiment_t = self.ph5.Experiment_t['rows']

        try:
            seed_network = experiment_t[0]['net_code_s']
        except BaseException:
            raise PH5toMSAPIError("Error-No net_code_s entry in Experiment_t. "
                                  "Verify that this experiment is "
                                  "PH5 version >= PN4.")

        if self.netcode and self.netcode != seed_network:
            raise PH5toMSAPIError(
                "Error - The requested SEED network code does "
                "not match this PH5 experiment network code. "
                "{0} != {1}".format(self.netcode, seed_network))

        experiment_id = experiment_t[0]['experiment_id_s']

        array_names = sorted(self.ph5.Array_t_names)
        self.read_events(None)

        if self.reqtype == "SHOT" or self.reqtype == "RECEIVER":
            # create list of all matched shotlines and shot-ids for request by
            # shot or receiver
            shot_lines = sorted(self.ph5.Event_t_names)
            matched_shot_lines = []
            matched_shots = []
            for shot_line in shot_lines:
                if not self.shotline or ph5utils.does_pattern_exists(
                        self.shotline, shot_line[-3:]):
                    matched_shot_lines.append(shot_line)
                else:
                    continue
                event_t = self.ph5.Event_t[shot_line]['byid']
                for shot_id, _ in event_t.iteritems():
                    if not self.eventnumbers or ph5utils.does_pattern_exists(
                            self.eventnumbers, shot_id):
                        matched_shots.append(shot_id)
                    else:
                        continue
            if self.shotline and not matched_shot_lines:
                raise PH5toMSAPIError(
                    "Error - requested shotline(s) do not exist.")
            elif self.eventnumbers and not matched_shots:
                raise PH5toMSAPIError(
                    "Error - requested shotid(s) do not exist.")

        for array_name in array_names:
            array_code = array_name[8:]  # get 3 digit array code
            if self.array:
                array_patterns = self.array
                if not ph5utils.does_pattern_exists(
                        array_patterns, str(array_code)):
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
                    station_cut_times = []
                    station_len = len(station_list[deployment])

                    for st_num in range(0, station_len):

                        if station_list[deployment][
                                st_num]['seed_station_name_s']:
                            seed_station = station_list[deployment][
                                st_num]['seed_station_name_s']
                        else:
                            seed_station = station_list[
                                deployment][st_num]['id_s']

                        if self.station:
                            sta_patterns = self.station
                            if not ph5utils.does_pattern_exists(sta_patterns,
                                                                seed_station):
                                continue

                        if (self.reqtype == "SHOT" or
                                self.reqtype == "RECEIVER"):
                            # request by shot
                            for shotline in matched_shot_lines:
                                for shot in matched_shots:
                                    try:
                                        event_t = self.ph5.Event_t[
                                            shotline]['byid'][shot]
                                        # we add event info here for data
                                        # formats that use it, like SEG-Y
                                        sct = \
                                            StationCutTime(
                                                event_t['time/epoch_l'],
                                                shot_id=event_t['id_s'],
                                                shot_lat=event_t
                                                ['location/Y/value_d'],
                                                shot_lng=event_t
                                                ['location/X/value_d'],
                                                shot_elevation=event_t
                                                ['location/Z/value_d']
                                            )
                                        station_cut_times.append(sct)
                                    except Exception:
                                        raise PH5toMSAPIError(
                                            "Error reading events table.")
                                cuts_generator.append(self.create_cut(
                                    seed_network, ph5_station,
                                    seed_station, station_cut_times,
                                    station_list, deployment, st_num,
                                    array_code, experiment_id))
                        elif self.reqtype == "FDSN":
                            # fdsn request
                            cuts_generator.append(self.create_cut(
                                seed_network, ph5_station, seed_station,
                                station_cut_times, station_list, deployment,
                                st_num, array_code, experiment_id))

        return itertools.chain.from_iterable(cuts_generator)

    def process_all(self):
        cuts = self.create_cut_list()
        if cuts:
            for cut in cuts:
                self.ph5.clear()
                stream = self.create_trace(cut)
                if stream is not None:
                    yield stream
        else:
            raise PH5toMSAPIError("Request resulted in no data.")


def get_args():

    import argparse

    parser = argparse.ArgumentParser(
        description='Return mseed from a PH5 file.',
        usage='Version: {0} ph5toms --nickname="Master_PH5_file" [options]'
        .format(PROG_VERSION))

    parser.add_argument(
        "-n", "--nickname", action="store",
        type=str, metavar="nickname", default="master.ph5")

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
        action="store_false",
        default=True)

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
        "--non_standard", action="store_true", default=False,
        help="Change filename from standard output to "
        "[array].[seed_station].[seed_channel].[start_time]",
    )

    parser.add_argument(
        "--epoch", action="store_true", default=False,
        help="Log the epoch of the miniseed files to the terminal"
    )

    the_args = parser.parse_args()

    return the_args


def main():
    args = get_args()

    if args.nickname[-3:] == 'ph5':
        ph5file = os.path.join(args.ph5path, args.nickname)
    else:
        ph5file = os.path.join(args.ph5path, args.nickname + '.ph5')
        args.nickname += '.ph5'

    if not os.path.exists(ph5file):
        LOGGER.error("{0} not found.\n".format(ph5file))
        sys.exit(-1)

    ph5API_object = ph5api.PH5(path=args.ph5path, nickname=args.nickname)

    if args.array:
        args.array = args.array.split(',')
    if args.sta_id_list:
        args.sta_id_list = args.sta_id_list.split(',')
    if args.sta_list:
        args.sta_list = args.sta_list.split(',')
    if args.shotline:
        args.shotline = args.shotline.split(',')
    if args.eventnumbers:
        args.eventnumbers = args.eventnumbers.split(',')
    if args.sample_rate:
        args.sample_rate = args.sample_rate.split(',')
    if args.component:
        args.component = args.component.split(',')
    if args.channel:
        args.channel = args.channel.split(',')

    args.reqtype = args.reqtype.upper()
    args.format = args.format.upper()

    try:
        if args.reqtype != "SHOT" and args.reqtype != "FDSN" and \
                args.reqtype != "RECEIVER":
            raise PH5toMSAPIError("Error - Invalid request type {0}. "
                                  "Choose from FDSN, SHOT, or RECEIVER."
                                  .format(args.reqtype))

        if args.format != "MSEED" and args.format != "SAC":
            raise PH5toMSAPIError("Error - Invalid data format {0}. "
                                  "Choose from MSEED or SAC."
                                  .format(args.format))

        ph5ms = PH5toMSeed(ph5API_object, out_dir=args.out_dir,
                           reqtype=args.reqtype, netcode=args.network,
                           station=args.sta_list, station_id=args.sta_id_list,
                           channel=args.channel, component=args.component,
                           array=args.array, shotline=args.shotline,
                           eventnumbers=args.eventnumbers, length=args.length,
                           starttime=args.start_time, stoptime=args.stop_time,
                           offset=args.offset, das_sn=args.das_sn,
                           use_deploy_pickup=args.deploy_pickup,
                           decimation=args.decimation,
                           sample_rate_keep=args.sample_rate,
                           doy_keep=args.doy_keep, stream=args.stream,
                           reduction_velocity=args.red_vel,
                           notimecorrect=args.notimecorrect,
                           format=args.format,
                           log_epoch=args.epoch)

        if args.epoch:
            epoch_header = "{:>32} {:>32}".format('Start time', 'End time')
            print(epoch_header)

        for stream in ph5ms.process_all():
            if args.epoch:
                fmt = "{:>32} {:>32}"
                msg = fmt.format(stream.traces[0].stats['starttime'],
                                 stream.traces[0].stats['endtime'])
                print(msg)

            if args.format.upper() == "MSEED":
                if not args.non_standard:
                    stream.write(ph5ms.filenamemseed_gen(stream),
                                 format='MSEED', reclen=4096)
                else:
                    stream.write(ph5ms.filenamemseed_nongen(stream),
                                 format='MSEED', reclen=4096)
            elif args.format.upper() == "SAC":
                for trace in stream:
                    sac = SACTrace.from_obspy_trace(trace)
                    if not args.non_standard:
                        sac.write(ph5ms.filenamesac_gen(trace))
                    else:
                        sac.write(ph5ms.filenamesac_nongen(trace))

    except PH5toMSAPIError as err:
        LOGGER.error("{0}".format(err.message))
    except ph5api.APIError as err:
        LOGGER.error(err.msg)
    except experiment.HDF5InteractionError as err:
        LOGGER.error(err.msg)

    ph5API_object.close()


if __name__ == '__main__':
    main()
