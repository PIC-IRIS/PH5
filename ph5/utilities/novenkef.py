#!/usr/bin/env pnpython3
#
# Generate kef from csv
#
# Steve Azevedo, Feb 2015
#
# ***   Expects geographic coordinates   ***
#

import time
import re
import math
import logging
from ph5.core import timedoy

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)

KEF_COLS = {}
# /Experiment_g/Sorts_g/Array_t_xxx columns as of Feb 2015
KEF_COLS['receiver'] = ['id_s', 'location/X/value_d', 'location/X/units_s',
                        'location/Y/value_d', 'location/Y/units_s',
                        'location/Z/value_d', 'location/Z/units_s',
                        'location/coordinate_system_s',
                        'location/projection_s',
                        'location/ellipsoid_s', 'location/description_s',
                        'deploy_time/ascii_s', 'deploy_time/epoch_l',
                        'deploy_time/micro_seconds_i', 'deploy_time/type_s',
                        'pickup_time/ascii_s', 'pickup_time/epoch_l',
                        'pickup_time/micro_seconds_i', 'pickup_time/type_s',
                        'das/serial_number_s', 'das/model_s',
                        'das/manufacturer_s', 'das/notes_s',
                        'sensor/serial_number_s', 'sensor/model_s',
                        'sensor/manufacturer_s',
                        'sensor/notes_s', 'description_s', 'channel_number_i',
                        "seed_band_code_s", "seed_instrument_code_s",
                        "seed_orientation_code_s", "seed_location_code_s",
                        "seed_station_name_s", 'SEED_Channel', 'sample_rate_i',
                        'sample_rate_multiplier_i']
# /Experiment_g/Sorts_g/Event_t[_xxx] columns as of Feb 2015
KEF_COLS['event'] = ['id_s', 'location/X/value_d', 'location/X/units_s',
                     'location/Y/value_d', 'location/Y/units_s',
                     'location/Z/value_d',
                     'location/Z/units_s', 'location/coordinate_system_s',
                     'location/projection_s', 'location/ellipsoid_s',
                     'location/description_s', 'location/description_s',
                     'time/ascii_s', 'time/epoch_l', 'time/micro_seconds_i',
                     'time/type_s', 'size/value_d', 'size/units_s',
                     'depth/value_d', 'depth/units_s', 'description_s']

timeRE = re.compile(".*time/ascii_s")
locationRE = re.compile("(location/[XY]/).*")
elevationRE = re.compile("(location/Z/).*")
seed_channelRE = re.compile("SEED_Channel")


def get_header():
    header = "# Written by novenkef v{0} at {1}\n"\
        .format(PROG_VERSION,
                timedoy.epoch2passcal(
                    time.time()))
    return header


def get_times(key, value):
    '''
       Create time entries for Array_t_xxx or Event_t[_xxx]
    '''
    try:
        fepoch = timedoy.fdsn2epoch(value, fepoch=True)
    except timedoy.TimeError:
        try:
            fepoch = timedoy.passcal2epoch(value, fepoch=True)
        except timedoy.TimeError:
            # This SHOULD never happen
            pre = key.split('/')[0]
            LOGGER.error(
                "Bad time value for {0} {1}.".format(key, value))
            line = "\t{0}/ascii_s = {1}\n".format(pre, time.ctime(int(0)))
            line += "\t{0}/epoch_l = {1}\n".format(pre, int(0))
            line += "\t{0}/micro_seconds_i = {1}\n".format(pre,
                                                           int(0. * 1000000.))
            line += "\t{0}/type_s = {1}\n".format(pre, 'BOTH')
            return line

    f, i = math.modf(fepoch)
    pre = key.split('/')[0]
    line = "\t{0}/ascii_s = {1}\n".format(pre, time.ctime(int(i)))
    line += "\t{0}/epoch_l = {1}\n".format(pre, int(i))
    line += "\t{0}/micro_seconds_i = {1}\n".format(pre, int(f * 1000000.))
    line += "\t{0}/type_s = {1}\n".format(pre, 'BOTH')

    return line


