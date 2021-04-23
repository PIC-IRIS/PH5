#!/usr/bin/env pnpython3
#
# A class to read Fairfield SEG-D Version
# 1.5-1 & 1.6 files from the Sweetwater experiment.
#
# Steve Azevedo, May 2014
#

import sys
import logging
import os
import exceptions
import numpy as np
from ph5.core import segd_h

PROG_VERSION = "2021.112"
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
                 'line_number', 'event_number',
                 'trace_epoch', 'preamp_gain_db',
                 'lat', 'lon', 'ele']

    def __init__(self):
        self.trace_header = None
        self.trace_header_N = []
        self.line_number = None
        self.event_number = None
        self.trace_epoch = None
        self.lat = None
        self.lon = None
        self.ele = None
        self.preamp_gain_db = None


class Reader ():
    def __init__(self, infile=None):
        self.manufacturer = 'FairfieldNodal'
        self.infile = infile
        self.FH = None
        self.endianess = 'big'  # SEG-D is always big endian(?)
        # From General headers
        self.file_number = None
        self.record_length_sec = None
        self.chan_sets_per_scan = None
        self.extended_header_blocks = None
        self.external_header_blocks = None
        self.sample_rate = None
        # From Extended headers
        self.deploy_epoch = None
        self.pickup_epoch = None
        self.id_number = None
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

    def name(self):
        '''   Return name of open file   '''
        if self.FH:
            return self.FH.name
        else:
            return None

    def read_storage_unit_label(self):
        '''   For tapes   '''
        buf = self.read_buf(128)
        sul = segd_h.Storage_unit_label()
        sul.parse(buf)

        keys = segd_h.Storage_unit_label().__keys__

        for k in keys:
            what = 'container.{0}'.format(k)
            LOGGER.info("{0} {1}".format(k, eval(what)))

    def read_general_header_block_1(self):
        '''   Read the first General Header Block   '''
        buf = self.read_buf(32)

        ghb1 = segd_h.General_header_block_1()

        container = ghb1.parse(buf)

        return container

    def read_general_header_block_2(self):
        '''   Read the second General Header Block 2   '''
        buf = self.read_buf(32)

        ghb1 = segd_h.General_header_block_2()

        container = ghb1.parse(buf)

        return container

    def read_channel_set_descriptor(self):
        '''   Read Channel set descriptor   '''
        buf = self.read_buf(32)
        csd = segd_h.Channel_set_descriptor()

        container = csd.parse(buf)

        return container

    def read_extended_header_1(self):
        '''   Read first extended header   '''
        buf = self.read_buf(32)
        eh1 = segd_h.Extended_header_1()

        container = eh1.parse(buf)

        return container

    def read_extended_header_2(self):
        '''   Read second extended header   '''
        buf = self.read_buf(32)
        eh2 = segd_h.Extended_header_2()

        container = eh2.parse(buf)

        return container

    def read_extended_header_3(self):
        '''   Read third extended header   '''
        buf = self.read_buf(32)
        eh3 = segd_h.Extended_header_3()

        container = eh3.parse(buf)

        return container

    def read_extended_header_4(self):
        '''   Read forth extended header 0-n   '''
        buf = self.read_buf(32)
        eh4 = segd_h.Extended_header_4()

        container = eh4.parse(buf)

        return container

    def read_external_header(self):
        '''   Read first external header   '''
        buf = self.read_buf(32)
        eh = segd_h.External_header()

        container = eh.parse(buf)

        return container

    def read_external_header_shot(self):
        '''   Read second external header   '''
        buf = self.read_buf(32)
        ehs = segd_h.External_header_shot()

        container = ehs.parse(buf)

        return container

    def process_general_headers(self):
        self.reel_headers = ReelHeaders()

        self.reel_headers.general_header_blocks.append(
            self.read_general_header_block_1())
        self.reel_headers.general_header_blocks.append(
            self.read_general_header_block_2())
        # Set file number
        if self.reel_headers.general_header_blocks[0].file_number == 0xFFFF:
            self.file_number = self.reel_headers.\
                read_general_header_blocks[1].extended_file_number
        else:
            self.file_number = self.reel_headers.\
                general_header_blocks[0].file_number
        # Set record length
        if self.reel_headers.general_header_blocks[0].record_length == 0xFFF:
            self.record_length_sec = self.reel_headers.\
                general_header_blocks[1].extended_record_length
        else:
            self.record_length_sec = self.reel_headers.\
                general_header_blocks[0].record_length * 0.512
        # Set number of channel sets
        if self.reel_headers.general_header_blocks[
                0].chan_sets_per_scan == 0xFF:
            self.chan_sets_per_scan = self.reel_headers.\
                general_header_blocks[1].extended_chan_sets_per_scan_type
        else:
            self.chan_sets_per_scan = self.reel_headers.\
                general_header_blocks[0].chan_sets_per_scan
        # Number of extended headers
        if self.reel_headers.general_header_blocks[0].\
           number_extended_header_blocks == 0xFF:
            self.extended_header_blocks = self.reel_headers.\
                general_header_blocks[1].extended_header_blocks
        else:
            self.extended_header_blocks = self.reel_headers.\
                general_header_blocks[0].number_extended_header_blocks
        # Number of external headers
        if self.reel_headers.general_header_blocks[0].\
           number_external_header_blocks == 0xFF:
            self.external_header_blocks = self.\
                reel_headers.general_header_blocks[1].external_header_blocks
        else:
            self.external_header_blocks = self.\
                reel_headers.general_header_blocks[0].\
                number_external_header_blocks
        # Get sample rate from base scan interval (LSB is 1/16 milli-second)
        self.sample_rate = int(
            (1. / (self.reel_headers.
                   general_header_blocks[0].base_scan_interval / 16.)) * 1000.)

    def process_channel_set_descriptors(self):
        def create_key():
            # Create a mapping between channel sets to streamer cable numbers
            kv = {}
            for cs in self.reel_headers.channel_set_descriptor:
                k = cs.chan_set_number
                v = cs.streamer_cable_number
                kv[k] = v

            return kv

        for i in range(self.chan_sets_per_scan):
            cs = self.read_channel_set_descriptor()
            self.reel_headers.channel_set_descriptor.append(cs)
            # ***   Should we get current channel set number   ***
            # Channel set start time in seconds
            self.channel_set_start_time_sec =\
                self.reel_headers.channel_set_descriptor[i].\
                chan_set_start_time * 0.002
            # Channel set end time in seconds
            self.channel_set_end_time_sec =\
                self.reel_headers.channel_set_descriptor[
                    i].chan_set_end_time * 0.002
            # ***   Calculate scale factor for mili-volts.
            # Fairfield data recorded as mili-volts   ***
        self.reel_headers.channel_set_to_streamer_cable_map = create_key()

    def process_extended_headers(self):
        if self.extended_header_blocks > 0:
            self.reel_headers.extended_headers.append(
                self.read_extended_header_1())
        if self.extended_header_blocks > 1:
            self.reel_headers.extended_headers.append(
                self.read_extended_header_2())
        if self.extended_header_blocks > 2:
            self.reel_headers.extended_headers.append(
                self.read_extended_header_3())
        n = self.extended_header_blocks - 3
        for i in range(n):
            self.reel_headers.extended_headers.append(
                self.read_extended_header_4())
        self.deploy_epoch = self.reel_headers.extended_headers[
                                0].epoch_deploy / 1000000.
        self.pickup_epoch = self.reel_headers.extended_headers[
                                0].epoch_pickup / 1000000.
        self.id_number = self.reel_headers.extended_headers[0]['id_number']

    def process_external_headers(self):
        self.reel_headers.external_header = self.read_external_header()
        n = self.external_header_blocks
        if n > 1:
            self.reel_headers.external_header_shot.append(
                self.read_external_header_shot())
            # Throw away remaining external headers
            s = (n - 2) * 32
            self.read_buf(s)

    def read_trace_header(self):
        '''   Read 20 byte trace header   '''
        buf = self.read_buf(20)
        th = segd_h.Trace_header()

        container = th.parse(buf)

        return container

    def read_trace_header_1(self):
        buf = self.read_buf(32)
        th1 = segd_h.trace_header_1()

        container = th1.parse(buf)

        return container

    def read_trace_header_2(self):
        buf = self.read_buf(32)
        th2 = segd_h.trace_header_2()

        container = th2.parse(buf)

        return container

    def read_trace_header_3(self):
        buf = self.read_buf(32)
        th3 = segd_h.trace_header_3()

        container = th3.parse(buf)

        return container

    def read_trace_header_4(self):
        buf = self.read_buf(32)
        th4 = segd_h.trace_header_4()

        container = th4.parse(buf)

        return container

    def read_trace_header_5(self):
        buf = self.read_buf(32)
        th5 = segd_h.trace_header_5()

        container = th5.parse(buf)

        return container

    def read_trace_header_6(self):
        buf = self.read_buf(32)
        th6 = segd_h.trace_header_6()

        container = th6.parse(buf)

        return container

    def read_trace_header_7(self):
        buf = self.read_buf(32)
        th7 = segd_h.trace_header_7()

        container = th7.parse(buf)

        return container

    def read_trace_header_8(self):
        buf = self.read_buf(32)
        th8 = segd_h.trace_header_8()

        container = th8.parse(buf)

        return container

    def read_trace_header_9(self):
        buf = self.read_buf(32)
        th9 = segd_h.trace_header_9()

        container = th9.parse(buf)

        return container

    def read_trace_header_10(self):
        buf = self.read_buf(32)
        th10 = segd_h.trace_header_10()

        container = th10.parse(buf)

        return container

    def process_trace_headers(self):
        self.trace_headers = TraceHeaders()

        self.trace_headers.trace_header = self.read_trace_header()
        n = self.trace_headers.trace_header.trace_extension_blocks
        if n == 0:
            chan_set = self.trace_headers.trace_header.channel_set - 1
            n = self.reel_headers.channel_set_descriptor[chan_set].\
                number_trace_header_extensions
        if n > 0:
            self.trace_headers.trace_header_N.append(
                self.read_trace_header_1())
            n -= 1
        if n > 0:
            self.trace_headers.trace_header_N.append(
                self.read_trace_header_2())
            n -= 1
        if n > 0:
            self.trace_headers.trace_header_N.append(
                self.read_trace_header_3())
            n -= 1
        if n > 0:
            self.trace_headers.trace_header_N.append(
                self.read_trace_header_4())
            n -= 1
        if n > 0:
            self.trace_headers.trace_header_N.append(
                self.read_trace_header_5())
            n -= 1
        if n > 0:
            self.trace_headers.trace_header_N.append(
                self.read_trace_header_6())
            n -= 1
        if n > 0:
            self.trace_headers.trace_header_N.append(
                self.read_trace_header_7())
            n -= 1
        if n > 0:
            self.trace_headers.trace_header_N.append(
                self.read_trace_header_8())
            n -= 1
        if n > 0:
            self.trace_headers.trace_header_N.append(
                self.read_trace_header_9())
            n -= 1
        if n > 0:
            self.trace_headers.trace_header_N.append(
                self.read_trace_header_10())
        # Note: SEG-D 2.1 allows a total of 15 trace header extensions.
        # We only read 10 as per Fairfield rg1.6

        self.trace_headers.line_number = self.trace_headers.trace_header_N[
            4].line_number
        self.trace_headers.event_number = self.trace_headers.trace_header_N[
            1].shot_point
        self.trace_headers.trace_epoch = self.trace_headers.trace_header_N[
            2].shot_epoch
        self.trace_headers.preamp_gain_db = self.trace_headers.trace_header_N[
            3].preamp_gain_db
        self.trace_headers.lat = self.trace_headers.trace_header_N[
            4].receiver_point_Y_final
        self.trace_headers.lon = self.trace_headers.trace_header_N[
            4].receiver_point_X_final
        self.trace_headers.ele = self.trace_headers.trace_header_N[
            4].receiver_point_depth_final

        self.samples = self.trace_headers.trace_header_N[
            0].samples_per_trace

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
#
# Mix in's
#


