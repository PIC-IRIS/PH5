#!/usr/bin/env pnpython4
#
#   Produce SEG-Y in receiver order from a PH5 file using API
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
    '''
       Program arguments
    '''
    global ARGS, P5
    import argparse
    
    parser = argparse.ArgumentParser ()
    
    parser.usage = "Version: {0}: ph5torec -n nickname -p path_to_ph5_files --stations=stations_list --shot_line --length [options]".format (PROG_VERSION)
    parser.description = "Generate SEG-Y gathers in receiver order..."
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
    #   Stations to gather, comma seperated
    parser.add_argument ("-S", "--stations", "--station_list", dest="stations_to_gather",
                         help = "Comma separated list of stations to receiver gather.",
                         metavar = "stations_to_gather", required=True)
    #   Event id's in order, comma seperated
    parser.add_argument ("--event_list", dest="evt_list",
                         help = "Comma separated list of event id's to gather from defined or selected events.",
                         metavar="evt_list")
    #   Length of traces to put in gather
    parser.add_argument ("-l", "--length", action="store", required=True,
                         type=int, dest="length", metavar="length")
    #   Start trace at time offset from shot time
    parser.add_argument ("-O", "--seconds_offset_from_shot", "--offset", metavar="seconds_offset_from_shot",
                         help="Time in seconds from shot time to start the trace.",
                         type=float, default=0.)
    #   The array number
    parser.add_argument ("-A", "--station_array", dest="station_array", action="store",
                         help = "The array number that holds the station(s).",
                         type=int, metavar="station_array", required=True)
    #   The shot line number, 0 for Event_t
    parser.add_argument ("--shot_line", dest="shot_line", action="store",
                         help = "The shot line number that holds the shots.",
                         type=int, metavar="shot_line", required=True)
    #   Output directory
    parser.add_argument ("-o", "--out_dir", action="store", dest="out_dir", 
                         metavar="out_dir", type=str, default=".")
    #   Write to stdout
    parser.add_argument ("--stream", action="store_true", dest="write_stdout",
                         help="Write to stdout instead of a file.",
                         default=False)    
    #parser.add_argument ("-f", "--format", action="store", choices=["SEGY", "PSGY"],
                         #dest="format", metavar="format")
    #   Shot range to extract
    parser.add_argument ("-r", "--shot_range", action="store", dest="shot_range",
                         help="example: --shot_range=1001-11001",
                         metavar="shot_range")
    #   Apply a reduction velocity, km
    parser.add_argument ("-V", "--reduction_velocity", action="store", dest="red_vel",
                         metavar="red_vel", type=float, default="-1.")
    #   Decimate data. Decimation factor
    parser.add_argument ("-d", "--decimation", action="store",
                         choices=["2", "4", "5", "8", "10", "20"], dest="decimation",
                         metavar="decimation")
    #   Sort traces in gather by offset
    parser.add_argument ("--sort_by_offset", action="store_true", dest="sort_by_offset",
                         default=False)
    #   Use deploy and pickup times to determine where an instrument was deployed
    parser.add_argument ("--use_deploy_pickup", action="store_true", default=True,
                         help="Use deploy and pickup times to determine if data exists for a station.",
                         dest="deploy_pickup")
    #   Convert geographic coordinated in ph5 to UTM before creating gather
    parser.add_argument ("-U", "--UTM", action="store_true", dest="use_utm",
                         help="Fill SEG-Y headers with UTM instead of lat/lon.",
                         default=False)
    #   How to fill in the extended trace header
    parser.add_argument ("-x", "--extended_header", action="store", dest="ext_header",
                         help="Extended trace header style: \
                         'P' -> PASSCAL, \
                         'S' -> SEG, \
                         'U' -> Menlo USGS, default = U",
                         choices=["P", "S", "U"], default="U", metavar="extended_header_style")
    #   Ignore channel in Das_t. Only useful with texans
    parser.add_argument ("--ic", action="store_true", dest="ignore_channel", default=False)
    #   Allow traces to be 2^16 samples long vs 2^15
    parser.add_argument ("--break_standard", action = "store_false", dest = "break_standard",
                         help = "Force traces to be no longer than 2^15 samples.", default = True)
    #   Do not time correct texan data
    parser.add_argument ("-N", "--notimecorrect", action="store_false", default=True,
                         dest="do_time_correct")
    parser.add_argument ("--debug", dest = "debug", action = "store_true", default = False)
    
    ARGS = parser.parse_args ()
    #print ARGS
    try :
        P5 = ph5api.PH5 (path=ARGS.ph5_path, nickname=ARGS.ph5_file_prefix)
    except Exception as e :
        sys.stderr.write ("Error: Can't open {0} at {1}.".format (ARGS.ph5_file_prefix, ARGS.ph5_path))
        sys.exit (-1)
    
    if ARGS.shot_line == 0 :
        ARGS.shot_line = "Event_t"
    else :
        ARGS.shot_line = "Event_t_{0:03d}".format (ARGS.shot_line)
        
    ARGS.station_array = "Array_t_{0:03d}".format (ARGS.station_array)
    ARGS.stations_to_gather = ARGS.stations_to_gather.split (',')
    if ARGS.evt_list :
        ARGS.evt_list = ARGS.evt_list.split (',')
    elif ARGS.shot_range :
        a, b = map (int, ARGS.shot_range.split ('-'))
        ARGS.evt_list = map (str, range (a, b+1, 1))
        #print ARGS.evt_list[0], ARGS.evt_list[-1]
    ARGS.channels = map (int, ARGS.channels.split (','))
    
    if not os.path.exists (ARGS.out_dir) :
        os.mkdir (ARGS.out_dir)
        os.chmod(ARGS.out_dir, 0777)
    
