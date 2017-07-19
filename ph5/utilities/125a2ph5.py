#!/usr/bin/env pnpython3

#
#   Read rt-125 or rt-125a files and convert to ph5.
#
#   Steve Azevedo, Sept 2006, July 2012
#

import tables, sys, os, os.path, string, time, math, re, logging
from ph5.core import columns, experiment, kef, pn125, timedoy

PROG_VERSION = '2016.200 Developmental'
MAX_PH5_BYTES = 1073741824 * 2   #   GB (1024 X 1024 X 1024 X 2)
#MAX_PH5_BYTES = 1024 * 1024 * 2   #   2MB (1024 X 1024 X 2)
INDEX_T = None

TRDfileRE = re.compile (".*[Ii](\d\d\d\d)[Rr][Aa][Ww].*")
TRDfileREpunt = re.compile (".*(\d\d\d\d).*[Tt][Rr][Dd]$")
miniPH5RE = re.compile (".*miniPH5_(\d\d\d\d\d)\.ph5")

CURRENT_DAS = None
DAS_INFO = {}
#   Current raw file processing
F = None

os.environ['TZ'] = 'GMT'
time.tzset ()

#
#   To hold table rows and keys
#
class Rows_Keys (object) :
    __slots__ = ('rows', 'keys')
    def __init__ (self, rows = [], keys = None) :
        self.rows = rows
        self.keys = keys
        
    def set (self, rows = None, keys = None) :
        if rows != None : self.rows = rows
        if keys != None : self.keys = keys

class Index_t_Info (object) :
    __slots__ = ('das', 'ph5file', 'ph5path', 'startepoch', 'stopepoch')
    def __init__ (self, das, ph5file, ph5path, startepoch, stopepoch) :
        self.das        = das
        self.ph5file    = ph5file
        self.ph5path    = ph5path
        self.startepoch = startepoch
        self.stopepoch  = stopepoch
        
class Resp (object) :
    __slots__ = ('lines', 'keys', 't')
    def __init__ (self, t) :
        self.t = t
        self.update ()
        
    def update (self) :
        self.lines, self.keys = self.t.read_responses ()
        
    def match (self, bw, gain) :
        #print self.lines
        for l in self.lines :
            if l['bit_weight/value_d'] == bw and l['gain/value_i'] == gain :
                return l['n_i']
            
        return -1
    
    def next_i (self) :
        return len (self.lines)
        
def read_infile (infile) :
    global FILES
    try :
        fh = file (infile)
    except :
        sys.stderr.write ("Warning: Failed to open %s\n" % infile)
        return
        
    while 1 :
        line = fh.readline ()
        if not line : break
        line = string.strip (line)
        if not line : continue
        if line[0] == '#' : continue
        FILES.append (line)
        
def read_windows_file (f) :
    '''   Window start time   Window length
          YYYY:JJJ:HH:MM:SS   SSSS   '''
    w = []
    try :
        fh = open (f)
    except :
        return w
    
    #tdoy = TimeDoy.TimeDoy ()
    while 1 :
        line = fh.readline ()
        if not line : break
        line = line.strip ()
        if not line or line[0] == '#' : continue
        flds = line.split ()
        if len (flds) != 2 :
            sys.stderr.write ("Error in window file: %s\n" % line)
            continue
        
        ttuple = flds[0].split (':')
        if len (ttuple) != 5 :
            sys.stderr.write ("Error in window file: %s\n" % flds[0])
            continue
        
        try :
            tDOY = timedoy.TimeDOY (year=ttuple[0], 
                                    month=None, 
                                    day=None, 
                                    hour=ttuple[2], 
                                    minute=ttuple[3], 
                                    second=ttuple[4], 
                                    microsecond=0, 
                                    doy=ttuple[1], 
                                    epoch=None)
            #mo, da = tdoy.getMonthDay (int (ttuple[0]), int (ttuple[1]))
            #print flds[0], mo, da
            #start_secs = time.mktime ((int (ttuple[0]),   #   Year
                                       #mo,                #   Month
                                       #da,                #   Day
                                       #int (ttuple[2]),   #   Hour
                                       #int (ttuple[3]),   #   Minute
                                       #int (ttuple[4]),   #   Seconds
                                       #-1,                #   Weekday
                                       #int (ttuple[1]),   #   Day of year
                                       #0))                #   DST 
            
            #start_secs = int (start_secs)
            start_secs = tDOY.epoch ()
            stop_secs = int (flds[1]) + start_secs
        except Exception, e :
            sys.stderr.write ("Error in window file: %s\n" % line)
            sys.stderr.write ("%s" % e)
            continue
        
        w.append ([start_secs, stop_secs])
        
    return w

