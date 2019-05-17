'''
A collection of common methods for ph5toms.py, ph5tostationxml.py and
ph5toexml.py.
'''
################################################################
#
# modification
# version: 2019.032
# author: Lan Dam
# add inday_breakup() function

import fnmatch
from datetime import datetime, timedelta
from ph5.core.timedoy import epoch2passcal, passcal2epoch, TimeDOY, TimeError
import time

PROG_VERSION = "2019.137"


class PH5Response(object):
    def __init__(self, sensor_keys, datalogger_keys,
                 response, n_i=None):
        self.sensor_keys = sensor_keys
        self.datalogger_keys = datalogger_keys
        self.response = response
        self.n_i = n_i


class PH5ResponseManager(object):

    def __init__(self):
        self.responses = []

    def add_response(self, sensor_keys, datalogger_keys,
                     response, n_i=None):
        self.responses.append(
                        PH5Response(sensor_keys, datalogger_keys,
                                    response, n_i)
                    )

    def get_response(self, sensor_keys, datalogger_keys):
        for ph5_resp in self.responses:
            if set(sensor_keys) == set(ph5_resp.sensor_keys) and \
               set(datalogger_keys) == set(ph5_resp.datalogger_keys):
                return ph5_resp.response

    def is_already_requested(self, sensor_keys, datalogger_keys,
                             inresponse=None):
        for response in self.responses:
            if inresponse:
                if set(sensor_keys) == set(response.sensor_keys) and \
                   set(datalogger_keys) == set(response.datalogger_keys) and \
                        inresponse == response.response:
                    return True
            else:
                if set(sensor_keys) == set(response.sensor_keys) and \
                   set(datalogger_keys) == set(response.datalogger_keys):
                    return True

        return False

    def get_n_i(self, sensor_keys, datalogger_keys):
        for ph5_resp in self.responses:
            if set(sensor_keys) == set(ph5_resp.sensor_keys) and \
               set(datalogger_keys) == set(ph5_resp.datalogger_keys):
                return ph5_resp.n_i


def does_pattern_exists(patterns_list, value):
    """
    Checks a list of patterns against a value.
    :param: patterns_list : A list of regular glob expression strings
    :type: str
    :returns: Returns True if any of the patterns match the value,
        False otherwise.
    :type: boolean
    """
    for pattern in patterns_list:
        if fnmatch.fnmatch(str(value), str(pattern)):
            return True
    return False


def is_radial_intersection(point_lat, point_lon,
                           minradius, maxradius,
                           latitude, longitude):
    """
    Checks if there is a radial intersection between a point radius boundary
    and a latitude/longitude point.
    :param: point_lat : the latitude of the point radius boundary :type: float
    :param: point_lon : the longitude of the point radius boundary :type: float
    :param: minradius : the minimum radius boundary :type: float
    :param: maxradius : the maximum radius boundary :type: float
    :param: latitude : the latitude of the point to check :type: float
    :param: longitude : the longitude of the point to check :type: float
    """
    from obspy.geodetics import locations2degrees
    if minradius is not None or maxradius is not None or \
       point_lat is not None or point_lon is not None:
        # min radius default to 0.0
        if not minradius:
            minradius = 0.0
        # make max radius default to min radius when not defined
        if not maxradius:
            maxradius = minradius
        # latitude and longitude default to 0.0 when not defined
        if not point_lat:
            point_lat = 0.0
        if not point_lon:
            point_lon = 0.0
        dist = locations2degrees(latitude, longitude, point_lat, point_lon)
        if dist < minradius:
            return False
        elif dist > maxradius:
            return False
        else:
            return True
    else:
        return True


def is_rect_intersection(minlat, maxlat, minlon, maxlon, latitude, longitude):
    """
    Checks if there is a radial intersection between a point radius boundary
    and a latitude/longitude point.
    :param: minlat : the minimum rectangular latitude :type: float
    :param: maxlat : the maximum rectangular latitude :type: float
    :param: minlon : the minimum rectangular longitude :type: float
    :param: maxlon : the maximum rectangular longitude :type: float
    :param: latitude : the latitude of the point to check :type: float
    :param: longitude : the longitude of the point to check :type: float
    """
    if minlat is not None and float(
            minlat) > float(latitude):
        return False
    elif minlon is not None and float(
            minlon) > float(longitude):
        return False
    elif maxlat is not None and float(
            maxlat) < float(latitude):
        return False
    elif maxlon is not None and float(
            maxlon) < float(longitude):
        return False
    else:
        return True


def datestring_to_epoch(date_str):
    if isinstance(date_str, (str, unicode)):
        dt = datestring_to_datetime(date_str)
        return (dt - datetime.fromtimestamp(0)).total_seconds()
    elif isinstance(date_str, (float, int)):
        return date_str  # already a date
    else:
        raise ValueError("Got {0} expected str or unicode.".format(
            type(date_str)))


