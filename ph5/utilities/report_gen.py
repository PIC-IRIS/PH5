#!/usr/bin/env pnpython2

#
#   Generate the reports "data_description.txt" and "data_report_key.txt"
#

import sys, os, os.path, time, string
#   This provides the base functionality
from ph5.core import experiment, TimeDoy
#   The wiggles are stored as numpy arrays
import numpy

PROG_VERSION = '2011.144'

#
#   These are to hold different parts of the meta-data
#
#   /Experiment_g/Experiment_t
EXPERIMENT_T = None
#   /Experiment_g/Sorts_g/Event_t
EVENT_T = None
#   /Experiment_g/Sorts_g/Offset_t
OFFSET_T = None
#   /Experiment_g/Sorts_g/Sort_t
SORT_T = None
#   /Experiment_g/Responses_g/Response_t
RESPONSE_T = None
#   /Experiment_g/Sorts_g/Array_t_[nnn]
ARRAY_T = {}
#   /Experiment_g/Receivers_g/Das_g_[sn]/Das_t (keyed on DAS)
DAS_T = {}
#   /Experiment_g/Receivers_g/Das_g_[sn]/Receiver_t (keyed on DAS)
RECEIVER_T = {}
#   /Experiment_g/Receivers_g/Das_g_[sn]/SOH_a_[n] (keyed on DAS then by SOH_a_[n] name) 
SOH_A = {}
#   A list of Das_Groups that refers to Das_g_[sn]'s
DASS = {}

os.environ['TZ'] = 'UTM'
time.tzset ()
#
#   To hold table rows and keys
#
class Rows_Keys (object) :
    __slots__ = ('rows', 'keys')
    def __init__ (self, rows = None, keys = None) :
        self.rows = rows
        self.keys = keys
        
    def set (self, rows = None, keys = None) :
        if rows != None : self.rows = rows
        if keys != None : self.keys = keys

#
#   To hold DAS sn and references to Das_g_[sn]
#
class Das_Groups (object) :
    __slots__ = ('das', 'node')
    def __init__ (self, das = None, node = None) :
        self.das = das
        self.node = node
        
class Offset_Azimuth (object) :
    __slots__ = ('offset', 'azimuth')
    def __init__ (self, offset = None, azimuth = None) :
        self.offset = offset
        self.azimuth = azimuth

#
#   Read Command line arguments
#
def get_args () :
    global PH5, PATH, DEBUG, KEY_GIN, DES_GIN, DAS_SN
    
    from optparse import OptionParser
    
    oparser = OptionParser ()
    
    oparser.usage = "report-gin --nickname=ph5-file-prefix options"
    
    oparser.description = "Generate data_description.txt and/or data_request_key.txt."
    
    oparser.add_option ("-n", "--nickname", dest = "ph5_file_prefix",
                        help = "The ph5 file prefix (experiment nickname).",
                        metavar = "ph5_file_prefix")
    
    oparser.add_option ("-p", "--path", dest = "ph5_path",
                        help = "Path to ph5 files. Defaults to current directory.",
                        metavar = "ph5_path")
    
    oparser.add_option ("-k", "--key", dest = "key_gin",
                        help = "Write data_request_key.txt.",
                        action = "store_true", default = False)
    
    oparser.add_option ("-d", "--description", dest = "des_gin",
                        help = "Write data_description.txt.",
                        action = "store_true", default = False)
    
    #oparser.add_option ("-D", "--das_sn", dest = "das_sn",
                        #help = "Only consider a single DAS. Required with --key option.",
                        #metavar = "das_sn")
    
    oparser.add_option ("--bug", dest = "debug", action = "store_true", default = False)
    
    options, args = oparser.parse_args ()
    
    if options.ph5_file_prefix != None :
        PH5 = options.ph5_file_prefix
    else :
        PH5 = None
        
    if options.ph5_path != None :
        PATH = options.ph5_path
    else :
        PATH = "."
        
    if options.debug != None :
        DEBUG = options.debug
    
    KEY_GIN = options.key_gin
    DES_GIN = options.des_gin
    #DAS_SN = options.das_sn
    if KEY_GIN :
        sys.stderr.write ("Warning: Generation of data_request_key.txt is no longer needed.\n")
    
    if KEY_GIN == False and DES_GIN == False :
        sys.stderr.write ("Error: Either --key or --description option is required.\n")
        sys.exit (-3)
        
    #if DAS_SN == None and KEY_GIN == True :
        #sys.stderr.write ("Error: --das_sn option required with --key option.\n")
        #sys.exit (-4)
        
    if PH5 == None :
        sys.stderr.write ("Error: Missing required option --nickname. Try --help\n")
        sys.exit (-1)
        
    #ph5_path = os.path.join (PATH, PH5) + '.ph5'
    #if not os.path.exists (ph5_path) :
        #sys.stderr.write ("Error: %s does not exist.\n" % ph5_path)
        #sys.exit (-2)

