#!/usr/bin/env pnpython3

#
#   Generate SEG-Y or SEGY trace files from ph5 file.
#
#   Steve Azevedo, Refactored October 2010
#

import sys, os, os.path, time, logging, copy, traceback
import Experiment, SEGY_h, TimeDOY, ibmfloat, ebcdic, SEGYFactory, decimate
#   The wiggles are stored as numpy arrays in the ph5 file
import numpy

PROG_VERSION = "2016.176 Developmental"

#   Maximum samples in standard SEG-Y trace (2 ^ 15 - 1)
MAX_16 = 32767
#   Maximum samples for PASSCAL SEGY trace (2 ^ 31 - 1)
MAX_32 = 2147483647
#   Default Maximum samples
MAXSAMPLES = MAX_16

CHAN_MAP = { 1:'Z', 2:'N', 3:'E', 4:'Z', 5:'N', 6:'E' }

#   Force time zone to UTC
os.environ['TZ'] = 'UTC'
time.tzset ()

#   The next 3 options are mutually exclusive
#
#   Extract based on event/shot
EVENT_NUMBER = None
#   Extract all events
ALLEVENTS = False
#   Extract based on time
START_TIME = None
#   Extract everything
ALL = None
#
#   Options
#
#   Required
NICKNAME = None
#   Path to PH5 file
PH5PATH = None
#
#   Start time
STOP_TIME = None
#   ARRAY name
ARRAY = None
#   Length of output traces seconds
LENGTH = None
#   Offset from event time in seconds
OFFSET = None
#   Select a single channel
CHANNEL = None
#   Don't time correct
NOTIMECORRECT = None
#   Decimation factor 2, 4, 5, 8, 10, 20
DECIMATION = None
#   Format SEGY or PSGY, PSGY depricated Sept 2014
FORMAT = None
#   Directory to write data into
OUTPATH = None
#   Check all tables read from ph5 file
CHECK = False
#   Extract a single DAS
DAS = None
#   Extract a single station
STA = None
#   Extract a list of stations
###   ZZZ   ###
STA_LIST = None
#   List of DOY to extract. Empty means all.
DOY = []
#   Only extract this sample rate
SR = None
#   Reduction Velocity
RED_VEL = None
#   Sample rate for this array
SR_ARRAY = {}
#
#
#   Handle to ph5
EX = None
#
EXPERIMENT_T = None
#
PH5FILE = None
#
DASS = {}
#
UTM = False
#   Extended trace header style
EXT = 'U'   #   S -> SEG, P -> PASSCAL, U -> USGS Menlo, I -> SIOSEIS

#TDOY = TimeDoy.TimeDoy ()
#   We can extract data by event, start time, all/das
STATES = { 'Event': 0, 'Start': 1, 'All': 2, 'Error': 3, 'AllEvents': 4 }
#
DEPLOY_PICKUP = False

DECIMATION_FACTORS = { '2': '2', '4': '4', '5': '5', '8': '4,2', '10': '5,2', '20': '5,4' } 
#   Break SEG-Y standard
BREAK_STANDARD = False
#
CURRENT_TRACE_TYPE = None
#
CURRENT_TRACE_BYTEORDER = None

class TimeParseError (Exception) :
    def __init__ (self, errno, msg) :
        self.args = (errno, msg)
        self.errno = errno
        self.msg = msg

class lopttime :
    __slots__ = 'epoch', 'flds', 'year', 'doy', 'hr', 'mn', 'sc', 'ms'
    
    def __init__ (self, time_string) :
        if not time_string :
            #self.epoch = 0
            self.year = 0
            self.doy = 0
            self.hr = 0
            self.mn = 0
            self.sc = 0
            self.ms = 0
            return
        try :
            flds = time_string.split (':')
            self.year = int (flds[0])
            self.doy = int (flds[1])
            self.hr = int (flds[2])
            self.mn = int (flds[3])
            if len (flds) == 6 :
                self.sc = int (flds[4])
                self.ms = int ("{0:03d}".format (int (flds[5])))
            else :
                fldsms = flds[4].split ('.')
                self.sc = int (fldsms[0])
                if len (fldsms) == 2 :
                    self.ms = int ("{0:03d}".format (int (fldsms[1])))
                else :
                    self.ms = 0
        except Exception, e :
            sys.stderr.write ("{0}\n".format (e))
            raise TimeParseError (1, "Failed to parse time string: %s" % time_string)
        
    def epoch (self) :
        #tdoy = TimeDoy.TimeDoy ()
        try :
            tdoy = TimeDOY.TimeDOY (year=self.year, 
                                    month=None, 
                                    day=None, 
                                    hour=self.hr, 
                                    minute=self.mn, 
                                    second=self.sc, 
                                    microsecond=int (self.ms * 1000.), 
                                    doy=self.doy, 
                                    epoch=None, 
                                    dtobject=None)
        
            #secs = self.sc + (self.ms / 1000.)
            return tdoy.epoch (fepoch=True)
        except Exception, e :
            raise TimeParseError (1, "Failed to convert to epoch time. %s" % e)
#
#   To hold table rows and keys
#
class rows_keys (object) :
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
class das_groups (object) :
    __slots__ = ('das', 'node')
    def __init__ (self, das = None, node = None) :
        self.das = das
        self.node = node

