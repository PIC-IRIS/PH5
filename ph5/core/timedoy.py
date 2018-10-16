#!/usr/bin/env pnpython3
#
# Simplified time handling
#
# Steve Azevedo, July 2006
#

import time
import os
import math
import exceptions

from datetime import datetime, tzinfo, timedelta

PROG_VERSION = '2016.335 Developmental'

DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31, 31)
DAYS_IN_MONTH_LEAP = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31, 31)

os.environ['TZ'] = 'UTC'
time.tzset()


class TimeError (exceptions.Exception):
    pass


class UTC(tzinfo):
    """   UTC   """

    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return timedelta(0)


class TimeDOY (object):
    '''
       Time conversions involving day of year
       Input:
             year, month, day, [hour, minute, second, microsecond]
             year, doy, [hour, minute, second, microsecond]
             epoch, [microsecond]
             fepoch
    '''

    def __init__(self,
                 year=None,
                 month=None,
                 day=None,
                 hour=0,
                 minute=0,
                 second=0,
                 microsecond=0,
                 doy=None,
                 epoch=None,
                 dtobject=None):

        if isinstance(second, float):
            f, i = math.modf(second)
            second = int(i)
            microsecond += int(f * 1000000.)

        if isinstance(epoch, float):
            f, i = math.modf(epoch)
            epoch = int(i)
            microsecond += int(f * 1000000.)

        if epoch is not None:
            try:
                o = datetime.fromtimestamp(epoch, tz=UTC())
                year = o.year
                month = o.month
                day = o.day
                hour = o.hour
                minute = o.minute
                second = o.second
            except Exception as e:
                raise TimeError(
                    "Value error for epoch {0}\n{1}".format(epoch, e.message))

        if doy is not None and year is not None:
            month, day = self.getMonthDay(year, doy)

        if dtobject:
            self.dtobject = dtobject
        else:
            if not inrange(year, 1970, 2053):
                raise TimeError(
                    "Value for year, {0}, is out of range!".format(year))
            if not inrange(month, 1, 12):
                raise TimeError(
                    "Value for month, {0}, out of range!".format(month))
            if not inrange(day, 1, 31):
                raise TimeError(
                    "Value for day, {0}, out of range!".format(day))
            if not inrange(hour, 0, 23):
                raise TimeError(
                    "Value for hour, {0}, out of range!".format(hour))
            if not inrange(minute, 0, 59):
                raise TimeError(
                    "Value for minute, {0}, out of range!".format(minute))
            if not inrange(second, 0, 59):
                raise TimeError(
                    "Value for second, {0}, out of range!".format(second))
            if not inrange(microsecond, 0, 1000000):
                raise TimeError(
                    "Value for microsecond, {0}, out of range!"
                    .format(microsecond))

            self.dtobject = datetime(
                year, month, day, hour, minute, second, microsecond, UTC())

    def __repr__(self):
        return str(self.dtobject)

    def __sub__(self, other):
        '''   Subtract seconds from self.  '''
        dt = self.dtobject - timedelta(0, other)
        return TimeDOY(dtobject=dt)

    def __rsub__(self, other):
        '''   Subtract seconds from self.  '''
        dt = self.dtobject - timedelta(0, other)
        return TimeDOY(dtobject=dt)

    def __radd__(self, other):
        '''   Add seconds to self   '''
        dt = self.dtobject + timedelta(0, other)
        return TimeDOY(dtobject=dt)

    def __add__(self, other):
        '''   Add seconds to self   '''
        dt = self.dtobject + timedelta(0, other)
        return TimeDOY(dtobject=dt)

    def is_leap_year(self, year):
        '''   Aloysius Lilius   '''
        return (year % 4 == 0 and year % 100 != 0 or year % 400 == 0)

    def getMonthDay(self, year, doy):
        '''   Get month and day of month given year and day of year   '''
        if self.is_leap_year(year):
            days_in_month = DAYS_IN_MONTH_LEAP
        else:
            days_in_month = DAYS_IN_MONTH

        totalDays = 0
        month = 0
        day = 0
        for i in range(13):
            totalDays = totalDays + days_in_month[i]
            if totalDays > doy:
                totalDays = totalDays - days_in_month[i]
                month = i + 1
                day = doy - totalDays
                if day == 0:
                    day = days_in_month[i - 1]
                    month = month - 1
                break

        if not inrange(month, 1, 12):
            raise TimeError(
                "Value for month, {0}, out of range!".format(month))

        if not inrange(day, 1, 31):
            raise TimeError("Value for day, {0}, out of range!".format(day))

        return (month, day)

    def doy(self):
        '''   Day Of Year   '''
        jd = self.dtobject.timetuple()[7]

        if not inrange(jd, 1, 366):
            raise TimeError(
                "Value for day of year, {0}, out of range!".format(jd))

        return jd

    def epoch(self, fepoch=False):
        '''   Represented as UNIX epoch time   '''
        e = time.mktime(self.dtobject.timetuple())
        if fepoch is False:
            return int(e)
        else:
            return e + self.second()

    def microsecond(self):
        return self.dtobject.microsecond

    def millisecond(self):
        return self.dtobject.microsecond / 1000.

    def second(self):
        return self.dtobject.microsecond / 1000000.

    def getPasscalTime(self, sep=':', ms=False):
        '''   Time string in PASSCAL time
               YYYY:JJJ:HH:MM:SS.sss
        '''
        yr = self.dtobject.year
        self.dtobject.day
        hr = self.dtobject.hour
        mn = self.dtobject.minute
        sc = self.dtobject.second

        if ms:
            ret = "%4d:%03d:%02d:%02d:%06.3f" % (
                yr, self.doy(), hr, mn, sc + self.second())
        else:
            ret = "%4d:%03d:%02d:%02d:%02d" % (yr, self.doy(), hr, mn, sc)

        if sep != ':':
            ret = ret.replace(':', sep)

        return ret

    def getFdsnTime(self):
        '''   YYYY-MM-DDTHH:MM:SS   '''
        yr = self.dtobject.year
        mo = self.dtobject.month
        da = self.dtobject.day
        hr = self.dtobject.hour
        mn = self.dtobject.minute
        sc = self.dtobject.second
        sc = sc + self.second()

        return "{0:4d}-{1:02d}-{2:02d}T{3:02d}:{4:02d}:{5:09.6f}".format(
            yr, mo, da, hr, mn, sc)

    def getISOTime(self, sep=' '):
        '''   ISO time format   '''
        return self.dtobject.isoformat(sep=sep)

    def getCTime(self):
        '''   ctime as in time.ctime   '''
        return time.ctime(self.epoch())


