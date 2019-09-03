'''
Tests for pforma_io
'''
import unittest
import sys
import os
import time
from ph5.utilities import pformagui
from ph5 import assertTable
from contextlib import contextmanager
from StringIO import StringIO
import shutil


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class TestPforma_io(unittest.TestCase):
    print("Test Pforma_io")

    def setUp(self):
        os.mkdir("tmp")
        self.rootdir = os.getcwd()
        self.testdir = self.rootdir + "/tmp"
        os.chdir(self.testdir)
        self.fio, self.cmds, self.info = pformagui.init_fio(
            self.rootdir + '/ph5/test_data/segd/rg16/RG16_list',
            self.testdir, '13N', 1)

    def tearDown(self):
        del self.fio
        os.chdir(self.rootdir)
        shutil.rmtree(self.testdir)

    def test_run_simple(self):
        """
        test run_simple_method
        """
        for family in self.cmds.keys():
            c_list = self.cmds[family]
            for i in range(len(c_list)):
                self.fio.run_simple(c_list, i, family)
            time.sleep(0.001)

        dirlist = next(os.walk(self.testdir))[1]
        rawfilepaths = []
        for d in dirlist:
            curdir = self.testdir + "/" + d + "/"
            files = os.listdir(curdir)
            for filename in files:
                if filename.endswith(".lst"):
                    f = open(curdir + filename)
                    rawfilepaths += f.readlines()
                    f.close()

        # compare with paths to raw files in the original list
        f = open(self.fio.infile)
        self.assertEqual(rawfilepaths, f.readlines())
        f.close()

    def test_unite(self):
        """
        test unite method
        """
        for family in self.cmds.keys():
            c_list = self.cmds[family]
            for i in range(len(c_list)):
                self.fio.run_simple(c_list, i, family)

        self.fio.unite('Sigma')

        # check array
        assertTable(
            ['--all_arrays'],
            self.rootdir + '/ph5/test_data/segd/rg16/all_arrays.kef',
            self.testdir+"/Sigma")
        # check das_t_9X9050
        assertTable(
            ['--Das_t', '9X9050'],
            self.rootdir + '/ph5/test_data/segd/rg16/das_t_9X9050.kef',
            self.testdir + "/Sigma")
        # check index_t
        assertTable(
            ['--Index_t'],
            self.rootdir + '/ph5/test_data/segd/rg16/index_t.kef',
            self.testdir+"/Sigma")
        # check M_index_t
        assertTable(
            ['--M_Index_t'],
            self.rootdir + '/ph5/test_data/segd/rg16/M_index_t.kef',
            self.testdir+"/Sigma")


if __name__ == "__main__":
    unittest.main()
