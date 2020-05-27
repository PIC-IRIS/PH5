'''
Tests for ph5validate
'''
import unittest
import logging
import os
import sys

from mock import patch
from testfixtures import LogCapture, OutputCapture

from ph5.utilities import ph5validate
from ph5.core import ph5api
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase, kef_to_ph5

class TestPH5Validate_response(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5Validate_response, self).setUp()
        ph5path = os.path.join(self.home, "ph5/test_data/ph5")
        self.ph5API_object = ph5api.PH5(path=ph5path, nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(
            self.ph5API_object, '.', 'WARNING', 'ph5_validate.log')
        self.resp_check_info = [
            {'n_i': 0, 'array': 'Array_t_001', 'sta': '500',
             'cha_code': 'DP1', 'spr': 500, 'sprm': 1, 'cha_id': 1,
             'smodel': '', 'dmodel': 'ZLAND 3C'},
            {'n_i': 0, 'array': 'Array_t_001', 'sta': '500',
             'cha_code': 'DP2', 'spr': 500, 'sprm': 1, 'cha_id': 2,
             'smodel': '', 'dmodel': 'ZLAND 3C'},
            {'n_i': 0, 'array': 'Array_t_001', 'sta': '500',
             'cha_code': 'DPZ', 'spr': 500, 'sprm': 1, 'cha_id': 3,
             'smodel': '', 'dmodel': 'ZLAND 3C'},
            {'n_i': 5, 'array': 'Array_t_002', 'sta': '0407',
             'cha_code': 'HHN', 'spr': 200, 'sprm': 1, 'cha_id': 1,
             'smodel': 'None CMG-3T', 'dmodel': 'None Q330'},
            {'n_i': 6, 'array': 'Array_t_003', 'sta': '0407',
             'cha_code': 'LHN', 'spr': 100, 'sprm': 1, 'cha_id': 1,
             'smodel': 'None CMG-3T', 'dmodel': 'None Q330'},
            {'n_i': -1, 'array': 'Array_t_004', 'sta': '0407',
             'cha_code': 'LOG', 'spr': 0, 'sprm': 1, 'cha_id': -2,
             'smodel': 'None CMG-3T', 'dmodel': 'None Q330'},
            {'n_i': 1, 'array': 'Array_t_008', 'sta': '8001',
             'cha_code': 'HLZ', 'spr': 100, 'sprm': 1, 'cha_id': 1,
             'smodel': 'cmg-3t', 'dmodel': 'rt130'},
            {'n_i': 2, 'array': 'Array_t_008', 'sta': '8001',
             'cha_code': 'HL1', 'spr': 100, 'sprm': 1, 'cha_id': 2,
             'smodel': 'cmg-3t', 'dmodel': 'rt130'},
            {'n_i': 3, 'array': 'Array_t_008', 'sta': '8001',
             'cha_code': 'HL2', 'spr': 100, 'sprm': 1, 'cha_id': 3,
             'smodel': 'cmg-3t', 'dmodel': 'rt130'},
            {'n_i': 4, 'array': 'Array_t_009', 'sta': '9001',
             'cha_code': 'DPZ', 'spr': 500, 'sprm': 1, 'cha_id': 1,
             'smodel': 'gs11v', 'dmodel': 'rt125a'}]
        self.errors = ["Array_t_009-9001-1 response_table_n_i 4: Response das "
                       "file name should be 'rt125a_100_1_32' while currently "
                       "is 'rt125a_500_1_32'.",
                       "Array_t_009-9001-1 response_table_n_i 4: Response "
                       "sensor file name should be 'cmg3t' while currently "
                       "is 'gs11v'."]

    def tearDown(self):
        self.ph5API_object.close()
        super(TestPH5Validate_response, self).tearDown()

    def test_check_resp_data(self):
        errors = []
        # data has been loaded for response file rt130_100_1_1
        with LogCapture() as log:
            self.ph5validate.check_resp_data(
                self.ph5API_object.ph5, 'rt130_100_1_1', errors)
        self.assertEqual(log.records, [])

        # data has NOT been loaded for response file rt130_200_1_1
        with LogCapture() as log:
            self.ph5validate.check_resp_data(
                self.ph5API_object.ph5, 'rt130_200_1_1', errors)
        self.assertEqual(log.records[0].msg,
                         'No response data loaded for rt130_200_1_1')

        # data has been loaded for response file cmg3t
        with LogCapture() as log:
            self.ph5validate.check_resp_data(
                self.ph5API_object.ph5, 'cmg3t', errors)
        self.assertEqual(log.records, [])

        # data has NOT been loaded for response file cmg
        with LogCapture() as log:
            self.ph5validate.check_resp_data(
                self.ph5API_object.ph5, 'cmg', errors)
        self.assertEqual(log.records[0].msg,
                         'No response data loaded for cmg')

        self.assertEqual(errors, ['No response data loaded for rt130_200_1_1',
                                  'No response data loaded for cmg'])

    def test_check_resp_file_name(self):
        errors = []
        unique_filenames_n_i = []
        self.ph5validate.ph5.read_response_t()

        Response_t = self.ph5validate.ph5.get_response_t_by_n_i(4)
        info = self.resp_check_info[9]
        # n_i=4: respfile wasn't created by metadata
        with LogCapture() as log:
            ret = self.ph5validate.check_resp_file_name(
                Response_t, info,
                'metadata', unique_filenames_n_i, errors)
            self.assertIsNone(ret)
            self.assertEqual(unique_filenames_n_i, [])
            self.assertEqual(log.records, [])

        # n_i=4 response_das_file_name is 'rt125a_500_1_32'
        with LogCapture() as log:
            ret = self.ph5validate.check_resp_file_name(
                Response_t, info, 'das', unique_filenames_n_i, errors)
            self.assertEqual(ret, 'rt125a_500_1_32')
            # run twice to check unique_filenames_n_i
            ret = self.ph5validate.check_resp_file_name(
                Response_t, info, 'das', unique_filenames_n_i, errors)
            self.assertEqual(ret, 'rt125a_500_1_32')
            self.assertEqual(log.records, [])

        # n_i=4: response_das_file_name isn't 'rt125a_100_1_32'
        info['spr'] = 100
        with LogCapture() as log:
            ret = self.ph5validate.check_resp_file_name(
                Response_t, info, 'das', unique_filenames_n_i, errors)
            self.assertIsNone(ret)
            self.assertEqual(log.records[0].msg, self.errors[0])

        # n_i=4: response_sensor_file_name is 'gs11v'
        with LogCapture() as log:
            ret = self.ph5validate.check_resp_file_name(
                Response_t, info, 'sensor', unique_filenames_n_i, errors)
            self.assertEqual(ret, 'gs11v')
            self.assertEqual(log.records, [])

        # n_i=4: response_sensor_file_name isn't 'cmg3t'
        info['smodel'] = 'cmg3t'
        with LogCapture() as log:
            ret = self.ph5validate.check_resp_file_name(
                Response_t, info, 'sensor', unique_filenames_n_i, errors)
        self.assertIsNone(ret)
        self.assertEqual(log.records[0].msg, self.errors[1])

        # n_i=5 respfile created by metadata 'NoneQ330_NoneCMG3T_200HHN'
        Response_t = self.ph5validate.ph5.get_response_t_by_n_i(5)
        info = self.resp_check_info[3]
        with LogCapture() as log:
            ret = self.ph5validate.check_resp_file_name(
                Response_t, info, 'metadata', unique_filenames_n_i, errors)
            self.assertEqual(ret, 'NoneQ330_NoneCMG3T_200HHN')
            self.assertEqual(log.records, [])

        # n_i=0: ZLAND's response_das_file_name: 'ZLAND3C_500_1_24'
        #        ZLAND's response_sensor_file_name: ''
        Response_t = self.ph5validate.ph5.get_response_t_by_n_i(0)
        info = self.resp_check_info[2]
        with LogCapture() as log:
            ret = self.ph5validate.check_resp_file_name(
                Response_t, info, 'das', unique_filenames_n_i, errors)
            self.assertEqual(ret, 'ZLAND3C_500_1_24')
            ret = self.ph5validate.check_resp_file_name(
                Response_t, info, 'sensor', unique_filenames_n_i, errors)
            self.assertIsNone(ret)
            self.assertEqual(log.records, [])

        self.assertEqual(unique_filenames_n_i,
                         [('rt125a_500_1_32', 4), ('gs11v', 4),
                          ('NoneQ330_NoneCMG3T_200HHN', 5),
                          ('ZLAND3C_500_1_24', 0)])
        self.assertEqual(errors, self.errors)

    def test_check_array_t(self):
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            vb_array, resp_check_info = self.ph5validate.check_array_t()
            self.assertEqual(resp_check_info, self.resp_check_info)

    def test_check_response_t(self):
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = self.ph5validate.check_response_t(self.resp_check_info)
            self.assertEqual(ret[0].error, [])
            self.assertEqual(log.records, [])

        self.resp_check_info[9]['spr'] = 100
        self.resp_check_info[9]['smodel'] = 'cmg3t'
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = self.ph5validate.check_response_t(self.resp_check_info)
            self.assertEqual(ret[0].error, self.errors)
            for i in range(len(log.records)):
                self.assertEqual(log.records[i].msg, self.errors[i])
            self.assertEqual(ret[0].heading,
                             "-=-=-=-=-=-=-=-=-\n"
                             "Response_t\n"
                             "2 error, 0 warning, 0 info\n"
                             "-=-=-=-=-=-=-=-=-\n"
                             )


class TestPh5Validate_main_detect_data(TempDirTestCase, LogTestCase):

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
            self.ph5_object, self.tmpdir, "WARNING",
            outfile="ph5_validate.log")

    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestPh5Validate_detect_data, self).tearDown()

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

        # check warning before min_deploy_time
        station = arraybyid.get('9001')[1][0]
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertIn('Data exists before deploy time: 7 seconds.', warnings)

        # check warning data after pickup time
        station = arraybyid.get('9002')[1][0]
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertIn('Data exists after pickup time: 36 seconds.', warnings)

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
