#!/usr/bin/env pnpython4

import argparse
import os
import sys
import warnings
import logging
import re
import time
import math
import json
from math import modf
from ph5 import LOGGING_FORMAT
from ph5.core import experiment, timedoy

from obspy import read as readSEG2

PROG_VERSION = "2021.97"
LOGGER = logging.getLogger(__name__)

MAX_PH5_BYTES = 1073741824 * 1.  # 1 GB (1024 X 1024 X 1024 X 2)
miniPH5RE = re.compile(r".*miniPH5_(\d\d\d\d\d)\.ph5")

DAS_INFO = {}
MAP_INFO = {}

SIZE_FACTOR = .4

FILE_BLOCK_KEYS = ("ACQUISITION_DATE", "ACQUISITION_TIME", "CLIENT", "COMPANY",
                   "GENERAL_CONSTANT",
                   "INSTRUMENT", "JOB_ID", "OBSERVER", "PROCESSING_DATE",
                   "PROCESSING_TIME",
                   "TRACE_SORT", "UNITS")


class Index_t_Info(object):
    __slots__ = ('das', 'ph5file', 'ph5path', 'startepoch', 'stopepoch')

    def __init__(self, das, ph5file, ph5path, startepoch, stopepoch):
        self.das = das
        self.ph5file = ph5file
        self.ph5path = ph5path
        self.startepoch = startepoch
        self.stopepoch = stopepoch


def read_infile(infile):
    global FILES
    try:
        fh = file(infile)
    except BaseException:
        LOGGER.warning("Failed to open %s" % infile)
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


class Rows_Keys(object):
    __slots__ = ('rows', 'keys')

    def __init__(self, rows=[], keys=None):
        self.rows = rows
        self.keys = keys

    def set(self, rows=None, keys=None):
        if rows is not None:
            self.rows = rows
        if keys is not None:
            self.keys = keys


def get_args():
    ''' Parse input args
           -f   file containing list of raw files
           -n   output file
           -p   print out table list
           -M   create a specific number of miniPH5 files
           -S   First index of miniPH5_xxxxx.ph5
    '''
    global FILES, PH5, NUM_MINI, FIRST_MINI, PATH

    parser = argparse.ArgumentParser()
    parser.usage = "Version %s seg2toph5 [--help][--raw raw_file |\
        --file file_list_file] --nickname output_file_prefix" % PROG_VERSION
    parser.description = "Read data in SEG-2 revision 1 (StrataVisor)\
        into ph5 format."
    parser.epilog = "Notice: Data of a Das can't be stored in more than one \
        mini file."

    file_group = parser.add_mutually_exclusive_group()
    file_group.add_argument("-r", "--raw", dest="rawfile",
                            help="SEG-2 raw file", metavar="raw_file")
    file_group.add_argument("-f", "--file", dest="infile",
                            help=("File containing list of absolute paths "
                                  "to SEG-2 file."),
                            metavar="file_list_file")

    parser.add_argument("-n", "--nickname", dest="outfile",
                        help="The ph5 file prefix (experiment nick name).",
                        metavar="output_file_prefix")
    parser.add_argument("-M", "--num_mini",
                        help=("Create a given number of miniPH5 files."
                              " Ex: -M 38"),
                        metavar="num_mini", type=int, default=None)
    parser.add_argument("-S", "--first_mini",
                        help=("The index of the first miniPH5_xxxxx.ph5 "
                              "file of all. Ex: -S 5"),
                        metavar="first_mini", type=int, default=1)
    parser.add_argument("-p",
                        help="Do print",
                        dest="doprint",
                        action="store_true", default=False)
    args = parser.parse_args()

    FILES = []
    PH5 = None
    NUM_MINI = args.num_mini
    FIRST_MINI = args.first_mini

    if args.infile is not None:
        read_infile(args.infile)

    elif args.rawfile is not None:
        FILES.append(args.rawfile)

    if args.outfile is not None:
        PH5 = args.outfile

    if PH5 is None:
        LOGGER.error("Missing required option. Try --help")
        sys.exit()

    if not os.path.exists(PH5) and not os.path.exists(PH5 + '.ph5'):
        LOGGER.error("{0} does not exist!".format(PH5))
        sys.exit()
    else:
        PATH = os.path.dirname(PH5) or '.'
        # Debugging
        os.chdir(PATH)
        # Write log to file
        ch = logging.FileHandler(os.path.join(".", "seg2toph5.log"))
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
    LOGGER.info("Opening: {0}".format(filename))
    exrec = experiment.ExperimentGroup(nickname=filename)
    exrec.ph5open(True)
    exrec.initgroup()
    return exrec


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

    das = str(CURRENT_DAS)
    newestfile = ''
    # Get the most recent data only PH5 file or match DAS serialnumber
    n = 0
    for index_t in INDEX_T_DAS.rows:
        # This DAS already exists in a ph5 file
        if index_t['serial_number_s'] == das:
            newestfile = sstripp(index_t['external_file_name_s'])
            return openPH5(newestfile)
        # miniPH5_xxxxx.ph5 with largest xxxxx
        mh = miniPH5RE.match(index_t['external_file_name_s'])
        if n < int(mh.groups()[0]):
            newestfile = sstripp(index_t['external_file_name_s'])
            n = int(mh.groups()[0])

    if not newestfile:
        # This is the first file added
        mf = 'miniPH5_{0:05d}'.format(FIRST_MINI)
        return openPH5(mf)
    else:
        mf = newestfile + '.ph5'

    size_of_exrec = os.path.getsize(mf)
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


