'''
Tests for create_ext
'''
import os
import sys
import unittest
import logging

from mock import patch
from testfixtures import LogCapture

from ph5.utilities import csvtokef
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


class TestCSVToKef(TempDirTestCase, LogTestCase):

    def test_utf8(self):
        csv_utf8 = os.path.join(self.home,
                                'ph5/test_data/csv/array.utf8.csv')
        testargs = ['csvtokef', '-f', csv_utf8, '-o', 'array.kef']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                csvtokef.main()
                self.assertEqual(
                    "Wrote 84 records to 'array.kef'.",
                    log.records[0].msg)

    def test_utf8_bom(self):
        csv_utf8_bom = os.path.join(self.home,
                                'ph5/test_data/csv/array.utf8bom.csv')
        testargs = ['csvtokef', '-f', csv_utf8_bom, '-o', 'array.kef']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                csvtokef.main()
                self.assertEqual(
                    "Wrote 84 records to 'array.kef'.",
                    log.records[0].msg)


if __name__ == "__main__":
    unittest.main()
