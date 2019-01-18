#!/usr/bin/env pnpython3

#
# Translate and dump a binary SAC file to stdout
#
# December 2013, Steve Azevedo
#

import argparse
import logging
from ph5.core import sacreader

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)


def get_args():
    global INFILE, PRINT, ENDIAN

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = "Version: {0} Usage: dumpsac [options]".format(PROG_VERSION)

    parser.description = "Translate and dump a binary SAC file to stdout."

    parser.add_argument("-f", action="store", dest="infile", type=str,
                        required=True)

    parser.add_argument("-p", action="store_true",
                        dest="print_true", default=False)

    args = parser.parse_args()

    INFILE = args.infile
    PRINT = args.print_true


def print_it(header):
    try:
        keys = sorted(header.keys())
        for k in keys:
            print "{0:<12}\t{1:<12}".format(k, header[k])
    except AttributeError:
        for t in header:
            print t


def main():
    get_args()
    sr = sacreader.Reader(infile=INFILE)
    print "Endianness: {0}".format(sr.endianness)
    print "+------------+"
    print "|Float Header|"
    print "+------------+"
    print_it(sr.read_float_header())
    print "+--------------+"
    print "|Integer Header|"
    print "+--------------+"
    ret = sr.read_int_header()
    print_it(ret)
    print "+----------------+"
    print "|Character Header|"
    print "+----------------+"
    print_it(sr.read_char_header())
    if PRINT:
        print "+-----+"
        print "|Trace|"
        print "+-----+"
        print_it(sr.read_trace(ret['npts']))


if __name__ == '__main__':
    main()
