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

import construct
import bcd_py

from ph5.core import segdreader, segdreader_smartsolo

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


def read_manufacture_code(filename):
    """ read byte 17 for manufacture code"""
    f = open(filename, 'rb')
    f.seek(16)
    byte = f.read(1)
    swap = True
    if sys.byteorder == 'big':
        swap = False
    bin = construct.BitStruct("BIN",
                              construct.BitField(
                                  "field", 8, swapped=swap))
    bcd = bin.parse(byte)['field']
    if sys.byteorder == 'little':
        bcd = construct.ULInt64("xxx").build(bcd)
    else:
        bcd = construct.UBInt64("xxx").build(bcd)
    code = bcd_py.bcd2int(bcd, 0, 2)
    f.close()
    return code


def get_segdreader(filename):
    """
        get the segdreader from manufacture code infile
        or from --manufacturers_code argument
    """
    KNOWN_CODE = {20: (segdreader, 'FairField'),
                  61: (segdreader_smartsolo, 'SmartSolo')}
    req_code_list = ["%s for %s format" % (k, KNOWN_CODE[k][1])
                     for k in KNOWN_CODE.keys()]
    req_code_str = ("Please give flag --manufacturers_code either "
                    ' or '.join(req_code_list))

    manu = read_manufacture_code(filename)
    if manu in KNOWN_CODE.keys():
        reader, das_type = KNOWN_CODE[manu]
    else:
        LOGGER.error("The manufacture code recorded in file {0} is not "
                     "one of the known codes: {1}.\n{2}".
                     format(manu, KNOWN_CODE.keys(), req_code_str))
        raise Exception
    return reader, das_type


def create_fairfield_linkname(sd, outpath, old_filename, old_new_links_list):
    """
    Create new link for a fairfield data file and map with old name in
        old_new_links_list
    :param sd: segd reader
    :type sd: segdreader.Reader
    :param outpath: path to the folder for output data
    :type outpath: str
    :param old_filename: name of the original data file
    :type old_filename: str
    :param old_new_links_list: list of dir to map between old and new file
    :type old_new_links_list: [{'old': old_filename, 'new': new_linkname}
    """
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
    if old_filename not in [link['old'] for link in old_new_links_list]:
        old_new_links_list.append(
            {'old': old_filename, 'new': linkname}
        )


def create_smartsolo_newlinkparts(sd, old_filename, old_new_links_list):
    """
    Create mapping between old_filename and parts need for new links and time
        of trace to create part order later if needed.

    :param sd: segd reader
    :type sd: segdreader_smartsolo.Reader
    :param old_filename: name of the original data file
    :type old_filename: str
    :param old_new_links_list: list of dir to map between old and new
        file parts and time
    :type old_new_links_list:
        [{'old': old_filename,
         'newparts': {'line_number': ..., 'receiver_point': ..., 'id_number'}
         'time': trace_epoch}]
    """
    sd.process_trace_headers()
    new_parts = {}
    new_parts['line_number'] = sd.trace_headers.line_number
    new_parts['receiver_point'] = sd.trace_headers.receiver_point
    new_parts['id_number'] = sd.id_number
    trace_epoch = sd.trace_headers.trace_epoch

    file_name = sd.name().split('/')[-1]
    file_name_parts = file_name.split('.')
    new_parts['channel'] = file_name_parts[-2].upper()
    if new_parts['channel'] not in ['N', 'E', 'Z']:
        LOGGER.warning(
            "Neither channel E, N, nor Z can't be found in filename: %s"
            % file_name)

    if old_filename not in [link['old'] for link in old_new_links_list]:
        old_new_links_list.append(
            {'old': old_filename, 'newparts': new_parts, 'time': trace_epoch}
        )


def create_smartsolo_linknames_w_partorder(old_new_links_list, outpath):
    """
    Create new links for a smartsolo with part-order by sorting according
        to time than loop through the list and map with old names in
        old_new_links_list
    :param old_new_links_list: list of dir to map between old and new
        file parts and file
    :type old_new_links_list:
        [{'old': old_filename,
         'newparts': {'line_number': ..., 'receiver_point': ..., 'id_number'}
         'time': trace_epoch}]
    :param outpath: path to the folder for output data
    :type outpath: str
    """
    link_dict = {}
    old_new_links_list = sorted(old_new_links_list, key=lambda i: i['time'])

    for id, links in enumerate(old_new_links_list):
        new_parts = links['newparts']
        key = tuple(sorted(new_parts.items()))
        if key not in link_dict:
            link_dict[key] = 0
        else:
            link_dict[key] += 1
        file_number = link_dict[key]
        outfile = "SSolo_{0}_{1}_{2}_{3}_{4}.segd".format(
            new_parts['line_number'],
            new_parts['receiver_point'],
            new_parts['id_number'],
            file_number,
            new_parts['channel'])
        old_new_links_list[id]['new'] = os.path.join(outpath, outfile)


def main():
    global RH, TH
    TH = []
    get_args()
    outpath = ARGS.linkdirectory

    das_type = None
    old_new_links_list = []
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
            segd_reader, das_type = get_segdreader(filename)
            RH = segd_reader.ReelHeaders()
            try:
                sd = segd_reader.Reader(infile=filename)
            except BaseException:
                LOGGER.error(
                    "Failed to properly read {0}.".format(filename))
                sys.exit()
            general_headers(sd)
            channel_set_descriptors(sd)
            extended_headers(sd)
            external_header(sd)

            if das_type == 'FairField':
                create_fairfield_linkname(
                    sd, outpath, filename, old_new_links_list)
            elif das_type == 'SmartSolo':
                create_smartsolo_newlinkparts(
                    sd, filename, old_new_links_list)

        if das_type == 'SmartSolo':
            create_smartsolo_linknames_w_partorder(old_new_links_list, outpath)

        for links in old_new_links_list:
            filename = links['old']
            linkname = links['new']
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
                            "Failed to create soft link:\n{0} to file {1}: {2}"
                            .format(linkname, filename, e.message))
                        sys.exit()

                lh.write("{0} -> {1}\n".format(filename, linkname))
            except Exception as e:
                print e.message

        lh.close()


if __name__ == '__main__':
    main()
