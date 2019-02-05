#!/usr/bin/env pnpython3
#
# Program to generate /Experiment_g/Sorts_g/Sort_t entries
#
# Steve Azevedo, July 2007
#

import argparse
import sys
import logging
import os
import os.path
import time
import math
from ph5 import LOGGING_FORMAT
# This provides the base functionality
from ph5.core import experiment

PROG_VERSION = '2019.036'
LOGGER = logging.getLogger(__name__)

# Make sure we are all on the same time zone ;^)
os.environ['TZ'] = 'UTM'
time.tzset()


#
# To hold table rows and keys
#


class Rows_Keys(object):
    __slots__ = ('rows', 'keys')

    def __init__(self, rows=None, keys=None):
        self.rows = rows
        self.keys = keys

    def set(self, rows=None, keys=None):
        if rows is not None:
            self.rows = rows
        if keys is not None:
            self.keys = keys


#
# To hold DAS sn and references to Das_g_[sn]
#


class Das_Groups(object):
    __slots__ = ('das', 'node')

    def __init__(self, das=None, node=None):
        self.das = das
        self.node = node


#
# Read Command line arguments
#


def get_args():
    global PH5, PATH, DEBUG, SN, AUTO, OFILE

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)
    parser.usage = ("sort_kef_gen --nickname ph5-file-prefix --serial-number "
                    "DAS-SN | --auto [--path path-to-ph5-files]")

    parser.description = ("Version: {0} Generate a kef file to "
                          "populate Sort_t.".format(PROG_VERSION))

    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)

    parser.add_argument("-p", "--path", dest="ph5_path",
                        help="Path to ph5 files. Defaults to current "
                             "directory.",
                        metavar="ph5_path", default=".")

    parser.add_argument("-s", "--serial-number", dest="sn",
                        help="DAS to use to get windows.",
                        metavar="sn")

    parser.add_argument("-a", "--auto", dest="auto",
                        help=("Attempt to auto detect windows. Windows should "
                              "start at the same time on all DASs."),
                        action="store_true", default=False)

    parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                        default=False)

    parser.add_argument("-o", "--outfile", dest="output_file",
                        help="The kef output file to be saved at.",
                        metavar="output_file", default=None)

    args = parser.parse_args()

    PH5 = args.ph5_file_prefix
    PATH = args.ph5_path
    SN = args.sn
    AUTO = args.auto
    DEBUG = args.debug

    # define OFILE to write output
    o_filename = args.output_file
    if o_filename is None:
        OFILE = None
    else:
        OFILE = open(o_filename, 'w')

    if DEBUG:
        # change stream handler to write debug level logs
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        # Add formatter
        formatter = logging.Formatter(LOGGING_FORMAT)
        ch.setFormatter(formatter)
        LOGGER.addHandler(ch)

    if SN is None and AUTO is False:
        LOGGER.error("Serial number can not be undefined if auto is "
                     "set to false.")
        sys.exit(-1)


#
# Initialize ph5 file
#


def initialize_ph5(editmode=False):
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5

    EX = experiment.ExperimentGroup(PATH, PH5)
    EX.ph5open(editmode)
    EX.initgroup()


# XXX   Not used


def read_sort_table():
    '''   Read /Experiment_t/Sorts_g/Sort_g   '''
    global EX, SORT_T

    sorts, sorts_keys = EX.ph5_g_sorts.read_sorts()

    if sorts is None:
        return False

    rowskeys = Rows_Keys(sorts, sorts_keys)

    SORT_T = rowskeys

    return True


def get_sample_count(g, a):
    global EX

    EX.ph5_g_receivers.setcurrent(g)

    try:
        node = EX.ph5_g_receivers.find_trace_ref(a)
    except Exception as e:
        LOGGER.warning(
            "Couldn't count samples in data array. {0}".format(e))
        return None

    return node.nrows


def read_das_table(das):
    global EX, DAS_T

    das_group = EX.ph5_g_receivers.getdas_g(das)

    if das_group is None:
        return False

    EX.ph5_g_receivers.setcurrent(das_group)

    r, k = EX.ph5_g_receivers.read_das()

    if r is None:
        return False

    R = []
    # Get sample count for this array
    for r0 in r:
        r0['array_name_data_a']
        r0['samples'] = r0['sample_count_i']
        R.append(r0)

    k.append('samples')
    DAS_T = Rows_Keys(R, k)

    return True


