#!/usr/bin/env pnpython3
#
#   A take on ph52ms but using PH5API.
#
#   Steve Azevedo, May 2016
#   modified: Derick Hess, Sept 2016


PROG_VERSION = "2016.266 Developmental"

import sys, os
import obspy
import ph5API
import decimate
from TimeDOY import epoch2passcal
from TimeDOY import passcal2epoch
sys.settrace
#   We can extract data by event, start time, all/das
STATES = { 'Event': 0, 'Start': 1, 'All': 2, 'Error': 3, 'AllEvents': 4 }
#
CHAN_MAP = { 1:'Z', 2:'N', 3:'E', 4:'Z', 5:'N', 6:'E' }
DEPLOY_PICKUP = False
NOTIMECORRECT = False



def encode_sta(LLLSSS):
    # encodes a sta LLLSSS (Line Sta) into alpha-numberic line, and sta LLSSS
    # allowing 5 character limit of seed station name
    return numpy.base_repr(int(LLLSSS[:3]), 36) + LLLSSS[3:]

def decode_sta(LLSSS):
    # opposite of above encode_sta
    return str(int(LLSSS[:2], 36)) + LLSSS[2:]

def get_args () :
    global NETWORK, SEED_CHANNEL_PREFIX, DASSKIP, CHANNEL, CHANNEL_LIST, NICKNAME, PH5PATH, PH5FILE, OUTPATH, \
           STREAM, DEPLOY_PICKUP, STATIONS, STATION_LIST, DOYS, DOY_LIST, ARRAY, DECIMATION, LENGTH, OFFSET, \
           SAMPLE_RATE_KEEP, SAMPLE_RATE_LIST
    import argparse

    parser = argparse.ArgumentParser(description='Return mseed from a PH5 file.',
                                     usage='Version: {0} ph5tomsAPI --nickname="Master_PH5_file" [options]'.format (PROG_VERSION))

    parser.add_argument ("-n", "--nickname", action="store", required=True,
                         type=str, metavar="nickname")

    parser.add_argument ("-p", "--ph5path", action="store", default=".",
                         type=str, metavar="ph5_path")

    parser.add_argument('--netcode',
                        help='The 2 character SEED network code to be used in the MSEED output headers and fileames',
                        default='XX')
    parser.add_argument('--mseed_chan',
                        help='The first 2 characters of the MSEED channel code for headers and filenames. The 3rd character is the orientation taken from the ph5 file.',
                        default='DP')

    parser.add_argument('--dasskip',  metavar='dasskip',
                        help=argparse.SUPPRESS)
    ###   Need to get event or start time, length, array and/or station list
    #parser.add_argument ("-e", "--eventnumber", action="store",
    #                     type=str, metavar="event_number")

    #parser.add_argument ("-E", "--allevents", action="store_true", default=False)

    parser.add_argument ("--stream", action="store_true", default=False,
                         help="Stream output to stdout.")

    parser.add_argument ("-s", "--starttime", action="store",
                         type=str, dest="start_time", metavar="start_time")

    parser.add_argument ("-A", "--all", action="store_true", default=False, dest="extract_all")

    parser.add_argument ("-t", "--stoptime", action="store",
                         type=str, dest="stop_time", metavar="stop_time")

    parser.add_argument ("-a", "--array", action="store", 
                         type=str, dest="array", metavar="array")

    parser.add_argument ("-l", "--length", action="store",
                         type=int, dest="length", metavar="length")

    parser.add_argument ("-O", "--offset", action="store",
                         type=float, dest="offset", metavar="offset")    

    parser.add_argument ("-c", "--channel", action="store",
                         type=str, dest="channel", help="Comma separated list of channel numbers to extract", metavar="channel")

    parser.add_argument ("-N", "--notimecorrect", action="store_true", default=False)

    parser.add_argument ("-d", "--decimation", action="store",
                         choices=["2", "4", "5", "8", "10", "20"],
                         metavar="decimation")

    parser.add_argument ("-o", "--out_dir", action="store",
                         metavar="out_dir", type=str, default=".")

    parser.add_argument ("--use_deploy_pickup", action="store_true", default=True,
                         help="Use deploy and pickup times to determine if data exists for a station.",
                         dest="deploy_pickup")

    parser.add_argument ("-D", "--das", action="store", dest="das_sn",
                         metavar="das_sn", type=str, help=argparse.SUPPRESS)

    ###   ZZZ   ###
    parser.add_argument ("--station_list", action="store", dest="sta_list",
                         help="Comma separated list of station id's to extract from selected array.", 
                         metavar="sta_list", type=str)

    parser.add_argument ("-Y", "--doy", action="store", dest="doy_keep",
                         help="Comma separated list of julian days to extract.",
                         metavar="doy_keep", type=str)

    parser.add_argument ("-r", "--sample_rate_keep", action="store", dest="sample_rate", help="Comma separated list of sample rates to extract",
                         metavar="sample_rate", type=str)

    #parser.add_argument ("-V", "--reduction_velocity", action="store", dest="red_vel",
    #                    metavar="red_vel", type=float, default="-1.")



    args = parser.parse_args()

    channel_prefix = args.mseed_chan
    NETWORK = args.netcode
    #fileplace = args.fileplace
    NICKNAME = args.nickname
    PH5PATH = args.ph5path
    OUTPATH = args.out_dir
    STREAM = args.stream
    DEPLOY_PICKUP= args.deploy_pickup
    NOTIMECORRECT=args.notimecorrect
    DECIMATION = args.decimation
    LENGTH= args.length
    OFFSET= args.offset

    SAMPLE_RATE_KEEP = args.sample_rate
    if SAMPLE_RATE_KEEP != None:
        SAMPLE_RATE_LIST=SAMPLE_RATE_KEEP.split(",")
        SAMPLE_RATE_LIST = [ int(x) for x in SAMPLE_RATE_LIST ]


    ARRAY =args.array
    CHANNEL = args.channel
    if CHANNEL != None:
        CHANNEL_LIST=CHANNEL.split(",")
        CHANNEL_LIST = [ int(x) for x in CHANNEL_LIST ]

    STATIONS=args.sta_list
    if STATIONS !=None:
        STATION_LIST =STATIONS.split(",")

    DOYS=args.doy_keep
    if DOYS !=None:
        DOY_LIST =DOYS.split(",")


    if not os.path.exists (OUTPATH) :
        try :
            os.mkdir (OUTPATH)
        except Exception as e :
            sys.stderr.write ("Error: Can't create {0}.".format (OUTPATH))
            sys.exit ()
    if args.dasskip != None :
        DASSKIP = args.dasskip
    else : 
        DASSKIP = args.dasskip
    # Check Channel is 2 alphanum
    if ( not channel_prefix.isalnum() ) or (len(channel_prefix) != 2):
        sys.stderr.write ('Error parsing args: Channel must 2 character alphanumeric')
        sys.stderr.write (parser.usage)
        sys.exit(-1)
    else :
        SEED_CHANNEL_PREFIX = channel_prefix
    # Check network code is 2 alphanum
    if ( not NETWORK.isalnum() ) or (len(NETWORK) != 2):
        sys.stderr.write ('Error parsing args: Netcode must 2 character alphanumeric')
        sys.stderr.write (parser.usage)
        sys.exit(-2)

    #print PH5_PATH, PH5_FILE
    if NICKNAME[-3:] == 'ph5' :
        PH5FILE = os.path.join (PH5PATH, NICKNAME)
    else :
        PH5FILE = os.path.join (PH5PATH, NICKNAME + '.ph5')

    if not os.path.exists (PH5FILE) :
        sys.stderr.write ("Error: %s not found.\n" % PH5FILE)
        sys.exit (-1)

    def parse_all () :
        global ALL, DAS, STA, DOY, START_TIME, STOP_TIME

        if args.start_time != None :
            START_TIME = passcal2epoch(args.start_time)
        else:
            START_TIME= None

        if args.stop_time != None :
            STOP_TIME = passcal2epoch(args.stop_time)
        else:
            STOP_TIME= None	




        ALL = args.extract_all
        DAS = args.das_sn
        #STA = args.station
        #logging.info ("Extracting ALL DAS = {0} Stations = {1} Days = {2}".format (DAS, STA, options.doy_keep))





    if args.extract_all :
        parse_all ()
        return STATES['All']