def datestring_to_datetime(date_str):
    """
    Converts a FDSN or PASSCAL date string to a datetime.datetime object
    :param: date_str
    :type: str
    :returns: datetime equivalent to string
    :type: datetime
    """
    if isinstance(date_str, (str, unicode)):
        fmts = ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y:%j:%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")
        for fmt in fmts:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.year < 1900:
                    err_msg = ('Date %s is out of range. '
                               'Year must be year >= 1900.' % date_str)
                    raise ValueError(err_msg)
                return dt
            except ValueError:
                pass
        err_msg = 'Unsupported date format. %s' % date_str
        raise ValueError(err_msg)
    elif isinstance(date_str, datetime):
        return date_str  # already a date
    else:
        raise ValueError("Got {0} expected str or unicode.".format(
            type(date_str)))


def fdsntime_to_epoch(fdsn_time):
    """
    Converts a FDSN date string to epoch seconds
    :param: fdsn_time
    :type: str
    :returns: epoch seconds
    :type: float
    """
    from decimal import Decimal
    pattern = "%Y-%m-%dT%H:%M:%S.%f"
    mseconds = fdsn_time[fdsn_time.index(".") + len("."):]
    length = len(mseconds)
    divisor = float(Decimal(1).shift(length))
    epoch = float(
        time.mktime(
            time.strptime(
                fdsn_time, pattern)))+(float(mseconds)/divisor)
    if not epoch:
        raise ValueError("could not convert")
        return None
    return epoch


def doy_breakup(start_fepoch, length=86400):
    """
    Given a start time epoch returns a next days equivalent epoch time and the
    difference in seconds between the start and stop epoch times.
    :param: start_fepoch
    :type: float
    :returns: stop_fepoch : next days stop epoch :type: float
              seconds: difference in seconds between the start and end
              epoch times :type: float
    """
    if type(start_fepoch) is not float:
        if type(start_fepoch) is not int:
            raise ValueError('start_fepoch must be float or int')

    if type(length) is not float:
        if type(length) is not int:
            raise ValueError('length must be float or int')

    passcal_start = epoch2passcal(float(start_fepoch))
    start_passcal_list = passcal_start.split(":")
    start_year = start_passcal_list[0]
    start_doy = start_passcal_list[1]
    start_hour = start_passcal_list[2]
    start_minute = start_passcal_list[3]
    start_second = start_passcal_list[4]

    datestr = "{0}:{1}:{2}:{3}:{4}".format(start_year, start_doy,
                                           start_hour, start_minute,
                                           start_second)
    passcal_date = datetime.strptime(datestr, "%Y:%j:%H:%M:%S.%f")

    next_passcal_date = passcal_date + timedelta(seconds=length)
    next_passcal_date_str = next_passcal_date.strftime("%Y:%j:%H:%M:%S.%f")

    stop_fepoch = passcal2epoch(next_passcal_date_str, fepoch=True)
    seconds = stop_fepoch - start_fepoch
    return stop_fepoch, seconds


def inday_breakup(start_fepoch):
    """
    Given a start time epoch returns the midnight epoch time of that day
    and the difference in seconds between the start and midnight epoch times.
    :param: start_fepoch
    :type: float
    :returns: midnight_fepoch : midnight epoch :type: float
              seconds: difference in seconds between the start and end
              epoch times :type: float
    """
    passcal_start = epoch2passcal(float(start_fepoch))
    start_passcal_list = passcal_start.split(":")
    try:
        midnight = TimeDOY(year=int(start_passcal_list[0]),
                           doy=int(start_passcal_list[1]) + 1,
                           hour=0,
                           minute=0,
                           second=0,
                           microsecond=0)
    except TimeError:
        midnight = TimeDOY(year=int(start_passcal_list[0]) + 1,
                           doy=1,
                           hour=0,
                           minute=0,
                           second=0,
                           microsecond=0)

    midnight_fepoch = midnight.epoch()
    seconds = midnight_fepoch - start_fepoch
    return midnight_fepoch, seconds


def microsecs_to_sec(microsec):
    """
    Given mircoseonds returns seconds
    :param: microseconds
    :type: integer
    :returns: seconds :type: integer
    """
    if type(microsec) is not int:
        raise ValueError("microsec must be integer")
    return float(microsec) / 1000000


def roundSeconds(dateTimeObject):
    newDateTime = dateTimeObject

    if newDateTime.microsecond >= 500000:
        newDateTime = newDateTime + timedelta(seconds=1)

    return newDateTime.replace(microsecond=0)
