"""
General methods for testing
"""

import logging
import sys
from StringIO import StringIO
from contextlib import contextmanager
from ph5 import logger, ch as CH
from ph5.core import experiment


@contextmanager
def captured_output():
    """
    to capture stdout:
    from ph5.core.tests import base_test
    with base_test.captured_output() as (out, err):
        //some function
    output = out.getvalue().strip()
    """
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def log_capture_string():
    """
    to capture log:
    from ph5.core.tests import base_test
    capture = base_test.log_capture_string()
    loglines = capture.getvalue().split("\n")
    """
    capture = StringIO()
    logger.removeHandler(CH)
    ch = logging.StreamHandler(capture)
    logger.addHandler(ch)

    return capture


def initialize_ph5(nickname, path='.', editmode=False):
    ex = experiment.ExperimentGroup(nickname=nickname, currentpath=path)
    ex.ph5open(editmode)
    ex.initgroup()
    return ex
