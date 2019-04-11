"""
unit tests for ph5availability
"""

import unittest
from ph5.clients import ph5availability
from ph5.core import ph5api
import sys
import os
import re
from mock import patch
from contextlib import contextmanager
from StringIO import StringIO


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def checkTupleAlmostEqualIn(tup, tupList, place):
    """
    check if a tuple in a list of tuples in which float items only
    need to be almost equal
    :type tup: tuple
    :param tup: tuple to be checked
    :type tupList: list of tuples
    :para tupList: list of tuples that tup need to be check with
    :place: decimal places to round the values to compare
    """
    for T in tupList:
        length = len(tup)
        if length != len(T):
            continue
        for i in range(length):
            if type(tup[i]) is float:
                if round(tup[i], place) != round(T[i], place):
                    break
            else:
                if tup[i] != T[i]:
                    break
            if i == length - 1:
                return True
    return False


def checkFieldsMatch(fieldNames, fieldsList, dictList):
    """
    check if given fieldslist match the dict dictList at field fieldNames
    :type fieldsName: list of str
    :param fieldsName: list of field names that their values are to be compared
       with items in dictList
    :type fieldsList: list of tuple
    :para fieldsList: list of tuple of fields' values
    :type dictList: list of dictionary
    :para dictList: list of dictionary to be compared with
    """
    if len(fieldsList) != len(dictList):
        return False
    for d in dictList:
        arow = ()
        for i in range(len(fieldNames)):
            arow += (d[fieldNames[i]], )
        if arow not in fieldsList:
            return False
        fieldsList.remove(arow)
    return True


