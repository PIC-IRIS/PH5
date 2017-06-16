#!/usr/bin/env pnpython3

import os, sys
import Kef

PROG_VERSION = "2014.038.a"

def belch_kef (a) :
    arrays = a.keys ()
    arrays.sort ()
    for array in arrays :
        stations = a[array].keys ()
        stations.sort ()
        for station in stations :
            print array
            kv = a[array][station]
            keys = kv.keys ()
            keys.sort ()
            for k in keys :
                print "\t{0} = {1}".format (k, kv[k])

if __name__ == '__main__' :
    try :
        k = Kef.Kef (sys.argv[1])
        k.open (); k.read (); k.rewind ()
    except Exception as e :
        sys.stderr.write ("Usage: sort-recv-kef recv_only_kef_file.dep > sorted_kef_file.dep\n{0}".format (e))
        sys.exit ()
        
    ARRAY = {}
    p, kv = k.next ()
    while p :
        array = p
        station = int (kv['id_s'])
        if not ARRAY.has_key (array) :
            ARRAY[array] = {}
            
        ARRAY[array][station] = kv
        
        p, kv = k.next ()
        
    belch_kef (ARRAY)