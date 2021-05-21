#!/usr/bin/env pnpython3
#
#
# Steve Azevedo, December 2010
#
#

from __future__ import division
from __future__ import print_function

import argparse
import sys
import os
import re
import time
import logging
from math import radians, cos, tan, sqrt, pi
from ph5.core import timedoy


PROG_VERSION = __version__ = "2021.84"
LOGGER = logging.getLogger(__name__)
try:
    from PySide2 import QtWidgets, QtCore, Qt
except Exception:
    msg = ("\n\nNo module named PySide2. "
           "Please environment_gui.yml to install conda environment"
           "PySide2 is needed for novitiate.")
    raise ImportError(msg)

# Gives range of expected data logger serial numbers
MIN_DAS_SN = 10000
MAX_DAS_SN = 20000
# Expect face plate number in spreadsheet, ie. serial-number - 10,000
USE_FACE_PLATE_SN = True
# Maximum difference in deploy and pickup location. Also elevation.
LOC_TOL_METERS = 100.
# Write dep file
DEP = False


def get_args():
    global DEP

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = "novitiate [options]"

    parser.description = ("Interactive GUI to create a dep file from a csv "
                          "spread sheet.\n\nVersion: {0}".format(PROG_VERSION))

    parser.add_argument("-s", "--das_sn_range", dest="das_sn_range",
                        action='store',
                        help="The serial number range of DAS's on experiment. "
                             "--das_sn_range=10000-20000")

    parser.add_argument("-f", "--dont_use_face_plate_sn",
                        dest="use_face_plate_sn", action="store_false",
                        help="Do not assume face plate serial numbers, ie. "
                             "do not add 10000 to sn from csv file. "
                             "Default is to use face plate sn.",
                        default=True)

    parser.add_argument("-l", "--location_tolerance",
                        dest="location_tolerance",
                        action='store',
                        help="Flag distances exceed this value in location. "
                             "--location_tolerance=100.", type=float)

    parser.add_argument("--generate_kefs", dest="generate_kefs",
                        action='store_false',
                        help="Write kef files instead of dep files.",
                        default=True)

    args = parser.parse_args()

    if args.das_sn_range:
        MAX_DAS_SN, MIN_DAS_SN = args.das_sn_range.split('-')
        MAX_DAS_SN = int(MAX_DAS_SN)
        MIN_DAS_SN = int(MIN_DAS_SN)


def _sign(val, latlon):
    # Convert to N/S/W/E lat/lon to signed lat/lon
    ret = val
    try:
        nsew = str(val[0])
        nsew.upper()
        if nsew == 'N' or nsew == 'S' or nsew == 'E' or nsew == 'W':
            return ret

        if nsew == '+':
            val = val[1:]

        if latlon == 'lat':
            if nsew == '-':
                ret = 'S' + val[1:]
            else:
                ret = 'N' + val
        elif latlon == 'lon':
            if nsew == '-':
                ret = 'W' + val[1:]
            else:
                ret = 'E' + val

    except IndexError:
        pass

    return ret


def __sign(val, latlon):
    # Convert to signed lat/lon from N/S/E/W lat/lon
    ret = val
    try:
        nsew = str(val[0])
        nsew.upper()
        if nsew == '+' or nsew == '-' or nsew.isdigit():
            return ret

        if nsew == 'N' or nsew == 'E':
            val = val[1:]

        if latlon == 'lat':
            if nsew == 'S':
                ret = '-' + val[1:]
            else:
                ret = '+' + val
        elif latlon == 'lon':
            if nsew == 'W':
                ret = '-' + val[1:]
            else:
                ret = '+' + val

    except IndexError:
        pass
    return ret


timeRE = re.compile(".*Time.*")


def has_time(order):
    keys = order.keys()
    for k in keys:
        if timeRE.match(k):
            return True

    return False


def is_deploy(order, line):
    if 'DorP' in order:
        if line[order['DorP']].upper() == 'D':
            return True

    return False


#
# Write Event_t.kef
#


