#!/usr/bin/env pnpython3
#
#   Core functionality to manipulate ph5 files
#
#   Steve Azevedo, August 2006
#

import tables, numpy
import os, os.path, time, sys, string, re
from ph5.core import columns
try :
    import importlib.reload as reload
except ImportError :
    pass

PROG_VERSION = '2017.069 Developmental'
ZLIBCOMP=6

os.environ['TZ'] = 'UTM'
time.tzset ()

externalLinkRE = re.compile (".*ExternalLink.*")

class HDF5InteractionError (Exception) :
    def __init__ (self, errno, msg) :
        self.args = (errno, msg)
        self.errno = errno
        self.msg = msg

class MapsGroup :
    ''' /Experiment_g/Maps_g
                        /Das_g_[nnnn]
                                /Hdr_a_[nnnn]
                        /Sta_g_[nnnn]
                        /Evt_g_[nnnn]
                        */Guides_g_[nnnn]
                                */Guide_t
                                */Fn_a_[nnnn]
                        */Blush_t
                                *out_s
                                *sub_s
                                *n_i
        * -> Not implemented.
        
        Un-tested as of December 4 2013.
        See JSON format:
        {
             "name":"Hdr_a_" {
             "properties": {
                  "FileType":"SAC"|"SEG-Y"|"MSEED"|"SEG-D"|"SEG-2" {,
                      "type":"string",
                      "description":"Type of originating file",
                      "required": True,
                  },
                  "HeaderType":"reel"|"trace"{,
                      "type":"string",
                      "description":"The header type",
                      "required":True,
                  },
                  "HeaderSubType":"iNova"|"Menlo"|"SEG"|"PASSCAL" {,
                      "type":"string",
                      "description":"Currently extended header type",
                      "required":False
                      },
             },
             "properties": {,
                  "key:value": {,
                      "type": "any",
                      "description": "varies",
                      "required": True 
                 },
             }
             }
        }
    '''
    def __init__ (self, ph5) :
        self.ph5 = ph5
        self.current_g_das = None
        self.arrayRE = re.compile ("([H]\w+_a_)(\d+)")
        self.groupRE = re.compile ("([DSE]\w+_g_)(\d+)")
        self.ph5_t_index = None   
        
    def initgroup (self) :
        try :
            #   Create Maps group
            self.ph5_g_maps = initialize_group (self.ph5, 
                                                '/Experiment_g',
                                                'Maps_g')
            #   Create Index table
            self.ph5_t_index = initialize_table (self.ph5,
                                                 '/Experiment_g/Maps_g',
                                                 'Index_t',
                                                 columns.Index)
            columns.add_reference ('/Experiment_g/Maps_g/Index_t', self.ph5_t_index)
        except tables.FileModeError as e :
            pass
        
    def nuke_index_t (self) :
        self.ph5_t_index.remove ()
        self.initgroup () 
            
    def setcurrent (self, g) :
        #   If this is an external link it needs to be redirected.
        if externalLinkRE.match (g.__str__ ()) :
            g = g ()
                
        self.current_g_das = g 
        
    def getdas_g (self, sn) :
        '''   Return group for a given serial number   '''
        sn = 'Das_g_' + sn
        self.current_g_das = None
        for g in self.ph5.iter_nodes ('/Experiment_g/Maps_g') :
            if g._v_name == sn :
                self.setcurrent (g)
                return g
            
        return None
            
    def newdas (self, what, sn) :
        #   Create a new group for a DAS, Station, or Event
        choices = ['Das_g_', 'Stn_g_', 'Evt_g_']
        if what in choices :
            sn = what + sn
        else : return None
        #   Create the das group
        d = initialize_group (self.ph5, '/Experiment_g/Maps_g', sn)
            
        self.current_g_das = d
        
        return d
    
    def get_array_nodes (self, name) :
        '''   Find array nodes based on name prefix   '''
        return get_nodes_by_name (self.ph5, 
                                  '/Experiment_g/Maps_g', 
                                  re.compile (name + '(\d+)'), None) 
    
    def writeheader (self, hdr_json_list, desc = None) :
        nxt = self.nextarray ('Hdr_a_')
        a = self.newearray (nxt, desc)
        a.append (hdr_json_list)
        
        a.flush ()
    
    def nextarray (self, prefix) :
        ns = 0
        name = self.current_g_das._v_name
        if columns.LAST_ARRAY_NODE_MAPS.has_key (name) and columns.LAST_ARRAY_NODE_MAPS[name].has_key (prefix) :
            mo = self.arrayRE.match (columns.LAST_ARRAY_NODE_MAPS[name][prefix])
            cprefix, an = mo.groups ()
            nombre = "%s%04d" % (prefix, int (an) + 1)
        else :
            for n in self.ph5.iter_nodes (self.current_g_das, classname = 'Array') :
                mo = self.arrayRE.match (n._v_name)
                if not mo : continue
                cprefix, an = mo.groups ()
                if cprefix == prefix :
                    if int (an) > ns :
                        ns = int (an)
                        
            nombre = "%s%04d" % (prefix, ns + 1)
            
        columns.add_last_array_node_maps (self.current_g_das, prefix, nombre)
            
        return nombre       
    
    def newearray (self, name, description = None) :
        #
        batom = tables.StringAtom (itemsize=40)
        a = create_empty_earray (self.ph5,
                                 self.current_g_das,
                                 name,
                                 batom=batom,
                                 expectedrows=120)
        
        if description != None :
            a.attrs.description = description
            
        return a
    
    def read_index (self) :
        '''   Read Index table   '''
        ret, keys = read_table (self.ph5_t_index)
        
        return ret, keys
    
    def read_hdr (self) :
        '''   Read Hdr text arrays   '''
        ret = {}
        arrays = self.get_array_nodes ('Hdr_a_')
        keys = arrays.keys ()
        for k in keys :
            name = arrays[k]._v_name
            ret[name] = arrays[k].read ()
            
        return ret       
    
    def populateIndex_t (self, p, key = None) :
        required_keys = ['serial_number_s', 'external_file_name_s']
        populate_table (self.ph5_t_index,
                        p,
                        key,
                        required_keys)
            
        self.ph5.flush ()    
