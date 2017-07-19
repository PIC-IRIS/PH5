#!/usr/bin/env pnpython4
#
#   Produce SEG-Y in shot (event) order from PH5 file using API
#
#   Steve Azevedo, August 2016
#

import os, sys, logging
from ph5.core import ph5api, segyfactory, decimate, timedoy

PROG_VERSION = "2017.186 Developmental"
#   This should never get used. See ph5api.
CHAN_MAP = { 1:'Z', 2:'N', 3:'E', 4:'Z', 5:'N', 6:'E' }

DECIMATION_FACTORS = segyfactory.DECIMATION_FACTORS

def get_args () :
    '''   Read command line argments   '''
    global ARGS, P5
    import argparse
    
    parser = argparse.ArgumentParser ()
    
    parser.usage = "Version: %s\n" % PROG_VERSION
    parser.usage += "ph5toevt --eventnumber=shot --nickname=experiment_nickname --length=seconds [--path=ph5_directory_path] [options]\n"
    parser.usage += "\toptions:\n\t--array=array, --offset=seconds (float), --reduction_velocity=km-per-second (float) --format=['SEGY']\n\n"
    parser.usage += "ph5toevt --allevents --nickname=experiment_nickname --length=seconds [--path=ph5_directory_path] [options]\n"
    parser.usage += "\toptions:\n\t--array=array, --offset=seconds (float), --reduction_velocity=km-per-second (float) --format=['SEGY']\n\n"
    parser.usage += "ph5toevt --starttime=yyyy:jjj:hh:mm:ss[:.]sss --nickname=experiment_nickname --length=seconds [--path=ph5_directory_path] [options]\n"
    parser.usage += "\toptions:\n\t--stoptime=yyyy:jjj:hh:mm:ss[:.]sss, --array=array, --reduction_velocity=km-per-second (float) --format=['SEGY']\n\n"
    #parser.usage += "ph5toseg --all, --nickname=experiment_nickname [--path=ph5_directory_path] [--das=das_sn] [--station=station_id] [--doy=comma seperated doy list] [options]"
    parser.usage += "\n\n\tgeneral options:\n\t--channel=[1,2,3]\n\t--sample_rate_keep=sample_rate\n\t--notimecorrect\n\t--decimation=[2,4,5,8,10,20]\n\t--out_dir=output_directory"
    
    parser.description = "Generate SEG-Y gathers in shot order..."
    #   Usually master.ph5
    parser.add_argument ("-n", "--nickname", dest="ph5_file_prefix", 
                         help="The ph5 file prefix (experiment nickname).",
                         metavar="ph5_file_prefix", required=True)
    #   Path to the directory that holds master.ph5
    parser.add_argument ("-p", "--path", dest = "ph5_path",
                         help = "Path to ph5 files. Defaults to current directory.",
                         metavar = "ph5_path", default='.')
    #   SEED channel
    parser.add_argument ("--channel", dest="seed_channel",
                         help="Filter on SEED channel.",
                         metavar="seed_channel")
    #   SEED network code
    parser.add_argument ("--network", dest="seed_network",
                         help="Filter on SEED net code.",
                         metavar="seed_network")
    #   SEED loc code
    parser.add_argument ("--location", dest="seed_location",
                         help="Filter on SEED loc code.",
                         metavar="seed_location")
    #   Channels. Will extract in order listed here. 'Usually' 1 -> Z, 2-> N, 3 -> E
    parser.add_argument ("-c", "--channels", action="store",
                         help="List of comma seperated channels to extract. Default = 1,2,3.",
                         type=str, dest="channels", metavar="channels",
                         default='1,2,3')
    #   Extract a single event
    parser.add_argument ("-e", "--eventnumber", action="store", dest="event_number",
                         type = int, metavar = "event_number")
    #   Event id's in order, comma seperated
    parser.add_argument ("--event_list", dest="evt_list",
                         help = "Comma separated list of event id's to gather from defined or selected events.",
                         metavar="evt_list")
    #   Extract all events in Event_t
    parser.add_argument ("-E", "--allevents", action="store_true", dest="all_events",
                         help = "Extract all events in event table.", default=False)
    #   The shot line number, 0 for Event_t
    parser.add_argument ("--shot_line", dest="shot_line", action="store",
                         help = "The shot line number that holds the shots.",
                         type=int, metavar="shot_line")
    #   Extract data for all stations starting at this time
    parser.add_argument ("-s", "--starttime", action="store", dest="start_time",
                        type=str, metavar="start_time")
    #   The array number
    parser.add_argument ("-A", "--station_array", dest="station_array", action="store",
                         help = "The array number that holds the station(s).",
                         type=int, metavar="station_array", required=True)                        
    #   Length of traces to put in gather
    parser.add_argument ("-l", "--length", action="store", required=True,
                         type=int, dest="length", metavar="length")
    #   Start trace at time offset from shot time
    parser.add_argument ("-O", "--seconds_offset_from_shot", "--offset", metavar="seconds_offset_from_shot",
                         help="Time in seconds from shot time to start the trace.",
                         type=float, default=0.)
    #   Do not time correct texan data
    parser.add_argument ("-N", "--notimecorrect", action="store_false", default=True,
                        dest="do_time_correct")
    #   Output directory
    parser.add_argument ("-o", "--out_dir", action="store", dest="out_dir", 
                         metavar="out_dir", type=str, default=".")
    #   Write to stdout
    parser.add_argument ("--stream", action="store_true", dest="write_stdout",
                         help="Write to stdout instead of a file.",
                         default=False)
    #   Use deploy and pickup times to determine where an instrument was deployed
    parser.add_argument ("--use_deploy_pickup", action="store_true", default=False,
                         help="Use deploy and pickup times to determine if data exists for a station.",
                         dest="deploy_pickup")    
    #   Stations to gather, comma seperated
    parser.add_argument ("-S", "--stations", "--station_list", dest="stations_to_gather",
                         help = "Comma separated list of stations to receiver gather.",
                         metavar = "stations_to_gather", required=False)
    #   Filter out all sample rates except the listed
    parser.add_argument ("-r", "--sample_rate_keep", action="store", dest="sample_rate",
                        metavar="sample_rate", type=float)
    #   Apply a reduction velocity, km
    parser.add_argument ("-V", "--reduction_velocity", action="store", dest="red_vel",
                         help="Reduction velocity in km/sec.",
                         metavar="red_vel", type=float, default="-1.")    
    #   Decimate data. Decimation factor
    parser.add_argument ("-d", "--decimation", action="store",
                         choices=["2", "4", "5", "8", "10", "20"], dest="decimation",
                         metavar="decimation")
    #   Convert geographic coordinated in ph5 to UTM before creating gather
    parser.add_argument ("-U", "--UTM", action="store_true", dest="use_utm",
                         help="Fill SEG-Y headers with UTM instead of lat/lon.",
                         default=False)
    #   How to fill in the extended trace header    
    parser.add_argument ("-x", "--extended_header", action="store", dest="ext_header",
                        help="Extended trace header style: \
                        'P' -> PASSCAL, \
                        'S' -> SEG, \
                        'U' -> Menlo USGS, \
                        default = U",
                        choices=["P", "S", "U", "I", "N"], default="U", metavar="extended_header_style")
    #   Ignore channel in Das_t. Only useful with texans
    parser.add_argument ("--ic", action="store_true", dest="ignore_channel", default=False)
    #   Allow traces to be 2^16 samples long vs 2^15
    parser.add_argument ("--break_standard", action = "store_false", dest = "break_standard",
                         help = "Force traces to be no longer than 2^15 samples.", default = True) 
    parser.add_argument ("--debug", dest = "debug", action = "store_true", default = False)
    
    ARGS = parser.parse_args ()  
    #print ARGS
    try :
        P5 = ph5api.PH5 (path=ARGS.ph5_path, nickname=ARGS.ph5_file_prefix)
    except Exception as e :
        sys.stderr.write ("Error: Can't open {0} at {1}.".format (ARGS.ph5_file_prefix, ARGS.ph5_path))
        sys.exit (-1)
    #
    if ARGS.event_number :
        ARGS.evt_list = list ([str (ARGS.event_number)])
    elif ARGS.evt_list :
        ARGS.evt_list = map (str, ARGS.evt_list.split (','))
    elif ARGS.start_time :
        ARGS.start_time = timedoy.TimeDOY (epoch=timedoy.passcal2epoch (ARGS.start_time, fepoch=True))
        ARGS.evt_list = [ARGS.start_time]
    #   
    if not ARGS.evt_list and not ARGS.all_events :
        sys.stderr.write ("Error: Required argument missing. event_number|evt_list|all_events.\n")
        sys.exit (-1)
    #   Event or shot line
    if ARGS.shot_line != None :
        if ARGS.shot_line == 0 :
            ARGS.shot_line = "Event_t"
        else :
            ARGS.shot_line = "Event_t_{0:03d}".format (ARGS.shot_line)
        
    elif not ARGS.start_time :
        sys.stderr.write ("Error: Shot line or start time required.")
        sys.exit (-2)
    #   Array or station line
    ARGS.station_array = "Array_t_{0:03d}".format (ARGS.station_array)
    #   Order of channels in gather
    ARGS.channels = map (int, ARGS.channels.split (','))
    #   Stations to gather
    if ARGS.stations_to_gather :
        ARGS.stations_to_gather = map (int, ARGS.stations_to_gather.split (','))
        ARGS.stations_to_gather.sort ()
        ARGS.stations_to_gather = map (str, ARGS.stations_to_gather)
        
    if not os.path.exists (ARGS.out_dir) :
        os.mkdir (ARGS.out_dir)
        os.chmod(ARGS.out_dir, 0777)    
    
