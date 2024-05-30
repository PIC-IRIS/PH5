#!/usr/bin/env pnpython4

#
# Build SEG-Y or PASSCAL SEGY file.
#
# This sits between the code that talks to the ph5
# file, and the code that generates the SEG file.
#
# Steve Azevedo, August 2007
#

import math
import numpy
import os
import time
import string
import sys
import logging
from pyproj import Geod
from ph5.core.cs2cs import geod2utm
from ph5.core import segy_h, ebcdic

PROG_VERSION = '2024.151'
LOGGER = logging.getLogger(__name__)

os.environ['TZ'] = 'UTC'
time.tzset()

MAX_16 = 32767.
MIN_16 = -32768.
MAX_32 = 2147483647.
MIN_32 = -2147483648.
MAXSAMPLES = 65536

FACTS = {'km': 1000., 'm': 1., 'dm': 1. / 10., 'cm': 1. / 100.,
         'mm': 1. / 1000., 'kmi': 1852.0, 'in': 0.0254, 'ft': 0.3048,
         'yd': 0.9144,
         'mi': 1609.344, 'fath': 1.8288, 'ch': 20.1168, 'link': 0.201168,
         'us-in': 1. / 39.37, 'us-ft': 0.304800609601219,
         'us-yd': 0.914401828803658,
         'us-ch': 20.11684023368047, 'us-mi': 1609.347218694437,
         'ind-yd': 0.91439523, 'ind-ft': 0.30479841, 'ind-ch': 20.11669506}


def __version__():
    print PROG_VERSION


# Map channel number to Trace ID (29-30 in trace header)
CHAN2TID = {1: 1, 2: 16, 3: 17, 4: 15, 5: 16, 6: 17}
COMP2TID = {'Z': 15, 'N': 16, 'E': 17}
COUNTMULT = {'nV/count': 1000000000., 'uV/count': 1000000., 'mV/count': 1000.,
             'volts/count': 1.}
LOCUNITS = {'feet': 1, 'meters': 1, 'seconds': 2, 'degrees': 3, 'dms': 4}

EXT_HEADER_CHOICES = ['P', 'S', 'U', 'I', 'N']

DECIMATION_FACTORS = {'2': '2', '4': '4', '5': '5', '8': '4,2', '10': '5,2',
                      '20': '5,4'}


def add_string_to_header(ext, key, bit_number, text, string_name):
    """
    Add text that has been convert to integer to external header (ext)
    if value is compliant with bit_number of the field.

    :param ext: dictionary of external header
    :param key: key of field to be added in external header
    :param bit_number: number of bits of unsigned integer for trace header's
        entry
    :param text: string to be added
    :param string_name: name of string to be used in warning message,
    """
    range_upper = 2 ** bit_number - 1

    text_int = int(text)
    if 0 <= text_int <= range_upper:
        ext[key] = text_int
    else:
        LOGGER.warning(
            "%s, %s, not added to segy header: Descriptions must be "
            "numeric values in range [0,%s] to be added to header." %
            (string_name, text_int, range_upper))



class SEGYError(Exception):
    '''
    Raised if SEG-Y file can't be created
    '''

    def __init__(self, *args, **kwargs):
        self.args = (args, kwargs)
        self.message = args[0]


