'''
Tests for ph5validate
'''
import unittest
import os
import sys

from mock import patch
from testfixtures import OutputCapture

from ph5.utilities import ph5validate, texan2ph5, kef2ph5, initialize_ph5
from ph5.core import ph5api
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


class TestPh5Validate(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestPh5Validate, self).setUp()
        # create master.ph5
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()
        # add data
        testargs = ['texan2ph5', '-n', 'master.ph5', '-r',
                    os.path.join(self.home,
                                 "ph5/test_data/rt125a/I2183RAW.TRD")]
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                texan2ph5.main()
        # add metadata
        testargs = ['kef2ph5', '-n', 'master.ph5', '-k',
                    os.path.join(
                        self.home,
                        "ph5/test_data/metadata/array_t_9_validate.kef")]
        with patch.object(sys, 'argv', testargs):
            kef2ph5.main()

        self.ph5_object = ph5api.PH5(
            nickname='master.ph5', path=self.tmpdir)
        self.ph5validate = ph5validate.PH5Validate(
            self.ph5_object, self.tmpdir, outfile="ph5_validate.log")

    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestPh5Validate, self).tearDown()

    def test_analyze_time(self):
        """
        + check if das_time created has all time and station info
        + check if it catch the case data exists before or after the whole
        time range?
        """
        self.ph5validate.analyze_time()
        self.assertEqual(self.ph5validate.das_time.keys(), [('12183', 1, 500)])
        Dtime = self.ph5validate.das_time[('12183', 1, 500)]

        # 3 different deploy time
        self.assertEqual(len(Dtime['time_windows']), 3)

        # station 9001
        self.assertEqual(Dtime['time_windows'][0],
                         (1550849950, 1550850034, '9001'))
        # station 9002
        self.assertEqual(Dtime['time_windows'][1],
                         (1550850043, 1550850093, '9002'))
        # station 9003
        self.assertEqual(Dtime['time_windows'][2],
                         (1550850125, 1550850187, '9003'))

        self.assertEqual(Dtime['min_deploy_time'],
                         [1550849950,
                          'Data exists before deploy time: 7 seconds.'])

        self.assertEqual(Dtime['max_pickup_time'],
                         [1550850187,
                          'Data exists after pickup time: 2 seconds.'])

    def test_check_station_completeness(self):
        self.ph5validate.das_time = {
            ('12183', 1, 500):
            {'time_windows': [(1550849950, 1550850034, '9001'),
                              (1550850043, 1550850093, '9002'),
                              (1550850125, 1550850187, '9003')],
             'min_deploy_time': [1550849950,
                                 'Data exists before deploy time: 7 seconds.'],
             'max_pickup_time': [1550850187,
                                 'Data exists after deploy time: 2 seconds.']
             }
        }

        self.ph5validate.read_arrays('Array_t_009')
        arraybyid = self.ph5validate.ph5.Array_t['Array_t_009']['byid']
        DT = self.ph5validate.das_time[('12183', 1, 500)]

        # check warning before min_deploy_time
        station = arraybyid.get('9001')[1][0]
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertIn('Data exists before deploy time: 7 seconds.', warnings)

        # check warning after max_pickup_time
        station = arraybyid.get('9003')[1][0]
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertIn('Data exists after deploy time: 2 seconds.', warnings)

        # check warning data after pickup time
        station = arraybyid.get('9002')[1][0]
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertIn('Data exists after pickup time: 36 seconds.', warnings)

        # check error overlaping
        # => change deploy time of the 3rd station
        DT['time_windows'][2] = \
            (1550850090, 1550850187, '9003')
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn('Overlap time on station(s): 9002, 9003', errors)

        # check no data found for array's time
        # => change array's time to where there is no data
        station = arraybyid.get('9003')[1][0]
        station['deploy_time/epoch_l'] = 1550850190
        station['pickup_time/epoch_l'] = 1550850191
        DT['time_windows'][2] = (1550850190, 1550850191, '9003')
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn("No data found for das serial number 12183 during this "
                      "station's time. You may need to reload the raw data "
                      "for this station.",
                      errors)
        # check no data found errors
        station = arraybyid.get('9002')[1][0]
        station['das/serial_number_s'] = '1218'
        self.ph5validate.das_time[('1218', 1, 500)] = \
            self.ph5validate.das_time[('12183', 1, 500)]
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn("No data found for das serial number 1218. "
                      "You may need to reload the raw data for this station.",
                      errors)


if __name__ == "__main__":
    unittest.main()