def get_args () :
    '''   Read command line argments   '''
    global NICKNAME, PH5PATH, PH5FILE, CHANNEL, NOTIMECORRECT, DECIMATION, FORMAT, OUTPATH, MAXSAMPLES, CHECK, DAS, SR, \
           START_TIME, STOP_TIME, UTM, EXT, DEPLOY_PICKUP, BREAK_STANDARD, IGNORE_CHANNEL, STA_LIST
    
    from optparse import OptionParser
    
    oparser = OptionParser ()
    
    oparser.usage = "Version: %s\n" % PROG_VERSION
    oparser.usage += "ph5toseg --eventnumber=shot --nickname=experiment_nickname --length=seconds [--path=ph5_directory_path] [options]\n"
    oparser.usage += "\toptions:\n\t--array=array, --offset=seconds (float), --reduction_velocity=km-per-second (float) --format=['SEGY']\n\n"
    oparser.usage += "ph5toseg --allevents --nickname=experiment_nickname --length=seconds [--path=ph5_directory_path] [options]\n"
    oparser.usage += "\toptions:\n\t--array=array, --offset=seconds (float), --reduction_velocity=km-per-second (float) --format=['SEGY']\n\n"
    oparser.usage += "ph5toseg --starttime=yyyy:jjj:hh:mm:ss[:.]sss --nickname=experiment_nickname --length=seconds [--path=ph5_directory_path] [options]\n"
    oparser.usage += "\toptions:\n\t--stoptime=yyyy:jjj:hh:mm:ss[:.]sss, --array=array, --reduction_velocity=km-per-second (float) --format=['SEGY']\n\n"
    oparser.usage += "ph5toseg --all, --nickname=experiment_nickname [--path=ph5_directory_path] [--das=das_sn] [--station=station_id] [--doy=comma seperated doy list] [options]"
    oparser.usage += "\n\n\tgeneral options:\n\t--channel=[1,2,3]\n\t--sample_rate_keep=sample_rate\n\t--notimecorrect\n\t--decimation=[2,4,5,8,10,20]\n\t--out_dir=output_directory"
    
    oparser.description = "Convert ph5 file to standard SEG-Y."
    
    oparser.add_option ("-e", "--eventnumber", action="store", dest="event_number",
                        type = "string", metavar = "event_number")
    
    oparser.add_option ("-E", "--allevents", action="store_true", dest="all_events",
                        default=False, metavar="all_events")
    
    oparser.add_option ("-s", "--starttime", action="store", dest="start_time",
                        type="string", metavar="start_time")
    
    oparser.add_option ("-A", "--all", action="store_true", dest="extract_all",
                        default=False, metavar="extract_all")
    
    oparser.add_option ("-t", "--stoptime", action="store", dest="stop_time",
                        type="string", metavar="stop_time")
                        
    oparser.add_option ("-a", "--array", action="store", 
                        type="string", dest="array", metavar="array")
    
    oparser.add_option ("-l", "--length", action="store",
                        type="int", dest="length", metavar="length")
    
    oparser.add_option ("-O", "--offset", action="store",
                        type="float", dest="offset", metavar="offset")
    
    oparser.add_option ("-n", "--nickname", action="store",
                        type="string", dest="nickname", metavar="nickname")
    
    oparser.add_option ("-p", "--ph5path", action="store", default=".",
                        type="string", dest="ph5_path", metavar="ph5_path")
    
    oparser.add_option ("-c", "--channel", action="store",
                        type="int", dest="channel", metavar="channel")
    
    oparser.add_option ("-N", "--notimecorrect", action="store_true", default=False,
                        dest="no_time_correct", metavar="no_time_correct")
    
    oparser.add_option ("-d", "--decimation", action="store",
                        choices=["2", "4", "5", "8", "10", "20"], dest="decimation",
                        metavar="decimation")
    
    oparser.add_option ("-f", "--format", action="store", choices=["SEGY", "PSGY"],
                        dest="format", metavar="format", default='SEGY')
    
    oparser.add_option ("-o", "--out_dir", action="store", dest="out_dir", 
                        metavar="out_dir", type="string", default=".")
    
    oparser.add_option ("-C", "--check_tables", action="store_true", default=False,
                        dest="check_tables", metavar="check_tables")
    
    oparser.add_option ("--use_deploy_pickup", action="store_true", default=False,
                        help="Use deploy and pickup times to determine if data exists for a station.",
                        dest="deploy_pickup", metavar="deploy_pickup")
    
    oparser.add_option ("-D", "--das", action="store", dest="das_sn",
                        metavar="das_sn", type="string")
    
    oparser.add_option ("-S", "--station", action="store", dest="station",
                        metavar="station", type="string")
    ###   ZZZ   ###
    oparser.add_option ("--station_list", action="store", dest="sta_list",
                        help="Comma separated list of station id's to extract from selected array.",
                        metavar="sta_list", type="string")
    
    oparser.add_option ("-Y", "--doy", action="store", dest="doy_keep",
                        help="Comma separated list of julian days to extract.",
                        metavar="doy_keep", type="string")
    
    oparser.add_option ("-r", "--sample_rate_keep", action="store", dest="sample_rate",
                        metavar="sample_rate", type="float")
    
    oparser.add_option ("-V", "--reduction_velocity", action="store", dest="red_vel",
                        metavar="red_vel", type="float", default="-1.")
    
    oparser.add_option ("-U", "--UTM", action="store_true", dest="use_utm",
                        help="Fill SEG-Y headers with UTM instead of lat/lon.",
                        default=False, metavar="use_utm")
    
    oparser.add_option ("-x", "--extended_header", action="store", dest="ext_header",
                        help="Extended trace header style: \
                        'P' -> PASSCAL, \
                        'S' -> SEG, \
                        'U' -> Menlo USGS, \
                        'I' -> Scripts SIOSEIS Not implemented, \
                        'N' -> iNova Firefly Not implemented",
                        choices=["P", "S", "U", "I", "N"], default="S", metavar="extended_header_style")
    
    oparser.add_option ("--ic", action="store_true", dest="ignore_channel", default=False)
    
    oparser.add_option ("--break_standard", action = "store_true", dest = "break_standard",
                        default = False, metavar = "break_standard")    
    
    options, args = oparser.parse_args ()
    
    def parse_event () :
        global EVENT_NUMBER, ARRAY, LENGTH, OFFSET, RED_VEL
        
        EVENT_NUMBER = options.event_number
        ARRAY = options.array
        LENGTH = options.length
        OFFSET = options.offset
        RED_VEL = options.red_vel
        logging.info ("Event Number = {0} Array = {1} Length Seconds = {2} Offset Seconds = {3} Reduction Velocity = {4}".format (EVENT_NUMBER,
                                                                                                                                  ARRAY,
                                                                                                                                  LENGTH,
                                                                                                                                  OFFSET,
                                                                                                                                  RED_VEL))
        
        if not LENGTH :
            logging.error ("Error: Length of trace in seconds is required.")
            
    def parse_all_events () :
        global ARRAY, LENGTH, OFFSET, RED_VEL
        
        ARRAY = options.array
        LENGTH = options.length
        OFFSET = options.offset
        RED_VEL = options.red_vel
        logging.info ("Event Number = all Array = {0} Length Seconds = {1} Offset Seconds = {2} Reduction Velocity = {3}".format (ARRAY,
                                                                                                                                  LENGTH,
                                                                                                                                  OFFSET,
                                                                                                                                  RED_VEL))
        
        if not LENGTH :
            logging.error ("Error: Length of trace in seconds is required.")        
        
    def parse_time () :
        global START_TIME, STOP_TIME, LENGTH, ARRAY, RED_VEL
        
        START_TIME = lopttime (options.start_time)
        start_time = "{0:04d}:{1:03d}:{2:02d}:{3:02d}:{4:02d}.{5:03d}".format (START_TIME.year,
                                                                               START_TIME.doy,
                                                                               START_TIME.hr,
                                                                               START_TIME.mn,
                                                                               START_TIME.sc,
                                                                               START_TIME.ms)
        STOP_TIME = lopttime (options.stop_time)
        stop_time = "{0:04d}:{1:03d}:{2:02d}:{3:02d}:{4:02d}.{5:03d}".format (STOP_TIME.year,
                                                                              STOP_TIME.doy,
                                                                              STOP_TIME.hr,
                                                                              STOP_TIME.mn,
                                                                              STOP_TIME.sc,
                                                                              STOP_TIME.ms)
        LENGTH = options.length
        ARRAY = options.array
        RED_VEL = options.red_vel
        logging.info ("Start Time = {0} Stop Time = {4} Array = {1} Length Seconds = {2} Reduction Velocity = {3}".format (start_time,
                                                                                                                           ARRAY,
                                                                                                                           LENGTH,
                                                                                                                           RED_VEL,
                                                                                                                           stop_time))
        if not LENGTH :
            logging.error ("Error: Length of trace in seconds is required.")
    
    def parse_all () :
        global ALL, DAS, STA, DOY
        
        ALL = options.extract_all
        DAS = options.das_sn
        STA = options.station
        logging.info ("Extracting ALL DAS = {0} Stations = {1} Days = {2}".format (DAS, STA, options.doy_keep))
        
        if DAS and STA :
            logging.error ("Warning: Both DAS and station entered. Using station.")
            DAS = None
            
        if options.doy_keep :
            d = options.doy_keep.split (',')
            DOY = map (int, d)
            DOY.sort ()
        
    #   
    if not options.nickname :
        #   XXX
        sys.stderr.write ("Error: --nickname option required.\n")
        sys.exit (-1)
        
    IGNORE_CHANNEL = options.ignore_channel    
    BREAK_STANDARD = options.break_standard
    CHANNEL = options.channel
    NOTIMECORRECT = options.no_time_correct
    DECIMATION = options.decimation
    FORMAT = options.format
    if FORMAT != 'SEGY' :
        sys.stderr.write ("Warning: Generation of PASSCAL SEGY trace files has been depricated in favor of SAC. Generating SEG-Y gather.")
        FORMAT = 'SEGY'
        
    if BREAK_STANDARD :
        MAXSAMPLES = MAX_32
        
    OUTPATH = options.out_dir
    NICKNAME = options.nickname
    PH5PATH = options.ph5_path
    CHECK = options.check_tables
    SR = options.sample_rate
    UTM = options.use_utm
    EXT = options.ext_header
    DEPLOY_PICKUP = options.deploy_pickup
    ###   ZZZ   ###
    try :
        if options.sta_list :
            tmp = options.sta_list.split (',')
            STA_LIST = [int (a.strip ()) for a in tmp]
    except :
        STA_LIST = None
        sys.stderr.write ("Warning: Could not interpret station_list: {0}".format (options.sta_list))
         
    if NICKNAME[-3:] == 'ph5' :
        PH5FILE = os.path.join (PH5PATH, NICKNAME)
    else :
        PH5FILE = os.path.join (PH5PATH, NICKNAME + '.ph5')
        
    if not os.path.exists (PH5FILE) :
        sys.stderr.write ("Error: %s not found.\n" % PH5FILE)
        sys.exit (-1)
    else :
        #   Set up logging
        if not os.path.exists (OUTPATH) :
            os.mkdir (OUTPATH)
            os.chmod(OUTPATH, 0777)
            
        logging.basicConfig (
            filename = os.path.join (OUTPATH, "ph5toseg.log"),
            format = "%(asctime)s %(message)s",
            level = logging.INFO
        )
        
    if options.event_number :
        parse_event ()
        return STATES['Event']
    elif options.all_events == True :
        parse_all_events ()
        return STATES['AllEvents']
    elif options.start_time :
        parse_time ()
        return STATES['Start']
    elif options.extract_all :
        parse_all ()
        return STATES['All']
    else :
        return STATES['Error']
    
#   Convert from polar to rectangular coordinates
def rect(r, w, deg=0): 
    # radian if deg=0; degree if deg=1 
    from math import cos, sin, pi 
    if deg: 
        w = pi * w / 180.0 
    #   return x, y
    return r * cos(w), r * sin(w) 

