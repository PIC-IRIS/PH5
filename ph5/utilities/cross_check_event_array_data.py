#!/usr/bin/env pnpython4
#
# Cross check Array_t_all.json, Event_t_all.json and Data.json.
# Simulates cutting data for each event for all stations, 65536 samples.
# The columns returned are:
#    Event table name
#    Event ID
#    Shot time
#    Cut end time
#    Array table name
#    Station ID
#    SEED station name
#    DAS SN
#    Component
#    First sample time in match window
#    Last sample time in match window
#    Gaps start and end time preceded by a tab (if any)
#
# Steve Azevedo, November 2016
#

import os
import sys
import logging
import json
from ph5.core import timedoy
from ph5.core.ph5api import is_in

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)
__version__ = PROG_VERSION


def get_args():
    global ARGS

    import argparse

    parser = argparse.ArgumentParser()

    parser.description = "Version: {0}. Cross check Event, Array, and Data."\
        .format(
            PROG_VERSION)

    parser.add_argument("--array_json", dest="array_json", required=True,
                        help="As returned by meta-data-gen -r.")
    parser.add_argument("--event_json", dest="event_json", required=True,
                        help="As returned by meta-data-gen -e.")
    parser.add_argument("--data_json", dest="data_json", required=True,
                        help="As returned by meta-data-gen -d.")
    parser.add_argument("--offset_secs", dest="offset_secs", type=float)
    parser.add_argument("--csv", action="store_true", dest="csv",
                        help="Separate output columns with ','\
                        instead of ' '.")
    parser.add_argument("--epoch", action="store_true", dest="epoch",
                        help="Times as epoch.")

    ARGS = parser.parse_args()


def _read_json(what):
    '''
       Load a json file.
          Input: A json file name to read
          Return: A 'structure' containing the contents of the json file
    '''
    with open(what) as fh:
        ret = json.load(fh)

    return ret


def read_json():
    '''
       Read all 3 json files.
          Inputs:
             ARGS.array_json
             ARGS.event_json
             ARGS.data_json
          Sets:
             ARRAY - A global object containing the contents of ARGS.array_json
             EVENT - A global object containing the contents of ARGS.event_json
             DATA - A global object containing the contents of ARGS.data_json
    '''
    global EVENT, ARRAY, DATA

    nope = []
    if not os.path.exists(ARGS.event_json):
        nope.append(ARGS.event_json)
    elif not os.path.exists(ARGS.array_json):
        nope.append(ARGS.array_json)
    elif not os.path.exists(ARGS.data_json):
        nope.append(ARGS.data_json)

    if len(nope) != 0:
        for n in nope:
            LOGGER.error("{0} not found.".format(n))
        sys.exit()

    EVENT = _read_json(ARGS.event_json)
    ARRAY = _read_json(ARGS.array_json)
    DATA = {}
    # Organize DATA by DAS SN for easy lookup
    D = _read_json(ARGS.data_json)
    Datas = D['Data']
    for Data in Datas:
        if Data['das'] not in DATA:
            DATA[Data['das']] = []
        yr, doy, hr, mn, sc = Data['first_sample'].split(':')
        window_start = timedoy.TimeDOY(year=int(yr),
                                       doy=int(doy),
                                       hour=int(hr),
                                       minute=int(mn),
                                       second=float(sc))
        yr, doy, hr, mn, sc = Data['last_sample'].split(':')
        window_stop = timedoy.TimeDOY(year=int(yr),
                                      doy=int(doy),
                                      hour=int(hr),
                                      minute=int(mn),
                                      second=float(sc))
        # Save window_start and window_stop as timedoy object
        Data['window_start'] = window_start
        Data['window_stop'] = window_stop
        DATA[Data['das']].append(Data)


