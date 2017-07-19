#!/usr/bin/env pnpython3
#
#   Dump Fairfield SEG-D header values
#
#   Steve Azevedo, October 2014
#
import sys, os
from ph5.core import segdreader

PROG_VERSION = "2017.199"

def print_container (container) :
    keys = container.keys ()
    for k in keys :
        print k, container[k]
        
    print '-' * 80

def general_headers (sd) :
    sd.process_general_headers ()
    print '*' * 80
    print sd.infile
    print '*' * 80
    print "*** General Header Block 1 ***"
    print_container (sd.reel_headers.general_header_block_1)
    print "*** General Header Block 2 ***"
    print_container (sd.reel_headers.general_header_block_2)
    
def channel_set_descriptors (sd) :
    print "*** Channel Set Descriptor(s): ***"
    sd.process_channel_set_descriptors ()
    i = 1
    for c in sd.reel_headers.channel_set_descriptor :
        print i; i += 1
        print_container (c)
        
def extended_headers (sd) :
    print "*** Extended Headers ***"
    sd.process_extended_headers ()
    n = sd.extended_header_blocks
    if n > 0 :
        print_container (sd.reel_headers.extended_header_1)
        n -= 1
    else : return
    if n > 0 :
        print 2
        print_container (sd.reel_headers.extended_header_2)
        n -= 1
    else : return
    if n > 0 :
        print 3
        print_container (sd.reel_headers.extended_header_3)
        
    i = 1
    for c in sd.reel_headers.extended_header_4 :
        print i; i += 1
        print_container (c)
        
def external_header (sd) :
    print "*** External Header ***"
    sd.process_external_headers ()
    print_container (sd.reel_headers.external_header)
    i = 1
    for c in sd.reel_headers.external_header_shot :
        print i; i += 1
        print_container (c)
    n = 1
    
def trace_headers (sd) :
    n = 1
    print "*** Trace Header ***", n
    
    sd.process_trace_headers ()
    print_container (sd.trace_headers.trace_header)
    i = 1
    for c in sd.trace_headers.trace_header_N :
        print i; i += 1
        print_container (c)
        
    trace = sd.read_trace (sd.samples)
    #for s in trace :
        #print s
    #n += 1
    while True :
        if sd.isEOF () :
            break
        print "*** Trace Header ***", n
        sd.process_trace_headers ()
        print_container (sd.trace_headers.trace_header)
        i = 1
        for c in sd.trace_headers.trace_header_N :
            print i; i += 1
            print_container (c)
        
        n += 1    
        trace = sd.read_trace (sd.samples)
        #for s in trace :
            #print s    
            
    print "There were {0} traces.".format (n)


def main():
    global RH, TH
    TH = []
    
    RH = segdreader.ReelHeaders () 
    try :
        sd = segdreader.Reader (infile=sys.argv[1])
    except :
        print "Usage: dumpfair fairfield_seg-d_file.rg16"
        sys.exit ()
    
    general_headers (sd)
    channel_set_descriptors (sd)
    extended_headers (sd)
    external_header (sd)
    trace_headers (sd)
    print "{0} bytes read.".format (sd.bytes_read)


if __name__ == '__main__' :
    main()
