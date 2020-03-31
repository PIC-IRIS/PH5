import os
import shutil
import tempfile
import unittest
import logging
from StringIO import StringIO

from ph5 import logger
from ph5.core import experiment


def initialize_ex(nickname, path, editmode=False):
    ex = experiment.ExperimentGroup(nickname=nickname, currentpath=path)
    ex.ph5open(editmode)
    ex.initgroup()
    return ex


class LogTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # enable propagating to higher loggers
        logger.propagate = 1
        cls.handlers = [h for h in logger.handlers]
        # switch handler that send log to console
        # to StringIO handler to catch log's messages in test
        log = StringIO()
        new_handler = logging.StreamHandler(log)
        logger.handlers = [new_handler]

    @classmethod
    def tearDownClass(cls):
        # disable propagating to higher loggers
        logger.propagate = 0
        # put back the stream handler in ph5.__init__.logger
        logger.handlers = cls.handlers

    def tearDown(self):
        # clean up handlers in any ph5 files' loggers that have been used
        # but exclude logger from ph5/__init__.py to catch log's messages in
        # next test
        for k, v in logging.Logger.manager.loggerDict.items():
            if (not isinstance(v, logging.PlaceHolder)) and ('ph5.' in k):
                v.handlers = []
        super(LogTestCase, self).tearDown()


class TempDirTestCase(unittest.TestCase):

    def setUp(self):
        """
        create tmpdir
        """
        self.tmpdir = None
        self.home = None
        self.home = os.getcwd()
        self.tmpdir = tempfile.mkdtemp(
            dir=os.path.join(self.home, "ph5/test_data/"))
        os.chdir(self.tmpdir)
        self.addCleanup(os.chdir, self.home)
        super(TempDirTestCase, self).setUp()

    def tearDown(self):
        super(TempDirTestCase, self).tearDown()
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
