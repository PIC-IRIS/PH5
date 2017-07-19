#!/usr/bin/env pnpython4

#
#   Dump tables in ph5 file to kef format.
#
#   Steve Azevedo, April 2007
#

import sys, os, os.path, string, time
#   This provides the base functionality
from ph5.core import experiment
#   The wiggles are stored as numpy arrays
import numpy

PROG_VERSION = "2017.136"
#
#   These are to hold different parts of the meta-data
#
def init_local () :
    global EXPERIMENT_T, EVENT_T, OFFSET_T, SORT_T, RESPONSE_T, REPORT_T, ARRAY_T, DAS_T
    global RECEIVER_T, SOH_A, INDEX_T, M_INDEX_T, DASS, TIME_T, TABLE_KEY
    #   /Experiment_g/Experiment_t
    EXPERIMENT_T = None
    #   /Experiment_g/Sorts_g/Event_t
    EVENT_T = {}
    #   /Experiment_g/Sorts_g/Offset_t
    OFFSET_T = {}
    #   /Experiment_g/Sorts_g/Sort_t
    SORT_T = None
    #   /Experiment_g/Responses_g/Response_t
    RESPONSE_T = None
    #   /Experiment_g/Reports_g/Report_t
    REPORT_T = None
    #   /Experiment_g/Sorts_g/Array_t_[nnn]
    ARRAY_T = {}
    #   /Experiment_g/Receivers_g/Das_g_[sn]/Das_t (keyed on DAS)
    DAS_T = {}
    #   /Experiment_g/Receivers_g/Receiver_t
    RECEIVER_T = None
    #   /Experiment_g/Receivers_g/Das_g_[sn]/SOH_a_[n] (keyed on DAS then by SOH_a_[n] name) 
    SOH_A = {}
    #   /Experiment_g/Receivers_g/Index_t
    INDEX_T = None
    #   /Experiment_g/Maps_g/Index_t
    M_INDEX_T = None
    #   A list of Das_Groups that refers to Das_g_[sn]'s
    DASS = []
    #   /Experiment_g/Receivers_g/Time_t
    TIME_T = None
    #
    TABLE_KEY = None

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

