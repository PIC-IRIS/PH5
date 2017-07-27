#!/usr/bin/env pnpython4
#
#   Basic API for reading a family of ph5 files
#
#   Steve Azevedo, March 2015
#

import sys, os, time, re, math
import numpy as np
from pyproj import Geod
from ph5.core import columns, experiment, timedoy

PROG_VERSION = '2017.208 Developmental'
PH5VERSION = columns.PH5VERSION

#   No time corrections applied if slope exceeds this value, normally 0.001 (.1%)
MAX_DRIFT_RATE = 0.001

__version__ = PROG_VERSION

#   Conversion factors to meters
FACTS_M = { 'km':1000., 'm':1., 'dm':1./10., 'cm':1./100., 'mm':1./1000., 'kmi':1852.0, 'in':0.0254, 'ft':0.3048, 'yd':0.9144,
            'mi':1609.344, 'fath':1.8288, 'ch':20.1168, 'link':0.201168, 'us-in':1./39.37, 'us-ft':0.304800609601219, 'us-yd':0.914401828803658,
            'us-ch':20.11684023368047, 'us-mi':1609.347218694437, 'ind-yd':0.91439523, 'ind-ft':0.30479841, 'ind-ch':20.11669506 }

class APIError (Exception) :
    def __init__ (self, errno, msg) :
        self.args = (errno, msg)
        self.errno = errno
        self.msg = msg
        
class CutHeader (object) :
    '''    PH5 cut header object
           array -> The receiver array number or None if receiver gather
           shot_line -> The shot line number or None if shot gather
           length -> Number of samples in each line
           order -> The order of the station or shot id's
           si_us -> Sample interval in micro-seconds
    '''
    __slots__ = 'array', 'shot_line', 'length', 'order', 'si_us'
    def __init__ (self, array=None, shot_line=None, length=0, order=[], si_us=0) :
        self.array = array
        self.shot_line = shot_line
        self.length = length
        self.order = order
        self.si_us = si_us
        
    def __repr__ (self) :
        if self.array :
            gather_type = "Shot"
        elif self.shot_line :
            gather_type = "Receiver"
        else :
            gather_type = "Unknown"
            
        return "Gather type: {0}, Trace length: {1} Sample interval: {2} us, Number of traces {3}".format (gather_type,
                                                                                                           self.length,
                                                                                                           self.si_us,
                                                                                                           len (self.order))
        
class Cut (object) :
    '''    PH5 cut object
           das_sn -> The DAS to cut data from
           start_fepoch -> The starting time of the cut as a float
           stop_fepoch -> The ending time of the cut as a float
           sample_rate -> The sample rate in samples per second as a float
           channels -> A list of chanels to cut
           das_t_times -> A list of Das_t times found for the start_fepoch, stop_fepoch, 
                          ((start, stop), (start, stop), (start, stop), ...)
           msg -> List of error or warning messages
           id_s -> The shot id for receiver gathers or station id for shot gathers
    '''
    __slots__ = 'id_s', 'das_sn', 'das_t_times', 'start_fepoch', 'stop_fepoch', 'sample_rate', 'channels', 'msg'
    def __init__ (self, das_sn, start_fepoch, stop_fepoch, sample_rate, channels={}, das_t_times=[], msg=None, id_s=None) :
        self.das_sn = das_sn
        self.das_t_times = das_t_times
        self.start_fepoch = start_fepoch
        self.stop_fepoch = stop_fepoch
        self.sample_rate = sample_rate
        self.channels = channels
        self.msg = []
        if msg != None :
            self.msg.append (msg)
        self.id_s = id_s
        
    def __repr__ (self) :
        ret = ''
        ret = "ID: {1} DAS: {0} SR: {2} samp/sec SI: {3:G} us\n".format (self.das_sn, 
                                                                         self.id_s, 
                                                                         self.sample_rate,
                                                                         (1./self.sample_rate)*1000000)
        ret += "Start: {0} Stop: {1}\n".format (timedoy.epoch2passcal (self.start_fepoch),
                                                timedoy.epoch2passcal (self.stop_fepoch))
        for m in self.msg :
            ret += m + '\n'
        ret += "DAS windows:\n"
        for w in self.das_t_times :
            ret += "\t{0} - {1}\n".format (timedoy.epoch2passcal (w[0]),
                                           timedoy.epoch2passcal (w[1]))
            
        return ret

class Clock (object) :
    '''   Clock performance
          slope -> Drift rate in seconds/second
          offset_secs -> The offset of the clock at offload
          max_drift_rate_allowed -> The maximum allowed drift rate for time corrections
          comment -> Comment on clock performance
    '''
    __slots__ = ('slope', 'offset_secs', 'max_drift_rate_allowed', 'comment')
    def __init__ (self, slope=0., offset_secs=0., max_drift_rate_allowed=1.) :
        self.slope = slope
        self.offset_secs = offset_secs
        self.max_drift_rate_allowed = max_drift_rate_allowed
        self.comment = []
        
    def __repr__ (self) :
        return "Slope: {0}\nMaximum slope: {1}\nOffload offset: {2}\nComment: {3}\n".format (self.slope,
                                                                                             self.max_drift_rate_allowed,
                                                                                             self.offset_secs,
                                                                                             self.comment)
        
