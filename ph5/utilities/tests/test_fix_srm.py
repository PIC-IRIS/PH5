'''
Tests for fix_srm
'''
import os
import sys
import unittest
import logging
from StringIO import StringIO
import time
import shutil

import tables
from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.utilities import initialize_ph5, segd2ph5, nuke_table, kef2ph5
from ph5.utilities import fix_srm
from ph5.core import ph5api, timedoy
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase

tdoy = timedoy.TimeDOY(epoch=time.time())
yeardoy = "{0:04d}{1:03d}".format(tdoy.dtobject.year, tdoy.dtobject.day)


def count_smr_0_1(filepath):
    # count 'sample_rate_multiplier_i=0' and 'sample_rate_multiplier_i=0'
    # in filepath
    with open(filepath, 'r') as file:
        content = file.read()
        smr0_no = content.count('sample_rate_multiplier_i=0')
        smr1_no = content.count('sample_rate_multiplier_i=1')
        return smr0_no, smr1_no


class TestFixSRM(TempDirTestCase, LogTestCase):
    def test_get_args(self):
        # check one of the arguments --all_das or "-D" is required
        testargs = ['fix_srm', '-n', 'master.ph5']
        with OutputCapture() as out:
            with patch.object(sys, 'argv', testargs):
                with self.assertRaises(SystemExit):
                    fix_srm.get_args()
            self.assertEqual(
                out.captured.split('\n')[1],
                'fix_srm: error: one of the arguments --all_das -D/--Das_t '
                '--all_arrays -A/--Array_t_ --all is required')

        testargs = ['fix_srm', '-n', 'master.ph5', '--all_das',
                    '-D', '1X1111']
        with OutputCapture() as out:
            with patch.object(sys, 'argv', testargs):
                with self.assertRaises(SystemExit):
                    fix_srm.get_args()
            self.assertEqual(
                out.captured.split('\n')[1],
                'fix_srm: error: argument -D/--Das_t: '
                'not allowed with argument --all_das')

        # Check flag -D
        testargs = ['fix_srm', '-n', 'master.ph5', '-D', '1X1111']
        with patch.object(sys, 'argv', testargs):
            ret = fix_srm.get_args()
        self.assertEqual(ret[0], 'master.ph5')
        self.assertEqual(ret[1], '.')
        self.assertEqual(ret[2], False)
        self.assertEqual(ret[3], '1X1111')

        # check flag --all_das
        testargs = ['fix_srm', '-n', 'master.ph5', '--all_das']
        with patch.object(sys, 'argv', testargs):
            ret = fix_srm.get_args()
        self.assertEqual(ret[0], 'master.ph5')
        self.assertEqual(ret[1], '.')
        self.assertEqual(ret[2], True)
        self.assertIsNone(ret[3])

    def test_set_logger(self):
        # check if FileHandler's filename is fix_srm.log
        fix_srm.set_logger()
        self.assertEqual(len(fix_srm.LOGGER.handlers), 1)
        self.assertIsInstance(fix_srm.LOGGER.handlers[0],
                              logging.FileHandler)
        self.assertEqual(fix_srm.LOGGER.handlers[0].baseFilename,
                         os.path.join(self.tmpdir, 'fix_srm.log'))

    def test_fix_srm_in_kef(self):
        # smr0daskef has 9 smr=0 and 0 smr=1
        # fix_srm_in_kef will created fixedfiles.kef with 0 smr=0 and 9 smr=1
        smr0daskef = os.path.join(
            self.home, 'ph5/test_data/metadata/Das_t_1X1111.0.0_SRM0.kef')
        smr0_no, smr1_no = count_smr_0_1(smr0daskef)
        self.assertEqual(smr0_no, 9)
        self.assertEqual(smr1_no, 0)
        fixedfilepath = os.path.join(self.tmpdir, 'fixedfile.kef')
        with LogCapture() as log:
            fix_srm.fix_srm_in_kef(smr0daskef, fixedfilepath)
        self.assertTrue(os.path.isfile(fixedfilepath))
        smr0_no, smr1_no = count_smr_0_1(fixedfilepath)
        self.assertEqual(smr0_no, 0)
        self.assertEqual(smr1_no, 9)
        self.assertEqual(
            log.records[0].msg,
            'Convert 9 sample_rate_multiplier_i=0 to 1 in %s and save in %s.'
            % (smr0daskef, fixedfilepath)
        )


