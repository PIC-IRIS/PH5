import unittest
import pyproj
from ph5.core.ph5utils import UTMConversions


class TestUTMconversion(unittest.TestCase):

    def test_is_valid_utm_conversion(self):
        u = UTMConversions()  # PIC Socorro
        self.assertAlmostEqual(u.lat_long(322916, 3771967, 13, 'N'),
                         (34.07349577107704, -106.91909595147378))

    def test_is_valid_utm_conversion_south(self):
        u = UTMConversions()  # Castle Rock Antarctica
        self.assertAlmostEqual(u.lat_long(540947, 1361594, 58, 'S'),
                         (-77.81567398301094, 166.73816638798527))

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
