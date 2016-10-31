#!/usr/bin/env pnpython4
#
#   Basic API for reading a family of ph5 files
#
#   Steve Azevedo, March 2015
#

import sys, os, time, re
import numpy as np
from pyproj import Geod
import columns, Experiment, TimeDOY

PROG_VERSION = '2016.305 Developmental'
PH5VERSION = columns.PH5VERSION

#   No time corrections applied if slope exceeds this value, normally 0.01 (1%)
MAX_DRIFT_RATE = 0.01

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
        
class Trace (object) :
    '''   PH5 trace object:
          data -> Numpy array of trace data points
          start_time -> TimeDOY time object
          time_correction_ms -> The correction to account for ocillator drift
          nsamples -> Number of data samples, ie. length of data
          sample_rate -> Number of samples per second as a float
          ttype -> Data sample point type, at this point 'int' or 'float'
          byteorder -> Data byteorder
          das_t -> A list of Das_t dictionaries
          receiver_t -> Orientation
          response_t -> Gain and bit weight fo now.
          Methods:
          time_correct -> Apply any time corrections and return a TimeDOY object
    '''
    __slots__ = ('data', 'start_time', 'time_correction_ms', 'nsamples', 'sample_rate', 'ttype', 'byteorder', 'das_t', 'receiver_t', 'response_t', 'time_correct')
    def __init__ (self, data, fepoch, time_correction_ms, nsamples, sample_rate, ttype, byteorder, das_t, receiver_t, response_t) :
        self.data = data
        self.start_time = TimeDOY.TimeDOY (epoch=fepoch)
        self.time_correction_ms = time_correction_ms
        self.nsamples = nsamples
        self.sample_rate = sample_rate
        self.ttype = ttype
        self.byteorder = byteorder
        self.das_t = das_t
        self.receiver_t = receiver_t
        self.response_t = response_t
        
    def __repr__ (self) :
        return "start_time: {0}\nnsamples: {1}\nsample_rate: {2}\ntime_correction_ms: {3}\nttype: {4}\nchannel_number: {5}".format (self.start_time,
                                                                                                                                    self.nsamples,
                                                                                                                                    self.sample_rate,
                                                                                                                                    self.time_correction_ms,
                                                                                                                                    self.ttype,
                                                                                                                                    self.das_t[0]['channel_number_i'])
        
    def time_correct (self) :
        return TimeDOY.timecorrect (self.start_time, self.time_correction_ms)
        
