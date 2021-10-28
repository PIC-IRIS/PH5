'''
Tests for dumpsegd
'''
import os
import sys
import unittest

from mock import patch
from testfixtures import OutputCapture

from ph5.utilities import dumpsegd
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


class TestDumpSEGD(TempDirTestCase, LogTestCase):
    def test_main(self):
        segdfile = os.path.join(
            self.home,
            'ph5/test_data/segd/smartsolo/'
            '453005513.2.2021.05.08.20.06.00.000.E.segd')
        segdheaderfile = segdfile + '.header'
        with open(segdheaderfile, 'r') as headerFile:
            header = headerFile.read().split()

        testargs = ['dumpsegd', segdfile]
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                dumpsegd.main()
                output = out.captured.split()
        # skip the filename lines
        self.assertEqual(output[2:], header[2:])


if __name__ == "__main__":
    unittest.main()
