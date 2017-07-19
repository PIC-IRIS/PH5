#!/usr/bin/env pnpython4
# -*- coding: iso-8859-15 -*-
#
#   Read Fairfield SEG-D (Version 1.6) from the Sweetwater experiment.
#   Write PH5
#
#   Steve Azevedo, May 2014
#   Modified to read SEG-D from 3C's, July 2016
#

PROG_VERSION = "2017.114.1 Developmental"

MAX_PH5_BYTES = 1073741824 * 100.   #   100 GB (1024 X 1024 X 1024 X 2)

import os, sys, logging, time, json, re
from math import modf
from ph5.core import experiment, columns, segdreader
from pyproj import Proj, transform

os.environ['TZ'] = 'GMT'
time.tzset ()

APPEND = 1   #   Number of SEG-D events to append to make 1 ph5 event.

DAS_INFO = {}
MAP_INFO = {}
#   Current raw file processing
F = None
#   RE for mini files
miniPH5RE = re.compile (".*miniPH5_(\d\d\d\d\d)\.ph5")

#LSB = 6.402437066e-6   #   From Malcolm UCSD
LSB00 = 2500. / (2**23)   #   0dB
LSB12 = 625. / (2**23)    #   12dB
LSB24 = 156. / (2**23)    #   24dB
LSB36 = 39. / (2**23)     #   36dB = 39mV full scale
LSB = LSB36

LSB_MAP = {36:LSB36, 24:LSB24, 12:LSB12, 0:LSB00}

#   Manufacturers codes
FAIRFIELD=20
OTHER=0
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
    
class Trace (object) :
    __slots__ = ("trace", "headers")
    def __init__ (self, trace, headers) :
        self.trace = trace
        self.headers = headers

def read_infile (infile) :
    '''   Read list of input SEG-D files from a file   '''
    global FILES
    
    def fn_sort (a, b) :
        #print os.path.basename (a), os.path.basename (b)
        return cmp (os.path.basename (a), os.path.basename (b))
    
    try :
        fh = file (infile)
    except :
        sys.stderr.write ("Warning: Failed to open %s\n" % infile)
        return
        
    while True :
        line = fh.readline ()
        if not line : break
        line = line.strip ()
        if not line : continue
        if line[0] == '#' : continue
        FILES.append (line) 
        
    FILES.sort (fn_sort)
        
def get_args () :
    global PH5, FILES, EVERY, NUM_MINI, TSPF, UTM, FIRST_MINI, APPEND, MANUFACTURERS_CODE
    
    TSPF = False
    
    from optparse import OptionParser
    oparser = OptionParser ()
    
    oparser.usage = "Version: {0} Usage: segd2ph5 [options]".format (PROG_VERSION)
    
    oparser.add_option ("-r", "--raw", dest = "rawfile",
                        help="Fairfield SEG-D v1.6 file.", metavar="raw_file")    
    
    oparser.add_option ("-f", action="store", dest="infile", type="string",
                        help = "File containing list of Fairfield SEG-D v1.6 file names.")
    
    oparser.add_option ("-n", "--nickname", dest = "outfile",
                        help="The ph5 file prefix (experiment nick name).",
                        metavar = "output_file_prefix")
    
    oparser.add_option ("-U", "--UTM", dest = "utm_zone",
                        help="Locations in SEG-D file are UTM, --UTM=utmzone.",
                        type = 'int', default = 0,
                        metavar = "utm_zone")    
    
    oparser.add_option ("-T", "--TSPF", dest = "texas_spc",
                        help="Locations are in texas state plane coordinates.",
                        action='store_true', default=False)
    
    oparser.add_option ("-M", "--num_mini", dest = "num_mini",
                        help = "Create a given number of miniPH5_xxxxx.ph5 files.",
                        metavar = "num_mini", type = 'int', default = None)
    
    oparser.add_option ("-S", "--first_mini", dest = "first_mini",
                        help = "The index of the first miniPH5_xxxxx.ph5 file.",
                        metavar = "first_mini", type = 'int', default = 1)
    
    oparser.add_option ("-c", "--combine", dest = "combine",
                        help = "Combine this number if SEG-D traces to one PH5 trace.",
                        metavar = "combine", type = 'int', default=APPEND)
    
    oparser.add_option ("-E", "--allevents", action="store_true", dest="all_events",
                        default=False, metavar="all_events")
    
    oparser.add_option ("--manufacturers_code", dest="manufacturers_code",
                        help="Manufacturers code. Defaults to 20 for Fairfield. Most likely will not work for SEG-D written by other data loggers,",
                        type='int', default=FAIRFIELD)
    
    options, args = oparser.parse_args ()

    FILES = []
    PH5 = None
    
    EVERY = options.all_events
    NUM_MINI = options.num_mini
    FIRST_MINI = options.first_mini
    UTM = options.utm_zone
    TSPF = options.texas_spc
    APPEND = options.combine
    MANUFACTURERS_CODE = options.manufacturers_code
    
    if options.infile != None :
        read_infile (options.infile)
        
    elif options.rawfile != None :
        FILES.append (options.rawfile)    
    
    if len (FILES) == 0 :
        sys.stderr.write ("Error: No input file given.\n")
        sys.exit ()
        
    #   Set output file
    if options.outfile != None :
        PH5 = options.outfile
    else :
        sys.stderr.write ("Error: No outfile (PH5) given.\n")
        sys.exit ()   
        
    logging.basicConfig (
        filename = os.path.join ('.', "segd2ph5.log"),
        format = "%(asctime)s %(message)s",
        level = logging.INFO
    )
    #   Need to process in order: R309_674.1.0.rg16, 309 == line, 674 = receiver point, 1 = first file
    #   Sorted where the file list is read...
    #FILES.sort ()

