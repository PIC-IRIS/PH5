'''
Tests for resp_load
'''
import os
import sys
import unittest
import copy

from mock import patch
from testfixtures import LogCapture

from ph5.core import ph5api
from ph5.utilities import resp_load, segd2ph5, metadatatoph5, obspytoph5
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


class Test_n_i_fix(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(Test_n_i_fix, self).setUp()
        """
        add create master.ph5 with the following tables:
         array_001-sta500-cha1,2,3-das3x500-modelZLAND_sr500-response_n_i0
         das_3x500
         response_t: n_i=0 bit_weight=1.88e-05
        """
        testargs = ['segdtoph5', '-n', 'master.ph5', '-r',
                    os.path.join(self.home, "ph5/test_data/segd/3ch.fcnt")]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        """
        use metadata to add metadata info
         array_002-st0407 - das5553 - response_n_i=1
         array_003-st0407 - das5553 - response_n_i=2
         array_004-st0407 - das5553 - response_n_i=-1
         response_t: n_i=1 response_file_das_a= NoneQ330_NoneCMG3T_200HHN
         response_t: n_i=2 response_file_das_a= NoneQ330_NoneCMG3T_100LHN
         response_t: n_i=-1
        """
        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    os.path.join(self.home,
                                 "ph5/test_data/metadata/station.xml")]
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()

        """
        add das_t 5553's
        """
        testargs = ['mstoph5', '-n', 'master.ph5', '-d',
                    os.path.join(self.home,
                                 "ph5/test_data/miniseed")]
        with patch.object(sys, 'argv', testargs):
            obspytoph5.main()

        self.ph5API_object = ph5api.PH5(path='.',
                                        nickname='master.ph5',
                                        editmode=True)
        self.n_i_fix = resp_load.n_i_fix(self.ph5API_object, False, False,
                                         ['1', '2', '3', '4'])

    def tearDown(self):
        self.ph5API_object.ph5close()
        super(Test_n_i_fix, self).tearDown()

    def test_init(self):
        self.assertEqual(self.n_i_fix.array, ['1', '2', '3', '4'])
        self.assertEqual(self.n_i_fix.reload_resp, False)
        self.assertEqual(self.n_i_fix.skip_response_t, False)
        self.assertEqual(self.n_i_fix.last_loaded_n_i, 2)
        # check noloaded_resp
        self.assertEqual(self.n_i_fix.noloaded_resp[0]['n_i'], 0)
        self.assertEqual((self.n_i_fix.noloaded_resp[0]['bit_weight/value_d']),
                         1.880399419308285e-05)

        # check loaded_resp
        self.assertEqual(self.n_i_fix.loaded_resp[0]['n_i'], 1)
        self.assertEqual((self.n_i_fix.loaded_resp[0]['response_file_das_a']),
                         '/Experiment_g/Responses_g/NoneQ330_NoneCMG3T_200HHN')
        self.assertEqual(self.n_i_fix.loaded_resp[1]['n_i'], 2)
        self.assertEqual((self.n_i_fix.loaded_resp[1]['response_file_das_a']),
                         '/Experiment_g/Responses_g/NoneQ330_NoneCMG3T_100LHN')
        self.assertEqual(self.n_i_fix.loaded_resp[2]['n_i'], -1)

        # check all_resp
        self.assertEqual(self.n_i_fix.all_resp[0]['n_i'], 0)
        self.assertEqual((self.n_i_fix.all_resp[0]['bit_weight/value_d']),
                         1.880399419308285e-05)
        self.assertEqual(self.n_i_fix.all_resp[1]['n_i'], 1)
        self.assertEqual(self.n_i_fix.all_resp[1]['response_file_das_a'],
                         '/Experiment_g/Responses_g/NoneQ330_NoneCMG3T_200HHN')
        self.assertEqual(self.n_i_fix.all_resp[2]['n_i'], 2)
        self.assertEqual(self.n_i_fix.all_resp[2]['response_file_das_a'],
                         '/Experiment_g/Responses_g/NoneQ330_NoneCMG3T_100LHN')
        self.assertEqual(self.n_i_fix.all_resp[3]['n_i'], -1)

        # check meta_loaded_das_file
        self.assertEqual(
            self.n_i_fix.meta_loaded_das_file,
            ['/Experiment_g/Responses_g/NoneQ330_NoneCMG3T_200HHN',
             '/Experiment_g/Responses_g/NoneQ330_NoneCMG3T_100LHN'])

    def test_get_response_t(self):
        # no response loaded
        ret = self.n_i_fix.get_response_t('ZLAND', '', 500, 1, 0, 0)
        self.assertEqual(ret[0]['bit_weight/value_d'], 1.880399419308285e-05)
        self.assertEqual(ret[1], False)

        # response loaded by metadata
        ret = self.n_i_fix.get_response_t('', '', 200, 1, 1, 1)
        self.assertEqual(ret[0]['response_file_das_a'],
                         '/Experiment_g/Responses_g/NoneQ330_NoneCMG3T_200HHN')
        self.assertEqual(ret[1], True)

        # response entry created by metadata when instrument has no response
        ret = self.n_i_fix.get_response_t('', '', 0, 1, 0, -1)
        self.assertEqual(ret[0]['n_i'], -1)
        self.assertEqual(ret[1], True)

    def test_create_list(self):
        ret = self.n_i_fix.create_list()

        self.assertEqual(
            (ret[0].array, ret[0].channel, ret[0].sample_rate,
             ret[0].das_model, ret[0].sensor_model, ret[0].gain,
             ret[0].bit_weight, ret[0].response_n_i),
            ('1', 1, 500, 'ZLAND3C', '', 24, 1.880399419308285e-05, None)
        )
        self.assertEqual(
            (ret[1].array, ret[1].channel, ret[1].sample_rate,
             ret[1].das_model, ret[1].sensor_model, ret[1].gain,
             ret[1].bit_weight, ret[1].response_n_i),
            ('1', 2, 500, 'ZLAND3C', '', 24, 1.880399419308285e-05, None)
        )
        self.assertEqual(
            (ret[2].array, ret[2].channel, ret[2].sample_rate,
             ret[2].das_model, ret[2].sensor_model, ret[2].gain,
             ret[2].bit_weight, ret[2].response_n_i),
            ('1', 3, 500, 'ZLAND3C', '', 24, 1.880399419308285e-05, None)
        )
        self.assertEqual(
            (ret[3].array, ret[3].channel, ret[3].sample_rate,
             ret[3].das_model, ret[3].sensor_model, ret[3].gain,
             ret[3].bit_weight, ret[3].response_n_i),
            ('2', 1, 200, 'NoneQ330', 'NoneCMG-3T', 1, 0.0, 1)
        )
        self.assertEqual(
            (ret[4].array, ret[4].channel, ret[4].sample_rate,
             ret[4].das_model, ret[4].sensor_model, ret[4].gain,
             ret[4].bit_weight, ret[4].response_n_i),
            ('3', 1, 100, 'NoneQ330', 'NoneCMG-3T', 1, 0.0, 2)
        )
        self.assertEqual(
            (ret[5].array, ret[5].channel, ret[5].sample_rate,
             ret[5].das_model, ret[5].sensor_model, ret[5].gain,
             ret[5].bit_weight, ret[5].response_n_i),
            ('4', -2, 0, 'NoneQ330', 'NoneCMG-3T', 0, 0.0, -1)
        )

    def test_load_response(self):
        # check total entries in response_t
        entries = self.n_i_fix.ph5.Response_t['rows']
        old_entries = copy.copy(entries)
        data = self.n_i_fix.create_list()
        ret = self.n_i_fix.load_response(
            '.', 'master.ph5', data,
            os.path.join(self.home, 'ph5/test_data/metadata/input.csv'))
        # check array data
        self.assertEqual(
            (ret[0].array, ret[0].id_s, ret[0].channel, ret[0].response_n_i),
            ('1', '500', 1, 3))
        self.assertEqual(
            (ret[1].array, ret[1].id_s, ret[1].channel, ret[1].response_n_i),
            ('1', '500', 2, 3))
        self.assertEqual(
            (ret[2].array, ret[2].id_s, ret[2].channel, ret[2].response_n_i),
            ('1', '500', 3, 3))
        self.assertEqual(
            (ret[3].array, ret[3].id_s, ret[3].channel, ret[3].response_n_i),
            ('2', '0407', 1, 1))
        self.assertEqual(
            (ret[4].array, ret[4].id_s, ret[4].channel, ret[4].response_n_i),
            ('3', '0407', 1, 2))
        self.assertEqual(
            (ret[5].array, ret[5].id_s, ret[5].channel, ret[5].response_n_i),
            ('4', '0407', -2, -1))

        # check response data has one more entry with new n_i created
        self.assertEqual(len(entries), 5)
        self.assertEqual(entries[0:4], old_entries)
        self. assertEqual(entries[4]['bit_weight/value_d'],
                          1.880399419308285e-05)
        self.assertEqual(entries[4]['n_i'], 3)

    def test_load_respdata(self):
        data = self.n_i_fix.read_respdata(
            os.path.join(self.home,
                         'ph5/test_data/metadata/RESP/125a500_32_RESP'))
        ph5table = self.n_i_fix.ph5.ph5
        loaded_list = []
        # reload_resp=False
        # First load with first_load=True
        with LogCapture() as log:
            self.n_i_fix.load_respdata(ph5table, 'rt125a_500_1_32',
                                       data, loaded_list, True)
            self.assertEqual(loaded_list, ['rt125a_500_1_32'])
            self.assertEqual(log.records[0].msg,
                             "Loaded rt125a_500_1_32")
        # Already loaded with first_load=False
        with LogCapture() as log:
            self.n_i_fix.load_respdata(ph5table, 'rt125a_500_1_32',
                                       data, loaded_list, False)
            self.assertEqual(loaded_list, ['rt125a_500_1_32'])
            self.assertEqual(log.records[0].msg,
                             "Reloaded rt125a_500_1_32.")
        # Already loaded with first_load=True, reload_resp=False
        with LogCapture() as log:
            self.n_i_fix.load_respdata(ph5table, 'rt125a_500_1_32',
                                       data, loaded_list, True)
            self.assertEqual(loaded_list, ['rt125a_500_1_32'])
            self.assertEqual(
                log.records[0].msg,
                "rt125a_500_1_32 has been loaded in another resp_load run.")
        # Already loaded with first_load=True, reload_resp=True
        self.n_i_fix.reload_resp = True
        with LogCapture() as log:
            self.n_i_fix.load_respdata(ph5table, 'rt125a_500_1_32',
                                       data, loaded_list, True)
            self.assertEqual(loaded_list, ['rt125a_500_1_32'])
            self.assertEqual(log.records[0].msg,
                             "Reloaded rt125a_500_1_32.")

    def test_read_respdata(self):
        ret = self.n_i_fix.read_respdata(
            os.path.join(self.home,
                         'ph5/test_data/metadata/RESP/125a500_32_RESP'))
        self.assertIn('RESP', ret[0])


if __name__ == "__main__":
    unittest.main()
