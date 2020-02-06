import unittest
from testfixtures import LogCapture
from unittest_ex.log_capture_test import logEx


class TestLogEx(unittest.TestCase):
    def setUp(self):
        # enable propagating to higher loggers
        logEx.logger.propagate = 1
        # disable writing log to console
        logEx.logger.removeHandler(logEx.ch)

    def tearDown(self):
        # enable disable to higher loggers
        logEx.logger.propagate = 0
        # enable writing log to console
        logEx.logger.addHandler(logEx.ch)

    def test_makeLog(self):
        path = 'unittest_ex.log_capture_test.logEx'

        with LogCapture() as log:
            logEx.makeLog()
        log.check(
            (path, 'WARNING', 'My first warning'),
            (path, 'INFO', 'My first info'),
            (path, 'ERROR', 'My first error'),
            (path, 'ERROR', 'My second error'),
            (path, 'WARNING', 'My second warning'),
            (path, 'INFO', 'My second info'))


if __name__ == "__main__":
    unittest.main()
