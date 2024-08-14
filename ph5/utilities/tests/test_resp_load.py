'''
Tests for resp_load
'''
import os
import sys
import unittest
import copy
import logging

import tables
from mock import patch
from testfixtures import LogCapture

from ph5.core import ph5api, columns
from ph5.utilities import resp_load, segd2ph5, metadatatoph5, obspytoph5, \
    initialize_ph5, tabletokef
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


class Test_n_i_fix_indiv(TempDirTestCase, LogTestCase):
    def tearDown(self):
        try:
            self.ph5API_object.ph5close()
        except AttributeError:
            pass
        super(Test_n_i_fix_indiv, self).tearDown()

    def test_main(self):
        testargs = ['segdtoph5', '-n', 'master.ph5', '-r',
                    os.path.join(self.home,
                                 "ph5/test_data/segd/fairfield/3ch.fcnt")]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        testargs = [
            'resp_load', '-n', 'master.ph5', '-a', '1', '-i',
            os.path.join(self.home, 'ph5/test_data/metadata/input.csv')]
        with patch.object(sys, 'argv', testargs):
            resp_load.main()
        self.ph5API_object = ph5api.PH5(path='.', nickname='master.ph5')
        # check array_t
        self.ph5API_object.read_array_t('Array_t_001')
        entries = self.ph5API_object.Array_t['Array_t_001']['byid']['500'][1]
        self.assertEqual(entries[0]['response_table_n_i'], 0)
        self.assertEqual(entries[0]['receiver_table_n_i'], 1)

        # check response_t
        response_t = self.ph5API_object.get_response_t_by_n_i(0)
        self.assertEqual(response_t['response_file_das_a'],
                         '/Experiment_g/Responses_g/ZLAND3C_500_1_24')

        # check response data loaded for all response files listed in input.csv
        try:
            self.ph5API_object.ph5.get_node('/Experiment_g/Responses_g/',
                                            'ZLAND3C_500_1_24')
            self.ph5API_object.ph5.get_node('/Experiment_g/Responses_g/',
                                            'cmg3t')
            self.ph5API_object.ph5.get_node('/Experiment_g/Responses_g/',
                                            'gs11v')
            self.ph5API_object.ph5.get_node('/Experiment_g/Responses_g/',
                                            'rt125a_500_1_32')
            self.ph5API_object.ph5.get_node('/Experiment_g/Responses_g/',
                                            'rt130_100_1_1')
        except tables.NoSuchNodeError as e:
            raise AssertionError(e)

    def test_group_list_dict(self):
        data = [{'das': 'rt130', 'sr': 100, 'srm': 1, 'st_id': '1001'},
                {'das': 'rt130', 'sr': 1, 'srm': 1, 'st_id': '1003'},
                {'das': 'rt130', 'sr': 100, 'srm': 1, 'st_id': '1002'},
                {'das': 'rt130', 'sr': 1, 'srm': 1, 'st_id': '1004'}]
        ret = resp_load.group_list_dict(data, ['st_id'])
        self.assertEqual(
            sorted(ret),
            [{'das': 'rt130', 'sr': 1, 'srm': 1, 'st_ids': ['1003', '1004']},
             {'das': 'rt130', 'sr': 100, 'srm': 1, 'st_ids': ['1001', '1002']},
             ]
        )


