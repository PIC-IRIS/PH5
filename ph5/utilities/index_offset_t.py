#!/usr/bin/env pnpython2
#
# Index offset table in ph5 file to speed up in kernal searches
#
# Steve Azevedo, March 2012
#

import argparse
import sys
import logging
from ph5.core import experiment

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)

EX = None
PH5 = None
PATH = None


def get_args():
    global PH5, PATH, NAME

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)
    parser.usage = "index_offset_t --nickname ph5-file-prefix"

    parser.description = ("Index offset table in ph5 file to speed up in "
                          "kernal searches.\n\nVersion: {0}"
                          .format(PROG_VERSION))

    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)

    parser.add_argument("-p", "--path", dest="ph5_path",
                        help=("Path to ph5 files. Default to current "
                              "directory."),
                        metavar="ph5_path", default=".")

    parser.add_argument("-t", "--offset_table", dest="offset_table_name",
                        help=("The name of the offset table. Example: "
                              "Offset_t_001_003."),
                        metavar="offset_table_name", required=True)

    args = parser.parse_args()

    PH5 = args.ph5_file_prefix
    PATH = args.ph5_path
    NAME = args.offset_table_name


#
# Initialize ph5 file
#


def initialize_ph5(editmode=False):
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5
    try:
        EX = experiment.ExperimentGroup(PATH, PH5)
        EX.ph5open(editmode)
        EX.initgroup()
    except Exception:
        LOGGER.error("Cannot open PH5 file. Use -h argument for help.")
        sys.exit()


def info_print():
    global EX


#
# Print Rows_Keys
#


def table_print(t, a):
    global TABLE_KEY
    i = 0
    # Loop through table rows
    for r in a.rows:
        i += 1
        print "# Table row %d" % i
        # Print table name
        if TABLE_KEY in a.keys:
            print "{0}:Update:{1}".format(t, TABLE_KEY)
        else:
            print t
        # Loop through each row column and print
        for k in a.keys:
            print "\t", k, "=", r[k]


def main():
    get_args()

    initialize_ph5(True)

    # index on event_id_s and receiver_id_s
    EX.ph5_g_sorts.index_offset_table(name=NAME)

    EX.ph5close()


if __name__ == '__main__':
    main()
