'''
Tests for segd2ph5
'''
import os
import sys
import unittest
import logging
import operator

from mock import patch
from testfixtures import LogCapture, OutputCapture

from ph5.utilities import segd2ph5, tabletokef, initialize_ph5
from ph5.core import segdreader, segdreader_smartsolo, ph5api, experiment
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase,\
    initialize_ex


class TestSegDtoPH5_main(TempDirTestCase, LogTestCase):
    def tearDown(self):
        self.EX.ph5close()
        super(TestSegDtoPH5_main, self).tearDown()

    def test_main(self):
        # add fcnt data of the same das in the same array but with different
        # deploytime
        segd_dir = os.path.join(self.home, "ph5/test_data/segd/fairfield/")
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


class TestSegDtoPH5(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestSegDtoPH5, self).setUp()
        # initiate ph5
        self.EX = segd2ph5.EX = initialize_ex('master.ph5', '.', True)

    def tearDown(self):
        self.EX.ph5close()
        try:
            segd2ph5.EXREC.ph5close()
        except AttributeError:
            pass
        # Clear global variables
        segd2ph5.EX = None
        segd2ph5.DAS_INFO = {}
        segd2ph5.MAP_INFO = {}
        segd2ph5.ARRAY_T = {}
        super(TestSegDtoPH5, self).tearDown()

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

    def test_write_arrays_Smartsolo(self):
        # the entries with overlaps or no gaps will be combined into one entry
        array_c1 = [
            {'das/serial_number_s': '1X2060', 'id_s': '2060',
             'channel_number_i': 1,
             'deploy_time/ascii_s': "Mon Sep 28 20:39:24 2020",
             'deploy_time/epoch_l': 1601325564,
             'pickup_time/ascii_s': 'Tue Sep 29 16:39:24 2020',
             'pickup_time/epoch_l': 1601397564,
             'pickup_time/micro_seconds_i': 0},
            # overlap => combine with previous
            {'das/serial_number_s': '1X2060', 'id_s': '2060',
             'channel_number_i': 1,
             'deploy_time/ascii_s': "Tue Sep 29 16:23:45 2020",
             'deploy_time/epoch_l': 1601396625,
             'pickup_time/ascii_s': 'Wed Sep 30 16:23:45 2020',
             'pickup_time/epoch_l': 1601483025,
             'pickup_time/micro_seconds_i': 0},
            # gap=150s: separate with previous
            {'das/serial_number_s': '1X2060', 'id_s': '2060',
             'channel_number_i': 1,
             'deploy_time/ascii_s': "Wed Sep 30 16:26:15 2020",
             'deploy_time/epoch_l': 1601483175,
             'pickup_time/ascii_s': 'Thu Oct 1 16:23:45 2020',
             'pickup_time/epoch_l': 1601569425,
             'pickup_time/micro_seconds_i': 0},
            {'das/serial_number_s': '1X2060', 'id_s': '2060',
             'channel_number_i': 1,
             'deploy_time/ascii_s': "Thu Oct 1 16:23:45 2020",
             'deploy_time/epoch_l': 1601569425,
             'pickup_time/ascii_s': 'Fri Oct 2 16:21:15 2020',
             'pickup_time/epoch_l': 1601655675,
             'pickup_time/micro_seconds_i': 0}
        ]
        array_c2 = [
            {'das/serial_number_s': '1X2060', 'id_s': '2060',
             'channel_number_i': 2,
             'deploy_time/ascii_s': "Mon Sep 28 20:39:24 2020",
             'deploy_time/epoch_l': 1601325564,
             'pickup_time/ascii_s': 'Tue Sep 29 16:39:24 2020',
             'pickup_time/epoch_l': 1601397564,
             'pickup_time/micro_seconds_i': 1},
            # overlap => combine with previous
            {'das/serial_number_s': '1X2060', 'id_s': '2060',
             'channel_number_i': 2,
             'deploy_time/ascii_s': "Tue Sep 29 16:23:45 2020",
             'deploy_time/epoch_l': 1601396625,
             'pickup_time/ascii_s': 'Wed Sep 30 16:23:45 2020',
             'pickup_time/epoch_l': 1601483025,
             'pickup_time/micro_seconds_i': 2}]

        array_t = \
            {1: {'1X2060': {1601325564: {1: [array_c1[0]], 2: [array_c2[0]]},
                            1601396625: {1: [array_c1[1]], 2: [array_c2[1]]},
                            1601483175: {1: [array_c1[2]]},
                            1601569425: {1: [array_c1[3]]}}}}
        logs = ['Das 1X2060 - Array_t_001 - station 2060 - chan 1: Combine '
                'overlapping entry '
                '[Tue Sep 29 16:23:45 2020 - Wed Sep 30 16:23:45 2020] '
                'into previous entry '
                '[Mon Sep 28 20:39:24 2020 - Tue Sep 29 16:39:24 2020]',
                'Das 1X2060 - Array_t_001 - station 2060 - chan 1: Combine '
                'entry [Thu Oct 1 16:23:45 2020 - Fri Oct 2 16:21:15 2020] '
                'into previous entry '
                '[Wed Sep 30 16:26:15 2020 - Thu Oct 1 16:23:45 2020]',
                'Das 1X2060 - Array_t_001 - station 2060 - chan 2: Combine '
                'overlapping entry '
                '[Tue Sep 29 16:23:45 2020 - Wed Sep 30 16:23:45 2020] '
                'into previous entry '
                '[Mon Sep 28 20:39:24 2020 - Tue Sep 29 16:39:24 2020]']
        SD = segdreader_smartsolo.Reader(
            infile=os.path.join(self.home,
                                "ph5/test_data/segd/smartsolo/453005483.1."
                                "2021.03.15.16.00.00.000.E.segd"))
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            segd2ph5.write_arrays(SD, array_t)
            for i in range(len(log.records)):
                self.assertEqual(log.records[i].msg, logs[i])

        ret = segd2ph5.EX.ph5_g_sorts.ph5_t_array['Array_t_001']
        self.assertEqual(len(ret), 3)   # 2 entries for chan1, 1 for chan2

        # combine array_c1[0] and overlapping array_c1[1]
        self.assertEqual(ret[0]['deploy_time']['epoch_l'],
                         array_c1[0]['deploy_time/epoch_l'])
        self.assertEqual(ret[0]['pickup_time']['epoch_l'],
                         array_c1[1]['pickup_time/epoch_l'])
        self.assertEqual(ret[0]['pickup_time']['ascii_s'],
                         array_c1[1]['pickup_time/ascii_s'])
        self.assertEqual(ret[0]['pickup_time']['micro_seconds_i'],
                         array_c1[1]['pickup_time/micro_seconds_i'])
        self.assertEqual(ret[0]['deploy_time']['epoch_l'],
                         array_c1[0]['deploy_time/epoch_l'])

        # combine array_c2[0] and overlapping array_c2[1]
        self.assertEqual(ret[1]['deploy_time']['epoch_l'],
                         array_c1[0]['deploy_time/epoch_l'])
        self.assertEqual(ret[1]['pickup_time']['epoch_l'],
                         array_c2[1]['pickup_time/epoch_l'])
        self.assertEqual(ret[1]['pickup_time']['ascii_s'],
                         array_c2[1]['pickup_time/ascii_s'])
        self.assertEqual(ret[1]['pickup_time']['micro_seconds_i'],
                         array_c2[1]['pickup_time/micro_seconds_i'])

        # combine array_c1[2] and deploy_time match pickup_time array_c1[3]
        self.assertEqual(ret[2]['deploy_time']['epoch_l'],
                         array_c1[2]['deploy_time/epoch_l'])
        self.assertEqual(ret[2]['pickup_time']['epoch_l'],
                         array_c1[3]['pickup_time/epoch_l'])
        self.assertEqual(ret[2]['pickup_time']['ascii_s'],
                         array_c1[3]['pickup_time/ascii_s'])
        self.assertEqual(ret[2]['pickup_time']['micro_seconds_i'],
                         array_c1[3]['pickup_time/micro_seconds_i'])

    def test_write_arrays_Fairfield(self):
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
        SD = segdreader.Reader(
            infile=os.path.join(self.home,
                                'ph5/test_data/segd/fairfield/3ch.fcnt'))
        segd2ph5.write_arrays(SD, array_t)
        ret = segd2ph5.EX.ph5_g_sorts.ph5_t_array['Array_t_001']

        i = 0
        for r in ret.iterrows():
            for k in arrays[0].keys():
                self.assertEqual(r[k], arrays[i][k])
            i += 1

    def test_process_traces_Fairfield(self):
        segd2ph5.setLogger()
        segd2ph5.SD = SD = segdreader.Reader(
            infile=os.path.join(self.home,
                                'ph5/test_data/segd/fairfield/3ch.fcnt'))
        SD.process_general_headers()
        SD.process_channel_set_descriptors()
        SD.process_extended_headers()
        SD.process_external_headers()

        SIZE = os.path.getsize(
            os.path.join(self.home, 'ph5/test_data/segd/fairfield/3ch.fcnt'))
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
        trace, cs = SD.process_trace(0)
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


