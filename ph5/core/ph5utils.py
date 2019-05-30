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
from obspy.geodetics import locations2degrees
from ph5.core.timedoy import epoch2passcal, passcal2epoch, TimeDOY, TimeError
import time
import re

PROG_VERSION = "2019.81"


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


"""
===============
Utility methods
===============
"""


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


def is_str_unicode(value):
    """
    Checks if value is a instance of str or unicode
    :param value: The str value to check
    :type: str
    :returns: True if value is a str or unicode, otherwise False
    """
    if isinstance(value, (str, unicode)):
        return True
    else:
        return False


def is_pos_str_int(value, extra_symbols=''):
    """
    Checks if value is string representation of a positive int including
    wildcards.
    :param value:
    :type: str or None
    :param extra_symbols: comma separated list of additionally valid symbols.
    e.g. "*?-", '*' and '?' are treated as wildcards.
    :type: str
    :returns: True if value is a positive integer, otherwise False
    :type: Boolean
    """
    if is_str_unicode(value):
        try:
            # if any extra wildcards then include them in regex
            if extra_symbols:
                extra_symbols = ''.join(re.escape(s) for s in extra_symbols)
            re_str = r"(^[\d%s]+$)" % (extra_symbols)
            regex = re.compile(re_str)
            if re.match(regex, value):
                return True
        except ValueError:
            return False
    else:
        return False


def is_pos_str_float(value):
    """
    Checks if value is string representation of a positive float
    :param value:
    :type: str or None
    :returns: True if value is a positive float, otherwise False
    :type: Boolean
    """
    if is_str_unicode(value):
        try:
            a = float(value)
            # check if negative or alphabetic character (ie. NaN or Infinity)
            if a < 0 or value.isalpha():
                return False
            else:
                return True
        except ValueError:
            return False
    else:
        return False


def str_to_int(value, err_msg=None):
    """
    Converts str to int if str represents a valid int
    :param value:
    :type: str, int, or None
    :param err_msg: A optional error message to use
    :type: str
    :returns:
    :type: int or None
    """
    if is_str_unicode(value):
        try:
            a = int(value)
            if value.isalpha():  # (ie. NaN or Infinity)
                raise ValueError(err_msg)
            else:
                return a
        except ValueError:
            raise ValueError(err_msg)
    elif isinstance(value, int):
        return int(value)
    elif value is None:
        return None
    else:
        raise ValueError("str_to_int: Input value must be a string, int, or "
                         "None. Value was %s." % value)


def str_to_float(value, err_msg=None):
    """
    Converts str to float if str represents a valid float. If a float is
    entered, then the value is returned unchanged. A int will be cast as a
    float.
    :param value:
    :type: str, float, int, or None
    :param err_msg: A optional error message to use
    :type: str
    :returns:
    :type: float or None
    """
    if is_str_unicode(value):
        try:
            a = float(value)
            if value.isalpha():  # (ie. NaN or Infinity)
                raise ValueError(err_msg)
            else:
                return a
        except ValueError:
            raise ValueError(err_msg)
    elif isinstance(value, (float, int)):
        return float(value)
    elif value is None:
        return None
    else:
        raise ValueError("str_to_float - Input value must be a string, float "
                         "or None. Value was %s (%s)." % (value, type(value)))


def str_to_pos_int(value, err_msg=None):
    """
    Converts str to int if str represents a valid positive int.
    If a positive int is entered, then the value is returned unchanged.
    :param value:
    :type: str, int, or None
    :param err_msg: A optional error message to use
    :type: str
    :returns: int >= 0
    :type: str or None"""
    if is_str_unicode(value):
        if is_pos_str_int(value):
            return str_to_int(value, err_msg)
        else:
            raise ValueError(err_msg)
    elif isinstance(value, int):
        if value >= 0:
            return int(value)
        else:
            raise ValueError(err_msg)
    elif value is None:
        return None
    else:
        raise ValueError("str_to_pos_int = Input value must be a string, int, "
                         "or None. Value was %s." % value)


def str_to_pos_float(value, err_msg=None):
    """
    Converts str to float if str represents a valid positive float.
    If a positive float is entered, then the value is returned unchanged.
    A int will be cast as a float.
    :param value:
    :type: str, float, or None
    :param err_msg: A optional error message to use
    :type: str
    :returns: float >= 0 :type: float or None
    """
    if is_str_unicode(value):
        if is_pos_str_float(value):
            return str_to_float(value, err_msg)
        else:
            raise ValueError(err_msg)
    elif isinstance(value, (float, int)):
        if value >= 0:
            return float(value)
        else:
            raise ValueError(err_msg)
    elif value is None:
        return None
    else:
        raise ValueError("str_to_pos_float - Input value must be a string, "
                         "float, or None. Value was %s." % value)


