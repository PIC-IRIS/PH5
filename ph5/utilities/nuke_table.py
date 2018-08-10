#!/usr/bin/env pnpython3
#
#   Program to re-initialize a table in a ph5 file.
#
#   Steve Azevedo, February 2013
#

import os
import sys
import time
from ph5.core import experiment, timedoy
# from ph5.utilities import tabletokef as T2K
import tabletokef as T2K

PROG_VERSION = '2017.325 Developmental'

if float(T2K.PROG_VERSION[0:8]) < 2017.317:
    sys.stderr.write(
        "Found old version of tabletokef.py."
        " Requires version 2017.317 or newer.")
    sys.exit(-2)


#
#   Read Command line arguments
#


def get_args():
    global PH5, PATH, DEBUG, EXPERIMENT_TABLE, SORT_TABLE, OFFSET_TABLE,\
        EVENT_TABLE, \
        ARRAY_TABLE, RESPONSE_TABLE, REPORT_TABLE, RECEIVER_TABLE, TIME_TABLE,\
        INDEX_TABLE, DAS_TABLE, M_INDEX_TABLE, NO_BACKUP

    from optparse import OptionParser

    oparser = OptionParser()

    oparser.usage = "Version: {0}\ndelete_table --nickname ph5-file-prefix\
    options".format(PROG_VERSION)

    oparser.description = "Initialize a table in a ph5 file. Caution:" \
                          "Deletes contents of table!"

    oparser.add_option("-n", "--nickname", dest="ph5_file_prefix",
                       help="The ph5 file prefix (experiment nickname).",
                       metavar="ph5_file_prefix")

    oparser.add_option("-p", "--path", dest="ph5_path",
                       help="Path to ph5 files. Default to current directory.",
                       metavar="ph5_path")

    oparser.add_option("-d", dest="debug", action="store_true", default=False)

    oparser.add_option("-N", "--no_backup", dest="no_backup",
                       action="store_true", default=False,
                       help="Do NOT create a kef file backup of the table.")

    oparser.add_option("-E", "--Experiment_t", dest="experiment_t",
                       action="store_true",
                       default=False,
                       help="Nuke /Experiment_g/Experiment_t.")

    oparser.add_option("-S", "--Sort_t", dest="sort_t", action="store_true",
                       default=False,
                       help="Nuke /Experiment_g/Sorts_g/Sort_t.")

    oparser.add_option("-O", "--Offset_t", dest="offset_t_", metavar="a_e",
                       help="Nuke\
                       /Experiment_g/Sort_g/Offset_t_[arrayID_eventID] "
                            "to a kef file.")

    oparser.add_option("-V", "--Event_t", dest="event_t_", metavar="n",
                       type=int,
                       help="Nuke /Experiment_g/Sorts_g/Event_t_[n].\
                       Use 0 for Event_t")

    oparser.add_option("-A", "--Array_t_", dest="array_t_", metavar="n",
                       help="Nuke /Experiment_g/Sorts_g/Array_t_[n].",
                       type=int)

    oparser.add_option("-R", "--Response_t", dest="response_t",
                       action="store_true",
                       default=False,
                       help="Nuke /Experiment_g/Responses_g/Response_t.")

    oparser.add_option("-P", "--Report_t", dest="report_t",
                       action="store_true",
                       default=False,
                       help="Nuke /Experiment_g/Reports_g/Report_t.")

    oparser.add_option("-C", "--Receiver_t", dest="receiver_t",
                       action="store_true",
                       default=False,
                       help="Nuke /Experiment_g/Receivers_g/Receiver_t.")

    oparser.add_option("-I", "--Index_t", dest="index_t", action="store_true",
                       default=False,
                       help="Nuke /Experiment_g/Receivers_g/Index_t.")

    oparser.add_option("-M", "--M_Index_t", dest="m_index_t",
                       action="store_true",
                       default=False,
                       help="Nuke /Experiment_g/Maps_g/Index_t.")

    oparser.add_option("-D", "--Das_t", dest="das_t_", metavar="das",
                       help="Nuke/Experiment_g/Receivers_g/Das_g_[das]/Das_t.")

    oparser.add_option("-T", "--Time_t", dest="time_t", action="store_true",
                       default=False,
                       help="Nuke /Experiment_g/Receivers_g/Time_t.")

    options, args = oparser.parse_args()

    if options.ph5_file_prefix is not None:
        PH5 = options.ph5_file_prefix
    else:
        PH5 = None

    if options.ph5_path is not None:
        PATH = options.ph5_path
    else:
        PATH = "."

    if options.debug is not None:
        DEBUG = options.debug

    EXPERIMENT_TABLE = options.experiment_t
    SORT_TABLE = options.sort_t
    if options.offset_t_ is not None:
        try:
            OFFSET_TABLE = map(int, options.offset_t_.split("_"))
        except Exception as e:
            sys.stderr.write(
                "Offset table should be entered as arrayID underscore"
                "shotLineID, eg. 1_2 or 0_0.")
            sys.stderr.write(e.message)
            sys.exit()
    else:
        OFFSET_TABLE = None
    EVENT_TABLE = options.event_t_
    TIME_TABLE = options.time_t
    INDEX_TABLE = options.index_t
    M_INDEX_TABLE = options.m_index_t

    if options.array_t_ is not None:
        ARRAY_TABLE = options.array_t_
    else:
        ARRAY_TABLE = None

    RESPONSE_TABLE = options.response_t
    REPORT_TABLE = options.report_t

    RECEIVER_TABLE = options.receiver_t

    if options.das_t_ is not None:
        DAS_TABLE = options.das_t_
    else:
        DAS_TABLE = None

    if PH5 is None:
        sys.stderr.write("Error: Missing required option. Try --help\n")
        sys.exit(-1)

    NO_BACKUP = options.no_backup


