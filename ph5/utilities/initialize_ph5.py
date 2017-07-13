#!/usr/bin/env pnpython3

from ph5.core import Kef, Experiment
import sys, os

PROG_VERSION = "2016.181 Developmental"

RECEIVER_T = os.path.join (os.environ['KX'], 'apps', 'pn4', 'Receiver_t.kef')

def get_args () :
    ''' Parse input args
           -o   output file
           -k   kef file
    '''
    global PH5, KEFFILE, RECEIVER_T
    
    from optparse import OptionParser

    oparser = OptionParser ()
    oparser.usage = "Version: %s initialize_ph5 [--help]--kef kef_file --output output_file" % Experiment.PROG_VERSION
    oparser.description = "Program to initialize PH5 file at start of experiment. The kef file should contain information for experiment table /Experiment_g/Experiment_t."
    oparser.add_option ("-n", "--nickname", dest = "outfile",
                        help="Experiment nickname.",
                        metavar = "output_file")
    oparser.add_option ("-r", "--receiver_t", dest = "receiver_t",
                        help = "Load an alternate /Experiment_g/Receivers_g/Receiver_t kef file.",
                        metavar = "receiver_t")
    options, args = oparser.parse_args()
    
    FILES = []
    PH5 = KEFFILE = None
    
    if options.outfile != None :
        PH5 = options.outfile
        
    if options.receiver_t != None :
        RECEIVER_T = os.path.abspath (options.receiver_t)

    if PH5 == None :
        #print H5, FILES
        sys.stderr.write ("Error: Missing required option. Try --help\n")
        sys.exit ()
        

def main():
    global PH5, KEFFILE
    get_args ()
    #   Create ph5 file
    EDITMODE = True
    ex = Experiment.ExperimentGroup (nickname = PH5)
    ex.ph5open (EDITMODE)
    ex.initgroup ()
    #   Update Experiment_t
    if KEFFILE :
        k = Kef.Kef (KEFFILE)
        k.open ()
        k.read ()
        k.batch_update ()
        k.close ()
        
    if os.path.exists (RECEIVER_T) :
        k = Kef.Kef (RECEIVER_T)
        k.open ()
        k.read ()
        k.batch_update ()
        k.close ()
    else :
        sys.stderr.write ("Warning: /Experiment_g/Receivers_g/Receiver_t not set!\n")
        
    #   Close PH5 file
    ex.ph5close ()
    print "Done..."
    

if __name__ == "__main__" :
    main()
