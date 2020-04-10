#!/usr/bin/env pnpython3
#
# Generate Station/Array, Event, Data info
#

import argparse
import json
import os
import os.path
import sys
import logging
import time
# This provides the base functionality
from ph5.core import experiment, timedoy

# Timeseries are stored as numpy arrays

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)

#
# These are to hold different parts of the meta-data
#
# /Experiment_g/Experiment_t
EXPERIMENT_T = None
# /Experiment_g/Sorts_g/Event_t
EVENT_T = {}
# /Experiment_g/Sorts_g/Offset_t
OFFSET_T = {}
# /Experiment_g/Sorts_g/Sort_t
SORT_T = None
# /Experiment_g/Responses_g/Response_t
RESPONSE_T = None
# /Experiment_g/Sorts_g/Array_t_[nnn]
ARRAY_T = {}
# /Experiment_g/Receivers_g/Das_g_[sn]/Das_t (keyed on DAS)
DAS_T = {}
# /Experiment_g/Receivers_g/Das_g_[sn]/Receiver_t (keyed on DAS)
RECEIVER_T = {}
# /Experiment_g/Receivers_g/Das_g_[sn]/SOH_a_[n]
# (keyed on DAS then by SOH_a_[n] name)
SOH_A = {}
# A list of Das_Groups that refers to Das_g_[sn]'s
DASS = {}
#
INDEX_T = {}

os.environ['TZ'] = 'UTM'
time.tzset()


#
# To hold table rows and keys
#


class Rows_Keys(object):
    __slots__ = ('rows', 'keys')

    def __init__(self, rows=None, keys=None):
        self.rows = rows
        self.keys = keys

    def set(self, rows=None, keys=None):
        if rows is not None:
            self.rows = rows
        if keys is not None:
            self.keys = keys


#
# To hold DAS sn and references to Das_g_[sn]
#


class Das_Groups(object):
    __slots__ = ('das', 'node')

    def __init__(self, das=None, node=None):
        self.das = das
        self.node = node


class Offset_Azimuth(object):
    __slots__ = ('offset', 'azimuth')

    def __init__(self, offset=None, azimuth=None):
        self.offset = offset
        self.azimuth = azimuth


#
# Read Command line arguments
#


def get_args():
    global PH5, PATH, DEBUG, RECEIVER_GEN, EVENT_GEN, DATA_GEN, DAS_SN,\
        EXPERIMENT_GEN

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = ("meta-data-gen --nickname=ph5-file-prefix "
                    "options")

    parser.description = ("Write info about receivers, events, or data.\n\n"
                          "Version: {0}".format(PROG_VERSION))

    parser.add_argument("-E", "--experiment", dest="experiment_gen",
                        help="Write info about experiment to stdout,"
                             "Experiment_t.json",
                        action="store_true", default=False)

    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)

    parser.add_argument("-p", "--path", dest="ph5_path",
                        help="Path to ph5 files.Defaults to current "
                             "directory.", default=".",
                        metavar="ph5_path")

    parser.add_argument("-r", "--receivers", dest="receiver_gen",
                        help="Write info about receivers to stdout,"
                             "Array_t_all.json",
                        action="store_true", default=False)

    parser.add_argument("-e", "--events", dest="event_gen",
                        help="Write info about events to stdout, Event_t.json",
                        action="store_true", default=False)

    parser.add_argument("-d", "--data", dest="data_gen",
                        help="Write info about data to stdout, Das_t_all.json",
                        action="store_true", default=False)

    parser.add_argument("--debug", dest="debug",
                        action="store_true", default=False)

    args = parser.parse_args()

    PH5 = args.ph5_file_prefix
    PATH = args.ph5_path
    DEBUG = args.debug
    RECEIVER_GEN = args.receiver_gen
    EVENT_GEN = args.event_gen
    DATA_GEN = args.data_gen
    EXPERIMENT_GEN = args.experiment_gen


#
# Initialize ph5 file
#


def initialize_ph5(editmode=False):
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5

    EX = experiment.ExperimentGroup(PATH, PH5)
    EX.ph5open(editmode)
    EX.initgroup()


#
# Print Rows_Keys
#


def debug_print(a):
    i = 1
    # Loop through table rows
    for r in a.rows:
        i += 1
        # Loop through each row column and print
        for k in a.keys:
            print k, "=>", r[k], ",",
        print


def info_print():
    import time
    global EX

    print "#\n#\t%s\tph5 version: %s\n#" % (
        time.ctime(time.time()), EX.version())


#
# Print Rows_Keys
#


def table_print(t, a):
    i = 0
    # Loop through table rows
    for r in a.rows:
        i += 1
        print "# Table row %d" % i
        # Print table name
        print t
        # Loop through each row column and print
        for k in a.keys:
            print "\t", k, "=", r[k]