#   Linear regression, return coefficients a and b (a/b and c)
""" Returns coefficients to the regression line "y=ax+b" from x[] and y[]. 
    Basically, it solves 
        Sxx a + Sx b = Sxy 
        Sx a + N b = Sy 
    where Sxy = \sum_i x_i y_i, Sx = \sum_i x_i, and Sy = \sum_i y_i. 
    The solution is 
        a = (Sxy N - Sy Sx)/det 
        b = (Sxx Sy - Sx Sxy)/det 
    where det = Sxx N - Sx^2. In addition, 
    Var|a| = s^2 |Sxx Sx|^-1 = s^2 | N -Sx| / det 
       |b|       |Sx N |           |-Sx Sxx| 
    s^2 = {\sum_i (y_i - \hat{y_i})^2 \over N-2} 
        = {\sum_i (y_i - ax_i - b)^2 \over N-2} 
        = residual / (N-2) 
    R^2 = 1 - {\sum_i (y_i - \hat{y_i})^2 \over \sum_i (y_i - \mean{y})^2} 
        = 1 - residual/meanerror 
        
    It also prints to <stdout> few other data, N, a, b, R^2, s^2, 
    which are useful in assessing the confidence of estimation. 
""" 
def linreg(X, Y): 
    from math import sqrt 
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
        
    Var_a, Var_b = ss * N / det, ss * Sxx / det 
    
    #print "y=ax+b" 
    #print "N= %d" % N 
    #print "a= %g \\pm t_{%d;\\alpha/2} %g" % (a, N-2, sqrt(Var_a)) 
    #print "b= %g \\pm t_{%d;\\alpha/2} %g" % (b, N-2, sqrt(Var_b)) 
    #print "R^2= %g" % RR 
    #print "s^2= %g" % ss 
    
    return a, b, (RR, ss)

def calc_offset_sign (offsets) :
    '''   offsets is a list of offset_t   '''
    from math import atan, degrees, fabs
    X = []; Y = []; O = []
    offsetmin = 21 ** 63 - 1
    stationmin = 0
    azmin = 0
    for offset_t in offsets :
        try :
            w = offset_t['azimuth/value_f']
            r = offset_t['offset/value_d']
            if abs (r) < abs (offsetmin) :
                offsetmin = r
                stationmin = offset_t['receiver_id_s']
                azmin = w
                #print "Offset min: ", r, " Az min: ", w, " Station: ", stationmin
                
            x, y = rect (r, w, deg=True)
            X.append (x); Y.append (y)
        except Exception, e :
            sys.stderr.write ("%s\n" % e)
            
    #   The seismic line is abx + c (ab => w)   
    ab, c, err = linreg (X, Y)
    
    logging.info ("Linear regression: {0}x + {1}, R^2 = {2}, s^2 = {3}".format (ab, c, err[0], err[1]))
    
    if abs (ab) > 1 :
        regangle = degrees (atan (1./ab))
    else :
        regangle = degrees (atan (ab))
        
    #print "RR: {2} Rise / Run {1} Regression angle: {0}".format (regangle, ab, err[0])
    #if regangle < 0 :
        #regangle += 180.
    #else :
        #regangle = 90. - regangle
        
    #print " Corrected: {0}".format (regangle)
    
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
                
            #if offset_t['receiver_id_s'][0] == '3' :
                #print "Receiver: {2} Azimuth: {0} Corrected azimuth: {1}".format (a, w, offset_t['receiver_id_s'])
            #   Use azimuth to determine sign of offset
            #if flop :
                #sig *= -1
                #offset_t['offset/value_d'] = sig * float (offset_t['offset/value_d'])
            #elif w < 0 :
                #'''   esquerdo   '''
                #offset_t['offset/value_d'] = -1.0 * float (offset_t['offset/value_d'])
                #sig = 1
            #else :
                #'''   direita   '''
                #offset_t['offset/value_d'] = float (offset_t['offset/value_d'])
                #sig = -1
            
            #print "w: ", w, "regangle: ", regangle, "offset: ", offset_t['offset/value_d']
            O.append (offset_t)
        except Exception, e :
            sys.stderr.write ("%s\n" % e)
            
    #   XXX        
    sys.stdout.flush ()
    #   Returning Oh not zero
    return O
    
def get_table_line_by_key (table, key, value) :
    '''   Get a row in a table based on key value pair   '''
    for r in table.rows :
        if not r.has_key (key) : return None
        if r[key] == value :
            return r
        
    return None

def key_array_t_by_das (Array_ts) :
    '''   Key array table lines by das   '''
    keyed = {}
    array_keys = None
    try :
        #   Get array names
        arrays = Array_ts.keys ()
        for array in arrays :
            Array_t = Array_ts[array]
            if CHECK : check_table (Array_t, '/Experiment_g/Sorts_g/Array_t_%s' % array)
            #   Get keys for rows
            array_keys = Array_t.keys
            for array_t in Array_t.rows :
                das = array_t['das/serial_number_s'].strip ()
                #   Build a list of array_t rows keyed on das
                if keyed.has_key (das) :
                    keyed[das].append (array_t)
                else :
                    keyed[das] = []
                    keyed[das].append (array_t)
                    
    except AttributeError :
        pass
    
    #   Build a dummy entry so we can get at DAS's not assigned to an array
    dum = {}
    for k in array_keys :
        if k[-1:] == 'i' or k[-1:] == 'l' :
            dum[k] = 0
        elif k[-1:] == 's' :
            dum[k] = ''
        elif k[-1:] == 'f' or k[-1:] == 'd' :
            dum[k] = 0.
            
    keyed['DUMMY'] = []
    keyed['DUMMY'].append (dum)
                
    return keyed
    
def get_chans_in_array (Array_t) :
    akey = {}
    for r in Array_t.rows :
        if r['channel_number_i'] :
            akey[r['channel_number_i']] = True
        
    ckeys = akey.keys (); ckeys.sort ()
    ret = ''
    for c in ckeys :
        ret = ret + CHAN_MAP[c]
        
    return ret

def get_sort_t_by_time_and_array (sort_t, start, array) :
    rows = []
    found = False
    if array != None :
        try :
            array = int (array)
        except TypeError :
            logging.warn ('Warning: can\'t decipher array name %s' % array)
            
    for r in sort_t.rows :
        sort_start = SEGYFactory.fepoch (r['start_time/epoch_l'], r['start_time/micro_seconds_i'])
        sort_stop = SEGYFactory.fepoch (r['end_time/epoch_l'], r['end_time/micro_seconds_i'])
        if array == None :
            if start >= sort_start and start <= sort_stop :
                rows.append (r)
        else :
            sort_array = int (r['array_name_s'])
            if array == sort_array and start >= sort_start and start <= sort_stop :
                found = True
                rows.append (r)
                
    if array and not found :
        logging.warning ('Warning: Data not found for array %d not found.' % array)
        
    return rows_keys (rows, sort_t.keys)
                
#
#   Initialize ph5 file
#
def initialize_ph5 (editmode = False) :
    '''   Initialize the ph5 file   '''
    global EX
    
    EX = Experiment.ExperimentGroup (PH5PATH, NICKNAME)
    EX.ph5open (editmode)
    EX.initgroup ()
#
#
#
def read_response_table () :
    '''   Read /Experiment_g/Respones_g/Response_t   '''
    global EX
    
    response, response_keys = EX.ph5_g_responses.read_responses ()
    
    rowskeys = rows_keys (response, response_keys)
    
    return rowskeys  
#
#
#
def read_receiver_table () :
    '''   Read receiver table   '''
    global EX
    
    receiver, receiver_keys = EX.ph5_g_receivers.read_receiver ()
    rowskeys = rows_keys (receiver, receiver_keys)
    
    return rowskeys
#
#
#
def read_experiment_table () :
    '''   Read /Experiment_g/Experiment_t   '''
    global EX
    
    exp, exp_keys = EX.read_experiment ()
    
    rowskeys = rows_keys (exp, exp_keys)
    
    return rowskeys
#
#
#
def read_sort_table () :
    '''   Read /Experiment_t/Sorts_g/Sort_g   '''
    global EX
    
    sorts, sorts_keys = EX.ph5_g_sorts.read_sorts ()
    
    rowskeys = rows_keys (sorts, sorts_keys)
    
    return rowskeys
#
#
#
def read_sort_arrays () :
    '''   Read /Experiment_t/Sorts_g/Array_t_[n]   '''
    global EX, SR_ARRAY, ARRAY
    
    array_t = {}
    #   We get a list of Array_t_[n] names here...
    #   (these are also in Sort_t)
    names = EX.ph5_g_sorts.names ()
    for n in names :
        if ARRAY != None :
            array_num = int (n.split ('_')[2])
            if int (ARRAY) != array_num :
                continue
        
        if SR :
            SR_ARRAY[n] = SR
        else :
            SR_ARRAY[n] = None
  
        arrays, array_keys = EX.ph5_g_sorts.read_arrays (n)
        
        rowskeys = rows_keys (arrays, array_keys)
        #   We key this on the name since there can be multiple arrays
        array_t[n] = rowskeys
        
    return array_t
#
#
#
def read_event_table () :
    '''   Read /Experiment_g/Sorts_g/Event_t   '''
    global EX
    
    events, event_keys = EX.ph5_g_sorts.read_events ()
    
    rowskeys = rows_keys (events, event_keys)
    
    return rowskeys
#
#
#
def read_offset_table (event = None, stations = None) :
    '''   Read /Experinent_t/Sorts_g/Offset_t
          return Event_t keyed by event         '''
    global EX
    
    shotrange = [ int (event), int (event) ]
    # 
    keyed_event = {}
    
    offsets, offset_keys = EX.ph5_g_sorts.read_offsets (shotrange, stations)
    
    for o in offsets :
        shot = o['event_id_s']
        if event and (event != shot) : continue
        if keyed_event.has_key (shot) :
            keyed_event[shot].append (o)
        else :
            keyed_event[shot] = [ o ]
            
    shots = keyed_event.keys ()
    for s in shots :
        offsets = keyed_event[s]
        calc_offset_sign (offsets)
        keyed_event[s] = rows_keys (offsets, offset_keys)
        
    return keyed_event
