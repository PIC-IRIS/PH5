#!/usr/bin/env pnpython3

import sys
import logging
import os
import string
import re
from ph5.core import columns

PROG_VERSION = '2019.14'
LOGGER = logging.getLogger(__name__)


keyValFileRE = re.compile(r"(.*)\s*[;=]\s*(.*)")
updateRE = re.compile(r"(/.*):Update:(.*)\s*")
deleteRE = re.compile(r"(/.*):Delete:(.*)\s*")
receiverRE = re.compile("/Experiment_g/Receivers_g/Das_g_.*")

arrayRE = re.compile(r"/Experiment_g/Sorts_g/Array_t_(\d+)")
eventRE = re.compile(r"/Experiment_g/Sorts_g/Event_t(_(\d+))?")
offsetRE = re.compile(r"/Experiment_g/Sorts_g/Offset_t(_(\d+)_(\d+))?")


class KefError (Exception):
    def __init__(self, args=None):
        self.args = args


class KefWarning (Exception):
    def __init__(self, args=None):
        self.args = args


class Kef:
    '''
          Deal with kef (kitchen, exchange, format) files.
    '''

    def __init__(self, filename):
        self.filename = filename  # The input file
        self.fh = None  # The file handle
        # The file parsed: parsed[path] = [keyval, keyval, ...] keyval = (keys
        # are table keys)
        self.parsed = {}
        self.updateMode = False
        self.keyvals = []  # Current key value dictionary list
        self.current_path = None
        self.paths = []

    def open(self):
        try:
            self.fh = file(self.filename)
        except Exception as e:
            self.fh = None
            raise KefError("Failed to open %s. Exception: %s" %
                           (self.filename, e))

    def close(self):
        self.fh.close()

    def read(self, num=None):
        appnd = ""
        keyval = {}
        self.parsed = {}
        path = None

        EOF = False
        sincepath = 0
        nret = 0
        n = sys.maxsize
        if num is not None:
            n = num

        while n > 0:
            n -= 1
            line = self.fh.readline()
            if not line:
                EOF = True
                break

            nchars = len(line)
            # Skip empty lines and comments
            if line[0] == '#' or line[0] == '\n':
                if sincepath != 0:
                    sincepath -= nchars
                continue

            # Remove all leading and trailing whitespace
            line = string.strip(line)
            # If the length of the stripped line is 0, continue to next line
            if not line:
                continue
            nret += 1
            # If line ends in '\' it is continued on next line
            while line[-1] == '\\':
                line = line[:-1]
                line = line + ' '
                appnd = self.fh.readline()
                if not appnd:
                    break
                len(appnd)
                appnd = string.strip(appnd)
                line = line + appnd

            # This line contains the path to the table to update
            if line[0] == '/':
                if path:
                    self.parsed[path].append(keyval)
                    keyval = {}

                path = line
                sincepath = nchars * -1
                continue

            mo = keyValFileRE.match(line)
            if mo:
                key, value = mo.groups()
                sincepath -= nchars
            else:
                LOGGER.warning("Unparsable line: {0} ... Skipping"
                               .format(line))
                continue

            key = string.strip(key)
            value = string.strip(value)
            if value != 'None':
                if path not in self.parsed:
                    self.parsed[path] = []

                keyval[key] = value

        # No limits on what to read
        if num is None or EOF:
            if keyval:
                self.parsed[path].append(keyval)
        else:
            self.fh.seek(sincepath, os.SEEK_CUR)

        return nret

    def _next_path(self):
        try:
            path = self.paths.pop(0)
            self.keyvals = self.parsed[path]
        except IndexError:
            path = None
            self.keyvals = []

        if path and updateRE.match(path):
            self.updateMode = True
        else:
            self.updateMode = False

        self.current_path = path
        return path

    def _next_keyval(self):
        try:
            keyval = self.keyvals.pop(0)
        except IndexError:
            keyval = None

        return keyval

    # Return next path and key value dictionary
    def next(self):
        path = self.current_path
        keyval = self._next_keyval()
        if not keyval:
            path = self._next_path()
            keyval = self._next_keyval()

        return path, keyval

    def rewind(self):
        self.paths = self.parsed.keys()
        self.keyvals = []

    def batch_update(self, trace=False):
        '''   Batch update ph5 file from kef file   '''
        err = False
        self.rewind()
        p, kv = self.next()
        while p:
            if trace is True:
                kys = kv.keys()
                print("=-" * 30)
                print("{0}".format(p))
                for k in kys:
                    print("\t{0} = {1}".format(k, kv[k]))

            DELETE = False
            # Update or Append or Delete
            mo = deleteRE.match(p)
            if mo:
                DELETE = True
            else:
                mo = updateRE.match(p)

            key = []
            if mo:
                p, k = mo.groups()
                key.append(k)

            # columns.TABLES keeps a dictionary of key = table name, value =
            # reference to table
            if p not in columns.TABLES:
                LOGGER.warning("No table reference for key: {0}".format(p))
                LOGGER.info("Possibly ph5 file is not open or initialized?")
                p, kv = self.next()
                continue

            # Get handle
            ref = columns.TABLES[p]
            # key needs to be list for columns.validate
            if trace is True:
                LOGGER.info("Validating...")

            errs_keys, errs_required = columns.validate(ref, kv, key)
            for e in errs_keys + errs_required:
                err = True
                LOGGER.error(e)

            if trace is True:
                LOGGER.info("Done")

            if len(key) == 0:
                key = None
            else:
                key = key.pop(0)

            if DELETE:
                if trace is True:
                    LOGGER.info("Deleting...")
                else:
                    columns.delete(ref, kv[key], key)
            else:
                if trace is True:
                    LOGGER.info("Updating...")
                else:
                    columns.populate(ref, kv, key)

            if trace is True:
                LOGGER.info("Skipped")

            p, kv = self.next()

        return err

    def strip_receiver_g(self):
        ret = []
        self.rewind()

        for p in self.paths:
            if receiverRE.match(p):
                base = string.split(p, ':')[0]
                ret.append(base)

        return ret

    def strip_a_e_o(self):
        reta = {}
        rete = {}
        reto = {}
        self.rewind()

        for p in self.paths:
            if arrayRE.match(p):
                base = string.split(p, '/')[-1:]
                reta[base[0]] = True
            elif eventRE.match(p):
                base = string.split(p, '/')[-1:]
                rete[base[0]] = True
            elif offsetRE.match(p):
                base = string.split(p, '/')[-1:]
                reto[base[0]] = True

        a = sorted(reta.keys())
        e = rete.keys()
        e.sort()
        o = reto.keys()
        o.sort()

        return a, e, o

    def ksort(self, key):
        def cmp_on_key(x, y):
            return cmp(int(x[key]), int(y[key]))

        keys = self.parsed.keys()
        for k in keys:
            elements = self.parsed[k]
            tmp = sorted(elements, cmp_on_key)
            self.parsed[k] = tmp


if __name__ == '__main__':
    k = Kef('Experiment_t.kef')
    k.open()
    k.read()
    k.rewind()

    p, kv = k.next()
    while p:
        kall = sorted(kv.keys())
        for k1 in kall:
            print p, k1, kv[k1]

        p, kv = k.next()

    k.close()