def create_testPH5_from_segd(segdpath):
    testargs = ['initialize_ph5', '-n', 'master.ph5']
    with patch.object(sys, 'argv', testargs):
        initialize_ph5.main()

    testargs = ['segdtoph5', '-n', 'master.ph5', '-r', segdpath]
    with patch.object(sys, 'argv', testargs):
        segd2ph5.main()


def remove_table_from_PH5(flag, val):
    testargs = ['delete_table', '-n', 'master.ph5', flag, val]
    with patch.object(sys, 'argv', testargs):
        with OutputCapture():
            f = StringIO('y')
            sys.stdin = f
            nuke_table.main()
            f.close()


def add_kef_to_PH5(kefpath):
    testargs = ['keftoph5', '-n', 'master.ph5', '-k', kefpath]
    with patch.object(sys, 'argv', testargs):
        kef2ph5.main()


class TestFixSRM_PH5Object(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestFixSRM_PH5Object, self).setUp()
        segdpath = os.path.join(self.home, 'ph5/test_data/segd/1111.0.0.fcnt')
        create_testPH5_from_segd(segdpath)
        self.ph5_object = ph5api.PH5(
            path=self.tmpdir, nickname='master.ph5', editmode=True)
        fix_srm.init_T2K(self.ph5_object)

    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestFixSRM_PH5Object, self).tearDown()

    def test_delete_das(self):
        # check das 1X1111's data to compare with the result afterward
        das = self.ph5_object.ph5_g_receivers.getdas_g('1X1111')
        self.ph5_object.ph5_g_receivers.setcurrent(das)
        self.assertEqual(self.ph5_object.ph5_g_receivers.current_t_das.nrows,
                         9)
        with LogCapture() as log:
            ret = fix_srm.delete_das(self.ph5_object, das_name='Das_t_1X1111')

        backupfile = 'Das_t_1X1111_%s_00.kef' % yeardoy
        datapath = '/Experiment_g/Receivers_g/Das_g_1X1111/Das_t'
        # check nuke log msg
        self.assertEqual(log.records[2].msg, 'Nuke %s.' % datapath)
        # check returning backupfile's name for das
        self.assertEqual(ret, backupfile)
        # check if backupfile exist
        self.assertTrue(os.path.exists(os.path.join(
            self.tmpdir, backupfile)))
        # check if das 1X1111's data has been removed from self.ph5_object
        self.assertEqual(self.ph5_object.ph5_g_receivers.current_t_das.nrows,
                         0)

    def test_delete_array(self):
        # check Array_t_001's data to compare with the result afterward
        self.ph5_object.read_array_t_names()
        node = self.ph5_object.ph5_g_sorts.ph5.get_node(
            '/Experiment_g/Sorts_g', name='Array_t_001', classname='Table')
        self.assertIsInstance(node, tables.table.Table)
        with LogCapture() as log:
            ret = fix_srm.delete_array(self.ph5_object,
                                       array_name='Array_t_001')

        backupfile = 'Array_t_001_%s_00.kef' % yeardoy
        datapath = '/Experiment_g/Sorts_g/Array_t_001'
        # # check nuke log msg
        self.assertEqual(log.records[2].msg,
                         'Nuke %s.' % datapath)
        # # check returning backupfile's name for das
        self.assertEqual(ret, backupfile)
        # check if backupfile exist
        self.assertTrue(os.path.exists(os.path.join(
            self.tmpdir, backupfile)))
        # check if array's data has been removed from self.ph5_object
        with self.assertRaises(tables.NoSuchNodeError):
            self.ph5_object.ph5_g_sorts.ph5.get_node(
                '/Experiment_g/Sorts_g', name='Array_t_001', classname='Table')

    def test_add_fixed_table(self):
        # remove das 1X1111 from ph5_object
        fix_srm.delete_das(self.ph5_object, 'Das_t_1X1111')
        # check if das has been removed
        das = self.ph5_object.ph5_g_receivers.getdas_g('1X1111')
        self.ph5_object.ph5_g_receivers.setcurrent(das)
        self.assertEqual(self.ph5_object.ph5_g_receivers.current_t_das.nrows,
                         0)

        # test adding fixed kef file to ph5 object
        smr0daskef = os.path.join(
            self.home, 'ph5/test_data/metadata/Das_t_1X1111.0.0_SRM0.kef')
        shutil.copy(smr0daskef, 'das.kef')
        fix_srm.add_fixed_table(
            self.ph5_object, 'master.ph5', 'das.kef')
        # check if das has been added
        self.assertEqual(self.ph5_object.ph5_g_receivers.current_t_das.nrows,
                         9)


