#!/usr/bin/env pnpython4

#
# Dump tables in ph5 file to kef format.
#
# Steve Azevedo, April 2007
#


import argparse
import string
import logging
import time
import re
# This provides the base functionality
from ph5.core import experiment

# Timeseries are stored as numpy arrays

PROG_VERSION = '2019.051'
LOGGER = logging.getLogger(__name__)


#
# These are to hold different parts of the meta-data
#


def init_local():
    # /Experiment_g/Experiment_t
    EXPERIMENT_T = None
    # /Experiment_g/Sorts_g/Event_t
    EVENT_T = {}
    # /Experiment_g/Sorts_g/Offset_t
    OFFSET_T = {}
    # /Experiment_g/Sorts_g/Sort_t
    SORT_T = None
    # /Experiment_g/Responses_g/Response_t
    RESPONSE_T = None
    # /Experiment_g/Reports_g/Report_t
    REPORT_T = None
    # /Experiment_g/Sorts_g/Array_t_[nnn]
    ARRAY_T = {}
    # /Experiment_g/Receivers_g/Das_g_[sn]/Das_t (keyed on DAS)
    DAS_T = {}
    # /Experiment_g/Receivers_g/Receiver_t
    RECEIVER_T = None
    # /Experiment_g/Receivers_g/Das_g_[sn]/SOH_a_[n] (keyed on DAS then by
    # SOH_a_[n] name)
    SOH_A = {}
    # /Experiment_g/Receivers_g/Index_t
    INDEX_T = None
    # /Experiment_g/Maps_g/Index_t
    M_INDEX_T = None
    # A list of Das_Groups that refers to Das_g_[sn]'s
    DASS = []
    # /Experiment_g/Receivers_g/Time_t
    TIME_T = None
    #
    TABLE_KEY = None

    return EXPERIMENT_T, EVENT_T, OFFSET_T, SORT_T, RESPONSE_T, REPORT_T, \
        ARRAY_T, DAS_T, RECEIVER_T, SOH_A, INDEX_T, M_INDEX_T, DASS, TIME_T, \
        TABLE_KEY


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
    print("get_args")
    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = "Version: {0}\ntabletokef\
     --nickname ph5-file-prefix options".format(
        PROG_VERSION)

    parser.description = "Dump a table to a kef file."

    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)

    parser.add_argument("-p", "--path", dest="ph5_path",
                        help=("Path to ph5 files. Default to current "
                              "directory."), default=".",
                        metavar="ph5_path")

    parser.add_argument("-u", "--update_key", dest="update_key",
                        help="Set generated kef file to do an Update on key.",
                        metavar="update_key", type=str)

    parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                        default=False)

    parser.add_argument("-E", "--Experiment_t", dest="experiment_t",
                        action="store_true",
                        default=False,
                        help="Dump /Experiment_g/Experiment_t to a kef file.")

    parser.add_argument("-S", "--Sort_t", dest="sort_t", action="store_true",
                        default=False,
                        help=("Dump /Experiment_g/Sorts_g/Sort_t to a kef "
                              "file."))

    parser.add_argument("-O", "--Offset_t", dest="offset_t_", metavar="a_e",
                        help=("Dump "
                              "/Experiment_g/Sort_g/Offset_t_[arrayID_eventID]"
                              " to a kef file."))

    parser.add_argument("-V", "--Event_t_", dest="event_t_", metavar="n",
                        type=int,
                        help=("Dump /Experiment_g/Sorts_g/Event_t_[n]"
                              "to a kef file."))

    parser.add_argument("--all_events", dest='all_events', action='store_true',
                        default=False,
                        help=("Dump all /Experiment_g/Sorts_g/Event_t_xxx "
                              "to a kef file."))

    parser.add_argument("-A", "--Array_t_", dest="array_t_", metavar="n",
                        type=int,
                        help=("Dump /Experiment_g/Sorts_g/Array_t_[n] "
                              "to a kef file."))

    parser.add_argument("--all_arrays", dest='all_arrays', action='store_true',
                        default=False,
                        help=("Dump all /Experiment_g/Sorts_g/Array_t_xxx "
                              "to a kef file."))

    parser.add_argument("-R", "--Response_t", dest="response_t",
                        action="store_true",
                        default=False,
                        help=("Dump /Experiment_g/Responses_g/Response_t "
                              "to a kef file."))

    parser.add_argument("-P", "--Report_t", dest="report_t",
                        action="store_true",
                        default=False,
                        help=("Dump /Experiment_g/Reports_g/Report_t "
                              "to a kef file."))

    parser.add_argument("-C", "--Receiver_t", dest="receiver_t",
                        action="store_true",
                        default=False,
                        help=("Dump /Experiment_g/Receivers_g/Receiver_t "
                              "to a kef file."))

    parser.add_argument("-I", "--Index_t", dest="index_t", action="store_true",
                        default=False,
                        help=("Dump /Experiment_g/Receivers_g/Index_t "
                              "to a kef file."))

    parser.add_argument("-M", "--M_Index_t", dest="m_index_t",
                        action="store_true",
                        default=False,
                        help=("Dump /Experiment_g/Maps_g/Index_t to a "
                              "kef file."))

    parser.add_argument("-D", "--Das_t", dest="das_t_", metavar="das",
                        help=("Dump /Experiment_g/Receivers_g/Das_g_[das]/"
                              "Das_t to a kef file."))

    parser.add_argument("-T", "--Time_t", dest="time_t", action="store_true",
                        default=False,
                        help=("Dump /Experiment_g/Receivers_g/Time_t "
                              "to a kef file."))

    parser.add_argument("-o", "--outfile", dest="output_file",
                        help="The kef output file to be saved at.",
                        metavar="output_file", default=None)

    args = parser.parse_args()

    PH5 = args.ph5_file_prefix
    PATH = args.ph5_path
    DEBUG = args.debug
    EXPERIMENT_TABLE = args.experiment_t
    SORT_TABLE = args.sort_t
    if args.offset_t_ is not None:
        try:
            OFFSET_TABLE = map(int, args.offset_t_.split("_"))
        except Exception:
            err_msg = "Offset table should be entered as arrayID underscore" \
                      "shotLineID, eg. 1_2 or 0_0."
            raise Exception(err_msg)
    else:
        OFFSET_TABLE = None
    EVENT_TABLE = args.event_t_
    TIME_TABLE = args.time_t
    INDEX_TABLE = args.index_t
    M_INDEX_TABLE = args.m_index_t
    ARRAY_TABLE = args.array_t_
    ALL_ARRAYS = args.all_arrays
    ALL_EVENTS = args.all_events
    RESPONSE_TABLE = args.response_t
    REPORT_TABLE = args.report_t
    RECEIVER_TABLE = args.receiver_t
    DAS_TABLE = args.das_t_

    table_list = [EXPERIMENT_TABLE, SORT_TABLE, OFFSET_TABLE, EVENT_TABLE,
                  TIME_TABLE, INDEX_TABLE, M_INDEX_TABLE, ARRAY_TABLE,
                  ALL_ARRAYS, ALL_EVENTS, RESPONSE_TABLE, REPORT_TABLE,
                  RECEIVER_TABLE, DAS_TABLE]
    if all(not t for t in table_list):
        raise Exception("No table specified for output. See --help for more "
                        "details.")

    # define OFILE to write output
    o_filename = args.output_file
    if o_filename is None:
        OFILE = None
    else:
        OFILE = open(o_filename, 'w')

    return PH5, PATH, OFILE, DEBUG, EXPERIMENT_TABLE, SORT_TABLE, \
        OFFSET_TABLE, EVENT_TABLE, ALL_EVENTS, ARRAY_TABLE, ALL_ARRAYS, \
        RESPONSE_TABLE, REPORT_TABLE, RECEIVER_TABLE, DAS_TABLE, TIME_TABLE, \
        INDEX_TABLE, M_INDEX_TABLE

