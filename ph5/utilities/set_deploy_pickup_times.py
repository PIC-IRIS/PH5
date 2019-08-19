#!/usr/bin/env pnpython2

import argparse
import os
import os.path
import sys
import logging
import time
import re
import datetime
from ph5.core import timedoy, kefx, ph5api
from kef2ph5 import add_references
from math import floor, ceil


PROG_VERSION = '2019.197'
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


def get_args():
    global ARRAY_FILE, DEPLOY, PICKUP, AUTO_CORRECT, NICKNAME, PATH
    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)
    parser.usage = (" set_deploy_pickup_times -a Array_t_xxx.kef "
                    "-d ASCII_deploy_time -p ASCII_pickup_time")

    parser.description = "Version: %s: Set deploy and pickup times in an\
     Array_t_xxx.kef file." % PROG_VERSION

    parser.add_argument("-a", "--array-kef", dest="array_kef",
                        help="The Array_t_xxx.kef file to modify.",
                        metavar="array_kef", required=True)

    parser.add_argument("-n", "--nickname", default="master.ph5",
                        type=str, metavar="nickname", required=False,
                        help="Name of the PH5 file.", dest="nickname")

    parser.add_argument("-p", "--ph5path", action="store", default=".",
                        help=("Comma separated list of paths to ph5 "
                              "experiments."),
                        type=str, metavar="ph5path", required=False,
                        dest="path")

    parser.add_argument("-dt", "--deploy-time", dest="deploy_time",
                        help="Array deployment time: YYYY:JJJ:HH:MM:SS",
                        metavar="deploy_time", required=False)

    parser.add_argument("-pt", "--pickup-time", dest="pickup_time",
                        help="Array pickup time: YYYY:JJJ:HH:MM:SS",
                        metavar="pickup_time", required=False)

    parser.add_argument("-ac", "--auto-correct", dest="auto_correct",
                        help="Assigns the metadata deploy and pickup times"
                             "to time stamps calculated by the PH5 traces.",
                        metavar="auto_correct", required=False, default=False)

    args = parser.parse_args()
    NICKNAME = args.nickname
    PATH = args.path
    ARRAY_FILE = args.array_kef
    DEPLOY = args.deploy_time
    PICKUP = args.pickup_time
    AUTO_CORRECT = args.auto_correct


def barf(fh, of, dep_time, pu_time, das):
    inc = 0
    while True:
        line = fh.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        if line[0:5] == '#   T':
            of.write('\n')
            of.write(line + '\n')
            continue
        if line[0] == '#':
            of.write(line + '\n')
            continue
        if line[0] == '/':
            of.write("%s\n" % line)
            continue

        if deployRE.match(line):
            key, val = line.split('=')
            pre, post = key.split('/')
            post = post.strip()
            if post == 'epoch_l':
                if dep_time[inc] is None:
                    of.write("\tdeploy_time/epoch_l=\n")
                else:
                    of.write("\tdeploy_time/epoch_l=%d\n" %
                             dep_time[inc].epoch_l)
            elif post == 'micro_seconds_i':
                if dep_time[inc] is None:
                    of.write("\tdeploy_time/micro_seconds_i=\n")
                else:
                    of.write("\tdeploy_time/micro_seconds_i=%d\n" %
                             dep_time[inc].micro_seconds_i)
            elif post == 'type_s':
                if dep_time[inc] is None:
                    of.write("\tdeploy_time/type_s=\n")
                else:
                    of.write("\tdeploy_time/type_s=%s\n" %
                             dep_time[inc].type_s)
            elif post == 'ascii_s':
                if dep_time[inc] is None:
                    of.write("\tdeploy_time/ascii_s=\n")
                else:
                    of.write("\tdeploy_time/ascii_s=%s\n" %
                             dep_time[inc].ascii_s)
        elif pickupRE.match(line):
            key, val = line.split('=')
            pre, post = key.split('/')
            post = post.strip()
            if post == 'epoch_l':
                if pu_time[inc] is None:
                    of.write("\tpickup_time/epoch_l=\n")
                else:
                    of.write("\tpickup_time/epoch_l=%d\n" %
                             pu_time[inc].epoch_l)
            elif post == 'micro_seconds_i':
                if pu_time[inc] is None:
                    of.write("\tpickup_time/micro_seconds_i=\n")
                else:
                    of.write("\tpickup_time/micro_seconds_i=%d\n" %
                             pu_time[inc].micro_seconds_i)
            elif post == 'type_s':
                if pu_time[inc] is None:
                    of.write("\tpickup_time/type_s=\n")
                else:
                    of.write("\tpickup_time/type_s=%s\n" % pu_time[inc].type_s)
                inc = inc+1  # Increments the list of input units.
            elif post == 'ascii_s':
                if pu_time[inc] is None:
                    of.write("\tpickup_time/ascii_s=\n")
                else:
                    of.write("\tpickup_time/ascii_s=%s\n" %
                             pu_time[inc].ascii_s)
        else:
            of.write("\t%s\n" % line)


