import logging
from StringIO import StringIO as StringBuffer

LOGGING_FORMAT = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s"

# Setup the logger.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# Prevent propagating to higher loggers.
logger.propagate = 0


def basic_logging():
    # Console log handler. By default any logs of level info and above are
    # written to the console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return ch


def unittest_logging(ch):
    log_capture_string = StringBuffer()
    logger.removeHandler(ch)
    # Any logs of level info and above are written to log_capture_string
    # to be captured in unittest
    ch = logging.StreamHandler(log_capture_string)
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return log_capture_string


ch = basic_logging()
