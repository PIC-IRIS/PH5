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
from decimal import Decimal
from math import modf
import warnings
import operator

from pyproj import Proj, transform
import construct
import bcd_py
from tables import NaturalNameWarning

from ph5.core import (experiment, columns, segdreader, segdreader_smartsolo,
                      ph5api)
from ph5 import LOGGING_FORMAT
warnings.filterwarnings('ignore', category=NaturalNameWarning)


PROG_VERSION = "2022.109"
LOGGER = logging.getLogger(__name__)

MAX_PH5_BYTES = 1073741824 * 100.  # 100 GB (1024 X 1024 X 1024 X 2)

os.environ['TZ'] = 'GMT'
time.tzset()

APPEND = 1  # Number of SEG-D events to append to make 1 ph5 event.

DAS_INFO = {}
MAP_INFO = {}
#   Current raw file processing
F = None
#   RE for mini files
miniPH5RE = re.compile(r".*miniPH5_(\d\d\d\d\d)\.ph5")

# -2.5V to 2.5V
mV_full_scale = 5000
# 24-bit
counts_full_scale = 2**24


def bitweight(db):
    # where db = 20log(V1,V2)
    return (mV_full_scale / (10.**(db/20.))) / counts_full_scale


dbs = (0, 6, 12, 18, 24, 30, 36)
LSB_MAP = {db: bitweight(db) for db in dbs}
LSB = LSB_MAP[36]

#   Manufacturers codes
FAIRFIELD = 20
OTHER = 0


def read_manufacture_code(filename):
    """ read byte 17 for manufacture code"""
    f = open(filename, 'rb')
    f.seek(16)
    byte = f.read(1)
    swap = True
    if sys.byteorder == 'big':
        swap = False
    bin = construct.BitStruct("BIN",
                              construct.BitField(
                                  "field", 8, swapped=swap))
    bcd = bin.parse(byte)['field']
    if sys.byteorder == 'little':
        bcd = construct.ULInt64("xxx").build(bcd)
    else:
        bcd = construct.UBInt64("xxx").build(bcd)
    code = bcd_py.bcd2int(bcd, 0, 2)
    f.close()
    return code


def get_segdreader(filename, manucode):
    """
        get the segdreader from manufacture code infile
        or from --manufacturers_code argument
    """
    KNOWN_CODE = {20: (segdreader, 'FairField'),
                  61: (segdreader_smartsolo, 'SmartSolo')}
    req_code_list = ["%s for %s format" % (k, KNOWN_CODE[k][1])
                     for k in KNOWN_CODE.keys()]
    req_code_str = ("Please give flag --manufacturers_code either "
                    ' or '.join(req_code_list))

    manu = read_manufacture_code(filename)
    if manu in KNOWN_CODE.keys():
        reader = KNOWN_CODE[manu][0]
    else:
        try:
            if manucode in KNOWN_CODE.keys():
                reader = KNOWN_CODE[manucode][0]
            else:
                LOGGER.error("manufacturers_code flag {0} is not one of "
                             "the known codes: {1}.\n{2}".
                             format(manucode, KNOWN_CODE.keys(), req_code_str))
                raise Exception
        except IndexError:
            LOGGER.error("The manufacture code recorded in file {0} is not "
                         "one of the known codes: {1}.\n{2}".
                         format(manucode, KNOWN_CODE.keys(), req_code_str))
            raise Exception
    return reader


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
        for ln in self.lines:
            if ln['bit_weight/value_d'] == bw and ln['gain/value_i'] == gain:
                return ln['n_i']

        return -1

    def next_i(self):
        return len(self.lines)


class Trace(object):
    __slots__ = ("trace", "headers")

    def __init__(self, trace, headers):
        self.trace = trace
        self.headers = headers


def read_infile(infile):
    '''   Read list of input SEG-D files from a file   '''
    global FILES

    def fn_sort(a, b):
        return cmp(os.path.basename(a), os.path.basename(b))

    try:
        fh = file(infile)
    except Exception:
        LOGGER.warning("Failed to open %s\n" % infile)
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
        FILES.append(line)

    FILES.sort(fn_sort)


