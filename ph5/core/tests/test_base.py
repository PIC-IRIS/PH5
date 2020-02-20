from ph5 import logger, ch
from StringIO import StringIO
import logging

newch = None


def change_logger_handler():
    # enable propagating to higher loggers
    logger.propagate = 1
    # disable writing log to console
    logger.removeHandler(ch)
    # add StringIO handler to prevent message "No handlers could be found"
    log = StringIO()
    newch = logging.StreamHandler(log)
    logger.addHandler(newch)


def revert_logger_handler():
    # disable propagating to higher loggers
    logger.propagate = 0
    # revert logger handler
    logger.removeHandler(newch)
    logger.addHandler(ch)
