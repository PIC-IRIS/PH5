#!/usr/bin/env pnpython3
#
# Find total size of ph5 files in a directory.
#
import argparse
import os
import logging
import re

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser(
            description='Find total size of ph5 files in a directory.',
            usage=('Version: {0} ph5_total -p="<ph5path>" '
                   '[options]'.format(PROG_VERSION))
            )
    parser.add_argument("-n", "--nickname", action="store",
                        type=str, default="master.ph5", metavar="nickname")
    parser.add_argument("-p", "--ph5path", action="store",
                        help=("Path to ph5 experiments directory."),
                        type=str, metavar="ph5path", default=".")
    args = parser.parse_args()
    return args


def main():
    args = get_args()

    masterRE = re.compile(args.nickname)
    try:
        files = os.listdir(args.ph5path)
    except OSError as e:
        LOGGER.error(e)
    else:
        F = {}
        B = {}
        M = {}
        total_bytes = 0
        biggest = 0
        smallest = 2 ** 64
        for f in files:
            if f[-4:] != '.ph5':
                continue
            else:
                filename = os.path.join(args.ph5path, f)
                sz = os.path.getsize(filename)
                total_bytes += sz
                if masterRE.match(f):
                    F[filename] = sz
                else:
                    if sz > biggest:
                        biggest = sz
                        B = {}
                        B[filename] = sz

                    if sz < smallest:
                        smallest = sz
                        M = {}
                        M[filename] = sz

        if not F:
            LOGGER.warning("No master file with nickname '{0}' found "
                           "under path '{1}'"
                           .format(args.nickname, args.ph5path))

        if total_bytes == 0:
            LOGGER.error("No ph5 files found.")
        else:
            print("Total: {0} GB\t"
                  .format(total_bytes / 1024. / 1024. / 1024.))
            if F:
                f = F.keys()[0]
                print("Master: {0}: {1} MB\t".format(f, F[f] / 1024. / 1024.))
            b = B.keys()[0]
            print("Largest: {0}: {1} MB\t".format(b, B[b] / 1024. / 1024.))
            m = M.keys()[0]
            print("Smallest: {0}: {1} MB".format(m, M[m] / 1024. / 1024.))


if __name__ == '__main__':
    main()
