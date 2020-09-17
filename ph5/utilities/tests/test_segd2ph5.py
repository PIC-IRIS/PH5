'''
Tests for segd2ph5
'''
import os
import sys
import unittest
import logging

from mock import patch
from testfixtures import LogCapture, OutputCapture

from ph5.utilities import segd2ph5, tabletokef
from ph5.core import segdreader
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase,\
    initialize_ex, das_in_mini


def create_fcntlist_file(home, namestart=''):
    """
    create file that keep the path of fcnt file under 'ph5/test_data/segd'
    of which name start with parameter 'namestart'
    """
    segd_dir = os.path.join(home, 'ph5/test_data/segd/')
    # create list file
    list_file = open('fcnt_list', 'w')
    fileList = os.listdir(segd_dir)
    s = ""
    for f in fileList:
        if f.endswith('.fcnt') and f.startswith(namestart):
            s += segd_dir + f + "\n"
    list_file.write(s)
    list_file.close()


class TestSegDtoPH5_noclose(TempDirTestCase, LogTestCase):
    def tearDown(self):
        segd2ph5.MAX_PH5_BYTES = 1073741824 * 100.
        super(TestSegDtoPH5_noclose, self).tearDown()

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

    def test_getHighestMini(self):
        index_t_das_rows = [{'external_file_name_s': './miniPH5_00003.ph5'},
                            {'external_file_name_s': './miniPH5_00010.ph5'},
                            {'external_file_name_s': './miniPH5_00001.ph5'},
                            {'external_file_name_s': './miniPH5_00009.ph5'},
                            {'external_file_name_s': './miniPH5_00007.ph5'}]
        index_t_das = segd2ph5.Rows_Keys(index_t_das_rows)
        ret = segd2ph5.getHighestMini(index_t_das)
        self.assertEqual(ret, 10)

    def test_get_args(self):
        # error when -M and -F is used at the same time
        testargs = ['segdtoph5', '-n', 'master.ph5', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/3ch.fcnt'),
                    '-M', '5', '-F', '3']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                self.assertRaises(
                    SystemExit,
                    segd2ph5.get_args)

        # -M
        testargs = ['segdtoph5', '-n', 'master.ph5', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/3ch.fcnt'),
                    '-M', '5']
        with patch.object(sys, 'argv', testargs):
            segd2ph5.get_args()
        self.assertEqual(segd2ph5.NUM_MINI, 5)

        # -F
        testargs = ['segdtoph5', '-n', 'master.ph5', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/3ch.fcnt'),
                    '-F', '5']
        with patch.object(sys, 'argv', testargs):
            segd2ph5.get_args()
        self.assertEqual(segd2ph5.FROM_MINI, 5)

    def test_main_from_mini(self):
        """ test main() with -F option """
        create_fcntlist_file(self.home, '1111')
        # reset MAX_PH5_BYTES to allow MB for a mini file only
        # check 2 mini file is created start from FROM_MINI
        segd2ph5.MAX_PH5_BYTES = 1024 * 1024 * 1.5
        testargs = ['segdtoph5', '-n', 'master', '-f', 'fcnt_list', '-F', '3']
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        ph5set = {f for f in os.listdir(self.tmpdir) if f.endswith('.ph5')}
        self.assertEqual(ph5set,
                         {'miniPH5_00003.ph5', 'miniPH5_00004.ph5',
                          'master.ph5'})

        # FROM_MINI < highest mini
        testargs = ['segdtoph5', '-n', 'master.ph5', '-F', '3', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/3ch.fcnt')]
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                self.assertRaises(SystemExit, segd2ph5.main)
                self.assertEqual(
                    log.records[0].msg,
                    'FROM_MINI must be greater than or equal to 4, '
                    'the highest mini file in ph5.')

        testargs = ['segdtoph5', '-n', 'master.ph5', '-F', '6', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/3ch.fcnt')]
        # check mini file continue from FROM_MINI
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        ph5set = {f for f in os.listdir(self.tmpdir) if f.endswith('.ph5')}
        self.assertEqual(ph5set,
                         {'miniPH5_00003.ph5', 'miniPH5_00004.ph5',
                          'miniPH5_00006.ph5', 'master.ph5'})
        self.assertEqual(das_in_mini(self.tmpdir, 'miniPH5_00003.ph5'),
                         ['Das_g_1X1111'])
        self.assertEqual(das_in_mini(self.tmpdir, 'miniPH5_00004.ph5'),
                         ['Das_g_1X1111'])
        self.assertEqual(das_in_mini(self.tmpdir, 'miniPH5_00006.ph5'),
                         ['Das_g_3X500'])


class TestSegDtoPH5_closeEX(TempDirTestCase, LogTestCase):
    def tearDown(self):
        self.EX.ph5close()
        super(TestSegDtoPH5_closeEX, self).tearDown()

    def test_main_diff_deploy(self):
        # add fcnt data of the same das in the same array but with different
        # deploytime
        create_fcntlist_file(self.home, '1111')

        # add segD to ph5
        testargs = ['segdtoph5', '-n', 'master', '-f', 'fcnt_list']
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        # check that all deploy times are in array_t
        self.EX = tabletokef.EX = initialize_ex('master.ph5', '.', False)
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

    def test_write_arrays(self):
        self.EX = segd2ph5.EX = initialize_ex('master.ph5', '.', True)
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
        self.EX = segd2ph5.EX = initialize_ex('master.ph5', '.', True)

        segd2ph5.setLogger()
        segd2ph5.SD = SD = segdreader.Reader(
            infile=os.path.join(self.home, 'ph5/test_data/segd/3ch.fcnt'))
        SD.process_general_headers()
        SD.process_channel_set_descriptors()
        SD.process_extended_headers()
        SD.process_external_headers()

        SIZE = os.path.getsize(
            os.path.join(self.home, 'ph5/test_data/segd/3ch.fcnt'))
        # need to use relative path './miniPH5_00001.ph5' because
        # index_t's 'external_file_name_s will be chopped off if the path's
        # length is greater than 32
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
        segd2ph5.FROM_MINI = None
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

    def test_get_current_data_only(self):
        testargs = ['segdtoph5', '-n', 'master', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/1111.0.0.fcnt'),
                    '-F', '3']
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()
        segd2ph5.initializeExperiment()
        self.EX = segd2ph5.EX
        rows, keys = segd2ph5.EX.ph5_g_receivers.read_index()
        segd2ph5.INDEX_T_DAS = segd2ph5.Rows_Keys(rows, keys)
        segd2ph5.EXREC = segd2ph5.openPH5('miniPH5_00003.ph5')

        # FROM_MINI < miniPH5_00003.ph5
        # size of data + size of miniPH5_00003.ph5 < MAX_PH5_BYTES
        # => save to current mini: miniPH5_00003.ph5
        segd2ph5.FROM_MINI = 2
        segd2ph5.EXREC = segd2ph5.get_current_data_only(1083348, '3X500')
        self.assertEqual(segd2ph5.EXREC.filename, './miniPH5_00003.ph5')

        segd2ph5.MAX_PH5_BYTES = 1024 * 1024 * 2
        # FROM_MINI < miniPH5_00003.ph5 whose das is current das
        # size of data + size of miniPH5_00003.ph5 < MAX_PH5_BYTES
        # => save to current mini: miniPH5_00003.ph5
        segd2ph5.FROM_MINI = 2
        segd2ph5.EXREC = segd2ph5.get_current_data_only(1083348, '1X1111')
        self.assertEqual(segd2ph5.EXREC.filename, './miniPH5_00003.ph5')

        # FROM_MINI < miniPH5_00003.ph5
        # size of data + size of miniPH5_00003.ph5 > MAX_PH5_BYTES
        # => save to miniPH5_00004.ph5 (last+1)
        segd2ph5.FROM_MINI = 2
        segd2ph5.EXREC = segd2ph5.get_current_data_only(2183348, '1X1111')
        self.assertEqual(segd2ph5.EXREC.filename, './miniPH5_00004.ph5')

        # FROM_MINI > last mini file
        # => save to miniPH5_00005.ph5 (FROM_MINI)
        segd2ph5.FROM_MINI = 5
        segd2ph5.EXREC = segd2ph5.get_current_data_only(1083348, '1X1111')
        self.assertEqual(segd2ph5.EXREC.filename, './miniPH5_00005.ph5')


if __name__ == "__main__":
    unittest.main()