#
###   Mixins refactor here Dec 11
#
#import sqlite3 as sql
class SortsGroup :
    '''   /Experiment_g/Sorts_g
                               /Sort_t                           #   columns.Sort, groups data by time and location
                               /Array_t_[array]                  #   columns.Array, groups data by location
                               /Offset_t(_[array]_[shotline])?   #   columns.Offset, source to receiver offsets
                               /Event_t(_[shotline])?            #   columns.Event, list of events
    '''
    def __init__ (self, ph5) :
        self.ph5 = ph5
        self.ph5_g_sorts = None
        self.ph5_t_sort = None
        self.ph5_t_array = {}                  #   Local cached nodes keyed on Array_t_xxx
        self.ph5_t_offset = {}                 #   Local cached nodes keyed on Offset_t_aaa_sss
        self.ph5_t_event = {}                  #   Local cached nodes keyed on Event_t_xxx
        self.Array_tRE = re.compile ("Array_t_(\d+)")
        self.Event_tRE = re.compile ("Event_t(_(\d+))?")
        self.Offset_tRE = re.compile ("Offset_t(_(\d+)_(\d+))?")
        
    def update_local_table_nodes (self) :
        '''
        Cache node references to Array_t_xxx, Event_t_xxx, Offset_t_aaa_sss, tables in this group
        '''
        names = columns.TABLES.keys ()
        for n in names :
            name = os.path.basename (n)
            #for re in (self.Array_tRE, self.Event_tRE, self.Offset_tRE) :
            mo = self.Array_tRE.match (name)
            if mo :
                self.ph5_t_array[name] = columns.TABLES[n]
                continue
            mo = self.Event_tRE.match (name)
            if mo :
                self.ph5_t_event[name] = columns.TABLES[n]
                continue
            mo = self.Offset_tRE.match (name)
            if mo :
                self.ph5_t_offset[name] = columns.TABLES[n]
        
    def read_offset (self, offset_name = None) :
        if offset_name == None and self.ph5_t_offset.has_key ('Offset_t') :
            #   Legacy naming
            ret, keys = read_table (self.ph5_t_offset['Offset_t'])
        else :
            try :
                node = self.ph5_t_offset[offset_name]
            except KeyError :
                node = self.ph5.get_node ('/Experiment_g/Sorts_g', name = offset_name, classname = 'Table')
                self.ph5_t_offset[offset_name] = node
                
            ret, keys = read_table (node)
            
        return ret, keys        
        
    def read_events (self, event_name = None) :
        if event_name == None and self.ph5_t_event.has_key ('Event_t') :
            #   Legacy 
            ret, keys = read_table (self.ph5_t_event['Event_t'])
        else :
            try :
                node = self.ph5_t_event[event_name]
            except KeyError :
                node = self.ph5.get_node ('/Experiment_g/Sorts_g', name = event_name, classname = 'Table')
                self.ph5_t_event[event_name] = node
                
            ret, keys = read_table (node)
            
        return ret, keys
    
    def read_sorts (self) :
        ret, keys = read_table (self.ph5_t_sort)
        
        return ret, keys
    
    def read_arrays (self, array_name) :
        try :
            node = self.ph5_t_array[array_name]
        except KeyError :
            node = self.ph5.get_node ('/Experiment_g/Sorts_g', name = array_name, classname = 'Table')
            self.ph5_t_array[array_name] = node
            
        ret, keys = read_table (node)
        
        return ret, keys
    
    ####   DBDBDB   ###
    #def db_create_offset (self, dbname) :
        ##import sqlite3 as sql
        #conn = sql.connect (dbname)
        #curs = conn.cursor ()
        #try :
            #curs.execute ("create table offsets (receiver_id_s integer, event_id_s integer, azimuth_value_f real, azimuth_units_s text, offset_value_d real, offset_units_s text)")
            #conn.commit ()
        #except sql.OperationalError :
            #pass
        
    ####   DBDBDB   ###    
    #def db_populate_offsets (self, dbname) :
        ##import sqlite3 as sql
        #conn = sql.connect (dbname)
        #curs = conn.cursor ()
        ##keys, names = columns.keys (self.ph5_t_offset)
        #for row in self.ph5_t_offset.iterrows () :
            #curs.execute ("insert into offsets values (?,?,?,?,?,?)", (int (row['receiver_id_s']),
                                                                       #int (row['event_id_s']),
                                                                       #row['azimuth/value_f'],
                                                                       #row['azimuth/units_s'],
                                                                       #row['offset/value_d'],
                                                                       #row['offset/units_s']))
        #conn.commit ()
    ####   DBDBDB   ###
    #def db_get_connection (self, dbname) :
        #conn = sql.connect  (dbname)
        #return conn
    ####   DBDBDB   ###
    #def db_read_offset (self, conn, shot, station) :
        ##import sqlite3 as sql
        #curs = conn.cursor ()
        #command = "select azimuth_value_f,azimuth_units_s,offset_value_d,offset_units_s from offsets where receiver_id_s={0} and event_id_s={1}".format (station, shot)
        #curs.execute (command)
        #flds = curs.fetchone ()
        #curs.close ()
        
        #row = None
        #if flds != None :
            #row = { 'azimuth_value_f':flds[0], 'azimuth_units_s':flds[1], 'offset_value_d':flds[2], 'offset_units_s':flds[3] }
        
        #return row
    
    ###   ###
    def index_offset_table (self, name='Offset_t', level=9, weight='full') :
        '''   Index offset table on event and station id_s
              Inputs:
                 name -> offset table name, Offset_t_002_003
                 level -> level of optimization, 0-9
                 weight -> kind of index, 'ultralight', 'light', 'medium', 'full'.
        '''
        #
        try :
            #
            self.ph5_t_offset[name].cols.event_id_s.create_index (optlevel=level, kind=weight)
        except (ValueError, tables.exceptions.NodeError, tables.exceptions.FileModeError) as e :
            #print e.message
            pass
        
        try :
            #
            self.ph5_t_offset[name].cols.receiver_id_s.create_index (optlevel=level, kind=weight)
        except (ValueError, tables.exceptions.NodeError, tables.exceptions.FileModeError) as e :
            #print e.message
            pass        
    
    def read_offset_fast (self, shot, station, name=None) :
        #
        if name == None and self.ph5_t_offset.has_key ('Offset_t'):
            #   Legacy
            name = 'Offset_t'
            
        ret = {}
        query = "(event_id_s == b'{0}') & (receiver_id_s == b'{1}')".format (shot, station)
        result = [[row['offset/value_d'],row['offset/units_s'],row['azimuth/value_f'],row['azimuth/units_s']] for row in self.ph5_t_offset[name].where (query)]
        
        if result :
            ret['offset/value_d'], ret['offset/units_s'], ret['azimuth/value_f'], ret['azimuth/units_s'] = result[0]
            ret['event_id_s'] = str (shot)
            ret['receiver_id_s'] = str (station)
        
        return ret
        
    def read_offsets (self, shotrange=None, stations=None, name='Offset_t') :
        offsets = []
        
        #shots = map (int, shots); shots = map (str, shots)
        if stations != None :
            stations = map (int, stations); stations = map (str, stations)
            
        keys, names = columns.keys (self.ph5_t_offset[name])
        
        for row in self.ph5_t_offset[name].iterrows () :
        #for row in self.ph5_t_offset.itersorted (self.ph5_t_offset.cols._f_col ('event_id_s'), checkCSI=False) :   #   forceCSI to True
            if shotrange != None :
                try :
                    shot = int (row['event_id_s'])
                except :
                    sys.stderr.write ("Warning: Non-numeric event in Offset_t. Event: {0} Station: {1}.\n".format (row['event_id_s'], row['receiver_id_s']))
                    continue
                    
                if shot > shotrange[1] :
                    continue
                
                if not (shot >= shotrange[0] and shot <= shotrange[1]) :
                    #print "Reject Shot", shot, shotrange
                    continue
                #else : print "Accept Shot", shot, shotrange
                
            if stations != None :
                try :
                    station = str (int (row['receiver_id_s']))
                except :
                    sys.stderr.write ("Warning: Non-numeric station in Offset_t. Event_t : {0} Station: {1}.\n".format (row['event_id_s'], row['receiver_id_s']))
                    continue
                
                if not station in stations :
                    #print "Reject Station", station, stations
                    continue
                
            #print "Match", shot, shotrange
            r = {}
            for k in keys :
                r[k] = row[k]
                
            offsets.append (r)
            
        #ret = columns.rowstolist (offsets, keys)
        #for o in offsets : print o
        #sys.exit ()
        return offsets, keys
    
    def newOffsetSort (self, name) :
        o = initialize_table (self.ph5, 
                              '/Experiment_g/Sorts_g',
                              name,
                              columns.Offset)
                
        self.ph5_t_offset[name] = o
        #self.index_offset_table (name=name)
                    
        columns.add_reference ('/Experiment_g/Sorts_g/' + name, self.ph5_t_offset[name])
                
        return o        
    
    def newEventSort (self, name) :
        e = initialize_table (self.ph5, 
                              '/Experiment_g/Sorts_g',
                              name,
                              columns.Event)
        
        self.ph5_t_event = e
            
        columns.add_reference ('/Experiment_g/Sorts_g/' + name, self.ph5_t_event)
        
        return e       
        
    def newArraySort (self, name) :
        '''   Names should be 000 - 999
              Array_t_xxx
        '''
        #name = 'Array_t_' + name
        #   Create Array table
        a = initialize_table (self.ph5, 
                              '/Experiment_g/Sorts_g',
                              name,
                              columns.Array)
        
        self.ph5_t_array = a
            
        columns.add_reference ('/Experiment_g/Sorts_g/' + name, self.ph5_t_array)
        
        return a
    
    def NewSort (self, name) :
        return self.newArraySort (name)
    
    #   June 18, 2015
    #def _names (self, what)
    #def _nextName (self, what)
    
    def nextName (self) :
        names = []
        names.append (0)
        for n in self.ph5.walk_nodes ('/Experiment_g/Sorts_g', classname = 'Table') :
            mo = self.Array_tRE.match (n._v_name)
            if not mo :
                continue
            
            name = int (mo.groups ()[0])
            names.append (name)
        
        names.sort ()
        s = "Array_t_%03d" % (names[-1] + 1)
        
        return s
    
    def namesRE (self, re) :
        '''   Sorts_g table names by RE   '''
        names = []
        for n in self.ph5.walk_nodes ('/Experiment_g/Sorts_g', classname = 'Table') :
            if re.match (n._v_name) :
                names.append (n._v_name)
                
        return names        
    
    def namesArray_t (self) :
        names = self.ph5_t_array.keys ()
        if len (names) == 0 :
            names = self.namesRE (self.Array_tRE)
            
        return names
    
    def names (self) :
        return self.namesArray_t ()

    def namesEvent_t (self) :
        names = self.ph5_t_event.keys ()
        if len (names) == 0 :
            names = self.namesRE (self.Event_tRE)
            
        return names
    
    def namesOffset_t (self) :
        names = self.ph5_t_offset.keys ()
        if len (names) == 0 :
            names = self.namesRE (self.Offset_tRE)
            
        return names    
    
    def populate (self, ref, p, key = []) :
        # 
        populate_table (ref, p, key)
        
        ref.flush ()
    
    def populateSort_t (self, p, pkey = []) :
        self.populate (self.ph5_t_sort, p, pkey)
            
    def populateArray_t (self, p, pkey = [], name=None) :
        self.populate (self.ph5_t_array[name], p, pkey)
            
    def populateEvent_t (self, p, pkey = [], name='Event_t') :
        self.populate (self.ph5_t_event[name], p, pkey)
        
    def populateOffset_t (self, p, pkey = [], name='Offset_t') :
        self.populate (self.ph5_t_offset[name], p, pkey)
    
    def initgroup (self) :
        #   Create Sorts group
        self.ph5_g_sorts = initialize_group (self.ph5, '/Experiment_g', 'Sorts_g')
        
        #   Create Sort table
        self.ph5_t_sort = initialize_table (self.ph5, 
                                            '/Experiment_g/Sorts_g', 
                                            'Sort_t', 
                                            columns.Sort)
            
        columns.add_reference ('/Experiment_g/Sorts_g/Sort_t', self.ph5_t_sort)
        
        #   Reference Offset table(s)   ***   See Offset_tRE   ***
        offsets = get_nodes_by_name (self.ph5, 
                                    '/Experiment_g/Sorts_g', 
                                    self.Offset_tRE, 
                                    'Table')   #   Should this be Table or Array? 
        keys = offsets.keys ()
        for k in keys :
            nombre = offsets[k]._v_name
            columns.add_reference ('/Experiment_g/Sorts_g/' + nombre, offsets[k])
            #self.index_offset_table (name=nombre)
            
        #   Reference Event table   ***   See Event_tRE   ***
        events = get_nodes_by_name (self.ph5, 
                                    '/Experiment_g/Sorts_g', 
                                    self.Event_tRE, 
                                    'Table')   #   Should this be Table or Array? 
        keys = events.keys ()
        for k in keys :
            nombre = events[k]._v_name
            columns.add_reference ('/Experiment_g/Sorts_g/' + nombre, events[k])
            
        #   Find any Attay_t_[nnn]
        arrays = get_nodes_by_name (self.ph5, 
                                    '/Experiment_g/Sorts_g', 
                                    self.Array_tRE, 
                                    'Table')   #   Should this be Table or Array?
        keys = arrays.keys ()
        for k in keys :
            nombre = arrays[k]._v_name
            columns.add_reference ('/Experiment_g/Sorts_g/' + nombre, arrays[k])
            
        self.update_local_table_nodes ()
                
    def nuke_array_t (self, n) :
        nombre = "Array_t_{0:03d}".format (n)
        allArray_t = self.names ()
        
        if nombre in allArray_t :
            n = self.ph5.get_node ('/Experiment_g/Sorts_g',
                                  name = nombre,
                                  classname = 'Table')
            n.remove ()
            #self.newSort (nombre)
            return True
        else :
            return False
            
    def nuke_event_t (self, name = 'Event_t') :
        try :
            self.ph5_t_event[name].remove ()
            self.initgroup ()
            return True
        except Exception as e :
            return False
        
    def nuke_sort_t (self) :
        try :
            self.ph5_t_sort.remove ()
            self.initgroup ()
            return True
        except Exception as e :
            return False
        
    def nuke_offset_t (self, name = 'Offset_t') :
        #   Remove the indexes before removing the table
        try :
            self.ph5_t_offset[name].cols.event_id_s.remove_index ()
        except Exception as e :
            pass
        
        try :
            self.ph5_t_offset[name].cols.receiver_id_s.remove_index ()
        except Exception as e :
            pass
        #   Remove cruft left from failed indexing
        cruftRE = re.compile (".*value_d")
        nodes = get_nodes_by_name (self.ph5, '/Experiment_g/Sorts_g/', cruftRE, None)
        for k in nodes.keys () :
            try :
                nodes[k].remove ()
            except Exception as e :
                pass
        #   Remove the offset table
        try :
            self.ph5_t_offset[name].remove ()
            self.initgroup ()
            return True
        except Exception as e :
            return False
        
        