class TestFixSRM_srm0PH5file(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestFixSRM_srm0PH5file, self).setUp()
        smr0daskef = os.path.join(
            self.home, 'ph5/test_data/metadata/Das_t_1X1111.0.0_SRM0.kef')
        smr0arraykef = os.path.join(
            self.home, 'ph5/test_data/metadata/Array_t_001_smr0.kef')
        segdpath = os.path.join(self.home, 'ph5/test_data/segd/1111.0.0.fcnt')
        create_testPH5_from_segd(segdpath)
        remove_table_from_PH5('-D', '1X1111')
        add_kef_to_PH5(smr0daskef)
        remove_table_from_PH5('-A', '1')
        add_kef_to_PH5(smr0arraykef)
        das_backupname = 'Das_t_1X1111_%s_01.kef' % yeardoy
        das_backup_path = os.path.join(self.tmpdir, das_backupname)
        array_backupname = 'Array_t_001_%s_01.kef' % yeardoy
        array_backup_path = os.path.join(self.tmpdir, array_backupname)
        self.logmsg = [
            (">>> Processing Das: Das_t_1X1111"
             "Read /Experiment_g/Receivers_g/Das_g_1X1111/Das_t (Table(9,)) ''"
             "Writing table backup: %s."
             "Nuke /Experiment_g/Receivers_g/Das_g_1X1111/Das_t."
             "Convert 9 sample_rate_multiplier_i=0 to 1 in %s and save in "
             "fixed.kef.Loading fixed.kef into master.ph5."
             % (das_backup_path, das_backupname)),
            (">>> Processing Array: Array_t_001"
             "Read /Experiment_g/Sorts_g/Array_t_001 (Table(3,)) ''"
             "Writing table backup: %s."
             "Nuke /Experiment_g/Sorts_g/Array_t_001."
             "Convert 3 sample_rate_multiplier_i=0 to 1 in %s and save in "
             "fixed.kef.Loading fixed.kef into master.ph5."
             % (array_backup_path, array_backupname))
        ]

    def tearDown(self):
        try:
            self.ph5_object.ph5close()
        except AttributeError:
            pass
        super(TestFixSRM_srm0PH5file, self).tearDown()

    def assertArraySRM(self, array_name, srm_val, total_srm):
        arraybyid = self.ph5_object.Array_t[array_name]['byid']
        srm_count = 0
        for station_list in arraybyid:
            for deployment in arraybyid[station_list]:
                for station in arraybyid[station_list][deployment]:
                    if station['sample_rate_multiplier_i'] == srm_val:
                        srm_count += 1
        self.assertEqual(srm_count, total_srm)

    def test_process(self):
        self.ph5_object = ph5api.PH5(
            path=self.tmpdir, nickname='master.ph5', editmode=True)
        das = self.ph5_object.ph5_g_receivers.getdas_g('1X1111')
        self.ph5_object.ph5_g_receivers.setcurrent(das)
        # ph5_g_receivers.current_t_das.read() instead of
        # ph5_g_receivers.read_das() because the later change the value of srm
        ret = self.ph5_object.ph5_g_receivers.current_t_das.read()
        # before process:
        # there are 9 rows of sample_rate_multiplier_i=0 in das_t
        # there are 3 rows of sample_rate_multiplier_i=0 in array_t
        self.assertEqual(len(ret), 9)
        for row in ret:
            # check original srm=0
            self.assertEqual(row['sample_rate_multiplier_i'], 0)

        self.ph5_object.read_array_t('Array_t_001')
        self.assertArraySRM('Array_t_001', 0, 3)

        # after process das_name=Das_t_1X1111
        # In das_t 9 rows for sample_rate_multiplier_i change to 1
        # In array_t 3 rows for sample_rate_multiplier_i maintain 0
        with LogCapture() as log:
            fix_srm.process(self.ph5_object, 'master.ph5',
                            das_name='Das_t_1X1111')
            logmsg = ''.join([r.msg for r in log.records])
            self.assertEqual(logmsg, self.logmsg[0])
        ret = self.ph5_object.ph5_g_receivers.current_t_das.read()
        for row in ret:
            # check process_das change srm to 1
            self.assertEqual(row['sample_rate_multiplier_i'], 1)
        self.assertArraySRM('Array_t_001', 0, 3)

        # after process array_name=Array_t_001
        # In array_t 3 rows for sample_rate_multiplier_i change to 1
        with LogCapture() as log:
            fix_srm.process(self.ph5_object, 'master.ph5',
                            array_name='Array_t_001')
            logmsg = ''.join([r.msg for r in log.records])
            self.assertEqual(logmsg, self.logmsg[1])
        self.assertArraySRM('Array_t_001', 0, 3)

    def test_main_all_das(self):
        testargs = ['fix_srm', '-n', 'master.ph5', '--all_das']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                fix_srm.main()
                logmsg = ''.join([r.msg for r in log.records[3:]])
                self.assertEqual(logmsg, self.logmsg[0])
        self.ph5_object = ph5api.PH5(
            path=self.tmpdir, nickname='master.ph5', editmode=True)
        das = self.ph5_object.ph5_g_receivers.getdas_g('1X1111')
        self.ph5_object.ph5_g_receivers.setcurrent(das)
        ret = self.ph5_object.ph5_g_receivers.current_t_das.read()
        self.assertEqual(len(ret), 9)
        for row in ret:
            # check srm has been correct to 1
            self.assertEqual(row['sample_rate_multiplier_i'], 1)

    def test_main_D(self):
        testargs = ['fix_srm', '-n', 'master.ph5', '-D', '1X1111']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                fix_srm.main()
                logmsg = ''.join([r.msg for r in log.records[3:]])
                self.assertEqual(logmsg, self.logmsg[0])
        self.ph5_object = ph5api.PH5(
            path=self.tmpdir, nickname='master.ph5', editmode=True)
        das = self.ph5_object.ph5_g_receivers.getdas_g('1X1111')
        self.ph5_object.ph5_g_receivers.setcurrent(das)
        ret = self.ph5_object.ph5_g_receivers.current_t_das.read()
        self.assertEqual(len(ret), 9)
        for row in ret:
            # check srm has been correct to 1
            self.assertEqual(row['sample_rate_multiplier_i'], 1)

    def test_main_all_arrays(self):
        testargs = ['fix_srm', '-n', 'master.ph5', '--all_arrays']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                fix_srm.main()
                logmsg = ''.join([r.msg for r in log.records[3:]])
                self.assertEqual(logmsg, self.logmsg[1])
        self.ph5_object = ph5api.PH5(
            path=self.tmpdir, nickname='master.ph5', editmode=True)
        self.ph5_object.read_array_t('Array_t_001')
        self.assertArraySRM('Array_t_001', 1, 3)


if __name__ == "__main__":
    unittest.main()
