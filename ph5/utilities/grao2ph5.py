#!/usr/bin/env pnpython4
#
# A command line program to load MSEED data into a family of ph5 files.
# Can also read using web services.
#
# Steve Azevedo, June 2016
#
import os
import sys
import logging
import re
import time
import math
import obspy
from ph5 import LOGGING_FORMAT
from ph5.core import experiment, timedoy

PROG_VERSION = "2019.14"
LOGGER = logging.getLogger(__name__)

# Max size of each ph5 mini file
MAX_PH5_BYTES = 1073741824 * 6  # GB (1024 X 1024 X 1024 X 6)
# Band code to sample rate map
CHAN_SR_MAP = {'F': 5000, 'G': 5000, 'D': 1000, 'C': 1000, 'E': 250, 'S': 80,
               'H': 250, 'B': 80, 'M': 10, 'L': 1,
               'V': 0.1, 'U': 0.01, 'R': 0.001, 'P': 0.0001, 'T': 0.00001,
               'Q': 0.000001, 'A': None, 'O': None}
LAST_SAMPLE_RATE = 250
# Factor between mseed and PH5 file size: mseed_size * SIZE_FACTOR = PH5_size
SIZE_FACTOR = 1.0
DEBUG = False

miniPH5RE = re.compile(r".*miniPH5_(\d\d\d\d\d)\.ph5")

DAS_INFO = {}


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


def read_infile(infile):
    global FILES
    try:
        fh = file(infile)
    except BaseException:
        LOGGER.warning("Warning: Failed to open %s\n" % infile)
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


def get_args():
    ''' Parse input args
           -f   file containing list of raw files
           -n   output file
           -p   print out table list
           -M   create a specific number of miniPH5 files
           -S   First index of miniPH5_xxxxx.ph5
    '''
    global FILES, PH5, SR, NUM_MINI, FIRST_MINI

    import argparse

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)
    parser.usage = ("Version {0} grao2ph5 [--help][--raw raw_file | "
                    "--file file_list_file] --nickname output_file_prefix"
                    .format(PROG_VERSION))
    parser.description = ("Load MSEED data into a family of ph5 files. "
                          "Can also read using web services.")
    parser.add_argument("-f", "--file", dest="infile",
                        help=("File containing list of:\nWS:net_code:station:"
                              "location:channel:deploy_time:pickup_time:"
                              "length."),
                        metavar="file_list_file")
    parser.add_argument("-n", "--nickname", dest="outfile",
                        help="The ph5 file prefix (experiment nick name).",
                        metavar="output_file_prefix", required=True)
    parser.add_argument("-M", "--num_mini", dest="num_mini",
                        help=("Create a given number of miniPH5_xxxxx.ph5"
                              "files."),
                        metavar="num_mini", type=int, default=None)
    parser.add_argument("-S", "--first_mini", dest="first_mini",
                        help="The index of the first miniPH5_xxxxx.ph5 file.",
                        metavar="first_mini", type=int, default=1)
    parser.add_argument("-s", "--samplerate", dest="samplerate",
                        help="Extract only data at given sample rate.",
                        metavar="samplerate")
    parser.add_argument("-p",
                        help="Do print",
                        dest="doprint",
                        action="store_true",
                        default=False)
    args = parser.parse_args()

    FILES = []
    PH5 = args.outfile
    SR = args.samplerate
    NUM_MINI = args.num_mini
    FIRST_MINI = args.first_mini

    if args.infile is not None:
        read_infile(args.infile)

    if not os.path.exists(PH5) and not os.path.exists(PH5 + '.ph5'):
        LOGGER.error("Error: {0} does not exist!".format(PH5))
        sys.exit()
    else:
        # Write log to file
        ch = logging.FileHandler(os.path.join(".", "grao2ph5.log"))
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
    for index_t in INDEX_T.rows:
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