def get_args () :
    ''' Parse input args
           -r   raw file
           -f   file containing list of raw files
           -n   output file
           -k   kef file   #   REMOVED
           -d   dep file   #   REMOVED
           -p   print out table list
           -M   create a specific number of miniPH5 files
           -S   First index of miniPH5_xxxxx.ph5
    '''
    global FILES, PH5, SR, WINDOWS, OVERIDE, NUM_MINI, FIRST_MINI
    
    from optparse import OptionParser

    oparser = OptionParser ()
    oparser.usage = "Version %s 125a2ph5 [--help][--raw raw_file | --file file_list_file] --nickname output_file_prefix" % PROG_VERSION
    oparser.description = "Read a raw texan files and optionally a kef file into ph5 format."
    oparser.add_option ("-r", "--raw", dest = "rawfile",
                        help="RT-125(a) texan raw file", metavar="raw_file")
    oparser.add_option ("-f", "--file", dest = "infile",
                       help = "File containing list of RT-125(a) raw file names.",
                       metavar = "file_list_file")
    oparser.add_option ("-o", "--overide", dest = "overide",
                        help = "Overide file name checks.", 
                        action = "store_true", default = False)
    oparser.add_option ("-n", "--nickname", dest = "outfile",
                        help="The ph5 file prefix (experiment nick name).",
                        metavar = "output_file_prefix")
    oparser.add_option ("-M", "--num_mini", dest = "num_mini",
                        help = "Create a given number of miniPH5_xxxxx.ph5 files.",
                        metavar = "num_mini", type = 'int', default = None)
    oparser.add_option ("-S", "--first_mini", dest = "first_mini",
                        help = "The index of the first miniPH5_xxxxx.ph5 file.",
                        metavar = "first_mini", type = 'int', default = 1)
    #oparser.add_option ("-d", "--dep", dest = "depfile",
                        #help = "Rawmeet dep file.",
                        #metavar = "dep_file")
    oparser.add_option ("-s", "--samplerate", dest = "samplerate",
                        help = "Extract only data at given sample rate.",
                        metavar = "samplerate")
    oparser.add_option ("-w", "--windows_file", dest = "windows_file",
                        help = "File containing list of time windows to process.\n\
                        Window start time   Window length, seconds\n\
                        -----------------   ----\n\
                        YYYY:JJJ:HH:MM:SS   SSSS",
                        metavar = "windows_file")
    oparser.add_option ("-p", dest = "doprint", action = "store_true", default = False)
    options, args = oparser.parse_args()
    #print options.outfile
    
    FILES = []
    PH5 = None 
    KEFFILE = None
    DEPFILE = None
    OVERIDE = options.overide
    SR = options.samplerate
    NUM_MINI = options.num_mini
    FIRST_MINI = options.first_mini
    
    if options.infile != None :
        read_infile (options.infile)
        
    elif options.rawfile != None :
        FILES.append (options.rawfile)
        
    if options.outfile != None :
        PH5 = options.outfile

    if options.doprint != False :
        ex = experiment.ExperimentGroup ()
        ex.ph5open (True)
        ex.initgroup ()
        keys (ex)
        ex.ph5close ()
        sys.exit ()
        
    #if options.keffile != None :
        #KEFFILE = options.keffile
        
    #if options.depfile != None :
        #DEPFILE = options.depfile
        
    if options.windows_file != None :
        WINDOWS = read_windows_file (options.windows_file)
    else :
        WINDOWS = None

    if PH5 == None :
        #print H5, FILES
        sys.stderr.write ("Error: Missing required option. Try --help\n")
        sys.exit ()
        
    if not os.path.exists (PH5) and not os.path.exists (PH5 + '.ph5') :
        sys.stderr.write ("Error: %s does not exist!\n" % PH5)
        sys.exit ()
            
    else :
        #   Set up logging
        #if not os.path.exists (OUTPATH) :
            #os.mkdir (OUTPATH)
            
        logging.basicConfig (
            filename = os.path.join ('.', "125a2ph5.log"),
            format = "%(asctime)s %(message)s",
            level = logging.INFO
        )
        
