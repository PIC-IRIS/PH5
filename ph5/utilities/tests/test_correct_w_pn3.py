'''
Tests for correct_w_pn3
'''
import os
import sys
import unittest
import logging
import time
import shutil

from mock import patch
from testfixtures import LogCapture, OutputCapture

from ph5.utilities import correct_w_pn3, nuke_table, kef2ph5
from ph5.core import ph5api, timedoy, ph5api_pn3
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


def change_table(path, type, repl_datafile):
    """
    remove table according to type in path/master.ph5 with data from
    repl_datafile
    """
    if type == 'array':
        addargs = ['-A', '001']
    elif type == 'index':
        addargs = ['-I']
    testargs = ['nuke_table', '-n', 'master.ph5', '-p', path] + addargs
    with patch.object(sys, 'argv', testargs):
        nuke_table.main()
    testargs = ['kef2ph5', '-n', 'master.ph5', '-p', path, '-k', repl_datafile]
    with patch.object(sys, 'argv', testargs):
        kef2ph5.main()


def count_arrays_entries(ph5obj):
    """
    count all entries of array tables in ph5obj
    """
    count = 0
    for aname in ph5obj.Array_t_names:
        ph5obj.read_array_t(aname)
        arraybyid = ph5obj.Array_t[aname]['byid']
        for station in arraybyid.values():
            for deployment in station.values():
                count += len(deployment)
    return count


class TestCheckPn3Issues(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestCheckPn3Issues, self).setUp()
        os.mkdir('pn3')
        os.mkdir('pn4')
        self.datapath = os.path.join(self.home,
                                     "ph5/test_data/ph5_correct_w_pn3")
        self.pn3path = os.path.join(self.tmpdir, 'pn3')
        shutil.copy(
            os.path.join(self.datapath, "pn3_master.ph5"),
            os.path.join(self.pn3path, "master.ph5")
        )

    def tearDown(self):
        self.pn3object.close()
        super(TestCheckPn3Issues, self).tearDown()

    def test_consistent_data(self):
        pn3path = os.path.join(self.home,
                               "ph5/test_data/ph5_correct_w_pn3")
        self.pn3object = ph5api_pn3.PH5(
            path=pn3path, nickname='pn3_master.ph5', editmode=False)
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            (pn3_das_t,
             pn3_index_t,
             pn3_array_t,
             rem_das,
             existing_minifile_dict) = correct_w_pn3.check_pn3_issues(
                self.pn3object)
            self.assertEqual(len(log.records), 0)
            self.assertEqual(len(pn3_das_t), 2)
            self.assertEqual(len(pn3_index_t), 33)
            self.assertEqual(len(pn3_array_t), 12)
            self.assertEqual(rem_das, [])
            self.assertEqual(existing_minifile_dict,
                             {'miniPH5_00001.ph5': ['1X1111', '3X500']})

    def test_inconsistent_data1(self):
        """
        array_test1.kef:
            deploy=pickup: ids 1111, chan 3
            delete das 3X500
            duplicated rows: id_s 1111, chan 2
        """
        change_table(self.pn3path, 'array',
                     os.path.join(self.datapath, 'arrays_test1.kef'))

        self.pn3object = ph5api_pn3.PH5(
            path=self.pn3path, nickname='master.ph5', editmode=False)
        errmsg = [
            "Due to coincided deploy and pickup times, 1/11  entries will be "
            "removed from array_t:\n[array, chan, deptime]: {[das_serial]: "
            "[rem/total], [das_serial]: [rem/total], ...},\n('Array_t_001', "
            "3, 'Wed Dec 31 17:00:00 1969'): {'1X1111': '1/11'}\n",
            'Das 1X1111 channel 2 deploy time Sat Jul 20 14:46:58 2019 '
            'duplicated in Array_t_001. User need to handle this manually',
            "Due to nonexistency in array_t 1/33 entries will be removed "
            "from index_t for the following das:\n['3X500']",
            "Compare Das_g against the filtered list of index_t and array_t, "
            "the following Das will be removed from Das data:\n ['3X500']",
            "The following minifiles are missing:\n['miniPH5_00001.ph5']"
        ]
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            (pn3_das_t,
             pn3_index_t,
             pn3_array_t,
             rem_das,
             existing_minifile_dict) = correct_w_pn3.check_pn3_issues(
                self.pn3object)
            self.assertEqual(len(log.records), 5)
            for i in range(len(log.records)):
                self.assertEqual(log.records[i].msg, errmsg[i])
            self.assertEqual(len(pn3_das_t), 0)  # since no minifile
            self.assertEqual(len(pn3_index_t), 27)
            self.assertEqual(len(pn3_array_t), 10)
            self.assertEqual(rem_das, ['3X500'])
            self.assertEqual(existing_minifile_dict, {})

    def test_inconsistent_data3(self):
        """
        index_test.kef:
            remove row 12: das 3X500 channel=3
            row 10: change time from 2017 to 2019 for das 1X1111 channel 1
        """
        change_table(self.pn3path, 'index',
                     os.path.join(self.datapath, 'index_test.kef'))

        self.pn3object = ph5api_pn3.PH5(
            path=self.pn3path, nickname='master.ph5', editmode=False)

        errmsg = [
            "Due to nonexistency in index_t 3/12 entries will be removed from "
            "array_t:\nArray_t_001: remove 3 entries of das: ['3X500']\n",
            "Compare Das_g against the filtered list of index_t and array_t, "
            "the following Das will be removed from Das data:\n ['3X500']",
            "The following minifiles are missing:\n['miniPH5_00001.ph5']"
        ]
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            (pn3_das_t,
             pn3_index_t,
             pn3_array_t,
             rem_das,
             existing_minifile_dict) = correct_w_pn3.check_pn3_issues(
                self.pn3object)

            self.assertEqual(len(log.records), 3)
            for i in range(len(log.records)):
                self.assertEqual(log.records[i].msg, errmsg[i])
            self.assertEqual(len(pn3_das_t), 0)  # since no minifile
            self.assertEqual(len(pn3_index_t), 27)
            self.assertEqual(len(pn3_array_t), 9)
            self.assertEqual(rem_das, ['3X500'])
            self.assertEqual(existing_minifile_dict, {})


