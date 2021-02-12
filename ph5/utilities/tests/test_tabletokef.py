'''
Tests for tabletokef
'''
import os
import sys
import unittest
import logging

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.utilities import tabletokef
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


class TestTabletokef_SRM(TempDirTestCase, LogTestCase):

    def assert_main_error(self, testargs, tablename, srm_txt):
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                tabletokef.main()
                self.assertEqual(
                    log.records[0].msg,
                    ('%s has sample_rate_multiplier_i %s. '
                     'Please run fix_srm to fix sample_rate_multiplier_i '
                     'for PH5 data.' % (tablename, srm_txt)))

    def assert_main(self, testargs, tablepath, row_total, srm_total):
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                tabletokef.main()
                output = out.captured
        self.assertEqual(output.count(tablepath), row_total)
        self.assertEqual(output.count('sample_rate_multiplier_i'), srm_total)

    def test_main(self):
        # --------------- sample_rate_multiplier_i=0 -----------------
        srm0path = 'ph5/test_data/ph5/sampleratemultiplier0/array_das'
        ph5path = os.path.join(self.home, srm0path)
        testargs1 = ['tabletokef', '-n', 'master.ph5', '-p', ph5path]

        # Array_t, check srm and got error
        testargs2 = ['-A', '1']
        self.assert_main_error(testargs1 + testargs2,
                               'Array_t_001', 'with value 0')
        # Array_t, not check srm
        testargs2 += ['-i']
        self.assert_main(testargs1 + testargs2,
                         '/Experiment_g/Sorts_g/Array_t_001',
                         row_total=3, srm_total=3)
        # Das_t, check srm and got error
        testargs2 = ['-D', '1X1111']
        self.assert_main_error(testargs1 + testargs2,
                               'Das_t_1X1111', 'with value 0')
        # Array_t, not check srm
        testargs2 += ['-i']
        self.assert_main(testargs1 + testargs2,
                         '/Experiment_g/Receivers_g/Das_g_1X1111/Das_t',
                         row_total=9, srm_total=9)

        # ------------ sample_rate_multiplier_i missing --------------
        nosrmpath = 'ph5/test_data/ph5_no_srm/array_das'
        ph5path = os.path.join(self.home, nosrmpath)
        testargs1 = ['tabletokef', '-n', 'master.ph5', '-p', ph5path]

        # Array_t, check srm and got error
        testargs2 = ['-A', '1']
        self.assert_main_error(testargs1 + testargs2,
                               'Array_t_001', 'missing')
        # Array_t, not check srm
        testargs2 += ['-i']
        self.assert_main(testargs1 + testargs2,
                         '/Experiment_g/Sorts_g/Array_t_001',
                         row_total=3, srm_total=0)
        # Das_t, check srm and got error
        testargs2 = ['-D', '1X1111']
        self.assert_main_error(testargs1 + testargs2,
                               'Das_t_1X1111', 'missing')
        # Array_t, not check srm
        testargs2 += ['-i']
        self.assert_main(testargs1 + testargs2,
                         '/Experiment_g/Receivers_g/Das_g_1X1111/Das_t',
                         row_total=9, srm_total=0)


if __name__ == "__main__":
    unittest.main()
