import os
import shutil
import unittest
import tempfile


class TempDirTestCase(unittest.TestCase):

    def setUp(self):
        """
        create tmpdir
        """
        self.home = os.getcwd()
        self.tmpdir = tempfile.mkdtemp() + "/"
        os.chdir(self.tmpdir)

    def tearDown(self):
        if self._resultForDoCleanups.wasSuccessful():
            try:
                shutil.rmtree(self.tmpdir)
            except Exception as e:
                print("Cannot remove %s due to the error:%s" %
                      (self.tmpdir, str(e)))
        else:
            errmsg = "%s has FAILED. Inspect files created in %s." \
                % (self._testMethodName, self.tmpdir)
            print(errmsg)

        os.chdir(self.home)