def initializeExperiment () :
    global EX
    
    EX = experiment.ExperimentGroup (nickname = PH5)
    EDIT = True
    EX.ph5open (EDIT)
    EX.initgroup ()
    
def openPH5 (filename) :
    '''   Open PH5 file, miniPH5_xxxxx.ph5   '''
    try :
        if EXREC.ph5.isopen :
            if EXREC.filename != filename :
                EXREC.ph5close ()
            else :
                return EXREC
    except :
        pass    
    #sys.stderr.write ("***   Opening: {0} ".format (filename))
    exrec = experiment.ExperimentGroup (nickname = filename)
    exrec.ph5open (True)
    exrec.initgroup ()
    return exrec

def update_index_t_info (starttime, samples, sps) :
    '''   Update info that gets saved in Index_t   '''
    global DAS_INFO, MAP_INFO
    
    ph5file = EXREC.filename
    ph5path = '/Experiment_g/Receivers_g/' + EXREC.ph5_g_receivers.current_g_das._v_name
    ph5map = '/Experiment_g/Maps_g/' + EXREC.ph5_g_maps.current_g_das._v_name
    das = ph5path[32:]
    stoptime = starttime + (float (samples) / float (sps))
    di = Index_t_Info (das, ph5file, ph5path, starttime, stoptime)
    dm = Index_t_Info (das, ph5file, ph5map, starttime, stoptime)
    if not DAS_INFO.has_key (das) :
        DAS_INFO[das] = []
        MAP_INFO[das] = []
        
    DAS_INFO[das].append (di)
    MAP_INFO[das].append (dm)
    logging.info ("DAS: {0} File: {1} First Sample: {2} Last Sample: {3}".format (das, ph5file, time.ctime (starttime), time.ctime (stoptime)))

def update_external_references () :
    '''   Update external references in master.ph5 to miniPH5 files in Receivers_t    '''
    global F
    #sys.stderr.write ("Updating external references...\n"); sys.stderr.flush ()
    logging.info ("Updating external references...")
    n = 0
    for i in INDEX_T_DAS.rows :
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
            #print "DAS nuke ", e.message
            
        #   Re-create node
        try :
            EX.ph5.create_external_link ('/Experiment_g/Receivers_g', external_group, target)
            n += 1
        except Exception, e :
            #pass
            sys.stderr.write ("{0}\n".format (e.message))
            
        #sys.exit ()
    #sys.stderr.write ("done, {0} das nodes recreated.\n".format (n))

    logging.info ("done, {0} das nodes recreated.\n".format (n))
    
    n = 0
    for i in INDEX_T_MAP.rows :
        #   XXX
        #keys = i.keys ()
        #keys.sort ()
        #for k in keys :
            #print k, i[k]
            
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
            #print "MAP nuke ", e.message
            
        #   Re-create node
        try :
            EX.ph5.create_external_link ('/Experiment_g/Maps_g', external_group, target)
            n += 1
        except Exception, e :
            #pass
            sys.stderr.write ("{0}\n".format (e.message))
            
        #sys.exit ()
    #sys.stderr.write ("done, {0} map nodes recreated.\n".format (n))
    logging.info ("done, {0} map nodes recreated.\n".format (n))   
    
##@profile
#def get_current_data_only (size_of_data, das = None) :
    #'''   Return opened file handle for data only PH5 file that will be
          #less than MAX_PH5_BYTES after raw data is added to it.
    #'''
    
    #newest = 0
    #newestfile = ''
    ##   Get the most recent data only PH5 file or match DAS serialnumber
    #for index_t in INDEX_T_DAS.rows :
        ##   This DAS already exists in a ph5 file
        #if index_t['serial_number_s'] == str (das) :
            #newestfile = index_t['external_file_name_s']
            #newestfile = newestfile.replace ('.ph5', '')
            #newestfile = newestfile.replace ('./', '')
            #return openPH5 (newestfile)
        ##   Find most recent ph5 file
        #if index_t['time_stamp/epoch_l'] > newest :
            #newest = index_t['time_stamp/epoch_l']
            #newestfile = index_t['external_file_name_s']
            #newestfile = newestfile.replace ('.ph5', '')
            #newestfile = newestfile.replace ('./', '')
            
    ##print newest, newestfile
    #if not newestfile :
        ##   This is the first file added
        #return openPH5 ('miniPH5_00001')
    
    #size_of_exrec = os.path.getsize (newestfile + '.ph5')
    ##print size_of_data, size_of_exrec, size_of_data + size_of_exrec, MAX_PH5_BYTES
    #if (size_of_data + size_of_exrec) > MAX_PH5_BYTES :
        #newestfile = "miniPH5_{0:05d}".format (int (newestfile[8:13]) + 1)

    
    #return openPH5 (newestfile)


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
            
    das = str (das)
    newest = 0
    newestfile = ''
    #   Get the most recent data only PH5 file or match DAS serialnumber
    n = 0
    for index_t in INDEX_T_DAS.rows :
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
        if (int (newestfile[8:13]) - fm) < NUM_MINI :
            newestfile = "miniPH5_{0:05d}".format (int (newestfile[8:13]) + 1)
        else :
            small = sstripp (smallest ())
            return openPH5 (small)
        
    elif (size_of_data + size_of_exrec) > MAX_PH5_BYTES :
        newestfile = "miniPH5_{0:05d}".format (int (newestfile[8:13]) + 1)

    return openPH5 (newestfile)