def get_args():
    global PH5, FILES, EVERY, NUM_MINI, TSPF, UTM, FIRST_MINI, APPEND,\
        MANUFACTURERS_CODE

    TSPF = False
    from optparse import OptionParser

    class MyParser(OptionParser):
        """
        Override format_epilog to allow newlines
        """
        def format_epilog(self, formatter):
            return self.epilog

    oparser = MyParser()

    oparser.usage = "Version: {0} Usage: segdtoph5 [options]".format(
        PROG_VERSION)
    oparser.epilog = (
        "Notice:\n"
        "\tData of a Das can't be stored in more than one mini file.\n\n"
        "\tUpdate astropy package for the lastes leap second table used in "
        "converting time from GPS to UTC in SmartSolo's:\n"
        "\t\tconda update astropy\n")

    oparser.add_option("-r", "--raw", dest="rawfile",
                       help="Fairfield SEG-D v1.6 file.", metavar="raw_file")

    oparser.add_option("-f", "--file",
                       action="store", dest="infile", type="string",
                       help="File containing list of Fairfield SEG-D\
                        v1.6 file names.",
                       metavar="file_list_file")

    oparser.add_option("-n", "--nickname", dest="outfile",
                       help="The ph5 file prefix (experiment nick name).",
                       metavar="output_file_prefix")

    oparser.add_option("-U", "--UTM", dest="utm_zone",
                       help="Locations in SEG-D file are UTM, --UTM=utmzone."
                            " Zone number and N or S designation"
                            " eg 13N",
                       type='str', default=0,
                       metavar="utm_zone")

    oparser.add_option("-T", "--TSPF", dest="texas_spc",
                       help="Locations are in texas state plane coordinates.",
                       action='store_true', default=False)

    oparser.add_option("-M", "--num_mini",
                       help=("Create a given number of miniPH5 files."
                             " Ex: -M 38"),
                       metavar="num_mini", type='int', default=None)

    oparser.add_option("-S", "--first_mini",
                       help=("The index of the first miniPH5_xxxxx.ph5 "
                             "file of all. Ex: -S 5"),
                       metavar="first_mini", type='int', default=1)

    oparser.add_option("-c", "--combine", dest="combine",
                       help="Combine this number if SEG-D traces to one\
                        PH5 trace.",
                       metavar="combine", type='int', default=APPEND)

    oparser.add_option("-E", "--allevents", action="store_true",
                       dest="all_events",
                       default=False, metavar="all_events")

    oparser.add_option("--manufacturers_code", dest="manufacturers_code",
                       help="Manufacturers code. Defaults to 20 for Fairfield.\
                        Most likely will not work for SEG-D written by other\
                         data loggers,",
                       type='int', default=None)

    options, args = oparser.parse_args()

    if options.rawfile and options.infile:
        oparser.error("argument -f/--file: not allowed with argument -r/--raw")

    FILES = []
    PH5 = None

    EVERY = options.all_events
    NUM_MINI = options.num_mini
    FIRST_MINI = options.first_mini
    UTM = options.utm_zone
    TSPF = options.texas_spc
    APPEND = options.combine
    MANUFACTURERS_CODE = options.manufacturers_code

    if options.infile is not None:
        read_infile(options.infile)

    elif options.rawfile is not None:
        FILES.append(options.rawfile)

    if len(FILES) == 0:
        raise Exception("No input file given.\n")

    #   Set output file
    if options.outfile is not None:
        PH5 = options.outfile
    else:
        raise Exception("No outfile (PH5) given.\n")

    setLogger()


def setLogger():
    if LOGGER.handlers != []:
        LOGGER.removeHandler(LOGGER.handlers[0])

    # Write log to file
    ch = logging.FileHandler("segd2ph5.log")
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)


def initializeExperiment():
    global EX

    EX = experiment.ExperimentGroup(nickname=PH5)
    EDIT = True
    EX.ph5open(EDIT)
    EX.initgroup()


def openPH5(filename):
    '''   Open PH5 file, miniPH5_xxxxx.ph5   '''
    try:
        if EXREC.ph5.isopen:
            if EXREC.filename != filename:
                EXREC.ph5close()
            else:
                return EXREC
    except BaseException:
        pass
    exrec = experiment.ExperimentGroup(nickname=filename)
    exrec.ph5open(True)
    exrec.initgroup()
    return exrec


def update_index_t_info(starttime, samples, sps):
    '''   Update info that gets saved in Index_t   '''
    global DAS_INFO, MAP_INFO

    ph5file = EXREC.filename
    ph5path = '/Experiment_g/Receivers_g/' + \
              EXREC.ph5_g_receivers.current_g_das._v_name
    ph5map = '/Experiment_g/Maps_g/' + EXREC.ph5_g_maps.current_g_das._v_name
    das = ph5path[32:]
    stoptime = starttime + (float(samples) / float(sps))
    di = Index_t_Info(das, ph5file, ph5path, starttime, stoptime)
    dm = Index_t_Info(das, ph5file, ph5map, starttime, stoptime)
    if das not in DAS_INFO:
        DAS_INFO[das] = []
        MAP_INFO[das] = []

    DAS_INFO[das].append(di)
    MAP_INFO[das].append(dm)
    LOGGER.info(
        "DAS: {0} File: {1} First Sample: {2} Last Sample: {3}".format(
            das, ph5file, time.ctime(starttime), time.ctime(stoptime)))


def update_external_references():
    '''   Update external references in master.ph5 to
          miniPH5 files in Receivers_t    '''
    global F
    LOGGER.info("Updating external references...")
    n = 0
    for i in INDEX_T_DAS.rows:
        external_file = i['external_file_name_s'][2:]
        external_path = i['hdf5_path_s']
        target = external_file + ':' + external_path
        external_group = external_path.split('/')[3]

        #   Nuke old node
        try:
            group_node = EX.ph5.get_node(external_path)
            group_node.remove()
        except Exception as e:
            pass

        #   Re-create node
        try:
            EX.ph5.create_external_link(
                '/Experiment_g/Receivers_g', external_group, target)
            n += 1
        except Exception as e:
            # pass
            LOGGER.error("{0}\n".format(e.message))

    LOGGER.info("done, {0} das nodes recreated.\n".format(n))

    n = 0
    for i in INDEX_T_MAP.rows:
        external_file = i['external_file_name_s'][2:]
        external_path = i['hdf5_path_s']
        target = external_file + ':' + external_path
        external_group = external_path.split('/')[3]

        #   Nuke old node
        try:
            group_node = EX.ph5.get_node(external_path)
            group_node.remove()
        except Exception as e:
            pass

        #   Re-create node
        try:
            EX.ph5.create_external_link(
                '/Experiment_g/Maps_g', external_group, target)
            n += 1
        except Exception as e:
            # pass
            LOGGER.error("{0}\n".format(e.message))

    LOGGER.info("done, {0} map nodes recreated.\n".format(n))