def print_it (a) :
    #a.sort ()
    for k in a : print "\t" + k
        
def keys (ex) :
    #   Under Experiment_g/Experiment_t
    experiment_table, j = columns.keys (ex.ph5_t_experiment)              #
    #   Under Experiment_g/Sorts_g/Sort_t
    sort_table, j = columns.keys (ex.ph5_g_sorts.ph5_t_sort)              #
    ex.ph5_g_sorts.newSort ('001')
    #   Under Experiment_g/Sorts_g/Array_t
    k = ex.ph5_g_sorts_ph5_t_array.keys ()
    if k :
        sort_array_table, j = columns.keys (ex.ph5_g_sorts.ph5_t_array[k[0]])       #
    #   Under Experiment_g/Sorts_g/Offset_t
    k = ex.ph5_g_sorts.ph5_t_offset.keys ()
    if k :
        sort_offset_table, j = columns.keys (ex.ph5_g_sorts.ph5_t_offset[k[0]])     #
    #   Under Experiment_g/Sorts_g/Event_t
    k = ex.ph5_g_sorts.ph5_t_event.keys ()
    if k :
        sort_event_table, j = columns.keys (ex.ph5_g_sorts.ph5_t_event[k[0]])       #
    #
    ex.ph5_g_receivers.newdas ('9999')
    g = ex.ph5_g_receivers.getdas_g ('9999')
    #   Under Experiment_g/Receivers_g/Das_g_9999/Das_t
    das_table, j = columns.keys (g.Das_t)                                 #
    #   Under Experiment_g/Receivers_g/das_g_9999/Receiver_t
    receiver_table, j = columns.keys (g.Receiver_t)                       #
    time_table, j = columns.keys (g.Time_t)
    #   Under Experiment_g/Reports_g/[title]/
    report_table, j = columns.keys (ex.ph5_g_reports.ph5_t_report)
    #   Under Experiment_g/Responses_g/Responses_t
    response_table, j = columns.keys (ex.ph5_g_responses.ph5_t_response)
    
    print "\t\t\t\t\t\t\t\tPH5 TABLE KEYS\n"
    
    print "/Experiment_g/Experiment_t"
    print_it (experiment_table)
    
    print "/Experiment_g/Receivers_g/Das_g_[sn]/Das_t"
    print_it (das_table)
    
    print "/Experiment_g/Receivers_g/Das_g_[sn]/Receiver_t"
    print_it (receiver_table)
    
    print "/Experiment_g/Receivers_g/Das_g_[sn]/Time_t"
    print_it (time_table)
    
    print "/Experiment_g/Sorts_g/Sort_t"
    print_it (sort_table)
    
    print "/Experiment_g/Sorts_g/Array_t_[nnn]"
    print_it (sort_array_table)
    
    print "/Experiment_g/Sorts_g/Offset_t"
    print_it (sort_offset_table)
    
    print "/Experiment_g/Sorts_g/Event_t"
    print_it (sort_event_table)
    
    print "/Experiment_g/Reports_g/Report_t"
    print_it (report_table)
    
    print "/Experiment_g/Responses_g/Response_t"
    print_it (response_table)
    
def initializeExperiment () :
    global EX, PH5
    
    EX = experiment.ExperimentGroup (nickname = PH5)
    EDIT = True
    EX.ph5open (EDIT)
    EX.initgroup ()
    
def populateExperimentTable () :
    global EX, KEFFILE
    k = kef.Kef (KEFFILE)
    k.open ()
    k.read ()
    k.batch_update ()
    k.close ()
    
