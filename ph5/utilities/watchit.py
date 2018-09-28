#!/usr/bin/env pnpython3

from threading import Timer


class Timeout(Exception):
    def __init__(self, args=None):
        self.args = args


class Watchdog:
    def __init__(self, timeout, userHandler=None):  # timeout in seconds
        self.timeout = timeout
        self.handler = userHandler if userHandler is not None\
            else self.defaultHandler
        self.timer = Timer(self.timeout, self.handler)

    def reset(self):
        self.timer.cancel()
        self.timer = Timer(self.timeout, self.handler)

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.cancel()

    def defaultHandler(self):
        raise Timeout("Yikes")


if __name__ == '__main__':
    wd = None
    import time
    import sys

    def goHere():
        global go
        go = False
        print "Done"
        sys.exit()

    def loop():
        global go
        try:
            while go:
                print '.'
                time.sleep(1)
        except BaseException:
            print "Done"

    wd = Watchdog(23, userHandler=goHere)
    go = True
    wd.start()
    loop()
