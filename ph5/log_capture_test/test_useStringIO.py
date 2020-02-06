import unittest
import logging
from StringIO import StringIO
from contextlib import contextmanager
from ph5.log_capture_test import logEx


@contextmanager
def captured_log():
    capture = StringIO()
    chan = logging.StreamHandler(capture)
    logEx.logger.addHandler(chan)
    try:
        yield capture
    finally:
        logEx.logger.removeHandler(chan)


class TestLogEx(unittest.TestCase):

    def setUp(self):
        # disable writing log to console
        logEx.logger.removeHandler(logEx.ch)

    def tearDown(self):
        # enable writing log to console
        logEx.logger.addHandler(logEx.ch)

    def test_makeLog(self):
        with captured_log() as log:
            logEx.makeLog()
        loglines = log.getvalue().split("\n")

        self.assertEqual(loglines[0], 'My first warning')
        self.assertEqual(loglines[1], 'My first info')
        self.assertEqual(loglines[2], 'My first error')
        self.assertEqual(loglines[3], 'My second error')
        self.assertEqual(loglines[4], 'My second warning')
        self.assertEqual(loglines[5], 'My second info')


if __name__ == "__main__":
    unittest.main()
