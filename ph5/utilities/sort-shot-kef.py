#!/usr/bin/env pnpython3

import os, sys
from ph5.core import Kef

PROG_VERSION = "2014.038.a"

def belch_kef (a) :
    shots = a.keys ()
    shots.sort ()
    for s in shots :
        print '/Experiment_g/Sorts_g/Event_t'
        kv = a[s]
        keys = kv.keys ()
        keys.sort ()
        for k in keys :
            print "\t{0} = {1}".format (k, kv[k])

if __name__ == '__main__' :
    try :
        k = Kef.Kef (sys.argv[1])
        k.open (); k.read (); k.rewind ()
    except Exception as e :
        sys.stderr.write ("Usage: sort-shot-kef shot_only_kef_file.kef > sorted_kef_file.kef\n{0}".format (e))
        sys.exit ()
        
    SHOT = {}
    p, kv = k.next ()
    while p :
        station = int (kv['id_s'])
            
        SHOT[station] = kv
        
        p, kv = k.next ()
        
    belch_kef (SHOT)