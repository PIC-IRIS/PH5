'''
Tests for sort_kefGen
'''
import os
import sys
import logging
import unittest

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.utilities import sort_kef_gen
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


def rem_currtime_ver_info(text):
    lines = text.split('\n')[1:]        # remove first line with version
    lines = [line for line in lines if 'time_stamp' not in line]
    return '\n'.join(lines)


class TestSortKefGen_main(TempDirTestCase, LogTestCase):

    def test_main(self):
        ph5_dir = os.path.join(self.home, "ph5/test_data/ph5_empty_das_t/")

        # create soft.kef
        # Related to issue #480, if check_srm_valid isn't skipped for empty
        # das_t, sort_kef_gen will issue an error
        testargs = ['sort_kef_gen', '-n', 'master', '-p', ph5_dir, '-a']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.WARNING)
                with OutputCapture() as out:
                    sort_kef_gen.main()
                    output = out.captured.strip()
                self.assertEqual(len(log.records), 1)
                self.assertEqual(
                    log.records[0].msg,
                    "Table Das_t_1X1111 is empty. "
                    "Use nuke_table > 2019.037 to remove the table"
                )
        output = rem_currtime_ver_info(output)

        # compare with recreated sort_test_delete_das.kef
        with open(os.path.join(
                self.home,
                'ph5/test_data/ph5_empty_das_t/sort_test_delete_das.kef'),
                  'r') as content_file:
            content = content_file.read().strip()
        content = rem_currtime_ver_info(content)
        self.assertEqual(output, content)


if __name__ == "__main__":
    unittest.main()