def update_external_references():
    LOGGER.info("Updating external references...")
    n = 0
    for i in INDEX_T_DAS.rows:
        external_file = i['external_file_name_s'][2:]
        external_path = i['hdf5_path_s']
        target = external_file + ':' + external_path
        external_group = external_path.split('/')[3]

        # Nuke old node
        try:
            group_node = EX.ph5.get_node(external_path)
            group_node.remove()
        except Exception as e:
            pass

        # Re-create node
        try:
            EX.ph5.create_external_link(
                '/Experiment_g/Receivers_g', external_group, target)
            n += 1
        except Exception as e:
            LOGGER.error(e)

    n = 0
    for i in INDEX_T_MAP.rows:
        external_file = i['external_file_name_s'][2:]
        external_path = i['hdf5_path_s']
        target = external_file + ':' + external_path
        external_group = external_path.split('/')[3]

        # Nuke old node
        try:
            group_node = EX.ph5.get_node(external_path)
            group_node.remove()
        except Exception as e:
            pass

        # Re-create node
        try:
            EX.ph5.create_external_link(
                '/Experiment_g/Maps_g', external_group, target)
            n += 1
        except Exception as e:
            LOGGER.error(e.message)
    LOGGER.info("Done, {0} nodes recreated.\n".format(n))


def update_index_t_info(starttime, samples, sps):
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


def writeINDEX():
    global DAS_INFO, MAP_INFO, INDEX_T_DAS, INDEX_T_MAP

    dass = sorted(DAS_INFO.keys())

    for das in dass:
        di = {}
        mi = {}
        start = sys.maxsize
        stop = 0.
        dm = [(d, m) for d in DAS_INFO[das] for m in MAP_INFO[das]]
        for d, m in dm:
            di['external_file_name_s'] = './' + os.path.basename(d.ph5file)
            mi['external_file_name_s'] = './' + os.path.basename(m.ph5file)
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

        di['start_time/epoch_l'] = int(math.modf(start)[1])
        mi['start_time/epoch_l'] = int(modf(start)[1])
        di['start_time/micro_seconds_i'] = int(math.modf(start)[0] * 1000000)
        mi['start_time/micro_seconds_i'] = int(modf(start)[0] * 1000000)
        di['start_time/type_s'] = 'BOTH'
        mi['start_time/type_s'] = 'BOTH'
        di['start_time/ascii_s'] = time.ctime(start)
        mi['start_time/ascii_s'] = time.ctime(start)

        di['end_time/epoch_l'] = math.modf(stop)[1]
        mi['end_time/epoch_l'] = modf(stop)[1]
        di['end_time/micro_seconds_i'] = int(math.modf(stop)[0] * 1000000)
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


