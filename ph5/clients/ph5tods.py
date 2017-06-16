#!/usr/bin/env pnpython4
#
#   ph5tods (For WS data select)
#
#   Steve Azevedo, May 2016
#

PROG_VERSION = "2016.153 Developmental"

import sys, os, logging
import obspy
import ph5API, TimeDOY
from TimeDOY import epoch2passcal

#
CHAN_MAP = { 1:'Z', 2:'N', 3:'E', 4:'Z', 5:'N', 6:'E' }

def parse_time (time_string) :
    try :
        epoch = TimeDOY.passcal2epoch (time_string, fepoch=True)
    except TimeDOY.TimeError as e :
        #sys.stderr.write ("Error: Can't convert {0}.\n{1}".format (time_string, e.message))
        logging.error ("Can't convert {0}.\n{1}".format (time_string, e.message))
        return None
    
    try :
        tdoy = TimeDOY.TimeDOY (epoch=epoch)
    except TimeDOY.TimeError as e :
        #sys.stderr.write ("Error: Can't convert {0}.\n{1}".format (time_string, e.message))
        logging.error ("Can't convert {0}.\n{1}".format (time_string, e.message))
        return None
    
    return tdoy

def get_args () :
    global NICKNAME, PH5_PATH, OUT_DIR, START_TIME, END_TIME, NET_WORKS, CHANNELS, \
           PH5_FILE, STATIONS, STREAM
    
    import argparse
        
    parser = argparse.ArgumentParser(description='Return mseed from a PH5 file.',
                                     usage='Version: {0} ph5tods --nickname="Master_PH5_file" [options]'.format (PROG_VERSION))
    
    parser.add_argument ("-n", "--nickname", action="store", required=True,
                         type=str, metavar="nickname")

    parser.add_argument ("-p", "--ph5path", action="store", default=".",
                         type=str, metavar="ph5_path")

    parser.add_argument ("-o", "--out_dir", action="store",
                         metavar="out_dir", type=str, default=".")

    parser.add_argument ("-s", "--starttime", action="store", required=True,
                         help="YYYY:JJJ:HH:HH:SS.ssssss in ZULU time.",
                         type=str, metavar="start_time")

    parser.add_argument ("-t", "--endtime", action="store", required=True,
                         help="YYYY:JJJ:HH:HH:SS.ssssss in ZULU time.",
                         type=str, metavar="end_time")
    
    parser.add_argument ("--networks", required=True,
                         help="A comma seperated list of SEED network codes.",
                         type=str, metavar="net_works")
    
    parser.add_argument("--channels", required=True,
                        help="A comma seperated list of SEED channels.",
                        type=str)
    
    parser.add_argument ("--stations", action="store", dest="stations",
                         help="Comma separated list of SEED station names.",
                         metavar="stations", type=str, required=True)

    args = parser.parse_args()
    
    OUT_DIR = args.out_dir
    if not os.path.exists (OUT_DIR) :
        os.makedirs (OUT_DIR)
    logging.basicConfig (filename=os.path.join (OUT_DIR, 'ph5tods.log'),
                         format="%(asctime)s %(message)s",
                         level=logging.INFO)
    logging.info ("ph5tods v{0}".format (PROG_VERSION))
    logging.info ("{0}".format (repr (sys.argv)))
    STREAM = True   #   If true write to STDOUT.
    NICKNAME = args.nickname
    PH5_PATH = args.ph5path
    if NICKNAME[0] == '/' :
        PH5_FILE = NICKNAME
    else :
        PH5_FILE = os.path.join (PH5_PATH, NICKNAME)
    
    logging.info ("PH5_FILE: {0}".format (repr (PH5_FILE)))    
    START_TIME = parse_time (args.starttime)
    logging.info ("START_TIME: {0}".format (repr (START_TIME)))
    END_TIME = parse_time (args.endtime)
    logging.info ("END_TIME: {0}".format (repr (END_TIME)))
    NET_WORKS = args.networks.split (',')
    logging.info ("NET_WORKS: {0}".format (repr (NET_WORKS)))
    CHANNELS = args.channels.split (',')
    logging.info ("CHANNELS: {0}".format (repr (CHANNELS)))
    STATIONS = args.stations.split (',')
    logging.info ("STATIONS: {0}".format (repr (STATIONS)))
    pass

def array2loc(array_name):
    #   Encode array number to loc code
    aaa = array_name[-3:]
    return numpy.base_repr(int (aaa), 36)

def loc2array(loc_code):
    # opposite of array2loc
    return str(int(loc_code, 36))
   
def read_arrays (name) :
    '''
       Read Array_t or Array_t(s)
    '''
    if name == None :
        for n in ph5.Array_t_names :
            ph5.read_array_t (n)
    else : ph5.read_array_t (name)
    
