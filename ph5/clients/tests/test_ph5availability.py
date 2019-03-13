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
        self.assertTrue(('8001', '', 'Hl2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # Should return only station 8001
        ret = self.availability.get_slc(station='8001')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 3 entries
        self.assertEqual(3, len(ret))
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'Hl2') in ret)
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
        self.assertTrue(('8001', '', 'Hl2') in ret)
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
        self.assertTrue(('8001', '', 'Hl2') in ret)
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
        self.assertTrue(('8001', '', 'Hl2') in ret)
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
        self.assertTrue(('8001', '', 'Hl2') in ret)
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
        self.assertTrue(('8001', '', 'Hl2') in ret)
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

    def test_get_availability(self):
        """
        test get_availability method
        """

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
            '9001',
            '',
            'DPZ',
            1463568479,
            1463568518)
        self.assertTrue(isinstance(ret, tuple))
        self.assertAlmostEquals(0.9713, ret[0], 4)
        self.assertEqual(8, ret[1])

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
        self.assertTrue(
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