class TestCleanupPn4(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestCleanupPn4, self).setUp()
        os.mkdir('pn4')
        self.datapath = os.path.join(self.home,
                                     "ph5/test_data/ph5_correct_w_pn3")
        self.pn4path = os.path.join(self.tmpdir, 'pn4')
        shutil.copy(
            os.path.join(self.datapath, "pn4_master.ph5"),
            os.path.join(self.pn4path, "master.ph5")
        )
        self.pn4object = ph5api.PH5(path=self.pn4path, nickname='master.ph5',
                                    editmode=True)

    def tearDown(self):
        self.pn4object.close()
        super(TestCleanupPn4, self).tearDown()

    def test_cleanup_pn4(self):
        with OutputCapture():
            with LogCapture():
                correct_w_pn3.cleanup_pn4(self.pn4object, True)
        # close and reopen to update changes
        self.pn4object.close()
        self.pn4object = ph5api.PH5(path=self.pn4path, nickname='master.ph5')
        self.pn4object.read_array_t_names()
        self.assertEqual(self.pn4object.Array_t_names, [])
        self.pn4object.read_index_t()
        self.assertEqual(len(self.pn4object.Index_t['rows']), 0)
        self.pn4object.read_das_g_names()
        self.assertEqual(len(self.pn4object.Das_g_names), 0)


