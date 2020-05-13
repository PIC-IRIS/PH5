#!/usr/bin/env pnpython3

#
# Efficient and complete rt-130 file reader.
#
# 2008.311 for CPU FW 2.9.4
#
# Steve Azevedo, November 2008
#

import os
import zipfile
import tarfile
import re
import exceptions
import os.path
import string
import math
import logging
from ph5.core import rt_130_h, timedoy

PROG_VERSION = '2019.14'
LOGGER = logging.getLogger(__name__)

fileRE = re.compile(r".*\w{9}_\w{8}$")
sohRE = re.compile(r".*[Ss][Oo][Hh]\.[Rr][Tt]$")
skipRE = re.compile("__recursion_lock__|Reserved.*")

PACKET_SIZE = 1024
NUM_STREAMS = 9
NUM_CHANNELS = 6
# Bit weights at 1 and 32 x in micro-volts
BIT_WEIGHT = {'x1': '1.5895uV', 'x32': '49.671uV'}

# End of event, event header found
END_OF_EVENT_EH = 1
# End of event, event trailer found
END_OF_EVENT_ET = 2
# End of event, new event in DT packet
END_OF_EVENT_DT = 3
# Corrupt packet flag
CORRUPT_PACKET = 4
# Ignore this packet
IGNORE_PACKET = 5
# End of event Gap
END_OF_EVENT_GAP = 6
# End of event overlap
END_OF_EVENT_OVERLAP = 7


class REFError(exceptions.Exception):
    pass


class LastPacket(object):
    __slots__ = 'header', 'payload'

    def __init__(self):
        self.header = None
        self.payload = None


class TimeCheck(object):
    __slots__ = 'start_time_asc', 'start_time_secs', 'start_time_ms',\
                'end_time_secs', 'end_time_ms', 'sample_interval', 'samples'

    def __init__(self):
        self.start_time_asc = None
        self.start_time_secs = None
        self.start_time_ms = None
        self.end_time_secs = 0
        self.end_time_ms = 0
        self.sample_interval = None
        self.samples = 0


class ReadBuffer(object):
    '''   buf = string buffer
          ptr = next read position
          len = total len of buffer in bytes
    '''
    __slots__ = 'buf', 'ptr', 'len', 'set', 'clear', 'rewind', 'inc'

    def __init__(self):
        self.clear()

    def set(self, b):
        self.buf = b
        self.len = len(b)
        self.ptr = 0

    def clear(self):
        self.buf = None
        self.ptr = None
        self.len = None

    def rewind(self):
        self.set('')

    def inc(self, n):
        self.ptr += n


class DataFile(object):
    __slots__ = 'basefile', 'subfiles', 'subfilesall', 'fh', 'kind', 'next'

    def __init__(self, basefile=None):
        # The filename of directory name
        self.basefile = basefile
        # Subfiles in zip, tar, or raw file
        self.subfiles = []
        # All the subfiles
        self.subfilesall = []
        # The open filehandle or None
        self.fh = None
        # What kind of file is this?
        self.kind = None

    def set(self, what):
        self.subfiles = what
        self.subfilesall = what

    def rewind(self):
        self.subfiles = self.subfilesall

    def next(self):
        f = None
        try:
            f = self.subfiles[0]
        except IndexError:
            self.subfiles = []

        try:
            self.subfiles = self.subfiles[1:]
        except IndexError:
            self.subfiles = []

        return f


class DataPacket(object):
    '''   Keep start time for each packet of data   '''
    __slots__ = 'year', 'doy', 'hour', 'minute', 'seconds', 'milliseconds',\
                'trace'

    def __init__(self, c, p):
        self.year = p.year
        self.doy = p.doy
        self.hour = p.hr
        self.minute = p.mn
        self.seconds = p.sc
        self.milliseconds = p.ms
        self.trace = c.data


class Event130(object):
    __slots__ = (
        'event', 'year', 'doy', 'hour', 'minute', 'seconds', 'sampleRate',
        'sampleCount', 'channel_number', 'stream_number', 'trace', 'gain',
        'bitWeight', 'unitID', 'last_sample_time', 'milliseconds')

    def __init__(self):
        self.event = None
        self.year = None
        self.doy = None
        self.hour = None
        self.minute = None
        self.seconds = None
        self.milliseconds = None
        self.sampleRate = None
        self.sampleCount = None
        self.channel_number = None
        self.stream_number = None
        # trace is a list of DataPacket
        self.trace = []
        self.gain = None
        self.bitWeight = None
        self.unitID = None
        self.last_sample_time = None


class Log130(object):
    __slots__ = 'year', 'doy', 'hour', 'minute', 'seconds', 'message'

    def __init__(self):
        self.year = None
        self.doy = None
        self.hour = None
        self.minute = None
        self.seconds = None
        self.message = ''


'''
class streams (object) :
    __slots__ = ('channel')

    def __init__ (self, stream) :
        self.channel = []
        for i in range (NUM_CHANNELS) :
            t = Event130 ()
            t.channel_number = i
            t.stream_number = stream
            self.channel.append (t)
'''
validTypes = {'ZIP': 'ZIP', 'tar': 'tar', 'ref': 'ref', 'RAW': 'RAW'}


class NeoRAW:
    '''   rt-130 raw file reader   '''

    def __init__(self, filename, verbose=False):
        self.verbose = verbose
        # The file/directory to read from
        self.df = DataFile(filename)
        self.df.kind = 'RAW'
        # The buffer to read into
        self.buf = ReadBuffer()
        self.ERRS = []

    # Return any error messages
    def errors(self):
        errs = self.ERRS
        self.ERRS = []
        return errs

    # Prime the pump
    def open(self):
        self._get_raw_names()
        self._get_raw_filehandle()

    # Read into buffer
    def read(self):
        self._get_rawfile_buf()

    # Close open file handle
    def close(self):
        if self.df.fh is not None:
            if self.verbose:
                LOGGER.info("Closing subfile.")

            os.close(self.df.fh)
        self.df.fh = None

    def rewind_subfile(self, ptr=None):
        self.buf.rewind()
        os.lseek(self.df.fh, ptr, os.SEEK_CUR)

    # Read and return one packet from buffer
    def getPacket(self):
        pbuf = None
        if self.buf.ptr >= self.buf.len:
            self._get_rawfile_buf()

        ptr = self.buf.ptr
        ll = self.buf.len

        if ptr < ll:
            pbuf = self.buf.buf[ptr:PACKET_SIZE + ptr]
            len_pbuf = len(pbuf)
            self.buf.inc(len_pbuf)
            if len_pbuf != PACKET_SIZE:
                self.ERRS.append(
                    "Read Error: read %d of %d" %
                    (len_pbuf, PACKET_SIZE))
                if self.verbose:
                    LOGGER.error(
                        "Read Error: read %d of %d" %
                        (len_pbuf, PACKET_SIZE))

        return pbuf

    # Get all of the sub-file names
    def _get_names(self, dum, dirname, files):
        if self.verbose:
            LOGGER.info("Reading: {0}".format(dirname))

        for f in files:
            # Skip directories
            if os.path.isdir(f):
                continue
            # Found one!
            if fileRE.match(f) or sohRE.match(f):
                self.sf.append(os.path.join(dirname, f))

    # find all of the raw subfiles
    def _get_raw_names(self):
        self.sf = []
        filename = os.path.abspath(self.df.basefile)
        os.path.walk(filename, self._get_names, 1)
        self.sf.sort()
        self.df.set(self.sf)

    # Try to get a filehandle for the next file
    def _get_raw_filehandle(self):
        self.close()
        try:
            rawfile = None
            rawfile = self.df.next()
        except IndexError:
            self.df.fh = None

        if rawfile:
            if self.verbose:
                LOGGER.info("\tOpening: {0}".format(rawfile))

            try:
                self.df.fh = os.open(rawfile, os.O_RDONLY)
            except Exception as e:
                self.ERRS.append("%s" % e.message)
                if self.verbose:
                    LOGGER.error(e.message)
                self.df.fh = None

    # Try to read the next buffers worth of data
    def _get_rawfile_buf(self):
        self.buf.clear()
        # No open filehandle so try to open one
        if self.df.fh is None:
            self._get_raw_filehandle()

        # If we have an open filehandle read a buffers worth from it
        if self.df.fh is not None:
            buf = os.read(self.df.fh, PACKET_SIZE * 4)
            if buf:
                self.buf.set(buf)
            else:
                self.close()
                self._get_rawfile_buf()


