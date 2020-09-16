'''
Tests for obspytoph5
'''
import os
import sys
import unittest
import logging

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.utilities import obspytoph5, initialize_ph5
from ph5.utilities import metadatatoph5
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase,\
    initialize_ex, das_in_mini


class TestObspytoPH5_main(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestObspytoPH5_main, self).setUp()
        self.station_xml_path = os.path.join(
            self.home, 'ph5/test_data/metadata/station.xml')

    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestObspytoPH5_main, self).tearDown()

    def test_main1(self):
        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    self.station_xml_path]
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()

        # need to use relative path '../miniseed/' because das_t's
        # 'raw_file_name_s will be chopped off if the path's length is greater
        # than 32
        testargs = ['obspytoph5', '-n', 'master.ph5', '-d',
                    '../miniseed/']
        with patch.object(sys, 'argv', testargs):
            obspytoph5.main()
        self.assertTrue(os.path.isfile('master.ph5'))
        self.assertTrue(os.path.isfile('miniPH5_00001.ph5'))

        self.ph5_object = initialize_ex('master.ph5', '.', False)
        node = self.ph5_object.ph5_g_receivers.getdas_g('5553')
        self.ph5_object.ph5_g_receivers.setcurrent(node)
        ret, das_keys = self.ph5_object.ph5_g_receivers.read_das()
        keys = ['array_name_SOH_a', 'array_name_data_a', 'array_name_event_a',
                'array_name_log_a', 'channel_number_i', 'event_number_i',
                'raw_file_name_s', 'receiver_table_n_i', 'response_table_n_i',
                'sample_count_i', 'sample_rate_i', 'sample_rate_multiplier_i',
                'stream_number_i', 'time/ascii_s', 'time/epoch_l',
                'time/micro_seconds_i', 'time/type_s', 'time_table_n_i']
        self.assertEqual(keys, das_keys)
        self.assertEqual('../miniseed/0407HHN.ms',
                         ret[0]['raw_file_name_s'])
        self.assertEqual('../miniseed/0407LHN.ms',
                         ret[1]['raw_file_name_s'])

    def test_main2(self):
        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    self.station_xml_path]
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()

        # need to use relative path '../miniseed/' because das_t's
        # 'raw_file_name_s will be chopped off if the path's length is greater
        # than 32
        testargs = ['obspytoph5', '-n', 'master.ph5', '-f',
                    '../miniseed/0407HHN.ms']
        with patch.object(sys, 'argv', testargs):
            obspytoph5.main()
        self.assertTrue(os.path.isfile('master.ph5'))
        self.assertTrue(os.path.isfile('miniPH5_00001.ph5'))

        self.ph5_object = initialize_ex('master.ph5', '.', False)
        node = self.ph5_object.ph5_g_receivers.getdas_g('5553')
        self.ph5_object.ph5_g_receivers.setcurrent(node)
        ret, das_keys = self.ph5_object.ph5_g_receivers.read_das()
        keys = ['array_name_SOH_a', 'array_name_data_a', 'array_name_event_a',
                'array_name_log_a', 'channel_number_i', 'event_number_i',
                'raw_file_name_s', 'receiver_table_n_i', 'response_table_n_i',
                'sample_count_i', 'sample_rate_i', 'sample_rate_multiplier_i',
                'stream_number_i', 'time/ascii_s', 'time/epoch_l',
                'time/micro_seconds_i', 'time/type_s', 'time_table_n_i']
        self.assertEqual(keys, das_keys)
        self.assertEqual('../miniseed/0407HHN.ms',
                         ret[0]['raw_file_name_s'])

    def test_main3(self):
        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    self.station_xml_path]
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()

        with open("test_list", "w") as f:
            # need to use relative path '../miniseed/0407HHN.ms' because
            # das_t's 'raw_file_name_s will be chopped off if the path's
            # length is greater than 32
            f.write("../miniseed/0407HHN.ms")
        # first need to run obspytoph5
        testargs = ['obspytoph5', '-n', 'master.ph5', '-l',
                    'test_list']
        with patch.object(sys, 'argv', testargs):
            obspytoph5.main()
        self.assertTrue(os.path.isfile('master.ph5'))
        self.assertTrue(os.path.isfile('miniPH5_00001.ph5'))

        self.ph5_object = initialize_ex('master.ph5', '.', False)
        node = self.ph5_object.ph5_g_receivers.getdas_g('5553')
        self.ph5_object.ph5_g_receivers.setcurrent(node)
        ret, das_keys = self.ph5_object.ph5_g_receivers.read_das()
        keys = ['array_name_SOH_a', 'array_name_data_a', 'array_name_event_a',
                'array_name_log_a', 'channel_number_i', 'event_number_i',
                'raw_file_name_s', 'receiver_table_n_i', 'response_table_n_i',
                'sample_count_i', 'sample_rate_i', 'sample_rate_multiplier_i',
                'stream_number_i', 'time/ascii_s', 'time/epoch_l',
                'time/micro_seconds_i', 'time/type_s', 'time_table_n_i']
        self.assertEqual(keys, das_keys)
        self.assertEqual('../miniseed/0407HHN.ms',
                         ret[0]['raw_file_name_s'])


