#!/usr/bin/env pnpython2

#
# Set sample_count_i in Das_t based on length of data array
#
# Feb 2009
#

import argparse
import logging
import os
import os.path
import time
# This provides the base functionality
from ph5.core import experiment
# Timeseries are stored as numpy arrays

# Make sure we are all on the same time zone ;^)
os.environ['TZ'] = 'UTM'
time.tzset()

PROG_VERSION = '2019.058'
logging.basicConfig()
LOGGER = logging.getLogger(__name__)


#
# To hold table rows and keys
#
class Rows_Keys (object):
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


class Das_Groups (object):
    __slots__ = ('das', 'node')

    def __init__(self, das=None, node=None):
        self.das = das
        self.node = node


class FixNumSamples():
    #
    # These are to hold different parts of the meta-data
    #
    def __init__(self):
        # /Experiment_g/Experiment_t
        self.EXPERIMENT_T = None
        # /Experiment_g/Sorts_g/Event_t
        self.EVENT_T = None
        # /Experiment_g/Sorts_g/Offset_t
        self.OFFSET_T = None
        # /Experiment_g/Sorts_g/Sort_t
        self.SORT_T = None
        # /Experiment_g/Responses_g/Response_t
        self.RESPONSE_T = None
        # /Experiment_g/Sorts_g/Array_t_[nnn]
        self.ARRAY_T = {}
        # /Experiment_g/Receivers_g/Das_g_[sn]/Das_t (keyed on DAS)
        self.DAS_T = {}
        # /Experiment_g/Receivers_g/Das_g_[sn]/Receiver_t (keyed on DAS)
        self.RECEIVER_T = {}
        # /Experiment_g/Receivers_g/Das_g_[sn]/SOH_a_[n]
        # (keyed on DAS then by SOH_a_[n] name)
        self.SOH_A = {}
        # A list of Das_Groups that refers to Das_g_[sn]'s
        self.DASS = []

    #
    # Read Command line arguments
    #
    def get_args(self):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter)

        parser.usage = ("fix_num_samples --nickname ph5-file-prefix "
                        "[--path path-to-ph5-files]")

        parser.description = (
            "Correct number of samples in time series array\n"
            "to work around a bug in certain data loggers.\n"
            "Set sample_count_i in Das_t based on length\n"
            "of data array. Writes kef file, 1 per DAS.\n\n"
            "Version: {0}".format(PROG_VERSION))

        parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                            help="The ph5 file prefix (experiment nickname).",
                            metavar="ph5_file_prefix", required=True)

        parser.add_argument("-p", "--path", dest="ph5_path",
                            help=("Path to ph5 files. Default to current "
                                  "directory."),
                            metavar="ph5_path", default=".")

        parser.add_argument("-c", "--check", dest="check",
                            action="store_true", default=False)

        parser.add_argument("-d", dest="debug", action="store_true",
                            default=False)

        args = parser.parse_args()

        self.CHECK = args.check
        PH5 = args.ph5_file_prefix
        self.PATH = args.ph5_path
        self.DEBUG = args.debug
        self.PH5 = os.path.join(self.PATH, PH5)

        if not os.path.exists(self.PH5) \
           and not os.path.exists(self.PH5 + '.ph5'):
            raise Exception("{0} does not exist!".format(PH5))

    #
    # Initialize ph5 file
    #
    def initialize_ph5(self, editmode=False):
        '''   Initialize the ph5 file   '''
        self.EX = experiment.ExperimentGroup(self.PATH, self.PH5)
        self.EX.ph5open(editmode)
        self.EX.initgroup()

    #
    # Print Rows_Keys
    #
    def debug_print(self, a):
        i = 1
        # Loop through table rows
        for r in a.rows:
            # Print line number
            print "%d) " % i,
            i += 1
            # Loop through each row column and print
            for k in a.keys:
                print k, "=>", r[k], ",",
            print

    def read_experiment_table(self):
        '''   Read /Experiment_g/Experiment_t   '''

        exp, exp_keys = self.EX.read_experiment()

        rowskeys = Rows_Keys(exp, exp_keys)

        self.EXPERIMENT_T = rowskeys

    def read_event_table(self):
        '''   Read /Experiment_g/Sorts_g/Event_t   '''
        events, event_keys = self.EX.ph5_g_sorts.read_events()

        rowskeys = Rows_Keys(events, event_keys)

        self.EVENT_T = rowskeys

    def read_offset_table(self):
        '''   Read /Experinent_t/Sorts_g/Offset_t   '''

        offsets, offset_keys = self.EX.ph5_g_sorts.read_offsets()

        rowskeys = Rows_Keys(offsets, offset_keys)

        self.OFFSET_T = rowskeys

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

    def read_response_table(self):
        '''   Read /Experiment_g/Respones_g/Response_t   '''
        response, response_keys = self.EX.ph5_g_responses.read_responses()

        rowskeys = Rows_Keys(response, response_keys)

        self.RESPONSE_T = rowskeys

    #
    # Print Rows_Keys
    #
    def table_print(self, t, a, d):
        outfile = "Das_t_%s.kef" % d
        print outfile
        fh = open(outfile, 'w')
        i = 0
        # Loop through table rows
        for r in a.rows:
            i += 1
            fh.write("# Table row %d\n" % i)
            # Print table name
            fh.write("%s\n" % t)
            # Loop through each row column and print
            for k in a.keys:
                fh.write("\t%s = %s\n" % (k, str(r[k])))

        fh.close()

    def walk_das_tables(self):
        dass = sorted(self.DAS_T.keys())
        for d in dass:
            t = self.DAS_T[d]
            path = '/Experiment_g/Receivers_g/Das_g_' + d
            dtable = '/Experiment_g/Receivers_g/Das_g_' + d + '/Das_t'
            doprint = False
            for r in t.rows:
                # Only update iff 0
                if self.CHECK:
                    if r['sample_count_i'] != 0:
                        continue

                doprint = True
                array_name = r['array_name_data_a'].strip()
                array_node = self.EX.ph5.get_node(
                    path, name=array_name, classname='Array')
                r['sample_count_i'] = array_node.nrows

            if doprint:
                self.table_print(dtable + ":Update:array_name_data_a", t, d)

    def read_receivers(self):
        '''   Read tables and arrays (except wiggles) in Das_g_[sn]   '''
        # Get references for all das groups keyed on das
        dasGroups = self.EX.ph5_g_receivers.alldas_g()
        dass = sorted(dasGroups.keys())
        # Sort by das sn
        for d in dass:
            # Get node reference
            g = dasGroups[d]
            dg = Das_Groups(d, g)
            # Save a master list for later
            self.DASS.append(dg)

            # Set the current das group
            self.EX.ph5_g_receivers.setcurrent(g)

            # Read /Experiment_g/Receivers_g/Das_g_[sn]/Das_t
            das, das_keys = self.EX.ph5_g_receivers.read_das()
            rowskeys = Rows_Keys(das, das_keys)
            self.DAS_T[d] = rowskeys

    def read_data(self):
        '''   Read all of the wiggles and calculate standard
              deviation of trace data   '''

        # We use this to build up a list of trace standard deviations keyed by
        # epoch ;^)
        tmp = {}
        # How many points do we read?
        pts = 0
        # Loop through each Das_g_[sn]
        for dg in self.DASS:
            das = dg.das
            node = dg.node

            # Set current das
            self.EX.ph5_g_receivers.setcurrent(node)

            rowskeys = self.DAS_T[das]
            # Loop through each line in Das_t
            for r in rowskeys.rows:
                # Get data array name for this trace
                data_array_name = r['array_name_data_a'].strip()
                # Ascii start time
                r['time/ascii_s'].strip()
                # Epoch start time
                epoch = r['time/epoch_l']
                # Make sure it points to a list
                if epoch not in tmp:
                    tmp[epoch] = []
                # Get node reference to trace array
                trace_ref = \
                    self.EX.ph5_g_receivers.find_trace_ref(data_array_name)
                # Read the trace
                data = self.EX.ph5_g_receivers.read_trace(trace_ref)
                # Update total points
                pts += len(data)
                # Get standard deviation for this data trace spectra and save
                # it in tmp
                std = data.std()
                tmp[epoch].append(std)

        return tmp, pts


def main():
    fix = FixNumSamples()
    # Get program arguments
    try:
        fix.get_args()
    except Exception, err_msg:
        LOGGER.error(err_msg)
        return 1
    # Initialize ph5 file
    fix.initialize_ph5()
    # Read tables in Das_g_[sn]
    fix.read_receivers()
    fix.walk_das_tables()
    if fix.DEBUG:
        LOGGER.debug("SOH_A: {0}".format(fix.SOH_A))
        LOGGER.debug("DAS_T: {0}".format(fix.DAS_T))
        LOGGER.debug("RECEIVER_T: {0}".format(fix.RECEIVER_T))
        pass

    fix.EX.ph5close()
    print 'Done...'


if __name__ == "__main__":
    main()
