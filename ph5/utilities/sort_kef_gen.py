#!/usr/bin/env pnpython3
#
#   Program to generate /Experiment_g/Sorts_g/Sort_t entries
#
#   Steve Azevedo, July 2007
#
import sys, os, os.path, time, math
#   This provides the base functionality
from ph5.core import experiment

PROG_VERSION = "2016.334"

#   Make sure we are all on the same time zone ;^)
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

#
#   Read Command line arguments
#
def get_args () :
    global PH5, PATH, DEBUG, SN, AUTO
    
    from optparse import OptionParser
    
    oparser = OptionParser ()
    
    oparser.usage = "sort-kef-gen --nickname ph5-file-prefix --serial-number DAS-SN | --auto [--path path-to-ph5-files]"
    
    oparser.description = "Version: {0} Generate a kef file to populate Sort_t.".format (PROG_VERSION)
    
    oparser.add_option ("-n", "--nickname", dest = "ph5_file_prefix",
                        help = "The ph5 file prefix (experiment nickname).",
                        metavar = "ph5_file_prefix")
    
    oparser.add_option ("-p", "--path", dest = "ph5_path",
                        help = "Path to ph5 files. Defaults to current directory.",
                        metavar = "ph5_path")
    
    oparser.add_option ("-s", "--serial-number", dest = "sn",
                        help = "DAS to use to get windows.",
                        metavar = "sn")
    
    oparser.add_option ("-a", "--auto", dest = "auto",
                        help = "Attempt to auto detect windows. Windows should start at the same time on all DASs.",
                        action = "store_true", default = False,
                        metavar = "auto")
    
    oparser.add_option ("-d", dest = "debug", action = "store_true", default = False)
    
    options, args = oparser.parse_args ()
    
    if options.ph5_file_prefix != None :
        PH5 = options.ph5_file_prefix
    else :
        PH5 = None
        
    if options.ph5_path != None :
        PATH = options.ph5_path
    else :
        PATH = "."
        
    SN = options.sn
    
    AUTO = options.auto
        
    if options.debug != None :
        DEBUG = options.debug
        
    if PH5 == None or (SN == None and AUTO == False) :
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
    
#   XXX   Not used  
def read_sort_table () :
    '''   Read /Experiment_t/Sorts_g/Sort_g   '''
    global EX, SORT_T
    
    sorts, sorts_keys = EX.ph5_g_sorts.read_sorts ()
    
    if sorts == None : return False
    
    rowskeys = Rows_Keys (sorts, sorts_keys)
    
    SORT_T = rowskeys
    
    return True

def get_sample_count (g, a) :
    global EX
    
    EX.ph5_g_receivers.setcurrent (g)
    
    try :
        node = EX.ph5_g_receivers.find_trace_ref (a)
    except Exception as e :
        sys.stderr.write ("Warning: Couldn't count samples in data array. {0}".format (e))
        return None
    
    return node.nrows
    
def read_das_table (das) :
    global EX, DAS_T
    
    das_group = EX.ph5_g_receivers.getdas_g (das)
    
    if das_group == None : return False
    
    EX.ph5_g_receivers.setcurrent (das_group)
    
    r, k = EX.ph5_g_receivers.read_das ()
    
    if r == None : return False
    
    R = []
    #   Get sample count for this array
    for r0 in r :
        data_array_name = r0['array_name_data_a']
        #samples = get_sample_count (das_group, data_array_name)
        r0['samples'] = r0['sample_count_i']
        R.append (r0)
        
    k.append ('samples')
    DAS_T = Rows_Keys (R, k)
    
    return True

def read_all_das () :
    '''   Read all das tables and create a DAS_T that contains all
          of the windows.
    '''
    global EX, DAS_T
    
    rows = {}
    #   Get all of the das groups
    dasGroups = EX.ph5_g_receivers.alldas_g ()
    #   For each das
    dass = dasGroups.keys ()
    if not dass : return False
    
    for das in dass :
        #   Set the current group
        das_group = dasGroups[das]
        EX.ph5_g_receivers.setcurrent (das_group)
        #   Read the das table for this das
        r, k = EX.ph5_g_receivers.read_das ()
        
        if r == None or k == None : continue
        
        R = []
        #   Get sample count for this array by counting the array
        for r0 in r :
            if r0['channel_number_i'] != 1 : continue   #   Exclude all but channel 1
            #data_array_name = r0['array_name_data_a']
            #samples = get_sample_count (das_group, data_array_name)
            #   If for some reason counting the number of samples in an array fails use value from Das_t
            #if samples == None :
            samples = r0['sample_count_i']
            r0['time/epoch_f'] = float (r0['time/epoch_l']) + (float (r0['time/micro_seconds_i']) / 1000000.)
            r0['samples'] = samples;
            r0['das'] = das
            R.append (r0)
            
        k.append ('samples')
        
        #   Create a dictionary of rows keyed by start epoch
        #   This should contain all of the recording windows
        for r in R :
            rows[r['time/epoch_l']] = r
            
    #   Sort by start time epoch
    epochs = rows.keys ()
    epochs.sort ()
    #   Get the rows list back
    row = []
    for e in epochs :
        row.append (rows[e])
        
    #   Set DAS_T
    DAS_T = Rows_Keys (row, k)
    
    return True
        
