#!/usr/bin/env pnpython4

#
# Read rt-130 data into a ph5 file
#
# Steve Azevedo, November 2008, July 2012
#

import argparse
import sys
import logging
import os
import os.path
import string
import time
import math
import re
from ph5 import LOGGING_FORMAT
from ph5.core import experiment, kef, pn130, timedoy

PROG_VERSION = '2019.14'
LOGGER = logging.getLogger(__name__)

MAX_PH5_BYTES = 1073741824 * 4  # 2GB (1024 X 1024 X 1024 X 4)
NUM_CHANNELS = pn130.NUM_CHANNELS
NUM_STREAMS = pn130.NUM_STREAMS

ZIPfileRE = re.compile(
    r".*\d\d\d\d\d\d\.(\w\w\w\w)(\.\d\d)?\.[TtZz][AaIi][RrPp]")
RAWfileRE = re.compile(r".*(\w\w\w\w)\.[Cc][Ff]")
REFfileRE = re.compile(r".*(\w\w\w\w)\.[Rr][Ee][Ff]")
miniPH5RE = re.compile(r".*miniPH5_(\d\d\d\d\d)\.ph5")

CURRENT_DAS = None
DAS_INFO = {}
# Current raw file processing
F = None

VERBOSE = False
DEBUG = False

os.environ['TZ'] = 'UTC'
time.tzset()

if DEBUG:
    # change stream handler to write debug level logs
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)


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


def read_infile(infile):
    global FILES
    try:
        fh = file(infile)
    except BaseException:
        LOGGER.warning("Failed to open {0}".format(infile))
        return
    # Is this file ascii?
    try:
        fh.read().decode('ascii')
        fh.seek(0)
    except Exception:
        LOGGER.error(
            "The file containing a list of rt130 file names is not ASCII."
            " Use -r for a single raw file.")
        sys.exit()

    while True:
        line = fh.readline()
        if not line:
            break
        line = string.strip(line)
        if not line or line[0] == '#':
            continue
        if not os.path.exists(line):
            LOGGER.warning("File does not exist: {0}".format(line))
            continue

        FILES.append(line)


def read_windows_file(f):
    '''   Window start time   Window length
          YYYY:JJJ:HH:MM:SS   SSSS   '''
    w = []
    try:
        fh = open(f)
    except BaseException:
        return w

    while True:
        line = fh.readline()
        if not line:
            break
        line = line.strip()
        if not line or line[0] == '#':
            continue
        flds = line.split()
        if len(flds) != 2:
            LOGGER.error("Error in window file: {0}".format(line))
            continue

        ttuple = flds[0].split(':')
        if len(ttuple) != 5:
            LOGGER.error("Error in window file: {0}".format(flds[0]))
            continue

        tDOY = timedoy.TimeDOY(year=int(ttuple[0]),
                               month=None,
                               day=None,
                               hour=int(ttuple[2]),
                               minute=int(ttuple[3]),
                               second=int(ttuple[4]),
                               microsecond=0,
                               doy=int(ttuple[1]),
                               epoch=None)
        try:
            start_secs = tDOY.epoch()
            stop_secs = int(flds[1]) + start_secs
        except Exception as e:
            LOGGER.error("Error in window file: {0}\n{1}".format(line, e))
            continue

        w.append([start_secs, stop_secs])

    return w


class Par(object):
    __slots__ = (
        'das',
        'station',
        'loccode',
        'netcode',
        'channel',
        'refchan',
        'refstrm',
        'encoding',
        'samplerate',
        'gain')

    def __init__(self):
        self.das = None
        self.station = None
        self.loccode = None
        self.netcode = None
        self.channel = None
        self.refchan = None
        self.refstrm = None
        self.encoding = None
        self.samplerate = None
        self.gain = None


def get_order(line):
    '''   Reads order of fields in parameter file   '''
    order = {}
    line = line[1:]
    flds = string.split(line, ';')
    i = 0
    for f in flds:
        order[string.strip(f)] = i
        i += 1

    return order


