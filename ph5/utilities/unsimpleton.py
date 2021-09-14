#!/usr/bin/env pnpython4
#
# Rename nodal fcnt file names to RL_S.0.x.rg16 filename format.
#
# Input: List of files to rename in a file (one per line),
# output directory for links
#
# Usage: unsimpleton list_of_files_to_link out_directory
#
# Steve Azevedo, August 2016
#
import argparse
import sys
import os
import logging
from ph5.core import segdreader

PROG_VERSION = '2021.208'
LOGGER = logging.getLogger(__name__)


def get_args():
    '''   Get inputs
    '''
    global ARGS

    parser = argparse.ArgumentParser()

    parser.description = ("A command line utility to link fairfield SEG-D "
                          "file names that expose information about the "
                          "contents of the file, ie. makes file names for "
                          "carbon units. v{0}"
                          .format(PROG_VERSION))

    parser.add_argument("-f", "--filelist", dest="segdfilelist",
                        help="The list of SEG-D files to link.",
                        required=True)

    parser.add_argument("-d", "--linkdir", dest="linkdirectory",
                        help="Name directory to place renamed links.",
                        required=True)

    parser.add_argument("--hardlinks", dest="hardlinks", action="store_true",
                        help="Create hard links inplace of soft links.")

    ARGS = parser.parse_args()

    if not os.path.exists(ARGS.segdfilelist):
        LOGGER.error("Can not read {0}!".format(ARGS.segdfilelist))
        sys.exit()

    if not os.path.exists(ARGS.linkdirectory):
        try:
            os.mkdir(ARGS.linkdirectory)
        except Exception as e:
            LOGGER.error(e.message)
            sys.exit()


def print_container(container):
    keys = container.keys()
    for k in keys:
        print k, container[k]

    print '-' * 80


def general_headers(sd):
    sd.process_general_headers()


def channel_set_descriptors(sd):
    sd.process_channel_set_descriptors()


def extended_headers(sd):
    sd.process_extended_headers()


def external_header(sd):
    sd.process_external_headers()


def trace_headers(sd):
    n = 1
    print "*** Trace Header ***", n

    sd.process_trace_headers()
    print_container(sd.trace_headers.trace_header)
    i = 1
    for c in sd.trace_headers.trace_header_N:
        print i
        i += 1
        print_container(c)

    sd.read_trace(sd.samples)
    while True:
        if sd.isEOF():
            break
        print "*** Trace Header ***", n
        sd.process_trace_headers()
        print_container(sd.trace_headers.trace_header)
        i = 1
        for c in sd.trace_headers.trace_header_N:
            print i
            i += 1
            print_container(c)

        n += 1
        sd.read_trace(sd.samples)

    print "There were {0} traces.".format(n)


def main():
    global RH, TH
    TH = []
    get_args()
    outpath = ARGS.linkdirectory

    with open(ARGS.segdfilelist) as fh:
        lh = open("unsimpleton.log", 'a+')
        while True:
            line = fh.readline()
            if not line:
                break
            filename = line.strip()
            if not os.path.exists(filename):
                LOGGER.warning("Can't find: {0}".format(filename))
                continue
            RH = segdreader.ReelHeaders()
            try:
                sd = segdreader.Reader(infile=filename)
            except BaseException:
                LOGGER.error(
                    "Failed to properly read {0}.".format(filename))
                sys.exit()

            general_headers(sd)
            channel_set_descriptors(sd)
            extended_headers(sd)
            external_header(sd)

            line_number = sd.reel_headers.extended_headers[2]['line_number']
            receiver_point = sd.reel_headers.extended_headers[2][
                'receiver_point']
            sd.reel_headers.general_header_blocks[1]['file_version_number']
            id_number = sd.reel_headers.extended_headers[0]['id_number']
            outfile = "PIC_{0}_{1}_{3}.0.0.rg{2}".format(
                line_number, receiver_point, 16, id_number)
            linkname = os.path.join(outpath, outfile)
            i = 0
            while os.path.exists(linkname):
                i += 1
                outfile = "PIC_{0}_{1}_{4}.0.{3}.rg{2}".format(
                    line_number, receiver_point, 16, i, id_number)
                linkname = os.path.join(outpath, outfile)

            try:
                if ARGS.hardlinks is True:
                    print filename, 'hard->', linkname
                    try:
                        os.link(filename, linkname)
                    except Exception as e:
                        LOGGER.error(
                            "Failed to create HARD link:\n{0}"
                            .format(e.message))
                        sys.exit()
                else:
                    print filename, 'soft->', linkname
                    try:
                        os.symlink(filename, linkname)
                    except Exception as e:
                        LOGGER.error(
                            "Failed to create soft link:\n{0}"
                            .format(e.message))
                        sys.exit()

                lh.write("{0} -> {1}\n".format(filename, linkname))
            except Exception as e:
                print e.message

        lh.close()


if __name__ == '__main__':
    main()