def create_channel_map () :
    pass

def gather () :
    '''   Create receiver gather   '''
    for sta in ARGS.stations_to_gather :
        try :
            #   Read the appropriate line from Array_t
            if P5.Array_t.has_key (ARGS.station_array) :
                array_t = P5.Array_t[ARGS.station_array]['byid'][sta]
            else :
                P5.read_array_t (ARGS.station_array)
                array_t = P5.Array_t[ARGS.station_array]['byid'][sta]
            logging.info ("Extracting receiver(s) at station {0:s}.".format (sta))
            logging.info ("Found the following components:")
            for c in array_t.keys () :
                logging.info ("DAS: {0} component: {1}".format (array_t[c][0]['das/serial_number_s'], c))
                logging.info ("Lat: {0} Lon: {1} Elev: {2}".format (array_t[c][0]['location/Y/value_d'],
                                                                    array_t[c][0]['location/X/value_d'],
                                                                    array_t[c][0]['location/Z/value_d']))   
            #   Read the appropriate line from Das_t and get the sample rate
            P5.read_das_t (array_t[c][0]['das/serial_number_s'],
                           array_t[c][0]['deploy_time/epoch_l'],
                           array_t[c][0]['pickup_time/epoch_l'])
            sr = float (P5.Das_t[array_t[c][0]['das/serial_number_s']]['rows'][0]['sample_rate_i']) / float (P5.Das_t[array_t[c][0]['das/serial_number_s']]['rows'][0]['sample_rate_multiplier_i'])                
        except KeyError as e :
            logging.warn ("Warning: The station {0} not found in the current array.\n".format (sta))
            continue
        ###
        i = 0   #   Number of traces found
        fh = None   #   SEG-Y file 
        #   Get a mostly empty instance of segyfactory
        sf = segyfactory.Ssegy (None, None, utm=ARGS.use_utm)
        #   Set the type of extended header to write
        sf.set_ext_header_type (ARGS.ext_header)
        #   Should we allow traces that are 2^16 samples long
        sf.set_break_standard (ARGS.break_standard)
        ###   Filter out un-wanted channels here
        chans_available = array_t.keys ()
        chans = []
        #   Put the desired channels in the desired order
        for c in ARGS.channels :
            if c in chans_available :
                chans.append (c)
        #   Channel name for output file name
        chan_name = ''
        for c in chans : chan_name += "{0}".format (c)

        #   Read Event_t_xxx
        Event_t = P5.Event_t[ARGS.shot_line]['byid']
        order = P5.Event_t[ARGS.shot_line]['order']
        #print order[0], order[-1]
        #   Take a guess at the number of traces in this SEG-Y file based on number of shots
        num_traces = len (order) * len (chans)
        #   Try to read offset distances (keyed on shot id's)
        Offset_t = P5.read_offsets_receiver_order (ARGS.station_array, sta, ARGS.shot_line)
        #   Loop through each shot by shot id
        for o in order :
            #print o
            ###   Check event list (and also shot_range), ARGS.evt_list, here!
            if ARGS.evt_list :
                if not o in ARGS.evt_list : continue
            #XXX
            #print "Shot ID: ", o
            #   Appropriate line from Event_t
            event_t = Event_t[o]
            ###   Need to handle time offset here, ARGS.seconds_offset_from_shot
            event_tdoy = timedoy.TimeDOY (microsecond=event_t['time/micro_seconds_i'],  
                                          epoch=event_t['time/epoch_l'])
            #   Adjust start time based on offset entered on command line
            if ARGS.seconds_offset_from_shot : event_tdoy += ARGS.seconds_offset_from_shot
            end_tdoy = event_tdoy + ARGS.length
            #
            start_fepoch = event_tdoy.epoch (fepoch=True)
            stop_fepoch = end_tdoy.epoch (fepoch=True)
            #   Set start time in segyfactory
            sf.set_cut_start_epoch (start_fepoch)
            #   Set event
            sf.set_event_t (event_t)
            #   Set shot to receiver distance
            sf.set_offset_t (Offset_t[o])
            #   Set number of samples in trace, gets reset if decimated
            sf.set_length_points (int ((stop_fepoch - start_fepoch) * sr))
            #   Loop through each channel (channel_number_i)
            for c in chans :
                if not array_t.has_key (c) :
                    continue
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
                #   DAS
                das = array_t[c][0]['das/serial_number_s']
                for t in range (len (array_t[c])) :
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

                    ###   Need to apply reduction velocity here
                    if ARGS.red_vel > 0. :
                        try :
                            secs, errs = segyfactory.calc_red_vel_secs (Offset[o], ARGS.red_vel)
                        except Exception as e :
                            secs = 0.
                            errs = "Can not calculate reduction velocity: {0}.".format (e.message)
                        for e in errs : logging.info (e)
                        start_fepoch += secs
                        stop_fepoch += secs
                    #   Set array_t in segyfactory
                    sf.set_array_t (array_t[c][t])
                    #   Read Das table
                    #print ph5api.__version__
                    P5.forget_das_t (das)
                    #P5.read_das_t (das, start_epoch=start_fepoch, stop_epoch=stop_fepoch, reread=False)
                    #
                    ###   Cut trace
                    #                    
                    traces = P5.cut (das, start_fepoch, stop_fepoch, chan=c, sample_rate=sr)
                    trace = ph5api.pad_traces (traces)
                    if ARGS.do_time_correct :
                        logging.info ("Applied time drift correction by shifting trace by {0} samples.".format (-1 * sr * (trace.time_correction_ms/1000.)))
                        logging.info ("Correction is {0} ms.".format (trace.time_correction_ms))
                        logging.info ("Clock drift (seconds/second): {0}".format (trace.clock.slope))
                        for tccomment in trace.clock.comment :
                            tccmt = tccomment.split ('\n')
                            for tcc in tccmt :
                                logging.info ("Clock comment: {0}".format (tcc))                    
                    if trace.nsamples == 0 :
                        logging.info ("No data found for DAS {0} between {1} and {2}.".format (das, event_tdoy.getPasscalTime (), end_tdoy.getPasscalTime ()))
                        continue
                    if trace.padding != 0 :
                        logging.warn ("Warning: There were {0} samples of padding added to fill gap(s) in original traces.".trace.padding)
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
                        trace.nsamples = len (data)
                        
                    if trace.nsamples == 0 :
                        #   Failed to read any data
                        logging.warning ("Warning: No data for data logger {0} starting at {1}.".format (das, trace.start_time))
                        continue
                    #   Read receiver and response tables
                    #receiver_t = P5.Receiver_t['rows'][trace.das_t[0]['receiver_table_n_i']]
                    receiver_t = trace.receiver_t
                    response_t = P5.Response_t['rows'][trace.das_t[0]['response_table_n_i']]
                    #   Set sort_t in segyfactory
                    sf.set_sort_t (P5.get_sort_t (start_fepoch, ARGS.station_array))
                    #   Set das_t
                    sf.set_das_t (trace.das_t[0])
                    #   Line sequence (trace number)
                    sf.set_line_sequence (i); i += 1
                    if response_t :
                        sf.set_response_t (response_t)
                    else :
                        logging.warning ("No gain or bit weight found in ph5 file. Contact PIC.")
                    if receiver_t :
                        sf.set_receiver_t (receiver_t)
                    else :
                        logging.warning ("No sensor orientation found in ph5 file. Contact PIC.")
                    #   Some informational logging   
                    logging.info ("trace: {0}".format (i))
                    logging.info ("-=" * 20)
                    logging.info ("Extracting: Event ID %s" % event_t['id_s'])
                    logging.info ("Chan: {2} Start: {0:s}, Stop: {1:s}.".format (event_tdoy, 
                                                                                 end_tdoy, 
                                                                                 c))
                    logging.info ("Lat: %f Lon: %f Elev: %f %s" % (event_t['location/Y/value_d'],
                                                                   event_t['location/X/value_d'],
                                                                   event_t['location/Z/value_d'],
                                                                   event_t['location/Z/units_s'].strip ()))                
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
                            ###   Set up file nameing
                            #
                            try :
                                nickname = P5.Experiment_t['rows'][-1]['nickname_s']
                            except :
                                nickname = "X"
                            #
                            base = "{0}_{1}_{2}_{3}".format (nickname, ARGS.station_array[-3:], sta, chan_name)
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
                        try :
                            logs = segyfactory.write_segy_hdr (trace, fh, sf, num_traces)
                            #   Write any messages
                            for l in logs : logging.info (l)
                        except segyfactory.SEGYError as e :
                            logging.error ("Error: Header write failure.")
                            sys.exit ()
                    else :
                        #   Write trace
                        try :
                            logs = segyfactory.write_segy (trace, fh, sf)
                            for l in logs : logging.info (l)
                            logging.info ('=-' * 40)
                        except segyfactory.SEGYError as e :
                            logging.error ("Error: Trace write failure.")
                            sys.exit ()
                #
        #   Traces found does not match traces expected
        if fh and i != num_traces :
            #   Need to update reel_header
            logging.warn ("Wrote {0} of {1} traces listed in {2}.".format (i, num_traces, ARGS.station_array))
            sf.set_text_header (i)
            fh.seek (0, os.SEEK_SET)
            sf.write_text_header (fh)
            sf.set_reel_header (i)
            fh.seek (3200, os.SEEK_SET)
            sf.write_reel_header (fh)
            
        if fh : fh.close ()


