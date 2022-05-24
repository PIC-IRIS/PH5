#!/usr/bin/env pnpython4
#
# Produce SEG-Y in shot (event) order from PH5 file using API
#
# Steve Azevedo, August 2016
#

import argparse
import os
import sys
import logging
from ph5 import LOGGING_FORMAT
from ph5.core import ph5api, segyfactory, decimate, timedoy, external_file

PROG_VERSION = "2022.144"
LOGGER = logging.getLogger(__name__)
# This should never get used. See ph5api.
CHAN_MAP = {1: 'Z', 2: 'N', 3: 'E', 4: 'Z', 5: 'N', 6: 'E'}
DECIMATION_FACTORS = segyfactory.DECIMATION_FACTORS


def get_args():
    '''   Read command line argments   '''

    parser = argparse.ArgumentParser()

    parser.usage = "Version: %s\n" % PROG_VERSION
    parser.usage += "ph5toevt --eventnumber=shot --nickname=experiment_nickname\
    --length=seconds [--path=ph5_directory_path] [options]\n"
    parser.usage += "\toptions:\n\t--array=array, --offset=seconds (float),\
    --reduction_velocity=km-per-second (float) --format=['SEGY']\n\n"
    parser.usage += "ph5toevt --allevents --nickname=experiment_nickname\
    --length=seconds [--path=ph5_directory_path] [options]\n"
    parser.usage += "\toptions:\n\t--array=array, --offset=seconds (float),\
    --reduction_velocity=km-per-second (float) --format=['SEGY']\n\n"
    parser.usage += "ph5toevt --starttime=yyyy:jjj:hh:mm:ss[:.]sss\
    --nickname=experiment_nickname --length=seconds\
    [--path=ph5_directory_path] [options]\n"
    parser.usage += "\toptions:\n\t--stoptime=yyyy:jjj:hh:mm:ss[:.]sss,\
    --array=array, --reduction_velocity=km-per-second (float)\
    --format=['SEGY']\n\n"
    parser.usage += "\n\n\tgeneral options:\n\t--channel=[1,2,3]\n\t\
    --sample_rate_keep=sample_rate\n\t--notimecorrect\n\t\
    --decimation=[2,4,5,8,10,20]\n\t--out_dir=output_directory"

    parser.description = "Generate SEG-Y gathers in shot order..."
    # Usually master.ph5
    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)
    # Path to the directory that holds master.ph5
    parser.add_argument("-p", "--path", dest="ph5_path",
                        help="Path to ph5 files. Default current directory.",
                        metavar="ph5_path", default='.')
    # SEED channel
    parser.add_argument("--channel", dest="seed_channel",
                        help="Filter on SEED channel.",
                        metavar="seed_channel")
    # SEED network code
    parser.add_argument("--network", dest="seed_network",
                        help="Filter on SEED net code.",
                        metavar="seed_network")
    # SEED loc code
    parser.add_argument("--location", dest="seed_location",
                        help="Filter on SEED loc code.",
                        metavar="seed_location")
    # Channels. Will extract in order listed here. 'Usually' 1 -> Z, 2-> N, 3
    # -> E
    parser.add_argument("-c", "--channels", action="store",
                        help="List of comma seperated channels to extract.\
                        Default = 1,2,3.",
                        type=str, dest="channels", metavar="channels",
                        default='1,2,3')
    # Extract a single event
    parser.add_argument("-e", "--eventnumber", action="store",
                        dest="event_number",
                        type=int, metavar="event_number")
    # Event id's in order, comma seperated
    parser.add_argument("--event_list", dest="evt_list",
                        help="Comma separated list of event id's\
                        to gather from defined or selected events.",
                        metavar="evt_list")
    # Extract all events in Event_t
    parser.add_argument("-E", "--allevents", action="store_true",
                        dest="all_events",
                        help="Extract all events in event table.",
                        default=False)
    # The shot line number, 0 for Event_t
    parser.add_argument("--shot_line", dest="shot_line", action="store",
                        help="The shot line number that holds the shots.",
                        type=int, metavar="shot_line")
    # External shot line file
    parser.add_argument("--shot_file", dest="shot_file", action="store",
                        help="Input an external kef file that contains\
                        event information, Event_t.kef.",
                        type=str, metavar="shot_file")
    # Extract data for all stations starting at this time
    parser.add_argument("-s", "--starttime", action="store", dest="start_time",
                        type=str, metavar="start_time")
    # The array number
    parser.add_argument("-A", "--station_array", dest="station_array",
                        action="store",
                        help="The array number that holds the station(s).",
                        type=int, metavar="station_array", required=True)
    # Length of traces to put in gather
    parser.add_argument("-l", "--length", action="store", required=True,
                        type=int, dest="length", metavar="length")
    # Start trace at time offset from shot time
    parser.add_argument("-O", "--seconds_offset_from_shot", "--offset",
                        metavar="seconds_offset_from_shot",
                        help="Time in seconds from shot time\
                        to start the trace.",
                        type=float, default=0.)
    # Do not time correct texan data
    parser.add_argument("-N", "--notimecorrect", action="store_false",
                        default=True,
                        dest="do_time_correct")
    # Output directory
    parser.add_argument("-o", "--out_dir", action="store", dest="out_dir",
                        metavar="out_dir", type=str, default=".")
    # Write to stdout
    parser.add_argument("--stream", action="store_true", dest="write_stdout",
                        help="Write to stdout instead of a file.",
                        default=False)
    # Use deploy and pickup times to determine where an instrument was
    # deployed
    parser.add_argument("--use_deploy_pickup", action="store_true",
                        default=False,
                        help="Use deploy and pickup times to determine\
                        if data exists for a station.",
                        dest="deploy_pickup")
    # Stations to gather, comma seperated
    parser.add_argument("-S", "--stations", "--station_list",
                        dest="stations_to_gather",
                        help="Comma separated list of stations\
                        to receiver gather.",
                        metavar="stations_to_gather", required=False)
    # Filter out all sample rates except the listed
    parser.add_argument("-r", "--sample_rate_keep", action="store",
                        dest="sample_rate",
                        metavar="sample_rate", type=float)
    # Apply a reduction velocity, km
    parser.add_argument("-V", "--reduction_velocity", action="store",
                        dest="red_vel",
                        help="Reduction velocity in km/sec.",
                        metavar="red_vel", type=float, default="-1.")
    # Decimate data. Decimation factor
    parser.add_argument("-d", "--decimation", action="store",
                        choices=["2", "4", "5", "8", "10", "20"],
                        dest="decimation",
                        metavar="decimation")
    # Convert geographic coordinated in ph5 to UTM before creating gather
    parser.add_argument("-U", "--UTM", action="store_true", dest="use_utm",
                        help="Fill SEG-Y headers with UTM instead of lat/lon.",
                        default=False)
    # How to fill in the extended trace header
    parser.add_argument("-x", "--extended_header", action="store",
                        dest="ext_header",
                        help="Extended trace header style: \
                        'P' -> PASSCAL, \
                        'S' -> SEG, \
                        'U' -> Menlo USGS, \
                        default = U",
                        choices=["P", "S", "U", "I", "N"], default="U",
                        metavar="extended_header_style")
    # Ignore channel in Das_t. Only useful with texans
    parser.add_argument("--ic", action="store_true",
                        dest="ignore_channel", default=False)
    # Allow traces to be 2^16 samples long vs 2^15
    parser.add_argument("--break_standard", action="store_false",
                        dest="break_standard",
                        help="Force traces to be no longer than 2^15 samples.",
                        default=True)
    parser.add_argument("--debug", dest="debug",
                        action="store_true", default=False)

    args = parser.parse_args()
    try:
        p5 = ph5api.PH5(path=args.ph5_path, nickname=args.ph5_file_prefix)
    except Exception:
        LOGGER.error("Can't open {0} at {1}.".format(
            args.ph5_file_prefix, args.ph5_path))
        sys.exit(-1)

    if args.shot_file:
        if not args.shot_line:
            LOGGER.error(
                "Shot line switch, --shot_line,\
                required when using external shot file.")
            sys.exit(-3)
        external = external_file.External(args.shot_file)
        args.shot_file = external.Event_t
        p5.Event_t_names = args.shot_file.keys()
    else:
        p5.read_event_t_names()

    if args.event_number:
        args.evt_list = list([str(args.event_number)])
    elif args.evt_list:
        args.evt_list = map(str, args.evt_list.split(','))
    elif args.start_time:
        args.start_time = timedoy.TimeDOY(
            epoch=timedoy.passcal2epoch(args.start_time, fepoch=True))
        args.evt_list = [args.start_time]

    if not args.evt_list and not args.all_events:
        LOGGER.error(
            "Required argument missing.\
            event_number|evt_list|all_events.\n")
        sys.exit(-1)
    # Event or shot line
    if args.shot_line is not None:
        if args.shot_line == 0:
            args.shot_line = "Event_t"
        else:
            args.shot_line = "Event_t_{0:03d}".format(args.shot_line)
    elif not args.start_time:
        LOGGER.error("Shot line or start time required.")
        sys.exit(-2)
    # Array or station line
    args.station_array = "Array_t_{0:03d}".format(args.station_array)
    # Order of channels in gather
    args.channels = map(int, args.channels.split(','))
    # Stations to gather
    if args.stations_to_gather:
        args.stations_to_gather = map(int, args.stations_to_gather.split(','))
        args.stations_to_gather.sort()
        args.stations_to_gather = map(str, args.stations_to_gather)

    if not os.path.exists(args.out_dir):
        os.mkdir(args.out_dir)
        os.chmod(args.out_dir, 0o777)
    return args, p5


