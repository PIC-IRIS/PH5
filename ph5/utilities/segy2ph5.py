#!/usr/bin/env pnpython3
#
# Program to read a standard SEG-Y file and load it into a PH5 file.
#
# Steve Azevedo, May 2013
#
# Last modified to work with geod SEG-Y, May 2014
#

import argparse
import os
import sys
import logging
import time
import json
from math import modf
from ph5 import LOGGING_FORMAT
from ph5.core import experiment, columns, segyreader, timedoy

PROG_VERSION = "2024.227"
LOGGER = logging.getLogger(__name__)
DEPRECATION_WARNING = (
    'segy2ph5 is no longer supported by the PH5 software. '
    'Please use different functions to format data as PH5.\n\n'
    'To force running the command anyway, please use flag --force\n\n')

MAX_PH5_BYTES = 1073741824 * .5  # 1/2GB (1024 X 1024 X 1024 X .5)
DAS_INFO = {}
MAP_INFO = {}

# SEG-Y Reel Header 3255-3256
MFEET = {0: 'Unknown', 1: 'meters', 2: 'feet'}
# SEG-Y Trace Header 89-90
CUNITS = {0: 'Unknown', 1: MFEET, 2: 'seconds',
          3: 'degrees', 4: 'degrees,minutes,seconds'}
TTYPE = {'S': 'SEG-Y', 'U': 'Menlo',
         'P': 'PASSCAL', 'I': 'SioSeis', 'N': 'iNova'}
DTYPE = {1: 'float32', 2: 'int32', 3: 'int16', 5: 'float32', 8: 'int8'}

os.environ['TZ'] = 'GMT'
time.tzset()


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


def get_args():
    global SR, TYPE, PRINT, L, T, F, ENDIAN, EBCDIC, PH5, RECV_ORDER, DAS,\
        SIZE, CHAN3

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = ("segy2ph5 --nickname=ph5-file-prefix"
                    " [options]\nIMPORTANT: {0}".format(DEPRECATION_WARNING))

    parser.description = ("Read a standard SEG-Y file and load it into a "
                          "PH5 file.\n\nVersion: {0}"
                          .format(PROG_VERSION))

    parser.add_argument("-f",
                        action="store",
                        dest="infile",
                        type=str,
                        help="Input SEG-Y file.")

    parser.add_argument("-n", "--nickname",
                        dest="outfile",
                        help="The ph5 file prefix (experiment nick name).",
                        metavar="output_file_prefix",
                        required=True)

    parser.add_argument("-S", "--recv-order",
                        dest="recvorder",
                        help="The SEG-Y input file is in receiver order.",
                        action="store_true",
                        default=False)

    parser.add_argument("-t",
                        action="store",
                        dest="ttype",
                        choices=['U', 'P', 'S', 'N', 'I'],
                        default='S',
                        help="Extended trace header style. U => USGS Menlo, "
                             "P => PASSCAL, S => SEG, I => SIOSEIS, "
                             "N => iNova FireFly")

    parser.add_argument("-p",
                        action="store_true",
                        dest="print_true",
                        default=False)

    parser.add_argument("-L",
                        action="store",
                        dest="bytes_per_trace",
                        type=int,
                        help="Force bytes per trace. Overrides header values.")

    parser.add_argument("-T", action="store", dest="traces_per_ensemble",
                        type=int,
                        help="Force traces per ensemble. Overrides header "
                             "value.")

    parser.add_argument("-F", action="store", dest="trace_format", type=int,
                        help="1 = IBM - 4 bytes, 2 = INT - 4 bytes, "
                             "3 = INT - 2 bytes, 5 = IEEE - 4 bytes, "
                             "8 = INT - 1 byte. Override header value.")

    parser.add_argument("-e",
                        action="store",
                        dest="endian",
                        type=str,
                        default='big',
                        help="Endianess: 'big' or 'little'. "
                             "Default = 'big'. Override header value.")

    parser.add_argument("-i",
                        action="store_false",
                        dest="ebcdic",
                        default=True,
                        help="EBCDIC textural header. Override header value.")

    parser.add_argument("-d",
                        action="store",
                        dest="das",
                        type=int,
                        help="Set station ID for all traces, "
                             "otherwise field trace number is used.")

    parser.add_argument("-3",
                        action="store_true",
                        dest="chan3",
                        default=False,
                        help="The gather contains data recorded using 3 "
                             "channels, 1, 2, 3.")

    parser.add_argument("--force", dest="force_run",
                        help="Force to run the command.",
                        action="store_true", default=False)

    args = parser.parse_args()
    if not args.force_run:
        LOGGER.warning(DEPRECATION_WARNING)
        sys.exit()

    try:
        SIZE = os.path.getsize(args.infile)
        SR = segyreader.Reader(args.infile)
        SR.open_infile()
        if SR.FH is None:
            raise IOError()
    except Exception as e:
        LOGGER.error("Can't open infile (SEG-Y). {0}".format(e))
        sys.exit()

    # Set extended header type
    if args.ttype is not None:
        SR.set_ext_hdr_type(args.ttype)

    # Set output file
    PH5 = args.outfile
    # Is this gather in receiver order?
    RECV_ORDER = args.recvorder
    # Print contents of gather as ASCII
    PRINT = args.print_true
    # 3 channel data?
    CHAN3 = args.chan3

    if args.bytes_per_trace is not None:
        # Override bytes per trace from values in trace and bin headers
        L = args.bytes_per_trace

    if args.traces_per_ensemble is not None:
        # Override traces per ensemble in bin header
        T = args.traces_per_ensemble

    if args.trace_format is not None:
        # Override value in bin header
        F = args.trace_format

    DAS = args.das
    # 'big' or 'little' endian?
    ENDIAN = args.endian
    SR.set_endianess(ENDIAN)
    # Is text header EBCDIC or ASCII?
    EBCDIC = args.ebcdic
    if EBCDIC is True:
        SR.set_txt_hdr_type('E')
    else:
        SR.set_txt_hdr_type('A')
        # Write log to file
        ch = logging.FileHandler(os.path.join(".", "segy2ph5.log"))
        ch.setLevel(logging.INFO)
        # Add formatter
        formatter = logging.Formatter(LOGGING_FORMAT)
        ch.setFormatter(formatter)
        LOGGER.addHandler(ch)