#
#
#
def read_time_table () :
    global EX
    
    times, time_keys = EX.ph5_g_receivers.read_time ()
    
    return rows_keys (times, time_keys)
#
#
#
def read_das_groups () :
    '''   Get das groups   '''
    global EX
    
    #   Get references for all das groups keyed on das
    return EX.ph5_g_receivers.alldas_g ()

def get_events (event_t, start, end) :
    '''   Return rows keys from /Experiment_g/Sorts_g/Event_t that falls in start -> end   '''
    rows = []
    #print start, end
    start = float (start)
    end = float (end)
    for r in event_t.rows :
        event_start = SEGYFactory.fepoch (r['time/epoch_l'], r['time/micro_seconds_i'])
        if event_start >= start and event_start <= end :
            rows.append (r)
            
    rows.sort (key=lambda event: event['time/epoch_l'])
    return rows_keys (rows, event_t.keys)

def get_offset_t (Offset_t, station, shot) :
    if not Offset_t : return None
    if not shot : return None
    if not Offset_t.has_key (station) :
        return None
    
    if Offset_t[station].has_key (shot) :
        return Offset_t[station][shot]
        
    return None

def get_time (Time_t, das, start) :
    
    for r in Time_t.rows :
        if r['das/serial_number_s'].strip () != das :
            continue
        
        time_start = SEGYFactory.fepoch (r['start_time/epoch_l'], r['start_time/micro_seconds_i'])
        time_stop = SEGYFactory.fepoch (r['end_time/epoch_l'], r['end_time/micro_seconds_i'])
        if start >= time_start and start <= time_stop :
            return r
        
    return None

def get_response (Response_t, n) :
    rows = Response_t.rows
    
    return rows[n]

def get_offset_distance_for_array (Offset_t, Array_t) :
    '''   Find all offset_t for array combination.   '''
    #
    keyed_station = {}
    keyed_event = {}
    ks = {}
    for o in Offset_t.rows :
        sta = o['receiver_id_s']
        shot = o['event_id_s']
        #
        keyed_event[shot] = o
        ks[sta] = copy.deepcopy (keyed_event)
                
    for array_t in Array_t.rows :
        sta = array_t['id_s']
        if ks.has_key (sta) :
            keyed_station[sta] = copy.deepcopy (ks[sta])
            
    del ks
            
    return keyed_station
#
#
#
def check_table (table_t, name) :
    '''   Check a table for empty or zero entries   '''
    if table_t.rows == [] :
        logging.warn ("Warning: %s is not populated." % name)
        return
    
    i = 0
    for r in table_t.rows :
        i += 1
        for k in table_t.keys :
            if r.has_key (k) and r[k] == '' :
                logging.warn ("\tCheck: Row %d of %s/%s is not populated." % (i, name, k))
                
            if r.has_key (k) and r[k] == 0 :
                logging.warn ("\tCheck: Row %d of %s/%s is zero." % (i, name, k))
                
def get_das_lines (Das_t, start, stop, chan, sr_array) :
    '''   Get lines from a das (rows/keys) table that cover start stop times and channel   '''
    def last_das_start (tmp_row) :
        return SEGYFactory.fepoch (tmp_row['time/epoch_l'], tmp_row['time/micro_seconds_i'])
        
    rows = []
    used_sr = None
    for r in Das_t.rows :
        das_start = SEGYFactory.fepoch (r['time/epoch_l'], r['time/micro_seconds_i'])
        das_stop = das_start + (r['sample_count_i'] / (float (r['sample_rate_i']) / r['sample_rate_multiplier_i']))
        das_chan = r['channel_number_i']
        sample_rate = r['sample_rate_i'] / r['sample_rate_multiplier_i']
        #   Filter on sample rate
        if sr_array != None :
            if sr_array != sample_rate :
                continue
        #   Filter on channel
        if chan != None :
            if chan != das_chan : continue
            
        #   Check for duplicate data entered in ph5 file
        #   XXX   Should log duplicate data   XXX
        if start >= das_start and start <= das_stop :
            try :
                if len (rows) == 0 :
                    rows.append (r)
                    used_sr = sample_rate
                elif last_das_start (rows[-1]) != das_start :
                    rows.append (r)
                    used_sr = sample_rate
                elif last_das_start (rows[-1]) == das_start :
                    logging.warn ("Warning: Ignoring extra data trace in PH5 file.")
            except :
                pass
                
            continue
        
        if stop <= das_stop and stop >= das_start :
            try :
                if len (rows) == 0 :
                    rows.append (r)
                    used_sr = sample_rate
                elif last_das_start (rows[-1]) != das_start :
                    rows.append (r)
                    used_sr = sample_rate
            except :
                pass
            
    return rows_keys (rows, Das_t.keys), used_sr

def count_das (Array_t, start, stop, CHAN, sr_array) :
    n = 0
    counted = []
    for r in Array_t.rows :
        ###   ZZZ   ###
        if STA_LIST != None :
            if not int (r['id_s']) in STA_LIST :
                continue
        das = r['das/serial_number_s'].strip ()
        chan = r['channel_number_i']
        if CHAN :
            if CHAN != chan : 
                continue
            
        #   Check that this array entry is within time deployed
        deploy = r['deploy_time/epoch_l']
        pickup = r['pickup_time/epoch_l']
        #print deploy, start, pickup
        if DEPLOY_PICKUP == True and not ((start >= deploy and start <= pickup)) :
            #print '***'
            logging.info ("DAS {0} not deployed at station {1} on {2}.".format (das, r['id_s'], time.ctime (start)))
            logging.info ("Deployed: {0} Picked up: {1}.".format (time.ctime (deploy), time.ctime (pickup)))
            continue
        
        if DASS.has_key (das) :
            EX.ph5_g_receivers.setcurrent (DASS[das])
            das_r, das_keys = EX.ph5_g_receivers.read_das ()
            Das_t = rows_keys (das_r, das_keys)
            if IGNORE_CHANNEL :
                Das_t, tmp_sr = get_das_lines (Das_t, start, stop, None, sr_array)
            else :
                Das_t, tmp_sr = get_das_lines (Das_t, start, stop, chan, sr_array)
                
            if sr_array == None : sr_array = tmp_sr
            if Das_t.rows == [] :
                logging.info ("No data found for station %s channel %s" % (r['id_s'], chan))
                continue
            else :
                #   array_t, Das_t
                logging.info ("Found data for station %s channel %s sample rate %s" % (r['id_s'], chan, tmp_sr))
                counted.append ([r, Das_t])
                n += 1
                
    logging.info ("Found data for %d traces." % n)
    
    return counted, n
