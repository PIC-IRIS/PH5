#!/usr/bin/env pnpython4
#
# Basic API for reading a family of ph5 files
#
# Steve Azevedo, March 2015
#

import logging
import os
import time
import re
import math
from decimal import Decimal

import numpy as np
from pyproj import Geod
from tables.exceptions import NoSuchNodeError

from ph5.core import columns, experiment, timedoy


PROG_VERSION = '2022.144'

LOGGER = logging.getLogger(__name__)
PH5VERSION = columns.PH5VERSION

# No time corrections applied if slope exceeds this value, normally 0.001
# (.1%)
MAX_DRIFT_RATE = 0.001

__version__ = PROG_VERSION

# Conversion factors to meters
FACTS_M = {'km': 1000., 'm': 1., 'dm': 1. / 10., 'cm': 1. / 100.,
           'mm': 1. / 1000., 'kmi': 1852.0, 'in': 0.0254,
           'ft': 0.3048, 'yd': 0.9144, 'mi': 1609.344,
           'fath': 1.8288, 'ch': 20.1168, 'link': 0.201168,
           'us-in': 1. / 39.37, 'us-ft': 0.304800609601219,
           'us-yd': 0.914401828803658, 'us-ch': 20.11684023368047,
           'us-mi': 1609.347218694437, 'ind-yd': 0.91439523,
           'ind-ft': 0.30479841, 'ind-ch': 20.11669506}


class APIError(Exception):
    def __init__(self, errno, msg):
        self.args = (errno, msg)
        self.errno = errno
        self.msg = msg


class CutHeader(object):
    '''    PH5 cut header object
           array -> The receiver array number or None if receiver gather
           shot_line -> The shot line number or None if shot gather
           length -> Number of samples in each line
           order -> The order of the station or shot id's
           si_us -> Sample interval in micro-seconds
    '''
    __slots__ = 'array', 'shot_line', 'length', 'order', 'si_us'

    def __init__(self, array=None, shot_line=None,
                 length=0, order=[], si_us=0):
        self.array = array
        self.shot_line = shot_line
        self.length = length
        self.order = order
        self.si_us = si_us

    def __repr__(self):
        if self.array:
            gather_type = "Shot"
        elif self.shot_line:
            gather_type = "Receiver"
        else:
            gather_type = "Unknown"

        return "Gather type: {0}, Trace length: {1} Sample interval: {2} us,\
        Number of traces {3}".format(gather_type,
                                     self.length,
                                     self.si_us,
                                     len(self.order))


class Cut(object):
    '''    PH5 cut object
           das_sn -> The DAS to cut data from
           start_fepoch -> The starting time of the cut as a float
           stop_fepoch -> The ending time of the cut as a float
           sample_rate -> The sample rate in samples per second as a float
           channels -> A list of chanels to cut
           das_t_times -> A list of Das_t times found for
                           the start_fepoch, stop_fepoch,
                          ((start, stop), (start, stop), (start, stop), ...)
           msg -> List of error or warning messages
           id_s -> The shot id for receiver gathers or station id
           for shot gathers
    '''
    __slots__ = 'id_s', 'das_sn', 'das_t_times', 'start_fepoch',
    'stop_fepoch', 'sample_rate', 'channels', 'msg'

    def __init__(self, das_sn, start_fepoch, stop_fepoch, sample_rate,
                 channels={}, das_t_times=[], msg=None, id_s=None):
        self.das_sn = das_sn
        self.das_t_times = das_t_times
        self.start_fepoch = start_fepoch
        self.stop_fepoch = stop_fepoch
        self.sample_rate = sample_rate
        self.channels = channels
        self.msg = []
        if msg is not None:
            self.msg.append(msg)
        self.id_s = id_s

    def __repr__(self):
        ret = ''
        ret = "ID: {1} DAS: {0} SR: {2} samp/sec SI: {3:G} us\n" \
            .format(self.das_sn,
                    self.id_s,
                    self.sample_rate,
                    (1. / self.sample_rate) * 1000000)
        ret += "Start: {0} Stop: {1}\n" \
            .format(timedoy.epoch2passcal(self.start_fepoch),
                    timedoy.epoch2passcal(self.stop_fepoch))
        for m in self.msg:
            ret += m + '\n'
        ret += "DAS windows:\n"
        for w in self.das_t_times:
            ret += "\t{0} - {1}\n".format(timedoy.epoch2passcal(w[0]),
                                          timedoy.epoch2passcal(w[1]))

        return ret


class Clock(object):
    '''   Clock performance
          slope -> Drift rate in seconds/second
          offset_secs -> The offset of the clock at offload
          max_drift_rate_allowed -> The maximum allowed drift rate
          for time corrections
          comment -> Comment on clock performance
    '''
    __slots__ = ('slope', 'offset_secs', 'max_drift_rate_allowed', 'comment')

    def __init__(self, slope=0., offset_secs=0., max_drift_rate_allowed=1.):
        self.slope = slope
        self.offset_secs = offset_secs
        self.max_drift_rate_allowed = max_drift_rate_allowed
        self.comment = []

    def __repr__(self):
        return "Slope: {0}\nMaximum slope: {1}\nOffload offset:\
        {2}\nComment: {3}\n".format(self.slope,
                                    self.max_drift_rate_allowed,
                                    self.offset_secs,
                                    self.comment)


class Trace(object):
    '''   PH5 trace object:
          data -> Numpy array of trace data points
          start_time -> timedoy time object
          time_correction_ms -> The correction to account for ocillator drift
          clock -> Clock performance object
          nsamples -> Number of data samples, ie. length of data
          padding -> Number of samples padding as a result of gaps
          sample_rate -> Number of samples per second as a float
          ttype -> Data sample point type, at this point 'int' or 'float'
          byteorder -> Data byteorder
          das_t -> A list of Das_t dictionaries
          receiver_t -> Orientation
          response_t -> Gain and bit weight fo now.
          Methods:
          time_correct -> Apply any time correction and return a timedoy object
    '''
    __slots__ = ('data', 'start_time', 'time_correction_ms', 'clock',
                 'nsamples', 'padding', 'sample_rate', 'ttype', 'byteorder',
                 'das_t', 'receiver_t', 'response_t', 'time_correct')

    def __init__(self, data, fepoch, time_correction_ms, nsamples, sample_rate,
                 ttype, byteorder, das_t, receiver_t,
                 response_t, clock=Clock()):
        self.data = data
        self.start_time = timedoy.TimeDOY(epoch=fepoch)
        self.time_correction_ms = time_correction_ms
        self.clock = clock
        self.nsamples = nsamples
        self.sample_rate = sample_rate
        self.ttype = ttype
        self.byteorder = byteorder
        self.das_t = das_t
        self.receiver_t = receiver_t
        self.response_t = response_t

    def __repr__(self):
        end_time = self.get_endtime()
        return "start_time: {0}\nend_time: {7}\nnsamples: {1}/{6}\nsample_rate:\
        {2}\ntime_correction_ms: {3}\nttype: {4}\nchannel_number: {5}" \
            .format(self.start_time,
                    self.nsamples,
                    self.sample_rate,
                    self.time_correction_ms,
                    self.ttype,
                    self.das_t[0]['channel_number_i'],
                    len(self.data),
                    end_time)

    def get_endtime(self):
        if self.sample_rate > 0:
            delta = 1. / float(self.sample_rate)
            time_diff = float(self.nsamples - 1) * delta
            end_time = timedoy.TimeDOY(epoch=(self.start_time.epoch(
                fepoch=True) + time_diff))
        else:
            end_time = timedoy.TimeDOY(epoch=(self.start_time.epoch(
                fepoch=True)))
        return end_time.getFdsnTime()

    def time_correct(self):
        return timedoy.timecorrect(self.start_time, self.time_correction_ms)