class Ssegy:

    def __init__(self,
                 # start_point,     # Starting point integer
                 # length_points,   # Number of points
                 # das_t,           # Das_t row
                 sort_t,  # Sort_t row
                 # array_t,         # Array_t row
                 # time_t,          # Time_t row
                 event_t,  # Event_t row
                 # response_t,      # Response_t row
                 # receiver_t,      # Receiver_t row (orientation)
                 # offset_t,        # Offset_t
                 pas='U',  # 'P' -> PASSCAL extended header
                 # 'S' -> SEG extended header
                 # 'U' -> Menlo USGS extended header
                 # 'I' -> SIOSEIS
                 # 'N' -> iNova firefly
                 length_points=0,
                 seq=1,  # Line sequence number
                 user=False,  # Populate trace header with user coordinates
                 utm=False):  # Populate trace header with UTM coordinates

        self.start_point = 0
        self.length_points = length_points
        if length_points == 0:
            self.length_points_all = 0
        else:
            self.length_points_all = length_points

        self.das_t = None
        self.sample_rate = None
        self.channel_number = 1
        self.sort_t = sort_t
        self.time_t = None
        self.event_t = event_t
        self.response_t = None
        self.offset_t = None
        self.pas = pas
        self.utm = utm
        self.user = user
        self.seq = seq
        self.text_header = segy_h.Text()
        self.reel_header = segy_h.Reel()
        # Allow non-standard SEG-Y
        self.break_standard = False
        self.trace_type = None  # Current data trace type (int, float)
        self.trace_byteorder = None  # Current data trace byteorder
        self.ext = {}

    def write_text_header(self, fd):
        # 3200 bytes
        try:
            fd.write(self.text_header.get()[:3200])
        except Exception as e:
            raise SEGYError(
                "Failed to write SEG-Y textural header: {0}".format(e.message))

    def write_reel_header(self, fd):
        # 400 bytes
        try:
            fd.write(self.reel_header.get()[:400])
        except Exception as e:
            raise SEGYError(
                "Failed to write SEG-Y reel header: {0}".format(e.message))

    def write_trace_header(self, fd):
        # 180 bytes
        try:
            fd.write(self.trace_header.get()[:180])
            fd.flush()
        except Exception, e:
            raise SEGYError(
                "Failed to write SEG-Y trace header: {0}".format(e.message))

        # 60 bytes
        try:
            fd.write(self.extended_header.get()[:60])
            fd.flush()
        except Exception, e:
            raise SEGYError(
                "Failed to write extended portion of SEG-Y trace header: {0}"
                .format(e.message))

    def write_data_array(self, fd, nparray):
        try:
            nparray.tofile(file=fd)
        except Exception as e:
            raise SEGYError(
                "Failed to write SEG-Y data trace: {0}".format(e.message))

    def set_data_array(self):
        '''   Pad to correct length, convert to NumPy array, byteswap   '''
        # Pad data to correct length with the median value
        pad = numpy.array([])
        if len(self.data) < self.length_points_all:
            if len(self.data) == 0:
                m = 0
            else:
                m = numpy.median(self.data)

            short = self.length_points_all - len(self.data)
            pad = [m] * short

        data = numpy.append(self.data, pad)
        i = 0
        # Need to look in self.response_t for bit_weight/value_d and
        # scale trace values.
        bw = float(self.response_t['bit_weight/value_d'])
        # Use PASSCAL extended header
        #
        # This should never get executed. Generation of PASSCAL SEGY
        # trace files depricated Sept 2014.
        # Section of code left as reference.
        if self.pas == 'XXX':
            # PASSCAL SEGY should be the endianess of the machine
            if self.trace_type == 'int':
                #
                x_d = numpy.array(data, numpy.int32)
            # Float trace elements
            elif self.trace_type == 'float':
                x_f = numpy.array(data, numpy.float32)
                # This section scales the IEEE float to an integer
                if x_f.min() < 0:
                    x_f = x_f + abs(x_f.min())
                ran = abs(x_f.max())
                if ran < abs(x_f.min()):
                    ran = abs(x_f.min())

                M0 = float(2 ** 23)
                if ran == 0:
                    s = 1.
                else:
                    s = M0 / ran

                # This (was) hard coded for iNova data to apply a
                # fixed scale factor
                # This uses the scale factor derived as above
                if 'scale_fac' in self.ext:
                    self.ext['scale_fac'] = 1. / s

                x_d = x_f * s
                x_d = x_d.astype(numpy.uint32)

            else:
                LOGGER.warning(
                    "Trace type unknown: {0}".format(self.trace_type))

            # Always byte order of requesting machine
            if sys.byteorder == 'little':
                x_d = x_d.byteswap()
            # Get the number of points we wrote
            i += x_d.shape[0]
        #
        # Standard SEG-Y (Always go here!!!)
        #
        else:
            # Little endian machine
            # We always want big endian in the SEG-Y file
            if sys.byteorder == 'little':
                # Little endian trace
                # This SHOULD always be True
                # Int trace elements
                if self.trace_type == 'int':
                    x_d = numpy.array(data, numpy.int32)
                # Float trace elements
                elif self.trace_type == 'float':
                    x_d = numpy.array(data, numpy.float32)

                if bw != 0:
                    x_f = x_d * bw

                x_d = x_f.astype(numpy.float32)
                x_d = x_d.byteswap()

            elif sys.byteorder == 'big':
                # Big endian trace
                # This SHOULD always be True
                if self.trace_type == 'int':
                    x_d = numpy.array(data, numpy.int32)
                elif self.trace_type == 'float':
                    x_d = numpy.array(data, numpy.float32)

                if bw != 0:
                    x_f = x_d * bw

                x_d = x_f.astype(numpy.float32)
            # Write to end of file
            # How many points did we write
            i += x_d.shape[0]
        # We need to delay setting this incase scale_fac changed
        self.extended_header.set(self.ext)

        return i, x_d

    def set_utm(self, utm):
        self.utm = utm

    def set_user(self, user):
        self.user = user

    def set_event_t(self, event_t):
        self.event_t = event_t

    def set_array_t(self, array_t):
        if not type(array_t) == dict:
            raise SEGYError("set_array_t requires a dict.")
        self.array_t = array_t

    # PASSCAL extended header
    def set_pas(self):
        self.pas = 'P'

    # SEG extended header
    def set_seg(self):
        self.pas = 'S'

    # USGS Menlo extended header
    def set_usgs(self):
        self.pas = 'U'

    # iNova extended header
    def set_inova(self):
        self.pas = 'N'

    # Set extended header type
    def set_ext_header_type(self, ext_type):
        if ext_type in EXT_HEADER_CHOICES:
            self.pas = ext_type

    def set_data(self, data):
        self.data = data

    def set_trace_type(self, t, o):
        '''   Set trace type, and byteorder   '''
        self.trace_type = t
        self.trace_byteorder = o

    def set_das_t(self, das_t):
        self.das_t = das_t
        if not self.sample_rate:
            self.sample_rate = das_t['sample_rate_i']
        self.channel_number = das_t['channel_number_i']

    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate

    def set_time_t(self, time_t):
        self.time_t = time_t

    def set_response_t(self, response_t):
        self.response_t = response_t

    # Orientation info
    def set_receiver_t(self, receiver_t):
        self.receiver_t = receiver_t

    def set_offset_t(self, offset_t):
        self.offset_t = offset_t

    def set_sort_t(self, sort_t):
        self.sort_t = sort_t[0]

    def set_length_points(self, length_points):
        self.length_points = length_points
        if self.length_points_all == 0:
            self.length_points_all = length_points

    def set_line_sequence(self, seq):
        self.seq = seq

    def set_cut_start_epoch(self, start):
        self.cut_start_epoch = start

    def set_text_header(self, ntrpr=None):
        txt = {}
        if self.pas == 'U':
            style = 'MENLO'
        elif self.pas == 'P':
            style = 'PASSCAL'
        elif self.pas == 'S':
            style = 'SEG'
        elif self.pas == 'I':
            style = 'SIOSEIS'
        elif self.pas == 'N':
            style = 'INOVA'

        if self.break_standard is True:
            txt['_06_'] = ebcdic.AsciiToEbcdic(
                "C 6                         SAMPLES/TRACE {0:6d}"
                "                                ".format(
                    int(self.length_points)))
            if ntrpr is not None:
                txt['_05_'] = ebcdic.AsciiToEbcdic(
                    "C 5 DATA TRACES/RECORD {0:5d}"
                    "                                                    "
                    .format(int(ntrpr)))

        txt['_38_'] = ebcdic.AsciiToEbcdic(
            "C38 {0:<7} STYLE EXTENDED TRACE HEADER".format(style) + " " * 41)
        txt['_39_'] = ebcdic.AsciiToEbcdic("C39 SEG Y REV1" + " " * 66)
        txt['_40_'] = ebcdic.AsciiToEbcdic(
            "C40 END TEXTURAL HEADER" + " " * 57)

        try:
            self.text_header.set(txt)
        except segy_h.HeaderError as e:
            raise SEGYError("{0}".format(e.message))

    def set_reel_header(self, traces):
        rel = {}

        try:
            rel['lino'] = int(self.sort_t['array_name_s'])
        except (ValueError, TypeError):
            rel['lino'] = 1

        rel['reno'] = 1
        if traces <= MAX_16:
            rel['ntrpr'] = traces
        elif self.break_standard:
            rel['ntrpr'] = 0
        else:
            rel['ntrpr'] = int(MAX_16)

        rel['hdt'] = int((1.0 / float(self.sample_rate)) * 1000000.0)
        if self.length_points <= MAX_16:
            rel['hns'] = self.length_points
            rel['nso'] = self.length_points
        # Non-standard sample length
        elif self.break_standard is True:
            rel['hns'] = 0
            rel['nso'] = 0
        else:
            rel['hns'] = int(MAX_16)
            rel['nso'] = int(MAX_16)

        rel['format'] = 5  # IEEE floats
        rel['mfeet'] = 1  # meters
        rel['rev'] = 0x0100  # rev 1.0
        rel['trlen'] = 1  # all traces the same length
        rel['extxt'] = 0  # no extra text headers

        try:
            self.reel_header.set(rel)
        except Exception as e:
            raise SEGYError(
                "Possible overflow in SEG-Y reel header: {0}".format(
                    e.message))

    def set_break_standard(self, tof=False):
        self.break_standard = tof

    def _cor(self, max_drift_rate=0.01):
        '''
           Calculate start, end, drift and offset of clock
        '''
        if self.sort_t:
            sort_start_time = fepoch(self.sort_t['start_time/epoch_l'],
                                     self.sort_t['start_time/micro_seconds_i'])
        else:
            sort_start_time = self.cut_start_epoch

        if self.time_t is None:
            return 0, 0, sort_start_time

        if self.sort_t:
            sort_end_time = fepoch(self.sort_t['end_time/epoch_l'],
                                   self.sort_t['end_time/micro_seconds_i'])
        else:
            sort_end_time = sort_start_time + (
                self.length_points / self.sample_rate)

        sort_mid_time = sort_start_time + (
            (sort_end_time - sort_start_time) / 2.0)
        data_start_time = fepoch(self.time_t['start_time/epoch_l'],
                                 self.time_t['start_time/micro_seconds_i'])
        delta_time = sort_mid_time - data_start_time

        # 1% drift is excessive, don't time correct.
        if abs(self.time_t['slope_d']) >= max_drift_rate:
            time_correction_ms = 0
        else:
            time_correction_ms = int(
                self.time_t['slope_d'] * 1000.0 * delta_time)

        # Sample interval
        si = 1.0 / float(int(self.sample_rate))
        # Check if we need to time correct?
        if abs(self.time_t['offset_d']) < (si / 2.0):
            time_correction_ms = 0
        #  KLUDGE reverse sign here
        if time_correction_ms < 0:
            time_correction_ms *= -1
            sgn = 1
        else:
            sgn = -1

        new_start_time = (float(
            time_correction_ms * sgn) / 1000.0) + sort_start_time

        return (0xFFFF & time_correction_ms) * sgn, (
            0xFFFF & (time_correction_ms << 16)) * sgn, new_start_time

    def set_ext_header_inova(self):
        ext = {}
        self.extended_header = segy_h.iNova()

        return ext

    def set_ext_header_seg(self):
        '''   SEG-Y rev 01 extended header   '''
        ext = {}
        self.extended_header = segy_h.Seg()
        # Same as lino from reel header
        try:
            ext['Inn'] = int(self.sort_t['array_name_s'])
        except (ValueError, TypeError):
            ext['Inn'] = 1

        try:
            # Shot point number
            ext['Spn'] = int(self.event_t['id_s'])
            # Size of shot
            ext['Smsmant'] = int(self.event_t['size/value_d'])
        except BaseException:
            pass

        # Spn scaler
        ext['Scal'] = 1
        # Trace value measurement units
        ext['Tvmu'] = 0
        ext['Smsexp'] = 1
        ext['Smu'] = 0
        # Start of trace
        cor_low, cor_high, sort_start_time = self._cor()
        corrected_start_time = self.cut_start_epoch + (cor_low / 1000.0)
        u_secs = int(math.modf(corrected_start_time)[0] * 1000000.0)
        # Trace start usecs
        ext['start_usec'] = u_secs
        # Shot usecs
        ext['shot_us'] = self.event_t['time/micro_seconds_i']

        return ext

    def set_ext_header_pas(self):
        ext = {}
        self.extended_header = segy_h.Passcal()

        cor_low, cor_high, sort_start_time = self._cor()
        if cor_high < -MAX_16 or cor_high > MAX_16:
            cor_high = int(MAX_16)

        ext['totalStaticHi'] = cor_high
        ext['num_samps'] = int(self.length_points)
        ext['max'] = numpy.max(self.data)
        ext['min'] = numpy.min(self.data)
        ext['samp_rate'] = int((1.0 / self.sample_rate) * 1000000.0)
        ext['data_form'] = 1  # 32 bit
        ext['scale_fac'] = float(self.response_t['bit_weight/value_d'])

        corrected_start_time = self.cut_start_epoch + (cor_low / 1000.0)
        m_secs = int(math.modf(corrected_start_time)[0] * 1000.0)
        ext['m_secs'] = m_secs

        try:
            ttuple = time.gmtime([self.event_t['time/epoch_l']])
            ext['trigyear'] = ttuple[0]
            ext['trigday'] = ttuple[7]
            ext['trighour'] = ttuple[3]
            ext['trigminute'] = ttuple[4]
            ext['trigsecond'] = ttuple[5]
            ext['trigmills'] = int(
                self.event_t['time/micro_seconds_i'] / 1000.0)
        except BaseException:
            pass

        try:
            try:
                ext['inst_no'] = int(
                    self.array_t['das/serial_number_s']) & 0xFFFF
            except ValueError:
                ext['inst_no'] = int(self.array_t['das/serial_number_s'], 16)
        except BaseException:
            ext['inst_no'] = 0

        try:
            ext['station_name'] = string.ljust(
                string.strip(self.array_t['id_s']), 6)
        except BaseException:
            ext['station_name'] = string.ljust(
                string.strip(self.array_t['das/serial_number_s']), 6)

        return ext

    def set_ext_header_menlo(self):
        '''   Use USGS Menlo's idea of extended trace header   '''
        ext = {}
        self.extended_header = segy_h.Menlo()

        # Start of trace
        cor_low, cor_high, sort_start_time = self._cor()
        corrected_start_time = self.cut_start_epoch + (cor_low / 1000.0)
        u_secs = int(math.modf(corrected_start_time)[0] * 1000000.0)
        ext['start_usec'] = u_secs
        # Shot size in Kg
        try:
            if self.event_t['size/units_s'][0] == 'k' or \
                    self.event_t['size/units_s'][0] == 'K':
                ext['shot_size'] = self.event_t['size/value_d']
        except BaseException:
            pass

        # Shot time
        try:
            ttuple = time.gmtime(float(self.event_t['time/epoch_l']))
            ext['shot_year'] = ttuple[0]
            ext['shot_doy'] = ttuple[7]
            ext['shot_hour'] = ttuple[3]
            ext['shot_minute'] = ttuple[4]
            ext['shot_second'] = ttuple[5]
            ext['shot_us'] = self.event_t['time/micro_seconds_i']
        except BaseException:
            pass

        # Always set to 0
        ext['si_override'] = 0
        # Azimuth and inclination, set to 0?
        ext['sensor_azimuth'] = 0
        ext['sensor_inclination'] = 0
        # Linear moveout static x/v ms
        ext['lmo_ms'] = 0
        # LMO flag, 1 -> n
        ext['lmo_flag'] = 1
        # Inst type, 16 == texan
        if self.array_t['das/model_s'].find('130') != -1:
            ext['inst_type'] = 13  # RT-130
        else:
            ext['inst_type'] = 16  # texan

        # Always set to 0
        ext['correction'] = 0
        # Uphole azimuth set to zero
        ext['azimuth'] = 0
        # Sensor type
        if self.array_t['sensor/model_s'].find('28') != -1:
            ext['sensor_type'] = 1  # L28
        elif self.array_t['sensor/model_s'].find('22') != -1:
            ext['sensor_type'] = 2  # L22
        elif self.array_t['sensor/model_s'].find('4') != -1:
            ext['sensor_type'] = 4  # L4
        else:
            ext['sensor_type'] = 99  # Don't know, don't care

        # Sensor sn
        try:
            add_string_to_header(ext, 'sensor_sn', 16,
                                 self.array_t['sensor/serial_number_s'],
                                 "Array_t's sensor/serial_number_s")
        except BaseException:
            pass

        # DAS sn
        try:
            ext['das_sn'] = int(self.array_t['das/serial_number_s'])
        except ValueError:
            try:
                ext['das_sn'] = 0xFFFF & int(
                    self.array_t['das/serial_number_s'], 16)
            except ValueError:
                pass

        # 16 free bits
        try:
            ext['empty1'] = self.array_t['channel_number_i']
        except BaseException:
            pass

        # Number of samples
        ext['samples'] = self.length_points

        # 32 free bits
        try:
            add_string_to_header(ext, 'empty2', 32,
                                 self.array_t['description_s'],
                                 "Array_t's description_s")
        except BaseException:
            pass

        # clock correction
        try:
            ext['clock_drift'] = self._cor()[0]
            if ext['clock_drift'] > MAX_16 or ext['clock_drift'] < -MAX_16:
                ext['clock_drift'] = int(MAX_16)
        except BaseException:
            pass

        # 16 free bits
        try:
            add_string_to_header(ext, 'empty3', 16,
                                 self.event_t['description_s'],
                                 "Event_t's description_s")
        except BaseException:
            pass

        return ext

    def set_ext_header_sioseis(self):
        '''   Use SIOSEIS extended header   '''
        ext = {}
        self.extended_header = segy_h.Sioseis()
        ext['sampleInt'] = 1.0 / self.sample_rate
        '''
        if self.seq >= traces :
            ext['endOfRp'] =
        '''
        return ext

    def set_trace_header(self):
        '''
           Set values in trace header.
        '''
        tra = {}
        self.trace_header = segy_h.Trace()
        #
        # Get time correction
        #
        cor_low, cor_high, sort_start_time = self._cor()
        # Calculate start time based on calculated drift
        corrected_start_time = self.cut_start_epoch + (cor_low / 1000.0)

        cl, sl = scale_16(cor_low)
        if sl > 1:
            cor_low = MAX_16
        elif sl < 1:
            cor_low = MIN_16

        ch, sh = scale_16(cor_high)
        if sh > 1:
            cor_high = MAX_16
        elif sh < 1:
            cor_high = MIN_16

        # Set time correction
        tra['totalStatic'] = cor_low

        tra['lineSeq'] = self.seq
        tra['event_number'] = self.das_t['event_number_i']
        tra['channel_number'] = self.seq
        # Set the traceID to the channel, 15 => Z, 16 => N, 17 => E
        # Fallback is to set it to 1 => seismic data
        try:
            try:
                # This should be the orientation
                comp = self.receiver_t['orientation/description_s'][0]
                tra['traceID'] = COMP2TID[comp]
            except BaseException:
                tra['traceID'] = CHAN2TID[self.array_t['channel_number_i']]
        except BaseException:
            # Changed for Mark Goldman, Aug 2011
            tra['traceID'] = 1

        length_points = int(self.length_points)
        if length_points < MAX_16:
            tra['sampleLength'] = length_points
        # Non-standard sample length
        elif self.break_standard is True:
            # Set sample length to zero as a flag its non-standard
            tra['sampleLength'] = 0
        else:
            tra['sampleLength'] = int(MAX_16)

        sample_rate = float(int(self.sample_rate))
        if sample_rate > 30.0:
            # In usec
            tra['deltaSample'] = int((1.0 / sample_rate) * 1000000.0)
        else:
            tra['deltaSample'] = 1

        tra['gainType'] = 1
        tra['gainConst'] = int(self.response_t['gain/value_i'])

        twfUnits = self.response_t['bit_weight/units_s'].strip()
        try:
            mult = COUNTMULT[twfUnits]
        except BaseException:
            mult = 1.

        try:
            tra['traceWeightingFactor'] = int(
                math.log(self.response_t['bit_weight/value_d'] / mult,
                         2) + 0.5)
        except ValueError:
            tra['traceWeightingFactor'] = 1.

        ttuple = time.gmtime(corrected_start_time)
        tra['year'] = ttuple[0]
        tra['day'] = ttuple[7]
        tra['hour'] = ttuple[3]
        tra['minute'] = ttuple[4]
        tra['second'] = ttuple[5]
        tra['timeBasisCode'] = 4  # UTC

        # Limit size of phoneFirstTrace to 65535 maximum
        try:
            pft, spft = scale_u16(int(self.array_t['id_s']))
            if spft != 1:
                tra['phoneFirstTrace'] = pft
            else:
                tra['phoneFirstTrace'] = int(self.array_t['id_s'])
        except BaseException:
            tra['phoneFirstTrace'] = 0

        #
        # Set receiver location here
        #
        try:
            re, es = scale_32(self.array_t['location/Z/value_d'])
            tra['recElevation'] = re
            tra['elevationScale'] = es
        except BaseException:
            tra['recElevation'] = 0
            tra['elevationScale'] = 0

        if self.utm is True:
            try:
                Y, X, Z = geod2utm(None,  # Zone goes here
                                   "WGS84",
                                   self.array_t['location/Y/value_d'],
                                   self.array_t['location/X/value_d'],
                                   self.array_t['location/Z/value_d'])
                s, vx, vy = pick_values_32(X, Y)

                tra['coordScale'] = s
                tra['recLongOrX'] = vx
                tra['recLatOrY'] = vy
                tra['coordUnits'] = 1  # meters
            except BaseException:
                tra['coordScale'] = 0
                tra['recLongOrX'] = 0
                tra['recLatOrY'] = 0
                tra['coordUnits'] = 0
        else:
            try:
                s, vx, vy = pick_values_32(self.array_t['location/X/value_d'],
                                           self.array_t['location/Y/value_d'])
                tra['coordScale'] = s
                tra['recLongOrX'] = vx
                tra['recLatOrY'] = vy
                u = self.array_t['location/X/units_s'].strip()
                if u in LOCUNITS:
                    tra['coordUnits'] = LOCUNITS[u]
                else:
                    tra['coordUnits'] = 0
            except BaseException:
                tra['coordScale'] = 0
                tra['recLongOrX'] = 0
                tra['recLatOrY'] = 0
                tra['coordUnits'] = 0

        #
        # Event location
        #
        if self.event_t:
            try:
                tra['energySourcePt'] = int(self.event_t['id_s'])
            except Exception, e:
                tra['energySourcePt'] = 0

            # Set source location here
            try:
                sz, ez, rz = pick_values_32(self.event_t['location/Z/value_d'],
                                            self.array_t['location/Z/value_d'])
                tra['sourceSurfaceElevation'] = ez
                if tra['recElevation'] != rz:
                    tra['recElevation'] = rz
                    tra['elevationScale'] = sz
            except BaseException:
                tra['sourceSurfaceElevation'] = 0
                tra['sourceDepth'] = 0

            if self.utm:
                try:
                    Y, X, Z = geod2utm(None,  # Zone goes here
                                       "WGS84",
                                       self.event_t['location/Y/value_d'],
                                       self.event_t['location/X/value_d'],
                                       self.event_t['location/Z/value_d'])

                    s, vx, vy = pick_values_32(X, Y)
                    tra['sourceLongOrX'] = vx
                    tra['sourceLatOrY'] = vy

                except BaseException:
                    tra['sourceLongOrX'] = 0
                    tra['sourceLatOrY'] = 0

            else:
                try:
                    s, vx, vy = pick_values_32(
                        self.event_t['location/X/value_d'],
                        self.event_t['location/Y/value_d'])
                    tra['sourceLongOrX'] = vx
                    tra['sourceLatOrY'] = vy
                except BaseException:
                    tra['sourceLongOrX'] = 0
                    tra['sourceLatOrY'] = 0

        if self.offset_t:
            tra['sourceToRecDist'] = self.offset_t['offset/value_d']
        else:
            try:
                az_baz_dist = run_geod(self.event_t['location/Y/value_d'],
                                       self.event_t['location/X/value_d'],
                                       self.array_t['location/Y/value_d'],
                                       self.array_t['location/X/value_d'])
                tra['sourceToRecDist'] = az_baz_dist[2]
            except Exception as e:
                # sys.stderr.write (e.message)
                tra['sourceToRecDist'] = 0

        try:
            self.trace_header.set(tra)
        except Exception as e:
            raise SEGYError(
                "Possible SEG-Y trace header overflow: {0}".format(e.message))

        try:
            if self.pas == 'P':
                self.ext = self.set_ext_header_pas()
            elif self.pas == 'U':
                self.ext = self.set_ext_header_menlo()
            elif self.pas == 'S':
                self.ext = self.set_ext_header_seg()
            elif self.pas == 'I':
                self.ext = self.set_ext_header_sioseis()
            elif self.pas == 'N':
                self.ext = self.set_ext_header_inova()
        except Exception as e:
            raise SEGYError(
                "Possible overflow in extended portion of trace header: {0}"
                .format(e.message))


