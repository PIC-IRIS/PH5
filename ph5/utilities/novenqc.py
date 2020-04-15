#!/usr/bin/env pnpython3
#
# QC receiver and shot csv files
#
# Steve Azevedo, Feb 2015
#

import sys
import logging
import os
import re
from random import randint
from inspect import stack
from ast import literal_eval
from pyproj import Geod
import simplekml as kml

from ph5.core import timedoy

PROG_VERSION = '2019.14'
LOGGER = logging.getLogger(__name__)

FACTS = {'km': 1000., 'm': 1., 'dm': 1. / 10., 'cm': 1. / 100.,
         'mm': 1. / 1000., 'kmi': 1852.0, 'in': 0.0254, 'ft': 0.3048,
         'yd': 0.9144,
         'mi': 1609.344, 'fath': 1.8288, 'ch': 20.1168, 'link': 0.201168,
         'us-in': 1. / 39.37, 'us-ft': 0.304800609601219,
         'us-yd': 0.914401828803658,
         'us-ch': 20.11684023368047, 'us-mi': 1609.347218694437,
         'ind-yd': 0.91439523, 'ind-ft': 0.30479841, 'ind-ch': 20.11669506}

#  RE for type descripters, ie int31
typeRE = re.compile(r"(\D+)(\d+)")
#
timeRE = re.compile(".*time/ascii_s")

# List of table rows.
TABLE = []
# Ordered list of column names.
NAMES = []
# Configuration that describes table columns
COLS = {}
# Table column seperators
SEP = ''
# List of errors
ERR = []
# receiver: TOP[varray][vid][vchan] = list of dictionary of matching rows
# event: TOP[varray][vid] = list of dictionary of matching rows from csv
TOP = {}


def qc_map(outfile):
    '''
       Create a simple kml of events or receivers using simplekml
    '''
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        base = os.path.join(base_path, 'kmlicons')
    except Exception as e:
        LOGGER.error(e.message)
        sys.exit()

    def get_lat_lon(row):
        if 'location/Z/value_d' in row:
            lonlat = (row['location/X/value_d'],
                      row['location/Y/value_d'], row['location/Z/value_d'])
        else:
            lonlat = (row['location/X/value_d'], row['location/Y/value_d'])

        return lonlat

    if 'channel_number_i' in NAMES:
        is_rec = True
    else:
        is_rec = False

    varrays = sorted(TOP.keys())
    mmap = kml.Kml()
    if is_rec:
        for varray in varrays:
            # receiver
            vids = sorted(TOP[varray].keys())
            for vid in vids:
                chans = TOP[varray][vid].keys()
                for chan in chans:
                    rows = TOP[varray][vid][chan]
                    for r in rows:
                        llz = get_lat_lon(r)
                        if 'Deploy/Pickup' in r:
                            des = "Deploy or Pickup? {0}\n".format(
                                r['Deploy/Pickup'])
                        else:
                            des = ""
                        if 'das/serial_number_s' in r:
                            des += "DAS: {0}\n".format(
                                r['das/serial_number_s'])
                        if "deploy_time/ascii_s" in r:
                            des += " Deploy: {0}\n".format(
                                r["deploy_time/ascii_s"])
                        if "pickup_time/ascii_s" in r:
                            des += " Pickup: {0}".format(
                                r["pickup_time/ascii_s"])

                        pt = mmap.newpoint(name=str(vid), coords=[
                            llz], description=des)
                        pt.style.iconstyle.icon.href = 'file:/{0}'.format(
                            os.path.join(base, 'station.png'))
                        pt.style.iconstyle.scale = 0.5
    else:
        for varray in varrays:
            # event
            vids = TOP[varray].keys()
            for vid in vids:
                rows = TOP[varray][vid]
                for r in rows:
                    llz = get_lat_lon(r)
                    des = ""
                    if "time/ascii_s" in r:
                        des = "Event time: {0}\n".format(r["time/ascii_s"])
                    if "size/value_d" in r:
                        des += " Size: {0}".format(r["size/value_d"])
                    pt = mmap.newpoint(name=str(vid), coords=[
                        llz], description=des)
                    pt.style.iconstyle.icon.href = 'file://{0}'.format(
                        os.path.join(base, 'shot.png'))

    mmap.save(outfile)

    return False


def mk_table(table, sep):
    '''
       Split lines in csv file into list of dictionaries.
    '''
    ret = []
    errs = []
    n = 0
    ll = table[randint(0, len(table) - 1)]
    ncolumns = len(ll.split(','))
    for t in table:
        t = t.strip()
        n += 1
        if t[0] == '#' or t == '':
            continue
        try:
            flds = t.split(sep)
            ret.append(flds)
            if len(flds) != ncolumns:
                errs.append("{0}: Wrong number of columns.".format(n))
        except Exception as e:
            errs.append(
                "Exception {0} at input file line {1}.".format(e.message, n))

    return ret, errs