def gather () :
    '''   Create event gather   '''
    if not ARGS.stations_to_gather :
        ARGS.stations_to_gather = P5.Array_t[ARGS.station_array]['order']
    if ARGS.all_events :
        ARGS.evt_list = P5.Event_t[ARGS.shot_line]['order']
    for evt in ARGS.evt_list :
        try :
            if not ARGS.start_time :
                if P5.Event_t.has_key (ARGS.shot_line) :
                    event_t = P5.Event_t[ARGS.shot_line]['byid'][evt]
                else :
                    P5.read_event_t (ARGS.shot_line)
                    event_t = P5.Event_t[ARGS.shot_line]['byid'][evt]
            else : event_t = None
                
            logging.info ("Extracting receivers for event {0:s}.".format (evt))
        except Exception as e :
            logging.warn ("Warning: The event {0} not found.\n".format (evt))
            continue
        #   
        fh = None
        #   Initialize 
        sf = segyfactory.Ssegy (None, event_t, utm = ARGS.use_utm)
        #   Allow lenght of traces to be up to 2^16 samples long
        sf.set_break_standard (ARGS.break_standard)
        #   Set external header type
        sf.set_ext_header_type (ARGS.ext_header)
        #   Set event information
        if event_t :
            sf.set_event_t (event_t)
            #   Event time
            event_tdoy = timedoy.TimeDOY (microsecond = event_t['time/micro_seconds_i'], 
                                          epoch = event_t['time/epoch_l'])
            Offset_t = P5.read_offsets_shot_order (ARGS.station_array, evt, ARGS.shot_line)
            #Offset_t = P5.calc_offsets (ARGS.station_array, evt, ARGS.shot_line)
        else :
            event_tdoy = evt
            Offset_t = None
            logging.warn ("Warning: No shot to receiver distances found.")
        if ARGS.seconds_offset_from_shot : 
            event_tdoy += ARGS.seconds_offset_from_shot
        end_tdoy = event_tdoy + ARGS.length
        #   Event start time
        start_fepoch = event_tdoy.epoch (fepoch=True)
        #   Trace cut end time
        stop_fepoch = end_tdoy.epoch (fepoch=True)
        #
        #if event_t :
            #Offset_t = P5.read_offsets_shot_order (ARGS.station_array, evt, ARGS.shot_line)
        Array_t = P5.Array_t[ARGS.station_array]['byid']
        #   All channels (components) available for this array
        chans_available = P5.channels_Array_t (ARGS.station_array)
        #   The trace sequence
        i = 0
        skipped_chans = 0
        for sta in ARGS.stations_to_gather :
            logging.info ("-=" * 20)
            logging.info ("Attempting to find data for station {0}.".format (sta))
            #   Shot to station information
            if Offset_t and Offset_t.has_key (sta) :
                offset_t = Offset_t[sta]
                sf.set_offset_t (offset_t)
            #   Array geometry
            if not Array_t.has_key (sta) :
                logging.info ("Warning: The station {0} is not in array {1}.".format (sta, ARGS.station_array))
                continue
            array_t = Array_t[sta]
            #   Filter out unwanted channels
            chans = []
            for c in ARGS.channels :
                if c in chans_available :
                    chans.append (c)
            #   Create channel name for output file name
            chan_name = ''
            for c in chans : chan_name += "{0}".format (c)
            num_traces = len (chans) * len (ARGS.stations_to_gather)
            #   Loop through channels
            for c in chans :
                if not array_t.has_key (c) :
                    logging.warn ("Warning: No channel information for {0} in array {1}.".format (c, ARGS.station_array))
                    skipped_chans += 1
                    continue
                try :
                    #   Filter out unwanted seed loc codes
                    if ARGS.seed_location and array_t[c][0]['seed_location_code_s'] != ARGS.seed_location :
                        logging.info ("Location code mismatch: {0}/{1}/{2}".format (array_t[c][0]['seed_location_code_s'],
                                                                                    ARGS.seed_location,
                                                                                    c))
                        continue
                    #   Filter out unwanted seed channels
                    seed_channel_code_s = ph5api.seed_channel_code (array_t[c][0])
                    if ARGS.seed_channel and seed_channel_code_s != ARGS.seed_channel :
                        logging.info ("Channel code mismatch: {0}/{1}/{2}".format (array_t[c][0]['seed_channel_code_s'],
                                                                                   ARGS.seed_channel,
                                                                                   c))
                        continue
                except :
                    pass
                #   Loop for each array_t per id_s and channel
                for t in range (len (array_t[c])) :
                    #   DAS
                    das = array_t[c][t]['das/serial_number_s']
                    #   Deploy time
                    start_epoch = array_t[c][t]['deploy_time/epoch_l']
                    #   Pickup time
                    stop_epoch = array_t[c][t]['pickup_time/epoch_l']
                    #   Is this shot within the deploy and pickup times
                    if not ph5api.is_in (start_epoch, stop_epoch, event_tdoy.epoch (), end_tdoy.epoch ()) :
                        logging.info ("Data logger {0} not deployed between {1} to {2} at {3}.".format (array_t[c][t]['das/serial_number_s'], event_tdoy, end_tdoy, sta))
                        if ARGS.deploy_pickup :
                            logging.info ("Skipping.")  
                            continue 
                    #   Read Das table, may already be read so don't reread it
                    #   XXX   Debug only
                    try :
                        das_or_fail = P5.read_das_t (das, start_epoch=start_fepoch, stop_epoch=stop_fepoch, reread=False)
                    except :
                        logging.warn ("Failed to read DAS: {0} between {1} and {2}.".format (das, timedoy.epoch2passcal (start_epoch), timedoy.epoch2passcal (stop_epoch)))
                        continue
                    
                    if das_or_fail == None :
                        logging.warn ("Failed to read DAS: {0} between {1} and {2}.".format (das, timedoy.epoch2passcal (start_epoch), timedoy.epoch2passcal (stop_epoch)))
                        continue
                    
                    #   Sample rate
                    if P5.Das_t.has_key (array_t[c][t]['das/serial_number_s']) :
                        sr = float (P5.Das_t[array_t[c][t]['das/serial_number_s']]['rows'][0]['sample_rate_i']) / float (P5.Das_t[array_t[c][t]['das/serial_number_s']]['rows'][0]['sample_rate_multiplier_i'])     
                    else : sr = 0.   #   Oops! No data for this DAS
                    #   Check v4 sample rate from array_t
                    try :
                        if sr != array_t[c][0]['sample_rate_i'] / float (array_t[c][0]['sample_rate_multiplier_i']) :
                            continue
                    except :
                        pass
                    ###   Need to check against command line sample rate here
                    if ARGS.sample_rate and ARGS.sample_rate != sr :
                        logging.warn ("Warning: Sample rate for {0} is not {1}. Skipping.".format (das, sr))
                        continue
                    sf.set_length_points (int ((stop_fepoch - start_fepoch) * sr))
                    
                    ###   Need to apply reduction velocity here
                    #   Set cut start and stop times
                    cut_start_fepoch = start_fepoch
                    cut_stop_fepoch = stop_fepoch                                      
                    if ARGS.red_vel > 0. :
                                               
                        try :
                            secs, errs = segyfactory.calc_red_vel_secs (offset_t, ARGS.red_vel)
                        except Exception as e :
                            secs = 0.
                            errs = "Can not calculate reduction velocity: {0}.".format (e.message)
                        for e in errs : logging.info (e)
                        cut_start_fepoch += secs
                        cut_stop_fepoch += secs  
                    #
                    sf.set_cut_start_epoch (cut_start_fepoch)
                    sf.set_array_t (array_t[c][t])
                    #
                    ###   Cut trace
                    #     Need to pad iff multiple traces
                    traces = P5.cut (das, cut_start_fepoch, cut_stop_fepoch, chan=c, sample_rate=sr, apply_time_correction=ARGS.do_time_correct)
                    if len (traces[0].data) == 0 :
                        logging.warn ("Warning: No data found for {0} for station {1}.".format (das, sta))
                        continue
                    trace = ph5api.pad_traces (traces)
                    if ARGS.do_time_correct :
                        logging.info ("Applied time drift correction by shifting trace by {0} samples.".format (-1 * sr * (trace.time_correction_ms/1000.)))
                        logging.info ("Correction is {0} ms.".format (trace.time_correction_ms))
                        logging.info ("Clock drift (seconds/second): {0}".format (trace.clock.slope))
                        for tccomment in trace.clock.comment :
                            tccmt = tccomment.split ('\n')
                            for tcc in tccmt :
                                logging.info ("Clock comment: {0}".format (tcc))
                    if trace.padding != 0 :
                        logging.warn ("Warning: There were {0} samples of padding added to fill gap at middle or end of trace.".format (trace.padding))
                    ##   This may be a command line option later
                    #if True :
                        #if trace.response_t :
                            #try :
                                #tmp_data = trace.data * trace.response_t['bit_weight/value_d']
                                #trace.data = tmp_data
                            #except Exception as e :
                                #logging.warn ("Warning: Failed to apply bit weight. {0}".format (e.message))
                    ###   Need to apply decimation here
                    if ARGS.decimation :
                        #   Decimate
                        shift, data = decimate.decimate (DECIMATION_FACTORS[ARGS.decimation], trace.data)
                        #   Set new sample rate
                        wsr = int (sr/int (ARGS.decimation))
                        sf.set_sample_rate (wsr)
                        trace.sample_rate = wsr
                        #   Set length of trace in samples
                        sf.set_length_points (len (data))
                        sf.length_points_all = len (data)
                        trace.nsamples = len (data) 
                        trace.data = data
                    #   Did we read any data?
                    if trace.nsamples == 0 :
                        #   Failed to read any data
                        logging.warning ("Warning: No data for data logger {2}/{0} starting at {1}.".format (das, trace.start_time, sta))
                        continue 
                    #   Read receiver and response tables
                    receiver_t = trace.receiver_t
                    if receiver_t :
                        sf.set_receiver_t (receiver_t)
                    else :
                        logging.warning ("No sensor orientation found in ph5 file. Contact PIC.")
                    #   Read gain and bit weight
                    response_t = trace.response_t
                    if response_t :
                        sf.set_response_t (response_t)
                    else :
                        logging.warning ("No gain or bit weight found in ph5 file. Contact PIC.")
                    #   Increment line sequence
                    i += 1
                    sf.set_line_sequence (i)
                    sf.set_das_t (trace.das_t[0])
                    logging.info ("=-" * 20)
                    logging.info ("trace: {0}".format (i))
                    logging.info ("Extracted: Station ID {0}".format (sta))
                    logging.info ("Chan: {2} Start: {0:s}, Stop: {1:s}.".format (event_tdoy, 
                                                                                 end_tdoy, 
                                                                                 c)) 
                    logging.info ("Lat: %f Lon: %f Elev: %f %s" % (array_t[c][t]['location/Y/value_d'],
                                                                   array_t[c][t]['location/X/value_d'],
                                                                   array_t[c][t]['location/Z/value_d'],
                                                                   array_t[c][t]['location/Z/units_s'].strip ())) 
                    #
                    ###   Open SEG-Y file
                    #
                    if not fh :
                        if ARGS.write_stdout :
                            try :
                                fh = sys.stdout
                            except Exception as e :
                                logging.error ("{0}".format (e.message))
                                logging.error ("Failed to open STDOUT. Can not continue.")
                                sys.exit (-1)
                        else :
                            #
                            ###   Set up file naming
                            #
                            try :
                                nickname = P5.Experiment_t['rows'][-1]['nickname_s']
                            except :
                                nickname = "X"
                            #
                            base = "{0}_{1}_{2}_{3}".format (nickname, ARGS.station_array[-3:], evt, chan_name)
                            outfilename = "{1:s}/{0:s}_0001.SGY".format (base, ARGS.out_dir)
                            #   Make sure that the name in unique
                            j = 1
                            while os.path.exists (outfilename) :
                                j += 1
                                tmp = outfilename[:-8]
                                outfilename = "{0}{1:04d}.SGY".format (tmp, j) 
                            #   Open SEG-Y file
                            try :
                                fh = open (outfilename, 'w+')
                                logging.info ("Opened: {0}".format (outfilename))
                            except Exception as e :
                                logging.error ("Error: Failed to open {0}.\t{1}".format (outfilename, e.message))
                                sys.stderr.write ("Error: Failed to open {0}.\t{1}".format (outfilename, e.message))
                                sys.exit () 
                        #   Write reel headers and first trace
                        logs = segyfactory.write_segy_hdr (trace, fh, sf, num_traces)
                        #   Write any messages
                        for l in logs : logging.info (l)
                    else :
                        #   Write trace
                        logs = segyfactory.write_segy (trace, fh, sf)
                        for l in logs : logging.info (l) 
            #   chan
        #   Traces found does not match traces expected
        if i != num_traces and fh :
            #   Need to update reel_header
            if (num_traces - skipped_chans) < i :
                logging.warn ("Warning: Wrote {0} of {1} trace/channels listed in {2}.".format (i, num_traces - skipped_chans, ARGS.station_array))
            sf.set_text_header (i)
            fh.seek (0, os.SEEK_SET)
            sf.write_text_header (fh)
            sf.set_reel_header (i)
            fh.seek (3200, os.SEEK_SET)
            sf.write_reel_header (fh)
        ##   Decimation
        #if ARGS.decimation :
            ##   Need to update reel_header
            #sf.set_sample_rate (wsr)
            #sf.set_length_points (trace.nsamples)
            #sf.set_text_header (i)
            #fh.seek (0, os.SEEK_SET)
            #sf.write_text_header (fh)
            #sf.set_reel_header (i)
            #fh.seek (3200, os.SEEK_SET)
            #sf.write_reel_header (fh)
        try :            
            fh.close ()
        except AttributeError :
            pass
        #   sta
    #   evt


