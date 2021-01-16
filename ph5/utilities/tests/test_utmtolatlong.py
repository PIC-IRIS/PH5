import unittest
import pyproj
from ph5.core.ph5utils import lat_lon_to_utm
from ph5.core.ph5utils import utm_to_lat_lon
from ph5.core.ph5utils import lat_lon_elev_to_utm
from ph5.core.ph5utils import tspc_lat_lon
from ph5.core.ph5utils import lat_lon_to_geod
from ph5.core.ph5utils import lat_lon_to_ups_north
from ph5.core.ph5utils import lat_lon_to_ups_south
from ph5.core.ph5utils import ups_north_to_lat_lon
from ph5.core.ph5utils import ups_south_to_lat_lon


PROG_VERSION = '2020.091'


class TestUTMconversion(unittest.TestCase):

    def test_is_valid_utm_conversion_north(self):
        # location: PIC
        lat, lon = utm_to_lat_lon(3771967, 322916, 'N', 13)
        self.assertAlmostEqual(lat, 34.07349577107704)
        self.assertAlmostEqual(lon, -106.91909595147378)

    def test_is_valid_utm_conversion_south(self):
        # location: Castle Rock, Antarctica
        lat, lon = utm_to_lat_lon(1361594, 540947, 'S', 58)
        self.assertAlmostEqual(lat, -77.81567398301094)
        self.assertAlmostEqual(lon, 166.73816638798527)

    def test_for_correct_type(self):
        # heck, no are invalid eastings/northings
        with self.assertRaises(ValueError):
            lat, lon = utm_to_lat_lon('heck', 'no', 'S', 58)

    def test_for_correct_value(self):
        # 666 is invalid UTM zone
        with self.assertRaises(pyproj.exceptions.CRSError):
            lat, lon = utm_to_lat_lon(1361594, 540947, 'S', 666)

    def test_is_valid_geod_conversion(self):
        # location: PIC
        northing, easting, elev =\
            lat_lon_elev_to_utm(34.0734958, -106.9190959, 1456.0)
        self.assertAlmostEqual(northing, 3771967.003118457)
        self.assertAlmostEqual(easting, 322916.0048106084)
        self.assertAlmostEqual(elev, 1456.0)

    def test_is_valid_utm_latlong_conversion_north(self):
        # location: PIC
        northing, easting, zone, hemisphere =\
                 lat_lon_to_utm(34.0734958, -106.9190959)
        self.assertAlmostEqual(northing, 3771967.003118457)
        self.assertAlmostEqual(easting, 322916.0048106084)
        self.assertEqual(zone, 13)
        self.assertAlmostEqual(hemisphere, 'N')

    def test_is_valid_utm_latlong_conversion_south(self):
        # location: Castle Rock Antarctica
        northing, easting, zone, hemisphere =\
            lat_lon_to_utm(-77.81567398301094, 166.73816638798527)
        self.assertAlmostEqual(northing, 1361594.0)
        self.assertAlmostEqual(easting, 540947.0)
        self.assertEqual(zone, 58)
        self.assertAlmostEqual(hemisphere, 'S')

    def test_is_valid_tsp_conversion(self):
        # Sweetwater, Texas, units US FEET
        lat, lon = tspc_lat_lon(6858888, 1380811)
        self.assertAlmostEqual(lat, 32.468972700219375)
        self.assertAlmostEqual(lon, -100.40568335900281)

    def test_is_valid_lat_lon_to_geod_conversion(self):
        # socorro to albuquerque in miles
        az, baz, dist = lat_lon_to_geod(34.0543, -106.907,
                                        35.1053, -106.646,
                                        1609.344)
        self.assertAlmostEqual(az, 11.533074930503515)
        self.assertAlmostEqual(baz, -168.3187871800244)
        self.assertAlmostEqual(dist, 73.95826059337135)

    def test_is_valid_ups_conversion_north(self):
        lat, lon = ups_north_to_lat_lon(1500000.0, 2500000.0)
        self.assertAlmostEqual(lat, 83.63731756105707)
        self.assertAlmostEqual(lon, 45.0)

    def test_is_valid_ups_conversion_south(self):
        lat, lon = ups_south_to_lat_lon(1500000.0, 2500000.0)
        self.assertAlmostEqual(lat, -83.63731756105707)
        self.assertAlmostEqual(lon, 135.0)

    def test_is_valid_ups_latlong_conversion_north(self):
        northing, easting = lat_lon_to_ups_north(83.63731756105707, 135.)
        self.assertAlmostEqual(northing, 2500000.0)
        self.assertAlmostEqual(easting, 2500000.0)

    def test_is_valid_ups_latlong_conversion_south(self):
        northing, easting = lat_lon_to_ups_south(-83.63731756105707, 45.)
        self.assertAlmostEqual(northing, 2500000.0)
        self.assertAlmostEqual(easting, 2500000.0)


if __name__ == "__main__":
    unittest.main()
