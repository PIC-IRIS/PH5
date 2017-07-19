#!/usr/bin/env pnpython4
#
#   Merge Response_t from a family of ph5 files and create corrected Das_t files
#   Only creates corrected Response_t and Das_t files.
#
#   Steve Azevedo, Mar 2017
#

import sys, os, re
from ph5.core import ph5api

PROG_VERSION = '2017.068a'

ALL_FAMILIES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q']
def get_args () :
    global ARGS, P5
    import argparse

    parser = argparse.ArgumentParser ()
    parser.usage = "v{0}: set_n_i_response (Run from top level families directory.)".format (PROG_VERSION)
    #   Usually master.ph5
    #
    #parser.add_argument ("-R", dest="catted_response_kef", required=False, default="Response_t_by_family.kef",
                         #help="Catted Respons_t kef files from all families. First line at start of new family example: '## A'")
    parser.add_argument ("-F", dest="families_directory", required=False,
                         help="Directory that holds the family directories. Absolute path.")
    parser.add_argument ("-N", dest="first_n_i", required=False, type=int, default=0,
                         help="The n_i of the first entry. Defaults to zero.")

    ARGS = parser.parse_args ()
    
    if ARGS.families_directory == None :
        ARGS.families_directory = os.getcwd ()

def dump_kefs () :
    '''   Dump each family Response_t into a single kef file.
          Label start of each Response_t with the family name '## A' as an example
    '''
    global ORIG_RESPS
    miniRE = re.compile ("miniPH5_\d{5}.ph5")
    here = os.getcwd ()
    first = True
    if not os.path.exists ("RESPONSE_T_N_I") :
        os.mkdir ("RESPONSE_T_N_I")
    ORIG_RESPS = os.path.join (here, "RESPONSE_T_N_I", "Response_t_by_family.kef")
    sys.stderr.write ("Creating: {0}\n".format (ORIG_RESPS))
    with open (ORIG_RESPS, 'w+') as fh :
        for fam in ALL_FAMILIES :
            if os.path.exists (os.path.join (fam, "master.ph5")) :
                files = os.listdir (os.path.join ('.', fam))
                matches = [f for f in files if miniRE.match (f)]
                if len (matches) == 0 : continue
                if first :
                    fh.write ("## {0}\n".format (here))
                    first = False
                command = "table2kef -n {0}/master.ph5 -R".format (fam)
                fh.write ("## {0}\n".format (fam))
                pipeh = os.popen (command)
                if pipeh :
                    while True :
                        line = pipeh.readline ()
                        if not line : break
                        fh.write (line)
#
#   First line at start of family kef: "## A" (as an example)
#
def parse_kef () :
    '''   Parse catted response file created by dump_kefs to a map:
          MAP[family][index]['n_i_all':n, 'n_i_family':n, [Response_t_dictionary]]
          family => Family name, 'A' as an example
          n_i_all => The n_i after all the Response_t are catted together
          n_i_family => The original n_i
          Response_t_dictionary => A dictionary for the line from the Response_t, keys are 
          column names
    '''
    global ARGS
    ret = {}
    row = None
    n_i_all = 0
    with open (ORIG_RESPS) as fh :
        while True :
            line = fh.readline ()
            if not line : break
            if line[0] == '#' :
                #print line, len (line)
                #   Comment with family
                if len (line) == 5 and line[1] == '#' :
                    #   Save row, Just finished last family so save last row
                    if row != None :
                        row['n_i_family'] = len (ret[family])
                        ret[family].append (row)

                    row = {}
                    #   Get family name and set to empty list
                    family = line[3:].strip ()
                    if not ret.has_key (family) :
                        ret[family] = []
                ##   Families directory
                #elif len (line) > 4 and line[3] == '/' :
                    #ARGS.families_directory = line[3:].strip ()
            #   We start a new row in the table here
            elif line[0] == '/' :
                #   Save row if there is one
                if row != {} :
                    row['n_i_family'] = len (ret[family])
                    ret[family].append (row)

                row = {}
                row['n_i_all'] = n_i_all + ARGS.first_n_i               
                row['ppath'] = line.strip ()
                n_i_all += 1
            elif line[0] == '\t' :
                line = line.strip ()
                key, value = line.split ('=')
                if key == 'n_i' :
                    last_n_i = int (value)
                if not row.has_key ('kv') :
                    row['kv'] = {}
                row['kv'][key] = value

        #row['n_i_all'] = n_i_all + ARGS.first_n_i
        row['n_i_family'] = last_n_i + ARGS.first_n_i
        ret[family].append (row)    
    return ret

