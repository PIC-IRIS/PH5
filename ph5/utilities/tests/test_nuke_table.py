"""
unit tests for nuke_table
"""

import unittest
from ph5.utilities import nuke_table
import sys
import os
import stat
from shutil import copyfile
from mock import patch
from StringIO import StringIO


class TestNukeTable(unittest.TestCase):

    def setUp(self):
        """
        setup for tests
        """
        self.nukeT = nuke_table.NukeTable()

    def assertInListItem(self, txt, strlist):
        """
        return True if txt in any items of strlist
        raise AssertionError if txt not in any items of strlist
        """
        for s in strlist:
            if txt in s:
                return s
        raise AssertionError("%s not in any items of %s." % (txt, strlist))

    def test_get_args(self):
        """
        test get_args method
        """

        # no nick name
        testargs = ['nuke-table']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                self.nukeT.get_args()

        # no table type selected
        testargs = ['nuke-table', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            self.assertRaises(nuke_table.NukeTableError, self.nukeT.get_args)

        # wrong format offset
        testargs = ['nuke-table', '-n', 'master.ph5', '-O', '1']
        with patch.object(sys, 'argv', testargs):
            self.assertRaises(nuke_table.NukeTableError, self.nukeT.get_args)

        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5', '-N','-E']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertEqual('master.ph5', self.nukeT.PH5)
        self.assertEqual('ph5', self.nukeT.PATH)
        self.assertTrue(self.nukeT.NO_BACKUP)
        self.assertEqual("Experiment_t", self.nukeT.table_type)

        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5', '-S']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertEqual("Sort_t", self.nukeT.table_type)

        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5', '-O', '1_2']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertEqual("Offset_t", self.nukeT.table_type)
        self.assertEqual([1, 2], self.nukeT.ARG)

        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5',
                    '-V', '1']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertEqual("Event_t", self.nukeT.table_type)
        self.assertEqual(1, self.nukeT.ARG)

        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5', '-A', '1']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertEqual("Array_t", self.nukeT.table_type)
        self.assertEqual(1, self.nukeT.ARG)
    
        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5',
                    '--all_arrays']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertEqual("All_Array_t", self.nukeT.table_type)

        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5', '-R']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertEqual("Response_t", self.nukeT.table_type)

        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5', '-P']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertEqual("Report_t", self.nukeT.table_type)

        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5', '-C']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertEqual("Receiver_t", self.nukeT.table_type)

        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5', '-I']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertTrue("Index_t", self.nukeT.table_type)

        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5', '-M']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertEqual("Map_Index_t", self.nukeT.table_type)

        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5', '-D', '5553']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertEqual("Das_t", self.nukeT.table_type)
        self.assertEqual('5553', self.nukeT.ARG)

        # test param
        testargs = ['nuke-table', '-n', 'master.ph5', '-p', 'ph5', '-T']
        with patch.object(sys, 'argv', testargs):
            self.nukeT.get_args()
        self.assertEqual("Time_t", self.nukeT.table_type)

    def test_initialize_ph5(self):
        """
        test initialize_ph5 method
        """
        # test wrong path
        self.nukeT.PATH = 'ph5/test_data/ph'
        self.nukeT.PH5 = 'master.ph5'
        self.assertRaises(Exception, self.nukeT.initialize_ph5)
        # test right path
        self.nukeT.PATH = 'ph5/test_data/ph5'
        self.nukeT.initialize_ph5()
        self.assertEqual('ph5/test_data/ph5/master.ph5',
                         self.nukeT.EX.ph5.filename)
        self.assertEqual(self.nukeT.EX, self.nukeT.T2K.EX)

    def test_backup(self):
        """
        test backup method
        """
        self.nukeT.PATH = 'ph5/test_data/ph5'
        self.nukeT.PH5 = 'master.ph5'
        self.nukeT.initialize_ph5()
        self.nukeT.T2K.read_sort_arrays()
        outfile0_name = self.nukeT.backup(
            'Array_t_001',
            '/Experiment_g/Sorts_g/Array_t_001',
            self.nukeT.T2K.ARRAY_T['Array_t_001'])
        self.assertEqual('Array_t_001_2019001_00.kef', outfile0_name)
        # testing 2nd backups
        outfile1_name = self.nukeT.backup(
            'Array_t_001',
            '/Experiment_g/Sorts_g/Array_t_001',
            self.nukeT.T2K.ARRAY_T['Array_t_001'])
        self.assertEqual('Array_t_001_2019001_01.kef', outfile1_name)
        with open(outfile0_name, 'r') as ret_file:
            ret_content = ret_file.readlines()[3:]
        with open('ph5/test_data/ph5/array_t_1.kef', 'r') as dest_file:
            dest_content = dest_file.readlines()[3:]
        self.assertEqual(dest_content, ret_content)
        os.remove(outfile0_name)
        os.remove(outfile1_name)

        # no backup
        self.nukeT.NO_BACKUP = True
        outfile = self.nukeT.backup(
            'Array_t_001',
            '/Experiment_g/Sorts_g/Array_t_001',
            self.nukeT.T2K.ARRAY_T['Array_t_001'])
        self.assertEqual(None, outfile)
        self.nukeT.NO_BACKUP = False

        # read report_table which is empty
        self.nukeT.T2K.read_report_table()
        outfile = self.nukeT.backup(
            'Report_t', '/Experiment_g/Reports_g/Report_t',
            self.nukeT.T2K.REPORT_T)
        self.assertEqual(None, outfile)

        # test no write permission (os.access in nuke_table)
        currmode = os.stat('.').st_mode         # get current permission
        nowritemode = currmode & ~stat.S_IWUSR  # remove write permission
        os.chmod('.', nowritemode)              # set new permission
        self.assertRaises(nuke_table.NukeTableError, self.nukeT.backup,
                          'Array_t_001',
                          '/Experiment_g/Sorts_g/Array_t_001',
                          self.nukeT.T2K.ARRAY_T['Array_t_001'])
        os.chmod('.', currmode)                 # return original permission

    def _test_backupFiles(self, table_type_list, orglistdir):
        newlistdir = os.listdir('.')
        backupfiles = [f for f in newlistdir if f not in orglistdir]

        self.assertEqual(len(table_type_list), len(backupfiles))
        for table_type in table_type_list:
            backupfile = self.assertInListItem(table_type, backupfiles)
            backupfiles.remove(backupfile)
            os.remove(backupfile)

    def _test_doNuke(self, table_type_list, orglistdir, exist=True):
        if not exist:
            self.assertRaises(nuke_table.NukeTableError, self.nukeT.doNuke)
            return
        self.nukeT.doNuke()
        self._test_backupFiles(table_type_list, orglistdir)

    def _resetNukeT(self):
        # to update the table that has been nuked, need for the one that nee
        # to set value (not True/False)
        self.nukeT.EX.ph5close()
        self.nukeT.T2K.close()
        self.nukeT.initialize_ph5()

    def test_doNuke(self):
        """
        test doNuke method
        """
        # copy files: don't want to do this part in setup because this test
        # will delete tables in ph5, so when testing main, the tasks need to
        # be repeated
        copyfile('ph5/test_data/ph5/master.ph5', 'master.ph5')
        copyfile('ph5/test_data/ph5/miniPH5_00001.ph5', 'miniPH5_00001.ph5')
        self.nukeT.PATH = '.'
        self.nukeT.PH5 = 'master.ph5'
        self.nukeT.initialize_ph5()
        self.nukeT.T2K.PRINTOUT = True

        orglistdir = os.listdir('.')

        # nuke Experiment_t
        self.nukeT.table_type = "Experiment_t"
        self._test_doNuke(['Experiment_t'], orglistdir)
        self._test_doNuke([], orglistdir)

        # nuke Sort_t
        self.nukeT.table_type = "Sort_t"
        self._test_doNuke(['Sort_t'], orglistdir)
        self._test_doNuke([], orglistdir)

        # nuke Offset_t
        self.nukeT.table_type = "Offset_t"
        self.nukeT.ARG = [3, 1]
        self._test_doNuke(['Offset_t_003_001'], orglistdir)
        self._resetNukeT()
        self._test_doNuke(['Offset_t_003_001'], orglistdir, False)

        # nuke Offset_t not exist
        self.nukeT.ARG = [3, 2]
        self._test_doNuke(['Offset_t_003_002'], orglistdir, False)

        # cannot test OFFSET_TABLE[0]=0 or /Experiment_g/Sorts_g/Offset_t
        # because this is the old type of ph5, there is no test data for that

        # nuke Event_t_
        self.nukeT.table_type = "Event_t"
        self.nukeT.ARG = 1
        self._test_doNuke(['Event_t_001'], orglistdir)
        self._resetNukeT()
        self._test_doNuke(['Event_t_001'], orglistdir, False)

        # nuke Event_t_ not exist
        self.nukeT.ARG = 2
        self._test_doNuke(['Event_t_002'], orglistdir, False)

        # cannot test EVENT_TABLE=0 or /Experiment_g/Sorts_g/Event_t
        # because this is the old type of ph5, there is no test data for that

        # nuke Array_t_
        self.nukeT.table_type = "Array_t"
        self.nukeT.ARG = 1
        self._test_doNuke(['Array_t_001'], orglistdir)
        self._resetNukeT()
        self._test_doNuke(['Array_t_001'], orglistdir, False)

        # nuke Array_t_ not exist
        self.nukeT.ARG = 5
        self._test_doNuke(['Array_t_005'], orglistdir, False)

        # nuke ALL_ARRAYS
        
        # update deleted Array_t_001
        self._resetNukeT()
        self.nukeT.T2K.PRINTOUT = True

        self.nukeT.table_type = "All_Array_t"
        self._test_doNuke(['Array_t_002', 'Array_t_003', 'Array_t_004',
                           'Array_t_008', 'Array_t_009'], orglistdir)
        self._resetNukeT()
        self._test_doNuke([], orglistdir)
        #self.nukeT.ALL_ARRAYS = False
        #self.nukeT.ARRAY_TABLE = None  # reset for it is set when do all_arrays

        # nuke Time_t
        self.nukeT.table_type = "Time_t"
        self._test_doNuke(['Time_t'], orglistdir)
        self._test_doNuke([], orglistdir)

        # nuke Index_t
        self.nukeT.table_type = "Index_t"
        self._test_doNuke(['Index_t'], orglistdir)
        self._test_doNuke([], orglistdir)

        # nuke M_Index_t
        self.nukeT.table_type = "Map_Index_t"
        self._test_doNuke(['M_Index_t'], orglistdir)
        self._test_doNuke([], orglistdir)

        # nuke Receiver_t
        self.nukeT.table_type = "Receiver_t"
        self._test_doNuke(['Receiver_t'], orglistdir)
        self._test_doNuke([], orglistdir)
        self.nukeT.RECEIVER_TABLE = False

        # nuke Response_t
        self.nukeT.table_type = "Response_t"
        self._test_doNuke(['Response_t'], orglistdir)
        self._test_doNuke([], orglistdir)
        self.nukeT.RECEIVER_TABLE = False

        # nuke Report_t: report t not exist: no backup created
        self.nukeT.table_type = "Report_t"
        self._test_doNuke([], orglistdir)
        self.nukeT.REPORT_TABLE = False

        # nuke Das_t_
        self.nukeT.table_type = "Das_t"
        self.nukeT.ARG = '5553'
        f = StringIO('n')
        sys.stdin = f   # answer 'n' for question in doNuke()
        self._test_doNuke([], orglistdir)
        f.close()

        f = StringIO('y')
        sys.stdin = f   # answer 'y' for question in doNuke()
        self._test_doNuke(['Das_t_5553'], orglistdir)
        f.close()
        f = StringIO('y')
        sys.stdin = f   # answer 'y' for question in doNuke()
        self._test_doNuke([], orglistdir)
        f.close()

        # nuke Das_t not exist
        self.nukeT.ARG = 'xxxx'
        f = StringIO('y')
        sys.stdin = f   # answer 'y' for question in doNuke()
        self._test_doNuke([], orglistdir)
        f.close()

    def test_main(self):
        """
        test main method
        """
        copyfile('ph5/test_data/ph5/master.ph5', 'master.ph5')
        copyfile('ph5/test_data/ph5/miniPH5_00001.ph5', 'miniPH5_00001.ph5')
        orglistdir = os.listdir('.')
        # no nick name
        testargs = ['nuke-table']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                nuke_table.main()

        # wrong format offset
        testargs = ['nuke-table', '-n', 'master.ph5', '-O', '1']
        with patch.object(sys, 'argv', testargs):
            ret = nuke_table.main()
        self.assertEqual(1, ret)

        # nuke Experiment_t
        testargs = ['nuke-table', '-n', 'master.ph5', '-E']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles(['Experiment_t'], orglistdir)
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke Sort_t
        testargs = ['nuke-table', '-n', 'master.ph5', '-S']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles(['Sort_t'], orglistdir)
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke Offset_t
        testargs = ['nuke-table', '-n', 'master.ph5', '-O', '3_1']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles(['Offset_t_003_001'], orglistdir)
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke Event_t_
        testargs = ['nuke-table', '-n', 'master.ph5', '-V', '1']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles(['Event_t_001'], orglistdir)
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke Array_t
        testargs = ['nuke-table', '-n', 'master.ph5', '-A', '1']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles(['Array_t_001'], orglistdir)
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke Array_t no back up
        testargs = ['nuke-table', '-n', 'master.ph5', '-A', '2', '-N']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke all_arrays
        testargs = ['nuke-table', '-n', 'master.ph5', '--all_arrays']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles(['Array_t_003', 'Array_t_004',
                                'Array_t_008', 'Array_t_009'], orglistdir)
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke Time_t
        testargs = ['nuke-table', '-n', 'master.ph5', '-T']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles(['Time_t'], orglistdir)
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke Index_t
        testargs = ['nuke-table', '-n', 'master.ph5', '-I']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles(['Index_t'], orglistdir)
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke M_Index_t
        testargs = ['nuke-table', '-n', 'master.ph5', '-M']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles(['M_Index_t'], orglistdir)
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke Receiver_t
        testargs = ['nuke-table', '-n', 'master.ph5', '-C']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles(['Receiver_t'], orglistdir)
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke Response_t
        testargs = ['nuke-table', '-n', 'master.ph5', '-R']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles(['Response_t'], orglistdir)
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke Report_t: report t not exist: no backup created
        testargs = ['nuke-table', '-n', 'master.ph5', '-P']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        self._test_backupFiles([], orglistdir)

        # nuke Das_t_
        testargs = ['nuke-table', '-n', 'master.ph5', '-D', '5553']
        with patch.object(sys, 'argv', testargs):
            f = StringIO('n')
            sys.stdin = f   # answer 'n' for question in doNuke()
            nuke_table.main()
            f.close()
        self._test_backupFiles([], orglistdir)

        with patch.object(sys, 'argv', testargs):
            f = StringIO('y')
            sys.stdin = f   # answer 'y' for question in doNuke()
            nuke_table.main()
            f.close()
        self._test_backupFiles(['Das_t_5553'], orglistdir)

        # das not exist anymore
        with patch.object(sys, 'argv', testargs):
            f = StringIO('y')
            sys.stdin = f   # answer 'y' for question in doNuke()
            nuke_table.main()
            f.close()
        self._test_backupFiles([], orglistdir)

        # remove files:
        os.remove('master.ph5')
        os.remove('miniPH5_00001.ph5')

    def tearDown(self):
        """
        teardown for tests
        """
        try:
            os.remove('master.ph5')
            os.remove('miniPH5_00001.ph5')
            self.nukeT.close_ph5()
        except Exception:
            pass
        listdir = os.listdir('.')
        for f in listdir:
            if f.endswith('.kef'):
                os.remove(f)


if __name__ == "__main__":
    unittest.main()
