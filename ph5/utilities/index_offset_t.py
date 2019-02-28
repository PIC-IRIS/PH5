#!/usr/bin/env pnpython2
#
# Index offset table in ph5 file to speed up in kernal searches
#
# Steve Azevedo, March 2012
#

import argparse
import logging
from ph5.core import experiment

PROG_VERSION = '2019.058'
LOGGER = logging.getLogger(__name__)


class Index_offset_t():
    def __init__(self):
        self.EX = None
        self.PH5 = None
        self.PATH = None

    def get_args(self):
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

        self.PH5 = args.ph5_file_prefix
        self.PATH = args.ph5_path
        self.NAME = args.offset_table_name

    #
    # Initialize ph5 file
    #

    def initialize_ph5(self, editmode=False):
        '''   Initialize the ph5 file   '''
        try:
            self.EX = experiment.ExperimentGroup(self.PATH, self.PH5)
            self.EX.ph5open(editmode)
            self.EX.initgroup()
        except Exception:
            raise Exception("Cannot open PH5 file. Use -h argument for help.")

    #
    # Print Rows_Keys
    #
    def table_print(self, t, a):
        i = 0
        # Loop through table rows
        for r in a.rows:
            i += 1
            print "# Table row %d" % i
            # Print table name
            if self.TABLE_KEY in a.keys:
                print "{0}:Update:{1}".format(t, self.TABLE_KEY)
            else:
                print t
            # Loop through each row column and print
            for k in a.keys:
                print "\t", k, "=", r[k]


def main():
    indexOffset = Index_offset_t()
    indexOffset.get_args()
    try:
        indexOffset.initialize_ph5(True)
    except Exception, err_msg:
        LOGGER.error(err_msg)

    # index on event_id_s and receiver_id_s
    indexOffset.EX.ph5_g_sorts.index_offset_table(name=indexOffset.NAME)

    indexOffset.EX.ph5close()


if __name__ == '__main__':
    main()