def get_current_data_only(size_of_data, das=None):
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
    for index_t in INDEX_T_DAS.rows:
        #   This DAS already exists in a ph5 file
        if index_t['serial_number_s'] == das:
            newestfile = sstripp(index_t['external_file_name_s'])
            return openPH5(newestfile)
        #   miniPH5_xxxxx.ph5 with largest xxxxx
        mh = miniPH5RE.match(index_t['external_file_name_s'])
        if n < int(mh.groups()[0]):
            newestfile = sstripp(index_t['external_file_name_s'])
            n = int(mh.groups()[0])

    if not newestfile:
        #   This is the first file added
        return openPH5('miniPH5_{0:05d}'.format(FIRST_MINI))

    size_of_exrec = os.path.getsize(newestfile + '.ph5')
    if NUM_MINI is not None:
        fm = FIRST_MINI - 1
        if (int(newestfile[8:13]) - fm) < NUM_MINI:
            newestfile = "miniPH5_{0:05d}".format(int(newestfile[8:13]) + 1)
        else:
            small = sstripp(smallest())
            return openPH5(small)

    elif (size_of_data + size_of_exrec) > MAX_PH5_BYTES:
        newestfile = "miniPH5_{0:05d}".format(int(newestfile[8:13]) + 1)

    return openPH5(newestfile)


def getLOG():
    '''   Create a open a new and unique header file under Maps_g/Das_g_
                                                                 /Sta_g_
                                                                 /Evt_g_
                                                                        /Hdr_a_
    '''
    current_das = EXREC.ph5_g_receivers.get_das_name()
    g = EXREC.ph5_g_maps.newdas('Das_g_', current_das)
    EXREC.ph5_g_maps.setcurrent(g)
    try:
        name = EXREC.ph5_g_maps.nextarray('Hdr_a_')
    except TypeError:
        return None

    log_array = EXREC.ph5_g_maps.newearray(
        name, description="SEG-D header entries: {0}".format(Das))

    return log_array, name


