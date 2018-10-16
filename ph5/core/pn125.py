#!/usr/bin/env pnpython2
#
# Process raw texan files up to CPU firmware version 1.0.26.
#
# Steve Azevedo, March 2004
# 125a Sept. 2006
#

import exceptions
import os
import struct
import sys
import logging
import rt_125a_py

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)

if sys.version_info >= (2, 3):
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning, append=1)

# Page size
TRDPAGE = 528
# Define block as xx pages (not sure why 11 is the optimal number???)
TRDBLOCK = TRDPAGE * 66


class TRDError (exceptions.Exception):
    pass


class ReadBuffer (object):
    '''   buf = string buffer
          ptr = next read position
          len = total len of buffer in bytes
    '''
    __slots__ = ('buf', 'ptr', 'len', 'set', 'get', 'clear', 'rewind', 'inc')

    def __init__(self):
        self.clear()

    def set(self, b):
        self.buf = b
        self.len = len(b)
        self.ptr = 0

    def get(self, n):
        p = self.ptr
        ll = self.len
        if (p + n) > ll:
            n = ll - p

        b = self.buf[p:n + p]
        self.inc(n)

        return b

    def clear(self):
        self.buf = None
        self.ptr = None
        self.len = None

    def rewind(self):
        self.ptr = 0

    def inc(self, n):
        self.ptr += n


class Page125 (object):
    __slots__ = ('pageType', 'model', 'unitID',
                 'sequence', 'first', 'last', 'ext')
    '''   Page stuff   '''

    def __init__(self):
        self.pageType = None
        self.model = "rt-125"
        self.unitID = None
        self.sequence = None
        self.first = None
        self.last = None
        self.ext = None


class Event125 (object):
    __slots__ = ('event', 'year', 'doy', 'hour', 'minute',
                 'seconds', 'sampleRate',
                 'sampleCount', 'channel_number',
                 'stream_number', 'trace', 'gain', 'fsd')
    '''   Event stuff   '''

    def __init__(self):
        self.event = None
        self.year = None
        self.doy = None
        self.hour = None
        self.minute = None
        self.seconds = None
        self.sampleRate = None
        self.sampleCount = None
        self.channel_number = 1
        self.stream_number = 1
        self.trace = []
        self.gain = None
        self.fsd = None


class SOH125 (object):
    __slots__ = ('year', 'doy', 'hour', 'minute', 'seconds', 'message')
    '''   SOH stuff   '''

    def __init__(self):
        self.year = None
        self.doy = None
        self.hour = None
        self.minute = None
        self.seconds = None
        self.message = ''


class Table125 (object):
    __slots__ = ('year', 'doy', 'hour', 'minute',
                 'seconds', 'action', 'parameter')
    '''   Event table   '''

    def __init__(self):
        self.year = None
        self.doy = None
        self.hour = None
        self.minute = None
        self.seconds = None
        self.action = None
        self.parameter = None