#
# Initialize ph5 file
#


def initialize_ph5(PATH, PH5, editmode=False):
    '''   Initialize the ph5 file   '''

    EX = experiment.ExperimentGroup(PATH, PH5)
    EX.ph5open(editmode)
    EX.initgroup()
    return EX


#
# Print out report
#
def print_report(OFILE, text):
    if OFILE is None:
        print(text)
    else:
        OFILE.write(text + '\n')


#
# Print Rows_Keys
#
def table_print(EX, PATH, TABLE_KEY, OFILE, t, a, fh=None):
    i = 0
    s = ''
    s = s + \
        "#\n#\t%s\tph5 version: %s\n#\n" % (
            time.ctime(time.time()), EX.version())
    # Loop through table rows
    for r in a.rows:
        i += 1

        s = s + "#   Table row %d\n" % i
        # Print table name
        if TABLE_KEY in a.keys:
            s = s + "{0}:Update:{1} \n".format(t, TABLE_KEY)
        else:
            s = s + t + "\n"
        # Loop through each row column and print
        for k in a.keys:
            s = s + "\t" + str(k) + "=" + str(r[k]) + "\n"
        if fh is None:
            print_report(OFILE, s)
            s = ''
        else:
            fh.write(s)
            s = ''


def read_time_table(EX, TIME_T):
    times, time_keys = EX.ph5_g_receivers.read_time()

    TIME_T = Rows_Keys(times, time_keys)
    return TIME_T


