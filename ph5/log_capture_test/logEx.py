import ph5


def makeLog():
    ph5.logger.warning("My first warning")
    ph5.logger.info("My first info")
    ph5.logger.error("My first error")
    ph5.logger.error("My second error")
    ph5.logger.warning("My second warning")
    ph5.logger.info("My second info")


if __name__ == "__main__":
    makeLog()