class ph5 (Experiment.ExperimentGroup) :
    das_gRE = re.compile ("Das_g_(.*)")
    def __init__ (self, path=None, nickname=None, editmode=False) :
        '''   path -> Path to ph5 file
              nickname -> The master ph5 file name, ie. master.ph5
              editmode -> Always False
        '''
        if not os.path.exists (os.path.join (path, nickname)) :
            raise APIError (0, "PH5 file does not exist: {0}".format (os.path.join (path, nickname)))
        Experiment.ExperimentGroup.__init__ (self, currentpath=path, nickname=nickname)
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
                 Array_t[name]['order']['channel'] Keyed in order as in PH5 file (a list of dictionaries)
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
            
        if das in dass and not reread : return das
        if self.Das_g_names == [] : self.read_das_g_names ()
        node = None; found = False
        
        if das_g in self.Das_g_names :
            node = self.ph5_g_receivers.getdas_g (das)
            self.ph5_g_receivers.setcurrent (node)
        
        if node == None : return None
        rows_keep = []
        rows, keys = self.ph5_g_receivers.read_das ()
        if  stop_epoch != None and start_epoch != None :
            for r in rows :
                #   Start and stop for this das event window
                start = float (r['time/epoch_l']) + float (r['time/micro_seconds_i']) / 1000000.
                stop = start + (float (r['sample_count_i']) / float (r['sample_rate_i']) / float (r['sample_rate_multiplier_i']))
                #   We need to keep this
                if is_in (start, stop, start_epoch, stop_epoch) :
                    rows_keep.append (r)
                    found = True
        else : rows_keep = rows 
        
        if len (rows_keep) > 0 :        
            self.Das_t[das] = { 'rows':rows_keep, 'keys':keys }
            self.num_found_das += 1
            
        return das
    
    def forget_das_t (das) :
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
        if apply_time_correction :
            Time_t = self.get_time_t (das)
            time_cor_guess_ms = _cor (start_fepoch, stop_fepoch, Time_t)
            if self.Das_t.has_key (das) :
                sr = sample_rate
            else : sr = 0.
            time_cor_guess_samples = sr * (time_cor_guess_ms / 1000.)
        else :
            time_cor_guess_samples = 0.
            
        samples_read = 0
        first = True
        new_trace = False
        traces = []
        das_t = []
            
        window_start_fepoch0 = None
        window_stop_fepoch = None
        data=None
        for d in Das_t :
            sr = float (d['sample_rate_i']) / float (d['sample_rate_multiplier_i'])
            if (d['channel_number_i'] != chan) or  (sr != sample_rate) or (d['time/epoch_l'] > stop_fepoch) :
                continue
            window_start_fepoch = fepoch (d['time/epoch_l'], d['time/micro_seconds_i'])
            if window_start_fepoch0 == None : window_start_fepoch0 = window_start_fepoch
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
            if first :
                first = False
                needed_samples = cut_samples
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
                                
            if len (data_tmp) > 0 :
                #  Gap!!!
                if new_trace :
                    trace = Trace (data, 
                                   start_fepoch, 
                                   0,                       #   time_correction
                                   len (data),              #   samples_read
                                   sr, 
                                   current_trace_type, 
                                   current_trace_byteorder, 
                                   das_t, 
                                   None,                    #   receiver_t
                                   None)                    #   response_t
                    start_fepoch = window_start_fepoch
                    traces.append (trace)
                    data = data_tmp
                    das_t = [d]
                    new_trace = False
                else :
                    data = np.append (data, data_tmp)
                    samples_read += len (data_tmp)
                    das_t.append (d)
 
            new_window_start_fepoch = window_stop_fepoch + (1./sr)

        #   Done reading all the traces catch the last bit
        if data is None:
            return [Trace (np.array ([]), start_fepoch, 0., 0, sample_rate, None, None, das_t, None, None)]
        trace = Trace (data, 
                       start_fepoch, 
                       0,                       #   time_correction_ms
                       len (data),              #   nsamples
                       sr, 
                       current_trace_type, 
                       current_trace_byteorder, 
                       das_t, 
                       None,                    #   receiver_t
                       None)                    #   response_t
        traces.append (trace)
        if das_t :
            receiver_t = self.get_receiver_t (das_t[0])
            response_t = self.get_response_t (das_t[0])  
        else : 
            receiver_t = None
            response_t = None         
        ret = []
        #start0 = None
        #start1 = None
        for t in traces :
            ##   Remove extra traces in case DAS was loaded multiple times.
            #if start1 == None : 
                #start0 = t.start_time.epoch (fepoch=True)
                #start1 = t.start_time.epoch (fepoch=True)
            #else :
                #start1 = t.start_time.epoch (fepoch=True)
                
            #if start1 < start0 : 
                #break
            
            if apply_time_correction :
                window_start_fepoch0 = t.start_time
                window_stop_fepoch = window_start_fepoch0 + (t.nsamples / sr)
                try :    
                    time_correction = _cor (window_start_fepoch0, window_stop_fepoch, Time_t)
                except APIError as e :
                    sys.stderr.write ("Warning: {0}: {1}".format (e.errno, e.msg))
                    time_correction = 0.
            else :
                time_correction = 0.
            #   Set time correction    
            t.time_correction_ms = time_correction
            #
            #   Set receiver_t and response_t
            t.receiver_t = receiver_t
            t.response_t = response_t
            ret.append (t)
            #trace = Trace (data, 
                           #start_fepoch, 
                           #time_correction, 
                           #samples_read, 
                           #window_sample_rate, 
                           #current_trace_type, 
                           #current_trace_byteorder, 
                           #das_t, 
                           #receiver_t,
                           #response_t)
            
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
                 traces[0].byteorder,      #   Should not change
                 traces[0].das_t,         #   Gets appended to
                 traces[0].receiver_t,    #   Should not change
                 traces[0].response_t)    #   Should not change
    ret.start_time = traces[0].start_time
    
    end_time0 = None
    end_time1 = None
    x = 0
    tcor_sum = 0
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
                
        end_time1 = end_time0 + (1. / t.sample_rate)
        
    ret.nsamples = len (ret.data)
    ret.time_correction_ms = int ((tcor_sum / x) + 0.5)
         
    return ret
        
def seed_channel_code (array_t) :
    return array_t['seed_band_code_s'] + array_t['seed_instrument_code_s'] + array_t['seed_orientation_code_s']

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
    tdoy = TimeDOY.TimeDOY (epoch=time.time ())
    ret = "#\n###   Written by ph5API v{0} at {1}\n#\n".format (PROG_VERSION, tdoy.getFdsnTime ())
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

def _cor (start_fepoch, stop_fepoch, Time_t) :
    '''   Calculate clock correction in miliseconds   '''
    if not Time_t :
        return 0
    
    time_t = None
    for t in Time_t :
        data_start = fepoch (t['start_time/epoch_l'], t['start_time/micro_seconds_i'])
        data_stop = fepoch (t['end_time/epoch_l'], t['end_time/micro_seconds_i'])
        if is_in (data_start, data_stop, start_fepoch, stop_fepoch) :
            time_t = t
            break
        
    if time_t == None :
        return 0
    #   Handle fixed offset correction
    if time_t['slope_d'] == 0. and time_t['offset_d'] != 0. :
        return 1000. * time_t['offset_d']
    
    if abs (time_t['slope_d']) > MAX_DRIFT_RATE :
        raise APIError (-2, "Drift rate exceeds {0} percent.".format (MAX_DRIFT_RATE * 100))
    
    mid_fepoch = start_fepoch + ((stop_fepoch - start_fepoch) / 2.)
    delta_fepoch = mid_fepoch - data_start
    
    time_correction_ms = int (time_t['slope_d'] * 1000. * delta_fepoch) * -1
    return time_correction_ms