class PH5(experiment.ExperimentGroup):
    das_gRE = re.compile("Das_g_(.*)")

    def __init__(self, path=None, nickname=None, editmode=False):
        '''   path -> Path to ph5 file
              nickname -> The master ph5 file name, ie. master.ph5
              editmode -> Always False
        '''
        if not os.path.exists(os.path.join(path, nickname)):
            raise APIError(0, "PH5 file does not exist: {0}".format(
                os.path.join(path, nickname)))
        experiment.ExperimentGroup.__init__(
            self, currentpath=path, nickname=nickname)
        if self.currentpath is not None and self.nickname is not None:
            self.ph5open(editmode)
            self.initgroup()

        self.clear()

    def clear(self):
        '''   Clears key variables   '''
        self.Array_t = {
        }  # Array_t[array_name] = { 'byid':byid, 'order':order, 'keys':keys }
        # Event_t[event_name] = { 'byid':byid, 'order':order, 'keys':keys }
        self.Event_t = {}
        self.Sort_t = {}  # Sort_t[array_name] = { 'rows':rows, 'keys':keys }
        self.Das_t = {}  # Das_t[das] = { 'rows':rows, 'keys':keys }
        # Das_t_full[das], internal complete copy of Das_t
        self.Das_t_full = {}
        # Offset_t[offset_name] = { 'byid':byid, 'order':order, 'keys':keys }
        self.Offset_t = {}
        self.Index_t = None
        self.Time_t = None
        self.Receiver_t = None
        self.Experiment_t = None
        self.Response_t = None
        self.Offset_t_names = []
        self.Array_t_names = []
        self.Event_t_names = []
        self.Das_g_names = []
        self.num_found_das = 0

    def close(self):
        self.clear()
        self.ph5close()

    def channels(self, array, station):
        '''
           Inputs:
              array -> The Array_t name example: Array_t_001
              station -> The station id_s
           Output:
              returns a list of channels for this station
        '''
        try:
            # self.read_array_t(array)
            chans = sorted(self.Array_t[array]['byid'][station].keys())
            return chans
        except Exception:
            return []

    def channels_Array_t(self, array):
        '''
           Inputs:
              array -> The Array_t name example: Array_t_001
           Output:
              returns a list of channels
        '''
        try:
            if array in self.Array_t:
                order = self.Array_t[array]['order']
            else:
                self.read_array_t(array)
                order = self.Array_t[array]['order']
        except Exception:
            return []

        ret = {}
        for o in order:
            chans = self.Array_t[array]['byid'][o].keys()
            for c in chans:
                ret[c] = True

        ret = sorted(ret.keys())

        return ret

    def get_offset(self, sta_line, sta_id, evt_line, evt_id):
        '''   Calculate offset distance in meters from a shot to a station
              Inputs:
                 sta_line -> the array or line
                 sta_id -> the station id
                 evt_line -> the shot line
                 evt_id -> the event or shot id
              Returns:
                 A dictionary with the following keys:
                 {   'event_id_s': The event or shot id,
                     'receiver_id_s': The station or receiver id,
                     'azimuth/value_f:The azimuth from the station to the shot,
                     'azimuth/units_s': The units of the azimuth,
                     'offset/value_d': The offset distance,
                     'offset/units_s': The units of the offset
                 }
        '''
        az = 0.0
        baz = 0.0
        dist = 0.0
        chans = self.channels(sta_line, sta_id)
        if chans:
            c = chans[0]
        else:
            LOGGER.warning("Couldn't get offset.")
            return {}
        try:
            if sta_line in self.Array_t and evt_line in self.Event_t:
                array_t = self.Array_t[sta_line]['byid'][sta_id][c]
                event_t = self.Event_t[evt_line]['byid'][evt_id]
                lon0 = array_t[0]['location/X/value_d']
                lat0 = array_t[0]['location/Y/value_d']
                lon1 = event_t['location/X/value_d']
                lat1 = event_t['location/Y/value_d']
                az, baz, dist = run_geod(lat0, lon0, lat1, lon1)
        except Exception as e:
            LOGGER.warning("Couldn't get offset. {0}".format(repr(e)))
            return {}

        return {'event_id_s': evt_id, 'receiver_id_s': sta_id,
                'azimuth/value_f': az, 'azimuth/units_s': 'degrees',
                'offset/value_d': dist, 'offset/units_s': 'm'}

    def calc_offsets(self, array, shot_id, shot_line="Event_t"):
        '''
           Calculate offset with sign from a shot point to each station in an
           array.
           Inputs:
              array -> the array or line as named in the ph5 file,'Array_t_001'
              shot_id -> the event or shot id, '101'.
              shot_line -> the shot line, 'Event_t' (old style), 'Event_t_001'
           Returns:
              A list of dictionaries in the same format as ph5 Offset_t.
        '''
        Offset_t = []
        if not self.Array_t_names:
            self.read_array_t_names()
        if array not in self.Array_t_names:
            return Offset_t
        if array not in self.Array_t:
            self.read_array_t(array)
        if not self.Event_t_names:
            self.read_event_t_names()
        if shot_line not in self.Event_t:
            self.read_event_t(shot_line)

        Array_t = self.Array_t[array]
        order = Array_t['order']

        Event_t = self.Event_t[shot_line]
        if shot_id in Event_t['byid']:
            Event_t['byid'][shot_id]
        else:
            return Offset_t

        for o in order:
            array_t = Array_t['byid'][o]
            chans = self.channels(array, o)
            c = chans[0]
            offset_t = self.get_offset(
                array, array_t[c][0]['id_s'], shot_line, shot_id)
            Offset_t.append(offset_t)

        rows = calc_offset_sign(Offset_t)

        byid, order = by_id(rows, key='receiver_id_s')

        return {'byid': byid, 'order': order, 'keys': rows[0].keys()}

    def read_offsets_shot_order(
            self, array_table_name, shot_id, shot_line="Event_t"):
        '''   Reads shot to station distances from Offset_t_aaa_sss
              Inputs:
                 array_table_name -> The array table name such as Array_t_001
                 shot_id -> The shot id, id_s from the event table
                 shot_line -> The event table name such as Event_t_002
              Returns:
                 A dictionary keyed on array table id_s that points to a
                 row from the offset table.
        '''
        if shot_line == "Event_t":
            # Legacy Offset table name
            offset_table_name = "Offset_t"
        else:
            offset_table_name = "Offset_t_{0}_{1}" \
                .format(array_table_name[-3:],
                        shot_line[-3:])

        Offset_t = {}
        if not self.Array_t_names:
            self.read_array_t_names()
        if array_table_name not in self.Array_t_names:
            return Offset_t
        if array_table_name not in self.Array_t:
            self.read_array_t(array_table_name)
        if not self.Event_t_names:
            self.read_event_t_names()
        if shot_line not in self.Event_t:
            self.read_event_t(shot_line)
        if not self.Offset_t_names:
            self.read_offset_t_names()
        if offset_table_name not in self.Offset_t_names:
            return Offset_t

        Array_t = self.Array_t[array_table_name]
        order = Array_t['order']
        for o in order:
            c = self.channels(array_table_name, o)[0]
            array_t = Array_t['byid'][o]
            offset_t = self.ph5_g_sorts. \
                read_offset_fast(shot_id,
                                 array_t[c][0]['id_s'],
                                 name=offset_table_name)

            Offset_t[array_t[c][0]['id_s']] = offset_t

        return Offset_t

    def read_offsets_receiver_order(
            self, array_table_name, station_id, shot_line="Event_t"):
        '''   Reads shot to station distances from Offset_t_aaa_sss
              Inputs:
                 array_table_name -> The array table name such as Array_t_001
                 station_id -> The station id, id_s from the array table
                 shot_line -> The event table name such as Event_t_002
              Returns:
                 A dictionary keyed on event table id_s that points to a row
                 from the offset table.
        '''
        if shot_line == "Event_t":
            offset_table_name = "Offset_t"
        else:
            offset_table_name = "Offset_t_{0}_{1}" \
                .format(array_table_name[-3:],
                        shot_line[-3:])

        Offset_t = {}
        if not self.Array_t_names:
            self.read_array_t_names()
        if array_table_name not in self.Array_t_names:
            return Offset_t

        if not self.Event_t_names:
            self.read_event_t_names()
        if shot_line not in self.Event_t:
            self.read_event_t(shot_line)
        if not self.Offset_t_names:
            self.read_offset_t_names()
        if offset_table_name not in self.Offset_t_names:
            return Offset_t

        Event_t = self.Event_t[shot_line]
        order = Event_t['order']
        for o in order:
            event_t = Event_t['byid'][o]
            offset_t = self.ph5_g_sorts. \
                read_offset_fast(event_t['id_s'],
                                 station_id,
                                 name=offset_table_name)
            Offset_t[event_t['id_s']] = offset_t

        return Offset_t

    def read_experiment_t(self):
        '''   Read Experiment_t
              Sets:
                 Experiment_t['rows'] (a list of dictionaries)
                 Experiment_t['keys'] (a list of dictionary keys)
        '''
        rows, keys = self.read_experiment()
        self.Experiment_t = {'rows': rows, 'keys': keys}

    def read_offset_t_names(self):
        '''   Read Offset_t names
              Sets:
                 Offset_t_names
        '''
        self.Offset_t_names = self.ph5_g_sorts.namesOffset_t()

    def read_offset_t(self, name, id_order='event_id_s'):
        '''
              Read Offset_t
              Inputs:
                 name -> Offset_t_aaa_sss name
                 id_order -> 'event_id_s', or 'receiver_id_s'
              Sets:
                 Offset_t[name]['byid']
                 Offset_t[name]['order']
                 Offset_t[name]['keys']
        '''
        if not self.Offset_t_names:
            self.read_offset_t_names()
        if name in self.Offset_t_names:
            rows, keys = self.ph5_g_sorts.read_offset(name)
            byid, order = by_id(rows, key=id_order)
            self.Offset_t[name] = {'byid': byid, 'order': order, 'keys': keys}

    def read_event_t_names(self):
        '''   Read Event_t names
              Sets:
                 Event_t_names
        '''
        self.Event_t_names = self.ph5_g_sorts.namesEvent_t()

    def read_event_t(self, name):
        '''   Read Event_t
              Inputs:
                 name -> the Event_t_xxx name
              Sets:
                 Event_t[name]['byid'] Keyed by shot id(a list of dictionaries)
                 Event_t[name]['order'] Keyed by order in the PH5 file
                 (a list of dictionaries)
                 Event_t[name]['keys'] (a list of dictionary keys)
        '''
        if not self.Event_t_names:
            self.read_event_t_names()
        if name in self.Event_t_names:
            rows, keys = self.ph5_g_sorts.read_events(name)
            byid, order = by_id(rows)
            self.Event_t[name] = {'byid': byid, 'order': order, 'keys': keys}

    def read_array_t_names(self):
        '''   Read Array_t names
              Sets:
                 Array_t_names
        '''
        self.Array_t_names = self.ph5_g_sorts.namesArray_t()

    def read_array_t(self, name):
        '''   Read Array_t n
              Inputs:
                 name -> the name of the array as a string 'Array_t_xxx'
              Sets:
                 Array_t[name]['byid'] Keyed by station id as a list of dict of
                 array_t lines by channel
                 Array_t[name]['order'] Keyed in order as in PH5 file
                 (a list of dictionaries)
                 Array_t[name]['keys'] (a list of dictionary keys)
        '''
        if not self.Array_t_names:
            self.read_array_t_names()
        if name in self.Array_t_names:
            rows, keys = self.ph5_g_sorts.read_arrays(name)
            byid, order = by_id(
                rows, secondary_key='channel_number_i', unique_key=False)
            self.Array_t[name] = {'byid': byid, 'order': order, 'keys': keys}

    def get_sort_t(self, start_epoch, array_name):
        '''
           Get list of sort_t lines based on a time and array
           Returns:
               A list of sort_t lines
        '''
        if not self.Sort_t:
            self.read_sort_t()

        ret = []
        if array_name not in self.Sort_t:
            return ret

        for sort_t in self.Sort_t[array_name]['rows']:
            start = sort_t['start_time/epoch_l'] + \
                    (sort_t['start_time/micro_seconds_i'] / 1000000.)
            if not start_epoch >= start:
                continue
            stop = sort_t['end_time/epoch_l'] + \
                (sort_t['end_time/micro_seconds_i'] / 1000000.)
            if not start_epoch <= stop:
                continue
            ret.append(sort_t)

        return ret

    def read_sort_t(self):
        '''   Read Sort_t
              Sets:
                 Sort_t[array_name]['rows'] (a list sort_t of dictionaries)
                 Sort_t[array_name]['keys']
        '''
        tmp = {}
        rows, keys = self.ph5_g_sorts.read_sorts()
        for r in rows:
            if r['array_t_name_s'] not in tmp:
                tmp[r['array_t_name_s']] = []

            tmp[r['array_t_name_s']].append(r)

        arrays = tmp.keys()
        for a in arrays:
            self.Sort_t[a] = {'rows': tmp[a], 'keys': keys}

    def read_index_t(self):
        '''   Read Index_t
              Sets:
                 Index_t['rows'] (a list of dictionaries)
                 Index_t['keys'] (a list of dictionary keys)
        '''
        rows, keys = self.ph5_g_receivers.read_index()
        self.Index_t = {'rows': rows, 'keys': keys}

    def read_time_t(self):
        '''   Read Time_t
              Sets:
                 Time_t['rows'] (a list of dictionaries)
                 Time_t['keys'] (a list of dictionary keys)
        '''
        rows, keys = self.ph5_g_receivers.read_time()
        self.Time_t = {'rows': rows, 'keys': keys}

    def get_time_t(self, das):
        '''   Return Time_t as a list of dictionaries
              Returns:
                 time_t (a list of dictionaries)
        '''
        if not self.Time_t:
            self.read_time_t()

        time_t = []
        for t in self.Time_t['rows']:
            if t['das/serial_number_s'] == das:
                time_t.append(t)

        return time_t

    def read_receiver_t(self):
        '''   Read Receiver_t
              Sets:
                 Receiver_t['rows] (a list of dictionaries)
                 Receiver_t['keys'] (a list of dictionary keys)
        '''
        rows, keys = self.ph5_g_receivers.read_receiver()
        self.Receiver_t = {'rows': rows, 'keys': keys}

    def get_receiver_t(self, das_t, by_n_i=True):
        '''
           Read Receiver_t to match n_i as set in das_t else use channel
           Returns:
              receiver_t
        '''

        if not self.Receiver_t:
            self.read_receiver_t()

        if by_n_i:
            try:

                n_i = das_t['receiver_table_n_i']

                receiver_t = self.Receiver_t['rows'][n_i]
            except KeyError:
                receiver_t = None
        else:
            try:
                chan = das_t['channel_number_i']
                for receiver_t in self.Receiver_t['rows']:
                    if receiver_t['orientation/channel_number_i'] == chan:
                        break
            except BaseException:
                receiver_t = None

        return receiver_t

    def get_receiver_t_by_n_i(self, n_i):
        '''
           Read Receiver_t to match n_i
           Returns:
              receiver_t
        '''

        if not self.Receiver_t:
            self.read_receiver_t()

        try:
            receiver_t = self.Receiver_t['rows'][n_i]
        except KeyError:
            receiver_t = None

        return receiver_t

    def read_response_t(self):
        '''   Read Response_t
              Sets:
                 Response_t['rows'] (a list of dictionaries)
                 Response_t['keys] (a list of dictionary keys)
        '''
        rows, keys = self.ph5_g_responses.read_responses()
        self.Response_t = {'rows': rows, 'keys': keys}

    def get_response_t(self, das_t):
        '''
           Read Response_t to match n_i as set in das_t
           Returns:
               response_t
        '''
        if not self.Response_t:
            self.read_response_t()

        try:
            try:
                n_i = das_t[0]['response_table_n_i']
            except BaseException:
                n_i = das_t['response_table_n_i']

            response_t = self.Response_t['rows'][n_i]
            if response_t['n_i'] != n_i:
                for response_t in self.Response_t['rows']:
                    if response_t['n_i'] == n_i:
                        break
        except (KeyError, IndexError):
            response_t = None

        return response_t

    def get_response_t_by_n_i(self, n_i):
        '''
           Read Response_t to match n_i
           Returns:
               response_t
        '''
        if not self.Response_t:
            self.read_response_t()

        try:
            for response_t in self.Response_t['rows']:
                if response_t['n_i'] == n_i:
                    return response_t
        except BaseException:
            return None

        return None

    def read_das_g_names(self):
        '''   Read Das_g names
              Sets:
                 Das_g_names (a list of dictionary keys)
        '''
        self.Das_g_names = self.ph5_g_receivers.alldas_g()

    def query_das_t(self,
                    das,
                    chan=None,
                    start_epoch=None,
                    stop_epoch=None,
                    sample_rate=None,
                    sample_rate_multiplier=1,
                    check_samplerate=True):
        ''' Uses queries to get data from specific das table'''
        das_g = "Das_g_{0}".format(das)
        try:
            node = self.ph5_g_receivers.getdas_g(das)
        except experiment.HDF5InteractionError as e:
            raise e
        if not node:
            return []
        self.ph5_g_receivers.setcurrent(node)
        try:
            tbl = self.ph5.get_node('/Experiment_g/Receivers_g/' + das_g,
                                    'Das_t')
        except NoSuchNodeError:
            return []
        try:
            sample_rate_multiplier_i = tbl.cols.sample_rate_multiplier_i  # noqa
            sample_rate_multiplier_i = sample_rate_multiplier_i
        except AttributeError:
            errmsg = ("%s has sample_rate_multiplier_i "
                      "missing. Please run fix_srm to fix "
                      "sample_rate_multiplier_i for PH5 data."
                      % tbl._v_parent._v_name.replace('Das_g', 'Das_t'))
            raise APIError(-1, errmsg)

        if len(list(tbl.where('sample_rate_multiplier_i==0'))) > 0:
            errmsg = ("%s has sample_rate_multiplier_i "
                      "with value 0. Please run fix_srm to fix "
                      "sample_rate_multiplier_i for PH5 data."
                      % tbl._v_parent._v_name.replace('Das_g', 'Das_t'))
            raise APIError(-1, errmsg)

        epoch_i = tbl.cols.time.epoch_l  # noqa
        micro_seconds_i = tbl.cols.time.micro_seconds_i  # noqa
        sample_count_i = tbl.cols.sample_count_i  # noqa
        sample_rate_i = tbl.cols.sample_rate_i  # noqa
        epoch_i = epoch_i
        micro_seconds_i = micro_seconds_i
        sample_count_i = sample_count_i
        sample_rate_i = sample_rate_i
        das = []
        if not start_epoch:
            start_epoch = 0
        if not stop_epoch:
            stop_epoch = 32509613590

        if sample_rate == 0 or sample_rate is None:
            numexprstr = (
                    '(channel_number_i == '
                    + str(chan) + ' )&(epoch_i+micro_seconds_i/1000000>='
                    + str(start_epoch) +
                    ')&(epoch_i+micro_seconds_i/1000000<='
                    + str(stop_epoch) + ')'
            )
        elif check_samplerate is False:
            numexprstr = (
                 '(channel_number_i == '
                 + str(chan) + ' )&(epoch_i+micro_seconds_i/1000000 >= '
                 + str(start_epoch) +
                 '-sample_count_i/sample_rate_i/sample_rate_multiplier_i)'
                 '&(epoch_i+micro_seconds_i/1000000 <= '
                 + str(stop_epoch) + ')'
                 )
        else:
            numexprstr = (
                '(channel_number_i == '
                + str(chan) + ' )&(epoch_i+micro_seconds_i/1000000>='
                + str(start_epoch) +
                '-sample_count_i/sample_rate_i/sample_rate_multiplier_i)'
                '&(epoch_i+micro_seconds_i/1000000<='
                + str(stop_epoch) + ')&(sample_rate_i==' +
                str(sample_rate) +
                ')&(sample_rate_multiplier_i==' +
                str(sample_rate_multiplier) + ')'
            )

        for row in tbl.where(numexprstr):
            row_dict = {'array_name_SOH_a': row['array_name_SOH_a'],
                        'array_name_data_a': row['array_name_data_a'],
                        'array_name_event_a': row['array_name_event_a'],
                        'array_name_log_a': row['array_name_log_a'],
                        'channel_number_i': row['channel_number_i'],
                        'event_number_i': row['event_number_i'],
                        'raw_file_name_s': row['raw_file_name_s'],
                        'receiver_table_n_i': row['receiver_table_n_i'],
                        'response_table_n_i': row['response_table_n_i'],
                        'sample_count_i': row['sample_count_i'],
                        'sample_rate_i': row['sample_rate_i'],
                        'sample_rate_multiplier_i':
                            row['sample_rate_multiplier_i'],
                        'stream_number_i': row['stream_number_i'],
                        'time/ascii_s': row['time/ascii_s'],
                        'time/epoch_l': row['time/epoch_l'],
                        'time/micro_seconds_i':
                            row['time/micro_seconds_i'],
                        'time/type_s': row['time/type_s'],
                        'time_table_n_i': row['time_table_n_i']
                        }
            das.append(row_dict)
        return das

    def read_das_t(self, das, start_epoch=None, stop_epoch=None, reread=True):
        '''   Read Das_t, return Das_t keyed on DAS serial number
              Inputs:
                 das -> DAS serial number as string or name of das group
                 start_epoch -> epoch time in seconds
                 stop_epoch -> epoch time in seconds
                 reread -> Re-read table even if Das_t[das] exists
              Sets:
                 Das_t[das]['rows'] (a list of dictionaries)
                 Das_t[das]['keys'] (a list of dictionary keys)

        '''
        dass = self.Das_t.keys()
        mo = self.das_gRE.match(das)
        if mo:
            das_g = das
            das = mo.groups()[0]
        else:
            das_g = "Das_g_{0}".format(das)

        if das in dass and not reread and not start_epoch:
            if das in self.Das_t_full:
                self.Das_t[das] = self.Das_t_full[das]
                return das
        if self.Das_g_names == []:
            self.read_das_g_names()
        node = None

        if das_g in self.Das_g_names:
            node = self.ph5_g_receivers.getdas_g(das)
            self.ph5_g_receivers.setcurrent(node)
        if node is None:
            return None
        rows_keep = []
        rows = []
        rk = {}
        rows, keys = self.ph5_g_receivers.read_das()
        self.Das_t_full[das] = {'rows': rows, 'keys': keys}
        if stop_epoch is not None and start_epoch is not None:
            for r in self.Das_t_full[das]['rows']:
                # Start and stop for this das event window
                start = float(r['time/epoch_l']) + \
                        float(r['time/micro_seconds_i']) / 1000000.

                if r['sample_rate_i'] > 0:
                    stop = start + (float(r['sample_count_i']) / (
                            float(r['sample_rate_i']) /
                            float(r['sample_rate_multiplier_i'])))
                else:
                    stop = start
                if r['sample_rate_i'] > 0:
                    sr = float(r['sample_rate_i']) / \
                        float(r['sample_rate_multiplier_i'])
                else:
                    sr = 0
                # We need to keep this
                if is_in(start, stop, start_epoch, stop_epoch):
                    if sr not in rk:
                        rk[sr] = []
                    rk[sr].append(r)
            rkk = rk.keys()
            # Sort so higher sample rates are first
            rkk.sort(reverse=True)
            for s in rkk:
                rows_keep.extend(rk[s])
        else:
            rows_keep = rows

        if len(rows_keep) > 0:
            self.Das_t[das] = {'rows': rows_keep,
                               'keys': self.Das_t_full[das]['keys']}
            self.num_found_das += 1
        else:
            das = None

        return das

    def forget_das_t(self, das):
        node = self.ph5_g_receivers.getdas_g(das)
        try:
            node.umount()
        except NoSuchNodeError:
            # when no minixxx.ph5 is used
            pass
        if das in self.Das_t:
            del self.Das_t[das]

    def read_t(self, table, n=None):
        '''   Read table and return kef
              Inputs:
                 table -> Experiment_t, Sort_t, Offset_t, Event_t,
                 Array_t requires n, Response_t, Receiver_t, Index_t,
                 Das_t requires n, Time_t
                 n -> the number of the table
                   -> or a tuple n containing n of Array_t and n of Event_t
                   -> or a DAS serial number
        '''
        if table == "Experiment_t":
            self.read_experiment_t()
            return build_kef("/Experiment_g/Experiment_t",
                             self.Experiment_t['rows'])
        elif table == "Sort_t":
            self.read_sort_t()
            keys = self.Sort_t.keys()
            rows = []
            for k in keys:
                rows += self.Sort_t[k]['rows']
            return build_kef("/Experiment_t/Sorts_g/Sort_t", rows)
        elif table == "Offset_t":
            rows = []
            kef = ''
            self.read_offset_t_names()
            if n and len(n) == 2:
                a = n[0]
                s = n[1]
                off = ["Offset_t_{0:03d}_{1:03d}".format(a, s)]
            else:
                off = sorted(self.Offset_t_names)

            for o in off:
                self.read_offset_t(o)
                bi = self.Offset_t[o]['byid']
                order = self.Offset_t[o]['order']
                for r in order:
                    rows.append(bi[r])
                kef += build_kef("Experiment_g/Sorts_g/{0}".format(o), rows)
            return kef
        # This will change once shot lines are implemented
        elif table == "Event_t":
            rows = []
            en = []
            self.read_event_t_names()
            kef = ''
            if n:
                en = ["Event_t_{0:03d}".format(int(n))]
            else:
                en = sorted(self.Event_t_names)

            for n in en:
                self.read_event_t(n)
                bi = self.Event_t[n]['byid']
                order = self.Event_t[n]['order']
                for o in order:
                    rows.append(bi[o])
                kef += build_kef("/Experiment_g/Sorts_g/{0}".format(n), rows)
            return kef
        elif table == "Array_t":
            n = int(n)
            self.read_array_t_names()
            self.read_array_t("Array_t_{0:03d}".format(n))
            rows = []
            bi = self.Array_t["Array_t_{0:03d}".format(n)]['byid']
            order = self.Array_t["Array_t_{0:03d}".format(n)]['order']
            for o in order:
                rows.append(bi[o])
            return build_kef(
                "/Experiment_g/Sorts_g/Array_t_{0:03d}".format(n), rows)
        elif table == "Response_t":
            self.read_response_t()
            return build_kef(
                "/Experiment_g/Responses_g/Response_t",
                self.Response_t['rows'])
        elif table == "Report_t":
            raise APIError(-1, "Return of Report_t not implemented.")
        elif table == "Receiver_t":
            self.read_receiver_t()
            return build_kef(
                "/Experiment_g/Receivers_g/Receiver_t",
                self.Receiver_t['rows'])
        elif table == "Index_t":
            self.read_index_t()
            return build_kef(
                "/Experiment_g/Receivers_g/Index_t", self.Index_t['rows'])
        elif table == "Das_t":
            self.read_das_g_names()
            self.read_das_t(n)
            return build_kef(
                "/Experiment_g/Receivers_g/Das_t_{0}/Das_t".format(n),
                self.Das_t[n]['rows'])
        elif table == "Time_t":
            self.read_time_t()
            return build_kef(
                "/Experiment_g/Receivers_g/Time_t", self.Time_t['rows'])
        else:
            return None

    def textural_cut(self, das,
                     start_fepoch, stop_fepoch,
                     chan,
                     das_t=None):
        """
        Cuts a text based trace such as LOG file
        :param das:
        :param start_fepoch:
        :param stop_fepoch:
        :param chan:
        :param das_t:
        :return:
        """
        if not das_t:
            self.read_das_t(das, start_epoch=start_fepoch,
                            stop_epoch=stop_fepoch, reread=False)
            if das not in self.Das_t:
                return []
            Das_t = filter_das_t(self.Das_t[das]['rows'], chan)
        else:
            Das_t = das_t

        traces = list()
        for entry in Das_t:
            if entry['sample_rate_i'] > 0:
                continue
            ref = self.ph5_g_receivers.find_trace_ref(
                entry['array_name_data_a'].strip())
            stime = (entry['time/epoch_l'] +
                     entry['time/micro_seconds_i']/1000000)

            data = self.ph5_g_receivers.read_trace(ref)
            trace = Trace(data,
                          stime,
                          0,  # time_correction
                          len(data),  # samples_read
                          0,
                          '|S1',
                          None,
                          Das_t,
                          None,  # receiver_t
                          None,  # response_t
                          clock=None)
            traces.append(trace)
        return traces

    def cut(self, das, start_fepoch, stop_fepoch, chan=1,
            sample_rate=None, apply_time_correction=True, das_t=None):
        '''   Cut trace data and return a Trace object
              Inputs:
                 das -> data logger serial number
                 start_fepoch -> time to cut start of trace as a
                 floating point epoch
                 stop_fepoch -> time to cut end of trace as a
                 floating point epoch
                 chan -> channel to cut
                 sample_rate -> sample rate in samples per second
                 apply_time_correction -> iff True, slide traces to
                 correct for clock drift
              Returns:
                 A list of PH5 trace objects split on gaps
        '''
        if not das_t:
            self.read_das_t(das, start_epoch=start_fepoch,
                            stop_epoch=stop_fepoch, reread=False)
            if das not in self.Das_t:
                return [Trace(np.array([]), start_fepoch, 0., 0,
                              sample_rate, None, None, [], None, None)]
            Das_t = filter_das_t(self.Das_t[das]['rows'], chan)
        else:
            Das_t = das_t
        if sample_rate == 0 or chan == -2:
            LOGGER.info("calling textural_cut")
            cuts = self.textural_cut(
                das,
                start_fepoch,
                stop_fepoch,
                chan,
                Das_t)
            return cuts

        # We shift the samples to match the requested start
        # time to apply the time correction

        clock = Clock()
        if apply_time_correction:
            Time_t = self.get_time_t(das)
            time_cor_guess_ms, clock = _cor(start_fepoch, stop_fepoch, Time_t)
            if das in self.Das_t:
                sr = sample_rate
                si = 1. / float(sr)
            else:
                sr = 0.
                si = 0.
            time_cor_guess_secs = abs(time_cor_guess_ms / 1000.)
            if time_cor_guess_secs > si:
                time_cor_guess_samples = int(
                    (sr * (time_cor_guess_ms / 1000.)) + 0.5)
            else:
                time_cor_guess_samples = 0
        else:
            clock.comment.append("No time correction applied.")
            time_cor_guess_samples = 0

        samples_read = 0
        first = True
        new_trace = False
        traces = []
        das_t = []

        window_start_fepoch0 = None
        window_stop_fepoch = None
        trace_start_fepoch = None
        data = None
        for d in Das_t:
            sr = float(d['sample_rate_i']) / \
                 float(d['sample_rate_multiplier_i'])
            window_start_fepoch = fepoch(
                d['time/epoch_l'], d['time/micro_seconds_i'])
            if (d['channel_number_i'] != chan) or (
                    sr != sample_rate) or (window_start_fepoch > stop_fepoch):
                continue
            if window_start_fepoch0 is None:
                window_start_fepoch0 = window_start_fepoch
            # Number of samples in window
            window_samples = d['sample_count_i']
            # Window stop epoch
            window_stop_fepoch = (window_start_fepoch +
                                  float(Decimal(window_samples) / Decimal(sr)))

            # Requested start before start of window, we must need to
            # start cutting at start of window
            if start_fepoch < window_start_fepoch:
                cut_start_fepoch = window_start_fepoch
                cut_start_sample = 0
            else:
                # Cut start is somewhere in window
                cut_start_fepoch = start_fepoch
                # round up to make sure it will start at or after
                # window_start_fepoch
                cut_start_sample = int(math.ceil(
                    (cut_start_fepoch - window_start_fepoch) * sr))
            # Requested stop is after end of window so we need rest of window
            if stop_fepoch > window_stop_fepoch:
                cut_stop_fepoch = window_stop_fepoch
                cut_stop_sample = window_samples
            else:
                # Requested stop is somewhere in window
                cut_stop_fepoch = round(stop_fepoch, 6)
                cut_stop_sample = round(
                    (cut_stop_fepoch - window_start_fepoch) * sr)
            # Get trace reference and cut data available in this window
            trace_reference = self.ph5_g_receivers.find_trace_ref(
                d['array_name_data_a'].strip())

            if trace_reference is None:
                continue

            if not trace_reference:
                continue

            data_tmp = self.ph5_g_receivers.read_trace(
                trace_reference,
                start=int(round(cut_start_sample - time_cor_guess_samples)),
                stop=int(round(cut_stop_sample - time_cor_guess_samples)))
            current_trace_type, current_trace_byteorder = (
                self.ph5_g_receivers.trace_info(trace_reference))
            if first:
                # Correct start time to 'actual' time of first sample
                if trace_start_fepoch is None:
                    trace_start_fepoch = \
                        window_start_fepoch + cut_start_sample / sr
                first = False
                dt = 'int32'
                if current_trace_type == 'float':
                    dt = 'float32'

                data = np.array([], dtype=dt)
            else:
                # Time difference between the end of last window and the start
                # of this one
                time_diff = abs(window_start_fepoch)
                # Overlaps are positive
                d['gap_overlap'] = time_diff - (1. / sr)
                # Data gap
                if abs(time_diff) > (1. / sr):
                    new_trace = True
            if len(data_tmp) > 0:
                #  Gap!!!
                if das_t and new_trace:
                    # Save trace before gap
                    trace = Trace(data,
                                  trace_start_fepoch,
                                  0,  # time_correction
                                  len(data),  # samples_read
                                  sr,
                                  current_trace_type,
                                  current_trace_byteorder,
                                  das_t,
                                  None,  # receiver_t
                                  None,  # response_t
                                  clock=clock)
                    traces.append(trace)
                    #
                    # Start of trace after gap
                    #
                    start_fepoch = trace_start_fepoch
                    trace_start_fepoch = window_start_fepoch
                    samples_read = len(data_tmp)

                    dt = 'int32'
                    if current_trace_type == 'float':
                        dt = 'float32'
                    data = np.array([], dtype=dt)

                    data = np.append(data, data_tmp)
                    das_t = [d]
                    new_trace = False
                else:
                    data = np.append(data, data_tmp)
                    samples_read += len(data_tmp)
                    das_t.append(d)
                # adjust the number of data samples as to not over extend the
                # cut_stop_fepoch
                if data is None:
                    return [Trace(np.array([]), start_fepoch, 0.,
                                  0, sample_rate, None, None, das_t, None,
                                  None, clock=clock)]
                calc_stop_fepoch = trace_start_fepoch + (len(data) / sr)

                # calculate number of overextending samples
                # num_overextend_samples is specific to the data per das table
                # needs to be embedded in for loop to work properly.
                num_overextend_samples = int(math.floor(calc_stop_fepoch -
                                                        cut_stop_fepoch) * sr)
                samples_to_cut = int(len(data) - num_overextend_samples)
                if num_overextend_samples > 0:
                    # trim the data array to exclude the over extending samples
                    data = data[0:samples_to_cut]
        # Done reading all the traces catch the last bit
        trace = Trace(data,
                      trace_start_fepoch,
                      0,  # time_correction_ms
                      len(data),  # nsamples
                      sample_rate,
                      current_trace_type,
                      current_trace_byteorder,
                      das_t,
                      None,  # receiver_t
                      None,  # response_t
                      clock=clock)
        traces.append(trace)
        if das_t:
            receiver_t = self.get_receiver_t(das_t[0])
            response_t = self.get_response_t(das_t[0])
        else:
            receiver_t = None
            response_t = None
        ret = []

        for t in traces:
            if apply_time_correction:
                window_start_fepoch0 = t.start_time
                window_stop_fepoch = window_start_fepoch0 + (t.nsamples / sr)
                time_correction, clock = \
                    _cor(window_start_fepoch0.epoch(fepoch=True),
                         window_stop_fepoch.epoch(fepoch=True),
                         Time_t)
                if time_correction != time_cor_guess_ms:
                    t.clock.comment.append(
                        "Time correction mismatch. {0}ms/{1}ms"
                        .format(time_correction, time_cor_guess_ms))
            else:
                time_correction = 0.
            # Set time correction
            t.time_correction_ms = time_correction
            # Set receiver_t and response_t
            t.receiver_t = receiver_t
            t.response_t = response_t
            ret.append(t)

        if 'PH5API_DEBUG' in os.environ and os.environ['PH5API_DEBUG']:
            for t in ret:
                print('-=' * 40)
                print(t)

        return ret

    def get_extent(self, das, component, sample_rate, start=None, end=None):
        '''
        Takes a das serial number, and option start and end time
        and returns the time of the earliest and latest samples
        fot a given channel
        Required: das serial and component
        Optional: Start time, End time
        :param das: das serial number
        :param component: component channel number
        :param start: start time epoch
        :param end:  end time epoch
        :param sample_rate: sample rate
        :return: earliest epoch and latest epoch
        '''
        das_t_t = None
        if component is None:
            raise ValueError("Component required for get_extent")
        if start or end:
            if not (start and end):
                raise ValueError("if start or end, both are required")
        # self.read_das_t(das, start, end, reread=True)

        if das not in self.Das_t:
            das_t_t = self.query_das_t(
                das,
                chan=component,
                start_epoch=start,
                stop_epoch=end,
                sample_rate=sample_rate)
            if not das_t_t:
                LOGGER.warning("No Das table found for " + das)
                return None, None

        if not das_t_t:
            Das_t = filter_das_t(self.Das_t[das]['rows'], component)
        else:
            Das_t = filter_das_t(das_t_t, component)
        new_das_t = sorted(Das_t, key=lambda k: k['time/epoch_l'])

        if not new_das_t:
            LOGGER.warning("No Das table found for " + das)
            return None, None
        earliest_epoch = (float(new_das_t[0]['time/epoch_l']) +
                          float(new_das_t[0]
                                ['time/micro_seconds_i']) / 1000000)

        latest_epoch_start = (float(new_das_t[-1]['time/epoch_l']) +
                              float(new_das_t[-1]
                                    ['time/micro_seconds_i']) / 1000000)
        if new_das_t[-1]['sample_rate_i'] > 0:
            true_sample_rate = (float(new_das_t[-1]['sample_rate_i']) /
                                float(new_das_t[-1]
                                      ['sample_rate_multiplier_i']))
            latest_epoch = (latest_epoch_start +
                            (float(new_das_t[-1]['sample_count_i'])
                             / true_sample_rate))
        else:
            latest_epoch = earliest_epoch

        self.forget_das_t(das)

        return earliest_epoch, latest_epoch

    def get_availability(self, das, sample_rate, component,
                         start=None, end=None):
        '''
        Required: das, sample_rate and component
        Optional: Start time, End time
        :param das: das serial number
        :param sample_rate: sample rate
        :param component: component channel number
        :param start: start time epoch
        :param end:  end time epoch
        :return: list of tuples (sample_rate, start, end)
        '''
        das_t_t = None
        gaps = 0
        if component is None:
            raise ValueError("Component required for get_availability")
        if sample_rate is None:
            raise ValueError("Sample rate required for get_availability")

        self.read_das_t(das, start, end, reread=True)

        if das not in self.Das_t:
            das_t_t = self.query_das_t(
                das,
                chan=component,
                start_epoch=start,
                stop_epoch=end,
                sample_rate=sample_rate)
            if not das_t_t:
                LOGGER.warning("No Das table found for " + das)
                return None
        if not das_t_t:
            Das_t = filter_das_t(self.Das_t[das]['rows'], component)
        else:
            Das_t = filter_das_t(das_t_t, component)
        if sample_rate > 0:
            Das_t = [das_t for das_t in Das_t if
                     das_t['sample_rate_i'] /
                     das_t['sample_rate_multiplier_i'] == sample_rate]
        else:
            Das_t = [das_t for das_t in Das_t if
                     das_t['sample_rate_i'] == sample_rate]

        new_das_t = sorted(Das_t, key=lambda k: k['time/epoch_l'])

        if not new_das_t:
            LOGGER.warning("No Das table found for " + das)
            return None

        gaps = 0
        prev_start = None
        prev_end = None
        prev_len = None
        prev_sr = None
        times = []
        for entry in new_das_t:
            # set the values for this entry
            cur_time = (float(entry['time/epoch_l']) +
                        float(entry['time/micro_seconds_i']) /
                        1000000)
            if entry['sample_rate_i'] > 0:
                cur_len = (float(entry['sample_count_i']) /
                           float(entry['sample_rate_i']) /
                           float(entry['sample_rate_multiplier_i']))
                cur_sr = (float(entry['sample_rate_i']) /
                          float(entry['sample_rate_multiplier_i']))
            else:
                cur_len = 0
                cur_sr = 0
            cur_end = cur_time + cur_len

            if (prev_start is None and prev_end is None and
                    prev_len is None and prev_sr is None):
                prev_start = cur_time
                prev_end = cur_end
                prev_len = cur_len
                prev_sr = cur_sr
            else:
                if (cur_time == prev_start and
                        cur_len == prev_len and
                        cur_sr == prev_sr):
                    # duplicate entry - skip
                    continue
                elif (cur_time > prev_end or
                        cur_sr != prev_sr):
                    # there is a gap so add a new entry
                    times.append((prev_sr,
                                  prev_start,
                                  prev_end))
                    # increment the number of gaps and reset previous
                    gaps = gaps + 1
                    prev_start = cur_time
                    prev_end = cur_end
                    prev_len = cur_len
                    prev_sr = cur_sr
                elif (cur_time == prev_end and
                        cur_sr == prev_sr):
                    # extend the end time since this was a continuous segment
                    prev_end = cur_end
                    prev_len = cur_len
                    prev_sr = cur_sr

        # add the last continuous segment
        times.append((prev_sr,
                      prev_start,
                      prev_end))

        self.forget_das_t(das)

        return times