#
#
#
def cut (start, stop, Das_t, time_t, Response_t, Receiver_t, sf) :
    '''   Cut trace data from the ph5 file   '''
    global EX, CURRENT_TRACE_BYTEORDER, CURRENT_TRACE_TYPE
    
    data = []
    samples_read = 0
    
    #   Loop through each das table line for this das
    for d in Das_t.rows :
        #   Start time and stop time of recording window
        window_start_epoch = SEGYFactory.fepoch (d['time/epoch_l'], d['time/micro_seconds_i'])
        window_sample_rate = d['sample_rate_i'] / float (d['sample_rate_multiplier_i'])
        window_samples = d['sample_count_i']
        window_stop_epoch = window_start_epoch + (window_samples / window_sample_rate)
        
        #   Number of samples left to cut
        cut_samples = int (((stop - start) * window_sample_rate) - samples_read)
        #
        if samples_read == 0 and not DECIMATION :
            sf.set_length_points (cut_samples)
            
        #   How many samples into window to start cut
        cut_start_sample = int ((start - window_start_epoch) * window_sample_rate)
        #   If this is negative we must be at the start of the next recording window
        if cut_start_sample < 0 : cut_start_sample = 0
        #   Last sample in this recording window that we need to cut
        cut_stop_sample = cut_start_sample + cut_samples
        
        #   Read the data trace from this window
        trace_reference = EX.ph5_g_receivers.find_trace_ref (d['array_name_data_a'].strip ())
        data_tmp = EX.ph5_g_receivers.read_trace (trace_reference, 
                                                  start = cut_start_sample,
                                                  stop = cut_stop_sample)
        
        CURRENT_TRACE_TYPE, CURRENT_TRACE_BYTEORDER = EX.ph5_g_receivers.trace_info (trace_reference)
        
        #   First das table line
        if data == [] :
            #data.extend (data_tmp)
            #samples_read = len (data)
            #new_window_start_epoch = window_stop_epoch + (1. / window_sample_rate)
            needed_samples = cut_samples
            #   Set das table in SEGYFactory.Ssegy
            sf.set_das_t (d)
            #   Get response table line
            if Response_t :
                try :
                    response_t = Response_t.rows[d['response_table_n_i']]
                except Exception as e :
                    sys.stderr.write ("Response_t error: {0}\n".format (e))
                    response_t = None
            else :
                response_t = None
                
            #   Get receiver table line 
            if Receiver_t :
                try :
                    receiver_t = Receiver_t.rows[d['receiver_table_n_i']]
                except Exception as e :
                    sys.stderr.write ("Receiver_t error: {0}\n".format (e))
                    sys.stderr.write ("Is Receiver_t empty?\n")
                    receiver_t = None
            else :
                receiver_t = None
            
            #   Log information about recorder and sensor
            if response_t :
                sf.set_response_t (response_t)
                logging.info ("Gain: %d %s Bitweight: %g %s" % (response_t['gain/value_i'],
                                                                response_t['gain/units_s'],
                                                                response_t['bit_weight/value_d'],
                                                                response_t['bit_weight/units_s'].strip ()))
            if receiver_t :
                sf.set_receiver_t (receiver_t)
                logging.info ("Component: %s Azimuth: %5.1f %s Dip: %5.1f %s" % (receiver_t['orientation/description_s'].strip (),
                                                                                 receiver_t['orientation/azimuth/value_f'],
                                                                                 receiver_t['orientation/azimuth/units_s'].strip (),
                                                                                 receiver_t['orientation/dip/value_f'],
                                                                                 receiver_t['orientation/dip/units_s'].strip ()))
            #   Log time correction information
            if time_t :
                sf.set_time_t (time_t)
                logging.info ("Clock: Start Epoch: %015.3f End Epoch: %015.3f" % (SEGYFactory.fepoch (time_t['start_time/epoch_l'], time_t['start_time/micro_seconds_i']),
                                                                                  SEGYFactory.fepoch (time_t['end_time/epoch_l'], time_t['end_time/micro_seconds_i'])))
                
                logging.info ("Clock: Offset: %g seconds Slope: %g" % (time_t['offset_d'],
                                                                       time_t['slope_d']))
            else :
                #   Do not apply time correction
                sf.set_time_t (None)
                
        #   We are at the start of the next recording window
        else :
            #   Time difference between the end of last window and the start of this one
            time_diff = abs (new_window_start_epoch - window_start_epoch)
            if time_diff > (1. / window_sample_rate) :
                logging.error ("Error: Attempted to cut past end of recording window and data is not continuous!")
                #return []
                
        if len (data_tmp) > 0 :
            data.extend (data_tmp)
            samples_read = len (data)
            
        new_window_start_epoch = window_stop_epoch + (1. / window_sample_rate)
        
    #   Attempt to cut past end of recording window
    if samples_read < needed_samples :
        logging.error ("Error: Attempted to cut past end of recording window!")
        #return []
                    
    #   Do we need to decimate this trace?
    if DECIMATION :
        #print "decimate..."
        shift, data = decimate.decimate (DECIMATION_FACTORS[DECIMATION], data)
        #print "done"
        window_sample_rate = int (window_sample_rate / int (DECIMATION))
        sf.set_sample_rate (window_sample_rate)
        samples_read = len (data)
        shift_seconds = float (shift) / window_sample_rate
        if shift_seconds > (1./window_sample_rate) :
            logging.warn ("Warning: Time shift from decimation %06.4f" % shift_seconds)

        sf.set_length_points (int ((stop - start) * window_sample_rate))
    
    logging.info ("Sample rate: %d Number of samples: %d" % (window_sample_rate, samples_read))
    
    return data
#
#   Write a PASSCAL SEGY file
#
def write_psgy (data, fd, sf) :
    if len (data) > MAX_32 :
        logging.warn ("Warning: Data trace too long, %d samples, truncating to %d" % (len (data), MAX_32))
        sf.set_length_points (MAX_32)
    else :
        sf.set_length_points (sf.length_points_all)
        
    #logging.info ("New " * 10)
    logging.info ("Opening: %s" % fd.name)
    
    sf.set_data (data[:MAX_32])
    sf.set_trace_type (CURRENT_TRACE_TYPE, CURRENT_TRACE_BYTEORDER)
    sf.set_pas ()
    try :
        sf.set_trace_header ();
    except SEGYFactory.SEGYError as e :
        logging.error (e)
        sys.stderr.write ("{0}\n".format (e))
        traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback,
                                  limit=2, file=sys.stderr)        

        
    try :
        n, nparray = sf.set_data_array ()
    except Exception as e :
        logging.error (e)
        sys.stderr.write ("{0}\n".format (e))
        traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback,
                                  limit=2, file=sys.stderr)        
     
        
    #   *XXX*
    try :
        sf.write_trace_header (fd); 
        sf.write_data_array (fd, nparray)
    except SEGYFactory.SEGYError as e :
        logging.error (e)
        sys.stderr.write ("{0}\n".format (e))
        traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback,
                                  limit=2, file=sys.stderr)        
     
        
    L = len (data)
    p = sf.length_points_all - L
    logging.info ("Wrote: {0:d} samples with {1:d} sample padding.".format (L, p))
    if n != sf.length_points_all :
        logging.warn ("Only wrote {0} samples.".format (n))
#
#   Write standard SEG-Y reel header
#
def write_segy_hdr (data, fd, sf, num_traces) :
    if len (data) > MAX_16 and BREAK_STANDARD == False :
        logging.warn ("Warning: Data trace too long, %d samples, truncating to %d" % (len (data), MAX_16))
        sf.set_length_points (MAX_16)
    else :
        sf.set_length_points (sf.length_points_all)
        
    logging.info ("New " * 10)
    logging.info ("Opening: %s" % fd.name)
    sf.set_data (data[:MAXSAMPLES])
    sf.set_trace_type (CURRENT_TRACE_TYPE, CURRENT_TRACE_BYTEORDER)
    try :
        sf.set_text_header ()
        sf.set_reel_header (num_traces)
        sf.set_trace_header ()    
    except SEGYFactory.SEGYError as e :
        logging.error (e)
        sys.stderr.write ("{0}\n".format (e))
        traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback,
                                  limit=2, file=sys.stderr)        

    
    try :   
        n, nparray = sf.set_data_array ()
    except Exception as e :
        logging.error (e)
        sys.stderr.write ("{0}\n".format (e))
        traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback,
                                  limit=2, file=sys.stderr)        
            
    
    try :    
        sf.write_text_header (fd)
        sf.write_reel_header (fd)
        sf.write_trace_header (fd)
        sf.write_data_array (fd, nparray)
    except SEGYFactory.SEGYError as e :
        logging.error (e)
        #exc_type, exc_value, exc_traceback = sys.exc_info()
        sys.stderr.write ("{0}\n".format (e))
        traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback,
                                  limit=2, file=sys.stderr)        
        
    L = len (data)
    p = sf.length_points_all - L
    logging.info ("Wrote: {0:d} samples with {1:d} sample padding.".format (L, p))
    if n != sf.length_points_all :
        logging.warn ("Only wrote {0} samples.".format (n))
    
#
#   Write SEG-Y trace
#
def write_segy (data, fd, sf) :
    if len (data) > MAX_16 and BREAK_STANDARD == False :
        logging.warn ("Warning: Data trace too long, %d samples, truncating to %d" % (len (data), MAX_16))
        sf.set_length_points (MAX_16)
        
    #sf.set_length_points (len (data))
    sf.set_data (data[:MAXSAMPLES])
    sf.set_trace_type (CURRENT_TRACE_TYPE, CURRENT_TRACE_BYTEORDER)
    try :
        sf.set_trace_header ()
    except SEGYFactory.SEGYError as e :
        logging.error (e)
        sys.stderr.write ("{0}\n".format (e))
        traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback,
                                  limit=2, file=sys.stderr)        
            
    
    try :    
        n, nparray = sf.set_data_array ()
    except Exception as e :
        logging.error (e)
        sys.stderr.write ("{0}\n".format (e))
        traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback,
                                  limit=2, file=sys.stderr)        
    
        
    #   *XXX*
    #for d in nparray : print d
    try :
        sf.write_trace_header (fd)
        sf.write_data_array (fd, nparray)
    except SEGYFactory.SEGYError as e :
        logging.error (e)
        sys.stderr.write ("{0}\n".format (e))
        traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback,
                                  limit=2, file=sys.stderr)        
           
    
    L = len (data)
    p = sf.length_points_all - L
    logging.info ("Wrote: {0:d} samples with {1:d} sample padding.".format (L, p))
    if n != sf.length_points_all :
        logging.warn ("Only wrote {0} samples.".format (n))    

#
#
#
def calc_red_vel_secs (offset_t) :
    global RED_VEL
    
    if RED_VEL <= 0 :
        return 0.
    
    if offset_t == None :
        logging.warn ("Warning: No geometry for station. Reduction velocity not applied.")
        return 0.
     
    if offset_t['offset/units_s'] != 'm' :
        logging.warn ("Warning: Units for offset not in meters! No reduction velocity applied.")
        return 0.
    
    #   m / m/s = seconds
    try :
        secs = abs (offset_t['offset/value_d']) / (RED_VEL * 1000.)
        logging.info ("Applying a reduction velocity of {0:5.3f} seconds".format (secs))
        #print secs
        return secs
    except Exception, e :
        logging.warn ("{0:s}\n".format (e))
        return 0.
    