def read_par_file(file):
    '''
       Read parameter file containing: das;station;netcode;channel;loccode;
       encoding;samplerate;gain
    '''
    global PARAMETERS
    PARAMETERS = {}
    try:
        fh = open(file)
    except BaseException:
        return False

    while True:
        line = fh.readline()
        if not line:
            break
        line = line[:-1]
        if line[0] == '#':
            order = get_order(line)
            # 'das', 'refchan', 'refstrm' form the key. All are required.
            if 'das' not in order:
                return False

            if 'refchan' not in order:
                return False

            if 'refstrm' not in order:
                return False

            continue

        flds = string.split(line, ';')

        if len(flds) != len(order.keys()):
            LOGGER.error('Error in parameter file: {}'.format(line))
            return False

        par = Par()
        # Key on DAS:refchan:refstrm
        id = "%s:%s:%s" % (string.strip(flds[order['das']]),
                           string.strip(flds[order['refchan']]),
                           string.strip(flds[order['refstrm']]))

        par.das = string.strip(flds[order['das']])
        par.refchan = string.strip(flds[order['refchan']])
        par.refstrm = string.strip(flds[order['refstrm']])
        if 'station' in order:
            par.station = string.strip(flds[order['station']])
        if 'netcode' in order:
            par.netcode = string.strip(flds[order['netcode']])
        if 'channel' in order:
            par.channel = string.strip(flds[order['channel']])
        if 'loccode' in order:
            par.loccode = string.strip(flds[order['loccode']])
        if 'encoding' in order:
            try:
                s = string.strip(flds[order['encoding']])
            except KeyError:
                LOGGER.error(
                    "Unknown encoding format in parameter file: {0}".format(s))
                return False
        if 'samplerate' in order:
            par.samplerate = string.strip(flds[order['samplerate']])
        if 'gain' in order:
            par.gain = string.strip(flds[order['gain']])

        PARAMETERS[id] = par

    return True


