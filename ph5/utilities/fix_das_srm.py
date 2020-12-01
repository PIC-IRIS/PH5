#
# Lan Dam, November 2020
#

import argparse
import os
import sys
import logging

from ph5.core import ph5api
from ph5.utilities import nuke_table, kef2ph5 as K2T, tabletokef as T2K
from ph5 import LOGGING_FORMAT

PROG_VERSION = '2020.325'
LOGGER = logging.getLogger(__name__)


#
# Read Command line arguments
#
def get_args():
    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = ("fix_das_srm --nickname ph5-file-prefix [options]")

    parser.description = ("Fix Das table(s) with no sample rate multiplier or "
                          "sample rate multiplier 0. \nVersion: {0}"
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

    args = parser.parse_args()
    ph5 = args.ph5_file_prefix
    path = args.ph5_path
    all_das = args.all_das
    das_table = args.das_t_
    return ph5, path, all_das, das_table


def set_logger():
    """
    Setting logger's format and filehandler
    """

    # set filehandler
    ch = logging.FileHandler("fix_das_srm.log")
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)


def delete_das(ex, das_sn):
    """
    Delete das table with serial number das_sn from ex
    :param ex: experiment where the das table will be deleted (experiment)
    :param das_sn: serial number to specify das table to delete (str)
    :return backupfile: name of the kef file to backup the deleted table
    """
    T2K.LOGGER = LOGGER
    nuke_table.LOGGER = LOGGER
    T2K.init_local()
    T2K.EX = ex
    nuke_table.NO_BACKUP = False
    table_type = 'Das_t_{0}'.format(das_sn)
    T2K.DAS_TABLE = das_sn
    T2K.read_receivers(das_sn)
    if das_sn in T2K.DAS_T.keys():
        backupfile = nuke_table.backup(
            table_type,
            '/Experiment_g/Receivers_g/Das_g_{0}/Das_t'.format(das_sn),
            T2K.DAS_T[das_sn])
        ex.ph5_g_receivers.nuke_das_t(das_sn)
        LOGGER.info('Nuke/Experiment_g/Receivers_g/Das_g_%s/Das_t.' % das_sn)
    return backupfile


def fix_srm_in_kef(startfilename, fixedfilename):
    """
    Correct sample rate multiplier (srm) in das table kef file:
        + replace srm=0 with srm=1
        + add srm=1 for each data row if there is no srm
    :param startfilename: name of kef file for das table (str)
    :param fixedfilename: name of kef file in which srms are fixed (str)
    """
    startfile = open(startfilename, 'r')
    fixedfile = open(fixedfilename, 'w')
    content = startfile.read()
    # occurrences of sample rate multiplier
    srm_occ = [i for i in range(len(content))
               if content.startswith('sample_rate_multiplier_i', i)]

    if len(srm_occ) > 0:
        # there are sample rate multipliers in kef file
        content = content.replace('sample_rate_multiplier_i=0',
                                  'sample_rate_multiplier_i=1')
    else:
        # due to some error, sample rate is missing in Das_t
        # => add one after each row header
        content = content.replace(
            '/Experiment_g/Receivers_g/Das_g_1X1111/Das_t',
            '/Experiment_g/Receivers_g/Das_g_1X1111/Das_t'
            '\n\tsample_rate_multiplier_i=1')

    fixedfile.write(content)
    startfile.close()
    fixedfile.close()
    LOGGER.info('Fix Sample Rate Multiplier in %s and save in %s.'
                % (startfilename, fixedfilename))


def add_fixed_table(ex, ph5, fixedfilename):
    """
    Add fixed kef file to ex in which table has been removed.
    The fixed kef file will be deleted after added to ex.
    :param ex: experiment where the das table has been deleted (experiment)
    :param ph5: name of the processed ph5 file (str)
    :param fixedfilename: name of the fixed kef file to be added
        to the experiment (str)
    """
    K2T.LOGGER = LOGGER
    K2T.EX = ex
    K2T.KEFFILE = fixedfilename
    K2T.TRACE = False
    K2T.PH5 = ph5
    K2T.populateTables()
    os.unlink(fixedfilename)


def process_das(ex, ph5, das_sn):
    """
    Correct srm in a das specified by das_sn.
    :param ex: experiment where the das table's srm need to be corrected
        (experiment)
    :param ph5: name of the being processed ph5 file (str)
    :param das_sn: serial number of das table of which srm need
        to be corrected (str)
    """
    fixedfilename = 'fixed.kef'
    LOGGER.info('>>> Processing Das: %s' % das_sn)
    backupfile = delete_das(ex, das_sn)
    fix_srm_in_kef(backupfile, fixedfilename)
    add_fixed_table(ex, ph5, fixedfilename)


def main():
    ph5, path, all_das, das_sn = get_args()

    set_logger()
    ph5object = ph5api.PH5(path=path, nickname=ph5, editmode=True)
    LOGGER.info("fix_das_srm {0}".format(PROG_VERSION))
    LOGGER.info("{0}".format(sys.argv))
    if das_sn:
        # fix given das table
        process_das(ph5object, ph5, das_sn)
    else:
        # fix all das tables
        ph5object.read_das_g_names()
        das_sn_list = [d.replace("Das_g_", "")
                       for d in ph5object.Das_g_names.keys()]
        for das_sn in das_sn_list:
            process_das(ph5object, ph5, das_sn)
    ph5object.close()


if __name__ == '__main__':
    main()