class Trace (object) :
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
          time_correct -> Apply any time corrections and return a timedoy object
    '''
    __slots__ = ('data', 'start_time', 'time_correction_ms', 'clock', 'nsamples', 'padding', 'sample_rate', 'ttype', 'byteorder', 'das_t', 'receiver_t', 'response_t', 'time_correct')
    def __init__ (self, data, fepoch, time_correction_ms, nsamples, sample_rate, ttype, byteorder, das_t, receiver_t, response_t, clock=Clock ()) :
        self.data = data
        self.start_time = timedoy.TimeDOY (epoch=fepoch)
        self.time_correction_ms = time_correction_ms
        self.clock = clock
        self.nsamples = nsamples
        self.sample_rate = sample_rate
        self.ttype = ttype
        self.byteorder = byteorder
        self.das_t = das_t
        self.receiver_t = receiver_t
        self.response_t = response_t
        
    def __repr__ (self) :
        end_time = timedoy.TimeDOY (epoch=(self.start_time.epoch (fepoch=True) + (float (self.nsamples) / self.sample_rate)))
        return "start_time: {0}\nend_time: {7}\nnsamples: {1}/{6}\nsample_rate: {2}\ntime_correction_ms: {3}\nttype: {4}\nchannel_number: {5}".format (self.start_time,
                                                                                                                                                       self.nsamples,
                                                                                                                                                       self.sample_rate,
                                                                                                                                                       self.time_correction_ms,
                                                                                                                                                       self.ttype,
                                                                                                                                                       self.das_t[0]['channel_number_i'],
                                                                                                                                                       len (self.data),
                                                                                                                                                       end_time)
        
    def time_correct (self) :
        return timedoy.timecorrect (self.start_time, self.time_correction_ms)
        
class PH5 (experiment.ExperimentGroup) :
    das_gRE = re.compile ("Das_g_(.*)")
    def __init__ (self, path=None, nickname=None, editmode=False) :
        '''   path -> Path to ph5 file
              nickname -> The master ph5 file name, ie. master.ph5
              editmode -> Always False
        '''
        if not os.path.exists (os.path.join (path, nickname)) :
            raise APIError (0, "PH5 file does not exist: {0}".format (os.path.join (path, nickname)))
        experiment.ExperimentGroup.__init__ (self, currentpath=path, nickname=nickname)
        if self.currentpath != None and self.nickname != None :
            self.ph5open (editmode)
            self.initgroup ()
            
        self.clear ()
        
    def clear (self) :
        '''   Clears key variables   '''
        self.Array_t = {}          #   Array_t[array_name] = { 'byid':byid, 'order':order, 'keys':keys }
        self.Event_t = {}          #   Event_t[event_name] = { 'byid':byid, 'order':order, 'keys':keys }
        self.Sort_t = {}           #   Sort_t[array_name] = { 'rows':rows, 'keys':keys }
        self.Das_t = {}            #   Das_t[das] = { 'rows':rows, 'keys':keys }
        self.Das_t_full = {}       #   Das_t_full[das], internal complete copy of Das_t
        self.Offset_t = {}         #   Offset_t[offset_name] = { 'byid':byid, 'order':order, 'keys':keys }
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
        
    def close (self) :
        self.clear ()
        self.ph5close ()
        
    def channels (self, array, station) :
        '''
           Inputs:
              array -> The Array_t name example: Array_t_001
              station -> The station id_s
           Output:
              returns a list of channels for this station
        '''
        try :
            chans = self.Array_t[array]['byid'][station].keys ()
            chans.sort ()
            return chans
        except Exception as e :
            return []
        
    def channels_Array_t (self, array) :
        '''
           Inputs:
              array -> The Array_t name example: Array_t_001
           Output:
              returns a list of channels
        '''
        try :
            if self.Array_t.has_key (array) :
                order = self.Array_t[array]['order']
            else :
                self.read_array_t (array)
                order = self.Array_t[array]['order']
        except Exception as e :
            return []
        
        ret = {}
        for o in order :
            chans = self.Array_t[array]['byid'][o].keys ()
            for c in chans :
                ret[c] = True
                
        ret = ret.keys ()
        ret.sort ()
        
        return ret
        
    def get_offset (self, sta_line, sta_id, evt_line, evt_id) :
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
                     'azimuth/value_f: The azimuth from the station to the shot,
                     'azimuth/units_s': The units of the azimuth,
                     'offset/value_d': The offset distance,
                     'offset/units_s': The units of the offset
                 }
        '''
        az = 0.0
        baz = 0.0
        dist = 0.0
        chans = self.channels (sta_line, sta_id)
        c = chans[0]
        try :
            if self.Array_t.has_key (sta_line) and self.Event_t.has_key (evt_line) :
                array_t = self.Array_t[sta_line]['byid'][sta_id][c]
                event_t = self.Event_t[evt_line]['byid'][evt_id]
                lon0 = array_t[0]['location/X/value_d']
                lat0 = array_t[0]['location/Y/value_d']
                lon1 = event_t['location/X/value_d']
                lat1 = event_t['location/Y/value_d']
                az, baz, dist = run_geod (lat0, lon0, lat1, lon1)
        except Exception as e :
            sys.stderr.write ("Warning: Couldn't get offset. {0}\n".format (repr (e)))
        
        return {'event_id_s': evt_id, 'receiver_id_s': sta_id, 'azimuth/value_f': az, 'azimuth/units_s': 'degrees', 'offset/value_d': dist, 'offset/units_s': 'm'}    
    
    def calc_offsets (self, array, shot_id, shot_line="Event_t") :
        '''
           Calculate offset with sign from a shot point to each station in an
           array.
           Inputs:
              array -> the array or line as named in the ph5 file, 'Array_t_001'.
              shot_id -> the event or shot id, '101'.
              shot_line -> the shot line, 'Event_t' (old style), 'Event_t_001' (new style).
           Returns:
              A list of dictionaries in the same format as ph5 Offset_t.
        '''
        #   
        Offset_t = []
        if not self.Array_t_names :
            self.read_array_t_names ()
        if array not in self.Array_t_names :
            return Offset_t
        if not self.Array_t.has_key (array) :
            self.read_array_t (array)
        if not self.Event_t_names :
            self.read_event_t_names ()
        if not self.Event_t.has_key (shot_line) :
            self.read_event_t (shot_line)
            
        Array_t = self.Array_t[array]
        order = Array_t['order']
        
        Event_t = self.Event_t[shot_line]
        if Event_t['byid'].has_key (shot_id) :
            event_t = Event_t['byid'][shot_id]
        else : return Offset_t
        
        for o in order :
            array_t = Array_t['byid'][o]
            #print array_t['id_s']
            chans = self.channels (array, o)
            c = chans[0]
            #for c in array_t.keys () :
            offset_t = self.get_offset (array, array_t[c][0]['id_s'], shot_line, shot_id)
            Offset_t.append (offset_t)
            
        rows = calc_offset_sign (Offset_t)
        
        byid, order = by_id (rows, key='receiver_id_s')
        
        return {'byid':byid, 'order':order, 'keys':rows[0].keys ()}
    
    def read_offsets_shot_order (self, array_table_name, shot_id, shot_line="Event_t") :
        '''   Reads shot to station distances from Offset_t_aaa_sss
              Inputs:
                 array_table_name -> The array table name such as Array_t_001
                 shot_id -> The shot id, id_s from the event table
                 shot_line -> The event table name such as Event_t_002
              Returns:
                 A dictionary keyed on array table id_s that points to a row from the offset table.
        '''
        if shot_line == "Event_t" :
            #   Legacy Offset table name
            offset_table_name = "Offset_t"
        else :
            offset_table_name = "Offset_t_{0}_{1}".format (array_table_name[-3:],
                                                           shot_line[-3:])
        
        Offset_t = {}
        if not self.Array_t_names :
            self.read_array_t_names ()
        if array_table_name not in self.Array_t_names :
            return Offset_t
        if not self.Array_t.has_key (array_table_name) :
            self.read_array_t (array_table_name)
        if not self.Event_t_names :
            self.read_event_t_names ()
        if not self.Event_t.has_key (shot_line) :
            self.read_event_t (shot_line)        
        if not self.Offset_t_names :
            self.read_offset_t_names ()
        if not offset_table_name in self.Offset_t_names :
            return Offset_t
        
        Array_t = self.Array_t[array_table_name]
        order = Array_t['order']
        for o in order :
            c = self.channels (array_table_name, o)[0]
            array_t = Array_t['byid'][o]
            offset_t = self.ph5_g_sorts.read_offset_fast (shot_id, 
                                                          array_t[c][0]['id_s'], 
                                                          name=offset_table_name)
            
            Offset_t[array_t[c][0]['id_s']] = offset_t
            
        return Offset_t
    
    def read_offsets_receiver_order (self, array_table_name, station_id, shot_line="Event_t") :
        '''   Reads shot to station distances from Offset_t_aaa_sss
              Inputs:
                 array_table_name -> The array table name such as Array_t_001
                 station_id -> The station id, id_s from the array table
                 shot_line -> The event table name such as Event_t_002
              Returns:
                 A dictionary keyed on event table id_s that points to a row from the offset table.
        '''        
        if shot_line == "Event_t" :
            offset_table_name = "Offset_t"
        else :
            offset_table_name = "Offset_t_{0}_{1}".format (array_table_name[-3:],
                                                           shot_line[-3:])
            
        Offset_t = {}
        if not self.Array_t_names :
            self.read_array_t_names ()
        if array_table_name not in self.Array_t_names :
            return Offset_t
        
        if not self.Event_t_names :
            self.read_event_t_names ()
        if not self.Event_t.has_key (shot_line) :
            self.read_event_t (shot_line)        
        if not self.Offset_t_names :
            self.read_offset_t_names ()
        if not offset_table_name in self.Offset_t_names :
            return Offset_t
        
        Event_t = self.Event_t[shot_line]
        order = Event_t['order']
        for o in order :
            event_t = Event_t['byid'][o]
            offset_t = self.ph5_g_sorts.read_offset_fast (event_t['id_s'], 
                                                          station_id, 
                                                          name=offset_table_name)
            Offset_t[event_t['id_s']] = offset_t
            
        return Offset_t
        
    def read_experiment_t (self) :
        '''   Read Experiment_t
              Sets:
                 Experiment_t['rows'] (a list of dictionaries)
                 Experiment_t['keys'] (a list of dictionary keys)
        '''
        rows, keys = self.read_experiment ()
        self.Experiment_t = {'rows':rows, 'keys':keys}
        
    def read_offset_t_names (self) :
        '''   Read Offset_t names
              Sets:
                 Offset_t_names
        '''
        self.Offset_t_names = self.ph5_g_sorts.namesOffset_t ()
        
    def read_offset_t (self, name, id_order='event_id_s') :
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
        if name in self.Offset_t_names :
            rows, keys = self.ph5_g_sorts.read_offset (name)
            byid, order = by_id (rows, key=id_order)
            self.Offset_t[name] = {'byid':byid, 'order':order, 'keys':keys}

    def read_event_t_names (self) :
        '''   Read Event_t names
              Sets:
                 Event_t_names
        '''
        self.Event_t_names = self.ph5_g_sorts.namesEvent_t ()
        
    def read_event_t (self, name) :
        '''   Read Event_t
              Inputs:
                 name -> the Event_t_xxx name
              Sets:
                 Event_t[name]['byid'] Keyed by shot id (a list of dictionaries)
                 Event_t[name]['order'] Keyed by order in the PH5 file (a list of dictionaries)
                 Event_t[name]['keys'] (a list of dictionary keys)
        '''
        if name in self.Event_t_names :
            rows, keys = self.ph5_g_sorts.read_events (name)
            byid, order = by_id (rows)
            self.Event_t[name] = {'byid':byid, 'order':order, 'keys':keys}

    def read_array_t_names (self) :
        '''   Read Array_t names
              Sets:
                 Array_t_names
        '''
        self.Array_t_names = self.ph5_g_sorts.namesArray_t ()
        
    def read_array_t (self, name) :
        '''   Read Array_t n
              Inputs:
                 name -> the name of the array as a string 'Array_t_xxx'
              Sets:
                 Array_t[name]['byid'] Keyed by station id as a list of dict of array_t lines by channel
                 Array_t[name]['order'] Keyed in order as in PH5 file (a list of dictionaries)
                 Array_t[name]['keys'] (a list of dictionary keys)
        '''
        if name in self.Array_t_names :
            rows, keys = self.ph5_g_sorts.read_arrays (name)
            byid, order = by_id (rows, secondary_key='channel_number_i', unique_key=False)
            self.Array_t[name] = {'byid':byid, 'order':order, 'keys':keys}
            
    def get_sort_t (self, start_epoch, array_name) :
        '''
           Get list of sort_t lines based on a time and array
           Returns:
               A list of sort_t lines
        '''
        if not self.Sort_t :
            self.read_sort_t ()
            
        ret = []
        if not self.Sort_t.has_key (array_name) :
            return ret
        
        for sort_t in self.Sort_t[array_name]['rows'] :
            start = sort_t['start_time/epoch_l'] + (sort_t['start_time/micro_seconds_i'] / 1000000.)
            if not start_epoch >= start :
                continue
            stop = sort_t['end_time/epoch_l'] + (sort_t['end_time/micro_seconds_i'] / 1000000.)
            if not start_epoch <= stop :
                continue
            
            ret.append (sort_t)
                
        return ret
    
    def read_sort_t (self) :
        '''   Read Sort_t
              Sets:
                 Sort_t[array_name]['rows'] (a list sort_t of dictionaries)
                 Sort_t[array_name]['keys']
        '''
        tmp = {}
        rows, keys = self.ph5_g_sorts.read_sorts ()
        for r in rows :
            if not tmp.has_key (r['array_t_name_s']) :
                tmp[r['array_t_name_s']] = []
             
            tmp[r['array_t_name_s']].append (r)
        
        arrays = tmp.keys ()
        for a in arrays :
            self.Sort_t[a] = { 'rows':tmp[a], 'keys':keys }
            
    def read_index_t (self) :
        '''   Read Index_t
              Sets:
                 Index_t['rows'] (a list of dictionaries)
                 Index_t['keys'] (a list of dictionary keys)
        '''
        rows, keys = self.ph5_g_receivers.read_index ()
        self.Index_t = { 'rows':rows, 'keys': keys }
        
    def read_time_t (self) :
        '''   Read Time_t
              Sets:
                 Time_t['rows'] (a list of dictionaries)
                 Time_t['keys'] (a list of dictionary keys)
        '''
        rows, keys = self.ph5_g_receivers.read_time ()
        self.Time_t = { 'rows':rows, 'keys':keys }
        
    def get_time_t (self, das) :
        '''   Return Time_t as a list of dictionaries   
              Returns:
                 time_t (a list of dictionaries)
        '''
        if not self.Time_t :
            self.read_time_t ()
        
        time_t = []   
        for t in self.Time_t['rows'] :
            if t['das/serial_number_s'] == das :
                time_t.append (t)
                
        return time_t
    
    def read_receiver_t (self) :
        '''   Read Receiver_t
              Sets:
                 Receiver_t['rows] (a list of dictionaries)
                 Receiver_t['keys'] (a list of dictionary keys)
        '''
        rows, keys = self.ph5_g_receivers.read_receiver ()
        self.Receiver_t = { 'rows':rows, 'keys':keys }
        
    def get_receiver_t (self, das_t, by_n_i=True) :
        '''
           Read Receiver_t to match n_i as set in das_t else use channel
           Returns:
              receiver_t
        '''
        
        if not self.Receiver_t :
            self.read_receiver_t ()
        
        if by_n_i :    
            try :
                
                n_i = das_t['receiver_table_n_i']
                
                receiver_t = self.Receiver_t['rows'][n_i]
            except KeyError :
                receiver_t = None
        else :
            try :
                chan = das_t['channel_number_i']
                for receiver_t in self.Receiver_t['rows'] :
                    if receiver_t['orientation/channel_number_i'] == chan :
                        break
            except :
                receiver_t = None
            
        return receiver_t
    
    def get_receiver_t_by_n_i (self, n_i) :
        '''
           Read Receiver_t to match n_i
           Returns:
              receiver_t
        '''
        
        if not self.Receiver_t :
            self.read_receiver_t ()
            
        try :
            receiver_t = self.Receiver_t['rows'][n_i]
        except KeyError :
            receiver_t = None
        
            
        return receiver_t    
        
    def read_response_t (self) :
        '''   Read Response_t
              Sets:
                 Response_t['rows'] (a list of dictionaries)
                 Response_t['keys] (a list of dictionary keys)
        '''
        rows, keys = self.ph5_g_responses.read_responses ()
        self.Response_t = { 'rows':rows, 'keys':keys }
        
    def get_response_t (self, das_t) :
        '''
           Read Response_t to match n_i as set in das_t
           Returns:
               response_t
        '''
        if not self.Response_t :
            self.read_response_t ()
            
        try :
            n_i = das_t['response_table_n_i']
            response_t = self.Response_t['rows'][n_i]
            if response_t['n_i'] != n_i :
                for response_t in self.Response_t['rows'] :
                    if response_t['n_i'] == n_i :
                        break
        except (KeyError, IndexError) :
            response_t = None
        
        return response_t
    
    def get_response_t_by_n_i (self, n_i) :
        '''
           Read Response_t to match n_i
           Returns:
               response_t
        '''
        if not self.Response_t :
            self.read_response_t ()
            
        try :
            response_t = self.Response_t['rows'][n_i]
            if response_t['n_i'] != n_i :
                for response_t in self.Response_t['rows'] :
                    if response_t['n_i'] == n_i :
                        break
        except KeyError :
            response_t = None
        
        return response_t    
        
    def read_das_g_names (self) :
        '''   Read Das_g names   
              Sets:
                 Das_g_names (a list of dictionary keys)
        '''
        self.Das_g_names = self.ph5_g_receivers.alldas_g ()
        
    def read_das_t (self, das, start_epoch=None, stop_epoch=None, reread=True) :
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
        dass = self.Das_t.keys ()
        mo = self.das_gRE.match (das)
        if mo :
            das_g = das
            das = mo.groups ()[0]
        else :
            das_g = "Das_g_{0}".format (das)
            
        if das in dass and not reread and not start_epoch :
            if self.Das_t_full.has_key (das) :
                self.Das_t[das] = self.Das_t_full[das]
                return das
        
        if self.Das_g_names == [] : self.read_das_g_names ()
        node = None; found = False
        
        if das_g in self.Das_g_names :
            node = self.ph5_g_receivers.getdas_g (das)
            self.ph5_g_receivers.setcurrent (node)
        
        if node == None : return None
        rows_keep = []
        rows = []
        rk = {}
        if not self.Das_t_full.has_key (das) :
            rows, keys = self.ph5_g_receivers.read_das ()
            self.Das_t_full[das] = { 'rows':rows, 'keys':keys }
            
        if  stop_epoch != None and start_epoch != None :
            for r in self.Das_t_full[das]['rows'] :
                #   Start and stop for this das event window
                start = float (r['time/epoch_l']) + float (r['time/micro_seconds_i']) / 1000000.
                stop = start + (float (r['sample_count_i']) / float (r['sample_rate_i']) / float (r['sample_rate_multiplier_i']))
                sr = float (r['sample_rate_i']) / float (r['sample_rate_multiplier_i'])
                #   We need to keep this
                if is_in (start, stop, start_epoch, stop_epoch) :
                    if not rk.has_key (sr) : rk[sr] = []
                    rk[sr].append (r)
                    found = True
            rkk = rk.keys ()
            #   Sort so higher sample rates are first
            rkk.sort (reverse=True)
            for s in rkk :
                rows_keep.extend (rk[s])
        else : rows_keep = rows 
        
        if len (rows_keep) > 0 :        
            self.Das_t[das] = { 'rows':rows_keep, 'keys':self.Das_t_full[das]['keys'] }
            self.num_found_das += 1
        else :
            das = None
            
        return das
    
    def forget_das_t (self, das) :
        if self.Das_t.has_key (das) :
            del self.Das_t[das]
            
    def read_t (self, table, n=None) :
        '''   Read table and return kef
              Inputs:
                 table -> Experiment_t, Sort_t, Offset_t, Event_t, Array_t requires n, Response_t, Receiver_t, Index_t, Das_t requires n, Time_t
                 n -> the number of the table
                   -> or a tuple n containing n of Array_t and n of Event_t
                   -> or a DAS serial number
        '''
        if table == "Experiment_t" :
            self.read_experiment_t ()
            return build_kef ("/Experiment_g/Experiment_t", self.Experiment_t['rows'])
        elif table == "Sort_t" :
            self.read_sort_t ()
            keys = self.Sort_t.keys ()
            rows = []
            for k in keys :
                rows += self.Sort_t[k]['rows']
            return build_kef ("/Experiment_t/Sorts_g/Sort_t", rows)
        elif table == "Offset_t" :
            rows = []
            kef = ''
            self.read_offset_t_names ()
            if n and len (n) == 2 :
                a = n[0]; s = n[1]
                off = ["Offset_t_{0:03d}_{1:03d}".format (a, s)]
            else :
                off = self.Offset_t_names
                off.sort ()
                
            for o in off :
                self.read_offset_t (o)
                bi = self.Offset_t[o]['byid']
                order = self.Offset_t[o]['order']
                for r in order :
                    rows.append (bi[r])
                kef += build_kef ("Experiment_g/Sorts_g/{0}".format (o), rows)
            return kef
            #raise APIError (-1, "Return of Offset_t not inplemented.")
        #   This will change once shot lines are implemented
        elif table == "Event_t" :
            rows = []
            en = []
            self.read_event_t_names ()
            kef = ''
            if n :
                en = ["Event_t_{0:03d}".format (int (n))]
            else :
                en = self.Event_t_names
                en.sort ()
                
            for n in en :
                self.read_event_t (n)
                bi = self.Event_t[n]['byid']
                order = self.Event_t[n]['order']
                for o in order :
                    rows.append (bi[o])
                kef += build_kef ("/Experiment_g/Sorts_g/{0}".format (n), rows)
            return kef
        elif table == "Array_t" :
            n = int (n)
            self.read_array_t_names ()
            self.read_array_t ("Array_t_{0:03d}".format (n))
            rows = []
            bi = self.Array_t["Array_t_{0:03d}".format (n)]['byid']
            order = self.Array_t["Array_t_{0:03d}".format (n)]['order']
            for o in order :
                rows.append (bi[o])
            return build_kef ("/Experiment_g/Sorts_g/Array_t_{0:03d}".format (n), rows)
        elif table == "Response_t" :
            self.read_response_t ()
            return build_kef ("/Experiment_g/Responses_g/Response_t", self.Response_t['rows'])
        elif table == "Report_t" :
            raise APIError (-1, "Return of Report_t not implemented.")
        elif table == "Receiver_t" :
            self.read_receiver_t ()
            return build_kef ("/Experiment_g/Receivers_g/Receiver_t", self.Receiver_t['rows'])
        elif table == "Index_t" :
            self.read_index_t ()
            return build_kef ("/Experiment_g/Receivers_g/Index_t", self.Index_t['rows'])
        elif table == "Das_t" :
            self.read_das_g_names ()
            self.read_das_t (n)
            return build_kef ("/Experiment_g/Receivers_g/Das_t_{0}/Das_t".format (n), self.Das_t[n]['rows'])
        elif table == "Time_t" :
            self.read_time_t ()
            return build_kef ("/Experiment_g/Receivers_g/Time_t", self.Time_t['rows'])
        else :
            return None
        
    def cut (self, das, start_fepoch, stop_fepoch, chan=1, sample_rate=None, apply_time_correction = True) :
        '''   Cut trace data and return a Trace object
              Inputs:
                 das -> data logger serial number
                 start_fepoch -> time to cut start of trace as a floating point epoch
                 stop_fepoch -> time to cut end of trace as a floating point epoch
                 chan -> channel to cut
                 sample_rate -> sample rate in samples per second
                 apply_time_correction -> iff True, slide traces to correct for clock drift
              Returns:
                 A list of PH5 trace objects split on gaps
        '''
        self.read_das_t (das, start_epoch=start_fepoch, stop_epoch=stop_fepoch, reread=False)
        if not self.Das_t.has_key (das) :   
            return [Trace (np.array ([]), start_fepoch, 0., 0, sample_rate, None, None, [], None, None)]
        Das_t = filter_das_t (self.Das_t[das]['rows'], chan)
        #
        #   We shift the samples to match the requested start time to apply the time correction
        #
        clock = Clock ()
        if apply_time_correction :
            Time_t = self.get_time_t (das)
            time_cor_guess_ms, clock = _cor (start_fepoch, stop_fepoch, Time_t)
            if self.Das_t.has_key (das) :
                sr = sample_rate
                si = 1. / float (sr)
            else : 
                sr = 0.
                si = 0.
            time_cor_guess_secs = abs (time_cor_guess_ms / 1000.)
            if time_cor_guess_secs > si :
                time_cor_guess_samples = int ((sr * (time_cor_guess_ms / 1000.)) + 0.5)
            else :
                time_cor_guess_samples = 0
        else :
            clock.comment.append ("No time correction applied.")
            time_cor_guess_samples = 0
            
        samples_read = 0
        first = True
        new_trace = False
        traces = []
        das_t = []
            
        window_start_fepoch0 = None
        window_stop_fepoch = None
        trace_start_fepoch = None
        data=None
        for d in Das_t :
            sr = float (d['sample_rate_i']) / float (d['sample_rate_multiplier_i'])
            if (d['channel_number_i'] != chan) or  (sr != sample_rate) or (d['time/epoch_l'] > stop_fepoch) :
                continue
            window_start_fepoch = fepoch (d['time/epoch_l'], d['time/micro_seconds_i'])
            #
            if window_start_fepoch0 == None : 
                window_start_fepoch0 = window_start_fepoch
            #   Number of samples in window
            window_samples = d['sample_count_i']
            #   Window stop epoch
            window_stop_fepoch = window_start_fepoch + (window_samples / sr)
            #   Number of samples left to cut
            cut_samples = int (((stop_fepoch - start_fepoch) * sr) - samples_read)
            #   How many samples into window to start cut
            cut_start_sample = int ((start_fepoch - window_start_fepoch) * sr)
            #   If this is negative we must be at the start of the next recording window
            if cut_start_sample < 0 : cut_start_sample = 0
            #   Last sample in this recording window that we need to cut
            cut_stop_sample = cut_start_sample + cut_samples
            #   Read the data trace from this window
            trace_reference = self.ph5_g_receivers.find_trace_ref (d['array_name_data_a'].strip ())
            data_tmp = self.ph5_g_receivers.read_trace (trace_reference, 
                                                        start = int (cut_start_sample - time_cor_guess_samples),
                                                        stop = int (cut_stop_sample - time_cor_guess_samples))
            current_trace_type, current_trace_byteorder = self.ph5_g_receivers.trace_info (trace_reference)
            #
            ###
            #
            if first :
                #   Correct start time to 'actual' time of first sample
                #start_fepoch = window_start_fepoch + (float (cut_start_sample - time_cor_guess_samples)/sr)
                #start_fepoch = window_start_fepoch + float (cut_start_sample / sr)
                if not d['raw_file_name_s'].endswith('rg16'):
	            start_fepoch = window_start_fepoch + float (cut_start_sample / sr)
                if trace_start_fepoch == None :
                    trace_start_fepoch = start_fepoch            
                #print timedoy.TimeDOY (epoch=start_fepoch)
                first = False
                dt = 'int32'
                if current_trace_type == 'float' :
                    dt = 'float32'
                    
                data = np.array ([], dtype=dt)
            else :
                #   Time difference between the end of last window and the start of this one
                time_diff = abs (new_window_start_fepoch - window_start_fepoch)
                #   Overlaps are positive
                d['gap_overlap'] = time_diff - (1. / sr)
                #   Data gap
                if abs (time_diff) > (1. / sr) :
                    new_trace = True
            #
            ###
            #
            if len (data_tmp) > 0 :
                #  Gap!!!
                if new_trace :
                    #   Save trace before gap
                    trace = Trace (data, 
                                   trace_start_fepoch, 
                                   0,                       #   time_correction
                                   len (data),              #   samples_read
                                   sr, 
                                   current_trace_type, 
                                   current_trace_byteorder, 
                                   das_t, 
                                   None,                    #   receiver_t
                                   None,                    #   response_t
                                   clock=clock)                    
                    traces.append (trace)
                    #
                    ###   Start of trace after gap
                    #
                    trace_start_fepoch = window_start_fepoch
                    start_fepoch = window_start_fepoch
                    samples_read = len (data_tmp)
                    
                    dt = 'int32'
                    if current_trace_type == 'float' :
                        dt = 'float32'
                    data = np.array ([], dtype=dt)
                    
                    data = np.append (data, data_tmp)
                    das_t = [d]
                    new_trace = False
                else :
                    data = np.append (data, data_tmp)
                    samples_read += len (data_tmp)
                    das_t.append (d)
 
            new_window_start_fepoch = window_stop_fepoch + (1./sr)

        #   Done reading all the traces catch the last bit
        if data is None:
            return [Trace (np.array ([]), start_fepoch, 0., 0, sample_rate, None, None, das_t, None, None, clock=clock)]
        
        trace = Trace (data, 
                       trace_start_fepoch, 
                       0,                       #   time_correction_ms
                       len (data),              #   nsamples
                       sample_rate, 
                       current_trace_type, 
                       current_trace_byteorder, 
                       das_t, 
                       None,                    #   receiver_t
                       None,                    #   response_t
                       clock=clock)                    
        
        traces.append (trace)
        if das_t :
            receiver_t = self.get_receiver_t (das_t[0])
            response_t = self.get_response_t (das_t[0])  
        else : 
            receiver_t = None
            response_t = None         
        ret = []
        #
        for t in traces :
            if apply_time_correction :
                window_start_fepoch0 = t.start_time
                window_stop_fepoch = window_start_fepoch0 + (t.nsamples / sr)
                #try :    
                time_correction, clock = _cor (window_start_fepoch0.epoch (fepoch=True), window_stop_fepoch.epoch (fepoch=True), Time_t)
                if time_correction != time_cor_guess_ms :
                    t.clock.comment.append ("Time correction mismatch. {0}ms/{1}ms".format (time_correction, time_cor_guess_ms))
                    
                #except APIError as e :
                    #sys.stderr.write ("Warning: {0}: {1}".format (e.errno, e.msg))
                    #time_correction = 0.
            else :
                time_correction = 0.
            #   Set time correction    
            t.time_correction_ms = time_correction
            #
            #   Set receiver_t and response_t
            t.receiver_t = receiver_t
            t.response_t = response_t
            ret.append (t)
        
        if os.environ.has_key ('PH5API_DEBUG') and os.environ['PH5API_DEBUG'] :
            for t in ret :
                print '-=' * 40
                print t
                
        return ret
    #
    ###
    #
    def _Cut (self, das, start_time, stop_time, chan, sr=None, msg=None) :
        '''   Find out if data exists for a given DAS, start, stop, channel, sample rate
              Inputs:
              das -> The data logger serial number as in the Das_t in the ph5 file
              start_time -> The cut start time as a float epoch seconds
              stop_time -> The stop time as a float epoch seconds
              chan -> The channel number as given in the Das_t
              sr -> The sample rate as a float. If not given will use the first sample rate
              found from the Das_t
              msg -> Error or warning message
              Returns:
              C -> A Cut object
        '''
        self.forget_das_t (das)
        self.read_das_t (das, start_time, stop_time)
        C = Cut (das, start_time, stop_time, sr, msg=msg, das_t_times=[])
        if msg != None :
            return C
        if not self.Das_t.has_key (das) or len (self.Das_t[das]['rows']) == 0 :
            C.msg.append ("No data found for time period.")
            return C
        for das_t in self.Das_t[das]['rows'] :
            #   Filter on channel
            if chan != das_t['channel_number_i'] :
                continue
            das_sr = float (das_t['sample_rate_i']) / float (das_t['sample_rate_multiplier_i'])
            #   Filter on sample rate
            if sr != None and sr != das_sr :
                continue
            window_start_fepoch = fepoch (das_t['time/epoch_l'], das_t['time/micro_seconds_i'])
            window_stop_fepoch = window_start_fepoch + (float (das_t['sample_count_i']) / das_sr)
            if is_in (window_start_fepoch, window_stop_fepoch, start_time, stop_time) :
                if C.sample_rate == None :
                    C.sample_rate = das_sr
                if C.das_t_times == [] :
                    C.das_t_times.append ((window_start_fepoch, window_stop_fepoch))
                else :
                    ###
                    i = len (C.das_t_times)
                    last_start, last_stop = C.das_t_times[i-1]
                    new_start = last_stop + 1. / das_sr
                    delta = abs (new_start - window_start_fepoch)
                    #   Allow 1/2 sample overlap or gap
                    if delta < ((1. / das_sr) * 1.5) :
                        C.das_t_times[i-1][1] = window_stop_fepoch
                    else :
                        C.msg.append ("Time gap or overlap of {1} seconds at {0}".format (timedoy.epoch2passcal (window_start_fepoch), delta))
                        C.das_t_times.append ((window_start_fepoch, window_stop_fepoch))
                C.channels[chan] = True 
                
        return C
    #
    ###
    #
    def shot_cut (self, array_t_name, start_time, length) :
        '''    Return a generator of Cut objects, ret, in shot order
               (Used to find what data exists without cutting it)
               
               array_t_name -> The Array_t name
               start_time -> The cut start time epoch as a float
               length -> The length of the cut in seconds as a float
        '''
        ret = []
        #   Make sure array exists
        if self.Array_t.has_key (array_t_name) :
            Array_t = self.Array_t[array_t_name]['byid']
            order = self.Array_t[array_t_name]['order']
        else :
            #yield 
            return ret
        #   Header
        H = CutHeader (array=array_t_name[8:], order=[])
        #   Loop through each station in Array
        stations_found = {}
        for o in order :
            #   Loop through each channel for this station
            chans = Array_t[o].keys ()
            for c in chans :
                #   Loop through each entry for this station / channel combination
                for array_t in Array_t[o][c] :
                    #   Use Array sample rate if it is available
                    if array_t.has_key ('sample_rate_i') :
                        sr = array_t['sample_rate_i']
                    else :
                        sr = None
                    das = array_t['das/serial_number_s']
                    chan = array_t['channel_number_i']
                    deploy_fepoch = fepoch (array_t['deploy_time/epoch_l'], array_t['deploy_time/micro_seconds_i'])
                    pickup_fepoch = fepoch (array_t['pickup_time/epoch_l'], array_t['pickup_time/micro_seconds_i'])
                    stop_time = start_time + length
                    #   Filter on deploy and pickup times
                    if not is_in (deploy_fepoch, pickup_fepoch, start_time, stop_time) :
                        msg = "Start: {0} and Stop: {1} outside of deploy and pickup time.".format (timedoy.epoch2passcal (start_time), timedoy.epoch2passcal (stop_time))
                    else : msg = None
                    #   Get Cut object for time span, channel, and sample rate if available
                    C = self._Cut (das, start_time, stop_time, chan, sr=sr, msg=msg)
                    C.id_s = array_t['id_s']
                    if C.das_t_times != [] :
                        if not stations_found.has_key (array_t['id_s']) :
                            H.order.append (o)
                            if H.length == 0 :
                                H.length = length * sr
                            if H.si_us == 0 :
                                H.si_us = int ((1.0 / float (sr)) * 1000000.)                            
                        stations_found[array_t['id_s']] = True
                    #yield C
                    ret.append (C)
                    
        if H.order != [] :
            #yield H
            ret.insert (0, H)
        #print H.order    
        return ret
            
    #
    ###
    #
    def receiver_cut (self, event_t_name, array_t, length) :
        '''    Return a generator of Cut objects in receiver order
               (Used to find what data exists without cutting it)
               
               event _t_name -> The name of Event_t
               array_t -> An Array_t dictionary for one station (not a list)
               length -> The length of the cut in seconds as a float
        '''
        ret = []
        #   Get sample rate if available
        sr = None
        if array_t.has_key ('sample_rate_i') :
            sr = float (array_t['sample_rate_i']) / float (array_t['sample_rate_multiplier_i'])
        chan = array_t['channel_number_i']
        Event_t = self.Event_t[event_t_name]['byid']
        order = self.Event_t[event_t_name]['order']
        if len (event_t_name) == 7 :
            shot_line = '0'
        else :
            shot_line = event_t_name[8:]
        H = CutHeader (shot_line=shot_line, order=[])
        #   Loop through each event ID
        events_found = {}
        for o in order :
            event_t = Event_t[o]
            start_time = fepoch (event_t['time/epoch_l'], event_t['time/micro_seconds_i'])
            stop_time = start_time + length
            das = array_t['das/serial_number_s']
            deploy_fepoch = fepoch (array_t['deploy_time/epoch_l'], array_t['deploy_time/micro_seconds_i'])
            pickup_fepoch = fepoch (array_t['pickup_time/epoch_l'], array_t['pickup_time/micro_seconds_i'])
            #   Filter on deploy and pickup time
            if not is_in (deploy_fepoch, pickup_fepoch, start_time, stop_time) :
                msg = "Start: {0} and Stop: {1} outside of deploy and pickup time.".format (timedoy.epoch2passcal (start_time), timedoy.epoch2passcal (stop_time))
            else : msg = None
            #   Get a Cut object for this time span, channel and sample rate if available
            C = self._Cut (das, start_time, stop_time, chan, sr=sr, msg=msg)
            C.id_s = event_t['id_s']
            if C.das_t_times != [] :
                if not events_found.has_key (event_t['id_s']) :
                    H.order.append (o)
                    if H.length == 0 :
                        H.length = length * sr
                    if H.si_us == 0 :
                        H.si_us = int ((1.0 / float (sr)) * 1000000.)
                        
                events_found[o] = True
            #
            #yield C
            ret.append (C)
            
        if H.order != [] :
            #print H.order
            #yield H
            ret.insert (0, H)
            
        return ret