#
#   Initialize ph5 file
#
def initialize_ph5 (editmode = False) :
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5
    
    EX = experiment.ExperimentGroup (PATH, PH5)
    EX.ph5open (editmode)
    EX.initgroup ()

#
#   Print Rows_Keys
#
def debug_print (a) :
    i = 1
    #   Loop through table rows
    for r in a.rows :
        #   Print line number
        #print "%d) " % i,
        i += 1
        #   Loop through each row column and print
        for k in a.keys :
            print k, "=>", r[k], ",",
        print
        
def info_print () :
    import time
    global EX
    
    print "#\n#\t%s\tph5 version: %s\n#" % (time.ctime (time.time ()), EX.version ())
#
#   Print Rows_Keys
#
def table_print (t, a) :
    i = 0
    #   Loop through table rows
    for r in a.rows :
        i += 1
        print "#   Table row %d" % i
        #   Print table name
        print t
        #   Loop through each row column and print
        for k in a.keys :
            print "\t", k, "=", r[k]
        
def read_experiment_table () :
    '''   Read /Experiment_g/Experiment_t   '''
    global EX, EXPERIMENT_T
    
    exp, exp_keys = EX.read_experiment ()
    
    rowskeys = Rows_Keys (exp, exp_keys)
    
    EXPERIMENT_T = rowskeys
    
def read_event_table () :
    '''   Read /Experiment_g/Sorts_g/Event_t   '''
    global EX, EVENT_T
    
    events, event_keys = EX.ph5_g_sorts.read_events ()
    
    rowskeys = Rows_Keys (events, event_keys)
    
    EVENT_T = rowskeys
    
def read_offset_table () :
    '''   Read /Experinent_t/Sorts_g/Offset_t   '''
    global EX, OFFSET_T
    
    offsets, offset_keys = EX.ph5_g_sorts.read_offsets ()
    
    rowskeys = Rows_Keys (offsets, offset_keys)
    
    OFFSET_T = rowskeys
    
def read_sort_table () :
    '''   Read /Experiment_t/Sorts_g/Sort_g   '''
    global EX, SORT_T
    
    sorts, sorts_keys = EX.ph5_g_sorts.read_sorts ()
    
    rowskeys = Rows_Keys (sorts, sorts_keys)
    
    SORT_T = rowskeys
    
def read_sort_arrays () :
    '''   Read /Experiment_t/Sorts_g/Array_t_[n]   '''
    global EX, ARRAY_T
    
    #   We get a list of Array_t_[n] names here...
    #   (these are also in Sort_t)
    names = EX.ph5_g_sorts.names ()
    for n in names :
        arrays, array_keys = EX.ph5_g_sorts.read_arrays (n)
        
        rowskeys = Rows_Keys (arrays, array_keys)
        #   We key this on the name since there can be multiple arrays
        ARRAY_T[n] = rowskeys
    
def read_response_table () :
    '''   Read /Experiment_g/Respones_g/Response_t   '''
    global EX, RESPONSE_T
    
    response, response_keys = EX.ph5_g_responses.read_responses ()
    
    rowskeys = Rows_Keys (response, response_keys)
    
    RESPONSE_T = rowskeys

