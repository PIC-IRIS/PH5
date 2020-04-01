'''
Tests for obspytoph5
'''
import os
import sys
import unittest

from mock import patch
from testfixtures import OutputCapture

from ph5.utilities import obspytoph5
from ph5.utilities import metadatatoph5
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase,\
    initialize_ex


class TestObspytoPH5(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestObspytoPH5, self).setUp()
        self.station_xml_path = os.path.join(
            self.home, 'ph5/test_data/metadata/station.xml')
        if 'test_main' not in self._testMethodName:
            # the condition exclude test_main1/2/3() when creating
            # self.ph5_object because in test_main(), self.ph5_object have to
            # be created after the call of main() to check the data added
            # by main()
            self.ph5_object = initialize_ex('master.ph5', self.tmpdir, True)
            self.obs = obspytoph5.ObspytoPH5(
                self.ph5_object,
                self.tmpdir,
                1,
                1)
            self.obs.verbose = True
            self.ph5_object.ph5flush()
            self.ph5_object.ph5_g_sorts.update_local_table_nodes()

    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestObspytoPH5, self).tearDown()

    def test_get_args(self):
        """
        test get_args
        """
        with OutputCapture():
            with self.assertRaises(SystemExit):
                obspytoph5.get_args([])

        ret = obspytoph5.get_args(['-n', 'master.ph5', '-f', 'test.ms',
                                   '-V'])
        self.assertEqual(ret.nickname, 'master.ph5')
        self.assertEqual(ret.infile, 'test.ms')
        self.assertEqual(ret.ph5path, '.')
        self.assertTrue(ret.verbose)

    def test_main1(self):
        # first need to run metadatatoph5
        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    self.station_xml_path]
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()

        # first need to run obspytoph5
        # need to use relative path '../miniseed/' because das_t's
        # 'raw_file_name_s will be chopped off if the path's length is greater
        # than 32
        testargs = ['obspytoph5', '-n', 'master.ph5', '-d',
                    '../miniseed/']
        with patch.object(sys, 'argv', testargs):
            obspytoph5.main()
        self.assertTrue(os.path.isfile('master.ph5'))
        self.assertTrue(os.path.isfile('miniPH5_00001.ph5'))

        # This self.ph5_object isn't the repeat of the self.ph5_object in
        # setUp() because the one in setUp() already excludes test_main().
        # This self.ph5_object has to be created after
        # the call of main() to check the data added by main()
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
        # first need to run metadatatoph5
        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    self.station_xml_path]
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()
        # first need to run obspytoph5
        # need to use relative path '../miniseed/' because das_t's
        # 'raw_file_name_s will be chopped off if the path's length is greater
        # than 32
        testargs = ['obspytoph5', '-n', 'master.ph5', '-f',
                    '../miniseed/0407HHN.ms']
        with patch.object(sys, 'argv', testargs):
            obspytoph5.main()
        self.assertTrue(os.path.isfile('master.ph5'))
        self.assertTrue(os.path.isfile('miniPH5_00001.ph5'))

        # This self.ph5_object isn't the repeat of the self.ph5_object in
        # setUp() because the one in setUp() already excludes test_main().
        # This self.ph5_object has to be created after
        # the call of main() to check the data added by main()
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
        # first need to run metadatatoph5
        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    self.station_xml_path]
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()

        # now make a list for obspytoph5
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

        # This self.ph5_object isn't the repeat of the self.ph5_object in
        # setUp() because the one in setUp() already excludes test_main().
        # This self.ph5_object has to be created after
        # the call of main() to check the data added by main()
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

    def test_to_ph5(self):
        """
        test to_ph5
        """
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

        # now load LOG CH
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


if __name__ == "__main__":
    unittest.main()
