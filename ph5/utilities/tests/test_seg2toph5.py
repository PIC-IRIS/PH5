'''
Tests for seg2toph5
'''
import os
import sys
import unittest
import logging

from mock import patch
from testfixtures import LogCapture, OutputCapture

from ph5.utilities import seg2toph5, initialize_ph5
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase,\
    das_in_mini, create_list_file


class TestRT130toPH5_noclose(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestRT130toPH5_noclose, self).setUp()
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()
        self.MAX_PH5_BYTES = seg2toph5.MAX_PH5_BYTES

    def tearDown(self):
        seg2toph5.MAX_PH5_BYTES = self.MAX_PH5_BYTES
        super(TestRT130toPH5_noclose, self).tearDown()

    def test_get_highest_mini(self):
        index_t_das_rows = [{'external_file_name_s': './miniPH5_00003.ph5'},
                            {'external_file_name_s': './miniPH5_00010.ph5'},
                            {'external_file_name_s': './miniPH5_00001.ph5'},
                            {'external_file_name_s': './miniPH5_00009.ph5'},
                            {'external_file_name_s': './miniPH5_00007.ph5'}]
        index_t_das = seg2toph5.Rows_Keys(index_t_das_rows)
        ret = seg2toph5.get_highest_mini(index_t_das)
        self.assertEqual(ret, 10)

    def test_get_args(self):
        # error when -M and -F is used at the same time
        testargs = ['seg2toph5', '-n', 'master.ph5', '-f', 'test',
                    '-M', '5', '-F', '3']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                self.assertRaises(
                    SystemExit,
                    seg2toph5.get_args)

        # -M
        testargs = ['seg2toph5', '-n', 'master.ph5', '-f', 'test',
                    '-M', '5']
        with patch.object(sys, 'argv', testargs):
            seg2toph5.get_args()
        self.assertEqual(seg2toph5.NUM_MINI, 5)

        # -F
        testargs = ['seg2toph5', '-n', 'master.ph5', '-f', 'test',
                    '-F', '5']
        with patch.object(sys, 'argv', testargs):
            seg2toph5.get_args()
        self.assertEqual(seg2toph5.FROM_MINI, 5)

    def test_main_from_mini(self):
        """ test main() with -F option """
        filename = create_list_file(self.home, 'dat', 'seg2', '1007')
        # reset MAX_PH5_BYTES to allow MB for a mini file only
        # check 2 mini file is created start from FROM_MINI
        seg2toph5.MAX_PH5_BYTES = 1024 * 1024
        testargs = ['seg2toph5', '-n', 'master.ph5', '-f', filename, '-F', '3']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                seg2toph5.main()

        ph5set = {f for f in os.listdir(self.tmpdir) if f.endswith('.ph5')}
        self.assertEqual(ph5set,
                         {'miniPH5_00003.ph5', 'master.ph5'})

        # FROM_MINI < highest mini
        testargs = ['seg2toph5', '-n', 'master.ph5', '-f', filename, '-F', '2']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                self.assertRaises(SystemExit, seg2toph5.main)
                self.assertEqual(
                    log.records[0].msg,
                    'FROM_MINI must be greater than or equal to 3, '
                    'the highest mini file in ph5.')

        filename = create_list_file(self.home, 'dat', 'seg2', '1008')
        testargs = ['seg2toph5', '-n', 'master.ph5', '-f', filename, '-F', '7']

        # check mini file continue from FROM_MINI
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                seg2toph5.main()

        ph5set = {f for f in os.listdir(self.tmpdir) if f.endswith('.ph5')}
        self.assertEqual(ph5set,
                         {'miniPH5_00003.ph5', 'miniPH5_00007.ph5',
                          'master.ph5'})
        self.assertEqual(das_in_mini(self.tmpdir, 'miniPH5_00003.ph5'),
                         ['Das_g_0000SV43', 'Das_g_0000SV08', 'Das_g_0000SV09',
                          'Das_g_0000SV04', 'Das_g_0000SV05', 'Das_g_0000SV06',
                          'Das_g_0000SV07', 'Das_g_0000SV01', 'Das_g_0000SV02',
                          'Das_g_0000SV03', 'Das_g_0000SV22', 'Das_g_0000SV23',
                          'Das_g_0000SV20', 'Das_g_0000SV21', 'Das_g_0000SV26',
                          'Das_g_0000SV27', 'Das_g_0000SV24', 'Das_g_0000SV25',
                          'Das_g_0000SV40', 'Das_g_0000SV41', 'Das_g_0000SV28',
                          'Das_g_0000SV29', 'Das_g_0000SV44', 'Das_g_0000SV45',
                          'Das_g_0000SV46', 'Das_g_0000SV47', 'Das_g_0000SV48',
                          'Das_g_0000SV19', 'Das_g_0000SV18', 'Das_g_0000SV13',
                          'Das_g_0000SV12', 'Das_g_0000SV11', 'Das_g_0000SV10',
                          'Das_g_0000SV17', 'Das_g_0000SV16', 'Das_g_0000SV15',
                          'Das_g_0000SV14', 'Das_g_0000SV31', 'Das_g_0000SV30',
                          'Das_g_0000SV33', 'Das_g_0000SV32', 'Das_g_0000SV35',
                          'Das_g_0000SV34', 'Das_g_0000SV37', 'Das_g_0000SV36',
                          'Das_g_0000SV39', 'Das_g_0000SV38', 'Das_g_0000SV42']
                         )
        self.assertEqual(das_in_mini(self.tmpdir, 'miniPH5_00007.ph5'),
                         ['Das_g_0000SV43', 'Das_g_0000SV08', 'Das_g_0000SV09',
                          'Das_g_0000SV04', 'Das_g_0000SV05', 'Das_g_0000SV06',
                          'Das_g_0000SV07', 'Das_g_0000SV01', 'Das_g_0000SV02',
                          'Das_g_0000SV03', 'Das_g_0000SV22', 'Das_g_0000SV23',
                          'Das_g_0000SV20', 'Das_g_0000SV21', 'Das_g_0000SV26',
                          'Das_g_0000SV27', 'Das_g_0000SV24', 'Das_g_0000SV25',
                          'Das_g_0000SV40', 'Das_g_0000SV41', 'Das_g_0000SV28',
                          'Das_g_0000SV29', 'Das_g_0000SV44', 'Das_g_0000SV45',
                          'Das_g_0000SV46', 'Das_g_0000SV47', 'Das_g_0000SV48',
                          'Das_g_0000SV19', 'Das_g_0000SV18', 'Das_g_0000SV13',
                          'Das_g_0000SV12', 'Das_g_0000SV11', 'Das_g_0000SV10',
                          'Das_g_0000SV17', 'Das_g_0000SV16', 'Das_g_0000SV15',
                          'Das_g_0000SV14', 'Das_g_0000SV31', 'Das_g_0000SV30',
                          'Das_g_0000SV33', 'Das_g_0000SV32', 'Das_g_0000SV35',
                          'Das_g_0000SV34', 'Das_g_0000SV37', 'Das_g_0000SV36',
                          'Das_g_0000SV39', 'Das_g_0000SV38', 'Das_g_0000SV42']
                         )