def updatePH5(stream):
    global EXREC, CURRENT_DAS, LAST_SAMPLE_RATE, RESP

    def process(hdr, header_type):
        ''''''
        ll = [{'FileType': 'SEG-2', 'HeaderType': header_type}, hdr]
        log_array.append(json.dumps(ll, sort_keys=True, indent=4).split('\n'))

    RESP = Resp(EX.ph5_g_responses)
    size_guess = len(stream[0].data) * len(stream)
    for trace in stream:
        p_das_t = {}
        p_response_t = {}
        try:
            EXREC.ph5close()
        except BaseException:
            pass
        LAST_SAMPLE_RATE = trace.stats.sampling_rate

        try:
            CURRENT_DAS = "{0}SV{1:02d}".format(
                trace.stats.seg2['INSTRUMENT'].split(' ')[-1],
                int(trace.stats.seg2['CHANNEL_NUMBER']))
        except Exception as e:
            LOGGER.warn(
                "Can not set DAS serial number: {0}. Set to 0000SV00".format(
                    e.message))
            CURRENT_DAS = "0000SV00"

        size_of_data = len(trace.data) * SIZE_FACTOR
        if size_guess < size_of_data:
            size_guess = size_of_data
        EXREC = get_current_data_only(size_guess)
        size_guess -= size_of_data

        # The gain and bit weight
        try:
            gain, units = trace.stats.seg2['FIXED_GAIN'].split(' ')
        except KeyError:
            gain = 0
            units = 'DB'

        try:
            bw = (trace.stats.calib / float(trace.stats.seg2['STACK'])) * 1000.
        except KeyError:
            bw = trace.stats.calib * 1000.

        p_response_t['gain/value_i'] = int(gain)
        p_response_t['gain/units_s'] = units
        p_response_t['bit_weight/units_s'] = 'volts/count'
        p_response_t['bit_weight/value_d'] = bw

        n_i = RESP.match(
            p_response_t['bit_weight/value_d'], p_response_t['gain/value_i'])
        if n_i < 0:
            n_i = RESP.next_i()
            p_response_t['n_i'] = n_i
            EX.ph5_g_responses.populateResponse_t(p_response_t)
            RESP.update()

        # Check to see if group exists for this das, if not build it
        EXREC.ph5_g_receivers.newdas(CURRENT_DAS)
        # Update Maps_g
        fd = {}
        td = {}
        for k in trace.stats.seg2:
            if k in FILE_BLOCK_KEYS:
                # ObsPy does not know how to save the NOTE in the File
                # Descriptor Block!
                if k != 'NOTE':
                    fd[k] = trace.stats.seg2[k]
            else:
                if k != 'NOTE':
                    td[k] = trace.stats.seg2[k]
                else:
                    tdd = {}

                    if isinstance(trace.stats.seg2[k], list):
                        # list: Obspy 1.2.2
                        for j in trace.stats.seg2[k]:
                            k, v = j.split()
                            tdd[k] = v
                    else:
                        # AtribDict: Obspy 1.1.1
                        for j in trace.stats.seg2[k]:
                            tdd[j] = trace.stats.seg2[k][j]

                    td[k] = tdd

        log_array, name = getLOG(CURRENT_DAS)
        process(fd, "File Descriptor Block")
        process(td, "Trace Descriptor Block")
        log_array.close()
        # Fill in das_t
        p_das_t['raw_file_name_s'] = F
        p_das_t['response_table_n_i'] = n_i
        p_das_t['channel_number_i'] = 1
        p_das_t['sample_count_i'] = int(trace.stats.npts)
        p_das_t['sample_rate_i'] = int(trace.stats.sampling_rate)
        p_das_t['sample_rate_multiplier_i'] = 1

        tdoy = timedoy.UTCDateTime2tdoy(trace.stats.starttime)
        p_das_t['time/epoch_l'] = tdoy.epoch()
        # XXX   need to cross check here   XXX
        p_das_t['time/ascii_s'] = time.asctime(
            time.gmtime(p_das_t['time/epoch_l']))
        p_das_t['time/type_s'] = 'BOTH'
        # XXX   Should this get set????   XXX
        p_das_t['time/micro_seconds_i'] = tdoy.microsecond()
        # XXX   Need to check if array name exists and generate unique name.
        p_das_t['array_name_data_a'] = EXREC.ph5_g_receivers.nextarray(
            'Data_a_')
        des = "Epoch: " + str(p_das_t['time/epoch_l']) + \
              " Channel: " + trace.stats.channel
        # XXX   This should be changed to handle exceptions   XXX
        EXREC.ph5_g_receivers.populateDas_t(p_das_t)
        # Write out array data (it would be nice if we had int24) we use int32!
        EXREC.ph5_g_receivers.newarray(
            p_das_t['array_name_data_a'], trace.data, dtype='int32',
            description=des)
        update_index_t_info(p_das_t['time/epoch_l'] + (
                    float(p_das_t['time/micro_seconds_i']) / 1000000.),
                            p_das_t['sample_count_i'],
                            p_das_t['sample_rate_i'] / p_das_t[
                                'sample_rate_multiplier_i'])

    if DAS_INFO:
        writeINDEX()


def getLOG(Das):
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
        name, description="SEG-2 header entries: {0}".format(Das))
    log_array.set_attr('rowsize', 128)
    return log_array, name


def main():
    global F, RESP, INDEX_T_DAS
    get_args()
    import time
    then = time.time()
    initializeExperiment()
    LOGGER.info("seg2toph5 {0}".format(PROG_VERSION))
    LOGGER.info("{0}".format(sys.argv))

    if len(FILES) > 0:
        Resp(EX.ph5_g_responses)
        rows, keys = EX.ph5_g_receivers.read_index()
        INDEX_T_DAS = Rows_Keys(rows, keys)

    for f in FILES:
        F = f
        sys.stdout.write(":<Processing>: {0}\n".format(f))
        sys.stdout.flush()
        LOGGER.info("Processing: {0}...".format(f))
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                stream = readSEG2(f, format='SEG2')

            if stream is not None:
                LOGGER.info(
                    "Adding stream for {0}:{3} starting at {1} and ending at\
                     {2} to PH5".format(
                        stream[0].stats.station,
                        stream[0].stats.starttime,
                        stream[0].stats.endtime,
                        stream[0].stats.channel))
                updatePH5(stream)
            else:
                LOGGER.info("Failed to read: {0}.".format(f))
                LOGGER.error("Can't process {0}".format(f))
                continue
        except Exception as e:
            LOGGER.error(
                "{0}. Can't process {1}".format(e.message, f))
            continue
        update_external_references()
        sys.stdout.write(":<Finished>: {0}\n".format(f))
        sys.stdout.flush()
    seconds = time.time() - then
    print "Done...{0:b}".format(int(seconds / 6.))  # Minutes X 10
    LOGGER.info("Done...{0:b}".format(int(seconds / 6.)))
    try:
        EX.ph5close()
        EXREC.ph5close()
    except NameError:
        pass


if __name__ == '__main__':
    main()
