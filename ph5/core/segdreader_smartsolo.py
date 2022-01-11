#!/usr/bin/env pnpython3
#
# A class to read SmartSolo SEG-D Version
# based on SmartSolo Software User Manual Version 1.3
# and segdreader.py by Steve Azevedo
#
# Lan Dam, March 2021
#

import sys
import logging
import os
import exceptions

import numpy as np
try:
    from astropy.time import Time as asTime
except ImportError:
    errmsg = ("astropy package is needed to run this command. "
              "Please run 'conda install astropy' to install it.")
    raise ImportError(errmsg)

from ph5.core import segd_h_smartsolo as segd_h
from ph5.core.timedoy import TimeDOY

PROG_VERSION = "2021.155"
LOGGER = logging.getLogger(__name__)


class InputsError (exceptions.Exception):
    def __init__(self, args=None):
        self.args = args


class ReelHeaders (object):
    '''   Container to hold receiver record related headers   '''
    __slots__ = ['storage_unit_label', 'general_header_blocks',
                 'channel_set_descriptor', 'extended_headers',
                 'external_header',
                 'external_header_shot',
                 'channel_set_to_streamer_cable_map']

    def __init__(self):
        self.storage_unit_label = None
        self.general_header_blocks = []
        self.channel_set_descriptor = []
        self.extended_headers = []
        self.external_header = None
        self.external_header_shot = []
        self.channel_set_to_streamer_cable_map = None


class TraceHeaders (object):
    '''   Container to hold trace related headers   '''
    __slots__ = ['trace_header', 'trace_header_N',
                 'line_number', 'receiver_point',
                 'event_number', 'trace_epoch',
                 'preamp_gain_db',
                 'lat', 'lon', 'ele']

    def __init__(self):
        self.trace_header = None
        self.trace_header_N = []
        self.line_number = None
        self.receiver_point = None
        self.event_number = None
        self.trace_epoch = None
        self.lat = None
        self.lon = None
        self.ele = None
        self.preamp_gain_db = None