class TestObspytoPH5(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestObspytoPH5, self).setUp()
        self.station_xml_path = os.path.join(
            self.home, 'ph5/test_data/metadata/station.xml')
        self.ph5_object = initialize_ex('master.ph5', self.tmpdir, True)
        self.obs = obspytoph5.ObspytoPH5(self.ph5_object, self.tmpdir, 1, 1)
        self.obs.verbose = True
        self.ph5_object.ph5flush()
        self.ph5_object.ph5_g_sorts.update_local_table_nodes()

    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestObspytoPH5, self).tearDown()

    def test_get_args(self):
        with OutputCapture():
            with self.assertRaises(SystemExit):
                obspytoph5.get_args([])

        ret = obspytoph5.get_args(['-n', 'master.ph5', '-f', 'test.ms',
                                   '-V'])
        self.assertEqual(ret.nickname, 'master.ph5')
        self.assertEqual(ret.infile, 'test.ms')
        self.assertEqual(ret.ph5path, '.')
        self.assertTrue(ret.verbose)

        # error when -M and -F is used at the same time
        testargs = ['-n', 'master.ph5', '-f', 'test.ms', '-M', '5', '-F', '3']
        with OutputCapture():
            self.assertRaises(
                SystemExit,
                obspytoph5.get_args,
                testargs)
        # -M
        testargs = ['-n', 'master.ph5', '-f', 'test.ms', '-M', '5']
        with OutputCapture():
            ret = obspytoph5.get_args(testargs)
        self.assertEqual(ret.num_mini, 5)

        # -F
        testargs = ['-n', 'master.ph5', '-f', 'test.ms', '-F', '5']
        with OutputCapture():
            ret = obspytoph5.get_args(testargs)
        self.assertEqual(ret.from_mini, 5)

    def test_to_ph5(self):
        index_t_full = list()
        # try load without metadata
        # need to use relative path '../miniseed/0407HHN.ms' because das_t's
        # 'raw_file_name_s will be chopped off if the path's length is greater
        # than 32
        entry = "../miniseed/0407HHN.ms"
        message, index_t = self.obs.toph5((entry, 'MSEED'))
        self.assertFalse(index_t)
        self.assertEqual('stop', message)

        # with metadata
        metadata = metadatatoph5.MetadatatoPH5(self.obs.ph5)
        with open(self.station_xml_path, "r") as f:
            inventory_ = metadata.read_metadata(f, "station.xml")
        parsed_array = metadata.parse_inventory(inventory_)
        metadata.toph5(parsed_array)
        self.obs.ph5.initgroup()
        message, index_t = self.obs.toph5((entry, 'MSEED'))
        self.assertTrue('done', message)
        self.assertTrue(1, len(index_t))
        for e in index_t:
            index_t_full.append(e)

        # load LOG CH
        # need to use relative path '../miniseed/0407LOG.ms' because das_t's
        # 'raw_file_name_s will be chopped off if the path's length is greater
        # than 32
        entry = "../miniseed/0407LOG.ms"
        message, index_t = self.obs.toph5((entry, 'MSEED'))
        self.assertTrue('done', message)
        self.assertTrue(1, len(index_t))
        for e in index_t:
            index_t_full.append(e)
        if len(self.obs.time_t) > 0:
            for entry in self.obs.time_t:
                self.obs.ph5.ph5_g_receivers.populateTime_t_(entry)
        for entry in index_t_full:
            self.obs.ph5.ph5_g_receivers.populateIndex_t(entry)
        self.obs.update_external_references(index_t_full)
        self.assertTrue(os.path.isfile("master.ph5"))
        self.assertTrue(os.path.isfile("miniPH5_00001.ph5"))

        node = self.obs.ph5.ph5_g_receivers.getdas_g('5553')
        self.obs.ph5.ph5_g_receivers.setcurrent(node)
        ret, das_keys = self.obs.ph5.ph5_g_receivers.read_das()
        keys = ['array_name_SOH_a', 'array_name_data_a', 'array_name_event_a',
                'array_name_log_a', 'channel_number_i', 'event_number_i',
                'raw_file_name_s', 'receiver_table_n_i', 'response_table_n_i',
                'sample_count_i', 'sample_rate_i', 'sample_rate_multiplier_i',
                'stream_number_i', 'time/ascii_s', 'time/epoch_l',
                'time/micro_seconds_i', 'time/type_s', 'time_table_n_i']
        self.assertEqual(keys, das_keys)
        self.assertEqual('../miniseed/0407HHN.ms',
                         ret[0]['raw_file_name_s'])
        self.assertEqual('../miniseed/0407LOG.ms',
                         ret[1]['raw_file_name_s'])

        # test from_mini=3, data will be added to mini 3
        # load LHN CH
        # need to use relative path '../miniseed/0407LHN.ms' because das_t's
        # 'raw_file_name_s will be chopped off if the path's length is greater
        # than 32
        self.obs.from_mini = 3
        entry = "../miniseed/0407LHN.ms"
        message, index_t = self.obs.toph5((entry, 'MSEED'))
        self.assertTrue('done', message)
        self.assertTrue(1, len(index_t))
        for e in index_t:
            index_t_full.append(e)
        if len(self.obs.time_t) > 0:
            for entry in self.obs.time_t:
                self.obs.ph5.ph5_g_receivers.populateTime_t_(entry)
        for entry in index_t_full:
            self.obs.ph5.ph5_g_receivers.populateIndex_t(entry)
        self.obs.update_external_references(index_t_full)
        self.assertTrue(os.path.isfile("master.ph5"))
        self.assertTrue(os.path.isfile("miniPH5_00003.ph5"))

        node = self.obs.ph5.ph5_g_receivers.getdas_g('5553')
        self.obs.ph5.ph5_g_receivers.setcurrent(node)
        ret, das_keys = self.obs.ph5.ph5_g_receivers.read_das()
        self.assertEqual(keys, das_keys)
        self.assertEqual('../miniseed/0407LHN.ms',
                         ret[0]['raw_file_name_s'])

    def test_main(self):
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()

        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    os.path.join(self.home,
                                 'ph5/test_data/metadata/station.xml')]
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()

        # create mini 1
        testargs = ['obspytoph5', '-n', 'master.ph5', '-f',
                    os.path.join(self.home,
                                 'ph5/test_data/miniseed', '0407HHN.ms')]
        with patch.object(sys, 'argv', testargs):
            obspytoph5.main()
        # check mini=1 in tmpdir
        ph5set = {f for f in os.listdir(self.tmpdir) if f.endswith('.ph5')}
        self.assertEqual(ph5set, {'miniPH5_00001.ph5', 'master.ph5'})
        self.assertEqual(das_in_mini(self.tmpdir, 'miniPH5_00001.ph5'),
                         ['Das_g_5553'])

        # use FROM_MINI=4 > Highest_mini=1
        testargs = ['obspytoph5', '-n', 'master.ph5', '-f',
                    os.path.join(self.home,
                                 'ph5/test_data/miniseed', '0407LHN.ms'),
                    '-F', '4']
        with patch.object(sys, 'argv', testargs):
            obspytoph5.main()
        # check mini=4 in tmpdir
        ph5set = {f for f in os.listdir(self.tmpdir) if f.endswith('.ph5')}
        self.assertEqual(ph5set, {'miniPH5_00001.ph5', 'miniPH5_00004.ph5',
                                  'master.ph5'})
        self.assertEqual(das_in_mini(self.tmpdir, 'miniPH5_00004.ph5'),
                         ['Das_g_5553'])

        # use FROM_MINI=4 < Highest_mini=1 => error
        testargs = ['obspytoph5', '-n', 'master.ph5', '-f',
                    os.path.join(self.home,
                                 'ph5/test_data/miniseed', '0407LHN.ms'),
                    '-F', '3']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                self.assertRaises(SystemExit, obspytoph5.main)
                self.assertEqual(log.records[0].msg,
                                 'FROM_MINI must be greater than or equal to 4'
                                 ', the highest mini file in ph5.')


if __name__ == "__main__":
    unittest.main()