def get_event_row(vals):
    pass
    #
    # Get epoch and us
    if vals['X'] and vals['Y']:
        X = vals['X']
        Y = vals['Y']
        units = 'meters'
        coordinate_system = 'arbritrary'
        ellipsoid = 'unknown'
    else:
        X = vals['Lon']
        Y = vals['Lat']
        units = 'degrees'
        coordinate_system = 'geodetic'
        ellipsoid = 'WGS84'

    yr, doy, hr, mn, sc = vals['Time'].split(':')
    yr, doy, hr, mn = map(int, [yr, doy, hr, mn])
    tdoy = timedoy.TimeDOY(year=yr,
                           month=None,
                           day=None,
                           hour=hr,
                           minute=mn,
                           second=float(sc),
                           microsecond=0,
                           doy=doy,
                           epoch=None,
                           dtobject=None)

    epoch = tdoy.epoch()
    us = tdoy.dtobject.microsecond

    event_t = '/Experiment_g/Sorts_g/Event_t\n'
    # id_s, description_s
    event_t += "\tid_s = {0}\n\tdescription_s = {1}\n".format(
        vals['ID'], vals['Comment'])
    # time/ascii_s, time/epoch_l, time/micro_seconds_i, time/type_s
    event_t += "\ttime/ascii_s = {0}\n\ttime/epoch_l = " \
               "{1}\n\ttime/micro_seconds_i = {2}\n\ttime/type_s = {3}\n" \
        .format(time.ctime(epoch),
                int(epoch),
                us,
                'BOTH')
    # location/X/value_d, location/X/units_s, location/Y/value_d,
    # location/Y/units_s, location/Z/value_d, location/Z/units_s
    event_t += "\tlocation/X/value_d = {0}\n\tlocation/X/units_s =" \
               " {1}\n\tlocation/Y/value_d = {2}\n\tlocation/Y/units_s = " \
               "{3}\n\tlocation/Z/value_d = {4}\n\tlocation/Z/units_s = {5}\n"\
        .format(X,
                units,
                Y,
                units,
                vals['Elev'],
                'meters')
    # location/coordinate_system_s, location/projection_s,
    # location/ellipsoid_s, location/description_s
    event_t += "\tlocation/coordinate_system_s =" \
               "{0}\n\tlocation/projection_s = {1}\n\tlocation/ellipsoid_s =" \
               " {2}\n\tlocation/description_s = {3}\n"\
        .format(coordinate_system,
                'none',
                ellipsoid,
                vals['ID'])
    # size/value_d, size/units_s, depth/value_d, depth/units_s
    event_t += "\tsize/value_d = {0}\n\tsize/units_s = {1}" \
               "\n\tdepth/value_d = {2}\n\tdepth/units_s = {3}"\
        .format(vals['Size'],
                'lbs',
                vals['Depth'],
                'meters')
    return event_t


FIELD_KEYS = ('SHOT', 'RECV')
FIELDS = {}
SHOTQC = {}
FIELDS['SHOT'] = ['Shot-ID', 'Station', 'Line', 'Channel', 'Lat', 'Y', 'Lon',
                  'X', 'Elev',
                  'STimeY:J:H:M:S.s', 'STimeYear', 'STimeJd', 'STimeMo',
                  'STimeDa',
                  'STimeHr', 'STimeMn', 'STimeSc', 'STimeMs', 'PreSec',
                  'PostSec',
                  'SR', 'Depth', 'Size', 'RVel', 'Radius', 'Comment']


def build_shot(order, line, n):
    vals = {'ID': '', 'Station': '', 'Line': '999', 'Channel': '1', 'Lat': '',
            'Y': '',
            'Lon': '', 'X': '', 'Elev': '', 'Time': '', 'Pre': '', 'Post': '',
            'SR': '',
            'Depth': '', 'Size': '', 'RVel': '', 'Radius': '', 'Comment': ''}

    if 'Receiver-ID' in order:
        return None

    if 'Shot-ID' not in order:
        # XXX   Need a error dialog here   XXX
        LOGGER.error("Shot-ID needed to create dep file.\n")
        return None

    try:
        if 'STimeY:J:H:M:S.s' not in order:
            yr = int(line[order['STimeYear']])
            if 'STimeMo' in order:
                mo = int(line[order['STimeMo']])
                da = int(line[order['STimeDa']])
                tdoy = timedoy.TimeDOY(year=yr,
                                       month=mo,
                                       day=da,
                                       hour=0,
                                       minute=0,
                                       second=0,
                                       microsecond=0,
                                       doy=None,
                                       epoch=None,
                                       dtobject=None)
                doy = tdoy.doy()
            else:
                doy = int(line[order['STimeJd']])

            hr = int(line[order['STimeHr']])
            mn = int(line[order['STimeMn']])
            if 'STimeSc' in order:
                sc = float(line[order['STimeSc']])
            else:
                sc = 0.0

            if 'STimeMs' in order:
                sc += float(line[order['STimeMs']]) / 1000.

            STime = "{0:4d}:{1:03d}:{2:02d}:{3:02d}:{4:06.3f}".format(yr,
                                                                      doy,
                                                                      hr,
                                                                      mn,
                                                                      sc)
        else:
            STime = line[order['STimeY:J:H:M:S.s']]
    except Exception as e:
        LOGGER.error(
            "{1}:\n\tCan't convert time {0}\n".format(line, e))
        return

    keys = order.keys()
    for k in keys:
        try:
            if k == 'Shot-ID':
                try:
                    vals['ID'] = str(int(line[order[k]]))
                except BaseException:
                    vals['ID'] = line[order[k]]
            elif k == 'Station':
                try:
                    vals['Station'] = str(int(line[order[k]]))
                except BaseException:
                    vals['Station'] = line[order[k]]
            elif k == 'Line':
                vals['Line'] = line[order[k]]
            elif k == 'Channel':
                vals['Channel'] = line[order[k]]
            elif k == 'Lat':
                if DEP:
                    vals['Lat'] = _sign(line[order[k]], 'lat')
                else:
                    vals['Lat'] = __sign(line[order[k]], 'lat')
            elif k == 'Y':
                vals['Y'] = line[order[k]]
            elif k == 'Lon':
                if DEP:
                    vals['Lon'] = _sign(line[order[k]], 'lon')
                else:
                    vals['Lon'] = __sign(line[order[k]], 'lon')
            elif k == 'X':
                vals['X'] = line[order[k]]
            elif k == 'Elev':
                vals['Elev'] = line[order[k]]
            elif k == 'PreSec':
                vals['Pre'] = line[order[k]]
            elif k == 'PostSec':
                vals['Post'] = line[order[k]]
            elif k == 'SR':
                vals['SR'] = line[order[k]]
            elif k == 'Depth':
                vals['Depth'] = line[order[k]]
            elif k == 'Size':
                vals['Size'] = line[order[k]]
            elif k == 'RVel':
                vals['RVel'] = line[order[k]]
            elif k == 'Radius':
                vals['Radius'] = line[order[k]]
            elif k == 'Comment':
                vals['Comment'] = line[order[k]]
        except IndexError:
            pass

    vals['Time'] = STime
    tmpkey = vals['Station']
    i = 0
    while tmpkey in SHOTQC:
        tmpkey = tmpkey.split(':')[0] + ":{0}".format(i)
        i += 1

    SHOTQC[tmpkey] = [vals['ID'], vals['Station'], vals['Line'], vals['Lat'],
                      vals['Lon'],
                      vals['Elev'], vals['Time'], vals['Pre'], vals['Post'],
                      vals['SR'],
                      vals['Depth'], vals['Size'], vals['RVel'],
                      vals['Radius'], vals['Comment']]

    if DEP:
        return "SHOT;{0};{1};{2};{3};{4};{5};{6};{7};{8};{9};{10};{11};{12};" \
               "{13};{14}"\
            .format(vals['ID'],
                    vals['Station'],
                    vals['Line'],
                    vals['Lat'],
                    vals['Lon'],
                    vals['Elev'],
                    vals['Time'],
                    vals['Pre'],
                    vals['Post'],
                    vals['SR'],
                    vals['Depth'],
                    vals['Size'],
                    vals['RVel'],
                    vals['Radius'],
                    vals['Comment'])
    else:
        return get_event_row(vals)


