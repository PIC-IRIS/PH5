
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


def makeLog():
    """
    # Write log to file
    ch = logging.FileHandler("logEx.log")
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    """

    logger.warning("My first warning")
    logger.info("My first info")
    logger.error("My first error")
    logger.error("My second error")
    logger.warning("My second warning")
    logger.info("My second info")


if __name__ == "__main__":
    makeLog()