def kefTables(kef_file, NICKNAME, PATH):

    k = kefx.Kef(ARRAY_FILE)
    k.open()
    while True:
        n = k.read(10000)
        if n == 0:
            LOGGER.error("Kef file is empty")
            break
        # Get Das_g references
        ret = k.strip_receiver_g()
        if ret:
            add_references(ret)

            # Make sure Array_t_xxx, Event_t_xxx, and Offset_t_aaa_sss exist
            arrays, events, offsets = k.strip_a_e_o()


def main():
    global ARRAY_FILE, DEPLOY, PICKUP, AUTO_CORRECT, NICKNAME, PATH

    get_args()
    if not os.path.exists(ARRAY_FILE):
        LOGGER.error("Can't open {0}!".format(ARRAY_FILE))
        sys.exit()
    else:
        fh = open(ARRAY_FILE)
        mdir = os.path.dirname(ARRAY_FILE)
        base = os.path.basename(ARRAY_FILE)
        base = 'autocortime_{0}'.format(base)
        of = open(os.path.join(mdir, base), 'w+')
        # LOGGER.info("Opened: {0}".join(os.path.join(mdir, base)))
    if AUTO_CORRECT:
        dep_time = []
        pu_time = []
        ph5_api_object = ph5api.PH5(path=PATH, nickname=NICKNAME)
        ph5_api_object.read_array_t_names()
        if not ph5_api_object.Array_t_names:
            LOGGER.error("No arrays or no events defined in ph5 file."
                         "Can not continue!")
            ph5_api_object.close()
            sys.exit()
        LOGGER.info("Writing updated kef file: {0}".format(of.name))
        for array_name in ph5_api_object.Array_t_names:
            ph5_api_object.read_array_t(array_name)
            arraybyid = ph5_api_object.Array_t[array_name]['byid']
            arrayorder = ph5_api_object.Array_t[array_name]['order']
            for ph5_station in arrayorder:
                station_list = arraybyid.get(ph5_station)
                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        station = station_list[deployment][st_num]
                        das = station['das/serial_number_s']
                        true_deploy, true_pickup = \
                            ph5_api_object.get_extent(
                                das=station['das/serial_number_s'],
                                component=station['channel_number_i'],
                                sample_rate=station['sample_rate_i'])
                        if type(true_deploy) != float:
                            LOGGER.warning('No DAS Table Found for %s' % das)
                            dep_time.append(None)
                            pu_time.append(None)
                            continue
                        julian_tdeploy = (
                            datetime.datetime.fromtimestamp(floor(true_deploy))
                            .strftime('%Y:%j:%H:%M:%S'))
                        julian_tpickup = (
                            datetime.datetime.fromtimestamp(ceil(true_pickup))
                            .strftime('%Y:%j:%H:%M:%S'))
                        dep_time.append(PH5_Time(passcal_s=julian_tdeploy))
                        pu_time.append(PH5_Time(passcal_s=julian_tpickup))
        barf(fh, of, dep_time, pu_time, das)
    else:
        dep_time = PH5_Time(passcal_s=DEPLOY)
        pu_time = PH5_Time(passcal_s=PICKUP)
        barf(fh, of, dep_time, pu_time, das)
    of.close()
    fh.close()


if __name__ == '__main__':
    main()
