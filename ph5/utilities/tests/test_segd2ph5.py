'''
Tests for segd2ph5
'''
import unittest
import sys
import os
import tables
from ph5.utilities import segd2ph5
from ph5.core import experiment, segdreader
from ph5.utilities.tests import assertTable

from mock import patch


class CONVERSION:
    def __init__(self, EX, miniFileName):
        self.EX = EX
        d = segd2ph5.Index_t_Info(
            '3X500', miniFileName,
            '/Experiment_g/Receivers_g/Das_g_3X500',
            1502294400.38, 1502294430.38)
        m = segd2ph5.Index_t_Info(
            '3X500', miniFileName,
            '/Experiment_g/Maps_g/Das_g_3X500',
            1502294400.38, 1502294430.38)
        self.DAS_INFO = {'3X500': [d]}
        self.MAP_INFO = {'3X500': [m]}


class TestSegdtoph5(unittest.TestCase):
    print "Test segd2ph5"

    def tearDown(self):
        try:
            self.EX.ph5close()
            del self.EX
            self.EXREC.ph5.close()
            del self.EXREC
        except Exception:
            pass
        filelist = os.listdir(".")
        for f in filelist:
            if f.endswith(".ph5") or f.endswith(".log") or f.endswith(".lst"):
                os.remove(f)

    def test_main(self):
        """
        test main
        """
        testargs = ['segdtoph5', '-n', 'master.ph5', '-T', 'True',
                    '-r', 'ph5/test_data/segd/3ch.fcnt']
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        assertTable(
            ['--all_arrays'], 'ph5/test_data/segd/metadata/all_arrays.kef',
            exclStrs=["receiver_table_n_i", "response_table_n_i"])
        assertTable(
            ['--Das_t', '3X500'],
            'ph5/test_data/segd/metadata/das_t_3X500.kef')
        assertTable(
            ['--Index_t'], 'ph5/test_data/segd/metadata/index_t.kef')
        assertTable(
            ['--M_Index_t'], 'ph5/test_data/segd/metadata/M_index_t.kef')

        # run list file with path to 2 segd files for the same das, same array
        # same chan_number, different deploy times, will uncomment when sample
        # files ready for testing
        """
        testargs = ['segdtoph5', '-n', 'master.ph5',
                    '-f', 'ph5/test_data/segd/rg16/RG16_list']
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()
        assertTable(
            ['--all_arrays'],
            'ph5/test_data/segd/rg16/metadata/all_arrays.kef',
            exclStrs=["receiver_table_n_i", "response_table_n_i"])
        # check das_t_9X9050
        assertTable(
            ['--Das_t', '9X9050'],
            'ph5/test_data/segd/rg16/metadata/das_t_9X9050.kef')
        # check index_t
        assertTable(
            ['--Index_t'],
            'ph5/test_data/segd/rg16/metadata/index_t.kef')
        # check M_index_t
        assertTable(
            ['--M_Index_t'],
            'ph5/test_data/segd/rg16/metadata/M_index_t.kef')
        """

    def test_write_arrays(self):
        arrays = \
            [{'das/serial_number_s': '3X500', 'channel_number_i': 1,
              'deploy_time/epoch_l': 1544545576},
             {'das/serial_number_s': '3X500', 'channel_number_i': 2,
              'deploy_time/epoch_l': 1502293592},
             {'das/serial_number_s': '3X500', 'channel_number_i': 1,
              'deploy_time/epoch_l': 1544545576},
             {'das/serial_number_s': '3X500', 'channel_number_i': 2,
              'deploy_time/epoch_l': 1502293592}]
        array_t = \
            {1: {'3X500': {1502293592: {1: [arrays[0]], 2: [arrays[1]]},
                           1546021724: {1: [arrays[2]], 2: [arrays[3]]}}}}
        self.EX = segd2ph5.initializeExperiment("master.ph5")
        segd2ph5.write_arrays(self.EX, array_t)
        ret = self.EX.ph5_g_sorts.ph5_t_array

        i = 0
        for r in ret.iterrows():
            for k in arrays[0].keys():
                self.assertEqual(r[k], arrays[i][k])
            i += 1

    def test_read_infile(self):
        os.system("ls -d ph5/test_data/segd/rg16/*.rg16 > rg16.lst")

        FILES = []
        segd2ph5.read_infile("rg16.lst", FILES)
        filelist = ['ph5/test_data/segd/rg16/PIC_9_9050_2875.0.0.rg16',
                    'ph5/test_data/segd/rg16/PIC_9_9050_2901.0.0.rg16']
        self.assertEqual(FILES, filelist)

    def test_txncsptolatlon(self):
        ret = segd2ph5.txncsptolatlon(5280709.7, 469565.2)
        self.assertEqual(ret[0], 45.93618912127325)
        self.assertEqual(ret[1], -103.35984617012576)

    def test_utmcsptolatlon(self):
        ret = segd2ph5.utmcsptolatlon(5280709.7, 469565.2, '13N')
        self.assertEqual(ret[0], 47.6790599341565)
        self.assertEqual(ret[1], -105.40548953916888)

        ret = segd2ph5.utmcsptolatlon(5280709.7, 469565.2, '13S')
        self.assertEqual(ret[0], -42.62545471188468)
        self.assertEqual(ret[1], -105.3711482818481)

    def test_writeINDEX(self):
        """
        test writeINDEX method
        """
        # prepare
        self.EX = segd2ph5.initializeExperiment("master.ph5")
        conv = CONVERSION(self.EX, './miniPH5_00001.ph5')

        # test writeINDEX()
        segd2ph5.writeINDEX(conv)
        index = {'end_time/type_s': 'BOTH',
                 'start_time/ascii_s': 'Wed Aug  9 16:00:00 2017',
                 'time_stamp/type_s': 'BOTH',
                 'start_time/micro_seconds_i': 380000,
                 'start_time/type_s': 'BOTH',
                 'end_time/micro_seconds_i': 380000,
                 'start_time/epoch_l': 1502294400,
                 'external_file_name_s': './miniPH5_00001.ph5',
                 'serial_number_s': '3X500',
                 'end_time/ascii_s': 'Wed Aug  9 16:00:30 2017',
                 'end_time/epoch_l': 1502294430,
                 'time_stamp/micro_seconds_i': 0}

        # check conv.INDEX_T_DAS
        index['hdf5_path_s'] = '/Experiment_g/Receivers_g/Das_g_3X500'
        self.assertEqual(15, len(conv.INDEX_T_DAS.keys))
        for r in conv.INDEX_T_DAS.rows:
            for k in index.keys():
                self.assertEqual(r[k], index[k])
        # check conv.INDEX_T_MAP
        index['hdf5_path_s'] = '/Experiment_g/Maps_g/Das_g_3X500'
        self.assertEqual(15, len(conv.INDEX_T_MAP.keys))
        for r in conv.INDEX_T_MAP.rows:
            for k in index.keys():
                self.assertEqual(r[k], index[k])

    def test_update_external_references(self):
        """
        test update_external_references method
        """
        # prepare
        self.EX = segd2ph5.initializeExperiment("master.ph5")
        conv = CONVERSION(self.EX, './miniPH5_00001.ph5')
        segd2ph5.writeINDEX(conv)

        # test update_external_references()
        segd2ph5.update_external_references(conv)

        # check updated ExternalLinks
        ret_link_das = conv.EX.ph5.get_node(
            "/Experiment_g/Receivers_g/Das_g_3X500")
        self.assertIsInstance(ret_link_das, tables.link.ExternalLink)
        self.assertEqual(
            ret_link_das.target,
            "miniPH5_00001.ph5:/Experiment_g/Receivers_g/Das_g_3X500")

        ret_link_map = conv.EX.ph5.get_node(
            "/Experiment_g/Maps_g/Das_g_3X500")
        self.assertIsInstance(ret_link_map, tables.link.ExternalLink)
        self.assertEqual(
            ret_link_map.target,
            "miniPH5_00001.ph5:/Experiment_g/Maps_g/Das_g_3X500")

    def test_get_current_data_only(self):
        """
        test get_current_data_only method
        """
        # prepare
        self.EX = segd2ph5.initializeExperiment("master.ph5")
        conv = CONVERSION(self.EX, './miniPH5_00001.ph5')
        segd2ph5.writeINDEX(conv)

        # test get_current_data_only()
        # ___________ has INDEX_T_DAS ___________
        # given das is the das in index_t
        self.EXREC = segd2ph5.get_current_data_only(conv, 362328, '3X500')
        self.assertIsInstance(self.EXREC, experiment.ExperimentGroup)
        self.assertEqual(self.EXREC.filename, './miniPH5_00001.ph5')
        self.EXREC.ph5close()

        # given das is NOT the das in index_t
        # num in file - (FIRST_MINI-1) < NUM_MINI
        conv.NUM_MINI = 2
        conv.FIRST_MINI = 1
        self.EXREC = segd2ph5.get_current_data_only(conv, 362328, '9X9050')
        self.assertIsInstance(self.EXREC, experiment.ExperimentGroup)
        self.assertEqual(self.EXREC.filename, './miniPH5_00002.ph5')
        self.EXREC.ph5.close()

        # num in file - (FIRST_MINI-1) >= NUM_MINI
        conv.NUM_MINI = 1
        self.EXREC = segd2ph5.get_current_data_only(conv, 362328, '9X9050')
        self.assertIsInstance(self.EXREC, experiment.ExperimentGroup)
        self.assertEqual(self.EXREC.filename, './miniPH5_00001.ph5')
        self.EXREC.ph5.close()

        # NUM_MIN = None
        # size_of_data + size_of_exrec <=MAX_PH5_BYTES (100GB)
        conv.NUM_MINI = None
        self.EXREC = segd2ph5.get_current_data_only(conv, 362328, '9X9050')
        self.assertIsInstance(self.EXREC, experiment.ExperimentGroup)
        self.assertEqual(self.EXREC.filename, './miniPH5_00001.ph5')
        self.EXREC.ph5.close()

        # size_of_data + size_of_exrec > MAX_PH5_BYTES (100GB)
        conv.NUM_MINI = None
        self.EXREC = segd2ph5.get_current_data_only(
            conv, segd2ph5.MAX_PH5_BYTES, '9X9050')
        self.assertIsInstance(self.EXREC, experiment.ExperimentGroup)
        self.assertEqual(self.EXREC.filename, './miniPH5_00002.ph5')
        self.EXREC.ph5.close()

        # ___________ has NO INDEX_T_DAS ___________
        conv.INDEX_T_DAS = segd2ph5.Rows_Keys((), ())
        self.EXREC = segd2ph5.get_current_data_only(conv, 362328, '3X500')
        self.assertIsInstance(self.EXREC, experiment.ExperimentGroup)
        self.assertEqual(self.EXREC.filename, './miniPH5_00001.ph5')
        self.EXREC.ph5.close()

    def test_process_traces(self):
        """
        test process_traces method
        """
        # prepare SD
        SD = segdreader.Reader(infile='ph5/test_data/segd/3ch.fcnt')
        SD.process_general_headers()
        SD.process_channel_set_descriptors()
        SD.process_extended_headers()
        SD.process_external_headers()

        SIZE = os.path.getsize('ph5/test_data/segd/3ch.fcnt')

        # prepare conv
        self.EX = segd2ph5.initializeExperiment("master.ph5")
        conv = CONVERSION(self.EX, './miniPH5_00001.ph5')
        conv.SD = SD
        conv.Das = '3X500'
        conv.ARRAY_T = {}
        conv.TSPF = False
        conv.UTM = 0
        conv.LON = None
        conv.LAT = None
        conv.RH = False
        segd2ph5.writeINDEX(conv)
        conv.RESP = segd2ph5.Resp(conv.EX.ph5_g_responses)
        conv.EXREC = segd2ph5.get_current_data_only(conv, SIZE, conv.Das)
        conv.TRACE_JSON = []

        # prepare trace
        trace, cs = SD.process_trace()
        T = segd2ph5.Trace(trace, SD.trace_headers)

        # ___________test process_traces ____________________
        segd2ph5.process_traces(conv, SD.reel_headers, T.headers, T.trace)

        # check ARRAY_T
        array_line = conv.ARRAY_T.keys()[0]
        self.assertEqual(array_line, 1)

        das = conv.ARRAY_T[array_line].keys()[0]
        self.assertEqual(das, '3X500')

        deploy_time = conv.ARRAY_T[array_line][das].keys()[0]
        self.assertEqual(deploy_time, 1502293592)

        chan = conv.ARRAY_T[array_line][das][deploy_time].keys()[0]
        self.assertEqual(chan, 1)

        # DAS_INFO
        self.assertEqual(conv.DAS_INFO.keys()[0], '3X500')
        das_info = conv.DAS_INFO['3X500'][0]
        self.assertEqual(das_info.ph5file, './miniPH5_00001.ph5')
        self.assertEqual(das_info.ph5path,
                         "/Experiment_g/Receivers_g/Das_g_3X500")
        self.assertEqual(das_info.startepoch,  1502294400.38)
        self.assertEqual(das_info.stopepoch,  1502294430.38)
        self.assertEqual(das_info.das, '3X500')

        # MAP_INFO
        self.assertEqual(conv.MAP_INFO.keys()[0], '3X500')
        map_info = conv.MAP_INFO['3X500'][0]
        self.assertEqual(map_info.ph5file, './miniPH5_00001.ph5')
        self.assertEqual(map_info.ph5path,
                         "/Experiment_g/Maps_g/Das_g_3X500")
        self.assertEqual(map_info.startepoch,  1502294400.38)
        self.assertEqual(map_info.stopepoch,  1502294430.38)
        self.assertEqual(map_info.das, '3X500')

        # RESP
        R_KEYS = ['n_i', 'bit_weight/value_d', 'bit_weight/units_s',
                  'gain/units_s', 'gain/value_i', 'response_file_a',
                  'response_file_das_a', 'response_file_sensor_a']
        LINE = {'gain/value_i': 24, 'response_file_das_a': '',
                'bit_weight/units_s': 'mV/count',
                'bit_weight/value_d': 1.8596649169921875e-05,
                'gain/units_s': 'dB', 'response_file_a': '',
                'response_file_sensor_a': '', 'n_i': 0}
        self.assertEqual(conv.RESP.keys, R_KEYS)
        self.assertEqual(len(conv.RESP.lines), 1)
        for k in R_KEYS:
            self.assertEqual(conv.RESP.lines[0][k], LINE[k])


if __name__ == "__main__":
    unittest.main()
