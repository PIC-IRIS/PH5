#!/usr/bin/env pnpython3

#
# Read rt-125 or rt-125a files and convert to ph5.
#
# Steve Azevedo, Sept 2006, July 2012
#

import argparse
import logging
import math
import os
import os.path
import re
import string
import sys
import time
from ph5 import LOGGING_FORMAT
from ph5.core import columns, experiment, kef, pn125, timedoy

PROG_VERSION = '2019.14'
LOGGER = logging.getLogger(__name__)

MAX_PH5_BYTES = 1073741824 * 2  # GB (1024 X 1024 X 1024 X 2)
INDEX_T = None

TRDfileRE = re.compile(r".*[Ii](\d\d\d\d)[Rr][Aa][Ww].*")
TRDfileREpunt = re.compile(r".*(\d\d\d\d).*[Tt][Rr][Dd]$")
miniPH5RE = re.compile(r".*miniPH5_(\d\d\d\d\d)\.ph5")

CURRENT_DAS = None
DAS_INFO = {}
# Current raw file processing
F = None

os.environ['TZ'] = 'GMT'
time.tzset()

#
# To hold table rows and keys
#


class Rows_Keys (object):
    __slots__ = ('rows', 'keys')

    def __init__(self, rows=[], keys=None):
        self.rows = rows
        self.keys = keys

    def set(self, rows=None, keys=None):
        if rows is not None:
            self.rows = rows
        if keys is not None:
            self.keys = keys


class Index_t_Info (object):
    __slots__ = ('das', 'ph5file', 'ph5path', 'startepoch', 'stopepoch')

    def __init__(self, das, ph5file, ph5path, startepoch, stopepoch):
        self.das = das
        self.ph5file = ph5file
        self.ph5path = ph5path
        self.startepoch = startepoch
        self.stopepoch = stopepoch


class Resp (object):
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
        LOGGER.warning("Failed to open %s" % infile)
        return

    while True:
        line = fh.readline()
        if not line:
            break
        line = string.strip(line)
        if not line:
            continue
        if line[0] == '#':
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
            LOGGER.error("Error in window file: %s" % line)
            continue

        ttuple = flds[0].split(':')
        if len(ttuple) != 5:
            LOGGER.error("Error in window file: %s" % flds[0])
            continue

        try:
            tDOY = timedoy.TimeDOY(year=ttuple[0],
                                   month=None,
                                   day=None,
                                   hour=ttuple[2],
                                   minute=ttuple[3],
                                   second=ttuple[4],
                                   microsecond=0,
                                   doy=ttuple[1],
                                   epoch=None)
            start_secs = tDOY.epoch()
            stop_secs = int(flds[1]) + start_secs
        except Exception as e:
            LOGGER.error("Error in window file: {0}\n{1}".format(line, e))
            continue

        w.append([start_secs, stop_secs])

    return w


