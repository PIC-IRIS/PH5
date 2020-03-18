'''
Tests for ph5validate
'''

import unittest
import logging
from ph5.utilities import ph5validate
from ph5.core import ph5api
from ph5.utilities import initialize_ph5
from obspy.core import inventory
from obspy import UTCDateTime
import os
import sys
import shutil
from ph5.core.tests.test_base_ import LogTestCase, TempDirTestCase, \
     initialize_ex, kef_to_ph5
from testfixtures import LogCapture


class TestPH5Validate(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5Validate, self).setUp()
        shutil.copy(self.home + "/ph5/test_data/ph5/master.ph5", self.tmpdir)
        self.ph5API_object = ph5api.PH5(path='.', nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(
            self.ph5API_object, '.', 'WARNING', 'ph5_validate.log')
        
    def tearDown(self):
        self.ph5API_object.close()
        super(TestPH5Validate, self).tearDown()

    def test_check_resp_data(self):
        errors = []
        # data has been loaded for response file rt130_100_1_1
        with LogCapture() as log:
            self.ph5validate.check_resp_data(
                '.', 'master.ph5', 'rt130_100_1_1', errors)
        self.assertEqual(log.records, [])

        # data has NOT been loaded for response file rt130_200_1_1
        with LogCapture() as log:
            self.ph5validate.check_resp_data(
                '.', 'master.ph5', 'rt130_200_1_1', errors)
        self.assertEqual(log.records[0].msg,
                         'No response data loaded for rt130_200_1_1')

        # data has been loaded for response file cmg3t
        with LogCapture() as log:
            self.ph5validate.check_resp_data(
                '.', 'master.ph5', 'cmg3t', errors)
        self.assertEqual(log.records, [])

        # data has NOT been loaded for response file cmg
        with LogCapture() as log:
            self.ph5validate.check_resp_data(
                '.', 'master.ph5', 'cmg', errors)
        self.assertEqual(log.records[0].msg,
                         'No response data loaded for cmg')

        self.assertEqual(errors, ['No response data loaded for rt130_200_1_1',
                                  'No response data loaded for cmg'])


    def test_check_resp_file_name(self):
        errors = []
        self.ph5validate.ph5.read_response_t()
        Response_t = self.ph5validate.ph5.get_response_t_by_n_i(4)

        # 'rt125a_500_1_32' is response_das_file_name at n_i=4
        with LogCapture() as log:
            self.ph5validate.check_resp_file_name(
                Response_t, 4, 'STA', 'CHAN', 'das', 'rt125a_500_1_32', errors)
        self.assertEqual(log.records, [])

        # 'rt125a_500_1_1' isn't response_das_file_name at n_i=4
        with LogCapture() as log:
            self.ph5validate.check_resp_file_name(
                Response_t, 4, 'STA', 'CHAN', 'das', 'rt125a_500_1_1', errors)
        self.assertEqual(
            log.records[0].msg,
            "STA-CHAN-response_table_n_i 4: Response das file name should be "
            "'rt125a_500_1_1' while currently is 'rt125a_500_1_32'.")

        # 'gs11v' is response_sensor_file_name at n_i=4
        with LogCapture() as log:
            self.ph5validate.check_resp_file_name(
                Response_t, 4, 'STA', 'CHAN', 'sensor', 'gs11v', errors)
        self.assertEqual(log.records, [])

        # 'cmg3t' isn't response_sensor_file_name at n_i=4
        with LogCapture() as log:
            self.ph5validate.check_resp_file_name(
                Response_t, 4, 'STA', 'CHAN', 'sensor', 'cmg3t', errors)
        self.assertEqual(
            log.records[0].msg,
            "STA-CHAN-response_table_n_i 4: Response sensor file name should "
            "be 'cmg3t' while currently is 'gs11v'.")

        self.assertEqual(
            errors,
            ["STA-CHAN-response_table_n_i 4: Response das file name should be "
             "'rt125a_500_1_1' while currently is 'rt125a_500_1_32'.",
             "STA-CHAN-response_table_n_i 4: Response sensor file name should "
             "be 'cmg3t' while currently is 'gs11v'."])

    def test_check_response_t(self):
        resp_check_info = [
            {'sta': '500', 'spr': 500, 'chan': 1, 'sprm': 1,'n_i': 7,
             'model': 'ZLAND 3C'},
            {'model': '', 'chan': 1, 'n_i': 7, 'sta': '500'},
            {'model': 'CMG-3T', 'chan': 1, 'n_i': 5, 'sta': '0407'},
            {'sta': '0407', 'spr': 100, 'chan': 1, 'sprm': 1, 'n_i': 6,
             'model': 'Q330'},
            {'model': 'CMG-3T', 'chan': 1, 'n_i': 6, 'sta': '0407'},
            {'sta': '0407', 'spr': 0, 'chan': -2, 'sprm': 1, 'n_i': -1,
             'model': 'Q330'},
            {'model': 'CMG-3T', 'chan': -2, 'n_i': -1, 'sta': '0407'},
            {'sta': '8001', 'spr': 100, 'chan': 1, 'sprm': 1, 'n_i': 7,
             'model': 'rt130'},
            {'model': 'cmg-3t', 'chan': 1, 'n_i': 7, 'sta': '8001'},
            {'model': 'gs11v', 'chan': 1, 'n_i': 7, 'sta': '9001'}]
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = self.ph5validate.check_response_t(
                resp_check_info, '.', 'master.ph5')
        print("errors:", ret[0].error)
        for r in log.records:
            print("log:", r.msg)

if __name__ == "__main__":
    unittest.main()