class Data_Trace (object) :
    __slots__ = ("das", "epoch", "length", "channel", "data_trace", "receiver", "keys")
    def __init__ (self) :
        das        = None                #   ASCII DAS serial number
        epoch      = None                #   Floating point epoch
        length     = None                #   Length of data in seconds
        channel    = None                #   Channel number
        data_trace = None                #   Data trace reference
        receiver   = None                #   Receiver_t row for this das
        keys       = None                #   Receiver_t row keys
        
class ReceiversGroup :
    '''   /Experiment_g/Receivers_g/Das_g_[sn]                       #   Data for this DAS in this group
                                              /Das_t                 #   columns.Data
                                              /Data_a_[n]            #   A 1 x n array containing the data for an event
                                              /SOH_a_[n]             #   State of health data, usually a list of strings
                                              /Event_a_[n]           #   Event table, usually a list of strings
                                              /Log_a_[n]             #   Log channel
          /Experiment_g/Receivers_g
                                    /Receiver_t            #   columns.Receiver
                                    /Time_t                #   columns.Time
                                    /Index_t               #   columns.Index
    '''
    def __init__ (self, ph5) :
        self.ph5 = ph5
        self.ph5_g_receivers = None                         #   Receivers group
        self.current_g_das = None                           #   Current das group
        self.current_t_das = None                           #   Current das table
        #self.current_t_receiver = None                     #   Current receiver table
        self.ph5_t_receiver = None                          #   Current receiver table
        #self.current_t_time = None                         #   Current time table
        self.ph5_t_time = None                              #   Current time table
        self.ph5_t_index = None                             #
        self.arrayRE = re.compile ("([DSEL]\w+_a_)(\d+)")   #   Match arrays under Das_g_[sn]
        self.dasRE = re.compile ("Das_g_(.+)")              #   Match Das_g groups
        self.byteorder = None                               #   Trace atom byte order
        self.elementtype = None                             #   Trace atom type "int", "float", or "undetermined"
        
    def get_das_name (self) :
        '''   Return the current das name   '''
        if self.current_g_das == None :
            return None
        
        name = self.current_g_das._v_name.split ('_')
        
        return name[-1]
        
    def read_das (self) :
        '''   Read DAS table   '''
        def cmp_epoch (a, b) :
            return int (a['time/epoch_l']) - int (b['time/epoch_l'])
        
        ret = []; keys = None
        ret_read, keys = read_table (self.current_t_das)
        #print ret_read
        if ret_read != None :
            ret_read.sort (cmp=cmp_epoch)
        else :
            return ret, keys
        #
        #   We look through each Das_t line and make sure it has the column
        #   sample_rate_multiplier_i and if it is missing we set it to 1.
        #   This column was added after data had been archived without it
        #   at the DMC.
        #
        for r in ret_read :
            if not r.has_key ('sample_rate_multiplier_i') :
                r['sample_rate_multiplier_i'] = 1
            elif r['sample_rate_multiplier_i'] == 0 :
                r['sample_rate_multiplier_i'] = 1
                
            ret.append (r)
            
        return ret, keys
    
    def read_receiver (self) :
        '''   Read Receiver table   '''
        ret, keys = read_table (self.ph5_t_receiver)
        
        return ret, keys
    
    def read_time (self) :
        '''   Read Time table   '''
        ret, keys = read_table (self.ph5_t_time)
        
        return ret, keys
    
    def read_index (self) :
        '''   Read Index table   '''
        ret = None; keys = None
        if not self.ph5.__contains__ ('/Experiment_g/Receivers_g/Index_t') :
            return ret, keys
        
        #rows = []
        #keys, name = columns.keys (self.ph5_t_index)
        #for row in self.ph5_t_index.iterrows () :
            #rows.append (row)
         
        #ret = columns.rowstolist (rows, keys)
        ret, keys = read_table (self.ph5_t_index)
        
        return ret, keys
        
    def get_array_nodes (self, name) :
        '''   Find array nodes based on name prefix   '''
        arrays = get_nodes_by_name (self.ph5, 
                                    '/Experiment_g/Receivers_g', 
                                    re.compile (name + "(\d+)"), 
                                    'Array')
                                    
            
        return arrays
    
    def read_soh (self) :
        '''   Read SOH text arrays   '''
        ret = {}
        try :
            das_g = self.current_g_das._v_name
        except AttributeError as e :
            return ret
        
        #print "Das ", das_g
        arrays = get_nodes_by_name (self.ph5,
                                    self.current_g_das,
                                    re.compile ('SOH_a_' + "(\d+)"),
                                    'Array')
        keys = arrays.keys ()
        for k in keys :
            name = arrays[k]._v_name
            ret[name] = arrays[k].read ()
            #print name, ret[name]
            
        return ret
    
    def read_event (self) :
        '''   Read Event text arrays   '''
        ret = {}
        arrays = self.get_array_nodes ('Event_a_')
        keys = arrays.keys ()
        for k in keys :
            name = arrays[k]._v_name
            ret[name] = arrays[k].read ()
            
        return ret
    
    def read_log (self) :
        '''   Read Log text arrays   '''
        ret = {}
        arrays = self.get_array_nodes ('Log_a_')
        keys = arrays.keys ()
        for k in keys :
            name = arrays[k]._v_name
            ret[name] = arrays[k].read ()
            
        return ret        
        
    def trace_info (self, trace_ref) :
        #print trace_ref.atom
        try :
            s = repr (trace_ref.atom)
            #print s
            s = s.split ("(")[0]
            #print s
            if s == "Int32Atom" :
                t = "int"
            elif s == "Float32Atom" :
                t = "float"
            else : t = "undetermined"
        except Exception as e :
            sys.stderr.write ("Unable to get trace element type.\n(0)\n".format (e.message))
            t = "undetermined"
        
        return t, trace_ref.byteorder
    
    def read_trace (self, trace_ref, start = None, stop = None) :
        '''   Read data trace   '''
        #
        if start == None and stop == None :
            data = trace_ref.read ()
        else :
            data = trace_ref.read (start = start, stop = stop)
        #    
        return data
    
    def find_trace_ref (self, name) :
        try :
            node = self.ph5.get_node (self.current_g_das, name = name, classname = 'Array')
        except Exception as e :
            sys.stderr.write ("Warning: DAS group: {0} Name: {1} Error: {2}\n".format (self.current_g_das,
                                                                                       name,
                                                                                       e.message))
            node = None
            
        return node
        
    def find_traces (self, epoch = None) :
        traces = []                             #   List of data_trace (above)
        das_dict = {}                           #   Keyed on DAS points to traces list
        receiver_t = []
        
        x = 0
        #   Get all Das_g
        for g in self.ph5.iter_nodes ('/Experiment_g/Receivers_g') :
            traces = []
            #   Not sure why it returns its own name???
            if g._v_name == 'Receivers_g' :
                continue
            
            #   Get Das_t
            t = g.Das_t
            
            #tr = self.ph5.get_node ('/Experiment_g/Receivers_g/' + g._v_name, name = 'Receiver_t', classname = 'Table')
            #   Get Receiver_t
            tr = g.Receiver_t
            tkeys, names = columns.keys (tr)
            #   XXX   This is a kludge!   XXX
            for receiver in tr :
                receiver_t.append (receiver)
            
            #t = self.ph5.get_node ('/Experiment_g/Receivers_g/' + g._v_name, name = 'Das_t', classname = 'Table')
            for r in t.iterrows () :
                i = r['receiver_table_n_i']
                e = float (r['time/epoch_l']) + float (r['time/micro_seconds_i']) / 1000000.0
                sps = r['sample_rate_i']
                a = r['array_name_data_a']
                an = self.ph5.get_node ('/Experiment_g/Receivers_g/' + g._v_name + '/' + a)
                n = an.nrows
                #   Length of trace in seconds
                l = float (n) / float (sps)
                #   Epoch of last sample
                s = e + l
                #   Does epoch fall in trace? epoch == None flag to get all
                if (epoch >= e and epoch <= s) or epoch == None :
                    #   Get an instance of our Data_Trace (structure?)
                    dt = Data_Trace ()
                    dt.das = g._v_name[6:]
                    dt.epoch = e
                    dt.length = l
                    dt.channel = r['channel_number_i']
                    dt.data_trace = an
                    #   Just return receiver table row for this das
                    dt.receiver = receiver_t[i]
                    dt.keys = tkeys
                    #print dt.receiver['sensor/serial_number_s']
                    traces.append (dt)
            
            x = x + 1
            #   No epoch so key on x
            if epoch == None :
                das_dict[str (x)] = traces
            #   We have an epoch so key on das
            else :
                das_dict[dt.das] = traces
            
        return das_dict
    
    def setcurrent (self, g) :
        '''
        '''
        #   If this is an external link it needs to be redirected.
        #print g, g.__str__(), g.__repr__()
        if externalLinkRE.match (g.__str__ ()) :
            #print g
            try :
                if self.ph5.mode == 'r' :
                    g = g ()
                else :
                    g = g (mode='a')
            except tables.exceptions.NoSuchNodeError :
                self.current_g_das = None
                self.current_t_das = None
                return
            
        self.current_g_das = g
        self.current_t_das = g.Das_t
            
        #self.current_t_receiver = g.Receiver_t
        #self.current_t_time = g.Time_t
        
    def getdas_g (self, sn) :
        '''   Return group for a given serial number   '''
        sn = 'Das_g_' + sn
        self.current_g_das = None
        try :
            g = self.ph5.get_node (self.ph5_g_receivers, name=sn)
            self.current_g_das = g
        except Exception as e :
            raise HDF5InteractionError (0, e.message)
            
        return self.current_g_das
    
    def alldas_g (self) :
        dasGroups = get_nodes_by_name (self.ph5, 
                                       '/Experiment_g/Receivers_g', 
                                       re.compile ('Das_g_' + '(\w+)'),
                                       None)
           
        return dasGroups
    #
    def init_Das_t (self, sn) :
        sn = 'Das_g_' + sn
        t = initialize_table (self.ph5, 
                              '/Experiment_g/Receivers_g/' + sn, 
                              'Das_t', 
                              columns.Data)
        return t
    #   New das group and tables 
    def newdas (self, sn) :
        t = None
        sn = 'Das_g_' + sn
        #   Create the das group
        d = initialize_group (self.ph5, 
                              '/Experiment_g/Receivers_g', 
                              sn)
        
        t = initialize_table (self.ph5, 
                              '/Experiment_g/Receivers_g/' + sn, 
                              'Das_t', 
                              columns.Data)
        
        self.current_g_das = d
        self.current_t_das = t
        columns.add_reference ('/Experiment_g/Receivers_g/' + sn + '/Das_t', self.current_t_das)
        
        return d, t, self.ph5_t_receiver, self.ph5_t_time
    
    def nextarray (self, prefix) :
        ns = 0
        name = self.current_g_das._v_name
        if columns.LAST_ARRAY_NODE_DAS.has_key (name) and columns.LAST_ARRAY_NODE_DAS[name].has_key (prefix) :
            mo = self.arrayRE.match (columns.LAST_ARRAY_NODE_DAS[name][prefix])
            cprefix, an = mo.groups ()
            nombre = "%s%04d" % (prefix, int (an) + 1)
            #
        else :
            #
            for n in self.ph5.iter_nodes (self.current_g_das, classname = 'Array') :
                mo = self.arrayRE.match (n._v_name)
                if not mo : continue
                cprefix, an = mo.groups ()
                if cprefix == prefix :
                    if int (an) > ns :
                        ns = int (an)
                        
            nombre = "%s%04d" % (prefix, ns + 1)
            
        columns.add_last_array_node_das (self.current_g_das, prefix, nombre)
            
        return nombre
    
    def newearray (self, name, description = None, expectedrows = None) :
        #prefix, body, suffix = string.split (name, '_')
        #pbody = "_".join ([prefix, body]) + '_'   
        
        batom = tables.StringAtom (itemsize=80)
        a = create_empty_earray (self.ph5, 
                                 self.current_g_das, 
                                 name,
                                 batom=batom,
                                 expectedrows=expectedrows)
        
        if description != None :
            a.attrs.description = description
                
        return a
    
    
    def newdataearray (self, name, data, batom = None, rows = None) :
        #   Use zlib, standard for HDF5
        bfilter = tables.Filters (complevel=ZLIBCOMP, complib='zlib', shuffle=True)
        #
        a = create_data_earray (self.ph5, 
                                self.current_g_das, 
                                name, 
                                data, 
                                batom, 
                                rows=rows)
        
        return a
                
    def newarray (self, name, data, dtype = None, description = None) :
        '''   
              name is name of array as follows:
              Data_a_[event_number]   --- Numarray array
              SOH_a_[n]             --- State of health (python list)
              Event_a_[n]           --- Event table (python list)
              Log_a_[n]             --- Generic log channel (python list)
              
              inputs: name        --- name of array
                      data        --- data to place in array
                      description --- description of array
                      
              returns: tables array descriptor
        '''
        #   If this is a data array convert it to a numarray.array
        prefix, body1, suffix = string.split (name, '_')
        pbody = "_".join ([prefix, body1]) + '_'
        if prefix == 'Data' :
            if dtype == None :
                dtype = 'i'
            
            data = numpy.fromiter (data, dtype=dtype)
        
        if self.current_g_das != None :
            try :
                self.ph5.remove_node (self.current_g_das, name = name)
                sys.stderr.write ("Warning: Node %s exists. Overwritten. " % name)
            except Exception, e :
                pass
                
            if dtype == 'int32' :
                a = self.newdataearray (name, data, batom = tables.Int32Atom ())
            elif dtype == 'float32' :
                ###
                a = self.newdataearray (name, data, batom = tables.Float32Atom ())
            else :
                a = self.ph5.create_array (self.current_g_das, name, data)
            
        if description != None :
            a.attrs.description = description
            
        return a
    
    def populateDas_t (self, p, key = None) :
        required_keys = ['time/epoch_l', 'channel_number_i', 'array_name_data_a']
            
        populate_table (self.current_t_das, p, key, required_keys)
            
        self.ph5.flush ()
            
    def populateReceiver_t (self, p, key = None) :
        required_keys = []
        
        populate_table (self.current_t_receiver, p, key, required_keys)    
            
        self.ph5.flush ()
        
    def populateTime_t (self, p, key = None) :
        required_keys = ['das/serial_number_s', 'start_time/epoch_l', 'end_time/epoch_l', 'offset_l', 'slope_d']
            
        populate_table (self.current_t_time, p, key, required_keys)
            
        self.ph5.flush ()
        
    def populateIndex_t (self, p, key = None) :
        required_keys = ['serial_number_s', 'external_file_name_s']
            
        populate_table (self.ph5_t_index, p, key, required_keys)
            
        self.ph5.flush ()
        
    def indexIndex_t (self) :
        '''   Set up indexing on DAS SN and external mini filename   '''
        try :
            self.ph5_t_index.cols.serial_number_s.create_csindex ()
            #self.ph5_t_index.cols.external_file_name_s.create_csindex ()
        except (ValueError, tables.exceptions.NodeError, tables.exceptions.FileModeError) as e :
            #print e.message
            pass
        #print self.ph5_t_index.autoindex
        try :
            #self.ph5_t_index.cols.serial_number_s.create_csindex ()
            self.ph5_t_index.cols.external_file_name_s.create_csindex ()
        except (ValueError, tables.exceptions.NodeError, tables.exceptions.FileModeError) as e :
            #print e.message
            pass        
            
    def initgroup (self) :
        #   Create receivers group
        self.ph5_g_receivers = initialize_group (self.ph5, 
                                                 '/Experiment_g', 
                                                 'Receivers_g')
        #   Create receivers table
        self.ph5_t_receiver = initialize_table (self.ph5, 
                                                '/Experiment_g/Receivers_g', 
                                                'Receiver_t', 
                                                columns.Receiver)
        #   Create time table
        self.ph5_t_time = initialize_table (self.ph5, 
                                            '/Experiment_g/Receivers_g', 
                                            'Time_t', 
                                            columns.Time)
        #   Create index table
        self.ph5_t_index = initialize_table (self.ph5, 
                                             '/Experiment_g/Receivers_g', 
                                             'Index_t', 
                                             columns.Index)
        self.ph5_t_index.expectedrows = 1000000
        #self.indexIndex_t ()   
        
        columns.add_reference ('/Experiment_g/Receivers_g/Receiver_t', self.ph5_t_receiver)
        columns.add_reference ('/Experiment_g/Receivers_g/Time_t', self.ph5_t_time)
        columns.add_reference ('/Experiment_g/Receivers_g/Index_t', self.ph5_t_index)
    
    def nuke_index_t (self) :
        self.ph5_t_index.remove ()
        self.initgroup ()
        
    def nuke_receiver_t (self) :
        self.ph5_t_receiver.remove ()
        self.initgroup ()
        
    def nuke_time_t (self) :
        self.ph5_t_time.remove ()
        self.initgroup ()
        
    def nuke_das_t (self, das) :
        g = self.getdas_g (das)
        if not g : return False
        self.setcurrent (g)
        self.current_t_das.truncate (0)
        #self.newdas (das)
        return True
        
    
