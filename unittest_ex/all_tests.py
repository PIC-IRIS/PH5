#!/usr/bin/env python

"""
recursively run all tests in unittest/
"""

import unittest
from sys import exit

if __name__ == '__main__':
    test_suite = unittest.defaultTestLoader.discover('.')
    result = unittest.TextTestRunner(verbosity=3).run(test_suite)
    exit(0 if result.wasSuccessful() else 1)