class Reader ():
    def __init__(self, infile=None):
        self.manufacturer = 'SmartSolo'
        self.infile = infile
        self.FH = None
        self.endianess = 'big'  # SEG-D is always big endian(?)
        # From General headers
        self.file_number = None
        self.record_length_sec = None
        self.chan_sets_per_record = None
        self.sample_rate = None
        self.deploy_epoch = None
        # From Extended headers
        self.pickup_epoch = None
        # From Channel set headers
        self.channel_set_start_time_sec = None
        self.channel_set_end_time_sec = None
        self.preamp_gain_db = None
        # From trace headers
        self.samples = None
        self.bytes_read = 0
        self.id_number = None

    def open_infile(self):
        try:
            self.FH = open(self.infile)
        except Exception as e:
            LOGGER.error(e)
            self.FH = None

    def read_buf(self, size):
        buf = None
        if not self.FH:
            self.open_infile()

        try:
            buf = self.FH.read(size)
        except Exception as e:
            LOGGER.error(e)
            self.FH.close()

        if buf:
            self.bytes_read += len(buf)

        return buf

    def name(self):
        '''   Return name of open file   '''
        if self.FH:
            return self.FH.name
        else:
            return None

    def read_block(self, size, block_obj):
        buf = self.read_buf(size)
        container = block_obj.parse(buf)
        return container

    def get_deploy_epoch(self, ghb):
        t = TimeDOY(year=2000 + ghb.first_shot_point_year,
                    doy=ghb.first_shot_point_doy,
                    hour=ghb.hour_of_day_utc,
                    minute=ghb.minute_of_hour_utc,
                    second=ghb.second_of_minute_utc)
        return t.epoch()

    def getLocationDecimal(self, integer, fraction):
        """
        OLD FORMAT: degree2decimal
        lat degree: DDMMSS.sss
        lon degree: DDDMMSS.sss
        return decimal = deg + min/60 + sec/3600
        NEW FORMAT: combine signed integer with string
        integer is signed ingeter
        return signed_integer.fraction
        """
        """
        # OLD FORMAT DDMMSS.sss
        degree_str = "%.3f" % (integer + fraction)
        sec = float(degree_str[-6:])
        min = float(degree_str[-8:-6])
        deg = float(degree_str[:-8])
        decimal = deg + min/60. + sec/3600.
        return decimal
        """
        # NEW FORMAT: ingeger is a signed one
        if integer < 0:
            degree_str = integer - fraction
        else:
            degree_str = integer + fraction
        return degree_str

    def process_general_headers(self):
        self.reel_headers = ReelHeaders()

        for i in range(3):
            self.reel_headers.general_header_blocks.append(
                self.read_block(32, segd_h.General_header_block(i)))

        # Set record length
        if self.reel_headers.general_header_blocks[0].record_length == 0xFFF:
            self.record_length_sec = self.reel_headers. \
                general_header_blocks[1].extended_record_length
        else:
            self.record_length_sec = self.reel_headers.general_header_blocks[
                                         0].record_length * 0.512
        # Set number of channel sets
        if self.reel_headers.general_header_blocks[
                0].chan_sets_per_scan == 0xFF:
            self.chan_sets_per_scan = self.reel_headers. \
                general_header_blocks[1].extended_chan_sets_per_scan_type
        else:
            self.chan_sets_per_scan = self.reel_headers. \
                general_header_blocks[0].chan_sets_per_scan

        self.sample_rate = int(
            (1. / (self.reel_headers.
                   general_header_blocks[0].base_scan_interval / 16.)) * 1000.)

        self.deploy_epoch = self.get_deploy_epoch(
            self.reel_headers.general_header_blocks[0])

    def process_channel_set_descriptors(self):
        """ name in SmartSolo Doc.: Scan Type Header """
        def create_key():
            # Create a mapping between channel sets to streamer cable numbers
            kv = {}
            for cs in self.reel_headers.channel_set_descriptor:
                k = cs.chan_set_number
                v = cs.streamer_cable_number
                kv[k] = v

            return kv

        for i in range(self.chan_sets_per_scan):
            cs = self.read_block(32, segd_h.Channel_set_descriptor())
            self.reel_headers.channel_set_descriptor.append(cs)
            # ***   Should we get current channel set number   ***
            # Channel set start time in seconds
            self.channel_set_start_time_sec = \
                self.reel_headers.channel_set_descriptor[
                    i]. chan_set_start_time_ms / 1000
            # Channel set end time in seconds
            self.channel_set_end_time_sec = \
                self.reel_headers.channel_set_descriptor[
                    i].chan_set_end_time_ms / 1000
            # ***   Calculate scale factor for mili-volts.
            # SmartSolo data recorded as mili-volts   ***
        self.reel_headers.channel_set_to_streamer_cable_map = create_key()
        # Calculate preamp_gain
        self.preamp_gain_db = None
        mp = self.reel_headers.channel_set_descriptor[
            0].MP_factor_descaler_multiplier
        self.MP_factor_descaler_multiplier = mp
        mp_hex = "{0:x}".format(mp)
        if mp == 0:         # 0x0000
            self.preamp_gain_db = 0
        elif mp == 132:     # 0x0084
            self.preamp_gain_db = 6
        elif mp == 136:     # 0x0088
            self.preamp_gain_db = 12
        elif mp == 140:     # 0x008c
            self.preamp_gain_db = 18
        elif mp == 144:     # 0x0090
            self.preamp_gain_db = 24
        elif mp == 148:     # 0x0094
            self.preamp_gain_db = 30
        elif mp == 152:     # 0x0098
            self.preamp_gain_db = 36
        else:
            LOGGER.error("MP_factor_descaler_multiplier is Ox{0} while it "
                         "should be one of the following values:\n"
                         "0x0000,0x0084,0x0088,0x008c,0x0090,0x0094,"
                         "0x0098".format(mp_hex))

    def process_extended_headers(self):
        self.reel_headers.extended_headers.append(
            self.read_block(1024, segd_h.Extended_header_block()))
        sample_rate = int((10**6) / self.reel_headers.extended_headers[0]
                          .sample_rate_microsec)
        if sample_rate != self.sample_rate:
            raise InputsError("Sample rate in Extended Header[0] is conflict"
                              "with base_scan_interval")
        number_of_traces = self.reel_headers.extended_headers[
            0].number_of_traces
        number_of_samples_in_traces = self.reel_headers.extended_headers[
            0].number_of_samples_in_traces
        self.pickup_epoch = self.deploy_epoch + (
            number_of_samples_in_traces * number_of_traces / sample_rate
        )

    def process_external_headers(self):
        self.reel_headers.external_header = self.read_block(
            1024, segd_h.External_header_block())

    def process_trace_headers(self):
        self.trace_headers = TraceHeaders()

        self.trace_headers.trace_header = self.read_block(
            20, segd_h.Trace_header())
        n = self.trace_headers.trace_header.trace_extension_blocks
        for i in range(n):
            self.trace_headers.trace_header_N.append(
                self.read_block(32, segd_h.Trace_header_extension(i)))

        self.id_number = self.trace_headers.trace_header_N[
            5].unit_serial_number
        self.trace_headers.event_number = \
            self.trace_headers.trace_header.trace_number

        thN0 = self.trace_headers.trace_header_N[0]
        self.samples = thN0.samples_per_trace
        # ignore fraction part
        self.trace_headers.line_number = \
            thN0.extended_receiver_line_number_integer
        self.trace_headers.receiver_point = \
            thN0.extended_receiver_point_number_integer

        thN3 = self.trace_headers.trace_header_N[3]
        self.trace_headers.lat = self.getLocationDecimal(
            thN3.IGU_GPS_lat_integer, thN3.IGU_GPS_lat_fraction)
        self.trace_headers.lon = self.getLocationDecimal(
            thN3.IGU_GPS_lon_integer, thN3.IGU_GPS_lon_fraction)
        self.trace_headers.ele = thN3.IGU_GPS_height
        self.trace_headers.preamp_gain_db = self.preamp_gain_db
        TB_GPS_time_time_sec = self.trace_headers.trace_header_N[
                                  1].TB_GPS_time_microsec/1000000.
        # Use astropy package to convert time from gps to utc
        # https: // docs.astropy.org / en / stable / time /
        gps_time = asTime(TB_GPS_time_time_sec, format='gps')
        trace_epoch_sec = asTime(gps_time, format='unix', scale='utc').value
        trace_epoch_ms = trace_epoch_sec * 10.**3
        self.trace_headers.trace_epoch = trace_epoch_sec * 10.**6   # microsec
        number_of_samples_in_traces = self.trace_headers.trace_header_N[
            0].samples_per_trace
        trace_endtime_ms = trace_epoch_ms + (
            number_of_samples_in_traces / self.sample_rate)

        trace_endtime = trace_endtime_ms / float(
            10**(len(str(trace_endtime_ms)) - len(str(int(self.pickup_epoch))))
        )

        if self.pickup_epoch < trace_endtime:
            self.pickup_epoch = trace_endtime

        return self.samples

    def read_trace(self, number_of_samples):
        '''   Read data trace and return as numpy array
              8015 -- 20 bit binary
              8022 -- 8 bit quanternary
              8024 -- 16 bit quanternary
              8036 -- 24 bit 2s compliment integer
              8038 -- 32 bit 2s compliment integer
              8042 -- 8 bit hexidecimal
              8044 -- 16 bit hexidecimal
              8048 -- 32 bit hexidecimal
              8058 -- 32 bit IEEE float   '''

        f = self.trace_fmt = self.reel_headers.\
            general_header_blocks[0].data_sample_format_code

        bytes_per_sample = 4  # Assumes 32 bit IEEE floats
        buf = self.read_buf(bytes_per_sample * number_of_samples)
        # IEEE floats - 4 byte - Should be big endian
        if f == 8058:
            try:
                if self.endianess != sys.byteorder:
                    # Swap 4 byte
                    ret = np.fromstring(buf, dtype=np.float32)
                    ret = ret.byteswap()
                else:
                    ret = np.fromstring(buf, dtype=np.float32)
            except Exception as e:
                raise InputsError(
                    "Error: Could not read data trace: {0}".format(e))

        else:
            raise InputsError("Format code of {0} not supported!".format(f))

        return ret

    def process_trace(self, trace_index):

        if trace_index == 0:
            """
            With SmartSolo, segd2ph5 need to run process_trace_headers()
            to get some info in trace_header at the beginning
            => not run self.process_trace_headers() for the first trace
            """
            samples = self.samples
        else:
            samples = self.process_trace_headers()
        ret = self.read_trace(samples)
        cs = self.trace_headers.trace_header.channel_set
        # Return trace and channel set number
        return ret, cs

    def isEOF(self):
        if self.FH.closed:
            return True

        try:
            n = len(self.FH.read(20))
            if n != 20:
                raise EOFError
            self.FH.seek(-20, os.SEEK_CUR)
            return False
        except EOFError:
            self.FH.close()
            return True
