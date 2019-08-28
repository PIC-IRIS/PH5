#!/usr/bin/env pnpython4
# -*- coding: iso-8859-15 -*-
#
#   Read Fairfield SEG-D (Version 1.6) from the Sweetwater experiment.
#   Write PH5
#
#   Steve Azevedo, May 2014
#   Modified to read SEG-D from 3C's, July 2016
#

import os
import sys
import logging
import time
import json
import re
from math import modf
from ph5.core import experiment, columns, segdreader
from ph5 import LOGGING_FORMAT
from pyproj import Proj, transform

PROG_VERSION = "2019.78"
LOGGER = logging.getLogger(__name__)

MAX_PH5_BYTES = 1073741824 * 100.  # 100 GB (1024 X 1024 X 1024 X 2)

os.environ['TZ'] = 'GMT'
time.tzset()

#   RE for mini files
miniPH5RE = re.compile(r".*miniPH5_(\d\d\d\d\d)\.ph5")

# LSB = 6.402437066e-6   #   From Malcolm UCSD
LSB00 = 2500. / (2 ** 23)  # 0dB
LSB12 = 625. / (2 ** 23)  # 12dB
LSB24 = 156. / (2 ** 23)  # 24dB
LSB36 = 39. / (2 ** 23)  # 36dB = 39mV full scale

LSB_MAP = {36: LSB36, 24: LSB24, 12: LSB12, 0: LSB00}

#   Manufacturers codes
FAIRFIELD = 20
OTHER = 0


#
#   To hold table rows and keys
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


class Index_t_Info(object):
    __slots__ = ('das', 'ph5file', 'ph5path', 'startepoch', 'stopepoch')

    def __init__(self, das, ph5file, ph5path, startepoch, stopepoch):
        self.das = das
        self.ph5file = ph5file
        self.ph5path = ph5path
        self.startepoch = startepoch
        self.stopepoch = stopepoch


class Resp(object):
    __slots__ = ('lines', 'keys', 't')

    def __init__(self, t):
        self.t = t
        self.update()

    def update(self):
        self.lines, self.keys = self.t.read_responses()

    def match(self, bw, gain):
        # print self.lines
        for l in self.lines:
            if l['bit_weight/value_d'] == bw and l['gain/value_i'] == gain:
                return l['n_i']

        return -1

    def next_i(self):
        return len(self.lines)


class Trace(object):
    __slots__ = ("trace", "headers")

    def __init__(self, trace, headers):
        self.trace = trace
        self.headers = headers