def reopenPH5s():
    global EX, EXREC

    def reopen(ex):
        filename = ex.filename
        ex.ph5close()
        ex = experiment.ExperimentGroup(nickname=filename)
        ex.ph5open(True)
        ex.initgroup()
        return ex

    EX = reopen(EX)
    EXREC = reopen(EXREC)


def initializeExperiment():
    '''   Open PH5 file, master.ph5   '''
    global EX, PH5

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


def print_header(hdr, keys=None):
    '''   Print hdr to stdout   '''
    if keys is None:
        keys = sorted(hdr.keys())

    for k in keys:
        print "{0:<25}{1:<72}".format(k, hdr[k])

    print '-' * 80


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
        name, description="SEG-Y header entries: {0}".format(Das))

    return log_array, name


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


def get_current_data_only(size_of_data, das=None):
    '''   Return opened file handle for data only PH5 file that will be
          less than MAX_PH5_BYTES after raw data is added to it.
    '''

    newest = 0
    newestfile = ''
    # Get the most recent data only PH5 file or match DAS serialnumber
    for index_t in INDEX_T_DAS.rows:
        # This DAS already exists in a ph5 file
        if index_t['serial_number_s'] == das:
            newestfile = index_t['external_file_name_s']
            newestfile = newestfile.replace('.ph5', '')
            newestfile = newestfile.replace('./', '')
            return openPH5(newestfile)
        # Find most recent ph5 file
        if index_t['time_stamp/epoch_l'] > newest:
            newest = index_t['time_stamp/epoch_l']
            newestfile = index_t['external_file_name_s']
            newestfile = newestfile.replace('.ph5', '')
            newestfile = newestfile.replace('./', '')

    if not newestfile:
        # This is the first file added
        return openPH5('miniPH5_00001')

    size_of_exrec = os.path.getsize(newestfile + '.ph5')
    if (size_of_data + size_of_exrec) > MAX_PH5_BYTES:
        newestfile = "miniPH5_{0:05d}".format(int(newestfile[8:13]) + 1)

    return openPH5(newestfile)


def read_extended_headers(th):
    '''   Read extended textural headers as per SEG-Y rev 1.0   '''
    ret = []
    ret.append(th)

    if SR.number_of_extended_text_headers == -1:
        while True:
            th = SR.read_text_header()
            ret.append(th)
            if PRINT:
                print_header(th)
            if SR.last_extended_header(th):
                break
    elif SR.number_of_extended_text_headers > 0:
        for n in range(SR.number_of_extended_text_headers):
            th = SR.read_text_header()
            ret.append(th)
            if PRINT:
                print_header(th)

    return ret