def read_arrays (name) :
    if name == None :
        for n in ph5.Array_t_names :
            ph5.read_array_t (n)
    else : ph5.read_array_t (name)

def filename_gen (mseed_trace, array) :
    if STREAM :
        return sys.stdout
    s = mseed_trace.stats
    secs = int (s.starttime.timestamp)
    pre = epoch2passcal (secs, sep='_')
    ret = "{0}.{1}.{2}.{3}.{4}.ms".format (pre, s.network, s.station, s.channel, array)
    ret = os.path.join (OUTPATH, ret)
    return ret

def process_all () : 

    read_arrays (None)
    experiment_t =ph5.Experiment_t['rows']
    array_names = ph5.Array_t_names; array_names.sort ()
    for array_name in array_names :
        array = array_name[-3:]

        if ARRAY != None and ARRAY != array:
            continue
        arraybyid = ph5.Array_t[array_name]['byid']
        arrayorder = ph5.Array_t[array_name]['order']

        for station in arrayorder :


            if STATIONS:
                if station not in STATION_LIST:
                    continue

            station_list= arraybyid.get(station)


            for deployment in station_list:




                deploy = station_list[deployment][0]['deploy_time/epoch_l']
                pickup = station_list[deployment][0]['pickup_time/epoch_l']
                das =  station_list[deployment][0]['das/serial_number_s']

                if 'sample_rate_i' in station_list[deployment][0]:
                    sample_rate = station_list[deployment][0]['sample_rate_i']


                if SAMPLE_RATE_KEEP != None and sample_rate not in SAMPLE_RATE_LIST:
                    continue

                if 'seed_band_code_s' in station_list[deployment][0]:
                    band_code=station_list[deployment][0]['seed_band_code_s']
                else:
                    band_code="D"

                if 'seed_instrument_code_s' in station_list[deployment][0]: 
                    instrument_code=station_list[deployment][0]['seed_instrument_code_s']
                else:
                    instrument_code="P"

                if DASSKIP == das:
                    continue


                if DAS != None and DAS != das:
                    continue


                ph5.read_das_t (das)


                if START_TIME:
                    start_fepoch=START_TIME


                else:
                    start_fepoch = ph5API.fepoch (station_list[deployment][0]['deploy_time/epoch_l'], station_list[deployment][0]['deploy_time/micro_seconds_i'])

                if LENGTH != None:
                    stop_fepoch =start_fepoch+LENGTH

                elif STOP_TIME != None:
                    stop_fepoch=STOP_TIME
                else:
                    stop_fepoch = ph5API.fepoch (station_list[deployment][0]['pickup_time/epoch_l'], station_list[deployment][0]['pickup_time/micro_seconds_i'])		

                if DEPLOY_PICKUP == True and not ((start_fepoch >= deploy and stop_fepoch <= pickup)):
                    #das not deployed within deploy/pickup time       	    
                    continue

                start_passcal=epoch2passcal(start_fepoch, sep=':')
                start_passcal_list=start_passcal.split(":")
                start_doy=start_passcal_list[1] 

                if OFFSET != None:
                    start_fepoch = start_fepoch +OFFSET

                if DOYS:
                    if start_doy not in DOY_LIST:
                        continue		

                data = {}

                c = station_list[deployment][0]['channel_number_i']

                print "cutting data for station "+station+" Channel "+str(c)		    
                if not data.has_key (c) :
                    data[c] = []



                if CHANNEL and c in CHANNEL_LIST:
                    data[c].append (ph5.cut (das, start_fepoch, stop_fepoch, chan=c))

                if CHANNEL and c not in CHANNEL_LIST:
                    data[c] = []

                if not CHANNEL:
                    data[c].append (ph5.cut (das, start_fepoch, stop_fepoch, chan=c))


                chans = data.keys (); chans.sort ()
                for c in chans :
                    traces = data[c]
                    for trace in traces :

                        if DECIMATION != None:
                            shift, data = decimate.decimate (DECIMATION, trace.data) 
                            sr = int (sr/int (DECIMATION))
                            trace.sample_rate = wsr
                            trace.nsamples = len (data)
                            if trace.nsamples == 0 :
                                #   Failed to read any data
                                sys.stderr.write ("Warning: No data for data logger {2}/{0} starting at {1}.".format (das, trace.start_time, sta))
                                continue 			    
                        print "converting mseed"
                        try :
                            mseed_trace = obspy.Trace (data=trace.data)
                        except ValueError :
                            sys.stderr.write ("Error: Can't create trace for DAS {0} at {1}.".format (das, repr (trace.start_time)))
                            continue
                        mseed_trace.stats.sampling_rate = float (trace.das_t[0]['sample_rate_i']) / float (trace.das_t[0]['sample_rate_multiplier_i'])
                        mseed_trace.stats.station = station   ###   ZZZ   Get from Maps_g

                        mseed_trace.stats.channel = band_code+instrument_code+CHAN_MAP[c]
                        if 'net_code_s' in experiment_t[0]:
                            mseed_trace.stats.network = experiment_t[0]['net_code_s']
                        else:
                            mseed_trace.stats.network = 'XX'
                        if NOTIMECORRECT == True:
                            corrected_time = trace.time_correct ()
                            mseed_trace.stats.starttime = obspy.UTCDateTime (corrected_time.epoch (fepoch=False))
                            mseed_trace.stats.starttime.microsecond = corrected_time.dtobject.microsecond

                        else: 
                            mseed_trace.stats.starttime = obspy.UTCDateTime (trace.start_time.epoch (fepoch=True))
                            mseed_trace.stats.starttime.microsecond = trace.start_time.dtobject.microsecond

                        #stream = obspy.core.Stream ()
                        #stream.append (mseed_trace)
                        outfile = filename_gen (mseed_trace, array)


                        if STREAM == True:
                            mseed_trace.write (sys.stdout, format='MSEED', reclen=512, encoding='STEIM2')
                        else:	 
                            mseed_trace.write (outfile, format='MSEED', reclen=512, encoding='STEIM2')
        #print 'Next?'
    #print 'ZZZ'

def process_event () :
    pass
def process_start () :
    pass
def process_error () :
    pass
def process_all_events () :
    pass

STATE = [ process_event, process_start, process_all, process_error, process_all_events ]    
if __name__ == '__main__' :
    global ph5
    #from time import time as t
    #then = t ()
    s = get_args ()
    ph5 = ph5API.ph5 (path=PH5PATH, nickname=PH5FILE)
    ph5.read_array_t_names ()
    ph5.read_das_g_names ()
    ph5.read_experiment_t()
    STATE[s]()
    ph5.close ()
    #print t () - then