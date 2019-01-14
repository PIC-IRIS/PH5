#!/usr/bin/env pnpython3

import argparse
import os.path
import re
import string
import sys
import logging
import time
from ph5.core import experiment, kef, columns

PROG_VERSION = '2019.14'
LOGGER = logging.getLogger(__name__)

updateRE = re.compile(r"(/.*):Update:(.*)\s*")


def get_args():
    '''
       Parse input arguments
          -k   kef file
          -r   report file
          -n   nickname
          -p   path
    '''
    global FILE, KEF, PH5, PATH

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = ("report2ph5 --file report-file --nickname "
                    "experiment-nickname [--path path-to-kef-file]"
                    "[--kef kef-file]")
    parser.description = "Load a report (pdf) into a ph5 file."
    parser.add_argument("-n", "--nickname", dest="nickname",
                        help="Experiment nickname.", required=True)
    parser.add_argument("-p", "--path", dest="path", default=".",
                        help="Path to where ph5 files are stored. "
                             "Defaults to current working directory."
                        )
    parser.add_argument("-f", "--file", dest="report_file",
                        help="The file containing the report, "
                             "(pdf, doc, ps, etc.).", required=True)
    parser.add_argument("-k", "--kef", dest="kef_file", default=None,
                        help="Kef file describing row in Report_t "
                             "for the report. Not required.")
    args = parser.parse_args()

    FILE = args.report_file
    if not os.path.exists(FILE):
        LOGGER.error("{0} does not exist!".format(FILE))
        sys.exit(-1)

    KEF = args.kef_file
    if KEF is not None:
        if not os.path.exists(KEF):
            LOGGER.error("{0} does not exist!".format(KEF))
            sys.exit(-2)

    PH5 = args.nickname
    PATH = args.path


def initializeExperiment():
    global EX, PH5, PATH

    EX = experiment.ExperimentGroup(currentpath=PATH, nickname=PH5)
    EDIT = True
    EX.ph5open(EDIT)
    EX.initgroup()


def update():
    global EX, ARRAY_NAME, KEF
    # There is a bug in batch update that kills kv
    k = kef.Kef(KEF)
    k.open()
    k.read()
    k.rewind()
    ARRAY_NAME = None
    while True:
        p, kv = k.next()
        if not p:
            break
        if 'array_name_a' in kv:
            ARRAY_NAME = kv['array_name_a']
        else:
            LOGGER.error(
                "Kef file does not contain entry for array_name_a. "
                "Can not continue!")
            return False

        ref = EX.ph5_g_reports.ph5_t_report
        if p not in columns.TABLES:
            LOGGER.warning("No table reference for key: {0}. "
                           "Possibly ph5 file is not open or initialized?"
                           .format(p))

        key = []
        errs_keys, errs_required = columns.validate(ref, kv, key)
        for e in errs_keys + errs_required:
            LOGGER.error(e)

        key = None
        columns.populate(ref, kv, key)

    return True


def load_report():
    global ARRAY_NAME

    if not ARRAY_NAME:
        LOGGER.error("It appears that 'array_name_a' is not set in kef file.")
        sys.exit()

    fh = open(FILE)
    buf = fh.read()
    fh.close()

    EX.ph5_g_reports.newarray(ARRAY_NAME, buf)


def get_input(prompt, default=None):
    if default is None:
        default = ''

    while True:
        val = raw_input(prompt + " [" + default + "]: ")
        if val == '' and default != '':
            val = default
            break
        elif val != '':
            break

    return val


def get_kef_info():
    global EX, FILE, KEF

    base = os.path.basename(FILE)

    title, suffix = string.split(base, '.')
    suffix = string.upper(suffix)

    array = EX.ph5_g_reports.nextName()

    title = get_input("Report title", title)
    suffix = get_input("File suffix", suffix)
    array = get_input("Internal array name", array)

    description = get_input("File description")

    kef = array + ".kef"
    LOGGER.info("Writing: {0}".format(kef))
    fh = open(kef, 'w+')
    fh.write("#   %s   report2ph5 version: %s   ph5 version: %s\n" %
             (time.ctime(time.time()), PROG_VERSION, EX.version()))
    fh.write("/Experiment_g/Reports_g/Report_t\n")
    fh.write("\tarray_name_a = %s\n" % array)
    fh.write("\ttitle_s = %s\n" % title)
    fh.write("\tformat_s = %s\n" % suffix)
    fh.write("\tdescription_s = %s\n" % description)

    fh.close()

    KEF = kef


def main():
    global FILE, KEF, PATH, PH5, EX
    get_args()
    initializeExperiment()

    # If there is no kef file prompt for its contents.
    if KEF is None:
        get_kef_info()

    if not update():
        sys.exit(-1)

    load_report()
    # Close ph5
    EX.ph5close()


if __name__ == '__main__':
    main()