def closePH5 () :
    global EX
    EX.ph5close ()
    
#def writeReceiver_t (page) :
    #global EX
    #p_receiver_t = {}
    
    #das_number = str (page.unitID)
    #das_g, das_t, receiver_t, time_t = EX.ph5_g_receivers.newdas (das_number)
    
    #p_receiver_t['orientation/azimuth/units_s'] = 'degrees'
    #p_receiver_t['orientation/azimuth/value_f'] = 0.0
    #p_receiver_t['orientation/dip/units_s'] = 'degrees'
    #p_receiver_t['orientation/dip/value_f'] = -90.0
    #p_receiver_t['orientation/description_s'] = 'Z'
    #EX.ph5_g_receivers.populateReceiver_t (p_receiver_t)
    
    #p_receiver_t['orientation/azimuth/units_s'] = 'degrees'
    #p_receiver_t['orientation/azimuth/value_f'] = 0.0
    #p_receiver_t['orientation/dip/units_s'] = 'degrees'
    #p_receiver_t['orientation/dip/value_f'] = 0.0
    #p_receiver_t['orientation/description_s'] = 'N'
    #EX.ph5_g_receivers.populateReceiver_t (p_receiver_t)
    
    #p_receiver_t['orientation/azimuth/units_s'] = 'degrees'
    #p_receiver_t['orientation/azimuth/value_f'] = 90.0
    #p_receiver_t['orientation/dip/units_s'] = 'degrees'
    #p_receiver_t['orientation/dip/value_f'] = 0.0
    #p_receiver_t['orientation/description_s'] = 'E'
    #EX.ph5_g_receivers.populateReceiver_t (p_receiver_t)
    
def window_contained (e) :
    '''   Is this event in the data we want to keep?   '''
    global WINDOWS
    
    #   We want to keep all the data
    if WINDOWS == None :
        return True
    
    if not e :
        return False
    
    #tdoy = TimeDoy.TimeDoy ()
    sample_rate = e.sampleRate
    sample_count = e.sampleCount
    tDOY = timedoy.TimeDOY (year=e.year,
                            month=None, 
                            day=None, 
                            hour=e.hour, 
                            minute=e.minute, 
                            second= int (e.seconds), 
                            microsecond=0, 
                            doy=e.doy, 
                            epoch=None)
    #mo, da = tdoy.getMonthDay (e.year, e.doy)
    #event_start_epoch = time.mktime ((e.year,
                                      #mo,
                                      #da,
                                      #e.hour,
                                      #e.minute,
                                      #int (e.seconds),
                                      #-1,
                                      #e.doy,
                                      #0))
                                      
    event_start_epoch = tDOY.epoch ()
    event_stop_epoch = int ((float (sample_count) / float (sample_rate)) + event_start_epoch)
    
    for w in WINDOWS :
        window_start_epoch = w[0]
        window_stop_epoch = w[1]
        
        #   Window start in event KEEP
        if event_start_epoch <= window_start_epoch and event_stop_epoch >= window_start_epoch :
            return True
        #   Entire event in window KEEP
        if event_start_epoch >= window_start_epoch and event_stop_epoch <= window_stop_epoch :
            return True
        #   Event stop in window KEEP
        if event_start_epoch <= window_stop_epoch and event_stop_epoch >= window_stop_epoch :
            return True
        
    return False

def update_index_t_info (starttime, samples, sps) :
    global DAS_INFO
    #tdoy = timedoy.TimeDOY ()
    ph5file = EXREC.filename
    ph5path = '/Experiment_g/Receivers_g/' + EXREC.ph5_g_receivers.current_g_das._v_name
    das = ph5path[32:]
    stoptime = starttime + (float (samples) / float (sps))
    di = Index_t_Info (das, ph5file, ph5path, starttime, stoptime)
    if not DAS_INFO.has_key (das) :
        DAS_INFO[das] = []
        
    DAS_INFO[das].append (di)
    logging.info ("DAS: {0} File: {1} First Sample: {2} Last Sample: {3}".format (das, ph5file, time.ctime (starttime), time.ctime (stoptime)))
    #startms, startsecs = math.modf (starttime)
    #startms = int (startms * 1000.); startsecs = int (startsecs)
    #stopms, stopsecs = math.modf (stoptime)
    #stopms = int (stopms * 1000.); stopsecs = int (stopsecs)
    #ptimestart = tdoy.epoch2PasscalTime (startsecs, startms)
    #ptimestop  = tdoy.epoch2PasscalTime (stopsecs, stopms)
    #print ph5file, ph5path, ptimestart, ptimestop
    
