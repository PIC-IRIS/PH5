#!/usr/bin/env pnpython4
#
# Produce SEG-Y in receiver order from a PH5 file using API
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
    '''
       Program arguments
    '''

    parser = argparse.ArgumentParser()

    parser.usage = "Version: {0}: ph5torec -n nickname -p path_to_ph5_files\
    --stations=stations_list --shot_line --length [options]".format(
                                                                PROG_VERSION)
    parser.description = "Generate SEG-Y gathers in receiver order..."
    # Usually master.ph5
    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)
    # Path to the directory that holds master.ph5
    parser.add_argument("-p", "--path", dest="ph5_path",
                        help="Path to ph5 files.\
                        Defaults to current directory.",
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
    # Stations to gather, comma seperated
    parser.add_argument("-S", "--stations", "--station_list",
                        dest="stations_to_gather",
                        help="Comma separated list of stations\
                        to receiver gather.",
                        metavar="stations_to_gather", required=True)
    # Event id's in order, comma seperated
    parser.add_argument("--event_list", dest="evt_list",
                        help="Comma separated list of event id's to gather\
                        from defined or selected events.",
                        metavar="evt_list")
    # Length of traces to put in gather
    parser.add_argument("-l", "--length", action="store", required=True,
                        type=int, dest="length", metavar="length")
    # Start trace at time offset from shot time
    parser.add_argument("-O", "--seconds_offset_from_shot", "--offset",
                        metavar="seconds_offset_from_shot",
                        help="Time in seconds from shot time to\
                        start the trace.",
                        type=float, default=0.)
    # The array number
    parser.add_argument("-A", "--station_array", dest="station_array",
                        action="store",
                        help="The array number that holds the station(s).",
                        type=int, metavar="station_array", required=True)
    # The shot line number, 0 for Event_t
    parser.add_argument("--shot_line", dest="shot_line", action="store",
                        help="The shot line number that holds the shots.",
                        type=int, metavar="shot_line", required=True)
    # External shot line file
    parser.add_argument("--shot_file", dest="shot_file", action="store",
                        help="Input an external kef file that contains event\
                        information, Event_t.kef.",
                        type=str, metavar="shot_file")
    # Output directory
    parser.add_argument("-o", "--out_dir", action="store", dest="out_dir",
                        metavar="out_dir", type=str, default=".")
    # Write to stdout
    parser.add_argument("--stream", action="store_true", dest="write_stdout",
                        help="Write to stdout instead of a file.",
                        default=False)
    # Shot range to extract
    parser.add_argument("-r", "--shot_range", action="store",
                        dest="shot_range",
                        help="example: --shot_range=1001-11001",
                        metavar="shot_range")
    # Apply a reduction velocity, km
    parser.add_argument("-V", "--reduction_velocity", action="store",
                        dest="red_vel",
                        metavar="red_vel", type=float, default="-1.")
    # Decimate data. Decimation factor
    parser.add_argument("-d", "--decimation", action="store",
                        choices=["2", "4", "5", "8", "10", "20"],
                        dest="decimation",
                        metavar="decimation")
    # Sort traces in gather by offset
    parser.add_argument("--sort_by_offset", action="store_true",
                        dest="sort_by_offset",
                        default=False)
    # Use deploy and pickup times to determine where an instrument was
    # deployed
    parser.add_argument("--use_deploy_pickup", action="store_true",
                        default=True,
                        help="Use deploy and pickup times to determine if\
                        data exists for a station.",
                        dest="deploy_pickup")
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
                         'U' -> Menlo USGS, default = U",
                        choices=["P", "S", "U"], default="U",
                        metavar="extended_header_style")
    # Ignore channel in Das_t. Only useful with texans
    parser.add_argument("--ic", action="store_true",
                        dest="ignore_channel", default=False)
    # Allow traces to be 2^16 samples long vs 2^15
    parser.add_argument("--break_standard", action="store_false",
                        dest="break_standard",
                        help="Force traces to be no longer than 2^15 samples.",
                        default=True)
    # Do not time correct texan data
    parser.add_argument("-N", "--notimecorrect", action="store_false",
                        default=True,
                        dest="do_time_correct")
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
            LOGGER.error("Shot line required when using external shot file.")
            sys.exit(-2)
        external = external_file.External(args.shot_file)
        args.shot_file = external.Event_t
        p5.Event_t_names = args.shot_file.keys()
    else:
        p5.read_event_t_names()

    if args.shot_line == 0:
        args.shot_line = "Event_t"
    else:
        args.shot_line = "Event_t_{0:03d}".format(args.shot_line)

    args.station_array = "Array_t_{0:03d}".format(args.station_array)
    args.stations_to_gather = args.stations_to_gather.split(',')
    if args.evt_list:
        args.evt_list = args.evt_list.split(',')
    elif args.shot_range:
        a, b = map(int, args.shot_range.split('-'))
        args.evt_list = map(str, range(a, b + 1, 1))
    args.channels = map(int, args.channels.split(','))

    if not os.path.exists(args.out_dir):
        os.mkdir(args.out_dir)
        os.chmod(args.out_dir, 0o777)
    return args, p5


