'''
Tests for metadatatoph5
'''
import os
import sys
import unittest

from mock import patch
from testfixtures import LogCapture

from ph5.utilities import segy2ph5
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


class TestSegytoPH5Main(TempDirTestCase, LogTestCase):

    def test_main_without_force(self):
        testargs = ['segytoph5', '-n', 'master.ph5', '-f',
                    os.path.join(
                        self.home,
                        'ph5/test_data/segy/GIAME14_006_18_1_0001.SGY')]
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                with self.assertRaises(SystemExit):
                    segy2ph5.main()
                self.assertEqual(
                    log.records[0].msg,
                    segy2ph5.DEPRECATION_WARNING
                )


if __name__ == "__main__":
    unittest.main()
