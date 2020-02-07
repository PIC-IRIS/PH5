import unittest
from testfixtures import LogCapture
from ph5.log_capture_test import logEx
import ph5
import logging


class TestLogEx(unittest.TestCase):
    def setUp(self):
        # enable propagating to higher loggers
        ph5.logger.propagate = 1
        # disable writing log to console
        ph5.logger.removeHandler(ph5.ch)

    def tearDown(self):
        # enable disable to higher loggers
        ph5.logger.propagate = 0
        # enable writing log to console
        ph5.logger.addHandler(ph5.ch)

    def test_makeLog(self):
        logger_name = 'ph5'

        # check the whole log
        with LogCapture() as log:
            logEx.makeLog()
        log.check(
            (logger_name, 'WARNING', 'My first warning'),
            (logger_name, 'INFO', 'My first info'),
            (logger_name, 'ERROR', 'My first error'),
            (logger_name, 'ERROR', 'My second error'),
            (logger_name, 'WARNING', 'My second warning'),
            (logger_name, 'INFO', 'My second info'))

        # check if a log message exists
        log.check_present((logger_name, 'WARNING', 'My second warning'))

        # check ERROR only
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            logEx.makeLog()
        log.check(
            (logger_name, 'ERROR', 'My first error'),
            (logger_name, 'ERROR', 'My second error'))

        # check specific errors
        self.assertEqual(log.records[1].msg, 'My second error')


if __name__ == "__main__":
    unittest.main()