#
#   Read Command line arguments
#
def get_args () :
    global PH5, PATH, DEBUG, EXPERIMENT_TABLE, SORT_TABLE, OFFSET_TABLE, EVENT_TABLE, \
           ARRAY_TABLE, RESPONSE_TABLE, REPORT_TABLE, RECEIVER_TABLE, DAS_TABLE, TIME_TABLE, \
           TABLE_KEY, INDEX_TABLE, M_INDEX_TABLE, ALL_ARRAYS, ALL_EVENTS
    
    from optparse import OptionParser
    
    oparser = OptionParser ()
    
    oparser.usage = "Version: {0}\ntabletokef --nickname ph5-file-prefix options".format (PROG_VERSION)
    
    oparser.description = "Dump a table to a kef file."
    
    oparser.add_option ("-n", "--nickname", dest = "ph5_file_prefix",
                        help = "The ph5 file prefix (experiment nickname).",
                        metavar = "ph5_file_prefix")
    
    oparser.add_option ("-p", "--path", dest = "ph5_path",
                        help = "Path to ph5 files. Defaults to current directory.",
                        metavar = "ph5_path")
    
    oparser.add_option ("-u", "--update_key", dest = "update_key",
                        help = "Set generated kef file to do an Update on key.",
                        metavar = "update_key", type = "string")
    
    oparser.add_option ("-d", dest = "debug", action = "store_true", default = False)
    
    oparser.add_option ("-E", "--Experiment_t", dest = "experiment_t", action = "store_true",
                        default = False,
                        help = "Dump /Experiment_g/Experiment_t to a kef file.")
    
    oparser.add_option ("-S", "--Sort_t", dest = "sort_t", action = "store_true",
                        default = False,
                        help = "Dump /Experiment_g/Sorts_g/Sort_t to a kef file.")
    
    oparser.add_option ("-O", "--Offset_t", dest = "offset_t_", metavar="a_e",
                        help = "Dump /Experiment_g/Sort_g/Offset_t_[arrayID_eventID] to a kef file.")
    
    oparser.add_option ("-V", "--Event_t_", dest = "event_t_", metavar="n",
                        type=int,
                        help = "Dump /Experiment_g/Sorts_g/Event_t_[n] to a kef file.")
    
    oparser.add_option ("--all_events", dest='all_events', action='store_true',
                        default=False,
                        help='Dump all /Experiment_g/Sorts_g/Event_t_xxx to a kef file.')
    
    oparser.add_option ("-A", "--Array_t_", dest = "array_t_", metavar = "n",
                        type=int,
                        help = "Dump /Experiment_g/Sorts_g/Array_t_[n] to a kef file.")
    
    oparser.add_option ("--all_arrays", dest = 'all_arrays', action='store_true',
                        default=False,
                        help = "Dump all /Experiment_g/Sorts_g/Array_t_xxx to a kef file.")
    
    oparser.add_option ("-R", "--Response_t", dest = "response_t", action = "store_true",
                        default = False,
                        help = "Dump /Experiment_g/Responses_g/Response_t to a kef file.")
    
    oparser.add_option ("-P", "--Report_t", dest = "report_t", action = "store_true",
                        default = False,
                        help = "Dump /Experiment_g/Reports_g/Report_t to a kef file.")
    
    oparser.add_option ("-C", "--Receiver_t", dest = "receiver_t", action = "store_true",
                        default = False,
                        help = "Dump /Experiment_g/Receivers_g/Receiver_t to a kef file.")
    
    oparser.add_option ("-I", "--Index_t", dest = "index_t", action = "store_true",
                        default = False,
                        help = "Dump /Experiment_g/Receivers_g/Index_t to a kef file.")
    
    oparser.add_option ("-M", "--M_Index_t", dest = "m_index_t", action = "store_true",
                            default = False,
                            help = "Dump /Experiment_g/Maps_g/Index_t to a kef file.")    
    
    oparser.add_option ("-D", "--Das_t", dest = "das_t_", metavar = "das",
                        help = "Dump /Experiment_g/Receivers_g/Das_g_[das]/Das_t to a kef file.")
    
    oparser.add_option ("-T", "--Time_t", dest = "time_t", action = "store_true",
                        default = False,
                        help = "Dump /Experiment_g/Receivers_g/Time_t to a kef file.")
    
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
        
    EXPERIMENT_TABLE = options.experiment_t
    SORT_TABLE = options.sort_t
    if options.offset_t_ != None :
        try :
            OFFSET_TABLE = map (int, options.offset_t_.split ("_"))
        except Exception as e :
            sys.stderr.write ("Offset table should be entered as arrayID underscore shotLineID, eg. 1_2 or 0_0.")
            sys.stderr.write (e.message)
            sys.exit ()
    else :
        OFFSET_TABLE = None
    EVENT_TABLE = options.event_t_
    TIME_TABLE = options.time_t
    INDEX_TABLE = options.index_t
    M_INDEX_TABLE = options.m_index_t
    
    if options.update_key != None :
        TABLE_KEY = options.update_key
        
    if options.array_t_ != None :
        ARRAY_TABLE = options.array_t_
    else :
        ARRAY_TABLE = None
        
    ALL_ARRAYS = options.all_arrays
    ALL_EVENTS = options.all_events
    RESPONSE_TABLE = options.response_t
    REPORT_TABLE = options.report_t
    
    RECEIVER_TABLE = options.receiver_t
        
    if options.das_t_ != None :
        DAS_TABLE = options.das_t_
    else :
        DAS_TABLE = None
        
    if PH5 == None :
        sys.stderr.write ("Error: Missing required option. Try --help\n")
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
def table_print (t, a) :
    global TABLE_KEY
    global PATH
    global EX
    i = 0
    s=''
    s=s+"#\n#\t%s\tph5 version: %s\n#\n" % (time.ctime (time.time ()), EX.version ())
    #   Loop through table rows
    for r in a.rows :
        i += 1
        
        s= s+"#   Table row %d\n" % i
        #   Print table name
        if TABLE_KEY in a.keys :
            s=s+ "{0}:Update:{1} \n".format (t, TABLE_KEY)
        else :
            s=s+ t+"\n"
        #   Loop through each row column and print
        for k in a.keys :
            s=s+"\t" + str(k) + "=" + str(r[k])+"\n"
        print s,; s = ''
    #f=open(PATH+"/temp.kef", "w")
    #f.write(s)


	
