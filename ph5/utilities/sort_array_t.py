#!/usr/bin/env pnpython4
#
# Sort an Array_t_xxx.kef file by station ID, id_s.
#
# Steve Azevedo, Feb 2017
#

import argparse
import sys
import logging
from ph5.core import kefx

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)
    parser.usage = ("sort_array_t Array_t_unsorted.kef -f "
                    "Array_t_unsorted.kef")
    parser.description = ("Sort an Array_t_xxx.kef file by station ID, id_s. "
                          "v{0}".format(PROG_VERSION))
    parser.add_argument("-f", "--file", dest="infile", required=True,
                        help="KEF file containing unsorted stations.")
    parser.add_argument("-o", "--outfile", action="store",
                        help="Sorted KEF file create. Defaults to stdout.",
                        default=sys.stdout)
    args = parser.parse_args()
    return args


def main():
    args = get_args()

    kefin = args.infile

    try:
        kx = kefx.Kef(kefin)
        kx.open()
    except Exception as e:
        LOGGER.error("Error opening kef file {0} - {1}".format(kefin, e))
    else:
        kx.read()
        kx.rewind()
        kx.ksort('id_s')
        kx.rewind()
        if isinstance(args.outfile, (str, unicode)):
            args.outfile = open(args.outfile, "w")
        args.outfile.write(kx.to_str())


if __name__ == "__main__":
    main()
