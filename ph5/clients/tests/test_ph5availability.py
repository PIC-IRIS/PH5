"""
unit tests for ph5availability
"""

import unittest
from ph5.clients import ph5availability
from ph5.core import ph5api


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
        self.assertTrue(('0407', '', 'HHN',
                         1545085230.917, 1545085240.922) in ret)
        #                 1545085230.917, 1545085240.92) in ret)
        self.assertTrue(('0407', '', 'LHN',
                         1545085230.681998, 1545085240.691998) in ret)
        #                 1545085230.681998, 1545085240.69) in ret)
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
        self.assertTrue(('0407', '', 'HHN',
                         1545085230.917, 1545085240.922) in ret)
        #                 1545085230.917, 1545085240.92) in ret)
        self.assertTrue(('0407', '', 'LHN',
                         1545085230.681998, 1545085240.691998) in ret)
        #                 1545085230.681998, 1545085240.69) in ret)
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
        self.assertTrue(('0407', '', 'HHN',
                         1545085230.917, 1545085240.922) in ret)
        #                 1545085230.917, 1545085240.92) in ret)
        self.assertTrue(('0407', '', 'LHN',
                         1545085230.681998, 1545085240.691998) in ret)
        #                 1545085230.681998, 1545085240.69) in ret)
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

    def tearDown(self):
        """
        teardown for tests
        """
        self.ph5_object.close()


if __name__ == "__main__":
    unittest.main()