#   NOT USED
def read_receivers () :
    '''   Read tables and arrays (except wiggles) in Das_g_[sn]   '''
    global EX, DAS_T, RECEIVER_T, DASS, SOH_A
    
    #   Get references for all das groups keyed on das
    dasGroups = EX.ph5_g_receivers.alldas_g ()
    dass = dasGroups.keys ()
    #   Sort by das sn
    dass.sort ()
    for d in dass :
        #   Get node reference
        g = dasGroups[d]
        dg = Das_Groups (d, g)
        #   Save a master list for later
        DASS.append (dg)
        
        #   Set the current das group
        EX.ph5_g_receivers.setcurrent (g)
        
        #   Read /Experiment_g/Receivers_g/Das_g_[sn]/Das_t
        das, das_keys = EX.ph5_g_receivers.read_das ()
        rowskeys = Rows_Keys (das, das_keys)
        DAS_T[d] = rowskeys
        
        #   Read /Experiment_g/Receivers_g/Receiver_t
        receiver, receiver_keys = EX.ph5_g_receivers.read_receiver ()
        rowskeys = Rows_Keys (receiver, receiver_keys)
        RECEIVER_T[d] = rowskeys
        
        #   Read SOH file(s) for this das
        SOH_A[d] = EX.ph5_g_receivers.read_soh ()
        
def read_das_groups () :
    '''   Get das groups   '''
    global EX
    
    #   Get references for all das groups keyed on das
    return EX.ph5_g_receivers.alldas_g ()

def read_das_table (das) :
    global EX, DASS
    
    if DASS.has_key (das) :
        EX.ph5_g_receivers.setcurrent (DASS[das])
        das_r, das_keys = EX.ph5_g_receivers.read_das ()
        return Rows_Keys (das_r, das_keys)
    else :
        return None
        
def strip_offset_t () :
    global OFFSET_T, STATION_ID, EVENT_ID
    
    if STATION_ID == None and EVENT_ID == None : return
    
    tmp = []
    for o in OFFSET_T.rows :
        event_id = o['event_id_s']
        receiver_id = o['receiver_id_s']
        
        if STATION_ID != None and EVENT_ID != None :
            if event_id == EVENT_ID and receiver_id == STATION_ID :
                tmp.append (o)
        elif STATION_ID == None :
            if event_id == EVENT_ID :
                tmp.append (o)
        elif EVENT_ID == None :
            if station_id == STATION_ID :
                tmp.append (o)
                
    if tmp != [] :
        OFFSET_T = Rows_Keys (tmp, OFFSET_T.keys)

def strip_array_t () :
    global ARRAY_T, STATION_ID, DAS_SN
    
    if STATION_ID == None and DAS_SN == None : return
    
    keys = ARRAY_T.keys ()
    for k in keys :
        tmp = []
        for a in ARRAY_T[k].rows :
            station_id = a['id_s']
            das_sn = a['das/serial_number_s']
            if STATION_ID != None and DAS_SN != None :
                if station_id == STATION_ID and das_sn == DAS_SN :
                    tmp.append (a)
            elif STATION_ID == None :
                if das_sn == DAS_SN :
                    tmp.append (a)
            elif DAS_SN == None :
                if station_id == STATION_ID :
                    tmp.append (a)
        
        if tmp != [] :
            ARRAY_T[k] = Rows_Keys (tmp, ARRAY_T[k].keys)
            
def offset_t_sort (a, b) :
    return cmp (a['offset/value_d'], b['offset/value_d'])

def order_station_by_offset () :
    global SORTED_OFFSET
    
    SORTED_OFFSET = OFFSET_T.rows
    
    for o in SORTED_OFFSET :
        if o['azimuth/value_f'] < 0 :
            o['offset/value_d'] = o['offset/value_d'] * -1.0
            
    SORTED_OFFSET.sort (offset_t_sort)
    
def key_array (array) :
    ka = {}
    for a in array.rows :
        ka[a['id_s']] = a
           
    return ka
    
def build_array_from_offset (array) :
    global SORTED_OFFSET
    sorted_array = []
    
    keyed_array = key_array (array)
    
    for o in SORTED_OFFSET :
        station = o['receiver_id_s']
        sorted_array.append (keyed_array[station])
        
    return Rows_Keys (sorted_array, array.keys)

