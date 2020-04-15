#!/usr/bin/env python
"""
Script to run all tests in the entire project
"""

import unittest
from sys import exit

if __name__ == '__main__':
    test_suite = unittest.defaultTestLoader.discover('.')
    result = unittest.TextTestRunner(verbosity=3).run(test_suite)
    exit(0 if result.wasSuccessful() else 1)

