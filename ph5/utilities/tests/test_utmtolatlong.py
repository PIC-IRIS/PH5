import unittest
import pyproj
from ph5.core.ph5utils import UTMConversions
from ph5.core.ph5utils import tspc_lat_long


class TestUTMconversion(unittest.TestCase):

    def test_is_valid_utm_conversion(self):
        u = UTMConversions(None, None, 'N', 13)  # PIC Socorro
        lat, lon = u.utm2latlong(322916, 3771967)
        self.assertAlmostEqual(lat, 34.07349577107704)
        self.assertAlmostEqual(lon, -106.91909595147378)

    def test_is_valid_utm_conversion_south(self):
        u = UTMConversions(None, None, 'S', 58)  # Castle Rock Antarctica
        lat, lon = u.utm2latlong(540947, 1361594)
        self.assertAlmostEqual(lat, -77.81567398301094)
        self.assertAlmostEqual(lon, 166.73816638798527)

    def test_is_valid_utm_conversion_inverse(self):
        u = UTMConversions(34.0734958, -106.9190959, None, None)  # PIC
        northing, easting, elev = u.geod2utm(34.0734958, -106.9190959, 1456.0)
        self.assertAlmostEqual(northing, 3771967.003118457)
        self.assertAlmostEqual(easting, 322916.0048106084)

    def test_is_valid_utm_conversion_fancyinverse(self):
        u = UTMConversions(34.0734958, -106.9190959, None, None)  # PIC
        easting, northing, zone, hemisphere = \
            u.latlong2utm(34.0734958, -106.9190959)
        self.assertAlmostEqual(easting, 322916.0048106084)
        self.assertAlmostEqual(northing, 3771967.003118457)
        self.assertEqual(zone, 13)
        self.assertAlmostEqual(hemisphere, 'N')

    def test_is_valid_tsp_conversion(self):
        # Sweetwater, Texas, units US FEET
        lon, lat = tspc_lat_long(1380811, 6858888)
        self.assertAlmostEqual(lon, -100.40568335900281)
        self.assertAlmostEqual(lat, 32.468972700219375)

    def test_for_correct_type(self):
        with self.assertRaises(ValueError):
            u = UTMConversions('heck', 'no', 'S', 58)  # 'heck' is not a float
            u.utm2latlong('heck', 'no')

    def test_for_correct_value(self):  # 666 is invalid UTM zone
        with self.assertRaises(pyproj.exceptions.CRSError):
            u = UTMConversions(None, None, 'S', 666)
            u.utm2latlong(540947, 1361594)


if __name__ == "__main__":
    unittest.main()
