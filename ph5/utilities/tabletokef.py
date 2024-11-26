#!/usr/bin/env pnpython4

#
# Dump tables in ph5 file to kef format.
#
# Steve Azevedo, April 2007
#


import argparse
import string
import sys
import logging
import time
# This provides the base functionality
from ph5.core import experiment

# Timeseries are stored as numpy arrays

PROG_VERSION = '2024.318'
LOGGER = logging.getLogger(__name__)


#
# These are to hold different parts of the meta-data
#


def init_local():
    global EXPERIMENT_T, EVENT_T, OFFSET_T, SORT_T, RESPONSE_T, REPORT_T
    global ARRAY_T, DAS_T
    global RECEIVER_T, SOH_A, INDEX_T, M_INDEX_T, DASS, TIME_T, TABLE_KEY
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
    global PH5, PATH, DEBUG, EXPERIMENT_TABLE, SORT_TABLE, OFFSET_TABLE, \
        EVENT_TABLE, ARRAY_TABLE, RESPONSE_TABLE, REPORT_TABLE, \
        RECEIVER_TABLE, DAS_TABLE, TIME_TABLE, TABLE_KEY, INDEX_TABLE, \
        M_INDEX_TABLE, ALL_ARRAYS, ALL_EVENTS, OFILE, IGNORE_SRM

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

    parser.add_argument("-i", "--ignore_srm", action="store_true",
                        default=False,
                        help=("Ignore checking sample_rate_multiplier_i "
                              "in Array_t or Das_t"))

    args = parser.parse_args()

    PH5 = args.ph5_file_prefix
    PATH = args.ph5_path
    DEBUG = args.debug
    IGNORE_SRM = args.ignore_srm
    EXPERIMENT_TABLE = args.experiment_t
    SORT_TABLE = args.sort_t
    if args.offset_t_ is not None:
        try:
            OFFSET_TABLE = map(int, args.offset_t_.split("_"))
        except Exception as e:
            LOGGER.error(
                "Offset table should be entered as arrayID underscore "
                "shotLineID, eg. 1_2 or 0_0.")
            LOGGER.error(e.message)
            sys.exit()
    else:
        OFFSET_TABLE = None
    EVENT_TABLE = args.event_t_
    TIME_TABLE = args.time_t
    INDEX_TABLE = args.index_t
    M_INDEX_TABLE = args.m_index_t
    TABLE_KEY = args.update_key
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
        LOGGER.error("No table specified for output. See --help for more "
                     "details.")

    # define OFILE to write output
    o_filename = args.output_file
    if o_filename is None:
        OFILE = None
    else:
        OFILE = open(o_filename, 'w')

#
# Initialize ph5 file
#


def initialize_ph5(editmode=False):
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5

    EX = experiment.ExperimentGroup(PATH, PH5)
    EX.ph5open(editmode)
    EX.initgroup()


#
# Print out report
#
def print_report(text):
    global OFILE
    if OFILE is None:
        print(text)
    else:
        OFILE.write(text + '\n')


#
# Print Rows_Keys
#
def table_print(t, a, fh=None):
    global TABLE_KEY
    global PATH
    global EX
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
            print_report(s)
            s = ''
        else:
            fh.write(s)
            s = ''


def read_time_table():
    global EX, TIME_T

    times, time_keys = EX.ph5_g_receivers.read_time()

    TIME_T = Rows_Keys(times, time_keys)


def read_report_table():
    global EX, REPORT_T

    reports, report_keys = EX.ph5_g_reports.read_reports()

    rowskeys = Rows_Keys(reports, report_keys)

    REPORT_T = rowskeys


def read_experiment_table():
    '''   Read /Experiment_g/Experiment_t   '''
    global EX, EXPERIMENT_T

    exp, exp_keys = EX.read_experiment()

    rowskeys = Rows_Keys(exp, exp_keys)

    EXPERIMENT_T = rowskeys


def read_event_table():
    '''   Read /Experiment_g/Sorts_g/Event_t   '''
    global EX, EVENT_T

    if EVENT_TABLE == 0:
        T = "Event_t"
    else:
        T = "Event_t_{0:03d}".format(EVENT_TABLE)

    try:
        events, event_keys = EX.ph5_g_sorts.read_events(T)
    except Exception:
        LOGGER.error("Can't read {0}.\nDoes it exist?\n".format(T))
        sys.exit()

    rowskeys = Rows_Keys(events, event_keys)

    EVENT_T[T] = rowskeys


def read_all_event_table():
    global EX, EVENT_T
    import re
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


def read_offset_table():
    '''   Read /Experinent_t/Sorts_g/Offset_t   '''
    global EX, OFFSET_T

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