# MixIns
def units_stub(have, want):
    """
       Finds the conversion multiplier needed.
    """
    # Add more prefixes?
    pref = {'yocto': 1e-24, 'micro': 1e-6, 'milli': 1e-3, 'centi': 1e-2,
            'deci': 1e-1, 'deka': 1e1, 'hecto': 1e2, 'kilo': 1e3, 'mega': 1e6}
    h = None
    w = None
    for p in pref.keys():
        if have[:len(p)] == p:
            h = pref[p]
        if want[:len(p)] == p:
            w = pref[p]

    if h is None:
        h = 1.0
    if w is None:
        w = 1.0

    ret = h / w

    return ret


def fepoch(epoch, ms):
    '''
    Given ascii epoch and miliseconds return epoch as a float.
    '''
    epoch = float(int(epoch))
    secs = float(int(ms)) / 1000000.0

    return epoch + secs


#
# Scale by 10
#
def scale(value, upper, lower):
    #
    if value < 0:
        value = abs(value)
        multiplier = -1
    else:
        multiplier = 1

    f0, v0 = math.modf(value)
    f0 *= 10000000.

    def do_div(v):
        i = 0
        while True:
            v /= 10.
            i += 1
            if v > lower and i < 5:
                continue
            else:
                v *= 10.
                i -= 1
                return int(v + 0.5), 10 ** i

    def do_mult(v):
        i = 0
        while True:
            v *= 10.
            i += 1
            if v < upper and i < 5:
                continue
            else:
                v /= 10.
                i -= 1
                return int(v + 0.5), 10 ** i * -1

    # Need to scale value down (possible error)
    if value > upper:
        x, s = do_div(value)
    # Need to scale value down (possible error)
    elif value < lower:
        x, s = do_mult(value)
    # Need to scale up to preserve fractional part of value
    elif f0 >= 1:
        x, s = do_mult(value)
    else:
        x = int(value)
        s = 1

    return x * multiplier, s


