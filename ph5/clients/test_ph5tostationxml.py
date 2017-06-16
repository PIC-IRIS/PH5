'''
Tests for ph5tostationxml
'''
import unittest
from ph5tostationxml import PH5toStationXML


class TestPH5toStationXML(unittest.TestCase):

    def test_is_rect_intersection(self):
        """
        Tests is_rect_intersection()
        """
        latitude = 35.0
        longitude = -106.0
        # exact point
        self.assertTrue(PH5toStationXML.is_rect_intersection(35.0, 35.0,
                                                             -106.0, -106.0,
                                                             latitude, longitude))
        # box around point
        self.assertTrue(PH5toStationXML.is_rect_intersection(34.0, 36.0,
                                                             -107.0, -105.0,
                                                             latitude, longitude))
        # box touching point longitude
        self.assertTrue(PH5toStationXML.is_rect_intersection(34.0, 36.0,
                                                             -107.0, -106.0,
                                                             latitude, longitude))
        # box touching point latitude
        self.assertTrue(PH5toStationXML.is_rect_intersection(35.0, 36.0,
                                                             -108.0, -105.0,
                                                             latitude, longitude))
        # box outside point - latitude too small
        self.assertFalse(PH5toStationXML.is_rect_intersection(31.0, 34.9,
                                                             -107.0, -105.0,
                                                             latitude, longitude))
        # box outside point - latitude too large
        self.assertFalse(PH5toStationXML.is_rect_intersection(35.1, 37.0,
                                                             -108.1, -100.0,
                                                             latitude, longitude))
        # box outside point - longitude too small
        self.assertFalse(PH5toStationXML.is_rect_intersection(33.0, 36.0,
                                                             -120.0, -106.1,
                                                             latitude, longitude))
        # box outside point - longitude too large
        self.assertFalse(PH5toStationXML.is_rect_intersection(34.0, 36.0,
                                                             -105.9, -100.0,
                                                             latitude, longitude))

    def test_is_radial_intersection(self):
        """
        Tests is_radial_intersection()
        """
        # Use IU ANMO as a test case
        latitude = 34.946
        longitude = -106.457
        # point is an exact match to location
        self.assertTrue(PH5toStationXML.is_radial_intersection(34.946, -106.457,
                                                               0, 1,
                                                               latitude, longitude))
        self.assertTrue(PH5toStationXML.is_radial_intersection(34.946, -106.457,
                                                               0, 0,
                                                               latitude, longitude))
        # intersect ANMO
        self.assertTrue(PH5toStationXML.is_radial_intersection(46.195, -121.553,
                                                       0, 17.623,
                                                       latitude, longitude))
        # intersect ANMO no min radius defined
        self.assertTrue(PH5toStationXML.is_radial_intersection(46.195, -121.553,
                                                       None, 17.623,
                                                       latitude, longitude))
        # intersect ANMO with a min radius
        self.assertTrue(PH5toStationXML.is_radial_intersection(35.174, -91.846,
                                                       10, 14.377,
                                                       latitude, longitude))
        # does not intersect ANMO
        self.assertFalse(PH5toStationXML.is_radial_intersection(46.195, -121.553,
                                                       0, 3,
                                                       latitude, longitude))
        self.assertFalse(PH5toStationXML.is_radial_intersection(31.915, -106.282,
                                               0, 0.752,
                                               latitude, longitude))
        # min radius is outside ANMO
        self.assertFalse(PH5toStationXML.is_radial_intersection(34.946, -106.457,
                                                               1, 4, 
                                                               latitude, longitude))
        # min radius is outside ANMO - no max radius defined
        self.assertFalse(PH5toStationXML.is_radial_intersection(34.946, -106.457,
                                                       1, None,
                                                       latitude, longitude))

if __name__ == "__main__":
    unittest.main()