def read_all_offset_table():
    global EX, OFFSET_T
    import re
    OFFSET_T_NAME_RE = re.compile("Offset_t.*")

    names = EX.ph5_g_sorts.namesRE(OFFSET_T_NAME_RE)
    for name in names:
        try:
            offsets, offset_keys = EX.ph5_g_sorts.read_offsets(name=name)
        except Exception:
            LOGGER.error("Can't read {0}. Does it exist?".format(name))
            continue

        rowskeys = Rows_Keys(offsets, offset_keys)
        OFFSET_T[name] = rowskeys


def read_sort_table():
    '''   Read /Experiment_t/Sorts_g/Sort_g   '''
    global EX, SORT_T

    sorts, sorts_keys = EX.ph5_g_sorts.read_sorts()

    rowskeys = Rows_Keys(sorts, sorts_keys)

    SORT_T = rowskeys


def read_sort_arrays(ignore_srm=False):
    '''   Read /Experiment_t/Sorts_g/Array_t_[n]   '''
    global EX, ARRAY_T

    # We get a list of Array_t_[n] names here...
    # (these are also in Sort_t)
    names = EX.ph5_g_sorts.names()
    for n in names:
        try:
            arrays, array_keys = EX.ph5_g_sorts.read_arrays(n, ignore_srm)
        except experiment.HDF5InteractionError as e:
            LOGGER.error(e.msg)
            return
        rowskeys = Rows_Keys(arrays, array_keys)
        # We key this on the name since there can be multiple arrays
        ARRAY_T[n] = rowskeys


def read_response_table():
    '''   Read /Experiment_g/Respones_g/Response_t   '''
    global EX, RESPONSE_T

    response, response_keys = EX.ph5_g_responses.read_responses()

    rowskeys = Rows_Keys(response, response_keys)

    RESPONSE_T = rowskeys


def read_receiver_table():
    global EX, RECEIVER_T

    # Read /Experiment_g/Receivers_g/Receiver_t
    receiver, receiver_keys = EX.ph5_g_receivers.read_receiver()
    rowskeys = Rows_Keys(receiver, receiver_keys)
    RECEIVER_T = rowskeys


def read_index_table():
    global EX, INDEX_T

    rows, keys = EX.ph5_g_receivers.read_index()
    INDEX_T = Rows_Keys(rows, keys)


def read_m_index_table():
    global EX, M_INDEX_T

    rows, keys = EX.ph5_g_maps.read_index()
    M_INDEX_T = Rows_Keys(rows, keys)


def read_receivers(das=None, ignore_srm=False):
    '''   Read tables and arrays (except wiggles) in Das_g_[sn]   '''
    global EX, DAS_T, RECEIVER_T, DASS, SOH_A

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
        try:
            das, das_keys = EX.ph5_g_receivers.read_das(ignore_srm)
        except experiment.HDF5InteractionError as e:
            LOGGER.error(e.msg)
            return
        rowskeys = Rows_Keys(das, das_keys)
        DAS_T[d] = rowskeys

        # Read SOH file(s) for this das
        SOH_A[d] = EX.ph5_g_receivers.read_soh()


#####################################################
# def readPH5
# author: Lan Dam
# updated: 201802
# read data from exp(PH5) to use for KefUtility => KefEdit.py


def readPH5(exp, filename, path, tableType, arg=None):
    # print "readPH5"
    global EX, OFFSET_TABLE, EVENT_TABLE, ARRAY_TABLE, OFFSET_T, EVENT_T,\
        ARRAY_T
    global DAS_T, DASS, SOH_A
    init_local()  # innitiate values and clear cache

    EX = exp

    if tableType == "Experiment_t":
        read_experiment_table()
        return EXPERIMENT_T

    if tableType == "Sort_t":
        read_sort_table()
        return SORT_T

    if tableType == "Offset_t":
        if arg == "Offset_t":
            OFFSET_TABLE = [0]
        else:
            OFFSET_TABLE = map(int, arg.split("_"))
        # read_offset_table() will read from global var. OFFSET_TABLE to add
        # new item into dict. OFFSET_T
        read_offset_table()
        return OFFSET_T

    if tableType == "All_Offset_t":
        for o in EX.Offset_t_names:
            if o == "Offset_t":
                OFFSET_TABLE = [0]
                read_offset_table()
                break
            OFFSET_TABLE = map(int, o.replace("Offset_t_", "").split("_"))
            read_offset_table()
        return OFFSET_T

    if tableType == "Event_t":
        EVENT_TABLE = int(arg)

        # read_event_table() will read from global var. EVENT_TABLE to add new
        # item into dict. EVENT_T
        read_event_table()
        return EVENT_T

    if tableType == "All_Event_t":

        for n in EX.Event_t_names:
            if n == 'Event_t':
                EVENT_TABLE = 0
            else:
                EVENT_TABLE = int(n.replace('Event_t_', ''))
            read_event_table()

        return EVENT_T

    if tableType == "Index_t":
        read_index_table()
        return INDEX_T

    if tableType == "Map_Index_t":
        read_m_index_table()
        return M_INDEX_T

    if tableType == "Time_t":
        read_time_table()
        return TIME_T

    if tableType == "Array_t":
        ARRAY_TABLE = arg
        read_sort_table()
        read_sort_arrays()
        arrays = ARRAY_T.keys()
        for a in arrays:
            n = int(string.split(a, '_')[2])
            if n == int(ARRAY_TABLE):
                return ARRAY_T[a]

    if tableType == "All_Array_t":
        read_sort_table()
        read_sort_arrays()
        arrays = ARRAY_T.keys()
        return ARRAY_T

    if tableType == "Response_t":
        read_response_table()
        return RESPONSE_T

    if tableType == "Report_t":
        read_report_table()
        return REPORT_T

    if tableType == "Receiver_t":
        read_receiver_table()
        return RECEIVER_T

    if tableType == "Das_t":
        read_receivers(arg)
        return DAS_T