def churn():
    '''
       Key table row dictionaries by array, id_s and channel_number_i.
    '''
    top = {}
    n = 0
    if 'channel_number_i' in NAMES:
        is_rec = True
    else:
        is_rec = False

    for t in TABLE:
        n += 1
        vals = {}
        for i in range(len(NAMES)):
            k = NAMES[i]
            v = t[i]
            vals[k] = v

        vals['in_file_line_number'] = n
        vid_s = int(vals['id_s'])
        if is_rec:
            varray = int(vals['Array'])
            vchannel_number_i = int(vals['channel_number_i'])
            if varray not in top:
                top[varray] = {}
            if vid_s not in top[varray]:
                top[varray][vid_s] = {}
                top[varray][vid_s][vchannel_number_i] = []
            if vchannel_number_i not in top[varray][vid_s]:
                top[varray][vid_s][vchannel_number_i] = []

            top[varray][vid_s][vchannel_number_i].append(vals)
        else:
            varray = int(vals['Array'])
            if varray not in top:
                top[varray] = {}
            if vid_s not in top[varray]:
                top[varray][vid_s] = []

            top[varray][vid_s].append(vals)

    return top


def qc_deploy_pickup(rows):
    '''
       Look at deploy and pickup times and locations.
    '''

    def qc_dist(ys, xs, zs):
        '''
           Measure distance between pickup and deployment.
        '''
        if ys == [] or xs == []:
            return [None] * 4

        #
        # Need to check for UTM and convert to lat/lon
        #
        units = 'm'
        ellipsoid = 'WGS84'
        config = "+ellps={0}".format(ellipsoid)
        g = Geod(config)
        az, baz, dist = g.inv(xs[0], ys[0], xs[1], ys[1])
        if len(zs) > 1:
            zdelta = float(zs[1]) - float(zs[0])
        else:
            zdelta = 0.0
        return az, baz, dist / FACTS[units], zdelta

    def qc_time(t1, t2):
        '''
           Measure difference between deployment and pickup times.
        '''
        try:
            e1 = timedoy.fdsn2epoch(t1)
        except timedoy.TimeError:
            e1 = timedoy.passcal2epoch(t1)

        try:
            e2 = timedoy.fdsn2epoch(t2)
        except timedoy.TimeError:
            e2 = timedoy.passcal2epoch(t2)

        return e2 - e1

    ell = len(rows)
    if ell == 1:
        return []
    ys = []
    xs = []
    zs = []
    line_numbers = []
    dptime = {}
    errs = []
    for n in range(ell):
        r = rows[n]
        line_numbers.append(r['in_file_line_number'])
        try:
            ys.append(r['location/Y/value_d'])
            xs.append(r['location/X/value_d'])
            zs.append(r['location/Z/value_d'])
        except KeyError:
            pass

        try:
            dop = r['Deploy/Pickup']
            if dop == 'D':
                dptime['D'] = r['deploy_time/ascii_s']
            elif dop == 'P':
                dptime['P'] = r['pickup_time/ascii_s']
        except KeyError:
            try:
                dptime['D'] = r['deploy_time/ascii_s']
                dptime['P'] = r['pickup_time/ascii_s']
            except KeyError:
                dptime['D'] = "1970:001:00:00:00.000"
                dptime['P'] = "2052:001:00:00:00.000"

    # How far should we allow between the deploy and pickup locations?
    az, baz, dist, zdelta = qc_dist(ys, xs, zs)
    if dist is not None and dist > 5:
        # XXX   ERROR   XXX
        errs.append(
            "{0}-{1} Warning: Distance between deployment and pickup locations"
            " seems large for station {2}.".format(
                line_numbers[0], line_numbers[1], r['id_s']))
    # What should be the time between deployment and pickup?
    time_delta = qc_time(dptime['D'], dptime['P'])
    # About 6 months
    if time_delta > 15552000 or time_delta < 0:
        errs.append(
            "{0}-{1} Warning: time between deployment and pickup unusual for"
            " station {2}.".format(
                line_numbers[0], line_numbers[1], r['id_s']))

    return errs


def qc_bulogic_receiver():
    '''
       Entry point to qc receiver business logic.
    '''
    ret = []
    #
    # varrays
    #
    varrays = sorted(TOP.keys())
    for varray in varrays:
        vids = sorted(TOP[varray].keys())
        for vid in vids:
            if isinstance(TOP[varray][vid], dict):
                chans = sorted(TOP[varray][vid].keys())
                for chan in chans:
                    rows = TOP[varray][vid][chan]
                    err = qc_deploy_pickup(rows)
                    if err:
                        ret += err

    return ret


def match_range(value, rrange):
    '''
       Check if value is in rrange.
    '''
    if rrange is None:
        return True
    low, high = map(float, rrange.split('-'))
    try:
        v = float(value)
    except Exception:
        return False

    if v >= low and v <= high:
        return True
    else:
        return False


