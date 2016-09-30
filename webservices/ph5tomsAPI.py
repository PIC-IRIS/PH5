#!/usr/bin/env pnpython3

#

#   A take on ph52ms but using PH5API.

#

#   Steve Azevedo, May 2016

#   modified: Derick Hess, Sept 2016

PROG_VERSION = "2016.264 Developmental"



import sys, os

import obspy

import ph5API

import decimate

import time

from datetime import datetime

import TimeDOY

from TimeDOY import epoch2passcal

from TimeDOY import passcal2epoch

import numpy







def fdsntimetoepoch(fdsn_time):
    pattern = "%Y-%m-%dT%H:%M:%S.%f"
    epoch = float(time.mktime(time.strptime(fdsn_time, pattern)))
    return epoch


def encode_sta(LLLSSS):

    # encodes a sta LLLSSS (Line Sta) into alpha-numberic line, and sta LLSSS

    # allowing 5 character limit of seed station name

    return numpy.base_repr(int(LLLSSS[:3]), 36) + LLLSSS[3:]



def decode_sta(LLSSS):

    # opposite of above encode_sta

    return str(int(LLSSS[:2], 36)) + LLSSS[2:]

def DOY_breakup(start_fepoch):
    
    
    passcal_start = epoch2passcal(start_fepoch) 
    start_passcal_list=passcal_start.split(":")
    start_doy=start_passcal_list[1] 
    year= start_passcal_list[0] 
    next_doy=int(start_doy)+1
    if next_doy >365:
        next_doy=1
        year=int(year)+1
        
    Next_passcal_date=str(year)+":"+str(next_doy)+":00:00:00.000"
    stop_fepoch = passcal2epoch(Next_passcal_date)
    stop_fepoch=stop_fepoch-.001
    
    seconds= stop_fepoch-start_fepoch
    return stop_fepoch, seconds




