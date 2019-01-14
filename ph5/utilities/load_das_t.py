#!/usr/bin/env pnpython4
#
# A program to load a series of das table kef files based on
# regular expression of file names.
#
# Steve Azevedo, May 2017
#

import os
import re
import logging
import subprocess

PROG_VERSION = '2019.14'
LOGGER = logging.getLogger(__name__)

all = os.listdir('.')


def get_args():
    global ARGS

    import argparse

    parser = argparse.ArgumentParser()

    parser.usage = "v{0}: load_das_t options\nLoad a batch of Das_t kef" \
                   "files.".format(PROG_VERSION)
    # Path to family of ph5 files to modify.
    parser.add_argument('--path', type=str, default='../Sigma',
                        help="Path to merged PH5 families. Normally in /Sigma")
    # Regular expression of das table kef files.
    parser.add_argument('--re', type=str,
                        default=r"Das_t_response_n_i_(\w{3,16})\.kef",
                        help=r"Regular expression for das table kef files."
                             r"Default:\"Das_t_response_n_i_(\w{3,16})\.kef\"")
    # Only load, don't save and clear first.
    parser.add_argument('--onlyload', action='store_true',
                        help="Only load table, don't clear existing table.")
    # Only save and clear, don't load table.
    parser.add_argument('--onlysave', action='store_true',
                        help="Save existing table as kef then clear table.")

    ARGS = parser.parse_args()


# Save table as a kef then clear


def save_kefs():
    # All the files in this directory
    for f in all:
        # that match the kef file RE
        mo = RE.match(f)
        if mo:
            das = mo.groups()[0]
            # Save table as kef (S stands for saved)
            new = "Das_t_S_{0}.kef".format(das)
            command = "ph5tokef -n {2} -D {0} > {1}".format(das, new, MASTER)
            LOGGER.info(command)
            ret = subprocess.call(command, shell=True)
            if ret < 0:
                LOGGER.error("Command failed: {0}".format(ret))
                continue
            # Clear existing table
            command = "delete_table -n {1} -D {0}".format(das, MASTER)
            LOGGER.info(command)
            try:
                p = subprocess.Popen(command,
                                     bufsize=0,
                                     executable=None,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     preexec_fn=None,
                                     close_fds=False,
                                     shell=True,
                                     cwd=None,
                                     env=None,
                                     universal_newlines=False,
                                     startupinfo=None,
                                     creationflags=0)
                p.stdin.write('y\n')
            except Exception as e:
                LOGGER.error("Command failed: {0}".format(e.message))

    LOGGER.info("-=" * 40)


# Load das teble kef


def load_kefs():
    for f in all:
        mo = RE.match(f)
        if mo:
            command = "keftoph5 -n {1} -k {0}".format(f, MASTER)
            LOGGER.info(command)
            ret = subprocess.call(command, shell=True)
            if ret < 0:
                LOGGER.error("Command failed: {0}".format(ret))


def main():
    global MASTER, RE
    get_args()
    MASTER = os.path.join(ARGS.path, 'master.ph5')
    RE = re.compile(ARGS.re)
    if not ARGS.onlyload:
        save_kefs()
    if not ARGS.onlysave:
        load_kefs()


if __name__ == '__main__':
    main()