def writeEvent (trace, page) :
    global EX, EXREC, RESP, SR
    p_das_t = {}
    p_response_t = {}

    if SR != None :
        if trace.sampleRate != int (SR) :
            return
    
    das_number = str (page.unitID)
    
    #   The gain and bit weight
    p_response_t['gain/value_i'] = trace.gain
    p_response_t['bit_weight/units_s'] = 'volts/count'
    p_response_t['bit_weight/value_d'] = 10.0 / trace.gain / trace.fsd 
    
    n_i = RESP.match (p_response_t['bit_weight/value_d'], p_response_t['gain/value_i'])
    if n_i < 0 :
        n_i = RESP.next_i ()
        p_response_t['n_i'] = n_i
        EX.ph5_g_responses.populateResponse_t (p_response_t)
        RESP.update ()
    
    #   Check to see if group exists for this das, if not build it
    das_g, das_t, receiver_t, time_t = EXREC.ph5_g_receivers.newdas (das_number)
    #   Fill in das_t
    p_das_t['raw_file_name_s'] = os.path.basename (F)
    p_das_t['array_name_SOH_a'] = EXREC.ph5_g_receivers.nextarray ('SOH_a_')
    p_das_t['response_table_n_i'] = n_i
    p_das_t['channel_number_i'] = trace.channel_number
    p_das_t['event_number_i'] = trace.event
    p_das_t['sample_count_i'] = trace.sampleCount
    p_das_t['sample_rate_i'] = trace.sampleRate
    p_das_t['sample_rate_multiplier_i'] = 1
    p_das_t['stream_number_i'] = trace.stream_number
    #tdoy = timedoy.TimeDOY ()
    #mo, da = tdoy.getMonthDay (trace.year, trace.doy)
    #p_das_t['time/epoch_l'] = int (time.mktime ((trace.year, mo, da, trace.hour, trace.minute, int (trace.seconds), -1, trace.doy, 0)))
    tDOY = timedoy.TimeDOY (year=trace.year, 
                            month=None, 
                            day=None, 
                            hour=trace.hour, 
                            minute=trace.minute, 
                            second=int (trace.seconds), 
                            microsecond=0, 
                            doy=trace.doy, 
                            epoch=None)
    
    p_das_t['time/epoch_l'] = tDOY.epoch ()
    #   XXX   need to cross check here   XXX
    p_das_t['time/ascii_s'] = time.asctime (time.gmtime (p_das_t['time/epoch_l']))
    p_das_t['time/type_s'] = 'BOTH'
    #   XXX   Should this get set????   XXX
    p_das_t['time/micro_seconds_i'] = 0
    #   XXX   Need to check if array name exists and generate unique name.   XXX
    p_das_t['array_name_data_a'] = EXREC.ph5_g_receivers.nextarray ('Data_a_')
    des = "Epoch: " + str (p_das_t['time/epoch_l']) + " Channel: " + str (trace.channel_number)
    #   XXX   This should be changed to handle exceptions   XXX
    EXREC.ph5_g_receivers.populateDas_t (p_das_t)
    #   Write out array data (it would be nice if we had int24) we use int32!
    EXREC.ph5_g_receivers.newarray (p_das_t['array_name_data_a'], trace.trace, dtype = 'int32', description = des)
    update_index_t_info (p_das_t['time/epoch_l'] + (float (p_das_t['time/micro_seconds_i']) / 1000000.), p_das_t['sample_count_i'], p_das_t['sample_rate_i'] / p_das_t['sample_rate_multiplier_i'])
    
