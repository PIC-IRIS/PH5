#
# Lan Dam, November 2020
#

import argparse
import sys
import logging
import operator

from ph5.core import ph5api, experiment
from ph5.utilities import nuke_table, tabletokef as T2K
from ph5 import LOGGING_FORMAT

PROG_VERSION = '2022.109'
LOGGER = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = ("fix_das_t_order --nickname ph5-file-prefix [options]")

    parser.description = ("Reorder das_t according to channel_number_i and "
                          "time. Will update all das_t in an experiment."
                          " \nVersion: {0}"
                          .format(PROG_VERSION))

    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)

    parser.add_argument("-p", "--path", dest="ph5_path",
                        help="Path to ph5 files. Default to current "
                             "directory.",
                        metavar="ph5_path", default=".")

    args = parser.parse_args()
    ph5 = args.ph5_file_prefix
    path = args.ph5_path
    return ph5, path


def set_logger():
    """
    Setting logger's format and filehandler
    """

    # set filehandler
    ch = logging.FileHandler("fix_das_t_order.log")
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)


def init_T2K(ph5object):
    T2K.LOGGER = LOGGER
    nuke_table.LOGGER = LOGGER
    T2K.init_local()
    T2K.EX = ph5object
    nuke_table.NO_BACKUP = False


def fix_das(ph5object, ph5, path, das_sn):
    """
    Truncate das table identified by das_sn from ph5object
    Populate order-fixed das table
    :param ph5object: ph5 object where the das table will be deleted
    :param ph5: name of ph5 file (str)
    :param path: path to ph5 file (str)
    :param das_sn: das serial number (str)
    """
    das_g = ph5object.ph5_g_receivers.getdas_g(das_sn)
    if das_g is None:
        raise Exception('DAS %s not exist.' % das_sn)
    ph5object.ph5_g_receivers.setcurrent(das_g)
    das_rows, das_keys = experiment.read_table(
        ph5object.ph5_g_receivers.current_t_das)

    das_t = T2K.Rows_Keys(das_rows, das_keys)

    das_name = 'Das_t_' + das_sn
    datapath = '/Experiment_g/Receivers_g/Das_g_{0}/Das_t'.format(das_sn)
    backupfile = nuke_table.backup(
        das_name,
        datapath,
        das_t)
    LOGGER.info('Backup {0} in {1}.'.format(datapath, backupfile))

    ph5object.ph5_g_receivers.truncate_das_t(das_sn)
    LOGGER.info('Truncate {0}.'.format(datapath))

    das_rows = sorted(das_rows,
                      key=operator.itemgetter('channel_number_i',
                                              'time/epoch_l',
                                              'time/micro_seconds_i'))
    LOGGER.info('Populate {0} with order-fixed table.'.format(datapath))
    for r in das_rows:
        ph5object.ph5_g_receivers.populateDas_t(r)


def main():
    ph5, path = get_args()
    set_logger()
    ph5object = ph5api.PH5(path=path, nickname=ph5, editmode=True)
    LOGGER.info("fix_das_t_order {0}".format(PROG_VERSION))
    LOGGER.info("{0}".format(sys.argv))
    init_T2K(ph5object)
    try:
        # fix all das tables
        ph5object.read_das_g_names()
        for das_g_name in ph5object.Das_g_names.keys():
            das_sn = das_g_name.replace('Das_g_', '')
            fix_das(ph5object, ph5, path, das_sn=das_sn)
    except Exception as e:
        LOGGER.error(e.message)

    ph5object.close()


if __name__ == '__main__':
    main()