def match_re(value, reg_expr):
    '''
       Check to see if value matches regular expression, reg_expr.
    '''
    if reg_expr is None:
        return True

    reg_expr = str(reg_expr)
    rre = re.compile(reg_expr)
    if rre.match(value):
        return True
    else:
        return False


def match_type(value, ttype):
    '''
       Check to see if value matches type, example int15, string1024, float64.
    '''
    if ttype is None:
        return True

    value = value.strip()
    value = value.lstrip('0')
    try:
        mo = typeRE.match(ttype)
        t, ll = mo.groups()
        if t == 'int':
            v = literal_eval(value)
            v = int(value)
            if not isinstance(v, int):
                return False
            maximum = 2 ** int(ll) - 1
            minimum = (maximum + 1) * -1
            if v < maximum and v > minimum:
                return True
            else:
                return False
        elif t == 'float':
            v = literal_eval(value)
            if isinstance(v, float) or isinstance(v, int):
                return True
            else:
                return False
        elif t == 'string':
            v = str(value)
            n = len(v)
            if n <= ll:
                return True
            else:
                return False
        else:
            print "Unknown type {0} in cfg.".format(ttype)
    except Exception as e:
        print "Error: ", e.message
        return False


def qc_fields():
    '''
       Check each column for regular expression, type, range.
    '''
    n = 0
    ret = []
    for t in TABLE:
        n += 1
        for i in range(len(t)):
            key = NAMES[i]
            if key == 'Ignore':
                continue
            v = t[i]
            if 'type' in COLS[key]:
                ttype = COLS[key]['type']
            else:
                ttype = None
            if 'help' in COLS[key]:
                hhelp = COLS[key]['help']
            else:
                hhelp = None
            if 're' in COLS[key]:
                rre = COLS[key]['re']
            else:
                rre = None
            if 'range' in COLS[key]:
                rrange = COLS[key]['range']
            else:
                rrange = None
            # Check regular expression
            if not match_re(v, rre):
                ret.append(
                    "{0}: Value of column {1} {2} does not match re. Help:"
                    " {3}".format(
                        n, key, v, hhelp))
            # Check type
            if not match_type(v, ttype):
                ret.append(
                    "{0}: Value of column {1} {2} does not match type. Type:"
                    " {3}".format(
                        n, key, v, ttype))
            # Check range
            if not match_range(v, rrange):
                ret.append(
                    "{0}: Value of column {1} {2} does not match expected"
                    " range. Range: {3}".format(
                        n, key, v, rrange))
            # Check if ascii time
            if timeRE.match(key):
                try:
                    timedoy.fdsn2epoch(v, fepoch=True)
                except timedoy.TimeError:
                    try:
                        timedoy.passcal2epoch(v, fepoch=True)
                    except timedoy.TimeError:
                        ret.append(
                            "{0}: Value of column {1} {2} does not match"
                            " expected time string".format(
                                n, key, v))

    return ret


def qc_req_cols():
    '''
       Check to see if all required columns are present.
    '''
    ret = []
    cols_keys = COLS.keys()
    for k in cols_keys:
        info_keys = COLS[k]
        req = eval(info_keys['required'])
        if req is True:
            if k not in NAMES:
                ret.append("Missing column {0}. Help: {1}".format(
                    k, info_keys['help']))
        elif req is not False:
            flds = stack()
            print "Should never get here: {0} {1}.".format(flds[1], flds[2])

    return ret


def qc_receivers(table, names, cols, sep=','):
    '''
       Entry point to QC receiver csv data
    '''
    global TABLE, NAMES, COLS, TOP, ERR

    NAMES = names
    COLS = cols
    ERR = []
    TOP = {}
    # Do we have the required named columns
    ret = qc_req_cols()
    # Convert to list (rows) of lists ()
    TABLE, err = mk_table(table, sep)
    if err != [] or ret != []:
        # Fatal errors in input
        ERR = ret + err
        return False

    ret = qc_fields()
    if ret != []:
        ERR = ret
        return False

    TOP = churn()
    ERR = qc_bulogic_receiver()

    return False


def qc_shots(table, names, cols, sep=','):
    '''
       Entry point to QC shot csv data
    '''
    global TABLE, NAMES, COLS, TOP, ERR

    NAMES = names
    COLS = cols
    ERR = []
    TOP = {}
    # Do we have the required named columns
    ret = qc_req_cols()
    # Convert to list (rows) of lists ()
    TABLE, err = mk_table(table, sep)
    if err != [] or ret != []:
        # Fatal errors in input
        ERR = ret + err
        return False

    ret = qc_fields()
    if ret != []:
        ERR = ret
        return False

    TOP = churn()

    return False


if __name__ == '__main__':
    pass