def process_traces(rh, th, tr):
    '''
        Inputs:
           rh -> reel headers
           th -> first trace header
           tr -> trace data
    '''

    def get_true_channel(SD):
        if SD.manufacturer == 'FairfieldNodal':
            '''
            Orientation Code:
               chan 1 -> N Changed to '1'
               chan 2 -> E Changed to '2'
               chan 3 -> Z
            or
               chan 1 -> Z
            '''
            #   Find channel by mapping to streamer_cable_number
            if rh.channel_set_to_streamer_cable_map[
                th.trace_header.channel_set] \
                    == 0:
                true_channel = th.trace_header.channel_set
            else:
                true_channel = rh.channel_set_to_streamer_cable_map[
                    th.trace_header.channel_set]
            if SD.chan_sets_per_scan >= 3:
                OM = {1: '1', 2: '2', 3: 'Z'}
            elif SD.chan_sets_per_scan == 1:
                OM = {1: 'Z'}
            else:
                OM = None
            if OM is None:
                orientation_code = true_channel
            else:
                orientation_code = OM[true_channel]
        elif SD.manufacturer == 'SmartSolo':
            channel_list = ['N', 'E', 'Z']
            filename_parts = SD.name().split('.')
            found_channel = False
            true_channel = 0
            orientation_code = None
            for p in filename_parts:
                if p in channel_list:
                    orientation_code = p
                    true_channel = channel_list.index(p) + 1
                    found_channel = True
                    break
            if not found_channel:
                LOGGER.warning(
                    "Neither E, N, nor Z can't be found in filename")
        return true_channel, orientation_code

    def get_raw_file_name(SD):
        filename = SD.name()
        if SD.manufacturer == 'SmartSolo':
            channel_list = ['E', 'N', 'Z']
            filename_parts = filename.split('.')
            chanidx = -1
            for c in channel_list:
                try:
                    chanidx = filename_parts.index(c)
                    break
                except ValueError:
                    pass
            """
            Shorten filename to fit the field:
            remove 'segd' at the end
            remove second and decimal of second
            add . in front of chan to show somethings have been removed
            Ex: filename: 453005483.1.2021.03.15.16.00.00.000.E.segd
            => shorten:   453005483.1.2021.03.15.16.00..E
            """
            filename_parts.remove('segd')
            filename_parts[chanidx] = '.' + filename_parts[chanidx]
            filename_parts.pop(chanidx - 1)  # remove decimal part
            filename_parts.pop(chanidx - 2)  # remove second part
            filename = '.'.join(filename_parts)
        return os.path.basename(filename)

    def process_das():
        global LSB
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
        das_g, das_t, receiver_t, time_t = EXREC.ph5_g_receivers.newdas(
            str(Das))
        #   Build maps group (XXX)
        EXREC.ph5_g_maps.newdas('Das_g_', str(Das))
        if rh.general_header_blocks[0].chan_sets_per_scan == 1:
            #   Single channel
            p_das_t['receiver_table_n_i'] = 0  # 0 -> Z
        elif rh.general_header_blocks[0].chan_sets_per_scan >= 3:
            # 1 (N node) -> 1 (N PH5), 2 (E Node)-> 2 (E PH5), 3 (Z Node) -> 0
            # (Z PH5)
            M = {1: 1, 2: 2, 3: 0}
            p_das_t['receiver_table_n_i'] = M[get_true_channel(SD)[0]]
        else:
            p_das_t['receiver_table_n_i'] = 0  # 0 -> Z
            LOGGER.warning(
                "Header channel set: {0}. Check Receiver_t entries!".format(
                    th.trace_header.channel_set))

        p_das_t['response_table_n_i'] = None
        p_das_t['time_table_n_i'] = 0
        p_das_t['time/type_s'] = 'BOTH'
        try:
            trace_epoch = th.trace_epoch
        except Exception as e:
            LOGGER.warning("Failed to read shot epoch: {0}.".format(e.message))
            trace_epoch = 0.

        tmp = Decimal(trace_epoch) / 1000000
        p_das_t['time/epoch_l'] = int(tmp)
        p_das_t['time/ascii_s'] = time.ctime(p_das_t['time/epoch_l'])
        p_das_t['time/micro_seconds_i'] = int((tmp % 1) * 1000000)
        p_das_t['event_number_i'] = th.event_number
        p_das_t['channel_number_i'] = get_true_channel(SD)[0]
        p_das_t['sample_rate_i'] = SD.sample_rate
        p_das_t['sample_rate_i'] = SD.sample_rate
        p_das_t['sample_rate_multiplier_i'] = 1
        p_das_t['sample_count_i'] = len(tr)
        p_das_t['stream_number_i'] = 1
        p_das_t['raw_file_name_s'] = get_raw_file_name(SD)
        p_das_t['array_name_data_a'] = EXREC.ph5_g_receivers.nextarray(
            'Data_a_')
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
            LSB = LSB_MAP[th.preamp_gain_db]
            n_i = RESP.match(LSB, th.preamp_gain_db)
        except Exception as e:
            n_i = 0
        p_response_t['gain/units_s'] = 'dB'
        try:
            p_response_t['gain/value_i'] = th.preamp_gain_db
        except Exception as e:
            LOGGER.warning(
                "Failed to read trace pre amp gain: {0}.".format(e.message))
            p_response_t['gain/value_i'] = 0.
            p_response_t['gain/units_s'] = 'Unknown'

        p_response_t['bit_weight/units_s'] = 'mV/count'
        p_response_t['bit_weight/value_d'] = LSB
        if n_i < 0:
            n_i = RESP.next_i()
            p_response_t['n_i'] = n_i
            EX.ph5_g_responses.populateResponse_t(p_response_t)
            RESP.update()
        p_das_t['response_table_n_i'] = n_i
        EXREC.ph5_g_receivers.populateDas_t(p_das_t)
        des = "Epoch: " + str(p_das_t['time/epoch_l']) + \
              " Channel: " + str(p_das_t['channel_number_i'])
        #   Write trace data here
        try:
            if SD.manufacturer == 'FairfieldNodal':
                #   Convert to counts
                tr_counts = tr / LSB
                EXREC.ph5_g_receivers.newarray(
                    p_das_t['array_name_data_a'], tr_counts, dtype='int32',
                    description=des)
            elif SD.manufacturer == 'SmartSolo':
                # SmartSolo is recorded by mV
                EXREC.ph5_g_receivers.newarray(
                    p_das_t['array_name_data_a'], tr, dtype='float32',
                    description=des)
        except Exception as e:
            #   Failed, leave as float
            LOGGER.warning(
                "Could not convert trace to counts. max: {1},\
                 min {2}\n{0}".format(
                    e.message, tr.max(), tr.min()))
            p_response_t['bit_weight/value_d'] = 1.
            EXREC.ph5_g_receivers.newarray(
                p_das_t['array_name_data_a'], tr, dtype='float32',
                description=des)
        update_index_t_info(p_das_t['time/epoch_l'] + (
                    float(p_das_t['time/micro_seconds_i']) / 1000000.),
                            p_das_t['sample_count_i'],
                            p_das_t['sample_rate_i'] / p_das_t[
                                'sample_rate_multiplier_i'])

    def process_array():
        p_array_t = {}

        def seen_sta():
            if line not in ARRAY_T:
                return False
            elif Das not in ARRAY_T[line]:
                return False
            elif dtime not in ARRAY_T[line][Das]:
                return False
            elif chan_set in ARRAY_T[line][Das][dtime]:
                if not ARRAY_T[line][Das][dtime][chan_set]:
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
        if SD.sample_rate >= 1000:
            band_code = 'G'
        elif SD.sample_rate >= 250 and SD.sample_rate < 1000:
            band_code = 'D'
        elif SD.sample_rate >= 80 and SD.sample_rate < 250:
            band_code = 'E'
        elif SD.sample_rate >= 10 and SD.sample_rate < 80:
            band_code = 'S'
        else:
            band_code = 'X'
        '''
        Instrument Code:
           Changed from H to P at request from Akram
        '''
        instrument_code = 'P'
        chan_set, orientation_code = get_true_channel(SD)

        p_array_t['seed_band_code_s'] = band_code
        p_array_t['seed_instrument_code_s'] = instrument_code
        p_array_t['seed_orientation_code_s'] = orientation_code

        p_array_t['seed_station_name_s'] = Das.split('X')[1]
        p_array_t['sample_rate_i'] = SD.sample_rate
        p_array_t['sample_rate_multiplier_i'] = 1
        p_array_t['deploy_time/type_s'] = 'BOTH'
        try:
            f, i = modf(SD.deploy_epoch)
        except Exception as e:
            LOGGER.warning(
                "Failed to read deploy epoch: {0}.".format(
                    e.message))
            f = i = 0.
        p_array_t['deploy_time/epoch_l'] = int(i)
        p_array_t['deploy_time/ascii_s'] = time.ctime(int(i))
        p_array_t['deploy_time/micro_seconds_i'] = int(f * 1000000.)
        p_array_t['pickup_time/type_s'] = 'BOTH'
        try:
            f, i = modf(SD.pickup_epoch)
        except Exception as e:
            LOGGER.warning(
                "Failed to read pickup epoch: {0}.".format(
                    e.message))
            f = i = 0.
        p_array_t['pickup_time/epoch_l'] = int(i)
        p_array_t['pickup_time/ascii_s'] = time.ctime(int(i))
        p_array_t['pickup_time/micro_seconds_i'] = int(f * 1000000.)
        p_array_t['id_s'] = Das.split('X')[1]

        # use manu_code to decide SMARTSOLO dasmodel
        p_array_t['das/manufacturer_s'] = SD.manufacturer

        try:
            if SD.manufacturer == "SmartSolo":
                p_array_t['das/model_s'] = 'SmartSolo IGU16'
            elif SD.manufacturer == "FairfieldNodal":
                if SD.chan_sets_per_scan >= 3:
                    p_array_t['das/model_s'] = "ZLAND 3C"
                else:
                    p_array_t['das/model_s'] = 'ZLAND 1C'
        except Exception as e:
            LOGGER.warning(
                "Failed to read channel sets per scan: {0}.".format(e.message))
            p_array_t['das/model_s'] = 'zland-[13]C'
        p_array_t['das/serial_number_s'] = Das
        p_array_t[
            'das/notes_s'] = "manufacturer and model not read from data file."
        p_array_t['sensor/manufacturer_s'] = 'Geo Space'
        p_array_t['sensor/model_s'] = 'GS-30CT'
        p_array_t[
            'sensor/notes_s'] = "manufacturer and model not read from file."
        if SD.manufacturer == 'FairfieldNodal':
            if TSPF:
                p_array_t['location/description_s'] = (
                    "Converted from Texas State Plane FIPS zone 4202")
            elif UTM:
                p_array_t['location/description_s'] = (
                    "Converted from UTM Zone {0}".format(UTM))
            else:
                p_array_t['location/description_s'] = "Read from SEG-D as is."
        else:
            p_array_t['location/description_s'] = "Read from SEG-D as is."

        p_array_t['location/coordinate_system_s'] = 'geographic'
        p_array_t['location/projection_s'] = 'WGS84'
        p_array_t['location/X/units_s'] = 'degrees'
        p_array_t['location/X/value_d'] = LON
        p_array_t['location/Y/units_s'] = 'degrees'
        p_array_t['location/Y/value_d'] = LAT
        p_array_t['location/Z/units_s'] = 'unknown'
        try:
            p_array_t['location/Z/value_d'] = th.ele / 10.
        except Exception as e:
            LOGGER.warning(
                "Failed to read elevation: {0}.".format(e.message))
            p_array_t['location/Z/value_d'] = 0.

        p_array_t['channel_number_i'] = chan_set
        try:
            p_array_t['description_s'] = "DAS: {0}, Node ID: {1}".format(
                Das, SD.id_number)
        except Exception as e:
            LOGGER.warning(
                "Failed to read ID number: {0}.".format(
                    e.message))

        try:
            line = th.line_number
            if line == -1:
                line = 1
        except Exception as e:
            LOGGER.warning("Failed to read line number: {0}.".format(
                e.message))
            line = 0

        dtime = p_array_t['deploy_time/epoch_l']
        if line not in ARRAY_T:
            ARRAY_T[line] = {}
        if Das not in ARRAY_T[line]:
            ARRAY_T[line][Das] = {}
        if dtime not in ARRAY_T[line][Das]:
            ARRAY_T[line][Das][dtime] = {}
        if chan_set not in ARRAY_T[line][Das][dtime]:
            ARRAY_T[line][Das][dtime][chan_set] = []

        if not seen_sta():
            ARRAY_T[line][Das][dtime][chan_set].append(p_array_t)
        elif SD.manufacturer == "SmartSolo":
            # need to update the row after each trace is readed
            # because the pickup time will be
            # updated depend on trace_epoch
            ARRAY_T[line][Das][dtime][chan_set][-1] = p_array_t

    def process_reel_headers():
        global RH
        '''   Save receiver record header information in\
              Maps_g/Das_g_xxxxxxx/Hdr_a_xxxx file   '''

        def process(hdr, header_type):
            ll = [{'FileType': 'SEG-D', 'HeaderType': header_type}, hdr]
            log_array.append(json.dumps(
                ll, sort_keys=True, indent=4).split('\n'))

        log_array, log_name = getLOG()
        for i in range(len(rh.general_header_blocks)):
            ht = "General {0}".format(i+1)
            process(rh.general_header_blocks[i], ht)
        #   Channel set descriptors
        for i in range(len(rh.channel_set_descriptor)):
            ht = "Channel Set {0}".format(i + 1)
            process(rh.channel_set_descriptor, ht)

        for i in range(len(rh.extended_headers)):
            ht = "Extended {0}".format(i)
            process(rh.extended_headers[i], ht)
        #   External header
        process(rh.external_header, "External Header")
        #   External header shot
        for i in range(len(rh.external_header_shot)):
            ht = "External Shot {0}".format(i + 1)
            process(rh.external_header_shot[i], ht)
        RH = True

    def process_trace_header():
        '''   Save trace header information in\
              Maps_g/Das_g_xxxxxxx/Hdr_a_xxxx file   '''

        def process(hdr, header_type):
            global TRACE_JSON
            ll = [{'FileType': 'SEG-D', 'HeaderType': 'trace',
                  'HeaderSubType': header_type}, hdr]
            TRACE_JSON.append(json.dumps(
                ll, sort_keys=True, indent=4).split('\n'))

        process(th.trace_header, "Trace Header")
        for i in range(len(th.trace_header_N)):
            ht = "Header N-{0}".format(i + 1)
            process(th.trace_header_N[i], ht)

    process_das()
    process_array()
    if not RH:
        process_reel_headers()
    process_trace_header()