def main():
    get_args ()
    #   --stream set
    if ARGS.write_stdout :
        logging.basicConfig (
            #stream = sys.stderr,
            format = "%(asctime)s %(message)s",
            level = logging.ERROR
        ) 
    #   Write log to file
    else :
        logging.basicConfig (
            filename = os.path.join (ARGS.out_dir, "ph5toevt.log"),
            format = "%(asctime)s %(message)s",
            level = logging.INFO
        )
    ###
    logging.info ("{0}: {1}".format (PROG_VERSION, sys.argv))
    P5.read_event_t_names ()
    if not ARGS.start_time :
        if not ARGS.shot_line in P5.Event_t_names :
            logging.error ("Error: {0} not found. {1}\n".format (ARGS.shot_line, " ".join (P5.Event_t_names)))
            sys.exit (-1)
        else :
            P5.read_event_t (ARGS.shot_line)
            #SHOTS_ALL = P5.Event_t[ARGS.shot_line]['byid'].keys ()
    P5.read_array_t_names ()
    if not ARGS.station_array in P5.Array_t_names :
        logging.error ("Error: {0} not found.  {1}\n".format (ARGS.station_array, " ".join (P5.Array_t_names)))
        sys.exit (-1)
    else :
        P5.read_array_t (ARGS.station_array)
        #STATIONS_ALL = P5.Array_t[ARGS.station_array]['byid'].keys ()
       
    P5.read_receiver_t ()
    P5.read_response_t ()
    P5.read_experiment_t ()
    if P5.Experiment_t != None and P5.Experiment_t['rows'] != [] :
        experiment_t = P5.Experiment_t['rows'][-1]
        logging.info ("Experiment: {0}".format (experiment_t['longname_s'].strip ()))
        logging.info ("Summary: {0}".format (experiment_t['summary_paragraph_s'].strip ()))
        if ARGS.seed_network and P5.Experiment_t['net_code_s'] != ARGS.seed_network :
            logging.info ("Netcode mis-match: {0}/{1}".format (P5.Experiment_t['net_code_s'], ARGS.seed_network))
            sys.exit (-1)
    else :
        logging.warning ("Warning: No experiment information found. Contact PIC.")
    gather ()
    logging.info ("Done.")
    logging.shutdown ()
    P5.close ()
    sys.stderr.write ("Done\n")


if __name__ == '__main__' :
    main()