def writeSOH (soh) :
    global EXREC
    
    #   Check to see if any data has been written
    if EXREC.ph5_g_receivers.current_g_das == None or EXREC.ph5_g_receivers.current_t_das == None :
        return
    
    name = EXREC.ph5_g_receivers.nextarray ('SOH_a_')
    data = []
    for el in soh :
        line = "%04d:%03d:%02d:%02d:%4.2f -- %s" % (el.year, el.doy, el.hour, el.minute, el.seconds, el.message)
        data.append (line)
        
    EXREC.ph5_g_receivers.newarray (name, data, description = "Texan State of Health")
    
def writeET (et) :
    '''   '''
    global EXREC
    
    #   Check to see if any data has been written
    if EXREC.ph5_g_receivers.current_g_das == None or EXREC.ph5_g_receivers.current_t_das == None :
        return    
    
    name = EXREC.ph5_g_receivers.nextarray ('Event_a_')
    data = []
    for el in et :
        line = "%04d:%03d:%02d:%02d:%02d %d %d" % (el.year, el.doy, el.hour, el.minute, el.seconds, el.action, el.parameter)
        data.append (line)
        
    EXREC.ph5_g_receivers.newarray (name, data, description = "Texan Event Table")
    
def openPH5 (filename) :
    #sys.stderr.write ("***   Opening: {0} ".format (filename))
    exrec = experiment.ExperimentGroup (nickname = filename)
    exrec.ph5open (True)
    exrec.initgroup ()
    return exrec    
    
def get_current_data_only (size_of_data, das = None) :
    '''   Return opened file handle for data only PH5 file that will be
          less than MAX_PH5_BYTES after raw data is added to it.
    '''
    #global NM
    #global INDEX_T, CURRENT_DAS
    def sstripp (s) :
        s = s.replace ('.ph5', '')
        s = s.replace ('./', '')
        return s
    
    def smallest () :
        '''   Return the name of the smallest miniPH5_xxxxx.ph5   '''
        minifiles = filter (miniPH5RE.match, os.listdir ('.'))
        
        tiny = minifiles[0]
        for f in minifiles :
            if os.path.getsize (f) < os.path.getsize (tiny) :
                tiny = f
                
        return tiny
            
    das = str (CURRENT_DAS)
    newest = 0
    newestfile = ''
    #   Get the most recent data only PH5 file or match DAS serialnumber
    n = 0
    for index_t in INDEX_T.rows :
        #   This DAS already exists in a ph5 file
        if index_t['serial_number_s'] == das :
            newestfile = sstripp (index_t['external_file_name_s'])
            return openPH5 (newestfile) 
        #   miniPH5_xxxxx.ph5 with largest xxxxx
        mh = miniPH5RE.match (index_t['external_file_name_s'])
        if n < int (mh.groups ()[0]) :
            newestfile = sstripp (index_t['external_file_name_s'])
            n = int (mh.groups ()[0])
            
    if not newestfile :
        #   This is the first file added
        return openPH5 ('miniPH5_{0:05d}'.format (FIRST_MINI))
    
    size_of_exrec = os.path.getsize (newestfile + '.ph5')
    #print size_of_data, size_of_exrec, size_of_data + size_of_exrec, MAX_PH5_BYTES
    if NUM_MINI != None :
        fm = FIRST_MINI - 1
        if (int (newestfile[8:13]) - fm)  < NUM_MINI :
            newestfile = "miniPH5_{0:05d}".format (int (newestfile[8:13]) + 1)
        else :
            small = sstripp (smallest ())
            return openPH5 (small)
        
    elif (size_of_data + size_of_exrec) > MAX_PH5_BYTES :
        newestfile = "miniPH5_{0:05d}".format (int (newestfile[8:13]) + 1)

    return openPH5 (newestfile)