def read_index_table():
    global EX, INDEX_T

    rows, keys = EX.ph5_g_receivers.read_index()
    INDEX_T = Rows_Keys(rows, keys)


def read_experiment_table():
    '''   Read /Experiment_g/Experiment_t   '''
    global EX, EXPERIMENT_T

    exp, exp_keys = EX.read_experiment()

    rowskeys = Rows_Keys(exp, exp_keys)

    EXPERIMENT_T = rowskeys


def read_event_table():
    '''   Read /Experiment_g/Sorts_g/Event_t   '''
    global EX, EVENT_T

    names = EX.ph5_g_sorts.namesEvent_t()
    for n in names:
        events, event_keys = EX.ph5_g_sorts.read_events(event_name=n)
        rowskeys = Rows_Keys(events, event_keys)
        EVENT_T[n] = rowskeys


def read_offset_table():
    '''   Read /Experinent_t/Sorts_g/Offset_t   '''
    global EX, OFFSET_T

    names = EX.ph5_g_sorts.namesOffset_t()
    for n in names:
        offsets, offset_keys = EX.ph5_g_sorts.read_offset(offset_name=n)
        rowskeys = Rows_Keys(offsets, offset_keys)
        OFFSET_T[n] = rowskeys


def read_sort_table():
    '''   Read /Experiment_t/Sorts_g/Sort_g   '''
    global EX, SORT_T

    sorts, sorts_keys = EX.ph5_g_sorts.read_sorts()

    rowskeys = Rows_Keys(sorts, sorts_keys)

    SORT_T = rowskeys


def read_sort_arrays():
    '''   Read /Experiment_t/Sorts_g/Array_t_[n]   '''
    global EX, ARRAY_T

    # We get a list of Array_t_[n] names here...
    # (these are also in Sort_t)
    names = EX.ph5_g_sorts.names()
    for n in names:
        arrays, array_keys = EX.ph5_g_sorts.read_arrays(n)

        rowskeys = Rows_Keys(arrays, array_keys)
        # We key this on the name since there can be multiple arrays
        ARRAY_T[n] = rowskeys


def read_response_table():
    '''   Read /Experiment_g/Respones_g/Response_t   '''
    global EX, RESPONSE_T

    response, response_keys = EX.ph5_g_responses.read_responses()

    rowskeys = Rows_Keys(response, response_keys)

    RESPONSE_T = rowskeys


# NOT USED


def read_receivers():
    '''   Read tables and arrays (except wiggles) in Das_g_[sn]   '''
    global EX, DAS_T, RECEIVER_T, DASS, SOH_A

    # Get references for all das groups keyed on das
    dasGroups = EX.ph5_g_receivers.alldas_g()
    dass = sorted(dasGroups.keys())
    # Sort by das sn
    for d in dass:
        # Get node reference
        g = dasGroups[d]
        dg = Das_Groups(d, g)
        # Save a master list for later
        DASS.append(dg)

        # Set the current das group
        EX.ph5_g_receivers.setcurrent(g)

        # Read /Experiment_g/Receivers_g/Das_g_[sn]/Das_t
        das, das_keys = EX.ph5_g_receivers.read_das()
        rowskeys = Rows_Keys(das, das_keys)
        DAS_T[d] = rowskeys

        # Read /Experiment_g/Receivers_g/Receiver_t
        receiver, receiver_keys = EX.ph5_g_receivers.read_receiver()
        rowskeys = Rows_Keys(receiver, receiver_keys)
        RECEIVER_T[d] = rowskeys

        # Read SOH file(s) for this das
        SOH_A[d] = EX.ph5_g_receivers.read_soh()


def read_das_groups():
    '''   Get das groups   '''
    global EX

    # Get references for all das groups keyed on das
    return EX.ph5_g_receivers.alldas_g()


def read_das_table(das):
    global EX, DASS

    das = "Das_g_{0}".format(das)
    if das in DASS:
        EX.ph5_g_receivers.setcurrent(DASS[das])
        das_r, das_keys = EX.ph5_g_receivers.read_das()
        return Rows_Keys(das_r, das_keys)
    else:
        return None


def strip_offset_t():
    global OFFSET_T, STATION_ID, EVENT_ID

    if STATION_ID is None and EVENT_ID is None:
        return

    tmp = []
    for o in OFFSET_T.rows:
        event_id = o['event_id_s']
        receiver_id = o['receiver_id_s']
        station_id = o['station_is_s']
        if STATION_ID is not None and EVENT_ID is not None:
            if event_id == EVENT_ID and receiver_id == STATION_ID:
                tmp.append(o)
        elif STATION_ID is None:
            if event_id == EVENT_ID:
                tmp.append(o)
        elif EVENT_ID is None:
            if station_id == STATION_ID:
                tmp.append(o)

    if tmp != []:
        OFFSET_T = Rows_Keys(tmp, OFFSET_T.keys)


