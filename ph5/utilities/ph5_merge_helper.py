#!/usr/bin/env pnpython3
#
#   A program to aid merging multiple families of ph5 files, ie if you have mulitple
#   deployment sites in a single experiment.
#
#   Steve Azevedo, February 2014
#

import os, sys, re
from subprocess import call

PROG_VERSION = '2016.144'

miniPH5RE = re.compile (".*miniPH5_(\d\d\d\d\d)\.ph5")

#   Index of first miniPH5_xxxxx.ph5 file (value of xxxxx)
FIRST_MINI_INDEX = 0
#   Dictionary, key = original miniPH5_xxxxx.ph5 file name,
#               value = new miniPH5_xxxxx.ph5 file name.
OLD_NEW = None
#
#   Read Command line arguments
#
def get_args () :
    '''   Get program args:
          -s new_miniPH5_xxxxx.ph5 index (ie value of xxxxx)
    '''
    global FIRST_MINI_INDEX
    
    from optparse import OptionParser
    
    oparser = OptionParser ()
    
    oparser.usage = "ph5_merge_helper [-s miniPH5_start_index]"
    
    oparser.description = "Modify Index_t.kef and miniPH5_xxxxx.ph5 file names so they can be merged."
    
    oparser.add_option ("-s", dest = "mini_ph5_index",
                        help = "For the first miniPH5_xxxxx.ph5, xxxxx should equal the given value.",
                        metavar = "mini_ph5_index", action='store', type='int')
    
    oparser.add_option ("-d", dest = "debug", action = "store_true", default = False)
    
    options, args = oparser.parse_args ()
    
    if options.mini_ph5_index :
        FIRST_MINI_INDEX = options.mini_ph5_index
        
def dump_Index_t () :
    '''   Dump Index_t.kef from master.ph5   '''
    command = "table2kef -n master.ph5 -I 2>&1 > Index_t.kef"
    ret = call (command, shell = True)
    if ret < 0 :
        sys.stderr.write ("Error: Failed to read master.ph5, {0}\n".format (ret))
        sys.exit ()
        
def resequence_Index_t () :
    '''   Set the value of external_file_name_s based on FIRST_MINI_INDEX in Index_t.kef   '''
    global OLD_NEW
    
    OLD_NEW = {}
    
    try :
        fh = open ('Index_t.kef', 'rU')
        of = open ('_Index_t.kef', 'w')
    except Exception as e :
        sys.stderr.write ("Error: Failed to open 'Index_t.kef', {0}\n".format (e))
        sys.exit ()
        
    while 1 :
        line = fh.readline ()
        if not line : 
            break
        if line[0] != '\t' :
            of.write (line)
            continue
        
        flds = line.split ('=')
        key = flds[0].strip ()
        if key != 'external_file_name_s' :
            of.write (line)
            continue
        
        value = flds[1].strip ()
        m = miniPH5RE.match (value)
        if m :
            n = int (m.groups ()[0])
            #print n, FIRST_MINI_INDEX
            n = n + FIRST_MINI_INDEX - 1
            OLD_NEW[value] = "miniPH5_{0:05d}.ph5".format (n)
            of.write ("\texternal_file_name_s=./{0}\n".format (OLD_NEW[value]))
            
    fh.close (); of.close ()
    command = "mv _Index_t.kef Index_t" + str (FIRST_MINI_INDEX) + ".kef 2>&1 > /dev/null"
    ret = call (command, shell = True)
    if ret < 0 :
        sys.stderr.write ("Error: Index_t.kef may not be correct.\n")
    
def rename_miniPH5 () :
    '''   Rename miniPH5_xxxxx.ph5 files based on new starting index.   '''
    olds = OLD_NEW.keys ()
    for o in olds :
        command = "mv {0} {1} 2>&1 > /dev/null".format (o, OLD_NEW[o])
        print command
        ret = call (command, shell = True)
        if ret < 0 :
            sys.stderr.write ("File rename may have failed.\n")


def main():
    get_args ()
    dump_Index_t ()
    resequence_Index_t ()
    rename_miniPH5 ()


if __name__ == '__main__' :
    main()