def update_external_references():
    global EX, INDEX_T

    LOGGER.info("Updating external references...")
    n = 0
    for i in INDEX_T.rows:
        external_file = i['external_file_name_s'][2:]
        external_path = i['hdf5_path_s']
        i['serial_number_s']
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
    LOGGER.info("done, {0} nodes recreated.\n".format(n))


def update_index_t_info(starttime, samples, sps):
    global DAS_INFO
    ph5file = EXREC.filename
    ph5path = '/Experiment_g/Receivers_g/' + \
              EXREC.ph5_g_receivers.current_g_das._v_name
    das = ph5path[32:]
    stoptime = starttime + (float(samples) / float(sps))
    di = Index_t_Info(das, ph5file, ph5path, starttime, stoptime)
    if das not in DAS_INFO:
        DAS_INFO[das] = []

    DAS_INFO[das].append(di)
    LOGGER.info(
        "DAS: {0} File: {1} First Sample: {2} Last Sample: {3}".format(
            das, ph5file, time.ctime(starttime), time.ctime(stoptime)))


def writeINDEX():
    global DAS_INFO, INDEX_T

    dass = sorted(DAS_INFO.keys())

    for das in dass:
        i = {}
        start = sys.maxsize
        stop = 0.
        das_info = DAS_INFO[das]
        for d in das_info:
            i['external_file_name_s'] = d.ph5file
            i['hdf5_path_s'] = d.ph5path
            i['serial_number_s'] = das
            if d.startepoch < start:
                start = d.startepoch

            if d.stopepoch > stop:
                stop = d.stopepoch

        i['time_stamp/epoch_l'] = int(time.time())
        i['time_stamp/micro_seconds_i'] = 0
        i['time_stamp/type_s'] = 'BOTH'
        i['time_stamp/ascii_s'] = time.ctime(i['time_stamp/epoch_l'])

        i['start_time/epoch_l'] = int(math.modf(start)[1])
        i['start_time/micro_seconds_i'] = int(math.modf(start)[0] * 1000000)
        i['start_time/type_s'] = 'BOTH'
        i['start_time/ascii_s'] = time.ctime(start)

        i['end_time/epoch_l'] = math.modf(stop)[1]
        i['end_time/micro_seconds_i'] = int(math.modf(stop)[0] * 1000000)
        i['end_time/type_s'] = 'BOTH'
        i['end_time/ascii_s'] = time.ctime(stop)

        EX.ph5_g_receivers.populateIndex_t(i)

    rows, keys = EX.ph5_g_receivers.read_index()
    INDEX_T = Rows_Keys(rows, keys)

    DAS_INFO = {}


def updatePH5(stream):
    global EXREC, CURRENT_DAS, LAST_SAMPLE_RATE
    CHAN_MAP = {"EL1": 1, "EL2": 2, "ELZ": 3, "EDH": 4, "HH1": 1,
                "HH2": 2, "HHZ": 3, "HDH": 4, "BHE": 1, "BHN": 2, "BHZ": 3}
    size_guess = SIZE_GUESS
    for trace in stream:
        p_das_t = {}
        p_response_t = {}
        try:
            EXREC.ph5close()
        except BaseException:
            pass
        LAST_SAMPLE_RATE = trace.stats.sampling_rate
        CURRENT_DAS = trace.stats.station
        size_of_data = len(trace.data) * SIZE_FACTOR
        if size_guess < size_of_data:
            size_guess = size_of_data
        EXREC = get_current_data_only(size_guess)
        size_guess -= size_of_data

        # The gain and bit weight
        p_response_t['gain/value_i'] = 1
        p_response_t['bit_weight/units_s'] = 'volts/count'
        p_response_t['bit_weight/value_d'] = 1

        n_i = RESP.match(
            p_response_t['bit_weight/value_d'], p_response_t['gain/value_i'])
        if n_i < 0:
            n_i = RESP.next_i()
            p_response_t['n_i'] = n_i
            EX.ph5_g_responses.populateResponse_t(p_response_t)
            RESP.update()

        # Check to see if group exists for this das, if not build it
        EXREC.ph5_g_receivers.newdas(CURRENT_DAS)
        # Fill in das_t
        p_das_t['raw_file_name_s'] = F
        p_das_t['response_table_n_i'] = n_i
        p_das_t['channel_number_i'] = CHAN_MAP[trace.stats.channel]
        p_das_t['sample_count_i'] = trace.stats.npts
        p_das_t['sample_rate_i'] = trace.stats.sampling_rate
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