class TestPH5Availability(unittest.TestCase):

    def setUp(self):
        """
        setup for tests
        """
        self.ph5_object = ph5api.PH5(
            path='ph5/test_data/ph5',
            nickname='master.ph5')
        self.availability = ph5availability.PH5Availability(
            self.ph5_object)

    def assertStrEqual(self, str1, str2):
        """
        return True if 2 strings are the same, othewise
        return the index of the first difference between 2 strings
        """
        if str1 == str2:
            return True
        else:
            for i in range(len(str1)):
                if str1[i] != str2[i]:
                    errmsg = "The strings are different from %s.\n" % i
                    if i > 0:
                        errmsg += "BEFORE:\n\tstr1: '%s'\n\tstr2: '%s'\n" % \
                            (str1[:i], str2[:i])
                    errmsg += "Different at:\n\tstr1: '%s'\n\tstr2: '%s'\n"\
                        "AFTER:\n\tstr1: '%s'\n\tstr2: '%s'" % \
                        (str1[i], str2[i], str1[i:], str2[i:])
                    raise AssertionError(errmsg)

    def test_get_slc(self):
        """
        test get_slc method
        """

        # should return ALL available
        # station location and channels
        ret = self.availability.get_slc()
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 10 entries
        self.assertEqual(10, len(ret))
        # check for expected tuple values
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # Should return only station 8001
        ret = self.availability.get_slc(station='8001')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 3 entries
        self.assertEqual(3, len(ret))
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)

        # Should return only station 500
        ret = self.availability.get_slc(station='5??')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 3 entries
        self.assertEqual(3, len(ret))
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)

        # Should return stations 500 and 9001 channel DPZ
        ret = self.availability.get_slc(channel='DPZ')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 2 entries
        self.assertEqual(2, len(ret))
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # Should return stations 500 and 9001 channel
        # all channels starting with DP
        ret = self.availability.get_slc(channel='DP?')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 4 entries
        self.assertEqual(4, len(ret))
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # should return all stations and channels
        # because they all have same loc
        ret = self.availability.get_slc(location='')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 10 entries
        self.assertEqual(10, len(ret))
        # check for expected tuple values
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # should return all stations and channels
        # because they are all on or after start time
        ret = self.availability.get_slc(starttime=1463568480)
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 10 entries
        self.assertEqual(10, len(ret))
        # check for expected tuple values
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # should return all stations and channels
        # because they all contain data before end time
        ret = self.availability.get_slc(endtime=1550850240)
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 10 entries
        self.assertEqual(10, len(ret))
        # check for expected tuple values
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # should return all stations and channels
        # because they are all contain data between start and end time
        ret = self.availability.get_slc(starttime=1463568480,
                                        endtime=1550850240)
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 10 entries
        self.assertEqual(10, len(ret))
        # check for expected tuple values
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # should return no stations
        # because they all end before start time
        ret = self.availability.get_slc(starttime=1741880232)
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 0 entries
        self.assertEqual(0, len(ret))

        # should return no stations
        # because they all start after end time
        ret = self.availability.get_slc(endtime=637342632)
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 0 entries
        self.assertEqual(0, len(ret))

        # should return
        # station 0407 and all channels
        ret = self.availability.get_slc(
            station='0407',
            location='',
            channel='*',
            starttime=1545085229)
        # return type should be list
        self.assertTrue(type(ret) is list)
        self.assertEqual(3, len(ret))
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)

        # should return all stations
        # should return all stations and channels
        # because they are all contain data between start and end time
        ret = self.availability.get_slc(
            station='*',
            location='',
            channel='*',
            starttime=1463568480,
            endtime=1550850240)
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 10 entries
        self.assertEqual(10, len(ret))
        # check for expected tuple values
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # should return nothing
        ret = self.availability.get_slc(station='99999')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 0 entries
        self.assertEqual(0, len(ret))

        # should return nothing
        ret = self.availability.get_slc(station='8001',
                                        channel='XYZ')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 0 entries
        self.assertEqual(0, len(ret))

        # should return nothing
        ret = self.availability.get_slc(station='9001',
                                        channel='HHN')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 0 entries
        self.assertEqual(0, len(ret))

    def test_get_availability_extent(self):
        """
        test get_availability_extent method
        """
        # expected to return all extent information
        ret = self.availability.get_availability_extent()
        # There are 10 channels all with data
        # so expect 10 entries
        self.assertEqual(10, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550850189) in ret)
        self.assertTrue(('8001', '', 'HL1',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(('8001', '', 'HL2',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(('8001', '', 'HLZ',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(checkTupleAlmostEqualIn(
            ('0407', '', 'HHN', 1545085230.917, 1545085240.92), ret, 2))
        self.assertTrue(checkTupleAlmostEqualIn(
            ('0407', '', 'LHN', 1545085230.681998, 1545085240.69), ret, 2))
        self.assertTrue(('0407', '', 'LOG',
                         1545088205, 1545088205) in ret)
        self.assertTrue(('500', '', 'DP1',
                         1502294400.38, 1502294460.38) in ret)
        self.assertTrue(('500', '', 'DP2',
                         1502294400.38, 1502294460.38) in ret)
        self.assertTrue(('500', '', 'DPZ',
                         1502294400.38, 1502294460.38) in ret)

        # get extent for 9001. A station with gaps
        # large time range encompassing trace
        ret = self.availability.get_availability_extent(
            station='9001',
            channel='DPZ',
            location='',
            starttime=1,
            endtime=2530985583)
        # expect 1 entry because only 1 channel
        # within time range was requested
        self.assertEqual(1, len(ret))
        # expected entry
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550850189) in ret)

        # same request but with sample rate included
        ret = self.availability.get_availability_extent(
            station='9001',
            channel='DPZ',
            location='',
            starttime=1,
            endtime=2530985583,
            include_sample_rate=True)
        # expect 1 entry because only 1 channel
        # within time range was requested
        self.assertEqual(1, len(ret))
        # expected entry with sample_rate included
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550850189,
                         500.0) in ret)
        #                 250.0) in ret)

        # Check LOG channel
        ret = self.availability.get_availability_extent(
            station='0407',
            channel='LOG',
            location='',
            starttime=1545088205,
            endtime=1545088205)
        # expect 1 entry because only 1 channel
        # within time range was requested
        self.assertEqual(1, len(ret))
        self.assertTrue(('0407', '', 'LOG',
                         1545088205, 1545088205) in ret)

        # Check LOG channel with sample rate
        ret = self.availability.get_availability_extent(
            station='0407',
            channel='LOG',
            location='',
            starttime=1545088205,
            endtime=1545088205,
            include_sample_rate=True)
        # expect 1 entry because only 1 channel
        # within time range was requested
        self.assertEqual(1, len(ret))
        self.assertTrue(('0407', '', 'LOG',
                         1545088205, 1545088205, 0.0) in ret)

        # get all DPZ channels
        ret = self.availability.get_availability_extent(
            station='*',
            channel='DPZ',
            location='',
            starttime=1,
            endtime=2530985583)
        # there are 2 DPZ channels in the time range
        self.assertEqual(2, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550850189) in ret)
        self.assertTrue(('500', '', 'DPZ',
                         1502294400.38, 1502294460.38) in ret)

        # get matching all locations ''
        # expected to return all extent information
        ret = self.availability.get_availability_extent(
            station='*',
            channel='*',
            location='',
            starttime=1,
            endtime=2530985583
        )
        # There are 10 channels all with data
        # so expect 10 entries
        self.assertEqual(10, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550850189) in ret)
        self.assertTrue(('8001', '', 'HL1',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(('8001', '', 'HL2',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(('8001', '', 'HLZ',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(checkTupleAlmostEqualIn(
            ('0407', '', 'HHN', 1545085230.917, 1545085240.92), ret, 2))
        self.assertTrue(checkTupleAlmostEqualIn(
            ('0407', '', 'LHN', 1545085230.681998, 1545085240.69), ret, 2))
        self.assertTrue(('0407', '', 'LOG',
                         1545088205, 1545088205) in ret)
        self.assertTrue(('500', '', 'DP1',
                         1502294400.38, 1502294460.38) in ret)
        self.assertTrue(('500', '', 'DP2',
                         1502294400.38, 1502294460.38) in ret)
        self.assertTrue(('500', '', 'DPZ',
                         1502294400.38, 1502294460.38) in ret)

        # get matching all locations '01'
        # expected to return none
        ret = self.availability.get_availability_extent(
            station='*',
            channel='*',
            location='01',
            starttime=1,
            endtime=2530985583
        )
        # There are 0 channels with data
        # so expect 0 entries
        self.assertFalse(ret)

        # expected to return none
        ret = self.availability.get_availability_extent(
            station='12345',
            channel='*',
            location='*',
            starttime=1,
            endtime=2530985583
        )
        # There are 0 channels with data
        # so expect 0 entries
        self.assertFalse(ret)

        # expected to return none
        ret = self.availability.get_availability_extent(
            station='8001',
            channel='*',
            location='*',
            starttime=1502294400.38,
            endtime=1502294460.38
        )
        # There are 0 channels with data
        # so expect 0 entries
        self.assertFalse(ret)

    def test_get_availability(self):
        """
        test get_availability method
        """
        # expected to return all availability information
        ret = self.availability.get_availability()
        # There are 10 channels all with data
        # but 9001 has 8 gaps so expect 18 entries
        self.assertEqual(18, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550849949) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550849973, 1550849974) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850003, 1550850009) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850033, 1550850034) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850060, 1550850068) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850093, 1550850094) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850123, 1550850129) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850153, 1550850154) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850183, 1550850189) in ret)
        self.assertTrue(('8001', '', 'HL1',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(('8001', '', 'HL2',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(('8001', '', 'HLZ',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(checkTupleAlmostEqualIn(
            ('0407', '', 'HHN', 1545085230.917, 1545085240.92), ret, 2))
        self.assertTrue(checkTupleAlmostEqualIn(
            ('0407', '', 'LHN', 1545085230.681998, 1545085240.69), ret, 2))
        self.assertTrue(('0407', '', 'LOG',
                         1545088205, 1545088205) in ret)
        self.assertTrue(('500', '', 'DP1',
                         1502294400.38, 1502294460.38) in ret)
        self.assertTrue(('500', '', 'DP2',
                         1502294400.38, 1502294460.38) in ret)
        self.assertTrue(('500', '', 'DPZ',
                         1502294400.38, 1502294460.38) in ret)

        # expected to return all availability information
        # for 9001
        ret = self.availability.get_availability(
            station='9001', channel='DPZ',
            location='', starttime=1550849943,
            endtime=1550850189)
        # 9001 has 8 gaps so expect 9 entries
        self.assertEqual(9, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550849949) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550849973, 1550849974) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850003, 1550850009) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850033, 1550850034) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850060, 1550850068) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850093, 1550850094) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850123, 1550850129) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850153, 1550850154) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850183, 1550850189) in ret)

        # expected to return partial information
        # for 9001 based on times requested
        ret = self.availability.get_availability(
            station='9001', channel='DPZ',
            location='', starttime=1550849973,
            endtime=1550850005)
        # 9001 for this time range has 1 gap
        self.assertEqual(2, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550849973, 1550849974) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850003, 1550850005) in ret)

        # expected to return partial information
        # for 9001 based on times requested
        ret = self.availability.get_availability(
            station='9001', channel='DPZ',
            location='', starttime=1550850060,
            endtime=1550850154)
        # 9001 for this time range has 3 gaps
        self.assertEqual(4, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550850060, 1550850068) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850093, 1550850094) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850123, 1550850129) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850153, 1550850154) in ret)

        # expected to return no gaps
        # for 500 all data in channel DPZ
        ret = self.availability.get_availability(
            station='500', channel='DPZ',
            location='', starttime=1502294400.38,
            endtime=1502294460.38)
        # 500 DPZ has 2 windows but no gaps
        self.assertEqual(1, len(ret))
        self.assertTrue(('500', '', 'DPZ',
                         1502294400.38, 1502294460.38) in ret)

    def test_get_availability_percentage(self):
        """
        test get_availability_percentage method
        """

        # should return 100% and 0 gaps
        ret = self.availability.get_availability_percentage(
            '500',
            '',
            'DP1',
            1502294400.38,
            1502294460.38)
        self.assertTrue(isinstance(ret, tuple))
        self.assertEqual(1.0, ret[0])
        self.assertEqual(0, ret[1])

        # should return 14.63% and 8 gaps
        ret = self.availability.get_availability_percentage(
            '9001',
            '',
            'DPZ',
            1550849943,
            1550850189)
        self.assertTrue(isinstance(ret, tuple))
        self.assertAlmostEquals(0.14634146341, ret[0], 4)
        self.assertEqual(8, ret[1])

        # should return 11.67% and 2 gaps
        ret = self.availability.get_availability_percentage(
            '9001',
            '',
            'DPZ',
            1550849943,
            1550850003)
        self.assertTrue(isinstance(ret, tuple))
        self.assertAlmostEquals(0.1167, ret[0], 3)
        self.assertEqual(2, ret[1])

        # should return 97.13% and 2 gaps
        ret = self.availability.get_availability_percentage(
            '8001',
            '',
            'HLZ',
            1463568479,
            1463568518)
        self.assertTrue(isinstance(ret, tuple))
        self.assertAlmostEquals(0.9713, ret[0], 4)
        self.assertEqual(2, ret[1])

        # should return 0% and 0 gaps
        ret = self.availability.get_availability_percentage(
            '9001',
            '',
            'DP1',
            1463568479,
            1463568518)
        self.assertTrue(isinstance(ret, tuple))
        self.assertEqual(0.0, ret[0])
        self.assertEqual(0, ret[1])

        # should return 0% and 0 gaps
        ret = self.availability.get_availability_percentage(
            '12345',
            '',
            'XYZ',
            1463568479,
            1463568518)
        self.assertTrue(isinstance(ret, tuple))
        self.assertEqual(0.0, ret[0])
        self.assertEqual(0, ret[1])

        # should return 0% and 0 gaps
        ret = self.availability.get_availability_percentage(
            '8001',
            '',
            'HLZ',
            1550849943,
            1550850183)
        self.assertTrue(isinstance(ret, tuple))
        self.assertEqual(0.0, ret[0])
        self.assertEqual(0, ret[1])

    def test_has_data(self):
        """
        test has_data method
        """
        # assumes all for everything
        # should return true
        self.assertTrue(
            self.availability.has_data())

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='*'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='8001'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='0407'))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                station='9999'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                channel='*'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                channel='???'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                channel='HHN'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                channel='LOG'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                channel='DP1'))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                station='XYZ'))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                station='DP9'))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                location='01'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                location=''))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='0407',
                location=''))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                station='0407',
                location='01'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='8001',
                channel='HL?',
                location=''))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='8001',
                channel='HLZ',
                location=''))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                station='8001',
                channel='XYZ',
                location=''))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                starttime=1463568480))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                starttime=1550849929))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                starttime=1615652704))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                endtime=1463568489))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                endtime=605809504))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='*',
                location='',
                channel='???',
                starttime=605809504,
                endtime=1741883104))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='8001',
                location='',
                channel='HL2',
                starttime=605809504,
                endtime=1741883104))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='0407',
                location='',
                channel='LOG',
                starttime=605809504,
                endtime=1741883104))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                station='500',
                location='',
                channel='LOG',
                starttime=605809504,
                endtime=1741883104))

    def test_get_args(self):
        """
        test get_args
        """
        # NOTE needs much more
        with self.assertRaises(SystemExit):
            ph5availability.get_args([])
        with self.assertRaises(SystemExit):
            ph5availability.get_args(['-n', 'master.ph5'])
        with self.assertRaises(SystemExit):
            ph5availability.get_args(
                ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5'])
        # test false args
        with self.assertRaises(SystemExit):
            ph5availability.get_args(
                ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                 '-a', '0', '-T'])
        # test default args
        ret = vars(ph5availability.get_args(
            ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5', '-a', '0']))
        expect = {
            'array_t_': None, 'format': None, 'start_time': None,
            'output_file': None, 'avail': 0, 'end_time': None,
            'sta_id_list': [], 'ph5path': 'ph5/test_data/ph5',
            'samplerate': False, 'nickname': 'master.ph5', 'sta_list': [],
            'channel': [], 'location': None}
        self.assertDictEqual(ret, expect)
        # test correct args received
        ret = vars(ph5availability.get_args(
            ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5', '-a', '0',
             '-s', '2017-08-09T16:00:00.380000',
             '-e', '2017-08-09T16:01:00.380000', '--station', '500,0407',
             '--station_id', '500,0407', '-l', '00', '-c', 'DP1', '-S',
             '-A', '1', '-F', 't', '-o', 'extent.txt']))
        expect = {
            'array_t_': 1, 'format': 't', 'ph5path': 'ph5/test_data/ph5',
            'output_file': 'extent.txt', 'avail': 0,
            'start_time': '2017-08-09T16:00:00.380000',
            'end_time': '2017-08-09T16:01:00.380000',
            'sta_id_list': '500,0407', 'sta_list': '500,0407',
            'samplerate': True, 'nickname': 'master.ph5',
            'channel': 'DP1', 'location': '00'}
        self.assertDictEqual(ret, expect)

    def test_analyze_args(self):
        """
        test analyze_args method
        """
        A = self.availability
        # test wrong format channel
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5', '-a', '0',
             '-c', '1 2 3'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, False)

        # test wrong format location: len > 2
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5', '-a', '0',
             '-l', 'Oaa'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, False)

        # test wrong format location: invalid character
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5', '-a', '0',
             '-l', 'O^'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, False)

        # test wrong format station
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5', '-a', '0',
             '--station', 'o-g'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, False)

        # test default args
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5', '-a', '0'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, True)
        self.assertEqual(A.stations, ['*'])
        self.assertEqual(A.locations, ['*'])
        self.assertEqual(A.channels, ['*'])
        self.assertEqual(A.starttime, None)
        self.assertEqual(A.endtime, None)
        self.assertEqual(A.array, None)
        self.assertEqual(A.avail, 0)
        self.assertEqual(A.SR_included, False)
        self.assertEqual(A.OFILE, None)

        # test wildcard station, location, channel
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5', '-a', '0',
             '--station', '*', '-l', '*', '-c', '*'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, True)
        self.assertEqual(A.stations, ['*'])
        self.assertEqual(A.locations, ['*'])
        self.assertEqual(A.channels, ['*'])

        # test wildcard station, location, channel
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5', '-a', '0',
             '--station', '?001', '-l', '??', '-c', 'DP?'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, True)
        self.assertEqual(A.stations, ['?001'])
        self.assertEqual(A.locations, ['??'])
        self.assertEqual(A.channels, ['DP?'])

        # test args are assigned correctly
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5', '-a', '0',
             '-s', '2017-08-09T16:00:00.380000',
             '-e', '2017-08-09T16:01:00.380000', '--station', '500,0407',
             '-l', '00', '-c', 'DP1', '-S',
             '-A', '1', '-F', 't', '-o', 'extent.txt'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, True)
        self.assertEqual(A.stations, ['500', '0407'])
        self.assertEqual(A.locations, ['00'])
        self.assertEqual(A.channels, ['DP1'])
        self.assertEqual(A.starttime, 1502294400.38)
        self.assertEqual(A.endtime, 1502294460.38)
        self.assertEqual(A.array, 1)
        self.assertEqual(A.avail, 0)
        # SR_included only True when avail =2 or 3
        self.assertEqual(A.SR_included, False)
        self.assertIsInstance(A.OFILE, file)
        self.assertEqual(A.OFILE.name, 'extent.txt')
        self.assertEqual(A.OFILE.closed, False)

        # same args, with avail=2, check if SR_included=True
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', 'ph5/test_data/ph5', '-a', '2',
             '-s', '2017-08-09T16:00:00.380000',
             '-e', '2017-08-09T16:01:00.380000', '--station', '500,0407',
             '-l', '00', '-c', 'DP1', '-S',
             '-A', '1', '-F', 't', '-o', 'extent.txt'])
        ret = A.analyze_args(args)
        self.assertEqual(A.SR_included, True)

    def test_main(self):
        """
        test main function
        """

        # test has_data station with data
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '0', '--station',
                    '500', '--channel', 'DP1']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        self.assertEqual(output, 'True')

        # test has_data station with data all channels
        # expect to return True 3 times, once for each channel
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '0', '--station',
                    '500', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        self.assertEqual(output, 'True')

        # test has_data station with no data
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '0', '--station',
                    '9576', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        self.assertEqual(output, 'False')

        # test has_data station list data, no data,
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '0', '--station',
                    '9001,91234', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        self.assertEqual(output, 'True\nFalse')

        # test has_data with start time
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '0', '-s',
                    '2017-08-09T16:00:00.380000', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        self.assertEqual(output, 'True')

        # test has_data with end time
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '0', '-e',
                    '2019-02-22T15:43:09.000000', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        self.assertEqual(output, 'True')

        # test has_data with time range having data
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '0',
                    '-s', '2019-02-22T15:39:03.000000',
                    '-e', '2019-02-22T15:43:09.000000', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        self.assertEqual(output, 'True')

        # test has_data with time range having no data
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '0',
                    '-s', '2017-08-09T16:01:01.0',
                    '-e', '2018-12-17T22:20:30.0', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        self.assertEqual(output, 'False')

        # test get_slc with station
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '1', '--station', '0407']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        expect = "[('0407', '', 'HHN'), ('0407', '', 'LHN'), "\
            "('0407', '', 'LOG')]"
        self.assertEqual(output, expect)

        # test get_slc with channel
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '1', '-c', 'LOG']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        expect = "[('0407', '', 'LOG')]"
        self.assertEqual(output, expect)

        # test get_slc with time
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '1',
                    '-s', '2019-02-22T15:39:03.000000',
                    '-e', '2019-02-22T15:43:09.000000']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        expect = "[('9001', '', 'DPZ')]"
        self.assertEqual(output, expect)

        # test get_availability with station
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '2', '--station', '0407']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        expect = "[('0407', '', 'HHN', 1545085230.917, 1545085240.9220002), "\
            "('0407', '', 'LHN', 1545085230.681998, 1545085240.691998), "\
            "('0407', '', 'LOG', 1545088205.0, 1545088205.0)]"
        self.assertStrEqual(output, expect)

        # test get_availability with channel
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '2', '-c', 'LOG']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        expect = "[('0407', '', 'LOG', 1545088205.0, 1545088205.0)]"
        self.assertStrEqual(output, expect)

        # test get_availability with time
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '2',
                    '-s', '2018-12-17T23:10:05.0',
                    '-e', '2019-02-22T15:39:03.1']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        expect = "[('0407', '', 'LOG', 1545088205.0, 1545088205.0), "\
            "('9001', '', 'DPZ', 1550849943.0, 1550849943.1)]"
        self.assertStrEqual(output, expect)

        # test get_availability_extent with station
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '3', '--station', '9001']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        expect = "[('9001', '', 'DPZ', 1550849943.0, 1550850189.0)]"
        self.assertStrEqual(output, expect)

        # test get_availability_extent with channel
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '3', '-c', 'DP2']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        expect = "[('500', '', 'DP2', 1502294400.38, 1502294460.38)]"
        self.assertStrEqual(output, expect)

        # test get_availability_extent with time
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '3', '-S',
                    '-s', '2018-12-17T23:10:05.0',
                    '-e', '2019-02-22T15:39:03.1']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        expect = "[('0407', '', 'LOG', 1545088205.0, 1545088205.0, 0), "\
            "('9001', '', 'DPZ', 1550849943.0, 1550849943.1, 500.0)]"
        self.assertStrEqual(output, expect)

        # test get_availability_extent with wildcard station, location, channel
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '3',
                    '--station', '?001', '-l', '*', '-c', 'DP?']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        expect = "[('9001', '', 'DPZ', 1550849943.0, 1550850189.0)]"
        self.assertEqual(output, expect)

        # test get_availability_percentage with station, no channel
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '4', '--station', '9001']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        self.assertStrEqual(output, '')

        # test get_availability_percentage with channel, no station
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '4', '-c', 'DP2']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        self.assertStrEqual(output, '')

        # test get_availability_percentage with channel, station=*
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '4', '-c', 'DP2',
                    '--station', '*']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        self.assertStrEqual(output, '')

        # test get_availability_percentage with channel, station=*
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '4', '-c', 'DP1',
                    '--station', '500']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        self.assertStrEqual(output, '(1.0, 0)')

        # test get_availability_percentage with station, channel, time
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '4', '--station', '9001',
                    '-s', '2019-02-22T15:39:03.0', '-c', 'DPZ',
                    '-e', '2019-02-22T15:40:03.0']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = re.sub(r"\(|\)", '', out.getvalue().strip())
        ret = output.split(',')
        self.assertAlmostEquals(0.1167, float(ret[0]), 3)
        self.assertEqual(2, int(ret[1]))

        # test extent and text format
        # should return 10 channels
        # should match slc_full.txt from test data
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '3',
                    '-F', 't', '-S']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        with open('ph5/test_data/metadata/extent_full.txt', 'r') as \
                content_file:
            content = content_file.read().strip()
        self.assertEqual(output, content)

        # test extent and geocsv format
        # should return 10 channels
        # should match slc_full_geocsv.csv from test data
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '3',
                    '-F', 'g', '-S']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        with open('ph5/test_data/metadata/extent_full.csv', 'r') as \
                content_file:
            content = content_file.read().strip()
        self.assertStrEqual(output, content)

        # test extent and text format
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '3',
                    '-F', 't', '-S']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        with open('ph5/test_data/metadata/extent_full.txt', 'r') as \
                content_file:
            content = content_file.read().strip()
        self.assertStrEqual(output, content)

        # test extent and sync format
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '3',
                    '-F', 's', '-S']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        i1 = output.find('\n')
        with open('ph5/test_data/metadata/extent_full.sync', 'r') as \
                content_file:
            content = content_file.read().strip()
        i2 = content.find('\n')
        self.assertStrEqual(output[i1:], content[i2:])

        # test extent and json format
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-a', '3',
                    '-F', 'j', '-S']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5availability.main()
        output = out.getvalue().strip()
        i1 = output.find('"datasources"')
        with open('ph5/test_data/metadata/extent_full.json', 'r') as \
                content_file:
            content = content_file.read().strip()
        i2 = content.find('"datasources"')
        self.assertStrEqual(output[i1:], content[i2:])

    def test_convert_time(self):
        """
        test convert_time method
        """
        # convert list with epoch times at 3, 4
        ret = self.availability.convert_time(
            ['500', '', 'DP2', 1502294400.38, 1502294460.38])
        self.assertEqual(['500', '', 'DP2', '2017-08-09T16:00:00.380000Z',
                          '2017-08-09T16:01:00.380000Z'], ret)

        # convert list with FDSN time at 3, 4
        ret = self.availability.convert_time(
                    ['500', '', 'DP2', '2017-08-09T16:00:00.380000Z',
                     '2017-08-09T16:01:00.380000Z'])
        self.assertEqual(['500', '', 'DP2', '2017-08-09T16:00:00.380000Z',
                          '2017-08-09T16:01:00.380000Z'], ret)

        # convert list with epoch times at 2,3: wrong format
        ret = self.availability.convert_time(
            ['500', 'DP2', 1502294400.38, 1502294460.38])
        self.assertEqual(-1, ret)

    def test_get_channel(self):
        """
        test get_channel method
        """
        # get channel from station that lacks of info for channel
        ret = self.availability.get_channel({})
        self.assertEqual('DPX', ret)

        # get channel from station with enough info
        ret = self.availability.get_channel(
            {'seed_band_code_s': 'L', 'seed_instrument_code_s': 'O',
             'seed_orientation_code_s': 'G'})
        self.assertEqual('LOG', ret)

    def test_get_slc_info(self):
        """
        test get_slc_info method
        """
        arrayorder, arraybyid = self.availability.get_array_order_id(
            'Array_t_001')
        st = arraybyid['500'][1][0]

        # get any (sta,loc,chan) value from the st passed
        ret = self.availability.get_slc_info(st, '*', '*', '*')
        self.assertEqual(('500', '', 'DP1'), ret)
        # channel DP1 in st
        ret = self.availability.get_slc_info(st, '*', '*', 'DP1')
        self.assertEqual(('500', '', 'DP1'), ret)
        # station 500 in st
        ret = self.availability.get_slc_info(st, '500', '*', '*')
        self.assertEqual(('500', '', 'DP1'), ret)
        # channel DP2 not in st
        ret = self.availability.get_slc_info(st, '*', '*', 'DP2')
        self.assertEqual(-1, ret)
        # station 0407 not in st
        ret = self.availability.get_slc_info(st, '0407', '*', '*')
        self.assertEqual(-1, ret)
        # location 00 not in st
        ret = self.availability.get_slc_info(st, '*', '00', '*')
        self.assertEqual(-1, ret)

    def test_get_start(self):
        """
        test get_start method
        """
        ret = self.availability.get_start(
            {'time/epoch_l': 1502294400, 'time/micro_seconds_i': 380000})
        self.assertEqual(1502294400.38, ret)

    def test_get_end(self):
        """
        test get_end method
        """
        # samplerate != 0
        ret = self.availability.get_end(
            {'sample_count_i': 15000}, 1502294400.38, 500)
        self.assertEqual(1502294430.38, ret)

        # samplerate == 0
        ret = self.availability.get_end(
            {'sample_count_i': 15000}, 1502294400.38, 0)
        self.assertEqual(1502294400.38, ret)

    def test_get_sample_rate(self):
        """
        test get_sample_rate method
        """
        # sample_rate_i != 0
        ret = self.availability.get_sample_rate(
            {'sample_rate_i': 100, 'sample_rate_multiplier_i': 1})
        self.assertEqual(100, ret)

        # sample_rate_i == 0
        ret = self.availability.get_sample_rate(
            {'sample_rate_i': 0, 'sample_rate_multiplier_i': 1})
        self.assertEqual(0, ret)

    def test_get_time_das_t(self):
        """
        test get_time_das_t method
        """
        # start=None, end=None; no component, sample_rate
        ret = self.availability.get_time_das_t(
            '3X500', None, None)
        self.assertEqual(1502294400.38, ret[0])
        self.assertEqual(1502294460.38, ret[1])
        self.assertTrue(checkFieldsMatch(
            ['array_name_data_a'],
            [('Data_a_0001',), ('Data_a_0002',), ('Data_a_0003',),
             ('Data_a_0004',), ('Data_a_0005',), ('Data_a_0006',)],
            ret[2]))
        # have start, end=None; no component, sample_rate
        ret = self.availability.get_time_das_t(
            '3X500', 1502294431.38, None)
        self.assertEqual(1502294430.38, ret[0])
        self.assertEqual(1502294460.38, ret[1])
        self.assertTrue(checkFieldsMatch(
            ['array_name_data_a'],
            [('Data_a_0002', ), ('Data_a_0004', ), ('Data_a_0006', )],
            ret[2]))
        # start=None, have End; no component, sample_rate
        ret = self.availability.get_time_das_t(
            '3X500', None, 1502294430)
        self.assertEqual(1502294400.38, ret[0])
        self.assertEqual(1502294430.38, ret[1])
        self.assertTrue(checkFieldsMatch(
            ['array_name_data_a'],
            [('Data_a_0001', ), ('Data_a_0003', ), ('Data_a_0005', )],
            ret[2]))
        # have start, end; no component, sample_rate
        ret = self.availability.get_time_das_t(
            '3X500', 1502294431.38, 1502294455.38)
        self.assertEqual(1502294430.38, ret[0])
        self.assertEqual(1502294460.38, ret[1])
        self.assertTrue(checkFieldsMatch(
            ['array_name_data_a'],
            [('Data_a_0002', ), ('Data_a_0004', ), ('Data_a_0006', )],
            ret[2]))
        # start=None, end=None; have component, no sample_rate
        ret = self.availability.get_time_das_t(
            '3X500', None, None, 1)
        self.assertEqual(1502294400.38, ret[0])
        self.assertEqual(1502294460.38, ret[1])
        self.assertTrue(checkFieldsMatch(
            ['array_name_data_a'],
            [('Data_a_0001', ), ('Data_a_0002', )],
            ret[2]))
        # start=None, end=None; have component, sample_rate
        ret = self.availability.get_time_das_t(
            '5553', None, None, 1, 100)
        self.assertEqual(1545085230.681998, ret[0])
        self.assertEqual(1545085240.691998, ret[1])
        self.assertTrue(checkFieldsMatch(
            ['array_name_data_a'],
            [('Data_a_00002', )],
            ret[2]))
        # start=None, end=None; no component, have sample_rate
        ret = self.availability.get_time_das_t(
            '5553', None, None, sample_rate=100)
        self.assertEqual(-1, ret)
        # start=None, end=None; have component, have false sample_rate
        ret = self.availability.get_time_das_t(
            '5553', None, None, 1, 500)
        self.assertEqual(-1, ret)

    def test_get_sampleNos_gapOverlap(self):
        st = {'deploy_time/micro_seconds_i': 0,
              'deploy_time/epoch_l': 1550849940,
              'pickup_time/epoch_l': 1550850240,
              'pickup_time/micro_seconds_i': 0}

        # 3 gaps inside
        das_t = [{'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 3000, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849943},  # end: 1550849949
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 500, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849973},  # end: 1550849974
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 3000, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550850003},  # end: 1550850009
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 500, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550850033}]  # end: 1550850034

        ret = self.availability.get_sampleNos_gapOverlap(
            das_t, 1550849943.0, 1550850034.0, None, None, 500, st)
        self.assertEqual((45500, 7000, 3), ret)

        # 1 gap bw traces 3 & 4; 1 at the beginning; 1 at the end
        das_t = [{'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 3000, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849943},  # end: 1550849949
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 500, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849949},  # end: 1550849950
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 3000, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849950},  # end: 1550849956
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 500, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550850033}]  # end: 1550850034
        ret = self.availability.get_sampleNos_gapOverlap(
            das_t, 1550849943.0, 1550850034.0, 1550849942, 1550850035, 500, st)
        self.assertEqual((46500, 7000, 3), ret)

        # 1 overlap bw traces 2 & 3; 1 gap bw 3 & 4; 1 at beginning
        das_t = [{'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 3000, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849943},  # end: 1550849949
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 500, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849949},  # end: 1550849950
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 3000, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849947},  # end: 1550849953
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 500, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550850033}]  # end: 1550850034
        ret = self.availability.get_sampleNos_gapOverlap(
            das_t, 1550849943.0, 1550850034.0, 1550849942, 1550850032, 500, st)
        self.assertEqual((45000, 6500, 3), ret)

    def test_get_array_order_id(self):
        """
        test get_array_order_id method
        """
        ret = self.availability.get_array_order_id('Array_t_009')
        self.assertEqual(['9001'], ret[0])
        self.assertTrue(1, len(ret[1]))
        self.assertTrue('9001' in ret[1].keys())

        ret = self.availability.get_array_order_id('Array_t_008')
        self.assertEqual(['8001'], ret[0])
        self.assertTrue(1, len(ret[1]))
        self.assertTrue('8001' in ret[1].keys())

        # array_name not exist
        ret = self.availability.get_array_order_id('Array_t_010')
        self.assertEqual(-1, ret)

    def test_get_text_report(self):
        """
        test get_text_report method
        """
        result = self.availability.get_availability_extent(
            include_sample_rate=True)
        ret = self.availability.get_text_report(result).strip()
        with open('ph5/test_data/metadata/extent_full.txt', 'r') as \
                content_file:
            content = content_file.read().strip()
        self.assertStrEqual(ret, content)

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1,
            include_sample_rate=True)
        ret = self.availability.get_text_report(result).strip()
        with open('ph5/test_data/metadata/avail_time.txt', 'r') as \
                content_file:
            content = content_file.read().strip()
        self.assertStrEqual(ret, content)

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1)
        ret = self.availability.get_text_report(result).strip()
        with open('ph5/test_data/metadata/avail_time_noSR.txt', 'r') as \
                content_file:
            content = content_file.read().strip()
        self.assertStrEqual(ret, content)

    def test_print_report(self):
        self.availability.OFILE = None
        with captured_output() as (out, err):
            self.availability.print_report("this is a text line")
        output = out.getvalue().strip()
        self.assertEqual(output, "this is a text line")

        self.availability.OFILE = open("test", 'w')
        with captured_output() as (out, err):
            self.availability.print_report("this is a text line")
        output = out.getvalue().strip()
        self.assertEqual(output, "")
        self.assertTrue(self.availability.OFILE.closed)
        with open('test', 'r') as content_file:
            content = content_file.read().strip()
        self.assertEqual(content, "this is a text line")
        os.remove('test')

    def test_get_geoCSV_report(self):
        """
        test get_geoCSV_report method
        """
        result = self.availability.get_availability_extent(
            include_sample_rate=True)
        ret = self.availability.get_geoCSV_report(result).strip()
        with open('ph5/test_data/metadata/extent_full.csv', 'r') as \
                content_file:
            content = content_file.read().strip()
        self.assertStrEqual(ret, content)

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1,
            include_sample_rate=True)
        ret = self.availability.get_geoCSV_report(result).strip()
        with open('ph5/test_data/metadata/avail_time.csv', 'r') as \
                content_file:
            content = content_file.read().strip()
        self.assertStrEqual(ret, content)

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1)
        ret = self.availability.get_geoCSV_report(result).strip()
        with open('ph5/test_data/metadata/avail_time_noSR.csv', 'r') as \
                content_file:
            content = content_file.read().strip()
        self.assertStrEqual(ret, content)

    def test_get_sync_report(self):
        """
        test get_sync_report method
        """
        result = self.availability.get_availability_extent(
            include_sample_rate=True)
        ret = self.availability.get_sync_report(result).strip()
        i1 = ret.find('\n')
        with open('ph5/test_data/metadata/extent_full.sync', 'r') as \
                content_file:
            content = content_file.read().strip()
        i2 = content.find('\n')
        self.assertStrEqual(ret[i1:], content[i2:])

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1,
            include_sample_rate=True)
        ret = self.availability.get_sync_report(result).strip()
        i1 = ret.find('\n')
        with open('ph5/test_data/metadata/avail_time.sync', 'r') as \
                content_file:
            content = content_file.read().strip()
        i2 = content.find('\n')
        self.assertStrEqual(ret[i1:], content[i2:])

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1)
        ret = self.availability.get_sync_report(result).strip()
        i1 = ret.find('\n')
        with open('ph5/test_data/metadata/avail_time_noSR.sync', 'r') as \
                content_file:
            content = content_file.read().strip()
        i2 = content.find('\n')
        self.assertStrEqual(ret[i1:], content[i2:])

    def test_get_json_report(self):
        """
        test get_json_report method
        """
        result = self.availability.get_availability_extent(
            include_sample_rate=True)
        ret = self.availability.get_json_report(result).strip()
        i1 = ret.find('"datasources"')
        with open('ph5/test_data/metadata/extent_full.json', 'r') as \
                content_file:
            content = content_file.read().strip()
        i2 = content.find('"datasources"')
        self.assertStrEqual(ret[i1:], content[i2:])

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1,
            include_sample_rate=True)
        ret = self.availability.get_json_report(result).strip()
        i1 = ret.find('"datasources"')
        with open('ph5/test_data/metadata/avail_time.json', 'r') as \
                content_file:
            content = content_file.read().strip()
        i2 = content.find('"datasources"')
        self.assertStrEqual(ret[i1:], content[i2:])

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1)
        ret = self.availability.get_json_report(result).strip()
        i1 = ret.find('"datasources"')
        with open('ph5/test_data/metadata/avail_time_noSR.json', 'r') as \
                content_file:
            content = content_file.read().strip()
        i2 = content.find('"datasources"')
        self.assertStrEqual(ret[i1:], content[i2:])

    def test_get_report(self):
        """
        test get_report method
        """
        result = self.availability.get_availability_extent(
            include_sample_rate=True)
        ret = self.availability.get_report(result, format='t').strip()
        with open('ph5/test_data/metadata/extent_full.txt', 'r') as \
                content_file:
            content = content_file.read().strip()
        self.assertStrEqual(ret, content)

        ret = self.availability.get_report(result, format='g').strip()
        with open('ph5/test_data/metadata/extent_full.csv', 'r') as \
                content_file:
            content = content_file.read().strip()
        self.assertStrEqual(ret, content)

        ret = self.availability.get_report(result, format='s').strip()
        i1 = ret.find('\n')
        with open('ph5/test_data/metadata/extent_full.sync', 'r') as \
                content_file:
            content = content_file.read().strip()
        i2 = content.find('\n')
        self.assertStrEqual(ret[i1:], content[i2:])

        ret = self.availability.get_report(result, format='j').strip()
        i1 = ret.find('"datasources"')
        with open('ph5/test_data/metadata/extent_full.json', 'r') as \
                content_file:
            content = content_file.read().strip()
        i2 = content.find('"datasources"')
        self.assertStrEqual(ret[i1:], content[i2:])

        ret = self.availability.get_report(result, format='k')
        self.assertStrEqual(ret, result)

    def tearDown(self):
        """
        teardown for tests
        """
        self.ph5_object.close()


if __name__ == "__main__":
    unittest.main()