class TestSegDtoPH5_SmartSolo(TempDirTestCase, LogTestCase):
    def tearDown(self):
        self.ph5object.ph5close()
        super(TestSegDtoPH5_SmartSolo, self).tearDown()

    def test_main(self):
        sspath = os.path.join(
            self.home, ("ph5/test_data/segd/smartsolo/453005513.2.2021.05.08."
                        "20.06.00.000.E.segd"))

        # add segD to ph5
        testargs = ['segdtoph5', '-n', 'master.ph5', '-r', sspath, '-U', '5N']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.WARNING)
                segd2ph5.main()

        self.ph5object = ph5api.PH5(path='.', nickname='master.ph5')
        # check array_t
        self.ph5object.read_array_t_names()
        self.assertEqual(self.ph5object.Array_t_names, ['Array_t_001'])
        self.ph5object.read_array_t('Array_t_001')
        a = self.ph5object.Array_t['Array_t_001']['byid']['1'][2][0]
        self.assertEqual(a['location/Y/value_d'], 19.42083740234375)
        self.assertEqual(a['location/X/value_d'], -155.2911834716797)
        self.assertEqual(a['das/manufacturer_s'], 'SmartSolo')
        self.assertEqual(a['das/serial_number_s'], '1X1')
        self.assertEqual(a['sensor/model_s'], 'GS-30CT')
        self.assertEqual(a['deploy_time/epoch_l'], 1620504360)
        self.assertEqual(a['pickup_time/epoch_l'], 1620504720)
        self.assertEqual(a['channel_number_i'], 2)
        self.assertEqual(a['seed_station_name_s'], '1')
        self.assertEqual(a['seed_band_code_s'], 'D')
        self.assertEqual(a['seed_instrument_code_s'], 'P')
        self.assertEqual(a['sample_rate_i'], 250)
        self.assertEqual(a['sample_rate_multiplier_i'], 1)
        self.assertEqual(a['location/description_s'],
                         'Read from SEG-D as is.')

        # check das_t - first trace
        self.ph5object.read_das_g_names()
        self.assertEqual(self.ph5object.Das_g_names.keys(), ['Das_g_1X1'])
        das = self.ph5object.read_das_t('Das_g_1X1')
        d = self.ph5object.Das_t[das]['rows'][0]
        self.assertEqual(d['sample_rate_i'], 250)
        self.assertEqual(d['array_name_data_a'], 'Data_a_0001')
        self.assertEqual(d['sample_count_i'], 251)
        self.assertEqual(d['sample_rate_multiplier_i'], 1)
        self.assertEqual(d['time/epoch_l'], 1620504360)
        self.assertEqual(d['raw_file_name_s'],
                         '453005513.2.2021.05.08.20.06..E')