def strip_array_t():
    global ARRAY_T, STATION_ID, DAS_SN

    if STATION_ID is None and DAS_SN is None:
        return

    keys = ARRAY_T.keys()
    for k in keys:
        tmp = []
        for a in ARRAY_T[k].rows:
            station_id = a['id_s']
            das_sn = a['das/serial_number_s']
            if STATION_ID is not None and DAS_SN is not None:
                if station_id == STATION_ID and das_sn == DAS_SN:
                    tmp.append(a)
            elif STATION_ID is None:
                if das_sn == DAS_SN:
                    tmp.append(a)
            elif DAS_SN is None:
                if station_id == STATION_ID:
                    tmp.append(a)

        if tmp != []:
            ARRAY_T[k] = Rows_Keys(tmp, ARRAY_T[k].keys)


def offset_t_sort(a, b):
    return cmp(a['offset/value_d'], b['offset/value_d'])


def order_station_by_offset():
    global SORTED_OFFSET

    SORTED_OFFSET = OFFSET_T.rows

    for o in SORTED_OFFSET:
        if o['azimuth/value_f'] < 0:
            o['offset/value_d'] = o['offset/value_d'] * -1.0

    SORTED_OFFSET.sort(offset_t_sort)


def key_array(array):
    ka = {}
    for a in array.rows:
        ka[a['id_s']] = a

    return ka


def build_array_from_offset(array):
    global SORTED_OFFSET
    sorted_array = []

    keyed_array = key_array(array)

    for o in SORTED_OFFSET:
        station = o['receiver_id_s']
        sorted_array.append(keyed_array[station])

    return Rows_Keys(sorted_array, array.keys)


def array_start_stop(ar):
    start = 2145916800
    stop = 0
    for a in ar.rows:
        if a['deploy_time/epoch_l'] < start:
            start = a['deploy_time/epoch_l']

        if a['pickup_time/epoch_l'] > stop:
            stop = a['pickup_time/epoch_l']

    return start, stop


def get_sample_rate(a, start, stop):
    Array_t = ARRAY_T[a].rows
    for array_t in Array_t:
        if 'sample_rate_i' in array_t and array_t['sample_rate_i'] != 0:
            return int(array_t['sample_rate_i'] /
                       float(array_t['sample_rate_multiplier_i']))

        das = array_t['das/serial_number_s']
        Das_t = read_das_table(das)
        if Das_t is None:
            continue
        for das_t in Das_t.rows:
            das_start = das_t['time/epoch_l']
            das_stop = das_start + das_t['sample_count_i'] / (
                    das_t['sample_rate_i'] /
                    float(das_t['sample_rate_multiplier_i']))

            # Start contained
            if das_start >= start and das_start <= stop:
                return int(das_t['sample_rate_i'] /
                           float(das_t['sample_rate_multiplier_i']))

            # Stop contained
            if das_stop >= start and das_stop <= stop:
                return int(das_t['sample_rate_i'] /
                           float(das_t['sample_rate_multiplier_i']))

    return 0


class _Data(object):
    __slots__ = ('das', 'first_sample', 'last_sample',
                 'first_epoch', 'last_epoch')

    def cough(self):
        RET = {}
        RET['Data'] = {'das': self.das, 'first_sample': self.first_sample,
                       'last_sample': self.last_sample,
                       'first_epoch': self.first_epoch,
                       'last_epoch': self.last_epoch}
        return RET


def write_data():
    global INDEX_T, DASS
    L = {}
    L['Data'] = []
    fh = sys.stdout

    dass = sorted(DASS.keys())
    for das_group in dass:
        for i in INDEX_T.rows:
            d = das_group[6:]
            if i['serial_number_s'] == d:
                try:
                    D = {'das': d,
                         'first_sample': timedoy.epoch2passcal(
                             i['start_time/epoch_l'] +
                             (i['start_time/micro_seconds_i'] / 1000000.)),
                         'last_sample': timedoy.epoch2passcal(
                             i['end_time/epoch_l'] +
                             (i['end_time/micro_seconds_i'] / 1000000.)),
                         'first_epoch': i['start_time/epoch_l'],
                         'last_epoch': i['end_time/epoch_l']}
                except timedoy.TimeError as e:
                    LOGGER.warning(e.message)
                    continue

                L['Data'].append(D)

    fh.write(json.dumps(L, sort_keys=True, indent=4))


