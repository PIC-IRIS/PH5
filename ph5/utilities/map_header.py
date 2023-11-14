#!/usr/bin/env pnpython4
#
# create map of file paths and (array, station) for SmartSolo files
#
# Input: List of SmartSolo files to create map in a file (one per line)
#
# Usage: mapheader list_of_files_to_create_map
#
# Lan Dam, November 2023
#
import argparse
import sys
import os
import logging
from ph5.core import segdreader_smartsolo
from ph5 import LOGGING_FORMAT

PROG_VERSION = '2023.318'
LOGGER = logging.getLogger(__name__)


def get_args():
    """
    Get inputs
    """
    global ARGS

    parser = argparse.ArgumentParser()

    parser.description = ("A command line utility for SmartSolo SEG-D "
                          "to create mapping between filepaths and their "
                          "array, station. v{0}"
                          .format(PROG_VERSION))

    parser.add_argument("-f", "--listfile", dest="sslistfile",
                        help="File that contents the list of SmartSolo SEG-D "
                             "files to create map.",
                        required=True)

    ARGS = parser.parse_args()

    if not os.path.exists(ARGS.sslistfile):
        LOGGER.error("Can not read {0}!".format(ARGS.sslistfile))
        sys.exit()
    set_logger()


def set_logger():
    if LOGGER.handlers != []:
        LOGGER.removeHandler(LOGGER.handlers[0])

    # Write log to file
    ch = logging.FileHandler("mapheader.log")
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)


def create_mapping_line_for_smartsolo(path2file):
    """
    Read array_id and station_id from header of the given file to give back das
    name for the file

    :param path2file: absolute path to the file to get the info
    :return mapping line: in format: path2file:<array_id>X<station_id>
    """
    try:
        sd = segdreader_smartsolo.Reader(infile=path2file)
    except BaseException:
        LOGGER.error(
            "Failed to properly read {0}.".format(path2file))
        sys.exit()
    sd.process_general_headers()
    sd.process_channel_set_descriptors()
    sd.process_extended_headers()
    sd.process_external_headers()
    sd.process_trace_headers()
    arg = {'file': path2file}
    arg['array_id'] = sd.trace_headers.line_number
    arg['station_id'] = sd.trace_headers.receiver_point
    return "%(file)s:%(array_id)sX%(station_id)s\n" % arg


def main():
    get_args()

    with open(ARGS.sslistfile) as list_file:
        with open("smartsolo_map", 'w') as map_file:
            while True:
                line = list_file.readline()
                if not line:
                    break
                asbpath = line.strip()
                if not os.path.exists(asbpath):
                    LOGGER.warning("Can't find: {0}".format(asbpath))
                    continue
                map_line = create_mapping_line_for_smartsolo(asbpath)
                map_file.write(map_line)


if __name__ == '__main__':
    main()