class PH5toMSeed(object):

    def __init__(self, nickname, array, length, offset, component=[], station = [],

                 ph5path=".", netcode="XX", channel=[],

                 das_sn = None,  use_deploy_pickup = True, decimation = None,

                 sample_rate_keep=None, doy_keep=[], stream=False, out_dir=".", 

                starttime=None, stoptime=None, reduction_velocity = -1., dasskip=None):
        
        
       
        
        self.chan_map = { 1:'Z', 2:'N', 3:'E', 4:'Z', 5:'N', 6:'E' }

        self.array = array
        
        self.notimecorrect = False
        
        self.decimation = decimation
        
        self.component=component
        
        self.use_deploy_pickup = use_deploy_pickup
        
        self.offset = offset

        self.das_sn = das_sn

        self.station = station

        self.sample_rate_list = []

        self.doy_keep = doy_keep


        self.channel = channel

        self.netcode = netcode
        self.length = length

        #fileplace = args.fileplace

        self.nickname = nickname

        self.ph5path = ph5path

        self.out_dir = out_dir
        

        self.stream = stream

        self.start_time = starttime

        self.end_time = stoptime

        if not os.path.exists (self.out_dir) :

            try :

                os.mkdir (self.out_dir)

            except Exception as e :

                sys.stderr.write ("Error: Can't create {0}.".format (self.out_dir))

                sys.exit ()

        if dasskip != None :

            self.dasskip = dasskip

        else : 

            self.dasskip = dasskip

        

        # Check network code is 2 alphanum

        if ( not self.netcode.isalnum() ) or (len(self.netcode) != 2):

            sys.stderr.write ('Error parsing args: Netcode must 2 character alphanumeric')

            sys.exit(-2)

        

        #print PH5_PATH, PH5_FILE

        if self.nickname[-3:] == 'ph5' :

            PH5FILE = os.path.join (self.ph5path, self.nickname)

        else :

            PH5FILE = os.path.join (self.ph5path, self.nickname + '.ph5')

            self.nickname = self.nickname + '.ph5'

            

        if not os.path.exists (PH5FILE) :

            sys.stderr.write ("Error: %s not found.\n" % PH5FILE)

            sys.exit (-1)

            
       
        self.ph5 = ph5API.ph5 (path=self.ph5path, nickname=self.nickname)

        self.ph5.read_array_t_names ()

        self.ph5.read_das_g_names ()
        self.ph5.read_experiment_t()
        

        

        

    def read_arrays (self, name) :

        if name == None :

            for n in self.ph5.Array_t_names :

                self.ph5.read_array_t (n)

        else : self.ph5.read_array_t (name)

    

    def filename_gen (self, mseed_trace) :

        if self.stream:

            return sys.stdout

        s = mseed_trace.stats

        secs = int (s.starttime.timestamp)

        pre = epoch2passcal (secs, sep='_')

        ret = "{0}.{1}.{2}.{3}.ms".format (pre, s.network, s.station, s.channel)

        ret = os.path.join (self.out_dir, ret)

        return ret

    

    def process_all (self) : 
        CHAN_MAP = { 1:'Z', 2:'N', 3:'E', 4:'Z', 5:'N', 6:'E' }
        
        self.read_arrays (None)
       
        experiment_t =self.ph5.Experiment_t['rows']
       
        array_names = self.ph5.Array_t_names; array_names.sort ()
               
               
       
        for array_name in array_names :
            array = array_name[-3:]
            
            if self.array != None and self.array != array:
                
                continue
            
            arraybyid = self.ph5.Array_t[array_name]['byid']
            
            arrayorder = self.ph5.Array_t[array_name]['order']          
            
            for station in arrayorder :
                
                
                if self.station:
                    if station not in self.station:
                        
                        continue
            
                station_list= arraybyid.get(station)
            
                for deployment in station_list:
                    
                    deploy = station_list[deployment][0]['deploy_time/epoch_l']
            
                    pickup = station_list[deployment][0]['pickup_time/epoch_l']
            
                    das =  station_list[deployment][0]['das/serial_number_s']   
                    
                    if 'sample_rate_i' in station_list[deployment][0]:
                        sample_rate = station_list[deployment][0]['sample_rate_i']
                    
                    
                    #if SAMPLE_RATE_KEEP != None and sample_rate not in SAMPLE_RATE_LIST:
                    #    continue
                    
                    if 'seed_band_code_s' in station_list[deployment][0]:
                        band_code=station_list[deployment][0]['seed_band_code_s']
                    else:
                        band_code="D"
                    
                    if 'seed_instrument_code_s' in station_list[deployment][0]: 
                        instrument_code=station_list[deployment][0]['seed_instrument_code_s']
                    else:
                        instrument_code="P"
                        
                    c = station_list[deployment][0]['channel_number_i']     
                    
                    full_code= band_code+instrument_code+CHAN_MAP[c] 
                        
                    if self.channel and full_code not in self.channel:
                        continue
                        
                        
                    
                    #if DASSKIP == das:
                    #    continue
                    
                    
                    #if DAS != None and DAS != das:
                    #   continue
                    
                    
                    self.ph5.read_das_t (das)
                    
                    if self.start_time :
                        if "T" not in self.start_time:
                            start_fepoch=self.start_time 
                            start_fepoch=passcal2epoch(start_fepoch)
                        else:
                            start_fepoch = fdsntimetoepoch(self.start_time)
                    
                    
                    else:
                        start_fepoch = ph5API.fepoch (station_list[deployment][0]['deploy_time/epoch_l'], station_list[deployment][0]['deploy_time/micro_seconds_i'])                    
                    
                    
                    if self.length:
                            stop_fepoch =start_fepoch+self.length
                        
                    elif self.end_time:
                        if "T" not in self.end_time:
                            stop_fepoch=self.end_time 
                            stop_fepoch=passcal2epoch(stop_fepoch)
                        else:
                            stop_fepoch = fdsntimetoepoch(self.end_time)
                    else:
                        stop_fepoch = ph5API.fepoch (station_list[deployment][0]['pickup_time/epoch_l'], station_list[deployment][0]['pickup_time/micro_seconds_i'])       
                        
                    if self.use_deploy_pickup == True and not ((start_fepoch >= deploy and stop_fepoch <= pickup)):
                        #das not deployed within deploy/pickup time       	    
                        continue     
                    
                    start_passcal=epoch2passcal(start_fepoch, sep=':')
                    start_passcal_list=start_passcal.split(":")
                    start_doy=start_passcal_list[1]   
                    start_year=start_passcal_list[0]  
                    
                    
                    if self.offset:
                        start_fepoch = start_fepoch + int(self.offset)
                    
                    if self.doy_keep:
                        if start_doy not in self.doy:
                            continue	 
                        
                    data = {}
                        
                    c = station_list[deployment][0]['channel_number_i'] 
                    
                    if (stop_fepoch - start_fepoch) > 86400:
                        #print "we need to break this down into days"
                        # send start and stop time to DOY_breakup to get a list of star and stop times
                        seconds_covered=0
                        total_seconds= stop_fepoch - start_fepoch
                        times_to_cut=[]
                        stop_time, seconds =DOY_breakup(start_fepoch)
                        seconds_covered= seconds_covered+seconds   
                        times_to_cut.append([start_fepoch, stop_time])
                        start_time = stop_time+.001
                        
                        while  seconds_covered < total_seconds:
                            stop_time, seconds =DOY_breakup(start_time)
                            seconds_covered= seconds_covered+seconds
                            times_to_cut.append([start_time, stop_time])
                            start_time = stop_time+.001
                    else: 
                        times_to_cut=[[start_fepoch, stop_fepoch]]
                        
                        
                        
                            
                            
                            
                            
                        
                        
                            
                    for x in times_to_cut:
                        	    
                        if not data.has_key (c) :
                            data[c] = []     
                        
                        if self.component and c in self.component:
                            data[c].append (ph5.cut (das, x[0], x[1], chan=c))
                        
                        elif self.component and c not in self.component:
                            data[c] = []
                        
                        else:
                            data[c].append (ph5.cut (das, x[0], x[1], chan=c)) 
                        
                        chans = data.keys (); chans.sort ()
                    
                        
                        for c in chans : 
                        
                            traces = data[c]
                            for trace in traces: 
                                
                            
                                
                                
                                if self.decimation:
                                    shift, data = decimate.decimate (self.decimation, trace.data) 
                                    wsr = int (sample_rate/int (self.decimation))
                                    trace.sample_rate = wsr
                                    trace.nsamples = len (data)
                                if trace.nsamples == 0 :
                                        #   Failed to read any data
                                        #sys.stderr.write ("Warning: No data for data logger {2}/{0} starting at {1}.".format (das, trace.start_time, sta))
                                    continue 	
                            
                            
                                try :
                                    mseed_trace = obspy.Trace (data=trace.data)
                                except ValueError :
                                    #sys.stderr.write ("Error: Can't create trace for DAS {0} at {1}.".format (das, repr (trace.start_time)))
                                    continue
                                mseed_trace.stats.sampling_rate = float (trace.das_t[0]['sample_rate_i']) / float (trace.das_t[0]['sample_rate_multiplier_i'])
                                mseed_trace.stats.station = station   ###   ZZZ   Get from Maps_g
                                mseed_trace.stats.channel = band_code+instrument_code+CHAN_MAP[c]    
                            
                                if 'net_code_s' in experiment_t[0]:
                                    mseed_trace.stats.network = experiment_t[0]['net_code_s']
                                else:
                                    mseed_trace.stats.network = 'XX'
                            
                                if self.notimecorrect == True:
                                    corrected_time = trace.time_correct ()
                                    mseed_trace.stats.starttime = obspy.UTCDateTime (corrected_time.epoch (fepoch=False))
                                    mseed_trace.stats.starttime.microsecond = corrected_time.dtobject.microsecond
                                
                                else: 
                                    mseed_trace.stats.starttime = obspy.UTCDateTime (trace.start_time.epoch (fepoch=True))
                                    mseed_trace.stats.starttime.microsecond = trace.start_time.dtobject.microsecond 
                            
                                
                                
                                yield mseed_trace
                                    

                                                    
                        
                    
                    
            
            
            


    

    def process_event (self) :

        pass

    def process_start (self) :

        pass

    def process_error (self) :

        pass

    def process_all_events (self) :

        pass