class Test_n_i_fix(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(Test_n_i_fix, self).setUp()
        """
        use metadata to add metadata info
         array_002-st0407 - das5553 - response_n_i=0
         array_003-st0407 - das5553 - response_n_i=1
         array_004-st0407 - das5553 - response_n_i=-1
         response_t: n_i=0 response_file_das_a= NoneQ330_NoneCMG3T_200HHN
         response_t: n_i=1 response_file_das_a= NoneQ330_NoneCMG3T_100LHN
         response_t: n_i=-1
        """
        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    os.path.join(self.home,
                                 "ph5/test_data/metadata/station.xml"),
                    '--force']
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()
        """
        add das_t 5553's
        """
        testargs = ['mstoph5', '-n', 'master.ph5', '-d',
                    os.path.join(self.home,
                                 "ph5/test_data/miniseed"),
                    '--force']
        with patch.object(sys, 'argv', testargs):
            obspytoph5.main()

        """
        add create master.ph5 with the following tables:
         array_001-sta500-cha1,2,3-das3x500-modelZLAND_sr500-response_n_i0
         das_3x500
         response_t: n_i=0 bit_weight=1.88e-05
        """
        testargs = ['segdtoph5', '-n', 'master.ph5', '-r',
                    os.path.join(self.home,
                                 "ph5/test_data/segd/fairfield/3ch.fcnt")]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        self.ph5API_object = ph5api.PH5(path='.',
                                        nickname='master.ph5',
                                        editmode=True)
        self.n_i_fix = resp_load.n_i_fix(self.ph5API_object, False, True,
                                         ['1', '2', '3', '4'])

    def tearDown(self):
        self.ph5API_object.ph5close()
        super(Test_n_i_fix, self).tearDown()

    def test_load_response(self):
        # check total entries in response_t
        self.n_i_fix.ph5.read_response_t()
        entries = self.n_i_fix.ph5.Response_t['rows']
        old_entries = copy.copy(entries)

        # skip_update_resp = True
        data = self.n_i_fix.create_list()

        alllogs = ['Loaded rt125a_500_1_32', 'Loaded gs11v',
                   'Loaded ZLAND3C_500_1_24', 'Loaded rt130_100_1_1',
                   'Loaded cmg3t', 'Skip updating response index in '
                   'response_t and array_t.']
        with LogCapture() as log:
            self.n_i_fix.load_response(
                '.', data,
                os.path.join(self.home, 'ph5/test_data/metadata/input.csv'))
            for i in range(len(log.records)):
                self.assertEqual(log.records[i].msg, alllogs[i])

        # response_t not changed
        self.assertEqual(entries, old_entries)
        # check response data loaded for all response files listed in input.csv
        try:
            self.n_i_fix.ph5.ph5.get_node('/Experiment_g/Responses_g/',
                                          'ZLAND3C_500_1_24')
            self.n_i_fix.ph5.ph5.get_node('/Experiment_g/Responses_g/',
                                          'cmg3t')
            self.n_i_fix.ph5.ph5.get_node('/Experiment_g/Responses_g/',
                                          'gs11v')
            self.n_i_fix.ph5.ph5.get_node('/Experiment_g/Responses_g/',
                                          'rt125a_500_1_32')
            self.n_i_fix.ph5.ph5.get_node('/Experiment_g/Responses_g/',
                                          'rt130_100_1_1')
        except tables.NoSuchNodeError as e:
            raise AssertionError(e)

        # skip_update_resp = False
        self.n_i_fix.skip_update_resp = False
        alllogs = [
            'rt125a_500_1_32 has been loaded in another resp_load run.',
            'gs11v has been loaded in another resp_load run.',
            'ZLAND3C_500_1_24 has been loaded in another resp_load run.',
            'rt130_100_1_1 has been loaded in another resp_load run.',
            'cmg3t has been loaded in another resp_load run.',
            'Writing table backup: Response_t__00.kef.',
            'Writing table backup: Array_t_001__00.kef.',
            'Writing table backup: Array_t_002__00.kef.',
            'Writing table backup: Array_t_003__00.kef.',
            'Update Response_t.', 'Update Array_t_001.', 'Update Array_t_002.',
            'Update Array_t_003.', 'Array_t_004 not in ph5.']
        with LogCapture() as log:
            log.setLevel(logging.INFO)
            self.n_i_fix.load_response(
                '.', data,
                os.path.join(self.home, 'ph5/test_data/metadata/input.csv'))
            for i in range(len(log.records)):
                msg = log.records[i].msg
                if 'kef' not in msg:
                    self.assertEqual(msg, alllogs[i])
                else:
                    # remove the time info in kef file name
                    if 'Response' in msg:
                        self.assertEqual(msg[0:33] + msg[40:], alllogs[i])
                    else:
                        self.assertEqual(msg[0:34] + msg[41:], alllogs[i])

        # check response_table_n_i used the existing response_t's n_i
        self.assertEqual(self.n_i_fix.ph5.Array_t['Array_t_001']['byid'][
                             '500'][1][0]['response_table_n_i'],
                         3)
        self.assertEqual(self.n_i_fix.ph5.Array_t['Array_t_001']['byid'][
                             '500'][2][0]['response_table_n_i'],
                         3)
        # check receiver_table_n_i is updated
        self.assertEqual(self.n_i_fix.ph5.Array_t['Array_t_001']['byid'][
                             '500'][1][0]['receiver_table_n_i'],
                         1)
        self.assertEqual(self.n_i_fix.ph5.Array_t['Array_t_001']['byid'][
                             '500'][2][0]['receiver_table_n_i'],
                         2)
        # check response_table_n_i created by metadata unchanged
        self.assertEqual(self.n_i_fix.ph5.Array_t['Array_t_001']['byid'][
                             '0407'][1][0]['response_table_n_i'],
                         0)
        self.assertEqual(self.n_i_fix.ph5.Array_t['Array_t_002']['byid'][
                             '0407'][1][0]['response_table_n_i'],
                         1)
        self.assertEqual(self.n_i_fix.ph5.Array_t['Array_t_003']['byid'][
                             '0407'][-2][0]['response_table_n_i'],
                         -1)

        # check response_t filenames filled
        self.assertEqual(self.n_i_fix.ph5.Response_t['rows'][3]
                         ['response_file_das_a'],
                         '/Experiment_g/Responses_g/ZLAND3C_500_1_24')
        self.assertEqual(self.n_i_fix.ph5.Response_t['rows'][0]
                         ['response_file_sensor_a'],
                         '')

        # check different sample rate that use same n_i, create new n_i
        self.ph5API_object.initgroup()
        data[1].sample_rate = 100
        with LogCapture() as log:
            log.setLevel(logging.INFO)
            self.n_i_fix.load_response(
                '.', data,
                os.path.join(self.home, 'ph5/test_data/metadata/input.csv'))
            # n-i changed from 3 to 4 for sr=100 b/c 3 has been used for sr=500
            self.assertEqual(log.records[9].msg, '-ZLAND3C-100-1: n_i 3=>4')
        self.assertEqual(self.n_i_fix.ph5.Array_t['Array_t_001']['byid'][
                             '500'][1][0]['response_table_n_i'],
                         4)
        self.assertEqual(self.n_i_fix.ph5.Response_t['rows'][4]['n_i'],
                         4)
        self.assertEqual(self.n_i_fix.ph5.Response_t['rows'][4]
                         ['response_file_das_a'],
                         '/Experiment_g/Responses_g/ZLAND3C_100_1_24')

        # check n_i created by another resp_load run keep the same
        self.n_i_fix.reload_resp_data = True  # force reloading response data
        self.ph5API_object.initgroup()
        with LogCapture() as log:
            self.n_i_fix.load_response(
                '.', data,
                os.path.join(self.home, 'ph5/test_data/metadata/input.csv'))
            # check reloading response data
            self.assertEqual(log.records[0].msg, 'Reloaded rt125a_500_1_32.')
        self.assertEqual(self.n_i_fix.ph5.Array_t['Array_t_001']['byid'][
                             '500'][1][0]['response_table_n_i'],
                         4)
        self.assertEqual(self.n_i_fix.ph5.Response_t['rows'][4]['n_i'],
                         4)

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
        self.n_i_fix.reload_resp_data = True
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


