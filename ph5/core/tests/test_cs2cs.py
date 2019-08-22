"""
unit tests for ph5availability
"""

import unittest
from ph5.core import cs2cs


class Test_cs2cs(unittest.TestCase):
    print("test cs2cs's methods")

    def test__sign(self):
        """
        test _sign method
        """
        # start with N/S/E/W
        ret = cs2cs._sign('N34.023786', 'lon')
        self.assertEqual(ret, 'N34.023786')

        ret = cs2cs._sign('-106.898492', 'lat')
        self.assertEqual(ret, 'S106.898492')

        ret = cs2cs._sign('106.898492', 'lat')
        self.assertEqual(ret, 'N106.898492')

        ret = cs2cs._sign('+106.898492', 'lat')
        self.assertEqual(ret, 'N106.898492')

        ret = cs2cs._sign('-34.0237862', 'lon')
        self.assertEqual(ret, 'W34.0237862')

        ret = cs2cs._sign('34.0237862', 'lon')
        self.assertEqual(ret, 'E34.0237862')

        ret = cs2cs._sign('+34.0237862', 'lon')
        self.assertEqual(ret, 'E34.0237862')

    def test_lon2zone(self):
        """
        test lon2zone method
        """
        ret = cs2cs.lon2zone(-106.898492)
        self.assertEqual(ret, 13)

        # lon not in -180 to 174
        ret = cs2cs.lon2zone(179)
        self.assertIsNone(ret)

    def test_utm2geod_geod2utm(self):
        """
        test utm2geod
        """
        lat = 34.023786
        lon = -106.898492
        elev = 1456.0
        zone = 13

        Y, X, Z = cs2cs.geod2utm(None, 'WGS84', lat, lon, elev)
        self.assertAlmostEqual(Y, 3766418.5935, 3)
        self.assertAlmostEqual(X, 324715.1719, 3)
        self.assertEqual(Z, elev)

        Y, X, Z = cs2cs.geod2utm(zone, 'WGS84', lat, lon, elev)
        self.assertAlmostEqual(Y, 3766418.5935, 3)
        self.assertAlmostEqual(X, 324715.1719, 3)
        self.assertEqual(Z, elev)

        lat1, lon1, elev1 = cs2cs.utm2geod(zone, 'WGS84', X, Y, Z)
        self.assertAlmostEqual(lat1, lat)
        self.assertAlmostEqual(lon1, lon)
        self.assertEqual(elev1, elev)


if __name__ == "__main__":
    unittest.main()