def get_das(f):
    try:
        h = obspy.read(f, format="MSEED", headonly=True)
        return h[0].stats.station
    except Exception as e:
        LOGGER.error(
            ":<Error>: {0}. Can't process {1}".format(e.message, f))
        return None


def get_ds(network, station, location, channel, starttime, length):
    from obspy.clients.fdsn import Client

    t0 = obspy.core.UTCDateTime(starttime)
    t1 = t0 + length
    try:
        c = Client(base_url='http://service.iris.edu',
                   user="azevedo@passcal.nmt.edu",
                   password="haL8muerte",
                   timeout=20,
                   debug=DEBUG)
    except Exception as e:
        print e.message
    try:
        stream = None
        stream = c.get_waveforms(network,
                                 station,
                                 location,
                                 channel,
                                 t0, t1)
    except Exception as e:
        print t0, t1
        print e.message

    return stream


def main():
    global RESP, INDEX_T, CURRENT_DAS, SIZE_GUESS, F

    get_args()
    initializeExperiment()
    LOGGER.info("grao2ph5 {0}".format(PROG_VERSION))
    LOGGER.info("{0}".format(sys.argv))

    if len(FILES) > 0:
        RESP = Resp(EX.ph5_g_responses)
        rows, keys = EX.ph5_g_receivers.read_index()
        INDEX_T = Rows_Keys(rows, keys)

    for f in FILES:
        F = f
        LOGGER.info("Processing: %s..." % f)

        if f[0] == '#':
            continue
        if f[:3] == 'WS,':
            flds = f.split(',')
            if len(flds) != 8:
                continue
            deploy_flds = map(float, flds[5].split(':'))
            pickup_flds = map(float, flds[6].split(':'))
            tdoy0 = timedoy.TimeDOY(year=int(deploy_flds[0]),
                                    hour=int(deploy_flds[2]),
                                    minute=int(deploy_flds[3]),
                                    second=deploy_flds[4],
                                    doy=int(deploy_flds[1]))
            tdoyN = timedoy.TimeDOY(year=int(pickup_flds[0]),
                                    hour=int(pickup_flds[2]),
                                    minute=int(pickup_flds[3]),
                                    second=pickup_flds[4],
                                    doy=int(pickup_flds[1]))
            SIZE_GUESS = (tdoyN.epoch() - tdoy0.epoch()) * LAST_SAMPLE_RATE
            # WS:net_code:station:location:channel:deploy_time:pickup_time:length
            start_time = tdoy0.getFdsnTime()
            while True:
                if timedoy.delta(tdoy0, tdoyN) <= 0:
                    break
                stream = get_ds(flds[1], flds[2], flds[3],
                                flds[4], start_time, int(flds[7]))
                if stream is not None:
                    LOGGER.info(
                        "Adding stream for {0}:{3} starting at {1} and ending\
                        at {2} to PH5".format(
                            stream[0].stats.station,
                            stream[0].stats.starttime,
                            stream[0].stats.endtime,
                            stream[0].stats.channel))
                    updatePH5(stream)
                else:
                    LOGGER.info(
                        "No data found for {0} at {1}.".format(flds[2],
                                                               start_time))
                    time.sleep(3)
                e = tdoy0.epoch(fepoch=True) + int(flds[7])
                tdoy0 = timedoy.TimeDOY(epoch=e)
                start_time = tdoy0.getFdsnTime()

        update_external_references()
        LOGGER.info(":<Finished>: {0}\n".format(f))


if __name__ == '__main__':
    main()
