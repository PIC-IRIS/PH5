"""
unit tests for ph5availability
"""

import unittest
from ph5.core import decimate
import math as m


class Test_decimate(unittest.TestCase):
    print("test cs2cs's methods")

    def test_decimate(self):
        """
        test decimate method
        """
        ts = []
        # build a 36000 sample sine wave
        for i in range(72):
            val = int(m.sin(m.radians(i)) * 1000.)
            ts.append(val)

        # Decimate by a factor of 2 X 4 X 5 = 40
        shift, data = decimate.decimate('2,4,5', ts)
        self.assertEqual(shift, 8)
        self.assertEqual(data, [74, 664])


if __name__ == "__main__":
    unittest.main()
