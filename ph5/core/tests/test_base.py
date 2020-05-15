import os
import shutil
import tempfile
import unittest
import logging
from StringIO import StringIO

from testfixtures import OutputCapture

from ph5 import logger, ch
from ph5.core import experiment
from ph5.utilities import kef2ph5


def initialize_ex(nickname, path, editmode=False):
    ex = experiment.ExperimentGroup(nickname=nickname, currentpath=path)
    ex.ph5open(editmode)
    ex.initgroup()
    return ex


def kef_to_ph5(ph5path, nickname, commonpath, keflist,
               ex=None, das_sn_list=[]):
    """
    Add kef to ph5file or to experiment (if ex is passed).
    (The task of deleting table before adding the table should happen before
    calling this function. If it is required to have a delete function for all,
    it should be written in nuke_table.py)

    :para ph5path: path to ph5 file
    :type ph5path: string
    :para commonpath: common part of paths to kef files
    :type commonpath: string
    :para keflist: A list of different parts of paths to kef files
    :type keflist: list of string
    :para ex: ph5 experiment from caller
    :para ex: ph5 experiment object
    :result: the tables in the kef files will be added to ph5 file or the
    reference ex (if passed)
    """

    if ex is None:
        with OutputCapture():
            kef2ph5.EX = initialize_ex(nickname, ph5path, True)
    else:
        kef2ph5.EX = ex
    # create nodes for das
    for sn in das_sn_list:
        kef2ph5.EX.ph5_g_receivers.newdas(sn)

    kef2ph5.PH5 = os.path.join(ph5path, nickname)
    kef2ph5.TRACE = False

    for kef in keflist:
        kef2ph5.KEFFILE = os.path.join(commonpath, kef)
        kef2ph5.populateTables()

    if ex is None:
        kef2ph5.EX.ph5close()


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
        for log, h in self.find_all_file_loggers():
            log.removeHandler(h)


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