def array_start_stop (ar) :
    start = 2145916800; stop = 0
    for a in ar.rows :
        if a['deploy_time/epoch_l'] < start :
            start = a['deploy_time/epoch_l']
            
        if a['pickup_time/epoch_l'] > stop :
            stop = a['pickup_time/epoch_l']
            
    return start, stop

def get_sample_rate (a, start, stop) :
    
    Array_t = ARRAY_T[a].rows
    for array_t in Array_t :
        das = array_t['das/serial_number_s']
        
        Das_t = read_das_table (das)
        if Das_t == None : continue
        for das_t in Das_t.rows :
            das_start = das_t['time/epoch_l']
            das_stop = das_start + das_t['sample_count_i'] / (das_t['sample_rate_i'] / float (das_t['sample_rate_multiplier_i']))
                
            #   Start contained
            if das_start >= start and das_start <= stop :
                return int (das_t['sample_rate_i'] / float (das_t['sample_rate_multiplier_i']))
            
            #   Stop contained
            if das_stop >= start and das_stop <= stop :
                return int (das_t['sample_rate_i'] / float (das_t['sample_rate_multiplier_i']))
     
    return 0

def write_key_report () :
    global SORT_T, ARRAY_T, EVENT_T
    
    try :
        fh = open ("data_request_key.txt", "w+")
    except :
        sys.stderr.write ("Failed to open \"data_request_key.txt\".\n")
        return
    
    A = {}
    for k in ARRAY_T.keys () :
        a = ARRAY_T[k]
        start, stop = array_start_stop (a)
        array_i = int (k[-3:])
        A[array_i] = (start, stop)
    
    #tdoy = timedoy.TimeDOY ()
    fh.write ("shot|time|arrays\n")
    array_i_keys = A.keys ()
    for e in EVENT_T.rows :
        arrays = ''
        for i in array_i_keys :
            start, stop = A[i]
            if start == 0 :
                arrays = arrays + "%d," % i
            elif int (e['time/epoch_l']) >= start and int (e['time/epoch_l']) <= stop :
                arrays = arrays + "%d," % i
                
        ttuple = time.gmtime (int (e['time/epoch_l']))
        pictime = "%4d:%03d:%02d:%02d:%02d" % (ttuple[0],
                                               ttuple[7],
                                               ttuple[3],
                                               ttuple[4],
                                               ttuple[5])
        fh.write ("%s|%s|%s\n" % (e['id_s'],
                                  pictime,
                                  arrays[:-1]))
        

    fh.write ("request key|start time|length in seconds|array name|description\n")
    i = 1
    for s in SORT_T.rows :
        secs = int (s['end_time/epoch_l']) - int (s['start_time/epoch_l'])
        ttuple = time.gmtime (int (s['start_time/epoch_l']))
        #wday, amo, da, hrmnsc, yr = string.split (s['start_time/ascii_s'])
        #hr, mn, sc = string.split (hrmnsc, ':')
        #pictime = tdoy.getPasscalTime (amo, int (da), int (hr), int (mn), int (sc), int (yr))
        pictime = "%4d:%03d:%02d:%02d:%02d" % (ttuple[0],
                                               ttuple[7],
                                               ttuple[3],
                                               ttuple[4],
                                               ttuple[5])
        fh.write ("%d|%s|%5.3f|%s|%s\n" % (i,
                                           pictime,
                                           float (secs),
                                           s['array_name_s'],
                                           s['description_s']))
        
        i += 1
        
    fh.close ()
    