def get_args () :

    import argparse



    parser = argparse.ArgumentParser(description='Return mseed from a PH5 file.',

                                     usage='Version: {0} ph5tomsAPI --nickname="Master_PH5_file" [options]'.format (PROG_VERSION))



    parser.add_argument ("-n", "--nickname", action="store", required=True,

                         type=str, metavar="nickname")



    parser.add_argument ("-p", "--ph5path", action="store", default=".",

                         type=str, metavar="ph5_path")



    parser.add_argument('--network',

                        help='The 2 character SEED network code to be used in the MSEED output headers and fileames',

                        default='XX')

    

    parser.add_argument ("--channel", action="store",

                         type=str, dest="channel", help="Comma separated list of channel numbers to extract", metavar="channel",

                         default = [])


    

    ###   Need to get event or start time, length, array and/or station list

    #parser.add_argument ("-e", "--eventnumber", action="store",

    #                     type=str, metavar="event_number")



    #parser.add_argument ("-E", "--allevents", action="store_true", default=False)



    parser.add_argument ("--stream", action="store_true", default=False,

                         help="Stream output to stdout.")



    parser.add_argument ("-s", "--starttime", action="store",

                         type=str, dest="start_time", metavar="start_time")



    parser.add_argument ("-t", "--stoptime", action="store",

                         type=str, dest="stop_time", metavar="stop_time")



    parser.add_argument ("-A", "--all", action="store_true", default=False, dest="extract_all")



    parser.add_argument ("-a", "--array", action="store", 

                         type=str, dest="array", metavar="array")



    parser.add_argument ("-O", "--offset", action="store",

                         type=float, dest="offset", metavar="offset")    



    parser.add_argument ("-c", "--component", action="store",

                         type=str, dest="component", help="Comma separated list of channel numbers to extract", metavar="component",

                         default = [])



    parser.add_argument ("-d", "--decimation", action="store",

                         choices=["2", "4", "5", "8", "10", "20"],

                         metavar="decimation", default=None)



    parser.add_argument ("--station", action="store", dest="sta_list",

                         help="Comma separated list of station id's to extract from selected array.", 

                         metavar="sta_list", type=str, default=[])



    parser.add_argument ("-r", "--sample_rate_keep", action="store", dest="sample_rate", help="Comma separated list of sample rates to extract",

                         metavar="sample_rate", type=str)



    parser.add_argument ("-V", "--reduction_velocity", action="store", dest="red_vel",

                        metavar="red_vel", type=float, default="-1.")



    #Field only

    parser.add_argument ("-l", "--length", action="store",

                         type=int, dest="length", metavar="length")    

    

    parser.add_argument ("-N", "--notimecorrect", action="store_true", default=False)  

    

    parser.add_argument ("-o", "--out_dir", action="store",

                         metavar="out_dir", type=str, default=".")

    

    parser.add_argument ("--use_deploy_pickup", action="store_true", default=True,

                     help="Use deploy and pickup times to determine if data exists for a station.",

                     dest="deploy_pickup")



    parser.add_argument('--dasskip',  metavar='dasskip',

                        help=argparse.SUPPRESS)



    parser.add_argument ("-D", "--das", action="store", dest="das_sn",

                         metavar="das_sn", type=str, help=argparse.SUPPRESS, default=None)



    parser.add_argument ("-Y", "--doy", action="store", dest="doy_keep",

                         help="Comma separated list of julian days to extract.",

                         metavar="doy_keep", type=str)



    args = parser.parse_args()
    
    return args



if __name__ == '__main__' :

    #from time import time as t

    #then = t ()

    args = get_args ()

    ph5 = ph5API.ph5 (path=args.ph5path, nickname=args.nickname)

    ph5ms = PH5toMSeed(args.nickname, args.array, args.length, args.offset, args.component, args.sta_list, 

                       args.ph5path, args.network, args.channel, args.das_sn,  args.deploy_pickup, 

                       args.decimation, args.sample_rate, args.doy_keep, args.stream, 

                       args.out_dir, args.start_time, args.stop_time, args.red_vel, args.dasskip)
    

    
    traces = ph5ms.process_all()
    for t in traces:
        outfile = ph5ms.filename_gen (t)    
        t.write (outfile, format='MSEED', reclen=512, encoding='STEIM2')         

    
    ph5.close ()

    #print t () - then