class Test_n_i_fix_simpleph5object(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(Test_n_i_fix_simpleph5object, self).setUp()
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()
        self.ph5API_object = ph5api.PH5(path='.',
                                        nickname='master.ph5',
                                        editmode=True)
        self.n_i_fix = resp_load.n_i_fix(self.ph5API_object, False, True,
                                         ['1', '2', '3', '4'])

    def tearDown(self):
        self.ph5API_object.ph5close()
        super(Test_n_i_fix_simpleph5object, self).tearDown()

    def test_init(self):
        self.assertEqual(self.n_i_fix.array, ['1', '2', '3', '4'])
        self.assertEqual(self.n_i_fix.reload_resp_data, False)
        self.assertEqual(self.n_i_fix.skip_update_resp, True)
        self.assertTrue(hasattr(self.n_i_fix.ph5, 'Array_t_names'))

    def test_get_resp_file_names(self):
        x = {'d_model': '', 's_model': 'SMODEL', 's_rate': 100,
             's_rate_m': 1, 'gain': 1}
        ret = self.n_i_fix.get_resp_file_names(x)
        self.assertFalse(ret)

        x['d_model'] = 'DMODEL'
        ret = self.n_i_fix.get_resp_file_names(x)
        self.assertEqual(ret[0], '/Experiment_g/Responses_g/DMODEL_100_1_1')
        self.assertEqual(ret[1], '/Experiment_g/Responses_g/SMODEL')

        x['s_model'] = ''
        ret = self.n_i_fix.get_resp_file_names(x)
        self.assertFalse(ret)

        x['d_model'] = 'ZLAND_'
        ret = self.n_i_fix.get_resp_file_names(x)
        self.assertEqual(ret[0], '/Experiment_g/Responses_g/ZLAND__100_1_1')
        self.assertEqual(ret[1], '')

    def test_check_metadata_format(self):
        x = {'d_model': 'DMODEL'}
        response_entry = {'response_file_das_a':
                          '/Experiment_g/Responses_g/DMODEL_100_1_1'}
        ret = self.n_i_fix.check_metadata_format(response_entry, x)
        self.assertFalse(ret)

        response_entry['response_file_das_a'] = \
            '/Experiment_g/Responses_g/DMODEL_SMODEL_100HHN'
        ret = self.n_i_fix.check_metadata_format(response_entry, x)
        self.assertTrue(ret)

        x['d_model'] = 'DMODEL1'
        ret = self.n_i_fix.check_metadata_format(response_entry, x)
        self.assertFalse(ret)

        response_entry['response_file_das_a'] = ''
        ret = self.n_i_fix.check_metadata_format(response_entry, x)
        self.assertFalse(ret)

    def test_update_array(self):
        x = {'station_entrys': [{'ids': 1, 'response_table_n_i': 0},
                                {'ids': 2, 'response_table_n_i': 0}]}
        self.n_i_fix.update_array(x, 2)
        self.assertEqual(x['station_entrys'],
                         [{'ids': 1, 'response_table_n_i': 2},
                          {'ids': 2, 'response_table_n_i': 2}]
                         )

    def test_write_backup(self):
        response_entry = {}
        response_entry['n_i'] = 1
        response_entry['bit_weight/value_d'] = 2
        response_entry['gain/value_i'] = 1
        response_entry['response_file_das_a'] = "das_path"
        response_entry['response_file_sensor_a'] = "sens_path"
        ref = columns.TABLES['/Experiment_g/Responses_g/Response_t']
        columns.populate(ref, response_entry, None)
        self.n_i_fix.ph5.read_response_t()
        response_t = tabletokef.Rows_Keys(self.n_i_fix.ph5.Response_t['rows'],
                                          self.n_i_fix.ph5.Response_t['keys'])

        with LogCapture() as log:
            resp_load.write_backup(response_t,
                                   '/Experiment_g/Responses_g/Response_t',
                                   'Response_t')
            msg = log.records[0].msg
            self.assertEqual(msg[0:33] + msg[40:],
                             'Writing table backup: Response_t__00.kef.')
        filename = msg.split(': ')[1][:-1]
        with open(os.path.join(self.tmpdir, filename), 'r') as content_file:
            content = content_file.read().strip().split("Table row 1")[1]
        self.assertEqual(
            content,
            "\n/Experiment_g/Responses_g/Response_t"
            "\n\tn_i=1"
            "\n\tbit_weight/value_d=2.0"
            "\n\tbit_weight/units_s="
            "\n\tgain/units_s="
            "\n\tgain/value_i=1"
            "\n\tresponse_file_a="
            "\n\tresponse_file_das_a=das_path"
            "\n\tresponse_file_sensor_a=sens_path"
        )


if __name__ == "__main__":
    unittest.main()