def create_channel_map():
    pass


def gather(args, p5):
    '''   Create receiver gather   '''
    for sta in args.stations_to_gather:
        try:
            # Read the appropriate line from Array_t
            if args.station_array in p5.Array_t:
                array_t = p5.Array_t[args.station_array]['byid'][sta]
            else:
                p5.read_array_t(args.station_array)
                array_t = p5.Array_t[args.station_array]['byid'][sta]
            LOGGER.info(
                "Extracting receiver(s) at station {0:s}.".format(sta))
            LOGGER.info("Found the following components:")
            for c in array_t.keys():
                LOGGER.info("DAS: {0} component: {1}".format(
                    array_t[c][0]['das/serial_number_s'], c))
                LOGGER.info("Lat: {0} Lon: {1} Elev: {2}"
                            .format(array_t[c][0]['location/Y/value_d'],
                                    array_t[c][0]['location/X/value_d'],
                                    array_t[c][0]['location/Z/value_d']))
                LOGGER.info("{0}".format(array_t[c][0]['description_s']))
            # Read the appropriate line from Das_t and get the sample rate
            p5.read_das_t(array_t[c][0]['das/serial_number_s'],
                          array_t[c][0]['deploy_time/epoch_l'],
                          array_t[c][0]['pickup_time/epoch_l'])
            sr = float(p5.Das_t[array_t[c][0]['das/serial_number_s']]
                       ['rows'][0]['sample_rate_i']) / float(
                           p5.Das_t[array_t[c][0]['das/serial_number_s']]
                           ['rows'][0]['sample_rate_multiplier_i'])
        except KeyError as e:
            LOGGER.warn(
                "Warning: The station {0} not found in the current array.\n"
                .format(sta))
            continue

        i = 0  # Number of traces found
        fh = None  # SEG-Y file
        # Get a mostly empty instance of segyfactory
        sf = segyfactory.Ssegy(None, None, utm=args.use_utm)
        # Set the type of extended header to write
        sf.set_ext_header_type(args.ext_header)
        # Should we allow traces that are 2^16 samples long
        sf.set_break_standard(args.break_standard)
        # Filter out un-wanted channels here
        chans_available = array_t.keys()
        chans = []
        # Put the desired channels in the desired order
        for c in args.channels:
            if c in chans_available:
                chans.append(c)
        # Channel name for output file name
        chan_name = ''
        for c in chans:
            chan_name += "{0}".format(c)

        # Read Event_t_xxx
        Event_t = p5.Event_t[args.shot_line]['byid']
        order = p5.Event_t[args.shot_line]['order']

        # Take a guess at the number of traces in this SEG-Y file based on
        # number of shots
        num_traces = len(order) * len(chans)
        # Try to read offset distances (keyed on shot id's)
        Offset_t = p5.read_offsets_receiver_order(
            args.station_array, sta, args.shot_line)
        # Loop through each shot by shot id
        for o in order:
            # Check event list (and also shot_range), args.evt_list, here!
            if args.evt_list:
                if o not in args.evt_list:
                    continue

            # Appropriate line from Event_t
            event_t = Event_t[o]
            # Need to handle time offset here, args.seconds_offset_from_shot
            event_tdoy = timedoy.TimeDOY(microsecond=event_t[
                'time/micro_seconds_i'],
                                         epoch=event_t['time/epoch_l'])
            # Adjust start time based on offset entered on command line
            if args.seconds_offset_from_shot:
                event_tdoy += args.seconds_offset_from_shot
            end_tdoy = event_tdoy + args.length

            start_fepoch = event_tdoy.epoch(fepoch=True)
            stop_fepoch = end_tdoy.epoch(fepoch=True)
            # Set start time in segyfactory
            sf.set_cut_start_epoch(start_fepoch)
            # Set event
            sf.set_event_t(event_t)
            # Set shot to receiver distance
            sf.set_offset_t(Offset_t[o])
            # Set number of samples in trace, gets reset if decimated
            sf.set_length_points(int((stop_fepoch - start_fepoch) * sr))
            # Loop through each channel (channel_number_i)
            for c in chans:
                if c not in array_t:
                    continue
                # Filter out unwanted seed loc codes
                if args.seed_location and\
                   array_t[c][0]['seed_location_code_s'] != args.seed_location:
                    LOGGER.info("Location code mismatch: {0}/{1}/{2}"
                                .format(array_t[c][0]['seed_location_code_s'],
                                        args.seed_location,
                                        c))
                    continue
                # Filter out unwanted seed channels
                seed_channel_code_s = ph5api.seed_channel_code(array_t[c][0])
                if args.seed_channel and\
                   seed_channel_code_s != args.seed_channel:
                    LOGGER.info("Channel code mismatch: {0}/{1}/{2}"
                                .format(array_t[c][0]['seed_channel_code_s'],
                                        args.seed_channel,
                                        c))
                    continue
                # DAS
                das = array_t[c][0]['das/serial_number_s']
                for t in range(len(array_t[c])):
                    # Deploy time
                    start_epoch = array_t[c][t]['deploy_time/epoch_l']
                    # Pickup time
                    stop_epoch = array_t[c][t]['pickup_time/epoch_l']
                    # Is this shot within the deploy and pickup times
                    if not ph5api.is_in(
                            start_epoch, stop_epoch,
                            event_tdoy.epoch(),
                            end_tdoy.epoch()):
                        LOGGER.info("Data logger {0} not deployed between\
                        {1} to {2} at {3}.".format(
                                               array_t[c][t][
                                                   'das/serial_number_s'],
                                               event_tdoy, end_tdoy,
                                               sta))
                        if args.deploy_pickup:
                            LOGGER.info("Skipping.")
                            continue

                    # Need to apply reduction velocity here
                    if args.red_vel > 0.:
                        try:
                            secs, errs = segyfactory.calc_red_vel_secs(
                                Offset_t[o], args.red_vel)
                        except Exception as e:

                            secs = 0.
                            errs = ["Can not calculate "
                                    "reduction velocity: {0}."
                                    .format(e.message)]
                        for e in errs:
                            LOGGER.info(e)
                        start_fepoch += secs
                        stop_fepoch += secs
                    # Set array_t in segyfactory
                    sf.set_array_t(array_t[c][t])
                    # Read Das table
                    p5.forget_das_t(das)
                    #
                    # Cut trace
                    #
                    traces = p5.cut(das, start_fepoch,
                                    stop_fepoch, chan=c, sample_rate=sr)
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
                    if trace.nsamples == 0:
                        LOGGER.info("No data found for DAS "
                                    "{0} between {1} and {2}."
                                    .format(das,
                                            event_tdoy.getPasscalTime(),
                                            end_tdoy.getPasscalTime()))
                        continue
                    if trace.padding != 0:
                        LOGGER.warn(
                            "Warning: There were {0} samples of padding\
                            added to fill gap(s) in original traces."
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
                        trace.nsamples = len(data)

                    if trace.nsamples == 0:
                        # Failed to read any data
                        LOGGER.warning("Warning: No data for data\
                        logger {0} starting at {1}.".format(
                            das, trace.start_time))
                        continue
                    # Read receiver and response tables
                    receiver_t = trace.receiver_t
                    if 'response_table_n_i' in array_t[c][t] and\
                       array_t[c][t]['response_table_n_i'] != -1:
                        response_t = p5.get_response_t_by_n_i(
                            int(array_t[c][t]['response_table_n_i']))
                    else:
                        response_t = p5.Response_t['rows']
                        [trace.das_t[0]['response_table_n_i']]
                    # Set sort_t in segyfactory
                    sf.set_sort_t(p5.get_sort_t(
                        start_fepoch, args.station_array))
                    # Set das_t
                    sf.set_das_t(trace.das_t[0])
                    # Line sequence (trace number)
                    sf.set_line_sequence(i)
                    i += 1
                    if response_t:
                        sf.set_response_t(response_t)
                    else:
                        LOGGER.warning(
                            "No gain or bit weight found in ph5 file.")
                    if receiver_t:
                        sf.set_receiver_t(receiver_t)
                    else:
                        LOGGER.warning(
                            "No sensor orientation found in ph5 file.")
                    # Some informational logging
                    LOGGER.info("trace: {0}".format(i))
                    LOGGER.info("-=" * 20)
                    LOGGER.info("Extracting: Event ID %s" % event_t['id_s'])
                    LOGGER.info("Chan: {2} Start: {0:s}, Stop: {1:s}."
                                .format(event_tdoy,
                                        end_tdoy,
                                        c))
                    LOGGER.info("Lat: %f Lon: %f Elev:\
                    %f %s" % (event_t['location/Y/value_d'],
                              event_t['location/X/value_d'],
                              event_t['location/Z/value_d'],
                              event_t['location/Z/units_s'].strip()))
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
                            # Set up file nameing
                            #
                            try:
                                nickname = p5.Experiment_t['rows']
                                [-1]['nickname_s']
                            except BaseException:
                                nickname = "X"
                            #
                            base = "{0}_{1}_{2}_{3}".format(
                                nickname, args.station_array[-3:],
                                sta,
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
                                LOGGER.error("Failed to open {0}.\t{1}"
                                             .format(outfilename, e.message))
                                sys.exit()
                        # Write reel headers and first trace
                        try:
                            logs = segyfactory.write_segy_hdr(
                                trace, fh, sf, num_traces)
                            # Write any messages
                            for log in logs:
                                LOGGER.info(log)
                        except segyfactory.SEGYError as e:
                            LOGGER.error("Header write failure.")
                            sys.exit()
                    else:
                        # Write trace
                        try:
                            logs = segyfactory.write_segy(trace, fh, sf)
                            for log in logs:
                                LOGGER.info(log)
                            LOGGER.info('=-' * 40)
                        except segyfactory.SEGYError as e:
                            LOGGER.error("Trace write failure.")
                            sys.exit()
        # Traces found does not match traces expected
        if fh and i != num_traces:
            # Need to update reel_header
            LOGGER.warn("Wrote {0} of {1} traces listed in {2}.".format(
                i, num_traces, args.station_array))
            sf.set_text_header(i)
            fh.seek(0, os.SEEK_SET)
            sf.write_text_header(fh)
            sf.set_reel_header(i)
            fh.seek(3200, os.SEEK_SET)
            sf.write_reel_header(fh)

        if fh:
            fh.close()


def main():
    args, p5 = get_args()
    # Write log to file
    ch = logging.FileHandler(os.path.join(args.out_dir, "ph5torec.log"))
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.setLevel(logging.INFO)
    LOGGER.addHandler(ch)
    LOGGER.info("{0}: {1}".format(PROG_VERSION, sys.argv))
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
    p5.read_sort_t()
    if p5.Experiment_t:
        experiment_t = p5.Experiment_t['rows'][-1]
        LOGGER.info("Experiment: {0}".format(
            experiment_t['longname_s'].strip()))
        LOGGER.info("Summary: {0}".format(
            experiment_t['summary_paragraph_s'].strip()))
        if args.seed_network and\
           p5.Experiment_t['net_code_s'] != args.seed_network:
            LOGGER.info(
                "Netcode mis-match: {0}/{1}"
                .format(p5.Experiment_t['net_code_s'], args.seed_network))
            sys.exit(-1)
    else:
        LOGGER.warning("No experiment information found. Contact PIC.")

    gather(args, p5)
    LOGGER.info("Done.")
    logging.shutdown()
    p5.close()


if __name__ == '__main__':
    main()