def swap_bits(buf):
    b, ll = segd_h.swap_block_bits()
    c = b.parse(buf)

    return ll.build(c)


def swap_64(buf):
    b, ll = segd_h.swap_block_64()
    c = b.parse(buf)

    return ll.build(c)


def swap_32(buf):
    b, ll = segd_h.swap_block_32()
    c = b.parse(buf)

    return ll.build(c)


def swap_16(buf):
    b, ll = segd_h.swap_block_16()
    c = b.parse(buf)

    return ll.build(c)


if __name__ == '__main__':
    global RH, TH
    TH = []

    def print_container(container):
        keys = container.keys()
        for k in keys:
            print k, container[k]

        print '-' * 80

    RH = ReelHeaders()
    sd = Reader(infile=sys.argv[1])
    sd.process_general_headers()
    print '*' * 80
    print sd.infile
    print '*' * 80
    print "*** General Header Block 1 ***"
    print_container(sd.reel_headers.general_header_block_1)
    print "*** General Header Block 2 ***"
    print_container(sd.reel_headers.general_header_block_2)
    print "*** Channel Set Descriptor(s): ***"
    sd.process_channel_set_descriptors()
    i = 1
    for c in sd.reel_headers.channel_set_descriptor:
        print i
        i += 1
        print_container(c)
    print "*** Extended Headers ***"
    sd.process_extended_headers()
    print_container(sd.reel_headers.extended_header_1)
    print 2
    print_container(sd.reel_headers.extended_header_2)
    print 3
    print_container(sd.reel_headers.extended_header_3)
    i = 1
    for c in sd.reel_headers.extended_header_4:
        print i
        i += 1
        print_container(c)
    print "*** External Header ***"
    sd.process_external_headers()
    print_container(sd.reel_headers.external_header)
    i = 1
    for c in sd.reel_headers.external_header_shot:
        print i
        i += 1
        print_container(c)
    n = 1
    print "*** Trace Header ***", n

    traces = sd.process_traces()
    for cs in range(sd.chan_sets_per_scan):
        print_container(sd.trace_headers[cs].trace_header)
        i = 1
        for c in sd.trace_headers.trace_header_N:
            print i
            i += 1
            print_container(c)

        trace = traces[cs]
        n += 1
        while True:
            if sd.isEOF():
                break
            print "*** Trace Header ***", n
            print_container(sd.trace_headers[cs].trace_header)
            i = 1
            for c in sd.trace_headers[cs].trace_header_N:
                print i
                i += 1
                print_container(c)
            n += 1

    LOGGER.info("There were {0} traces.".format(n))