def set_from_binary_header(bh):
    '''   Set some things from the binary header we might need later.   '''
    # Format of trace sample
    SR.set_trace_fmt(bh['format'])
    # Number of traces per ensemble
    SR.set_traces_per_ensemble(bh['ntrpr'])
    # Number of aux traces per ensemble
    SR.set_aux_traces_per_ensemble(bh['nart'])
    # Number of samples per trace
    SR.set_samples_per_trace(bh['hns'])
    # Sample rate
    SR.set_sample_rate(bh['hdt'])
    # SEG-Y revision
    SR.set_segy_revision(bh['rev'])
    # Number of extended textural headers
    SR.set_number_of_extended_text_headers(bh['extxt'])
    #
    SR.set_bytes_per_sample()


def update_external_references():
    '''   Update external references in master.ph5 to miniPH5 files in
          Receivers_t    '''
    global EX

    LOGGER.info("Updating external references...")
    n = 0
    for i in INDEX_T_DAS.rows:
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
            LOGGER.error("DAS nuke - {0}".format(e))

        # Re-create node
        try:
            EX.ph5.create_external_link(
                '/Experiment_g/Receivers_g', external_group, target)
            n += 1
        except Exception as e:
            LOGGER.error("{0}\n".format(e))

    LOGGER.info("done, {0} das nodes recreated.\n".format(n))

    n = 0
    for i in INDEX_T_MAP.rows:
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
                '/Experiment_g/Maps_g', external_group, target)
            n += 1
        except Exception as e:
            LOGGER.error("{0}\n".format(e))
    LOGGER.info("done, {0} map nodes recreated.\n".format(n))


def read_trace():
    '''   Read SEG-Y trace header and trace data   '''
    if SR.isEOF():
        return None, None, None

    th = SR.read_trace_header()
    if not th:
        return None, None, None
    eh = SR.read_extended_header()
    tr = SR.read_trace(SR.samples_per_trace, SR.bytes_per_sample)
    # Trace header, extended trace header, trace
    return th, eh, tr


#
# Input: th => Textural header
#        bh => Binary header
#        rh => Trace header
#        eh => Extended trace header
#        tr => Trace
#