class TestSegDtoPH5_messed_order(TempDirTestCase, LogTestCase):
    def tearDown(self):
        self.ph5object.ph5close()
        super(TestSegDtoPH5_messed_order, self).tearDown()

    def test_main(self):
        """
        segd_list not in time order
        test if created das_t in time order
        """
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()

        # create list file
        segd_dir = os.path.join(self.home, "ph5/test_data/segd/messed_order/")
        with open('segd_list', "w") as segdlistfile:
            fileList = os.listdir(segd_dir)
            for f in fileList:
                if f.endswith('segd'):
                    segdlistfile.write(os.path.join(segd_dir, f) + "\n")

        # add segD to ph5
        testargs = ['segdtoph5', '-n', 'master.ph5', '-f', 'segd_list']
        with patch.object(sys, 'argv', testargs):
            with LogCapture():
                with OutputCapture():
                    segd2ph5.main()

        self.ph5object = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        das_g = self.ph5object.ph5_g_receivers.getdas_g('1X4')
        self.ph5object.ph5_g_receivers.setcurrent(das_g)
        das_rows, das_keys = experiment.read_table(
            self.ph5object.ph5_g_receivers.current_t_das)

        ordered_das_rows = sorted(
            das_rows,
            key=operator.itemgetter('channel_number_i',
                                    'time/epoch_l',
                                    'time/micro_seconds_i'))
        self.assertEqual(das_rows, ordered_das_rows)


class TestSegDtoPH5_precision(TempDirTestCase, LogTestCase):
    def tearDown(self):
        self.ph5object.ph5close()
        super(TestSegDtoPH5_precision, self).tearDown()

    def test_main(self):
        """
        test if created das_t[time/micro_second_i] is correct
        """
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()

        # create list file
        segd_file = os.path.join(
            self.home, "ph5/test_data/segd/smartsolo/453005513.2.2021.05.08."
                       "20.06.00.000.E.segd")

        # add segD to ph5
        testargs = ['segdtoph5', '-n', 'master.ph5', '-r', segd_file]
        with patch.object(sys, 'argv', testargs):
            with LogCapture():
                with OutputCapture():
                    segd2ph5.main()

        self.ph5object = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        das_g = self.ph5object.ph5_g_receivers.getdas_g('1X1')
        self.ph5object.ph5_g_receivers.setcurrent(das_g)
        das_rows, das_keys = experiment.read_table(
            self.ph5object.ph5_g_receivers.current_t_das)
        # 7999 before fixed
        self.assertEqual(das_rows[2]['time/micro_seconds_i'], 8000)
        # 19999 before fixed
        self.assertEqual(das_rows[5]['time/micro_seconds_i'], 20000)


if __name__ == "__main__":
    unittest.main()