def UTCDateTime2tdoy(udt):
    ttuple = udt.timetuple()
    ms = udt._get_microsecond()
    tdoy = TimeDOY(year=ttuple.tm_year,
                   month=ttuple.tm_mon,
                   day=ttuple.tm_mday,
                   hour=ttuple.tm_hour,
                   minute=ttuple.tm_min,
                   second=ttuple.tm_sec,
                   microsecond=ms)

    return tdoy


def timecorrect(tdoy, ms):
    '''
       Apply time correction in milliseconds
    '''
    try:
        return TimeDOY(dtobject=tdoy.dtobject + timedelta(0, 0, 0, ms))
    except Exception as e:
        print e.message
        return tdoy


def delta(tdoy1, tdoy2):
    '''
       Subtract TimeDOY object 1 from TimeDOY object 2 and return seconds
    '''
    d = tdoy2.dtobject - tdoy1.dtobject

    return (d.days * 86400.) + d.seconds + (d.microseconds / 1000.)


def compare(tdoy1, tdoy2):
    '''
       cmp TimeDOY1 to TimeDOY2
    '''
    d = delta(tdoy1, tdoy2)
    if d > 0:
        return -1
    elif d < 0:
        return 1
    else:
        return 0


def yrdoyhrmnsc2epoch(yr, jd, hr, mn, sc, us=0, fepoch=False):
    '''
       Convert year, doy, hour, minute, second, [microsecond]
       to epoch.
    '''
    tdoy = TimeDOY(year=yr,
                   hour=hr,
                   minute=mn,
                   second=sc,
                   microsecond=us,
                   doy=jd)

    return tdoy.epoch(fepoch=fepoch)


