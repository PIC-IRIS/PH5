#
# Lan Dam, November 2020
#

import argparse
import os
import sys
import logging
import tables

from ph5.core import ph5api, experiment
from ph5.utilities import nuke_table, kef2ph5 as K2T, tabletokef as T2K
from ph5 import LOGGING_FORMAT

PROG_VERSION = '2020.325'
LOGGER = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = ("fix_srm --nickname ph5-file-prefix [options]")

    parser.description = ("Change sample rate multiplier=0 to 1 in"
                          "Das table(s) or Array table(s). \nVersion: {0}"
                          .format(PROG_VERSION))

    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)

    parser.add_argument("-p", "--path", dest="ph5_path",
                        help="Path to ph5 files. Default to current "
                             "directory.",
                        metavar="ph5_path", default=".")

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument("--all_das", dest='all_das', action='store_true',
                       default=False,
                       help=r"Fix sample_rate_multiplier_i in all Das tables"
                            "\n/Experiment_g/Receivers_g/Das_g_xxx/Das_t.")

    group.add_argument("-D", "--Das_t", dest="das_t_", metavar="das",
                       help=r"Fix sample_rate_multiplier_i in Das table"
                            "\n/Experiment_g/Receivers_g/Das_g_[das]/Das_t.")

    group.add_argument("--all_arrays", dest='all_arrays', action='store_true',
                       default=False,
                       help=r"Fix sample_rate_multiplier_i in all Array "
                            "table\n /Experiment_g/Sorts_g/Array_t_xxx .")

    group.add_argument("-A", "--Array_t_", dest="array_t_", metavar="n",
                       help=r"Fix sample_rate_multiplier_i in Array table"
                            "\n /Experiment_g/Sorts_g/Array_t_[n].",
                       type=int)

    group.add_argument("--all", dest='all', action='store_true',
                       default=False,
                       help=r"Fix sample_rate_multiplier_i in all Das tables"
                            "\n/Experiment_g/Receivers_g/Das_g_xxx/Das_t."
                            "\n and all Array tables"
                            "\n /Experiment_g/Sorts_g/Array_t_xxx.")

    args = parser.parse_args()
    ph5 = args.ph5_file_prefix
    path = args.ph5_path
    all_das = args.all_das
    das_sn = args.das_t_
    all_array = args.all_arrays
    array_id = args.array_t_
    if args.all:
        all_array = True
        all_das = True
    return ph5, path, all_das, das_sn, all_array, array_id


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


