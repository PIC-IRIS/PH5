'''
Tests for texan2ph5
'''
import os
import sys
import unittest
import logging

from mock import patch
from testfixtures import LogCapture, OutputCapture

from ph5.utilities import texan2ph5, initialize_ph5
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase,\
    das_in_mini


class TestTexantoPH5_noclose(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestTexantoPH5_noclose, self).setUp()
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()

    def tearDown(self):
        texan2ph5.MAX_PH5_BYTES = 1073741824 * 100.
        super(TestTexantoPH5_noclose, self).tearDown()

    def test_get_highest_mini(self):
        index_t_das_rows = [{'external_file_name_s': './miniPH5_00003.ph5'},
                            {'external_file_name_s': './miniPH5_00010.ph5'},
                            {'external_file_name_s': './miniPH5_00001.ph5'},
                            {'external_file_name_s': './miniPH5_00009.ph5'},
                            {'external_file_name_s': './miniPH5_00007.ph5'}]
        index_t_das = texan2ph5.Rows_Keys(index_t_das_rows)
        ret = texan2ph5.get_highest_mini(index_t_das)
        self.assertEqual(ret, 10)

    def test_get_args(self):
        # error when -M and -F is used at the same time
        testargs = ['125a2ph5', '-n', 'master.ph5', '-r', 'test',
                    '-M', '5', '-F', '3']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                self.assertRaises(
                    SystemExit,
                    texan2ph5.get_args)

        # -M
        testargs = ['125a2ph5', '-n', 'master.ph5', '-r', 'test',
                    '-M', '5']
        with patch.object(sys, 'argv', testargs):
            texan2ph5.get_args()
        self.assertEqual(texan2ph5.NUM_MINI, 5)

        # -F
        testargs = ['125a2ph5', '-n', 'master.ph5', '-r', 'test',
                    '-F', '5']
        with patch.object(sys, 'argv', testargs):
            texan2ph5.get_args()
        self.assertEqual(texan2ph5.FROM_MINI, 5)

    def test_main_from_mini(self):
        """ test main() with -F option """
        # reset MAX_PH5_BYTES to allow MB for a mini file only
        # check 2 mini file is created start from FROM_MINI
        texan2ph5.MAX_PH5_BYTES = 1024 * 1024
        testargs = ['125a2ph5', '-n', 'master.ph5', '-F', '3', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/rt125a/I2183RAW.TRD')]
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                texan2ph5.main()

        ph5set = {f for f in os.listdir(self.tmpdir) if f.endswith('.ph5')}
        self.assertEqual(ph5set,
                         {'miniPH5_00003.ph5', 'master.ph5'})

        # FROM_MINI < highest mini
        testargs = ['125a2ph5', '-n', 'master.ph5', '-F', '2', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/rt125a/I2183RAW.TRD')]
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                self.assertRaises(SystemExit, texan2ph5.main)
                self.assertEqual(
                    log.records[0].msg,
                    'FROM_MINI must be greater than or equal to 3, '
                    'the highest mini file in ph5.')

        testargs = ['125a2ph5', '-n', 'master.ph5', '-F', '6', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/rt125a/I2183RAW.TRD')]
        # check mini file continue from FROM_MINI
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                texan2ph5.main()

        ph5set = {f for f in os.listdir(self.tmpdir) if f.endswith('.ph5')}
        self.assertEqual(ph5set,
                         {'miniPH5_00003.ph5', 'miniPH5_00006.ph5',
                          'master.ph5'})
        self.assertEqual(das_in_mini(self.tmpdir, 'miniPH5_00003.ph5'),
                         ['Das_g_12183'])
        self.assertEqual(das_in_mini(self.tmpdir, 'miniPH5_00006.ph5'),
                         ['Das_g_12183'])


class TestTexantoPH5_closeEX(TempDirTestCase, LogTestCase):
    def tearDown(self):
        try:
            texan2ph5.EX.ph5close()
            texan2ph5.EXREC.ph5close()
        except AttributeError:
            pass
        super(TestTexantoPH5_closeEX, self).tearDown()

    def test_get_current_data_only(self):
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()
        testargs = ['125a2ph5', '-n', 'master', '-F', '3', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/rt125a/I2183RAW.TRD')]
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                texan2ph5.main()
        texan2ph5.initializeExperiment()
        rows, keys = texan2ph5.EX.ph5_g_receivers.read_index()
        texan2ph5.INDEX_T = texan2ph5.Rows_Keys(rows, keys)

        # FROM_MINI < miniPH5_00003.ph5
        # size of data + size of miniPH5_00003.ph5 < MAX_PH5_BYTES
        # => save to last mini: miniPH5_00003.ph5
        texan2ph5.FROM_MINI = 2
        texan2ph5.EXREC = texan2ph5.get_current_data_only(1083348, '12183')
        self.assertEqual(texan2ph5.EXREC.filename, './miniPH5_00003.ph5')
        texan2ph5.EXREC.ph5close()

        texan2ph5.MAX_PH5_BYTES = 1024 * 1024 * 2
        # FROM_MINI < miniPH5_00003.ph5
        # size of data + size of miniPH5_00003.ph5 > MAX_PH5_BYTES
        # => save to miniPH5_00004.ph5 (last+1)
        texan2ph5.FROM_MINI = 2
        texan2ph5.EXREC = texan2ph5.get_current_data_only(2183348, '12183')
        self.assertEqual(texan2ph5.EXREC.filename, './miniPH5_00004.ph5')
        texan2ph5.EXREC.ph5close()

        # FROM_MINI > last mini file
        # => save to miniPH5_00005.ph5 (FROM_MINI)
        texan2ph5.FROM_MINI = 5
        texan2ph5.EXREC = texan2ph5.get_current_data_only(1083348, '92C8')
        self.assertEqual(texan2ph5.EXREC.filename, './miniPH5_00005.ph5')


if __name__ == "__main__":
    unittest.main()