PATH = {}
PATH['receiver'] = '/Experiment_g/Sorts_g/Array_t_{0:03d}'


def write_receiver(top, filename):
    '''
       Write /Experiment_g/Sorts_g/Array_t_xxx entries
    '''
    varrays = top.keys()
    varrays.sort()
    fh = open(filename, 'w+')
    fh.write(get_header())
    n = 0
    for varray in varrays:
        vids = top[varray].keys()
        vids.sort()
        for vid in vids:
            n += 1
            chans = top[varray][vid].keys()
            chans.sort()
            for chan in chans:
                rows = top[varray][vid][chan]
                for row in rows:
                    path = PATH['receiver'].format(int(row['Array']))
                    fh.write("#   {0}\n".format(n))
                    fh.write(path + '\n')
                    for k in row.keys():
                        if k in KEF_COLS['receiver']:
                            try:
                                if timeRE.match(k):
                                    fh.write(get_times(k, row[k]))
                                elif locationRE.match(k):
                                    mo = locationRE.match(k)
                                    pre = mo.groups()[0]
                                    fh.write("\t{0} = {1}\n".format(k, row[k]))
                                    fh.write(
                                        "\t{0}units_s = degrees\n".format(pre))
                                elif elevationRE.match(k):
                                    mo = elevationRE.match(k)
                                    pre = mo.groups()[0]
                                    fh.write("\t{0} = {1}\n".format(k, row[k]))
                                    fh.write("\t{0}units_s = m\n".format(pre))
                                # Check if seed channel and split into band,
                                # instrument, and orientation
                                elif seed_channelRE.match(k):
                                    fh.write("\t{0} = {1}\n".format(
                                        "seed_band_code_s", row[k][0]))
                                    fh.write("\t{0} = {1}\n".format(
                                        "seed_instrument_code_s", row[k][1]))
                                    fh.write("\t{0} = {1}\n".format(
                                        "seed_orientation_code_s", row[k][2]))
                                else:
                                    fh.write("\t{0} = {1}\n".format(k, row[k]))
                            except Exception as e:
                                LOGGER.error(
                                    "Error writing kef file: {0}.".format(
                                        e.message))

    fh.close()


PATH['event'] = '/Experiment_g/Sorts_g/Event_t_{0:03d}'


def write_event(top, filename):
    '''
       Write /Experiment_g/Sorts_g/Event_t[_xxx] entries
    '''
    varrays = top.keys()
    varrays.sort()
    fh = open(filename, 'w+')
    fh.write(get_header())
    n = 0
    for varray in varrays:
        vids = top[varray].keys()
        vids.sort()
        for vid in vids:
            rows = top[varray][vid]
            for row in rows:
                n += 1
                path = PATH['event'].format(varray)
                fh.write("#   {0}\n".format(n))
                fh.write(path + '\n')
                for k in row.keys():
                    if k in KEF_COLS['event']:
                        if timeRE.match(k):
                            fh.write(get_times(k, row[k]))
                        elif locationRE.match(k):
                            mo = locationRE.match(k)
                            pre = mo.groups()[0]
                            fh.write("\t{0} = {1}\n".format(k, row[k]))
                            fh.write("\t{0}units_s = degrees\n".format(pre))
                        elif elevationRE.match(k):
                            mo = elevationRE.match(k)
                            pre = mo.groups()[0]
                            fh.write("\t{0} = {1}\n".format(k, row[k]))
                            fh.write("\t{0}units_s = m\n".format(pre))
                        else:
                            fh.write("\t{0} = {1}\n".format(k, row[k]))

    fh.close()


def write_kef(top, filename):
    '''
       Entry point
    '''
    varrays = top.keys()
    vids = top[varrays[0]].keys()
    if isinstance(top[varrays[0]][vids[0]], dict):
        write_receiver(top, filename)
    elif isinstance(top[varrays[0]][vids[0]], list):
        write_event(top, filename)


if __name__ == '__main__':
    pass