def write_des_report () :
    global EXPERIMENT_T, ARRAY_T, EVENT_T
    
    tdoy = timedoy.TimeDOY ()
    
    A = {}
    for k in ARRAY_T.keys () :
        a = ARRAY_T[k]
        start, stop = array_start_stop (a)
        array_i = int (k[-3:])
        A[array_i] = (start, stop)    
    
    fh = open ("data_description.txt", "w+")
    
    for e in EXPERIMENT_T.rows : pass
    
    fh.write ("\t\t\t%s\n\n%s\n\n%s\n\n%s\n\n%s\n\n" % (e['nickname_s'],
                                                        e['longname_s'],
                                                        e['PIs_s'],
                                                        e['institutions_s'],
                                                        e['summary_paragraph_s']))
    
    fh.write ("***   Please check the following lines and remove this line before submission to DMC.   ***\n")
    fh.write ("\t\t\tShots\n\n")
    fh.write ("shot id\ttime                     lat         lon         elev (m) size (kg) depth (m)\n")
    fh.write ("-" * 85); fh.write ('\n')
    for e in EVENT_T.rows :
        ttuple = time.gmtime (int (e['time/epoch_l']))
        secs = ttuple[5] + (e['time/micro_seconds_i'] / 1000000.)
        #wday, amo, da, hrmnsc, yr = string.split (s['start_time/ascii_s'])
        #hr, mn, sc = string.split (hrmnsc, ':')
        #pictime = tdoy.getPasscalTime (amo, int (da), int (hr), int (mn), int (sc), int (yr))
        pictime = "%4d:%03d:%02d:%02d:%06.3f" % (ttuple[0],
                                                 ttuple[7],
                                                 ttuple[3],
                                                 ttuple[4],
                                                 secs)
        fh.write ("%-5s\t%s %12.6f %12.6f %9.3f %9.3f %9.3f\n" % (e['id_s'],
                                                                  pictime,
                                                                  e['location/Y/value_d'],
                                                                  e['location/X/value_d'],
                                                                  e['location/Z/value_d'],
                                                                  e['size/value_d'],
                                                                  e['depth/value_d']))
    
    fh.write ("\n\t\t\tArrays\n\n")
    
    arrays = ARRAY_T.keys ()
    
    arrays.sort ()
    for a in arrays :
        start, stop = A[int(a[-3:])]
        fh.write ("***   Please check the following lines and remove this line before submission to DMC.   ***\n")
        sample_rate = get_sample_rate (a, start, stop)
        
        fh.write ("\nArray: %s\n" % a[-3:])
        #   Sample rate:
        fh.write ("\t\tSample Rate: %d sps\n" % sample_rate)
        #   Sensor type
        #   Deployment time
        fh.write ("\t\tDeployment Time: %s\n" % tdoy.epoch2PasscalTime (start)[:-10])
        #   Pickup time
        fh.write ("\t\tPickup Time:     %s\n" % tdoy.epoch2PasscalTime (stop)[:-10])
        fh.write ("\t\tComponents: 1 => Z, 2 => N, 3 => E\n\n")
        fh.write ("station\tdas      lat         lon            elev (m)    component\n")
        fh.write ('-' * 65); fh.write ('\n')
        for e in ARRAY_T[a].rows :
            fh.write ("%-5s\t%s %12.6f %12.6f %9.3f\t%d\n" % (e['id_s'],
                                                              e['das/serial_number_s'],
                                                              float (e['location/Y/value_d']),
                                                              float (e['location/X/value_d']),
                                                              float (e['location/Z/value_d']),
                                                              e['channel_number_i']))
            
    #   Need to write sorts here!
        
    fh.close ()
    
        
if __name__ == '__main__' :
    global KEY_GIN, DES_GIN
    
    get_args ()
    
    sys.stderr.write ("Opening...")
    
    initialize_ph5 ()
    
    read_sort_arrays ()
    read_event_table ()
    DASS = read_das_groups ()
    
    if KEY_GIN == True :
        sys.stderr.write ("Writing data key report...\n")
        read_sort_table ()
        write_key_report ()
        
    if DES_GIN == True :
        sys.stderr.write ("Writing data description report...\n")
        read_experiment_table ()
        write_des_report ()
    
    #read_sort_arrays ()
    
    #for k in ARRAY_T.keys () :
        #debug_print (ARRAY_T[k])
    
    #if OFFSET == True :
        #read_offset_table ()
        #read_sort_table ()
        #read_sort_arrays ()
        #strip_offset_t ()
        ##debug_print (OFFSET_T)
        #strip_array_t ()
        ##for k in ARRAY_T.keys () :
            ##debug_print (ARRAY_T[k])
        #order_station_by_offset ()
        #info_print ()
        #for k in ARRAY_T.keys () :
            #rk = build_array_from_offset (ARRAY_T[k])
            #table_print ('/Experiment_g/Sorts_g/' + k, rk)
        
    EX.ph5close ()
    sys.stderr.write ("Done..\n")
