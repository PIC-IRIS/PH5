#!/usr/bin/env python
"""
Script to run all tests in the entire project
"""

import unittest
from sys import exit
import ph5
from StringIO import StringIO
import logging


if __name__ == '__main__':
    # enable propagating to higher loggers
    ph5.logger.propagate = 1
    # disable writing log to console
    ph5.logger.removeHandler(ph5.ch)
    ######
    # add StringIO handler to prevent message "No handlers could be found"
    log = StringIO()
    ch = logging.StreamHandler(log)
    ph5.logger.addHandler(ch)
    ######
    test_suite = unittest.defaultTestLoader.discover('.')
    result = unittest.TextTestRunner(verbosity=3).run(test_suite)
    exit(0 if result.wasSuccessful() else 1)

