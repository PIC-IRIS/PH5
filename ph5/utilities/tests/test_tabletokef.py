"""
unit tests for tabletokef
"""
import logging
import unittest
from ph5.utilities import tabletokef
from ph5.core import ph5api
import tables
import sys
import os
import stat
from shutil import copyfile
from mock import patch
from StringIO import StringIO
from contextlib import contextmanager


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

class TestTable2Kef(unittest.TestCase):

    def setUp(self):
        """
        setup for tests
        """
        self.T2K = tabletokef.Tabletokef()
        self.T2K.PATH = 'ph5/test_data/ph5'
        self.T2K.PH5 = 'master.ph5'
        self.T2K.initialize_ph5()

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
        print("test_get_args")
        # no nick name
        testargs = ['tabletokef']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                self.T2K.get_args()

        # no table type selected
        testargs = ['tabletokef', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            self.assertRaises(tabletokef.TabletokefError, self.T2K.get_args)

        # wrong format offset
        testargs = ['tabletokef', '-n', 'master.ph5', '-O', '1']
        with patch.object(sys, 'argv', testargs):
            self.assertRaises(tabletokef.TabletokefError, self.T2K.get_args)

        # test param: Experiment_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5','-E']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertEqual('master.ph5', self.T2K.PH5)
        self.assertEqual('ph5', self.T2K.PATH)
        self.assertEqual("Experiment_t", self.T2K.table_type)

        # test param: Sort_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5', '-S']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertEqual("Sort_t", self.T2K.table_type)

        # test param: Offset_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5', '-O', '1_2']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertEqual("Offset_t", self.T2K.table_type)
        self.assertEqual([1, 2], self.T2K.ARG)

        # test param: Event_t_
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5',
                    '-V', '1']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertEqual("Event_t", self.T2K.table_type)
        self.assertEqual(1, self.T2K.ARG)

        # test param: Array_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5', '-A', '1']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertEqual("Array_t", self.T2K.table_type)
        self.assertEqual(1, self.T2K.ARG)
   
        # test param: all_arrays
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5',
                    '--all_arrays']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertEqual("All_Array_t", self.T2K.table_type)

        # test param: Response_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5', '-R']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertEqual("Response_t", self.T2K.table_type)

        # test param: Report_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5', '-P']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertEqual("Report_t", self.T2K.table_type)

        # test param: Receiver_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5', '-C']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertEqual("Receiver_t", self.T2K.table_type)

        # test param: Index_t and ouput file
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5', '-I']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertTrue("Index_t", self.T2K.table_type)

        # test param: M_Index_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5', '-M']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertEqual("Map_Index_t", self.T2K.table_type)

        # test param: Das_t_
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5', '-D', '5553']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertEqual("Das_t", self.T2K.table_type)
        self.assertEqual('5553', self.T2K.ARG)

        # test param: Time_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5', '-T', 
                    '-k', 'test.kef']
        with patch.object(sys, 'argv', testargs):
            self.T2K.get_args()
        self.assertEqual(self.T2K.table_type, "Time_t")
        self.assertIsInstance(self.T2K.OFILE, file)
        self.assertEqual(self.T2K.OFILE.name, 'test.kef')
        self.assertEqual(self.T2K.OFILE.closed, False)

    def test_initialize_ph5_close(self):
        """
        test initialize_ph5 and close method
        """

        # check if setUp has initialize_ph5 correctly
        self.assertIsInstance(self.T2K.EX.ph5, tables.File)

        # check close
        self.T2K.close_ph5()
        self.assertEqual(self.T2K.EX.ph5, None)

        # check initialize_ph5 wrong path
        self.T2K.PATH = 'ph5/test_data/ph'
        self.assertRaises(OSError, self.T2K.initialize_ph5)

        # check initialize_ph5 right path
        self.T2K.PATH = 'ph5/test_data/ph5'
        self.T2K.initialize_ph5()
        self.assertEqual(self.T2K.EX.ph5.filename,
                         'ph5/test_data/ph5/master.ph5')

    def test_set_EX(self):
        """
        test set_EX method
        """
        EX = "EX"
        self.T2K.set_EX(EX)
        self.assertEqual(EX, self.T2K.EX)

    def test_read_experiment_table(self):
        """
        test read_experiment_table method
        """
        self.T2K.read_experiment_table()
        self.assertEqual(1, len(self.T2K.EXPERIMENT_T.rows))

    def test_read_time_table(self):
        """
        test read_time_table method
        """
        self.T2K.read_time_table()
        self.assertEqual(1, len(self.T2K.TIME_T.rows))

    def test_read_report_table(self):
        """
        test read_report_table method
        """
        self.T2K.read_report_table()
        # there is no report_t in /ph5/test_data/ph5/master.ph5
        self.assertEqual(0, len(self.T2K.REPORT_T.rows))

    def test_read_sort_table(self):
        """
        test read_sort_table method
        """
        self.T2K.read_sort_table()
        self.assertEqual(14, len(self.T2K.SORT_T.rows))

    def test_read_response_table(self):
        """
        test read_response_table method
        """
        self.T2K.read_response_table()
        self.assertEqual(7, len(self.T2K.RESPONSE_T.rows))

    def test_read_receiver_table(self):
        """
        test read_receiver_table method
        """
        self.T2K.read_receiver_table()
        self.assertEqual(4, len(self.T2K.RECEIVER_T.rows))

    def test_read_index_table(self):
        """
        test read_index_table method
        """
        self.T2K.read_index_table()
        self.assertEqual(11, len(self.T2K.INDEX_T.rows))

    def test_read_m_index_table(self):
        """
        test read_m_index_table method
        """
        self.T2K.read_m_index_table()
        self.assertEqual(6, len(self.T2K.M_INDEX_T.rows))

    def test_read_all_event_table(self):
        """
        test read_all_event_table method
        """
        self.T2K.read_all_event_table()
        self.assertEqual(['Event_t_001'], self.T2K.EVENT_T.keys())

    def test_read_event_table(self):
        """
        test read_event_table method
        """
        # existing event_t_: 1
        self.T2K.read_event_table(1)
        self.assertEqual(['Event_t_001'], self.T2K.EVENT_T.keys())
        # non existing event_t_: 2
        self.assertRaises(
            tabletokef.TabletokefError, self.T2K.read_event_table, 2)

    def test_read_sort_arrays(self):
        """
        test read_sort_table method
        """
        self.T2K.read_sort_table()
        self.T2K.read_sort_arrays()
        self.assertEqual(
            ['Array_t_001', 'Array_t_002', 'Array_t_003', 'Array_t_004',
             'Array_t_008', 'Array_t_009'], sorted(self.T2K.ARRAY_T.keys()))

    def test_read_offset_table(self):
        """
        test read_offset_table method
        """
        self.T2K.read_offset_table([3, 1])
        self.assertEqual(['Offset_t_003_001'], self.T2K.OFFSET_T.keys())

        self.assertRaises(
            tabletokef.TabletokefError, self.T2K.read_offset_table, [1, 3])

    def test_read_tables(self):
        """
        test read_tables method
        """
        # Experiment_t
        ret = self.T2K.read_tables("Experiment_t")
        self.assertEqual(1, len(ret.rows))

        # Sort_t
        ret = self.T2K.read_tables("Sort_t")
        self.assertEqual(14, len(ret.rows))

        # Index_t
        ret = self.T2K.read_tables("Index_t")
        self.assertEqual(11, len(ret.rows))

        # Map_Index_t
        ret = self.T2K.read_tables("Map_Index_t")
        self.assertEqual(6, len(ret.rows))

        # Time_t
        ret = self.T2K.read_tables("Time_t")
        self.assertEqual(1, len(ret.rows))

        # Response_t
        ret = self.T2K.read_tables("Response_t")
        self.assertEqual(7, len(ret.rows))

        # Report_t
        ret = self.T2K.read_tables("Report_t")
        self.assertEqual(0, len(ret.rows))

        # Receiver_t
        ret = self.T2K.read_tables("Receiver_t")
        self.assertEqual(4, len(ret.rows))

        # Event_t: 1
        ret = self.T2K.read_tables("Event_t", 1)
        self.assertEqual(['Event_t_001'], ret.keys())

        # Non exist Event_t: 2
        self.assertRaises(
            tabletokef.TabletokefError,
            self.T2K.read_tables, "Event_t", 2)

        # All_Event_t
        ret = self.T2K.read_tables("All_Event_t")
        self.assertEqual(['Event_t_001'], ret.keys())

        ret = self.T2K.read_tables("Sort_t")
        self.assertEqual(14, len(ret.rows))

        # Array_t: 1
        ret = self.T2K.read_tables("Array_t", 1)
        self.assertEqual(3, len(ret.rows))

        # Non exist Array_t: 5
        self.assertRaises(
            tabletokef.TabletokefError,
            self.T2K.read_tables, "Array_t", 5)

        # All_Array_t
        ret = self.T2K.read_tables("All_Array_t")
        self.assertEqual(
            ['Array_t_001', 'Array_t_002', 'Array_t_003', 'Array_t_004',
             'Array_t_008', 'Array_t_009'], sorted(ret.keys()))

        # Offset_t: 3_1
        ret = self.T2K.read_tables("Offset_t", '3_1')
        self.assertEqual(['Offset_t_003_001'], ret.keys())

        # Non exist Offset_t: 1_3
        self.assertRaises(
            tabletokef.TabletokefError,
            self.T2K.read_tables, "Offset_t", '1_3')

        # All_Offset_t
        ph5 = ph5api.PH5(path='ph5/test_data/ph5',
                         nickname='master.ph5')
        #self.T2K.set_EX(ph5)
        ret = self.T2K.read_tables("All_Offset_t")
        self.assertEqual(6, len(ret.keys()))

    def test_table_print(self):
        """
        test table_print method
        """
        self.T2K.read_sort_table()
        self.T2K.read_sort_arrays()
        content_file = open('test.kef', 'w')
        self.T2K.table_print("/Experiment_g/Sorts_g/Array_t_001",
                          self.T2K.ARRAY_T['Array_t_001'], content_file)
        with open('test.kef', 'r') as content_file:
            ret_content = content_file.readlines()[3:]
        
        with open("ph5/test_data/ph5/array_t_1.kef") as array_t_file:
            array_t_content = array_t_file.readlines()[3:]
        self.assertEqual(array_t_content, ret_content)
        os.remove('test.kef')
        
    def test_main(self):
        """
        test main method
        """
        # no nick name
        testargs = ['tabletokef']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                tabletokef.main()

        # wrong path
        testargs = ['tabletokef', '-n', 'master.ph5' '-p', 'tpath']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                tabletokef.main()

        # no table type selected
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue().strip()
        self.assertEqual('', output)
        
        # wrong format offset
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                     '-O', '1']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue().strip()
        self.assertEqual('', output)

        # test param: Experiment_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-E']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertIn('/Experiment_g/Experiment_t', output)

        # test param: Sort_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-S']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertIn('/Experiment_g/Sorts_g/Sort_t', output)

        # test param: Offset_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-O', '3_1']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertIn('/Experiment_g/Sorts_g/Offset_t_003_001', output)
        # test param: Offset_t wrong arg
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-O', '1_3']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertEqual('', output)

        # test param: Event_t_
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-V', '1']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertIn('/Experiment_g/Sorts_g/Event_t_001', output)
        # test param: Event_t_ wrong arg
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-V', '2']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertEqual('', output)

         # test param: Array_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-A', '1']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertIn('Table row 3\n/Experiment_g/Sorts_g/Array_t_001', output)

        # test param: all_arrays
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '--all_arrays']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertIn('Table row 3\n/Experiment_g/Sorts_g/Array_t_001', output)
        self.assertIn('Table row 1\n/Experiment_g/Sorts_g/Array_t_002', output)
        self.assertIn('Table row 1\n/Experiment_g/Sorts_g/Array_t_003', output)
        self.assertIn('Table row 1\n/Experiment_g/Sorts_g/Array_t_004', output)
        self.assertIn('Table row 3\n/Experiment_g/Sorts_g/Array_t_008', output)
        self.assertIn('Table row 1\n/Experiment_g/Sorts_g/Array_t_009', output)

        # test param: Response_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-R']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertIn('Table row 7\n/Experiment_g/Responses_g/Response_t',
                      output)

        # test param: Report_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-P']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertEqual(5, len(output.split("\n")))  # no report, only header

        # test param: Receiver_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-C']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertIn('Table row 4\n/Experiment_g/Receivers_g/Receiver_t',
                      output)

        # test param:Index_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-I']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertIn('Table row 11\n/Experiment_g/Receivers_g/Index_t',
                      output)

        # test param: M_Index_t
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-M']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertIn('Table row 6\n/Experiment_g/Maps_g/Index_t',
                      output)

        # test param: Das_t_
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-D', '5553']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertIn('Table row 3\n/Experiment_g/Receivers_g/Das_g_5553/Das_t',
                      output)

        # test param: Das_t_ wrong arg
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-D', 'xxxx']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertEqual('', output)

        # test param: Time_t and output file
        testargs = ['tabletokef', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5', '-T', 
                    '-k', 'test.kef']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()
        self.assertEqual('', output)
        with open('test.kef', 'r') as content_file:
            content = content_file.read().strip()
        self.assertIn('/Experiment_g/Receivers_g/Time_t', content)
        content_file.close()
        os.remove('test.kef')

    def tearDown(self):
        self.T2K.close_ph5()

if __name__ == "__main__":
    unittest.main()