class NeoZIP:
    '''   rt-130 zip file reader
          Uses the module zipfile to process the contents
    '''

    def __init__(self, filename, verbose=False):
        self.verbose = verbose
        self.df = DataFile(filename)
        self.df.kind = 'ZIP'
        self.buf = ReadBuffer()
        self.ERRS = []

    # Return any error messages
    def errors(self):
        errs = self.ERRS
        self.ERRS = []
        return errs

    def open(self):
        self._get_raw_names()

    def read(self):
        self._get_raw_file_buf()

    def close(self):
        if self.verbose:
            LOGGER.info("Closing: {0}".format(self.df.basefile))

        self.df.fh.close()
        self.df.fh = None

    def rewind_subfile(self, ptr=None):
        self.buf.ptr += ptr

    def getPacket(self):
        pbuf = None
        if self.buf.ptr >= self.buf.len:
            self._get_raw_file_buf()

        ptr = self.buf.ptr
        ll = self.buf.len

        if ptr < ll:
            pbuf = self.buf.buf[ptr:PACKET_SIZE + ptr]
            len_pbuf = len(pbuf)
            self.buf.inc(len_pbuf)
            if len_pbuf != PACKET_SIZE:
                self.ERRS.append(
                    "Read Error: read %d of %d" %
                    (len_pbuf, PACKET_SIZE))
                if self.verbose:
                    LOGGER.error(
                        "Read Error: read %d of %d" %
                        (len_pbuf, PACKET_SIZE))

        return pbuf

    def _get_raw_file_buf(self):
        self.buf.clear()
        buf = ''
        # Get next file from sorted list
        while True:
            z = self.df.next()
            if not z:
                return

            # Only select files that match RE
            if fileRE.match(z) or sohRE.match(z):
                break

        if self.verbose:
            LOGGER.info("\tReading: {0}".format(z))

        try:
            buf = self.df.fh.read(z)
        except Exception as e:
            self.ERRS.append("%s" % e.message)
            if self.verbose:
                LOGGER.error(e.message)

        # XXX Should really check the size of the buffer here!
        if buf:
            self.buf.set(buf)

    def _get_raw_names(self):
        # Open the zip file
        try:
            self.df.fh = zipfile.ZipFile(self.df.basefile)
        except Exception as e:
            self.ERRS.append("%s" % e.message)
            if self.verbose:
                LOGGER.error(e.message)

        # Get a list of filenames
        zipnames = sorted(self.df.fh.namelist())
        # Sort then (by time)
        self.df.set(zipnames)


class NeoTAR:
    '''   rt-130 tar file reader
          Uses the module tarfile to process the contents
    '''

    def __init__(self, filename, verbose=False):
        self.verbose = verbose
        self.df = DataFile(filename)
        self.df.kind = 'tar'
        self.buf = ReadBuffer()
        self.ERRS = []

    # Return any error messages
    def errors(self):
        errs = self.ERRS
        self.ERRS = []
        return errs

    def open(self):
        self._get_raw_names()

    def read(self):
        self._get_raw_file_buf()

    def close(self):
        if self.verbose:
            LOGGER.info("Closing: {0}".format(self.df.basefile))

        self.df.fh.close()
        self.df.fh = None

    def rewind_subfile(self, ptr=None):
        self.buf.ptr += ptr

    def getPacket(self):
        pbuf = None
        if self.buf.ptr >= self.buf.len:
            self._get_raw_file_buf()

        ptr = self.buf.ptr
        ll = self.buf.len

        if ptr < ll:
            pbuf = self.buf.buf[ptr:PACKET_SIZE + ptr]
            len_pbuf = len(pbuf)
            self.buf.inc(len_pbuf)
            if len_pbuf != PACKET_SIZE:
                self.ERRS.append(
                    "Read Error: read %d of %d" %
                    (len_pbuf, PACKET_SIZE))
                if self.verbose:
                    LOGGER.error(
                        "Read Error: read %d of %d\n" %
                        (len_pbuf, PACKET_SIZE))

        return pbuf

    # Compare tarfile members by file name
    def _member_cmp(self, a, b):
        return cmp(a.name, b.name)

    def _get_raw_file_buf(self):
        self.buf.clear()
        buf = ''
        # Get next member
        while True:
            m = self.df.next()
            if not m:
                return
            # Does it match our expected file name?
            if fileRE.match(m.name) or sohRE.match(m.name):
                break

        if self.verbose:
            LOGGER.info("\tReading: {0}".format(m.name))

        try:
            buf = self.df.fh.extractfile(m).read()
        except Exception as e:
            self.ERRS.append("%s" % e.message)
            if self.verbose:
                LOGGER.error(e.message)
        if buf:
            self.buf.set(buf)

    def _get_raw_names(self):
        # Try to open tar file
        if self.verbose:
            LOGGER.info("Opening: {0}".format(self.df.basefile))
        try:
            self.df.fh = tarfile.open(self.df.basefile)
        except Exception as e:
            self.ERRS.append("%s" % e.message)
            if self.verbose:
                LOGGER.error(e.message)
        # Get tar file 'members' and sort them
        members = self.df.fh.getmembers()
        members.sort(self._member_cmp)
        self.df.set(members)


class NeoREF:
    '''   rt-130 raw ref file reader   '''

    def __init__(self, filename, verbose=False):
        self.verbose = verbose
        self.df = DataFile(filename)
        self.df.kind = 'ref'
        self.buf = ReadBuffer()
        self.ERRS = []

    # Return any error messages
    def errors(self):
        errs = self.ERRS
        self.ERRS = []
        return errs

    def open(self):
        self._get_raw_names()

    def read(self):
        self._get_raw_file_buf()

    def close(self):
        if self.verbose:
            LOGGER.info("Closing: {0}".format(self.df.basefile))

        if self.df.fh is not None:
            os.close(self.df.fh)

        self.df.fh = None

    def rewind_subfile(self, ptr=None):
        self.buf.rewind()
        os.lseek(self.df.fh, ptr, os.SEEK_CUR)

    def getPacket(self):
        pbuf = None
        if self.buf.ptr >= self.buf.len:
            self._get_raw_file_buf()

        ptr = self.buf.ptr
        ll = self.buf.len

        if ptr < ll:
            pbuf = self.buf.buf[ptr:PACKET_SIZE + ptr]
            len_pbuf = len(pbuf)
            self.buf.inc(len_pbuf)
            if len_pbuf != PACKET_SIZE:
                self.ERRS.append(
                    "Read Error: read %d of %d" %
                    (len_pbuf, PACKET_SIZE))
                if self.verbose:
                    LOGGER.error(
                        "Read Error: read %d of %d\n" %
                        (len_pbuf, PACKET_SIZE))
        return pbuf

    def _get_raw_file_buf(self):
        self.buf.clear()
        if self.df.fh is not None:
            try:
                buf = os.read(self.df.fh, PACKET_SIZE * 4)
            except Exception as e:
                self.ERRS.append("%s" % e.message)
                if self.verbose:
                    LOGGER.error(e.message)

            if buf:
                self.buf.set(buf)
            else:
                self.close()

    def _get_raw_names(self):
        self.close()
        if self.verbose:
            LOGGER.info("Closing: {0}".format(self.df.basefile))

        try:
            self.df.fh = os.open(self.df.basefile, os.O_RDONLY)
        except Exception as e:
            self.ERRS.append("%s" % e.message)
            if self.verbose:
                LOGGER.error(e.message)

        self.df.set([self.df.basefile])