def delete_das(ph5object, das_name):
    """
    Delete das table identified by das_name from ph5object
    :param ph5object: ph5 object where the das table will be deleted
    :param das_name: das_name to identify das table to delete.
            Ex: 'Das_t_1X1111'
    :return backupfile: name of the kef file to backup the deleted table (str)
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
    ph5object.ph5_g_receivers.nuke_das_t(das_sn)

    LOGGER.info('Nuke {0}.'.format(datapath))
    return backupfile


def delete_array(ph5object, array_name):
    """
    Delete all array tables identified by array_id from ph5object
    :param ph5object: ph5 object where the das table will be deleted
    :param array_name: das_name to identify das table to delete.
            Ex: 'Array_t_001'
    :return backupfile: name of the kef file to backup the deleted table(str)
    """
    array_id = int(array_name.replace('Array_t_', ''))
    try:
        array, array_keys = ph5object.ph5_g_sorts.read_arrays(array_name)
    except tables.exceptions.NoSuchNodeError:
        raise Exception('Array %s not exist.' % array_name)
    array_t = T2K.Rows_Keys(array, array_keys)
    datapath = '/Experiment_g/Sorts_g/{0}'.format(array_name)
    backupfile = nuke_table.backup(
        array_name,
        datapath,
        array_t)
    ph5object.ph5_g_sorts.nuke_array_t(array_id)
    LOGGER.info('Nuke {0}.'.format(datapath))
    return backupfile


def fix_srm_in_kef(startfilepath, fixedfilepath):
    """
    Correct sample rate multiplier (srm) in das table kef file:
        + replace srm=0 with srm=1
        + add srm=1 for each data row if there is no srm
    :param startfilepath: name of kef file for das table (str)
    :param fixedfilepath: name of kef file in which srms are fixed (str)
    """
    startfile = open(startfilepath, 'r')
    fixedfile = open(fixedfilepath, 'w')
    content = startfile.read()
    # occurrences of sample rate multiplier
    srm_occ = [i for i in range(len(content))
               if content.startswith('sample_rate_multiplier_i=0', i)]

    if len(srm_occ) > 0:
        # there are sample rate multipliers in kef file
        content = content.replace('sample_rate_multiplier_i=0',
                                  'sample_rate_multiplier_i=1')

    fixedfile.write(content)
    startfile.close()
    fixedfile.close()
    LOGGER.info('Convert %s sample_rate_multiplier_i=0 to 1'
                ' in %s and save in %s.'
                % (len(srm_occ), startfilepath, fixedfilepath))


def add_fixed_table(ex, ph5, fixedfilepath):
    """
    Add fixed kef file to ex in which table has been removed.
    The fixed kef file will be deleted after added to ex.
    :param ex: experiment where the das table has been deleted (experiment)
    :param ph5: name of the processed ph5 file (str)
    :param fixedfilepath: name of the fixed kef file to be added
        to the experiment (str)
    """
    K2T.LOGGER = LOGGER
    K2T.EX = ex
    K2T.KEFFILE = fixedfilepath
    K2T.TRACE = False
    K2T.PH5 = ph5
    K2T.populateTables()
    os.unlink(fixedfilepath)


def process(ex, ph5, das_name=None, array_name=None):
    """
    Correct srm in a das identified by das_sn or
     in an array identify by array_id.
    :param ph5object: ph5object where the das table's srm need to be corrected
    :param ph5: name of the being processed ph5 file (str)
    :param das_name: name of das table of which srm need
        to be corrected (str)
    :param array_name: name of array tabel of which srm need
        to be corrected (str)
    """
    fixedfilepath = 'fixed.kef'

    if das_name is not None:
        LOGGER.info('>>> Processing Das: %s' % das_name)
        backupfile = delete_das(ex, das_name)
    else:
        LOGGER.info('>>> Processing Array: %s' % array_name)
        backupfile = delete_array(ex, array_name)
    fix_srm_in_kef(backupfile, fixedfilepath)
    add_fixed_table(ex, ph5, fixedfilepath)


def main():
    ph5, path, all_das, das_sn, all_array, array_id = get_args()

    set_logger()
    ph5object = ph5api.PH5(path=path, nickname=ph5, editmode=True)
    LOGGER.info("fix_srm {0}".format(PROG_VERSION))
    LOGGER.info("{0}".format(sys.argv))
    init_T2K(ph5object)
    try:
        if das_sn is not None:
            das_name = 'Das_t_{0}'.format(das_sn)
            # fix given das table
            process(ph5object, ph5, das_name=das_name)
        if array_id is not None:
            array_name = 'Array_t_{0:03d}'.format(array_id)
            # fix given array table
            process(ph5object, ph5, array_name=array_name)
        if all_das:
            # fix all das tables
            ph5object.read_das_g_names()
            for das_g_name in ph5object.Das_g_names.keys():
                das_t_name = das_g_name.replace('Das_g_', 'Das_t_')
                process(ph5object, ph5, das_name=das_t_name)
        if all_array:
            # fix all array tables
            ph5object.ph5_g_sorts.read_sorts()
            for array_name in ph5object.ph5_g_sorts.names():
                process(ph5object, ph5, array_name=array_name)
    except Exception as e:
        LOGGER.error(e.message)

    ph5object.close()


if __name__ == '__main__':
    main()
