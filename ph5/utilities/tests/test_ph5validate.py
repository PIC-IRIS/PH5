'''
Tests for ph5validate
'''
import unittest
import os
import sys
import logging

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.utilities import ph5validate, segd2ph5
from ph5.core import ph5api
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase, kef_to_ph5


class TestPH5Validate_response(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5Validate_response, self).setUp()
        ph5path = os.path.join(self.home, "ph5/test_data/ph5")
        self.ph5API_object = ph5api.PH5(path=ph5path, nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(self.ph5API_object, '.')
        self.resp_check_info = [
            {'n_i': 0, 'array': '001', 'sta': '500',
             'cha_code': 'DP1', 'spr': 500, 'sprm': 1, 'cha_id': 1,
             'smodel': '', 'dmodel': 'ZLAND 3C'},
            {'n_i': 0, 'array': '001', 'sta': '500',
             'cha_code': 'DP2', 'spr': 500, 'sprm': 1, 'cha_id': 2,
             'smodel': '', 'dmodel': 'ZLAND 3C'},
            {'n_i': 0, 'array': '001', 'sta': '500',
             'cha_code': 'DPZ', 'spr': 500, 'sprm': 1, 'cha_id': 3,
             'smodel': '', 'dmodel': 'ZLAND 3C'},
            {'n_i': 5, 'array': '002', 'sta': '0407',
             'cha_code': 'HHN', 'spr': 200, 'sprm': 1, 'cha_id': 1,
             'smodel': 'None CMG-3T', 'dmodel': 'None Q330'},
            {'n_i': 6, 'array': '003', 'sta': '0407',
             'cha_code': 'LHN', 'spr': 100, 'sprm': 1, 'cha_id': 1,
             'smodel': 'None CMG-3T', 'dmodel': 'None Q330'},
            {'n_i': -1, 'array': '004', 'sta': '0407',
             'cha_code': 'LOG', 'spr': 0, 'sprm': 1, 'cha_id': -2,
             'smodel': 'None CMG-3T', 'dmodel': 'None Q330'},
            {'n_i': 1, 'array': '008', 'sta': '8001',
             'cha_code': 'HLZ', 'spr': 100, 'sprm': 1, 'cha_id': 1,
             'smodel': 'cmg-3t', 'dmodel': 'rt130'},
            {'n_i': 2, 'array': '008', 'sta': '8001',
             'cha_code': 'HL1', 'spr': 100, 'sprm': 1, 'cha_id': 2,
             'smodel': 'cmg-3t', 'dmodel': 'rt130'},
            {'n_i': 3, 'array': '008', 'sta': '8001',
             'cha_code': 'HL2', 'spr': 100, 'sprm': 1, 'cha_id': 3,
             'smodel': 'cmg-3t', 'dmodel': 'rt130'},
            {'n_i': 4, 'array': '009', 'sta': '9001',
             'cha_code': 'DPZ', 'spr': 500, 'sprm': 1, 'cha_id': 1,
             'smodel': 'gs11v', 'dmodel': 'rt125a'}]

    def tearDown(self):
        self.ph5API_object.close()
        super(TestPH5Validate_response, self).tearDown()

    def test_check_array_t(self):
        vb_array, resp_check_info = self.ph5validate.check_array_t()
        self.assertEqual(resp_check_info, self.resp_check_info)

    def test_check_response_t(self):
        self.resp_check_info[9]['spr'] = 100
        self.resp_check_info[9]['smodel'] = 'cmg3t'

        errors = {'array 004, station 0407, channel -2, response_table_n_i -1:'
                  ' Metadata response with n_i=-1 has no response data.'}
        warnings = {
            "array 009, station 9001, channel 1, response_table_n_i 4: "
            "response_file_sensor_a 'gs11v' is inconsistence with "
            "model(s) cmg3t.",
            "array 009, station 9001, channel 1, response_table_n_i 4: "
            "response_file_das_a 'rt125a_500_1_32' is inconsistence with "
            "model(s) 'cmg3t' and 'rt125a'; sr=100 srm=1 gain=32 'cha=DPZ'."}
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            ret = self.ph5validate.check_response_t(self.resp_check_info)
            self.assertEqual(set(ret[0].error), errors)
            self.assertEqual(set(ret[0].warning), warnings)
            # check_response_t only print logs to file, not stdout
            self.assertEqual(len(log.records), 0)
            self.assertEqual(ret[0].heading,
                             "-=-=-=-=-=-=-=-=-\n"
                             "Response_t\n"
                             "1 error, 2 warning, 0 info\n"
                             "-=-=-=-=-=-=-=-=-\n"
                             )


class TestPh5Validate_main_detect_data(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestPh5Validate_main_detect_data, self).setUp()
        kef_to_ph5(
            self.tmpdir, 'master.ph5',
            os.path.join(self.home, 'ph5/test_data'),
            ['rt125a/das_t_12183.kef', 'metadata/array_t_9_validate.kef'],
            das_sn_list=['12183'])

    def test_main(self):
        # test invalid level
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARN']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                self.assertRaises(SystemExit, ph5validate.main)
                output = out.captured.strip().split('\n')
        self.assertEqual(
            output[1],
            "ph5_validate: error: argument -l/--level: invalid choice: "
            "'WARN' (choose from 'ERROR', 'WARNING', 'INFO')")

        # test WARNING level
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
            'Station 9001 Channel 1\n1 error, 3 warning, 0 info\n')
        self.assertEqual(
            all_logs[4],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'WARNING: No station description found.\n'
            'WARNING: Data exists before deploy time: 7 seconds.\n'
            'WARNING: Station 9001 [1550849950, 1550850034] is repeated '
            '2 time(s)\n')
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

        # test ERROR level
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'ERROR']
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
            'Station 9001 Channel 1\n1 error, 3 warning, 0 info\n')
        self.assertEqual(
            all_logs[4],
            'ERROR: No Response table found. Have you run resp_load yet?\n')
        self.assertEqual(
            all_logs[5],
            'Station 9002 Channel 1\n1 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[6],
            'ERROR: No Response table found. Have you run resp_load yet?\n')
        self.assertEqual(
            all_logs[7],
            'Station 9003 Channel 1\n1 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[8],
            'ERROR: No Response table found. Have you run resp_load yet?\n')

    def test_get_args(self):
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARN']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                self.assertRaises(SystemExit, ph5validate.get_args)
        output = out.captured.strip().split('\n')
        self.assertEqual(
            output[1],
            "ph5_validate: error: argument -l/--level: invalid choice: "
            "'WARN' (choose from 'ERROR', 'WARNING', 'INFO')")

        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARNING']
        with patch.object(sys, 'argv', testargs):
            ret = ph5validate.get_args()
        self.assertEqual(ret.level, 'WARNING')
        self.assertEqual(ret.nickname, 'master.ph5')
        self.assertEqual(ret.outfile, 'ph5_validate.log')
        self.assertEqual(ret.ph5path, self.tmpdir)
        self.assertEqual(ret.verbose, False)