def write_arrays(SD, Array_t):
    '''   Write /Experiment_g/Sorts_g/Array_t_xxx   '''
    lines = sorted(Array_t.keys())
    #   Loop through arrays/lines
    for line in lines:
        name = "Array_t_{0:03d}".format(int(line))
        a = EX.ph5_g_sorts.newArraySort(name)
        das_list = sorted(Array_t[line].keys())
        #   Loop through das_list
        for das in das_list:
            if SD.manufacturer == 'SmartSolo':
                Array_t[line][das] = combine_array_entries(
                    name, Array_t[line][das])
            dtimes = sorted(Array_t[line][das].keys())
            #   Loop through deploying times
            for dtime in dtimes:
                chan_sets = sorted(Array_t[line][das][dtime].keys())
                #   Loop through channel sets
                for chan_set in chan_sets:
                    try:
                        for array_t in Array_t[line][das][dtime][chan_set]:
                            columns.populate(a, array_t)
                    except Exception as e:
                        print(e.message)


def reorder_das(PH5):
    """
    Run only after EX and EXREC have been closed.
    Open ph5object, truncate das_t, reorder and re-populate it
    :param: PH5: name of master file. Ex: master.ph5
    """
    ph5filename = PH5 if PH5[-4:] == '.ph5' else PH5 + '.ph5'
    ph5object = ph5api.PH5(path='.', nickname=ph5filename, editmode=True)
    ph5object.read_das_g_names()
    for das_g_name in ph5object.Das_g_names.keys():
        das_sn = das_g_name.replace('Das_g_', '')
        das_g = ph5object.ph5_g_receivers.getdas_g(das_sn)
        ph5object.ph5_g_receivers.setcurrent(das_g)
        das_rows, das_keys = experiment.read_table(
            ph5object.ph5_g_receivers.current_t_das)

        ph5object.ph5_g_receivers.truncate_das_t(das_sn)

        das_rows = sorted(das_rows,
                          key=operator.itemgetter('channel_number_i',
                                                  'time/epoch_l',
                                                  'time/micro_seconds_i'))
        for r in das_rows:
            ph5object.ph5_g_receivers.populateDas_t(r)
    ph5object.close()
    LOGGER.info("Reorder and populate Das_t")