def getLOG () :
    '''   Create a open a new and unique header file under Maps_g/Das_g_
                                                                 /Sta_g_
                                                                 /Evt_g_
                                                                         /Hdr_a_
    '''
    current_das = EXREC.ph5_g_receivers.get_das_name ()
    g = EXREC.ph5_g_maps.newdas ('Das_g_', current_das)
    EXREC.ph5_g_maps.setcurrent (g)
    try :
        name = EXREC.ph5_g_maps.nextarray ('Hdr_a_')
    except TypeError :
        return None
    
    log_array = EXREC.ph5_g_maps.newearray (name, description = "SEG-D header entries: {0}".format (Das))
    
    return log_array, name

def process_traces (rh, th, tr) :
    '''
        Inputs:
           rh -> reel headers
           th -> first trace header
           tr -> trace data
    '''
    
    def process_das () :
        global LSB
        '''
        '''
        p_das_t = {}
        '''  Das_t
                receiver_table_n_i
                response_table_n_i
                time_table_n_i
                time/
                    type_s      
                    epoch_l
                    ascii_s
                    micro_seconds_i
                event_number_i
                channel_number_i
                sample_rate_i
                sample_rate_multiplier_i
                sample_count_i
                stream_number_i
                raw_file_name_s
                array_name_data_a
                array_name_SOH_a
                array_name_event_a
                array_name_log_a 
        '''
        #   Check to see if group exists for this das, if not build it
        das_g, das_t, receiver_t, time_t = EXREC.ph5_g_receivers.newdas (str (Das))
        #   Build maps group (XXX)
        map_g = EXREC.ph5_g_maps.newdas ('Das_g_', str (Das))  
        if rh.general_header_block_1.chan_sets_per_scan == 1 :
            #   Single channel
            p_das_t['receiver_table_n_i'] = 0   #   0 -> Z
        elif  rh.general_header_block_1.chan_sets_per_scan == 3 :
            #   1 (N node) -> 1 (N PH5), 2 (E Node)-> 2 (E PH5), 3 (Z Node) -> 0 (Z PH5)
            M = {1:1, 2:2, 3:0}
            p_das_t['receiver_table_n_i'] = M[th.trace_header.channel_set]
        else :
            p_das_t['receiver_table_n_i'] = 0   #   0 -> Z
            logging.warn ("Header channel set: {0}. Check Receiver_t entries!".format (th.trace_header.channel_set))
            
        p_das_t['response_table_n_i'] = None
        p_das_t['time_table_n_i'] = 0
        p_das_t['time/type_s'] = 'BOTH'
        #trace_epoch = th.trace_header_N[2].gps_tim1 * 4294967296 + th.trace_header_N[2].gps_tim2
        try :
            trace_epoch = th.trace_header_N[2].shot_epoch
        except Exception as e :
            logging.warn ("Failed to read shot epoch: {0}.".format (e.message))
            trace_epoch = 0.
            
        f, i = modf (trace_epoch / 1000000.)
        p_das_t['time/epoch_l'] = int (i)
        p_das_t['time/ascii_s'] = time.ctime (p_das_t['time/epoch_l'])
        p_das_t['time/micro_seconds_i'] = int (f * 1000000.)
        p_das_t['event_number_i'] = th.trace_header_N[1].shot_point
        p_das_t['channel_number_i'] = th.trace_header.channel_set
        p_das_t['sample_rate_i'] = SD.sample_rate
        p_das_t['sample_rate_multiplier_i'] = 1
        p_das_t['sample_count_i'] = len (tr)
        p_das_t['stream_number_i'] = 1
        p_das_t['raw_file_name_s'] = os.path.basename (SD.name ())
        p_das_t['array_name_data_a'] = EXREC.ph5_g_receivers.nextarray ('Data_a_')
        #p_das_t['array_name_SOH_a'] = None
        #p_das_t['array_name_event_a'] = None
        #p_das_t['array_name_log_a'] = None
        p_response_t = {}
        '''
            n_i
            gain/
                units_s
                value_i
            bit_weight/
                units_s       
                value_d        
            response_file_a
        '''
        try :
            LSB = LSB_MAP[th.trace_header_N[3].preamp_gain_db]
            n_i = RESP.match (LSB, th.trace_header_N[3].preamp_gain_db)
        except Exception as e :
            n_i = 0
        p_response_t['gain/units_s'] = 'dB'
        try :
            p_response_t['gain/value_i'] = th.trace_header_N[3].preamp_gain_db
        except Exception as e :
            logging.warn ("Failed to read trace pre amp gain: {0}.".format (e.message))
            p_response_t['gain/value_i'] = 0.
            p_response_t['gain/units_s'] = 'Unknown'
            
        p_response_t['bit_weight/units_s'] = 'mV/count'
        p_response_t['bit_weight/value_d'] = LSB
        if n_i < 0 :
            n_i = RESP.next_i ()
            p_response_t['n_i'] = n_i
            EX.ph5_g_responses.populateResponse_t (p_response_t)
            RESP.update ()
        p_das_t['response_table_n_i'] = n_i
        EXREC.ph5_g_receivers.populateDas_t (p_das_t)
        des = "Epoch: " + str (p_das_t['time/epoch_l']) + " Channel: " + str (p_das_t['channel_number_i'])
        #   Write trace data here
        try :
            #   Convert to counts
            #print tr.max (), tr.min ()
            tr_counts = tr / LSB
            EXREC.ph5_g_receivers.newarray (p_das_t['array_name_data_a'], tr_counts, dtype = 'int32', description = des)
        except Exception as e :
            #   Failed, leave as float
            #for x in tr : print x/LSB
            #print e.message
            sys.stderr.write ("Warning: Could not convert trace to counts. max: {1}, min {2}\n{0}".format (e.message, tr.max (), tr.min ()))
            p_response_t['bit_weight/value_d'] = 1.
            EXREC.ph5_g_receivers.newarray (p_das_t['array_name_data_a'], tr, dtype = 'float32', description = des)
        #
        update_index_t_info (p_das_t['time/epoch_l'] + (float (p_das_t['time/micro_seconds_i']) / 1000000.), p_das_t['sample_count_i'], p_das_t['sample_rate_i'] / p_das_t['sample_rate_multiplier_i'])
        
    def process_array () :
        #global DN
        p_array_t = {}
        
        def seen_sta () :
            if not ARRAY_T.has_key (line) :
                return False
            elif not ARRAY_T[line].has_key (Das) :
                return False
            elif ARRAY_T[line][Das].has_key (chan_set) :
                chans = ARRAY_T[line][Das].keys ()                   #   All channels seen
                if not ARRAY_T[line][Das][chan_set] :
                    return False
                else :
                    return True
            
        '''
            deploy_time/
                type_s
                epoch_l
                ascii_s
                micro_seconds_i
            pickup_time/
                type_s
                epoch_l
                ascii_s
                micro_seconds_i
            id_s
            das/
                manufacturer_s
                model_s
                serial_number_s
                notes_s
            sensor/
                manufacturer_s
                model_s
                serial_number_s
                notes_s
            location/
                coordinate_system_s
                projection_s
                ellipsoid_s
                X/
                    units_s
                    value_d
                Y/
                    units_s
                    value_d
                Z/
                    units_s
                    value_d
                description_s
            channel_number_i
            description_s
            sample_rate_i
            sample_rate_multiplier_i
        '''
        '''
        Band Code:
           1000 <= G < 5000
           250  <= D < 1000
           80   <= E < 250
           10   <= S < 80
        '''
        if SD.sample_rate >= 1000 :
            band_code = 'G'
        elif SD.sample_rate >= 250 and SD.sample_rate < 1000 :
            band_code = 'D'
        elif SD.sample_rate >= 80 and SD.sample_rate < 250 :
            band_code = 'E'
        elif SD.sample_rate >= 10 and SD.sample_rate < 80 :
            band_code = 'S'
        else :
            band_code = 'X'
        '''
        Instrument Code:
           Changed from H to P at request from Akram
        '''
        instrument_code = 'P'
        '''
        Orientation Code:
           chan 1 -> N Changed to '1'
           chan 2 -> E Changed to '2'
           chan 3 -> Z
        or
           chan 1 -> Z
        '''
        if SD.chan_sets_per_scan == 3 :
            OM = { 1:'1', 2:'2', 3:'Z' }
        elif SD.chan_sets_per_scan == 1 :
            OM = { 1:'Z' }
        else :
            OM = None
        if OM == None :
            orientation_code = th.trace_header.channel_set
        else :
            orientation_code = OM[th.trace_header.channel_set]
        #for cs in range (SD.chan_sets_per_scan) :
        p_array_t['seed_band_code_s'] = band_code
        p_array_t['seed_instrument_code_s'] = instrument_code
        p_array_t['seed_orientation_code_s'] = orientation_code
        p_array_t['sample_rate_i'] = SD.sample_rate
        p_array_t['sample_rate_multiplier_i'] = 1
        p_array_t['deploy_time/type_s'] = 'BOTH'
        try :
            f, i = modf (rh.extended_header_1.epoch_deploy / 1000000.)
        except Exception as e :
            logging.warn ("Failed to read extended header 1 deploy epoch: {0}.".format (e.message))
            f = i = 0.
        p_array_t['deploy_time/epoch_l'] = int (i)
        p_array_t['deploy_time/ascii_s'] = time.ctime (int(i))
        p_array_t['deploy_time/micro_seconds_i'] = int (f * 1000000.)
        p_array_t['pickup_time/type_s'] = 'BOTH'
        try :
            f, i = modf (rh.extended_header_1.epoch_pickup / 1000000.)
        except Exception as e :
            logging.warn ("Failed to read extended header 1 pickup epoch: {0}.".format (e.message))
            f = i = 0.
        p_array_t['pickup_time/epoch_l'] = int (i)
        p_array_t['pickup_time/ascii_s'] = time.ctime (int(i))
        p_array_t['pickup_time/micro_seconds_i'] = int (f * 1000000.)
        p_array_t['id_s'] = Das.split ('X')[1]
        p_array_t['das/manufacturer_s'] = 'FairfieldNodal'
        DM = { 1:'ZLAND 1C', 3:"ZLAND 3C" }
        try :
            p_array_t['das/model_s'] = DM[SD.chan_sets_per_scan]
        except Exception as e :
            logging.warn ("Failed to read channel sets per scan: {0}.".format (e.message))
            p_array_t['das/model_s'] = 'zland-[13]C'
        p_array_t['das/serial_number_s'] = Das
        p_array_t['das/notes_s'] = "manufacturer and model not read from data file."
        p_array_t['sensor/manufacturer_s'] = 'Geo Space'
        p_array_t['sensor/model_s'] = 'GS-30CT'
        p_array_t['sensor/notes_s'] = "manufacturer and model not read from data file."
        if TSPF :
            p_array_t['location/description_s'] = "Converted from Texas State Plane FIPS zone 4202"
        elif UTM :
            p_array_t['location/description_s'] = "Converted from UTM Zone {0}".format (UTM)
        else :
            p_array_t['location/description_s'] = "Read from SEG-D as is."
            
        p_array_t['location/coordinate_system_s'] = 'geographic'
        p_array_t['location/projection_s'] = 'WGS84'
        p_array_t['location/X/units_s'] = 'degrees'
        p_array_t['location/X/value_d'] = LON
        p_array_t['location/Y/units_s'] = 'degrees'
        p_array_t['location/Y/value_d'] = LAT
        p_array_t['location/Z/units_s'] = 'unknown'
        try :
            p_array_t['location/Z/value_d'] = th.trace_header_N[4].receiver_point_depth_final / 10.
        except Exception as e :
            logging.warn ("Failed to read receiver point depth: {0}.".format (e.message))
            p_array_t['location/Z/value_d'] = 0.
            
        p_array_t['channel_number_i'] = th.trace_header.channel_set
        #p_array_t['description_s'] = str (th.trace_header_N[4].line_number)
        try :
            p_array_t['description_s'] = "DAS: {0}, Node ID: {1}".format (Das, rh.extended_header_1.id_number)
        except Exception as e :
            logging.warn ("Failed to read extended header 1 ID number: {0}.".format (e.message))
            pass
        
        try :
            line = th.trace_header_N[4].line_number
        except Exception as e :
            logging.warn ("Failed to read line number: {0}.".format (e.message))
            line = 0
            
        chan_set = th.trace_header.channel_set
        if not ARRAY_T.has_key (line) :
            ARRAY_T[line] = {}
        if not ARRAY_T[line].has_key (Das) :
            ARRAY_T[line][Das] = {}
        if not ARRAY_T[line][Das].has_key (chan_set) :
            ARRAY_T[line][Das][chan_set] = []
        
        if not seen_sta () :  
            ARRAY_T[line][Das][chan_set].append (p_array_t)
            #if rh.general_header_block_1.chan_sets_per_scan == len (ARRAY_T[line].keys ()) :
                #DN = True
        
    def process_reel_headers () :
        global RH
        '''   Save receiver record header information in Maps_g/Das_g_xxxxxxx/Hdr_a_xxxx file   '''
        def process (hdr, header_type) :
            l = [{'FileType':'SEG-D', 'HeaderType':header_type},hdr]
            log_array.append (json.dumps (l, sort_keys=True, indent=4).split ('\n'))
            
        log_array, log_name = getLOG ()
        #   General header 1
        process (rh.general_header_block_1, 'General 1')
        #   General header 1
        process (rh.general_header_block_2, 'General 2')
        #   General header N
        for i in range (len (rh.general_header_block_N)) :
            ht = "General {0}".format (i + 3)
            process (rh.general_header_block_N[i], ht)
        #   Channel set descriptors
        for i in range (len (rh.channel_set_descriptor)) :
            ht = "Channel Set {0}".format (i + 1)
            process (rh.channel_set_descriptor, ht)
        #   Extended header 1
        process (rh.extended_header_1, "Extended 1")
        #   Extended header 2
        process (rh.extended_header_2, "Extended 2")
        #   Extended header 3
        process (rh.extended_header_3, "Extended 3")
        #   Extended header 4 - n
        for i in range (len (rh.extended_header_4)) :
            ht = "Extended 4 ({0})".format (i + 1)
            process (rh.extended_header_4[i], ht)
        #   External header
        process (rh.external_header, "External Header")
        #   External header shot
        for i in range (len (rh.external_header_shot)) :
            ht = "External Shot {0}".format (i + 1)
            process (rh.external_header_shot[i], ht)
        RH = True
        
    def process_trace_header () :
        '''   Save trace header information in Maps_g/Das_g_xxxxxxx/Hdr_a_xxxx file   '''
        def process (hdr, header_type) :
            global TRACE_JSON
            l = [{'FileType':'SEG-D', 'HeaderType':'trace', 'HeaderSubType':header_type},hdr]
            TRACE_JSON.append (json.dumps (l, sort_keys=True, indent=4).split ('\n'))
            
        #log_array, log_name = getLOG ()
        
        process (th.trace_header, "Trace Header")
        for i in range (len (th.trace_header_N)) :
            ht = "Header N-{0}".format (i + 1)
            process (th.trace_header_N[i], ht)
        
    #
    #
    #
    #print "\tprocess das"
    #for cs in range (rh.chan_sets_per_scan) :
    process_das ()
    #if not DN : 
    #print "\tprocess array"
    process_array ()
    #print "\tprocess headers"
    if not RH :
        process_reel_headers ()
    #print "\tprocess trace header"    
    process_trace_header ()
    pass