def churn_recv(recvqc, recvkey):

    ret = []

    def stripdeppu(vals):
        '''   Return vals_dep, vals_pu
        '''
        msg = ''
        if len(vals) == 2:
            if vals[0]['DTime'] and vals[1]['PUTime']:
                return vals[0], vals[1], msg
            elif vals[0]['PUTime'] and vals[1]['DTime']:
                return vals[1], vals[0], msg
        else:
            dt = {}
            pt = {}
            for v in vals:
                if v['DTime']:
                    dt[v['DTime']] = v
                if v['PUTime']:
                    pt[v['PUTime']] = v

            if not pt:
                msg = 'No pickup record'
                pt = dt
            elif not dt:
                msg = 'No deployment record'
                dt = pt

            keys_dt = dt.keys()
            keys_pt = pt.keys()

            keys_dt.sort()
            keys_pt.sort()
            keys_pt.reverse()

            return dt[keys_dt[0]], pt[keys_pt[0]], msg

    def get_recv_row(vals):
        # Build an Array_t_xxx kef file
        global RECVSTN
        vals_dep, vals_pu, msg = stripdeppu(vals)
        if vals_dep['X'] and vals_dep['Y']:
            X = vals_dep['X']
            Y = vals_dep['Y']
            units = 'meters'
            coordinate_system = 'arbritrary'
            ellipsoid = 'unknown'
        else:
            X = vals_dep['Lon']
            Y = vals_dep['Lat']
            units = 'degrees'
            coordinate_system = 'geodetic'
            ellipsoid = 'WGS84'

        # Get deploy time epoch and us
        dyr, ddoy, dhr, dmn, dsc = vals_dep['DTime'].split(':')
        dyr, ddoy, dhr, dmn = map(int, [dyr, ddoy, dhr, dmn])
        dtdoy = timedoy.TimeDOY(year=dyr,
                                month=None,
                                day=None,
                                hour=dhr,
                                minute=dmn,
                                second=float(dsc),
                                microsecond=0,
                                doy=ddoy,
                                epoch=None,
                                dtobject=None)
        depoch = dtdoy.epoch()
        dus = dtdoy.millisecond()
        # Get pickup time epoch and us
        pyr, pdoy, phr, pmn, psc = vals_pu['PUTime'].split(':')
        pyr, pdoy, phr, pmn = map(int, [pyr, pdoy, phr, pmn])
        ptdoy = timedoy.TimeDOY(year=pyr,
                                month=None,
                                day=None,
                                hour=phr,
                                minute=pmn,
                                second=float(psc),
                                microsecond=0,
                                doy=pdoy,
                                epoch=None,
                                dtobject=None)
        pepoch = ptdoy.epoch()
        pus = ptdoy.millisecond()
        arrayID = int(vals_dep['Line'])
        stationID = int(vals_dep['Station'])
        chan = int(vals_dep['Channel'])
        comment = vals_dep['Comment'] + " " + vals_pu['Comment']

        array_t = '/Experiment_g/Sorts_g/Array_t_{0:03d}\n'.format(arrayID)
        array_t += '\tid_s = {0}\n\tdescription_s = {1}\n'.format(
            vals_dep['Station'],
            comment)
        # DAS information
        array_t += '\tdas/serial_number_s = {0}\n\tdas/model_s = {1}' \
                   '\n\tdas/manufacturer_s = {2}\n\tdas/notes_s = {3}\n' \
            .format(vals_dep['ID'],
                    vals_dep['Type'],
                    'RefTek',
                    vals_dep['LED'])

        # Deployment time
        array_t += '\tdeploy_time/ascii_s = {0}\n\tdeploy_time/epoch_l = {1}' \
                   '\n\tdeploy_time/micro_seconds_i = {2}' \
                   '\n\tdeploy_time/type_s = {3}\n'\
            .format(time.ctime(int(depoch)),
                    int(depoch),
                    int(dus),
                    'BOTH')
        # Pickup time
        array_t += '\tpickup_time/ascii_s = {0}' \
                   '\n\tpickup_time/epoch_l = {1}' \
                   '\n\tpickup_time/micro_seconds_i = {2}' \
                   '\n\tpickup_time/type_s = {3}\n'\
            .format(time.ctime(int(pepoch)),
                    int(pepoch),
                    int(pus),
                    'BOTH')
        # Longitude and Latitude
        array_t += '\tlocation/X/value_d = {0}' \
                   '\n\tlocation/X/units_s = {1}' \
                   '\n\tlocation/Y/value_d = {2}' \
                   '\n\tlocation/Y/units_s = {3}\n'\
            .format(X,
                    units,
                    Y,
                    units)
        # Elevation
        array_t += '\tlocation/Z/value_d = {0}' \
                   '\n\tlocation/Z/units_s = {1}' \
                   '\n\tlocation/coordinate_system_s = {2}' \
                   '\n\tlocation/projection_s = {3}' \
                   '\n\tlocation/description_s = {4}\n'\
            .format(vals_dep['Elev'],
                    'meters',
                    coordinate_system,
                    'none',
                    ellipsoid)
        # Sensor information
        array_t += '\tsensor/serial_number_s = {0}' \
                   '\n\tsensor/model_s = {1}' \
                   '\n\tsensor/manufacturer_s = {2}' \
                   '\n\tsensor/notes_s = {3}' \
                   '\n\tchannel_number_i = {4}'\
            .format(vals_dep['Sensor'],
                    '',
                    '',
                    '',
                    vals_dep['Channel'])

        ret.append(array_t)
        RECVSTN[arrayID][stationID][chan] = array_t

    def append_ret(vals):
        '''   Build lines for dep file.
              val_dep is a hash of deployment values
              val_pu is a hash of pickups
        '''
        vals_dep, vals_pu, msg = stripdeppu(vals)
        ret.append(
            "RECV;{0};{1};{2};{3};{4};{5};{6};{7};{8};{9};{10};{11};{12};"
            "{13};{14}".format(vals_dep['ID'],
                               vals_dep['Station'],
                               vals_dep['Line'],
                               vals_dep['Type'],
                               vals_dep['Channel'],
                               vals_dep['Sensor'],
                               vals_dep['Uphole'],
                               vals_dep['Lat'],
                               vals_dep['Lon'],
                               vals_dep['Elev'],
                               vals_dep['DT'],
                               vals_dep['DTime'],
                               vals_pu['PUTime'],
                               vals_dep['Shots'],
                               vals_pu['Comment']))

    # End append_ret

    err = []

    def append_err(vals):
        '''   Check for errors in deployment and pickup entries
        Tests:
           *1) Does a texan have a missing pickup (or deploy) record?
           2) Are the station ID's unique?
           *3) Is the pickup position more than 100 meters from the
               deploy position?
           *4) Does the deploy texan ID match the pickup texan ID?
           *5) Is the elevation within 200 meters of the deployment record?
           *6) Is the pickup LED not 'G'?
           *7) Is texan ID in the correct range?
        '''
        vals_dep, vals_pu, msg = stripdeppu(vals)
        lineNos = "[ {0}, {1} ]".format(vals_dep['n'], vals_pu['n'])

        # 1) Missing deploy or pickup record
        if msg:
            msg = "#{0} Warning: Station: {1} {2}!\n".format(lineNos,
                                                             vals_dep[
                                                                 'Station'],
                                                             msg)
        else:
            msg = ''

        # 4) Deploy texan SN and pickup texan SN differ
        if vals_dep['ID'] != vals_pu['ID']:
            msg += "#{3} Warning: Station: {2}, deployed texan SN {0} and" \
                   " picked up texan SN {1} differ!\n"\
                .format(vals_dep['ID'],
                        vals_pu['ID'],
                        vals_dep['Station'],
                        lineNos)
        try:
            # 7)
            if int(vals_dep['ID']) > MAX_DAS_SN or int(
                    vals_dep['ID']) < MIN_DAS_SN:
                msg += "#{0} Warning: suspicious data logger serial number" \
                       " {1} at station {2}!\n"\
                    .format(lineNos,
                            vals_dep['ID'],
                            vals_dep['Station'])
        except ValueError:
            # 7)
            if int(vals_dep['ID'], 16) > MAX_DAS_SN or int(
                    vals_dep['ID'], 16) < MIN_DAS_SN:
                msg += "#{0} Warning: suspicious data logger serial number" \
                       " {1} at station {2}!\n"\
                    .format(lineNos,
                            vals_dep['ID'],
                            vals_dep['Station'])

        # 6) LED not green on pickup
        if 'LED' in vals_pu and vals_pu['LED'] != '':
            if vals_pu['LED'] != 'G' and vals_pu['LED'] != 'g':
                msg += "#{0} Warning: Station: {1}, LED was '{2}' at" \
                       " pickup!\n"\
                    .format(lineNos, vals_dep['Station'], vals_pu['LED'])

        try:
            # 5) Elevation on pickup record is not within 200 meters of
            # deployment
            if abs(float(vals_dep['Elev']) -
                   float(vals_pu['Elev'])) >= LOC_TOL_METERS:
                msg += "#{0} Warning: Station: {1}, elevation differs by" \
                       " more that 200 meters!\n"\
                    .format(lineNos, vals_dep['Station'])

            # 3) Is pickup location more that about 100 meters from deploy
            # location

            # Deploy lat and lon
            dist = 0
            if vals_dep['Lat'] and vals_dep['Lon'] and vals_pu['Lat'] and \
                    vals_pu['Lon']:
                d_lat = vals_dep['Lat'].replace('N', '+')
                d_lat = d_lat.replace('S', '-')
                d_lat = float(d_lat)
                d_lon = vals_dep['Lon'].replace('E', '+')
                d_lon = d_lon.replace('W', '-')
                d_lon = float(d_lon)
                # Pickup lat and lon
                p_lat = vals_pu['Lat'].replace('N', '+')
                p_lat = p_lat.replace('S', '-')
                p_lat = float(p_lat)
                p_lon = vals_pu['Lon'].replace('E', '+')
                p_lon = p_lon.replace('W', '-')
                p_lon = float(p_lon)
                '''
                # One degree lat equals this many meters at lat p
                # 111132.954 - 559.822(cos 2p) + 1.175(cos 4p)
                #
                # One degree lon equals this many meters at lat p
                # ((pi / 180.) * 6378137.) * cos (0.99664719. * tan (p))
                '''
                # Average lat
                a_lat = (d_lat + p_lat) / 2.
                fac_lat =\
                    111132.954 - (559.822 * (cos(2. * radians(a_lat)))) +\
                    (1.175 * (cos(4. * radians(a_lat))))
                fac_lon =\
                    ((pi / 180.) * 6378137.) * \
                    cos(0.99664719 * tan(radians(a_lat)))
                delta_lat = (d_lat - p_lat) * fac_lat
                delta_lon = (d_lon - p_lon) * fac_lon
                # This is a gross estimate
                dist = sqrt((delta_lat * delta_lat) + (delta_lon * delta_lon))
            elif vals_dep['Y'] and vals_dep['X'] and vals_pu['Y'] and\
                    vals_pu['X']:
                dist = sqrt(
                    ((float(vals_dep['Y']) - float(vals_pu['Y'])) ** 2) + (
                            (float(vals_dep['X']) - float(vals_pu['X'])) ** 2))

            if dist > LOC_TOL_METERS:
                msg += "#{0} Warning: Station: {1}, distance of pickup and" \
                       " deployment location differs by more that" \
                       " 100 meters!\n"\
                    .format(lineNos, vals_dep['Station'])
        except Exception as e:
            msg += "Unexpected exception: {0}\n".format(e)

        err.append(msg)

    # End append_err

    stations = sorted(recvkey.keys())
    for station in stations:
        keys = sorted(recvkey[station])
        vals = []
        for k in keys:
            vals.append(recvqc[k])
        append_err(vals)
        if DEP:
            append_ret(vals)
        else:
            get_recv_row(vals)
    return err, ret