#
#
#
def read_time_table () :
    global EX, TIME_T
    
    times, time_keys = EX.ph5_g_receivers.read_time ()
    
    TIME_T = Rows_Keys (times, time_keys)

def read_report_table () :
    global EX, REPORT_T
    
    reports, report_keys = EX.ph5_g_reports.read_reports ()
    
    rowskeys = Rows_Keys (reports, report_keys)
    
    REPORT_T = rowskeys
        
def read_experiment_table () :
    '''   Read /Experiment_g/Experiment_t   '''
    global EX, EXPERIMENT_T
    
    exp, exp_keys = EX.read_experiment ()
    
    rowskeys = Rows_Keys (exp, exp_keys)
    
    EXPERIMENT_T = rowskeys
    
def read_event_table () :
    '''   Read /Experiment_g/Sorts_g/Event_t   '''
    global EX, EVENT_T
    
    if EVENT_TABLE == 0 :
        T = "Event_t"
    else :
        T = "Event_t_{0:03d}".format (EVENT_TABLE)
    
    try :    
        events, event_keys = EX.ph5_g_sorts.read_events (T)
    except Exception as e :
        sys.stderr.write ("Error: Can't read {0}.\nDoes it exist?\n".format (T))
        sys.exit ()
    
    rowskeys = Rows_Keys (events, event_keys)
    
    EVENT_T[T] = rowskeys
    
def read_all_event_table () :
    global EX, EVENT_T
    import re
    EVENT_T_NAME_RE = re.compile ("Event_t.*")
    
    names = EX.ph5_g_sorts.namesRE (EVENT_T_NAME_RE)
    for name in names :
        try :
            events, event_keys = EX.ph5_g_sorts.read_events (name)
        except Exception as e :
            sys.stderr.write ("Error: Can't read {0}.\nDoes it exist?\n".format (name))
            continue
        
        rowskeys = Rows_Keys (events, event_keys)
        EVENT_T[name] = rowskeys
        
def read_offset_table () :
    '''   Read /Experinent_t/Sorts_g/Offset_t   '''
    global EX, OFFSET_T
    
    #offset_t = []
    #array = int (OFFSET_TABLE[0])
    #if array < 1 : array = 1
    #array = "Array_t_{0:03d}".format (array)
    #try :
        #arrays, array_keys = EX.ph5_g_sorts.read_arrays (array)
    #except Exception as e :
        #sys.stderr.write ("Error: Can't read {0}.\n".format (array))
        #sys.exit ()
        
    #event = int (OFFSET_TABLE[1])
    #if event == 0 :
        #event = "Event_t"
        #name = "Offset_t"
    #else :
        #event = "Event_t_{0:03d}".format (event)
        #name = "Offset_t_{0:03d}_{1:03d}".format (int (OFFSET_TABLE[0]), int (OFFSET_TABLE[1]))
    
    #try :    
        #events, event_keys = EX.ph5_g_sorts.read_events (event)
    #except Exception as e :
        #sys.stderr.write ("Error: Can't read {0}.\n".format (event))
        #sys.exit ()
    
    #for array_t in arrays :
        #sta = array_t['id_s']
        #for event_t in events :
            #evt = event_t['id_s']
            #try :
                #offset = EX.ph5_g_sorts.read_offset_fast (evt, sta, name=name)
            #except Exception as e :
                #sys.stderr.write ("Error: Problem reading offset for sta {0}, shot {1}. PH5 table {3}.".format (sta, evt, name))
                #break
                
            #offset_t.append (offset)
            
    if OFFSET_TABLE[0] == 0 or OFFSET_TABLE[1] == 0 :
        name = "Offset_t"
    else :
        name = "Offset_t_{0:03d}_{1:03d}".format (OFFSET_TABLE[0], OFFSET_TABLE[1])            
    
    try :
        rows, keys = EX.ph5_g_sorts.read_offset (name)
    except Exception as e :
        return
        
    #print offset_t
    OFFSET_T[name] = Rows_Keys (rows, keys)
    
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
    
