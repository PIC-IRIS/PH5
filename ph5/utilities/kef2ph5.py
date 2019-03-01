#!/usr/bin/env pnpython3
#
# Update a ph5 file from a kef file
#
# Steve Azevedo, January 2007
#

import argparse
import logging
import os
import os.path
import time
from ph5.core import experiment, kefx, columns

PROG_VERSION = '2019.060'
LOGGER = logging.getLogger(__name__)

# Force time zone to UTC
os.environ['TZ'] = 'UTC'
time.tzset()


class Kef2PH5:
    def get_args(self):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter)

        parser.usage = (
            "kef2ph5 --kef kef_file --nickname ph5_file_prefix [--path path]")

        parser.description = (
            "Update a ph5 file from a kef file.\n\nVersion: {0}"
            .format(PROG_VERSION))

        parser.add_argument(
            "-n", "--nickname", dest="outfile",
            help="The ph5 file prefix (experiment nickname).", required=True)
        parser.add_argument(
            "-k", "--kef", dest="keffile",
            help="Kitchen Exchange Format file.", required=True)
        parser.add_argument(
            "-p", "--path", dest="path",
            help="Path to directory where ph5 files are stored.", default=".")
        parser.add_argument(
            "-c", "--check", action="store_true", default=False, dest="check",
            help="Show what will be done but don't do it!")

        args = parser.parse_args()

        self.KEFFILE = args.keffile
        self.PH5 = args.outfile
        self.PATH = args.path
        self.TRACE = args.check

    def initialize_ph5(self):
        self.EX = experiment.ExperimentGroup(nickname=self.PH5,
                                             currentpath=self.PATH)
        EDIT = True
        self.EX.ph5open(EDIT)
        self.EX.initgroup()

    def add_references(self, rs):
        '''   Add a reference for each Das_t so we can look it up later   '''

        for r in rs:
            flds = r.split('/')
            das = flds[3].split('_')[2]
            g = self.EX.ph5_g_receivers.getdas_g(das)
            self.EX.ph5_g_receivers.setcurrent(g)
            # Set reference
            columns.add_reference(r, self.EX.ph5_g_receivers.current_t_das)

    def populateTables(self):
        LOGGER.info("Loading {0} into {1}.".format(self.KEFFILE, self.PH5))
        k = kefx.Kef(self.KEFFILE)
        k.open()

        while True:
            n = k.read(10000)
            if n == 0:
                err = "Empty kef file."
                break

            # Get Das_g references
            ret = k.strip_receiver_g()

            if ret:
                self.add_references(ret)

            # Make sure Array_t_xxx, Event_t_xxx, and Offset_t_aaa_sss exist
            arrays, events, offsets = k.strip_a_e_o()
            if arrays:
                for a in arrays:
                    a = a.split(':')[0]
                    self.EX.ph5_g_sorts.newArraySort(a)

            if events:
                for e in events:
                    e = e.split(':')[0]
                    self.EX.ph5_g_sorts.newEventSort(e)

            if offsets:
                for o in offsets:
                    o = o.split(':')[0]
                    self.EX.ph5_g_sorts.newOffsetSort(o)

            if self.TRACE is True:
                err = k.batch_update(trace=True)
            else:
                err = k.batch_update()

        k.close()
        if err is True:
            LOGGER.error("There were errors! See output.")

    def closePH5(self):
        self.EX.ph5close()

    def update_log(self):
        '''   Write a log of kef2ph5 activities.   '''
        # Don't log when run with the -c option
        if self.TRACE is True:
            return

        keffile = self.KEFFILE
        ph5file = os.path.join(self.PATH, self.PH5)
        klog = os.path.join(self.PATH, "kef2ph5.log")

        kef_mtime = time.ctime(os.stat(keffile).st_mtime)
        now = time.ctime(time.time())

        line = "%s*:*%s*:*%s*:*%s\n" % (now, ph5file, keffile, kef_mtime)
        if not os.path.exists(klog):
            line = "modification_time*:*experiment_nickname*:*\
            kef_filename*:*kef_file_mod_time\n" + \
                   "-------------------------------------------------------------\
                   -------------\n" + line

        try:
            LOGGER.info("Updated kef2ph5.log file.")
            fh = open(klog, 'a+')
            fh.write(line)
            fh.close()
        except BaseException:
            LOGGER.warning("Failed to write kef2ph5.log file.")


def main():
    K2T = Kef2PH5()
    K2T.get_args()
    K2T.initialize_ph5()
    K2T.populateTables()
    K2T.closePH5()
    K2T.update_log()


if __name__ == '__main__':
    main()