class pn125:
    def __init__(self, filename=None):
        # Input file name
        self.filename = filename
        # Open file handle
        self.pnfh = None
        # Page stuff
        self.page = Page125()
        # Event stuff
        self.trace = Event125()
        # State of Health Buffer
        self.sohbuf = []
        # Raw data buffer
        self.buf = ReadBuffer()
        # Count of pages left in buffer
        self.bufPages = 0
        # Event table buffer
        self.eventTable = []

    def openTRD(self):
        '''   Open raw data file   '''
        if self.filename is None:
            return

        self.pnfh = os.open(self.filename, os.O_RDONLY)

    def closeTRD(self):
        '''   Close raw data file   '''
        os.close(self.pnfh)

    def openEvent(self):
        '''   Open a new event   '''
        self.nullTrace()

    def closeEvent(self):
        self.trace.sampleCount = len(self.trace.trace)

    def readBlock(self):
        '''   Read a block of data   '''
        if self.pnfh is None:
            self.openTRD()
        # Attempt to read pages
        b = os.read(self.pnfh, TRDBLOCK)
        self.buf.set(b)
        # Number of pages in buffer
        self.bufPages = self.buf.len / TRDPAGE

    def nullPage(self):
        '''   Null values for page stuff   '''
        self.page.pageType = None
        self.page.unitID = None
        self.page.first = None
        self.page.last = None
        self.page.ext = None

    def nullTrace(self):
        '''   Null values for trace stuff   '''
        # print "Null"
        self.trace.event = None
        self.trace.year = None
        self.trace.doy = None
        self.trace.hour = None
        self.trace.minute = None
        self.trace.seconds = None
        self.trace.sampleRate = None
        self.trace.sampleCount = None
        self.trace.trace = []
        self.trace.gain = None
        self.trace.fsd = None

    def table(self, b):
        '''   Process event table info   '''
        # FIXME
        # Need new 125a files to test this on
        # sys.stderr.write ("Event table packet ignored...Untested code\n")
        # return
        # Number of entries in this page
        e = struct.unpack("!B", b[0])[0]

        # Number of entries per file
        b = b[7:]
        # Now process each line
        for i in range(e):
            nt = Table125()
            # s holds time, a holds action, p holds parameter
            s, a, p = struct.unpack("!6sBB", b[:8])
            b = b[8:]
            # Same format as SOH
            nt.year = 1984 + ord(s[0])
            nt.doy = ord(s[1]) * 100 + ord(s[2]) + 1
            nt.hour = ord(s[3])
            nt.minute = ord(s[4])
            nt.seconds = ord(s[5])
            # Limits on action code and parameter unclear so we just save as is
            nt.action = a
            nt.parameter = p
            self.eventTable.append(nt)

    def soh(self, b):
        '''   Read soh buffer   '''
        def element_ok(e):
            if e.year < 1984 or e.year > 2020:
                return False
            if e.doy < 1 or e.doy > 366:
                return False
            if e.hour < 0 or e.hour > 24:
                return False
            if e.minute < 0 or e.minute > 60:
                return False
            if e.seconds < 0 or e.seconds > 60:
                return False
            return True

        # Get byte count
        c = b[0:3]
        # Split off messages
        m = b[3:518]
        # Unpack counts
        p = struct.unpack("!HB", c)
        # Number of messages
        n = p[1]
        p = struct.unpack("!515s", m)[0]

        # Split on newlines
        s = p.split("\r\n")
        aflag = False
        for i in range(n):
            if aflag:
                aflag = False
                continue

            if len(s[i]) < 6:
                # This is short, maybe its a timestring that contained '\r\n'
                s[i] = s[i] + "\r\n" + s[i + 1]
                aflag = True

            element = SOH125()
            yr = 1984 + ord(s[i][0])

            jd = ord(s[i][1]) * 100 + ord(s[i][2]) + 1

            element.year = yr
            element.doy = jd
            element.hour = ord(s[i][3])
            element.minute = ord(s[i][4])
            element.seconds = ord(s[i][5])
            element.message = s[i][6:]
            if not element_ok(element):
                aflag = False
                continue

            self.sohbuf.append(element)

    def exth(self, b):
        '''   Translate extended header   '''
        p = struct.unpack("!BBBBBBHx", b)
        yr = p[0] + 1984
        jd = p[1] * 100 + p[2] + 1
        hr = p[3]
        mn = p[4]
        sc = p[5]
        sr = p[6]  # sample rate
        return yr, jd, hr, mn, sc, sr

    def evtc(self, b):
        '''   Translate gain/event/sample count   '''
        p = struct.unpack("!BHB", b)
        return p

    def extg(self, g):
        fsd = g >> 4
        gain = g & 0x0F
        fk = (0x500000, 0x600000)
        gk = (32, 1, 2, 4, 8, 16, 32, 64, 128, 256)
        return fk[fsd], gk[gain]

    def processEvent(self, b, n):
        d = rt_125a_py.data_decode(b, n)
        self.trace.trace.extend(d)

    def data(self, b):
        '''   Process data file   '''
        # Get gain event number and page sample count
        g, self.trace.event, n = self.evtc(b[0:4])
        b = b[4:]
        # First page or extended header flag
        if self.page.first or self.page.ext:
            # Read extended header
            # year, doy, hour, minute, seconds, samplerate
            if self.trace.year is None:
                p = self.exth(b[0:9])
                self.trace.year = p[0]
                self.trace.doy = p[1]
                self.trace.hour = p[2]
                self.trace.minute = p[3]
                self.trace.seconds = p[4]
                self.trace.sampleRate = p[5]
                self.trace.fsd, self.trace.gain = self.extg(g)

            b = b[9:]

        self.processEvent(b, n)

    def getPage(self):
        '''   Read and translate page   '''
        self.nullPage()
        if self.bufPages == 0:
            self.readBlock()
            if self.bufPages == 0:
                self.closeTRD()
                return
        # Fix these next 3 lines, they are slooooow....
        # Page header
        h = self.buf.get(6)
        # Page data
        b = self.buf.get(TRDPAGE - 6)
        # Remove this page from buffer
        # self.buf = self.buf[TRDPAGE:]
        # Number of pages remaining
        self.bufPages -= 1

        # Page type, Unit ID, Sequence, Flags
        p = struct.unpack("!BHHB", h)
        # Skip bad or erased pages
        if p[0] == 0xFF or p[0] == 0x00:
            self.page.pageType = -1
            return

        self.page.pageType = p[0]
        self.page.unitID = p[1] + 10000
        self.page.sequence = p[2]

        # Check and set page flags
        self.page.first = p[3] & 0x01
        self.page.last = (p[3] & 0x02) >> 1
        self.page.ext = (p[3] & 0x04) >> 2

        if self.page.last == 1:
            pass

        if 0:
            print self.page.pageType, self.page.unitID,
            self.page.sequence, p[3]

        if self.page.pageType == 1:
            self.soh(b[1:])
        elif self.page.pageType == 3:
            self.data(b)
        elif self.page.pageType == 5:
            self.table(b[1:])
        else:
            LOGGER.warning("Unrecognized page type: %d" % self.page.pageType)

    def getEvent(self):
        '''   Get next event   '''
        self.openEvent()
        while True:
            try:
                self.getPage()
            except Exception as e:
                raise TRDError(e)

            # Debug
            if self.page.pageType == 3:
                pass

            if self.page.pageType is None:
                # We are at end of file, return 0
                return 0
            elif self.page.pageType == -1:
                continue

            if self.page.last and self.page.pageType != 5:
                # End of this event, return sample count
                self.closeEvent()
                return self.trace.sampleCount


if __name__ == "__main__":
    import time

    now = time.time()

    for i in range(1):
        pn = pn125("./TRDS2/I3629RAWBR2.TRD")
        while True:
            points = pn.getEvent()
            if points == 0:
                break
            tr = pn.trace
            pg = pn.page
            bitweight = 10.0 / tr.gain / tr.fsd  # volts/bit
            print pg.unitID, tr.event, tr.year, tr.doy, tr.hour, tr.minute,
            tr.seconds,\
                tr.sampleRate, tr.sampleCount, tr.channel_number,
            tr.stream_number, tr.gain, bitweight

        print "SOH: "
        for el in pn.sohbuf:
            print el.year, el.doy, el.hour, el.minute, el.seconds, el.message
        else:
            print "END SOH"
        print "EVENT TABLE: "
        for el in pn.eventTable:
            print el.year, el.doy, el.hour, el.minute, el.seconds,
            el.action, el.parameter
        else:
            print "END EVENT TABLE"

    t = time.time() - now
    print t