def get_stations_from_Array_ts (Array_ts) :
    
    stations = []
    if Array_ts != None :
        keys = Array_ts.keys ()
        for k in keys :
            array_t = Array_ts[k]
            for a in array_t.rows :
                stations.append (int (a['id_s']))
            
    return stations

#
#
#
def process_event () :
    '''   Process event oriented requests   '''
    global DASS, SR_ARRAY, UTM, EVENT_NUMBER
    
    experiment_t = EXPERIMENT_T.rows[0]
    nickname = experiment_t['nickname_s'].strip ()
    
    #   Read event table and get event table line for this event
    Event_t = read_event_table ()
    event_t = get_table_line_by_key (Event_t, 'id_s', EVENT_NUMBER)
    if CHECK : check_table (rows_keys ([event_t], Event_t.keys), '/Experiment_g/Sorts_g/Event_t')
    if event_t == None :
        logging.error ('Error: Can\'t find %s in /Experiment_g/Sorts_g/Event_t.' % EVENT_NUMBER)
        sys.exit (-1)
      
    #   Get start time to cut based on start time of event and OFFSET set on command line
    start_epoch = SEGYFactory.fepoch (event_t['time/epoch_l'], event_t['time/micro_seconds_i'])
    if OFFSET :
        start_epoch += OFFSET
        
    #   Read sort table and find the sort table line based on cut start time and array
    Sort_t = read_sort_table ()
    if CHECK : check_table (Sort_t, '/Experiment_g/Sorts_g/Sort_t')
    Sort_t = get_sort_t_by_time_and_array (Sort_t, start_epoch, ARRAY)
    if Sort_t.rows == [] :
        logging.error ('Error: /Experiment_g/Sorts_g/Sort_t does not cover event %s for array %s.' % (EVENT_NUMBER, ARRAY))
        return
        
    #  Get cut stop time from length set on command line or set it to end time of sort
    if LENGTH :
        stop_epoch = start_epoch + LENGTH
    else :
        sort_t = Sort_t.rows[0]
        stop_epoch = SEGYFactory.fepoch (sort_t['end_time/epoch_l'], sort_t['end_time/micro_seconds_i'])
        
    #print "Start: ", start_epoch, "Stop: ", stop_epoch
    cut_length = stop_epoch - start_epoch
    
    #   Write event info to log
    logging.info ("Extracting: Event ID %s" % EVENT_NUMBER)
    logging.info ("Start: %s Stop: %s" % (time.ctime (start_epoch), time.ctime (stop_epoch)))
    logging.info ("Start epoch: %015.3f Stop epoch: %015.3f" % (start_epoch, stop_epoch))
    logging.info ("Shot ID: %s Description: %s" % (event_t['id_s'].strip (), event_t['description_s'].strip ()))
    logging.info ("Lat: %f Lon: %f Elev: %f %s" % (event_t['location/Y/value_d'],
                                                   event_t['location/X/value_d'],
                                                   event_t['location/Z/value_d'],
                                                   event_t['location/Z/units_s'].strip ()))
    

    #   Array_t = Array_ts[array_table_name]
    Array_ts = read_sort_arrays ()
    stations = get_stations_from_Array_ts (Array_ts)
    #   Offset table line = Offset_distance_t[event]
    Offset_distance_t = read_offset_table (EVENT_NUMBER, stations)
    #   List of DAS groups
    DASS = read_das_groups ()
    #   Counted_Das_Array[array_name_s] = [sort_t, [array_t, Das_t]]
    Counted_Das_Array = {}
    
    for s in Sort_t.rows :
        #   Get array lines for this array
        Array_t = Array_ts[s['array_t_name_s']]
        if CHECK : check_table (Array_t, '/Experiment_t/Sorts_g/%s' % s['array_t_name_s'])
        logging.info ('Searching for data: Array: %s' % s['array_name_s'])
        #   offset_t = keyed_offsets[station][shot]
        try :
            keyed_offsets = get_offset_distance_for_array (Offset_distance_t[EVENT_NUMBER], Array_t)
        except :
            keyed_offsets = {}
            
        #   counted_das_t = [array_t, Das_t]
        counted_das_t, num = count_das (Array_t, start_epoch, stop_epoch, CHANNEL, SR_ARRAY[s['array_t_name_s']])
        if len (counted_das_t) != 0 :
            #   [sort_t, [array_t, num_traces, Das_t]]
            Counted_Das_Array[s['array_name_s']] = [s, num, counted_das_t, keyed_offsets]
            
    #   Sort the arrays alphebetically
    arrays = Counted_Das_Array.keys ()
    arrays.sort ()
    #   Read the response table (gain and bit weight)
    Response_t = read_response_table ()
    if CHECK : check_table (Response_t, '/Experiment_g/Responses_g/Response_t')
    #   Read the time corrections table
    Time_t = read_time_table ()
    if CHECK : check_table (Time_t, '/Experiment_g/Receivers_g/Time_t')
    #   Read the receivers table (orientation of components)
    Receiver_t = read_receiver_table ()
    if CHECK : check_table (Receiver_t, '/Experiment_g/Receivers_g/Receiver_t')
    
    #   Loop through each of the arrays
    for a in arrays :
        sort_t, num_traces, counted_das_t, keyed_offsets = Counted_Das_Array[a]
        line_seq = 0
        fd = None
        sf = SEGYFactory.Ssegy (sort_t, event_t, utm = UTM)
        sf.set_break_standard (BREAK_STANDARD)
        
        #   basename for output
        #   Base name for files
        if CHANNEL :
            chan_name = CHAN_MAP[CHANNEL]
        else :
            key = 'Array_t_{0:03d}'.format (int (a))
            chan_name = get_chans_in_array (Array_ts[key])

        tdoy = TimeDOY.TimeDOY (year=None, 
                                month=None, 
                                day=None, 
                                hour=0, 
                                minute=0, 
                                second=0, 
                                microsecond=0, 
                                doy=None, 
                                epoch=start_epoch, 
                                dtobject=None)
        base = "%s_%s_%s_%s" % (nickname, a, tdoy.getPasscalTime (ms=True), chan_name)
        base = base.replace (':', '_'); base = base.replace (' ', '_')
                    
        #   counted_das_t is a list
        for c in counted_das_t :
            #   Get array table line and das table rows covering the cut
            array_t = c[0]; Das_t = c[1]
            if CHECK : check_table (Das_t, '/Experiment_g/Receivers_g/Das_g_%s/Das_t' % array_t['id_s'])

            #   Get offset table line for shot and station
            offset_t = get_offset_t (keyed_offsets, array_t['id_s'], EVENT_NUMBER)
            ###   Reduction Velocity here   ###
            rvs = calc_red_vel_secs (offset_t)
            #print start_epoch, stop_epoch
            #start_epoch += rvs; stop_epoch += rvs
            sf.set_cut_start_epoch (start_epoch + rvs)
            #print rvs, start_epoch, stop_epoch
            line_seq += 1
            
            #   Write station information to log file
            logging.info ("%d" % line_seq)
            logging.info ("Station_id: %s DAS: %s Channel: %d" % (array_t['id_s'],
                                                                  array_t['das/serial_number_s'], 
                                                                  array_t['channel_number_i']))
            
            logging.info ("Description: %s" % array_t['description_s'])
            
            logging.info ("Lat: %f Lon: %f Elev: %f %s" % (array_t['location/Y/value_d'],
                                                           array_t['location/X/value_d'],
                                                           array_t['location/Z/value_d'],
                                                           array_t['location/Z/units_s'].strip ()))
            
            if offset_t :
                logging.info ("Offset: %d %s Azimuth: %f %s" % (offset_t['offset/value_d'],
                                                                offset_t['offset/units_s'].strip (),
                                                                offset_t['azimuth/value_f'],
                                                                offset_t['azimuth/units_s'].strip ()))
            
            #   Das name comes from array table line
            das = array_t['das/serial_number_s']
            #   Set current das group
            EX.ph5_g_receivers.setcurrent (DASS[das])
            #   Get time correction table line
            if not NOTIMECORRECT :
                time_t = get_time (Time_t, das, start_epoch + rvs)
            else :
                time_t = None
            
            #   Set up SEGYFactory.Ssegy
            sf.set_array_t (array_t)
            sf.set_offset_t (offset_t)
            sf.set_line_sequence (line_seq)
            #   Set extended trace header style
            sf.set_ext_header_type (EXT)
            
            #   Read the data from the ph5 file
            data = cut (start_epoch + rvs, stop_epoch + rvs, Das_t, time_t, Response_t, Receiver_t, sf)
            #   *XXX*
            #for d in data : print d
            #sf.set_length_points (len (data))
            #print len (data)
            if len (data) == 0 :
                data = [0]
                logging.info ("Read zero samples.")
            
            temppath = os.path.join (OUTPATH, EVENT_NUMBER)
            if not os.path.exists (temppath) :
                os.makedirs (temppath)
                os.chmod(temppath, 0777)
                
            if not fd :
                filename = os.path.join (temppath, "%s.01.SGY" % base)
                i = 0
                while os.path.exists (filename) :
                    i += 1
                    tmp = filename[:-6]
                    filename = "%s%02d.SGY" % (tmp, i)
                    
                fd = open (filename, 'w+')
                write_segy_hdr (data, fd, sf, num_traces)
            else :
                write_segy (data, fd, sf)
                os.chmod(filename, 0777)
                
        if fd : fd.close ()

    logging.info ("Done.\n")

