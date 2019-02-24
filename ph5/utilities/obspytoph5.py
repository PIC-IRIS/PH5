"""
leverages obspy to read in streams/traces
and convert them to PH5

Derick Hess
"""
import logging
import argparse
import os
from ph5 import LOGGING_FORMAT
from ph5.utilities import initialize_ph5
from ph5.core import experiment
from obspy.io.mseed.core import _is_mseed
from obspy import read as reader

PROG_VERSION = '2019.053'
LOGGER = logging.getLogger(__name__)


class ObspytoPH5Error(Exception):
    """Exception raised when there is a problem with the request.
    :param: message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class ObspytoPH5(object):

    def __init__(self, ph5_object):
        """
        :type class: ph5.core.experiment
        :param ph5_object:
        """
        self.ph5 = ph5_object

    def toph5(self, file_tuple):
        """
        Takes a tuple (file_name, type)
        and loads it into ph5+object
        :type typle
        :param file_tuple:
        :return:
        """
        st = reader(file_tuple[0], format=file_tuple[1])
        # figure out what das to assign data to
        array_names = self.ph5.ph5_g_sorts.namesArray_t()
        if not array_names:
            err = "Array metadata must exist before loading miniSEED"
            LOGGER.error(err)
            return "stop"

        # figure out what mini file it should go in
        return


def getListOfFiles(dirName):
    # create a list of file and sub directories
    # names in the given directory
    listOfFile = os.listdir(dirName)
    allFiles = list()
    # Iterate over all the entries
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        # If entry is a directory then get the list of files in this directory
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)

    return allFiles


def get_args():
    """
    :return: class: argparse
    """
    parser = argparse.ArgumentParser(
            description='Takes data files and converts to PH5',
            usage=('Version: {0} mstoph5 --nickname="Master_PH5_file" '
                   '[options]'.format(PROG_VERSION))
            )
    parser.add_argument(
        "-n", "--nickname", action="store",
        type=str, metavar="nickname", default="master.ph5")

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    parser.add_argument(
        "-f", "--file", dest="infile",
        default=None,
        help="Data file...minissed file",
        metavar="file_file")

    parser.add_argument(
        "-l", "--list", dest="inlist",
        default=None,
        help="list of data files with full path",
        metavar="file_list_file")

    parser.add_argument(
        "-d", "--dir", dest="indir",
        default=None,
        help="Directory to traverse looking for data",
        metavar="directory")

    parser.add_argument(
        "-M", "--num_mini", dest="num_mini",
        help="Create a given number of miniPH5  files.",
        metavar="num_mini", type=int, default=None)

    parser.add_argument(
        "-S", "--first_mini", dest="first_mini",
        help="The index of the first miniPH5_xxxxx.ph5 file.",
        metavar="first_mini", type=int, default=1)

    args = parser.parse_args()
    return args


def main():
    args = get_args()

    if args.nickname[-3:] == 'ph5':
        ph5file = os.path.join(args.ph5path, args.nickname)
    else:
        ph5file = os.path.join(args.ph5path, args.nickname + '.ph5')
        args.nickname += '.ph5'

    PATH = os.path.dirname(args.ph5path) or '.'
    # Debugging
    os.chdir(PATH)
    # Write log to file
    ch = logging.FileHandler(os.path.join(".", "datatoph5.log"))
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)

    if not os.path.exists(ph5file):
        LOGGER.warning("{0} not found. Creating...".format(ph5file))
        # Create ph5 file
        ex = experiment.ExperimentGroup(nickname=ph5file)
        ex.ph5open(True)  # Open ph5 file for editing
        ex.initgroup()
        # Update /Experiment_g/Receivers_g/Receiver_t
        default_receiver_t = initialize_ph5.create_default_receiver_t()
        initialize_ph5.set_receiver_t(default_receiver_t)
        LOGGER.info("Removing temporary {0} kef file."
                    .format(default_receiver_t))
        os.remove(default_receiver_t)
        ex.ph5close()
        LOGGER.info("Done... Created new PH5 file {0}."
                    .format(ph5file))
    # Produce list of valid files from file, list, and dirs
    valid_files = list()
    if args.infile:
        if _is_mseed(args.infile):
            LOGGER.info("{0} is a valid miniSEED file. "
                        "Adding to process list.".format(args.infile))
            valid_files.append((args.infile, 'MSEED'))
        else:
            LOGGER.info("{0} is a  NOT valid miniSEED file.".format(
                args.infile))

    if args.inlist:
        LOGGER.info("Checking list...")
        with open(args.inlist) as f:
            content = f.readlines()
        for line in content:
            if os.path.isfile(line.rstrip()):
                if _is_mseed(line.rstrip()):
                    LOGGER.info("{0} is a valid miniSEED file. "
                                "Adding to"
                                "process list.".format(line.rstrip()))
                    valid_files.append((line.rstrip(), 'MSEED'))
                else:
                    LOGGER.info("{0} is NOT a valid miniSEED "
                                "file.".format(line.rstrip()))
            else:
                LOGGER.info("{0} does not exist".format(line.rstrip()))

    if args.indir:
        LOGGER.info("Scanning directory {0} and sub directories...".format(
            args.indir))
        found_files = getListOfFiles(args.indir)
        for f in found_files:
            if _is_mseed(f):
                LOGGER.info("{0} is a valid miniSEED file. "
                            "Adding to process list.".format(f))
                valid_files.append((f, 'MSEED'))
            else:
                LOGGER.info("{0} is NOT a valid miniSEED file.".format(f))

    # take list of valid files and load them into PH5
    ph5_object = experiment.ExperimentGroup(nickname=args.nickname,
                                            currentpath=args.ph5path)
    ph5_object.ph5open(True)
    ph5_object.initgroup()
    obs = ObspytoPH5(ph5_object)
    for entry in valid_files:
        message = obs.toph5(entry)
        if message == "stop":
            LOGGER.error("Stopping program...")
            break

    ph5_object.ph5close()


if __name__ == '__main__':
    main()