class PN130:
    '''   Process rt-130 data into events.
          self.reader -- read data from zip, tar, ref, or raw dir
                      -- provides: open -- Initialises input
                                   close -- Closes input
                                   read -- Read a buffer of data
                                   getPacket -- Return a single packet
          self.STREAMS -- The current event organized by stream
          self.LOGS -- The log info, SOH etc.
          self.ERRS -- Any error messages
    '''
    SEARCH_FOR_ET = True
    SEEN = {}

    def __init__(self, filename, filetype=None, verbose=False, par=None):
        # Zero packet counters
        self.zero_cnts()
        # Get filetype
        if filetype is not None:
            if filetype not in validTypes:
                filetype = None

        if filetype is None:
            filetype = self.guess_type(filename)
        # Set the reader based on filetype
        if filetype == 'RAW':
            self.reader = NeoRAW(filename, verbose)
        elif filetype == 'ZIP':
            self.reader = NeoZIP(filename, verbose)
        elif filetype == 'tar':
            self.reader = NeoTAR(filename, verbose)
        elif filetype == 'ref':
            self.reader = NeoREF(filename, verbose)
        else:
            self.reader = None

        self.verbose = int(verbose)
        self.LOGS = []
        self.LOGptr = 0
        self.SOH = []
        self.SOHptr = 0
        self.ERRS = []
        self.ERRSptr = 0
        self.par = par
        # Keep track of packet times to check for gaps/verlaps
        self.last_packet_time = {}
        # self.last_packet_type = None
        self.previous_event = [None] * NUM_STREAMS
        # This way it can be addressed self.current_event[stream][channel]
        self.current_event = [None] * NUM_STREAMS
        # End of event marker per stream
        # self.num_end_of_event = [-1] * NUM_STREAMS
        self.entry_num = 0
        self.points = [0] * NUM_STREAMS
        # Which channels have been seen for this event
        # self.das_channel_stream_seen = {}

        self.lastDT = LastPacket()
        self.lastAD = LastPacket()
        self.lastCD = LastPacket()
        self.lastEH = LastPacket()
        self.lastET = LastPacket()
        self.lastSH = LastPacket()
        self.lastSC = LastPacket()
        self.lastDS = LastPacket()
        self.lastFD = LastPacket()
        self.lastOM = LastPacket()

        self.open()

    # Initialize inputs
    def open(self):
        self.reader.open()
        if self.reader.df.fh is None:
            self.ERRS.append(
                "Warning: open of %s failed!" %
                self.reader.df.basefile)
            if self.verbose:
                LOGGER.warning(
                    "Warning: open of {0} failed!"
                    .format(self.reader.df.basefile))

    # Keep track of number of packets
    def zero_cnts(self):
        self.DTcnt = 0
        self.EHcnt = 0
        self.ETcnt = 0
        self.SHcnt = 0
        self.SCcnt = 0
        self.ADcnt = 0
        self.CDcnt = 0
        self.DScnt = 0
        self.FDcnt = 0
        self.OMcnt = 0

    # Guess file type based on suffix
    def guess_type(self, filename):
        # Its a directory so it must be raw data
        if os.path.isdir(filename):
            return 'RAW'
        elif fileRE.match(filename):
            return 'ref'

        suffix = filename[-3:]
        if suffix == 'ZIP' or suffix == 'tar' or suffix == 'ref':
            return suffix
        else:
            return None

    def packet_time_epoch(self, p):
        tdoy = timedoy.TimeDOY(year=p.year,
                               month=None,
                               day=None,
                               hour=p.hr,
                               minute=p.mn,
                               second=p.sc,
                               microsecond=0,
                               doy=p.doy,
                               epoch=None,
                               dtobject=None)
        return tdoy.epoch(), int(p.ms)

    def packet_time_string(self, p):
        packet_time = ("%04d:%03d:%02d:%02d:%02d:%03d" % (p.year,
                                                          p.doy,
                                                          p.hr,
                                                          p.mn,
                                                          p.sc,
                                                          p.ms))
        return packet_time

    def packet_tagline_string(self, p):
        packet_tagline = (
                "\n%07d %s exp %02d bytes %04d %s ID: %s seq %04d" % (
                    self.entry_num,
                    p.type,
                    p.experiment,
                    p.bytes,
                    self.packet_time_string(p),
                    p.unit,
                    p.sequence))
        return packet_tagline

    # c is the ET payload information
    # p is the packet header info
    def set_et_info(self, c, p):
        '''   Set info for event trailer   '''
        # Data stream
        stream = int(c.DataStream)
        # Event
        event = int(c.EventNumber)
        # How many channels
        try:
            num_channels = int(c.TotalChannels)
        except ValueError:
            num_channels = NUM_CHANNELS

        # Only for ET packets
        last_sample_time = c.LastSampleTime
        # First sample time
        fst = decode_sample_time(c.FirstSampleTime)

        # We have seen this event/stream before, good!
        if self.current_event[stream] is not None:
            # Look at each channel
            for num_chan in range(num_channels):
                # Okay, we are in the same event
                if self.current_event[stream][num_chan].event == event:
                    # Set the last sample time
                    self.current_event[stream][
                        num_chan].last_sample_time = last_sample_time
                else:
                    # We really should never get here
                    self.ERRS.append(
                        "Error: Event trailer before any event data."
                        "Event %d Channel %d" %
                        (event, num_chan))
                    if self.verbose:
                        LOGGER.error(
                            "Event trailer before any event data."
                            "Event %d Channel %d" %
                            (event, num_chan))

            self.previous_event[stream] = self.current_event[stream]
            self.current_event[stream] = None
        else:
            self.ERRS.append(
                "Error: Event trailer before event data. Event %d" %
                event)
            if self.verbose:
                LOGGER.error(
                    "Event trailer before event data. Event %d" % event)

        # Logging
        self.LOGS.append(self.packet_tagline_string(p))
        s = "Event Trailer"
        self.LOGS.append(s)
        s = "  event = %d" % event
        self.LOGS.append(s)
        s = "  stream = %d" % (stream + 1)
        self.LOGS.append(s)
        s = "  format = %s" % c.DataFormat
        self.LOGS.append(s)
        s = "  stream name = %s" % c.StreamName
        self.LOGS.append(s)
        s = "  sample rate = %s" % c.SampleRate
        self.LOGS.append(s)
        s = "  trigger type = %s" % c.TriggerType
        self.LOGS.append(s)
        t = decode_sample_time(c.TriggerTime)
        s = "  trigger time = %04d %03d:%02d:%02d:%02d:%03d" % (
            t[0], t[1], t[2], t[3], t[4], t[5])
        self.LOGS.append(s)

        s = "  first sample = %04d %03d:%02d:%02d:%02d:%03d" % (
            fst[0], fst[1], fst[2], fst[3], fst[4], fst[5])
        self.LOGS.append(s)
        t = decode_sample_time(c.LastSampleTime)
        if t[0] is not None:
            s = "  last sample = %04d %03d:%02d:%02d:%02d:%03d" % (
                t[0], t[1], t[2], t[3], t[4], t[5])
            self.LOGS.append(s)

        s = "  bit weights = %s" % ' '.join(c.NominalBitWeight).strip()
        self.LOGS.append(s)
        s = "  true weights = %s" % ' '.join(c.TrueBitWeight).strip()
        self.LOGS.append(s)
        self.LOGS.append(
            "DAS: %s EV: %04d DS: %d FST = %s TT = %s NS: %d SPS: %s"
            "ETO: 0" % (
                p.unit,
                event,
                stream + 1,
                colonize(
                    c.FirstSampleTime),
                colonize(
                    c.TriggerTime),
                self.points[
                    stream],
                c.SampleRate))

    def set_eh_info(self, c, p):
        '''   Set info from event header   '''
        # Data stream
        stream = int(c.DataStream)
        # Event
        event = int(c.EventNumber)
        # How many channels
        try:
            num_channels = int(c.TotalChannels)
        except ValueError:
            num_channels = NUM_CHANNELS

        # Only for ET packets
        # last_sample_time = c.LastSampleTime
        # First sample time
        fst = decode_sample_time(c.FirstSampleTime)
        #
        new_event = build_empty_current_stream()

        # First time for this event/stream
        if self.current_event[stream] is None:
            # Set info for new event
            for i in range(num_channels):
                new_event[i].unitID = p.unit
                new_event[i].event = event
                new_event[i].year = fst[0]
                new_event[i].doy = fst[1]
                new_event[i].hour = fst[2]
                new_event[i].minute = fst[3]
                new_event[i].seconds = fst[4]
                new_event[i].milliseconds = fst[5]
                new_event[i].sampleCount = 0
                new_event[i].sampleRate = c.SampleRate
                new_event[i].trace = []
                new_event[i].gain = c.Gain[i]
                new_event[i].bitWeight = c.TrueBitWeight[i]
                new_event[i].channel_number = i
                new_event[i].stream_number = stream

            self.current_event[stream] = new_event
        # We have seen this stream before
        # We need to check if its a new event
        else:
            for i in range(num_channels):
                new_event[i].unitID = p.unit
                new_event[i].event = event
                new_event[i].year = fst[0]
                new_event[i].doy = fst[1]
                new_event[i].hour = fst[2]
                new_event[i].minute = fst[3]
                new_event[i].seconds = fst[4]
                new_event[i].milliseconds = fst[5]
                new_event[i].sampleCount = 0
                new_event[i].sampleRate = c.SampleRate
                new_event[i].trace = []
                new_event[i].gain = c.Gain[i]
                new_event[i].bitWeight = c.TrueBitWeight[i]
                new_event[i].channel_number = i
                new_event[i].stream_number = stream

            self.previous_event[stream] = self.current_event[stream]
            self.current_event[stream] = new_event

        # Logging
        self.LOGS.append(self.packet_tagline_string(p))
        s = "Event Header"
        self.LOGS.append(s)
        s = "  event = %d" % event
        self.LOGS.append(s)
        s = "  stream = %d" % (stream + 1)
        self.LOGS.append(s)
        s = "  format = %s" % c.DataFormat
        self.LOGS.append(s)
        s = "  stream name = %s" % c.StreamName
        self.LOGS.append(s)
        s = "  sample rate = %s" % c.SampleRate
        self.LOGS.append(s)
        s = "  trigger type = %s" % c.TriggerType
        self.LOGS.append(s)
        t = decode_sample_time(c.TriggerTime)
        s = "  trigger time = %04d %03d:%02d:%02d:%02d:%03d" % (
            t[0], t[1], t[2], t[3], t[4], t[5])
        self.LOGS.append(s)
        s = "  first sample = %04d %03d:%02d:%02d:%02d:%03d" % (
            fst[0], fst[1], fst[2], fst[3], fst[4], fst[5])
        self.LOGS.append(s)
        t = decode_sample_time(c.LastSampleTime)
        if t[0] is not None:
            s = "  last sample = %04d %03d:%02d:%02d:%02d:%03d" % (
                t[0], t[1], t[2], t[3], t[4], t[5])
            self.LOGS.append(s)

        s = "  bit weights = %s" % ' '.join(c.NominalBitWeight).strip()
        self.LOGS.append(s)
        s = "  true weights = %s" % ' '.join(c.TrueBitWeight).strip()
        self.LOGS.append(s)
        self.LOGS.append(
            "DAS: %s EV: %04d DS: %d FST = %s TT = %s NS: %d SPS: %s"
            "ETO: 0" % (
                p.unit,
                event,
                stream + 1,
                colonize(
                    c.FirstSampleTime),
                colonize(
                    c.TriggerTime),
                self.points[
                    stream],
                c.SampleRate))

    def get_eh_info(self, c, p):
        '''   Case of the missing event header
              Get it from the DT packet
        '''
        ds = c.data_stream
        dc = c.channel
        das = p.unit
        ret = True
        k = "%s:%d:%d" % (das, dc + 1, ds + 1)
        # Set what we can from data packet
        try:
            new_event = self.current_event[ds]
            if new_event is None:
                raise
        except BaseException:
            new_event = build_empty_current_stream()

        new_event[dc].unitID = p.unit
        new_event[dc].event = int(c.event)
        new_event[dc].year = p.year
        new_event[dc].doy = p.doy
        new_event[dc].hour = p.hr
        new_event[dc].minute = p.mn
        new_event[dc].seconds = p.sc
        new_event[dc].milliseconds = p.ms
        new_event[dc].sampleCount = 0
        new_event[dc].channel_number = dc
        new_event[dc].stream_number = ds
        # Read sample rate from par file if possible
        if self.par and k in self.par:
            try:
                new_event[dc].sampleRate = int(self.par[k].samplerate)
            except ValueError:
                new_event[dc].sampleRate = float(self.par[k].samplerate)
        else:
            # XXX   Need to get sample rate from another source
            if ds == 9:
                new_event[dc].sampleRate = 0.1
            else:
                self.ERRS.append(
                    "Warning: No sample rate available. Setting it to 999.")
                if self.verbose:
                    LOGGER.warning(
                        "Warning: No sample rate available."
                        "Setting it to 999.")
                new_event[dc].sampleRate = 999
                ret = False

        # Read gain from par file if possible
        if self.par and k in self.par:
            try:
                new_event[dc].gain = self.par[k].gain
            except ValueError:
                new_event[dc].sampleRate = float(self.par[k].samplerate)
        else:
            # XXX   Need to get gain from another source
            if ds == 9:
                new_event[dc].gain = 'x1'
            else:
                self.ERRS.append(
                    "Warning: No gain available. Setting it to 2.")
                if self.verbose:
                    LOGGER.warning("No gain available. Setting it to 2.")
                new_event[dc].gain = 'x2'
                ret = False

        # Get bit-weight (nominal based on gain)
        try:
            new_event[dc].bitWeight = BIT_WEIGHT[new_event[dc].gain]
        except Exception:
            if ds == 9:
                new_event[dc].bitWeight = '637.0uV'
            else:
                self.ERRS.append(
                    "Warning: No bit weight available."
                    "Setting it to 1.0e-6.")
                if self.verbose:
                    LOGGER.warning(
                        "No bit weight available."
                        "Setting it to 1.0e-6.")
                new_event[dc].bitWeight = '1.0e-6 V'
                ret = False

        self.current_event[ds] = new_event

        return ret

    def end_event(self, stream, event, channel):
        self.previous_event[stream] = self.current_event[stream]
        for tchan in range(NUM_CHANNELS):
            # Set to current event so this only gets triggered
            # for the first DT packet with a missing EH and ET
            if self.current_event[stream][tchan].event is not None:
                self.current_event[stream][tchan].event = event
                self.current_event[stream][channel].trace = []
                self.current_event[stream][channel].sampleCount = 0

    def set_dt_info(self, c, p):
        '''   Set info from data packet and check for gaps/overlaps.   '''
        event = int(c.event)
        stream = c.data_stream
        channel = c.channel
        das = p.unit
        # End of event
        eoe = 0

        self.LOGS.append(self.packet_tagline_string(p))
        s = "ns = %s evt = %d ds = %d chan = %d data = %x" % (
            c.samples, event, stream + 1, c.channel + 1, c.data_format)
        self.LOGS.append(s)

        # This packet ends previous event?
        try:
            e = self.current_event[stream][channel].event
            if e is not None and event > e:
                eoe = END_OF_EVENT_DT
        except BaseException:
            pass

        # Check to see if we have a sample rate from the event header
        # If not we are missing the event header
        #
        try:
            sample_rate = self.current_event[stream][channel].sampleRate
            if sample_rate is None:
                raise

        except Exception as e:
            sample_rate = None
            self.ERRS.append(
                "Error: Data packet with no event header. %s Das: %s"
                "Channel: %d Stream: %d" % (
                    self.packet_time_string(p),
                    das,
                    channel + 1,
                    stream + 1))
            if self.verbose:
                LOGGER.error(
                    "Data packet with no event header. %s Das: %s"
                    "Channel: %d Stream: %d" % (
                        self.packet_time_string(p),
                        das,
                        channel + 1,
                        stream + 1))
            # Try to get sample rate etc..
            if not self.get_eh_info(c, p):
                self.ERRS.append(
                    "Warning: Could not determine sample rate, gain,"
                    "or bit weight")
                if self.verbose:
                    LOGGER.warning(
                        "Could not determine sample rate, gain, or bit weight")

            if sample_rate is None:
                sample_rate = self.current_event[stream][channel].sampleRate

        #
        # Keep info to check for gaps/overlaps
        #
        def set_this_pig(tc):
            # Start time etc. for this packet
            tc.start_time_asc = self.packet_time_string(p)
            tc.start_time_secs, tc.start_time_ms = self.packet_time_epoch(p)
            tc.samples += c.samples
            tc.sample_interval = 1.0 / float(sample_rate)
            # Seconds of data in this packet
            s = c.samples * tc.sample_interval
            ms, secs = math.modf(s)
            ms = int((ms + 0.0005) * 1000.)
            # Should be the start time of first sample in next packet
            tc.end_time_secs = int(secs) + tc.start_time_secs
            tc.end_time_ms = ms + tc.start_time_ms
            if tc.end_time_ms >= 1000:
                tc.end_time_ms -= 1000
                tc.end_time_secs += 1

        #
        # Check time gap/overlap
        #
        k = "%s:%d:%d" % (das, channel, stream)
        if k in self.last_packet_time:
            try:
                tpl = TimeCheck()
                set_this_pig(tpl)
            except timedoy.TimeError as e:
                self.ERRS.append(
                    "Failed to process packet: {0}".format(
                        e.message))
                if self.verbose:
                    LOGGER.warning(
                        "Failed to process packet: {0}".format(
                            e.message))
                return None

            delta_secs = tpl.start_time_secs - \
                self.last_packet_time[k].end_time_secs
            delta_secs += (tpl.start_time_ms -
                           self.last_packet_time[k].end_time_ms) / 1000.

            if delta_secs > 0:
                # Gap
                if self.verbose:
                    LOGGER.info(
                        "%s Chan: %d Strm: %d Time gap: %s of %7.3f secs\n" %
                        (das, channel + 1, stream + 1, tpl.start_time_asc,
                         delta_secs))
                self.ERRS.append(
                    "%s Chan: %d Strm: %d Time gap: %s of %7.3f secs" %
                    (das, channel + 1, stream + 1, tpl.start_time_asc,
                     delta_secs))
                eoe = END_OF_EVENT_GAP
            elif delta_secs < 0:
                # Overlap
                if self.verbose:
                    LOGGER.info(
                        "%s Chan: %d Strm: %d Time overlap: %s of"
                        "%7.3f secs\n" %
                        (das, channel + 1, stream + 1, tpl.start_time_asc,
                         delta_secs))
                self.ERRS.append(
                    "%s Chan: %d Strm: %d Time overlap: %s of %7.3f secs" %
                    (das, channel + 1, stream + 1, tpl.start_time_asc,
                     delta_secs))
                eoe = END_OF_EVENT_OVERLAP
            self.last_packet_time[k] = tpl
        else:
            # First packet in event
            try:
                self.last_packet_time[k] = TimeCheck()
                set_this_pig(self.last_packet_time[k])
            except timedoy.TimeError as e:
                self.ERRS.append(
                    "Failed to process packet: {0}".format(
                        e.message))
                if self.verbose:
                    LOGGER.warning(
                        "Failed to process packet: {0}".format(
                            e.message))
                del (self.last_packet_time[k])
                return None

        # Keep data points
        trace = DataPacket(c, p)
        self.current_event[stream][channel].trace.append(trace)
        self.current_event[stream][channel].sampleCount += c.samples
        self.points[stream] += c.samples

        # Return end of event?
        return eoe

    def set_sc_info(self, c, p):
        self.LOGS.append(self.packet_tagline_string(p))
        s = "Station Channel Definition  %s   ST: %s" % (
            colonize(c.ImplementTime), p.unit)
        self.LOGS.append(s)
        s = " Experiment Number = %s" % c.ExperimentNumber
        self.LOGS.append(s)
        s = " Experiment Name = %s" % c.ExperimentName
        self.LOGS.append(s)
        s = "  Comments - %s" % c.ExperimentComment
        self.LOGS.append(s)
        s = " Station Number = %s" % c.StationNumber
        self.LOGS.append(s)
        s = " Station Name = %s" % c.StationName
        self.LOGS.append(s)
        s = "  Station Comments - %s" % c.StationComment
        self.LOGS.append(s)
        s = " DAS Model Number = %s" % c.DASModel
        self.LOGS.append(s)
        s = " DAS Serial Number = %s" % c.DASSerial
        self.LOGS.append(s)
        s = " Experiment Start Time = %s" % c.ExperimentStart
        self.LOGS.append(s)
        s = " Time Clock Type = %s" % c.TimeClockType
        self.LOGS.append(s)
        s = " Clock Serial Number = %s" % c.TimeClockSN
        self.LOGS.append(s)
        for i in range(5):
            n = i + 1
            pre = "c.ChanInfo%d." % n
            Channel = eval(pre + "Channel")
            if Channel != '  ':
                s = "  Channel Number = %s" % Channel
                self.LOGS.append(s)
                s = "     Name - %s" % eval(pre + "ChannelName")
                self.LOGS.append(s)
                s = "     Azimuth - %s" % eval(pre + "Azimuth")
                self.LOGS.append(s)
                s = "     Inclination - %s" % eval(pre + "Inclination")
                self.LOGS.append("     Location")
                self.LOGS.append(s)
                s = "     X - %s  Y - %s  Z - %s" % (eval(pre + "XCoordinate"),
                                                     eval(pre + "YCoordinate"),
                                                     eval(pre + "ZCoordinate"))
                self.LOGS.append(s)
                s = "     XY Units - %s  Z Units - %s" % (
                    eval(pre + "XYUnits"),
                    eval(pre + "ZUnits"))
                self.LOGS.append(s)
                s = "     Preamplifier Gain = %s" % eval(pre + "PreampGain")
                self.LOGS.append(s)
                s = "     Sensor Model - %s" % eval(pre + "SensorModel")
                self.LOGS.append(s)
                s = "     Sensor Serial Number - %s" % eval(
                    pre + "SensorSerial")
                self.LOGS.append(s)
                s = "     Volts per Bit = %s" % eval(
                    pre + "AdjustedNominalBitWeight")
                self.LOGS.append(s)
                s = "     Comments - %s" % eval(pre + "Comments")
                self.LOGS.append(s)

    def set_sh_info(self, c, p):
        self.SOH.append(self.packet_tagline_string(p))
        s = "State of Health  %s   ST: %s" % (
            self.packet_time_string(p)[2:], p.unit)
        self.SOH.append(s)
        lines = string.split(c.Information, '\r\n')
        for line in lines:
            try:
                if line[0] != ' ':
                    self.SOH.append(line)
            except IndexError:
                pass

    def set_ds_info(self, cs, p):
        self.LOGS.append(self.packet_tagline_string(p))
        # cs is a list organized by stream
        for c in cs:
            # td is a trigger container
            td = c.Trigger

            s = "Data Stream Definition %s ST: %s" % (
                colonize(c.ImplementTime), p.unit)
            self.LOGS.append(s)
            s = "  Data Stream %s %s %s" % (
                c.DataStream, c.DataStreamName, c.RecordingDestination)
            self.LOGS.append(s)
            s = "  Channels %s" % c.ChannelsIncluded
            self.LOGS.append(s)
            s = "  Sample rate %s samples per second" % c.SampleRate
            self.LOGS.append(s)
            s = "  Data Format %s" % c.DataFormat
            self.LOGS.append(s)
            s = "  Trigger Type %s" % c.TriggerType
            self.LOGS.append(s)
            if not td:
                continue
            for d in td.keys():
                if not skipRE.match(d):
                    s = "     Trigger %s %s" % (d, td[d])
                    self.LOGS.append(s)

    def set_ad_info(self, c, p):
        self.LOGS.append(self.packet_tagline_string(p))
        s = "Auxiliary Data Parameter %s ST: %s" % (c.ImplementTime, p.unit)
        self.LOGS.append(s)
        chans = c.Channels
        tmp = []
        for i in range(16):
            if chans[i] != ' ':
                tmp.append("%d," % (i + 1))

        s = "  Channels %s" % string.join(tmp)
        self.LOGS.append(s)
        s = "  Sample Period %s" % c.SamplePeriod
        self.LOGS.append(s)
        s = "  Data Format %s" % c.DataFormat
        self.LOGS.append(s)
        s = "  Record Length %s" % c.RecordLength
        self.LOGS.append(s)
        s = "  Recording Destination %s" % c.RecordingDestination
        self.LOGS.append(s)

    def set_cd_info(self, c, p):
        self.LOGS.append(self.packet_tagline_string(p))
        s = "Calibration Definition %s ST: %s" % (
            colonize(c.ImplementTime), p.unit)
        self.LOGS.append(s)
        if c._72ACalibration.StartTime[0] != ' ':
            s = "  72A Calibration Start Time %s" % c._72ACalibration.StartTime
            self.LOGS.append(s)
            s = "  72A Calibration Repeat Interval %s"\
                % c._72ACalibration.RepeatInterval
            self.LOGS.append(s)
            s = "  72A Calibration Intervals %s" % c._72ACalibration.Intervals
            self.LOGS.append(s)
            s = "  72A Calibration Length %s" % c._72ACalibration.Length
            self.LOGS.append(s)
            s = "  72A Calibration Step On/Off %s"\
                % c._72ACalibration.StepOnOff
            self.LOGS.append(s)
            s = "  72A Calibration Step Period %s"\
                % c._72ACalibration.StepPeriod
            self.LOGS.append(s)
            s = "  72A Calibration Step Size %s" % c._72ACalibration.StepSize
            self.LOGS.append(s)
            s = "  72A Calibration Step Amplitude %s"\
                % c._72Calibration.StepAmplitude
            self.LOGS.append(s)
            s = "  72A Calibration Step Output %s"\
                % c._72ACalibration.StepOutput
            self.LOGS.append(s)

        for i in range(4):
            pre = "c._130AutoCenter%d." % (i + 1)
            sensor = eval(pre + "Sensor")
            if sensor != ' ':
                s = "  130 Auto Center Sensor %s" % sensor
                self.LOGS.append(s)
                s = "  130 Auto Center Enable %s" % eval(pre + "Enable")
                self.LOGS.append(s)
                s = "  130 Auto Center Reading Interval %s" % eval(
                    pre + "ReadingInterval")
                self.LOGS.append(s)
                s = "  130 Auto Center Cycle Interval %s" % eval(
                    pre + "CycleInterval")
                self.LOGS.append(s)
                s = "  130 Auto Center Level %s" % eval(pre + "Level")
                self.LOGS.append(s)
                s = "  130 Auto Center Attempts %s" % eval(pre + "Attempts")
                self.LOGS.append(s)
                s = "  130 Auto Center Attempt Interval %s" % eval(
                    pre + "AttemptInterval")
                self.LOGS.append(s)

        for i in range(4):
            pre = "c._130Calibration%d." % (i + 1)
            sensor = eval(pre + "Sensor")
            if sensor != ' ':
                s = "  130 Calibration Sensor %s" % sensor
                self.LOGS.append(s)
                s = "  130 Calibration Enable %s" % eval(pre + "Enable")
                self.LOGS.append(s)
                s = "  130 Calibration Duration %s" % eval(pre + "Duration")
                self.LOGS.append(s)
                s = "  130 Calibration Amplitude %s" % eval(pre + "Amplitude")
                self.LOGS.append(s)
                s = "  130 Calibration Signal %s" % eval(pre + "Signal")
                self.LOGS.append(s)
                s = "  130 Calibration Step Interval %s" % eval(
                    pre + "StepInterval")
                self.LOGS.append(s)
                s = "  130 Calibration Step Width %s" % eval(pre + "StepWidth")
                self.LOGS.append(s)
                s = "  130 Calibration Sine Frequency %s" % eval(
                    pre + "SineFrequency")
                self.LOGS.append(s)

        for i in range(4):
            pre = "c._130CalibrationSequence%s." % (i + 1)
            sequence = eval(pre + "Sequence")
            if sequence != ' ':
                s = "  130 Calibration Sequence %s" % sequence
                self.LOGS.append(s)
                s = "  130 Calibration Sequence Enable %s" % eval(
                    pre + "Enable")
                self.LOGS.append(s)
                s = "  130 Calibration Sequence Start Time %s" % eval(
                    pre + "StartTime")
                self.LOGS.append(s)
                s = "  130 Calibration Sequence Interval %s" % eval(
                    pre + "Interval")
                self.LOGS.append(s)
                s = "  130 Calibration Sequence Count %s" % eval(pre + "Count")
                self.LOGS.append(s)
                s = "  130 Calibration Sequence Record Length %s" % eval(
                    pre + "RecordLength")
                self.LOGS.append(s)

    def set_fd_info(self, c, p):
        self.LOGS.append(self.packet_tagline_string(p))
        # XXX Mostly untested... XXX
        for f in c:
            s = "Filter Description %s ST: %s" % (f.ImplementTime, p.unit)
            self.LOGS.append(s)
            s = "     Filter Block Count %d" % f.FilterBlockCount
            self.LOGS.append(s)
            s = "     Filter ID %s" % f.FilterID
            self.LOGS.append(s)
            s = "     Filter Decimation %d" % f.FilterDecimation
            self.LOGS.append(s)
            s = "     Filter Scaler %d" % f.FilterScaler
            self.LOGS.append(s)
            s = "     Filter Coefficient Count %d" % f.FilterCoefficientCount
            self.LOGS.append(s)
            s = "     Filter Packet Coefficient Count %d"\
                % f.PacketCoefficientCount
            self.LOGS.append(s)
            s = "     Filter Coefficient Packet Count %d"\
                % f.CoefficientPacketCount
            self.LOGS.append(s)
            s = "     Filter Coefficient Format %d" % f.CoefficientFormat
            self.LOGS.append(s)
            s = "     Filter Coefficients:"
            self.LOGS.append(s)
            for coeff in f.Coefficients:
                s = "  %d" % coeff
                self.LOGS.append(s)

    def set_om_info(self, c, p):
        self.LOGS.append(self.packet_tagline_string(p))
        s = "Operating Mode Definition %s ST: %s" % (
            colonize(c.ImplementTime), p.unit)
        self.LOGS.append(s)
        s = "  Operating Mode 72A Power State %s" % c._72APowerState
        self.LOGS.append(s)
        s = "  Operating Mode Recording Mode %s" % c.RecordingMode
        self.LOGS.append(s)
        s = "  Operating Mode Auto Dump on ET %s" % c.AutoDumpOnET
        self.LOGS.append(s)
        s = "  Operating Mode Auto Dump Threshold %s" % c.AutoDumpThreshold
        self.LOGS.append(s)
        s = "  Operating Mode 72A Power Down Delay %s" % c._72APowerDownDelay
        self.LOGS.append(s)
        s = "  Operating Mode Disk Wrap %s" % c.DiskWrap
        self.LOGS.append(s)
        s = "  Operating Mode 72A Disk Power %s" % c._72ADiskPower
        self.LOGS.append(s)
        s = "  Operating Mode 72A Terminator Power %s" % c._72ATerminatorPower
        self.LOGS.append(s)
        s = "  Operating Mode 72A Wake Up Start Time %s"\
            % c._72AWakeUpStartTime
        self.LOGS.append(s)
        s = "  Operating Mode 72A Wake Up Duration %s" % c._72AWakeUpDuration
        self.LOGS.append(s)
        s = "  Operating Mode 72A Wake Up Repeat Interval %s"\
            % c._72AWakeUpRepeatInterval
        self.LOGS.append(s)
        s = "  Operating Mode 72A Number of Wake Up Intervals %s"\
            % c._72AWakeUpNumberOfIntervals
        self.LOGS.append(s)

    # Process a single packet
    def parse_packet(self, pbuf):
        end_of_event_bool = 0
        # Decode packet header
        try:
            ph = rt_130_h.PacketHeader()
            ret = ph.decode(pbuf)
            self.last_packet_header = ret
            self.entry_num += 1
            if self.verbose == 2:
                LOGGER.info(
                    "\t\tParsing: Type: %s Unit: %s Sequence: %d" %
                    (ret.type, ret.unit, ret.sequence))
        except rt_130_h.HeaderError as e:
            if self.verbose:
                LOGGER.info(
                    "Failed to parse packet header: Type: {0}"
                    "Unit: {1} Sequence: {2}\n{3}".format(
                        ret.type,
                        ret.unit,
                        ret.sequence,
                        e.message))

            return CORRUPT_PACKET

        # Data packet
        if ret.type == 'DT':
            self.DTcnt += 1
            try:
                dt = rt_130_h.DT()
                c = dt.decode(pbuf)
                packet_data_stream = c.data_stream
                packet_event_number = c.event
                packet_channel_number = c.channel
            except rt_130_h.CorruptPacketError as e:
                self.ERRS.append("Found corrupt packet. Discarding.")
                if self.verbose:
                    LOGGER.warning("Found corrupt packet. Discarding.")
                return CORRUPT_PACKET

            # Ignore channels
            if packet_channel_number > NUM_CHANNELS:
                self.ERRS.append(
                    "Warning: Ignoring packet for stream %d channel %d." %
                    (packet_data_stream, packet_channel_number))
                if self.verbose:
                    LOGGER.warning(
                        "Ignoring packet for stream %d channel %d."
                        % (packet_data_stream, packet_channel_number))
                return IGNORE_PACKET

            # If data is steim1 or steim2 then x0 is in 2nd to last
            # data sample
            # and xn is in the last data sample
            if c.data_format == 0xc0 or c.data_format == 0xc2:
                # x0 = c.data[-2]
                xn = c.data[-1]
                del c.data[-2:]

                if self.verbose and c.data:
                    if xn != c.data[-1]:
                        self.ERRS.append(
                            "Garbled data packet at:"
                            "%d:%03d:%02d:%02d:%02d %03dms contains %d"
                            "samples" % (
                                ret.year,
                                ret.doy,
                                ret.hr,
                                ret.mn,
                                ret.sc,
                                ret.ms,
                                c.samples))
                        LOGGER.info(
                            "Garbled data packet at:"
                            "%d:%03d:%02d:%02d:%02d %03dms contains %d"
                            "samples\n" % (
                                ret.year,
                                ret.doy,
                                ret.hr,
                                ret.mn,
                                ret.sc,
                                ret.ms,
                                c.samples))
            try:
                end_of_event_bool = self.set_dt_info(c, ret)
            except Exception as e:
                self.ERRS.append(
                    "Could not process packet, set_dt_info. {0}".format(
                        e.message))
                if self.verbose:
                    LOGGER.warning(
                        "Could not process packet, set_dt_info. {0}".format(
                            e.message))

                end_of_event_bool = None

            if end_of_event_bool is None:
                return CORRUPT_PACKET

            self.lastDT.header = ret
            self.lastDT.payload = c
        # Event header
        elif ret.type == 'EH':
            # Count this Event Header
            self.EHcnt += 1
            # Decode Packet payload into c
            try:
                eh = rt_130_h.EH()
                c = eh.decode(pbuf)
                packet_data_stream = c.DataStream
                packet_event_number = c.EventNumber
            except rt_130_h.CorruptPacketError as e:
                self.ERRS.append("{0}".format(e.message))
                if self.verbose:
                    LOGGER.error(e.message)

                return CORRUPT_PACKET
            try:
                packet_total_channels = int(c.TotalChannels)
            except BaseException:
                self.ERRS.append(
                    "Warning: No total number of channels for EH packet given."
                    "Setting to %d." %
                    NUM_CHANNELS)
                if self.verbose:
                    LOGGER.warning(
                        "No total number of channels for"
                        "EH packet given. Setting to %d." %
                        NUM_CHANNELS)
                packet_total_channels = NUM_CHANNELS

            # Keep last event header packet
            self.lastEH.header = ret
            self.lastEH.payload = c

            for chan in range(packet_total_channels):
                e = None
                try:
                    e = self.current_event[packet_data_stream][chan].event
                except Exception:
                    # print ex
                    continue

                if e is not None:
                    break

            if e is not None and packet_event_number > e:
                end_of_event_bool = END_OF_EVENT_EH

            # Set previous event, set current event
            self.set_eh_info(c, ret)
        # Event trailer
        elif ret.type == 'ET':
            self.ETcnt += 1
            try:
                et = rt_130_h.EH()
                c = et.decode(pbuf)
                # End of event
                end_of_event_bool = END_OF_EVENT_ET
                self.set_et_info(c, ret)
                self.lastET.header = ret
                self.lastET.payload = c
            except rt_130_h.CorruptPacketError as e:
                self.ERRS.append("{0}".format(e.message))
                if self.verbose:
                    LOGGER.error(e.message)

                return CORRUPT_PACKET
        # State of health
        elif ret.type == 'SH':
            self.SHcnt += 1
            try:
                sh = rt_130_h.SH()
                c = sh.parse(pbuf)
                self.set_sh_info(c, ret)
                self.lastSH.header = ret
                self.lastSH.payload = c
            except rt_130_h.CorruptPacketError as e:
                self.ERRS.append("{0}".format(e.message))
                if self.verbose:
                    LOGGER.error(e.message)

                return CORRUPT_PACKET
            # print SHcnt
        # Station channel
        elif ret.type == 'SC':
            self.SCcnt += 1
            try:
                sc = rt_130_h.SC()
                c = sc.parse(pbuf)
                self.set_sc_info(c, ret)
                self.lastSC.header = ret
                self.lastSC.payload = c
            except rt_130_h.CorruptPacketError as e:
                self.ERRS.append("{0}".format(e.message))
                if self.verbose:
                    LOGGER.error(e.message)

                return CORRUPT_PACKET
        # Auxiliary data
        elif ret.type == 'AD':
            self.ADcnt += 1
            try:
                ad = rt_130_h.AD()
                c = ad.parse(pbuf)
                self.set_ad_info(c, ret)
                self.lastAD.header = ret
                self.lastAD.payload = c
            except rt_130_h.CorruptPacketError as e:
                self.ERRS.append("{0}".format(e.message))
                if self.verbose:
                    LOGGER.error(e.message)

                return CORRUPT_PACKET
        # Calibration parameter
        elif ret.type == 'CD':
            self.CDcnt += 1
            try:
                cd = rt_130_h.CD()
                c = cd.parse(pbuf)
                self.set_cd_info(c, ret)
                self.lastCD.header = ret
                self.lastCD.payload = c
            except rt_130_h.CorruptPacketError as e:
                self.ERRS.append("{0}".format(e.message))
                if self.verbose:
                    LOGGER.error(e.message)

                return CORRUPT_PACKET
        # Data stream
        elif ret.type == 'DS':
            self.DScnt += 1
            try:
                ds = rt_130_h.DS()
                c = ds.decode(pbuf)
                self.set_ds_info(c, ret)
                self.lastDS.header = ret
                self.lastDS.payload = c
            except rt_130_h.CorruptPacketError as e:
                self.ERRS.append("{0}".format(e.message))
                if self.verbose:
                    LOGGER.error(e.message)

                return CORRUPT_PACKET
        # Filter description
        elif ret.type == 'FD':
            self.FDcnt += 1
            try:
                fd = rt_130_h.FD()
                c = fd.decode(pbuf)
                self.set_fd_info(c, ret)
                self.lastFD.header = ret
                self.lastFD.payload = c
            except rt_130_h.HeaderError as e:
                self.ERRS.append("{0}".format(e.message))
                if self.verbose:
                    LOGGER.error(e.message)

                return CORRUPT_PACKET
        # Operating mode
        elif ret.type == 'OM':
            try:
                self.OMcnt += 1
                om = rt_130_h.OM()
                c = om.parse(pbuf)
                self.set_om_info(c, ret)
                self.lastOM.header = ret
                self.lastOM.payload = c
            except rt_130_h.HeaderError as e:
                self.ERRS.append("{0}".format(e.message))
                if self.verbose:
                    LOGGER.error(e.message)

                return CORRUPT_PACKET
        else:
            self.ERRS.append(
                "Error: Unknown packet type at packet number %d! Skipping." %
                self.entry_num)
            if self.verbose:
                LOGGER.error(
                    "Unknown packet type at packet number %d!"
                    "Skipping." %
                    self.entry_num)
            end_of_event_bool = CORRUPT_PACKET

        return end_of_event_bool

    # These were using up memory...
    def get_soh(self):
        ret = self.SOH[self.SOHptr:]
        self.SOH = []
        self.SOHptr = len(self.SOH)
        return ret

    def get_logs(self):
        ret = self.LOGS[self.LOGptr:]
        self.LOGS = []
        self.LOGptr = len(self.LOGS)
        return ret

    def get_errs(self):
        ret = self.reader.ERRS
        self.reader.ERRS = []
        ret += self.ERRS[self.ERRSptr:]
        self.ERRS = []
        self.ERRSptr = len(self.ERRS)
        return ret

    def get_stream_event(self, s):
        events = {}
        '''   if s (stream number) is -1 we reached end of file
              possibly before writing all pending events   '''
        if s >= 0:
            events[s] = self.previous_event[s]
            self.previous_event[s] = None
        else:
            '''   Check for ungracious termination   '''
            for s in range(NUM_STREAMS):
                event = self.previous_event[s]
                if event is None:
                    continue
                events[s] = event
                self.previous_event[s] = None

        return events

    # Determine if we are at end of event
    def end_of_event(self):
        # Not an event header or event trailer
        type = self.last_packet_header.type
        if type != 'EH' and type != 'ET':
            # print type
            return False

        for i in range(NUM_STREAMS):
            if self.previous_event[i] is not None:
                return i + 1

        return False

    # Initialize this event
    def openEvent(self, stream):
        self.previous_event[stream] = None
        self.points[stream] = 0

    # Get a single packet from the reader
    def getPage(self):
        pbuf = self.reader.getPacket()
        return pbuf

    def getEvent(self):
        #
        # Work around events split across CF cards, ie. no event header
        #
        def do_et():
            # Search for Event Trailer if no Event Header is found
            pbuf = self.reader.getPacket()
            if not pbuf:
                return pbuf
            ph = rt_130_h.PacketHeader()
            tmp = ph.decode(pbuf)
            # We are not starting with a data packet
            if tmp.type != 'DT':
                if tmp.type == 'EH':
                    eh = rt_130_h.EH()
                    ttmp = eh.decode(pbuf)
                    # Ok, found an Event Header so no need to look for the
                    # Event Trailers
                    self.SEEN[ttmp.DataStream] = True
                elif tmp.type == 'ET':
                    et = rt_130_h.EH()
                    ttmp = et.decode(pbuf)
                    self.SEEN[ttmp.DataStream] = True

                return pbuf
            else:
                dt = rt_130_h.DT()
                ttmp = dt.decode(pbuf)
                if self.SEEN[ttmp.data_stream] is True:
                    return pbuf

                yr = tmp.year
                doy = tmp.doy
                hr = tmp.hr
                mn = tmp.mn
                sc = tmp.sc
                ms = tmp.ms
                tstr = "{0:04d}{1:03d}{2:02d}{3:02d}{4:02d}{5:03d}".format(
                    yr, doy, hr, mn, sc, ms)
                self.ERRS.append(
                    "Warning: DT packet forward of EH at {0}."
                    "Attempting to use ET.".format(
                        tstr))
                # Loop until we find an event trailer
                self.SEEN[ttmp.data_stream] = True
                ptr = -1 * PACKET_SIZE
                while tmp.type != 'ET':
                    # Keep track of how many packets we have found
                    ptr -= PACKET_SIZE
                    tpbuf = self.reader.getPacket()
                    if not tpbuf:
                        self.ERRS.append("Error: No ET found. Yikes!")
                        return tpbuf

                    ph = rt_130_h.PacketHeader()
                    tmp = ph.decode(tpbuf)

                # Count this as an Event Header
                self.EHcnt += 1
                # Decode Packet payload into c
                eh = rt_130_h.EH()
                c = eh.decode(tpbuf)
                c.FirstSampleTime = tstr
                tmp.year = yr
                tmp.doy = doy
                tmp.hr = hr
                tmp.mn = mn
                tmp.sc = sc
                tmp.ms = ms
                packet_data_stream = c.DataStream
                try:
                    packet_total_channels = int(c.TotalChannels)
                except BaseException:
                    LOGGER.warning(
                        "No total number of channels for"
                        "EH packet given. Setting to %d." %
                        NUM_CHANNELS)
                    packet_total_channels = NUM_CHANNELS

                # Keep last event header packet
                self.lastEH.header = tmp
                self.lastEH.payload = c

                for chan in range(packet_total_channels):
                    e = None
                    try:
                        e = self.current_event[packet_data_stream][chan].event
                    except Exception:
                        # print ex
                        continue

                    if e is not None:
                        break

                # Set previous event, set current event
                self.set_eh_info(c, tmp)
                # Return the first buffer we read 'DT' and continue reading
                self.reader.rewind_subfile(ptr)
                pbuf = self.reader.getPacket()
                return pbuf

        for i in range(NUM_STREAMS):
            self.SEEN[i] = False
        while True:
            try:
                pbuf = do_et()
            except Exception as e:
                raise REFError(e)

            # End of file, close all streams
            if not pbuf:
                if not self.lastDT.header:
                    stream = None
                    num_points_stream = None
                else:
                    stream = self.lastDT.payload.data_stream
                    num_points_stream = sum(self.points)

                return stream, num_points_stream, True

            end_of_event = self.parse_packet(pbuf)
            # Check if its an end of event and which stream to close
            if end_of_event == 0:
                # Not end of event
                continue
            elif end_of_event == END_OF_EVENT_GAP:
                continue
            elif end_of_event == END_OF_EVENT_OVERLAP:
                continue
            elif end_of_event == END_OF_EVENT_DT:
                # We found a DT packet for a new event
                stream = self.lastDT.payload.data_stream
                event = self.lastDT.payload.event
                channel = self.lastDT.payload.channel
                self.end_event(stream, event, channel)
            elif end_of_event == END_OF_EVENT_EH:
                # We found a EH for a new event
                stream = self.lastEH.payload.DataStream
            elif end_of_event == END_OF_EVENT_ET:
                # Normal termination on ET
                stream = self.lastET.payload.DataStream
            elif end_of_event == CORRUPT_PACKET:
                # Ignore corrupt packets
                continue
            elif end_of_event == IGNORE_PACKET:
                continue

            num_points_stream = self.points[stream]
            self.points[stream] = 0
            return stream, num_points_stream, False