def read_all_das():
    '''   Read all das tables and create a DAS_T that contains all
          of the windows.
    '''
    global EX, DAS_T

    rows = {}
    # Get all of the das groups
    dasGroups = EX.ph5_g_receivers.alldas_g()
    # For each das
    dass = dasGroups.keys()
    if not dass:
        return False

    for das in dass:
        # Set the current group
        das_group = dasGroups[das]
        EX.ph5_g_receivers.setcurrent(das_group)
        # Read the das table for this das
        r, k = EX.ph5_g_receivers.read_das()

        if r is None or k is None:
            continue

        R = []
        # Get sample count for this array by counting the array
        for r0 in r:
            if r0['channel_number_i'] != 1:
                continue  # Exclude all but channel 1
            samples = r0['sample_count_i']
            r0['time/epoch_f'] =\
                float(r0['time/epoch_l']) +\
                (float(r0['time/micro_seconds_i']) / 1000000.)
            r0['samples'] = samples
            r0['das'] = das
            R.append(r0)

        k.append('samples')

        # Create a dictionary of rows keyed by start epoch
        # This should contain all of the recording windows
        for r in R:
            rows[r['time/epoch_l']] = r

    # Sort by start time epoch
    epochs = sorted(rows.keys())
    # Get the rows list back
    row = []
    for e in epochs:
        row.append(rows[e])

    # Set DAS_T
    DAS_T = Rows_Keys(row, k)

    return True


# XXX   Not used


def get_arrays():
    global SORT_T

    KV = {}

    for s in SORT_T.rows:
        KV[s['array_name_s']] = s['array_t_name_s']

    return KV


def first_last(array_t):
    mmax = 0
    mmin = sys.maxsize
    for a in array_t:
        array_pickup = a['pickup_time/epoch_l']
        array_deploy = a['deploy_time/epoch_l']
        if array_deploy < mmin:
            mmin = array_deploy
        if array_pickup > mmax:
            mmax = array_pickup

    if mmax == 0:
        mmax = sys.maxsize
    return mmin, mmax


def print_report(text):
    global OFILE
    if OFILE is None:
        print(text)
    else:
        OFILE.write(text + '\n')


def report_gen():
    global DAS_T, EX

    PH5_VERSION = EX.version()

    ar = EX.ph5_g_sorts.names()

    if ar == []:
        LOGGER.error(
            "No sort arrays (Array_t_xxx) defined!\
             Can not produce sort table.\n")
        return

    now = time.time()
    print_report("#   sort-kef-gen Version: %s ph5 Version: %s" %
                 (PROG_VERSION, PH5_VERSION))
    r = 1
    # XXX   This assumes that the arrays were deployed for the same recording
    # windows.   XXX
    for a in ar:
        array_t, k = EX.ph5_g_sorts.read_arrays(a)
        array_deploy, array_pickup = first_last(array_t)
        if len(DAS_T.rows) < 1:
            LOGGER.warning("Failed to read any DAS information!\n")

        for d in DAS_T.rows:
            # Skip everything but channel 1
            if d['channel_number_i'] != 1:
                continue
            t0 = d['time/epoch_l'] + (d['time/micro_seconds_i'] / 1000000)
            ll = d['samples'] / d['sample_rate_i']
            t1 = t0 + ll
            (float_part, int_part) = math.modf(t1)
            if array_deploy <= d['time/epoch_l'] and array_pickup >= int_part:
                #
                print_report("#   row {0} das {1}\n/Experiment_g/Sorts_g/"
                             "Sort_t".format(r, d['das']))
                print_report("\tarray_name_s = %s" % a[-3:])
                print_report("\tarray_t_name_s = %s" % a)
                print_report("\tdescription_s = Recording window %04d" %
                             d['event_number_i'])
                print_report("\tstart_time/epoch_l = %d" % d['time/epoch_l'])
                print_report("\tstart_time/micro_seconds_i = %d" %
                             d['time/micro_seconds_i'])
                print_report("\tstart_time/type_s = %s" % d['time/type_s'])
                print_report("\tstart_time/ascii_s = %s" % d['time/ascii_s'])
                print_report("\tend_time/epoch_l = %d" % int_part)
                print_report("\tend_time/micro_seconds_i = %d" %
                             (float_part * 1000000.0))
                print_report("\tend_time/ascii_s = %s" % time.ctime(t1))
                print_report("\tend_time/type_s = BOTH")
                print_report("\ttime_stamp/epoch_l = %d" % now)
                print_report("\ttime_stamp/ascii_s = %s" % time.ctime(now))
                print_report("\ttime_stamp/micro_seconds_i = 0")
                print_report("\ttime_stamp/type_s = BOTH")
                r += 1


def main():
    global SN, EX, AUTO, OFILE

    get_args()
    initialize_ph5()

    if SN is not None:
        if not read_das_table(SN):
            LOGGER.error("Failed to read Das_t for {0}.".format(SN))
            sys.exit()
    elif AUTO is True:
        if not read_all_das():
            LOGGER.error("Failed to read DAS tables.")
            sys.exit()

    report_gen()
    EX.ph5close()
    if OFILE is not None:
        OFILE.close()


if __name__ == "__main__":
    main()
