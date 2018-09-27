import logging


LOGGING_FORMAT = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s"

# Setup the logger.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# Prevent propagating to higher loggers.
logger.propagate = 0
# Console log handler. By default any logs of level info and above are
# written to the console
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# Add formatter
formatter = logging.Formatter(LOGGING_FORMAT)
ch.setFormatter(formatter)
logger.addHandler(ch)