#
###   Mix-ins
#
def pad_traces (traces) :
    '''
       Input:
          A list of ph5 Trace objects
       Return:
          A trace object with gaps padded with the mean
    '''
    def pad (data, n, dtype) :
        m = np.mean (data, dtype=dtype)
        
        return np.append (data, [m] * n)
        
    ret = Trace (traces[0].data,          #   Gets extended (np.append)
                 0.,                      #   Gets set at begining
                 0,                       #   ???
                 0.,                      #   Gets set at end
                 traces[0].sample_rate,   #   Should not change 
                 traces[0].ttype,         #   Should not change
                 traces[0].byteorder,     #   Should not change
                 traces[0].das_t,         #   Gets appended to
                 traces[0].receiver_t,    #   Should not change
                 traces[0].response_t,    #   Should not change
                 clock=traces[0].clock)    
    ret.start_time = traces[0].start_time
    
    end_time0 = None
    end_time1 = None
    x = 0
    tcor_sum = 0
    N = 0
    for t in traces :
        tcor_sum += t.time_correction_ms
        x += 1.
        end_time0 = t.start_time.epoch (fepoch=True) + (t.nsamples / t.sample_rate)
        if end_time1 != None :
            if end_time0 != end_time1 :
                n = int (((end_time1 - end_time0) * ret.sample_rate) + 0.5)
                #   Pad
                d = pad (t.data, n, dtype=ret.ttype)
                ret.data = np.append (ret.data, d)
                N += n
                
        end_time1 = end_time0 + (1. / t.sample_rate)
    
    ret.padding = N    
    ret.nsamples = len (ret.data)
    ret.time_correction_ms = int ((tcor_sum / x) + 0.5)
         
    return ret
        