def fdsn2epoch(fdsn, fepoch=False):
    '''
       Convert YYYY-MM-DDTHH:MM:SS.ssssss to epoch
    '''
    try:
        ddate, ttime = fdsn.split('T')
        flds = ddate.split('-')
        yr, mo, da = map(int, flds)
        flds = ttime.split(':')
        hr, mn = map(int, flds[:-1])
        sc = float(flds[2])
    except Exception:
        raise TimeError

    tdoy = TimeDOY(year=yr,
                   month=mo,
                   day=da,
                   hour=hr,
                   minute=mn,
                   second=sc)

    return tdoy.epoch(fepoch=fepoch)


def passcal2epoch(lopt, sep=':', fepoch=False):
    '''
       Convert "YYYY:DOY:HH:MM:SS[.sss]" to epoch
    '''
    try:
        flds = lopt.split(sep)
        yr, jd, hr, mn = map(int, flds[:-1])
        sc = float(flds[4])
    except Exception:
        raise TimeError

    tdoy = TimeDOY(year=yr,
                   hour=hr,
                   minute=mn,
                   second=sc,
                   doy=jd)

    return tdoy.epoch(fepoch=fepoch)


def epoch2passcal(epoch, sep=':'):
    '''
       Convert epoch to PASSCAL time format "YYYY:DOY:HH:MM:SS[.sss]".
    '''
    tdoy = TimeDOY(epoch=epoch)
    if isinstance(epoch, float):
        ms = True
    else:
        ms = False

    return tdoy.getPasscalTime(sep=sep, ms=ms)


def inrange(value, low, high):
    if value < low or value > high:
        return False
    else:
        return True


if __name__ == "__main__":
    import sys
    import os
    tdoy = TimeDOY(microsecond=400000, epoch=1469645921)
    print tdoy
    sys.exit()
    tdoy = TimeDOY(microsecond=231034, epoch=1402509329)
    print "Should return", '2014:162:17:55:29'
    print tdoy.getPasscalTime()
    print "Should return", '231034'
    print tdoy.dtobject.microsecond

    tdoy = TimeDOY(year=2014, hour=17, minute=55,
                   second=29, doy=162, microsecond=123456)
    print "Should return", '1402509329'
    print tdoy.epoch()
    print tdoy.getFdsnTime()
    print tdoy.getPasscalTime(ms=True)

    tdoy = TimeDOY(year=1970, month=1, day=1, hour=0,
                   minute=0, second=0, microsecond=0)
    print "Should return 0"
    print tdoy.epoch()
    tdoy = TimeDOY(year=None,
                   month=None,
                   day=None,
                   hour=0,
                   minute=0,
                   second=0,
                   microsecond=0,
                   doy=None,
                   epoch=36)
    print tdoy.getISOTime()

    tdoy1 = TimeDOY(year=1970, month=1, day=1, hour=0,
                    minute=0, second=0, microsecond=0)
    tdoy2 = TimeDOY(year=1970, month=1, day=1, hour=1,
                    minute=1, second=1, microsecond=1001)
    s = delta(tdoy1, tdoy2)
    print s
    print compare(tdoy1, tdoy2), compare(tdoy2, tdoy1)
    import time as t
    print TimeDOY(epoch=t.time()).getPasscalTime(ms=True)
    print passcal2epoch("2014:213:06:47:40.32", fepoch=True)
    print epoch2passcal(passcal2epoch("2014:213:06:47:40.32", fepoch=True))
    print fdsn2epoch("1970-01-01T00:00:00.000001", fepoch=True)