def write_arrays (Array_t) :
    '''   Write /Experiment_g/Sorts_g/Array_t_xxx   '''
    def station_cmp (x, y) :
        return cmp (x['id_s'], y['id_s'])
    
    lines = Array_t.keys ()
    lines.sort ()
    #   Loop through arrays/lines
    for line in lines :
        #name = EX.ph5_g_sorts.nextName ()
        name = "Array_t_{0:03d}".format (int(line))
        a = EX.ph5_g_sorts.newArraySort (name)
        stations = Array_t[line].keys ()
        stations.sort ()
        Array = {}
        n = 0
        #   Loop through stations
        for station in stations :
            chan_sets = Array_t[line][station].keys ()
            chan_sets.sort ()
            #   Loop through channel sets
            for chan_set in chan_sets :
                try :
                    for array_t in Array_t[line][station][chan_set] :
                        columns.populate (a, array_t)
                except Exception as e :
                    print e.message
            
def writeINDEX () :
    '''   Write /Experiment_g/Receivers_g/Index_t   '''
    global DAS_INFO, MAP_INFO, INDEX_T_DAS, INDEX_T_MAP
    
    dass = DAS_INFO.keys ()
    dass.sort ()
    
    for das in dass :
        di = {}
        mi = {}
        start = sys.maxint
        stop = 0.        
        dm = [(d, m) for d in DAS_INFO[das] for m in MAP_INFO[das]]
        for d, m in dm :
            di['external_file_name_s'] = d.ph5file
            mi['external_file_name_s'] = m.ph5file
            di['hdf5_path_s'] = d.ph5path
            mi['hdf5_path_s'] = m.ph5path
            di['serial_number_s'] = das
            mi['serial_number_s'] = das
            if d.startepoch < start :
                start = d.startepoch
                
            if d.stopepoch > stop :
                stop = d.stopepoch
                
        di['time_stamp/epoch_l'] = int (time.time ())
        mi['time_stamp/epoch_l'] = int (time.time ())
        di['time_stamp/micro_seconds_i'] = 0
        mi['time_stamp/micro_seconds_i'] = 0
        di['time_stamp/type_s'] = 'BOTH'
        mi['time_stamp/type_s'] = 'BOTH'
        di['time_stamp/ascii_s'] = time.ctime (di['time_stamp/epoch_l'])
        mi['time_stamp/ascii_s'] = time.ctime (mi['time_stamp/epoch_l'])
        
        di['start_time/epoch_l'] = int (modf (start)[1])
        mi['start_time/epoch_l'] = int (modf (start)[1])
        di['start_time/micro_seconds_i'] = int (modf (start)[0] * 1000000)
        mi['start_time/micro_seconds_i'] = int (modf (start)[0] * 1000000)
        di['start_time/type_s'] = 'BOTH'
        mi['start_time/type_s'] = 'BOTH'
        di['start_time/ascii_s'] = time.ctime (start)
        mi['start_time/ascii_s'] = time.ctime (start)
        
        di['end_time/epoch_l'] = modf (stop)[1]
        mi['end_time/epoch_l'] = modf (stop)[1]
        di['end_time/micro_seconds_i'] = int (modf (stop)[0] * 1000000)
        mi['end_time/micro_seconds_i'] = int (modf (stop)[0] * 1000000)
        di['end_time/type_s'] = 'BOTH'
        mi['end_time/type_s'] = 'BOTH'
        di['end_time/ascii_s'] = time.ctime (stop)
        mi['end_time/ascii_s'] = time.ctime (stop)
                
        EX.ph5_g_receivers.populateIndex_t (di)
        EX.ph5_g_maps.populateIndex_t (mi)
            
    rows, keys = EX.ph5_g_receivers.read_index ()
    INDEX_T_DAS = Rows_Keys (rows, keys)
    
    rows, keys = EX.ph5_g_maps.read_index ()
    INDEX_T_MAP = Rows_Keys (rows, keys)    
    
    DAS_INFO = {}
    MAP_INFO = {}
    