def read_report_table(EX, REPORT_T):
    reports, report_keys = EX.ph5_g_reports.read_reports()

    rowskeys = Rows_Keys(reports, report_keys)

    REPORT_T = rowskeys
    return REPORT_T


def read_experiment_table(EX, EXPERIMENT_T):
    '''   Read /Experiment_g/Experiment_t   '''

    exp, exp_keys = EX.read_experiment()

    rowskeys = Rows_Keys(exp, exp_keys)

    EXPERIMENT_T = rowskeys

    return EXPERIMENT_T


def read_event_table(EX, EVENT_TABLE, EVENT_T):
    '''   Read /Experiment_g/Sorts_g/Event_t   '''

    if EVENT_TABLE == 0:
        T = "Event_t"
    else:
        T = "Event_t_{0:03d}".format(EVENT_TABLE)

    try:
        events, event_keys = EX.ph5_g_sorts.read_events(T)
    except Exception:
        raise Exception("Can't read {0}.\nDoes it exist?\n".format(T))

    rowskeys = Rows_Keys(events, event_keys)

    EVENT_T[T] = rowskeys

    return EVENT_T


def read_all_event_table(EX, EVENT_T):
    EVENT_T_NAME_RE = re.compile("Event_t.*")

    names = EX.ph5_g_sorts.namesRE(EVENT_T_NAME_RE)
    for name in names:
        try:
            events, event_keys = EX.ph5_g_sorts.read_events(name)
        except Exception:
            LOGGER.error("Can't read {0}. Does it exist?".format(name))
            continue

        rowskeys = Rows_Keys(events, event_keys)
        EVENT_T[name] = rowskeys
    return EVENT_T


def read_offset_table(EX, OFFSET_TABLE, OFFSET_T):
    '''   Read /Experinent_t/Sorts_g/Offset_t   '''

    if OFFSET_TABLE[0] == 0 or OFFSET_TABLE[1] == 0:
        name = "Offset_t"
    else:
        name = "Offset_t_{0:03d}_{1:03d}".format(
            OFFSET_TABLE[0], OFFSET_TABLE[1])

    try:
        rows, keys = EX.ph5_g_sorts.read_offset(name)
    except Exception:
        return

    OFFSET_T[name] = Rows_Keys(rows, keys)
    return OFFSET_T


