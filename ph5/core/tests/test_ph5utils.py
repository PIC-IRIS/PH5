'''
Tests for ph5utils
'''
import unittest
from ph5.core import ph5utils
import datetime


class TestPH5Utils(unittest.TestCase):

    def test_is_rect_intersection(self):
        """
        Tests is_rect_intersection()
        """
        latitude = 35.0
        longitude = -106.0
        # exact point
        self.assertTrue(ph5utils.is_rect_intersection(35.0, 35.0,
                                                      -106.0, -106.0,
                                                      latitude, longitude))
        # box around point
        self.assertTrue(ph5utils.is_rect_intersection(34.0, 36.0,
                                                      -107.0, -105.0,
                                                      latitude, longitude))
        # box touching point longitude
        self.assertTrue(ph5utils.is_rect_intersection(34.0, 36.0,
                                                      -107.0, -106.0,
                                                      latitude, longitude))
        # box touching point latitude
        self.assertTrue(ph5utils.is_rect_intersection(35.0, 36.0,
                                                      -108.0, -105.0,
                                                      latitude, longitude))
        # box outside point - latitude too small
        self.assertFalse(ph5utils.is_rect_intersection(31.0, 34.9,
                                                       -107.0, -105.0,
                                                       latitude, longitude))
        # box outside point - latitude too large
        self.assertFalse(ph5utils.is_rect_intersection(35.1, 37.0,
                                                       -108.1, -100.0,
                                                       latitude, longitude))
        # box outside point - longitude too small
        self.assertFalse(ph5utils.is_rect_intersection(33.0, 36.0,
                                                       -120.0, -106.1,
                                                       latitude, longitude))
        # box outside point - longitude too large
        self.assertFalse(ph5utils.is_rect_intersection(34.0, 36.0,
                                                       -105.9, -100.0,
                                                       latitude, longitude))

        # all outside range
        self.assertFalse(ph5utils.is_rect_intersection(0, 0,
                                                       0, 0,
                                                       latitude, longitude))

    def test_is_radial_intersection(self):
        """
        Tests is_radial_intersection()
        """
        # Use IU ANMO as a test case
        latitude = 34.946
        longitude = -106.457
        # point is an exact match to location
        self.assertTrue(ph5utils.is_radial_intersection(34.946, -106.457,
                                                        0, 1,
                                                        latitude, longitude))
        self.assertTrue(ph5utils.is_radial_intersection(34.946, -106.457,
                                                        0, 0,
                                                        latitude, longitude))
        # intersect ANMO
        self.assertTrue(ph5utils.is_radial_intersection(46.195, -121.553,
                                                        0, 17.623,
                                                        latitude, longitude))
        # intersect ANMO no min radius defined
        self.assertTrue(ph5utils.is_radial_intersection(46.195, -121.553,
                                                        None, 17.623,
                                                        latitude, longitude))
        # intersect ANMO with a min radius
        self.assertTrue(ph5utils.is_radial_intersection(35.174, -91.846,
                                                        10, 14.377,
                                                        latitude, longitude))
        # does not intersect ANMO
        self.assertFalse(ph5utils.is_radial_intersection(46.195, -121.553,
                                                         0, 3,
                                                         latitude, longitude))
        self.assertFalse(ph5utils.is_radial_intersection(31.915, -106.282,
                                                         0, 0.752,
                                                         latitude, longitude))
        # min radius is outside ANMO
        self.assertFalse(ph5utils.is_radial_intersection(34.946, -106.457,
                                                         1, 4,
                                                         latitude, longitude))
        # min radius is outside ANMO - no max radius defined
        self.assertFalse(ph5utils.is_radial_intersection(34.946, -106.457,
                                                         1, None,
                                                         latitude, longitude))

        # all outside range
        self.assertFalse(ph5utils.is_radial_intersection(0, 0,
                                                         0, 0,
                                                         latitude, longitude))

    def test_does_pattern_exists(self):
        """
        Tests does_patter_exist
        """

        # match via *
        self.assertTrue(ph5utils.does_pattern_exists(['*'], "Test"))

        # exact match
        self.assertTrue(ph5utils.does_pattern_exists(['Test'], "Test"))

        # match one value of list
        self.assertTrue(ph5utils.does_pattern_exists(['Test', 'random'],
                                                     "Test"))
        # match via ?
        self.assertTrue(ph5utils.does_pattern_exists(['DP?'], 'DPZ'))

        # No match via ?
        self.assertFalse(ph5utils.does_pattern_exists(['DP?'], 'DHZ'))

        # No match multiple patterns
        self.assertFalse(ph5utils.does_pattern_exists(['DPZ', 'XXX', 'test'],
                                                      'DHZ'))

    def test_datestring_to_datetime(self):
        """
        tests datestring_to_datetime
        """

        # bad input string
        with self.assertRaises(ValueError):
            ph5utils.datestring_to_datetime("Bad string")

        # bad input not string or unicode
        with self.assertRaises(ValueError):
            ph5utils.datestring_to_datetime(int(19))

        # %Y:%j:%H:%M:%S.%f good
        ret = ph5utils.datestring_to_datetime(
            "2019:01:23:59:59.999")
        self.assertTrue(ret)
        self.assertTrue(type(ret) is datetime.datetime)

        # %Y:%j:%H:%M:%S.%f < 1900
        with self.assertRaises(ValueError):
            ret = ph5utils.datestring_to_datetime(
                "1899:01:23:59:59.999")

        # %Y-%m-%dT%H:%M:%S.%f good
        ret = ph5utils.datestring_to_datetime(
            "2019-01-01T23:59:59.999")
        self.assertTrue(ret)
        self.assertTrue(type(ret) is datetime.datetime)

        # %Y-%m-%dT%H:%M:%S.%f < 1900
        with self.assertRaises(ValueError):
            ret = ph5utils.datestring_to_datetime(
                "1777-01-01T23:59:59.999")

        # %Y-%m-%dT%H:%M:%S good
        ret = ph5utils.datestring_to_datetime(
            "2019-01-01T23:59:59")
        self.assertTrue(ret)
        self.assertTrue(type(ret) is datetime.datetime)

        # %Y-%m-%dT%H:%M:%S < 1900
        with self.assertRaises(ValueError):
            ret = ph5utils.datestring_to_datetime(
                "1777-01-01T23:59:59")

        # %Y-%m-%d good
        ret = ph5utils.datestring_to_datetime(
            "2019-01-01")
        self.assertTrue(ret)
        self.assertTrue(type(ret) is datetime.datetime)

        # %Y-%m-%d < 1900
        with self.assertRaises(ValueError):
            ret = ph5utils.datestring_to_datetime(
                "1777-01-01")

        # already a datetime object
        ret1 = ph5utils.datestring_to_datetime(ret)
        self.assertEqual(ret1, ret)

    def test_fdsntime_to_epoch(self):
        """
        tests  fdsntime_to_epoch
        """

        # bad
        with self.assertRaises(ValueError):
            ret = ph5utils.fdsntime_to_epoch("test")

        # Good %Y-%m-%dT%H:%M:%S.%f
        ret = ph5utils.fdsntime_to_epoch(
            "2018-03-09T23:01:01.987")
        self.assertTrue(ret)
        self.assertTrue(type(ret) is float)
        self.assertEqual(ret, 1520636461.987)

        # Good %Y-%m-%dT%H:%M:%S.%f
        ret = ph5utils.fdsntime_to_epoch(
            "2018-03-09T23:01:01.000")
        self.assertTrue(ret)
        self.assertTrue(type(ret) is float)
        self.assertEqual(ret, 1520636461.000)

    def test_doy_breakup(self):
        """
        tests doy_breakup
        """

        # Good non decimal
        stop, seconds = ph5utils.doy_breakup(
            1552754922,
            length=86400)
        self.assertTrue(stop)
        self.assertTrue(seconds)
        self.assertEqual(stop, 1552841322)
        self.assertEqual(seconds, 86400)

        # Good decimal
        stop, seconds = ph5utils.doy_breakup(
            1552754922.787,
            length=86400)
        self.assertTrue(stop)
        self.assertTrue(seconds)
        self.assertAlmostEqual(stop, 1552841322.787, 3)
        self.assertAlmostEqual(seconds, 86400, 1)

        # Good non decimal different length
        stop, seconds = ph5utils.doy_breakup(
            1552754922,
            length=3600)
        self.assertTrue(stop)
        self.assertTrue(seconds)
        self.assertEqual(stop, 1552758522)
        self.assertEqual(seconds, 3600)

        # Good decimal different length
        stop, seconds = ph5utils.doy_breakup(
            1552754922.787,
            length=3600)
        self.assertTrue(stop)
        self.assertTrue(seconds)
        self.assertAlmostEqual(stop, 1552758522.787, 3)
        self.assertAlmostEqual(seconds, 3600, 1)

        # bad input
        with self.assertRaises(ValueError):
            ph5utils.doy_breakup(
                "MMM",
                length=3600)

        # bad input
        with self.assertRaises(ValueError):
            ph5utils.doy_breakup(
                1552754922.787,
                length="threeve")

    def test_inday_breakup(self):
        """
        test inday_breakup
        """

        # bad input
        with self.assertRaises(ValueError):
            ph5utils.inday_breakup("BAD!")

        midnight, seconds = ph5utils.inday_breakup(
            1552758522.787)
        self.assertTrue(midnight)
        self.assertTrue(seconds)
        self.assertEqual(midnight, 1552780800)
        self.assertAlmostEqual(seconds, 22277.213, 3)

    def test_microsecs_to_sec(self):
        """
        test microsecs_to_sec
        """

        # bad
        with self.assertRaises(ValueError):
            ph5utils.microsecs_to_sec("1234")
        ret = ph5utils.microsecs_to_sec(12345)
        self.assertTrue(ret)
        self.assertAlmostEqual(ret, 0.012345, 6)

    def test_PH5ResponseManager(self):
        """
        tests PH5ResponseManager class and methods
        """


if __name__ == "__main__":
    unittest.main()