FIELDS['RECV'] = ['Receiver-ID', 'Station', 'Line', 'Type', 'Channel',
                  'Sensor',
                  'Uphole', 'Lat', 'Y', 'Lon', 'X', 'Elev', 'Team',
                  'DTimeY:J:H:M:S', 'TimeYear',
                  'TimeH:M', 'TimeMo/Da', 'PTimeY:J:H:M:S', 'Shots', 'Comment',
                  'LED', 'DorP']

RECVQC = {}
RECVKEY = {}
RECVSTN = {}


def build_recv(order, line, n):
    ''' order => the keys we have used from FIELD
        line  => the fields of the line from the field
        n     => the line number from original file
    '''
    global RECVSTN
    vals = {'ID': '', 'Station': '', 'Line': '999', 'Type': '', 'Channel': '1',
            'Sensor': '', 'Uphole': '', 'Lat': '', 'Y': '', 'Lon': '', 'X': '',
            'Elev': '', 'DT': '',
            'DTime': '', 'PUTime': '', 'Shots': '', 'Comment': '', 'LED': '',
            'DorP': '',
            'n': ''}

    # Shot info in this file
    if 'Shot-ID' in order:
        return None

    if 'Receiver-ID' not in order:
        LOGGER.error("Receiver-ID needed to create dep file.\n")
        return None

    DTime = ''
    PTime = ''
    # Get deploy and pickup time
    if has_time(order):
        try:
            if 'DTimeY:J:H:M:S' not in order and is_deploy(order, line):
                yr = int(line[order['TimeYear']])
                if 'TimeH:M' in order:
                    hr, mn = map(int, line[order['TimeH:M']].split(':'))

                if 'TimeMo/Da' in order:
                    mo, da = map(int, line[order['TimeMo/Da']].split('/'))
                    tdoy = timedoy.TimeDOY(year=yr,
                                           month=mo,
                                           day=da,
                                           hour=hr,
                                           minute=mn,
                                           second=0,
                                           microsecond=0,
                                           doy=None,
                                           epoch=None,
                                           dtobject=None)
                    doy = tdoy.doy()

                sc = 0.0

                DTime = "{0:4d}:{1:03d}:{2:02d}:{3:02d}:{4:06.3f}".format(yr,
                                                                          doy,
                                                                          hr,
                                                                          mn,
                                                                          sc)
            else:
                try:
                    DTime = line[order['DTimeY:J:H:M:S']]
                except BaseException:
                    DTime = None

            if 'PTimeY:J:H:M:S' not in order and not is_deploy(order, line):
                yr = int(line[order['TimeYear']])
                if 'TimeH:M' in order:
                    hr, mn = map(int, line[order['TimeH:M']].split(':'))

                if 'TimeMo/Da' in order:
                    mo, da = map(int, line[order['TimeMo/Da']].split('/'))
                    tdoy = timedoy.TimeDOY(year=yr,
                                           month=mo,
                                           day=da,
                                           hour=hr,
                                           minute=mn,
                                           second=0,
                                           microsecond=0,
                                           doy=None,
                                           epoch=None,
                                           dtobject=None)
                    doy = tdoy.doy()

                sc = 0.0

                PTime = "{0:4d}:{1:03d}:{2:02d}:{3:02d}:{4:06.3f}".format(yr,
                                                                          doy,
                                                                          hr,
                                                                          mn,
                                                                          sc)
            else:
                try:
                    PTime = line[order['PTimeY:J:H:M:S']]
                except BaseException:
                    PTime = None
        except Exception as e:
            LOGGER.error(
                "{1}:\n\tCan't convert time {0}\n".format(line, e))
            return

    keys = order.keys()
    # Look through rest of columns
    for k in keys:
        try:
            if k == 'Receiver-ID':
                try:
                    vals['ID'] = int(line[order[k]])
                    if USE_FACE_PLATE_SN and vals['ID'] < 10000:
                        vals['ID'] += 10000

                    vals['ID'] = str(vals['ID'])
                except BaseException:
                    vals['ID'] = line[order[k]]
            elif k == 'Station':
                try:
                    vals['Station'] = str(int(line[order[k]]))
                except BaseException:
                    vals['Station'] = line[order[k]]
                if vals['Station'] == '100':
                    pass
            elif k == 'Line':
                vals['Line'] = line[order[k]]
            elif k == 'Type':
                vals['Type'] = line[order[k]]
            elif k == 'Channel':
                vals['Channel'] = line[order[k]]
                try:
                    int(vals['Channel'])
                except ValueError:
                    vals['Channel'] = '1'
            elif k == 'Sensor':
                vals['Sensor'] = line[order[k]]
            elif k == ['Uphole']:
                vals['Uphole'] = line[order[k]]
            elif k == 'Lat':
                if DEP:
                    vals['Lat'] = _sign(line[order[k]], 'lat')
                else:
                    vals['Lat'] = __sign(line[order[k]], 'lat')
            elif k == 'Y':
                vals['Y'] = line[order[k]]
            elif k == 'Lon':
                if DEP:
                    vals['Lon'] = _sign(line[order[k]], 'lon')
                else:
                    vals['Lon'] = __sign(line[order[k]], 'lon')
            elif k == 'X':
                vals['X'] = line[order[k]]
            elif k == 'Elev':
                vals['Elev'] = line[order[k]]
            elif k == 'Team':
                vals['DT'] = line[order[k]]
            elif k == 'Shots':
                vals['Shots'] = line[order[k]]
            elif k == 'Comment':
                vals['Comment'] = line[order[k]]
            elif k == 'LED':
                vals['LED'] = line[order[k]]
            if k == 'DorP':
                vals['DorP'] = line[order[k]]
        except IndexError:
            pass

    vals['n'] = n
    vals['DTime'] = DTime
    vals['PUTime'] = PTime

    if int(vals['Line']) not in RECVSTN:
        RECVSTN[int(vals['Line'])] = {}

    tmpkey = vals['Station']
    if int(vals['Station']) not in RECVSTN[int(vals['Line'])]:
        RECVSTN[int(vals['Line'])][int(vals['Station'])] = {}

    RECVSTN[int(vals['Line'])][int(vals['Station'])][
        int(vals['Channel'])] = False

    i = 0
    while tmpkey in RECVQC:
        tmpkey = tmpkey.split(':')[0] + ":{0}".format(i)
        i += 1
    rkey = "{0}:{1}".format(vals['Station'], vals['Channel'])
    if rkey not in RECVKEY:
        RECVKEY[rkey] = []

    RECVKEY[rkey].append(tmpkey)
    RECVQC[tmpkey] = vals