def process_trace(th, bh, rh, eh, tr):
    global ARRAY_T, EVENT_T

    # If samples per second is less than 1,
    # return int sample rate with appropriate divisor
    def as_ints(v):
        if v >= 1:
            return int(v), 1

        mult = 10.0
        while mult < 10000:
            r = v * mult
            f, i = modf(r)
            if f * 1000.0 < 1.0:
                return int(i), int(mult)

            mult *= 10.0

        return None, None

    def writeLog():
        '''   Save textural header under Receivers_g/Das_g as Log_a_   '''
        global EXREC

        # Check to see if any data has been written
        if EXREC.ph5_g_receivers.current_g_das is None or\
                EXREC.ph5_g_receivers.current_t_das is None:
            return

        name = EXREC.ph5_g_receivers.nextarray('Log_a_')
        data = []
        for t in th:
            keys = sorted(t.keys())
            for k in keys:
                line = "{0} {1:<80}".format(k, t[k])
                data.append(line)

        EXREC.ph5_g_receivers.newarray(
            name, data, description="SEG-Y textural header")

    def process_binary_header():
        '''   Save reel header information in
              Maps_g/Das_g_xxxxxxx/Hdr_a_xxxx file   '''
        log_array, log_name = getLOG()
        # Standard header
        keys = sorted(bh.keys())
        # ell zero
        l0 = {}
        for k in keys:
            l0[k] = bh[k]

        ll = [{'FileType': 'SEG-Y', 'HeaderType': 'reel'}, l0]

        log_array.append(json.dumps(ll, sort_keys=True, indent=4).split('\n'))

    def process_trace_header():
        '''   Save trace header information in
              Maps_g/Das_g_xxxxxxx/Hdr_a_xxxx file   '''
        log_array, log_name = getLOG()
        # Standard header
        keys = sorted(rh.keys())
        # ell zero
        l0 = {}
        for k in keys:
            l0[k] = rh[k]

        # Portion of header after byte 180
        keys = eh.keys()
        keys.sort()
        # ell one
        l1 = {}
        for k in keys:
            l1[k] = eh[k]

        ht = TTYPE[SR.ext_hdr_type]
        ll = [{'FileType': 'SEG-Y', 'HeaderType': 'trace',
               'HeaderSubType': ht},
              l0, l1]

        log_array.append(json.dumps(ll, sort_keys=True, indent=4).split('\n'))

    def process_event():
        # Process channel 1 (Z)
        if rh['lineSeq'] != 1:
            return

        # Have we already seen this event?
        if rh['event_number'] in EVENT_T:
            return

        p_event_t = {}

        p_event_t['id_s'] = rh['event_number']
        year = rh['year']
        doy = rh['day']
        hour = rh['hour']
        minute = rh['minute']
        seconds = rh['second']
        delay_time_secs = rh['delay'] / 1000.
        if SR.ext_hdr_type == 'U':
            # Menlo USGS
            year = eh['shot_year']
            doy = eh['shot_doy']
            hour = eh['shot_hour']
            minute = eh['shot_minute']
            seconds = eh['shot_second']
            p_event_t['time/micro_seconds_i'] = eh['shot_us']
            delay_time_secs = 0.0
        elif SR.ext_hdr_type == 'P':
            # PASSCAL
            year = eh['trigyear']
            doy = eh['trigday']
            hour = eh['trighour']
            minute = eh['trigminute']
            seconds = eh['trigsecond']
            p_event_t['time/micro_seconds_i'] = int(eh['trigmills'] / 1000.)
            delay_time_secs = 0.0
        else:
            p_event_t['time/micro_seconds_i'] = 0

        tdoy = timedoy.TimeDOY(year=year,
                               month=None,
                               day=None,
                               hour=hour,
                               minute=minute,
                               second=seconds,
                               microsecond=0,
                               doy=doy,
                               epoch=None,
                               dtobject=None)

        tmp_epoch = tdoy.epoch() + delay_time_secs
        f, i = modf(tmp_epoch)
        p_event_t['time/epoch_l'] = int(i)
        p_event_t['time/micro_seconds_i'] = int(f / 1000000.)
        p_event_t['time/ascii_s'] = time.ctime(p_event_t['time/epoch_l'])
        p_event_t['time/type_s'] = 'BOTH'

        if SR.ext_hdr_type == 'S':
            # SEG
            if eh['Spn'] != 0:
                p_event_t['id_s'] = eh['Spn']
        elif SR.ext_hdr_type == 'I':
            # iNova
            if eh['ShotID'] != 0:
                p_event_t['id_s'] = eh['ShotID']
        else:
            # As used by PIC
            if rh['energySourcePt'] != 0:
                p_event_t['id_s'] = rh['energySourcePt']

        coordScale = rh['coordScale']
        if coordScale < 0:
            coordScale = -1. / coordScale

        if rh['coordUnits'] == 1:
            units = MFEET[bh['mfeet']]
        else:
            units = CUNITS[rh['coordUnits']]

        elevationScale = rh['elevationScale']
        if elevationScale < 0:
            elevationScale = -1. / elevationScale

        p_event_t['location/X/value_d'] = rh['sourceLongOrX'] * coordScale
        p_event_t['location/X/units_s'] = units

        p_event_t['location/Y/value_d'] = rh['sourceLatOrY'] * coordScale
        p_event_t['location/Y/units_s'] = units

        p_event_t['location/Z/value_d'] =\
            rh['sourceSurfaceElevation'] * elevationScale
        p_event_t['location/Z/units_s'] = MFEET[bh['mfeet']]

        p_event_t['depth/value_d'] = rh['sourceDepth'] * elevationScale
        p_event_t['depth/units_s'] = MFEET[bh['mfeet']]

        if p_event_t['id_s'] not in EVENT_T:
            EVENT_T[p_event_t['id_s']] = []

        EVENT_T[p_event_t['id_s']].append(p_event_t)

    def process_array():
        '''   Save station meta-data   '''
        global FIRST_TIME, LAST_TIME
        p_array_t = {}
        p_array_t['id_s'] = str(int(rh['channel_number']) & 0x7FFF)
        p_array_t['das/serial_number_s'] = Das
        p_array_t['channel_number_i'] = p_das_t['channel_number_i']
        coordScale = rh['coordScale']
        if coordScale < 0:
            coordScale = -1. / coordScale

        if rh['coordUnits'] == 1:
            units = MFEET[bh['mfeet']]
        else:
            units = CUNITS[rh['coordUnits']]

        p_array_t['location/X/value_d'] = rh['recLongOrX'] * coordScale
        p_array_t['location/X/units_s'] = units
        p_array_t['location/Y/value_d'] = rh['recLatOrY'] * coordScale
        p_array_t['location/Y/units_s'] = units
        elevationScale = rh['elevationScale']
        if elevationScale < 0:
            elevationScale = -1. / elevationScale

        p_array_t['location/Z/value_d'] = rh['datumElevRec'] * elevationScale
        p_array_t['location/Z/units_s'] = MFEET[bh['mfeet']]

        year = rh['year']
        doy = rh['day']
        hour = rh['hour']
        minute = rh['minute']
        seconds = rh['second']
        tdoy = timedoy.TimeDOY(year=year,
                               month=None,
                               day=None,
                               hour=hour,
                               minute=minute,
                               second=seconds,
                               microsecond=0,
                               doy=doy,
                               epoch=None,
                               dtobject=None)
        if SR.ext_hdr_type == 'U':
            # Menlo USGS
            p_array_t['deploy_time/micro_seconds_i'] = eh['start_usec']
            p_array_t['pickup_time/micro_seconds_i'] = eh['start_usec']
        elif SR.ext_hdr_type == 'P':
            # PASSCAL
            p_array_t['deploy_time/micro_seconds_i'] = int(
                eh['m_secs'] / 1000.)
            p_array_t['pickup_time/micro_seconds_i'] = int(
                eh['m_secs'] / 1000.)
        else:
            p_array_t['deploy_time/micro_seconds_i'] = 0
            p_array_t['pickup_time/micro_seconds_i'] = 0

        samples = rh['sampleLength']
        sample_rate = (1. / rh['deltaSample']) * 1000000.
        sample_rate, factor = as_ints(sample_rate)
        sample_rate = sample_rate / factor

        p_array_t['deploy_time/epoch_l'] = tdoy.epoch()
        p_array_t['deploy_time/ascii_s'] = time.ctime(
            p_array_t['deploy_time/epoch_l'])
        p_array_t['deploy_time/type_s'] = 'BOTH'
        if p_array_t['deploy_time/epoch_l'] < FIRST_TIME:
            FIRST_TIME = p_array_t['deploy_time/epoch_l'] + \
                         (p_array_t['deploy_time/micro_seconds_i'] / 1000000.)

        seconds = int(modf(samples / sample_rate)
                      [1]) + p_array_t['deploy_time/epoch_l']
        usec = int(modf(samples / sample_rate)[0] * 1000000.)
        p_array_t['pickup_time/micro_seconds_i'] += usec
        if p_array_t['pickup_time/micro_seconds_i'] > 1000000:
            x = p_array_t['pickup_time/micro_seconds_i'] / 1000000.
            seconds += int(modf(x)[1])
            p_array_t['pickup_time/micro_seconds_i'] = int(
                modf(x)[0] * 1000000.)

        p_array_t['pickup_time/epoch_l'] = seconds
        p_array_t['pickup_time/ascii_s'] = time.ctime(seconds)
        p_array_t['pickup_time/type_s'] = 'BOTH'
        if p_array_t['pickup_time/epoch_l'] > LAST_TIME:
            LAST_TIME = p_array_t['pickup_time/epoch_l'] + \
                        (p_array_t['pickup_time/micro_seconds_i'] / 1000000.)

        ffid = rh['event_number']
        if ffid not in ARRAY_T:
            ARRAY_T[ffid] = []

        ARRAY_T[ffid].append(p_array_t)

    def process_das():
        '''   Save trace data   '''
        p_response_t = {}
        # Make Data_a and fill in Das_t
        global EXREC, MINIPH5

        EXREC = get_current_data_only(SIZE, Das)
        if EXREC.filename != MINIPH5:
            LOGGER.info("Opened: {0}...\n".format(EXREC.filename))
            MINIPH5 = EXREC.filename

        # This is gain in dB since it is from SEG-Y
        try:
            p_response_t['gain/value_i'] = rh['gainConst']
            p_response_t['gain/units_s'] = 'dB'
            p_response_t['bit_weight/value_d'] = rh['traceWeightingFactor']
            p_response_t['bit_weight/units_s'] = 'Unknown'
            n_i = RESP.match(
                p_response_t['bit_weight/value_d'],
                p_response_t['gain/value_i'])
            if n_i < 0:
                n_i = RESP.next_i()
                p_response_t['n_i'] = n_i
                EX.ph5_g_responses.populateResponse_t(p_response_t)
                RESP.update()
        except Exception as e:
            LOGGER.warn("Bit weight or gain improperly "
                        "defined in SEG-Y file - {0}"
                        .format(e))

        # Check to see if group exists for this das, if not build it
        das_g, das_t, receiver_t, time_t = EXREC.ph5_g_receivers.newdas(Das)
        # Build maps group (XXX)
        EXREC.ph5_g_maps.newdas('Das_g_', Das)
        p_das_t['array_name_log_a'] = EXREC.ph5_g_receivers.nextarray('Log_a_')
        p_das_t['response_table_n_i'] = n_i

        year = rh['year']
        doy = rh['day']
        hour = rh['hour']
        minute = rh['minute']
        seconds = rh['second']
        tdoy = timedoy.TimeDOY(year=year,
                               month=None,
                               day=None,
                               hour=hour,
                               minute=minute,
                               second=seconds,
                               microsecond=0,
                               doy=doy,
                               epoch=None,
                               dtobject=None)
        if SR.ext_hdr_type == 'U':
            # Menlo USGS
            p_das_t['time/micro_seconds_i'] = eh['start_usec']
        elif SR.ext_hdr_type == 'P':
            # PASSCAL
            p_das_t['time/micro_seconds_i'] = int(eh['m_secs'] / 1000.)
        else:
            p_das_t['time/micro_seconds_i'] = 0

        p_das_t['sample_count_i'] = rh['sampleLength']
        sample_rate = (1. / rh['deltaSample']) * 1000000.
        sample_rate, factor = as_ints(sample_rate)
        p_das_t['sample_rate_i'] = int(sample_rate)
        p_das_t['sample_rate_multiplier_i'] = factor

        p_das_t['time/epoch_l'] = tdoy.epoch()
        p_das_t['time/ascii_s'] = time.ctime(p_das_t['time/epoch_l'])
        p_das_t['time/type_s'] = 'BOTH'

        if rh['lineSeq'] == 0:
            rh['lineSeq'] = 1

        chan = 1
        if CHAN3:
            mm = rh['lineSeq'] % 3
            if mm == 0:
                chan = 3
            else:
                chan = mm

        p_das_t['channel_number_i'] = chan
        p_das_t['event_number_i'] = rh['event_number']
        p_das_t['array_name_data_a'] = EXREC.ph5_g_receivers.nextarray(
            'Data_a_')
        EXREC.ph5_g_receivers.populateDas_t(p_das_t)
        des = "Epoch: " + str(p_das_t['time/epoch_l']) + \
              " Channel: " + str(p_das_t['channel_number_i'])
        # Write trace data here
        EXREC.ph5_g_receivers.newarray(
            p_das_t['array_name_data_a'], tr, dtype=DTYPE[SR.trace_fmt],
            description=des)
        update_index_t_info(p_das_t['time/epoch_l'] + (
                    float(p_das_t['time/micro_seconds_i']) / 1000000.),
                            p_das_t['sample_count_i'],
                            p_das_t['sample_rate_i'] / p_das_t[
                                'sample_rate_multiplier_i'])

    p_das_t = {}
    process_das()
    process_array()
    process_event()
    if th:
        writeLog()
        process_binary_header()

    process_trace_header()

    return None