def seed_channel_code (array_t) :
    try :
        if len (array_t['seed_band_code_s']) == 1 and len (array_t['seed_instrument_code_s']) == 1 and len (array_t['seed_orientation_code_s']) == 1 :
            return array_t['seed_band_code_s'] + array_t['seed_instrument_code_s'] + array_t['seed_orientation_code_s']
        else :
            return "---"
    except KeyError :
        return "---"

def by_id (rows, key='id_s', secondary_key=None, unique_key=True) :
    '''   Order table info by id_s (usually) then if required a secondary key.
    '''
    order = []
    byid = {}
    for r in rows :
        if r.has_key (key) :
            Id = r[key]
            if unique_key :
                byid[Id] = r
                order.append (Id)
            elif secondary_key and r.has_key (secondary_key):
                if not byid.has_key (Id) :
                    byid[Id] = {}
                    order.append (Id)
                if not byid[Id].has_key (r[secondary_key]) :
                    byid[Id][r[secondary_key]] = [r]
                else :
                    byid[Id][r[secondary_key]].append (r)
                    #raise APIError (-2, "{0} has too many {1}, {2}.".format (Id, secondary_key, r[secondary_key]))
            else :
                if not byid.has_key (Id) :
                    byid[Id] = []
                    order.append (Id)
                byid[Id].append (r)
            
    return byid, order
