from ph5 import logger, ch
from StringIO import StringIO
import logging
import unittest
import os
import shutil
import tempfile

newch = None


class LogTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # enable propagating to higher loggers
        logger.propagate = 1
        # disable writing log to console
        logger.removeHandler(ch)
        # add StringIO handler to prevent message "No handlers could be found"
        log = StringIO()
        newch = logging.StreamHandler(log)
        logger.addHandler(newch)

    @classmethod
    def tearDownClass(cls):
        # disable propagating to higher loggers
        logger.propagate = 0
        # revert logger handler
        logger.removeHandler(newch)
        logger.addHandler(ch)


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
