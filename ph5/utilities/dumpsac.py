#!/usr/bin/env pnpython3

#
#   Translate and dump a binary SAC file to stdout
#
#   December 2013, Steve Azevedo
#

import sys, os
from ph5.core import sacreader
import construct
import numpy as np

PROG_VERSION = "2013.365.a"

def get_args () :
    global INFILE, PRINT, ENDIAN
    
    from optparse import OptionParser
    oparser = OptionParser ()
    
    oparser.usage = "Version: {0} Usage: dumpsac [options]".format (PROG_VERSION)
    
    oparser.add_option ("-f", action="store", dest="infile", type="string")
    
    oparser.add_option ("-p", action="store_true", dest="print_true", default=False)
    
    options, args = oparser.parse_args ()
    
    if options.infile != None :
        INFILE = options.infile
    else :
        sys.stderr.write ("No infile given.\n")
        sys.exit ()
        
    PRINT = options.print_true
        
def print_it (header) :
    try :
        keys = header.keys ()
        keys.sort ()
        for k in keys : print "{0:<12}\t{1:<12}".format (k, header[k])
    except AttributeError :
        for t in header : print t


def main():
    get_args ()
    sr = sacreader.Reader (infile=INFILE)
    print "Endianness: {0}".format (sr.endianness)
    print "+------------+"
    print "|Float Header|"
    print "+------------+"
    print_it (sr.read_float_header ())
    print "+--------------+"
    print "|Integer Header|"
    print "+--------------+"
    ret = sr.read_int_header ()
    print_it (ret)
    print "+----------------+"
    print "|Character Header|"
    print "+----------------+"
    print_it (sr.read_char_header ())
    if PRINT :
        print "+-----+"
        print "|Trace|"
        print "+-----+"
        print_it (sr.read_trace (ret['npts']))
    
if __name__ == '__main__' :
    main()