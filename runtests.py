"""
Script to run all tests in the entire project
"""


import unittest
import argparse
from ph5.clients.tests.test_ph5toms import TestPH5toMSeed
from ph5.core.tests.test_ph5utils import TestPH5Utils
from ph5.clients.tests.test_ph5availability import TestPH5Availability
from ph5.core.tests.test_ph5api import TestPH5API
from ph5.utilities.tests.test_metadatatoph5 import TestMetadatatoPH5
from ph5.utilities.tests.test_obspytoph5 import TestObspytoPH5


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Runs tests for PH5 Web Services.')
    parser.add_argument('--include_ph5_dependent',
                        help='Run tests that require access to the PH5 archive.',
                        default=False,
                        action="store_true",)
    args = parser.parse_args()
    return args


def run_test(class_name):
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    runner = unittest.TextTestRunner(verbosity=3)
    return runner.run(suite)


if __name__ == '__main__':
    args = parse_arguments()
    tests = [TestPH5toMSeed, TestPH5Utils, TestPH5API,
             TestMetadatatoPH5, TestObspytoPH5,
             TestPH5Availability]
    passed = True
    for test_class in tests:
        test_result = run_test(test_class)
        if test_result.failures:
            passed = False
    if not passed:
        exit(1)  # One or more test failed
    else:
        exit(0)  # All tests passing