def writeINDEX () :
    global DAS_INFO, INDEX_T
    
    dass = DAS_INFO.keys ()
    dass.sort ()
    
    for das in dass :
        i = {}
        start = sys.maxint
        stop = 0.        
        das_info = DAS_INFO[das]
        for d in das_info :
            i['external_file_name_s'] = d.ph5file
            i['hdf5_path_s'] = d.ph5path
            i['serial_number_s'] = das
            if d.startepoch < start :
                start = d.startepoch
                
            if d.stopepoch > stop :
                stop = d.stopepoch
                
        i['time_stamp/epoch_l'] = int (time.time ())
        i['time_stamp/micro_seconds_i'] = 0
        i['time_stamp/type_s'] = 'BOTH'
        i['time_stamp/ascii_s'] = time.ctime (i['time_stamp/epoch_l'])
        
        i['start_time/epoch_l'] = int (math.modf (start)[1])
        i['start_time/micro_seconds_i'] = int (math.modf (start)[0] * 1000000)
        i['start_time/type_s'] = 'BOTH'
        i['start_time/ascii_s'] = time.ctime (start)
        
        i['end_time/epoch_l'] = math.modf (stop)[1]
        i['end_time/micro_seconds_i'] = int (math.modf (stop)[0] * 1000000)
        i['end_time/type_s'] = 'BOTH'
        i['end_time/ascii_s'] = time.ctime (stop)
                
        EX.ph5_g_receivers.populateIndex_t (i)
            
    rows, keys = EX.ph5_g_receivers.read_index ()
    INDEX_T = Rows_Keys (rows, keys)
    
    DAS_INFO = {}
        
def updatePH5 (f) :
    global EX, EXREC
    #sys.stdout.write ("Processing: %s %s =" % (f, CURRENT_DAS))
    sys.stdout.write (":<Processing>: %s\n" % (f)); sys.stdout.flush ()
    logging.info ("Processing: %s..." % f)
    size_of_data = os.path.getsize (f) * 1.250
    try :
        EXREC.ph5close ()
    except :
        pass
    
    EXREC = get_current_data_only (size_of_data)
    pn = pn125.pn125 (f)
    i = -1
    while 1 :
        #i = i + 1
        try :
            points = pn.getEvent ()
        except pn125.TRDError, e :
            sys.stderr.write ("\nTRD read error. {0}".format (e))
            sys.stdout.write (":<Error>: {0}\n".format (f)); sys.stdout.flush ()
            break
            
        if points == 0 : break
        #if i % 2 == 0 :
            #sys.stdout.write ("\b-"); sys.stdout.flush ()
        #else :
            #sys.stdout.write ("\b="); sys.stdout.flush ()
        
        if window_contained (pn.trace) :
            writeEvent (pn.trace, pn.page)
            
        #if i == 0 :
            #writeReceiver_t (pn.page)
            
    if DAS_INFO :
        writeINDEX ()
    
    if len (pn.sohbuf) > 0 :
        writeSOH (pn.sohbuf)
        
    if len (pn.eventTable) > 0 :
        writeET (pn.eventTable)
    
    #ph5flush ()
    #sys.stdout.write (" done\n")
    sys.stdout.write (":<Finished>: {0}\n".format (f)); sys.stdout.flush ()
    
def ph5flush () :
    global EX
    EX.ph5flush ()
    
#def dep_update () :
    #global EX, DEPFILE
    
    #dp = Dep.Dep (DEPFILE)
    #dp.open ()
    #dp.read ()
    #dp.rewindReceiver ()
    #dp.rewindShot ()
    #dp.rewindTime ()
    
    ##   Populate shot table Event_t  
    ##print "Event_t"
    #while 1 :
        #p = dp.nextShot ()
        #if not p : break
        #b = dp._build (p)
        #b = b['Event_t']
        #EX.ph5_g_sorts.populateEvent_t (b)
    
    ##self.rewindShot ()
    #current_array = None
    #ref = None
    ##   Populate Sort_t and Array_t tables
    ##   XXX   Assumes that Line designation is grouped together in dep file   XXX
    #while 1 :
        #p = dp.nextReceiver ()
        #if not p : break
        #b = dp._build (p)
        
        #tmp = p['R_array']   #   p['R_line']
        ##   
        #if tmp != current_array :
            #current_array = tmp
            #next = EX.ph5_g_sorts.nextName ()
            #ref = EX.ph5_g_sorts.newSort (next)
            ##s = b['Sort_t']
            ##s['array_t_name_s'] = next
            ##print "Sort_t"
            ##EX.ph5_g_sorts.populateSort_t (s)
          
        #a = b['Array_t']
        ##print "Array_t"
        #EX.ph5_g_sorts.populateArray_t (a)
        
    ##   Process TIME from dep    
    #while 1 :
        #p = dp.nextTime ()
        #if not p : break
        #try :
            #filename = p['T_file']
            #das = str (int (filename[1:5]) + 10000)
        #except :
            #sys.stderr.write ("Warning: Can't update Time_t. Unuseable filename from TIME section of dep file.\n")
            #continue
            
        #if EX.ph5_g_receivers.getdas_g (das) :
            #b = dp._build (p)
            #EX.ph5_g_receivers.populateTime_t (b['Time_t'])
        #else :
            #sys.stderr.write ("Warning: No data for %s\n" % das)
        
