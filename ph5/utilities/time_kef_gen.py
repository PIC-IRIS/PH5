#!/usr/bin/env pnpython4
#
# Program to create time correction kef files for texan rt-125a's
# Read the SOH_a_[n] files under Receivers_g/Das_g_[n] and produce a kef file
# to populate Time_t
# Writes kef file to stdout
#
# Steve Azevedo, June 2017
#
import re
import sys
import time
import numpy as npy
import argparse
import logging
from ph5.core import ph5api, timedoy
from ph5.core.columns import PH5VERSION as ph5version

PROG_VERSION = '2019.063'
LOGGER = logging.getLogger(__name__)

# Match lines related to timing in SOH
timetoRE = re.compile(
    r".*TIME\s+CHANGED\s+TO\s+(\d{4}:\d{3}:\d{2}:\d{2}:\d{2}:\d{3})\s+"
    r"AND\s+(\d{4}/\d{4})\s+MS")
timefromRE = re.compile(
    r".*TIME\s+CHANGED\s+FROM\s+(\d{4}:\d{3}:\d{2}:\d{2}:\d{2}:\d{3})\s+"
    r"AND\s+(\d{4}/\d{4})\s+MS")


#
# Read Command line arguments
#

class TimeKefGen():

    def get_args(self):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter)

        parser.usage = "Version: {0}, time-kef-gen --nickname ph5-file-prefix\
         [-p path]".format(PROG_VERSION)

        parser.description = (
            "Generates kef file to populate Time_t from SOH_A_. \n\n"
            "Calculate clock drift from texan data previously\n"
            "loaded into a family of ph5 files and produce a\n"
            "kitchen exchange format (KEF) file containing\n"
            "clock correction information. The KEF file can\n"
            "then be loaded directly into the family of ph5\n"
            "files.")
        # -n master.ph5
        parser.add_argument(
            "-n", "--nickname", dest="ph5_file_prefix",
            help="The ph5 file prefix (experiment nickname).",
            metavar="ph5_file_prefix", required=True)
        # -p /path/to/ph5/family/files
        parser.add_argument(
            "-p", "--path", dest="ph5_path", metavar="ph5_path", default='.',
            help="Path to ph5 files Defaults current directory.",
                            )
        parser.add_argument(
            "-r", "--clock_report", action="store_true", default=False,
            help="Write clock performance log, time-kef-gen.log")
        parser.add_argument(
            "-k", "--keffile", dest="output_file",  metavar="output_file",
            help="The kef output file to be saved at.", default=None)

        self.ARGS = parser.parse_args()
        # define OFILE to write output
        o_filename = self.ARGS.output_file
        if o_filename is None:
            self.OFILE = None
        else:
            self.OFILE = open(o_filename, 'w')

    def read_soh(self, das_group):
        '''   Read SOH text from SOH_a_[n] into a list
        '''
        self.P5.ph5_g_receivers.setcurrent(das_group)
        soh = self.P5.ph5_g_receivers.read_soh()

        return soh

    def parse_soh(self, soh_buf):
        '''   Parse out TIME CHANGED TO and TIME CHANGED FROM messages
        '''

        def ms():
            '''
               Calculate seconds
            '''
            a, b = map(float, m.split('/'))
            return (a / b) / 1000.

        def str2tdoy():
            '''   Convert colon separated string to epoch   '''
            yr, jd, hr, mn, sc, ms = map(int, t.split(":"))
            us = int(ms) * 1000
            tdoy = timedoy.TimeDOY(year=int(yr),
                                   hour=int(hr),
                                   minute=int(mn),
                                   second=int(sc),
                                   microsecond=us,
                                   doy=(jd))

            return tdoy

        # tos, fos hold time changed to/from [epoch, seconds]
        tos = []
        fos = []
        for line in soh_buf:
            to = timetoRE.match(line)
            if to:
                t, m = to.groups()
                tos.append([str2tdoy(), ms()])
                continue
            fr = timefromRE.match(line)
            if fr:
                t, m = fr.groups()
                fos.append([str2tdoy(), ms()])

        return tos, fos

    def process_soh(self, soh):
        '''   Parse TO's and FROM's
        '''
        tos = []
        fos = []
        soh_array_names = soh.keys()
        for soh_array_name in soh_array_names:
            soh_buf = soh[soh_array_name]
            tos, fos = self.parse_soh(soh_buf)

        return tos, fos

    def parse_tos_froms(self, tos, fos):
        '''   Calculate and return start time, end time, clock drift slope,
              clock offset
              On any error return None, None, None, None
        '''
        try:
            # The first time set to
            start_tdoy = tos[0][0] + tos[0][1]
            end125_tdoy = fos[0][0] + fos[0][1]
            endgps_tdoy = tos[1][0] + tos[0][1]
            offset = end125_tdoy.epoch(fepoch=True) - endgps_tdoy.\
                epoch(fepoch=True)
            total_secs = endgps_tdoy.epoch(
                fepoch=True) - start_tdoy.epoch(fepoch=True)
            slope = offset / total_secs
        except IndexError:
            return None, None, None, None

        return start_tdoy, endgps_tdoy, slope, offset

    #
    # Print out report
    #
    def print_report(self, text):
        if self.OFILE is None:
            print(text)
        else:
            self.OFILE.write(text + '\n')

    def print_kef(self, das, clock):
        '''   Print Time_t info for this DAS
        '''
        if clock[0] is None:
            return
        tdoy_start = clock[0]
        tdoy_end = clock[1]
        self.print_report("/Experiment_g/Receivers_g/Time_t")
        self.print_report("\tdas/serial_number_s = %s" % das)
        self.print_report("\tstart_time/epoch_l = %d" % tdoy_start.epoch())
        self.print_report(
            "\tstart_time/micro_seconds_i = %d" % tdoy_start.microsecond())
        self.print_report(
            "\tstart_time/ascii_s = %s" % time.ctime(tdoy_start.epoch()))
        self.print_report("\tstart_time/type_s = BOTH")
        self.print_report("\tend_time/epoch_l = %d" % tdoy_end.epoch())
        self.print_report(
            "\tend_time/micro_seconds_i = %d" % tdoy_end.microsecond())
        self.print_report(
            "\tend_time/ascii_s = %s" % time.ctime(tdoy_end.epoch()))
        self.print_report("\tend_time/type_s = BOTH")
        self.print_report("\tslope_d = %g" % clock[2])
        self.print_report("\toffset_d = %g" % clock[3])

    def report(self, stats, no_cor):
        '''   Write clock performance for each DAS to a log file
        '''
        LOGGER.info("Writing time-kef-gen.log.")
        with open("time-kef-gen.log", 'w+') as fh:
            fh.write("{0}\n".format(sys.argv))
            for das in no_cor:
                fh.write("Failed to calculate clock drift. DAS: {0}\n".
                         format(das))
            sd = npy.average(stats[3])
            ave = npy.std(stats[3])
            fh.write("Average clock drift: {0:g} Std: {1:g}\n".format(ave, sd))
            for i in xrange(len(stats[0])):
                das = stats[0][i]
                start = stats[1][i]
                stop = stats[2][i]
                drift = stats[3][i]
                offset = stats[4][i]
                delta = ave - drift
                fh.write(
                    "DAS: {0} {4} to {5} Drift: {1:g} seconds/second Offset: {2:g}\
                     seconds Delta: {3:G}\n".format(
                        das,
                        drift,
                        offset,
                        delta,
                        start,
                        stop))


