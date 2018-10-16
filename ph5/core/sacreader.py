#!/usr/bin/env pnpython3

#
# Read a SAC file
#
# December 2013, Steve Azevedo
#

import sys
import logging
from ph5.core import sac_h
import numpy as np

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)


class SacError(Exception):
    """
    Raised if the SAC file is corrupt or if necessary information
    in the SAC file is missing.
    """


class SacIOError(Exception):
    """
    Raised if the given SAC file can't be read.
    """


class Reader (object):
    def __init__(self, infile=None):
        self.infile = infile
        self.FH = None
        self.endianness = sys.byteorder
        self.guess_endianness()

    def read_buf(self, size):
        def open_infile():
            try:
                self.FH = open(self.infile)
            except IOError:
                self.FH = None
                raise SacIOError(
                    "File does not exist: {0}".format(self.infile))

        buf = None
        if not self.FH:
            try:
                open_infile()
            except SacIOError:
                return buf

        try:
            buf = self.FH.read(size)
        except Exception as e:
            LOGGER.error(e)

        if not buf:
            self.FH.close()

        return buf

    def read_float_header(self):
        ret = {}

        keys = sac_h.SAC_float().__keys__

        for k in keys:
            what = "container.{0}".format(k)
            float_value = eval(what)

            ret[k] = float_value

        return ret

    def read_int_header(self):
        ret = {}

        keys = sac_h.SAC_int().__keys__

        for k in keys:
            what = "container.{0}".format(k)
            int_value = eval(what)

            ret[k] = int_value

        return ret

    def read_char_header(self):
        ret = {}

        keys = sac_h.SAC_char().__keys__

        for k in keys:
            what = "container.{0}".format(k)
            char_value = eval(what)

            ret[k] = char_value

        return ret

    def read_trace(self, n):
        buf = self.read_buf(n * 4)

        if self.endianness != sys.byteorder:
            ret = np.fromstring(buf, dtype=np.float32)
            ret = ret.byteswap()
        else:
            ret = np.fromstring(buf, dtype=np.float32)

        return ret

    def guess_endianness(self):
        self.read_buf(70 * 4)
        iret = self.read_int_header()
        self.FH.seek(0)
        version = iret['nvhdr']
        if version < 0 or version > 20:
            if self.endianness == 'little':
                self.endianness = 'big'
            elif self.endianness == 'big':
                self.endianness = 'little'


if __name__ == '__main__':
    sr = Reader(infile='./OBSPY/obspy-0.8.4/obspy/sac/tests/data/seism.sac')
    float_header = sr.read_float_header()
    int_header = sr.read_int_header()
    char_header = sr.read_char_header()
    trace = sr.read_trace(int_header['npts'])
    for t in trace:
        print t
