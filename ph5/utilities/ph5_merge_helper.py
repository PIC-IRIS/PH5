#!/usr/bin/env python
#
# A program to aid merging multiple families of ph5 files, ie if you
# have mulitple
# deployment sites in a single experiment.
#
# Steve Azevedo, February 2014
#

import re
import sys
import logging
import argparse
from subprocess import call

PROG_VERSION = '2019.14'
LOGGER = logging.getLogger(__name__)

miniPH5RE = re.compile(r".*miniPH5_(\d\d\d\d\d)\.ph5")

# Index of first miniPH5_xxxxx.ph5 file (value of xxxxx)
FIRST_MINI_INDEX = 0
# Dictionary, key = original miniPH5_xxxxx.ph5 file name,
#             value = new miniPH5_xxxxx.ph5 file name.
OLD_NEW = None


#
# Read Command line arguments
#


def get_args():
    '''   Get program args:
          -s new_miniPH5_xxxxx.ph5 index (ie value of xxxxx)
    '''
    global FIRST_MINI_INDEX

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)
    parser.usage = "ph5_merge_helper [-s miniPH5_start_index]"

    parser.description = ("Modify Index_t.kef and miniPH5_xxxxx.ph5 file "
                          "names so they can be merged.")

    parser.add_argument("-s", dest="mini_ph5_index",
                        help=("For the first miniPH5_xxxxx.ph5, xxxxx should "
                              "equal the given value."),
                        metavar="mini_ph5_index", action='store', type=int)

    parser.add_argument("-d", dest="debug", action="store_true", default=False)

    args = parser.parse_args()

    if args.mini_ph5_index:
        FIRST_MINI_INDEX = args.mini_ph5_index


def dump_Index_t():
    '''   Dump Index_t.kef from master.ph5   '''
    command = "ph5tokef -n master.ph5 -I 2>&1 > Index_t.kef"
    ret = call(command, shell=True)
    if ret < 0:
        LOGGER.error("Failed to read master.ph5, {0}".format(ret))
        sys.exit()


def dump_M_Index_t():
    '''   Dump M_Index_t.kef from master.ph5   '''
    command = "ph5tokef -n master.ph5 -M 2>&1 > M_Index_t.kef"
    ret = call(command, shell=True)
    if ret < 0:
        LOGGER.error("Failed to read master.ph5, {0}".format(ret))
        sys.exit()


def resequence_Index_t():
    '''   Set the value of external_file_name_s based on FIRST_MINI_INDEX in
          Index_t.kef   '''
    global OLD_NEW

    OLD_NEW = {}

    try:
        fh = open('Index_t.kef', 'rU')
        of = open('_Index_t.kef', 'w')
    except Exception as e:
        LOGGER.error(
            "Failed to open 'Index_t.kef', {0}\n".format(e))
        sys.exit()

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
            n = n + FIRST_MINI_INDEX - 1
            OLD_NEW[value] = "miniPH5_{0:05d}.ph5".format(n)
            of.write("\texternal_file_name_s=./{0}\n".format(OLD_NEW[value]))

    fh.close()
    of.close()
    command = "mv _Index_t.kef Index_t" + \
              str(FIRST_MINI_INDEX) + ".kef 2>&1 > /dev/null"
    ret = call(command, shell=True)
    if ret < 0:
        LOGGER.error("Index_t.kef may not be correct.")


def resequence_M_Index_t():
    '''   Set the value of external_file_name_s based on FIRST_MINI_INDEX in
          M_Index_t.kef   '''
    global OLD_NEW

    OLD_NEW = {}

    try:
        fh = open('M_Index_t.kef', 'rU')
        of = open('_M_Index_t.kef', 'w')
    except Exception as e:
        LOGGER.error(
            "Error: Failed to open 'Index_t.kef', {0}".format(e))
        sys.exit()

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
            n = n + FIRST_MINI_INDEX - 1
            OLD_NEW[value] = "miniPH5_{0:05d}.ph5".format(n)
            of.write("\texternal_file_name_s=./{0}\n".format(OLD_NEW[value]))

    fh.close()
    of.close()
    command = "mv _M_Index_t.kef M_Index_t" + \
              str(FIRST_MINI_INDEX) + ".kef 2>&1 > /dev/null"
    ret = call(command, shell=True)
    if ret < 0:
        LOGGER.error("Index_t.kef may not be correct.")


def rename_miniPH5():
    '''   Rename miniPH5_xxxxx.ph5 files based on new starting index.   '''
    olds = OLD_NEW.keys()
    for o in olds:
        command = "mv {0} {1} 2>&1 > /dev/null".format(o, OLD_NEW[o])
        print command
        ret = call(command, shell=True)
        if ret < 0:
            LOGGER.error("File rename may have failed.")


def main():
    get_args()
    dump_Index_t()
    resequence_Index_t()
    dump_M_Index_t()
    resequence_M_Index_t()
    rename_miniPH5()


if __name__ == '__main__':
    main()
