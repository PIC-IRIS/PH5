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
             'smodel': '', 'dmodel': 'ZLAND-3C'},
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
            "array 009, station 9001, channel 1, response_table_n_i 4: "
            "response_file_das_a 'rt125a_500_1_32' is inconsistent with "
            "das_model='rt125a'; sr=100 srm=1 gain=32.",
            "array 009, station 9001, channel 1, response_table_n_i 4: "
            "response_file_sensor_a 'gs11v' is inconsistent with "
            "sensor_model cmg3t.",
            "array 002, station 0407, channel 1, response_table_n_i 5: "
            "response_file_das_a 'NoneQ330_CMG3T_200HHN' is inconsistent "
            "with sensor_model='NoneCMG3T' and das_model='NoneQ330';"
            " sr=200 srm=1 gain=1 'cha=HHN'."]

    def tearDown(self):
        self.ph5API_object.close()
        super(TestValidation_response, self).tearDown()

    def test_check_resp_data(self):
        checked_data_files = {}
        header = "array 008, station 8001, channel 1, response_table_n_i 1: "
        # data has been loaded for response file rt130_100_1_1
        validation.check_resp_data(
            self.ph5API_object.ph5,
            '/Experiment_g/Responses_g/rt130_100_1_1',
            header, checked_data_files)
        self.assertEqual(checked_data_files,
                         {'rt130_100_1_1': ''})

        # data has NOT been loaded for response file rt130_200_1_1
        self.assertRaisesRegexp(
            Exception,
            '%sNo response data loaded for rt130_200_1_1.' % header,
            validation.check_resp_data,
            self.ph5API_object.ph5,
            '/Experiment_g/Responses_g/rt130_200_1_1',
            header, checked_data_files)

        self.assertEqual(
            checked_data_files,
            {'rt130_200_1_1': '%sNo response data loaded for rt130_200_1_1.'
                % header,
             'rt130_100_1_1': ''})

        # data has been loaded for response file cmg3t
        validation.check_resp_data(
            self.ph5API_object.ph5,
            '/Experiment_g/Responses_g/cmg3t',
            header, checked_data_files)
        self.assertEqual(
            checked_data_files,
            {'rt130_200_1_1': '%sNo response data loaded for rt130_200_1_1.'
                % header,
             'rt130_100_1_1': '', 'cmg3t': ''})

        # data has NOT been loaded for response file cmg
        self.assertRaisesRegexp(
            Exception,
            '%sNo response data loaded for cmg.' % header,
            validation.check_resp_data,
            self.ph5API_object.ph5,
            '/Experiment_g/Responses_g/cmg',
            header, checked_data_files)
        self.assertEqual(
            checked_data_files,
            {'rt130_200_1_1': '%sNo response data loaded for rt130_200_1_1.'
                % header,
             'cmg': '%sNo response data loaded for cmg.' % header,
             'rt130_100_1_1': '', 'cmg3t': ''})

    def test_check_resp_file_name(self):
        errors = set()
        self.ph5API_object.read_response_t()

        Response_t = self.ph5API_object.get_response_t_by_n_i(4)
        info = self.resp_check_info[9]
        header = "array 009, station 9001, channel 1, response_table_n_i 4: "
        # n_i=4: respfile wasn't created by metadata
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, header, 'metadata', errors, logger)
            self.assertEqual(ret, (False, 'rt125a_gs11v_500DPZ'))
            self.assertEqual(log.records, [])

        # n_i=4 response_das_file_name is 'rt125a_500_1_32'
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, header, 'das', errors, logger)
            self.assertEqual(ret,
                             (True, 'rt125a_500_1_32'))
            # run twice to check unique_filenames_n_i not duplicate
            validation.check_resp_file_name(
                Response_t, info, header, 'das', errors, logger)
            self.assertEqual(log.records, [])

        # n_i=4: response_das_file_name isn't 'rt125a_100_1_32'
        info['spr'] = 100
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            ret = validation.check_resp_file_name(
                Response_t, info, header, 'das', errors, logger)
            self.assertEqual(ret, (False, None))
            self.assertEqual(log.records[0].msg, self.errors[0])

        # n_i=4: response_sensor_file_name is 'gs11v'
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, header, 'sensor', errors, logger)
            self.assertEqual(ret, (True, 'gs11v'))
            self.assertEqual(log.records, [])

        # n_i=4: response_sensor_file_name isn't 'cmg3t'
        info['smodel'] = 'cmg3t'
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            ret = validation.check_resp_file_name(
                Response_t, info, header, 'sensor', errors, logger)
        self.assertEqual(ret, (False, None))
        self.assertEqual(log.records[0].msg, self.errors[1])

        # n_i=5 respfile created by metadata 'NoneQ330_NoneCMG3T_200HHN'
        Response_t = self.ph5API_object.get_response_t_by_n_i(5)
        info = self.resp_check_info[3]
        header = "array 002, station 0407, channel 1, response_table_n_i 5: "
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, header, 'metadata', errors, logger)
            self.assertEqual(
                ret,
                (True, 'NoneQ330_NoneCMG3T_200HHN'))
            self.assertEqual(log.records, [])

        # n_i=5 das model mismatch
        Response_t['response_file_das_a'] = \
            '/Experiment_g/Responses_g/NoneQ330_CMG3T_200HHN'
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, header,
                'metadata', errors, logger)
            self.assertEqual(ret, (False, 'NoneQ330_NoneCMG3T_200HHN'))

            ret = validation.check_resp_file_name(
                Response_t, info, header,
                'das', errors, logger, ret[1])
            self.assertEqual(ret, (False, None))
            self.assertEqual(log.records[0].msg, self.errors[2])

        # n_i=0: ZLAND's response_das_file_name: 'ZLAND3C_500_1_24'
        #        ZLAND's response_sensor_file_name: ''
        # das model is ZLAND-3C (omit checking for any of charaters:',-=._ '
        # in between characters of the model)
        Response_t = self.ph5API_object.get_response_t_by_n_i(0)
        info = self.resp_check_info[1]
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, header, 'das', errors, logger)
            self.assertEqual(ret,
                             (True, 'ZLAND3C_500_1_24'))
            ret = validation.check_resp_file_name(
                Response_t, info, header, 'sensor', errors, logger)
            self.assertEqual(ret, (True, ''))
            self.assertEqual(log.records, [])

        self.assertEqual(errors, {(err, 'warning') for err in self.errors})

        # n_i=0: ZLAND's response_das_file_name: 'ZLAND3C_500_1_24'
        #        ZLAND's response_sensor_file_name: ''
        Response_t = self.ph5API_object.get_response_t_by_n_i(0)
        info = self.resp_check_info[2]
        header = "array 001, station 500, channel 3, response_table_n_i 0: "
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, header, 'das', errors, logger)
            self.assertEqual(ret,
                             (True, 'ZLAND3C_500_1_24'))
            ret = validation.check_resp_file_name(
                Response_t, info, header, 'sensor', errors, logger)
            self.assertEqual(ret, (True, ''))
            self.assertEqual(log.records, [])

        Response_t['response_file_das_a'] = ''
        errors = set()
        with LogCapture() as log:
            ret = validation.check_resp_file_name(
                Response_t, info, header, 'das', errors, logger)
            self.assertEqual(ret, (False, None))
            self.assertEqual(log.records, [])

    def test_check_response_info(self):
        self.ph5API_object.read_response_t()
        checked_data_files = {}
        errors = set()
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            ret = validation.check_response_info(
                self.resp_check_info[9], self.ph5API_object,
                checked_data_files, errors, logger)
            self.assertEqual(ret, ('/Experiment_g/Responses_g/rt125a_500_1_32',
                                   '/Experiment_g/Responses_g/gs11v'))
            self.assertEqual(errors, set())
            self.assertEqual(log.records, [])

        info = next(item for item in self.resp_check_info if item["n_i"] == 4)
        info['spr'] = 100
        info['smodel'] = 'cmg3t'
        chckerrors = set(
            ["array 009, station 9001, channel 1, response_table_n_i 4: "
             "response_file_das_a 'rt125a_500_1_32' is inconsistent with "
             "sensor_model='cmg3t' and das_model='rt125a'; "
             "sr=100 srm=1 gain=32 'cha=DPZ'.",
             "array 009, station 9001, channel 1, response_table_n_i 4: "
             "response_file_sensor_a 'gs11v' is inconsistent with "
             "sensor_model cmg3t."])
        info = next(item for item in self.resp_check_info if item["n_i"] == 4)
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            ret = validation.check_response_info(
                info, self.ph5API_object, checked_data_files, errors, logger)
            self.assertEqual(ret, ('/Experiment_g/Responses_g/rt125a_500_1_32',
                                   '/Experiment_g/Responses_g/gs11v'))
            self.assertEqual(
                errors,
                {(errmsg, 'warning') for errmsg in chckerrors})
            self.assertEqual({r.msg for r in log.records},
                             chckerrors)

        response_t = self.ph5API_object.get_response_t_by_n_i(1)
        response_t['response_file_das_a'] = 'rt130_200_1_1'
        info = next(item for item in self.resp_check_info if item["n_i"] == 1)
        info['spr'] = 200
        ret = validation.check_response_info(
            info, self.ph5API_object, checked_data_files, errors, logger)
        self.assertEqual(ret,
                         (False, 'array 008, station 8001, channel 1, '
                                 'response_table_n_i 1: No response data '
                                 'loaded for rt130_200_1_1.'))

        info['n_i'] = 8
        ret = validation.check_response_info(
                info, self.ph5API_object, checked_data_files, errors, logger)
        self.assertEqual(ret,
                         (False, 'array 008, station 8001, channel 1,'
                                 ' response_table_n_i 8: '
                                 'Response_t has no entry for n_i=8'))

    def test_check_response_unique_n_i(self):
        self.ph5API_object.read_response_t()
        response_t = self.ph5API_object.get_response_t_by_n_i(1)
        response_t['n_i'] = 2
        errors = set()
        validation.check_resp_unique_n_i(self.ph5API_object, errors)
        self.assertEqual(errors,
                         {('Response_t n_i(s) duplicated: 2', 'error')})

    def test_check_has_response_filename(self):
        self.ph5API_object.read_response_t()
        has_response_file = validation.check_has_response_filename(
            self.ph5API_object.Response_t, [], None)
        self.assertTrue(has_response_file)


class TestValidation_no_response_filename(LogTestCase, TempDirTestCase):
    def tearDown(self):
        self.ph5.close()
        super(TestValidation_no_response_filename, self).tearDown()

    def test_check_has_response_filename(self):
        testargs = ['segdtoph5', '-n', 'master.ph5', '-U', '13N', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/3ch.fcnt')]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()
        self.ph5 = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        self.ph5.read_response_t()
        has_response_file = validation.check_has_response_filename(
            self.ph5.Response_t, set(), None)
        self.assertEqual(has_response_file,
                         "Response table does not contain any response file "
                         "names. Check if resp_load has been run or if "
                         "metadatatoph5 input contained response information.")


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