def _is_in(das, shot_time, length, si):
    '''
       Test to see if data is available for a given das
       starting at shot_time for length.
       Check to see if there are any gaps greater than the sample interval.
       Inputs:
          das - The das serial number as a string
          shot_time - The shot time as a timedoy object
          length - Length is seconds as a float
          si - Sample interval in seconds
       Returns:
          A tuple containing:
          Match first sample time as a timedoy object, None if no match
          Match last sample time as a timedoy object, None if no match
          Gaps as a list of start and end times as timedoy objects
    '''
    if das in DATA:
        data = DATA[das]
    else:
        data = []
    shot_start_epoch = shot_time.epoch(fepoch=True)
    shot_stop_epoch = shot_start_epoch + length

    hits = []
    gaps = []

    for d in data:
        data_start_epoch = d['window_start'].epoch(fepoch=True)
        data_stop_epoch = d['window_stop'].epoch(fepoch=True)
        # Call ph5api.is_in
        if is_in(data_start_epoch, data_stop_epoch,
                 shot_start_epoch, shot_stop_epoch):
            hits.append(d)

    # Match no gaps
    if len(hits) == 1:
        return hits[0]['first_sample'], hits[0]['last_sample'], gaps
    # No match
    elif len(hits) == 0:
        return None, None, gaps
    # Match with gaps
    else:
        fs = None
        ls = None
        for h in hits:
            if fs is None:
                fs = h['first_sample']
            if ls is None:
                ls = h['last_sample']
            delta = abs(timedoy.passcal2epoch(
                h['last_sample']) - timedoy.passcal2epoch(ls))
            if delta > si:
                gaps.append((ls, h['last_sample']))

            ls = h['last_sample']

        return fs, ls, gaps


def process_all():
    '''
       Process through each shot line, shot, array, station,
       component (channel) and print matches to stdout
    '''
    Events = EVENT['Events']
    for Event in Events:
        shot_line = Event['shot_line']
        shot_line_name = "Event_t_{0:03d}".format(int(shot_line))
        for event in Event['Events']:
            yr, doy, hr, mn, sc = event['time'].split(':')
            shot_time = timedoy.TimeDOY(year=int(yr),
                                        doy=int(doy),
                                        hour=int(hr),
                                        minute=int(mn),
                                        second=float(sc))
            if ARGS.offset_secs:
                shot_time = shot_time + ARGS.offset_secs
            shot_id = event['id']
            Arrays = ARRAY['Arrays']
            for Array in Arrays:
                array_name = "Array_t_{0:03d}".format(int(Array['array']))
                sample_rate = Array['sample_rate']
                length = 65536. / sample_rate
                cut_end = shot_time + length
                for station in Array['Stations']:
                    chan = station['chan']
                    das = station['das']
                    station_id = station['id']
                    seed_id = station['seed_station_name']
                    fs, ls, gaps = _is_in(
                        das, shot_time, length, 1. / sample_rate)
                    if fs is None:
                        fs = 'NA'
                    if ls is None:
                        ls = 'NA'
                    if ARGS.epoch:
                        if fs != 'NA':
                            fs = str(timedoy.passcal2epoch(fs, fepoch=True))
                        if ls != 'NA':
                            ls = str(timedoy.passcal2epoch(ls, fepoch=True))
                        line = [shot_line_name,
                                shot_id,
                                str(shot_time.epoch(fepoch=True)),
                                str(cut_end.epoch(fepoch=True)),
                                array_name,
                                station_id,
                                seed_id,
                                das,
                                str(chan),
                                fs,
                                ls]
                    else:
                        line = [shot_line_name,
                                shot_id,
                                shot_time.getPasscalTime(ms=True),
                                cut_end.getPasscalTime(ms=True),
                                array_name,
                                station_id,
                                seed_id,
                                das,
                                str(chan),
                                fs,
                                ls]
                    if ARGS.csv:
                        print ','.join(line)
                    else:
                        print ' '.join(line)
                    if len(gaps) != 0:
                        for g in gaps:
                            print "\t", g[0], g[1]


def main():
    get_args()
    read_json()
    process_all()


if __name__ == "__main__":
    main()
