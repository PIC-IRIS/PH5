#!/usr/bin/env pnpython3
#
#   Recreate external references under Receivers_g, and Maps_g from Index_t
#
#   Steve Azevedo, September 2012
#
import os, sys, time
from ph5.core import experiment

PROG_VERSION='2016.307'
INDEX_T = {}
M_INDEX_T = {}
PATH = None
PH5 = None

os.environ['TZ'] = 'UTM'
time.tzset ()
#
#   To hold table rows and keys
#
class Rows_Keys (object) :
    __slots__ = ('rows', 'keys')
    def __init__ (self, rows = None, keys = None) :
        self.rows = rows
        self.keys = keys
        
    def set (self, rows = None, keys = None) :
        if rows != None : self.rows = rows
        if keys != None : self.keys = keys
 
#       
def read_index_table () :
    global EX, INDEX_T
    
    rows, keys = EX.ph5_g_receivers.read_index ()
    INDEX_T = Rows_Keys (rows, keys)        
#        
def read_m_index_table () :
    global EX, M_INDEX_T
    
    rows, keys = EX.ph5_g_maps.read_index ()
    M_INDEX_T = Rows_Keys (rows, keys)        
#        
def update_external_references () :
    global EX, INDEX_T
    
    sys.stderr.write ("Updating external references..."); sys.stderr.flush ()
    #logging.info ("Updating external references...")
    n = 0
    for i in INDEX_T.rows :
        external_file = i['external_file_name_s']
        external_path = i['hdf5_path_s']
        das = i['serial_number_s']
        target = external_file + ':' + external_path
        external_group = external_path.split ('/')[3]
        print external_file, external_path, das, target, external_group
        
        #   Nuke old node
        try :
            group_node = EX.ph5.get_node (external_path)
            group_node.remove ()
        except Exception, e :
            
            print "E1 ", e.message
            
        #   Re-create node
        try :
            EX.ph5.create_external_link ('/Experiment_g/Receivers_g', external_group, target)
            n += 1
        except Exception, e :
            
            print "E2 ", e.message
            
    m = 0
    for i in M_INDEX_T.rows :
        external_file = i['external_file_name_s']
        external_path = i['hdf5_path_s']
        das = i['serial_number_s']
        target = external_file + ':' + external_path
        external_group = external_path.split ('/')[3]
        print external_file, external_path, das, target, external_group
        
        #   Nuke old node
        try :
            group_node = EX.ph5.get_node (external_path)
            group_node.remove ()
        except Exception, e :
            
            print "E3 ", e.message
            
        #   Re-create node
        try :
            EX.ph5.create_external_link ('/Experiment_g/Maps_g', external_group, target)
            m += 1
        except Exception, e :
            
            print "E4 ", e.message        
            
        #sys.exit ()
    sys.stderr.write ("done, Index_t {0} nodes recreated. M_Index_t {1} nodes recreated.\n".format (n, m))
    #logging.info ("done, {0} nodes recreated.\n".format (n))
    
#
#   Initialize ph5 file
#
def initialize_ph5 (editmode = False) :
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5
    
    EX = experiment.ExperimentGroup (PATH, PH5)
    EX.ph5open (True)
    EX.initgroup ()
    
#
#   Read Command line arguments
#
def get_args () :
    global PH5, PATH
    
    from optparse import OptionParser
    
    oparser = OptionParser ()
    
    oparser.usage = "recreate_external_references --nickname=ph5-file-prefix"
    
    oparser.description = "Version: {0} Rebuild external references under Receivers_g from info in Index_t.".format (PROG_VERSION)
    
    oparser.add_option ("-n", "--nickname", dest = "ph5_file_prefix",
                        help = "The ph5 file prefix (experiment nickname).",
                        metavar = "ph5_file_prefix")
    
    oparser.add_option ("-p", "--path", dest = "ph5_path",
                        help = "Path to ph5 files. Defaults to current directory.",
                        metavar = "ph5_path")
    
    options, args = oparser.parse_args ()
    
    if options.ph5_file_prefix != None :
        PH5 = options.ph5_file_prefix
    else :
        PH5 = None
        
    if options.ph5_path != None :
        PATH = options.ph5_path
    else :
        PATH = "."

        
    if PH5 == None :
        sys.stderr.write ("Error: Missing required option --nickname. Try --help\n")
        sys.exit (-1)


def main():
    get_args ()
    initialize_ph5 ()
    read_index_table ()
    read_m_index_table ()
    update_external_references ()


if __name__ == '__main__' :
    main()