def combine_array_entries(aName, aOfDas):
    """
    :para aName: "Array_t_xxx" to add to warning message
    :param aOfDas: {dtime: {c:[entry]}} in which each dtime is an entry
    :return aOnDeployTimes which has the same structure of aOfDas but the
        times are combined if gap less than 2m
    """
    aOnChannels = {}  # {c_i: list of entries according to dtimes' order}
    dtimes = sorted(aOfDas.keys())
    for dtime in dtimes:
        chan_sets = sorted(aOfDas[dtime].keys())
        for c in chan_sets:
            if c not in aOnChannels:
                aOnChannels[c] = []
            for entry in aOfDas[dtime][c]:
                aOnChannels[c].append(entry)

    # same structure of aOfDas but the times are combined if deploy time of
    # the current entry is exactly the same as the pickup time of the previous
    # one:    # {dtime: {c:[combined entry] } }
    aOnDeployTimes = {}
    for c in aOnChannels:
        prevPickupTime = 0
        currDeployTime = 0
        dEntries = aOnChannels[c]
        for d in dEntries:
            deployTime = d['deploy_time/epoch_l']
            if deployTime > prevPickupTime:
                currDeployTime = deployTime
                if deployTime not in aOnDeployTimes:
                    aOnDeployTimes[deployTime] = {}
                if c not in aOnDeployTimes[deployTime]:
                    aOnDeployTimes[deployTime][c] = [d]
            else:
                uEntry = aOnDeployTimes[currDeployTime][c][0]
                msg = "Das %s - %s - station %s - chan %s: " % (
                    d['das/serial_number_s'], aName,
                    d['id_s'], d['channel_number_i'])
                msg += "Combine %s"
                msg += ("entry [%s - %s] into previous entry [%s - %s]" %
                        (d['deploy_time/ascii_s'],
                         d['pickup_time/ascii_s'],
                         uEntry['deploy_time/ascii_s'],
                         uEntry['pickup_time/ascii_s']))
                descr = ""
                if deployTime < prevPickupTime:
                    descr = "overlapping "
                msg %= descr
                LOGGER.warning(msg)
                uEntry['pickup_time/epoch_l'] = d['pickup_time/epoch_l']
                uEntry['pickup_time/ascii_s'] = d['pickup_time/ascii_s']
                uEntry['pickup_time/micro_seconds_i'] = d['pickup_time/'
                                                          'micro_seconds_i']
            prevPickupTime = d['pickup_time/epoch_l']
    return aOnDeployTimes