def read_receiver_table () :
    global EX, RECEIVER_T
    
    #   Read /Experiment_g/Receivers_g/Receiver_t
    receiver, receiver_keys = EX.ph5_g_receivers.read_receiver ()
    rowskeys = Rows_Keys (receiver, receiver_keys)
    RECEIVER_T = rowskeys
    
def read_index_table () :
    global EX, INDEX_T
    
    rows, keys = EX.ph5_g_receivers.read_index ()
    INDEX_T = Rows_Keys (rows, keys)
    
def read_m_index_table () :
    global EX, M_INDEX_T
    
    rows, keys = EX.ph5_g_maps.read_index ()
    M_INDEX_T = Rows_Keys (rows, keys)
            
def read_receivers (das = None) :
    '''   Read tables and arrays (except wiggles) in Das_g_[sn]   '''
    global EX, DAS_T, RECEIVER_T, DASS, SOH_A
    
    dasGroups = EX.ph5_g_receivers.alldas_g ()
    if das == None :
        #   Get references for all das groups keyed on das
        dass = dasGroups.keys ()
        #   Sort by das sn
        dass.sort ()
    else :
        dass = [das]
        
    for d in dass :
        #   Get node reference
        if not dasGroups.has_key ("Das_g_"+d) :
            continue
        
        g = dasGroups["Das_g_"+d]
        dg = Das_Groups (d, g)
        #   Save a master list for later
        DASS.append (dg)
        
        #   Set the current das group
        EX.ph5_g_receivers.setcurrent (g)
        
        #   Read /Experiment_g/Receivers_g/Das_g_[sn]/Das_t
        das, das_keys = EX.ph5_g_receivers.read_das ()
        rowskeys = Rows_Keys (das, das_keys)
        DAS_T[d] = rowskeys
        

        #   Read SOH file(s) for this das
        SOH_A[d] = EX.ph5_g_receivers.read_soh ()

#####################################################
# def readPH5
# author: Lan Dam
# updated: 201703
# read data from exp(PH5) to use for KefUtility => KefEdit.py
def readPH5(exp, filename, path, tableType, arg=None):
    print "readPH5"
    global EX, OFFSET_TABLE, EVENT_TABLE, ARRAY_TABLE, OFFSET_T, EVENT_T, ARRAY_T, DAS_T
    
    EX = exp
    
    
    if tableType == "Experiment_t":
        read_experiment_table ()
        return EXPERIMENT_T
        
    if tableType == "Sort_t" :
        read_sort_table ()
        return SORT_T
        
    if tableType == "Offset_t" :
        OFFSET_T = {}               # clear cache
        OFFSET_TABLE = map (int, arg.split ("_"))
        read_offset_table ()
        keys = OFFSET_T.keys ()
        return OFFSET_T
        
    if tableType == "Event_t":
        EVENT_T = {}               # clear cache
        EVENT_TABLE = int(arg)
        read_event_table ()
        return EVENT_T
    
    if tableType == "All_Event_t":
        EVENT_T = {}               # clear cache
        
        for n in EX.Event_t_names:
            if n == 'Event_t': EVENT_TABLE = 0
            else: EVENT_TABLE = int( n.replace('Event_t_', '') )            
            read_event_table()
            
        return EVENT_T
        
    if tableType == "Index_t":
        read_index_table ()
        return INDEX_T
        
    if tableType == "Map_Index_t":
        read_m_index_table ()
        return M_INDEX_T
        
    if tableType == "Time_t":
        read_time_table ()
        return TIME_T
        
    if tableType == "Array_t":
        ARRAY_T = {}               # clear cache
        ARRAY_TABLE = arg
        read_sort_table ()
        read_sort_arrays ()
        arrays = ARRAY_T.keys ()
        for a in arrays :
            n = int (string.split (a, '_')[2])
            if n == int (ARRAY_TABLE) :        
                return ARRAY_T[a]
            
    if tableType == "All_Array_t":
        ARRAY_T = {}               # clear cache
        read_sort_table ()            
        read_sort_arrays ()
        arrays = ARRAY_T.keys ()            
        return ARRAY_T       
        
    if tableType == "Response_t":
        read_response_table ()
        return RESPONSE_T
        
    if tableType == "Report_t":
        read_report_table ()
        return REPORT_T
        
    if tableType == "Receiver_t" :
        read_receiver_table ()
        return RECEIVER_T
        
    if tableType == "Das_t":
        DAS_T = {}               # clear cache
        read_receivers (arg)
        return DAS_T


