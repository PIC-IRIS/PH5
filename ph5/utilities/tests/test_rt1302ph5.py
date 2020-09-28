'''
Tests for rt1302ph5
'''
import os
import sys
import unittest
import logging

from mock import patch
from testfixtures import LogCapture, OutputCapture

from ph5.utilities import rt1302ph5, initialize_ph5
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase,\
    das_in_mini, create_list_file


class TestRT130toPH5_noclose(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestRT130toPH5_noclose, self).setUp()
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()

    def tearDown(self):
        rt1302ph5.MAX_PH5_BYTES = 1073741824 * 100.
        super(TestRT130toPH5_noclose, self).tearDown()

    def test_get_highest_mini(self):
        index_t_das_rows = [{'external_file_name_s': './miniPH5_00003.ph5'},
                            {'external_file_name_s': './miniPH5_00010.ph5'},
                            {'external_file_name_s': './miniPH5_00001.ph5'},
                            {'external_file_name_s': './miniPH5_00009.ph5'},
                            {'external_file_name_s': './miniPH5_00007.ph5'}]
        index_t_das = rt1302ph5.Rows_Keys(index_t_das_rows)
        ret = rt1302ph5.get_highest_mini(index_t_das)
        self.assertEqual(ret, 10)

    def test_get_args(self):
        # error when -M and -F is used at the same time
        testargs = ['130toph5', '-n', 'master.ph5', '-r', 'test',
                    '-M', '5', '-F', '3']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                self.assertRaises(
                    SystemExit,
                    rt1302ph5.get_args)

        # -M
        testargs = ['130toph5', '-n', 'master.ph5', '-r', 'test',
                    '-M', '5']
        with patch.object(sys, 'argv', testargs):
            rt1302ph5.get_args()
        self.assertEqual(rt1302ph5.NUM_MINI, 5)

        # -F
        testargs = ['130toph5', '-n', 'master.ph5', '-r', 'test',
                    '-F', '5']
        with patch.object(sys, 'argv', testargs):
            rt1302ph5.get_args()
        self.assertEqual(rt1302ph5.FROM_MINI, 5)

    def test_main_from_mini(self):
        """ test main() with -F option """
        filename = create_list_file(self.home, 'ZIP', 'rt130')
        # reset MAX_PH5_BYTES to allow MB for a mini file only
        # check 2 mini file is created start from FROM_MINI
        rt1302ph5.MAX_PH5_BYTES = 1024 * 1024
        testargs = ['130toph5', '-n', 'master.ph5', '-f', filename, '-F', '3']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                rt1302ph5.main()

        ph5set = {f for f in os.listdir(self.tmpdir) if f.endswith('.ph5')}
        self.assertEqual(ph5set,
                         {'miniPH5_00003.ph5', 'miniPH5_00004.ph5',
                          'master.ph5'})

        # FROM_MINI < highest mini
        testargs = ['130toph5', '-n', 'master.ph5', '-F', '3', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/rt130/2016139.9EEF.ZIP')]
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                self.assertRaises(SystemExit, rt1302ph5.main)
                self.assertEqual(
                    log.records[0].msg,
                    'FROM_MINI must be greater than or equal to 4, '
                    'the highest mini file in ph5.')

        testargs = ['130toph5', '-n', 'master.ph5', '-F', '6', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/rt130/2016139.9EEF.ZIP')]
        # check mini file continue from FROM_MINI
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                rt1302ph5.main()

        ph5set = {f for f in os.listdir(self.tmpdir) if f.endswith('.ph5')}
        self.assertEqual(ph5set,
                         {'miniPH5_00003.ph5', 'miniPH5_00004.ph5',
                          'miniPH5_00006.ph5', 'master.ph5'})
        self.assertEqual(das_in_mini(self.tmpdir, 'miniPH5_00003.ph5'),
                         ['Das_g_92C8'])
        self.assertEqual(das_in_mini(self.tmpdir, 'miniPH5_00004.ph5'),
                         ['Das_g_9EEF'])
        self.assertEqual(das_in_mini(self.tmpdir, 'miniPH5_00006.ph5'),
                         ['Das_g_9EEF'])


class TestRT130toPH5_closeEX(TempDirTestCase, LogTestCase):
    def tearDown(self):
        try:
            rt1302ph5.EX.ph5close()
            rt1302ph5.EXREC.ph5close()
        except AttributeError:
            pass
        super(TestRT130toPH5_closeEX, self).tearDown()

    def test_get_current_data_only(self):
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()
        testargs = ['130toph5', '-n', 'master', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/rt130/2016139.9EEF.ZIP'),
                    '-F', '3']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                rt1302ph5.main()
        rt1302ph5.initializeExperiment('master')
        rows, keys = rt1302ph5.EX.ph5_g_receivers.read_index()
        rt1302ph5.INDEX_T = rt1302ph5.Rows_Keys(rows, keys)

        # FROM_MINI < miniPH5_00003.ph5
        # size of data + size of miniPH5_00003.ph5 < MAX_PH5_BYTES
        # => save to last mini: miniPH5_00003.ph5
        rt1302ph5.FROM_MINI = 2
        rt1302ph5.EXREC = rt1302ph5.get_current_data_only(1083348, '9EEF')
        self.assertEqual(rt1302ph5.EXREC.filename, './miniPH5_00003.ph5')
        rt1302ph5.EXREC.ph5close()

        rt1302ph5.MAX_PH5_BYTES = 1024 * 1024 * 2
        # FROM_MINI < miniPH5_00003.ph5
        # size of data + size of miniPH5_00003.ph5 > MAX_PH5_BYTES
        # => save to miniPH5_00004.ph5 (last+1)
        rt1302ph5.FROM_MINI = 2
        rt1302ph5.EXREC = rt1302ph5.get_current_data_only(2183348, '92C8')
        self.assertEqual(rt1302ph5.EXREC.filename, './miniPH5_00004.ph5')
        rt1302ph5.EXREC.ph5close()

        # FROM_MINI > last mini file
        # => save to miniPH5_00005.ph5 (FROM_MINI)
        rt1302ph5.FROM_MINI = 5
        rt1302ph5.EXREC = rt1302ph5.get_current_data_only(1083348, '92C8')
        self.assertEqual(rt1302ph5.EXREC.filename, './miniPH5_00005.ph5')


if __name__ == "__main__":
    unittest.main()
