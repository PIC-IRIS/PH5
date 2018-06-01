import argparse
import sys
import zipfile
import time
from uuid import uuid4
import cStringIO
from obspy.clients import fdsn
from obspy.io.sac import SACTrace
from obspy import UTCDateTime
from obspy.core.util import AttribDict
from obspy.geodetics.base import gps2dist_azimuth
from obspy.clients.fdsn.header import FDSNNoDataException
from ph5.core import parse_arguments
from ph5.clients.webservice_clients import common


"""
PH5 shot gather web service client.
"""

def process_arguments():

    sentinel_dict = {}

    def _preprocess_sysargv(argv):
        inputs = []
        for arg in argv[1:]:
            # handles case where values contain --, otherwise they will
            # be interpreted as arguments.
            if '--,' in arg or ',--' in arg or arg == '--':
                sentinel = uuid4().hex
                key = '%s' % sentinel
                sentinel_dict[key] = arg
                inputs.append(sentinel)
            else:
                inputs.append(arg)
        return inputs

    def _postprocess_sysargv(v):
        if v in sentinel_dict:
            return sentinel_dict.get(v)
        else:
            return v

    # define command line arguments
    parser = common.CustomArgParser(description=
                                    'Command line ph5 web service client for '
                                    'shot gathers.')
    required = parser.add_argument_group('required arguments')
    # required options
    required.add_argument('--network', '--net',
                          help="Select one or more network codes. Can be SEED "
                               "codes or data center defined codes. Accepts "
                               "wildcards and lists.",
                          required=True)
    required.add_argument('--starttime', '--start',
                          help="Limit to metadata describing channels "
                               "operating on or after the specified "
                               "start time.",
                          required=True)
    required.add_argument('--endtime', '--end',
                          help="Limit to metadata describing channels "
                               "operating on or before the specified "
                               "end time.",
                          required=True)
    required.add_argument('--shotid',
                          help="Specifies the shot (event) id for a request "
                               "by shot. Accepts a comma separated list if "
                               "requesting multiple events.",
                          required=True)
    required.add_argument('--shotline',
                          help="The shot line number that holds "
                               "the shots.",
                          required=True)

    # optional options
    parser.add_argument('--station', '--sta',
                          help="Select one or more SEED station codes. "
                               "Accepts wildcards and lists.",
                          default=None)
    parser.add_argument('--location', '--loc',
                          help="Select one or more SEED location identifier. "
                          "Use -- for 'Blank' location IDs (ID's containing 2 "
                          "spaces). Accepts wildcards and lists.",
                          type=_postprocess_sysargv, default=None)
    parser.add_argument('--channel', '--cha',
                          help="Select one or more SEED channel codes. "
                               "Accepts wildcards and lists.",
                          default=None)
    parser.add_argument('--arrayid', '--array',
                          help="Select one or more SEED channel codes. "
                               "Accepts wildcards and lists.",
                          default=None)
    parser.add_argument('--offset',
                          help="Time in seconds from shot time to start "
                               "the trace. Defaults to 60 seconds.",
                          default=60)

    parser.add_argument('--format',
                          default='plot',
                          help="Specify output format. Valid formats "
                               "include 'plot', 'mseed', 'sac'.")

    args = parser.parse_args(_preprocess_sysargv(sys.argv))
    return args