#
###
#
def run_geod (lat0, lon0, lat1, lon1) :
    UNITS = 'm' 
    ELLIPSOID = 'WGS84'

    flds = []
    
    config = "+ellps={0}".format (ELLIPSOID)
    
    g = Geod (config)
    
    az, baz, dist = g.inv (lon0, lat0, lon1, lat1)
    
    if dist :
        dist /= FACTS_M[UNITS]
        
    #   Return list containing azimuth, back azimuth, distance
    return az, baz, dist
#
###
#
def deg2dms (dgs) :
    f, d = math.modf (dgs)
    f = abs (f)
    m = 60.0 * f
    f, m = math.modf (m)
    #print math.frexp (f), math.frexp (m)
    s = 60.0 * f
    dms = "%dd%02d'%09.6f\"" % (d, m, s)
    #print dms
    return dms
#
###
#
#   Convert from polar to rectangular coordinates
def rect(r, w, deg=0): 
    # radian if deg=0; degree if deg=1 
    from math import cos, sin, pi 
    if deg: 
        w = pi * w / 180.0 
    return r * cos(w), r * sin(w) 

def linreg(X, Y): 
    if len(X) != len(Y): 
        raise ValueError, 'Unequal length, X and Y. Can\'t do linear regression.' 
    
    N = len(X) 
    Sx = Sy = Sxx = Syy = Sxy = 0.0 
    for x, y in map(None, X, Y): 
        Sx = Sx + x 
        Sy = Sy + y 
        Sxx = Sxx + x*x 
        Syy = Syy + y*y 
        Sxy = Sxy + x*y 
        
    det = Sxx * N - Sx * Sx
    if det == 0 :
        return 0.0, 0.0
    
    a, b = (Sxy * N - Sy * Sx)/det, (Sxx * Sy - Sx * Sxy)/det 
    
    meanerror = residual = 0.0 
    for x, y in map(None, X, Y): 
        meanerror = meanerror + (y - Sy/N)**2 
        residual = residual + (y - a * x - b)**2 
        
    RR = 1 - residual/meanerror
    if N > 2 :
        ss = residual / (N-2)
    else :
        ss = 1.
        
    #Var_a, Var_b = ss * N / det, ss * Sxx / det 
    return a, b, (RR, ss)


