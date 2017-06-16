#!/usr/bin/env pnpython3

import firfilt_py

PROG_VERSION = "2013.261"

def decimate (decfacts, data_in) :
    n = len (data_in)
    #print "In: ", n,
    data_out = firfilt_py.decimate (data_in, n, decfacts)
    #print "Out: ", len (data_out)
    samp_shift = data_out[-1]
    
    return samp_shift, data_out[:-1]

if __name__ == '__main__' :
    import math as m
    import sys
    ts = []
    #   build a 36000 sample sine wave
    for i in range (36000) :
        val =  int(m.sin (m.radians (i)) * 1000.)
        ts.append (val)
        
    #   Decimate by a factor of 2 X 4 X 5 = 40
    shift, data = decimate ('2,4,5', ts)
    sys.stderr.write ("Shift: %d\n" % shift)
    for d in data :
        print d