def write_shot_header(fh):
    import time as t
    fh.write("#Shot dep written by noven {1} : {0}\n".format(
        t.ctime(t.time()), PROG_VERSION))
    fh.write(
        "#S_id;S_station;S_line;S_lat;S_lon;S_elev;S_time;S_pre-trig;"
        "S_post-trig;S_sr;S_depth;S_size;S_rvel;S_radius;S_comment\n")


def write_recv_header(fh):
    import time as t
    fh.write("#Receiver dep written by noven {1} : {0}\n".format(
        t.ctime(t.time()), PROG_VERSION))
    fh.write(
        "#R_id;R_station;R_line;R_receiver-type;R_chan;R_sensor;R_uphole;"
        "R_lat;R_lon;R_elev;R_team;R_deploy_time;R_pickup_time;"
        "R_shots;R_comment\n")


SEPMAP = {r'tab': '\t', 'comma': ',',
          'semi-colon': ';', 'colon': ':', 'space': r'\s'}


class MyQTableWidget(QtWidgets.QTableWidget):

    def __init__(self, parent=None):
        super(MyQTableWidget, self).__init__(parent)

    def mclear(self):
        self.colKey = {}
        self.cols = []

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        fmts = event.mimeData().formats()
        fmts.count()

        item = self.itemAt(event.pos())
        if item is not None:
            col = item.column()
            if item.row() == 0:
                text = event.mimeData().text()
                cell = QtWidgets.QTableWidgetItem(text)
                self.setItem(item.row(), item.column(), cell)
                self.colheaders()
                self.resizeColumnToContents(col)

    def colheaders(self):
        self.colKey = {}
        self.cols = []
        ncols = self.columnCount()
        for y in range(ncols):
            item = self.item(0, y)
            mytext = Qt.QString()
            mytext = item.text()
            self.colKey[str(mytext)] = y
            self.cols.append(str(mytext))