class ReportsGroup :
    '''   /Experiment_g/Reports_g                      #   Group to hold experiment reports
                                 /Report_t             #   Report table, columns.Report
                                 /Report_a_[title]     #   The report in pdf format
    '''
    def __init__ (self, ph5) :
        self.ph5 = ph5
        self.ph5_g_reports = None
        self.ph5_t_report = None
        self.Report_aRE = re.compile ("Report_a_(\d\d\d)")
        
    def read_reports (self) :
        ret, keys = read_table (self.ph5_t_report)
        
        return ret, keys
    
    def nextName (self) :
        report_array_nodes = get_nodes_by_name (self.ph5, 
                                                '/Experiment_g/Reports_g', 
                                                self.Report_aRE, 
                                                'Array')
        keys = report_array_nodes.keys ()
        keys.sort ()
        try :
            n = int (keys[-1])
        except :
            n = 0
            
        s = "Report_a_%03d" % (n + 1)
        
        return s
    
    def get_report (self, name) :
        buf = None
        try :
            node = self.ph5.get_node (self.ph5_g_reports, name = name, classname = 'Array')
            #print node.flavor, node.nrows, node.nrow, node.type, node.stype, node.itemsize
            buf = node.read ()
            #print len (buf), node.itemsize
        except Exception, e :
            sys.stderr.write ("Error: Failed to read report %s\n" % name)
            
        return buf        
        
    def newarray (self, title, data, description = None) :
        name = title
        try :
            self.ph5.remove_node (self.current_g_reports, name = name)
            sys.stderr.write ("Warning: Node %s exists. Overwritten. " % name)
        except Exception, e :
            pass
        
        #print "Len: ", len (data)
        a = self.ph5.create_array (self.ph5_g_reports, name, data)
        if description != None :
            a.attrs.description = description

    def populate (self, p, pkey = None) :
        populate_table (self.ph5_t_report, 
                        p, 
                        key=pkey)
        
        self.ph5.flush ()
        
    def initgroup (self) :
        #   Create reports group
        self.ph5_g_reports = initialize_group (self.ph5, 
                                               '/Experiment_g', 
                                               'Reports_g')
        #   Create reports table
        self.ph5_t_report = initialize_table (self.ph5, 
                                              '/Experiment_g/Reports_g', 
                                              'Report_t', 
                                              columns.Report)
            
        columns.add_reference ('/Experiment_g/Reports_g/Report_t', self.ph5_t_report)
        
    def nuke_report_t (self) :
        self.ph5_t_report.remove ()
        self.initgroup ()
            
