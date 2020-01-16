'''
Tests for segd2ph5
'''
import unittest
import os
import sys
import shutil
import tempfile
from mock import patch
from ph5 import logger, ch as CH
from ph5.utilities import segd2ph5, tabletokef
from ph5.core import segdreader
from ph5.core.tests.base_test import log_capture_string, initialize_ph5


class TestSegDtoPH5(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.log_capture_string = log_capture_string()

    def setUp(self):
        # create tmpdir
        self.home = os.getcwd()
        self.tmpdir = tempfile.mkdtemp() + "/"
        os.chdir(self.tmpdir)

        # initiate ph5
        self.EX = segd2ph5.EX = initialize_ph5("master.ph5", editmode=True)

    def tearDown(self):
        try:
            self.EX.ph5close()
            segd2ph5.EXREC.ph5close()
        except Exception:
            pass
        if self._resultForDoCleanups.wasSuccessful():
            try:
                shutil.rmtree(self.tmpdir)
            except Exception as e:
                print("Cannot remove %s due to the error:%s" %
                      (self.tmpdir, str(e)))
        else:
            errmsg = "%s has FAILED. Inspect files created in %s." \
                % (self._testMethodName, self.tmpdir)
            print(errmsg)
        os.chdir(self.home)

    def test_bit_weights(self):
        # From old
        LSB00 = 2500. / (2 ** 23)  # 0dB
        LSB12 = 625. / (2 ** 23)  # 12dB
        LSB24 = 156. / (2 ** 23)  # 24dB
        LSB36 = 39. / (2 ** 23)  # 36dB = 39mV full scale
        self.assertAlmostEqual(LSB00, segd2ph5.LSB_MAP[0])
        self.assertAlmostEqual(LSB12, segd2ph5.LSB_MAP[12], places=6)
        self.assertAlmostEqual(LSB24, segd2ph5.LSB_MAP[24], places=6)
        self.assertAlmostEqual(LSB36, segd2ph5.LSB_MAP[36], places=6)

    def test_write_arrays(self):
        # same das, different deploy times
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

        segd2ph5.write_arrays(array_t)
        ret = segd2ph5.EX.ph5_g_sorts.ph5_t_array

        i = 0
        for r in ret.iterrows():
            for k in arrays[0].keys():
                self.assertEqual(r[k], arrays[i][k])
            i += 1

    def test_process_traces(self):
        """
        test process_traces method
        """
        segd2ph5.setLogger()
        segd2ph5.SD = SD = segdreader.Reader(
            infile=self.home + '/ph5/test_data/segd/3ch.fcnt')
        SD.process_general_headers()
        SD.process_channel_set_descriptors()
        SD.process_extended_headers()
        SD.process_external_headers()

        SIZE = os.path.getsize(self.home + '/ph5/test_data/segd/3ch.fcnt')

        segd2ph5.DAS_INFO = {'3X500': [segd2ph5.Index_t_Info(
            '3X500', './miniPH5_00001.ph5',
            '/Experiment_g/Receivers_g/Das_g_3X500',
            1502294400.38, 1502294430.38)]}
        segd2ph5.MAP_INFO = {'3X500': [segd2ph5.Index_t_Info(
            '3X500', './miniPH5_00001.ph5',
            '/Experiment_g/Maps_g/Das_g_3X500',
            1502294400.38, 1502294430.38)]}

        segd2ph5.Das = '3X500'
        segd2ph5.ARRAY_T = {}
        segd2ph5.TSPF = False
        segd2ph5.UTM = 0
        segd2ph5.LON = None
        segd2ph5.LAT = None
        segd2ph5.RH = False
        segd2ph5.writeINDEX()
        segd2ph5.RESP = segd2ph5.Resp(segd2ph5.EX.ph5_g_responses)
        segd2ph5.EXREC = segd2ph5.get_current_data_only(SIZE, segd2ph5.Das)
        segd2ph5.TRACE_JSON = []

        # prepare trace
        trace, cs = SD.process_trace()
        T = segd2ph5.Trace(trace, SD.trace_headers)

        # ___________test process_traces ____________________
        segd2ph5.process_traces(SD.reel_headers, T.headers, T.trace)

        # check ARRAY_T [array][das][deploy_time][chan]
        array_line = segd2ph5.ARRAY_T.keys()[0]
        self.assertEqual(array_line, 1)

        das = segd2ph5.ARRAY_T[array_line].keys()[0]
        self.assertEqual(das, '3X500')

        deploy_time = segd2ph5.ARRAY_T[array_line][das].keys()[0]
        self.assertEqual(deploy_time, 1502293592)

        chan = segd2ph5.ARRAY_T[array_line][das][deploy_time].keys()[0]
        self.assertEqual(chan, 1)

        # DAS_INFO
        self.assertEqual(segd2ph5.DAS_INFO.keys()[0], '3X500')
        das_info = segd2ph5.DAS_INFO['3X500'][0]
        self.assertEqual(das_info.ph5file, './miniPH5_00001.ph5')
        self.assertEqual(das_info.ph5path,
                         "/Experiment_g/Receivers_g/Das_g_3X500")
        self.assertEqual(das_info.startepoch,  1502294400.38)
        self.assertEqual(das_info.stopepoch,  1502294430.38)
        self.assertEqual(das_info.das, '3X500')

        # MAP_INFO
        self.assertEqual(segd2ph5.MAP_INFO.keys()[0], '3X500')
        map_info = segd2ph5.MAP_INFO['3X500'][0]
        self.assertEqual(map_info.ph5file, './miniPH5_00001.ph5')
        self.assertEqual(map_info.ph5path,
                         "/Experiment_g/Maps_g/Das_g_3X500")
        self.assertEqual(map_info.startepoch,  1502294400.38)
        self.assertEqual(map_info.stopepoch,  1502294430.38)
        self.assertEqual(map_info.das, '3X500')

        # RESP
        response = {'gain/value_i': 24,
                    'response_file_das_a': '',
                    'bit_weight/units_s': 'mV/count',
                    'bit_weight/value_d': 1.880399419308285e-05,
                    'gain/units_s': 'dB', 'response_file_a': '',
                    'response_file_sensor_a': '',
                    'n_i': 0}
        self.assertEqual(sorted(segd2ph5.RESP.keys), sorted(response.keys()))
        self.assertEqual(len(segd2ph5.RESP.lines), 1)
        for k in response.keys():
            if isinstance(segd2ph5.RESP.lines[0][k], float):
                self.assertAlmostEqual(segd2ph5.RESP.lines[0][k], response[k],
                                       places=5)
            else:
                self.assertEqual(segd2ph5.RESP.lines[0][k], response[k])

    def test_main(self):
        """
        test main function
        """
        # close EX before test main
        try:
            segd2ph5.EX.ph5close()
        except Exception:
            pass
        ####################################################################
        # add fcnt data of the same das in the same array but with different
        # deploytime
        segd_dir = self.home + "/ph5/test_data/segd/"
        # create list file
        list_file = open('fcnt_list', "w")
        fileList = os.listdir(segd_dir)
        s = ""
        for f in fileList:
            if f.endswith(".fcnt") and f.startswith("1111"):
                s += segd_dir + f + "\n"
        list_file.write(s)
        list_file.close()

        # add segD to ph5
        testargs = ['segdtoph5', '-n', 'master', '-f', 'fcnt_list']
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        # check that all deploy times are in array_t
        self.EX = tabletokef.EX = initialize_ph5("master.ph5", editmode=False)
        tabletokef.ARRAY_T = {}
        tabletokef.read_sort_table()
        tabletokef.read_sort_arrays()
        self.assertEqual(len(tabletokef.ARRAY_T), 1)
        self.assertEqual(tabletokef.ARRAY_T.keys()[0], "Array_t_001")
        self.assertEqual(len(tabletokef.ARRAY_T['Array_t_001'].rows), 9)
        # id_s 1111 SHOULD have 3 different times,
        # each has 3 rows for 3 channels
        time_count = {}
        for s in tabletokef.ARRAY_T['Array_t_001'].rows:
            if s['id_s'] == '1111':
                d = s['deploy_time/epoch_l']
                if d not in time_count.keys():
                    time_count[d] = 0
                time_count[d] += 1

        self.assertDictEqual(time_count,
                             {1561831393: 3, 1563634018: 3, 1567269236: 3})

        ####################################################################


if __name__ == "__main__":
    unittest.main()