class DragLabel(QtWidgets.QLabel):
    def __init__(self, text, parent):
        super(DragLabel, self).__init__(text, parent)

        self.setAutoFillBackground(True)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

    def mousePressEvent(self, event):
        hotSpot = event.pos()

        mimeData = QtCore.QMimeData()
        mimeData.setText(self.text())
        mimeData.setData('application/x-hotspot',
                         '%d %d' % (hotSpot.x(), hotSpot.y()))

        pixmap = QtWidgets.QPixmap(self.size())
        self.render(pixmap)

        drag = QtWidgets.QDrag(self)
        drag.setMimeData(mimeData)
        drag.setPixmap(pixmap)
        drag.setHotSpot(hotSpot)

        dropAction = drag.exec_(QtCore.Qt.CopyAction |
                                QtCore.Qt.MoveAction, QtCore.Qt.CopyAction)

        if dropAction == QtCore.Qt.MoveAction:
            self.close()
            self.update()


class DragWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(DragWidget, self).__init__(parent)
        x = 5
        y = 5
        xmax = 250
        xbase = 5

        #
        # FIELD_KEYS: ('SHOT', 'RECV')
        # FIELDS keyed on FIELD_KEYS
        #
        for key in FIELD_KEYS:
            for word in FIELDS[key]:
                wordLabel = DragLabel(word, self)
                wordLabel.move(x, y)
                wordLabel.show()
                x += wordLabel.width() + 2
                if x >= xmax:
                    x = xbase
                    y += wordLabel.height() + 2

            x = xmax + 100
            xbase = xmax + 100
            xmax = (2 * xmax) + 100
            y = 5

        wordLabel = DragLabel('Ignore', self)
        wordLabel.move(685, 5)
        wordLabel.show()


