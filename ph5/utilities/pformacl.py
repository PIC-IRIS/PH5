#!/usr/bin/env pnpython3
#
#   Load PH5 from RAW in parallel
#
#   Steve Azevedo, August 2015
#
import os, sys

from ph5.utilities import pforma_io

PROG_VERSION = "2016.049 Developmental"

def get_args () :
    global JSON_DB, JSON_CFG, RAW_LST, PROJECT, NFAMILY, M, MERGE, UTM, TSPF

    from optparse import OptionParser
    from multiprocessing import cpu_count

    oparser = OptionParser ()
    oparser.usage = "Version %s: pforma --project_home=/path/to/project --files=list_of_raw_files [options] | --project_home=/path/to/project --merge" % PROG_VERSION
    oparser.description = "Create or open a project and process raw data to PH5 in parallel."
    
    oparser.add_option ("-f", "--files", dest = "infile",
                        help = "File containing list of raw file names.",
                        metavar = "file_list_file")
    oparser.add_option ("-p", "--project_home", dest = "home",
                        help = "Path to project directory.")
    oparser.add_option ("-n", "--num_families", dest = "nfamilies",
                        help = "Number of PH5 families to process. Defaults to number of CPU's + 1 else number of raw files.",
                        type='int')
    oparser.add_option ("-M", "--num_minis", dest = "num_minis",
                        help = "Number of mini ph5 files per family.",
                        type='int')
    oparser.add_option ("-U", dest = "utm",
                        help = "The UTM zone if required for SEG-D conversion.",
                        type='int')
    oparser.add_option ("-T", "--TSPF", dest="tspf",
                        help = "Coordinates is texas state plane coordinates (SEG-D).",
                        action="store_true", default=False)
    oparser.add_option ("-m", "--merge", dest = "merge_minis",
                        help="Merge all families to one royal family in A.",
                        action="store_true", default=False)
    
    options, args = oparser.parse_args()
    
    if options.infile and options.merge_minis :
        sys.stderr.write ("Error: Loading and merging must be done as seperate operations. Exiting.\n")
        sys.exit (1)
        
    if options.infile != None and not os.path.exists (options.infile):
        sys.stderr.write ("Error: Can not find {0}.\n".format (options.infile))
        sys.exit (1)
    else :
        RAW_LST = options.infile
        
    if options.home == None :
        sys.stderr.write ("Error: Project home required, --project_home. Exiting.")
        sys.exit (1)
    else :
        PROJECT = options.home
        
    #JSON_DB = os.path.join (PROJECT, "pforma.json")
    #JSON_CFG = os.path.join (PROJECT, "pforma.cfg")
    if options.nfamilies == None :
        NFAMILY = cpu_count () + 1
    else :
        NFAMILY = options.nfamilies
    M = options.num_minis
    UTM = options.utm
    TSPF = options.tspf
    MERGE = options.merge_minis
    
def exexists (exe) :
    import distutils.spawn as s
    if s.find_executable (exe) :
        return True
    else :
        return False
    
def adjust (fio) :
    if fio.number_raw <= len (fio.nmini) :
        print "The number of raw files is small compared to number of families!"
        yn = raw_input ("Adjust number of families and M within family? (y/n) ")
        if yn == 'y' :
            fio.set_nmini (fio.number_raw)
            fio.set_M (1)
            
