#!/usr/bin/env pnpython3

from ph5.core import kef, experiment
import sys, os
import tempfile

PROG_VERSION = "2016.181 Developmental"



RECEIVER_T="kef.tmp"
RECEIVER_T_STRING = str("""
#   Table row 1
/Experiment_g/Receivers_g/Receiver_t
        orientation/azimuth/value_f = 0.0
        orientation/azimuth/units_s = degrees
        orientation/dip/value_f = 90.0
        orientation/dip/units_s = degrees
        orientation/description_s = Z
#   Table row 2
/Experiment_g/Receivers_g/Receiver_t
        orientation/azimuth/value_f = 0.0
        orientation/azimuth/units_s = degrees
        orientation/dip/value_f = 0.0
        orientation/dip/units_s = degrees
        orientation/description_s = N
#   Table row 3
/Experiment_g/Receivers_g/Receiver_t
        orientation/azimuth/value_f = 90.0
        orientation/azimuth/units_s = degrees
        orientation/dip/value_f = 0.0
        orientation/dip/units_s = degrees
        orientation/description_s = E
#   Table row 4
/Experiment_g/Receivers_g/Receiver_t
        orientation/azimuth/value_f = 0.0
        orientation/azimuth/units_s = degrees
        orientation/dip/value_f = -90.0
        orientation/dip/units_s = degrees
        orientation/description_s = Z
        """)
kef_file = open("kef.tmp", "w")
kef_file.write(RECEIVER_T_STRING)
kef_file.close()

def get_args () :
    ''' Parse input args
           -o   output file
           -k   kef file
    '''
    global PH5, KEFFILE, RECEIVER_T
    
    from optparse import OptionParser

    oparser = OptionParser ()
    oparser.usage = "Version: %s initialize_ph5 [--help]--kef kef_file --output output_file" % experiment.PROG_VERSION
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
        os.remove("kef.tmp")
        sys.exit ()


def main():
    global PH5, KEFFILE
    get_args ()
    #   Create ph5 file
    EDITMODE = True
    ex = experiment.ExperimentGroup (nickname = PH5)
    ex.ph5open (EDITMODE)
    ex.initgroup ()
    #   Update Experiment_t
    if KEFFILE :
        k = kef.Kef (KEFFILE)
        k.open ()
        k.read ()
        k.batch_update ()
        k.close ()
    
       
    if os.path.exists (RECEIVER_T) :
        k = kef.Kef (RECEIVER_T)
        k.open ()
        k.read ()
        k.batch_update ()
        k.close ()
    else :
        sys.stderr.write ("Warning: /Experiment_g/Receivers_g/Receiver_t not set!\n")
        os.remove("kef.tmp")
        
    #   Close PH5 file
    ex.ph5close ()
    print "Done..."
    os.remove("kef.tmp")


if __name__ == "__main__" :
    main()
