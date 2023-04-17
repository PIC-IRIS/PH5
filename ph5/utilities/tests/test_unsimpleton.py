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
    def test_main_fairfield(self):
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

    def test_main_smartsolo(self):
        # add segd data of the same das in the same array and station
        # but with different trace epoch
        ssolo_dir = os.path.join(
            self.home, "ph5/test_data/segd/messed_order/")
        # create list file
        list_file = open('ssolo_list', "w")
        ssolo_file_list = os.listdir(ssolo_dir)
        s = ""
        for f in ssolo_file_list:
            if f.endswith(".segd"):
                s += ssolo_dir + f + "\n"
        list_file.write(s)
        list_file.close()

        # run unsimpleton => 2 ssolo files created with appropriate names
        testargs = ['unsimpleton', '-f', 'ssolo_list', '-d', 'ssolodata']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                unsimpleton.main()
        new_ssolo_dir = os.path.join(self.tmpdir, "ssolodata")
        new_ssolo_list = sorted(os.listdir(new_ssolo_dir))

        self.assertEqual(new_ssolo_list,
                         ['SSolo_1_4_453005811_0_Z.segd',
                          'SSolo_1_4_453005811_1_Z.segd'])


if __name__ == "__main__":
    unittest.main()
