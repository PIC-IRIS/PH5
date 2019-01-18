#!/usr/bin/env pnpython2

import argparse
import os
import os.path
import sys
import logging
import time
import re
from ph5.core import timedoy

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)

os.environ['TZ'] = 'UTC'
time.tzset()

deployRE = re.compile("deploy_time.*")
pickupRE = re.compile("pickup_time.*")


class PH5_Time(object):
    __slots__ = 'epoch_l', 'ascii_s', 'micro_seconds_i', 'type_s'

    def __init__(self, passcal_s=None, epoch_l=None,
                 ascii_s=None, micro_seconds_i=None):
        if passcal_s is not None:
            self._passcal(passcal_s)
        elif epoch_l is not None:
            self._epoch(epoch_l)
        elif ascii_s is not None:
            self._ascii(ascii_s)

        if micro_seconds_i is not None:
            self.micro_seconds_i = micro_seconds_i
        else:
            self.micro_seconds_i = 0

    def _passcal(self, passcal_s):
        flds = passcal_s.split(':')
        for i in range(5):
            try:
                flds[i]
            except BaseException:
                flds.append(0)

        tdoy = timedoy.TimeDOY(year=int(flds[0]),
                               hour=int(flds[2]),
                               minute=int(flds[3]),
                               second=int(flds[4]),
                               microsecond=0,
                               doy=int(flds[1]))
        epoch_l = tdoy.epoch()
        self._epoch(epoch_l)

    # Read ascii time as produced by time.ctime XXX   Untested   XXX
    def _ascii(self, ascii_s):
        ttuple = time.strptime(ascii_s, "%a %b %d %H:%M:%S %Y")
        epoch_l = time.mktime(ttuple)
        self._epoch(epoch_l)

    def _epoch(self, epoch_l):
        self.epoch_l = epoch_l
        self.ascii_s = time.ctime(self.epoch_l)
        self.type_s = 'BOTH'


#
# Read Command line arguments
#


def get_args():
    global ARRAY_FILE, DEPLOY, PICKUP

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)
    parser.usage = (" set_deploy_pickup_times -a Array_t_xxx.kef "
                    "-d ASCII_deploy_time -p ASCII_pickup_time")

    parser.description = "Version: %s: Set deploy and pickup times in an\
     Array_t_xxx.kef file." % PROG_VERSION

    parser.add_argument("-a", "--array-kef", dest="array_kef",
                        help="The Array_t_xxx.kef file to modify.",
                        metavar="array_kef", required=True)

    parser.add_argument("-d", "--deploy-time", dest="deploy_time",
                        help="Array deployment time: YYYY:JJJ:HH:MM:SS",
                        metavar="deploy_time", required=True)

    parser.add_argument("-p", "--pickup-time", dest="pickup_time",
                        help="Array pickup time: YYYY:JJJ:HH:MM:SS",
                        metavar="pickup_time", required=True)

    args = parser.parse_args()

    ARRAY_FILE = args.array_kef
    DEPLOY = args.deploy_time
    PICKUP = args.pickup_time


def barf(fh, of, dep_time, pu_time):
    of.write("#  %s v%s %s\n" %
             (sys.argv[0], PROG_VERSION, time.ctime(time.time())))
    while True:
        line = fh.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        if line[0] == '#':
            of.write(line + '\n')
            continue

        if line[0] == '/':
            of.write("%s:Update:id_s\n" % line)
            continue

        if deployRE.match(line):
            key, val = line.split('=')
            pre, post = key.split('/')
            post = post.strip()
            if post == 'epoch_l':
                of.write("\tdeploy_time/epoch_l = %d\n" % dep_time.epoch_l)
            elif post == 'micro_seconds_i':
                of.write("\tdeploy_time/micro_seconds_i = %d\n" %
                         dep_time.micro_seconds_i)
            elif post == 'type_s':
                of.write("\tdeploy_time/type_s = %s\n" % dep_time.type_s)
            elif post == 'ascii_s':
                of.write("\tdeploy_time/ascii_s = %s\n" % dep_time.ascii_s)
        elif pickupRE.match(line):
            key, val = line.split('=')
            pre, post = key.split('/')
            post = post.strip()
            if post == 'epoch_l':
                of.write("\tpickup_time/epoch_l = %d\n" % pu_time.epoch_l)
            elif post == 'micro_seconds_i':
                of.write("\tpickup_time/micro_seconds_i = %d\n" %
                         pu_time.micro_seconds_i)
            elif post == 'type_s':
                of.write("\tpickup_time/type_s = %s\n" % pu_time.type_s)
            elif post == 'ascii_s':
                of.write("\tpickup_time/ascii_s = %s\n" % pu_time.ascii_s)
        else:
            of.write("\t%s\n" % line)


def main():
    global ARRAY_FILE, DEPLOY, PICKUP

    get_args()

    if not os.path.exists(ARRAY_FILE):
        LOGGER.error("Can't open {0}!".format(ARRAY_FILE))
        sys.exit()
    else:
        fh = open(ARRAY_FILE)
        mdir = os.path.dirname(ARRAY_FILE)
        base = os.path.basename(ARRAY_FILE)
        base = '_' + base
        of = open(os.path.join(mdir, base), 'w+')
        LOGGER.info("Opened: {0}".join(os.path.join(mdir, base)))

    dep_time = PH5_Time(passcal_s=DEPLOY)

    pu_time = PH5_Time(passcal_s=PICKUP)

    barf(fh, of, dep_time, pu_time)

    of.close()
    fh.close()


if __name__ == '__main__':
    main()
