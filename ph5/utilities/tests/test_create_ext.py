'''
Tests for create_ext
'''
import os
import sys
import unittest
import logging

import tables
from mock import patch
from testfixtures import LogCapture

from ph5.core import ph5api
from ph5.utilities import segd2ph5, nuke_table, create_ext, kef2ph5
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


class TestCreateExt(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestCreateExt, self).setUp()
        """
        from segd data create ph5 which include array_t, index_t_, das_g
        """
        testargs = ['segdtoph5', '-n', 'master.ph5', '-r',
                    os.path.join(self.home,
                                 "ph5/test_data/segd/fairfield/3ch.fcnt")]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

    def tearDown(self):
        try:
            self.ph5obj.close()
        except AttributeError:
            pass
        super(TestCreateExt, self).tearDown()

    def rem_ext_link(self):
        # remove ext_link to das_g
        ph5object = ph5api.PH5(path='.', nickname='master.ph5', editmode=True)
        ph5object.ph5.get_node('/Experiment_g/Receivers_g/Das_g_3X500'
                               ).remove()
        ph5object.close()

    def checkExtlink(self):
        self.ph5obj = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        try:
            self.ph5obj.ph5.get_node('/Experiment_g/Receivers_g/Das_g_3X500')
        except tables.exceptions.NoSuchNodeError:
            return False
        return True

    def test_main_wrong_mini(self):
        testargs = ['create_ext', '-n', 'master.ph5', '-D', '3X500',
                    '-m', 'miniPH5_00002.ph5']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                create_ext.main()
                self.assertEqual(
                    "Minifile '%s' not exist."
                    % os.path.join(self.tmpdir, 'miniPH5_00002.ph5'),
                    log.records[0].msg)

    def test_main_w_extlink(self):
        testargs = ['create_ext', '-n', 'master.ph5', '-D', '3X500',
                    '-m', 'miniPH5_00001.ph5']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                create_ext.main()
                self.assertEqual(
                    "External link '/Experiment_g/Receivers_g/Das_g_3X500' "
                    "already exist.",
                    log.records[0].msg)

    def test_main_wo_extlink(self):
        self.rem_ext_link()
        testargs = ['create_ext', '-n', 'master.ph5', '-D', '3X500',
                    '-m', 'miniPH5_00001.ph5']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.INFO)
                create_ext.main()
                self.assertEqual(
                    "External link '/Experiment_g/Receivers_g/Das_g_3X500' "
                    "is created. Please run ph5_validate to check for "
                    "consistency.",
                    log.records[2].msg)
        self.assertTrue(self.checkExtlink())

    def test_main_wo_extlink_arr(self):
        self.rem_ext_link()
        testargs = ['nuke_table', '-n', 'master.ph5', '-A', '001']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()

        testargs = ['create_ext', '-n', 'master.ph5', '-D', '3X500',
                    '-m', 'miniPH5_00001.ph5']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                create_ext.main()
                self.assertEqual(
                    "Das 3X500 not found in Array_t. Metadata need "
                    "to be added before creating external link.",
                    log.records[0].msg)
        self.assertFalse(self.checkExtlink())

    def test_main_wo_extLink_index(self):
        self.rem_ext_link()
        testargs = ['nuke_table', '-n', 'master.ph5', '-I']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()

        testargs = ['create_ext', '-n', 'master.ph5', '-D', '3X500',
                    '-m', 'miniPH5_00001.ph5']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                create_ext.main()
                self.assertEqual(
                    "Das 3X500 not found in Index_t. Metadata need "
                    "to be added before creating external link.",
                    log.records[0].msg)
        self.assertFalse(self.checkExtlink())

    def test_main_wo_extLink_mini_changed(self):
        self.rem_ext_link()

        # change minifile name in index_t
        testargs = ['nuke_table', '-n', 'master.ph5', '-I']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        testargs = ['kef2ph5', '-n', 'master.ph5', '-k',
                    os.path.join(
                        self.home,
                        'ph5/test_data/metadata/index_minichanged.kef')]
        with patch.object(sys, 'argv', testargs):
            kef2ph5.main()

        testargs = ['create_ext', '-n', 'master.ph5', '-D', '3X500',
                    '-m', 'miniPH5_00001.ph5']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                create_ext.main()
                self.assertEqual(
                    log.records[0].msg,
                    "Minifile for Das 3X500 in index_t is miniPH5_00002.ph5 "
                    "while the given minifile is miniPH5_00001.ph5.")
        self.assertFalse(self.checkExtlink())

    def test_scan_folder_for_minifile(self):
        testargs = ['create_ext', '-n', 'master.ph5', '-D', '3X500', '-s']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                create_ext.main()
                self.assertEqual(
                    log.records[-1].msg,
                    "Waveform data for DAS 3X500 is found in "
                    "'./miniPH5_00001.ph5'")

        testargs = ['create_ext', '-n', 'master.ph5', '-D', '3X501', '-s']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                create_ext.main()
                self.assertEqual(
                    log.records[-1].msg,
                    "DAS 3X501's waveform data can't be found in any of the "
                    "minifiles in the given path: '.'")


if __name__ == "__main__":
    unittest.main()