def main():

    TKefGen = TimeKefGen()

    TKefGen.get_args()
    try:
        TKefGen.P5 = ph5api.PH5(path=TKefGen.ARGS.ph5_path,
                                nickname=TKefGen.ARGS.ph5_file_prefix)
    except Exception:
        LOGGER.error("Can't open {0} at {1}.".format(
            TKefGen.ARGS.ph5_file_prefix, TKefGen.ARGS.ph5_path))
        return 1

    dasGroups = TKefGen.P5.ph5_g_receivers.alldas_g()
    dass = sorted(dasGroups.keys())
    # DAS, start time, end time, drift slope, offset
    stats = ([], [], [], [], [])
    no_cor = []
    print "#   Written by time-gef-gen v{0}, PH5 v{1}".format(
        PROG_VERSION, ph5version)
    for d in dass:
        das = d[6:]
        soh = TKefGen.read_soh(dasGroups[d])
        tos, fos = TKefGen.process_soh(soh)
        clock = TKefGen.parse_tos_froms(tos, fos)
        TKefGen.print_kef(das, clock)
        if clock[0] is None:
            no_cor.append(das)
            continue
        else:
            stats[0].append(das)
            stats[1].append(clock[0])
            stats[2].append(clock[1])
            stats[3].append(clock[2])
            stats[4].append(clock[3])

    if TKefGen.ARGS.clock_report:
        TKefGen.report(stats, no_cor)

    TKefGen.P5.close()


if __name__ == '__main__':
    main()