class TestMain(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestMain, self).setUp()
        os.mkdir('pn3')
        os.mkdir('pn4')
        self.datapath = os.path.join(self.home,
                                     "ph5/test_data/ph5_correct_w_pn3")
        self.pn3path = os.path.join(self.tmpdir, 'pn3')
        self.pn4path = os.path.join(self.tmpdir, 'pn4')
        shutil.copy(
            os.path.join(self.datapath, "pn3_master.ph5"),
            os.path.join(self.pn3path, "master.ph5")
        )
        shutil.copy(
            os.path.join(self.datapath, "miniPH5_00001.ph5"),
            os.path.join(self.pn3path, "miniPH5_00001.ph5")
        )
        shutil.copy(
            os.path.join(self.datapath, "pn4_master.ph5"),
            os.path.join(self.pn4path, "master.ph5")
        )

    def tearDown(self):
        self.pn4object.close()
        super(TestMain, self).tearDown()

    def test_consistent_data(self):
        addInfoPath = os.path.join(self.datapath, 'addInfo.txt')
        testargs = ['correctwpn3', '--pn3', self.pn3path,
                    '--pn4', self.pn4path, '-a', addInfoPath, '-S']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                correct_w_pn3.main()
        tdoy = timedoy.TimeDOY(epoch=time.time())
        tt = "{0:04d}{1:03d}".format(tdoy.dtobject.year, tdoy.dtobject.day)
        index_backup = "Index_t_{0}_backup_from_pn3.kef".format(tt)
        msg = [
            'Opened ph5 file %s in read only mode.'
            % os.path.join(self.pn3path, 'master.ph5'),
            "Read /Experiment_g/Sorts_g/Array_t_001 (Table(12,)) ''",
            "Read /Experiment_g/Receivers_g/Index_t (Table(33,)) ''",
            "Read /Experiment_g/Receivers_g/Das_g_1X1111/Das_t (Table(27,))"
            " ''",
            "Read /Experiment_g/Receivers_g/Das_g_3X500/Das_t (Table(6,)) ''",
            "Read /Experiment_g/Receivers_g/Index_t (Table(33,)) ''",
            'Writing table backup: %s.'
            % os.path.join(self.tmpdir, index_backup),
            'Opened ph5 file %s in append edit mode.'
            % os.path.join(self.pn4path, 'master.ph5'),
            "Remove the following array_t from pn4: ['Array_t_001']",
            'Remove Index_t from pn4',
            "Remove Das_g external links from pn4: ['1X1111', '3X500']",
            'Preparing minifile: miniPH5_00001.ph5',
            'Opened ph5 file %s in append edit mode.'
            % os.path.join(self.pn4path, 'miniPH5_00001.ph5'),
            "External link to miniPH5_00001.ph5 is created for the following "
            "das: ['1X1111', '3X500']",
            'FINISH correcting pn4 data using info from pn3.'
        ]
        for i in range(len(log.records)):
            self.assertEqual(log.records[i].msg, msg[i])
        self.pn4object = ph5api.PH5(path=self.pn4path, nickname='master.ph5')
        self.pn4object.read_array_t_names()
        self.assertEqual(self.pn4object.Array_t_names, ['Array_t_001'])
        for aname in self.pn4object.Array_t_names:
            self.pn4object.read_array_t(aname)
            arraybyid = self.pn4object.Array_t[aname]['byid']
            for station in arraybyid.values():
                for deployment in station.values():
                    for e in deployment:
                        self.assertEqual(e['sensor/model_s'], 'L28')
                        self.assertEqual(e['sensor/manufacturer_s'], 'Sercel')
                        self.assertEqual(e['das/model_s'], 'rt125')
        self.pn4object.read_index_t()
        self.assertEqual(len(self.pn4object.Index_t['rows']), 33)
        self.pn4object.read_das_g_names()
        self.assertEqual(len(self.pn4object.Das_g_names), 2)

    def test_inconsistent_data1(self):
        """
        array_test1.kef:
            deploy=pickup: ids 1111, chan 3
            delete das 3X500
            duplicated rows: id_s 1111, chan 2
        """
        change_table(self.pn3path, 'array',
                     os.path.join(self.datapath, 'arrays_test1.kef'))

        testargs = ['correctwpn3', '--pn3', self.pn3path,
                    '--pn4', self.pn4path, '-S']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                correct_w_pn3.main()

        self.assertEqual(len(log.records), 20)
        self.assertEqual(
            log.records[-2].msg,
            "External link is not created for the following das, "
            "Use tool 'create_ext' when metadata is found: ['3X500']"
        )
        # not test other log mesg because they are similar to
        # TestCheckPn3Issues.test_inconsistent_data1()'s
        self.pn4object = ph5api.PH5(path=self.pn4path, nickname='master.ph5')
        self.pn4object.read_array_t_names()
        self.assertEqual(self.pn4object.Array_t_names, ['Array_t_001'])
        self.assertEqual(count_arrays_entries(self.pn4object), 10)
        self.pn4object.read_index_t()
        self.assertEqual(len(self.pn4object.Index_t['rows']), 27)
        self.pn4object.read_das_g_names()
        self.assertEqual(len(self.pn4object.Das_g_names), 1)

    def test_inconsistent_data2(self):
        """
        array_test2.kef:
            remove row 12: das 3X500 channel=3
            row 10: change time from 2017 to 2019 for das 1X1111 channel 1
        """
        change_table(self.pn3path, 'array',
                     os.path.join(self.datapath, 'arrays_test2.kef'))

        testargs = ['correctwpn3', '--pn3', self.pn3path,
                    '--pn4', self.pn4path, '-S']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.WARNING)
                correct_w_pn3.main()

        self.assertEqual(len(log.records), 1)
        self.assertEqual(
            log.records[0].msg,
            'Das 3X500 at channel 1 has no trace between time '
            '[1567269236, 1569681037].')

        self.pn4object = ph5api.PH5(path=self.pn4path, nickname='master.ph5')
        self.pn4object.read_array_t_names()
        self.assertEqual(self.pn4object.Array_t_names, ['Array_t_001'])
        self.assertEqual(count_arrays_entries(self.pn4object), 11)
        self.pn4object.read_index_t()
        self.assertEqual(len(self.pn4object.Index_t['rows']), 33)
        self.pn4object.read_das_g_names()
        self.assertEqual(len(self.pn4object.Das_g_names), 2)

    def test_inconsistent_data3(self):
        """
        index_test.kef:
            remove row 12: das 3X500 channel=3
            row 10: change time from 2017 to 2019 for das 1X1111 channel 1
        """
        change_table(self.pn3path, 'index',
                     os.path.join(self.datapath, 'index_test.kef'))

        testargs = ['correctwpn3', '--pn3', self.pn3path,
                    '--pn4', self.pn4path, '-S']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.WARNING)
                correct_w_pn3.main()

        # not test other log mesg because they are similar to
        # TestCheckPn3Issues.test_inconsistent_data3()'s
        self.assertEqual(len(log.records), 3)

        self.pn4object = ph5api.PH5(path=self.pn4path, nickname='master.ph5')
        self.pn4object.read_array_t_names()
        self.assertEqual(self.pn4object.Array_t_names, ['Array_t_001'])
        self.assertEqual(count_arrays_entries(self.pn4object), 9)
        self.pn4object.read_index_t()
        self.assertEqual(len(self.pn4object.Index_t['rows']), 27)
        self.pn4object.read_das_g_names()
        self.assertEqual(len(self.pn4object.Das_g_names), 1)


if __name__ == "__main__":
    unittest.main()
