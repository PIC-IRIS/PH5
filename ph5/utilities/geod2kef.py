#!/usr/bin/env pnpython4
#
# Program to generate offset tables from Array_t_nnn and Event_t_nnn.
#
# Steve Azevedo, July 2017
#
import argparse
import sys
import logging
import numpy as npy
from ph5.core import ph5api
from ph5.core.columns import PH5VERSION as ph5version

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)


#
# Read Command line arguments
#


def get_args():
    global ARGS

    parser = argparse.ArgumentParser()

    parser.usage = "Version: {0}, geod2kef --nickname ph5-file-prefix\
     [-p path]".format(
        PROG_VERSION)

    parser.description = ("Read locations and calculate offsets from "
                          "events to receivers. Produce kef file to "
                          "populate ph5 file.")
    # -n master.ph5
    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)
    # -p /path/to/ph5/family/files
    parser.add_argument("-p", "--path", dest="ph5_path",
                        help=("Path to ph5 files. Defaults to current "
                              "directory."),
                        metavar="ph5_path", default='.')

    ARGS = parser.parse_args()


def print_kef(array_num, event_num, Offset_t):
    '''   Write out kef file to stdout
    '''
    global N
    table_path = "/Experiment_g/Sorts_g/Offset_t_{0:03d}_{1:03d}".format(
        array_num, event_num)
    offsets = [[], [], []]
    order = sorted(Offset_t['order'])
    keys = Offset_t['keys']
    for o in order:
        N += 1
        print "# {0}".format(N)
        print table_path
        offset_t = Offset_t['byid'][o]
        offsets[0].append(offset_t['receiver_id_s'])
        offsets[1].append(offset_t['event_id_s'])
        offsets[2].append(offset_t['offset/value_d'])
        for key in keys:
            print "\t{0}={1}".format(key, offset_t[key])

    return offsets


def write_log(array, shot_line, shot, offsets):
    '''   Write log file with offset statistics
    '''
    # Calculate mean of offsets
    ave = npy.mean(offsets[2])
    # Calculate standard deviation
    sd = npy.std(offsets[2])
    # Calculate max and min offset
    max_offset = npy.max(offsets[2])
    min_offset = npy.min(offsets[2])
    # Calculate offsets below and 1st percentile and above 99th percentile
    per = npy.percentile(offsets[2], [1, 99])
    print >> LOG, "{0} {1} Event: {2} Mean offset: {3:12.1f} Std: {4:12.1f}\
     Maximum: {5:12.1f} Minimum: {6:12.1f}".format(
        array,
        shot_line,
        shot,
        ave,
        sd,
        max_offset,
        min_offset)
    print >> LOG, "\n-> Stations that are below the 1st percentile or above\
     the 99th percentile:"
    for i in xrange(len(offsets[2])):
        if offsets[2][i] >= per[1]:
            print >> LOG, "\tStation: {0} Event: {1} Offset: {2:12.1f}".format(
                offsets[0][i], shot, offsets[2][i])
        if offsets[2][i] == per[0]:
            print >> LOG, "\tStation: {0} Event: {1} Offset: {2:12.1f}".format(
                offsets[0][i], shot, offsets[2][i])
    print >> LOG, "-=" * 40


def main():
    global P5, N, LOG

    N = 0

    get_args()
    try:
        P5 = ph5api.PH5(path=ARGS.ph5_path, nickname=ARGS.ph5_file_prefix)
    except Exception:
        LOGGER.error("Can't open {0} at {1}.".format(ARGS.ph5_file_prefix,
                                                     ARGS.ph5_path))
        sys.exit(-1)

    P5.read_array_t_names()
    P5.read_event_t_names()
    if not P5.Array_t_names or not P5.Event_t_names:
        LOGGER.error("No arrays or no events defined in ph5 file."
                     "Can not continue!")
        P5.close()
        sys.exit()
    print "# geod2kef v{0}, PH5 v{1}".format(PROG_VERSION, ph5version)
    with open("geod2kef.log", 'w+') as LOG:
        print >> LOG, sys.argv
        print >> LOG, "***\nOffset statistics:"
        for Array_t_name in P5.Array_t_names:
            array_num = int(Array_t_name[8:])
            P5.read_array_t(Array_t_name)
            for Event_t_name in P5.Event_t_names:
                event_num = int(Event_t_name[8:])
                P5.read_event_t(Event_t_name)
                order = P5.Event_t[Event_t_name]['order']
                for shot_id in order:
                    Offset_t = P5.calc_offsets(
                        Array_t_name, shot_id, shot_line=Event_t_name)
                    offsets = print_kef(array_num, event_num, Offset_t)
                    write_log(Array_t_name, Event_t_name, event_num, offsets)
    P5.close()


if __name__ == '__main__':
    main()
