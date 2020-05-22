'''
Tests for ph5validate
'''

import unittest
import logging
import os

from testfixtures import LogCapture

from ph5.core import ph5api
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase
from ph5.utilities import ph5validate


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


if __name__ == "__main__":
    unittest.main()