#
# Scale to signed 32 bit int
#
def scale_32(value):
    upper = 2147483647.
    lower = -2147483648.

    return scale(value, upper, lower)


#
# Scale to signed 16 bit int
#
def scale_16(value):
    upper = 32767.
    lower = -32768.

    return scale(value, upper, lower)


def scale_u16(value):
    upper = 2 ** 16
    lower = 0

    return scale(value, upper, lower)


#
# Choose scaler
#
def choose_scaler(s1, s2):
    if abs(s1) > abs(s2):
        return s1
    else:
        return s2


#
# Pick values
#
def pick_values_32(X, Y):
    vx, sx = scale_32(X)
    vy, sy = scale_32(Y)
    if sx != sy:
        cs = choose_scaler(sx, sy)
        if cs == sx:
            if abs(cs) < 1:
                vy = int(Y / abs(cs))
            else:
                vy = int(Y * abs(cs))

            sy = cs
        else:
            if abs(cs) < 1:
                vx = int(X / abs(cs))
            else:
                vx = int(X * abs(cs))

            sx = cs

    return sx, vx, vy


def run_geod(lat0, lon0, lat1, lon1):
    ELLIPSOID = 'WGS84'
    UNITS = 'm'

    config = "+ellps={0}".format(ELLIPSOID)

    g = Geod(config)

    az, baz, dist = g.inv(lon0, lat0, lon1, lat1)

    if dist:
        dist /= FACTS[UNITS]

    # Return list containing azimuth, back azimuth, distance
    return az, baz, dist