class SetupDialog(QtWidgets.QDialog):
    def __init__(self, settings, parent=None):
        super(SetupDialog, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        outfileFormatLabel = QtWidgets.QLabel("Output Format")
        self.outfileFormat = QtWidgets.QComboBox()
        outfileFormatLabel.setBuddy(self.outfileFormat)
        self.outfileFormat.addItems(["kef", ])
        self.outfileFormat.setCurrentIndex(
            self.outfileFormat.findText(settings['outFormat']))

        fieldSeparatorLabel = QtWidgets.QLabel("Column Separator")
        self.fieldSeparator = QtWidgets.QComboBox()
        fieldSeparatorLabel.setBuddy(self.fieldSeparator)
        self.fieldSeparator.addItems(
            ["comma", "semi-colon", "colon", "tab", "space"])
        self.fieldSeparator.setCurrentIndex(
            self.fieldSeparator.findText(settings['colSep']))

        skipLinesLabel = QtWidgets.QLabel("Skip Lines")
        self.skipLines = QtWidgets.QSpinBox()
        skipLinesLabel.setBuddy(self.skipLines)
        self.skipLines.setRange(0, 12)
        self.skipLines.setValue(settings['linesSkip'])

        viewLinesLabel = QtWidgets.QLabel("View Lines")
        self.viewLines = QtWidgets.QSpinBox()
        viewLinesLabel.setBuddy(self.viewLines)
        self.viewLines.setRange(1, 60)
        self.viewLines.setValue(settings['linesView'])

        self.settings = settings

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Apply |
            QtWidgets.QDialogButtonBox.Close)

        grid = QtWidgets.QGridLayout()
        grid.addWidget(outfileFormatLabel, 0, 0)
        grid.addWidget(self.outfileFormat, 0, 1)
        grid.addWidget(fieldSeparatorLabel, 1, 0)
        grid.addWidget(self.fieldSeparator, 1, 1)
        grid.addWidget(skipLinesLabel, 2, 0)
        grid.addWidget(self.skipLines, 2, 1)
        grid.addWidget(viewLinesLabel, 3, 0)
        grid.addWidget(self.viewLines, 3, 1)

        grid.addWidget(buttonBox, 4, 0, 2, -1)
        self.setLayout(grid)

        self.connect(buttonBox.button(QtWidgets.QDialogButtonBox.Apply),
                     QtCore.SIGNAL("clicked ()"), self.apply)

        self.connect(buttonBox, QtCore.SIGNAL("rejected ()"),
                     self, QtCore.SLOT("reject ()"))

    def apply(self):
        self.settings['linesView'] = self.viewLines.value()
        self.settings['colSep'] = self.fieldSeparator.currentText()
        self.settings['outFormat'] = self.outfileFormat.currentText()
        self.settings['linesSkip'] = self.skipLines.value()
        self.emit(QtCore.SIGNAL("changed"))

    def rejected(self):
        LOGGER.info("Reject")


