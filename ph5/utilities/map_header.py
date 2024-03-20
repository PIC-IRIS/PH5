#!/usr/bin/env pnpython4
#
# create map of file paths and (array, station) for SmartSolo files
#
# Input: List of SmartSolo files to create map in a file (one per line)
#
# Usage: mapheader -f list_of_files_to_create_map
#    Or: mapheader -d directory_of_files_to_create_map
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
                          "to create `smartsolo_map` between filepaths and "
                          "their array, station. v{0}"
                          .format(PROG_VERSION))

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--listfile", dest="sslistfile",
                       help="File that contents the list of SmartSolo SEG-D "
                             "files to create map.")

    group.add_argument("-d", "--dir", dest="ssdirectory",
                       help="Name of directory that SmartSolo SEG-D files "
                             "to create map are located.")

    ARGS = parser.parse_args()

    if ARGS.sslistfile is not None and not os.path.exists(ARGS.sslistfile):
        LOGGER.error("Can not read {0}!".format(ARGS.sslistfile))
        sys.exit()
    if ARGS.ssdirectory is not None and not os.path.exists(ARGS.ssdirectory):
        LOGGER.error("{0} not exist!".format(ARGS.ssdirectory))
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
    arg = {'file': path2file,
           'array_id': sd.trace_headers.line_number,
           'station_id': sd.trace_headers.receiver_point}
    return "%(file)s:%(array_id)sX%(station_id)s\n" % arg


def create_map_from_list_file(list_file_name):
    """
    Create map file from file of list of SmartSolo files
    :param list_file_name: name of list file
    """
    with open(list_file_name) as list_file:
        with open("smartsolo_map", 'w') as map_file:
            while True:
                line = list_file.readline()
                if not line:
                    break
                abs_path = line.strip()
                if not os.path.exists(abs_path):
                    LOGGER.warning("Can't find: {0}".format(abs_path))
                    continue
                map_line = create_mapping_line_for_smartsolo(abs_path)
                map_file.write(map_line)


def create_map_from_directory_path(dir_path):
    """
    Create map file from directory of SmartSolo files
    :param dir_path: path to SmartSolo directory (either absolute or relative)
    """
    with open("smartsolo_map", 'w') as map_file:
        for path, subdirs, files in os.walk(dir_path):
            for file_name in files:
                if not file_name.endswith('.segd'):
                    continue
                abs_path = os.path.abspath(os.path.join(path, file_name))
                map_line = create_mapping_line_for_smartsolo(abs_path)
                map_file.write(map_line)


def main():
    get_args()
    LOGGER.info("map_header {0}".format(PROG_VERSION))
    LOGGER.info("{0}".format(sys.argv))
    if ARGS.sslistfile is not None:
        create_map_from_list_file(ARGS.sslistfile)
    else:
        create_map_from_directory_path(ARGS.ssdirectory)


if __name__ == '__main__':
    main()