#
# Mix-ins
#


def pad_traces(traces):
    '''
       Input:
          A list of ph5 Trace objects
       Return:
          A trace object with gaps padded with the mean
    '''

    def pad(data, n, dtype):
        m = np.mean(data, dtype=dtype)

        return np.append(data, [m] * n)

    ret = Trace(traces[0].data,  # Gets extended (np.append)
                0.,  # Gets set at begining
                0,  # ???
                0.,  # Gets set at end
                traces[0].sample_rate,  # Should not change
                traces[0].ttype,  # Should not change
                traces[0].byteorder,  # Should not change
                traces[0].das_t,  # Gets appended to
                traces[0].receiver_t,  # Should not change
                traces[0].response_t,  # Should not change
                clock=traces[0].clock)
    ret.start_time = traces[0].start_time

    end_time0 = None
    end_time1 = None
    x = 0
    tcor_sum = 0
    N = 0
    for t in traces:
        tcor_sum += t.time_correction_ms
        x += 1.
        end_time0 = t.start_time.epoch(
            fepoch=True) + (t.nsamples / t.sample_rate)
        if end_time1 is not None:
            if end_time0 != end_time1:
                n = int(((end_time1 - end_time0) * ret.sample_rate) + 0.5)
                # Pad
                d = pad(t.data, n, dtype=ret.ttype)
                ret.data = np.append(ret.data, d)
                N += n

        end_time1 = end_time0 + (1. / t.sample_rate)

    ret.padding = N
    ret.nsamples = len(ret.data)
    ret.time_correction_ms = int((tcor_sum / x) + 0.5)

    return ret


