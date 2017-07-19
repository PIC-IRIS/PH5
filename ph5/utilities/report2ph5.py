#!/usr/bin/env pnpython3

from ph5.core import experiment, kef, columns
import numpy, sys, os.path, re, array, string, time

PROG_VERSION = '2013.347'

updateRE = re.compile ("(/.*):Update:(.*)\s*")

def get_args () :
    '''
       Parse input arguments
          -k   kef file
          -r   report file
          -n   nickname
          -p   path
    '''
    global FILE, KEF, PH5, PATH
    
    err = False
    PATH = '.'
    KEF = None
    
    from optparse import OptionParser
    oparser = OptionParser ()
    
    oparser.usage = "report2ph5 --file report-file --nickname experiment-nickname [--path path-to-kef-file][--kef kef-file]"
    oparser.description = "Load a report (pdf) into a ph5 file."
    oparser.add_option ("-f", "--file", dest = "report_file",
                        help = "The file containing the report, (pdf, doc, ps, etc.).")
    oparser.add_option ("-k", "--kef", dest = "kef_file",
                        help = "Kef file describing row in Report_t for the report. Not required.")
    oparser.add_option ("-n", "--nickname", dest = "nickname",
                        help = "Experiment nickname.")
    oparser.add_option ("-p", "--path", dest = "path",
                        help = "Path to where ph5 files are stored")
    options, args = oparser.parse_args ()
    
    if options.report_file != None :
        FILE = options.report_file
        if not os.path.exists (FILE) :
            sys.stderr.write ("Error: %s does not exist!\n" % FILE)
            sys.exit (-1)
    else :
        err = True
        
    if options.kef_file != None :
        KEF = options.kef_file
        if not os.path.exists (KEF) :
            sys.stderr.write ("Error: %s does not exist!\n" % KEF)
            sys.exit (-2)
        
    if options.nickname != None :
        PH5 = options.nickname
    else :
        err = True
        
    if options.path != None :
        PATH = options.path
        
    if err == True :
        sys.stderr.write ("Error: Missing required option. Try --help\n")
        sys.exit (-3)
        
    #if not os.path.exists (os.path.join (PATH, PH5) + '.ph5') :
        #sys.stderr.write ("Error: %s does not exist.\n" % (os.path.join (PATH, PH5) + 'ph5'))
        #sys.exit (-4)
        
def initializeExperiment () :
    global EX, PH5, PATH
    
    EX = experiment.ExperimentGroup (currentpath = PATH, nickname = PH5)
    EDIT = True
    EX.ph5open (EDIT)
    EX.initgroup ()
    
def update () :
    global EX, ARRAY_NAME, KEF
    #   There is a bug in batch update that kills kv
    k = kef.Kef (KEF)
    k.open ()
    k.read ()
    #k.batch_update ()
    #k.close () ; sys.exit ()
    k.rewind ()
    ARRAY_NAME = None
    while 1 :
        p, kv = k.next ()
        if not p : break
        if kv.has_key ('array_name_a') :
            ARRAY_NAME = kv['array_name_a']
        else :
            sys.stderr.write ("Error: Kef file does not contain entry for array_name_a.\nCan not continue!\n")
            return False
        
        #   XXX   We always append   XXX
        #mo = updateRE.match (p)
        ref = EX.ph5_g_reports.ph5_t_report
        if not columns.TABLES.has_key (p) :
            sys.stderr.write ("Warning: No table reference for key: %s\n" % p)
            sys.stderr.write ("Possibly ph5 file is not open or initialized?\n")
            
        key = []
        errs_keys, errs_required = columns.validate (ref, kv, key)
        for e in errs_keys + errs_required : sys.stderr.write (e + '\n')
        
        key = None
        columns.populate (ref, kv, key)
        
    return True
        
def load_report () :
    global ARRAY_NAME
    import numpy as np
    #   XXX
    if not ARRAY_NAME :
        sys.stderr.write ("Error: It appears that 'array_name_a' is not set in kef file\n")
        sys.exit ()
        
    fh = open (FILE)
    buf = fh.read ()
    fh.close ()
    #print len (buf)
    
    EX.ph5_g_reports.newarray (ARRAY_NAME, buf)
    
def get_input (prompt, default = None) :
    
    if default == None :
        default = ''
        
    while 1 :
        val = raw_input (prompt + " [" + default + "]: ")
        if val == '' and default != '' :
            val = default
            break
        elif val != '' :
            break
        
    return val
    
def get_kef_info () :
    global EX, FILE, KEF
    
    base = os.path.basename (FILE)
    
    title, suffix = string.split (base, '.')
    suffix = string.upper (suffix)
    
    array = EX.ph5_g_reports.nextName ()
    
    title = get_input ("Report title", title)
    suffix = get_input ("File suffix", suffix)
    array = get_input ("Internal array name", array)
    
    description = get_input ("File description")
    
    kef = array + ".kef"
    print "Writing: %s" % kef
    fh = open (kef, 'w+')
    fh.write ("#   %s   report2ph5 version: %s   ph5 version: %s\n" % (time.ctime (time.time ()), PROG_VERSION, EX.version ()))
    fh.write ("/Experiment_g/Reports_g/Report_t\n")
    fh.write ("\tarray_name_a = %s\n" % array)
    fh.write ("\ttitle_s = %s\n" % title)
    fh.write ("\tformat_s = %s\n" % suffix)
    fh.write ("\tdescription_s = %s\n" % description)
    
    fh.close ()
    
    KEF = kef


def main():
    global FILE, KEF, PATH, PH5, EX
    get_args ()
    initializeExperiment ()

    #   If there is no kef file prompt for its contents.
    if KEF == None :
        get_kef_info ()
        
    if not update () :
        sys.exit (-1)
            
    load_report ()
    
    #buf = EX.ph5_g_reports.get_report ('Report_a_005')
    #hf = open ('junk.png', 'w+')
    #hf.write (buf)
    #   Read report into an array, populate ph5
    #   Read kef file and populate ph5
    #   Close ph5
    EX.ph5close ()

        
if __name__ == '__main__' :
    main()