#   XXX   Not used
def get_arrays () :
    global SORT_T
    
    KV = {}
    
    for s in SORT_T.rows :
        KV[s['array_name_s']] = s['array_t_name_s']
        
    return KV

def first_last (array_t) :
    mmax = 0; mmin = sys.maxint
    for a in array_t :
        array_pickup = a['pickup_time/epoch_l']
        array_deploy = a['deploy_time/epoch_l']
        if array_deploy < mmin : mmin = array_deploy
        if array_pickup > mmax : mmax = array_pickup
        
    if mmax == 0 : mmax = sys.maxint
    return mmin, mmax

def report_gin () :
    global DAS_T, EX
    
    PH5_VERSION = EX.version ()
    
    ar = EX.ph5_g_sorts.names ()
    
    if ar == [] :
        sys.stderr.write ("Warning: No sort arrays (Array_t_xxx) defined! Can not produce sort table.\n")
        return
    
    now = time.time ()
    print "#   sort-kef-gen Version: %s ph5 Version: %s" % (PROG_VERSION, PH5_VERSION)
    r = 1
    #   XXX   This assumes that the arrays were deployed for the same recording windows.   XXX
    for a in ar :
        array_t, k = EX.ph5_g_sorts.read_arrays (a)
        array_deploy, array_pickup = first_last (array_t)
        if len (DAS_T.rows) < 1 :
            sys.stderr.write ("Warning: Failed to read any DAS information!\n")

        for d in DAS_T.rows :
            #   Skip everything but channel 1
            if d['channel_number_i'] != 1 : continue
            t0 = d['time/epoch_l'] + (d['time/micro_seconds_i'] / 1000000)
            l = d['samples'] / d['sample_rate_i']
            t1 = t0 + l
            (float_part, int_part) = math.modf (t1)
            if array_deploy <= d['time/epoch_l'] and array_pickup >= int_part :
                #
                print "#   row {0} das {1}\n/Experiment_g/Sorts_g/Sort_t".format (r, d['das'])
                print "\tarray_name_s = %s" % a[-3:]
                print "\tarray_t_name_s = %s" % a
                print "\tdescription_s = Recording window %04d" % d['event_number_i']
                print "\tstart_time/epoch_l = %d" % d['time/epoch_l']
                print "\tstart_time/micro_seconds_i = %d" % d['time/micro_seconds_i']
                print "\tstart_time/type_s = %s" % d['time/type_s']
                print "\tstart_time/ascii_s = %s" % d['time/ascii_s']
                print "\tend_time/epoch_l = %d" % int_part
                print "\tend_time/micro_seconds_i = %d" % (float_part * 1000000.0)
                print "\tend_time/ascii_s = %s" % time.ctime (t1)
                print "\tend_time/type_s = BOTH"
                print "\ttime_stamp/epoch_l = %d" % now
                print "\ttime_stamp/ascii_s = %s" % time.ctime (now)
                print "\ttime_stamp/micro_seconds_i = 0"
                print "\ttime_stamp/type_s = BOTH"
                r += 1
            #else :
                #sys.stderr.write ("#Warning: DAS {0} time outside of deploy pickup times!\n")
                #sys.stderr.write ("#\tArray: {0} Deploy: {1} Pickup: {2}\n".format (a, array_deploy, array_pickup))
                #sys.stderr.write ("#DAS: {0} Deploy: {1} Pickup: {2}\n".format (array_t['das/serial_number_s'], d['time/epoch_l'], int_part))


def main():
    global SN, EX, AUTO
    
    get_args ()
    initialize_ph5 ()
    '''
    if not read_sort_table () :
        sys.stderr.write ("Failed to read /Experiment_g/Sorts_g/Sort_t\n")
        sys.exit ()
    '''
    if SN != None :
        if not read_das_table (SN) :
            sys.stderr.write ("Failed to read Das_t for %s.\n" % SN)
            sys.exit ()
            
    elif AUTO == True :
        if not read_all_das () :
            sys.stderr.write ("Failed to read DAS tables.")
            sys.exit ()
        
    report_gin ()
        
    EX.ph5close ()


if __name__ == "__main__" :
    main()