def write_events():
    global EVENT_T

    L = {}
    L['Events'] = []
    fh = sys.stdout
    #
    shot_lines = EVENT_T.keys()
    for sl in shot_lines:
        events = []
        this_line = {'shot_line': str(sl[-3:])}
        for e in EVENT_T[sl].rows:
            pictime = timedoy.epoch2passcal(
                e['time/epoch_l'] + (e['time/micro_seconds_i'] / 1000000.))

            E = {'id': e['id_s'], 'time': pictime,
                 'lat': e['location/Y/value_d'],
                 'lon': e['location/X/value_d'],
                 'elev': e['location/Z/value_d'], 'mag': e['size/value_d'],
                 'depth': e['depth/value_d']}
            events.append(E)

        this_line['Events'] = events
        L['Events'].append(this_line)
        if L:
            fh.write(json.dumps(L, sort_keys=True, indent=4))


def write_arrays():
    global ARRAY_T

    fh = sys.stdout
    A = {}
    for k in ARRAY_T.keys():
        a = ARRAY_T[k]
        start, stop = array_start_stop(a)
        array_i = int(k[-3:])
        A[array_i] = (start, stop)

    arrays = sorted(ARRAY_T.keys())

    AR = {}
    AR['Arrays'] = []
    for a in arrays:
        stations = []
        start, stop = A[int(a[-3:])]
        sample_rate = get_sample_rate(a, start, stop)
        try:
            deploy_time = timedoy.epoch2passcal(start)
        except timedoy.TimeError as e:
            LOGGER.error("Time conversion error {0}".format(e.message))
            deploy_time = ""

        try:
            pickup_time = timedoy.epoch2passcal(stop)
        except timedoy.TimeError as e:
            LOGGER.error("Time conversion error {0}".format(e.message))
            pickup_time = ""

        this_array = {'array': str(a[-3:]), 'sample_rate': sample_rate,
                      'deploy_time': deploy_time, 'pickup_time': pickup_time,
                      'Stations': None}
        for e in ARRAY_T[a].rows:
            S = {'id': e['id_s'], 'das': e['das/serial_number_s'],
                 'lat': e['location/Y/value_d'],
                 'lon': e['location/X/value_d'],
                 'elev': e['location/Z/value_d'],
                 'chan': e['channel_number_i'],
                 'seed_band_code': e['seed_band_code_s'],
                 'seed_instrument_code': e['seed_instrument_code_s'],
                 'seed_orientation_code': e['seed_orientation_code_s'],
                 'seed_station_name': e['seed_station_name_s']}
            stations.append(S)

        this_array['Stations'] = stations
        AR['Arrays'].append(this_array)

    fh.write(json.dumps(AR, sort_keys=True, indent=4))


class _Experiment(object):
    __slots__ = ('id', 'netcode', 'nw', 'se', 'nickname',
                 'longname', 'PIs', 'institutions', 'summary')

    def cough(self):
        RET = {}
        RET['Experiment'] = {'ID': self.id, 'netcode': self.netcode,
                             'nickname': self.nickname,
                             'longname': self.longname,
                             'PIs': self.PIs,
                             'institutions': self.institutions,
                             'NWcorner': self.nw, 'SEcorner': self.se,
                             'summary': self.summary}
        return RET


def write_experiment():
    global EXPERIMENT_T
    L = []
    fh = sys.stdout
    e = None
    for e in EXPERIMENT_T.rows:
        pass

    if e:
        E = _Experiment()
        E.id = e['experiment_id_s']
        E.netcode = e['net_code_s']
        E.nickname = e['nickname_s']
        E.longname = e['longname_s']
        E.PIs = e['PIs_s']
        E.institutions = e['institutions_s']
        E.summary = e['summary_paragraph_s']
        E.nw = {'longitude': e['north_west_corner/X/value_d'],
                'latitude': e['north_west_corner/Y/value_d'],
                'elevation': e['north_west_corner/Z/value_d']}
        E.se = {'longitude': e['south_east_corner/X/value_d'],
                'latitude': e['south_east_corner/Y/value_d'],
                'elevation': e['south_east_corner/Z/value_d']}
        L.append(E)

    if L:
        fh.write(json.dumps(E.cough(), sort_keys=True, indent=4))


def main():
    global DATA_GEN, EVENT_GEN, RECEIVER_GEN, DASS

    get_args()

    initialize_ph5()

    if EXPERIMENT_GEN is True:
        read_experiment_table()
        write_experiment()
    if DATA_GEN is True:
        DASS = read_das_groups()
        if DASS:
            read_index_table()
            write_data()
    if EVENT_GEN is True:
        read_event_table()
        write_events()
    if RECEIVER_GEN is True:
        read_sort_arrays()
        write_arrays()

    EX.ph5close()


if __name__ == '__main__':
    main()