class SEGD2PH5:
    def __init__(self):
        self.LSB = LSB36
        self.TSP = False
        self.FIRST_MINI = 1
        self.UTM = 0
        self.LAT = None
        self.LON = None
        self.MANUFACTURERS_CODE = FAIRFIELD

        self.DAS_INFO = {}
        self.MAP_INFO = {}
        #   Current raw file processing
        self.F = None
        self.ARRAY_T = {}
        self.APPEND = 1  # Number of SEG-D events to append to make 1 ph5 event

    def read_infile(self, infile):
        '''   Read list of input SEG-D files from a file   '''

        def fn_sort(a, b):
            # print os.path.basename (a), os.path.basename (b)
            return cmp(os.path.basename(a), os.path.basename(b))

        try:
            fh = file(infile)
        except BaseException:
            sys.stderr.write("Warning: Failed to open %s\n" % infile)
            return

        while True:
            line = fh.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            if line[0] == '#':
                continue
            self.FILES.append(line)

        self.FILES.sort(fn_sort)

    def get_args(self):

        from optparse import OptionParser
        oparser = OptionParser()

        oparser.usage = "Version: {0} Usage: segd2ph5 [options]".format(
            PROG_VERSION)

        oparser.add_option(
            "-r", "--raw", dest="rawfile",
            help="Fairfield SEG-D v1.6 file.", metavar="raw_file")

        oparser.add_option(
            "-f", action="store", dest="infile", type="string",
            help="File containing list of Fairfield SEG-D v1.6 file names.")

        oparser.add_option(
            "-n", "--nickname", dest="outfile",
            help="The ph5 file prefix (experiment nick name).",
            metavar="output_file_prefix")

        oparser.add_option(
            "-U", "--UTM", dest="utm_zone",
            help="Locations in SEG-D file are UTM, --UTM=utmzone.\
            Zone number and N or S designation eg 13N",
            type='str', default=0, metavar="utm_zone")

        oparser.add_option(
            "-T", "--TSPF", dest="texas_spc",
            help="Locations are in texas state plane coordinates.",
            action='store_true', default=False)

        oparser.add_option(
            "-M", "--num_mini", dest="num_mini",
            help="Create a given number of miniPH5 files.",
            metavar="num_mini", type='int', default=None)

        oparser.add_option(
            "-S", "--first_mini", dest="first_mini",
            help="The index of the first miniPH5_xxxxx.ph5 file.",
            metavar="first_mini", type='int', default=1)

        oparser.add_option(
            "-c", "--combine", dest="combine",
            help="Combine this number if SEG-D traces to one PH5 trace.",
            metavar="combine", type='int', default=self.APPEND)

        oparser.add_option(
            "-E", "--allevents", action="store_true", dest="all_events",
            default=False, metavar="all_events")

        oparser.add_option(
            "--manufacturers_code", dest="manufacturers_code",
            help="Manufacturers code. Defaults to 20 for Fairfield.\
            Most likely will not work for SEG-D written by other data\
            loggers.",
            type='int', default=FAIRFIELD)

        options, args = oparser.parse_args()

        self.FILES = []
        self.PH5 = None

        self.EVERY = options.all_events
        self.NUM_MINI = options.num_mini
        self.FIRST_MINI = options.first_mini
        self.UTM = options.utm_zone
        self.TSP = options.texas_spc
        self.APPEND = options.combine
        self.MANUFACTURERS_CODE = options.manufacturers_code

        if options.infile is not None:
            self.read_infile(options.infile)

        elif options.rawfile is not None:
            self.FILES.append(options.rawfile)

        if len(self.FILES) == 0:
            sys.stderr.write("Error: No input file given.\n")
            sys.exit()

        #   Set output file
        if options.outfile is not None:
            self.PH5 = options.outfile
        else:
            sys.stderr.write("Error: No outfile (PH5) given.\n")
            sys.exit()

        # Write log to file
        ch = logging.FileHandler(os.path.join('.', "segd2ph5.log"))
        ch.setLevel(logging.INFO)
        # Add formatter
        formatter = logging.Formatter(LOGGING_FORMAT)
        ch.setFormatter(formatter)
        LOGGER.addHandler(ch)

        #   Need to process in order: R309_674.1.0.rg16, 309 == line,
        #   674 = receiver point, 1 = first file
        #   Sorted where the file list is read...
        # self.FILES.sort ()

    def initialize_ph5(self):
        self.EX = experiment.ExperimentGroup(nickname=self.PH5)
        EDIT = True
        self.EX.ph5open(EDIT)
        self.EX.initgroup()

    def openPH5(self, filename):
        '''   Open PH5 file, miniPH5_xxxxx.ph5   '''
        try:
            if self.EXREC.ph5.isopen:
                if self.EXREC.filename != filename:
                    self.EXREC.ph5close()
                else:
                    return self.EXREC
        except BaseException:
            pass
        # sys.stderr.write ("***   Opening: {0} ".format (filename))
        exrec = experiment.ExperimentGroup(nickname=filename)
        exrec.ph5open(True)
        exrec.initgroup()
        return exrec

    def update_index_t_info(self, starttime, samples, sps):
        '''   Update info that gets saved in Index_t   '''

        ph5file = self.EXREC.filename
        ph5path = '/Experiment_g/Receivers_g/' + \
                  self.EXREC.ph5_g_receivers.current_g_das._v_name
        ph5map = '/Experiment_g/Maps_g/' + \
            self.EXREC.ph5_g_maps.current_g_das._v_name
        das = ph5path[32:]
        stoptime = starttime + (float(samples) / float(sps))
        di = Index_t_Info(das, ph5file, ph5path, starttime, stoptime)
        dm = Index_t_Info(das, ph5file, ph5map, starttime, stoptime)
        if das not in self.DAS_INFO:
            self.DAS_INFO[das] = []
            self.MAP_INFO[das] = []

        self.DAS_INFO[das].append(di)
        self.MAP_INFO[das].append(dm)
        LOGGER.info(
            "DAS: {0} File: {1} First Sample: {2} Last Sample: {3}".format(
                das, ph5file, time.ctime(starttime), time.ctime(stoptime)))

    def update_external_references(self):
        '''   Update external references in master.ph5 to
              miniPH5 files in Receivers_t    '''

        # sys.stderr.write ("Updating external references...\n");
        #  sys.stderr.flush ()
        LOGGER.info("Updating external references...")
        n = 0
        for i in self.INDEX_T_DAS.rows:
            external_file = i['external_file_name_s'][2:]
            external_path = i['hdf5_path_s']
            i['serial_number_s']
            target = external_file + ':' + external_path
            external_group = external_path.split('/')[3]
            # print external_file, external_path, das, target, external_group

            #   Nuke old node
            try:
                group_node = self.EX.ph5.get_node(external_path)
                group_node.remove()
            except Exception as e:
                pass
                # print "DAS nuke ", e.message
            #   Re-create node
            try:
                self.EX.ph5.create_external_link(
                    '/Experiment_g/Receivers_g', external_group, target)
                n += 1
            except Exception as e:
                # pass
                sys.stderr.write("{0}\n".format(e.message))

            # sys.exit ()
        # sys.stderr.write ("done, {0} das nodes recreated.\n".format (n))

        LOGGER.info("done, {0} das nodes recreated.\n".format(n))

        n = 0
        for i in self.INDEX_T_MAP.rows:
            #   XXX
            # keys = i.keys ()
            # keys.sort ()
            # for k in keys :
            # print k, i[k]

            external_file = i['external_file_name_s'][2:]
            external_path = i['hdf5_path_s']
            i['serial_number_s']
            target = external_file + ':' + external_path
            external_group = external_path.split('/')[3]
            # print external_file, external_path, das, target, external_group

            #   Nuke old node
            try:
                group_node = self.EX.ph5.get_node(external_path)
                group_node.remove()
            except Exception as e:
                pass
                # print "MAP nuke ", e.message

            #   Re-create node
            try:
                self.EX.ph5.create_external_link(
                    '/Experiment_g/Maps_g', external_group, target)
                n += 1
            except Exception as e:
                # pass
                sys.stderr.write("{0}\n".format(e.message))

            # sys.exit ()
        # sys.stderr.write ("done, {0} map nodes recreated.\n".format (n))
        LOGGER.info("done, {0} map nodes recreated.\n".format(n))

    def get_current_data_only(self, size_of_data, das=None):
        '''   Return opened file handle for data only PH5 file that will be
              less than MAX_PH5_BYTES after raw data is added to it.
        '''

        def sstripp(s):
            s = s.replace('.ph5', '')
            s = s.replace('./', '')
            return s

        def smallest():
            '''   Return the name of the smallest miniPH5_xxxxx.ph5   '''
            minifiles = filter(miniPH5RE.match, os.listdir('.'))

            tiny = minifiles[0]
            for f in minifiles:
                if os.path.getsize(f) < os.path.getsize(tiny):
                    tiny = f

            return tiny

        das = str(das)
        newestfile = ''
        #   Get the most recent data only PH5 file or match DAS serialnumber
        n = 0
        for index_t in self.INDEX_T_DAS.rows:
            #   This DAS already exists in a ph5 file
            if index_t['serial_number_s'] == das:
                newestfile = sstripp(index_t['external_file_name_s'])
                return self.openPH5(newestfile)
            #   miniPH5_xxxxx.ph5 with largest xxxxx
            mh = miniPH5RE.match(index_t['external_file_name_s'])
            if n < int(mh.groups()[0]):
                newestfile = sstripp(index_t['external_file_name_s'])
                n = int(mh.groups()[0])

        if not newestfile:
            #   This is the first file added
            return self.openPH5('miniPH5_{0:05d}'.format(self.FIRST_MINI))

        size_of_exrec = os.path.getsize(newestfile + '.ph5')
        # print size_of_data, size_of_exrec, size_of_data + size_of_exrec,
        # MAX_PH5_BYTES
        if self.NUM_MINI is not None:
            fm = self.FIRST_MINI - 1
            if (int(newestfile[8:13]) - fm) < self.NUM_MINI:
                newestfile = "miniPH5_{0:05d}".format(
                    int(newestfile[8:13]) + 1)
            else:
                small = sstripp(smallest())
                return self.openPH5(small)

        elif (size_of_data + size_of_exrec) > MAX_PH5_BYTES:
            newestfile = "miniPH5_{0:05d}".format(int(newestfile[8:13]) + 1)

        return self.openPH5(newestfile)

    def getLOG(self):
        '''   Create a open a new and unique header file under
        Maps_g/Das_g_
              /Sta_g_
              /Evt_g_
                     /Hdr_a_
        '''
        current_das = self.EXREC.ph5_g_receivers.get_das_name()
        g = self.EXREC.ph5_g_maps.newdas('Das_g_', current_das)
        self.EXREC.ph5_g_maps.setcurrent(g)
        try:
            name = self.EXREC.ph5_g_maps.nextarray('Hdr_a_')
        except TypeError:
            return None

        log_array = self.EXREC.ph5_g_maps.newearray(
            name, description="SEG-D header entries: {0}".format(self.Das))

        return log_array, name

    def get_true_channel(self, rh, th):
        #   Find channel by mapping to streamer_cable_number

        if rh.channel_set_to_streamer_cable_map[th.trace_header.channel_set]\
           == 0:
            true_channel = th.trace_header.channel_set
        else:
            true_channel = rh.channel_set_to_streamer_cable_map[
                th.trace_header.channel_set]
        return true_channel

    def process_das(self, rh, th, tr):
        '''
        '''
        p_das_t = {}
        '''  Das_t
                        receiver_table_n_i
                        response_table_n_i
                        time_table_n_i
                        time/
                            type_s
                            epoch_l
                            ascii_s
                            micro_seconds_i
                        event_number_i
                        channel_number_i
                        sample_rate_i
                        sample_rate_multiplier_i
                        sample_count_i
                        stream_number_i
                        raw_file_name_s
                        array_name_data_a
                        array_name_SOH_a
                        array_name_event_a
                        array_name_log_a
                '''

        #   Check to see if group exists for this das, if not build it
        das_g, das_t, receiver_t, time_t = self.EXREC.ph5_g_receivers.newdas(
            str(self.Das))
        #   Build maps group (XXX)
        self.EXREC.ph5_g_maps.newdas('Das_g_', str(self.Das))
        if rh.general_header_block_1.chan_sets_per_scan == 1:
            #   Single channel
            p_das_t['receiver_table_n_i'] = 0  # 0 -> Z
        elif rh.general_header_block_1.chan_sets_per_scan >= 3:
            # 1 (N node) -> 1 (N PH5), 2 (E Node)-> 2 (E PH5), 3 (Z Node) -> 0
            # (Z PH5)
            M = {1: 1, 2: 2, 3: 0}
            p_das_t['receiver_table_n_i'] = M[self.get_true_channel(rh, th)]
        else:
            p_das_t['receiver_table_n_i'] = 0  # 0 -> Z
            LOGGER.warning(
                "Header channel set: {0}. Check Receiver_t entries!".format(
                    th.trace_header.channel_set))

        p_das_t['response_table_n_i'] = None
        p_das_t['time_table_n_i'] = 0
        p_das_t['time/type_s'] = 'BOTH'
        # trace_epoch = th.trace_header_N[2].gps_tim1 * 4294967296 +\
        #  th.trace_header_N[2].gps_tim2
        try:
            trace_epoch = th.trace_header_N[2].shot_epoch
        except Exception as e:
            LOGGER.warning("Failed to read shot epoch: {0}.".format(e.message))
            trace_epoch = 0.

        f, i = modf(trace_epoch / 1000000.)
        p_das_t['time/epoch_l'] = int(i)
        p_das_t['time/ascii_s'] = time.ctime(p_das_t['time/epoch_l'])
        p_das_t['time/micro_seconds_i'] = int(f * 1000000.)
        p_das_t['event_number_i'] = th.trace_header_N[1].shot_point
        p_das_t['channel_number_i'] = self.get_true_channel(rh, th)
        p_das_t['sample_rate_i'] = self.SD.sample_rate
        p_das_t['sample_rate_multiplier_i'] = 1
        p_das_t['sample_count_i'] = len(tr)
        p_das_t['stream_number_i'] = 1
        p_das_t['raw_file_name_s'] = os.path.basename(self.SD.name())
        p_das_t['array_name_data_a'] = self.EXREC.ph5_g_receivers.nextarray(
            'Data_a_')
        # p_das_t['array_name_SOH_a'] = None
        # p_das_t['array_name_event_a'] = None
        # p_das_t['array_name_log_a'] = None
        p_response_t = {}
        '''
                    n_i
                    gain/
                        units_s
                        value_i
                    bit_weight/
                        units_s
                        value_d
                    response_file_a
                '''
        try:
            self.LSB = LSB_MAP[th.trace_header_N[3].preamp_gain_db]
            n_i = self.RESP.match(
                self.LSB, th.trace_header_N[3].preamp_gain_db)
        except Exception as e:
            n_i = 0
        p_response_t['gain/units_s'] = 'dB'
        try:
            p_response_t['gain/value_i'] = th.trace_header_N[3].preamp_gain_db
        except Exception as e:
            LOGGER.warning(
                "Failed to read trace pre amp gain: {0}.".format(e.message))
            p_response_t['gain/value_i'] = 0.
            p_response_t['gain/units_s'] = 'Unknown'

        p_response_t['bit_weight/units_s'] = 'mV/count'
        p_response_t['bit_weight/value_d'] = self.LSB
        if n_i < 0:
            n_i = self.RESP.next_i()
            p_response_t['n_i'] = n_i
            self.EX.ph5_g_responses.populateResponse_t(p_response_t)
            self.RESP.update()
        p_das_t['response_table_n_i'] = n_i
        self.EXREC.ph5_g_receivers.populateDas_t(p_das_t)
        des = "Epoch: " + str(p_das_t['time/epoch_l']) + \
            " Channel: " + str(p_das_t['channel_number_i'])
        #   Write trace data here
        try:
            #   Convert to counts
            # print tr.max (), tr.min ()
            tr_counts = tr / self.LSB
            self.EXREC.ph5_g_receivers.newarray(
                p_das_t['array_name_data_a'], tr_counts, dtype='int32',
                description=des)
        except Exception as e:
            #   Failed, leave as float
            # for x in tr : print x/self.LSB
            # print e.message
            sys.stderr.write(
                "Warning: Could not convert trace to counts. max: {1},\
                         min {2}\n{0}".format(
                                          e.message, tr.max(), tr.min()))
            p_response_t['bit_weight/value_d'] = 1.
            self.EXREC.ph5_g_receivers.newarray(
                p_das_t['array_name_data_a'], tr, dtype='float32',
                description=des)
        #
        self.update_index_t_info(p_das_t['time/epoch_l'] + (
            float(p_das_t['time/micro_seconds_i']) / 1000000.),
                                 p_das_t['sample_count_i'],
                                 p_das_t['sample_rate_i'] / p_das_t[
                                     'sample_rate_multiplier_i'])

    def process_array(self, rh, th):
        p_array_t = {}

        def seen_sta():
            if line not in self.ARRAY_T:
                return False
            elif self.Das not in self.ARRAY_T[line]:
                return False
            elif dtime not in self.ARRAY_T[line][self.Das]:
                return False
            elif chan_set in self.ARRAY_T[line][self.Das][dtime]:
                if not self.ARRAY_T[line][self.Das][dtime][chan_set]:
                    return False
                else:
                    return True

        '''
            deploy_time/
                type_s
                epoch_l
                ascii_s
                micro_seconds_i
            pickup_time/
                type_s
                epoch_l
                ascii_s
                micro_seconds_i
            id_s
            das/
                manufacturer_s
                model_s
                serial_number_s
                notes_s
            sensor/
                manufacturer_s
                model_s
                serial_number_s
                notes_s
            location/
                coordinate_system_s
                projection_s
                ellipsoid_s
                X/
                    units_s
                    value_d
                Y/
                    units_s
                    value_d
                Z/
                    units_s
                    value_d
                description_s
            channel_number_i
            description_s
            sample_rate_i
            sample_rate_multiplier_i
        '''
        '''
        Band Code:
           1000 <= G < 5000
           250  <= D < 1000
           80   <= E < 250
           10   <= S < 80
        '''
        if self.SD.sample_rate >= 1000:
            band_code = 'G'
        elif self.SD.sample_rate >= 250 and self.SD.sample_rate < 1000:
            band_code = 'D'
        elif self.SD.sample_rate >= 80 and self.SD.sample_rate < 250:
            band_code = 'E'
        elif self.SD.sample_rate >= 10 and self.SD.sample_rate < 80:
            band_code = 'S'
        else:
            band_code = 'X'
        '''
        Instrument Code:
           Changed from H to P at request from Akram
        '''
        instrument_code = 'P'
        '''
        Orientation Code:
           chan 1 -> N Changed to '1'
           chan 2 -> E Changed to '2'
           chan 3 -> Z
        or
           chan 1 -> Z
        '''
        if self.SD.chan_sets_per_scan >= 3:
            # true_chan = get_true_channel ()
            OM = {1: '1', 2: '2', 3: 'Z'}
        elif self.SD.chan_sets_per_scan == 1:
            OM = {1: 'Z'}
        else:
            OM = None
        if OM is None:
            orientation_code = self.get_true_channel(rh, th)
        else:
            orientation_code = OM[self.get_true_channel(rh, th)]
        # for cs in range (self.SD.chan_sets_per_scan) :
        p_array_t['seed_band_code_s'] = band_code
        p_array_t['seed_instrument_code_s'] = instrument_code
        p_array_t['seed_orientation_code_s'] = orientation_code
        p_array_t['seed_station_name_s'] = self.Das.split('X')[1]
        p_array_t['sample_rate_i'] = self.SD.sample_rate
        p_array_t['sample_rate_multiplier_i'] = 1
        p_array_t['deploy_time/type_s'] = 'BOTH'
        try:
            f, i = modf(rh.extended_header_1.epoch_deploy / 1000000.)
        except Exception as e:
            LOGGER.warning(
                "Failed to read extended header 1 deploy epoch: {0}.".format(
                    e.message))
            f = i = 0.
        p_array_t['deploy_time/epoch_l'] = int(i)
        p_array_t['deploy_time/ascii_s'] = time.ctime(int(i))
        p_array_t['deploy_time/micro_seconds_i'] = int(f * 1000000.)
        p_array_t['pickup_time/type_s'] = 'BOTH'
        try:
            f, i = modf(rh.extended_header_1.epoch_pickup / 1000000.)
        except Exception as e:
            LOGGER.warning(
                "Failed to read extended header 1 pickup epoch: {0}.".format(
                    e.message))
            f = i = 0.
        p_array_t['pickup_time/epoch_l'] = int(i)
        p_array_t['pickup_time/ascii_s'] = time.ctime(int(i))
        p_array_t['pickup_time/micro_seconds_i'] = int(f * 1000000.)
        p_array_t['id_s'] = self.Das.split('X')[1]
        p_array_t['das/manufacturer_s'] = 'FairfieldNodal'
        DM = {1: 'ZLAND 1C', 3: "ZLAND 3C"}
        try:
            # p_array_t['das/model_s'] = DM[self.SD.chan_sets_per_scan]
            if self.SD.chan_sets_per_scan >= 3:
                p_array_t['das/model_s'] = DM[3]
            else:
                p_array_t['das/model_s'] = DM[1]
        except Exception as e:
            LOGGER.warning(
                "Failed to read channel sets per scan: {0}.".format(e.message))
            p_array_t['das/model_s'] = 'zland-[13]C'
        p_array_t['das/serial_number_s'] = self.Das
        p_array_t[
            'das/notes_s'] = "manufacturer and model not read from data file."
        p_array_t['sensor/manufacturer_s'] = 'Geo Space'
        p_array_t['sensor/model_s'] = 'GS-30CT'
        p_array_t[
            'sensor/notes_s'] = "manufacturer and model not read from file."
        if self.TSP:
            p_array_t[
                'location/description_s'] = "Converted from Texas State Plane\
                 FIPS zone 4202"
        elif self.UTM:
            p_array_t[
                'location/description_s'] = "Converted from UTM Zone {0}"\
                .format(
                self.UTM)
        else:
            p_array_t['location/description_s'] = "Read from SEG-D as is."

        p_array_t['location/coordinate_system_s'] = 'geographic'
        p_array_t['location/projection_s'] = 'WGS84'
        p_array_t['location/X/units_s'] = 'degrees'
        p_array_t['location/X/value_d'] = self.LON
        p_array_t['location/Y/units_s'] = 'degrees'
        p_array_t['location/Y/value_d'] = self.LAT
        p_array_t['location/Z/units_s'] = 'unknown'
        try:
            p_array_t['location/Z/value_d'] =\
                th.trace_header_N[4].receiver_point_depth_final / 10.
        except Exception as e:
            LOGGER.warning(
                "Failed to read receiver point depth: {0}.".format(e.message))
            p_array_t['location/Z/value_d'] = 0.

        p_array_t['channel_number_i'] = self.get_true_channel(rh, th)
        # p_array_t['description_s'] = str (th.trace_header_N[4].line_number)
        try:
            p_array_t['description_s'] = "DAS: {0}, Node ID: {1}".format(
                self.Das, rh.extended_header_1.id_number)
        except Exception as e:
            LOGGER.warning(
                "Failed to read extended header 1 ID number: {0}.".format(
                    e.message))

        try:
            line = th.trace_header_N[4].line_number
        except Exception as e:
            LOGGER.warning(
                "Failed to read line number: {0}.".format(e.message))
            line = 0

        chan_set = self.get_true_channel(rh, th)
        dtime = p_array_t['deploy_time/epoch_l']
        if line not in self.ARRAY_T:
            self.ARRAY_T[line] = {}
        if self.Das not in self.ARRAY_T[line]:
            self.ARRAY_T[line][self.Das] = {}
        if dtime not in self.ARRAY_T[line][self.Das]:
            self.ARRAY_T[line][self.Das][dtime] = {}
        if chan_set not in self.ARRAY_T[line][self.Das][dtime]:
            self.ARRAY_T[line][self.Das][dtime][chan_set] = []

        if not seen_sta():
            self.ARRAY_T[line][self.Das][dtime][chan_set].append(p_array_t)
            # if rh.general_header_block_1.chan_sets_per_scan ==\
            #  len (self.ARRAY_T[line].keys ()) :
            # DN = True

    def process_reel_headers(self, rh):
        '''   Save receiver record header information in\
              Maps_g/Das_g_xxxxxxx/Hdr_a_xxxx file   '''

        def process(hdr, header_type):
            ll = [{'FileType': 'SEG-D', 'HeaderType': header_type}, hdr]
            log_array.append(json.dumps(
                ll, sort_keys=True, indent=4).split('\n'))

        log_array, log_name = self.getLOG()
        #   General header 1
        process(rh.general_header_block_1, 'General 1')
        #   General header 1
        process(rh.general_header_block_2, 'General 2')
        #   General header N
        for i in range(len(rh.general_header_block_N)):
            ht = "General {0}".format(i + 3)
            process(rh.general_header_block_N[i], ht)
        #   Channel set descriptors
        for i in range(len(rh.channel_set_descriptor)):
            ht = "Channel Set {0}".format(i + 1)
            process(rh.channel_set_descriptor, ht)
        #   Extended header 1
        process(rh.extended_header_1, "Extended 1")
        #   Extended header 2
        process(rh.extended_header_2, "Extended 2")
        #   Extended header 3
        process(rh.extended_header_3, "Extended 3")
        #   Extended header 4 - n
        for i in range(len(rh.extended_header_4)):
            ht = "Extended 4 ({0})".format(i + 1)
            process(rh.extended_header_4[i], ht)
        #   External header
        process(rh.external_header, "External Header")
        #   External header shot
        for i in range(len(rh.external_header_shot)):
            ht = "External Shot {0}".format(i + 1)
            process(rh.external_header_shot[i], ht)
        self.RH = True

    def process_trace_header(self, th):
        '''   Save trace header information in\
              Maps_g/Das_g_xxxxxxx/Hdr_a_xxxx file   '''

        def process(hdr, header_type):
            ll = [{'FileType': 'SEG-D', 'HeaderType': 'trace',
                  'HeaderSubType': header_type}, hdr]
            self.TRACE_JSON.append(json.dumps(
                ll, sort_keys=True, indent=4).split('\n'))

        # log_array, log_name = self.getLOG ()

        process(th.trace_header, "Trace Header")
        for i in range(len(th.trace_header_N)):
            ht = "Header N-{0}".format(i + 1)
            process(th.trace_header_N[i], ht)

    def process_traces(self, rh, th, tr):
        '''
            Inputs:
               rh -> reel headers
               th -> first trace header
               tr -> trace data
        '''
        self.RH = False
        self.TRACE_JSON = []
        # print "\tprocess das"
        # for cs in range (rh.chan_sets_per_scan) :
        self.process_das(rh, th, tr)
        # if not DN :
        # print "\tprocess array"
        self.process_array(rh, th)
        # print "\tprocess headers"
        if not self.RH:
            self.process_reel_headers(rh)
        # print "\tprocess trace header"
        self.process_trace_header(th)

    def write_arrays(self, Array_t):
        '''   Write /Experiment_g/Sorts_g/Array_t_xxx   '''

        def station_cmp(x, y):
            return cmp(x['id_s'], y['id_s'])

        lines = sorted(Array_t.keys())
        #   Loop through arrays/lines
        for line in lines:
            # name = self.EX.ph5_g_sorts.nextName ()
            name = "Array_t_{0:03d}".format(int(line))
            a = self.EX.ph5_g_sorts.newArraySort(name)
            stations = sorted(Array_t[line].keys())
            #   Loop through stations
            for station in stations:
                dtimes = sorted(Array_t[line][station].keys())
                #   Loop through channel sets
                for dtime in dtimes:
                    try:
                        chan_sets = sorted(Array_t[line][station][dtime].
                                        keys())
                        for c in chan_sets:
                            for array_t in Array_t[line][station][dtime][c]:
                                columns.populate(a, array_t)
                    except Exception as e:
                        print e.message

    def writeINDEX(self):
        '''   Write /Experiment_g/Receivers_g/Index_t   '''

        dass = sorted(self.DAS_INFO.keys())

        for das in dass:
            di = {}
            mi = {}
            start = sys.maxsize
            stop = 0.
            dm = [(d, m) for d in self.DAS_INFO[das]
                  for m in self.MAP_INFO[das]]
            for d, m in dm:
                di['external_file_name_s'] = d.ph5file
                mi['external_file_name_s'] = m.ph5file
                di['hdf5_path_s'] = d.ph5path
                mi['hdf5_path_s'] = m.ph5path
                di['serial_number_s'] = das
                mi['serial_number_s'] = das
                if d.startepoch < start:
                    start = d.startepoch

                if d.stopepoch > stop:
                    stop = d.stopepoch

            di['time_stamp/epoch_l'] = int(time.time())
            mi['time_stamp/epoch_l'] = int(time.time())
            di['time_stamp/micro_seconds_i'] = 0
            mi['time_stamp/micro_seconds_i'] = 0
            di['time_stamp/type_s'] = 'BOTH'
            mi['time_stamp/type_s'] = 'BOTH'
            di['time_stamp/ascii_s'] = time.ctime(di['time_stamp/epoch_l'])
            mi['time_stamp/ascii_s'] = time.ctime(mi['time_stamp/epoch_l'])

            di['start_time/epoch_l'] = int(modf(start)[1])
            mi['start_time/epoch_l'] = int(modf(start)[1])
            di['start_time/micro_seconds_i'] = int(modf(start)[0] * 1000000)
            mi['start_time/micro_seconds_i'] = int(modf(start)[0] * 1000000)
            di['start_time/type_s'] = 'BOTH'
            mi['start_time/type_s'] = 'BOTH'
            di['start_time/ascii_s'] = time.ctime(start)
            mi['start_time/ascii_s'] = time.ctime(start)

            di['end_time/epoch_l'] = modf(stop)[1]
            mi['end_time/epoch_l'] = modf(stop)[1]
            di['end_time/micro_seconds_i'] = int(modf(stop)[0] * 1000000)
            mi['end_time/micro_seconds_i'] = int(modf(stop)[0] * 1000000)
            di['end_time/type_s'] = 'BOTH'
            mi['end_time/type_s'] = 'BOTH'
            di['end_time/ascii_s'] = time.ctime(stop)
            mi['end_time/ascii_s'] = time.ctime(stop)

            self.EX.ph5_g_receivers.populateIndex_t(di)
            self.EX.ph5_g_maps.populateIndex_t(mi)

        rows, keys = self.EX.ph5_g_receivers.read_index()
        self.INDEX_T_DAS = Rows_Keys(rows, keys)

        rows, keys = self.EX.ph5_g_maps.read_index()
        self.INDEX_T_MAP = Rows_Keys(rows, keys)

        self.DAS_INFO = {}
        self.MAP_INFO = {}
    
    def process_SD(self, f):
        self.SD = segdreader.Reader(infile=f)

        if not self.SD.isSEGD(
            expected_manufactures_code=self.MANUFACTURERS_CODE):
            sys.stdout.write(":<Error>: {0}\n".format(self.SD.name()))
            sys.stdout.flush()
            LOGGER.info(
                "{0} is not a Fairfield SEG-D file. Skipping.".format(
                    self.SD.name()))
            return False
        try:
            # print "general headers"
            self.SD.process_general_headers()
            # print "channel sets"
            self.SD.process_channel_set_descriptors()
            # print "extended headers"
            self.SD.process_extended_headers()
            # print "external headers"
            self.SD.process_external_headers()
        except segdreader.InputsError as e:
            sys.stdout.write(":<Error>: {0}\n".format("".join(e.message)))
            sys.stdout.flush()
            LOGGER.info(
                "Error: Possible bad SEG-D file -- {0}".format(
                    "".join(e.message)))
            return False
        return self.SD