def clean_array(Array, latkey, lonkey):
    '''   Remove Array entries that are at the same location   '''
    tmp_array = {}
    skipped = 0
    lat = None
    lon = None
    fkeys = sorted(Array.keys())
    for f in fkeys:
        array = Array[f]
        for a in array:
            if lat is None:
                if f not in tmp_array:
                    tmp_array[f] = []

                lat = a[latkey]
                lon = a[lonkey]
                tmp_array[f].append(a)
                continue

            if a[latkey] == lat and a[lonkey] == lon:
                skipped += 1
                continue
            else:
                if f not in tmp_array:
                    tmp_array[f] = []

                lat = a[latkey]
                lon = a[lonkey]
                tmp_array[f].append(a)

    return skipped, tmp_array


def write_arrays(Array_t):
    '''   Write /Experiment_g/Sorts_g/Array_t_xxx   '''
    keys = sorted(Array_t.keys())
    for k in keys:
        name = EX.ph5_g_sorts.nextName()
        a = EX.ph5_g_sorts.newSort(name)
        for array_t in Array_t[k]:
            columns.populate(a, array_t)


def write_events(Event_t):
    '''   Write /Experiment_g/Sorts_g/Event_t   '''
    keys = sorted(Event_t.keys())
    for k in keys:
        a = EX.ph5_g_sorts.ph5_t_event
        for event_t in Event_t[k]:
            columns.populate(a, event_t)