def _event_number (event_t) :
    return event_t['id_s']
#
#
#
def process_all_events () :
    global EVENT_NUMBER
    
    events = map (_event_number, read_event_table ().rows)
    #print events
    events.sort ()
    for e in events :
        EVENT_NUMBER = e
        process_event ()
        
#
#
#
def process_start () :
    '''   '''
    global DASS, SR_ARRAY, UTM, EVENT_NUMBER
    
    experiment_t = EXPERIMENT_T.rows[0]
    nickname = experiment_t['nickname_s'].strip ()
    
    start_epoch = START_TIME.epoch ()
    
    #   Read sort table and find the sort table line based on cut start time and array
    Sort_t = read_sort_table ()
    if CHECK : check_table (Sort_t, '/Experiment_g/Sorts_g/Sort_t')
    Sort_t = get_sort_t_by_time_and_array (Sort_t, start_epoch, ARRAY)
    if Sort_t.rows == [] :
        logging.error ('Error: /Experiment_g/Sorts_g/Sort_t does not cover start time %s.' % time.ctime (start_epoch))
        sys.exit (-1)
        
    #  Get cut stop time from length set on command line or set it to end time of sort
    if STOP_TIME.year and LENGTH :
        logging.warning ("Warning: Both stop time and length specified. Using length.")
    
    if LENGTH :
        stop_epoch = start_epoch + LENGTH
    elif STOP_TIME :
        stop_epoch = STOP_TIME.epoch ()
        
    cut_length = stop_epoch - start_epoch
    #   Read event table and get event table line for this event
    Event_t = read_event_table ()
    event_t = get_events (Event_t, start_epoch, stop_epoch)
    
    if CHECK : check_table (event_t, '/Experiment_g/Sorts_g/Event_t')
    #   Write event info to log
    #logging.info ("Extracting: Event ID %s" % EVENT_NUMBER)
    logging.info ("Extracting: Start: %s Stop: %s" % (time.ctime (start_epoch), time.ctime (stop_epoch)))
    logging.info ("Start epoch: %015.3f Stop epoch: %015.3f" % (start_epoch, stop_epoch))
    #   Array_t = Array_ts[array_table_name]
    Array_ts = read_sort_arrays ()
    stations = get_stations_from_Array_ts (Array_ts)
    if len (event_t.rows) > 0 :
        #print event_t
        event_t = event_t.rows[0]
        logging.info ("Shot ID: %s Description: %s" % (event_t['id_s'].strip (), event_t['description_s'].strip ()))
        logging.info ("Lat: %f Lon: %f Elev: %f %s" % (event_t['location/Y/value_d'],
                                                       event_t['location/X/value_d'],
                                                       event_t['location/Z/value_d'],
                                                       event_t['location/Z/units_s'].strip ())) 

        #   Offset table line = Offset_distance_t[event]
        EVENT_NUMBER = event_t['id_s'].strip ()
        Offset_distance_t = read_offset_table (EVENT_NUMBER, stations)
    else :
        logging.info ("No shot information found.")
        Offset_distance_t = None
        
    #   List of DAS groups
    DASS = read_das_groups ()
    #   Counted_Das_Array[array_name_s] = [sort_t, [array_t, Das_t]]
    Counted_Das_Array = {}
    
    for s in Sort_t.rows :
        #   Get array lines for this array
        Array_t = Array_ts[s['array_t_name_s']]
        if CHECK : check_table (Array_t, '/Experiment_t/Sorts_g/%s' % s['array_t_name_s'])
        logging.info ('Searching for data: Array: %s' % s['array_name_s'])
        #   offset_t = keyed_offsets[station][shot]
        try :
            keyed_offsets = get_offset_distance_for_array (Offset_distance_t[event_t['id_s'].strip ()], Array_t)
        except :
            keyed_offsets = {}
            
        #   counted_das_t = [array_t, Das_t]
        counted_das_t, num = count_das (Array_t, start_epoch, stop_epoch, CHANNEL, SR_ARRAY[s['array_t_name_s']])
        if num != 0 :
            #   [sort_t, [array_t, num_traces, Das_t]]
            Counted_Das_Array[s['array_name_s']] = [s, num, counted_das_t, keyed_offsets]    

    #   Sort the arrays alphebetically
    arrays = Counted_Das_Array.keys ()
    arrays.sort ()
    #   Read the response table (gain and bit weight)
    Response_t = read_response_table ()
    if CHECK : check_table (Response_t, '/Experiment_g/Responses_g/Response_t')
    #   Read the time corrections table
    Time_t = read_time_table ()
    if CHECK : check_table (Time_t, '/Experiment_g/Receivers_g/Time_t')
    #   Read the receivers table (orientation of components)
    Receiver_t = read_receiver_table ()
    if CHECK : check_table (Receiver_t, '/Experiment_g/Receivers_g/Receiver_t')
    
    #   Loop through each of the arrays
    for a in arrays :
        sort_t, num_traces, counted_das_t, keyed_offsets = Counted_Das_Array[a]
        line_seq = 0
        fd = None
        sf = SEGYFactory.Ssegy (sort_t, event_t, utm = UTM)
        sf.set_cut_start_epoch (start_epoch)
        sf.set_break_standard (BREAK_STANDARD)
        
        #   basename for output
        #   Base name for files
        if CHANNEL :
            chan_name = CHAN_MAP[CHANNEL]
        else :
            key = 'Array_t_{0:03d}'.format (int (a))
            chan_name = get_chans_in_array (Array_ts[key])

        tdoy = TimeDOY.TimeDOY (year=None, 
                                month=None, 
                                day=None, 
                                hour=0, 
                                minute=0, 
                                second=0, 
                                microsecond=0, 
                                doy=None, 
                                epoch=start_epoch, 
                                dtobject=None)
        base = "%s_%s_%s_%s" % (nickname, a, tdoy.getPasscalTime (ms=True), chan_name)
        base = base.replace (':', '_'); base = base.replace (' ', '_')
                    
        #   counted_das_t is a list
        for c in counted_das_t :
            #   Get array table line and das table rows covering the cut
            array_t = c[0]; Das_t = c[1]
            if CHECK : check_table (Das_t, '/Experiment_g/Receivers_g/Das_g_%s/Das_t' % array_t['id_s'])

            #   Get offset table line for shot and station
            offset_t = get_offset_t (keyed_offsets, array_t['id_s'], EVENT_NUMBER)
            ###   Reduction Velocity here   ###
            rvs = calc_red_vel_secs (offset_t)
            #start_epoch += rvs; stop_epoch += rvs
            line_seq += 1
            
            #   Write station information to log file
            logging.info ("%d" % line_seq)
            logging.info ("Station_id: %s DAS: %s Channel: %d" % (array_t['id_s'],
                                                                  array_t['das/serial_number_s'], 
                                                                  array_t['channel_number_i']))
            
            logging.info ("%s" % array_t['description_s'])
            
            logging.info ("Lat: %f Lon: %f Elev: %f %s" % (array_t['location/Y/value_d'],
                                                           array_t['location/X/value_d'],
                                                           array_t['location/Z/value_d'],
                                                           array_t['location/Z/units_s'].strip ()))
            
            if offset_t :
                logging.info ("Offset: %d %s Azimuth: %f %s" % (offset_t['offset/value_d'],
                                                                offset_t['offset/units_s'].strip (),
                                                                offset_t['azimuth/value_f'],
                                                                offset_t['azimuth/units_s'].strip ()))
            
            #   Das name comes from array table line
            das = array_t['das/serial_number_s']
            #   Set current das group
            EX.ph5_g_receivers.setcurrent (DASS[das])
            #   Get time correction table line
            if not NOTIMECORRECT :
                time_t = get_time (Time_t, das, start_epoch + rvs)
            else :
                time_t = None
            
            #   Set up SEGYFactory.Ssegy
            sf.set_array_t (array_t)
            sf.set_offset_t (offset_t)
            sf.set_line_sequence (line_seq)
            #   Set extended header type
            sf.set_ext_header_type (EXT)
            
            #   Read the data from the ph5 file
            data = cut (start_epoch + rvs, stop_epoch + rvs, Das_t, time_t, Response_t, Receiver_t, sf)
            if len (data) == [] :
                logging.info ("Read zero samples.")
                continue
            
            if EVENT_NUMBER :
                temppath = os.path.join (OUTPATH, EVENT_NUMBER)
                if not os.path.exists (temppath) :
                    os.makedirs (temppath)
                    os.chmod(temppath, 0777)
                    
            else :
                temppath = OUTPATH
            
            if not fd :
                filename = os.path.join (temppath, "%s.01.SGY" % base)
                i = 0
                while os.path.exists (filename) :
                    i += 1
                    tmp = filename[:-6]
                    filename = "%s%02d.SGY" % (tmp, i)
                    
                fd = open (filename, 'w+')
                write_segy_hdr (data, fd, sf, num_traces)
            else :
                write_segy (data, fd, sf)
                os.chmod(filename, 0777)
        if fd : fd.close ()

    logging.info ("Done.\n")
