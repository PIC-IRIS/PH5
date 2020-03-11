'''
Tests for metadatatoph5
'''
import unittest
from ph5.utilities import obspytoph5
from ph5.core import experiment
from ph5.utilities import initialize_ph5
import os
from ph5.utilities import metadatatoph5
import sys
from mock import patch
from ph5.core.tests.test_base import LogTestCase
from testfixtures import OutputCapture


class TestObspytoPH5(LogTestCase):
    def setUp(self):
        self.path = 'ph5/test_data/miniseedph5'
        os.mkdir(self.path)

        ph5_object = experiment.ExperimentGroup(
            nickname='master.ph5',
            currentpath=self.path)
        ph5_object.ph5open(True)
        ph5_object.initgroup()
        default_receiver_t = initialize_ph5.create_default_receiver_t()
        initialize_ph5.set_receiver_t(default_receiver_t)
        os.remove(default_receiver_t)
        ph5_object.initgroup()
        self.obs = obspytoph5.ObspytoPH5(
            ph5_object,
            self.path,
            1,
            1)
        self.obs.verbose = True
        ph5_object.ph5flush()
        ph5_object.ph5_g_sorts.update_local_table_nodes()

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

    def test_main(self):
        """
        test main
        """
        # first need to run metadatatoph5
        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    'ph5/test_data/metadata/station.xml']
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()

        # first need to run obspytoph5
        testargs = ['obspytoph5', '-n', 'master.ph5', '-d',
                    'ph5/test_data/miniseed/']
        with patch.object(sys, 'argv', testargs):
            obspytoph5.main()
        self.assertTrue(os.path.isfile('master.ph5'))
        self.assertTrue(os.path.isfile('miniPH5_00001.ph5'))
        ph5_object = experiment.ExperimentGroup(
            nickname='master.ph5')
        ph5_object.ph5open(True)
        ph5_object.initgroup()
        node = ph5_object.ph5_g_receivers.getdas_g('5553')
        ph5_object.ph5_g_receivers.setcurrent(node)
        ret, das_keys = ph5_object.ph5_g_receivers.read_das()
        keys = ['array_name_SOH_a', 'array_name_data_a', 'array_name_event_a',
                'array_name_log_a', 'channel_number_i', 'event_number_i',
                'raw_file_name_s', 'receiver_table_n_i', 'response_table_n_i',
                'sample_count_i', 'sample_rate_i', 'sample_rate_multiplier_i',
                'stream_number_i', 'time/ascii_s', 'time/epoch_l',
                'time/micro_seconds_i', 'time/type_s', 'time_table_n_i']
        self.assertEqual(keys, das_keys)
        self.assertEqual(
            'ph5/test_data/miniseed/0407HHN.m',
            ret[0]['raw_file_name_s'])
        self.assertEqual(
            'ph5/test_data/miniseed/0407LHN.m',
            ret[1]['raw_file_name_s'])
        ph5_object.ph5close()
        os.remove('master.ph5')
        os.remove('miniPH5_00001.ph5')
        os.remove('metadatatoph5.log')
        os.remove('datatoph5.log')

        # first need to run metadatatoph5
        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    'ph5/test_data/metadata/station.xml']
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()
        # first need to run obspytoph5
        testargs = ['obspytoph5', '-n', 'master.ph5', '-f',
                    'ph5/test_data/miniseed/0407HHN.ms']
        with patch.object(sys, 'argv', testargs):
            obspytoph5.main()
        self.assertTrue(os.path.isfile('master.ph5'))
        self.assertTrue(os.path.isfile('miniPH5_00001.ph5'))
        ph5_object = experiment.ExperimentGroup(
            nickname='master.ph5')
        ph5_object.ph5open(True)
        ph5_object.initgroup()
        node = ph5_object.ph5_g_receivers.getdas_g('5553')
        ph5_object.ph5_g_receivers.setcurrent(node)
        ret, das_keys = ph5_object.ph5_g_receivers.read_das()
        keys = ['array_name_SOH_a', 'array_name_data_a', 'array_name_event_a',
                'array_name_log_a', 'channel_number_i', 'event_number_i',
                'raw_file_name_s', 'receiver_table_n_i', 'response_table_n_i',
                'sample_count_i', 'sample_rate_i', 'sample_rate_multiplier_i',
                'stream_number_i', 'time/ascii_s', 'time/epoch_l',
                'time/micro_seconds_i', 'time/type_s', 'time_table_n_i']
        self.assertEqual(keys, das_keys)
        self.assertEqual(
            'ph5/test_data/miniseed/0407HHN.m',
            ret[0]['raw_file_name_s'])
        ph5_object.ph5close()
        os.remove('master.ph5')
        os.remove('miniPH5_00001.ph5')
        os.remove('metadatatoph5.log')
        os.remove('datatoph5.log')

        # first need to run metadatatoph5
        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    'ph5/test_data/metadata/station.xml']
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()

        # now make a list for obspytoph5
        f = open("test_list", "w")
        f.write("ph5/test_data/miniseed/0407HHN.ms")
        f.close()
        # first need to run obspytoph5
        testargs = ['obspytoph5', '-n', 'master.ph5', '-l',
                    'test_list']
        with patch.object(sys, 'argv', testargs):
            obspytoph5.main()
        self.assertTrue(os.path.isfile('master.ph5'))
        self.assertTrue(os.path.isfile('miniPH5_00001.ph5'))
        ph5_object = experiment.ExperimentGroup(
            nickname='master.ph5')
        ph5_object.ph5open(True)
        ph5_object.initgroup()
        node = ph5_object.ph5_g_receivers.getdas_g('5553')
        ph5_object.ph5_g_receivers.setcurrent(node)
        ret, das_keys = ph5_object.ph5_g_receivers.read_das()
        keys = ['array_name_SOH_a', 'array_name_data_a', 'array_name_event_a',
                'array_name_log_a', 'channel_number_i', 'event_number_i',
                'raw_file_name_s', 'receiver_table_n_i', 'response_table_n_i',
                'sample_count_i', 'sample_rate_i', 'sample_rate_multiplier_i',
                'stream_number_i', 'time/ascii_s', 'time/epoch_l',
                'time/micro_seconds_i', 'time/type_s', 'time_table_n_i']
        self.assertEqual(keys, das_keys)
        self.assertEqual(
            'ph5/test_data/miniseed/0407HHN.m',
            ret[0]['raw_file_name_s'])
        ph5_object.ph5close()
        os.remove('master.ph5')
        os.remove('miniPH5_00001.ph5')
        os.remove('metadatatoph5.log')
        os.remove('datatoph5.log')
        os.remove('test_list')

    def test_to_ph5(self):
        """
        test to_ph5
        """
        index_t_full = list()
        # try load without metadata
        entry = "ph5/test_data/miniseed/0407HHN.ms"
        message, index_t = self.obs.toph5((entry, 'MSEED'))
        self.assertFalse(index_t)
        self.assertEqual('stop', message)

        # with metadata
        metadata = metadatatoph5.MetadatatoPH5(
            self.obs.ph5)
        f = open(
            "ph5/test_data/metadata/station.xml", "r")
        inventory_ = metadata.read_metadata(
            f,
            "station.xml")
        f.close()
        parsed_array = metadata.parse_inventory(inventory_)
        metadata.toph5(parsed_array)
        self.obs.ph5.initgroup()
        message, index_t = self.obs.toph5((entry, 'MSEED'))
        self.assertTrue('done', message)
        self.assertTrue(1, len(index_t))
        for e in index_t:
            index_t_full.append(e)

        # now load LOG CH
        entry = "ph5/test_data/miniseed/0407LOG.ms"
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
        self.assertTrue(
            os.path.isfile("ph5/test_data/miniseedph5/master.ph5"))
        self.assertTrue(
            os.path.isfile("ph5/test_data/miniseedph5/miniPH5_00001.ph5"))

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
        self.assertEqual(
            'ph5/test_data/miniseed/0407HHN.m',
            ret[0]['raw_file_name_s'])
        self.assertEqual(
            'ph5/test_data/miniseed/0407LOG.m',
            ret[1]['raw_file_name_s'])

    def tearDown(self):
        """"""
        self.obs.ph5.ph5close()
        os.remove(os.path.join(self.path, 'master.ph5'))
        try:
            os.remove(os.path.join(self.path, 'miniPH5_00001.ph5'))
        except BaseException:
            pass
        os.removedirs(self.path)


if __name__ == "__main__":
    unittest.main()
