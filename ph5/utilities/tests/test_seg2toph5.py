'''
Tests for seg2toph5
'''
import os
import sys
import unittest
import logging

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.utilities import seg2toph5, initialize_ph5
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase,\
    initialize_ex
from ph5.core import ph5api


class TestSeg2toPH5_main(TempDirTestCase, LogTestCase):
    def tearDown(self):
        self.ph5object.ph5close()
        super(TestSeg2toPH5_main, self).tearDown()

    def test_main(self):
        # check external links created
        data_nodes = ['Das_g_0000SV01', 'Das_g_0000SV02', 'Das_g_0000SV03',
                      'Das_g_0000SV04', 'Das_g_0000SV05', 'Das_g_0000SV06',
                      'Das_g_0000SV07', 'Das_g_0000SV08', 'Das_g_0000SV09',
                      'Das_g_0000SV10', 'Das_g_0000SV11', 'Das_g_0000SV12',
                      'Das_g_0000SV13', 'Das_g_0000SV14', 'Das_g_0000SV15',
                      'Das_g_0000SV16', 'Das_g_0000SV17', 'Das_g_0000SV18',
                      'Das_g_0000SV19', 'Das_g_0000SV20', 'Das_g_0000SV21',
                      'Das_g_0000SV22', 'Das_g_0000SV23', 'Das_g_0000SV24',
                      'Das_g_0000SV25', 'Das_g_0000SV26', 'Das_g_0000SV27',
                      'Das_g_0000SV28', 'Das_g_0000SV29', 'Das_g_0000SV30',
                      'Das_g_0000SV31', 'Das_g_0000SV32', 'Das_g_0000SV33',
                      'Das_g_0000SV34', 'Das_g_0000SV35', 'Das_g_0000SV36',
                      'Das_g_0000SV37', 'Das_g_0000SV38', 'Das_g_0000SV39',
                      'Das_g_0000SV40', 'Das_g_0000SV41', 'Das_g_0000SV42',
                      'Das_g_0000SV43', 'Das_g_0000SV44', 'Das_g_0000SV45',
                      'Das_g_0000SV46', 'Das_g_0000SV47', 'Das_g_0000SV48',
                      'Das_g_0000SV49', 'Das_g_0000SV50', 'Das_g_0000SV51',
                      'Das_g_0000SV52', 'Das_g_0000SV53', 'Das_g_0000SV54',
                      'Das_g_0000SV55', 'Das_g_0000SV56', 'Das_g_0000SV57',
                      'Das_g_0000SV58', 'Das_g_0000SV59', 'Das_g_0000SV60']
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()
        # add seg2 to ph5
        testargs = ['seg2toph5', '-n', 'master.ph5', '-r',
                    os.path.join(self.home, "ph5/test_data/seg2/15001.dat")]
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                with LogCapture() as log:
                    log.setLevel(logging.ERROR)
                    seg2toph5.main()

        # before commit caf6978, there would be 1 error log if run this in
        # environment that uses Obspy 1.2.2
        self.assertEqual(len(log.records), 0)
        self.ph5object = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')

        target_p1 = 'miniPH5_00001.ph5:/Experiment_g/Maps_g/'
        targets = [target_p1 + n for n in data_nodes]

        node = self.ph5object.ph5.get_node("/Experiment_g/Maps_g/")
        i = 0
        ret_targets = []
        for n in self.ph5object.ph5.list_nodes(node):
            if hasattr(n, 'target'):
                ret_targets.append(n.target)
                i += 1
        self.assertEqual(ret_targets, targets)

        target_p1 = 'miniPH5_00001.ph5:/Experiment_g/Receivers_g/'
        targets = [target_p1 + n for n in data_nodes]

        node = self.ph5object.ph5.get_node("/Experiment_g/Receivers_g/")
        i = 0
        ret_targets = []
        for n in self.ph5object.ph5.list_nodes(node):
            if hasattr(n, 'target'):
                ret_targets.append(n.target)
                i += 1
        self.assertEqual(ret_targets, targets)

    def test_update_external_references(self):
        self.ph5object = seg2toph5.EX = \
            initialize_ex('master.ph5', '.', True)
        keys = ['external_file_name_s', 'hdf5_path_s', 'serial_number_s']
        INDEX_T_DAS_rows = \
            [{'external_file_name_s': './miniPH5_00001.ph5',
              'hdf5_path_s': '/Experiment_g/Receivers_g/Das_g_0000SV01'}]
        seg2toph5.INDEX_T_DAS = seg2toph5.Rows_Keys(INDEX_T_DAS_rows, keys)

        INDEX_T_MAP_rows = \
            [{'external_file_name_s': './miniPH5_00001.ph5',
              'hdf5_path_s': '/Experiment_g/Maps_g/Das_g_0000SV01'}]
        seg2toph5.INDEX_T_MAP = seg2toph5.Rows_Keys(INDEX_T_MAP_rows, keys)

        seg2toph5.update_external_references()

        # check if external links are created
        node = self.ph5object.ph5.get_node("/Experiment_g/Receivers_g/")
        target = 'miniPH5_00001.ph5:/Experiment_g/Receivers_g/Das_g_0000SV01'
        for n in self.ph5object.ph5.list_nodes(node):
            if hasattr(n, 'target'):
                self.assertEqual(n.target, target)
                break

        node = self.ph5object.ph5.get_node("/Experiment_g/Maps_g/")
        target = 'miniPH5_00001.ph5:/Experiment_g/Maps_g/Das_g_0000SV01'
        for n in self.ph5object.ph5.list_nodes(node):
            if hasattr(n, 'target'):
                self.assertEqual(n.target, target)
                break


if __name__ == "__main__":
    unittest.main()