def read_sort_table(EX, SORT_T):
    '''   Read /Experiment_t/Sorts_g/Sort_g   '''

    sorts, sorts_keys = EX.ph5_g_sorts.read_sorts()

    rowskeys = Rows_Keys(sorts, sorts_keys)

    SORT_T = rowskeys
    return SORT_T


def read_sort_arrays(EX, ARRAY_T):
    '''   Read /Experiment_t/Sorts_g/Array_t_[n]   '''

    # We get a list of Array_t_[n] names here...
    # (these are also in Sort_t)
    names = EX.ph5_g_sorts.names()
    for n in names:
        arrays, array_keys = EX.ph5_g_sorts.read_arrays(n)

        rowskeys = Rows_Keys(arrays, array_keys)
        # We key this on the name since there can be multiple arrays
        ARRAY_T[n] = rowskeys
    return ARRAY_T


def read_response_table(EX, RESPONSE_T):
    '''   Read /Experiment_g/Respones_g/Response_t   '''

    response, response_keys = EX.ph5_g_responses.read_responses()

    rowskeys = Rows_Keys(response, response_keys)

    RESPONSE_T = rowskeys
    return RESPONSE_T


def read_receiver_table(EX, RECEIVER_T):
    """   Read /Experiment_g/Receivers_g/Receiver_t   """
    receiver, receiver_keys = EX.ph5_g_receivers.read_receiver()
    rowskeys = Rows_Keys(receiver, receiver_keys)
    RECEIVER_T = rowskeys
    return RECEIVER_T


def read_index_table(EX, INDEX_T):
    rows, keys = EX.ph5_g_receivers.read_index()
    INDEX_T = Rows_Keys(rows, keys)
    return INDEX_T


def read_m_index_table(EX, M_INDEX_T):
    rows, keys = EX.ph5_g_maps.read_index()
    M_INDEX_T = Rows_Keys(rows, keys)
    return M_INDEX_T


def read_receivers(EX, DAS_T, RECEIVER_T, DASS, SOH_A, das=None):
    '''   Read tables and arrays (except wiggles) in Das_g_[sn]   '''

    dasGroups = EX.ph5_g_receivers.alldas_g()
    if das is None:
        # Get references for all das groups keyed on das
        dass = sorted(dasGroups.keys())
        # Sort by das sn
    else:
        dass = [das]

    for d in dass:
        # Get node reference
        if "Das_g_" + d not in dasGroups:
            continue

        g = dasGroups["Das_g_" + d]
        dg = Das_Groups(d, g)
        # Save a master list for later
        DASS.append(dg)

        # Set the current das group
        EX.ph5_g_receivers.setcurrent(g)

        # Read /Experiment_g/Receivers_g/Das_g_[sn]/Das_t
        das, das_keys = EX.ph5_g_receivers.read_das()
        rowskeys = Rows_Keys(das, das_keys)
        DAS_T[d] = rowskeys

        # Read SOH file(s) for this das
        SOH_A[d] = EX.ph5_g_receivers.read_soh()
    return DAS_T


#####################################################
# def readPH5
# author: Lan Dam
# updated: 201802
# read data from exp(PH5) to use for KefUtility => KefEdit.py