class TestRT130toPH5_closeEX(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestRT130toPH5_closeEX, self).setUp()
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()
        self.MAX_PH5_BYTES = seg2toph5.MAX_PH5_BYTES

    def tearDown(self):
        seg2toph5.MAX_PH5_BYTES = self.MAX_PH5_BYTES
        try:
            seg2toph5.EX.ph5close()
            seg2toph5.EXREC.ph5close()
        except AttributeError:
            pass
        super(TestRT130toPH5_closeEX, self).tearDown()

    def test_get_current_data_only(self):
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()
        filename = create_list_file(self.home, 'dat', 'seg2', '1007')
        testargs = ['seg2toph5', '-n', 'master.ph5', '-f', filename, '-F', '3']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                seg2toph5.main()
        seg2toph5.initializeExperiment()
        rows, keys = seg2toph5.EX.ph5_g_receivers.read_index()
        seg2toph5.INDEX_T = seg2toph5.Rows_Keys(rows, keys)

        # FROM_MINI < miniPH5_00003.ph5
        # size of data + size of miniPH5_00003.ph5 < MAX_PH5_BYTES
        # => save to last mini: miniPH5_00003.ph5
        seg2toph5.FROM_MINI = 2
        seg2toph5.EXREC = seg2toph5.get_current_data_only(1083348, '0000SV43')
        self.assertEqual(seg2toph5.EXREC.filename, './miniPH5_00003.ph5')
        seg2toph5.EXREC.ph5close()

        seg2toph5.MAX_PH5_BYTES = 1024 * 1024 * 2

        # FROM_MINI < miniPH5_00003.ph5
        # size of data + size of miniPH5_00003.ph5 > MAX_PH5_BYTES
        # => save to miniPH5_00004.ph5 (last+1)
        seg2toph5.FROM_MINI = 2
        seg2toph5.EXREC = seg2toph5.get_current_data_only(2183348, '0000SV43')
        self.assertEqual(seg2toph5.EXREC.filename, './miniPH5_00004.ph5')
        seg2toph5.EXREC.ph5close()

        # FROM_MINI > last mini file
        # => save to miniPH5_00005.ph5 (FROM_MINI)
        seg2toph5.FROM_MINI = 5
        seg2toph5.EXREC = seg2toph5.get_current_data_only(1083348, '0000SV43')
        self.assertEqual(seg2toph5.EXREC.filename, './miniPH5_00005.ph5')


if __name__ == "__main__":
    unittest.main()
