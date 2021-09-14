'''
Tests for unsimpleton
'''
import os
import sys
import unittest

from mock import patch
from testfixtures import OutputCapture

from ph5.utilities import unsimpleton
from ph5.core.tests.test_base import TempDirTestCase


class TestUnsimpleton_main(TempDirTestCase):
    def test_main(self):
        # add fcnt data of the same das in the same array but with different
        # deploytime
        fcnt_dir = os.path.join(self.home, "ph5/test_data/segd/fairfield/")
        # create list file
        list_file = open('fcnt_list', "w")
        fcnt_fileList = os.listdir(fcnt_dir)
        s = ""
        for f in fcnt_fileList:
            if f.endswith(".fcnt") and f.startswith("1111"):
                s += fcnt_dir + f + "\n"
        list_file.write(s)
        list_file.close()

        # run unsimpleton => 3 rg16 files created with appropriate names
        testargs = ['unsimpleton', '-f', 'fcnt_list', '-d', 'rg16data']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                unsimpleton.main()
        rg16_dir = os.path.join(self.tmpdir, "rg16data")
        rg16_fileList = sorted(os.listdir(rg16_dir))
        self.assertEqual(rg16_fileList, ['PIC_1_1111_4886.0.0.rg16',
                                         'PIC_1_1111_4892.0.0.rg16',
                                         'PIC_1_1111_5118.0.0.rg16'])


if __name__ == "__main__":
    unittest.main()