def calc_offset_sign (offsets) :
    '''   offsets is a list of offset_t   '''
    if not offsets : return []
    from math import atan, degrees
    X = []; Y = []; O = []
    offsetmin = 21 ** 63 - 1
    for offset_t in offsets :
        try :
            w = offset_t['azimuth/value_f']
            r = offset_t['offset/value_d']
            if abs (r) < abs (offsetmin) :
                offsetmin = r
                
            x, y = rect (r, w, deg=True)
            X.append (x); Y.append (y)
        except Exception, e :
            sys.stderr.write ("%s\n" % e)
            
    #   The seismic line is abx + c (ab => w)   
    ab, c, err = linreg (X, Y)
    
    #sys.stderr.write ("Linear regression: {0}x + {1}, R^2 = {2}, s^2 = {3}\n".format (ab, c, err[0], err[1]))
    
    if abs (ab) > 1 :
        regangle = degrees (atan (1./ab))
    else :
        regangle = degrees (atan (ab))
        
    sig = 0
    flop = False
    for offset_t in offsets :
        try :
            #   Rotate line to have zero slope
            a = offset_t['azimuth/value_f']
            
            w = a - regangle
            #   Pick initial sign
            if sig == 0 :
                if w < 0 :
                    sig = -1
                else :
                    sig = 1
                    
            offset_t['offset/value_d'] = sig * float (offset_t['offset/value_d'])
            
            #   Once we pass the minimum offset flip the sign
            if abs (offsetmin) == abs (offset_t['offset/value_d']) and not flop :
                flop = True
                sig *= -1

            O.append (offset_t)
        except Exception, e :
            sys.stderr.write ("%s\n" % e)
        
    sys.stdout.flush ()
    #   Returning Oh not zero
    return O
