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


"""
PH5 shot gather web service client.
"""


class CustomArgParser(argparse.ArgumentParser):

    def error(self, message):
        sys.stderr.write('Error: %s\n' % message)
        self.print_help()
        sys.exit(2)


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
    parser = CustomArgParser(description=
                 'Command line parser for '
                 'ph5 shot gather.')
    required = parser.add_argument_group('Required Arguments')
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
    optional = parser.add_argument_group('Optional Arguments')
    optional.add_argument('--station', '--sta',
                          help="Select one or more SEED station codes. "
                               "Accepts wildcards and lists.",
                          default="*")
    optional.add_argument('--location', '--loc',
                          help="Select one or more SEED location identifier. "
                          "Use -- for 'Blank' location IDs (ID's containing 2 "
                          "spaces). Accepts wildcards and lists.",
                          type=_postprocess_sysargv, default="*")
    optional.add_argument('--channel', '--cha',
                          help="Select one or more SEED channel codes. "
                               "Accepts wildcards and lists.",
                          default="*")
    optional.add_argument('--arrayid', '--array',
                          help="Select one or more SEED channel codes. "
                               "Accepts wildcards and lists.",
                          default="*")
    optional.add_argument('--offset',
                          help="Time in seconds from shot time to start "
                               "the trace. If no offset is ",
                          default=60)

    optional.add_argument('--format',
                          default='plot',
                          help="Specify output format. Valid formats "
                               "include 'plot', 'mseed', 'sac'.")

    args = parser.parse_args(_preprocess_sysargv(sys.argv))
    return args


def get_stream_size(stream):
    size = 0
    for trace in stream:
        size = size + len(trace.data)
    return size


def shot_gather(arguments):
    network = ",".join(parse_arguments.parse_seed_network(arguments.network))
    station = ",".join(parse_arguments.parse_seed_station(arguments.station))
    location = ",".join(
                        parse_arguments.parse_seed_location(arguments.location)
                       )
    channel = ",".join(parse_arguments.parse_seed_channel(arguments.channel))
    arrayid = ",".join(parse_arguments.parse_ph5_arrayid(arguments.arrayid))
    # event constraints
    shotline = parse_arguments.parse_ph5_shotline(arguments.shotline)
    shotid = ",".join(parse_arguments.parse_ph5_shotid(arguments.shotid))
    # time constraints
    starttime = parse_arguments.parse_date(arguments.starttime)
    endtime = parse_arguments.parse_date(arguments.endtime)
    offset = parse_arguments.parse_ph5_offset(arguments.offset)

    # Use ph5ws-station to retrieve ZI (15-016) station metadata
    STATIONWS = 'http://service.iris.edu/ph5ws/station/1'
    c = fdsn.client.Client(
                           service_mappings={
                               'station': STATIONWS
                           },
                           debug=True
                          )
    inventory = c.get_stations(network=network,
                               station=station,
                               location=location,
                               channel=channel,
                               arrayid=arrayid,
                               level='response',
                               starttime=UTCDateTime(starttime),
                               endtime=UTCDateTime(endtime))

    # Use ph5ws-event to retrieve ZI (15-016) event 5013 metadata
    EVENTWS = 'http://service.iris.edu/ph5ws/event/1'
    c = fdsn.client.Client(
                           service_mappings={
                               'event': EVENTWS
                           },
                           debug=True
                          )
    events = c.get_events(catalog=network,
                          starttime=UTCDateTime(starttime),
                          endtime=UTCDateTime(endtime),
                          shotline=shotline,
                          shotid=shotid)

    # Use ph5ws-dataselect to retrieve ZI (15-016) waveform data
    DATASELECTWS = 'http://service.iris.edu/ph5ws/dataselect/1'
    c = fdsn.client.Client(
                   service_mappings={
                       'dataselect': DATASELECTWS
                   },
                   debug=True
                  )
    # Request the first 60 seconds of data immediately following
    # the shot. The "by shot" ph5ws-dataselect request type
    # option can be used as an alternative to manual windowing.
    stream = c.get_waveforms(network=network,
                             station=station,
                             location=location,
                             channel=channel,
                             arrayid=arrayid,
                             starttime=events[0].origins[0].time,
                             endtime=events[0].origins[0].time+float(offset))
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


def plot(stream):
    stream.plot(type='section',
                dist_degree=False,
                size=(800, 1024))


def write_mseed(stream):
        mseed_fn = "ph5_shotgather_{}.mseed".format(UTCDateTime()
                                                    .strftime(
                                                        "%Y-%m-%dT%H_%M_%SZ"
                                                    ).upper())
        stream.write(mseed_fn,
                     format="MSEED")
        sys.stdout.write("Wrote {} bytes of timeseries"
                         " data to {}.".format(get_stream_size(stream),
                                               mseed_fn)
                         )


def write_sac(stream):
    zip_fn = "ph5_shotgather_{}.zip".format(UTCDateTime()
                                            .strftime(
                                                "%Y-%m-%dT%H_%M_%SZ"
                                            ).upper())
    zf = zipfile.ZipFile(zip_fn,
                         mode='w',
                         )
    try:
        for trace in stream:
            sac_fn = "{0}.{1}.{2}.{3}.{4}.sac".format(
                trace.stats.network,
                trace.stats.station,
                trace.stats.location,
                trace.stats.channel,
                trace.stats.starttime.strftime("%Y-%m-%dT%H%M%S.%f"))
            info = zipfile.ZipInfo(sac_fn,
                                   date_time=time.localtime(time.time()),
                                   )
            info.compress_type = zipfile.ZIP_DEFLATED
            stio = cStringIO.StringIO()
            sac = SACTrace.from_obspy_trace(trace)
            sac.write(stio)
            zf.writestr(info, stio.getvalue())
    finally:
        zf.close()
    sys.stdout.write("Wrote {} bytes of timeseries"
                     " data to {}.".format(get_stream_size(stream),
                                           zip_fn)
                     )


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
            plot(gather)
        elif out_format.upper() == "MSEED":
            write_mseed(gather)
        elif out_format.upper() == "SAC":
            write_sac(gather)
    except FDSNNoDataException as err:
        sys.stderr.write("{}\n".format(err.message))
    except ValueError as err:
        sys.stderr.write("{}\n".format(err.message))
    except Exception as err:
        sys.stderr.write("An unexpected error "
                         "occured:\n{}".format(err.message))


if __name__ == '__main__':
    main()
