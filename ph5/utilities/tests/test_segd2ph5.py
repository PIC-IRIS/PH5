'''
Tests for segd2ph5
'''
import unittest
from ph5.utilities import segd2ph5


class TestSegDtoPH5(unittest.TestCase):
    def test_bit_weights(self):
        # From old
        LSB00 = 2500. / (2 ** 23)  # 0dB
        LSB12 = 625. / (2 ** 23)  # 12dB
        LSB24 = 156. / (2 ** 23)  # 24dB
        LSB36 = 39. / (2 ** 23)  # 36dB = 39mV full scale
        self.assertAlmostEqual(LSB00, segd2ph5.LSB_MAP[0])
        self.assertAlmostEqual(LSB12, segd2ph5.LSB_MAP[12], places=6)
        self.assertAlmostEqual(LSB24, segd2ph5.LSB_MAP[24], places=6)
        self.assertAlmostEqual(LSB36, segd2ph5.LSB_MAP[36], places=6)


if __name__ == "__main__":
    unittest.main()
