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

PROG_VERSION = '2019.036'
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


def get_args():
    global ARGS, OFILE

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = "Version: {0}, time-kef-gen --nickname ph5-file-prefix"\
        "[-p path]".format(PROG_VERSION)

    parser.description = ("Generates kef file to populate Time_t from SOH_A_. "
                          "\n\n"
                          "Calculate clock drift from texan data previously\n"
                          "loaded into a family of ph5 files and produce a\n"
                          "kitchen exchange format (KEF) file containing\n"
                          "clock correction information. The KEF file can\n"
                          "then be loaded directly into the family of ph5\n"
                          "files.")
    # -n master.ph5
    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)
    # -p /path/to/ph5/family/files
    parser.add_argument("-p", "--path", dest="ph5_path",
                        help="Path to ph5 files Defaults current directory.",
                        metavar="ph5_path", default='.')
    parser.add_argument("-r", "--clock_report", action="store_true",
                        default=False,
                        help="Write clock performance log, time-kef-gen.log")

    parser.add_argument("-o", "--outfile", dest="output_file",
                        help="The kef output file to be saved at.",
                        metavar="output_file", default=None)

    ARGS = parser.parse_args()
    # define OFILE to write output
    o_filename = ARGS.output_file
    if o_filename is None:
        OFILE = None
    else:
        OFILE = open(o_filename, 'w')


def read_soh(das_group):
    '''   Read SOH text from SOH_a_[n] into a list
    '''
    P5.ph5_g_receivers.setcurrent(das_group)
    soh = P5.ph5_g_receivers.read_soh()

    return soh


def parse_soh(soh_buf):
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


def process_soh(soh):
    '''   Parse TO's and FROM's
    '''
    to_froms = []
    soh_array_names = list(soh.keys())
    for soh_array_name in soh_array_names:
        soh_buf = soh[soh_array_name]
        to_froms.append(parse_soh(soh_buf))

    return to_froms


def parse_tos_froms(tos, fos):
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
def print_report(text):
    global OFILE
    if OFILE is None:
        print(text)
    else:
        OFILE.write(text + '\n')


def print_kef(das, clock):
    '''   Print Time_t info for this DAS
    '''
    if clock[0] is None:
        return
    tdoy_start = clock[0]
    tdoy_end = clock[1]
    print_report("/Experiment_g/Receivers_g/Time_t")
    print_report("\tdas/serial_number_s = %s" % das)
    print_report("\tstart_time/epoch_l = %d" % tdoy_start.epoch())
    print_report("\tstart_time/micro_seconds_i = %d"
                 % tdoy_start.microsecond())
    print_report("\tstart_time/ascii_s = %s" % time.ctime(tdoy_start.epoch()))
    print_report("\tstart_time/type_s = BOTH")
    print_report("\tend_time/epoch_l = %d" % tdoy_end.epoch())
    print_report("\tend_time/micro_seconds_i = %d" % tdoy_end.microsecond())
    print_report("\tend_time/ascii_s = %s" % time.ctime(tdoy_end.epoch()))
    print_report("\tend_time/type_s = BOTH")
    print_report("\tslope_d = %g" % clock[2])
    print_report("\toffset_d = %g" % clock[3])


def report(stats, no_cor):
    '''   Write clock performance for each DAS to a log file
    '''
    LOGGER.info("Writing time-kef-gen.log.")
    with open("time-kef-gen.log", 'w+') as fh:
        fh.write("{0}\n".format(sys.argv))
        for das in no_cor:
            fh.write("Failed to calculate clock drift. DAS: {0}\n".format(das))
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
    global P5, OFILE
    get_args()
    try:
        P5 = ph5api.PH5(path=ARGS.ph5_path, nickname=ARGS.ph5_file_prefix)
    except Exception:
        LOGGER.error("Can't open {0} at {1}.".format(ARGS.ph5_file_prefix,
                                                     ARGS.ph5_path))
        sys.exit(-1)

    dasGroups = P5.ph5_g_receivers.alldas_g()
    dass = sorted(dasGroups.keys())
    # DAS, start time, end time, drift slope, offset
    stats = ([], [], [], [], [])
    no_cor = []
    print_report("#   Written by time-gef-gen v{0}, PH5 v{1}".
                 format(PROG_VERSION, ph5version))
    for d in dass:
        das = d[6:]
        soh = read_soh(dasGroups[d])
        to_froms = process_soh(soh)
        count_cor = 0
        for tos, fos in to_froms:
            clock = parse_tos_froms(tos, fos)
            print_kef(das, clock)
            if clock[0] is not None:
                stats[0].append(das)
                stats[1].append(clock[0])
                stats[2].append(clock[1])
                stats[3].append(clock[2])
                stats[4].append(clock[3])
                count_cor += 1
        if count_cor == 0:
            no_cor.append(das)

    if ARGS.clock_report:
        report(stats, no_cor)

    P5.close()
    if OFILE is not None:
        OFILE.close()


if __name__ == '__main__':
    main()
