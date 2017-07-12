#!/usr/bin/env pnpython4
#
#   Sort an Array_t_xxx.kef file by station ID, id_s.
#
#   Steve Azevedo, Feb 2017
#

import os, sys, re
from ph5.core import Kefx

PROG_VERSION = "2017.033"

if __name__ == "__main__" :
    nodeIDRE = re.compile ("\d+X\d+")
    try :
        kefin = sys.argv[1]
        kx = Kefx.Kef (kefin)
        kx.open ()
    except :
        print "Version: {0} Usage: sort_array_t Array_t_unsorted.kef > Array_t_sorted.kef".format (PROG_VERSION)
        sys.exit ()
    
    kx.read ()
    kx.rewind ()
    kx.ksort ('id_s')
    kx.rewind ()
    for p, kv in kx :
        if nodeIDRE.match (kv['id_s']) :
            kv['id_s'] = kv['id_s'].split ('X')[1]
        Kefx.print_kef (p, kv)