class TestPh5Validate_detect_data(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestPh5Validate_detect_data, self).setUp()
        kef_to_ph5(
            self.tmpdir, 'master.ph5',
            os.path.join(self.home, 'ph5/test_data'),
            ['rt125a/das_t_12183.kef', 'metadata/array_t_9_validate.kef'],
            das_sn_list=['12183'])
        self.ph5_object = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(
            self.ph5_object, self.tmpdir)

    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestPh5Validate_detect_data, self).tearDown()

    def test_check_array_t(self):
        """
        check log messages, das_time and validation block return
        """
        with LogCapture() as log:
            log.setLevel(logging.INFO)
            vb, resp_check_info = self.ph5validate.check_array_t()

        self.assertEqual(log.records[0].msg, "Validating Array_t")

        self.assertEqual(
            self.ph5validate.das_time,
            {('12183', 1, 500):
                {'max_pickup_time': [1550850187],
                 'time_windows': [(1550849950, 1550850034, '9001'),
                                  (1550849950, 1550850034, '9001'),
                                  (1550849950, 1550850034, '9001'),
                                  (1550850043, 1550850093, '9002'),
                                  (1550850125, 1550850187, '9003')],
                 'min_deploy_time':
                     [1550849950,
                      'Data exists before deploy time: 7 seconds.']}}
        )

        self.assertEqual(vb[0].heading,
                         '-=-=-=-=-=-=-=-=-\nStation 9001 Channel 1\n'
                         '1 error, 3 warning, 0 info\n-=-=-=-=-=-=-=-=-\n')
        self.assertEqual(vb[0].info, [])
        self.assertEqual(
            vb[0].warning,
            ['No station description found.',
             'Data exists before deploy time: 7 seconds.',
             'Station 9001 [1550849950, 1550850034] is repeated 2 time(s)'])
        self.assertEqual(
            vb[0].error,
            ['No Response table found. Have you run resp_load yet?']
        )

        self.assertEqual(vb[1].heading,
                         '-=-=-=-=-=-=-=-=-\nStation 9002 Channel 1\n'
                         '1 error, 2 warning, 0 info\n-=-=-=-=-=-=-=-=-\n')
        self.assertEqual(vb[1].info, [])
        self.assertEqual(
            vb[1].warning,
            ['No station description found.',
             'Data exists after pickup time: 36 seconds.'])
        self.assertEqual(
            vb[1].error,
            ['No Response table found. Have you run resp_load yet?']
        )

        self.assertEqual(vb[2].heading,
                         '-=-=-=-=-=-=-=-=-\nStation 9003 Channel 1\n'
                         '1 error, 2 warning, 0 info\n-=-=-=-=-=-=-=-=-\n')
        self.assertEqual(vb[2].info, [])
        self.assertEqual(
            vb[2].warning,
            ['No station description found.',
             'Data exists after pickup time: 2 seconds.'])
        self.assertEqual(
            vb[2].error,
            ['No Response table found. Have you run resp_load yet?']
        )

    def test_analyze_time(self):
        """
        + check if das_time created has all time and station info
        + check if it catch the case data exists before the whole time range
        """
        self.ph5validate.analyze_time()
        self.assertEqual(self.ph5validate.das_time.keys(), [('12183', 1, 500)])
        Dtime = self.ph5validate.das_time[('12183', 1, 500)]

        # 3 different deploy time
        self.assertEqual(len(Dtime['time_windows']), 5)

        # station 9001
        self.assertEqual(Dtime['time_windows'][0],
                         (1550849950, 1550850034, '9001'))
        self.assertEqual(Dtime['time_windows'][1],
                         (1550849950, 1550850034, '9001'))
        self.assertEqual(Dtime['time_windows'][2],
                         (1550849950, 1550850034, '9001'))
        # station 9002
        self.assertEqual(Dtime['time_windows'][3],
                         (1550850043, 1550850093, '9002'))
        # station 9003
        self.assertEqual(Dtime['time_windows'][4],
                         (1550850125, 1550850187, '9003'))

        self.assertEqual(Dtime['min_deploy_time'],
                         [1550849950,
                          'Data exists before deploy time: 7 seconds.'])

    def test_check_station_completeness(self):
        self.ph5validate.das_time = {
            ('12183', 1, 500):
            {'time_windows': [(1550849950, 1550850034, '9001'),
                              (1550849950, 1550850034, '9001'),
                              (1550849950, 1550850034, '9001'),
                              (1550849950, 1550850034, '9001'),
                              (1550850043, 1550850093, '9002'),
                              (1550850125, 1550850187, '9003')],
             'min_deploy_time': [1550849950,
                                 'Data exists before deploy time: 7 seconds.'],
             }
        }

        self.ph5validate.read_arrays('Array_t_009')
        arraybyid = self.ph5validate.ph5.Array_t['Array_t_009']['byid']
        DT = self.ph5validate.das_time[('12183', 1, 500)]

        # check lon/lat not in range
        # check warning data exist before min_deploy_time
        station = arraybyid.get('9001')[1][0]
        station['location/X/value_d'] = 190.0
        station['location/X/units_s'] = 'degrees'
        station['location/Y/value_d'] = -100.0
        station['location/Y/units_s'] = 'degrees'
        station['location/Z/value_d'] = 1403
        station['location/Z/units_s'] = 'm'
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertEqual(
            warnings,
            ['No station description found.',
             'Data exists before deploy time: 7 seconds.',
             'Station 9001 [1550849950, 1550850034] is repeated 3 time(s)'])
        errors = ret[2]
        self.assertEqual(
            errors,
            ['No Response table found. Have you run resp_load yet?',
             'Channel longitude 190.0 not in range [-180,180]',
             'Channel latitude -100.0 not in range [-90,90]'])
        # check lon/lat = 0, no units, no elevation value
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
             'No Station location/Z/units_s value found.',
             'Data exists after pickup time: 36 seconds.'])
        errors = ret[2]
        self.assertEqual(
            errors,
            ['No Response table found. Have you run resp_load yet?'])

        # check error overlaping
        # => change deploy time of the 3rd station
        DT['time_windows'][5] = (1550850090, 1550850187, '9003')
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn('Overlap time on station(s): 9002, 9003', errors)

        # check no data found for array's time
        # => change array's time to where there is no data
        station = arraybyid.get('9003')[1][0]
        station['deploy_time/epoch_l'] = 1550850190
        station['pickup_time/epoch_l'] = 1550850191
        DT['time_windows'][5] = (1550850190, 1550850191, '9003')
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


class TestPH5Validate_resp_load_not_run(LogTestCase, TempDirTestCase):
    def tearDown(self):
        self.ph5API_object.close()
        super(TestPH5Validate_resp_load_not_run, self).tearDown()

    def test_check_response_t(self):
        testargs = ['segdtoph5', '-n', 'master.ph5', '-U', '13N', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/3ch.fcnt')]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()
        self.ph5API_object = ph5api.PH5(path=self.tmpdir,
                                        nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(self.ph5API_object, '.')
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = self.ph5validate.check_response_t([])
            self.assertEqual(
                ret[0].error,
                ['All response file names are blank in response table. '
                 'Check if resp_load has been run.'])
            self.assertEqual(
                log.records[0].msg,
                'All response file names are blank in response table. '
                'Check if resp_load has been run.')


if __name__ == "__main__":
    unittest.main()