def filename_gen (mseed_trace, array) :
    '''
       Generate mseed file name (STDOUT)
    '''
    s = mseed_trace.stats
    secs = int (s.starttime.timestamp)
    pre = epoch2passcal (secs, sep='_')
    ret = "{0}.{1}.{2}.{3}.{4}.ms".format (pre, s.network, s.station, s.channel, array)
    ret = os.path.join (OUT_DIR, ret)
    logging.info ("Writing data for: {0}".format (ret))
    if STREAM :
        return sys.stdout    
    return ret

def get_seed_chans (Array_t) :
    '''
       Read and construct SEED channel name from array_t.
    '''
    ret = []
    for array_t in Array_t :
        try :
            band_code = array_t['seed_band_code_s']
            instrument_code = array_t['seed_instrument_code_s']
            orientation_code = array_t['seed_orientation_code_s']
            r = band_code + instrument_code + orientation_code
            if len (r) != 3 : 
                raise RuntimeError ("Invalid or missing seed codes in array_t.")
            else :
                ret.append (r)
        except Exception as e :
            logging.warn ("Could not read seed codes from array_t: {0}".format (e.message))
            ret.append ('')    
    return ret

def process () :
    '''
       Process PH5 to mseed.
    '''
    read_arrays (None)
    array_names = ph5.Array_t_names; array_names.sort ()
    for array_name in array_names :
        array = array_name[-3:]
        arraybyid = ph5.Array_t[array_name]['byid']
        arrayorder = ph5.Array_t[array_name]['order']
        for station in STATIONS :
            if not station in arrayorder :
                continue
            channels = get_seed_chans (arraybyid[station])
            for channel, array_t in zip (channels, arraybyid[station]) :
                if not channel in CHANNELS :
                    continue
                #for array_t in arraybyid[station] :
                deploy = array_t['deploy_time/epoch_l']
                #dtdoy = TimeDOY.TimeDOY (epoch = arraybyid[station]['deploy_time/epoch_l'])
                #x = dtdoy.getPasscalTime ()
                pickup = array_t['pickup_time/epoch_l']
                #ptdoy = TimeDOY.TimeDOY (epoch = arraybyid[station]['pickup_time/epoch_l'])
                #y = ptdoy.getPasscalTime ()
                if not ph5API.is_in (deploy, pickup, START_TIME.epoch (), END_TIME.epoch ()) :
                    continue
                das = array_t['das/serial_number_s']
                ph5.read_das_t (das)
                data = []
                try :
                    dasrows = ph5.Das_t[das]['rows']
                except KeyError :
                    continue
                for das_t in dasrows :
                    trace_epoch = das_t['time/epoch_l']
                    if trace_epoch < deploy or trace_epoch > pickup :
                        continue
                    start_fepoch = ph5API.fepoch (das_t['time/epoch_l'], das_t['time/micro_seconds_i'])
                    
                    stop_fepoch = start_fepoch + (das_t['sample_count_i'] / (das_t['sample_rate_i'] / float (das_t['sample_rate_multiplier_i'])))
                    c = das_t['channel_number_i']
                        
                    data.append (ph5.cut (das, start_fepoch, stop_fepoch, chan=c))
                
                stream = obspy.core.Stream ()    
                for trace in data :
                    try :
                        mseed_trace = obspy.Trace (data=trace.data)
                    except ValueError :
                        logging.error ("Error: Can't create trace for DAS {0} at {1}.".format (das, repr (trace.start_time)))
                        continue
                    mseed_trace.stats.sampling_rate = float (trace.das_t[0]['sample_rate_i']) / float (trace.das_t[0]['sample_rate_multiplier_i'])
                    mseed_trace.stats.station = station
                    mseed_trace.stats.channel = channel
                    mseed_trace.stats.network = NET_WORKS[0]
                    corrected_time = trace.time_correct ()
                    mseed_trace.stats.starttime = obspy.UTCDateTime (corrected_time.epoch (fepoch=False))
                    mseed_trace.stats.starttime.microsecond = corrected_time.dtobject.microsecond
                    
                    stream.append (mseed_trace)
                    
                outfile = filename_gen (stream[0], array)
                stream.write (outfile, format='MSEED', reclen=512, encoding='STEIM2')
        
if __name__ == '__main__' :
    global ph5
    #from time import time as t
    #then = t ()
    s = get_args ()
    ph5 = ph5API.ph5 (path=PH5_PATH, nickname=NICKNAME)
    ph5.read_experiment_t ()
    experiment_t = ph5.Experiment_t['rows'][-1]
    try :
        seed_net = experiment_t['net_code_s']
        if not seed_net in NET_WORKS :
            logging.error ("{0} not in {1}".format (seed_net, repr (NET_WORKS)))
            sys.exit ()
    except Exception as e :
        logging.error ("Exception while reading SEED NETCODE: {0}".format (e.message))
        sys.exit ()
    ph5.read_array_t_names ()
    ph5.read_das_g_names ()
    process()
    ph5.close ()
    logging.info ("Done")
    logging.info ("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logging.shutdown ()