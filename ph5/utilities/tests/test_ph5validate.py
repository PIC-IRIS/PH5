'''
Tests for ph5validate
'''
import unittest
import os
import sys

from mock import patch
from testfixtures import OutputCapture

from ph5.utilities import ph5validate
from ph5.core import ph5api
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase, kef_to_ph5


class TestPh5Validate_main(TempDirTestCase, LogTestCase):

    def test_main(self):
        kef_to_ph5(
            self.tmpdir, 'master.ph5',
            os.path.join(self.home, 'ph5/test_data'),
            ['rt125a/das_t_12183.kef', 'metadata/array_t_9_validate.kef'],
            das_sn_list=['12183'])
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARNING']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                ph5validate.main()
        with open('ph5_validate.log') as f:
            all_logs = f.read().split("-=-=-=-=-=-=-=-=-\n")

        self.assertEqual(
            all_logs[2],
            'ERROR: Experiment_t does not exist. '
            'run experiment_t_gen to create table\n')
        self.assertEqual(
            all_logs[3],
            'Station 9001 Channel 1\n1 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[4],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'WARNING: No station description found.\n'
            'WARNING: Data exists before deploy time: 7 seconds.\n')
        self.assertEqual(
            all_logs[5],
            'Station 9002 Channel 1\n1 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[6],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'WARNING: No station description found.\n'
            'WARNING: Data exists after pickup time: 36 seconds.\n')
        self.assertEqual(
            all_logs[7],
            'Station 9003 Channel 1\n1 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[8],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'WARNING: No station description found.\n'
            'WARNING: Data exists after pickup time: 2 seconds.\n')

    def test_get_args(self):
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARNING']
        with patch.object(sys, 'argv', testargs):
            ret = ph5validate.get_args()
        self.assertEqual(ret.level, 'WARNING')
        self.assertEqual(ret.nickname, 'master.ph5')
        self.assertEqual(ret.outfile, 'ph5_validate.log')
        self.assertEqual(ret.ph5path, self.tmpdir)
        self.assertEqual(ret.verbose, False)


class TestPh5Validate(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestPh5Validate, self).setUp()
        kef_to_ph5(
            self.tmpdir, 'master.ph5',
            os.path.join(self.home, 'ph5/test_data'),
            ['rt125a/das_t_12183.kef', 'metadata/array_t_9_validate.kef'],
            das_sn_list=['12183'])
        self.ph5_object = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(
            self.ph5_object, self.tmpdir, "WARNING",
            outfile="ph5_validate.log")

    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestPh5Validate, self).tearDown()

    def test_analyze_time(self):
        """
        + check if das_time created has all time and station info
        + check if it catch the case data exists before the whole time range
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

    def test_check_station_completeness(self):
        self.ph5validate.das_time = {
            ('12183', 1, 500):
            {'time_windows': [(1550849950, 1550850034, '9001'),
                              (1550850043, 1550850093, '9002'),
                              (1550850125, 1550850187, '9003')],
             'min_deploy_time': [1550849950,
                                 'Data exists before deploy time: 7 seconds.'],
             }
        }

        self.ph5validate.read_arrays('Array_t_009')
        arraybyid = self.ph5validate.ph5.Array_t['Array_t_009']['byid']
        DT = self.ph5validate.das_time[('12183', 1, 500)]

        #
        # check warning Data exist before min_deploy_time
        station = arraybyid.get('9001')[1][0]
        station['location/X/value_d'] = 190.0
        station['location/X/units_s'] = 'degrees'
        station['location/Y/value_d'] = -100.0
        station['location/Y/units_s'] = 'degrees'
        station['location/Z/value_d'] = 1403
        station['location/Z/units_s'] = 'm'
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertEqual(warnings,
                         ['No station description found.',
                          'Channel longitude 190.0 not in range [-180,180]',
                          'Channel latitude -100.0 not in range [-90,90]',
                          'Data exists before deploy time: 7 seconds.'])

        # check warning data after pickup time
        station = arraybyid.get('9002')[1][0]
        station['location/X/value_d'] = 0
        station['location/X/units_s'] = ''
        station['location/Y/value_d'] = 0
        station['location/Y/units_s'] = None
        station['location/Z/value_d'] = None
        station['location/Z/units_s'] = ''
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertEqual(
            warnings,
            ['No station description found.',
             'Channel longitude seems to be 0. Is this correct???',
             'No Station location/X/units_s value found.',
             'Channel latitude seems to be 0. Is this correct???',
             'No Station location/Y/units_s value found.',
             'No Channel location/Z/value_d value found.',
             'No Station location/Z/units_s value found.',
             'Data exists after pickup time: 36 seconds.'])

        # check error overlaping
        # => change deploy time of the 3rd station
        DT['time_windows'][2] = (1550850090, 1550850187, '9003')
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
        self.ph5validate.das_time[
            ('1218', 1, 500)] = self.ph5validate.das_time[('12183', 1, 500)]
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn("No data found for das serial number 1218. "
                      "You may need to reload the raw data for this station.",
                      errors)


if __name__ == "__main__":
    unittest.main()