def seed_channel_code(array_t):
    try:
        if len(array_t['seed_band_code_s']) == 1 and len(
                array_t['seed_instrument_code_s']) == 1 and \
                len(array_t['seed_orientation_code_s']) == 1:
            return array_t['seed_band_code_s'] + \
                   array_t['seed_instrument_code_s'] + \
                   array_t['seed_orientation_code_s']
        else:
            return "---"
    except KeyError:
        return "---"


def by_id(rows, key='id_s', secondary_key=None, unique_key=True):
    '''   Order table info by id_s (usually) then if required a secondary key.
    '''
    order = []
    byid = {}
    for r in rows:
        if key in r:
            Id = r[key]
            if unique_key:
                byid[Id] = r
                order.append(Id)
            elif secondary_key and secondary_key in r:
                if Id not in byid:
                    byid[Id] = {}
                    order.append(Id)
                if r[secondary_key] not in byid[Id]:
                    byid[Id][r[secondary_key]] = [r]
                else:
                    byid[Id][r[secondary_key]].append(r)
            else:
                if Id not in byid:
                    byid[Id] = []
                    order.append(Id)
                byid[Id].append(r)

    return byid, order


def run_geod(lat0, lon0, lat1, lon1):
    UNITS = 'm'
    ELLIPSOID = 'WGS84'

    config = "+ellps={0}".format(ELLIPSOID)

    g = Geod(config)

    az, baz, dist = g.inv(lon0, lat0, lon1, lat1)

    if dist:
        dist /= FACTS_M[UNITS]

    # Return list containing azimuth, back azimuth, distance
    return az, baz, dist