def readPH5(EX, filename, PATH, tableType, arg=None):

    EXPERIMENT_T, EVENT_T, OFFSET_T, SORT_T, RESPONSE_T, REPORT_T, \
        ARRAY_T, DAS_T, RECEIVER_T, SOH_A, INDEX_T, M_INDEX_T, DASS, TIME_T, \
        TABLE_KEY = init_local()  # innitiate values and clear cache

    if tableType == "Experiment_t":
        return read_experiment_table(EX, EXPERIMENT_T)

    if tableType == "Sort_t":
        return read_sort_table(EX, SORT_T)

    if tableType == "Offset_t":
        if arg == "Offset_t":
            OFFSET_TABLE = [0]
        else:
            OFFSET_TABLE = map(int, arg.split("_"))

        return read_offset_table(EX, OFFSET_TABLE, OFFSET_T)

    if tableType == "All_Offset_t":
        for o in EX.Offset_t_names:
            if o == "Offset_t":
                OFFSET_TABLE = [0]
                OFFSET_T = read_offset_table(EX, OFFSET_TABLE, OFFSET_T)
                break
            OFFSET_TABLE = map(int, o.replace("Offset_t_", "").split("_"))
            OFFSET_T = read_offset_table(EX, OFFSET_TABLE, OFFSET_T)
        return OFFSET_T

    if tableType == "Event_t":
        EVENT_TABLE = int(arg)
        try:
            return read_event_table(EX, EVENT_TABLE, EVENT_T)
        except Exception, e:
            raise e

    if tableType == "All_Event_t":

        for n in EX.Event_t_names:
            if n == 'Event_t':
                EVENT_TABLE = 0
            else:
                EVENT_TABLE = int(n.replace('Event_t_', ''))
            try:
                EVENT_T = read_event_table(EX, EVENT_TABLE, EVENT_T)
            except Exception, e:
                raise e
        return EVENT_T

    if tableType == "Index_t":
        return read_index_table(EX, INDEX_T)

    if tableType == "Map_Index_t":
        return read_m_index_table(EX, M_INDEX_T)

    if tableType == "Time_t":
        return read_time_table(EX, TIME_T)

    if tableType == "Array_t":
        ARRAY_TABLE = arg
        read_sort_table(EX, SORT_T)
        ARRAY_T = read_sort_arrays(EX, ARRAY_T)
        arrays = ARRAY_T.keys()
        for a in arrays:
            n = int(string.split(a, '_')[2])
            if n == int(ARRAY_TABLE):
                return ARRAY_T[a]

    if tableType == "All_Array_t":
        read_sort_table(EX, SORT_T)
        ARRAY_T = read_sort_arrays(EX, ARRAY_T)
        return ARRAY_T

    if tableType == "Response_t":
        return read_response_table(EX, RESPONSE_T)

    if tableType == "Report_t":
        return read_report_table(EX, REPORT_T)

    if tableType == "Receiver_t":
        return read_receiver_table(EX, RECEIVER_T)

    if tableType == "Das_t":
        return read_receivers(EX, DAS_T, RECEIVER_T, DASS, SOH_A, arg)


