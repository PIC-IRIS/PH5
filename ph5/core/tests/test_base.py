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
        super(LogTestCase, self).setUp()
        file_loggers = self.find_all_file_loggers()
        # print('\nLog setup:')
        if file_loggers:
            print('\n\tsetup: {}'.format(file_loggers))

    def tearDown(self):
        file_loggers = self.find_all_file_loggers()
        if file_loggers:
            print('\n\tTeardown1 {}'.format(self.find_all_file_loggers()))

            # remove all file handlers
            for l, h in self.find_all_file_loggers():
                l.removeHandler(h)

            print('\tTeardown2 {}'.format(self.find_all_file_loggers()))
        super(LogTestCase, self).tearDown()

    @staticmethod
    def find_all_file_loggers():
        file_logger_handlers = list()
        for k, v in logging.Logger.manager.loggerDict.items():
            if not isinstance(v, logging.PlaceHolder):
                for h in v.handlers:
                    if isinstance(h, logging.FileHandler):
                        file_logger_handlers.append((logging.getLogger(k), h))
        return file_logger_handlers

    def remove_all_file_handlers(self):
        for k, v in logging.Logger.manager.loggerDict.items():
            if not isinstance(v, logging.PlaceHolder):
                for h in v.handlers:
                    if isinstance(h, logging.FileHandler):
                        print('Removing: {}   {}'.format(k, h.baseFilename))
                        print(logging.getLogger(k).removeHandler(h))


class TempDirTestCase(unittest.TestCase):

    def setUp(self):
        """
        create tmpdir
        """
        self.tmpdir = None
        self.home = None
        # self.debug()
        self.home = os.getcwd()
        self.tmpdir = tempfile.mkdtemp(dir=self.home + "/ph5/test_data/")
        os.chdir(self.tmpdir)
        self.addCleanup(os.chdir, self.home)
        # self.debug()
        super(TempDirTestCase, self).setUp()

    def tearDown(self):
        super(TempDirTestCase, self).tearDown()
        # self.debug()
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

    def debug(self):
        print()
        print('id:     {}'.format(self.id))
        print('tmpdir: {}'.format(self.tmpdir))
        print('cwd:    {}'.format(os.getcwd()))
        print('home:   {}'.format(self.home))
