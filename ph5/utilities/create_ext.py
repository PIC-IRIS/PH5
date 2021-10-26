#
# Lan Dam, October 2021
#

import argparse
import os
import sys
import logging
import tables

from ph5.core import ph5api
from ph5 import LOGGING_FORMAT

PROG_VERSION = '2021.294'
LOGGER = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = ("create_ext --nickname ph5-file-prefix [options]")

    parser.description = ("Create external link to minifile for a Das."
                          "\nVersion: {0}"
                          .format(PROG_VERSION))

    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)

    parser.add_argument("-p", "--path", dest="ph5_path",
                        help="Path to ph5 files. Default to current "
                             "directory.",
                        metavar="ph5_path", default=".")

    parser.add_argument("-D", "--Das_g", dest="das_g_", metavar="das",
                        help="Create external link "
                             "/Experiment_g/Receivers_g/Das_g_[das].\n"
                             "Entries related to the Das in Array_t and "
                             "Index_t are checked before link is created.",
                        required=True)

    parser.add_argument("-m", "--minifile",
                        help="Minifile's name. Ex: miniPH5_00001.ph5\n"
                             "Required to be in the same folder of master.ph5",
                        required=True)

    args = parser.parse_args()
    ph5 = args.ph5_file_prefix
    path = args.ph5_path
    das = args.das_g_
    mini = args.minifile
    return ph5, path, das, mini


def set_logger():
    """
    Setting logger's format and filehandler
    """

    # set filehandler
    ch = logging.FileHandler("create_ext.log")
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)


def check_mini(mini):
    """
    Check if the given mini file exist
    """
    minipath = os.path.join(os.getcwd(), mini)
    if os.path.isfile(minipath):
        return True
    raise Exception(
        "Minifile '%s' not exist." % (minipath))


def check_index_t(ph5obj, das, mini):
    """
    :param ph5obj: ph5api obj
    :param das: das serial
    :param mini: mini file name
    :return: raise exception if
        + das not found in index_t
        + found das but minifile not match
    """
    ph5obj.read_index_t()
    found = False
    for e in ph5obj.Index_t['rows']:
        if e['serial_number_s'] == das:
            found = True
            index_mini = e['external_file_name_s'].replace('./', '')

    if not found:
        raise Exception(
            "Das %s not found in Index_t. Metadata need to be added "
            "before creating external link." % das)
    if index_mini != mini:
        raise Exception(
            "Minifile for Das %s in index_t is %s while the given minifile "
            "is %s." % (das, index_mini, mini))


def check_array_t(ph5obj, das):
    """
    :param ph5obj: ph5api obj
    :param das: das serial
    :return: raise exception if das not found in array_t
    """
    ph5obj.read_array_t_names()
    for aname in sorted(ph5obj.Array_t_names):
        ph5obj.read_array_t(aname)
        arraybyid = ph5obj.Array_t[aname]['byid']
        arrayorder = ph5obj.Array_t[aname]['order']
        for ph5_station in arrayorder:
            station_list = arraybyid.get(ph5_station)
            for deployment in station_list:
                station_len = len(station_list[deployment])
                for st_num in range(0, station_len):
                    e = station_list[deployment][st_num]
                    if e['das/serial_number_s'] == das:
                        return True
    raise Exception("Das %s not found in Array_t. Metadata need to be added "
                    "before creating external link." % das)


def check_ext_link(ph5obj, ext_link):
    """
    :param ph5obj: ph5api obj
    :param ext_link: '/Experiment_g/Receivers_g/Das_g_3X500'
    :return: raise exception if the ext_link already exist in ph5
    """
    try:
        ph5obj.ph5.get_node(ext_link)
    except tables.exceptions.NoSuchNodeError:
        return True
    raise Exception("External link '%s' already exist." % ext_link)


def create_ext_link(ph5obj, das, mini, ext_link):
    """
    Create external link to minifile for das in ph5obj
    :param ph5obj: ph5api obj
    :param das: das serial
    :param mini: mini file name
    :param ext_link: '/Experiment_g/Receivers_g/Das_g_3X500'
    """
    ext_group = 'Das_g_%s' % das
    target = "%s:%s" % (mini, ext_link)
    ph5obj.ph5.create_external_link(
        '/Experiment_g/Receivers_g', ext_group, target)
    LOGGER.info("External link '%s' is created. Please run ph5_validate "
                "to check for consistency." % ext_link)


def main():
    ph5, path, das, mini = get_args()
    set_logger()
    ph5obj = ph5api.PH5(path=path, nickname=ph5, editmode=True)
    LOGGER.info("create_ext {0}".format(PROG_VERSION))
    LOGGER.info("{0}".format(sys.argv))
    ext_link = '/Experiment_g/Receivers_g/Das_g_%s' % das
    try:
        check_mini(mini)
        check_array_t(ph5obj, das)
        check_index_t(ph5obj, das, mini)
        check_ext_link(ph5obj, ext_link)
        create_ext_link(ph5obj, das, mini, ext_link)
    except Exception as e:
        LOGGER.error(str(e))
    ph5obj.close()


if __name__ == '__main__':
    main()