def update_external_references () :
    global EX, INDEX_T
    
    #sys.stderr.write ("Updating external references..."); sys.stderr.flush ()
    logging.info ("Updating external references...")
    n = 0
    for i in INDEX_T.rows :
        external_file = i['external_file_name_s'][2:]
        external_path = i['hdf5_path_s']
        das = i['serial_number_s']
        target = external_file + ':' + external_path
        external_group = external_path.split ('/')[3]
        ###print external_file, external_path, das, target, external_group
        
        #   Nuke old node
        try :
            group_node = EX.ph5.get_node (external_path)
            group_node.remove ()
        except Exception, e :
            pass
            ###print "E1 ", e
            
        #   Re-create node
        try :
            EX.ph5.create_external_link ('/Experiment_g/Receivers_g', external_group, target)
            n += 1
        except Exception, e :
            #pass
            sys.stderr.write ("{0}\n".format (e))
            
        #sys.exit ()
    #sys.stderr.write ("done, {0} nodes recreated.\n".format (n))
    logging.info ("done, {0} nodes recreated.\n".format (n))


def main():
    def prof () :
        global PH5, KEFFILE, FILES, DEPFILE, RESP, INDEX_T, CURRENT_DAS, F
        
        get_args ()
        
        #print "Initializing ph5 file..."
        initializeExperiment ()
        logging.info ("125a2ph5 {0}".format (PROG_VERSION))
        logging.info ("{0}".format (sys.argv))
        if len (FILES) > 0 :
            RESP = Resp (EX.ph5_g_responses)
            rows, keys = EX.ph5_g_receivers.read_index ()
            INDEX_T = Rows_Keys (rows, keys)
            #print INDEX_T
            #print "Processing TRD files..."
            
        for f in FILES :
            F = f
            ma = TRDfileRE.match (f)
            if  ma or OVERIDE :
                try :
                    if ma :
                        CURRENT_DAS = int (ma.groups ()[0]) + 10000
                    else :
                        ma = TRDfileREpunt.match (f)
                        if ma :
                            CURRENT_DAS = int (ma.groups ()[0]) + 10000
                        else :
                            raise Exception ()
                except :
                    CURRENT_DAS = None
                
                updatePH5 (f)
            else :
                sys.stdout.write (":<Error>: {0}\n".format (f)); sys.stdout.flush ()
                sys.stderr.write ("Warning: Unrecognized raw file name {0}. Skipping!\n".format (f))
        
        update_external_references ()
        #if DEPFILE :
            #print "Processing dep file..."
            #dep_update ()
            
        #if KEFFILE :
            #print "Processing kef file..."
            #populateExperimentTable ()
            
        #ph5flush ()
        closePH5 ()
        print "Done"
        logging.shutdown ()
    '''  
    #   Profile
    import cProfile, pstats
    sys.stderr.write ("Warning: Profiling enabled!\n")
    cProfile.run ('prof ()', "125a2ph5.profile")
    
    p = pstats.Stats ("125a2ph5.profile")
    p.sort_stats('time').print_stats(40)
    '''
    #   No profile
    prof ()

        
if __name__ == '__main__' :
    main()