class Novitiate(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(Novitiate, self).__init__(parent)

        self.settings = dict(outFormat='dep', colSep='comma',
                             linesSkip=0, linesView=3)

        self.setWindowTitle('Noven Version: ' + PROG_VERSION)

        self.readFileLines = None
        #
        # Setup menus
        #
        openin = QtWidgets.QAction('Open...', self)
        openin.setShortcut('Ctrl+O')
        openin.setStatusTip('Open input file.')
        self.connect(openin, QtCore.SIGNAL('triggered ()'), self.openInfile)

        saveas = QtWidgets.QAction('Save As...', self)
        saveas.setShortcut('Ctrl+S')
        saveas.setStatusTip('Save output file.')
        self.connect(saveas, QtCore.SIGNAL('triggered ()'), self.saveAs)

        config = QtWidgets.QAction('Configure...', self)
        config.setShortcut('Ctrl+C')
        config.setStatusTip('Set input file field separator etc.')
        self.connect(config, QtCore.SIGNAL('triggered ()'), self.configure)

        exit = QtWidgets.QAction('Exit', self)
        exit.setShortcut('Ctrl+Q')
        exit.setStatusTip('Exit application')
        self.connect(exit, QtCore.SIGNAL(
            'triggered()'), QtCore.SLOT('close()'))

        menubar = self.menuBar()
        file = menubar.addMenu('&File')
        file.addAction(openin)
        file.addAction(saveas)
        file.addAction(config)
        file.addAction(exit)

        #
        # Dock
        #
        dockW = QtWidgets.QDockWidget("SHOT Fields / RECV Fields", self)
        dockW.setObjectName("DockW")
        dockW.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
        dockW.setWidget(DragWidget(self))
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockW)

        #
        # Table
        #
        self.table = MyQTableWidget()
        self.setCentralWidget(self.table)

        status = self.statusBar()
        status.setSizeGripEnabled(False)
        status.showMessage("Ready", 5000)

    def configure(self):
        self.settingsDialog = SetupDialog(self.settings, self)
        self.connect(self.settingsDialog, QtCore.SIGNAL(
            "changed"), self.refreshTable)
        self.settingsDialog.show()

    def refreshTable(self):
        key = self.settings['colSep']
        sep = SEPMAP[str(key)]
        LOGGER.debug("Refresh, '{0}' \n".format(sep))

        maxY = 0
        LINES = []
        for line in self.readFileLines:
            line = line.strip()
            flds = line.split(sep)
            if len(flds) > maxY:
                maxY = len(flds)
            LINES.append(flds)

        maxX = self.settings['linesView'] + 1
        self.table.clear()

        self.table.setColumnCount(maxY)
        self.table.setRowCount(maxX)

        hh = self.table.horizontalHeader()
        hh.hide()
        vh = self.table.verticalHeader()
        vh.hide()

        try:
            if self.table.cols:
                y = 0
                for t in self.table.cols:
                    item = QtWidgets.QTableWidgetItem(t)
                    self.table.setItem(0, y, item)
                    y += 1

        except AttributeError:
            for y in range(maxY):
                item = QtWidgets.QTableWidgetItem('Ignore')
                self.table.setItem(0, y, item)

        s = self.settings['linesSkip']
        for x in range(maxX):
            try:
                FLDS = LINES[x + s]
            except IndexError:
                continue

            for y in range(maxY):
                try:
                    text = "{0}".format(FLDS[y])
                except IndexError:
                    continue

                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignRight |
                                      QtCore.Qt.AlignVCenter)

                self.table.setItem(x + 1, y, item)

        self.table.resizeColumnsToContents()
        self.table.setAcceptDrops(True)

    def openInfile(self):
        inFileName, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Open input file', os.getcwd())
        if os.path.exists(inFileName):
            fh = open(inFileName, 'U')
            self.readFileLines = fh.readlines()
            fh.close()
            self.table.clear()
            self.refreshTable()
        else:
            self.readFileLines = None

    def saveAs(self):
        saveFileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save output as', os.getcwd())
        if not saveFileName:
            return
        key = self.settings['colSep']
        sep = SEPMAP[str(key)]
        skip = self.settings['linesSkip']
        fh = None
        n = 1
        for line in self.readFileLines[skip:]:
            line = line.strip()
            if not line:
                continue
            flds = line.split(sep)
            build_recv(self.table.colKey, flds, n + skip)
            sline = build_shot(self.table.colKey, flds, n + skip)
            n += 1
            if sline is not None:
                if fh is None:
                    fh = open(saveFileName, 'w+')
                    write_shot_header(fh)
                if sline:
                    fh.write(sline + '\n')
        if RECVQC:
            err, ret = churn_recv(RECVQC, RECVKEY)
            if fh is None:
                fh = open(saveFileName, 'w+')
                write_recv_header(fh)

            for e in err:
                fh.write(e)
            arrays = sorted(RECVSTN.keys())
            for a in arrays:
                stations = sorted(RECVSTN[a].keys())
                for s in stations:
                    for c in range(1, 7):
                        if c in RECVSTN[a][s]:
                            fh.write(RECVSTN[a][s][c] + '\n')
        if fh:
            fh.close()


if __name__ == '__main__':
    get_args()
    app = QtWidgets.QApplication(sys.argv)
    form = Novitiate()
    form.show()
    app.exec_()
