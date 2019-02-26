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

PROG_VERSION = '2019.057'
LOGGER = logging.getLogger(__name__)


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
# These are to hold different parts of the meta-data
#

########################################################################
class Tabletokef:
    def __init__(self, PRINOUT=False):
        self.PRINTOUT = PRINOUT
        # /Experiment_g/Experiment_t
        self.EXPERIMENT_T = None
        # /Experiment_g/Sorts_g/Event_t
        self.EVENT_T = {}
        # /Experiment_g/Sorts_g/Offset_t
        self.OFFSET_T = {}
        # /Experiment_g/Sorts_g/Sort_t
        self.SORT_T = None
        # /Experiment_g/Responses_g/Response_t
        self.RESPONSE_T = None
        # /Experiment_g/Reports_g/Report_t
        self.REPORT_T = None
        # /Experiment_g/Sorts_g/Array_t_[nnn]
        self.ARRAY_T = {}
        # /Experiment_g/Receivers_g/Das_g_[sn]/Das_t (keyed on DAS)
        self.DAS_T = {}
        # /Experiment_g/Receivers_g/Receiver_t
        self.RECEIVER_T = None
        # /Experiment_g/Receivers_g/Das_g_[sn]/SOH_a_[n] (keyed on DAS then by
        # SOH_a_[n] name)
        self.SOH_A = {}
        # /Experiment_g/Receivers_g/Index_t
        self.INDEX_T = None
        # /Experiment_g/Maps_g/Index_t
        self.M_INDEX_T = None
        # A list of Das_Groups that refers to Das_g_[sn]'s
        self.DASS = []
        # /Experiment_g/Receivers_g/Time_t
        self.TIME_T = None
        #
        self.TABLE_KEY = None

    #
    # Read Command line arguments
    #
    def get_args(self):
        self.PRINTOUT = True

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
                            help="Set generated kef file to do an "
                            "Update on key.",
                            metavar="update_key", type=str)

        parser.add_argument("-d", "--debug", dest="debug",
                            action="store_true", default=False)

        parser.add_argument("-E", "--Experiment_t", dest="experiment_t",
                            action="store_true", default=False,
                            help="Dump /Experiment_g/Experiment_t"
                            " to a kef file.")

        parser.add_argument("-S", "--Sort_t", dest="sort_t",
                            action="store_true", default=False,
                            help=("Dump /Experiment_g/Sorts_g/Sort_t to a kef "
                                  "file."))

        parser.add_argument("-O", "--Offset_t", dest="offset_t_",
                            metavar="a_e",
                            help=("Dump /Experiment_g/Sort_g/" +
                                  "Offset_t_[arrayID_eventID] to a kef file."))

        parser.add_argument("-V", "--Event_t_", dest="event_t_", metavar="n",
                            type=int,
                            help=("Dump /Experiment_g/Sorts_g/Event_t_[n]"
                                  "to a kef file."))

        parser.add_argument("--all_events", dest='all_events',
                            action='store_true', default=False,
                            help=("Dump all /Experiment_g/Sorts_g/Event_t_xxx "
                                  "to a kef file."))

        parser.add_argument("-A", "--Array_t_", dest="array_t_", metavar="n",
                            type=int,
                            help=("Dump /Experiment_g/Sorts_g/Array_t_[n] "
                                  "to a kef file."))

        parser.add_argument("--all_arrays", dest='all_arrays',
                            action='store_true', default=False,
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

        parser.add_argument("-I", "--Index_t", dest="index_t",
                            action="store_true", default=False,
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

        parser.add_argument("-T", "--Time_t", dest="time_t",
                            action="store_true", default=False,
                            help=("Dump /Experiment_g/Receivers_g/Time_t "
                                  "to a kef file."))

        parser.add_argument("-k", "--keffile", dest="kef_file",
                            help="The kef output file to be saved at.",
                            metavar="output_file", default=None)

        args = parser.parse_args()

        self.PH5 = args.ph5_file_prefix
        self.PATH = args.ph5_path
        self.DEBUG = args.debug
        self.table_type = None
        self.ARG = None
        if args.experiment_t:
            self.table_type = "Experiment_t"
        elif args.sort_t:
            self.table_type = "Sort_t"
        elif args.offset_t_ is not None:
            self.table_type = "Offset_t"
            try:
                self.ARG = map(int, args.offset_t_.split("_"))
            except Exception:
                err_msg = "Offset table should be entered as arrayID "\
                    "underscore shotLineID, eg. 1_2 or 0_0."
                raise Exception(err_msg)
        elif args.event_t_ is not None:
            self.table_type = "Event_t"
            self.ARG = args.event_t_
        elif args.time_t:
            self.table_type = "Time_t"
        elif args.index_t:
            self.table_type = "Index_t"
        elif args.m_index_t:
            self.table_type = "Map_Index_t"
        elif args.array_t_ is not None:
            self.table_type = "Array_t"
            self.ARG = args.array_t_
        elif args.all_arrays:
            self.table_type = "All_Array_t"
        elif args.all_events:
            self.table_type = "All_Event_t"
        elif args.response_t:
            self.table_type = "Response_t"
        elif args.report_t:
            self.table_type = "Report_t"
        elif args.receiver_t:
            self.table_type = "Receiver_t"
        elif args.das_t_ is not None:
            self.table_type = "Das_t"
            self.ARG = args.das_t_

        if self.table_type is None:
            raise Exception("No table specified for output."
                            "See --help for more details.")

        # define OFILE to write output
        o_filename = args.kef_file
        if o_filename is None:
            self.OFILE = None
        else:
            self.OFILE = open(o_filename, 'w')

    def initialize_ph5(self, editmode=False):
        '''   Initialize the ph5 file   '''

        self.EX = experiment.ExperimentGroup(self.PATH, self.PH5)
        self.EX.ph5open(editmode)
        self.EX.initgroup()

    def close(self):
        try:
            self.EX.ph5close()
            self.OFILE.close()
        except Exception:
            pass

    def set_EX(self, EX):
        '''   parent has its own EX   '''
        self.EX = EX

    #
    # Print Rows_Keys
    #
    def table_print(self, table_path, table_data, ofile=None):
        if not self.PRINTOUT and ofile is None:
            return
        if ofile is not None:
            self.OFILE = ofile
        i = 0
        s = "#\n#\t%s\tph5 version: %s\n#\n" % (
                time.ctime(time.time()), self.EX.version())
        # Loop through table rows
        for r in table_data.rows:
            i += 1

            s = s + "#   Table row %d\n" % i
            # Print table name
            if self.TABLE_KEY in table_data.keys:
                s += "{0}:Update:{1} \n".format(table_path, self.TABLE_KEY)
            else:
                s += table_path + "\n"
            # Loop through each row column and print
            for k in table_data.keys:
                s += "\t" + str(k) + "=" + str(r[k]) + "\n"
        if self.OFILE is None:
            print(s)
        else:
            self.OFILE.write(s + '\n')

    def read_time_table(self):
        times, time_keys = self.EX.ph5_g_receivers.read_time()
        self.TIME_T = Rows_Keys(times, time_keys)

    def read_report_table(self):
        reports, report_keys = self.EX.ph5_g_reports.read_reports()
        rowskeys = Rows_Keys(reports, report_keys)
        self.REPORT_T = rowskeys

    def read_experiment_table(self):
        '''   Read /Experiment_g/Experiment_t   '''

        exp, exp_keys = self.EX.read_experiment()
        rowskeys = Rows_Keys(exp, exp_keys)
        self.EXPERIMENT_T = rowskeys

    def read_event_table(self, EVENT_TABLE):
        '''   Read /Experiment_g/Sorts_g/Event_t   '''

        if EVENT_TABLE == 0:
            T = "Event_t"
        else:
            T = "Event_t_{0:03d}".format(int(EVENT_TABLE))

        try:
            events, event_keys = self.EX.ph5_g_sorts.read_events(T)
        except Exception:
            raise Exception("Can't read {0}.\nDoes it exist?\n".format(T))

        rowskeys = Rows_Keys(events, event_keys)

        self.EVENT_T[T] = rowskeys
        return self.EVENT_T

    def read_all_event_table(self):
        EVENT_T_NAME_RE = re.compile("Event_t.*")

        names = self.EX.ph5_g_sorts.namesRE(EVENT_T_NAME_RE)
        for name in names:
            try:
                events, event_keys = self.EX.ph5_g_sorts.read_events(name)
            except Exception:
                LOGGER.error("Can't read {0}. Does it exist?".format(name))
                continue

            rowskeys = Rows_Keys(events, event_keys)
            self.EVENT_T[name] = rowskeys

    def read_offset_table(self, OFFSET_TABLE):
        '''   Read /Experinent_t/Sorts_g/Offset_t   '''

        if OFFSET_TABLE[0] == 0 or OFFSET_TABLE[1] == 0:
            name = "Offset_t"
        else:
            name = "Offset_t_{0:03d}_{1:03d}".format(
                OFFSET_TABLE[0], OFFSET_TABLE[1])

        try:
            rows, keys = self.EX.ph5_g_sorts.read_offset(name)
        except Exception:
            return

        self.OFFSET_T[name] = Rows_Keys(rows, keys)

    def read_sort_table(self):
        '''   Read /Experiment_t/Sorts_g/Sort_g   '''

        sorts, sorts_keys = self.EX.ph5_g_sorts.read_sorts()
        rowskeys = Rows_Keys(sorts, sorts_keys)
        self.SORT_T = rowskeys

    def read_sort_arrays(self):
        '''   Read /Experiment_t/Sorts_g/Array_t_[n]   '''

        # We get a list of Array_t_[n] names here...
        # (these are also in Sort_t)
        names = self.EX.ph5_g_sorts.names()
        for n in names:
            arrays, array_keys = self.EX.ph5_g_sorts.read_arrays(n)

            rowskeys = Rows_Keys(arrays, array_keys)
            # We key this on the name since there can be multiple arrays
            self.ARRAY_T[n] = rowskeys
        return self.ARRAY_T

    def read_response_table(self):
        '''   Read /Experiment_g/Respones_g/Response_t   '''

        response, response_keys = self.EX.ph5_g_responses.read_responses()
        rowskeys = Rows_Keys(response, response_keys)
        self.RESPONSE_T = rowskeys

    def read_receiver_table(self):
        """   Read /Experiment_g/Receivers_g/Receiver_t   """
        receiver, receiver_keys = self.EX.ph5_g_receivers.read_receiver()
        rowskeys = Rows_Keys(receiver, receiver_keys)
        self.RECEIVER_T = rowskeys

    def read_index_table(self):
        rows, keys = self.EX.ph5_g_receivers.read_index()
        self.INDEX_T = Rows_Keys(rows, keys)

    def read_m_index_table(self):
        rows, keys = self.EX.ph5_g_maps.read_index()
        self.M_INDEX_T = Rows_Keys(rows, keys)

    def read_receivers(self, das=None):
        '''   Read tables and arrays (except wiggles) in Das_g_[sn]   '''

        dasGroups = self.EX.ph5_g_receivers.alldas_g()
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
            self.DASS.append(dg)

            # Set the current das group
            self.EX.ph5_g_receivers.setcurrent(g)

            # Read /Experiment_g/Receivers_g/Das_g_[sn]/Das_t
            das, das_keys = self.EX.ph5_g_receivers.read_das()
            rowskeys = Rows_Keys(das, das_keys)
            self.DAS_T[d] = rowskeys

            # Read SOH file(s) for this das
            self.SOH_A[d] = self.EX.ph5_g_receivers.read_soh()

    def read_tables(self, tableType, arg=None, printout=False, fromKefU=False):
        if tableType == "Experiment_t":
            self.read_experiment_table()
            self.table_print("/Experiment_g/Experiment_t", self.EXPERIMENT_T)
            return self.EXPERIMENT_T

        if tableType == "Sort_t":
            self.read_sort_table()
            self.table_print("/Experiment_g/Sorts_g/Sort_t", self.SORT_T)
            return self.SORT_T

        if tableType == "Offset_t":
            try:
                if arg == "Offset_t":
                    OFFSET_TABLE = [0]
                else:
                    OFFSET_TABLE = map(int, arg.split("_"))
            except Exception:
                OFFSET_TABLE = arg
            self.read_offset_table(OFFSET_TABLE)
            for k in self.OFFSET_T.keys():
                self.table_print("/Experiment_g/Sorts_g/{0}".format(k),
                                 self.OFFSET_T[k])
            return self.OFFSET_T

        if tableType == "All_Offset_t":
            for o in self.EX.Offset_t_names:
                if o == "Offset_t":
                    OFFSET_TABLE = [0]
                    self.read_offset_table()
                    break
                OFFSET_TABLE = map(int, o.replace("Offset_t_", "").split("_"))
                self.read_offset_table(OFFSET_TABLE)
            return self.OFFSET_T

        if tableType == "Event_t":
            try:
                self.read_event_table(EVENT_TABLE=arg)
            except Exception, e:
                raise e

            for k in self.EVENT_T.keys():
                self.table_print("/Experiment_g/Sorts_g/{0}".format(k),
                                 self.EVENT_T[k])
            return self.EVENT_T

        if tableType == "All_Event_t":
            if fromKefU:
                for n in self.EX.Event_t_names:
                    if n == 'Event_t':
                        EVENT_TABLE = 0
                    else:
                        EVENT_TABLE = int(n.replace('Event_t_', ''))
                    try:
                        self.read_event_table(EVENT_TABLE=EVENT_TABLE)
                    except Exception, e:
                        raise e
            else:
                self.read_all_event_table()
                for k in self.EVENT_T.keys():
                    self.table_print("/Experiment_g/Sorts_g/{0}".format(k),
                                     self.EVENT_T[k])
            return self.EVENT_T

        if tableType == "Index_t":
            self.read_index_table()
            self.table_print("/Experiment_g/Receivers_g/Index_t", self.INDEX_T)
            return self.INDEX_T

        if tableType == "Map_Index_t":
            self.read_m_index_table()
            self.table_print("/Experiment_g/Maps_g/Index_t", self.M_INDEX_T)
            return self.M_INDEX_T

        if tableType == "Time_t":
            self.read_time_table()
            self.table_print("/Experiment_g/Receivers_g/Time_t", self.TIME_T)
            return self.TIME_T

        if tableType == "Array_t":
            ARRAY_TABLE = arg
            if not self.SORT_T:
                self.read_sort_table()
            self.read_sort_arrays()
            arrays = self.ARRAY_T.keys()
            for a in arrays:
                n = int(string.split(a, '_')[2])
                if n == int(ARRAY_TABLE):
                    self.table_print("/Experiment_g/Sorts_g/" + a,
                                     self.ARRAY_T[a])
                    return self.ARRAY_T[a]

        if tableType == "All_Array_t":
            if not self.SORT_T:
                self.read_sort_table()
            self.read_sort_arrays()
            for a in self.ARRAY_T.keys():
                self.table_print("/Experiment_g/Sorts_g/" + a, self.ARRAY_T[a])
            return self.ARRAY_T

        if tableType == "Response_t":
            self.read_response_table()
            self.table_print("/Experiment_g/Responses_g/Response_t",
                             self.RESPONSE_T)
            return self.RESPONSE_T

        if tableType == "Report_t":
            self.read_report_table()
            self.table_print("/Experiment_g/Reports_g/Report_t", self.REPORT_T)
            return self.REPORT_T

        if tableType == "Receiver_t":
            self.read_receiver_table()
            self.table_print("/Experiment_g/Receivers_g/Receiver_t",
                             self.RECEIVER_T)
            return self.RECEIVER_T

        if tableType == "Das_t":
            self.read_receivers(das=arg)
            for d in self.DAS_T.keys():
                self.table_print("/Experiment_g/Receivers_g/Das_g_" + d
                                 + "/Das_t", self.DAS_T[d])
            return self.DAS_T


def main():
    T2K = Tabletokef()
    try:
        T2K.get_args()

        T2K.initialize_ph5()
        T2K.read_tables(T2K.table_type, T2K.ARG, printout=True)

    except Exception, err_msg:
        LOGGER.error(err_msg)
        T2K.close()
        return 1
    T2K.close()


if __name__ == '__main__':
    main()
