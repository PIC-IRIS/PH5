import unittest
from testfixtures import LogCapture
from ph5.log_capture_test import logEx
import ph5


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
        path = 'ph5'

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
