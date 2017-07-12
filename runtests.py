"""
Script to run all tests in the entire project
"""


import unittest
import argparse
from ph5.clients.tests.test_ph5tomsAPI import TestPH5toMSeed
from ph5.core.tests.test_ph5utils import TestPH5Utils


def parse_arguments():
    parser = argparse.ArgumentParser(description='Runs tests for PH5 Web Services.')
    parser.add_argument('--include_ph5_dependent',
                        help='Run tests that require access to the PH5 archive.',
                        default=False,
                        action="store_true",)
    args = parser.parse_args()
    return args

def run_test(class_name):
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    runner=unittest.TextTestRunner(verbosity=3)
    return runner.run(suite)


if __name__ == '__main__':
    args = parse_arguments()
    tests = [TestPH5toMSeed, TestPH5Utils]
    passed = True
    for test_class in tests:
        test_result = run_test(test_class)
        if test_result.failures:
            passed = False
    if not passed:
        exit(1) # One or more test failed
    else:
        exit(0) # All tests passing
