#!/usr/bin/env python
#
# A program to aid merging multiple families of ph5 files, ie if you
# have mulitple
# deployment sites in a single experiment.
#
# Steve Azevedo, February 2014
#

import re
import logging
import argparse
from subprocess import call

PROG_VERSION = '2019.064'
logging.basicConfig()
LOGGER = logging.getLogger(__name__)

miniPH5RE = re.compile(r".*miniPH5_(\d\d\d\d\d)\.ph5")

# Index of first miniPH5_xxxxx.ph5 file (value of xxxxx)
FIRST_MINI_INDEX = 0
# Dictionary, key = original miniPH5_xxxxx.ph5 file name,
#             value = new miniPH5_xxxxx.ph5 file name.
OLD_NEW = None


class PH5MergeHelp():
    #
    # Read Command line arguments
    #
    def get_args(self):
        '''   Get program args:
              -s new_miniPH5_xxxxx.ph5 index (ie value of xxxxx)
        '''

        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter)
        parser.usage = "ph5_merge_helper [-s miniPH5_start_index]"

        parser.description = ("Modify Index_t.kef and miniPH5_xxxxx.ph5 file "
                              "names so they can be merged.")

        parser.add_argument(
            "-s", dest="mini_ph5_index",
            help=("For the first miniPH5_xxxxx.ph5, xxxxx should "
                  "equal the given value."),
            metavar="mini_ph5_index", action='store', type=int)

        parser.add_argument(
            "-d", dest="debug", action="store_true", default=False)

        args = parser.parse_args()

        if args.mini_ph5_index:
            self.FIRST_MINI_INDEX = args.mini_ph5_index

    def dump_Index_t(self):
        '''   Dump Index_t.kef from master.ph5   '''
        command = "ph5tokef -n master.ph5 -I 2>&1 > Index_t.kef"
        ret = call(command, shell=True)
        if ret < 0:
            raise Exception("Failed to read master.ph5, {0}".format(ret))

    def dump_M_Index_t(self):
        '''   Dump M_Index_t.kef from master.ph5   '''
        command = "ph5tokef -n master.ph5 -M 2>&1 > M_Index_t.kef"
        ret = call(command, shell=True)
        if ret < 0:
            raise Exception("Failed to read master.ph5, {0}".format(ret))

    def resequence_Index_t(self):
        '''   Set the value of external_file_name_s based on FIRST_MINI_INDEX in
              Index_t.kef   '''

        self.OLD_NEW = {}

        try:
            fh = open('Index_t.kef', 'rU')
            of = open('_Index_t.kef', 'w')
        except Exception as e:
            raise Exception("Failed to open 'Index_t.kef', {0}\n".format(e))

        while True:
            line = fh.readline()
            if not line:
                break
            if line[0] != '\t':
                of.write(line)
                continue

            flds = line.split('=')
            key = flds[0].strip()
            if key != 'external_file_name_s':
                of.write(line)
                continue

            value = flds[1].strip()
            m = miniPH5RE.match(value)
            if m:
                n = int(m.groups()[0])
                n = n + self.FIRST_MINI_INDEX - 1
                OLD_NEW[value] = "miniPH5_{0:05d}.ph5".format(n)
                of.write(
                    "\texternal_file_name_s=./{0}\n".format(OLD_NEW[value]))

        fh.close()
        of.close()
        command = "mv _Index_t.kef Index_t" + \
                  str(self.FIRST_MINI_INDEX) + ".kef 2>&1 > /dev/null"
        ret = call(command, shell=True)
        if ret < 0:
            LOGGER.error("Index_t.kef may not be correct.")

    def resequence_M_Index_t(self):
        '''   Set the value of external_file_name_s based on FIRST_MINI_INDEX in
              M_Index_t.kef   '''

        self.OLD_NEW = {}

        try:
            fh = open('M_Index_t.kef', 'rU')
            of = open('_M_Index_t.kef', 'w')
        except Exception as e:
            raise Exception(
                "Error: Failed to open 'Index_t.kef', {0}".format(e))

        while True:
            line = fh.readline()
            if not line:
                break
            if line[0] != '\t':
                of.write(line)
                continue

            flds = line.split('=')
            key = flds[0].strip()
            if key != 'external_file_name_s':
                of.write(line)
                continue

            value = flds[1].strip()
            m = miniPH5RE.match(value)
            if m:
                n = int(m.groups()[0])
                n = n + self.FIRST_MINI_INDEX - 1
                self.OLD_NEW[value] = "miniPH5_{0:05d}.ph5".format(n)
                of.write("\texternal_file_name_s=./{0}\n".
                         format(self.OLD_NEW[value]))

        fh.close()
        of.close()
        command = "mv _M_Index_t.kef M_Index_t" + \
                  str(self.FIRST_MINI_INDEX) + ".kef 2>&1 > /dev/null"
        ret = call(command, shell=True)
        if ret < 0:
            LOGGER.error("Index_t.kef may not be correct.")

    def rename_miniPH5(self):
        '''   Rename miniPH5_xxxxx.ph5 files based on new starting index.   '''
        olds = self.OLD_NEW.keys()
        for o in olds:
            command = "mv {0} {1} 2>&1 > /dev/null".format(o, self.OLD_NEW[o])
            print command
            ret = call(command, shell=True)
            if ret < 0:
                LOGGER.error("File rename may have failed.")


def main():
    try:
        ph5_merge_help = PH5MergeHelp()
        ph5_merge_help.get_args()
        ph5_merge_help.dump_Index_t()
        ph5_merge_help.resequence_Index_t()
        ph5_merge_help.dump_M_Index_t()
        ph5_merge_help.resequence_M_Index_t()
    except Exception, err_msg:
        LOGGER.error(err_msg)
        return 1
    ph5_merge_help.rename_miniPH5()


if __name__ == '__main__':
    main()
