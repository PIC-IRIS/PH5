#!/usr/bin/env pnpython4
#
# Kef handler library
# Steve Azevedo, September 2016
#

import sys
import logging
import os
import string
import re
from ph5.core import columns
from StringIO import StringIO

PROG_VERSION = '2019.53'
LOGGER = logging.getLogger(__name__)


keyValFileRE = re.compile(r"(.*)\s*[;=]\s*(.*)")
updateRE = re.compile(r"(/.*):Update:(.*)\s*")
deleteRE = re.compile(r"(/.*):Delete:(.*)\s*")
receiverRE = re.compile("/Experiment_g/Receivers_g/Das_g_.*")

arrayRE = re.compile(r"/Experiment_g/Sorts_g/Array_t_(\d+)")
eventRE = re.compile(r"/Experiment_g/Sorts_g/Event_t(_(\d+))?")
offsetRE = re.compile(r"/Experiment_g/Sorts_g/Offset_t(_(\d+)_(\d+))?")


class KefError (Exception):
    pass


class KefWarning (Exception):
    pass


def file_len(fh):
    """
    returns the number of lines in a file
    :type file
    :param fh:
    :return: :int number of lines in file
    """
    fh.seek(0, 0)
    for i, l in enumerate(fh):
        pass
    fh.seek(0, 0)
    return i + 1


def is_array_kef(fh):
    """
    Opens a file handle. Returns boolean value.
    True if file handle is a valid kef file
    :type file
    :param fh:
    :return: boolean
    """
    fh.seek(0, 0)
    length = file_len(fh)
    if length < 5:
        fh.seek(0, 0)
        return False

    arrayRE = re.compile(r"/Experiment_g/Sorts_g/Array_t_(\d+)(\W*)")
    head = [next(fh) for x in range(5)]
    for line in head:
        mo = arrayRE.match(line)
        if mo:
            fh.seek(0, 0)
            return True
    fh.seek(0, 0)
    return False


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

    def __iter__(self):
        while True:
            yield self.next()

    def to_str(self):
        stio = StringIO()
        for p, kv in self:
            keys = sorted(kv.keys())
            stio.write("{0}\n".format(p))
            for k in keys:
                stio.write("\t{0}={1}\n".format(k, kv[k]))
        return stio.getvalue()

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
        self.keySets = {}
        aKeySet = []
        self.pathCount = 0
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
                nchars += len(appnd)
                appnd = string.strip(appnd)
                line = line + appnd

            # This line contains the path to the table to update
            if line[0] == '/':
                self.pathCount += 1
                if path:
                    self.parsed[path].append(keyval)
                    keyval = {}
                    if path not in self.keySets:
                        self.keySets[path] = aKeySet
                        aKeySet = []

                path = line
                sincepath = nchars * -1
                continue

            mo = keyValFileRE.match(line)
            if mo:
                key, value = mo.groups()
                sincepath -= nchars
            else:
                LOGGER.warning("Unparsable line: %s\nSkipping" % line)
                continue

            key = string.strip(key)
            value = string.strip(value)
            if value != 'None':
                if path not in self.parsed:
                    self.parsed[path] = []

                keyval[key] = value
                if path not in self.keySets:
                    aKeySet.append(key)

        # No limits on what to read
        if num is None or EOF:
            if keyval:
                self.parsed[path].append(keyval)
                if path not in self.keySets:
                    self.keySets[path] = aKeySet
                    aKeySet = []

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

        if not path:
            raise StopIteration

        return path, keyval

    # Rewind
    def rewind(self):
        self.paths = self.parsed.keys()
        self.keyvals = []

    def batch_update(self, trace=False):
        '''   Batch update ph5 file from kef file   '''
        err = False
        self.rewind()
        for p, kv in self:
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
                LOGGER.warning("No table reference for key: {0}\n"
                               "Possibly ph5 file is not open or initialized?"
                               .format(p))
                continue

            # Get handle
            ref = columns.TABLES[p]
            # key needs to be list for columns.validate
            if trace is True:
                LOGGER.info("Validating...")

            errs_keys, errs_required = columns.validate(ref, kv, key)
            for e in errs_keys + errs_required:
                err = True
                LOGGER.info(e)

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

    def ksort(self, mkey):
        # Kludge to handle mis-written node id_s
        nodeIDRE = re.compile(r"\d+X\d+")

        def cmp_on_key(x, y):
            if nodeIDRE.match(x[mkey]):
                x[mkey] = x[mkey].split('X')[1]
            if nodeIDRE.match(y[mkey]):
                y[mkey] = y[mkey].split('X')[1]

            try:
                return cmp(int(x[mkey]), int(y[mkey]))
            except ValueError:
                return cmp(x[mkey], y[mkey])

        keys = self.parsed.keys()
        for k in keys:
            elements = self.parsed[k]
            tmp = sorted(elements, cmp_on_key)
            self.parsed[k] = tmp

#
# Mixins
#


def print_kef(p, kv, action='', key=None):
    '''
       Print a line to kef file format
       p -> Path (/Experiment_g/Sorts_g/Array_t_001)
       kv -> A dictionary of key value pairs
       action -> 'Delete or Update', requires key also
       key -> Valid key from kv
    '''
    if action not in ("Update", "Delete", ""):
        raise KefError(
            "Error: {0} not in recognized action list, Update|Delete."
            .format(action))
    keys = sorted(kv.keys())
    if len(action) != 0:
        if key not in keys:
            raise KefError(
                "Error: {0} not valid key. Example: Update:id_s."
                .format(key))
        action = ':' + action + ':' + key
    print("{0}{1}".format(p, action))
    for k in keys:
        print("\t{0}={1}".format(k, kv[k]))


#
# Main
#
if __name__ == '__main__':
    k = Kef('Experiment_t.kef')
    k.open()
    k.read()
    k.rewind()

    for p, kv in k:
        kall = sorted(kv.keys())
        for k1 in kall:
            print p, k1, kv[k1]
    k.close()