#
##
#
def is_in (start, stop, start_epoch, stop_epoch) :
    '''
       start is start of window
       stop is stop of window
       start_epoch is start of desired data
       stop_epoch is stop of desired data
    '''
    #   start_epoch is in between start and stop
    if start_epoch >= start and start_epoch <= stop :
        return True
    #   stop_epoch is in between start and stop
    elif stop_epoch >= start and stop_epoch <= stop :
        return True
    #   entire recording window is in between start_epoch and stop_epoch
    elif start_epoch <= start and stop_epoch >= stop :
        return True
    else :
        return False
#
###
#
def build_kef (ts, rs) :
    '''
       ts -> table string
       rs -> rows object
    '''
    tdoy = timedoy.TimeDOY (epoch=time.time ())
    ret = "#\n###   Written by ph5api v{0} at {1}\n#\n".format (PROG_VERSION, tdoy.getFdsnTime ())
    i = 0
    for r in rs :
        i += 1
        ret += "#   {0}\n".format (i)
        ret += ts + '\n'
        keys = r.keys ()
        for k in keys :
            line = "\t{0} = {1}\n".format (k, r[k])
            ret += line
            
    return ret
#
###
#
def fepoch (epoch, ms) :
    '''
    Given ascii epoch and miliseconds return epoch as a float.
    '''
    epoch = float (int (epoch))
    secs = float (int (ms)) / 1000000.0
    
    return epoch + secs

def _cor (start_fepoch, stop_fepoch, Time_t, max_drift_rate=MAX_DRIFT_RATE) :
    '''   Calculate clock correction in miliseconds   '''
    clock = Clock ()
    if not Time_t :
        Time_t = []
    
    time_t = None
    for t in Time_t :
        data_start = fepoch (t['start_time/epoch_l'], t['start_time/micro_seconds_i'])
        data_stop = fepoch (t['end_time/epoch_l'], t['end_time/micro_seconds_i'])
        if is_in (data_start, data_stop, start_fepoch, stop_fepoch) :
            time_t = t
            break
        
    if time_t == None :
        clock.comment.append ("No clock drift information available.")
        return 0., clock
    
    clock = Clock (slope=time_t['slope_d'], offset_secs=time_t['offset_d'], max_drift_rate_allowed=max_drift_rate)
    #   Handle fixed offset correction
    if time_t['slope_d'] == 0. and time_t['offset_d'] != 0. :
        return 1000. * time_t['offset_d'], clock
    
    if abs (time_t['slope_d']) > MAX_DRIFT_RATE :
        clock.comment.append ("Clock drift rate exceeds maximum drift rate.")
        #raise APIError (-2, "Drift rate exceeds {0} percent.".format (MAX_DRIFT_RATE * 100))
    
    mid_fepoch = start_fepoch + ((stop_fepoch - start_fepoch) / 2.)
    delta_fepoch = mid_fepoch - data_start
    
    time_correction_ms = int (time_t['slope_d'] * (delta_fepoch * 1000.)) * -1
    return time_correction_ms, clock
#
###
#
def filter_das_t (Das_t, chan) :
    #
    def sort_on_epoch (a, b) :
        a_epoch = a['time/epoch_l'] + (float (a['time/micro_seconds_i']) / 1000000.)
        b_epoch = b['time/epoch_l'] + (float (b['time/micro_seconds_i']) / 1000000.)
        
        if a_epoch > b_epoch :
            return 1
        elif a_epoch < b_epoch :
            return -1
        else :
            return 0
        
    ret = []    
    Das_t = [das_t for das_t in Das_t if das_t['channel_number_i'] == chan]
    
    for das_t in Das_t :
        if not ret :
            ret.append (das_t)
            continue
        if (ret[-1]['sample_rate_i'] == das_t['sample_rate_i'] and 
            ret[-1]['sample_rate_multiplier_i'] == das_t['sample_rate_multiplier_i'] and
            ret[-1]['time/micro_seconds_i'] == das_t['time/micro_seconds_i'] and
            ret[-1]['time/epoch_l'] == das_t['time/epoch_l']):
            continue
        else:
            ret.append (das_t)
    
    ret.sort (cmp=sort_on_epoch)    
    
    return ret
    