#
#   Initialize ph5 file
#


def initialize_ph5(editmode=True):
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5

    EX = experiment.ExperimentGroup(PATH, PH5)
    EX.ph5open(editmode)
    EX.initgroup()


def backup(table_type, table_path, table):
    '''   Create a backup in kef format. File has year and doy in name.
    '''
    if NO_BACKUP or table.rows == []:
        return
    tdoy = timedoy.TimeDOY(epoch=time.time())
    tt = "{0:04d}{1:03d}".format(tdoy.dtobject.year, tdoy.dtobject.day)
    prefix = "{0}_{1}".format(table_type, tt)
    outfile = "{0}_00.kef".format(prefix)
    #   Do not overwite existing file
    i = 1
    while os.path.exists(outfile):
        outfile = "{0}_{1:02d}.kef".format(prefix, i)
        i += 1
    #   Exit if we can't write backup kef
    if os.access(os.getcwd(), os.W_OK):
        print "Writing table backup: {0}.".format(os.path.join(outfile))
    else:
        sys.stderr.write(
            "Can't write: {0}.\nExiting!\n".format(os.getcwd(), outfile))
        sys.exit(-3)
    #
    try:
        fh = open(outfile, 'w')
        T2K.table_print(table_path, table, fh=fh)
        fh.close()
    except Exception:
        sys.stderr.write(
            "Failed to save {0}.\ne.message\nExiting!\n".format(os.getcwd(),
                                                                outfile))
        sys.exit(-4)


def exclaim(n):
    if (int(time.time()) % 235) == 0:
        print "{0} I am become Death, the Destroyer of Worlds.".format(n)
    else:
        print "{0} It worked.".format(n)