def writeINDEX():
    '''   Write /Experiment_g/Receivers_g/Index_t   '''
    global DAS_INFO, MAP_INFO, INDEX_T_DAS, INDEX_T_MAP

    dass = sorted(DAS_INFO.keys())

    for das in dass:
        di = {}
        mi = {}
        start = sys.maxsize
        stop = 0.
        dm = [(d, m) for d in DAS_INFO[das] for m in MAP_INFO[das]]
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

        EX.ph5_g_receivers.populateIndex_t(di)
        EX.ph5_g_maps.populateIndex_t(mi)

    rows, keys = EX.ph5_g_receivers.read_index()
    INDEX_T_DAS = Rows_Keys(rows, keys)

    rows, keys = EX.ph5_g_maps.read_index()
    INDEX_T_MAP = Rows_Keys(rows, keys)

    DAS_INFO = {}
    MAP_INFO = {}


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


def utmcsptolatlon(northing, easting):
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


def get_latlon(manu, th):
    try:
        if manu == 'FairfieldNodal':
            if UTM:
                #   UTM
                LAT, LON = utmcsptolatlon(th.lat/10., th.lon/10.)
            elif TSPF:
                #   Texas State Plane coordinates
                LAT, LON = txncsptolatlon(th.lat/10., th.lon/10.)
            else:
                LAT = th.lat / 10.
                LON = th.lon / 10.
        elif manu == 'SmartSolo':
            LAT = th.lat
            LON = th.lon
    except Exception as e:
        LOGGER.warning(
            "Failed to convert location: {0}.\n".format(
                e.message))

    return LAT, LON