def get_args():
    ''' Parse input args
           -r   raw file
           -f   file containing list of raw files
           -n   output file
           -k   kef file   # REMOVED
           -d   dep file   # REMOVED
           -p   print out table list
           -M   create a specific number of miniPH5 files
           -S   First index of miniPH5_xxxxx.ph5
    '''
    global FILES, PH5, SR, WINDOWS, OVERIDE, NUM_MINI, FIRST_MINI

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)
    parser.usage = ("Version {0} 125a2ph5 [--help][--raw raw_file | "
                    "--file file_list_file] --nickname output_file_prefix"
                    .format(PROG_VERSION))
    parser.description = ("Read a raw texan files and optionally a kef "
                          "file into ph5 format.")
    parser.epilog = ("Notice: Data of a Das can't be stored in more than one "
                     "mini file.")

    file_group = parser.add_mutually_exclusive_group()
    file_group.add_argument("-r", "--raw", dest="rawfile",
                            help="RT-125(a) texan raw file",
                            metavar="raw_file")
    file_group.add_argument("-f", "--file", dest="infile",
                            help=("File containing list of RT-125(a) "
                                  "raw file names."),
                            metavar="file_list_file")

    parser.add_argument("-o", "--overide", dest="overide",
                        help="Overide file name checks.",
                        action="store_true", default=False)
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
                              "process. Window start time Window length, "
                              "seconds\n "
                              "-----------------   ----\n "
                              "YYYY:JJJ:HH:MM:SS   SSSS"),
                        metavar="windows_file")
    parser.add_argument("-p",
                        help="Do print",
                        dest="doprint",
                        action="store_true",
                        default=False)
    args = parser.parse_args()

    FILES = []
    PH5 = None
    OVERIDE = args.overide
    SR = args.samplerate
    NUM_MINI = args.num_mini
    FIRST_MINI = args.first_mini

    if args.infile is not None:
        read_infile(args.infile)

    elif args.rawfile is not None:
        FILES.append(args.rawfile)

    if args.outfile is not None:
        PH5 = args.outfile

    if args.doprint is not False:
        ex = experiment.ExperimentGroup()
        ex.ph5open(True)
        ex.initgroup()
        keys(ex)
        ex.ph5close()
        sys.exit()

    if args.windows_file is not None:
        WINDOWS = read_windows_file(args.windows_file)
    else:
        WINDOWS = None

    if PH5 is None:
        LOGGER.error("Missing required option. Try --help\n")
        sys.exit()

    if not os.path.exists(PH5) and not os.path.exists(PH5 + '.ph5'):
        LOGGER.error("{0} not found.".format(PH5))
        sys.exit()
    else:
        # Set up logging
        # Write log to file
        ch = logging.FileHandler(os.path.join('.', "125a2ph5.log"))
        ch.setLevel(logging.INFO)
        # Add formatter
        formatter = logging.Formatter(LOGGING_FORMAT)
        ch.setFormatter(formatter)
        LOGGER.addHandler(ch)


def print_it(a):
    for k in a:
        print("\t" + k)


def keys(ex):
    # Under Experiment_g/Experiment_t
    experiment_table, j = columns.keys(ex.ph5_t_experiment)
    # Under Experiment_g/Sorts_g/Sort_t
    sort_table, j = columns.keys(ex.ph5_g_sorts.ph5_t_sort)
    ex.ph5_g_sorts.newSort('001')
    # Under Experiment_g/Sorts_g/Array_t
    k = ex.ph5_g_sorts_ph5_t_array.keys()
    if k:
        sort_array_table, j = columns.keys(
            ex.ph5_g_sorts.ph5_t_array[k[0]])
    # Under Experiment_g/Sorts_g/Offset_t
    k = ex.ph5_g_sorts.ph5_t_offset.keys()
    if k:
        sort_offset_table, j = columns.keys(
            ex.ph5_g_sorts.ph5_t_offset[k[0]])
    # Under Experiment_g/Sorts_g/Event_t
    k = ex.ph5_g_sorts.ph5_t_event.keys()
    if k:
        sort_event_table, j = columns.keys(
            ex.ph5_g_sorts.ph5_t_event[k[0]])
    ex.ph5_g_receivers.newdas('9999')
    g = ex.ph5_g_receivers.getdas_g('9999')
    # Under Experiment_g/Receivers_g/Das_g_9999/Das_t
    das_table, j = columns.keys(g.Das_t)
    # Under Experiment_g/Receivers_g/das_g_9999/Receiver_t
    receiver_table, j = columns.keys(g.Receiver_t)
    time_table, j = columns.keys(g.Time_t)
    # Under Experiment_g/Reports_g/[title]/
    report_table, j = columns.keys(ex.ph5_g_reports.ph5_t_report)
    # Under Experiment_g/Responses_g/Responses_t
    response_table, j = columns.keys(ex.ph5_g_responses.ph5_t_response)

    print("\t\t\t\t\t\t\t\tPH5 TABLE KEYS\n")

    print("/Experiment_g/Experiment_t")
    print_it(experiment_table)

    print("/Experiment_g/Receivers_g/Das_g_[sn]/Das_t")
    print_it(das_table)

    print("/Experiment_g/Receivers_g/Das_g_[sn]/Receiver_t")
    print_it(receiver_table)

    print("/Experiment_g/Receivers_g/Das_g_[sn]/Time_t")
    print_it(time_table)

    print("/Experiment_g/Sorts_g/Sort_t")
    print_it(sort_table)

    print("/Experiment_g/Sorts_g/Array_t_[nnn]")
    print_it(sort_array_table)

    print("/Experiment_g/Sorts_g/Offset_t")
    print_it(sort_offset_table)

    print("/Experiment_g/Sorts_g/Event_t")
    print_it(sort_event_table)

    print("/Experiment_g/Reports_g/Report_t")
    print_it(report_table)

    print("/Experiment_g/Responses_g/Response_t")
    print_it(response_table)