def main():
    global PH5, PATH, DEBUG, EXPERIMENT_TABLE, SORT_TABLE, OFFSET_TABLE,\
        EVENT_TABLE, \
        ARRAY_TABLE, RESPONSE_TABLE, REPORT_TABLE, RECEIVER_TABLE, DAS_TABLE,\
        TIME_TABLE, INDEX_TABLE, IGNORE_SRM

    init_local()

    get_args()

    initialize_ph5()

    if EXPERIMENT_TABLE:
        read_experiment_table()
        table_print("/Experiment_g/Experiment_t", EXPERIMENT_T)

    if SORT_TABLE:
        read_sort_table()
        table_print("/Experiment_g/Sorts_g/Sort_t", SORT_T)

    if OFFSET_TABLE:
        read_offset_table()
        keys = OFFSET_T.keys()
        for k in keys:
            table_print("/Experiment_g/Sorts_g/{0}".format(k), OFFSET_T[k])

    if EVENT_TABLE is not None:
        read_event_table()
        keys = EVENT_T.keys()
        for k in keys:
            table_print("/Experiment_g/Sorts_g/{0}".format(k), EVENT_T[k])
    elif ALL_EVENTS is not False:
        read_all_event_table()
        keys = EVENT_T.keys()
        for k in keys:
            table_print("/Experiment_g/Sorts_g/{0}".format(k), EVENT_T[k])

    if INDEX_TABLE:
        read_index_table()
        table_print("/Experiment_g/Receivers_g/Index_t", INDEX_T)

    if M_INDEX_TABLE:
        read_m_index_table()
        table_print("/Experiment_g/Maps_g/Index_t", M_INDEX_T)

    if TIME_TABLE:
        read_time_table()
        table_print("/Experiment_g/Receivers_g/Time_t", TIME_T)

    if ARRAY_TABLE:
        if not SORT_T:
            read_sort_table()

        read_sort_arrays(ignore_srm=IGNORE_SRM)
        arrays = ARRAY_T.keys()
        for a in arrays:
            n = int(string.split(a, '_')[2])
            if n == int(ARRAY_TABLE):
                table_print("/Experiment_g/Sorts_g/" + a, ARRAY_T[a])
    elif ALL_ARRAYS:
        if not SORT_T:
            read_sort_table()

        read_sort_arrays(ignore_srm=IGNORE_SRM)
        arrays = ARRAY_T.keys()
        for a in arrays:
            table_print("/Experiment_g/Sorts_g/" + a, ARRAY_T[a])

    if RESPONSE_TABLE:
        read_response_table()
        table_print("/Experiment_g/Responses_g/Response_t", RESPONSE_T)

    if REPORT_TABLE:
        read_report_table()
        table_print("/Experiment_g/Reports_g/Report_t", REPORT_T)

    if RECEIVER_TABLE:
        read_receiver_table()
        table_print("/Experiment_g/Receivers_g/Receiver_t", RECEIVER_T)

    if DAS_TABLE:
        read_receivers(DAS_TABLE, IGNORE_SRM)
        dass = DAS_T.keys()
        for d in dass:
            table_print("/Experiment_g/Receivers_g/Das_g_" +
                        d + "/Das_t", DAS_T[d])

    EX.ph5close()
    if OFILE is not None:
        OFILE.close()


if __name__ == '__main__':
    main()
