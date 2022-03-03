#
# Lan Dam, November 2020
#

import argparse
import os
import sys
import logging
import operator

from ph5.core import ph5api, experiment
from ph5.utilities import nuke_table, kef2ph5 as K2T, tabletokef as T2K
from ph5 import LOGGING_FORMAT

PROG_VERSION = '2022.062'
LOGGER = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = ("fix_das_t_order --nickname ph5-file-prefix [options]")

    parser.description = ("Reorder das_t according to channel_number_i and "
                          "time. \nVersion: {0}"
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
    ch = logging.FileHandler("fix_srm.log")
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


def delete_das(ph5object, das_name, ph5, path):
    """
    Delete das table identified by das_name from ph5object
    :param ph5object: ph5 object where the das table will be deleted
    :param das_name: string to identify das table to be deleted
            Ex: 'Das_t_1X1111'
    :param ph5: name of ph5 file (str)
    :param path: path to ph5 file (str)
    :return
        backupfile: name of the kef file to backup the deleted table (str)
        datapath: path to the table in ph5 structure
        ph5object: ph5 object of which das table has been deleted
    """
    das_sn = das_name.replace("Das_t_", "")
    das = ph5object.ph5_g_receivers.getdas_g(das_sn)
    if das is None:
        raise Exception('DAS %s not exist.' % das_sn)
    ph5object.ph5_g_receivers.setcurrent(das)
    das, das_keys = experiment.read_table(
        ph5object.ph5_g_receivers.current_t_das)
    das_t = T2K.Rows_Keys(das, das_keys)
    datapath = '/Experiment_g/Receivers_g/Das_g_{0}/Das_t'.format(das_sn)
    backupfile = nuke_table.backup(
        das_name,
        datapath,
        das_t)
    ph5object.ph5_g_receivers.truncate_das_t(das_sn)
    LOGGER.info('Nuke {0}.'.format(datapath))
    return backupfile, datapath, ph5object


def fix_das_order_in_kef(startfilepath, fixedfilepath, datapath):
    """
    Reorder Das_t according to channel and time in kef file startfilepath and
    save into fixedfilepath
    :param startfilepath: name of kef file for das table (str)
    :param fixedfilepath: name of kef file in which srms are fixed (str)
    :param datapath: path to the table in ph5 structure
    """
    startfile = open(startfilepath, 'r')
    fixedfile = open(fixedfilepath, 'w')
    content = startfile.read()
    parts = content.split("#")
    dasinfo = []
    for p in parts[4:]:
        d = {'kefStr': p}
        p_lines = p.split("\n")
        for line in p_lines:
            if 'channel_number_i' in line:
                d['channel_number_i'] = line.split('=')[1]
            if 'time/epoch_l' in line:
                d['time/epoch_l'] = line.split('=')[1]
            if 'time/micro_seconds_i' in line:
                d['time/micro_seconds_i'] = line.split('=')[1]
        dasinfo.append(d)

    sorted_dasinfo = sorted(dasinfo,
                            key=operator.itemgetter('channel_number_i',
                                                    'time/epoch_l',
                                                    'time/micro_seconds_i'))
    new_parts = parts[:4] + [das['kefStr'] for das in sorted_dasinfo]
    new_content = "#".join(new_parts)
    fixedfile.write(new_content)
    startfile.close()
    fixedfile.close()
    logmsg = ('Reorder das_t and save in %s.' % fixedfilepath)
    LOGGER.info(logmsg)


def add_fixed_table(ex, ph5, path, fixedfilepath):
    """
    Add fixed kef file to ex of which the table has been removed.
    The fixed kef file will be deleted after added to ex.
    :param ex: experiment where the das table has been deleted (experiment)
    :param ph5: name of ph5 file (str)
    :param path: path to ph5 file (str)
    :param fixedfilepath: name of the fixed kef file to be added
        to the experiment (str)
    """
    K2T.LOGGER = LOGGER
    K2T.EX = ex
    K2T.KEFFILE = fixedfilepath
    K2T.TRACE = False
    K2T.PH5 = ph5
    K2T.PATH = path
    K2T.populateTables()
    os.unlink(fixedfilepath)


def process(ph5object, ph5, path, das_name=None, array_name=None):
    """
    Correct srm in a das identified by das_sn or
     in an array identify by array_id.
    :param ph5object: ph5object where the das table's srm need to be corrected
    :param ph5: name of ph5 file (str)
    :param path: path to ph5 file (str)
    :param das_name: name of das table of which srm need to be corrected (str)
    :param array_name: name of array table of which srm need
        to be corrected (str)
    """
    fixedfilepath = 'fixed.kef'

    if das_name is not None:
        LOGGER.info('>>> Processing Das: %s' % das_name)
        backupfile, datapath, ph5object = delete_das(
            ph5object, das_name, ph5, path)

    fix_das_order_in_kef(backupfile, fixedfilepath, datapath)
    add_fixed_table(ph5object, ph5, path, fixedfilepath)
    return ph5object


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
            das_t_name = das_g_name.replace('Das_g_', 'Das_t_')
            ph5object = process(ph5object, ph5, path, das_name=das_t_name)
    except Exception as e:
        LOGGER.error(e.message)

    ph5object.close()


if __name__ == '__main__':
    main()