def main():
    get_args()
    initialize_ph5()
    T2K.init_local()
    T2K.EX = EX
    #   /Experiment_g/Experiment_t
    if EXPERIMENT_TABLE:
        table_type = 'Experiment_t'
        T2K.read_experiment_table()
        backup(table_type, '/Experiment_g/Experiment_t', T2K.EXPERIMENT_T)
        EX.nuke_experiment_t()
    #   /Experiment_g/Sorts_g/Sort_t
    if SORT_TABLE:
        table_type = 'Sort_t'
        T2K.read_sort_table()
        backup(table_type, '/Experiment_g/Sorts_g/Sort_t', T2K.SORT_T)
        EX.ph5_g_sorts.nuke_sort_t()
    #   /Experiment_g/Sorts_g/Offset_t
    if OFFSET_TABLE is not None:
        T2K.OFFSET_TABLE = OFFSET_TABLE
        T2K.read_offset_table()
        if OFFSET_TABLE[0] == 0:
            table_type = 'Offset_t'
            if table_type in T2K.OFFSET_T:
                backup(table_type, '/Experiment_g/Sorts_g/Offset_t',
                       T2K.OFFSET_T[table_type])
            if EX.ph5_g_sorts.nuke_offset_t():
                exclaim(OFFSET_TABLE)
            else:
                print "{0} Not found.".format(OFFSET_TABLE)
        else:
            table_type = "Offset_t_{0:03d}_{1:03d}".format(
                OFFSET_TABLE[0], OFFSET_TABLE[1])
            if table_type in T2K.OFFSET_T:
                backup(
                    table_type, '/Experiment_g/Sorts_g/{0}'.format(table_type),
                    T2K.OFFSET_T[table_type])
            if EX.ph5_g_sorts.nuke_offset_t(
                    "Offset_t_{0:03d}_{1:03d}".format(OFFSET_TABLE[0],
                                                      OFFSET_TABLE[1])):
                exclaim(OFFSET_TABLE)
            else:
                print "{0} Not found.".format(OFFSET_TABLE)
    #   /Experiment_g/Sorts_g/Event_t
    if EVENT_TABLE is not None:
        T2K.EVENT_TABLE = EVENT_TABLE
        T2K.read_event_table()
        if EVENT_TABLE == 0:
            table_type = 'Event_t'
            if table_type in T2K.EVENT_T:
                backup(table_type, '/Experiment_g/Sorts_g/Event_t',
                       T2K.EVENT_T[table_type])
            EX.ph5_g_sorts.nuke_event_t()
        else:
            table_type = "Event_t_{0:03d}".format(EVENT_TABLE)
            if table_type in T2K.EVENT_T:
                backup(
                    table_type, '/Experiment_g/Sorts_g/{0}'.format(table_type),
                    T2K.EVENT_T[table_type])
            if EX.ph5_g_sorts.nuke_event_t(
                    "Event_t_{0:03d}".format(EVENT_TABLE)):
                exclaim(EVENT_TABLE)
            else:
                print "{0} Not found.".format(EVENT_TABLE)
    #   /Experiment_g/Sorts_g/Array_t_xxx
    if ARRAY_TABLE:
        T2K.ARRAY_TABLE = ARRAY_TABLE
        T2K.read_sort_arrays()
        table_type = 'Array_t_{0:03d}'.format(ARRAY_TABLE)
        if table_type in T2K.ARRAY_T:
            backup(
                table_type, '/Experiment_g/Sorts_g/{0}'.format(table_type),
                T2K.ARRAY_T[table_type])
        if EX.ph5_g_sorts.nuke_array_t(ARRAY_TABLE):
            exclaim(ARRAY_TABLE)
        else:
            print "{0} Not found.".format(ARRAY_TABLE)

    #   /Experiment_g/Receivers_g/Time_t
    if TIME_TABLE:
        table_type = 'Time_t'
        T2K.read_time_table()
        backup(table_type, '/Experiment_g/Receivers_g/Time_t', T2K.TIME_T)
        EX.ph5_g_receivers.nuke_time_t()
    #   /Experiment_g/Receivers_g/Index_t
    if INDEX_TABLE:
        table_type = 'Index_t'
        T2K.read_index_table()
        backup(table_type, '/Experiment_g/Receivers_g/Index_t', T2K.INDEX_T)
        EX.ph5_g_receivers.nuke_index_t()
    #   /Experiment_g/Maps_g/Index_t
    if M_INDEX_TABLE:
        table_type = 'M_Index_t'
        T2K.read_m_index_table()
        backup(table_type, '/Experiment_g/Maps_g/Index_t', T2K.M_INDEX_T)
        EX.ph5_g_maps.nuke_index_t()
    #   /Experiment_g/Receivers_g/Receiver_t
    if RECEIVER_TABLE:
        table_type = 'Receiver_t'
        T2K.read_receiver_table()
        backup(
            table_type,
            '/Experiment_g/Receivers_g/Receiver_t',
            T2K.RECEIVER_T)
        EX.ph5_g_receivers.nuke_receiver_t()
    #   /Experiment_g/Responses_g/Response_t
    if RESPONSE_TABLE:
        table_type = 'Response_t'
        T2K.read_response_table()
        backup(
            table_type,
            '/Experiment_g/Responses_g/Response_t',
            T2K.RESPONSE_T)
        EX.ph5_g_responses.nuke_response_t()
    #   /Experiment_g/Reports_g/Report_t
    if REPORT_TABLE:
        table_type = 'Report_t'
        T2K.read_report_table()
        backup(table_type, '/Experiment_g/Reports_g/Report_t', T2K.REPORT_T)
        EX.ph5_g_reports.nuke_report_t()
    #
    if DAS_TABLE:
        yon = raw_input(
            "Are you sure you want to delete all data in Das_t for das {0}?"
            " y/n ".format(DAS_TABLE))
        if yon == 'y':
            table_type = 'Das_t_{0}'.format(DAS_TABLE)
            T2K.DAS_TABLE = DAS_TABLE
            T2K.read_receivers(DAS_TABLE)
            if DAS_TABLE in T2K.DAS_T:
                backup(table_type,
                       '/Experiment_g/Receivers_g/Das_g_{0}/Das_t'.format(
                           DAS_TABLE), T2K.DAS_T[DAS_TABLE])
            EX.ph5_g_receivers.nuke_das_t(DAS_TABLE)

    EX.ph5close()


if __name__ == '__main__':
    main()
