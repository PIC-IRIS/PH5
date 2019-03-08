'''
Tests for ph5api
'''

import unittest
from ph5.core import ph5api


class TestPH5API(unittest.TestCase):

    def setup(self):
        self.ph5API_object = None

    def test_load_ph5(self):
        """
        Tries to load the PH5 test file.
        Checks if it is an instance of ph5.core.ph5api.PH5
        """

        self.ph5API_object = ph5api.PH5(path='ph5/test_data/ph5',
                                        nickname='master.ph5')
        self.assertTrue(isinstance(self.ph5API_object, ph5api.PH5))


if __name__ == "__main__":
    unittest.main()
