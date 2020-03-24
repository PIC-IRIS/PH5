'''
Tests for metadatatoph5
'''
import os
import sys
import unittest

from obspy.core import inventory
from obspy import UTCDateTime
from mock import patch
from testfixtures import OutputCapture

from ph5.utilities import metadatatoph5
from ph5.core.tests.test_base import TempDirTestCase, initialize_ex


class TestMetadatatoPH5(TempDirTestCase):
    def setUp(self):
        self.LOGGERs = [metadatatoph5.LOGGER]
        super(TestMetadatatoPH5, self).setUp()
        if self._testMethodName != 'test_main':
            # not apply for test_main()
            self.ph5_object = initialize_ex('master.ph5', self.tmpdir, True)
            self.metadata = metadatatoph5.MetadatatoPH5(
                self.ph5_object)

    def tearDown(self):
        if self._testMethodName != 'test_main':
            self.ph5_object.ph5close()
        super(TestMetadatatoPH5, self).tearDown()

    def test_get_args(self):
        """
        test get_args
        """
        with OutputCapture():
            with self.assertRaises(SystemExit):
                metadatatoph5.get_args([])
            with self.assertRaises(SystemExit):
                metadatatoph5.get_args(['-n', 'master.ph5'])
            with self.assertRaises(SystemExit):
                metadatatoph5.get_args(['-f', 'test.xml'])
            ret = metadatatoph5.get_args(
                ['-n', 'master.ph5', '-f', 'test.xml'])
        self.assertEqual(ret.nickname, 'master.ph5')
        self.assertEqual(ret.infile, 'test.xml')
        self.assertEqual(ret.ph5path, '.')

    def test_main(self):
        """
        test main function
        """
        testargs = ['metadatatoph5', '-n', 'master.ph5', '-f',
                    '../metadata/station.xml']
        with patch.object(sys, 'argv', testargs):
            metadatatoph5.main()
        self.assertTrue(os.path.isfile('master.ph5'))
        # create ph5_object to check the result after run main()
        ph5_object = initialize_ex('master.ph5', '.', False)
        array_names = ph5_object.ph5_g_sorts.names()
        self.assertEqual(
            ['Array_t_001', 'Array_t_002', 'Array_t_003'], array_names)
        ret, keys = ph5_object.ph5_g_sorts.read_arrays('Array_t_001')
        key = ['id_s', 'location/X/value_d', 'location/X/units_s',
               'location/Y/value_d', 'location/Y/units_s',
               'location/Z/value_d', 'location/Z/units_s',
               'location/coordinate_system_s', 'location/projection_s',
               'location/ellipsoid_s', 'location/description_s',
               'deploy_time/ascii_s', 'deploy_time/epoch_l',
               'deploy_time/micro_seconds_i', 'deploy_time/type_s',
               'pickup_time/ascii_s', 'pickup_time/epoch_l',
               'pickup_time/micro_seconds_i', 'pickup_time/type_s',
               'das/serial_number_s', 'das/model_s', 'das/manufacturer_s',
               'das/notes_s', 'sensor/serial_number_s', 'sensor/model_s',
               'sensor/manufacturer_s', 'sensor/notes_s', 'description_s',
               'seed_band_code_s', 'sample_rate_i',
               'sample_rate_multiplier_i',
               'seed_instrument_code_s', 'seed_orientation_code_s',
               'seed_location_code_s', 'seed_station_name_s',
               'channel_number_i', 'receiver_table_n_i', 'response_table_n_i']
        self.assertEqual(key, keys)
        self.assertEqual(1, len(ret))
        self.assertEqual('5553', ret[0]['das/serial_number_s'])
        self.assertEqual('H', ret[0]['seed_instrument_code_s'])
        self.assertEqual('H', ret[0]['seed_band_code_s'])
        self.assertEqual('N', ret[0]['seed_orientation_code_s'])
        ph5_object.ph5close()

    def test_init(self):
        """
        test creating metadatatoph5 instance
        """
        self.assertTrue(self.metadata)
        self.assertTrue(isinstance(self.metadata,
                                   metadatatoph5.MetadatatoPH5))

    def test_read_metadata(self):
        """
        tests read_metadata method
        """
        # open file to pass handle
        f = open("../metadata/station.xml", "r")

        # should be a stationxml file, valid
        inventory_ = self.metadata.read_metadata(
            f,
            "station.xml")
        f.close()
        self.assertTrue(inventory_)
        self.assertTrue(isinstance(inventory_,
                                   inventory.Inventory))
        # check that it contains what we think it should
        self.assertEqual(2, len(inventory_[0].stations))
        self.assertEqual('0407',
                         inventory_[0].stations[0].code)
        self.assertEqual(2,
                         len(inventory_[0].stations[0].channels))
        self.assertEqual('LHN',
                         inventory_[0].stations[0].channels[1].code)

        # open file to pass handle
        f = open("../metadata/1B.13.AAA.2018123.dataless", "r")

        # should be a dataless SEED file, valid
        inventory_ = self.metadata.read_metadata(
            f,
            "1B.13.AAA.2018123.dataless")
        f.close()
        # check that it contains what we think it should
        self.assertEqual(4, len(inventory_[0].stations))
        self.assertEqual('HOL2B',
                         inventory_[0].stations[0].code)
        self.assertEqual(7,
                         len(inventory_[0].stations[0].channels))
        self.assertEqual('CH2',
                         inventory_[0].stations[0].channels[1].code)

        # open file to pass handle
        f = open("../metadata/station.txt", "r")

        # should be a station TXT, valid
        inventory_ = self.metadata.read_metadata(
            f,
            "station.txt")
        f.close()
        # check that it contains what we think it should
        self.assertEqual(397, len(inventory_[0].stations))
        self.assertEqual('1005',
                         inventory_[0].stations[4].code)
        self.assertEqual(3,
                         len(inventory_[0].stations[4].channels))
        self.assertEqual('DP1',
                         inventory_[0].stations[4].channels[0].code)

        # open file to pass handle
        f = open("../metadata/array_9_rt125a.kef", "r")
        # should be a KEF, valid
        inventory_ = self.metadata.read_metadata(
            f,
            "array_9_rt125a.kef")
        f.close()
        # check that it contains what we think it should
        self.assertFalse(inventory_)

        # open file to pass handle
        f = open("../metadata/array_8_130.csv", "r")
        # should be a CSV, valid
        inventory_ = self.metadata.read_metadata(
            f,
            "array_8_130.csv")
        f.close()
        # check that it contains what we think it should
        self.assertTrue(inventory_)

        # unknown file type
        f = open("../metadata/RESP/125a500_32_RESP", "r")
        # should be a KEF, valid
        inventory_ = self.metadata.read_metadata(
            f,
            "125a500_32_RESP")
        f.close()
        # check that it contains what we think it should
        self.assertFalse(inventory_)

        # try a closed file handle
        inventory_ = self.metadata.read_metadata(
            f,
            "125a500_32_RESP")
        self.assertFalse(inventory_)

    def test_parse_inventory(self):
        """
        test parsing inventory
        """
        # valid station xml
        # open file to pass handle
        f = open("../metadata/station.xml", "r")

        # should be a station TXT, valid
        inventory_ = self.metadata.read_metadata(
            f,
            "station.xml")
        f.close()
        parsed_array = self.metadata.parse_inventory(inventory_)
        # expect an array kef with 3 channels HHN, LHN, LOG
        self.assertTrue(parsed_array)
        self.assertEqual(3, len(parsed_array))
        self.assertEqual('5553', parsed_array[0]['das/serial_number_s'])
        self.assertEqual('5553', parsed_array[1]['das/serial_number_s'])
        self.assertEqual('5553', parsed_array[2]['das/serial_number_s'])
        self.assertEqual('H', parsed_array[0]['seed_band_code_s'])
        self.assertEqual('L', parsed_array[1]['seed_band_code_s'])
        self.assertEqual('L', parsed_array[2]['seed_band_code_s'])
        self.assertEqual('H', parsed_array[0]['seed_instrument_code_s'])
        self.assertEqual('H', parsed_array[1]['seed_instrument_code_s'])
        self.assertEqual('O', parsed_array[2]['seed_instrument_code_s'])
        self.assertEqual('N', parsed_array[0]['seed_orientation_code_s'])
        self.assertEqual('N', parsed_array[1]['seed_orientation_code_s'])
        self.assertEqual('G', parsed_array[2]['seed_orientation_code_s'])

        # check response manager for loaded responses
        sensor_keys = [parsed_array[0]['sensor/manufacturer_s'],
                       parsed_array[0]['sensor/model_s']]
        datalogger_keys = [parsed_array[0]['das/manufacturer_s'],
                           parsed_array[0]['das/model_s'],
                           parsed_array[0]['sample_rate_i']]
        self.assertTrue(
            self.metadata.resp_manager.is_already_requested(
                sensor_keys,
                datalogger_keys))

        # create empty inventory
        net = [inventory.Network('XX')]
        created = UTCDateTime.now()
        inventory_ = inventory.Inventory(
            networks=net, source="",
            sender="", created=created,
            module="", module_uri="")
        # should return empty list for parsed_array
        parsed_array = self.metadata.parse_inventory(inventory_)
        self.assertFalse(parsed_array)

        # test dataless seed
        # should be a dataless SEED file, valid
        f = open("../metadata/1B.13.AAA.2018123.dataless", "r")
        inventory_ = self.metadata.read_metadata(
            f,
            "1B.13.AAA.2018123.dataless")
        f.close()
        parsed_array = self.metadata.parse_inventory(inventory_)
        self.assertTrue(parsed_array)
        self.assertTrue(19, len(parsed_array))

        # dataless doesn't have datalogger serial numbers
        self.assertEqual("", parsed_array[0]['das/serial_number_s'])
        self.assertEqual("", parsed_array[9]['das/serial_number_s'])
        self.assertEqual("", parsed_array[17]['das/serial_number_s'])
        # check response manager for loaded responses
        sensor_keys = [parsed_array[0]['sensor/manufacturer_s'],
                       parsed_array[0]['sensor/model_s']]
        datalogger_keys = [parsed_array[0]['das/manufacturer_s'],
                           parsed_array[0]['das/model_s'],
                           parsed_array[0]['sample_rate_i']]
        self.assertFalse(
            self.metadata.resp_manager.is_already_requested(
                sensor_keys,
                datalogger_keys))

    def test_to_ph5(self):
        """
        test to_ph5 method
        """
        f = open("../metadata/station.xml", "r")
        inventory_ = self.metadata.read_metadata(
            f,
            "station.xml")
        f.close()
        parsed_array = self.metadata.parse_inventory(inventory_)
        # return true if successful
        self.assertTrue(self.metadata.toph5(parsed_array))
        self.metadata.ph5.initgroup()
        array_names = self.metadata.ph5.ph5_g_sorts.names()
        self.assertEqual(
            ['Array_t_001', 'Array_t_002', 'Array_t_003'], array_names)
        ret, keys = self.metadata.ph5.ph5_g_sorts.read_arrays('Array_t_001')
        key = ['id_s', 'location/X/value_d', 'location/X/units_s',
               'location/Y/value_d', 'location/Y/units_s',
               'location/Z/value_d', 'location/Z/units_s',
               'location/coordinate_system_s', 'location/projection_s',
               'location/ellipsoid_s', 'location/description_s',
               'deploy_time/ascii_s', 'deploy_time/epoch_l',
               'deploy_time/micro_seconds_i', 'deploy_time/type_s',
               'pickup_time/ascii_s', 'pickup_time/epoch_l',
               'pickup_time/micro_seconds_i', 'pickup_time/type_s',
               'das/serial_number_s', 'das/model_s', 'das/manufacturer_s',
               'das/notes_s', 'sensor/serial_number_s', 'sensor/model_s',
               'sensor/manufacturer_s', 'sensor/notes_s', 'description_s',
               'seed_band_code_s', 'sample_rate_i',
               'sample_rate_multiplier_i',
               'seed_instrument_code_s', 'seed_orientation_code_s',
               'seed_location_code_s', 'seed_station_name_s',
               'channel_number_i', 'receiver_table_n_i', 'response_table_n_i']
        self.assertEqual(key, keys)
        self.assertEqual(1, len(ret))
        self.assertEqual('5553', ret[0]['das/serial_number_s'])
        self.assertEqual('H', ret[0]['seed_instrument_code_s'])
        self.assertEqual('H', ret[0]['seed_band_code_s'])
        self.assertEqual('N', ret[0]['seed_orientation_code_s'])


if __name__ == "__main__":
    unittest.main()