def txncsptolatlon(northing, easting):
    '''
       Sweetwater
       Convert texas state plane coordinates in feet to
       geographic coordinates, WGS84.
    '''
    #   Texas NC state plane feet Zone 4202
    sp = Proj(init='epsg:32038')
    #   WGS84, geographic
    wgs = Proj(init='epsg:4326', proj='latlong')
    #   Texas SP coordinates: survey foot is 1200/3937 meters
    lon, lat = transform(sp, wgs, easting * 0.30480060960121924,
                         northing * 0.30480060960121924)

    return lat, lon


def utmcsptolatlon(UTM, northing, easting):
    '''
       Mount Saint Helens
       Convert UTM to
       geographic coordinates, WGS84.
    '''
    #   UTM
    new_UTM = re.split(r'(\d+)', UTM)
    utmzone = str(new_UTM[1])

    if str(new_UTM[2]).upper() == 'N':
        NS = 'north'
    elif str(new_UTM[2]).upper() == 'S':
        NS = 'south'
    else:
        NS = 'north'

    utmc = Proj("+proj=utm +zone="+utmzone+" +"+NS+" +ellps=WGS84")
    print
    #   WGS84, geographic
    wgs = Proj(init='epsg:4326', proj='latlong')
    #
    lon, lat = transform(utmc, wgs, easting, northing)

    return lat, lon