def main():
    import time
    then = time.time()
    from numpy import append as npappend

    def prof():
        global RESP, INDEX_T_DAS, INDEX_T_MAP, SD, EXREC, MINIPH5, Das, SIZE,\
            ARRAY_T, RH, LAT, LON, F, TRACE_JSON, APPEND

        MINIPH5 = None
        ARRAY_T = {}

        def get_das(sd, warn=False):
            if sd.manufacturer == 'FairfieldNodal':
                #   Return line_station or das#[-9:]
                try:
                    das = "{0}X{1}".format(
                        sd.reel_headers.extended_headers[2].line_number,
                        sd.reel_headers.extended_headers[2].receiver_point)
                except Exception:
                    try:
                        das = "{0}X{1}".format(
                            sd.reel_headers.external_header.receiver_line,
                            sd.reel_headers.external_header.receiver_point)
                    except Exception:
                        das = "sn" + \
                              str(sd.reel_headers.general_header_blocks[0].
                                  manufactures_sn)
                        if das == 0:
                            das = "id" + \
                                  str(sd.reel_headers
                                      .extended_headers[0].id_number)[-9:]
            elif sd.manufacturer == 'SmartSolo':
                line_number = sd.trace_headers.line_number
                receiver_point = sd.trace_headers.receiver_point
                if line_number == -1:
                    if warn:
                        LOGGER.warning(
                            "Line number is using invalid default value -1. "
                            "Using 1 instead.")
                    line_number = 1
                if receiver_point == -1:
                    if warn:
                        LOGGER.warning(
                            "Receiver point (stationID) is using invalid "
                            "default value -1. Using 1 instead.")
                    receiver_point = 1
                das = "{0}X{1}".format(line_number, receiver_point)
                # das = sd.id_number

            return das

        def get_node(sd):
            #   Return node part number, node id, and number of channels
            pn = None  # Part Number
            id = None  # Node ID
            nc = None  # Number of channel sets
            try:
                nc = sd.reel_headers.general_header_blocks[0][
                    'chan_sets_per_scan']
                id = sd.id_number
                if sd.manufacturer == 'FairfieldNodal':
                    pn = sd.reel_headers.extended_headers[0]['part_number']
            except Exception:
                pass
            return pn, id, nc

        try:
            get_args()
        except Exception as err_msg:
            LOGGER.error(err_msg)
            return 1

        initializeExperiment()
        LOGGER.info("segd2ph5 {0}".format(PROG_VERSION))
        LOGGER.info("{0}".format(sys.argv))
        if len(FILES) > 0:
            RESP = Resp(EX.ph5_g_responses)
            rows, keys = EX.ph5_g_receivers.read_index()
            INDEX_T_DAS = Rows_Keys(rows, keys)
            rows, keys = EX.ph5_g_maps.read_index()
            INDEX_T_MAP = Rows_Keys(rows, keys)

        for f in FILES:
            F = f
            traces = []
            TRACE_JSON = []
            try:
                SIZE = os.path.getsize(f)
            except Exception as e:
                LOGGER.error("Failed to read {0}, {1}.\
                 Skipping...\n".format(f, str(e.message)))
                continue
            try:
                segd_reader = get_segdreader(f, MANUFACTURERS_CODE)
            except Exception:
                continue
            SD = segd_reader.Reader(infile=f)
            LAT = None
            LON = None
            RH = False

            try:
                SD.process_general_headers()
                SD.process_channel_set_descriptors()
                SD.process_extended_headers()
                SD.process_external_headers()
                if SD.manufacturer == 'SmartSolo':
                    SD.process_trace_headers()
            except segdreader.InputsError as e:
                LOGGER.error(
                    "Possible bad SEG-D file -- {0}".format(
                        "".join(e.message)))
                continue

            nleft = APPEND
            Das = get_das(SD, warn=True)
            if not Das.isalnum():
                LOGGER.error(
                    "DAS %s is not alphanumeric. Can't process." % Das)
                return 1
            part_number, node_id, number_of_channels = get_node(SD)
            EXREC = get_current_data_only(SIZE, Das)
            LOGGER.info(":<Processing>: {0}\n".format(SD.name()))
            LOGGER.info(
                "Processing: {0}... Size: {1}\n".format(SD.name(), SIZE))
            if EXREC.filename != MINIPH5:
                LOGGER.info("Opened: {0}...\n".format(EXREC.filename))
                if node_id is None:
                    node_id_str = ''
                else:
                    node_id_str = ', Node ID: %s' % node_id
                LOGGER.info(
                    "DAS: {0}{1}, PN: {2}, Channels: {3}".format(
                        Das, node_id_str, part_number, number_of_channels))
                MINIPH5 = EXREC.filename

            n = 0
            trace_index = 0
            trace_headers_list = []
            while True:
                if SD.isEOF():
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
                        process_traces(SD.reel_headers, thl[0], t)
                        if DAS_INFO:
                            writeINDEX()
                    break

                try:
                    trace, cs = SD.process_trace(trace_index)
                    trace_index += 1
                except segdreader.InputsError as e:
                    LOGGER.error("{0}\n".format(F))
                    LOGGER.error(
                        "Possible bad SEG-D file -- {0}".format(
                            "".join(e.message)))
                    break

                if not LAT and not LON:
                    LAT, LON = get_latlon(SD.manufacturer, SD.trace_headers)

                trace_headers_list.append(SD.trace_headers)
                if n == 0:
                    traces.append(Trace(trace, SD.trace_headers))
                    n = 1
                    Das = get_das(SD)
                else:
                    traces.append(Trace(trace, SD.trace_headers))

                if n >= nleft or EVERY is True:
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
                            if isinstance(t, type(None)):
                                t = T.trace
                            else:
                                t = npappend(t, T.trace)
                        else:
                            new_traces.append(T)
                            if chan_set_next is None:
                                chan_set_next =\
                                    T.headers.trace_header.channel_set

                    traces = new_traces
                    process_traces(SD.reel_headers, thl[0], t)
                    if new_traces:
                        nleft = APPEND - len(new_traces)
                    else:
                        nleft = APPEND
                    chan_set = chan_set_next
                    chan_set_next = None
                    if DAS_INFO:
                        writeINDEX()
                    n = 0
                    trace_headers_list = []
                    continue

                n += 1

            update_external_references()
            if TRACE_JSON:
                log_array, name = getLOG()
                for line in TRACE_JSON:
                    log_array.append(line)

            LOGGER.info(":<Finished>: {0}\n".format(F))
        write_arrays(SD, ARRAY_T)
        seconds = time.time() - then

        try:
            EX.ph5close()
            EXREC.ph5close()
        except Exception as e:
            LOGGER.warning("{0}\n".format("".join(e.message)))

        # need to do this after close EX and EXREC so all info are pushed
        reorder_das(PH5)
        LOGGER.info("Done...{0:b}".format(int(seconds / 6.)))
        logging.shutdown()

    prof()


if __name__ == '__main__':
    main()