class ResponsesGroup :
    def __init__ (self, ph5) :
        self.ph5 = ph5
        self.ph5_g_responses = None
        self.ph5_t_response = None
        
    def populateResponse_t (self, p, pkey = None) :
        populate_table (self.ph5_t_response, p, pkey)
        
    def read_responses (self) :
        ret, keys = read_table (self.ph5_t_response)
        
        return ret, keys
    
    def get_response (self, name) :
        try:
            node = self.ph5.get_node (name)
            out =""
            for i in node:
                out=out+i
        except Exception, e :
            sys.stderr.write ("Error: Failed to read response %s\n" % name)
            
        return out        
    
    def newearray (self, name, description = None) :
        #
        batom = tables.StringAtom (itemsize=40)
        a = create_empty_earray (self.ph5,
                                 self.current_g_das,
                                 name,
                                 batom=batom,
                                 expectedrows=120)
        
        if description != None :
            a.attrs.description = description
            
        return a
    
    def initgroup (self) :
        #   Create response group
        self.ph5_g_responses = initialize_group (self.ph5, 
                                                 '/Experiment_g', 
                                                 'Responses_g')
        #   Create response table
        self.ph5_t_response = initialize_table (self.ph5, 
                                                '/Experiment_g/Responses_g', 
                                                'Response_t', 
                                                columns.Response)
            
        columns.add_reference ('/Experiment_g/Responses_g/Response_t', self.ph5_t_response)
        
    def nuke_response_t (self) :
        self.ph5_t_response.remove ()
        self.initgroup ()
    