def main():
    global PH5, PATH, DEBUG, EXPERIMENT_TABLE, SORT_TABLE, OFFSET_TABLE, EVENT_TABLE, \
           ARRAY_TABLE, RESPONSE_TABLE, REPORT_TABLE, RECEIVER_TABLE, DAS_TABLE, TIME_TABLE, INDEX_TABLE
    
    init_local ()
    
    get_args ()
    
    initialize_ph5 ()
    
    if EXPERIMENT_TABLE :
        read_experiment_table ()
        table_print ("/Experiment_g/Experiment_t", EXPERIMENT_T)
        
    if SORT_TABLE :
        read_sort_table ()
        table_print ("/Experiment_g/Sorts_g/Sort_t", SORT_T)
        
    if OFFSET_TABLE :
        read_offset_table ()
        keys = OFFSET_T.keys ()
        for k in keys :
            table_print ("/Experiment_g/Sorts_g/{0}".format (k), OFFSET_T[k])
        
    if EVENT_TABLE != None :
        read_event_table ()
        keys = EVENT_T.keys ()
        for k in keys :
            table_print ("/Experiment_g/Sorts_g/{0}".format (k), EVENT_T[k])
    elif ALL_EVENTS != False :
        read_all_event_table ()
        keys = EVENT_T.keys ()
        for k in keys :
            table_print ("/Experiment_g/Sorts_g/{0}".format (k), EVENT_T[k])        
        
    if INDEX_TABLE :
        read_index_table ()
        table_print ("/Experiment_g/Receivers_g/Index_t", INDEX_T)
        
    if M_INDEX_TABLE :
        read_m_index_table ()
        table_print ("/Experiment_g/Maps_g/Index_t", M_INDEX_T)
        
    if TIME_TABLE :
        read_time_table ()
        table_print ("/Experiment_g/Receivers_g/Time_t", TIME_T)
        
    if ARRAY_TABLE :
        if not SORT_T :
            read_sort_table ()
            
        read_sort_arrays ()
        arrays = ARRAY_T.keys ()
        for a in arrays :
            n = int (string.split (a, '_')[2])
            if n == int (ARRAY_TABLE) :
                table_print ("/Experiment_g/Sorts_g/" + a, ARRAY_T[a])
    elif ALL_ARRAYS :
        if not SORT_T :
            read_sort_table ()
            
        read_sort_arrays ()
        arrays = ARRAY_T.keys ()
        for a in arrays :
            table_print ("/Experiment_g/Sorts_g/" + a, ARRAY_T[a])        
        
    if RESPONSE_TABLE :
        read_response_table ()
        table_print ("/Experiment_g/Responses_g/Response_t", RESPONSE_T)
        
    if REPORT_TABLE :
        read_report_table ()
        table_print ("/Experiment_g/Reports_g/Report_t", REPORT_T)
        
    if RECEIVER_TABLE :
        read_receiver_table ()
        table_print ("/Experiment_g/Receivers_g/Receiver_t", RECEIVER_T)
        
    if DAS_TABLE :
        read_receivers (DAS_TABLE)
        dass = DAS_T.keys ()
        for d in dass :
            table_print ("/Experiment_g/Receivers_g/Das_g_" + d + "/Das_t", DAS_T[d])
        
    EX.ph5close ()

        
if __name__ == '__main__' :
    main()
