import os
import shutil
import tempfile
import unittest
import logging
from StringIO import StringIO

from ph5 import logger, ch
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
        # disable writing log to console
        logger.removeHandler(ch)
        # add StringIO handler to prevent message "No handlers could be found"
        log = StringIO()
        cls.newch = logging.StreamHandler(log)
        logger.addHandler(cls.newch)

    @classmethod
    def tearDownClass(cls):
        # disable propagating to higher loggers
        logger.propagate = 0
        # revert logger handler
        logger.removeHandler(cls.newch)
        logger.addHandler(ch)

    def setUp(self):
        self.addCleanup(self.remove_file_loggers)
        super(LogTestCase, self).setUp()

    def find_all_file_loggers(self):
        file_logger_handlers = list()
        for k, v in logging.Logger.manager.loggerDict.items():
            if not isinstance(v, logging.PlaceHolder):
                for h in v.handlers:
                    if isinstance(h, logging.FileHandler):
                        file_logger_handlers.append((logging.getLogger(k), h))
        return file_logger_handlers

    def remove_file_loggers(self):
        for l, h in self.find_all_file_loggers():
            l.removeHandler(h)


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        """
        create tmpdir
        """
        # Save the number of errors the test runner has seen.
        self.prev_errors = (len(self._resultForDoCleanups.errors) +
                            len(self._resultForDoCleanups.failures))
        self.home = os.getcwd()
        self.tmpdir = tempfile.mkdtemp(
            dir=os.path.join(self.home, "ph5/test_data/"))
        os.chdir(self.tmpdir)
        self.addCleanup(os.chdir, self.home)
        super(TempDirTestCase, self).setUp()

    def tearDown(self):
        super(TempDirTestCase, self).tearDown()
        current_errors = (len(self._resultForDoCleanups.errors) +
                          len(self._resultForDoCleanups.failures))
        if current_errors == self.prev_errors:
            try:
                shutil.rmtree(self.tmpdir)
            except Exception as e:
                print("Cannot remove {} due to the error:{}".format(
                    self.tmpdir, e))
        else:
            print("{} has FAILED. Inspect files created in {}.".format(
                self._testMethodName, self.tmpdir))
            self.prev_errors = current_errors


class TestTests(TempDirTestCase, LogTestCase):
    """
    These tests create failures and errors to exercise and ensure cleanup
    still happens properly, and that following tests are isolated.
    Perhaps they should be sprinkled through out other tests cases?
    """
    @unittest.expectedFailure
    def test_fails(self):
        self.assertTrue(False)

    @unittest.expectedFailure
    def test_raises(self):
        raise Exception('Testing exceptions')

    def test_good(self):
        self.assertTrue(True)
