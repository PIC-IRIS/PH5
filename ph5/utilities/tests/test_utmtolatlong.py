import unittest
import pyproj
from ph5.core.ph5utils import LatLongToUtmConvert
from ph5.core.ph5utils import utm_to_lat_long
from ph5.core.ph5utils import tspc_lat_long


class TestUTMconversion(unittest.TestCase):

    def test_is_valid_utm_conversion(self):
        # location: PIC
        lat, lon = utm_to_lat_long(322916, 3771967, 'N', 13)
        self.assertAlmostEqual(lat, 34.07349577107704)
        self.assertAlmostEqual(lon, -106.91909595147378)

    def test_is_valid_utm_conversion_south(self):
        # location: Castle Rock, Antarctica
        lat, lon = utm_to_lat_long(540947, 1361594, 'S', 58)
        self.assertAlmostEqual(lat, -77.81567398301094)
        self.assertAlmostEqual(lon, 166.73816638798527)

    def test_for_correct_type(self):
        # heck, no are invalid eastings/northings
        with self.assertRaises(ValueError):
            lat, lon = utm_to_lat_long('heck', 'no', 'S', 58)

    def test_for_correct_value(self):
        # 666 is invalid UTM zone
        with self.assertRaises(pyproj.exceptions.CRSError):
            lat, lon = utm_to_lat_long(540947, 1361594, 'S', 666)

    def test_is_valid_geod_conversion(self):
        # location: PIC
        u = LatLongToUtmConvert(34.0734958, -106.9190959)
        northing, easting, elev = u.geod_to_utm(1456.0)
        self.assertAlmostEqual(northing, 3771967.003118457)
        self.assertAlmostEqual(easting, 322916.0048106084)
        self.assertAlmostEqual(elev, 1456.0)

    def test_is_valid_latlong_conversion(self):
        # location: PIC
        u = LatLongToUtmConvert(34.0734958, -106.9190959)
        easting, northing, zone, hemisphere = u.lat_long_to_utm()
        self.assertAlmostEqual(easting, 322916.0048106084)
        self.assertAlmostEqual(northing, 3771967.003118457)
        self.assertEqual(zone, 13)
        self.assertAlmostEqual(hemisphere, 'N')

    def test_is_valid_tsp_conversion(self):
        # Sweetwater, Texas, units US FEET
        lon, lat = tspc_lat_long(1380811, 6858888)
        self.assertAlmostEqual(lon, -100.40568335900281)
        self.assertAlmostEqual(lat, 32.468972700219375)


if __name__ == "__main__":
    unittest.main()