def get_das(sd):
    #   Return line_station or das#[-9:]
    try:
        das = "{0}X{1}".format(
            sd.reel_headers.extended_header_3.line_number,
            sd.reel_headers.extended_header_3.receiver_point)
    except Exception:
        try:
            das = "{0}X{1}".format(
                sd.reel_headers.external_header.receiver_line,
                sd.reel_headers.external_header.receiver_point)
        except Exception:
            das = "sn" + \
                str(sd.reel_headers.general_header_block_1.
                    manufactures_sn)
            if das == 0:
                das = "id" + \
                    str(sd.reel_headers
                        .extended_header_1.id_number)[-9:]

    return das


def get_node(sd):
    #   Return node part number, node id, and number of channels
    pn = None  # Part Number
    id = None  # Node ID
    nc = None  # Number of channel sets
    try:
        nc = sd.reel_headers.general_header_block_1[
            'chan_sets_per_scan']
        pn = sd.reel_headers.extended_header_1['part_number']
        id = sd.reel_headers.extended_header_1['id_number']
    except Exception:
        pass

    return pn, id, nc


def main():
    import time
    then = time.time()
    from numpy import append as npappend

    MINIPH5 = None
    conv = SEGD2PH5()
    conv.get_args()

    conv.initialize_ph5()
    LOGGER.info("segd2ph5 {0}".format(PROG_VERSION))
    LOGGER.info("{0}".format(sys.argv))
    if len(conv.FILES) > 0:
        conv.RESP = Resp(conv.EX.ph5_g_responses)
        rows, keys = conv.EX.ph5_g_receivers.read_index()
        conv.INDEX_T_DAS = Rows_Keys(rows, keys)
        rows, keys = conv.EX.ph5_g_maps.read_index()
        conv.INDEX_T_MAP = Rows_Keys(rows, keys)

    for f in conv.FILES:
        conv.F = f
        traces = []
        try:
            SIZE = os.path.getsize(f)
        except Exception as e:
            sys.stderr.write("Error: failed to read {0}, {1}.\
             Skipping...\n".format(f, str(e.message)))
            LOGGER.error("Error: failed to read {0}, {1}.\
             Skipping...\n".format(f, str(e.message)))
            continue

        if not conv.process_SD(f):
            continue
        nleft = conv.APPEND
        conv.Das = get_das(conv.SD)
        part_number, node_id, number_of_channels = get_node(conv.SD)

        conv.EXREC = conv.get_current_data_only(SIZE, conv.Das)

        sys.stdout.write(":<Processing>: {0}\n".format(conv.SD.name()))
        sys.stdout.flush()
        LOGGER.info(
            "Processing: {0}... Size: {1}\n".format(conv.SD.name(), SIZE))
        if conv.EXREC.filename != MINIPH5:
            LOGGER.info("Opened: {0}...\n".format(conv.EXREC.filename))
            LOGGER.info(
                "DAS: {0}, Node ID: {1}, PN: {2}, Channels: {3}".format(
                    conv.Das, node_id, part_number, number_of_channels))
            MINIPH5 = conv.EXREC.filename

        n = 0
        trace_headers_list = []
        while True:
            #
            if conv.SD.isEOF():
                if n != 0:
                    thl = []
                    chan_set = None
                    t = None
                    new_traces = []
                    for T in traces:
                        thl.append(T.headers)
                        if chan_set is None:
                            chan_set = T.headers.trace_header.channel_set
                        if chan_set == T.headers.trace_header.channel_set:
                            if isinstance(t, type(None)):
                                t = T.trace
                            else:
                                t = npappend(t, T.trace)
                        else:
                            new_traces.append(T)

                    traces = new_traces
                    conv.process_traces(conv.SD.reel_headers, thl[0], t)

                    if conv.DAS_INFO:
                        conv.writeINDEX()
                break

            try:
                trace, cs = conv.SD.process_trace()
            except segdreader.InputsError as e:
                # sys.stderr.write ("Error 2: Possible bad SEG-D file \
                # -- {0}".format ("".join (e)))
                sys.stdout.write(":<Error:> {0}\n".format(conv.F))
                sys.stdout.flush()
                LOGGER.info(
                    "Error: Possible bad SEG-D file -- {0}".format(
                        "".join(e.message)))
                break

            if not conv.LAT and not conv.LON:
                try:
                    if conv.UTM:
                        #   UTM
                        conv.LAT, conv.LON = utmcsptolatlon(
                            conv.UTM,
                            conv.SD.trace_headers.trace_header_N[
                                4].receiver_point_Y_final / 10.,
                            conv.SD.trace_headers.trace_header_N[
                                4].receiver_point_X_final / 10.)
                    elif conv.TSP:
                        #   Texas State Plane coordinates
                        conv.LAT, conv.LON = txncsptolatlon(
                            conv.SD.trace_headers.trace_header_N[
                                4].receiver_point_Y_final / 10.,
                            conv.SD.trace_headers.trace_header_N[
                                4].receiver_point_X_final / 10.)
                    else:
                        conv.LAT = conv.SD.trace_headers.trace_header_N[
                                  4].receiver_point_Y_final / 10.
                        conv.LON = conv.SD.trace_headers.trace_header_N[
                                  4].receiver_point_X_final / 10.
                except Exception as e:
                    LOGGER.warning(
                        "Failed to convert location: {0}.\n".format(
                            e.message))

            trace_headers_list.append(conv.SD.trace_headers)
            # for cs in range (conv.SD.chan_sets_per_scan) :
            if n == 0:
                traces.append(Trace(trace, conv.SD.trace_headers))
                n = 1
                #   Node kludge
                # conv.Das = (conv.SD.trace_headers.trace_header_N[0]\
                # .receiver_line * 1000) + conv.SD.trace_headers.\
                # trace_header_N[0].receiver_point
                conv.Das = get_das(conv.SD)
            else:
                traces.append(Trace(trace, conv.SD.trace_headers))
                # traces = npappend (traces, trace)

            if n >= nleft or conv.EVERY is True:
                thl = []
                chan_set = None
                chan_set_next = None
                t = None
                new_traces = []
                # Need to check for gaps here!
                for T in traces:
                    thl.append(T.headers)
                    if chan_set is None:
                        chan_set = T.headers.trace_header.channel_set
                    if chan_set == T.headers.trace_header.channel_set:
                        # print type (t)
                        if isinstance(t, type(None)):
                            t = T.trace
                        else:
                            t = npappend(t, T.trace)
                        # print len (t), t.min (), t.max ()
                    else:
                        new_traces.append(T)
                        if chan_set_next is None:
                            chan_set_next =\
                                T.headers.trace_header.channel_set

                traces = new_traces
                conv.process_traces(conv.SD.reel_headers, thl[0], t)
                if new_traces:
                    nleft = conv.APPEND - len(new_traces)
                else:
                    nleft = conv.APPEND
                chan_set = chan_set_next
                chan_set_next = None
                if conv.DAS_INFO:
                    conv.writeINDEX()
                n = 0
                trace_headers_list = []
                continue

            n += 1

        conv.update_external_references()
        if conv.TRACE_JSON:
            log_array, name = conv.getLOG()
            for line in conv.TRACE_JSON:
                log_array.append(line)

        sys.stdout.write(":<Finished>: {0}\n".format(conv.F))
        sys.stdout.flush()

    conv.write_arrays(conv.ARRAY_T)
    seconds = time.time() - then

    try:
        conv.EX.ph5close()
        conv.EXREC.ph5close()
    except Exception as e:
        sys.stderr.write("Warning: {0}\n".format("".join(e.message)))

    print "Done...{0:b}".format(int(seconds / 6.))  # Minutes X 10
    LOGGER.info("Done...{0:b}".format(int(seconds / 6.)))
    logging.shutdown()


if __name__ == '__main__':
    main()