def main():
    #global STATIONS_ALL, SHOTS_ALL
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
            filename = os.path.join (ARGS.out_dir, "ph5torec.log"),
            format = "%(asctime)s %(message)s",
            level = logging.INFO
        )
    ###    
    logging.info ("{0}: {1}".format (PROG_VERSION, sys.argv))
    P5.read_event_t_names ()
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
    P5.read_sort_t ()
    if P5.Experiment_t :
        experiment_t = P5.Experiment_t['rows'][-1]
        logging.info ("Experiment: {0}".format (experiment_t['longname_s'].strip ()))
        logging.info ("Summary: {0}".format (experiment_t['summary_paragraph_s'].strip ()))
        if ARGS.seed_network and P5.Experiment_t['net_code_s'] != ARGS.seed_network :
            logging.info ("Netcode mis-match: {0}/{1}".format (P5.Experiment_t['net_code_s'], ARGS.seed_network))
            sys.exit (-1)        
    else :
        logging.warning ("Warning: No experiment information found. Contact PIC.")
        
    #import cProfile, pstats
    #sys.stderr.write ("Warning: Profiling enabled! Contact PASSCAL.\n")
    #cProfile.run ('trace = P5.cut (das, start_fepoch, stop_fepoch, chan=c)', 'ph5toreccut.profile')
    #p = pstats.Stats ("ph5toreccut.profile")
    #p.sort_stats('time').print_stats(40)    
    gather ()
    logging.info ("Done.")
    logging.shutdown ()
    P5.close ()
    sys.stderr.write ("Done\n")


if __name__ == '__main__' :
    main()
    