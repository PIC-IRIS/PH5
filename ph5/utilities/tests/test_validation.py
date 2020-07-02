'''
Tests for validation
'''
import unittest

from ph5.utilities import validation


class TestValidation(unittest.TestCase):
    def test_check_lat_lon_elev(self):
        station = {'location/X/value_d': 100.0,
                   'location/X/units_s': 'degrees',
                   'location/Y/value_d': 70.0,
                   'location/Y/units_s': 'degrees',
                   'location/Z/value_d': 1047,
                   'location/Z/units_s': 'm'}
        errors = []
        warnings = []
        validation.check_lat_lon_elev(station, errors, warnings)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

        station = {'location/X/value_d': 190.0,
                   'location/X/units_s': '',
                   'location/Y/value_d': -100.0,
                   'location/Y/units_s': '',
                   'location/Z/value_d': '',
                   'location/Z/units_s': ''}
        validation.check_lat_lon_elev(station, errors, warnings)
        self.assertEqual(
            errors,
            ['Channel longitude 190.0 not in range [-180,180]',
             'Channel latitude -100.0 not in range [-90,90]',
             'No Channel location/Z/value_d value found.'])
        self.assertEqual(
            warnings,
            ['No Station location/X/units_s value found.',
             'No Station location/Y/units_s value found.',
             'No Station location/Z/units_s value found.'])
        errors = []
        warnings = []
        station = {'location/X/value_d': 'ABC',
                   'location/X/units_s': '',
                   'location/Y/value_d': '',
                   'location/Y/units_s': '',
                   'location/Z/value_d': '',
                   'location/Z/units_s': ''}
        validation.check_lat_lon_elev(station, errors, warnings)
        self.assertEqual(
            errors,
            ['Channel longitude ABC is not a number.',
             'No Channel latitude value found.',
             'No Channel location/Z/value_d value found.'])
        self.assertEqual(
            warnings,
            ['No Station location/X/units_s value found.',
             'No Station location/Y/units_s value found.',
             'No Station location/Z/units_s value found.'])

        errors = []
        warnings = []
        station = {'location/X/value_d': 0,
                   'location/X/units_s': None,
                   'location/Y/value_d': None,
                   'location/Y/units_s': None,
                   'location/Z/value_d': None,
                   'location/Z/units_s': None}
        validation.check_lat_lon_elev(station, errors, warnings)
        self.assertEqual(
            errors,
            ['No Channel latitude value found.',
             'No Channel location/Z/value_d value found.'])
        self.assertEqual(
            warnings,
            ['Channel longitude seems to be 0. Is this correct???',
             'No Station location/X/units_s value found.',
             'No Station location/Y/units_s value found.',
             'No Station location/Z/units_s value found.'])


if __name__ == "__main__":
    unittest.main()