def rect(r, w, deg=0):
    # Convert from polar to rectangular coordinates
    # radian if deg=0; degree if deg=1
    from math import cos, sin, pi
    if deg:
        w = pi * w / 180.0
    return r * cos(w), r * sin(w)


def linreg(X, Y):
    if len(X) != len(Y):
        raise ValueError(
            'Unequal length, X and Y. Can\'t do linear regression.')

    N = len(X)
    Sx = Sy = Sxx = Syy = Sxy = 0.0
    for x, y in map(None, X, Y):
        Sx = Sx + x
        Sy = Sy + y
        Sxx = Sxx + x * x
        Syy = Syy + y * y
        Sxy = Sxy + x * y

    det = Sxx * N - Sx * Sx
    if det == 0:
        return 0.0, 0.0, None

    a, b = (Sxy * N - Sy * Sx) / det, (Sxx * Sy - Sx * Sxy) / det

    meanerror = residual = 0.0
    for x, y in map(None, X, Y):
        meanerror = meanerror + (y - Sy / N) ** 2
        residual = residual + (y - a * x - b) ** 2

    RR = 1 - residual / meanerror
    if N > 2:
        ss = residual / (N - 2)
    else:
        ss = 1.

    return a, b, (RR, ss)


def calc_offset_sign(offsets):
    '''   offsets is a list of offset_t   '''
    if not offsets:
        return []
    from math import atan, degrees
    X = []
    Y = []
    OO = []
    offsetmin = 21 ** 63 - 1
    for offset_t in offsets:
        try:
            w = offset_t['azimuth/value_f']
            r = offset_t['offset/value_d']
            if abs(r) < abs(offsetmin):
                offsetmin = r

            x, y = rect(r, w, deg=True)
            X.append(x)
            Y.append(y)
        except Exception as e:
            LOGGER.error(e)

    # The seismic line is abx + c (ab => w)
    ab, c, err = linreg(X, Y)

    if abs(ab) > 1:
        regangle = degrees(atan(1. / ab))
    else:
        regangle = degrees(atan(ab))

    sig = 0
    flop = False
    for offset_t in offsets:
        try:
            # Rotate line to have zero slope
            a = offset_t['azimuth/value_f']

            w = a - regangle
            # Pick initial sign
            if sig == 0:
                if w < 0:
                    sig = -1
                else:
                    sig = 1

            offset_t['offset/value_d'] = sig * \
                float(offset_t['offset/value_d'])

            # Once we pass the minimum offset flip the sign
            if abs(offsetmin) == abs(offset_t['offset/value_d']) and not flop:
                flop = True
                sig *= -1

            OO.append(offset_t)
        except Exception as e:
            LOGGER.error(e)

    # Returning Oh not zero
    return OO