#
# Write standard SEG-Y reel header
#
def write_segy_hdr(trace, fd, sf, num_traces):
    data = trace.data
    errors = []
    if len(data) > MAX_16 and sf.break_standard is False:
        errors.append(
            "Warning: Data trace too long, %d samples, truncating to %d" % (
                len(data), MAX_16))
        sf.set_length_points(MAX_16)
    else:
        sf.set_length_points(sf.length_points_all)

    sf.set_data(data[:MAXSAMPLES])
    sf.set_trace_type(trace.ttype, trace.byteorder)
    try:
        sf.set_text_header()
        sf.set_reel_header(num_traces)
        sf.set_trace_header()
    except Exception as e:
        errors.append(e.message)
        raise SEGYError(
            "Error: Failed to set reel or first trace header. {0}\n".format(
                e.message))

    try:
        n, nparray = sf.set_data_array()
    except Exception as e:
        errors.append(e.message)
        LOGGER.error("Failed to set data array. {0}".format(e.message))

    try:
        sf.write_text_header(fd)
    except Exception as e:
        errors.append(e.message)
        LOGGER.error(e.message)

    try:
        sf.write_reel_header(fd)
    except Exception as e:
        errors.append(e.message)
        LOGGER.error(e.message)

    try:
        sf.write_trace_header(fd)
    except Exception as e:
        errors.append(e.message)
        LOGGER.error(e.message)

    try:
        sf.write_data_array(fd, nparray)
    except Exception as e:
        errors.append(e.message)
        raise SEGYError(
            "Error: Failed to write reel and first trace. {0}\n".format(
                e.message))

    L = len(data)
    p = sf.length_points_all - L
    errors.append(
        "Wrote: {0:d} samples with {1:d} sample padding.".format(L, p))
    errors.append("=-" * 40)
    if n != sf.length_points_all:
        errors.append("Only wrote {0} samples.".format(n))
    # Return errors and messages for log
    return errors