def txncsptolatlon (northing, easting) :
    '''
       Sweetwater
       Convert texas state plane coordinates in feet to 
       geographic coordinates, WGS84.
    '''
    #   Texas NC state plane feet Zone 4202
    sp = Proj (init='epsg:32038')
    #   WGS84, geographic
    wgs = Proj (init='epsg:4326', proj='latlong')
    #   Texas SP coordinates: survey foot is 1200/3937 meters
    lon, lat = transform (sp, wgs, easting * 0.30480060960121924, northing * 0.30480060960121924)
    
    return lat, lon

def utmcsptolatlon (northing, easting) :
    '''
       Mount Saint Helens
       Convert UTM to
       geographic coordinates, WGS84.
    '''
    #   UTM
    utmc = Proj (proj='utm', zone=UTM, ellps='WGS84')
    #   WGS84, geographic
    wgs = Proj (init='epsg:4326', proj='latlong')
    #
    lon, lat = transform (utmc, wgs, easting, northing)

    return lat, lon

def correct_append_number () :
    #from math import modf
    traces = SD.reel_headers.extended_header_2['number_records']
    x = traces % APPEND
    A = APPEND - x


def main():
    import time
    then = time.time ()
    from numpy import append as npappend
    
    def prof () :
        global RESP, INDEX_T_DAS, INDEX_T_MAP, SD, EXREC, MINIPH5, Das, SIZE, ARRAY_T, RH, LAT, LON, F, TRACE_JSON, APPEND
        
        MINIPH5 = None
        ARRAY_T = {}
        
        def get_das (sd) :
            #   Return line_station or das#[-9:]
            try :
                das = "{0}X{1}".format (sd.reel_headers.extended_header_3.line_number, 
                                        sd.reel_headers.extended_header_3.receiver_point)
            except Exception as e :
                try :
                    das = "{0}X{1}".format (sd.reel_headers.external_header.receiver_line, 
                                            sd.reel_headers.external_header.receiver_point)
                except Exception as e :
                    das = "sn" + str (sd.reel_headers.general_header_block_1.manufactures_sn)
                    if das == 0 :
                        das = "id" + str (sd.reel_headers.extended_header_1.id_number)[-9:]
                    
            return das
        
        def get_node (sd) :
            #   Return node part number, node id, and number of channels
            pn = None   #   Part Number
            id = None   #   Node ID
            nc = None   #   Number of channel sets
            try :
                nc = sd.reel_headers.general_header_block_1['chan_sets_per_scan']
                pn = sd.reel_headers.extended_header_1['part_number']
                id = sd.reel_headers.extended_header_1['id_number']
            except Exception as e :
                pass
            
            return pn, id, nc
            
        def print_container (container) :
            keys = container.keys ()
            for k in keys :
                print k, container[k]
                
            print '-' * 80    
        
        get_args ()
        
        initializeExperiment ()
        logging.info ("segd2ph5 {0}".format (PROG_VERSION))
        logging.info ("{0}".format (sys.argv))
        if len (FILES) > 0 :
            RESP = Resp (EX.ph5_g_responses)
            rows, keys = EX.ph5_g_receivers.read_index ()
            INDEX_T_DAS = Rows_Keys (rows, keys)
            rows, keys = EX.ph5_g_maps.read_index ()
            INDEX_T_MAP = Rows_Keys (rows, keys)     
        
        for f in FILES :
            F = f
            traces = []
            TRACE_JSON = []
            try :
                SIZE = os.path.getsize (f)
            except Exception as e :
                sys.stderr.write ("Error: failed to read {0}, {1}. Skipping...\n".format (f, str (e.message)))
                logging.error ("Error: failed to read {0}, {1}. Skipping...\n".format (f, str (e.message)))
                continue
            
            SD = segdreader.Reader (infile=f)
            LAT = None; LON = None
            #DN = False; 
            RH = False
            #print "isSEGD"
            if not SD.isSEGD (expected_manufactures_code=MANUFACTURERS_CODE) :
                sys.stdout.write (":<Error>: {0}\n".format (SD.name ())); sys.stdout.flush ()
                logging.info ("{0} is not a Fairfield SEG-D file. Skipping.".format (SD.name ()))
                continue
        
            try :
                #print "general headers"
                SD.process_general_headers ()
                #print "channel sets"
                SD.process_channel_set_descriptors ()
                #print "extended headers"
                SD.process_extended_headers ()
                #print "external headers"
                SD.process_external_headers ()
            except segdreader.InputsError as e :
                sys.stdout.write (":<Error>: {0}\n".format ("".join (e.message))); sys.stdout.flush ()
                logging.info ("Error: Possible bad SEG-D file -- {0}".format ("".join (e.message)))
                continue
            
            #Das = (SD.reel_headers.extended_header_3.line_number * 1000) + SD.reel_headers.extended_header_3.receiver_point
            #APPEND = correct_append_number ()
            nleft = APPEND
            Das = get_das (SD)
            part_number, node_id, number_of_channels = get_node (SD)
            #
            EXREC = get_current_data_only (SIZE, Das)
            #sys.stderr.write ("Processing: {0}... Size: {1}\n".format (SD.name (), SIZE))
            sys.stdout.write (":<Processing>: {0}\n".format (SD.name ())); sys.stdout.flush ()
            logging.info ("Processing: {0}... Size: {1}\n".format (SD.name (), SIZE))
            if EXREC.filename != MINIPH5 :
                #sys.stderr.write ("Opened: {0}...\n".format (EXREC.filename))
                logging.info ("Opened: {0}...\n".format (EXREC.filename))
                logging.info ("DAS: {0}, Node ID: {1}, PN: {2}, Channels: {3}".format (Das, node_id, part_number, number_of_channels))
                MINIPH5 = EXREC.filename  
                
            n = 0
            trace_headers_list = []
            lat = None; lon = None
            while True :
                #
                if SD.isEOF () :
                    if n != 0 :
                        thl = []
                        chan_set = None
                        t = None
                        new_traces = []
                        for T in traces :
                            thl.append (T.headers)
                            if chan_set == None :
                                chan_set = T.headers.trace_header.channel_set
                            if chan_set == T.headers.trace_header.channel_set :
                                if isinstance (t, type (None)) :
                                    t = T.trace
                                else :
                                    t = npappend (t, T.trace)
                            else :
                                new_traces.append (T)
                                
                        traces = new_traces
                        process_traces (SD.reel_headers, thl[0], t)                        
                        #process_traces (SD.reel_headers, trace_headers_list[0], trace)
                        if DAS_INFO : writeINDEX ()
                    break
                
                try :
                    trace, cs = SD.process_trace ()
                except segdreader.InputsError as e :
                    #sys.stderr.write ("Error 2: Possible bad SEG-D file -- {0}".format ("".join (e)))
                    sys.stdout.write (":<Error:> {0}\n".format (F)); sys.stdout.flush ()
                    logging.info ("Error: Possible bad SEG-D file -- {0}".format ("".join (e.message)))
                    break
                    
                if not LAT and not LON :
                    try :
                        if UTM :
                            #   UTM
                            LAT, LON = utmcsptolatlon (SD.trace_headers.trace_header_N[4].receiver_point_Y_final / 10.,
                                                       SD.trace_headers.trace_header_N[4].receiver_point_X_final / 10.)
                        elif TSPF :
                            #   Texas State Plane coordinates
                            LAT, LON = txncsptolatlon (SD.trace_headers.trace_header_N[4].receiver_point_Y_final / 10.,
                                                       SD.trace_headers.trace_header_N[4].receiver_point_X_final / 10.)
                        else :
                            LAT = SD.trace_headers.trace_header_N[4].receiver_point_Y_final / 10.
                            LON = SD.trace_headers.trace_header_N[4].receiver_point_X_final / 10.
                    except Exception as e :
                        logging.warn ("Failed to convert location: {0}.\n".format (e.message))
                
                trace_headers_list.append (SD.trace_headers)
                #for cs in range (SD.chan_sets_per_scan) :
                if n == 0 :
                    traces.append (Trace (trace, SD.trace_headers))
                    n = 1
                    #   Node kludge
                    #Das = (SD.trace_headers.trace_header_N[0].receiver_line * 1000) + SD.trace_headers.trace_header_N[0].receiver_point
                    Das = get_das (SD)
                else :
                    traces.append (Trace (trace, SD.trace_headers))
                    #traces = npappend (traces, trace)
                    
                if n >= nleft or EVERY == True :
                    thl = []
                    chan_set = None
                    chan_set_next = None
                    t = None
                    new_traces = []
                    ###   Need to check for gaps here!
                    for T in traces :
                        thl.append (T.headers)
                        if chan_set == None :
                            chan_set = T.headers.trace_header.channel_set
                        if chan_set == T.headers.trace_header.channel_set :
                            #print type (t)
                            if isinstance (t, type (None)) :
                                t = T.trace
                            else :
                                t = npappend (t, T.trace)
                            #print len (t), t.min (), t.max ()
                        else :
                            new_traces.append (T)
                            if chan_set_next == None :
                                chan_set_next = T.headers.trace_header.channel_set
                            
                    traces = new_traces
                    process_traces (SD.reel_headers, thl[0], t)
                    if new_traces :
                        nleft = APPEND - len (new_traces)
                    else :
                        nleft = APPEND
                    chan_set = chan_set_next
                    chan_set_next = None
                    if DAS_INFO : 
                        writeINDEX ()
                    n = 0
                    trace_headers_list = []
                    continue
                
                n += 1
                
            update_external_references ()
            if TRACE_JSON :
                log_array, name = getLOG ()
                for line in TRACE_JSON :
                    log_array.append (line)
                
            sys.stdout.write (":<Finished>: {0}\n".format (F)); sys.stdout.flush ()
            
        write_arrays (ARRAY_T)
        seconds = time.time () - then
    
        try :
            EX.ph5close (); EXREC.ph5close ()
        except Exception as e :
            sys.stderr.write ("Warning: {0}\n".format ("".join (e.message)))
        
        print "Done...{0:b}".format (int (seconds/6.))   #   Minutes X 10
        logging.info ("Done...{0:b}".format (int (seconds/6.)))
        logging.shutdown
            
     
    ##   Profile
    #import cProfile, pstats
    #sys.stderr.write ("Warning: Profiling enabled!\n")
    #cProfile.run ('prof ()', "segd2ph5.profile")
    
    #p = pstats.Stats ("segd2ph5.profile")
    #p.sort_stats('time').print_stats(40)
    ##   Profile stop
    
    #   No profile
    prof ()    


if __name__ == '__main__' :
    main()    
    