def is_in(start, stop, start_epoch, stop_epoch):
    '''
       start is start of window
       stop is stop of window
       start_epoch is start of desired data
       stop_epoch is stop of desired data
    '''
    # start_epoch is in between start and stop
    if start_epoch >= start and start_epoch <= stop:
        return True
    # stop_epoch is in between start and stop
    elif stop_epoch >= start and stop_epoch <= stop:
        return True
    # entire recording window is in between start_epoch and stop_epoch
    elif start_epoch <= start and stop_epoch >= stop:
        return True
    else:
        return False


def build_kef(ts, rs):
    '''
       ts -> table string
       rs -> rows object
    '''
    tdoy = timedoy.TimeDOY(epoch=time.time())
    ret = "#\n### Written by ph5api v{0} at {1}\n#\n".format(
        PROG_VERSION, tdoy.getFdsnTime())
    i = 0
    for r in rs:
        i += 1
        ret += "# {0}\n".format(i)
        ret += ts + '\n'
        keys = r.keys()
        for k in keys:
            line = "\t{0} = {1}\n".format(k, r[k])
            ret += line

    return ret


def fepoch(epoch, usecs):
    '''
    Given ascii epoch and microseconds return epoch as a float.
    '''
    epoch = Decimal(epoch)
    secs = Decimal(usecs) / 1000000

    return float(epoch + secs)


