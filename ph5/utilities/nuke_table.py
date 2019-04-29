#!/usr/bin/env pnpython3
#
# Program to re-initialize a table in a ph5 file.
#
# Steve Azevedo, February 2013
#


import argparse
import os
import logging
import time
from ph5.core import experiment, timedoy
import tabletokef

PROG_VERSION = '2019.057'
logging.basicConfig()
LOGGER = logging.getLogger(__name__)


class NukeTableError(Exception):
    '''   Exception gets raised in NukeTable   '''

    def __init__(self, message=''):
        super(NukeTableError, self).__init__(message)
        self.message = message

#
# Read Command line arguments
#

class NukeTable():
    def __init__(self):
        self.ph5 = None
        self.PATH = None
        self.DEBUG = False
        self.EXPERIMENT_TABLE = False
        self.SORT_TABLE = False
        self.OFFSET_TABLE = None
        self.EVENT_TABLE = None
        self.TIME_TABLE = False
        self.INDEX_TABLE = False
        self.M_INDEX_TABLE = False
        self.ARRAY_TABLE = False
        self.ALL_ARRAYS = False
        self.RESPONSE_TABLE = False
        self.REPORT_TABLE = False
        self.RECEIVER_TABLE = False
        self.DAS_TABLE = None
        self.NO_BACKUP = False

    def get_args(self):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter)

        parser.usage = ("delete_table --nickname ph5-file-prefix "
                        "[options]".format(PROG_VERSION))

        parser.description = ("Initialize a table in a ph5 file. Caution:"
                              "Deletes contents of table!\n\nVersion: {0}"
                              .format(PROG_VERSION))

        parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                            help="The ph5 file prefix (experiment nickname).",
                            metavar="ph5_file_prefix", required=True)

        parser.add_argument("-p", "--path", dest="ph5_path",
                            help="Path to ph5 files. Default to current "
                                 "directory.",
                            metavar="ph5_path", default=".")

        parser.add_argument("-d", dest="debug", action="store_true",
                            default=False)

        parser.add_argument("-N", "--no_backup", dest="no_backup",
                            action="store_true", default=False,
                            help="Do NOT create a kef file backup of "
                            "the table.")

        parser.add_argument("-E", "--Experiment_t", dest="experiment_t",
                            action="store_true",
                            default=False,
                            help="Nuke /Experiment_g/Experiment_t.")

        parser.add_argument("-S", "--Sort_t", dest="sort_t",
                            action="store_true", default=False,
                            help="Nuke /Experiment_g/Sorts_g/Sort_t.")

        parser.add_argument("-O", "--Offset_t", dest="offset_t_",
                            metavar="a_e",
                            help="Nuke /Experiment_g/Sort_g/Offset_t_"
                            "[arrayID_eventID] to a kef file.")

        parser.add_argument("-V", "--Event_t", dest="event_t_", metavar="n",
                            type=int,
                            help="Nuke /Experiment_g/Sorts_g/Event_t_[n]. "
                                 "Use 0 for Event_t")

        parser.add_argument("-A", "--Array_t_", dest="array_t_", metavar="n",
                            help="Nuke /Experiment_g/Sorts_g/Array_t_[n].",
                            type=int)

        parser.add_argument("--all_arrays", dest='all_arrays',
                            action='store_true', default=False,
                            help=("Nuke all /Experiment_g/Sorts_g/Array_t_xxx "
                                  "to a kef file."))

        parser.add_argument("-R", "--Response_t", dest="response_t",
                            action="store_true",
                            default=False,
                            help="Nuke /Experiment_g/Responses_g/Response_t.")

        parser.add_argument("-P", "--Report_t", dest="report_t",
                            action="store_true",
                            default=False,
                            help="Nuke /Experiment_g/Reports_g/Report_t.")

        parser.add_argument("-C", "--Receiver_t", dest="receiver_t",
                            action="store_true",
                            default=False,
                            help="Nuke /Experiment_g/Receivers_g/Receiver_t.")

        parser.add_argument("-I", "--Index_t", dest="index_t",
                            action="store_true", default=False,
                            help="Nuke /Experiment_g/Receivers_g/Index_t.")

        parser.add_argument("-M", "--M_Index_t", dest="m_index_t",
                            action="store_true",
                            default=False,
                            help="Nuke /Experiment_g/Maps_g/Index_t.")

        parser.add_argument("-D", "--Das_t", dest="das_t_", metavar="das",
                            help="Nuke/Experiment_g/Receivers_g/Das_g_[das]/"
                                 "Das_t.")

        parser.add_argument("-T", "--Time_t", dest="time_t",
                            action="store_true", default=False,
                            help="Nuke /Experiment_g/Receivers_g/Time_t.")

        args = parser.parse_args()

        self.PH5 = args.ph5_file_prefix
        self.PATH = args.ph5_path
        self.DEBUG = args.debug
        self.EXPERIMENT_TABLE = args.experiment_t
        self.SORT_TABLE = args.sort_t
        if args.offset_t_ is not None:
            try:
                self.OFFSET_TABLE = map(int, args.offset_t_.split("_"))
                if len(self.OFFSET_TABLE) != 2:
                    raise NukeTableError()
            except Exception:
                raise NukeTableError(
                    "Offset table should be entered as arrayID "
                    "underscore shotLineID, eg. 1_2 or 0_0.")

        self.EVENT_TABLE = args.event_t_
        self.TIME_TABLE = args.time_t
        self.INDEX_TABLE = args.index_t
        self.M_INDEX_TABLE = args.m_index_t
        self.ARRAY_TABLE = args.array_t_
        self.ALL_ARRAYS = args.all_arrays
        self.RESPONSE_TABLE = args.response_t
        self.REPORT_TABLE = args.report_t
        self.RECEIVER_TABLE = args.receiver_t
        self.DAS_TABLE = args.das_t_
        self.NO_BACKUP = args.no_backup

    #
    # Initialize ph5 file
    #
    def initialize_ph5(self, editmode=True):
        '''   Initialize the ph5 file   '''

        self.EX = experiment.ExperimentGroup(self.PATH, self.PH5)
        self.EX.ph5open(editmode)
        self.EX.initgroup()
        self.T2K = tabletokef.Tabletokef()
        self.T2K.set_EX(self.EX)

    def backup(self, table_type, table_path, table):
        '''  Create a backup in kef format. File has year and doy in name.  '''
        if self.NO_BACKUP or table.rows == []:
            return
        tdoy = timedoy.TimeDOY(epoch=time.time())
        tt = "{0:04d}{1:03d}".format(tdoy.dtobject.year, tdoy.dtobject.day)
        prefix = "{0}_{1}".format(table_type, tt)
        outfile = "{0}_00.kef".format(prefix)
        # Do not overwite existing file
        i = 1
        while os.path.exists(outfile):
            outfile = "{0}_{1:02d}.kef".format(prefix, i)
            i += 1
        # Exit if we can't write backup kef
        if os.access(os.getcwd(), os.W_OK):
            LOGGER.info("Writing table backup: {0}.".
                        format(os.path.join(outfile)))
        else:
            raise NukeTableError(
                "Can't write: {0}/{1}.\nExiting!".format(os.getcwd(), outfile))

        try:
            fh = open(outfile, 'w')
            self.T2K.table_print(table_path, table, fh)
            fh.close()
        except Exception, e:
            raise NukeTableError("Failed to save {0}/{1}.\n{2}\nExiting!"
                                 .format(os.getcwd(), outfile, e.message))
        return outfile

    def exclaim(self, n):
        if (int(time.time()) % 235) == 0:
            LOGGER.info("{0} I am become Death, the Destroyer of Worlds."
                        .format(n))
        else:
            LOGGER.info("{0} It worked.".format(n))

    def doNuke(self):
        try:
            # /Experiment_g/Experiment_t
            if self.EXPERIMENT_TABLE:
                self.T2K.read_experiment_table()
                self.backup('Experiment_t', '/Experiment_g/Experiment_t',
                            self.T2K.EXPERIMENT_T)
                self.EX.nuke_experiment_t()

            # /Experiment_g/Sorts_g/Sort_t
            if self.SORT_TABLE:
                self.T2K.read_sort_table()
                self.backup('Sort_t', '/Experiment_g/Sorts_g/Sort_t',
                            self.T2K.SORT_T)
                self.EX.ph5_g_sorts.nuke_sort_t()

            # /Experiment_g/Sorts_g/Offset_t
            if self.OFFSET_TABLE is not None:
                self.T2K.read_offset_table(self.OFFSET_TABLE)
                if self.OFFSET_TABLE[0] == 0:
                    if 'Offset_t' in self.T2K.OFFSET_T:
                        self.backup('Offset_t',
                                    '/Experiment_g/Sorts_g/Offset_t',
                                    self.T2K.OFFSET_T['Offset_t'])

                    if self.EX.ph5_g_sorts.nuke_offset_t():
                        self.exclaim(self.OFFSET_TABLE)
                    else:
                        raise NukeTableError("{0} Not found."
                                             .format(self.OFFSET_TABLE))
                else:
                    table_type = "Offset_t_{0:03d}_{1:03d}".format(
                        self.OFFSET_TABLE[0], self.OFFSET_TABLE[1])
                    if table_type in self.T2K.OFFSET_T:
                        self.backup(
                            table_type, '/Experiment_g/Sorts_g/{0}'
                            .format(table_type),
                            self.T2K.OFFSET_T[table_type])
                    if self.EX.ph5_g_sorts.nuke_offset_t(
                        "Offset_t_{0:03d}_{1:03d}".format(
                            self.OFFSET_TABLE[0], self.OFFSET_TABLE[1])):
                        self.exclaim(self.OFFSET_TABLE)
                    else:
                        raise NukeTableError("{0} Not found."
                                             .format(self.OFFSET_TABLE))

            # /Experiment_g/Sorts_g/Event_t
            if self.EVENT_TABLE is not None:
                self.T2K.read_event_table(self.EVENT_TABLE)
                if self.EVENT_TABLE == 0:
                    table_type = 'Event_t'
                    if table_type in self.T2K.EVENT_T:
                        self.backup(table_type,
                                    '/Experiment_g/Sorts_g/Event_t',
                                    self.T2K.EVENT_T[table_type])
                    self.EX.ph5_g_sorts.nuke_event_t()
                else:
                    table_type = "Event_t_{0:03d}".format(self.EVENT_TABLE)
                    if table_type in self.T2K.EVENT_T:
                        self.backup(
                            table_type, '/Experiment_g/Sorts_g/{0}'.format(
                                table_type),
                            self.T2K.EVENT_T[table_type])
                    if self.EX.ph5_g_sorts.nuke_event_t(
                            "Event_t_{0:03d}".format(self.EVENT_TABLE)):
                        self.exclaim(self.EVENT_TABLE)
                    else:
                        raise NukeTableError("{0} Not found."
                                             .format(self.EVENT_TABLE))

            # /Experiment_g/Sorts_g/Array_t_[n]
            if self.ARRAY_TABLE:
                self.T2K.read_sort_arrays()
                table_type = 'Array_t_{0:03d}'.format(self.ARRAY_TABLE)
                if table_type in self.T2K.ARRAY_T:
                    self.backup(
                        table_type,
                        '/Experiment_g/Sorts_g/{0}'.format(table_type),
                        self.T2K.ARRAY_T[table_type])
                if self.EX.ph5_g_sorts.nuke_array_t(self.ARRAY_TABLE):
                    self.exclaim(self.ARRAY_TABLE)
                else:
                    raise NukeTableError("{0} Not found."
                                         .format(self.ARRAY_TABLE))

            # /Experiment_g/Sorts_g/Array_t_xxx
            elif self.ALL_ARRAYS:
                self.T2K.read_sort_arrays()
                for table_type in self.T2K.ARRAY_T:
                    self.backup(
                        table_type,
                        '/Experiment_g/Sorts_g/{0}'.format(table_type),
                        self.T2K.ARRAY_T[table_type])
                    self.ARRAY_TABLE = int(table_type[-3:])
                    if self.EX.ph5_g_sorts.nuke_array_t(self.ARRAY_TABLE):
                        self.exclaim(self.ARRAY_TABLE)
                    else:
                        raise NukeTableError("{0} Not found."
                                             .format(self.ARRAY_TABLE))

            # /Experiment_g/Receivers_g/Time_t
            if self.TIME_TABLE:
                self.T2K.read_time_table()
                self.backup('Time_t', '/Experiment_g/Receivers_g/Time_t',
                            self.T2K.TIME_T)
                self.EX.ph5_g_receivers.nuke_time_t()

            # /Experiment_g/Receivers_g/Index_t
            if self.INDEX_TABLE:
                self.T2K.read_index_table()
                self.backup(
                    'Index_t', '/Experiment_g/Receivers_g/Index_t',
                    self.T2K.INDEX_T)
                self.EX.ph5_g_receivers.nuke_index_t()

            # /Experiment_g/Maps_g/Index_t
            if self.M_INDEX_TABLE:
                self.T2K.read_m_index_table()
                self.backup('M_Index_t', '/Experiment_g/Maps_g/Index_t',
                            self.T2K.M_INDEX_T)
                self.EX.ph5_g_maps.nuke_index_t()
            # /Experiment_g/Receivers_g/Receiver_t

            if self.RECEIVER_TABLE:
                self.T2K.read_receiver_table()
                self.backup(
                    'Receiver_t',
                    '/Experiment_g/Receivers_g/Receiver_t',
                    self.T2K.RECEIVER_T)
                self.EX.ph5_g_receivers.nuke_receiver_t()

            # /Experiment_g/Responses_g/Response_t
            if self.RESPONSE_TABLE:
                self.T2K.read_response_table()
                self.backup(
                    'Response_t',
                    '/Experiment_g/Responses_g/Response_t',
                    self.T2K.RESPONSE_T)
                self.EX.ph5_g_responses.nuke_response_t()

            # /Experiment_g/Reports_g/Report_t
            if self.REPORT_TABLE:
                self.T2K.read_report_table()
                self.backup(
                    'Report_t', '/Experiment_g/Reports_g/Report_t',
                    self.T2K.REPORT_T)
                self.EX.ph5_g_reports.nuke_report_t()

            if self.DAS_TABLE:
                yon = raw_input(
                    "Are you sure you want to delete all data in Das_t "
                    "for das {0}? y/n ".format(self.DAS_TABLE))
                if yon == 'y':
                    table_type = 'Das_t_{0}'.format(self.DAS_TABLE)
                    self.T2K.read_receivers(self.DAS_TABLE)
                    if self.DAS_TABLE in self.T2K.DAS_T:
                        self.backup(
                            table_type,
                            '/Experiment_g/Receivers_g/Das_g_{0}/Das_t'.
                            format(self.DAS_TABLE),
                            self.T2K.DAS_T[self.DAS_TABLE])
                    self.EX.ph5_g_receivers.nuke_das_t(self.DAS_TABLE)

        except Exception, err_msg:
            raise NukeTableError(err_msg)


def main():
    try:
        nukeT = NukeTable()
        nukeT.get_args()

        nukeT.initialize_ph5()
        nukeT.doNuke()
        nukeT.EX.ph5close()
        nukeT.T2K.close()
    except Exception, err_msg:
        LOGGER.error(err_msg)
        return 1


if __name__ == '__main__':
    main()
