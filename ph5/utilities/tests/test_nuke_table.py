'''
Tests for nuke_table
'''
import os
import sys
import unittest
import logging
from shutil import copy
from StringIO import StringIO

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.utilities import nuke_table, initialize_ph5, tabletokef, kef2ph5
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase
from ph5.core import experiment


class TestTabletokef_SRM(TempDirTestCase, LogTestCase):

    def test_main(self):
        empty_das_path = os.path.join(self.home,
                                      'ph5/test_data/ph5_empty_das_t/')
        # prepare test file
        for f in os.listdir(empty_das_path):
            if f.endswith('.ph5'):
                copy(os.path.join(empty_das_path, f), self.tmpdir)

        testargs = ['nuke_table', '-n', 'master.ph5', '-D', '1X1111']
        # test with empty_das_t for the warning message
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.INFO)
                with OutputCapture() as out:
                    f = StringIO('y')
                    sys.stdin = f
                    nuke_table.main()
                    f.close()
                    out.compare(
                        "The following tables has entries related to das "
                        "1X1111: Array_t_001, Index_t.\n"
                        "To maintain consistency, those entries must be "
                        "removed along with removing the das.\n"
                        "Do you want to continue?(y/n)",
                    )
                    logrecs = log.records

        self.assertEqual(
            'Das_t for 1X1111 is empty which may result from deleting das '
            'using the old tool.',
            logrecs[2].msg
        )
        self.assertIn(
            "Writing table backup: %s" % os.path.join(self.tmpdir,
                                                      'Array_t_001'),
            logrecs[3].msg)
        self.assertIn(
            "Writing table backup: %s" % os.path.join(self.tmpdir, 'Index_t'),
            logrecs[4].msg)
        self.assertEqual(
            "Das 1X1111 and all entries related to it in and all entries "
            "related to it in Array_t_001, Index_t  have been removed from "
            "master file.\n"
            "To rollback this deletion you have to follow the steps:\n\t"
            "+ Recover das info in index_t, array_t from backup kef "
            "files. (If the das has been removed from the tables using other "
            "tool(s) users need to find another way to recover those tables "
            "before moving on to the next step. Please see PIC data group PH5 "
            "documentation on deleting and replacing tables if needed.)\n\t"
            "+ Use 'creare_ext' to add das back to master.\n\t"
            "+ If the das was nuked before with 'nuke_table' version less "
            "than 2021.336, you will need das' backup kef file created at "
            "that time to recover the das table.",
            logrecs[5].msg
        )

        # delete one more time to see warning Das_t not found
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.WARNING)
                nuke_table.main()
                self.assertEqual(len(log.records), 1)
                self.assertEqual(
                    'Das_t not found for 1X1111',
                    log.records[0].msg
                )


class TestLongArrayValue(TempDirTestCase, LogTestCase):
    def assert_array_list(self, ph5_path, array_list):
        ex = experiment.ExperimentGroup(ph5_path, 'master.ph5')
        ex.ph5open()
        ex.initgroup()
        self.assertListEqual(
            ex.ph5_g_sorts.names(),
            ['Array_t_2589373'],
            "array_list failed to match with %s" % array_list)
        ex.ph5close()

    def test_main(self):
        long_array_value_path = os.path.join(
            self.home, 'ph5/test_data/ph5_long_array_value')

        # prepare test file
        copy(os.path.join(long_array_value_path, 'master.ph5'), self.tmpdir)

        # check ph5 has array Array_t_2589373
        self.assert_array_list(long_array_value_path, ['Array_t_2589373'])

        testargs = ['nuke_table', '-n', 'master.ph5', '--all_arrays']
        # test to see if successfully delete array table with long value
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.INFO)
                nuke_table.main()
                self.assertEqual(log.records[3].msg,
                                 '2589373 It worked.')
        # check if Array_t_2589373 isn't in ph5 anymore
        self.assert_array_list(long_array_value_path, [])


class TestAllEventsFlags(TempDirTestCase, LogTestCase):

    def check_event_length(self, length):
        EX = experiment.ExperimentGroup(self.tmpdir, 'master.ph5')
        EX.ph5open(False)
        EX.initgroup()

        tabletokef.init_local()
        tabletokef.EX = EX

        tabletokef.read_all_event_table()
        self.assertEqual(len(tabletokef.EVENT_T), length)
        EX.ph5close()

    def test_main(self):
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()

        # add event table
        all_events_path = os.path.join(
            self.home,
            'ph5/test_data/metadata/delete_table/all_events.kef')
        testargs = ['kef2ph5', '-n', 'master.ph5', '-k', all_events_path]
        with patch.object(sys, 'argv', testargs):
            kef2ph5.main()
        # check there are 2 events
        self.check_event_length(2)

        # remove all events (FEATURE TO TEST)
        testargs = ['delete_table', '-n', 'master.ph5', '--all_events']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        # check there are no events
        self.check_event_length(0)


class TestAllOffsetsFlags(TempDirTestCase, LogTestCase):

    def check_offset_length(self, length):
        EX = experiment.ExperimentGroup(self.tmpdir, 'master.ph5')
        EX.ph5open(False)
        EX.initgroup()

        tabletokef.init_local()
        tabletokef.EX = EX

        tabletokef.read_all_offset_table()
        self.assertEqual(len(tabletokef.OFFSET_T), length)
        EX.ph5close()

    def test_main(self):
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()

        # add offset table
        all_offsets_path = os.path.join(
            self.home,
            'ph5/test_data/metadata/delete_table/all_offsets.kef')
        testargs = ['kef2ph5', '-n', 'master.ph5', '-k', all_offsets_path]
        with patch.object(sys, 'argv', testargs):
            kef2ph5.main()
        # check there are 12 offset
        self.check_offset_length(12)

        # remove all offset (FEATURE TO TEST)
        testargs = ['delete_table', '-n', 'master.ph5', '--all_offsets']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()
        # check there are no offset
        self.check_offset_length(0)


if __name__ == "__main__":
    unittest.main()