def str_to_pos_int_str_list(value, err_msg=None, extra_symbols=''):
    """
    Validates a comma separated list of positive
    integer strings and trims whitespace. If a list object is entered the
    method assumes that the list was already validated.
    :param value:
    :type: str, list, or None
    :param err_msg: A optional error message to use
    :type: str
    :param extra_symbols: comma separated list of additionally valid symbols.
    e.g. "*?-", '*' and '?' are treated as wildcards.
    :type: str
    :returns: list of positive ints
    :type: list or None
    """
    if is_str_unicode(value):
        value_list = [c.strip() for c in value.strip().split(',')
                      if len(c) > 0]
        for v in value_list:
            if not is_pos_str_int(v, extra_symbols):
                raise ValueError(err_msg)
        return value_list
    elif isinstance(value, list):
        return value  # assume already parsed
    elif value is None:
        return None
    else:
        raise ValueError("str_to_pos_int_list - Input value must be a string. "
                         "Value was %s." % value)


def str_to_pos_float_str_list(value, err_msg=None):
    """
    Validates a comma separated list of positive
    float strings and trims whitespace. If a list object is entered the
    method assumes that the list was already validated.
    :param value:
    :type: str, list, or None
    :param err_msg: A optional error message to use
    :type: str
    :returns: list of positive flaots
    :type: list or None
    """
    if is_str_unicode(value):
        value_list = [c.strip() for c in value.strip().split(',')
                      if len(c) > 0]
        for v in value_list:
            if not is_pos_str_float(v):
                raise ValueError(err_msg)
        return value_list
    elif isinstance(value, list):
        return value  # assume already parsed
    elif value is None:
        return None
    else:
        raise ValueError("str_to_pos_float_list = Input value must be a "
                         "string. Value was %s." % value)


def str_to_boolean(value, err_msg=None):
    """
    Converts string "true" or "false" to equivalent boolean value.
    If a boolean value is entered, then the value is returned unchanged.
    :param value:
    :type: str, boolean, or None
    :param err_msg: A optional error message to use
    :type: str
    :returns: equivalent boolean value :type: boolean or None
    """
    if is_str_unicode(value):
        value = value.strip().upper()
        if value == "TRUE":
            return True
        elif value == "FALSE":
            return False
        else:
            raise ValueError(err_msg)
    if isinstance(value, bool):
        return value
    elif value is None:
        return None
    else:
        raise ValueError("str_to_boolean - value parameter must be a string "
                         "or boolean. Choose from 'True' or 'False'. "
                         "Value was %s." % value)


def set_to_code_str_list(code, min_code_length, max_code_length, err_msg=None,
                         extra_symbols=''):
    """
    Validates a comma separated list of SEED codes and removes whitespace.
    If a list object is entered the method assumes that the list was already
    validated.
    :param value: :type: str or None
    :param err_msg: A optional error message to use
    :type: str
    :param extra_symbols: comma separated list of additionally valid symbols.
    e.g. "*?-", '*' and '?' are treated as wildcards.
    :type: str
    :returns: list of SEED codes
    :type: list or None
    """
    if is_str_unicode(code):
        code_list = [c.strip() for c in code.strip(' ,').split(',')]
        if max_code_length > 0:
            if extra_symbols:
                extra_symbols = ''.join(re.escape(s) for s in extra_symbols)
            re_str = r"(^[\w%s]{%s,%s}$)" % (extra_symbols, min_code_length,
                                             max_code_length)
            regex = re.compile(re_str)
            for code in code_list:
                if re.match(regex, code):
                    pass
                else:
                    raise ValueError(err_msg)
            if code_list:
                code_list = ["" if code == "--" else code
                             for code in code_list]
                return code_list
            else:  # case where code_list is empty
                raise ValueError(err_msg)
        else:
            raise ValueError("set_to_code_str_list - "
                             "max_code_length must be > 0.")
    elif isinstance(code, list):
        return code  # assume already parsed
    elif code is None:
        return None
    else:
        raise ValueError("SEED code must be a str or unicode.")


"""
===============================================
Methods for parsing client input arguments
===============================================
"""