def main():
    EXPERIMENT_T, EVENT_T, OFFSET_T, SORT_T, RESPONSE_T, REPORT_T, \
        ARRAY_T, DAS_T, RECEIVER_T, SOH_A, INDEX_T, M_INDEX_T, DASS, TIME_T, \
        TABLE_KEY = init_local()  # innitiate values and clear cache

    try:
        PH5, PATH, OFILE, DEBUG, EXPERIMENT_TABLE, SORT_TABLE, OFFSET_TABLE,\
            EVENT_TABLE, ALL_EVENTS, ARRAY_TABLE, ALL_ARRAYS, RESPONSE_TABLE, \
            REPORT_TABLE, RECEIVER_TABLE, DAS_TABLE, TIME_TABLE, INDEX_TABLE, \
            M_INDEX_TABLE = get_args()
    except Exception, err_msg:
        LOGGER.error(err_msg)
        return 1

    EX = initialize_ph5(PATH, PH5)

    if EXPERIMENT_TABLE:
        EXPERIMENT_T = read_experiment_table(EX, EXPERIMENT_T)
        table_print(
            EX, PATH, TABLE_KEY, OFILE,
            "/Experiment_g/Experiment_t", EXPERIMENT_T)

    if SORT_TABLE:
        SORT_T = read_sort_table(EX, SORT_T)
        table_print(
            EX, PATH, TABLE_KEY, OFILE,
            "/Experiment_g/Sorts_g/Sort_t", SORT_T)

    if OFFSET_TABLE:
        read_offset_table(EX, OFFSET_TABLE, OFFSET_T)
        keys = OFFSET_T.keys()
        for k in keys:
            table_print(
                EX, PATH, TABLE_KEY, OFILE,
                "/Experiment_g/Sorts_g/{0}".format(k), OFFSET_T[k])

    if EVENT_TABLE is not None:
        try:
            EVENT_T = read_event_table(EX, EVENT_TABLE, EVENT_T)
        except Exception, err_msg:
            LOGGER.error(err_msg)
            return 1
        keys = EVENT_T.keys()
        for k in keys:
            table_print(
                EX, PATH, TABLE_KEY, OFILE,
                "/Experiment_g/Sorts_g/{0}".format(k), EVENT_T[k])

    elif ALL_EVENTS is not False:
        read_all_event_table(EX, EVENT_T)
        keys = EVENT_T.keys()
        for k in keys:
            table_print(
                EX, PATH, TABLE_KEY, OFILE,
                "/Experiment_g/Sorts_g/{0}".format(k), EVENT_T[k])

    if INDEX_TABLE:
        INDEX_T = read_index_table(EX, INDEX_T)
        table_print(
            EX, PATH, TABLE_KEY, OFILE,
            "/Experiment_g/Receivers_g/Index_t", INDEX_T)

    if M_INDEX_TABLE:
        M_INDEX_T = read_m_index_table(EX, M_INDEX_T)
        table_print(
            EX, PATH, TABLE_KEY, OFILE,
            "/Experiment_g/Maps_g/Index_t", M_INDEX_T)

    if TIME_TABLE:
        TIME_T = read_time_table(EX, TIME_T)
        table_print(
            EX, PATH, TABLE_KEY, OFILE,
            "/Experiment_g/Receivers_g/Time_t", TIME_T)

    if ARRAY_TABLE:
        if not SORT_T:
            read_sort_table(EX, SORT_T)

        ARRAY_T = read_sort_arrays(EX, ARRAY_T)
        arrays = ARRAY_T.keys()
        for a in arrays:
            n = int(string.split(a, '_')[2])
            if n == int(ARRAY_TABLE):
                table_print(
                    EX, PATH, TABLE_KEY, OFILE,
                    "/Experiment_g/Sorts_g/" + a, ARRAY_T[a])

    elif ALL_ARRAYS:
        print("ALL_ARRAYS:", ALL_ARRAYS)
        if not SORT_T:
            read_sort_table(EX, SORT_T)

        ARRAY_T = read_sort_arrays(EX, ARRAY_T)
        arrays = ARRAY_T.keys()
        for a in arrays:
            table_print(
                EX, PATH, TABLE_KEY, OFILE,
                "/Experiment_g/Sorts_g/" + a, ARRAY_T[a])

    if RESPONSE_TABLE:
        RESPONSE_T = read_response_table(EX, RESPONSE_T)
        table_print(
            EX, PATH, TABLE_KEY, OFILE,
            "/Experiment_g/Responses_g/Response_t", RESPONSE_T)

    if REPORT_TABLE:
        REPORT_T = read_report_table(EX, REPORT_T)
        table_print(
            EX, PATH, TABLE_KEY, OFILE,
            "/Experiment_g/Reports_g/Report_t", REPORT_T)

    if RECEIVER_TABLE:
        RECEIVER_T = read_receiver_table(EX, RECEIVER_T)
        table_print(
            EX, PATH, TABLE_KEY, OFILE,
            "/Experiment_g/Receivers_g/Receiver_t", RECEIVER_T)

    if DAS_TABLE:
        DAS_T = read_receivers(EX, DAS_T, RECEIVER_T, DASS, SOH_A, DAS_TABLE)
        dass = DAS_T.keys()
        for d in dass:
            table_print(
                EX, PATH, TABLE_KEY, OFILE,
                "/Experiment_g/Receivers_g/Das_g_" + d + "/Das_t", DAS_T[d])

    EX.ph5close()
    if OFILE is not None:
        OFILE.close()


if __name__ == '__main__':
    main()
