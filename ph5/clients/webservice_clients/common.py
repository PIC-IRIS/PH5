import cStringIO
import time
import zipfile
import sys
import cStringIO
from obspy.io.sac import SACTrace
import argparse
from obspy import UTCDateTime


class CustomArgParser(argparse.ArgumentParser):

    def error(self, message):
        sys.stderr.write('Error: %s\n' % message)
        self.print_help()
        sys.exit(2)


def get_stream_size(stream):
    size = 0
    for trace in stream:
        size = size + len(trace.data)
    return size


def list_to_csv(value):
    if isinstance(value, list):
        return ",".join(value)
    else:
        return None

def plot(stream):
    stream.plot(type='section',
                dist_degree=False,
                size=(800, 1024),
                alpha=0.6,
                color="#000000")

def write_mseed(stream, label):
        mseed_fn = "ph5_{}_{}.mseed".format(label,
                                            UTCDateTime().strftime(
                                                "%Y-%m-%dT%H_%M_%SZ"
                                            ).upper())
        stream.write(mseed_fn,
                     format="MSEED")
        sys.stdout.write("Wrote {} bytes of timeseries"
                         " data to {}.".format(get_stream_size(stream),
                                               mseed_fn)
                         )


def write_sac(stream, label):
    zip_fn = "ph5_{}_{}.zip".format(label,
                                    UTCDateTime().strftime(
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