def print_new_Response_t (n_i_map) :
    '''   Print the final Response_t.kef
    '''
    CORRECTED_RESPS = os.path.join (ARGS.families_directory, "RESPONSE_T_N_I", "Response_t_cor.kef")
    sys.stderr.write ("Creating: {0}\n".format (CORRECTED_RESPS))
    with open (CORRECTED_RESPS, 'w+') as fh :
        families = n_i_map.keys ()
        families.sort ()
        for family in families :
            fh.write ("#  {0}\n".format (family))
            n = 0
            for element in n_i_map[family] :
                fh.write ("#  {0}\n".format (n)); n += 1
                kv = element['kv']
                kv['n_i'] = element['n_i_all']
                keys = kv.keys ()
                keys.sort ()
                fh.write (element['ppath'] + '\n')
                for k in keys :
                    fh.write ("\t{0}={1}\n".format (k, kv[k]))
                    
def print_new_Das_t (P5) :
    '''   Print Das_t corrected for Response_t n_i
    '''
    P5.read_das_g_names ()
    for das_g in P5.Das_g_names :
        das = P5.read_das_t (das_g)
        MAP = n_i_map[family]
        #if not das : continue
        if not das or not P5.Das_t.has_key (das) :
            sys.stderr.write ("#***\tMissing: {0}\n".format (das))
            continue
        
        if not os.path.exists (os.path.join (ARGS.families_directory, "RESPONSE_T_N_I")) :
            os.mkdir (os.path.join (ARGS.families_directory, "RESPONSE_T_N_I"))
            
        DAS_KEF = os.path.join (ARGS.families_directory, "RESPONSE_T_N_I", "Das_t_response_n_i_{0}.kef".format (das))
        sys.stderr.write ("Creating: {0}\n".format (DAS_KEF))
        with open (DAS_KEF, 'w+') as fh :
            fh.write ("#   PH5VERSION: {0}\n".format (ph5api.PH5VERSION))
            keys = P5.Das_t[das]['keys']
            keys.sort ()
            i = 1
            for das_t in P5.Das_t[das]['rows'] :
                try :
                    M = MAP[das_t['response_table_n_i']]
                    das_t['response_table_n_i'] = M['n_i_all']
                    fh.write ("#   {0}\n".format (i)); i += 1
                    fh.write ("/Experiment_g/Receivers_g/{0}/Das_t\n".format (das_g))
                    for k in keys :
                        fh.write ("\t{0}={1}\n".format (k, das_t[k]))
                except IndexError :
                    sr = ph5api.fepoch (das_t['sample_rate_i'], das_t['sample_rate_multiplier_i'])
                    sys.stderr.write ("#   Index out of range for DAS: {0}, sample rate: {1}\n".format (das, sr))
                    sys.stderr.write ("#   Entry unchanged! Suspect data.\n")
                    fh.write ("#   {0} response_table_n_i entry suspect!\n".format (i)); i += 1
                    fh.write ("/Experiment_g/Receivers_g/{0}/Das_t\n".format (das_g))
                    for k in keys :
                        fh.write ("\t{0}={1}\n".format (k, das_t[k]))


def main():
    get_args ()
    os.chdir (ARGS.families_directory)
    dump_kefs ()
    try:
        n_i_map = parse_kef ()
    except:
        print "Cannot create n_i map. Make sure the directory is correct using -F flag"
        sys.exit()

    for family in ALL_FAMILIES :
        #print ARGS.families_directory, family
        ph5 = os.path.join (ARGS.families_directory, family)
        #print '#***' + ph5
        try :
            P5 = ph5api.PH5 (path=ph5, nickname='master.ph5')
        except Exception as e :
            sys.stderr.write ("Warning: {0}\n".format (e.msg))
            continue
        
        print_new_Das_t (P5)
        P5.close ()
        
    print_new_Response_t (n_i_map)


if __name__ == '__main__' :
    main()
