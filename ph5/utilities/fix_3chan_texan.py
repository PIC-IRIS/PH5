#!/usr/bin/env pnpython4
#
#   Modify /Experiment_g/Receivers_g/Das_t_xxxxx/Das_t to correct
#   channel number based on channel number set in Array_t_xxx.
#   The experiment used texans to record horizontal channels.
#   Writes a kef file for each DAS.
#
#   Steve Azevedo, May 2011
#

import sys, os, os.path, string, time
#   This provides the base functionality
from ph5.core import experiment

PROG_VERSION = '2016.225 Developmental'
#   Valid horizontal channel numbers
HORIZ = [ 2, 3, 5, 6 ]
#   Array_t_xxxx keyed on xxxx 
ARRAY_T = {}
#   Das_t keyed on DAS SN
DAS_T = {}

DASGROUPS = None
#   Reference to Experiment_g
EX = None
#   PH5 file name
PH5 = None
#   Path to PH5
PATH = '.'
#   File handle to fixed kef file
#FH = None
#
#   To hold table rows and keys
#
class Rows_Keys (object) :
    __slots__ = ('rows', 'keys')
    def __init__ (self, rows = [], keys = []) :
        self.rows = rows
        self.keys = keys
        
    def set (self, rows = None, keys = None) :
        if rows != None : self.rows = rows
        if keys != None : self.keys = keys

#
#   To hold DAS sn and references to Das_g_[sn]
#
class Das_Groups (object) :
    __slots__ = ('das', 'node')
    def __init__ (self, das = None, node = None) :
        self.das = das
        self.node = node
        
#
#   Initialize ph5 file
#
def initialize_ph5 (editmode = False) :
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5
    
    EX = experiment.ExperimentGroup (PATH, PH5)
    EX.ph5open (editmode)
    EX.initgroup ()
    
def info_print () :
    '''   Print time of run, PH5 file organization version, this programs verion   '''
    global EX, FH
    
    if FH != None :
        FH.write ("#\n#\t%s\tph5 version: %s\tv%s\n#\n" % (time.ctime (time.time ()), EX.version (), PROG_VERSION)) 
    else :
        print ("#\n#\t%s\tph5 version: %s\tv%s\n#\n" % (time.ctime (time.time ()), EX.version (), PROG_VERSION)) ,
    
def save_orig (das, Das_t) :
    '''   Save a version of the original Das_t.kef   '''
    of = open ("Das_t_{0}orig.kef".format (das), 'w+')
    of.write ("#\n#\t%s\tph5 version: %s\n#" % (time.ctime (time.time ()), EX.version ()))
    for das_t in Das_t.rows :
        of.write ("/Experiment_g/Receivers_g/Das_g_{0}/Das_t\n".format (das))
        for k in Das_t.keys :
            of.write ("\t{0} = {1}\n".format (k, das_t[k]))
            
    of.close ()

#
#   Print Rows_Keys
#
def table_print (t, d, a, key) :
    #   Loop through table rows
    #for r in a.rows :
    #i += 1
    #print "#   Table row %d" % i
    #dirname = os.path.dirname (t)
    #keffilename = os.path.basename (dirname)
    #fh = open (keffilename + '.kef', mode='w')
    
    #   Print table name
    if key in a :
        FH.write ("{0}:Update:{1}\n".format (t, key))
    else :
        FH.write (t + '\n')
        
    #   Loop through each row column and print
    for k in a :
        FH.write ("\t{0} = {1}\n".format (k, d[k]))

    #fh.close ()    


def read_sort_arrays () :
    '''   Read /Experiment_t/Sorts_g/Array_t_[n]   '''
    global EX, ARRAY_T
    
    #   We get a list of Array_t_[n] names here...
    #   (these are also in Sort_t)
    names = EX.ph5_g_sorts.names ()
    for n in names :
        
        arrays, array_keys = EX.ph5_g_sorts.read_arrays (n)
        
        rowskeys = Rows_Keys (arrays, array_keys)
        #   We key this on the name since there can be multiple arrays
        ARRAY_T[n] = rowskeys
        
def read_receivers (das = None) :
    '''   Read tables and arrays (except wiggles) in Das_g_[sn]   '''
    global EX
    
    #print dasGroups.keys ()
    if das == None :
        #   Get references for all das groups keyed on das
        dass = DASGROUPS.keys ()
        #   Sort by das sn
        dass.sort ()
    else :
        dass = [das]
        
    for d in dass :
        #d = str (d)
        d = "Das_g_{0}".format (str (d))
        #sys.stderr.write ("DAS '{0}'\n".format (d))
        #   Get node reference
        if not DASGROUPS.has_key (d) :
            sys.stderr.write ("#No key '{0}'\n".format (d))
            continue
        
        g = DASGROUPS[d]
        #dg = Das_Groups (d, g)
        #   Save a master list for later
        #DASS.append (dg)
        
        #   Set the current das group
        EX.ph5_g_receivers.setcurrent (g)
        
        #   Read /Experiment_g/Receivers_g/Das_g_[sn]/Das_t
        das, das_keys = EX.ph5_g_receivers.read_das ()
        rowskeys = Rows_Keys (das, das_keys)
        #DAS_T[d] = rowskeys
        return rowskeys
    
    return Rows_Keys ()


def main():
    global FH
    try :
        PH5 = sys.argv[1]
    except IndexError :
        sys.stderr.write ("v{1} Usage: {0} file.ph5\n".format (sys.argv[0], PROG_VERSION))
        sys.exit ()
    
    initialize_ph5 ()
    
    #info_print ()
    #read_receivers ()
    read_sort_arrays ()
    DASGROUPS = EX.ph5_g_receivers.alldas_g ()
    
    #for k in DASGROUPS.keys () :
        #print "'{0}'".format (k)
        
    #sys.exit ()
    arrays = ARRAY_T.keys ()
    
    for a in arrays :
        #print a
        array_t = ARRAY_T[a]
        for r in array_t.rows :
            chan = r['channel_number_i']
            if not chan in HORIZ :
                continue
                #sys.stderr.write ("'{0}'".format (chan))
                #pass
            
            das = r['das/serial_number_s'].strip ()
            if len (das) != 5 :
                das = "0x{0}".format (das)
            try :
                dassn = int (das)
            except ValueError :
                dassn = int (das, 16)
             
            #   Must be an rt-130
            if dassn > 32000 : 
                continue
            
            start_epoch = r['deploy_time/epoch_l']
            stop_epoch = r['pickup_time/epoch_l']
            Das_t = read_receivers (das)
            save_orig (das, Das_t)
            FH = open ("Das_t_{0}.kef".format (das), 'w')
            info_print ()
            FH.write ('#\n#\t{0} {1} {2} {3}\n'.format (das, chan, start_epoch, stop_epoch))
            for d in Das_t.rows :
                #secs = d['sample_count_i'] / (d['sample_rate_i'] / d['sample_rate_multiplier_i'])
                start = d['time/epoch_l']
                #stop = start + secs
                if start >= start_epoch and start < stop_epoch :
                    t = '/Experiment_g/Receivers_g/Das_g_{0}/Das_t'.format (das)
                    d['channel_number_i'] = chan
                    d['receiver_table_n_i'] = chan - 1
                    table_print (t, d, Das_t.keys, 'time/epoch_l')

            FH.close ()

    EX.ph5close ()


if __name__ == '__main__' :
    main()
