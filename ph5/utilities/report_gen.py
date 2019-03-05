#!/usr/bin/env pnpython2

#
# Generate the reports "data_description.txt" and "data_report_key.txt"
#

import argparse
import os
import os.path
import logging
import time

# This provides the base functionality
from ph5.core import experiment
from ph5.core import timedoy as tdoy

# Timeseries are stored as numpy arrays

PROG_VERSION = '2019.057'
LOGGER = logging.getLogger(__name__)


#
# To hold DAS sn and references to Das_g_[sn]
#


class Das_Groups(object):
    __slots__ = ('das', 'node')

    def __init__(self, das=None, node=None):
        self.das = das
        self.node = node


class Offset_Azimuth(object):
    __slots__ = ('offset', 'azimuth')

    def __init__(self, offset=None, azimuth=None):
        self.offset = offset
        self.azimuth = azimuth
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


class ReportGen():
    def __init__(self):
        #
        # These are to hold different parts of the meta-data
        #
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
        self.DASS = {}  # NOQA

        os.environ['TZ'] = 'UTM'
        time.tzset()

    #
    # Read Command line arguments
    #
    def get_args(self):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter)

        parser.usage = "report_gen --nickname=ph5-file-prefix options"

        parser.description = ("Generate data_description.txt and/or "
                              "data_request_key.txt.")

        parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                            help="The ph5 file prefix (experiment nickname).",
                            metavar="ph5_file_prefix", required=True)

        parser.add_argument("-p", "--path", dest="ph5_path",
                            help=("Path to ph5 files. Default to current "
                                  "directory."),
                            metavar="ph5_path", default=".")

        parser.add_argument("-k", "--key", dest="key_gen",
                            help="Write data_request_key.txt.",
                            action="store_true", default=False)

        parser.add_argument("-d", "--description", dest="des_gen",
                            help="Write data_description.txt.",
                            action="store_true", default=False)

        parser.add_argument("--debug", dest="debug",
                            action="store_true", default=False)

        args = parser.parse_args()

        self.PH5 = args.ph5_file_prefix
        self.PATH = args.ph5_path
        self.DEBUG = args.debug
        self.KEY_GEN = args.key_gen
        self.DES_GEN = args.des_gen
        if self.KEY_GEN:
            LOGGER.warning("Generation of data_request_key.txt is no "
                           "longer needed.")

        if self.KEY_GEN is False and self.DES_GEN is False:
            raise Exception(
                "Either --key or --description option is required.")

        if self.PH5 is None:
            raise Exception(
                "Error: Missing required option --nickname. Try --help")

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
            i += 1
            # Loop through each row column and print
            for k in a.keys:
                print k, "=>", r[k], ",",
            print

    def info_print(self):
        print "#\n#\t%s\tph5 version: %s\n#" % (
            time.ctime(time.time()), self.EX.version())

    #
    # Print Rows_Keys
    #
    def table_print(self, t, a):
        i = 0
        # Loop through table rows
        for r in a.rows:
            i += 1
            print "#   Table row %d" % i
            # Print table name
            print t
            # Loop through each row column and print
            for k in a.keys:
                print "\t", k, "=", r[k]

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

    # NOT USED
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

            # Read /Experiment_g/Receivers_g/Receiver_t
            receiver, receiver_keys = self.EX.ph5_g_receivers.read_receiver()
            rowskeys = Rows_Keys(receiver, receiver_keys)
            self.RECEIVER_T[d] = rowskeys

            # Read SOH file(s) for this das
            self.SOH_A[d] = self.EX.ph5_g_receivers.read_soh()

    def read_das_groups(self):
        '''   Get das groups   '''

        # Get references for all das groups keyed on das
        return self.EX.ph5_g_receivers.alldas_g()

    def read_das_table(self, das):
        if das in self.DASS:
            self.EX.ph5_g_receivers.setcurrent(self.DASS[das])
            das_r, das_keys = self.EX.ph5_g_receivers.read_das()
            return Rows_Keys(das_r, das_keys)
        else:
            return None

    def strip_offset_t(self):
        if self.STATION_ID is None and self.EVENT_ID is None:
            return

        tmp = []
        for o in self.OFFSET_T.rows:
            event_id = o['event_id_s']
            receiver_id = o['receiver_id_s']
            station_id = o['station_ids_s']

            if self.STATION_ID is not None and self.EVENT_ID is not None:
                if event_id == self.EVENT_ID \
                   and receiver_id == self.STATION_ID:
                    tmp.append(o)
            elif self.STATION_ID is None:
                if event_id == self.EVENT_ID:
                    tmp.append(o)
            elif self.EVENT_ID is None:
                if station_id == self.STATION_ID:
                    tmp.append(o)

        if tmp != []:
            self.OFFSET_T = Rows_Keys(tmp, self.OFFSET_T.keys)

    def strip_array_t(self):
        if self.STATION_ID is None and self.DAS_SN is None:
            return
        if self.ARRAY_T:
            keys = self.ARRAY_T.keys()
            for k in keys:
                tmp = []
                for a in self.ARRAY_T[k].rows:
                    station_id = a['id_s']
                    das_sn = a['das/serial_number_s']
                    if self.STATION_ID is not None and self.DAS_SN is not None:
                        if station_id == self.STATION_ID \
                           and das_sn == self.DAS_SN:
                            tmp.append(a)
                    elif self.STATION_ID is None:
                        if das_sn == self.DAS_SN:
                            tmp.append(a)
                    elif self.DAS_SN is None:
                        if station_id == self.STATION_ID:
                            tmp.append(a)

                if tmp != []:
                    self.ARRAY_T[k] = Rows_Keys(tmp, self.ARRAY_T[k].keys)

    """
    def offset_t_sort(self, a, b):
        return cmp(a['offset/value_d'], b['offset/value_d'])

    def order_station_by_offset(self):

        self.SORTED_OFFSET = self.OFFSET_T.rows

        for o in self.SORTED_OFFSET:
            if o['azimuth/value_f'] < 0:
                o['offset/value_d'] = o['offset/value_d'] * -1.0

        self.SORTED_OFFSET.sort(offset_t_sort)
    """

    def key_array(self, array):
        ka = {}
        for a in array.rows:
            ka[a['id_s']] = a

        return ka

    def build_array_from_offset(self, array):
        sorted_array = []

        keyed_array = self.key_array(array)

        for o in self.SORTED_OFFSET:
            station = o['receiver_id_s']
            sorted_array.append(keyed_array[station])

        return Rows_Keys(sorted_array, array.keys)

    def array_start_stop(self, ar):
        start = 2145916800
        stop = 0
        for a in ar.rows:
            if a['deploy_time/epoch_l'] < start:
                start = a['deploy_time/epoch_l']

            if a['pickup_time/epoch_l'] > stop:
                stop = a['pickup_time/epoch_l']

        return start, stop

    def get_sample_rate(self, a, start, stop):
        if self.ARRAY_T:
            Array_t = self.ARRAY_T[a].rows
            for array_t in Array_t:
                das = array_t['das/serial_number_s']

                Das_t = self.read_das_table(das)
                if Das_t is None:
                    continue
                for das_t in Das_t.rows:
                    das_start = das_t['time/epoch_l']
                    das_stop = das_start + das_t['sample_count_i'] / (
                            das_t['sample_rate_i'] /
                            float(das_t['sample_rate_multiplier_i']))

                    # Start contained
                    if das_start >= start and das_start <= stop:
                        return int(das_t['sample_rate_i'] /
                                   float(das_t['sample_rate_multiplier_i']))

                    # Stop contained
                    if das_stop >= start and das_stop <= stop:
                        return int(das_t['sample_rate_i'] /
                                   float(das_t['sample_rate_multiplier_i']))

        return 0

    def write_key_report(self):
        try:
            fh = open("data_request_key.txt", "w+")
        except BaseException:
            LOGGER.error("Failed to open \"data_request_key.txt\".")
            return

        A = {}
        if self.ARRAY_T:
            for k in self.ARRAY_T.keys():
                a = self.ARRAY_T[k]
                start, stop = self.array_start_stop(a)
                array_i = int(k[-3:])
                A[array_i] = (start, stop)
        fh.write("shot|time|arrays\n")
        array_i_keys = A.keys()
        if self.EVENT_T:
            for e in self.EVENT_T.rows:
                arrays = ''
                for i in array_i_keys:
                    start, stop = A[i]
                    if start == 0:
                        arrays = arrays + "%d," % i
                    elif int(e['time/epoch_l']) >= start and int(
                            e['time/epoch_l']) <= stop:
                        arrays = arrays + "%d," % i

                ttuple = time.gmtime(int(e['time/epoch_l']))
                pictime = "%4d:%03d:%02d:%02d:%02d" % (ttuple[0],
                                                       ttuple[7],
                                                       ttuple[3],
                                                       ttuple[4],
                                                       ttuple[5])
                fh.write("%s|%s|%s\n" % (e['id_s'],
                                         pictime,
                                         arrays[:-1]))

        fh.write(
            "request key|start time|length in seconds|array name|"
            "description\n")
        i = 1
        for s in self.SORT_T.rows:
            secs = int(s['end_time/epoch_l']) - int(s['start_time/epoch_l'])
            ttuple = time.gmtime(int(s['start_time/epoch_l']))
            pictime = "%4d:%03d:%02d:%02d:%02d" % (ttuple[0],
                                                   ttuple[7],
                                                   ttuple[3],
                                                   ttuple[4],
                                                   ttuple[5])
            fh.write("%d|%s|%5.3f|%s|%s\n" % (i,
                                              pictime,
                                              float(secs),
                                              s['array_name_s'],
                                              s['description_s']))

            i += 1

        fh.close()

    def write_des_report(self):
        A = {}
        if self.ARRAY_T:
            for k in self.ARRAY_T.keys():
                a = self.ARRAY_T[k]
                start, stop = self.array_start_stop(a)
                array_i = int(k[-3:])
                A[array_i] = (start, stop)

        fh = open("data_description.txt", "w+")

        for e in self.EXPERIMENT_T.rows:
            pass

        fh.write("\t\t\t%s\n\n%s\n\n%s\n\n%s\n\n%s\n\n" %
                 (e['nickname_s'],
                  e['longname_s'],
                  e['PIs_s'],
                  e['institutions_s'],
                  e['summary_paragraph_s']))

        fh.write(
            "***   Please check the following lines and remove this line "
            "before submission to DMC.   ***\n")
        fh.write("\t\t\tShots\n\n")
        fh.write(
            "shot id\ttime    lat      lon         elev (m) "
            "size (kg) depth (m)\n")
        fh.write("-" * 85)
        fh.write('\n')
        if self.EVENT_T:
            for e in self.EVENT_T.rows:
                ttuple = time.gmtime(int(e['time/epoch_l']))
                secs = ttuple[5] + (e['time/micro_seconds_i'] / 1000000.)
                pictime = "%4d:%03d:%02d:%02d:%06.3f" % (ttuple[0],
                                                         ttuple[7],
                                                         ttuple[3],
                                                         ttuple[4],
                                                         secs)
                fh.write("%-5s\t%s %12.6f %12.6f %9.3f %9.3f %9.3f\n" %
                         (e['id_s'],
                          pictime,
                          e['location/Y/value_d'],
                          e['location/X/value_d'],
                          e['location/Z/value_d'],
                          e['size/value_d'],
                          e['depth/value_d']))

        fh.write("\n\t\t\tArrays\n\n")

        arrays = sorted(self.ARRAY_T.keys())
        if self.ARRAY_T:
            for a in arrays:
                start, stop = A[int(a[-3:])]
                fh.write(
                    "***   Please check the following lines and remove this line\
                    before submission to DMC.   ***\n")
                sample_rate = self.get_sample_rate(a, start, stop)

                fh.write("\nArray: %s\n" % a[-3:])
                # Sample rate:
                fh.write("\t\tSample Rate: %d sps\n" % sample_rate)
                # Sensor type
                # Deployment time
                fh.write("\t\tDeployment Time: %s\n" %
                         tdoy.epoch2passcal(start)[:-10])
                # Pickup time
                fh.write("\t\tPickup Time:     %s\n" %
                         tdoy.epoch2passcal(stop)[:-10])
                fh.write("\t\tComponents: 1 => Z, 2 => N, 3 => E\n\n")
                fh.write(
                    "station\t"
                    "das      lat        lon        elev (m)    component\n")
                fh.write('-' * 65)
                fh.write('\n')
                for e in self.ARRAY_T[a].rows:
                    fh.write("%-5s\t%s %12.6f %12.6f %9.3f\t%d\n" %
                             (e['id_s'],
                              e['das/serial_number_s'],
                              float(e['location/Y/value_d']),
                              float(e['location/X/value_d']),
                              float(e['location/Z/value_d']),
                              e['channel_number_i']))

            # Need to write sorts here!

            fh.close()


def main():
    reportGen = ReportGen()
    try:
        reportGen.get_args()
    except Exception as err:
        LOGGER.error(err)

    LOGGER.info("Opening...")

    reportGen.initialize_ph5()

    try:
        reportGen.read_sort_arrays()
        reportGen.read_event_table()
        reportGen.DASS = reportGen.read_das_groups()
    except Exception as err:
        LOGGER.warning(err)

    if reportGen.KEY_GEN is True:
        LOGGER.info("Writing data key report...")
        reportGen.read_sort_table()
        reportGen.write_key_report()

    if reportGen.DES_GEN is True:
        LOGGER.info("Writing data description report...")
        reportGen.read_experiment_table()
        reportGen.write_des_report()

    reportGen.EX.ph5close()
    LOGGER.info("Done..")


if __name__ == '__main__':
    main()