#
#
#
def process_all () :
    '''   Dump all DAS data in ph5 file to PASSCAL SEGY   '''
    global DASS, UTM
    #   Get experiment nickname from Experiment table
    experiment_t = EXPERIMENT_T.rows[0]
    nickname = experiment_t['nickname_s'].strip ()    
    #   Read all das groups
    DASS = read_das_groups ()
    #   Do we want to extract only a single DAS? 
    if DAS :
        if DASS.has_key (DAS) :
            tmp_DASS = DASS[DAS]
            DASS = {}
            DASS[DAS] = tmp_DASS
        else :
            logging.error ("Error: No data found for DAS %s" % DAS)
            sys.exit (-1)
            
    #   Get Array tables keyed on array names
    Array_ts = read_sort_arrays ()
    #   Key array_t rows by das
    Array_t_by_das = key_array_t_by_das (Array_ts)
    #   Do we want to extract only a single station
    if STA :
        tmp_DASS = {}
        arrays = Array_ts.keys ()
        #   Loop through all the Array_t_xxx array tables
        for a in arrays :
            Array_t = Array_ts[a]
            #   Loop through the rows of the table
            for r in Array_t.rows :
                if STA == r['id_s'] :
                    d = r['das/serial_number_s']
                    if DASS.has_key (d) :
                        tmp_DASS[d] = DASS[d]
                    else :
                        logging.error ("Error: No data found for station %s array %s" % (STA, a[-3:]))
                        
        DASS = tmp_DASS
    
    Time_t = read_time_table ()
    if CHECK : check_table (Time_t, '/Experiment_g/Receivers_g/Time_t')
    Receiver_t = read_receiver_table ()
    if CHECK : check_table (Receiver_t, '/Experiment_g/Receivers_g/Receiver_t')
    Response_t = read_response_table ()
    if CHECK : check_table (Response_t, '/Experiment_g/Responses_g/Response_t')
    #   Process DAS's in alphabetical order
    dass = DASS.keys (); dass.sort ()
    fd = None
    
    for das in dass :
        #   Read DAS table for this DAS
        EX.ph5_g_receivers.setcurrent (DASS[das])
        das_r, das_keys = EX.ph5_g_receivers.read_das ()
        Das_t = rows_keys (das_r, das_keys)
        if CHECK : check_table (Das_t, '/Experiment_g/Receivers_g/Das_g_%s/Das_t' % das)
        seq = 0
        logging.info ("Extracting PASSCAL SEGY for DAS: %s" % das)
        #   Loop through Das_t table for this das
        for das_t in Das_t.rows :
            #   Don't read this channel
            if CHANNEL :
                if CHANNEL != das_t['channel_number_i'] : continue
                
            cut_start = SEGYFactory.fepoch (das_t['time/epoch_l'], das_t['time/micro_seconds_i'])
            sr = das_t['sample_rate_i'] / float (das_t['sample_rate_multiplier_i'])
            cut_stop = cut_start + (das_t['sample_count_i'] / sr)
            
            #   Do we keep this jd
            if DOY :
                cut_start_doy = time.gmtime (int (cut_start))[7]
                cut_stop_doy = time.gmtime (int (cut_stop))[7]
                if not (int (cut_start_doy) in DOY) and not (int (cut_stop_doy) in DOY) : continue
                #if not int (cut_stop_doy) in DOY : continue
                
            array_t = None
            #   Try to find array_t row for this das_t entry
            if Array_t_by_das.has_key (das) :
                keyed_array_t = Array_t_by_das[das]
                for array_t in keyed_array_t :
                    array_deploy = SEGYFactory.fepoch (array_t['deploy_time/epoch_l'], array_t['deploy_time/micro_seconds_i'])
                    array_pickup = SEGYFactory.fepoch (array_t['pickup_time/epoch_l'], array_t['pickup_time/micro_seconds_i'])
                    #   Found, else defaults to last array_t read
                    if cut_start >= array_deploy and cut_start <= array_pickup : break
                    
            #   DAS not assigned to an array
            if not array_t :
                array_t = Array_t_by_das['DUMMY'][0]
                array_t['das/serial_number_s'] = das
                array_t['id_s'] = das
                array_t['description_s'] = "DAS not assigned to an array."
                
            #   Write station information to log file
            logging.info ("%d" % seq); seq += 1
            logging.info ("Trace start: %s Trace stop: %s" % (time.ctime (cut_start), time.ctime (cut_stop)))
            logging.info ("Start epoch: %015.3f Stop epoch: %015.3f" % (cut_start, cut_stop))
            logging.info ("Station_id: %s DAS: %s Channel: %d" % (array_t['id_s'],
                                                                  array_t['das/serial_number_s'], 
                                                                  array_t['channel_number_i']))
                          
            logging.info ("%s" % array_t['description_s'])
            
            logging.info ("Lat: %f Lon: %f Elev: %f %s" % (array_t['location/Y/value_d'],
                                                           array_t['location/X/value_d'],
                                                           array_t['location/Z/value_d'],
                                                           array_t['location/Z/units_s'].strip ()))
                                
            if not NOTIMECORRECT :
                time_t = get_time (Time_t, das, cut_start)
            else :
                time_t = None

            #   Get SEGYFactory assign sort_t and event_t to none
            sf = SEGYFactory.Ssegy (None, None, utm = UTM)
            #   We need a start time
            sf.set_cut_start_epoch (cut_start)
            #   Assign, a possibly DUMMY, array_t
            sf.set_array_t (array_t)
            #   Set extended header type
            sf.set_ext_header_type (EXT)
            sf.set_break_standard (BREAK_STANDARD)
            
            #   Base name for files
            if CHANNEL :
                chan_name = CHAN_MAP[CHANNEL]
            else :
                chan_name = CHAN_MAP[das_t['channel_number_i']]
             
            tdoy = TimeDOY.TimeDOY (year=None, 
                                    month=None, 
                                    day=None, 
                                    hour=0, 
                                    minute=0, 
                                    second=0, 
                                    microsecond=0, 
                                    doy=None, 
                                    epoch=cut_start, 
                                    dtobject=None)   
            #   Get a base for the out file name
            base = "%s_%s_%s_%s_00001.psgy" % (nickname, tdoy.getPasscalTime (ms=True), das, chan_name)
            doy = base.split (':')[1]
            #   Let's put these in day directories
            rdir = 'R' + doy
            base = base.replace (':', '_'); base = base.replace (' ', '_')
            #   Try to cut the data trace
            data = cut (cut_start, cut_stop, rows_keys ([das_t], das_keys), time_t, Response_t, Receiver_t, sf)
            if len (data) == [] :
                logging.info ("Read zero samples.")
                continue
            
            rdir = os.path.join (OUTPATH, rdir)
            if not os.path.exists (rdir) :
                os.makedirs (rdir)
                os.chmod(rdir, 0777)
                
            #   Create the directories and write a unique file name
            filename = os.path.join (rdir, base)
            if fd : fd.close ()
            i = 0
            while os.path.exists (filename) :
                i += 1
                tmp = filename[:-10]
                filename = "%s%05d.psgy" % (tmp, i)
                
            fd = open (filename, 'w+')
            write_psgy (data, fd, sf)
            os.chmod(filename, 0777)
    logging.info ("Done.\n")
            
def process_error () :
    sys.stderr.write ("Error: One of the following options is required:\n\t--eventnumber\n\t--allevents\n\t--starttime\n\t--all\n\nTry: --help")
    sys.exit (-1)
    
STATE = [ process_event, process_start, process_all, process_error, process_all_events ]

if __name__ == '__main__' :
    s = get_args ()
    logging.info ("%s: %s" % (PROG_VERSION, sys.argv))
    initialize_ph5 ()
    EXPERIMENT_T = read_experiment_table ()
    if CHECK : check_table (EXPERIMENT_T, '/Experiment_g/Experiment_t')
    try :
        experiment_t = EXPERIMENT_T.rows[0]
        logging.info ("Experiment: %s" % experiment_t['longname_s'].strip ())
        logging.info ("Summary: %s" % experiment_t['summary_paragraph_s'].strip ())
    except :
        logging.error ("Error: Critical information missing from /Experiment_g/Experiment_t. Exiting.")
        sys.exit (-1)
        
    STATE[s]()
    logging.shutdown ()
    sys.stderr.write ("Done\n")