# Mixins

def build_empty_current_stream():
    ret = [None] * NUM_CHANNELS
    for i in range(NUM_CHANNELS):
        ret[i] = Event130()

    # ret = [Event130 ()] * NUM_CHANNELS

    return ret


def split_sample_time(stime):
    yr = stime[0:4]
    doy = stime[4:7]
    hr = stime[7:9]
    mn = stime[9:11]
    sc = stime[11:13]
    ms = stime[13:16]

    return (yr, doy, hr, mn, sc, ms)


def decode_sample_time(stime):
    if stime[0] == ' ':
        return 0, 0, 0, 0, 0, 0

    flds = split_sample_time(stime)

    try:
        yr = int(flds[0])
        doy = int(flds[1])
        hr = int(flds[2])
        mn = int(flds[3])
        sc = int(flds[4])
        ms = int(flds[5])
    except BaseException:
        yr = 0
        doy = 0
        hr = 0
        mn = 0
        sc = 0
        ms = 0

    return (yr, doy, hr, mn, sc, ms)


def colonize(time_string):
    flds = split_sample_time(time_string)

    return ':'.join(flds)


if __name__ == "__main__":

    import time

    def print_packets(pn):
        print "DT: %d EH: %d SH: %d SC: %d AD: %d CD: %d DS: %d FD: %d" \
              "OM: %d\n" % (
                  pn.DTcnt,
                  pn.EHcnt,
                  pn.SHcnt,
                  pn.SCcnt,
                  pn.ADcnt,
                  pn.CDcnt,
                  pn.DScnt,
                  pn.FDcnt,
                  pn.OMcnt)

        print "Total Packets: ", pn.DTcnt + pn.EHcnt + pn.SHcnt + pn.SCcnt +\
              pn.ADcnt + pn.CDcnt + pn.DScnt + pn.FDcnt +\
              pn.OMcnt

    def prof():
        zipfilename = "/media/300GB_EXT/rt2ms_low_samplerate_bug/RAW" \
                      "2009225.991C.ZIP"

        now = time.time()
        pn = PN130(zipfilename)

        while True:
            # Stream number, points
            s, p = pn.getEvent()
            # End of file
            if s < 0:
                break
            # Oops, corrupt packet
            if s > NUM_STREAMS:
                # Go to next file
                break

            # No data points in this event
            if not p:
                continue
            events = pn.get_stream_event(s)
            logs = pn.get_logs()
            soh = pn.get_soh()
            streams = events.keys()
            for s in streams:
                event = events[s]
                for c in range(NUM_CHANNELS):
                    if event is not None:
                        # This is a streams object
                        w = event
                        # This is a list of trace tuples => [[], [], [], ...]
                        t = w[c].trace
                        # This is the event number (None if the channel is not
                        # present)
                        e = w[c].event
                        # Skip unused channels since the event will be None
                        if e is None:
                            continue
                        else:
                            print "*** Stream: ", s, " Channel: ", c,\
                                "Event: ", e,

                        # t is a list of tuples for each DT packet
                        points = 0
                        first_time = ''
                        for n in t:
                            # n is a DataPacket
                            if first_time:
                                last_time = "%04d:%03d:%02d:%02d:%02d.%03d"\
                                            % (
                                                n.year,
                                                n.doy,
                                                n.hour,
                                                n.minute,
                                                n.seconds,
                                                n.milliseconds)
                            else:
                                first_time = "%04d:%03d:%02d:%02d:%02d.%03d"\
                                             % (
                                                 n.year,
                                                 n.doy,
                                                 n.hour,
                                                 n.minute,
                                                 n.seconds,
                                                 n.milliseconds)
                                last_time = first_time
                            points += len(n.trace)

                        print " %s -- %s Samples: %d" % (
                            first_time, last_time, points)

            # Print log
            for log in logs:
                print log
            # Print soh
            for s in soh:
                print s

        print "File: %s Seconds: %f" % (
            pn.reader.df.basefile, time.time() - now)
        print_packets(pn)
    prof()