#
###
#
def filter_das_t (Das_t, chan) :
    #
    ret = []
    Das_t = [das_t for das_t in Das_t if das_t['channel_number_i'] == chan]
    for das_t in Das_t :
        if not ret :
            ret.append (das_t)
            continue
        time0 = ret[-1]['time/epoch_l'] + (ret[-1]['time/micro_seconds_i'] / 1000000.)
        time1 = das_t['time/epoch_l'] + (das_t['time/micro_seconds_i'] / 1000000.)
        if time0 < time1 : ret.append (das_t)
        
    return ret
    
if __name__ == '__main__' :
    #p = ph5 (path='/home/azevedo/Data/10-016', nickname='master.ph5')
    #O = p.calc_offsets ('Array_t_001', '101'); p.close ()
    #sys.exit ()
    ##   Initialize PH5
    #p = ph5 (path='/home/azevedo/Desktop/11-001/11-001', nickname='master.ph5')
    ##   Create dictionary to hold trace objects
    #d = {}
    ##   Cut Z
    #d['Z'] = p.cut ('964C', 1290391403.0, 1290391404.0, chan=1, sample_rate=250)
    ##   Cut N
    #d['N'] = p.cut ('964C', 1290391403.0, 1290391404.0, chan=2, sample_rate=250)
    ##   Cut E
    #d['E'] = p.cut ('964C', 1290391403.0, 1290391404.0, chan=3, sample_rate=250)
    ##   Display trace data
    #for c in ('Z', 'N', 'E') :
        #print d[c].start_time.getISOTime ()
        #i = 0
        #for point in d[c].data :
            #print i, point
            #i += 1
    ##   Close PH5
    #p.close ()
    #   Initialize new PH5
    p = ph5 (path='/home/azevedo/Data/PABIP/PROCESS/Sigma-bak', nickname='master.ph5')
    p.read_array_t_names ()
    p.calc_offsets (p.Array_t_names[0], '1002', shot_line="Event_t_001")
    traces = p.cut ('11528', 1443332700., 1443337210., chan=1, sample_rate=200.)
    p.close (); sys.exit ()
    #t0 = p.read_t ("Offset_t")
    ##print t0; sys.exit ()
    ##   Read Experiment_t, return kef
    #t1 = p.read_t ("Experiment_t")
    ##print t1
    ##   Read Sort_t, return kef
    #t2 = p.read_t ("Sort_t")
    ##   Read Event_t, return kef
    #t3 = p.read_t ("Event_t")
    ##print t3
    ##   Read Array_t_001, return kef
    #t4 = p.read_t ("Array_t", n=1)
    ##   Read Response_t, return kef
    #t5 = p.read_t ("Response_t")
    ##   Read Receiver_t, return kef
    #t6 = p.read_t ("Receiver_t")
    ##   Read Index_t, return kef
    #t7 = p.read_t ("Index_t")
    ##   Read Das_t for sn 10550, return kef
    #t8 = p.read_t ("Das_t", "10875")
    #print t8
    ##   Read Time_t, return kef
    #t9 = p.read_t ("Time_t")
    #print t9
    #   Read data in shot order, return Trace object
    p.read_array_t_names ()
    #for n in p.Array_t_names :
    for n in ['Array_t_006'] :
        if not p.Array_t.has_key (n) :
            p.read_array_t (n)
            
        array_t = p.Array_t[n]['byid']
        for k in array_t.keys () :
            das = array_t[k]['das/serial_number_s']
            #   Cut, DAS sn, start epoch, stop epoch
            d = p.cut (das, 1200913195.333, 1200913200.5, sample_rate=100)
            print d.nsamples
    ##   Read data in receiver order, return Trace object
    #p.read_event_t_names ()
    #for n in p.Event_t_names :
        #if not p.Event_t.has_key (n) :
            #p.read_event_t (n)
            
        #event_t = p.Event_t[n]['byid']
        #for k in event_t.keys () :
            #t0 = fepoch (event_t[k]['time/epoch_l'], event_t[k]['time/micro_seconds_i'])
            ##   Cut, DAS sn, event time (as epoch), event time + length
            #d = p.cut ('11809', t0, t0 + 10., sample_rate=100)
            #i = 0
            #print d.start_time.getFdsnTime ()
            #for point in d.data :
                #print i, point
                #i += 1
            #pass
    p.close ()