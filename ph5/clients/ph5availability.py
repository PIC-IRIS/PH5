# Derick Hess, Feb 2019

"""
Implements IRIS webservice style extent and query
for data availability in a PH5 archive.
"""

import os
import sys
import logging
import argparse
from ph5.core import ph5api

PROG_VERSION = '2019.49'
LOGGER = logging.getLogger(__name__)


class PH5AvailabilityError(Exception):
    """Exception raised when there is a problem with the request.
    :param: message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class PH5Availability(object):
    """
    Availability methods for Ph5 archive
    """

    def __init__(self, ph5API_object):
        """
        Initializes PH5Availability
        :type  :class core.ph5api
        :param object containg PH5 instance
        TODO: ADD ALL PARAMATERS NEEDED

        """

        self.ph5 = ph5API_object
        if not self.ph5.Array_t_names:
            self.ph5.read_array_t_names()
        return

    def get_nslc(self, station=None, location=None,
                 channel=None, starttime=None, endtime=None):
        """
        Get a list of tuples [(sta, loc, cha),...] containing information
        on what streams are included in PH5.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
            Wildcards '*' and '?' are supported.
        :type location: str
        :param location: Location code of requested data (e.g. "").
            Wildcards '*' and '?' are supported.
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
            Wildcards '*' and '?' are supported.
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :rtype: list(tuple(str, str, str, str))
        :returns: A list of tuples [(station, location, channel)...]
            containing information on what streams are included in PH5 archive.
        """
        nslc = []

        return nslc

    def get_availability_extent(self, station=None, location=None,
                                channel=None, starttime=None, endtime=None):
        """
        Get a list of tuples [(station, location, channel,
        earliest, latest)] containing data extent info for time series
        included in PH5.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
            Wildcards '*' and '?' are supported.
        :type location: str
        :param location: Location code of requested data (e.g. "").
            Wildcards '*' and '?' are supported.
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
            Wildcards '*' and '?' are supported.
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :rtype: list(tuple(str, str, str, str, float, float))
        :returns: A list of tuples [(station, location, channel,
            earliest, latest)...] containing data extent info for time series
            included in PH5 archive


        NOTE! ph5api as a get_extent() method that works on the channel level.
        Leverage this

        """
        availability_extents = []

        return availability_extents

    def get_availability(self, station=None, location=None,
                         channel=None, starttime=None, endtime=None,
                         include_sample_rate=False):
        """
        Get a list of tuples [(station, location, channel,
        starttime, endtime),...] containing data availability info for
        time series included in the ph5.
        If ``include_sample_rate=True``, then a tuple containing the sample
        rate [(sta, loc, cha, start, end, sample_rate),...] is returned.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
            Wildcards '*' and '?' are supported.
        :type location: str
        :param location: Location code of requested data (e.g. "").
            Wildcards '*' and '?' are supported.
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
            Wildcards '*' and '?' are supported.
        :type starttime: :class:`~obspy.core.utcdatetime.UTCDateTime`
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :type include_sample_rate: bool
        :param include_sample_rate: If ``include_sample_rate=True``, then
            a tuple containing the sample rate [(sta, loc, cha,
            start, end, sample_rate),...] is returned.
        :rtype: list(tuple(str, str, str, str, str))
        :returns: A list of tuples [( station, location, channel,
            earliest, latest)...] representing contiguous time spans for
            selected channels and time ranges.

        NOTE! ph5api as a get_availability()
        method that works on the channel level. Leverage this
        """
        availability = []
        return availability

    def get_availability_percentage(self, station,
                                    location, channel,
                                    starttime, endtime):
        """
        Get percentage of available data.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
        :type location: str
        :param location: Location code of requested data (e.g. "").
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :rtype: tuple(float, int)
        :returns: Tuple of percentage of available data (``0.0`` to ``1.0``)
            and number of gaps/overlaps.
        """
        return

    def has_data(self, station=None, location=None,
                 channel=None, starttime=None, endtime=None):
        """
        Return whether there is data for a specified station,
        location, channel, starttime, and endtime combination.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
            Wildcards '*' and '?' are supported.
        :type location: str
        :param location: Location code of requested data (e.g. "").
            Wildcards '*' and '?' are supported.
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
            Wildcards '*' and '?' are supported.
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :rtype: bool
        :returns: Returns ``True`` if there is data in Ph5 for a given
            station, location, channel, starttime, endtime.
        """
        return


def get_args():
    """
    Parses command line arguments and returns arg_parse object
    :rtype: :class argparse
    :returns: Returns arge parse class object

    TODO: ADD ALL COMMAND LINE ARGUMENTS NEEDED

    """

    parser = argparse.ArgumentParser(
        description='Get data availability form PH5',
        usage='Version: {0} ph5availability '
              '--nickname="Master_PH5_file" [options]'.format(PROG_VERSION))
    parser.add_argument(
        "-n", "--nickname", action="store",
        type=str, metavar="nickname", default="master.ph5")

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    parser.add_argument(
        "-s", "--starttime", action="store",
        type=str, dest="start_time", metavar="start_time",
        help="Time formats are YYYY:DOY:HH:MM:SS.ss or YYYY-mm-ddTHH:MM:SS.ss")

    parser.add_argument(
        "-t", "--stoptime", action="store",
        type=str, dest="stop_time", metavar="stop_time",
        help="Time formats are YYYY:DOY:HH:MM:SS.ss or YYYY-mm-ddTHH:MM:SS.ss")

    parser.add_argument(
        "--station", action="store", dest="sta_list",
        help="Comma separated list of SEED station id's",
        metavar="sta_list", type=str, default=[])

    parser.add_argument(
        "--station_id", action="store", dest="sta_id_list",
        help="Comma separated list of PH5 station id's",
        metavar="sta_id_list", type=str, default=[])

    parser.add_argument(
        "--channel", action="store",
        type=str, dest="channel",
        help="Comma separated list of SEED channels to extract",
        metavar="channel",
        default=[])

    parser.add_argument(
        "-c", "--component", action="store",
        type=str, dest="component",
        help="Comma separated list of channel numbers to extract",
        metavar="component",
        default=[])

    parser.add_argument(
        "-F", "-f", "--format", action="store", dest="format",
        help="text,sync,geocsv,json",
        metavar="format", type=str, default="text")

    the_args = parser.parse_args()
    return the_args


def main():
    """
    Main method for use for command line program
    """
    args = get_args()

    if args.nickname[-3:] == 'ph5':
        ph5file = os.path.join(args.ph5path, args.nickname)
    else:
        ph5file = os.path.join(args.ph5path, args.nickname + '.ph5')
        args.nickname += '.ph5'

    if not os.path.exists(ph5file):
        LOGGER.error("{0} not found.\n".format(ph5file))
        sys.exit(-1)
    try:
        ph5API_object = ph5api.PH5(path=args.ph5path, nickname=args.nickname)
        availability = PH5Availability(ph5API_object)
        availability = availability
        # stuff here

        ph5API_object.close()

    except ph5api.APIError as err:
        LOGGER.error(err)
    except PH5AvailabilityError as err:
        LOGGER.error(err)
    except Exception as e:
        LOGGER.error(e)


if __name__ == '__main__':
    main()