def run (fio) :
    import subprocess
    #
    ###   cmds -> cmds[Family] => List of commands to execute
    ###   pees -> pees[Family] => Subprocess
    ###   i -> The index of the list of commands that is running
    #   XXX   Debug 
    cmds, pees, i = fio.run ()
    ###
    l = {'A':i, 'B':i, 'C':i, 'D':i, 'E':i, 'F':i, 'G':i, 'H':i, 'I':i, 'J':i, 'K':i, 'L':i, 'M':i, 'N':i, 'O':i, 'P':i}
    cnt = 0
    out = {}; err = {}; fifo = {}
    xterms = {}
    running = True
    for m in fio.nmini :
        fifo[m] = "/tmp/fifo{0}".format (m)
        if not os.path.exists (fifo[m]) :
            os.mkfifo (fifo[m])
            
        xterms[m] = subprocess.Popen (['xterm', '-geometry', '80X3', '-T', m,  '-e', 'tail', '-f', fifo[m]])
        
    while running :
        running = False
        for m in fio.nmini :    
            if pees[m] == None :
                continue
            #print m, pees[m].pid, 'running' if pees[m].poll () == None else pees[m].poll ()
            if pees[m].poll () == 0 :
                #pees[m].kill ()
                l[m] += 1
                t, l[m] = fio.run_cmds (cmds, x=l[m], ems=m)
                if t != None : pees[m] = t
            if pees[m].poll () == None :
                running = True
        for m in fio.nmini :
            if pees[m] == None : continue
            #print "Open STDOUT"
            out[m] = open (fifo[m], 'w', 0)
            #print '.'
            out[m].write (pees[m].stdout.read (1))
            #print '.'
            pees[m].stdout.flush ()
            #print '.'
            out[m].close ()

        #print cnt, '-------------------'; cnt += 1
    for m in fio.nmini :
        out[m] = open (fifo[m], 'w', 0)
        out[m].write (pees[m].stdout.read ())
        pees[m].stdout.flush ()
        out[m].close ()
        #print "Open STDERR"
        #with open (fifo[m], 'w', 0) as out[m] :
            #print '.'
            #out[m].write (pees[m].stderr.read ())
            #print '.'
            #pees[m].stderr.flush ()
            #print '.'
            #out[m].close ()
        #print "Done"
        
    return xterms
        

def main():
    if not exexists ('xterm') :
        sys.stderr.write ("The external program xterm required. Not found.\n")
        sys.exit ()
        
    get_args ()
    #   Inputs list of raw files and project directory
    fio = pforma_io.FormaIO (infile=RAW_LST, outdir=PROJECT)
    #   Number of families is (default) number of CPU's + 1 or set
    fio.set_nmini (NFAMILY)
    #   M is the number of mini ph5 files per family, otherwise set in fio.read
    if M : fio.set_M (M)
    #   Set UTM zone for segd2ph5 if needed
    if UTM : fio.set_utm (UTM)
    if TSPF : fio.set_tspf (TSPF)
    #   Don't merge just process raw to PH5
    if not MERGE :
        #   Open list of input files
        try :
            fio.open ()
        except pforma_io.FormaIOError as e :
            sys.stderr.write ("Error: {0} Message: {1}\n".format (e.errno, e.message))
            sys.exit (1)
        #   Pre-process raw files
        try :
            fio.read ()
        except pforma_io.FormaIOError as e :
            sys.stderr.write ("Error: {0} Message: {1}\n".format (e.errno, e.message))
            sys.exit (1)
        #   Adjust the number M and the number of families if needed 
        print "Total raw size: {0:7.2f}GB".format (float (fio.total_raw / 1024. / 1024. / 1024.))
        adjust (fio)
        #   Set up the processing directory structure, and reset M if mini files already exist
        try :
            fio.initialize_ph5 ()
        except pforma_io.FormaIOError as e :
            sys.stderr.write ("Error: {0} Message: {1}\n".format (e.errno, e.message))
            sys.exit (1)
        #   Read JSON db   
        try :
            fio.readDB ()
        except pforma_io.FormaIOError as e :
            sys.stderr.write ("Error: {0} Message: {1}\n".format (e.errno, e.message))
            sys.exit (1)
        #   Resolve JSON db with list of files we are loading (have they been loaded already)    
        fio.resolveDB ()
        #   Do the conversions to PH5
        xterms = run (fio)
        #   Merge loaded raw files with existing JSON db and write new JSON db
        fio.merge (fio.resolved.keys ())
        
        #if MERGE :
            #fio.unite ()
        #   Write configuration     
        fio.write_cfg ()
        
        yn = raw_input ("Kill xterms? (y/n) ")
        if yn == 'y' :
            for k in xterms.keys () :
                xterms[k].kill ()
    else :
        #   Unite all PH5 families to one...
        msgs = fio.unite ('Sigma')
        for m in msgs : print m


if __name__ == "__main__" :
    main()