#
# Write SEG-Y trace
#
def write_segy(trace, fd, sf):
    data = trace.data
    errors = []
    if len(data) > MAX_16 and sf.break_standard is False:
        errors.append(
            "Warning: Data trace too long, %d samples, truncating to %d" % (
                len(data), MAX_16))
        sf.set_length_points(MAX_16)
        sf.set_data(data[:MAXSAMPLES])
    else:
        sf.set_data(data)

    try:
        sf.set_trace_type(trace.ttype, trace.byteorder)
        sf.set_trace_header()
    except Exception as e:
        errors.append(e.message)
        raise SEGYError(
            "Error: Failed to set trace header. {0}\n".format(e.message))

    try:
        n, nparray = sf.set_data_array()
    except Exception as e:
        errors.append(e.message)
        raise SEGYError(
            "Error: Failed to set data array. {0}\n".format(e.message))

    try:
        sf.write_trace_header(fd)
        sf.write_data_array(fd, nparray)
    except Exception as e:
        errors.append(e.message)
        raise SEGYError(
            "Error: Failed to write trace or trace header. {0}\n".format(
                e.message))

    L = len(data)
    p = sf.length_points_all - L
    errors.append(
        "Wrote: {0:d} samples with {1:d} sample padding.".format(L, p))
    if n != sf.length_points_all:
        errors.append("Only wrote {0} samples.".format(n))
    # return errors and messages
    return errors


def calc_red_vel_secs(offset_t, red_vel):
    errors = []
    if red_vel <= 0:
        return 0.

    if offset_t is None:
        errors.append(
            "Warning: No geometry for station."
            "Reduction velocity not applied.")
        return 0., errors

    if offset_t['offset/units_s'] != 'm':
        errors.append(
            "Warning: Units for offset not in meters!"
            "No reduction velocity applied.")
        return 0., errors

    # m / m/s = seconds
    try:
        secs = abs(offset_t['offset/value_d']) / (red_vel * 1000.)
        errors.append(
            "Applying a reduction velocity of {0:5.3f}"
            "seconds (Shot: {1}, Receiver: {2})".format(
                secs, offset_t['event_id_s'], offset_t['receiver_id_s']))
        return secs, errors
    except Exception:
        return 0., errors


if __name__ == '__main__':
    flds = pick_values_32(275.8, 201.0)
    pass