def parse_date(date_str):
    """
    Method for parsing date arguments
    :param date_str: String representation of a date or a datetime object.
    :type: str, datetime, or None
    :returns: A datetime object if date string matches accepted format,
    otherwise raises a ValueError.
    :type: datetime.datetime or None
    """
    if is_str_unicode(date_str):
        fmts = ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y:%j:%H:%M:%S.%f")
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
    elif date_str is None:
        return None
    else:
        raise ValueError("Unsupported data type. Date text must be a string "
                         "or unicode.")


def parse_ph5_reportnum(reportnum_code):
    """
    Method for parsing report number argument.
    :param reportnum_code: comma separated list of report numbers.
    If a list object is entered the method assumes that the list was already
    validated.
    :type: str, list, or None
    :returns: report number code
    :type: list or None
    """
    if is_str_unicode(reportnum_code):
        err_msg = 'Invalid report number code %s. ' % (reportnum_code) + \
            'Must match pattern [0-9][0-9]-[0-9][0-9][0-9].'
        regex = re.compile(r"(^[\d\?\*]+$)")
        code_list = [c.strip() for c in reportnum_code.strip().split(',')
                     if len(c) > 0]
        for code in code_list:
            if '-' in code:  # case for no wildcards or dash (-) and wildcards
                c1, c2 = code.split('-', 1)
                if (re.match(regex, c1) and len(c1) <= 2
                    and (len(c1) == 2 or '*' in c1)) and \
                   (re.match(regex, c2) and len(c2) <= 3
                        and (len(c2) == 3 or '*' in c2)):
                    pass
                else:
                    raise ValueError(err_msg)
            elif '*' in code and len(code) <= 6:  # case for wildcards
                if re.match(regex, code) and len(code) <= 6:
                    split_code = ''
                    if (len(code) > 3
                            and ('?' in code) and ('*' in code)):  # e.g. 13?*
                        # dash potentially replaced with ?
                        split_code = code.split('?')
                    elif (len(code) > 3 and ('*' in code)):  # e.g. *005
                        split_code = code.split('*')
                    for c1 in split_code:
                        # the largest part of a report num can be 3 characters
                        if len(c1) > 3:
                            raise ValueError(err_msg)
                else:
                    raise ValueError(err_msg)
            else:
                raise ValueError(err_msg)
        if code_list:
            return code_list
        else:  # case where code_list is empty
            raise ValueError(err_msg)
    elif isinstance(reportnum_code, list):
        return reportnum_code  # assume already parsed
    elif reportnum_code is None:
        return None
    else:
        raise ValueError("Unsupported data type. Report-num code must be a "
                         "string or unicode.")


def parse_ph5_longitude(lon):
    """
    Method for parsing min/max longitude argument, if possible
    (-180 <= lon <= 180)
    :param lon: longitude
    :type: str, numeric, or None
    :returns: min or longitude
    :type: float or None
    """
    err_msg = ("Invalid longitude: (%s) must be a float in "
               "the range of -180.0 to 180.0" % (lon))
    longitude = str_to_float(lon, err_msg)
    if longitude >= -180 and longitude <= 180:
        return longitude
    elif longitude is None:
        return None
    else:
        raise ValueError(err_msg)


def parse_ph5_latitude(lat):
    """
    Method for parsing min/max latitude argument,
    if possible (-90 <= lat <= 90)
    :param lat: latitude
    :type: str, numeric, or None
    :returns: min or max latitude
    :type: float or None
    """
    err_msg = ("Invalid latitude: (%s) must be a float in "
               "the range of -90.0 to 90.0" % (lat))
    latitude = str_to_float(lat, err_msg)
    if latitude >= -90 and latitude <= 90:
        return latitude
    elif latitude is None:
        return None
    else:
        raise ValueError(err_msg)


def parse_radius(radius):
    """
    Method for parsing min/max radius argument
    :param radius: point radius
    :type: str, numeric, or None
    :returns: min or max radius
    :type: float or None
    """
    err_msg = "Invalid radius: (%s) must be a positive float." % (radius)
    radius = str_to_float(radius, err_msg)
    if radius >= 0:
        return radius
    elif radius is None:
        return None
    else:
        raise ValueError(err_msg)


def parse_ph5_decimation(decimation_factor):
    """
    Method for parsing decimation factor argument.
    :param decimation_factor: decimation factor
    :type: str, int, or None
    :returns: decimation factor
    :type: int or None
    """
    err_msg = ("Invalid decimation factor - '%s'. "
               "Must be a positive integer." % (decimation_factor))
    return str_to_pos_int(decimation_factor, err_msg)