def get_args():
    ''' Parse input args
           -r   raw file
           -f   file containing list of raw files
           -o   output file
           -k   kef file   # REMOVED
           -d   dep file   # REMOVED
           -w   windows file
           -p   par_file
           -P   print out table list
           -v   be verbose
           -M   create a specific number of miniPH5 files
           -S   First index of miniPH5_xxxxx.ph5
    '''
    global FILES, PH5, WINDOWS, PARAMETERS, SR, NUM_MINI, VERBOSE, DEBUG
    global FIRST_MINI

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)
    parser.usage = ("1302ph5 [--help][--raw raw_file | --file file_list_file]"
                    " --nickname output_file_prefix")
    parser.description = ("Read a raw rt-130 files into ph5 format. v{0}"
                          .format(PROG_VERSION))
    parser.epilog = ("Notice: Data of a Das can't be stored in more than one "
                     "mini file.")

    file_group = parser.add_mutually_exclusive_group()
    file_group.add_argument("-r", "--raw", dest="rawfile",
                            help="RT-130 raw file", metavar="raw_file")
    file_group.add_argument(
        "-f", "--file", dest="infile",
        help="File containing list of RT-130 raw file names.",
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
    parser.add_argument("-s", "--samplerate", dest="samplerate",
                        help="Extract only data at given sample rate.",
                        metavar="samplerate")
    parser.add_argument("-w", "--windows_file", dest="windows_file",
                        help=("File containing list of time windows to "
                              "process. \n"
                              "Window start time   Window length, seconds\n"
                              "-----------------   ----\n"
                              "YYYY:JJJ:HH:MM:SS   SSSS"),
                        metavar="windows_file")
    parser.add_argument("-p", "--parfile", dest="par_file",
                        help=("[Used to set sample rate and gain in the case "
                              "of a missing event header.]\n"
                              "Parameter file used to set samplerate, gain.\n"
                              "The file contains colon separated lists.\n"
                              "The first line describes the order and the "
                              "first char must be '#'.\n"
                              "As example the first four lines could be:\n\n"
                              "9882; 1; 1; 40; x1\n"
                              "9882; 2; 1; 40; x1\n"
                              "9882; 2; 1; 40; x1\n"
                              "9882; 1; 2; 1; x32\n"
                              "9882; 2; 2; 1; x32\n"
                              "9882; 3; 2; 1; x32\n\n"
                              "Allowed fields: das;station;refchan;refstrm;"
                              "samplerate;gain"),
                        metavar="par_file")

    parser.add_argument("-P",
                        help="Do print",
                        dest="doprint",
                        action="store_true",
                        default=False)
    parser.add_argument("-v",
                        help="Verbose logging",
                        dest="verbose",
                        action="store_true",
                        default=False)
    parser.add_argument("-d",
                        help="Debug",
                        dest="debug",
                        action="store_true",
                        default=False)
    args = parser.parse_args()

    FILES = []
    PH5 = None
    SR = args.samplerate
    NUM_MINI = args.num_mini
    FIRST_MINI = args.first_mini
    VERBOSE = args.verbose
    DEBUG = args.debug
    if args.debug:
        VERBOSE = 2

    if args.infile is not None:
        read_infile(args.infile)

    elif args.rawfile is not None:
        FILES.append(args.rawfile)

    if args.outfile is not None:
        PH5 = args.outfile

    if args.windows_file is not None:
        WINDOWS = read_windows_file(args.windows_file)
    else:
        WINDOWS = None

    if args.doprint is not False:
        ex = experiment.ExperimentGroup()
        ex.ph5open(True)
        ex.initgroup()
        ex.ph5close()
        sys.exit()

    if args.par_file is not None:
        if not read_par_file(args.par_file):
            LOGGER.error("Failed to read: {0}".format(args.par_file))
            sys.exit()
    else:
        PARAMETERS = {}

    if PH5 is None:
        LOGGER.error("Missing required option. Try --help")
        sys.exit()

    if not os.path.exists(PH5) and not os.path.exists(PH5 + '.ph5'):
        LOGGER.error("{0} does not exist!".format(PH5))
        sys.exit()
    else:
        # Set up logging
        # Write log to file
        ch = logging.FileHandler(os.path.join('.', "1302ph5.log"))
        ch.setLevel(logging.INFO)
        # Add formatter
        formatter = logging.Formatter(LOGGING_FORMAT)
        ch.setFormatter(formatter)
        LOGGER.addHandler(ch)


def initializeExperiment(nickname):
    global EX, PH5

    EX = experiment.ExperimentGroup(nickname=PH5)
    EDIT = True
    EX.ph5open(EDIT)
    EX.initgroup()


def populateExperimentTable():
    global EX, KEFFILE
    k = kef.Kef(KEFFILE)
    k.open()
    k.read()
    k.batch_update()
    k.close()


def closePH5():
    global EX
    try:
        EX.ph5close()
        EXREC.ph5close()
    except BaseException:
        pass


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


def gwriteEvent(points, event):
    '''   Create an event list with all the gaps and overlaps cleansed   '''

    def clone(event):
        # Clone event list but without the traces
        clean_event = []
        for i in range(pn130.NUM_CHANNELS):
            clean_event.append(pn130.Event130())
            clean_event[i].bitWeight = event[i].bitWeight
            clean_event[i].channel_number = event[i].channel_number
            clean_event[i].doy = event[i].doy
            clean_event[i].event = event[i].event
            clean_event[i].gain = event[i].gain
            clean_event[i].hour = event[i].hour
            clean_event[i].last_sample_time = event[i].last_sample_time
            clean_event[i].milliseconds = event[i].milliseconds
            clean_event[i].minute = event[i].minute
            clean_event[i].sampleCount = event[i].sampleCount
            clean_event[i].sampleRate = event[i].sampleRate
            clean_event[i].seconds = event[i].seconds
            clean_event[i].stream_number = event[i].stream_number
            clean_event[i].trace = {}
            clean_event[i].unitID = event[i].unitID
            clean_event[i].year = event[i].year

        return clean_event

    clean_event = clone(event)
    for c in range(NUM_CHANNELS):
        if not event[c].unitID:
            continue
        sample_rate = event[c].sampleRate
        sample_interval = 1. / float(sample_rate)
        tdoy1 = None
        # Prepare new trace structure that allows us to break it up on gaps and
        # overlaps
        i = 0
        clean_event[c].trace[i] = []
        for t in event[c].trace:
            tdoy0 = timedoy.TimeDOY(year=t.year,
                                    month=None,
                                    day=None,
                                    hour=t.hour,
                                    minute=t.minute,
                                    second=int(t.seconds),
                                    microsecond=t.milliseconds * 1000,
                                    doy=t.doy,
                                    epoch=None)
            if tdoy1 is not None:
                # Start of this DT packet
                fepoch0 = tdoy0.epoch(fepoch=True)
                # Calculated start of packet from last DT packet
                fepoch1 = tdoy1.epoch(fepoch=True)
                delta = fepoch1 - fepoch0
                if delta < 0.:
                    i += 1
                    clean_event[c].trace[i] = []
                elif delta > 0.:
                    i += 1
                    clean_event[c].trace[i] = []

            clean_event[c].trace[i].append(t)
            num_samples = len(t.trace)
            secs = float(num_samples) * sample_interval
            tdoy1 = tdoy0 + secs
            event[c].trace = []

    writeEvent(points, clean_event)


def writeEvent(points, event):
    global EX, EXREC, RESP, SR
    p_das_t = {}
    p_response_t = {}

    if event is None:
        return

    def as_ints(v):
        if v >= 1:
            return int(v), 1

        mult = 10.0
        while mult < 10000:
            r = v * mult
            f, i = math.modf(r)
            if f * 1000.0 < 1.0:
                return int(i), int(mult)

            mult *= 10.0

        return None, None

    for c in range(NUM_CHANNELS):
        if not event[c].unitID:
            continue
        iis = sorted(event[c].trace.keys())
        for ii in iis:
            if SR is not None and event[c].sampleRate is not None:
                if float(event[c].sampleRate) != float(SR):
                    continue

            das_number = event[c].unitID
            if das_number is None or event[c].sampleCount == 0:
                continue

            try:
                if event[c].gain[0] == 'x':
                    # Gain times
                    gain = int(event[c].gain[1:])
                else:
                    # Gain dB
                    gain = int(event[c].gain[:-2])
            except Exception as e:
                LOGGER.warning(
                    "Can't determine gain from gain value '{0:s}'. "
                    "Exception: {1:s}".format(
                        event[c].gain, e))
                gain = 0

            # The gain and bit weight
            p_response_t['gain/value_i'] = gain
            try:
                p_response_t[
                    'bit_weight/units_s'] = '%s/count' % event[c].bitWeight[
                                                         -2:]
                p_response_t[
                    'bit_weight/value_d'] = float(event[c].bitWeight[:-2])

                n_i = RESP.match(
                    p_response_t['bit_weight/value_d'],
                    p_response_t['gain/value_i'])
                if n_i < 0:
                    RESP.update()
                    n_i = RESP.next_i()
                    p_response_t['n_i'] = n_i
                    EX.ph5_g_responses.populateResponse_t(p_response_t)
                    RESP.update()
            except Exception as e:
                LOGGER.error(
                    "Bit weight undefined. Can't convert '{1:s}'. "
                    "Exception: {0:s}".format(e, event[c].bitWeight))

            # Check to see if group exists for this das, if not build it
            das_g, das_t, receiver_t, time_t = EXREC.ph5_g_receivers.newdas(
                das_number)
            # Fill in das_t
            p_das_t['raw_file_name_s'] = os.path.basename(F)
            p_das_t['array_name_SOH_a'] = EXREC.ph5_g_receivers.nextarray(
                'SOH_a_')
            p_das_t['array_name_log_a'] = EXREC.ph5_g_receivers.nextarray(
                'Log_a_')
            p_das_t['response_table_n_i'] = n_i
            p_das_t['receiver_table_n_i'] = c
            p_das_t['channel_number_i'] = event[c].channel_number + 1
            p_das_t['event_number_i'] = event[c].event
            # force sample rate to 1 sps or greater
            irate, mult = as_ints(float(event[c].sampleRate))
            p_das_t['sample_rate_i'] = irate
            p_das_t['sample_rate_multiplier_i'] = mult
            p_das_t['sample_count_i'] = int(event[c].sampleCount)
            p_das_t['stream_number_i'] = event[c].stream_number + 1
            # Note: We use the time of the first trace. This is because rtleap
            # fix only changes DT packets!
            tDOY = timedoy.TimeDOY(year=event[c].trace[ii][0].year,
                                   month=None,
                                   day=None,
                                   hour=event[c].trace[ii][0].hour,
                                   minute=event[c].trace[ii][0].minute,
                                   second=int(event[c].trace[ii][0].seconds),
                                   microsecond=event[c].trace[
                                                   ii][0].milliseconds * 1000,
                                   doy=event[c].trace[ii][0].doy,
                                   epoch=None)
            p_das_t['time/epoch_l'] = tDOY.epoch(fepoch=False)
            # XXX   need to cross check here   XXX
            p_das_t[
                'time/ascii_s'] = time.asctime(
                time.gmtime(p_das_t['time/epoch_l']))
            p_das_t['time/type_s'] = 'BOTH'
            # XXX   Should this get set????   XXX
            p_das_t[
                'time/micro_seconds_i'] = event[c].trace[ii][
                                              0].milliseconds * 1000
            # XXX   Need to check if array name exists and generate unique
            # name.   XXX
            p_das_t['array_name_data_a'] = EXREC.ph5_g_receivers.nextarray(
                'Data_a_')
            # XXX   Write data   XXX
            t = event[c].trace[ii][0]
            if DEBUG:
                tcount = len(t.trace)
            earray = EXREC.ph5_g_receivers.newarray(
                p_das_t['array_name_data_a'], t.trace, dtype='int32')
            for t in event[c].trace[ii][1:]:
                if DEBUG:
                    tcount += len(t.trace)
                earray.append(t.trace)
            if DEBUG:
                LOGGER.debug(
                    "{0} SR: {1:12.2f}sps Channel: {2} Samples: {3}/{4}"
                    .format(
                        tDOY,
                        float(
                            irate) / float(mult),
                        p_das_t[
                            'channel_number_i'],
                        p_das_t[
                            'sample_count_i'],
                        tcount))
            # XXX   This should be changed to handle exceptions   XXX
            p_das_t['sample_count_i'] = earray.nrows
            EXREC.ph5_g_receivers.populateDas_t(p_das_t)
            if p_das_t['channel_number_i'] == 1:
                update_index_t_info(
                    p_das_t['time/epoch_l'] +
                    (
                            float(
                                p_das_t['time/micro_seconds_i']) /
                            1000000.),
                    p_das_t['sample_count_i'],
                    float(
                        p_das_t['sample_rate_i']) /
                    float(
                        p_das_t['sample_rate_multiplier_i']))


def writeSOH(soh):
    global EXREC

    # Check to see if any data has been written
    if EXREC.ph5_g_receivers.current_g_das is None or\
            EX.ph5_g_receivers.current_t_das is None:
        return

    name = EXREC.ph5_g_receivers.nextarray('SOH_a_')

    EXREC.ph5_g_receivers.newarray(
        name, soh, description="RT-130 State of Health")


def getSOH():
    global EXREC

    try:
        name = EXREC.ph5_g_receivers.nextarray('SOH_a_')
    except TypeError:
        return None
    except AttributeError:
        return None

    soh_array = EXREC.ph5_g_receivers.newearray(
        name, description="RT-130 SOH entries", expectedrows=30000)

    return soh_array


def getLOG():
    global EXREC

    try:
        name = EXREC.ph5_g_receivers.nextarray('Log_a_')
    except TypeError:
        return None
    except AttributeError:
        return None

    log_array = EXREC.ph5_g_receivers.newearray(
        name, description="RT-130 log entries", expectedrows=30000)

    return log_array


def window_contained(e):
    '''   Is this event in the data we want to keep?   '''
    global WINDOWS

    # We want to keep all the data
    if WINDOWS is None:
        return True

    if not e:
        return False

    sample_rate = e.sampleRate
    sample_count = e.sampleCount

    tDOY = timedoy.TimeDOY(year=e.year,
                           month=None,
                           day=None,
                           hour=e.hour,
                           minute=e.minute,
                           second=int(e.seconds),
                           microsecond=0,
                           doy=e.doy,
                           epoch=None)
    event_start_epoch = tDOY.epoch()
    event_stop_epoch = int(
        (float(sample_count) /
         float(sample_rate)) +
        event_start_epoch)

    for w in WINDOWS:
        window_start_epoch = w[0]
        window_stop_epoch = w[1]

        # Window start in event KEEP
        if event_start_epoch <= window_start_epoch and event_stop_epoch >=\
                window_start_epoch:
            return True
        # Entire event in window KEEP
        if event_start_epoch >= window_start_epoch and event_stop_epoch <=\
                window_stop_epoch:
            return True
        # Event stop in window KEEP
        if event_start_epoch <= window_stop_epoch and event_stop_epoch >=\
                window_stop_epoch:
            return True

    return False


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
    # newest = 0
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


def updatePH5(f):
    global EX, EXREC, VERBOSE, PARAMETERS
    global log_array, soh_array
    sys.stdout.write(":<Processing>: {0}\n".format(f))
    sys.stdout.flush()
    LOGGER.info("Processing: %s..." % f)
    size_of_data = os.path.getsize(f) * 1.40
    try:
        EXREC.ph5close()
    except BaseException:
        pass

    EXREC = get_current_data_only(size_of_data)
    log_array = None
    soh_array = None

    def ok_write_stream(stream, points):
        '''   Write all events in this stream   '''
        global log_array, soh_array

        events = pn.get_stream_event(stream)
        streams = events.keys()
        for s in streams:
            event = events[s]
            if not event:
                continue
            log = pn.get_logs()
            soh = pn.get_soh()
            errs = pn.get_errs()
            if len(errs) > 0:
                LOGGER.error("*" * 15 + "   ERRORS   " + "*" * 15)
                for e in errs:
                    LOGGER.error(e)
                LOGGER.error("*" * 15 + "   END   " + "*" * 15)

            if window_contained(event[0]):
                gwriteEvent(points, event)
                if log_array is None:
                    log_array = getLOG()
                    if log_array is None:
                        continue

                if soh_array is None:
                    soh_array = getSOH()
                    if soh_array is None:
                        continue

                if len(log) > 0:
                    log_array.append(log)

                if len(soh) > 0:
                    soh_array.append(soh)
            else:
                break

    def ok_write_stream_all():
        '''   Clean up batter   '''
        for s in range(pn130.NUM_STREAMS):
            if pn.current_event[s] is not None:
                pn.previous_event[s] = pn.current_event[s]
                pts = pn.points[s]
                ok_write_stream(s, pts)

    try:
        pn = pn130.PN130(f, verbose=int(VERBOSE), par=PARAMETERS)
    except Exception as e:
        LOGGER.error("Can't open {0}. {1}".format(f, e))
        return
    while True:
        try:
            stream, points, end = pn.getEvent()
        except pn130.REFError as e:
            LOGGER.error("REF read error. {0}"
                         ":<Error>: {1}".format(e, f))
            break
        # End of file
        if end is True:
            if points != 0:
                ok_write_stream_all()
            break
        # Corrupt packet
        if stream > NUM_STREAMS:
            break
        # Empty data packet
        if not points:
            continue
        ok_write_stream(stream, points)

    if DAS_INFO:
        writeINDEX()
    sys.stdout.write(":<Finished>: {0}\n".format(f))
    sys.stdout.flush()
    LOGGER.info(":<Finished>: {0}".format(f))


def ph5flush():
    global EX
    EX.ph5flush()


def update_external_references():
    global EX, INDEX_T
    LOGGER.info("Updating external references...")
    n = 0
    for i in INDEX_T.rows:
        external_file = i['external_file_name_s'][2:]
        external_path = i['hdf5_path_s']
        target = external_file + ':' + external_path
        external_group = external_path.split('/')[3]
        # Nuke old node
        try:
            group_node = EX.ph5.get_node(external_path)
            group_node.remove()
        except Exception:
            pass
        # Re-create node
        try:
            EX.ph5.create_external_link(
                '/Experiment_g/Receivers_g', external_group, target)
            n += 1
        except Exception:
            pass
    LOGGER.info("Done, {0} nodes recreated.".format(n))


def main():
    def prof():
        global PH5, KEFFILE, FILES, DEPFILE, RESP, INDEX_T, CURRENT_DAS, F
        get_args()
        LOGGER.info("Initializing ph5 file...")
        initializeExperiment(PH5)

        LOGGER.info("1302ph5 {0}".format(PROG_VERSION))
        LOGGER.info("{0}".format(sys.argv))

        fileprocessed = False
        if len(FILES) > 0:
            RESP = Resp(EX.ph5_g_responses)
            rows, keys = EX.ph5_g_receivers.read_index()
            INDEX_T = Rows_Keys(rows, keys)
            LOGGER.info("Processing RAW files...")
        for f in FILES:
            F = f
            for RE in (ZIPfileRE, RAWfileRE, REFfileRE):
                m = RE.match(f)
                if m:
                    break

            if m:
                try:
                    CURRENT_DAS = m.groups()[0]
                except BaseException:
                    CURRENT_DAS = None

                updatePH5(f)
            else:
                LOGGER.warning(
                    "Unrecognized raw file name {0}. Skipping!"
                    .format(f))

            closePH5()
            initializeExperiment(PH5)
            RESP = Resp(EX.ph5_g_responses)
            rows, keys = EX.ph5_g_receivers.read_index()
            INDEX_T = Rows_Keys(rows, keys)
            fileprocessed = True

        if fileprocessed:
            update_external_references()
        closePH5()
        logging.shutdown()
    prof()


if __name__ == '__main__':
    main()
