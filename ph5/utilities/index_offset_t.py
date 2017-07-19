#!/usr/bin/env pnpython2
#
#   Index offset table in ph5 file to speed up in kernal searches
#
#   Steve Azevedo, March 2012
#
import sys, os
from ph5.core import experiment

PROG_VERSION = "2012.069"

EX = None; PH5 = None; PATH = None

def get_args () :
    global PH5, PATH, NAME
    
    from optparse import OptionParser
    
    oparser = OptionParser ()
    
    oparser.usage = "Version: {0}\nindex_offset_t --nickname ph5-file-prefix".format (PROG_VERSION)
    
    oparser.add_option ("-n", "--nickname", dest = "ph5_file_prefix",
                        help = "The ph5 file prefix (experiment nickname).",
                        metavar = "ph5_file_prefix")
    
    oparser.add_option ("-p", "--path", dest = "ph5_path",
                        help = "Path to ph5 files. Defaults to current directory.",
                        metavar = "ph5_path")
    
    oparser.add_option ("-t", "--offset_table", dest = "offset_table_name",
                        help = "The name of the offset table. Example: Offset_t_001_003.",
                        metavar="offset_table_name")
    
    options, args = oparser.parse_args ()
    
    if options.ph5_file_prefix != None :
        PH5 = options.ph5_file_prefix
    else :
        PH5 = None
        
    if options.ph5_path != None :
        PATH = options.ph5_path
    else :
        PATH = "."
        
    NAME = options.offset_table_name
        
#
#   Initialize ph5 file
#
def initialize_ph5 (editmode = False) :
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5
    try: 
        EX = experiment.ExperimentGroup (PATH, PH5)
        EX.ph5open (editmode)
        EX.initgroup ()
    except Exception:
        print "Cannot open PH5 file. Use -h argument for help."
        sys.exit()

def info_print () :
    global EX
    
    print "#\n#\t%s\tph5 version: %s\n#" % (time.ctime (time.time ()), EX.version ())
#
#   Print Rows_Keys
#
def table_print (t, a) :
    global TABLE_KEY
    i = 0
    #   Loop through table rows
    for r in a.rows :
        i += 1
        print "#   Table row %d" % i
        #   Print table name
        if TABLE_KEY in a.keys :
            print "{0}:Update:{1}".format (t, TABLE_KEY)
        else :
            print t
        #   Loop through each row column and print
        for k in a.keys :
            print "\t", k, "=", r[k]


def main():
        
    get_args ()
    
    initialize_ph5 (True)
    
    #   index on event_id_s and receiver_id_s
    EX.ph5_g_sorts.index_offset_table (name=NAME)
    
    EX.ph5close ()

  
if __name__ == '__main__' :
    main()
    