class ExperimentGroup :
    def __init__ (self, currentpath = '.', nickname = "untitled-experiment") :
        self.nickname = nickname                       #   Experiment official nickname
        self.currentpath = currentpath                 #   Path to directory holding ph5 file
        self.filename = self.ph5buildFilename ()       #   Make filename
        self.ph5 = None                                #   PyTables file reference
        self.ph5_g_experiment = None                   #   Experiment group
        self.ph5_t_experiment = None                   #   Experiment table
        self.ph5_g_sorts = None                        #   Sorts group
        self.ph5_g_receivers = None                    #   Receivers group
        self.ph5_g_reports = None                      #   Reports group
        self.ph5_g_responses = None
        self.ph5_g_maps = None                         #   Maps group
        
    def version (self) :
        return columns.PH5VERSION
    
    def __version__ (self) :
        self.version ()
        
    def read_experiment (self) :
        ret, keys = read_table (self.ph5_t_experiment)
            
        return ret, keys
        
    def ph5exists (self) :
        '''   Check to see if file exists
              self.h5 -- Reference to hdf5 file   '''
        if os.path.exists (self.filename) :
            if tables.is_pytables_file (self.filename) :
                #   XXX Needs to be modified to return version of ph5 XXX
                return True
            else :
                return False
        else :
            return False
    
    def ph5buildFilename (self) :
        '''   Build filename from path and experiment nickname   '''
        postfix = '.ph5'
        if self.nickname[-4:] == postfix :
            f = os.path.join (self.currentpath, self.nickname)
        else :
            f = os.path.join (self.currentpath, self.nickname + postfix)
            
        return f
    
    def ph5flush (self) :
        self.ph5.flush ()
    
    def ph5open (self, editmode = False, ph5title = 'PIC KITCHEN HDF5 file, Version = ' + columns.PH5VERSION) :
        '''   Open ph5 file, create it if it doesn't exist   '''
        if self.ph5exists () :
            #   XXX Needs try:except XXX
            if editmode == True :
                self.ph5 = tables.open_file (self.filename, mode = 'a')
            else :
                self.ph5 = tables.open_file (self.filename, mode = 'r')
        elif editmode == True :
            self.ph5 = tables.open_file (self.filename, mode = 'w', title = ph5title)
        else :
            #print "XXX   Edit mode???   XXX"
            self.ph5 = None
            
    def ph5close (self) :
        if self.ph5 != None and self.ph5.isopen :
            self.ph5.close ()
            self.ph5 = None
            #   This will not work with version 3
            reload (columns)
            
    def populateExperiment_t (self, p) :
        ''' Keys: 'time_stamp/type, time_stamp/epoch, time_stamp/ascii, time_stamp/micro_seconds
                   nickname, longname, PIs, institutions, 
                   north_west_corner/coordinate_system, north_west_corner/projection
                   north_west_corner/ellipsoid, north_west_corner/[XYZ]/[units,value]
                   north_west_corner/description, (same for south_east_corner)
                   summary_paragraph'   '''
        
        populate_table (self.ph5_t_experiment, p)
        
        self.ph5.flush ()
            
    def initgroup (self, ph5_g_title = 'PIC KITCHEN HDF5 file, Version = ' + columns.PH5VERSION) :
        '''   If group Experiment_g does not exist create it, otherwise get a reference to it
              If table Experiment_t does not exist create it, otherwise get a reference to it   '''
        #   Create experiment group
        self.ph5_g_experiment = initialize_group (self.ph5, 
                                                  '/', 
                                                  'Experiment_g')
        #   Create experiment table
        self.ph5_t_experiment = initialize_table (self.ph5, 
                                                  '/Experiment_g', 
                                                  'Experiment_t', 
                                                  columns.Experiment)
        
        #   Put handle in lookup table columns.TABLE   
        columns.add_reference ('/Experiment_g/Experiment_t', self.ph5_t_experiment)
        
        #   XXX This stuff should be in own methods? XXX
        self.ph5_g_sorts = SortsGroup (self.ph5)
        self.ph5_g_sorts.initgroup ()
        
        self.ph5_g_receivers = ReceiversGroup (self.ph5)
        self.ph5_g_receivers.initgroup ()
        
        self.ph5_g_reports = ReportsGroup (self.ph5)
        self.ph5_g_reports.initgroup ()
        
        self.ph5_g_responses = ResponsesGroup (self.ph5)
        self.ph5_g_responses.initgroup ()
        
        self.ph5_g_maps = MapsGroup (self.ph5)
        self.ph5_g_maps.initgroup ()
        
    def nuke_experiment_t (self) :
        self.ph5_t_experiment.remove ()
        #   Create experiment group
        self.ph5_g_experiment = initialize_group (self.ph5, 
                                                  '/', 
                                                  'Experiment_g')
        #   Create experiment table
        self.ph5_t_experiment = initialize_table (self.ph5, 
                                                  '/Experiment_g', 
                                                  'Experiment_t', 
                                                  columns.Experiment)
        
        #   Put handle in lookup table columns.TABLE   
        columns.add_reference ('/Experiment_g/Experiment_t', self.ph5_t_experiment)