def initializeExperiment():
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
    EX.ph5close()
    try:
        EXREC.ph5close()
    except BaseException:
        pass


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
        (float(sample_count) / float(sample_rate)) + event_start_epoch)

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
    LOGGER.info("DAS: {0} File: {1} First Sample: {2} Last Sample: {3}"
                .format(das, ph5file, time.ctime(starttime),
                        time.ctime(stoptime)))


def writeEvent(trace, page):
    global EX, EXREC, RESP, SR
    p_das_t = {}
    p_response_t = {}

    if SR is not None:
        if trace.sampleRate != int(SR):
            return

    das_number = str(page.unitID)

    # The gain and bit weight
    p_response_t['gain/value_i'] = trace.gain
    p_response_t['bit_weight/units_s'] = 'volts/count'
    p_response_t['bit_weight/value_d'] = 10.0 / trace.gain / trace.fsd

    n_i = RESP.match(
        p_response_t['bit_weight/value_d'], p_response_t['gain/value_i'])
    if n_i < 0:
        n_i = RESP.next_i()
        p_response_t['n_i'] = n_i
        EX.ph5_g_responses.populateResponse_t(p_response_t)
        RESP.update()

    # Check to see if group exists for this das, if not build it
    das_g, das_t, receiver_t, time_t = EXREC.ph5_g_receivers.newdas(das_number)
    # Fill in das_t
    p_das_t['raw_file_name_s'] = os.path.basename(F)
    p_das_t['array_name_SOH_a'] = EXREC.ph5_g_receivers.nextarray('SOH_a_')
    p_das_t['response_table_n_i'] = n_i
    p_das_t['channel_number_i'] = trace.channel_number
    p_das_t['event_number_i'] = trace.event
    p_das_t['sample_count_i'] = trace.sampleCount
    p_das_t['sample_rate_i'] = trace.sampleRate
    p_das_t['sample_rate_multiplier_i'] = 1
    p_das_t['stream_number_i'] = trace.stream_number
    tDOY = timedoy.TimeDOY(year=trace.year,
                           month=None,
                           day=None,
                           hour=trace.hour,
                           minute=trace.minute,
                           second=int(trace.seconds),
                           microsecond=0,
                           doy=trace.doy,
                           epoch=None)

    p_das_t['time/epoch_l'] = tDOY.epoch()
    # XXX   need to cross check here   XXX
    p_das_t['time/ascii_s'] = time.asctime(
        time.gmtime(p_das_t['time/epoch_l']))
    p_das_t['time/type_s'] = 'BOTH'
    # XXX   Should this get set????   XXX
    p_das_t['time/micro_seconds_i'] = 0
    # XXX   Need to check if array name exists and generate unique name.   XXX
    p_das_t['array_name_data_a'] = EXREC.ph5_g_receivers.nextarray('Data_a_')
    des = "Epoch: " + str(p_das_t['time/epoch_l']) + \
        " Channel: " + str(trace.channel_number)
    # XXX   This should be changed to handle exceptions   XXX
    EXREC.ph5_g_receivers.populateDas_t(p_das_t)
    # Write out array data (it would be nice if we had int24) we use int32!
    EXREC.ph5_g_receivers.newarray(
        p_das_t['array_name_data_a'],
        trace.trace, dtype='int32', description=des)
    update_index_t_info(p_das_t['time/epoch_l'] +
                        (float(p_das_t['time/micro_seconds_i']) / 1000000.),
                        p_das_t['sample_count_i'], p_das_t['sample_rate_i'] /
                        p_das_t['sample_rate_multiplier_i'])