def parse_ph5_reduction(reduction):
    """
    Method for parsing reduction velocity argument.
    :param reduction: reduction velocity
    :type: str, numeric, or None
    :returns: reduction velocity
    :type: float or None
    """
    err_msg = "Invalid reduction velocity value. %s" % (reduction)
    return str_to_float(reduction, err_msg)


def parse_ph5_offset(offset):
    """
    Method for parsing offset argument.
    :param offset: offset in seconds
    :type: str, numeric, or None
    :returns: time offset
    :type: float or None
    """
    err_msg = "Invalid offset value. %s" % (offset)
    return str_to_float(offset, err_msg)


def parse_ph5_length(length):
    """
    Method for parsing length argument.
    :param length: length
    :type: str, numeric, or None
    :returns: length value as a float
    :type: float or None
    """
    err_msg = "Invalid length value. %s" % (length)
    return str_to_pos_float(length, err_msg)


def parse_ph5_arrayid(arrayid):
    """
    Method for parsing array-id argument.
    :param arrayid: comma separated list of array-ids
    :type: str, list, or None
    :returns: comma separated list of array-ids
    :type: list or None
    """
    err_msg = "Invalid array-id value. %s" % (arrayid)
    return str_to_pos_int_str_list(arrayid, err_msg, "?*")


def parse_ph5_componentid(componentid):
    """
    Method for parsing component-id argument.
    :param componentid: comma separated list of component-ids
    :type: str, list, or None
    :returns: Comma separated list of component-ids
    :type: list or None
    """
    err_msg = "Invalid component-id value. %s" % (componentid)
    return str_to_pos_int_str_list(componentid, err_msg, "?*")


def parse_ph5_shotid(shotid):
    """
    Method for parsing shot-id argument.
    :param shotid: comma separated list of shot-ids
    :type: str, list, or None
    :returns: comma separated list of shot-ids
    :type: list or None
    """
    err_msg = "Invalid shot-id value. %s" % (shotid)
    return str_to_pos_int_str_list(shotid, err_msg, "?*")


def parse_ph5_receiverid(receiverid):
    """
    Method for parsing receiver-id argument.
    :param receiverid: comma separated list of receiver-ids
    :type: str, list, or None
    :returns: comma separated list of receiver-ids
    :type: list or None
    """
    err_msg = "Invalid receiver-id value. %s" % (receiverid)
    return str_to_pos_int_str_list(receiverid, err_msg, "?*")


def parse_ph5_shotline(shotline):
    """
    Method for parsing shotline argument.
    :param shotid: shotline string
    :type: str or None
    :returns: shotline :type: str or None
    """
    if is_str_unicode(shotline):
        err_msg = "Invalid shotline value. %s" % (shotline)
        if is_pos_str_int(shotline):
            return shotline
        else:
            raise ValueError(err_msg)
    elif shotline is None:
        return None
    else:
        raise ValueError("Shotline must be a String or None type.")


def parse_ph5_shotline_with_wildcards(shotline):
    """
    Method for parsing shotline argument.
    :param shotid: shotline string
    :type: str or None
    :returns: shotline :type: list or None
    """
    err_msg = "Invalid shotline value. %s" % (shotline)
    return str_to_pos_int_str_list(shotline, err_msg, "?*")


def parse_seed_network(network_code):
    """
    Method for parsing SEED network code argument.
    :param network_code: comma separated list of SEED network codes
    :type: str, list, or None
    :returns: SEED network code :type: list or None
    """
    err_msg = "Invalid SEED network code %s." % network_code
    return set_to_code_str_list(network_code, 1, 2, err_msg, "?*")


def parse_seed_station(station_code):
    """
    Method for parsing SEED station code argument.
    :param station_code: comma separated list of SEED station codes
    :type: str, list, or None
    :returns: SEED station code :type: list or None
    """
    err_msg = "Invalid SEED station code %s." % station_code
    return set_to_code_str_list(station_code, 1, 5, err_msg, "?*")


def parse_seed_location(location_code):
    """
    Method for parsing SEED location code argument.
    :param location_code: comma separated list of SEED location codes
    :type: str, list, or None
    :returns: SEED location code :type: list or None
    """
    err_msg = "Invalid SEED location code %s." % location_code
    return set_to_code_str_list(location_code, 0, 2, err_msg, "?*-")


def parse_seed_channel(channel_code):
    """
    Method for parsing SEED channel code argument.
    :param channel_code: comma separated list of SEED channel codes
    :type: str, list, or None
    :returns: SEED channel code :type: list or None
    """
    err_msg = "Invalid SEED channel code %s." % channel_code
    return set_to_code_str_list(channel_code, 1, 3, err_msg, "?*")
