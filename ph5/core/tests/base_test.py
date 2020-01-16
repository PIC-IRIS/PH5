"""
General methods for testing
"""

import logging
from StringIO import StringIO
from ph5 import logger, ch as CH
from ph5.core import experiment


def log_capture_string():
    """
    to capture log:
    from ph5.core.tests import log_capture_string
    capture = log_capture_string()
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