def _cor(start_fepoch, stop_fepoch, Time_t, max_drift_rate=MAX_DRIFT_RATE):
    '''   Calculate clock correction in miliseconds   '''
    clock = Clock()
    if not Time_t:
        Time_t = []

    time_t = None
    for t in Time_t:
        if hasattr(t, 'corrected_i'):
            if t['corrected_i'] != 1:
                data_start = fepoch(t['start_time/epoch_l'],
                                    t['start_time/micro_seconds_i'])
                data_stop = fepoch(t['end_time/epoch_l'],
                                   t['end_time/micro_seconds_i'])
                if is_in(data_start, data_stop, start_fepoch, stop_fepoch):
                    time_t = t
                    break
        else:
            data_start = fepoch(t['start_time/epoch_l'],
                                t['start_time/micro_seconds_i'])
            data_stop = fepoch(t['end_time/epoch_l'],
                               t['end_time/micro_seconds_i'])
            if is_in(data_start, data_stop, start_fepoch, stop_fepoch):
                time_t = t
                break

    if time_t is None:
        clock.comment.append("No clock drift information available.")
        return 0., clock

    clock = Clock(slope=time_t['slope_d'], offset_secs=time_t['offset_d'],
                  max_drift_rate_allowed=max_drift_rate)
    # Handle fixed offset correction
    if time_t['slope_d'] == 0. and time_t['offset_d'] != 0.:
        return 1000. * time_t['offset_d'], clock

    if abs(time_t['slope_d']) > MAX_DRIFT_RATE:
        clock.comment.append("Clock drift rate exceeds maximum drift rate.")

    mid_fepoch = start_fepoch + ((stop_fepoch - start_fepoch) / 2.)
    delta_fepoch = mid_fepoch - data_start

    time_correction_ms = int(time_t['slope_d'] * (delta_fepoch * 1000.)) * -1
    return time_correction_ms, clock


def filter_das_t(Das_t, chan):
    def sort_on_epoch(a, b):
        a_epoch = a['time/epoch_l'] + \
                  (float(a['time/micro_seconds_i']) / 1000000.)
        b_epoch = b['time/epoch_l'] + \
                  (float(b['time/micro_seconds_i']) / 1000000.)

        if a_epoch > b_epoch:
            return 1
        elif a_epoch < b_epoch:
            return -1
        else:
            return 0

    ret = []
    Das_t = [das_t for das_t in Das_t if das_t['channel_number_i'] == chan]

    for das_t in Das_t:
        if not ret:
            ret.append(das_t)
            continue
        if (ret[-1]['sample_rate_i'] == das_t['sample_rate_i'] and
                ret[-1]['sample_rate_multiplier_i'] ==
                das_t['sample_rate_multiplier_i'] and
                ret[-1]['time/micro_seconds_i'] ==
                das_t['time/micro_seconds_i'] and
                ret[-1]['time/epoch_l'] == das_t['time/epoch_l']):
            continue
        else:
            ret.append(das_t)

    ret.sort(cmp=sort_on_epoch)

    return ret
