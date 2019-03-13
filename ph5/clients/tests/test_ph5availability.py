"""
unit tests for ph5availability
"""

import unittest
from ph5.clients import ph5availability
from ph5.core import ph5api


class TestPH5Availability(unittest.TestCase):

    def setUp(self):
        """
        setup for tests
        """
        self.ph5_object = ph5api.PH5(
            path='ph5/test_data/ph5',
            nickname='master.ph5')
        self.availability = ph5availability.PH5Availability(
            self.ph5_object)

    def test_get_slc(self):
        """
        test get_slc method
        """

    def test_get_availability_extent(self):
        """
        test get_availability_extent method
        """

    def test_get_availability(self):
        """
        test get_availability method
        """

    def test_get_availability_percentage(self):
        """
        test get_availability_percentage method
        """

    def test_has_data(self):
        """
        test has_data method
        """

    def tearDown(self):
        """
        teardown for tests
        """
        self.ph5_object.close()


if __name__ == "__main__":
    unittest.main()