if __name__ == '__main__' :
    from obspy.core import Stream as OPStream, Trace as OPTrace, UTCDateTime
    #p = ph5 (path='/home/azevedo/Data/10-016', nickname='master.ph5')
    #O = p.calc_offsets ('Array_t_001', '101'); p.close ()
    #sys.exit ()
    ##   Initialize PH5
    #p = ph5 (path='/run/media/azevedo/2TB_EXT4/Wavefields/PROCESS/Sigma', nickname='master.ph5')
    #p = ph5 (path='/run/media/azevedo/2TB_EXT4/Sigma', nickname='master.ph5')
    p = ph5 (path='/home/azevedo/Data/MATADORII/Nodes/PH5_2/Sigma/', nickname='master.ph5')
    das = p.read_das_t ('947F')
    stop = 0; start = sys.maxint
    #print p.Das_t
    #sr = p.Das_t[das]['rows'][0]['sample_rate_i']
    sr = 100
    for das_t in p.Das_t[das]['rows'] :
        tmpsr = int (float (das_t['sample_rate_i'])/ float (das_t['sample_rate_multiplier_i']))
        if tmpsr != sr :
            continue
        e = float (das_t['time/epoch_l']) + (float (das_t['time/micro_seconds_i']) / 1000000.)
        if e > stop :
            stop = e
        if e < start :
            start = e
    t1 = start
    #traces = []
    t2 = t1 + 3600.
    tdoy = timedoy.TimeDOY (year=2017,
                            hour=0, 
                            minute=0,
                            second=0, 
                            microsecond=0,
                            doy=1)
    t1 = tdoy.epoch (fepoch=True)
    t2 = t1 + 86400.
    while t1 < stop :
        cut_obj = p.cut (das, t1, t2, sample_rate=sr)
        print t1, t2
        print cut_obj

        for co in cut_obj :
            t = OPTrace (co.data)
            t.stats.sampling_rate = co.sample_rate
            e1 = co.start_time.epoch (fepoch=True)
            t.stats.starttime = UTCDateTime (e1)
            t.stats.station = das
            t.stats.channel = co.das_t[0]['channel_number_i']
            stringtime = co.start_time.getFdsnTime ()
            filename = 'DATA/{0}_{1}_{2}.sac'.format (das, stringtime, co.das_t[0]['channel_number_i'])
            #traces.append (t)
            print co.start_time.epoch (fepoch=True), stringtime, t.stats.starttime, t.stats.endtime
            t.write (filename, 'SAC')
        print    
        t1 = t2 + (1./float (sr))
        t2 = t1 + 3600.        
            
    print
    #p.read_array_t_names ()
    #for name in p.Array_t_names :
        #p.read_array_t (name)
    #p.read_event_t_names ()
    #for name in p.Event_t_names :
        #p.read_event_t (name)
    ##
    ####    Receiver gather
    ##
    #for name in p.Array_t_names :
        #Array_t = p.Array_t[name]['byid']
        #order = p.Array_t[name]['order']
        #length = 905
        ##   Order of stations
        #for o in order :
            #chans = Array_t[o].keys ()
            ##   foreach channel
            #for c in chans :
                ##   foreach entry per station
                ##   o -> station, c -> channel
                #for array_t in Array_t[o][c] :
                    #print "Station:", array_t['id_s']
                    #for ename in p.Event_t_names :
                        #print "Shot line:", ename
                        #Css = p.receiver_cut (ename, array_t, length)
                        #for Cs in Css :
                            #print Cs
                            ##print "Shot:", Cs.id_s, Cs.start_fepoch, Cs.stop_fepoch
                            ##for win in Cs.das_t_times :
                                ##print win[0], win[1]
                            ##for msg in Cs.msg :
                                ##print msg
    
    #raw_input ("P")
    ##
    ####   Shot gather
    ##
    #for name in p.Event_t_names :
        #Event_t = p.Event_t[name]['byid']
        #order = p.Event_t[name]['order']
        #length = 905
        #for o in order :
            #event_t = Event_t[o]
            #start_time = fepoch (event_t['time/epoch_l'], event_t['time/micro_seconds_i'])
            #for aname in p.Array_t_names :
                #Css = p.shot_cut (aname, start_time, length)
                #for Cs in Css :
                    #print Cs
                    ##print "Station:", Cs.id_s, Cs.start_fepoch, Cs.stop_fepoch
                    ##for win in Cs.das_t_times :
                        ##print win[0], win[1]
                    ##for msg in Cs.msg :
                        ##print msg  
    #raw_input ("P")
    #p.close ()        
    ###   Create dictionary to hold trace objects
    ##d = {}
    ###   Cut Z
    ##d['Z'] = p.cut ('A123', timedoy.passcal2epoch ("2016:201:00:00:00.000", fepoch=True), timedoy.passcal2epoch ("2016:201:23:59:59.999", fepoch=True), chan=1, sample_rate=100)
    ##print
    ###   Cut N
    ##d['N'] = p.cut ('964C', 1290391403.0, 1290391404.0, chan=2, sample_rate=250)
    ###   Cut E
    ##d['E'] = p.cut ('964C', 1290391403.0, 1290391404.0, chan=3, sample_rate=250)
    ###   Display trace data
    ##for c in ('Z', 'N', 'E') :
        ##print d[c].start_time.getISOTime ()
        ##i = 0
        ##for point in d[c].data :
            ##print i, point
            ##i += 1
    ###   Close PH5
    ##p.close ()
    ##   Initialize new PH5
    ##p = ph5 (path='/run/media/azevedo/2TB_EXT4/Wavefields/PROCESS/Sigma', nickname='master.ph5')
    ##p.read_array_t_names ()
    ##p.read_array_t ('Array_t_007')
    ###print p.Array_t['Array_t_005']['byid']['5X5004'][1][0]['deploy_time/ascii_s'], '->', p.Array_t['Array_t_005']['byid']['5X5004'][1][0]['pickup_time/ascii_s']
    ##array_t_0 = p.Array_t['Array_t_005']['byid']['5002'][1][0]
    ##array_t_1 = p.Array_t['Array_t_005']['byid']['5002'][1][-1]
    ##das = array_t_0['das/serial_number_s']
    ##sr = array_t_0['sample_rate_i'] / float (array_t_0['sample_rate_multiplier_i'])
    ##samples_per_day = int (86400 * sr)
    ##start_tdoy = timedoy.TimeDOY (epoch=array_t_0['deploy_time/epoch_l'])
    ##start_tdoy = timedoy.TimeDOY (year=start_tdoy.dtobject.year,
                                  ##hour=0,
                                  ##minute=0,
                                  ##second=0,
                                  ##microsecond=0,
                                  ##doy=start_tdoy.doy ())
    ##start_fepoch = start_tdoy.epoch (fepoch=True)
    ##stop_fepoch = start_fepoch + 86400.
    ##end_tdoy = timedoy.TimeDOY (epoch=array_t_1['pickup_time/epoch_l'])
    ##end_tdoy = timedoy.TimeDOY (year=end_tdoy.dtobject.year,
                                ##hour=23,
                                ##minute=59,
                                ##second=59,
                                ##microsecond=999999,
                                ##doy=end_tdoy.doy ())
    ##end_fepoch = end_tdoy.epoch (fepoch=True)
    ##while stop_fepoch < end_fepoch :
        ##traces = p.cut (das, start_fepoch, stop_fepoch, sample_rate=sr)
        ##for t in traces :
            ##print timedoy.epoch2passcal (start_fepoch), timedoy.epoch2passcal (stop_fepoch)
            ##print  '===>',t.start_time.getPasscalTime (ms=True),t.start_time.epoch (fepoch=True),t.sample_rate,t.nsamples,t.start_time.epoch (fepoch=True) + ((t.nsamples-1)/t.sample_rate),timedoy.epoch2passcal (t.start_time.epoch (fepoch=True) + ((t.nsamples-1)/t.sample_rate))
            ##samps = 0
            ##for d in t.das_t :
                ##samps += d['sample_count_i']
                ##tttttt = timedoy.TimeDOY (epoch=d['time/epoch_l'] + (d['time/micro_seconds_i'] / 1000000.))
                ##print "\t", tttttt.getPasscalTime (ms=True), d['sample_rate_i'], d['sample_count_i']
            ##print "\t", samps
            ##if len (t.data) != samples_per_day :
                ##print "*\t===> {0} {1}".format (samples_per_day, len (t.data))
        ##start_fepoch += 86400.
        ##stop_fepoch += 86400.
    ###Offset_t = p.calc_offsets (p.Array_t_names[0], '1002', shot_line="Event_t_001")
    ###start = timedoy.TimeDOY (year=2016, 
                             ###month=07, 
                             ###day=28, 
                             ###hour=0, 
                             ###minute=0, 
                             ###second=0, 
                             ###microsecond=0)
    ###traces = p.cut ('9389', start.epoch (fepoch=True), start.epoch (fepoch=True) + 3600., chan=1, sample_rate=100.)
    ##p.close (); sys.exit (-1)
    ##p = ph5 (path='/run/media/azevedo/1TB_EXT4/Data/SEGMeNT_onshore/Sigma-bak', nickname='master.ph5')
    ##p.read_event_t_names ()
    ##print p.Event_t_names
    ##p.close ()
    ##sys.exit ()
    ###t0 = p.read_t ("Offset_t")
    ####print t0; sys.exit ()
    ####   Read Experiment_t, return kef
    ###t1 = p.read_t ("Experiment_t")
    ####print t1
    ####   Read Sort_t, return kef
    ###t2 = p.read_t ("Sort_t")
    ####   Read Event_t, return kef
    ###t3 = p.read_t ("Event_t")
    ####print t3
    ####   Read Array_t_001, return kef
    ###t4 = p.read_t ("Array_t", n=1)
    ####   Read Response_t, return kef
    ###t5 = p.read_t ("Response_t")
    ####   Read Receiver_t, return kef
    ###t6 = p.read_t ("Receiver_t")
    ####   Read Index_t, return kef
    ###t7 = p.read_t ("Index_t")
    ####   Read Das_t for sn 10550, return kef
    ###t8 = p.read_t ("Das_t", "10875")
    ###print t8
    ####   Read Time_t, return kef
    ###t9 = p.read_t ("Time_t")
    ###print t9
    ###   Read data in shot order, return Trace object
    ##p.read_array_t_names ()
    ###for n in p.Array_t_names :
    ##for n in ['Array_t_006'] :
        ##if not p.Array_t.has_key (n) :
            ##p.read_array_t (n)
            
        ##array_t = p.Array_t[n]['byid']
        ##for k in array_t.keys () :
            ##das = array_t[k]['das/serial_number_s']
            ###   Cut, DAS sn, start epoch, stop epoch
            ##d = p.cut (das, 1200913195.333, 1200913200.5, sample_rate=100)
            ##print d.nsamples
    ####   Read data in receiver order, return Trace object
    ###p.read_event_t_names ()
    ###for n in p.Event_t_names :
        ###if not p.Event_t.has_key (n) :
            ###p.read_event_t (n)
            
        ###event_t = p.Event_t[n]['byid']
        ###for k in event_t.keys () :
            ###t0 = fepoch (event_t[k]['time/epoch_l'], event_t[k]['time/micro_seconds_i'])
            ####   Cut, DAS sn, event time (as epoch), event time + length
            ###d = p.cut ('11809', t0, t0 + 10., sample_rate=100)
            ###i = 0
            ###print d.start_time.getFdsnTime ()
            ###for point in d.data :
                ###print i, point
                ###i += 1
            ###pass
    ##p.close ()
