import unittest
import pyproj
from ph5.core.ph5utils import UTMConversions
from ph5.core.ph5utils import TSPConversions


class TestUTMconversion(unittest.TestCase):

    def test_is_valid_utm_conversion(self):
        u = UTMConversions()  # PIC Socorro
        self.assertAlmostEqual(u.lat_long(322916, 3771967, 13, 'N'),
                               (34.07349577107704, -106.91909595147378))

    def test_is_valid_utm_conversion_south(self):
        u = UTMConversions()  # Castle Rock Antarctica
        self.assertAlmostEqual(u.lat_long(540947, 1361594, 58, 'S'),
                               (-77.81567398301094, 166.73816638798527))

    def test_is_valid_utm_conversion_inverse(self):
        u = UTMConversions()  # PIC Socorro
        self.assertAlmostEqual(u.geod2utm(34.0734958, -106.9190959, 1456.0),
                               (3771967.003118457, 322916.0048106084, 1456.0))

    def test_is_valid_tsp_conversion(self):
        t = TSPConversions()  # Sweetwater, Texas, units US FEET
        self.assertAlmostEqual(t.lat_long(1380811, 6858888),
                               (-100.40568335900281, 32.468972700219375))

    def test_for_correct_type(self):
        with self.assertRaises(ValueError):
            u = UTMConversions()  # 'heck' is not a float
            u.lat_long('heck', 'no', 58, 'S')

    def test_for_correct_value(self):  # 666 is invalid UTM zone
        with self.assertRaises(pyproj.exceptions.CRSError):
            u = UTMConversions()
            u.lat_long(540947, 1361594, 666, 'S')


if __name__ == "__main__":
    unittest.main()
