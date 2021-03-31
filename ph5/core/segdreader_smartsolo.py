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
from ph5.core import segd_h_smartsolo as segd_h

PROG_VERSION = "2021.90"
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
    __slots__ = ['trace_header', 'trace_header_N']

    def __init__(self):
        self.trace_header = None
        self.trace_header_N = []


class Reader ():
    def __init__(self, infile=None):
        self.infile = infile
        self.FH = None
        self.endianess = 'big'  # SEG-D is always big endian(?)
        # From General headers
        self.file_number = None
        self.record_length_sec = None
        self.chan_sets_per_record = None
        self.sample_rate = None
        # From Channel set headers
        self.channel_set_start_time_sec = None
        self.channel_set_end_time_sec = None
        # From trace headers
        self.samples = None
        self.bytes_read = 0

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

    def read_block(self, size, block_obj):
        buf = self.read_buf(size)
        container = block_obj.parse(buf)
        return container

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

    def process_extended_headers(self):
        self.reel_headers.extended_headers.append(
            self.read_block(1024, segd_h.Extended_header_block()))

    def process_external_headers(self):
        self.reel_headers.external_header = self.read_block(
            1024, segd_h.External_header_block())

    def process_trace_headers(self):
        self.trace_headers = TraceHeaders()

        self.trace_headers.trace_header = self.read_block(
            20, segd_h.Trace_header())
        n = self.trace_headers.trace_header.number_trace_header_extension
        for i in range(n):
            self.trace_headers.trace_header_N.append(
                self.read_block(32, segd_h.Trace_header_extension(i)))
        self.samples = self.trace_headers.trace_header_N[0][
            'samples_per_trace']
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