def writeSOH(soh):
    global EXREC

    # Check to see if any data has been written
    if EXREC.ph5_g_receivers.current_g_das is None or\
       EXREC.ph5_g_receivers.current_t_das is None:
        return

    name = EXREC.ph5_g_receivers.nextarray('SOH_a_')
    data = []
    for el in soh:
        line = "%04d:%03d:%02d:%02d:%4.2f -- %s" % (
            el.year, el.doy, el.hour, el.minute, el.seconds, el.message)
        data.append(line)

    EXREC.ph5_g_receivers.newarray(
        name, data, description="Texan State of Health")


def writeET(et):
    '''   '''
    global EXREC

    # Check to see if any data has been written
    if EXREC.ph5_g_receivers.current_g_das is None or\
       EXREC.ph5_g_receivers.current_t_das is None:
        return

    name = EXREC.ph5_g_receivers.nextarray('Event_a_')
    data = []
    for el in et:
        line = "%04d:%03d:%02d:%02d:%02d %d %d" % (
            el.year, el.doy, el.hour, el.minute,
            el.seconds, el.action, el.parameter)
        data.append(line)

    EXREC.ph5_g_receivers.newarray(name, data, description="Texan Event Table")


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
            newestfile = "miniPH5_{0:05d}"\
                .format(int(newestfile[8:13]) + 1)
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
    global EX, EXREC
    sys.stdout.write(":<Processing>: {0}\n".format(f))
    sys.stdout.flush()
    LOGGER.info("Processing: %s..." % f)
    size_of_data = os.path.getsize(f) * 1.250
    try:
        EXREC.ph5close()
    except BaseException:
        pass

    EXREC = get_current_data_only(size_of_data)
    pn = pn125.pn125(f)
    while True:
        try:
            points = pn.getEvent()
        except pn125.TRDError as e:
            LOGGER.error("\nTRD read error. {0}\n"
                         ":<Error>: {1}".format(e, f))
            break

        if points == 0:
            break

        if window_contained(pn.trace):
            writeEvent(pn.trace, pn.page)

    if DAS_INFO:
        writeINDEX()

    if len(pn.sohbuf) > 0:
        writeSOH(pn.sohbuf)

    if len(pn.eventTable) > 0:
        writeET(pn.eventTable)
    sys.stdout.write(":<Finished>: {0}\n".format(f))
    sys.stdout.flush()
    LOGGER.info(":<Finished>: {0}\n".format(f))


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
        i['serial_number_s']
        target = external_file + ':' + external_path
        external_group = external_path.split('/')[3]
        # Nuke old node
        try:
            group_node = EX.ph5.get_node(external_path)
            group_node.remove()
        except Exception as e:
            pass
            # print "E1 ", e

        # Re-create node
        try:
            EX.ph5.create_external_link(
                '/Experiment_g/Receivers_g', external_group, target)
            n += 1
        except Exception as e:
            LOGGER.info("{0}\n".format(e))
    LOGGER.info("done, {0} nodes recreated.\n".format(n))


def main():
    def prof():
        global PH5, KEFFILE, FILES, DEPFILE, RESP, INDEX_T, CURRENT_DAS, F

        get_args()

        initializeExperiment()
        LOGGER.info("125a2ph5 {0}".format(PROG_VERSION))
        LOGGER.info("{0}".format(sys.argv))
        if len(FILES) > 0:
            RESP = Resp(EX.ph5_g_responses)
            rows, keys = EX.ph5_g_receivers.read_index()
            INDEX_T = Rows_Keys(rows, keys)

        for f in FILES:
            F = f
            ma = TRDfileRE.match(f)
            if ma or OVERIDE:
                try:
                    if ma:
                        CURRENT_DAS = int(ma.groups()[0]) + 10000
                    else:
                        ma = TRDfileREpunt.match(f)
                        if ma:
                            CURRENT_DAS = int(ma.groups()[0]) + 10000
                        else:
                            raise Exception()
                except BaseException:
                    CURRENT_DAS = None

                updatePH5(f)
            else:
                LOGGER.error(f)
                LOGGER.warning(
                    "Warning: Unrecognized raw file name {0}. Skipping!"
                    .format(f))

        update_external_references()
        closePH5()
        logging.shutdown()
    prof()


if __name__ == '__main__':
    main()