def gather(args, p5):
    '''   Create event gather   '''
    if not args.stations_to_gather:
        args.stations_to_gather = p5.Array_t[args.station_array]['order']
    if args.all_events:
        args.evt_list = p5.Event_t[args.shot_line]['order']

    for evt in args.evt_list:
        try:
            if not args.start_time:
                event_t = p5.Event_t[args.shot_line]['byid'][evt]
            else:
                event_t = None

            LOGGER.info("Extracting receivers for event {0:s}.".format(evt))
        except Exception as e:
            LOGGER.warn("Warning: The event {0} not found.\n".format(evt))
            continue

        fh = None
        # Initialize
        sf = segyfactory.Ssegy(None, event_t, utm=args.use_utm)
        # Allow lenght of traces to be up to 2^16 samples long
        sf.set_break_standard(args.break_standard)
        # Set external header type
        sf.set_ext_header_type(args.ext_header)
        # Set event information
        if event_t:
            sf.set_event_t(event_t)
            # Event time
            event_tdoy = timedoy.TimeDOY(microsecond=event_t
                                         ['time/micro_seconds_i'],
                                         epoch=event_t['time/epoch_l'])
            Offset_t = p5.read_offsets_shot_order(
                args.station_array, evt, args.shot_line)
        else:
            event_tdoy = evt
            Offset_t = None
            LOGGER.warn("Warning: No shot to receiver distances found.")
        if args.seconds_offset_from_shot:
            event_tdoy += args.seconds_offset_from_shot
        end_tdoy = event_tdoy + args.length
        # Event start time
        start_fepoch = event_tdoy.epoch(fepoch=True)
        # Trace cut end time
        stop_fepoch = end_tdoy.epoch(fepoch=True)
        Array_t = p5.Array_t[args.station_array]['byid']
        # All channels (components) available for this array
        chans_available = p5.channels_Array_t(args.station_array)
        # The trace sequence
        i = 0
        skipped_chans = 0
        for sta in args.stations_to_gather:
            LOGGER.info("-=" * 20)
            LOGGER.info(
                "Attempting to find data for station {0}.".format(sta))
            # Shot to station information
            if Offset_t and sta in Offset_t:
                offset_t = Offset_t[sta]
                sf.set_offset_t(offset_t)
            # Array geometry
            if sta not in Array_t:
                LOGGER.info("Warning: The station {0} is not in array {1}."
                            .format(sta, args.station_array))
                continue
            array_t = Array_t[sta]
            # Filter out unwanted channels
            chans = []
            for c in args.channels:
                if c in chans_available:
                    chans.append(c)
            # Create channel name for output file name
            chan_name = ''
            for c in chans:
                chan_name += "{0}".format(c)
            num_traces = len(chans) * len(args.stations_to_gather)
            # Loop through channels
            for c in chans:
                if c not in array_t:
                    LOGGER.warn("Warning: No channel information\
                    for {0} in array {1}.".format(c, args.station_array))
                    skipped_chans += 1
                    continue
                try:
                    # Filter out unwanted seed loc codes
                    if args.seed_location and\
                       array_t[c][0]['seed_location_code_s']\
                       != args.seed_location:
                        LOGGER.info("Location code mismatch: {0}/{1}/{2}"
                                    .format(array_t[c][0]
                                            ['seed_location_code_s'],
                                            args.seed_location,
                                            c))
                        continue
                    # Filter out unwanted seed channels
                    seed_channel_code_s = ph5api.seed_channel_code(
                        array_t[c][0])
                    if args.seed_channel and seed_channel_code_s \
                       != args.seed_channel:
                        LOGGER.info("Channel code mismatch: {0}/{1}/{2}"
                                    .format(array_t[c][0]
                                            ['seed_channel_code_s'],
                                            args.seed_channel,
                                            c))
                        continue
                except BaseException:
                    pass
                # Loop for each array_t per id_s and channel
                for t in range(len(array_t[c])):
                    # DAS
                    das = array_t[c][t]['das/serial_number_s']
                    # Deploy time
                    start_epoch = array_t[c][t]['deploy_time/epoch_l']
                    # Pickup time
                    stop_epoch = array_t[c][t]['pickup_time/epoch_l']
                    # Is this shot within the deploy and pickup times
                    if not ph5api.is_in(
                            start_epoch,
                            stop_epoch,
                            event_tdoy.epoch(),
                            end_tdoy.epoch()):
                        LOGGER.info("Data logger {0} not deployed\
                        between {1} to {2} at {3}.".format(
                            array_t[c][t]['das/serial_number_s'],
                            event_tdoy, end_tdoy, sta))
                        if args.deploy_pickup:
                            LOGGER.info("Skipping.")
                            continue
                    # Read Das table, may already be read so don't reread it
                    try:
                        das_or_fail = p5.read_das_t(
                            das,
                            start_epoch=start_fepoch,
                            stop_epoch=stop_fepoch,
                            reread=False)
                    except BaseException:
                        LOGGER.warn("Failed to read DAS:\
                        {0} between {1} and {2}.".format(
                            das,
                            timedoy.epoch2passcal(start_epoch),
                            timedoy.epoch2passcal(stop_epoch)))
                        continue

                    if das_or_fail is None:
                        LOGGER.warn("Failed to read DAS:\
                        {0} between {1} and {2}.".format(
                            das,
                            timedoy.epoch2passcal(start_epoch),
                            timedoy.epoch2passcal(stop_epoch)))
                        continue

                    # Sample rate
                    if array_t[c][t]['das/serial_number_s'] in p5.Das_t:
                        sr = float(p5.Das_t[array_t[c][t]
                                            ['das/serial_number_s']]['rows']
                                   [0]['sample_rate_i']) / float(
                            p5.Das_t[array_t[c][t]['das/serial_number_s']]
                            ['rows'][0]['sample_rate_multiplier_i'])
                    else:
                        sr = 0.  # Oops! No data for this DAS
                    # Check v4 sample rate from array_t
                    try:
                        if sr != array_t[c][0]['sample_rate_i'] / \
                                float(array_t[c][0]
                                      ['sample_rate_multiplier_i']):
                            continue
                    except BaseException:
                        pass
                    # Need to check against command line sample rate here
                    if args.sample_rate and args.sample_rate != sr:
                        LOGGER.warn(
                            "Warning: Sample rate for {0} is not {1}.\
                            Skipping.".format(das, sr))
                        continue
                    sf.set_length_points(
                        int((stop_fepoch - start_fepoch) * sr))

                    # Need to apply reduction velocity here
                    # Set cut start and stop times
                    cut_start_fepoch = start_fepoch
                    cut_stop_fepoch = stop_fepoch
                    if args.red_vel and args.red_vel > 0.:

                        try:
                            secs, errs = segyfactory.calc_red_vel_secs(
                                offset_t, args.red_vel)
                        except Exception as e:
                            secs = 0.
                            errs = ["Can not calculate "
                                    "reduction velocity: {0}."
                                    .format(e.message)]
                        for e in errs:
                            LOGGER.info(e)
                        cut_start_fepoch += secs
                        cut_stop_fepoch += secs

                    sf.set_cut_start_epoch(cut_start_fepoch)
                    sf.set_array_t(array_t[c][t])

                    # Cut trace
                    # Need to pad iff multiple traces
                    traces = p5.cut(das,
                                    cut_start_fepoch,
                                    cut_stop_fepoch,
                                    chan=c,
                                    sample_rate=sr,
                                    apply_time_correction=args.do_time_correct)
                    if len(traces[0].data) == 0:
                        LOGGER.warn(
                            "Warning: No data found for {0} for station {1}."
                            .format(das, sta))
                        continue
                    trace = ph5api.pad_traces(traces)
                    if args.do_time_correct:
                        LOGGER.info("Applied time drift correction by\
                        shifting trace by {0} samples.".format(
                            -1 * sr * (trace.time_correction_ms / 1000.)))
                        LOGGER.info("Correction is {0} ms.".format(
                            trace.time_correction_ms))
                        LOGGER.info(
                            "Clock drift (seconds/second): {0}"
                            .format(trace.clock.slope))
                        for tccomment in trace.clock.comment:
                            tccmt = tccomment.split('\n')
                            for tcc in tccmt:
                                LOGGER.info("Clock comment: {0}".format(tcc))
                    if trace.padding != 0:
                        LOGGER.warn(
                            "Warning: There were {0} samples of padding added\
                            to fill gap at middle or end of trace."
                            .format(trace.padding))
                    # Need to apply decimation here
                    if args.decimation:
                        # Decimate
                        shift, data = decimate.decimate(
                            DECIMATION_FACTORS[args.decimation], trace.data)
                        # Set new sample rate
                        wsr = int(sr / int(args.decimation))
                        sf.set_sample_rate(wsr)
                        trace.sample_rate = wsr
                        # Set length of trace in samples
                        sf.set_length_points(len(data))
                        sf.length_points_all = len(data)
                        trace.nsamples = len(data)
                        trace.data = data
                    # Did we read any data?
                    if trace.nsamples == 0:
                        # Failed to read any data
                        LOGGER.warning(
                            "Warning: No data for data logger {2}/{0}\
                            starting at {1}."
                            .format(das, trace.start_time, sta))
                        continue
                    # Read receiver and response tables
                    receiver_t = trace.receiver_t
                    if receiver_t:
                        sf.set_receiver_t(receiver_t)
                    else:
                        LOGGER.warning(
                            "No sensor orientation found in ph5 file.")
                    # Read gain and bit weight

                    if 'response_table_n_i' in array_t[c][t] and\
                       array_t[c][t]['response_table_n_i'] != -1:
                        response_t = p5.get_response_t_by_n_i(
                            int(array_t[c][t]['response_table_n_i']))
                    else:
                        response_t = trace.response_t

                    if response_t:
                        sf.set_response_t(response_t)
                    else:
                        LOGGER.warning(
                            "No gain or bit weight found in ph5 file.")
                    # Increment line sequence
                    i += 1
                    sf.set_line_sequence(i)
                    sf.set_das_t(trace.das_t[0])
                    LOGGER.info("=-" * 20)
                    LOGGER.info("trace: {0}".format(i))
                    LOGGER.info("Extracted: Station ID {0}".format(sta))
                    LOGGER.info("Chan: {2} Start: {0:s}, Stop: {1:s}."
                                .format(event_tdoy,
                                        end_tdoy,
                                        c))
                    LOGGER.info("Lat: %f Lon: %f Elev: %f %s"
                                % (array_t[c][t]['location/Y/value_d'],
                                   array_t[c][t]['location/X/value_d'],
                                   array_t[c][t]['location/Z/value_d'],
                                   array_t[c][t]['location/Z/units_s']
                                   .strip()))
                    LOGGER.info("{0}".format(array_t[c][t]['description_s']))
                    #
                    # Open SEG-Y file
                    #
                    if not fh:
                        if args.write_stdout:
                            try:
                                fh = sys.stdout
                            except Exception as e:
                                LOGGER.error("{0}".format(e.message))
                                LOGGER.error(
                                    "Failed to open STDOUT. Can not continue.")
                                sys.exit(-1)
                        else:
                            #
                            # Set up file naming
                            #
                            try:
                                nickname = \
                                    p5.Experiment_t['rows'][-1]['nickname_s']
                            except BaseException:
                                nickname = "X"
                            #
                            base = "{0}_{1}_{2}_{3}".format(
                                nickname,
                                args.station_array[-3:],
                                evt,
                                chan_name)
                            outfilename = "{1:s}/{0:s}_0001.SGY".format(
                                base, args.out_dir)
                            # Make sure that the name in unique
                            j = 1
                            while os.path.exists(outfilename):
                                j += 1
                                tmp = outfilename[:-8]
                                outfilename = "{0}{1:04d}.SGY".format(tmp, j)
                            # Open SEG-Y file
                            try:
                                fh = open(outfilename, 'w+')
                                LOGGER.info("Opened: {0}".format(outfilename))
                            except Exception as e:
                                LOGGER.error("Failed to open\
                                {0}.\t{1}".format(outfilename, e.message))
                                LOGGER.error("Failed to open {0}.\
                                \t{1}".format(
                                          outfilename, e.message))
                                sys.exit()
                        # Write reel headers and first trace
                        logs = segyfactory.write_segy_hdr(
                            trace, fh, sf, num_traces)
                        # Write any messages
                        for log in logs:
                            LOGGER.info(log)
                    else:
                        # Write trace
                        logs = segyfactory.write_segy(trace, fh, sf)
                        for log in logs:
                            LOGGER.info(log)
        # Traces found does not match traces expected
        if i != num_traces and fh:
            # Need to update reel_header
            if (num_traces - skipped_chans) < i:
                LOGGER.warn("Warning: Wrote {0} of {1}\
                trace/channels listed in {2}.".format(
                                                  i,
                                                  num_traces -
                                                  skipped_chans,
                                                  args.station_array))
            sf.set_text_header(i)
            fh.seek(0, os.SEEK_SET)
            sf.write_text_header(fh)
            sf.set_reel_header(i)
            fh.seek(3200, os.SEEK_SET)
            sf.write_reel_header(fh)
        try:
            fh.close()
        except AttributeError:
            pass