def main():
    def prof():
        global INDEX_T_DAS, INDEX_T_MAP, RESP, EXREC, MINIPH5, ARRAY_T,\
            EVENT_T, FIRST_TIME, LAST_TIME, Das
        FIRST_TIME = sys.maxsize
        LAST_TIME = 0

        ARRAY_T = {}
        EVENT_T = {}

        MINIPH5 = None
        get_args()
        LOGGER.info("segy2ph5 Version: {0}".format(PROG_VERSION))
        LOGGER.info("Opened: {0}".format(SR.infile))
        LOGGER.info("{0}".format(repr(sys.argv)))
        initializeExperiment()
        RESP = Resp(EX.ph5_g_responses)
        rows, keys = EX.ph5_g_receivers.read_index()
        INDEX_T_DAS = Rows_Keys(rows, keys)
        rows, keys = EX.ph5_g_maps.read_index()
        INDEX_T_MAP = Rows_Keys(rows, keys)
        # Read text header
        th = SR.read_text_header()
        if PRINT is True:
            print_header(th)
        # Read binary header
        bh = SR.read_binary_header()
        # Save some things from binary header that we will refer to later
        set_from_binary_header(bh)
        if PRINT:
            print_header(bh)
        # Read extended headers (+ textural header) into list of dictionaries
        th = read_extended_headers(th)
        if PRINT is True and len(th) > 1:
            for h in th[1:]:
                print_header(h)

        ctr = 0
        while True:
            ctr += 1
            rh, eh, tr = read_trace()
            if not rh:
                break
            if PRINT is True:
                print_header(rh)
                print_header(eh)
                i = 0
                for s in tr:
                    print i, s
                    i += 1

            Das = 0
            if DAS is None:
                # This is the field trace number
                Das = str(int(rh['channel_number']) & 0x7FFFFFFF)
            else:
                # Set on the command line
                Das = str(DAS)

            if Das == 0:
                import random as r
                Das = str(int(r.triangular() * 1000000))

            # Process text header (th), binary header (bh), trace header (rh),
            # extended trace header (eh), trace (tr)
            th = process_trace(th, bh, rh, eh, tr)
            if DAS_INFO:
                writeINDEX()

        # Do this if its in receiver order
        askip, tmp_array_t = clean_array(
            ARRAY_T, 'location/Y/value_d', 'location/X/value_d')
        # Do this if its in shot order
        # XXX   This should clean based on time!!!   XXX
        eskip, tmp_event_t = clean_array(
            EVENT_T, 'location/Y/value_d', 'location/X/value_d')

        if RECV_ORDER:
            keys = tmp_array_t.keys()
            if len(keys) == 1:
                tmp_array_t[keys[0]][0]['deploy_time/epoch_l'] = FIRST_TIME
                tmp_array_t[keys[0]][0]['deploy_time/ascii_s'] =\
                    time.ctime(FIRST_TIME)
                tmp_array_t[keys[0]][0]['deploy_time/type_s'] = 'BOTH'

                tmp_array_t[keys[0]][0]['pickup_time/epoch_l'] = LAST_TIME
                tmp_array_t[keys[0]][0]['pickup_time/ascii_s'] =\
                    time.ctime(LAST_TIME)
                tmp_array_t[keys[0]][0]['pickup_time/type_s'] = 'BOTH'

            write_arrays(tmp_array_t)
            write_events(EVENT_T)
        else:
            write_arrays(tmp_array_t)
            write_events(EVENT_T)

        update_external_references()

        try:
            EX.ph5close()
            EXREC.ph5close()
        except Exception:
            pass

        LOGGER.info("Done...")

    # Entry point
    prof()


if __name__ == '__main__':
    main()
