#!/usr/bin/env pnpython3
#
# Recreate external references under Receivers_g, and Maps_g from Index_t
#
# Steve Azevedo, September 2012
#
import argparse
import os
import logging
import time
from ph5.core import experiment

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)

INDEX_T = {}
M_INDEX_T = {}
PATH = None
PH5 = None

os.environ['TZ'] = 'UTM'
time.tzset()


#
# To hold table rows and keys
#


class Rows_Keys(object):
    __slots__ = ('rows', 'keys')

    def __init__(self, rows=None, keys=None):
        self.rows = rows
        self.keys = keys

    def set(self, rows=None, keys=None):
        if rows is not None:
            self.rows = rows
        if keys is not None:
            self.keys = keys


def read_index_table():
    global EX, INDEX_T

    rows, keys = EX.ph5_g_receivers.read_index()
    INDEX_T = Rows_Keys(rows, keys)


def read_m_index_table():
    global EX, M_INDEX_T

    rows, keys = EX.ph5_g_maps.read_index()
    M_INDEX_T = Rows_Keys(rows, keys)


def update_external_references():
    global EX, INDEX_T

    LOGGER.info("Updating external references...")
    n = 0
    for i in INDEX_T.rows:
        external_file = i['external_file_name_s']
        external_path = i['hdf5_path_s']
        das = i['serial_number_s']
        target = external_file + ':' + external_path
        external_group = external_path.split('/')[3]

        # Nuke old node
        try:
            group_node = EX.ph5.get_node(external_path)
            group_node.remove()
        except Exception as e:
            LOGGER.error("E1 {0}".format(e.message))
        # Re-create node
        try:
            EX.ph5.create_external_link(
                '/Experiment_g/Receivers_g', external_group, target)
            n += 1
        except Exception as e:
            LOGGER.error("E2 {0}".format(e.message))

    m = 0
    for i in M_INDEX_T.rows:
        external_file = i['external_file_name_s']
        external_path = i['hdf5_path_s']
        das = i['serial_number_s']
        target = external_file + ':' + external_path
        external_group = external_path.split('/')[3]
        print external_file, external_path, das, target, external_group

        # Nuke old node
        try:
            group_node = EX.ph5.get_node(external_path)
            group_node.remove()
        except Exception as e:
            LOGGER.error("E3: {0}".format(e.message))

        # Re-create node
        try:
            EX.ph5.create_external_link(
                '/Experiment_g/Maps_g', external_group, target)
            m += 1
        except Exception as e:
            LOGGER.error("E4: {0}".format(e.message))
            LOGGER.error("Done, Index_t {0} nodes recreated. "
                         "M_Index_t {1} nodes recreated.\n"
                         .format(n, m))


#
# Initialize ph5 file
#


def initialize_ph5(editmode=False):
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5

    EX = experiment.ExperimentGroup(PATH, PH5)
    EX.ph5open(True)
    EX.initgroup()


#
# Read Command line arguments
#


def get_args():
    global PH5, PATH

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)
    parser.usage = "recreate_external_references --nickname=ph5-file-prefix"

    parser.description = ("Version: {0} Rebuild external references under "
                          "Receivers_g from info in Index_t."
                          .format(PROG_VERSION))

    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)

    parser.add_argument("-p", "--path", dest="ph5_path",
                        help=("Path to ph5 files. Default to current "
                              "directory."),
                        metavar="ph5_path", default=".")

    args = parser.parse_args()

    PH5 = args.ph5_file_prefix
    PATH = args.ph5_path


def main():
    get_args()
    initialize_ph5()
    read_index_table()
    read_m_index_table()
    update_external_references()


if __name__ == '__main__':
    main()
