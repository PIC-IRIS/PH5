'''
Tests for validation
'''

import unittest
import os
import logging
import sys

from mock import patch
from testfixtures import LogCapture

from ph5.core import ph5api
from ph5 import logger
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase
from ph5.utilities import validation, segd2ph5


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
        errors = set()
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

        self.assertEqual(
            errors,
            {('No response data loaded for rt130_200_1_1.', 'error'),
             ('No response data loaded for cmg.', 'error')})

    def test_check_resp_file_name(self):
        errors = set()
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
        self.assertEqual(errors, {(err, 'error') for err in self.errors})

        Response_t['response_file_das_a'] = ''
        errors = set()
        unique_filenames_n_i = []
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, 'das', unique_filenames_n_i, errors, logger)
            errmsg = ('001-500-3 response_table_n_i 0: response_file_das_a '
                      'is blank while das model exists.')
            self.assertEqual(log.records[0].msg, errmsg)
            self.assertEqual(errors, {(errmsg, 'error')})

    def test_check_response_info(self):
        self.ph5API_object.read_response_t()
        unique_filenames_n_i = []
        checked_data_files = {}
        errors = set()
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            validation.check_response_info(
                self.resp_check_info[9], self.ph5API_object,
                unique_filenames_n_i,
                checked_data_files, errors, logger)
            self.assertEqual(errors, set())
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
            self.assertEqual(
                errors,
                {(errmsg, 'error') for errmsg in chckerrors})
            for i in range(len(log.records)):
                self.assertEqual(log.records[i].msg, chckerrors[i])

        errors = set()
        response_t = self.ph5API_object.get_response_t_by_n_i(1)
        response_t['response_file_das_a'] = 'rt130_200_1_1'
        info = next(item for item in self.resp_check_info if item["n_i"] == 1)
        info['spr'] = 200
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            validation.check_response_info(
                info, self.ph5API_object, unique_filenames_n_i,
                checked_data_files, errors, logger)
            self.assertEqual(
                errors,
                {('No response data loaded for rt130_200_1_1.', 'error')})
            self.assertEqual(log.records[0].msg,
                             'No response data loaded for rt130_200_1_1.')

        errors = set()
        info['n_i'] = 8
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            validation.check_response_info(
                info, self.ph5API_object, unique_filenames_n_i,
                checked_data_files, errors, logger)
            self.assertEqual(errors,
                             {('No response entry for n_i=8.', 'error')})
            self.assertEqual(log.records[0].msg,
                             'No response entry for n_i=8.')

    def test_check_response_unique_n_i(self):
        self.ph5API_object.read_response_t()
        response_t = self.ph5API_object.get_response_t_by_n_i(1)
        response_t['n_i'] = 2
        errors = set()
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            validation.check_resp_unique_n_i(
                self.ph5API_object, errors)
        self.assertEqual(errors,
                         {('Response_t n_i(s) duplicated: 2', 'error')})

    def test_check_resp_load(self):
        self.ph5API_object.read_response_t()
        resp_load_already = validation.check_resp_load(
            self.ph5API_object.Response_t, [], None)
        self.assertTrue(resp_load_already)


class TestValidation_resp_load_not_run(LogTestCase, TempDirTestCase):
    def tearDown(self):
        self.ph5.close()
        super(TestValidation_resp_load_not_run, self).tearDown()

    def test_check_resp_load(self):
        testargs = ['segdtoph5', '-n', 'master.ph5', '-U', '13N', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/3ch.fcnt')]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()
        self.ph5 = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        self.ph5.read_response_t()
        resp_load_already = validation.check_resp_load(
            self.ph5.Response_t, set(), None)
        self.assertFalse(resp_load_already)


class TestValidation_location(unittest.TestCase):
    def test_check_lat_lon_elev(self):
        station = {'location/X/value_d': 100.0,
                   'location/X/units_s': 'degrees',
                   'location/Y/value_d': 70.0,
                   'location/Y/units_s': 'degrees',
                   'location/Z/value_d': 1047,
                   'location/Z/units_s': 'm'}

        errors, warnings = validation.check_lat_lon_elev(station)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

        station = {'location/X/value_d': 190.0,
                   'location/X/units_s': '',
                   'location/Y/value_d': -100.0,
                   'location/Y/units_s': '',
                   'location/Z/value_d': 0.0,
                   'location/Z/units_s': ''}
        errors, warnings = validation.check_lat_lon_elev(station)
        self.assertEqual(
            errors,
            ['Channel longitude 190.0 not in range [-180,180]',
             'Channel latitude -100.0 not in range [-90,90]'])
        self.assertEqual(
            warnings,
            ['No Station location/X/units_s value found.',
             'No Station location/Y/units_s value found.',
             'Channel elevation seems to be 0. Is this correct???',
             'No Station location/Z/units_s value found.'])

        station = {'location/X/value_d': 0,
                   'location/X/units_s': '',
                   'location/Y/value_d': 0,
                   'location/Y/units_s': None,
                   'location/Z/value_d': 0,
                   'location/Z/units_s': None}
        errors, warnings = validation.check_lat_lon_elev(station)
        self.assertEqual(errors, [])
        self.assertEqual(
            warnings,
            ['Channel longitude seems to be 0. Is this correct???',
             'No Station location/X/units_s value found.',
             'Channel latitude seems to be 0. Is this correct???',
             'No Station location/Y/units_s value found.',
             'Channel elevation seems to be 0. Is this correct???',
             'No Station location/Z/units_s value found.'])


if __name__ == "__main__":
    unittest.main()
