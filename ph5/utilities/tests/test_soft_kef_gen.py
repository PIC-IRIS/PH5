'''
Tests for sort_kefGen
'''
import os
import sys
import unittest
import logging
from StringIO import StringIO

from mock import patch
from testfixtures import OutputCapture

from ph5.utilities import segd2ph5, nuke_table, sort_kef_gen
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase,\
    initialize_ex


def rem_currtime_ver_info(text):
    lines = text.split('\n')[1:]        # remove first line with version
    lines = [l for l in lines if 'time_stamp' not in l]
    return '\n'.join(lines)

class TestSortKefGen_main(TempDirTestCase, LogTestCase):

    def test_main(self):
        # add fcnt data of the same das in the same array but with different
        # deploytime
        segd_dir = os.path.join(self.home, "ph5/test_data/segd/fairfield/")
        # create list file
        list_file = open('fcnt_list', "w")
        list_file.write(os.path.join(segd_dir, '3ch.fcnt') + '\n')
        list_file.write(os.path.join(segd_dir, '1111.0.0.fcnt'))
        list_file.close()

        # add segD to ph5
        testargs = ['segdtoph5', '-n', 'master', '-f', 'fcnt_list']
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        # delete das 1X1111 from ph5
        testargs = ['delete_table', '-n', 'master', '-D', '1X1111']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                f = StringIO('y')
                sys.stdin = f
                nuke_table.main()
                f.close()

        # create soft.kef
        # Related to issue #480, if check_srm_valid isn't skipped for empty
        # das_t, sort_kef_gen will issue an error
        testargs = ['sort_kef_gen', '-n', 'master', '-a']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                sort_kef_gen.main()
                output = out.captured.strip()
        output = rem_currtime_ver_info(output)

        # compare with recreated sort_test_delete_das.kef
        with open(os.path.join(
                self.home,'ph5/test_data/metadata/sort_test_delete_das.kef'),
                  'r') as content_file:
            content = content_file.read().strip()
        content = rem_currtime_ver_info(content)
        self.assertEqual(output, content)


if __name__ == "__main__":
    unittest.main()
