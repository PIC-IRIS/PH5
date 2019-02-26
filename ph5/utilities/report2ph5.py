#!/usr/bin/env pnpython3

import argparse
import os.path
import re
import logging
import time
from ph5.core import experiment, kef, columns

PROG_VERSION = '2019.057'
logging.basicConfig()
LOGGER = logging.getLogger(__name__)

updateRE = re.compile(r"(/.*):Update:(.*)\s*")


class Report2PH5():
    def get_args(self):
        '''
           Parse input arguments
              -k   kef file
              -r   report file
              -n   nickname
              -p   path
        '''

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

        self.FILE = args.report_file
        if not os.path.exists(self.FILE):
            raise Exception("{0} does not exist!".format(self.FILE))

        self.KEF = args.kef_file
        if self.KEF is not None:
            if not os.path.exists(self.KEF):
                raise Exception("{0} does not exist!".format(self.KEF))

        self.PH5 = args.nickname
        self.PATH = args.path

    def initialize_ph5(self):
        self.EX = experiment.ExperimentGroup(currentpath=self.PATH,
                                             nickname=self.PH5)
        EDIT = True
        self.EX.ph5open(EDIT)
        self.EX.initgroup()

    def update(self):
        # There is a bug in batch update that kills kv
        k = kef.Kef(self.KEF)
        k.open()
        k.read()
        k.rewind()
        self.ARRAY_NAME = None
        while True:
            p, kv = k.next()
            if not p:
                break
            if 'array_name_a' in kv:
                self.ARRAY_NAME = kv['array_name_a']
            else:
                LOGGER.error(
                    "Kef file does not contain entry for array_name_a. "
                    "Can not continue!")
                return False

            ref = self.EX.ph5_g_reports.ph5_t_report
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

    def load_report(self):

        if not self.ARRAY_NAME:
            raise Exception("It appears that 'array_name_a' is not set in "
                            "kef file.")

        fh = open(self.FILE)
        buf = fh.read()
        fh.close()

        self.EX.ph5_g_reports.newarray(self.ARRAY_NAME, buf)

    def get_input(self, prompt, default=None):
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

    def get_kef_info(self):
        base = os.path.basename(self.FILE)

        title, suffix = base.split('.')
        suffix = suffix.upper()

        array = self.EX.ph5_g_reports.nextName()

        title = self.get_input("Report title", title)
        suffix = self.get_input("File suffix", suffix)
        array = self.get_input("Internal array name", array)

        description = self.get_input("File description")

        kef = array + ".kef"
        LOGGER.info("Writing: {0}".format(kef))
        fh = open(kef, 'w+')
        fh.write("#   %s   report2ph5 version: %s   ph5 version: %s\n" %
                 (time.ctime(time.time()), PROG_VERSION, self.EX.version()))
        fh.write("/Experiment_g/Reports_g/Report_t\n")
        fh.write("\tarray_name_a = %s\n" % array)
        fh.write("\ttitle_s = %s\n" % title)
        fh.write("\tformat_s = %s\n" % suffix)
        fh.write("\tdescription_s = %s\n" % description)

        fh.close()

        self.KEF = kef


def main():
    try:
        R2T = Report2PH5()
        R2T.get_args()
        R2T.initialize_ph5()

        # If there is no kef file prompt for its contents.
        if R2T.KEF is None:
            R2T.get_kef_info()

        if not R2T.update():
            return 1

        R2T.load_report()
    except Exception, err_msg:
        LOGGER.error(err_msg)
        return 1
    # Close ph5
    R2T.EX.ph5close()


if __name__ == '__main__':
    main()
