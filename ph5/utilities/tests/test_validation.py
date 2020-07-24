'''
Tests for validation
'''

import unittest
import os
import logging

from testfixtures import LogCapture

from ph5.core import ph5api
from ph5 import logger
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase
from ph5.utilities import validation


class TestValidation_response(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestValidation_response, self).setUp()
        ph5path = os.path.join(self.home, "ph5/test_data/ph5")
        self.ph5API_object = ph5api.PH5(path=ph5path, nickname='master.ph5')

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
        self.errors = [
            "009-9001-1 response_table_n_i 4: Response das file name should "
            "be 'rt125a_100_1_32' instead of 'rt125a_500_1_32'.",
            "009-9001-1 response_table_n_i 4: Response sensor file name "
            "should be 'cmg3t' instead of 'gs11v'.",
            "002-0407-1 response_table_n_i 5: Response das file name should "
            "be 'NoneQ330_200_1_1' or 'NoneQ330_NoneCMG3T_200HHN' instead of "
            "'NoneQ330_CMG3T_200HHN'."]

    def tearDown(self):
        self.ph5API_object.close()
        super(TestValidation_response, self).tearDown()

    def test_check_resp_data(self):
        errors = []
        # data has been loaded for response file rt130_100_1_1
        with LogCapture() as log:
            validation.check_resp_data(
                self.ph5API_object.ph5, 'rt130_100_1_1', errors, logger)
        self.assertEqual(log.records, [])

        # data has NOT been loaded for response file rt130_200_1_1
        with LogCapture() as log:
            validation.check_resp_data(
                self.ph5API_object.ph5, 'rt130_200_1_1', errors, logger)
        self.assertEqual(log.records[0].msg,
                         'No response data loaded for rt130_200_1_1.')

        # data has been loaded for response file cmg3t
        with LogCapture() as log:
            validation.check_resp_data(
                self.ph5API_object.ph5, 'cmg3t', errors, logger)
        self.assertEqual(log.records, [])

        # data has NOT been loaded for response file cmg
        with LogCapture() as log:
            validation.check_resp_data(
                self.ph5API_object.ph5, 'cmg', errors, logger)
        self.assertEqual(log.records[0].msg,
                         'No response data loaded for cmg.')

        self.assertEqual(errors, ['No response data loaded for rt130_200_1_1.',
                                  'No response data loaded for cmg.'])

    def test_check_resp_file_name(self):
        errors = []
        unique_filenames_n_i = []
        self.ph5API_object.read_response_t()

        Response_t = self.ph5API_object.get_response_t_by_n_i(4)
        info = self.resp_check_info[9]
        # n_i=4: respfile wasn't created by metadata
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info,
                'metadata', unique_filenames_n_i, errors, logger)
            self.assertEqual(ret[0], 'rt125a_gs11v_500DPZ')
            self.assertIsNone(ret[1], None)
            self.assertEqual(unique_filenames_n_i, [])
            self.assertEqual(log.records, [])

        # n_i=4 response_das_file_name is 'rt125a_500_1_32'
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, 'das', unique_filenames_n_i, errors, logger)
            self.assertEqual(ret,
                             ('rt125a_500_1_32',
                              '/Experiment_g/Responses_g/rt125a_500_1_32'))
            # run twice to check unique_filenames_n_i not duplicate
            validation.check_resp_file_name(
                Response_t, info, 'das', unique_filenames_n_i, errors, logger)
            self.assertEqual(log.records, [])

        # n_i=4: response_das_file_name isn't 'rt125a_100_1_32'
        info['spr'] = 100
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, 'das', unique_filenames_n_i, errors, logger)
            self.assertIsNone(ret)
            self.assertEqual(log.records[0].msg, self.errors[0])

        # n_i=4: response_sensor_file_name is 'gs11v'
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, 'sensor',
                unique_filenames_n_i, errors, logger)
            self.assertEqual(ret, ('gs11v', '/Experiment_g/Responses_g/gs11v'))
            self.assertEqual(log.records, [])

        # n_i=4: response_sensor_file_name isn't 'cmg3t'
        info['smodel'] = 'cmg3t'
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, 'sensor',
                unique_filenames_n_i, errors, logger)
        self.assertIsNone(ret)
        self.assertEqual(log.records[0].msg, self.errors[1])

        # n_i=5 respfile created by metadata 'NoneQ330_NoneCMG3T_200HHN'
        Response_t = self.ph5API_object.get_response_t_by_n_i(5)
        info = self.resp_check_info[3]
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, 'metadata',
                unique_filenames_n_i, errors, logger)
            self.assertEqual(
                ret,
                ('NoneQ330_NoneCMG3T_200HHN',
                 '/Experiment_g/Responses_g/NoneQ330_NoneCMG3T_200HHN'))
            self.assertEqual(log.records, [])

        # n_i=5 das model mismatch
        Response_t['response_file_das_a'] = \
            '/Experiment_g/Responses_g/NoneQ330_CMG3T_200HHN'
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, 'metadata', [], errors, logger)
            self.assertEqual(ret[0], 'NoneQ330_NoneCMG3T_200HHN')
            self.assertIsNone(ret[1])
            ret = validation.check_resp_file_name(
                Response_t, info, 'das', [],
                errors, logger, 'NoneQ330_NoneCMG3T_200HHN')
            self.assertIsNone(ret)
            self.assertEqual(log.records[0].msg, self.errors[2])

        # n_i=0: ZLAND's response_das_file_name: 'ZLAND3C_500_1_24'
        #        ZLAND's response_sensor_file_name: ''
        Response_t = self.ph5API_object.get_response_t_by_n_i(0)
        info = self.resp_check_info[2]
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, 'das', unique_filenames_n_i, errors, logger)
            self.assertEqual(ret,
                             ('ZLAND3C_500_1_24',
                              '/Experiment_g/Responses_g/ZLAND3C_500_1_24'))
            ret = validation.check_resp_file_name(
                Response_t, info, 'sensor',
                unique_filenames_n_i, errors, logger)
            self.assertIsNone(ret)
            self.assertEqual(log.records, [])

        self.assertEqual(unique_filenames_n_i,
                         [('rt125a_500_1_32', 4), ('gs11v', 4),
                          ('NoneQ330_NoneCMG3T_200HHN', 5),
                          ('ZLAND3C_500_1_24', 0)])
        self.assertEqual(errors, self.errors)

        Response_t['response_file_das_a'] = ''
        errors = []
        unique_filenames_n_i = []
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, 'das', unique_filenames_n_i, errors, logger)
            errmsg = ('001-500-3 response_table_n_i 0: response_file_das_a '
                      'is blank while das model exists.')
            self.assertEqual(log.records[0].msg, errmsg)
            self.assertEqual(errors, [errmsg])

    def test_check_response_info(self):
        self.ph5API_object.read_response_t()
        unique_filenames_n_i = []
        checked_data_files = {}
        errors = []
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            validation.check_response_info(
                self.resp_check_info[9], self.ph5API_object,
                unique_filenames_n_i,
                checked_data_files, errors, logger)
            self.assertEqual(errors, [])
            self.assertEqual(log.records, [])

        info = next(item for item in self.resp_check_info if item["n_i"] == 4)
        info['spr'] = 100
        info['smodel'] = 'cmg3t'
        chckerrors = ["009-9001-1 response_table_n_i 4: Response "
                      "sensor file name should be 'cmg3t' instead of "
                      "'gs11v'.",
                      "009-9001-1 response_table_n_i 4: Response das "
                      "file name should be 'rt125a_100_1_32' instead of "
                      "'rt125a_500_1_32'."]
        info = next(item for item in self.resp_check_info if item["n_i"] == 4)
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            validation.check_response_info(
                info, self.ph5API_object, unique_filenames_n_i,
                checked_data_files, errors, logger)
            self.assertEqual(errors, chckerrors)
            for i in range(len(log.records)):
                self.assertEqual(log.records[i].msg, chckerrors[i])

        errors = []
        response_t = self.ph5API_object.get_response_t_by_n_i(1)
        response_t['response_file_das_a'] = 'rt130_200_1_1'
        info = next(item for item in self.resp_check_info if item["n_i"] == 1)
        info['spr'] = 200
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            validation.check_response_info(
                info, self.ph5API_object, unique_filenames_n_i,
                checked_data_files, errors, logger)
            self.assertEqual(errors,
                             ['No response data loaded for rt130_200_1_1.'])
            self.assertEqual(log.records[0].msg,
                             'No response data loaded for rt130_200_1_1.')

        errors = []
        info['n_i'] = 8
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            validation.check_response_info(
                info, self.ph5API_object, unique_filenames_n_i,
                checked_data_files, errors, logger)
            self.assertEqual(errors,
                             ['No response entry for n_i=8.'])
            self.assertEqual(log.records[0].msg,
                             'No response entry for n_i=8.')

    def test_check_response_unique_n_i(self):
        self.ph5API_object.read_response_t()
        response_t = self.ph5API_object.get_response_t_by_n_i(1)
        response_t['n_i'] = 2
        errors = []
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            validation.check_resp_unique_n_i(
                self.ph5API_object, errors, logger)
            self.assertEqual(errors, ['Response_t n_i(s) duplicated: 2'])


if __name__ == "__main__":
    unittest.main()