def shot_gather(arguments):
    network = common.list_to_csv(
                parse_arguments.parse_seed_network(arguments.network)
              )
    station = common.list_to_csv(
                parse_arguments.parse_seed_station(arguments.station)
              )
    location = common.list_to_csv(
                parse_arguments.parse_seed_location(arguments.location)
               )
    channel = common.list_to_csv(
                parse_arguments.parse_seed_channel(arguments.channel)
              )
    arrayid = common.list_to_csv(
                parse_arguments.parse_ph5_arrayid(arguments.arrayid)
              )
    # event constraints
    shotline = parse_arguments.parse_ph5_shotline(arguments.shotline)
    shotid = common.list_to_csv(
                parse_arguments.parse_ph5_shotid(arguments.shotid)
             )
    # time constraints
    starttime = parse_arguments.parse_date(arguments.starttime)
    endtime = parse_arguments.parse_date(arguments.endtime)
    offset = parse_arguments.parse_ph5_offset(arguments.offset)
    
    # Use ph5ws-station to retrieve station metadata
    sta_request = {
                   "network": network,
                   "station": station,
                   "location": location,
                   "channel": channel,
                   "arrayid": arrayid,
                   "starttime": starttime,
                   "endtime": endtime,
                   "level": "response"
                 }
    sta_request = {k: v for k, v in sta_request.items() if v is not None}
    STATIONWS = 'http://service.iris.edu/ph5ws/station/1'
    c = fdsn.client.Client(
                           service_mappings={
                               'station': STATIONWS
                           },
                           debug=True
                          )
    inventory = c.get_stations(**sta_request)

    # Use ph5ws-event to retrieve event metadata
    event_request = {
                       "catalog": network,
                       "shotline": shotline,
                       "shotid": shotid,
                       "starttime": starttime,
                       "endtime": endtime,
                    }
    event_request = {k: v for k, v in event_request.items() if v is not None}
    EVENTWS = 'http://service.iris.edu/ph5ws/event/1'
    c = fdsn.client.Client(
                           service_mappings={
                               'event': EVENTWS
                           },
                           debug=True
                          )
    events = c.get_events(**event_request)

    # Use ph5ws-dataselect to retrieve waveform data
    ds_request = {
                   "network": network if network else "*",
                   "station": station if station else "*",
                   "location": location if location else "*",
                   "channel": channel if channel else "*",
                   "starttime": events[0].origins[0].time,
                   "endtime": events[0].origins[0].time+float(offset),
                   "arrayid": arrayid
                 }
    ds_request = {k: v for k, v in ds_request.items() if v is not None}
    DATASELECTWS = 'http://service.iris.edu/ph5ws/dataselect/1'
    c = fdsn.client.Client(
                   service_mappings={
                       'dataselect': DATASELECTWS
                   },
                   debug=True
                  )
    # Request the first 60 seconds of data immediately following
    # the shot.
    stream = c.get_waveforms(**ds_request)
    stream.attach_response(inventory)

    # Compute the distance from the source for each channel
    for trace in stream:
        for station in inventory[0]:
            for channel in station:
                if trace.stats.station == station.code and \
                   trace.stats.location == channel.location_code and \
                   trace.stats.channel == channel.code:
                    trace.stats.coordinates = AttribDict(
                                                {'latitude':
                                                    channel.latitude,
                                                 'longitude':
                                                    channel.longitude})
                    trace.stats.distance = gps2dist_azimuth(
                                                events[0].origins[0].latitude,
                                                events[0].origins[0].longitude,
                                                channel.latitude,
                                                channel.longitude)[0]

    # Order the traces by distance from the source
    stream.traces.sort(key=lambda x: x.stats.distance)
    return stream


def main():
    try:
        arguments = process_arguments()

        out_format = arguments.format
        if out_format.upper() not in ["PLOT", "MSEED", "SAC"]:
            raise ValueError("Invalid format. Choose "
                             "from PLOT, MSEED, or SAC.")

        gather = shot_gather(arguments)

        # Plot the traces
        if out_format.upper() == "PLOT":
            common.plot(gather)
        elif out_format.upper() == "MSEED":
            common.write_mseed(gather, "shotgather")
        elif out_format.upper() == "SAC":
            common.write_sac(gather, "shotgather")
    except FDSNNoDataException as err:
        sys.stderr.write("{}\n".format(err.message))
    except ValueError as err:
        sys.stderr.write("{}\n".format(err.message))
    except Exception as err:
        sys.stderr.write("An unexpected error "
                         "occured:\n{}".format(err.message))


if __name__ == '__main__':
    main()