def main():
    args, p5 = get_args()
    # Write log to file
    ch = logging.FileHandler(os.path.join(args.out_dir, "ph5toevt.log"))
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.setLevel(logging.INFO)
    LOGGER.addHandler(ch)
    LOGGER.info("{0}: {1}".format(PROG_VERSION, sys.argv))
    if not args.start_time:
        if args.shot_line not in p5.Event_t_names:
            LOGGER.error("{0} not found. {1}\n".format(
                args.shot_line, " ".join(p5.Event_t_names)))
            sys.exit(-1)
        else:
            if not args.shot_file:
                p5.read_event_t(args.shot_line)
            else:
                p5.Event_t = args.shot_file
    p5.read_array_t_names()
    if args.station_array not in p5.Array_t_names:
        LOGGER.error("{0} not found.  {1}\n".format(
            args.station_array, " ".join(p5.Array_t_names)))
        sys.exit(-1)
    else:
        p5.read_array_t(args.station_array)

    p5.read_receiver_t()
    p5.read_response_t()
    p5.read_experiment_t()
    if p5.Experiment_t is not None and p5.Experiment_t['rows'] != []:
        experiment_t = p5.Experiment_t['rows'][-1]
        LOGGER.info("Experiment: {0}".format(
            experiment_t['longname_s'].strip()))
        LOGGER.info("Summary: {0}".format(
            experiment_t['summary_paragraph_s'].strip()))
        if args.seed_network and p5.Experiment_t['net_code_s'] !=\
           args.seed_network:
            LOGGER.info(
                "Netcode mis-match: {0}/{1}".format(
                    p5.Experiment_t['net_code_s'],
                    args.seed_network))
            sys.exit(-1)
    else:
        LOGGER.warning(
            "Warning: No experiment information found. Contact PIC.")
    gather(args, p5)
    LOGGER.info("Done.")
    logging.shutdown()
    p5.close()


if __name__ == '__main__':
    main()