#
###   Mixins
#
def initialize_group (filenode, where, group, title = '') :
    returnnode = None
    path = '/'.join ([where, group])
    if filenode.__contains__ (path) :
        returnnode = filenode.get_node (where, name = group, classname = 'Group')
    else :
        returnnode = filenode.create_group (where, group, title = title)
            
    return returnnode

def initialize_table (filenode, where, table, description, expectedrows = None) :
    returnnode = None
    path = '/'.join ([where, table])
    if filenode.__contains__ (path) :
        returnnode = filenode.get_node (where, name = table, classname = 'Table')
    else :
        if expectedrows == None :
            returnnode = filenode.create_table (where, table, description)
        else :
            returnnode = filenode.create_table (where, table, description, expectedrows = expectedrows)
            
    return returnnode

def populate_table (tablenode, key_value, key = None, required_keys = []) :
    #if tablenode :
    err_keys, err_required = columns.validate (tablenode, key_value, required_keys)
    
    if err_keys :
        raise HDF5InteractionError (1, err_keys)
    
    if err_required :
        raise HDF5InteractionError (2, err_required)
    
    try :
        columns.populate (tablenode, key_value, key)
        tablenode.flush ()
    except Exception as e :
        raise HDF5InteractionError (3, e.message)
        
def read_table (tablenode) :
    ret = []; keys = None
    if not tablenode :
        return ret, keys
    
    try : 
        tableiterator = tablenode.iterrows ()
        keys, names = columns.keys (tablenode)
        ret = columns.rowstolist (tableiterator, keys)
    except Exception as e :
        raise HDF5InteractionError (4, e.message)
    
    return ret, keys

