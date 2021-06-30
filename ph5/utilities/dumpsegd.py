#!/usr/bin/env pnpython3
#
# Dump Fairfield SEG-D header values
#
# Steve Azevedo, October 2014
#
import sys
import os
from ph5.core import segdreader, segdreader_smartsolo
from signal import signal, SIGPIPE, SIG_DFL
import construct
import bcd_py
signal(SIGPIPE, SIG_DFL)

PROG_VERSION = "2021.130"


def print_container(container):
    keys = container.keys()
    for k in keys:
        if k in ['record_length',
                 'MP_factor_descaler_multiplier']:
            print("%s %s (HEX:%s)" %
                  (k, container[k], "{0:x}".format(container[k])))
        else:
            print k, container[k]

    print '-' * 80


def general_headers(sd):
    sd.process_general_headers()
    print '*' * 80
    print sd.infile
    print '*' * 80
    i = 1
    for ghb in sd.reel_headers.general_header_blocks:
        print("*** General Header Block %s ***" % i)
        print_container(ghb)
        i += 1


def channel_set_descriptors(sd):
    print "*** Channel Set Descriptor(s): ***"
    sd.process_channel_set_descriptors()
    i = 1
    for c in sd.reel_headers.channel_set_descriptor:
        print i
        i += 1
        print_container(c)


def extended_headers(sd):
    print "*** Extended Headers ***"
    sd.process_extended_headers()
    i = 1
    for c in sd.reel_headers.extended_headers:
        if len(sd.reel_headers.extended_headers) > 1:
            print i
        i += 1
        print_container(c)


def external_header(sd):
    print "*** External Header ***"
    sd.process_external_headers()
    print_container(sd.reel_headers.external_header)
    i = 1
    for c in sd.reel_headers.external_header_shot:
        print i
        i += 1
        print_container(c)


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

    trace = sd.read_trace(sd.samples)
    if 'fairprint' in os.environ:
        for s in trace:
            print s

    n += 1
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
        trace = sd.read_trace(sd.samples)
        if 'fairprint' in os.environ:
            for s in trace:
                print s

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


def get_segdreader():
    """
        get the segdreader from manufacture code infile
        or from second argument
    """
    KNOWN_CODE = {20: (segdreader, 'FairField'),
                  61: (segdreader_smartsolo, 'SmartSolo')}
    req_code_list = ["%s for %s format" % (k, KNOWN_CODE[k][1])
                     for k in KNOWN_CODE.keys()]
    req_code_str = ("Please give the second argument either "
                    ' or '.join(req_code_list))

    manu = read_manufacture_code(sys.argv[1])
    if manu in KNOWN_CODE.keys():
        reader = KNOWN_CODE[manu][0]
    else:
        try:
            manu = sys.argv[2]
            if manu in KNOWN_CODE.keys():
                reader = KNOWN_CODE[manu][0]
            else:
                print("The second argument {0} is not one of the known codes:"
                      " {1}.\n{2}".format(manu, KNOWN_CODE.keys(),
                                          req_code_str))
                raise Exception
        except IndexError:
            print("The manufacture code {0} is not one of the known codes:"
                  " {1}.\n{2}".format(manu, KNOWN_CODE.keys(), req_code_str))
            raise Exception
    return reader


def main():
    global RH, TH
    TH = []
    try:
        segd_reader = get_segdreader()
        RH = segd_reader.ReelHeaders()
        sd = segd_reader.Reader(infile=sys.argv[1])
        general_headers(sd)
        channel_set_descriptors(sd)
        extended_headers(sd)
        external_header(sd)
        trace_headers(sd)
        print "{0} bytes read.".format(sd.bytes_read)
    except Exception, e:
        print "Fail to read header due to error: ", e
        print "Usage: dumpsegd seg-d_file [format]"
        sys.exit()


if __name__ == '__main__':
    main()
