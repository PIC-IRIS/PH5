#!/usr/bin/env pnpython3

#
# Build SAC file.
#
# This sits between the code that talks to the ph5
# file and the code that generates the SAC file.
#
# Steve Azevedo, October 2013
#

from ph5.core import sac_h
import math
import numpy
import sys
import logging
import time

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)


class SACError (Exception):
    '''
    Raised if SAC file can't be created
    '''

    def __init__(self, *args, **kwargs):
        self.args = (args, kwargs)


class Ssac (object):
    def __init__(self,
                 sort_t,  # Sort_t row
                 event_t,  # Event_t row
                 byteorder=None,
                 length_points=0):

        self.start_point = 0
        self.length_points = length_points
        if length_points == 0:
            self.length_points_all = 0
        else:
            self.length_points_all = length_points

        self.das_t = None
        self.sample_rate = None
        self.sort_t = sort_t
        self.time_t = None
        self.event_t = event_t
        self.response_t = None
        self.offset_t = None
        if byteorder:
            self.trace_byteorder = byteorder  # Current data trace byteorder
        else:
            self.trace_byteorder = sys.byteorder
        self.init_float_header()
        self.init_int_header()
        self.init_char_header()

    def init_float_header(self):
        self.float_header = sac_h.SAC_float()

    def init_int_header(self):
        self.int_header = sac_h.SAC_int()

    def init_char_header(self):
        self.char_header = sac_h.SAC_char()

    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate

    def set_event_t(self, event_t):
        if event_t == []:
            self.event_t = None
        else:
            self.event_t = event_t

    def set_array_t(self, array_t):
        self.array_t = array_t

    def set_das_t(self, das_t):
        self.das_t = das_t
        self.sample_rate = das_t['sample_rate_i']

    def set_time_t(self, time_t):
        self.time_t = time_t

    def set_response_t(self, response_t):
        self.response_t = response_t

    def set_receiver_t(self, receiver_t):
        self.receiver_t = receiver_t

    def set_offset_t(self, offset_t):
        self.offset_t = offset_t

    def set_data_trace(self, data):
        self.data = data

    def set_length_points(self, length_points):
        # print "Set length points to: {0}".format (length_points)
        self.length_points = length_points
        if self.length_points_all == 0:
            # print "Set lenght points all {0}".format (length_points)
            self.length_points_all = length_points

    def set_cut_start_epoch(self, start):
        self.cut_start_epoch = start

    def set_float_header(self):
        f = {}
        xxx = -12345.0
        # Sample interval
        if self.sample_rate:
            self.das_t['sample_rate_i'] = self.sample_rate
            self.length_points_all = self.length_points

        f['delta'] = 1. / (float(self.das_t['sample_rate_i']) /
                           float(self.das_t['sample_rate_multiplier_i']))
        if self.data:
            # Min dependent variable
            f['depmin'] = numpy.amin(numpy.array(self.data))
            # Max dependent variable
            f['depmax'] = numpy.amax(numpy.array(self.data))

        # Beginning value of independent variable
        bbb = self.cut_start_epoch
        f['b'] = 0.0
        # Ending value of independent variable
        eee = bbb + self.length_points_all / \
            (float(self.das_t['sample_rate_i']) /
             float(self.das_t['sample_rate_multiplier_i']))
        f['e'] = eee - bbb

        if self.array_t:
            # Station lat
            f['stla'] = self.array_t['location/Y/value_d']
            # Station lon
            f['stlo'] = self.array_t['location/X/value_d']
            # Station elev
            f['stel'] = self.array_t['location/Z/value_d']

        if self.event_t:
            try:
                # Event lat
                f['evla'] = self.event_t['location/Y/value_d']
                # Event lon
                f['evlo'] = self.event_t['location/X/value_d']
                # Event elev
                f['evel'] = self.event_t['location/Z/value_d']
                # Event depth
                f['evdp'] = self.event_t['depth/value_d']
            except Exception as e:
                pass

        if self.offset_t:
            # Station to Event distance km
            f['dist'] = self.offset_t['offset/value_d']
            # Event to station azimuth
            f['az'] = self.offset_t['azimuth/value_f']
            # Station to event az
            f['baz'] = xxx

        if self.receiver_t:
            # Sensor channel azimuth
            f['cmpaz'] = self.receiver_t['orientation/azimuth/value_f']
            # Sensor incident angle
            f['cmpinc'] = self.receiver_t['orientation/dip/value_f']

        try:
            self.float_header.set(f)
        except Exception as e:
            raise SACError(
                "Possible overflow in SAC float header: {0}".format(e))

    def set_int_header(self):
        i = {}
        cor_low, cor_high, sort_start_time = self._cor()
        corrected_start_time = self.cut_start_epoch + (cor_low / 1000.0)

        ttuple = time.gmtime(corrected_start_time)
        # Year
        i['nzyear'] = ttuple[0]
        # Day of year
        i['nzjday'] = ttuple[7]
        # Hour
        i['nzhour'] = ttuple[3]
        # Minute
        i['nzmin'] = ttuple[4]
        # Second
        i['nzsec'] = ttuple[5]
        # milli-second
        i['nzmsec'] = int(math.modf(corrected_start_time)[0] * 1000.0)

        if self.event_t:
            try:
                # Event ID
                i['nevid'] = int(self.event_t['id_s'])
            except Exception as e:
                pass

        # Number of points
        i['npts'] = self.length_points_all
        # Type of file
        i['iftype'] = sac_h.ICONSTANTS['ITIME']
        # Type of dependent variable
        i['idep'] = sac_h.ICONSTANTS['IVOLTS']
        # Reference time
        i['iztype'] = sac_h.ICONSTANTS['IB']
        # Is data evenly spaced
        i['leven'] = True
        # Are Distance, Azimuth, calculated from station event coordinates
        i['lcalda'] = True
        # Header version number
        i['nvhdr'] = 6

        try:
            self.int_header.set(i)
        except Exception as e:
            raise SACError(
                "Possible overflow in SAC integer header: {0}".format(e))

    def set_char_header(self):
        c = {}
        xxx = '-12345  '
        if self.array_t:
            # Station name
            c['kstnm'] = "{0:<8}".format(self.array_t['id_s'])

        if self.event_t:
            try:
                # Event name
                c['kevnm'] = "{0:<16}".format(self.event_t['id_s'])
            except Exception as e:
                pass

        # Network name
        c['knetwk'] = xxx
        # Recording instrument
        c['kinst'] = xxx

        try:
            self.char_header.set(c)
        except Exception as e:
            raise SACError(
                "Possible overflow in SAC character header: {0}".format(e))

    def set_data_array(self):
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
        # Do we need to byte swap
        if sys.byteorder != self.trace_byteorder:
            x_d = numpy.array(data, numpy.float32).byteswap()
        else:
            x_d = numpy.array(data, numpy.float32)

        #
        # Need to look in self.response_t
        # for bit_weight/value_d and scale trace values.
        #
        try:
            bw = float(self.response_t['bit_weight/value_d'])
            if bw != 0:
                x_d *= bw

        except Exception as e:
            LOGGER.warning(
                "Problem applying trace bit weight.\n{0}".format(e))

        i += x_d.shape[0]

        return i, x_d

    def _cor(self, max_drift_rate=0.01):
        '''
           Calculate start, end, drift and offset of clock
        '''
        time_correction_ms = 0
        if self.sort_t:
            sort_start_time = fepoch(
                self.sort_t['start_time/epoch_l'],
                self.sort_t['start_time/micro_seconds_i'])
        else:
            sort_start_time = self.cut_start_epoch

        if self.time_t is None:
            return 0, 0, sort_start_time

        if self.sort_t:
            sort_end_time = fepoch(
                self.sort_t['end_time/epoch_l'],
                self.sort_t['end_time/micro_seconds_i'])
        else:
            sort_end_time = sort_start_time + \
                (self.length_points / self.sample_rate)

        sort_mid_time = sort_start_time + \
            ((sort_end_time - sort_start_time) / 2.0)
        data_start_time = fepoch(
            self.time_t['start_time/epoch_l'],
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

        return (
            0xFFFF & time_correction_ms) * sgn, (0xFFFF
                                                 & (time_correction_ms << 16))\
            * sgn

    def write_float_header(self, fd):
        try:
            fd.write(self.float_header.get()[:280])
        except Exception as e:
            raise SACError("Failed to write SAC float header: {0}".format(e))

    def write_int_header(self, fd):
        try:
            fd.write(self.int_header.get()[:160])
        except Exception as e:
            raise SACError("Failed to write SAC integer header: {0}".format(e))

    def write_char_header(self, fd):
        try:
            fd.write(self.char_header.get()[:192])
        except Exception as e:
            raise SACError(
                "Failed to write SAC character header: {0}".format(e))

    def write_data_array(self, fd, nparray):
        try:
            nparray.tofile(file=fd)
        except Exception as e:
            raise SACError("Failed to write SAC data array: {0}".format(e))


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
