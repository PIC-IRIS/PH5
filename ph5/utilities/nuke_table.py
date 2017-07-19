#!/usr/bin/env pnpython3
#
#   Program to re-initialize a table in a ph5 file.
#
#   Steve Azevedo, February 2013
#

import os, sys
from ph5.core import experiment, columns

PROG_VERSION = '2016.307'

#
#   Read Command line arguments
#
def get_args () :
    global PH5, PATH, DEBUG, EXPERIMENT_TABLE, SORT_TABLE, OFFSET_TABLE, EVENT_TABLE, \
           ARRAY_TABLE, RESPONSE_TABLE, REPORT_TABLE, RECEIVER_TABLE, TIME_TABLE, \
           INDEX_TABLE, DAS_TABLE, M_INDEX_TABLE
    
    from optparse import OptionParser
    
    oparser = OptionParser ()
    
    oparser.usage = "Version: {0}\nnuke-table --nickname ph5-file-prefix options".format (PROG_VERSION)
    
    oparser.description = "Initialize a table in a ph5 file. Caution: Deletes contents of table!"
    
    oparser.add_option ("-n", "--nickname", dest = "ph5_file_prefix",
                        help = "The ph5 file prefix (experiment nickname).",
                        metavar = "ph5_file_prefix")
    
    oparser.add_option ("-p", "--path", dest = "ph5_path",
                        help = "Path to ph5 files. Defaults to current directory.",
                        metavar = "ph5_path")
    
    oparser.add_option ("-d", dest = "debug", action = "store_true", default = False)
    
    oparser.add_option ("-E", "--Experiment_t", dest = "experiment_t", action = "store_true",
                        default = False,
                        help = "Nuke /Experiment_g/Experiment_t.")
    
    oparser.add_option ("-S", "--Sort_t", dest = "sort_t", action = "store_true",
                        default = False,
                        help = "Nuke /Experiment_g/Sorts_g/Sort_t.")
    
    oparser.add_option ("-O", "--Offset_t", dest = "offset_t_", metavar="a_e",
                        help = "Nuke /Experiment_g/Sort_g/Offset_t_[arrayID_eventID] to a kef file.")
    
    oparser.add_option ("-V", "--Event_t", dest = "event_t_", metavar = "n",
                        type = int,
                        help = "Nuke /Experiment_g/Sorts_g/Event_t_[n]. Use 0 for Event_t")
    
    oparser.add_option ("-A", "--Array_t_", dest = "array_t_", metavar = "n",
                        help = "Nuke /Experiment_g/Sorts_g/Array_t_[n].",
                        type = int)
    
    oparser.add_option ("-R", "--Response_t", dest = "response_t", action = "store_true",
                        default = False,
                        help = "Nuke /Experiment_g/Responses_g/Response_t.")
    
    oparser.add_option ("-P", "--Report_t", dest = "report_t", action = "store_true",
                        default = False,
                        help = "Nuke /Experiment_g/Reports_g/Report_t.")
    
    oparser.add_option ("-C", "--Receiver_t", dest = "receiver_t", action = "store_true",
                        default = False,
                        help = "Nuke /Experiment_g/Receivers_g/Receiver_t.")
    
    oparser.add_option ("-I", "--Index_t", dest = "index_t", action = "store_true",
                        default = False,
                        help = "Nuke /Experiment_g/Receivers_g/Index_t.")
    
    oparser.add_option ("-M", "--M_Index_t", dest = "m_index_t", action = "store_true",
                            default = False,
                            help = "Nuke /Experiment_g/Maps_g/Index_t.")    
    
    oparser.add_option ("-D", "--Das_t", dest = "das_t_", metavar = "das",
                        help = "Nuke /Experiment_g/Receivers_g/Das_g_[das]/Das_t.")
    
    oparser.add_option ("-T", "--Time_t", dest = "time_t", action = "store_true",
                        default = False,
                        help = "Nuke /Experiment_g/Receivers_g/Time_t.")
    
    options, args = oparser.parse_args ()
    
    
    if options.ph5_file_prefix != None :
        PH5 = options.ph5_file_prefix
    else :
        PH5 = None
        
    if options.ph5_path != None :
        PATH = options.ph5_path
    else :
        PATH = "."
        
    if options.debug != None :
        DEBUG = options.debug
        
    EXPERIMENT_TABLE = options.experiment_t
    SORT_TABLE = options.sort_t
    if options.offset_t_ != None :
        try :
            OFFSET_TABLE = map (int, options.offset_t_.split ("_"))
        except Exception as e :
            sys.stderr.write ("Offset table should be entered as arrayID underscore shotLineID, eg. 1_2 or 0_0.")
            sys.stderr.write (e.message)
            sys.exit ()
    else :
        OFFSET_TABLE = None    
    EVENT_TABLE = options.event_t_
    TIME_TABLE = options.time_t
    INDEX_TABLE = options.index_t
    M_INDEX_TABLE = options.m_index_t
    
    if options.array_t_ != None :
        ARRAY_TABLE = options.array_t_
    else :
        ARRAY_TABLE = None
        
    RESPONSE_TABLE = options.response_t
    REPORT_TABLE = options.report_t
    
    RECEIVER_TABLE = options.receiver_t
        
    if options.das_t_ != None :
        DAS_TABLE = options.das_t_
    else :
        DAS_TABLE = None
        
    if PH5 == None :
        sys.stderr.write ("Error: Missing required option. Try --help\n")
        sys.exit (-1)

