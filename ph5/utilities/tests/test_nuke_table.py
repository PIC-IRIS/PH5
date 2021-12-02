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

from ph5.utilities import nuke_table
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


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
            logrecs[0].msg
        )
        self.assertIn(
            "Writing table backup: %s" % os.path.join(self.tmpdir,
                                                      'Array_t_001'),
            logrecs[1].msg)
        self.assertIn(
            "Writing table backup: %s" % os.path.join(self.tmpdir, 'Index_t'),
            logrecs[2].msg)
        self.assertEqual(
            "Das 1X1111 and all entries related to it in and all entries "
            "related to it in Array_t_001, Index_t  have been removed from "
            "master file.\nSteps to rollback:\n\t"
            "+ Recover das info in index_t, array_t from backup kef files. "
            "(If the das has been removed from the tables using other tool(s) "
            "users need to find another way to recover those tables before "
            "moving on to the next step.)\n\t"
            "+ Use 'creare_ext' to add das back to master.\n\t"
            "+ If the das was nuked before with old 'nuke_table' tool, "
            "you will need das backup kef file created at that time to "
            "recover the das table.",
            logrecs[3].msg
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


if __name__ == "__main__":
    unittest.main()