def create_empty_earray (filenode, groupnode, name, batom = None, expectedrows = None) :
    try :
        bfilter = tables.Filters (complevel=ZLIBCOMP, complib='zlib')
        if expectedrows == None :
            a = filenode.create_earray (groupnode, 
                                        name, 
                                        atom=batom, 
                                        shape=(0,), 
                                        filters=bfilter)
        else :
            a = filenode.create_earray (groupnode, 
                                        name, 
                                        atom=batom, 
                                        shape=(0,), 
                                        filters=bfilter, 
                                        expectedrows=expectedrows)            
            
    except Exception as e :
        raise HDF5InteractionError (5, e.message)
    
    return a    

def create_data_earray (filenode, groupnode, name, data, batom, rows = None) :
    try :
        if rows == None :
            rows = len (data) / 4
            
        a = create_empty_earray (filenode, 
                                 groupnode, 
                                 name, 
                                 batom=batom, 
                                 expectedrows=rows)
        
        a.append (data)
    except Exception as e :
        raise HDF5InteractionError (6, e.message)
    
    return a

def get_nodes_by_name (filenode, where, RE, classname) :
    nodes = {}
    for n in filenode.iter_nodes (where, classname=classname) :
        mo = RE.match (n._v_name)
        if mo :
            #key = mo.groups ()[-1]
            key = n._v_name
            nodes[key] = n
            
    return nodes
        
if __name__ == '__main__' :
    import os
    #os.system ('rm -rf ./untitled-experiment.ph5')
    ex = ExperimentGroup ('.', 'GEO_DESIRE')
    #print ex.filename
    EDITMODE = False
    ex.ph5open (EDITMODE)
    ex.initgroup ()
    reports, keys = ex.ph5_g_reports.read_reports ()
    for r in reports :
        for k in keys :
            print k, r[k]
      
    ex.ph5close ()
    sys.exit ()
    sorts = ex.ph5_g_sorts.read_sorts ()
    first_sort = True
    i = 0
    for s in sorts :
        #   Get a dictionary of DASs in this array
        a_name = s['array_t_name_s']
        array = ex.ph5_g_sorts.read_arrays (a_name)
        #   The dictionary
        dass = {}
        for a in array :
            dass[a['das/serial_number_s']] = True
        
        #   Loop through events and populate the Sort_t table
        events = ex.ph5_g_sorts.read_events ()
        for e in events :
            ep = float (e['time/epoch_l']) + (float (e['time/micro_seconds_i']) / 1000000.0)
            dict = ex.ph5_g_receivers.find_traces (ep)
            ks = dict.keys ()
            for k in ks :
                
                #   Is this das in this array?
                if not dass.has_key (dict[k].das) :
                    print "Not found in any array: ", dict[k].das
                    continue
                lat = dict[k].receiver['location/X/value_d']
                lon = dict[k].receiver['location/Y/value_d']
                print dict[k].das, dict[k].epoch, dict[k].length, lat, lon
                i = i + 1
                
    print "Matched %d traces." % i
        
    #p = {}
    #epoch = time.time ()
    #p['time_stamp/epochs'] = epoch
    #p['time_stamp/ascii'] = time.ctime (epoch)
    #p['time_stamp/type'] = columns.TIME_TYPE['BOTH']
    #p['time_stamp/micro_seconds'] = 0
    #ex.populateExperiment_t (p)
    ##print `ex.ph5_t_experiment[:]`
    #ex.ph5_g_receivers.newdas ('9905')
    #p = {}
    #p['time/epoch'] = epoch
    #p['channel_number'] = 1
    #p['array_name_date'] = [1,2,3,4,5,6,7,8,9,0]
    #ex.ph5_g_receivers.populateDas_t (p)
    ex.ph5close ()
    