#
#   Initialize ph5 file
#
def initialize_ph5 (editmode = True) :
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5
    
    EX = experiment.ExperimentGroup (PATH, PH5)
    EX.ph5open (editmode)
    EX.initgroup ()


##
##   Print Rows_Keys
##
#def table_print (t, a) :
    #global TABLE_KEY
    #global PATH
    #global EX
    #i = 0
    #s=''
    #s=s+"#\n#\t%s\tph5 version: %s\n#\n" % (time.ctime (time.time ()), EX.version ())
    ##   Loop through table rows
    #for r in a.rows :
        #i += 1
        
        #s= s+"#   Table row %d\n" % i
        ##   Print table name
        #if TABLE_KEY in a.keys :
            #s=s+ "{0}:Update:{1} \n".format (t, TABLE_KEY)
        #else :
            #s=s+ t+"\n"
        ##   Loop through each row column and print
        #for k in a.keys :
            #s=s+"\t" + str(k) + "=" + str(r[k])+"\n"
    #print s
    #f=open(PATH+"/temp.kef", "w")
    #f.write(s)


def main():
    get_args ()
    initialize_ph5 ()
    #   /Experiment_g/Experiment_t
    if EXPERIMENT_TABLE :
        EX.nuke_experiment_t ()
    #   /Experiment_g/Sorts_g/Sort_t
    if SORT_TABLE :
        EX.ph5_g_sorts.nuke_sort_t ()
    #   /Experiment_g/Sorts_g/Offset_t
    if OFFSET_TABLE != None :
        if OFFSET_TABLE[0] == 0 :
            if EX.ph5_g_sorts.nuke_offset_t () :
                print "{0} I am become Death, the Destroyer of Worlds.".format (OFFSET_TABLE)
            else :
                print "{0} Not found.".format (OFFSET_TABLE)                
        else :
            if EX.ph5_g_sorts.nuke_offset_t ("Offset_t_{0:03d}_{1:03d}".format (OFFSET_TABLE[0], OFFSET_TABLE[1])) :
                print "{0} I am become Death, the Destroyer of Worlds.".format (OFFSET_TABLE)
            else :
                print "{0} Not found.".format (OFFSET_TABLE)                
    #   /Experiment_g/Sorts_g/Event_t
    if EVENT_TABLE != None :
        if EVENT_TABLE == 0 :
            EX.ph5_g_sorts.nuke_event_t ()
        else :
            if EX.ph5_g_sorts.nuke_event_t ("Event_t_{0:03d}".format (EVENT_TABLE)) :
                print "{0} I am become Death, the Destroyer of Worlds.".format (EVENT_TABLE)
            else :
                print "{0} Not found.".format (EVENT_TABLE)                
    #   /Experiment_g/Sorts_g/Array_t_xxx
    if ARRAY_TABLE :
        if EX.ph5_g_sorts.nuke_array_t (ARRAY_TABLE) :
            print "{0} I am become Death, the Destroyer of Worlds.".format (ARRAY_TABLE)
        else :
            print "{0} Not found.".format (ARRAY_TABLE)
            
    #   /Experiment_g/Receivers_g/Time_t
    if TIME_TABLE :
        EX.ph5_g_receivers.nuke_time_t ()
    #   /Experiment_g/Receivers_g/Index_t
    if INDEX_TABLE :
        EX.ph5_g_receivers.nuke_index_t ()
    #   /Experiment_g/Maps_g/Index_t
    if M_INDEX_TABLE :
        EX.ph5_g_maps.nuke_index_t ()
    #   /Experiment_g/Receivers_g/Receiver_t
    if RECEIVER_TABLE :
        EX.ph5_g_receivers.nuke_receiver_t ()
    #   /Experiment_g/Responses_g/Response_t
    if RESPONSE_TABLE :
        EX.ph5_g_responses.nuke_response_t ()
    #   /Experiment_g/Reports_g/Report_t
    if REPORT_TABLE :
        EX.ph5_g_reports.nuke_report_t ()
    #   
    if DAS_TABLE :
        yon = raw_input ("Are you sure you want to delete all data in Das_t for das {0}? y/n ".format (DAS_TABLE))
        if yon == 'y' :
            EX.ph5_g_receivers.nuke_das_t (DAS_TABLE)
            
    EX.ph5close ()


if __name__ == '__main__' :
    main()
        