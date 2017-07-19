#!/usr/bin/env pnpython3
#
#   Steve Azevedo, July 2015
#

import os, sys, exceptions
###import sqlite3 as db
import json, time
import subprocess32 as subprocess
#import subprocess

PROG_VERSION = '2017.032 Developmental'

#JSON_DB = 'pforma.json'
HOME = os.environ['HOME']
DOT = os.path.join (HOME, '.pforma')
#JSON_DB = os.path.join (HOME, 'Svn/pn3-devel/Forma', 'pforma.json')
JSON_DB = 'pforma.json'
#JSON_CFG = os.path.join (HOME, 'Svn/pn3-devel/Forma', 'pforma.cfg') 
JSON_CFG = 'pforma.cfg'

PROG2INST = {'125a2ph5':'texan', '1302ph5':'rt-130', 'segd2ph5':'nodal'}

ON_POSIX = 'posix' in sys.builtin_module_names

class FormaIOError (exceptions.Exception) :
    def __init__ (self, errno, msg) :
        self.errno = errno
        self.message = msg
        
class FormaIO () :
    '''
        Create a project to read RAW data into a PH5 file in parallel.
    '''
    #   These are the number of conversions that can be run at once.
    MINIS = ('A','B','C','D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P')
    def __init__ (self, infile = None, outdir = None) :
        self.infile = infile                    #   Input file (list of raw files)
        self.infh = None                        #   File handle for infile
        self.raw_files = {}                     #   Raw files organized by type
        self.total_raw = 0.0                    #   Total size of raw
        #self._json = os.path.join (outdir, 'pforma.json')   #   The JSON file that holds files that are already loaded
        #self.instrument_type = None
        self.home = outdir                      #   Where the processing of the ph5 files happens
        self.whereami = os.getcwd ()            #   Where the program was started
        self.M = None                           #   How many mini files in each ph5 family
        self.UTM = None                         #   UTM zone (SEG-D)
        self.TSPF = None                        #   texas state plane coordinates (SEG-D)
        self.COMBINE = 1                        #   Combine traces from SEG-D file
        self.read_cfg ()                        #   Configuration info
        if self.cfg and self.cfg.has_key ('M') : 
            self.M = int (self.cfg['M'])
        
        if self.cfg and self.cfg.has_key ('N') :
            self.nmini = FormaIO.MINIS[0:self.cfg['N']]
        else :
            self.nmini = FormaIO.MINIS[0:4]
            
        #print 'cfg', self.cfg,; sys.exit ()
    
    def set_cfg (self) :
        '''
            Set the location of the configuration file.
            Should get kept in the project.
            Contains:
                      JSON_DB -> Path to files already read into PH5 family
                      M -> How many mini files to build in each family
                      N -> How many families of PH5 files to create
        '''
        self.cfg = {}
        self.cfg['JSON_DB'] = os.path.join (self.home, JSON_DB)
        self.cfg['M'] = self.M
        self.cfg['N'] = len (self.nmini)
        
    def set_utm (self, utm) :
        self.UTM = utm
        
    def set_combine (self, combine) :
        self.COMBINE = combine
    
    def set_tspf (self, tspf) :
        self.TSPF = tspf
    
    def read_cfg (self) :
        '''
            Read the configuration file.
        '''
        self.cfg = read_json (os.path.join (self.home, JSON_CFG))
        #print 'CFG', self.cfg
        if self.cfg == None : self.cfg = {}
        
    def write_cfg (self) :
        '''
            Write the config file.
        '''
        self.set_cfg ()
        write_json (self.cfg, os.path.join (self.home, JSON_CFG))
        
    def set_nmini (self, n) :
        '''
            Set the self.nmini list of PH5 families from n and FormaIO.MINIS.
            Use value for N from pforma.cfg if it exists.
        '''
        if not self.cfg.has_key ('N') :
            self.nmini = FormaIO.MINIS[0:n]
        
    def initialize_ph5 (self) :
        '''   Set up processing directory structure and set M from existing mini files   '''
        if self.home == None : return
        if not os.path.exists (self.home) :
            try :
                os.makedirs (self.home)
            except Exception as e :
                raise FormaIOError (4, "Failed to create output directory: {0}".format (self.home))
            
        for m in self.nmini :
            os.chdir (self.home)
            if not os.path.exists (m) :
                os.mkdir (m)
            
            try :
                os.chdir (m)
                subprocess.call ('initialize-ph5 -n master', shell=True, stdout=open (os.devnull, 'w'), stderr=open (os.devnull, 'w'))
            except Exception as e :
                raise FormaIOError (5, "Failed to initialize {0}".format (os.path.join (self.home, m)))
            
            files = os.listdir ('.')
            minis = filter (lambda a : a[0:5] == 'miniP' and a[-3:] == 'ph5', files)
            if len (minis) :
                if self.M == None or len (minis) > self.M :
                    self.M = len (minis)
                
        os.chdir (self.whereami)
        
    def set_M (self, m) :
        '''
            Set self.M, the number of mini files in each family.
        '''
        try :
            self.M = int (m)
            #self.cfg['M'] = int (m)
        except Exception as e :
            raise FormaIOError (errno=10, msg="Failed to set M: {0}".format (e.message))

    def run_simple (self, cmds, x, family) :
        '''
            Run a single command in a subprocess. Line buffer output.
            cmds   -> A list of commands to be run for this family
            x      -> The sequence of the command to run
            family -> The family that goes with these commands
            pee    -> The process
            fifofh -> File handle to fifo
        '''
        pee = None
        try :
            cmd = cmds[x]
        except IndexError :
            return pee, None
        
        #fifo = os.path.join ("/tmp", "fifo{0}".format (family))
        #if not os.path.exists (fifo) :
            #os.mkfifo (fifo)
        
        #fifofh = open (fifo, mode='rw+')
        
        pee = subprocess.Popen (cmd,
                                shell=True,
                                bufsize=1,
                                cwd=os.path.join (self.home, family),
                                stdout=subprocess.PIPE,
                                universal_newlines=True,
                                close_fds=ON_POSIX)
        fifofh = pee.stdout
        
        return pee, fifofh
        
    def run_cmds (self, cmds, x = 0, ems = None) :
        '''
            Run conversion commands in a subprocess
            cmds -> A dictionary of families that point to a list of commands.
                    cmds['B']['125a2ph5 -n master.ph5 ...', '1302ph5 -n master.ph5 ...']
            x -> The sequence of the current command executing in the list in cmds.
            ems -> The list of families ['A', 'B', 'C' etc]
        '''
        pees = {}
        if ems == None :
            ems = self.nmini
        else :
            ems = [ems]
        #for inst in ('texan', 'rt-130', 'nodal') :
        for m in ems :
            if len (cmds[m]) > x :
                insts = cmds[m][x]
                pees[m] = subprocess.Popen (insts, 
                                            shell=True, 
                                            bufsize=-1,
                                            cwd=os.path.join (self.home, m),
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
                
            else :
                pees[m] = None
        if len (ems) > 1 :
            return pees, x
        else :
            return pees[m], x
    #
    ###   Should this be implemented as a closure?
    #
    def run (self, runit = True) :
        '''   Run processes to convert raw files to ph5
              runit -> If true, execute processes otherwise only return list of
              commands to execute.
        '''
        def split (ts) :
            '''   Split up lists of raw files for processing.
                  Key by mini ph5 family name.
            '''
            ret = {}   #   Files to load
            tot = {}   #   Total raw size per family
            #   Initialize
            #print self.nmini
            #sys.exit ()
            for m in self.nmini :
                ret[m] = {}
                tot[m] = 0
            
            #   Check to see if any of these are already loaded (data from a das must all be in the same family).   
            dass = self.resolved.keys ()
            for d in dass :
                raws = self.resolved[d]
                for r in raws :
                    if r['mini'] and ret.has_key (r['mini']) :
                        if not ret[r['mini']].has_key (d) :
                            ret[r['mini']][d] = []
                            
                        tot[r['mini']] += r['size']
                        ret[r['mini']][d].append (r)
            
            #   Go through remaining dass and assign them to a family
            dass.sort ()
            i = 0
            for d in dass :
                raws = self.resolved[d]
                if tot[self.nmini[i]] >= ts :
                    i += 1
                    if i > len (self.nmini) - 1 :
                        i -= 1
                    
                for r in raws :
                    if r['mini'] :
                        continue
                
                    #if (r['size'] + tot[FormaIO.MINIS[i]]) > ts :
                        #i += 1
                        #if i >= len (FormaIO.MINIS) :
                            #i -= 1
                        
                    if not ret[self.nmini[i]].has_key (d) :
                        ret[self.nmini[i]][d] = []
                        
                    r['mini'] = self.nmini[i]
                    tot[self.nmini[i]] += r['size']
                    ret[self.nmini[i]][d].append (r)
                    
            return ret
                    
        def setup (tl) :
            '''   Write sub-lists of raw files to each mini family directory   '''
            ret = {}
            for m in self.nmini :
                ret[m] = {}
                for typ in ('texan', 'rt-130', 'nodal') :
                    of = None
                    outfile = "{0}_{1}{2}.lst".format (typ, str (int (time.time ())), m)
                    os.chdir (os.path.join (self.home, m))
                    dass = tl[m]
                    keys = dass.keys ()
                    keys.sort ()
                    wrote = False
                    for d in keys :
                        files = dass[d]
                        for f in files :
                            if f['type'] == typ :
                                if not of :
                                    of = open (outfile, 'w+')
                                of.write (f['path'] + '\n')
                                wrote = True
                                
                    try : 
                        of.close () 
                    except : 
                        pass
                    if wrote :
                        ret[m][typ] = os.path.join (self.home, m, outfile)
                    
            os.chdir (self.whereami)
            
            return ret
            
        def build_cmds (lsts) :
            '''   Make commands to do the conversion from raw to ph5 for each mini ph5 family   '''
            ret = {}
            info = {}
            
            #info = {'lists':[], 'instruments':[]}
            i = 0
            for m in self.nmini :
                cmd = []
                lists = []; instruments = []
                lst = lsts[m]
                #cdcmd = "cd {0};".format (os.path.join (self.home, m))
                ess = i * self.M + 1
                if lst.has_key ('texan') :
                    lists.append (lst['texan'])
                    instruments.append ('texan')
                    cmd.append ("125a2ph5 -n master.ph5 -f {0} -M {1} -S {2} --overide 2>&1".format (lst['texan'], self.M, ess))
                if lst.has_key ('rt-130') :
                    lists.append (lst['rt-130'])
                    instruments.append ('rt-130')                    
                    cmd.append ("1302ph5 -n master.ph5 -f {0} -M {1} -S {2} 2>&1".format (lst['rt-130'], self.M, ess))
                if lst.has_key ('nodal') :
                    lists.append (lst['nodal'])
                    instruments.append ('nodal')                    
                    if self.UTM :
                        cmd.append ("segd2ph5 -n master.ph5 -f {0} -M {1} -U {3} -S {2} -c {4} 2>&1".format (lst['nodal'], self.M, ess, self.UTM, self.COMBINE))
                    elif self.TSPF :
                        cmd.append ("segd2ph5 -n master.ph5 -f {0} -M {1} -T -S {2} -c {3} 2>&1".format (lst['nodal'], self.M, ess, self.COMBINE))
                    else :
                        cmd.append ("segd2ph5 -n master.ph5 -f {0} -M {1} -S {2} -c {3} 2>&1".format (lst['nodal'], self.M, ess, self.COMBINE))
                #if len (cmd) != 0 :
                ret[m] = cmd
                if not info.has_key (m) :
                    info[m] = {}
                    
                info[m]['lists'] = lists
                info[m]['instruments'] = instruments
                    
                i += 1
                    
            return ret, info
        
        def save_cmds (cmds) :
            '''   Save commands   '''
            #fh = open (os.path.join (self.home, "commands{0}.json".format (str (int (time.time ())))), 'w+')
            #json.dump (cmds, fh, indent=4, sort_keys=True)
            #fh.close ()
            write_json (cmds, os.path.join (self.home, "commands{0}.json".format (str (int (time.time ())))))
        

        #
        ###   Main
        #
        target_size = self.total_raw / len (self.nmini)
        toload = split (target_size)
        lsts = setup (toload)
        cmds, info = build_cmds (lsts)
        save_cmds (cmds)
        if runit == True :
            pees, i = self.run_cmds (cmds)
            return cmds, pees, i
        else :
            return cmds, info, None
        
    def open (self) :
        '''   Open file containing list of raw files   '''
        if self.infile == None :
            return
        
        try :
            self.infh = open (self.infile, "Ur")
        except Exception as e :
            self.infh = None
            raise FormaIOError (errno=1, msg="Failed to open: {0}.".format (self.infile))
        
    def read (self) :
        '''   Read raw files   '''
        if self.infh == None :
            try :
                self.open ()
            except FormaIOError as e :
                sys.stderr.write ("{0}: {1}".format (e.errno, e.message))
                sys.exit ()
        if self.infh == None : return
        n = 0        
        while True :
            line = self.infh.readline ()
            if not line : break
            #   Skip commented lines
            if line[0] == '#' : continue
            line = line.strip ()
            #   Skip empty line
            if not line : continue
            n += 1
            #   Try to guess data logger type and serial number based on file name
            raw_file = os.path.basename (line)        #
            #das = str (int (raw_file[1:5]) + 10000)   #   Wrong!!! texan only
            #try :
            tp, das = guess_instrument_type (raw_file)
            #except FormaIOError as e :
                #sys.stderr.write (e.message)
                #sys.exit (e.errno)
            #print tp, das
            if das == 'lllsss' :
                raise FormaIOError (errno=4, msg="May be nodal SEG-D file but using simpleton file naming scheme. Please rename.")
            if tp == 'unknown' :
                raise FormaIOError (errno=3, msg="File in {1} does not have standard name: {0}".format (raw_file, self.infile))
            
            #   Save info about each raw file keyed by serial number in self.raw_files
            if not self.raw_files.has_key (das) :     #
                self.raw_files[das] = []
                
            file_info = {}
            #   Type of data logger
            file_info['type'] = tp
            #   Full path to raw file
            file_info['path'] = line
            #   Size of raw file in bytes
            file_info['size'] = os.stat (line).st_size
            #   Time file was modified
            file_info['mtime'] = os.stat (line).st_mtime
            #file_info['adler'] = check_sum (line)
            #   Which family of ph5 files does this belong to. See self.nmini
            file_info['mini'] = None
            #   Total of raw files so far in bytes
            self.total_raw += file_info['size']
            self.raw_files[das].append (file_info)
            
        self.average_raw = int (self.total_raw / n)
        self.number_raw = n
        self.infh.close ()
        #   Estimate M so each mini file is about 12GB
        if self.M == None :
            self.M = int ((((self.total_raw / len (self.nmini)) / 1024 / 1024 / 1024) / 12) + 0.5)
            if self.M == 0 : self.M = 1
        #print json.dumps (self.raw_files, indent=4, sort_keys=True)
        #pass
        
    def readDB (self) :
        '''   Read JSON file containing files loaded so far. Same format as self.raw_files   '''
        try :
            #fh = open (self._json, 'Ur')
            #self.db_files = json.load (fh)
            #fh.close
            self.db_files = read_json (os.path.join (self.home, JSON_DB))
        except Exception as e :
            self.db_files = {}
            raise FormaIOError (2, "Failed to read {0}. {1}".format (self._json, e.message))
            
    def resolveDB (self) :
        '''   Resolve the list of raw files with the files already loaded   '''
        new_keys = self.raw_files.keys ()
        new_keys.sort ()
        
        existing_keys = self.db_files.keys ()
        if len (existing_keys) == 0 :
            self.resolved = self.raw_files
            return
        
        existing_keys.sort ()
        
        ret = {}
        n_save = []
        #   Loop on DAS SN
        for nk in new_keys :
            #   List of dictionaries
            new_dass = self.raw_files[nk]
            #   We have seen this DAS before
            if nk in existing_keys :
                existing_dass = self.db_files[nk]
                for n in new_dass :
                    n_base = os.path.basename (n['path'])
                    for e in existing_dass :
                        #e = existing_dass[i]
                        e_base = os.path.basename (e['path'])
                        #   File names and sizes match, so calculate checksum
                        if e_base == n_base and e['size'] == n['size'] :
                            e_adler = check_sum (e['path'])
                            n_adler = check_sum (n['path'])
                            #   Checksums don't match so save
                            if e_adler != n_adler :
                                n['mini'] = e['mini']
                                n_save.append (n)
                        #   Appears to be different file so save
                        else :
                            n['mini'] = e['mini']
                            n_save.append (n)
                    #else :
                        #pass
                        #n_save.append (n)
                
                #   Save this file, we will need to load it
                if len (n_save) != 0 :        
                    ret[nk] = n_save
                    n_save = []
                    
            #   Have not seen this DAS yet
            else :
                ret[nk] = new_dass
        
        self.resolved = ret        
        #pass
    
    def unite (self, TO='A') :
        '''   Unite all of the ph5 families to one. Move everything to 'A'   
        '''
        from shutil import copy2
        def _wait_for_it (P) :
            while True :
                somerunning = False
                for p in P :
                    p.poll ()
                    if p.returncode == None :
                        somerunning = True
                    elif p.returncode != 0 :
                        sys.stderr.write ("Process {0} failed.".format (p.args))
                        
                if somerunning == False : return
                
        def get_index () :
            '''   Read /Experiment_g/Receivers_g/Index_t   '''
            #s.chdir (self.home)
            msg = []
            P = []
            for m in self.nmini :
                #if m == 'A' :
                    #continue
                os.chdir (os.path.join (self.home, m))
                command = "table2kef -n master.ph5 -I > Index_t.kef"
                ret = subprocess.Popen (command, shell=True, stderr=open (os.devnull, "w"))
                P.append (ret)
                msg.append ("Extracting Index_t for {0}".format (m))
            os.chdir (self.whereami)
            _wait_for_it (P)
                
            return msg
                
        def load_index () :
            '''   Load all Index_t files into the TO family   '''
            msg = []
            P = []
            if not os.path.exists (os.path.join (self.home, TO)) :
                os.mkdir (os.path.join (self.home, TO))
                
            os.chdir (os.path.join (self.home, TO))
            for m in self.nmini :
                if m == 'A' and TO != 'A' :
                    try :
                        copy2 ('../A/master.ph5', './master.ph5')
                    except :
                        raise FormaIOError (errno=7, msg="Failed to copy A/master.ph5 to {0}/master.ph5.".format (TO))
                
                command = "kef2ph5 -n master.ph5 -k ../{0}/Index_t.kef".format (m)
                ret = subprocess.Popen (command, shell=True, stderr=open (os.devnull, "w"))
                P.append (ret)
                #   Load one at a time
                _wait_for_it (P)
                msg.append ("Extracted Index_t from {0} and loading into {1}/master.ph5.".format (m, TO))
                
            os.chdir (self.whereami)
            
            return msg
        
        def get_array () :
            '''   Dump /Experiment_g/Sorts_g/Array_t_xxx to Array_t_cat.kef   '''
            msg = []
            P = []
            for m in self.nmini :
                os.chdir (os.path.join (self.home, m))
                command = "table2kef -n master.ph5 --all_arrays > Array_t_cat.kef"
                ret = subprocess.Popen (command, shell=True, stderr=open (os.devnull, "w"))
                P.append (ret)
                msg.append ("Extracting all Array_t for {0} to Array_t_cat.kef".format (m))
            os.chdir (self.whereami)
            _wait_for_it (P)
            
            return msg
        
        def load_array () :
            '''   Load Array_t_cat files into the TO family   '''
            msg = []
            P = []
            #if not os.path.exists (os.path.join (self.home, TO)) :
                #os.mkdir (os.path.join (self.home, TO))
                
            os.chdir (os.path.join (self.home, TO))
            for m in self.nmini :
                command = "kef2ph5 -n master.ph5 -k ../{0}/Array_t_cat.kef".format (m)
                ret = subprocess.Popen (command, shell=True, stderr=open (os.devnull, "w"))
                P.append (ret)
                #   Load one at a time
                _wait_for_it (P)
                msg.append ("Extracted Array_t_cat from {0} and loading into {1}/master.ph5.".format (m, TO))
                
            os.chdir (self.whereami)
            
            return msg
                
        def move_minis () :
            '''   Move all the mini ph5 files to the TO family   '''
            msg = []
            os.chdir (os.path.join (self.home, TO))
            for m in self.nmini :
                print m
                #if m == 'A' :
                    #continue
                        
                minis = os.listdir ("../{0}".format (m))
                for mini in minis :
                    if mini[0:5] == 'miniP' and not os.path.islink (mini) :
                        try :
                            os.link ("../{0}/{1}".format (m, mini), mini)
                            #os.link (mini, "../{0}/{1}".format (m, mini))
                        except Exception as e :
                            raise FormaIOError (errno=8, msg="Failed to move {0} to A.".format (mini))
                        
                        print "Hard link {0} to {2}, preserve {1}/master.ph5.".format (mini, m, TO)
                        msg.append ("Hard link {0} to {2}, preserve {1}/master.ph5.".format (mini, m, TO))
            
            os.chdir (self.whereami)
            return msg
                
        def recreate_references () :
            '''   Recreate extermal references in /Experiment_g/Receivers_g   '''
            msg = []
            P = []
            os.chdir (os.path.join (self.home, TO))
            #   Create a copy of the original master file
            copy2 ('../A/master.ph5', '../A/master_original.ph5')
            command = "recreate_external_references -n master.ph5"
            ret = subprocess.Popen (command, shell=True, stdout=open (os.devnull, "w"), stderr=open (os.devnull, "w"))
            P.append (ret)
            #if ret :
                #raise FormaIOError (errno=9, msg="Failed to recreate external references.")
            
            msg.append ("Recreated external references in {0}/master.ph5.".format (TO))
            
            os.chdir (self.whereami)
            _wait_for_it (P)
            return msg
        
    #def unite (self, TO='A') :
        msg = []
        msg.extend (get_index ())
        msg.extend (load_index ())
        msg.extend (get_array ())
        msg.extend (load_array ())
        msg.extend (move_minis ())
        msg.extend (recreate_references ())
        #print msg
        return msg
    
    def merge (self, loaded_dass) :
        '''   Merge list of raw loaded with already loaded and re-write JSON_DB   '''
        #   What was already loaded
        db_dass = self.db_files.keys ()
        #   What we just loaded
        #loaded_dass = self.resolved.keys ()
        for das in loaded_dass :
            if not das in db_dass :
                self.db_files[das] = []
                
            for r in self.resolved[das] :
                self.db_files[das].append (r)
            
        #fh = open ('/home/azevedo/Svn/pn3-devel/Forma/merged.json', 'w+')
        #fh = open (JSON_DB, 'w')
        #json.dump (self.db_files, fh, indent=4, sort_keys=True)
        #fh.close ()
        write_json (self.db_files, os.path.join (self.home, JSON_DB))
                
#
###   Mixins
#
from zlib import adler32
def check_sum (filename) :
    fd = os.open (filename, os.O_RDONLY)
    cs = 1
    while True :
        buf = os.read (fd, 268435456)
        if not buf : break
        cs = adler32 (buf, cs)
      
    os.close (fd)  
    return cs & 0xffffffff

import re
#   For type 'texan'
texanRE = re.compile ("[Ii](\d\d\d\d).*[Tt][Rr][Dd]")
#   For type 'rt-130'
rt130RE = re.compile ("\d\d\d\d\d\d\d\.(\w\w\w\w)(\.\d\d)?\.[Zz][Ii][Pp]")
#   For type 'nodal'
nodalRE = re.compile ("[Rr](\d+)_(\d+)\.\d+\.\d+\.[Rr][Gg](\d+)")
#   For simpleton 'nodal'
simpletonodalRE = re.compile ("\d+\.fcnt")
#   For PIC rename
picnodalRE = re.compile ("PIC_(\d+)_(\d+)_\d+\.\d+\.\d+\.[Rr][Gg](\d+)")
def guess_instrument_type (filename) :
    '''   Attempt to determine type of datalogger from data file name   '''
    mo = texanRE.match (filename)
    if mo :
        das = str (int (mo.groups ()[0]) + 10000)
        return 'texan', das
    mo = rt130RE.match (filename)
    if mo :
        das = mo.groups ()[0]
        return 'rt-130', das
    mo = nodalRE.match (filename)
    if mo :
        a, b, c = mo.groups ()
        das = a + 'X' + b
        return 'nodal', das
    mo = picnodalRE.match (filename)
    if mo :
        a, b, c = mo.groups ()
        das = a + 'X' + b
        return 'nodal', das    
    mo = simpletonodalRE.match (filename)
    if mo :
        #raise FormaIOError (-100, "Error: Nodal simpleton file naming scheme: {0}. Please rename files.")
        return 'nodal', 'lllsss'
    
    return 'unknown', None

def write_json (x, filename) :
    '''   Write x in JSON format to filename   '''
    fh = open (filename, 'w')
    json.dump (x, fh, indent=4, sort_keys=True)
    fh.close ()
    
def read_json (filename) :
    '''   Read JSON file filename and return object x   '''
    try :
        fh = open (filename)
        x = json.load (fh)
        #print 'X', x
        fh.close ()
    except Exception as e :
        #sys.stderr.write (e.message)
        x = {}
        
    return x
        
def print_it (x) :
    '''   Print JSON to screen   '''
    print json.dumps (x, indent=4, sort_keys=True)

#
###   Debug and example follows
#    
if __name__ == '__main__' :
    filename = "PIC_1_25_1941.0.0.rg16"
    print guess_instrument_type (filename)
    sys.exit ()
    
    import timedoy, time
    
    #2015-08-10 18:18:59,197 Processing: /home/azevedo/Salt/Raw/D069-10Mar/Greg/I1700RAWDO69.TRD...
    processRE = re.compile ("(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)\,\d\d\d Processing: (.*[TtZz][RrIi][DdPp])\.\.\..*")
    doneRE = re.compile ("(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d).*nodes recreated\..*")    
    
    
    #fio = FormaIO (infile = '/media/sf_ORANGE_MAC/short.lst')
    #fio = FormaIO (infile = '/media/sf_ORANGE_MAC/trd.lst')
    fio = FormaIO (infile = './trd2.lst', outdir = '/storage/Salt')
    #fio.set_M (10)
    #num = int (raw_input ("Number of parts: "))
    #if num > 16 : num = 16
    #fio.set_nmini(int (num))
    #fio.set_M (35)
    fio.initialize_ph5 ()
    
    try :
        fio.open ()
    except FormaIOError as e :
        print e.errno, e.message
    
    try :
        fio.read ()
        print "Total raw: {0}GB".format (int (fio.total_raw / 1024 / 1024 / 1024))
        print "M:", fio.M
        time.sleep (10)
    except FormaIOError as e :
        print e.errno, e.message
    
    try :
        fio.readDB ()
    except FormaIOError as e :
        print e.errno, e.message
        sys.exit (-1)
    
    #print_it (fio.raw_files)    
    
    fio.resolveDB ()
    
    #   Load raw data
    cmds, pees, i = fio.run ()
    ###   Debug   ###
    l = {'A':i, 'B':i, 'C':i, 'D':i, 'E':i, 'F':i, 'G':i, 'H':i, 'I':i, 'J':i, 'K':i, 'L':i, 'M':i, 'N':i, 'O':i, 'P':i}
    cnt = 0
    out = {}; err = {}; fifo = {}
    xterms = {}
    running = True
    for m in fio.nmini :
        fifo[m] = "/tmp/fifo{0}".format (m)
        if not os.path.exists (fifo[m]) :
            os.mkfifo (fifo[m])
            
        xterms[m] = subprocess.Popen (['xterm', '-T', m,  '-e', 'tail', '-f', fifo[m]])
        #out[m] = open (fifo[m], 'w', 0)
        #out[m].write ('Testing\n')
        #out[m].close ()
        
    while running :
        running = False
        for m in fio.nmini :    
            if pees[m] == None :
                continue
            print m, pees[m].pid, 'running' if pees[m].poll () == None else pees[m].poll ()
            if pees[m].poll () == 0 :
                #pees[m].kill ()
                l[m] += 1
                t, l[m] = fio.run_cmds (cmds, x=l[m], ems=m)
                if t != None : pees[m] = t
            if pees[m].poll () == None :
                running = True
        for m in fio.nmini :
            if pees[m] == None : continue
            print "Open STDOUT"
            out[m] = open (fifo[m], 'w', 0)
            print '.'
            out[m].write (pees[m].stdout.read (1))
            print '.'
            pees[m].stdout.flush ()
            print '.'
            out[m].close ()

        print cnt, '-------------------'; cnt += 1; #time.sleep (30)
    for m in fio.nmini :
        out[m] = open (fifo[m], 'w', 0)
        out[m].write (pees[m].stdout.read ())
        pees[m].stdout.flush ()
        out[m].close ()
        print "Open STDERR"
        with open (fifo[m], 'w', 0) as out[m] :
            print '.'
            out[m].write (pees[m].stderr.read ())
            print '.'
            pees[m].stderr.flush ()
            print '.'
            #out[m].close ()
        print "Done"        
        
        
    ###   END DEBUG   ###    
    
    fio.merge (fio.resolved.keys ())

    yn = raw_input ("Merge all mini files to A: (y/n) ")
    if yn == 'y' :
        fio.unite ()
        
    fio.write_cfg ()
    
    yn = raw_input ("Kill xterms: (y/n ) ")
    if yn == 'y' :
        for k in xterms.keys () :
            xterms[k].kill ()
            
    yn = raw_input ("Calc stats: (y/n ) ")
    if yn == 'y' :
        s = 0
        for m in fio.nmini :
            #fh = open (os.path.join (fio.home, m, '125a2ph5.log'))
            #s = 0
            tot = 0
            mmin = sys.maxint
            mmax = 0
            #try :
            for dataloggerlog in ('125a2ph5.log', '1302ph5.log', 'segd2ph5.log') :
                if not os.path.exists (os.path.join (fio.home, m, dataloggerlog)) :
                    continue
                with open (os.path.join (fio.home, m, dataloggerlog)) as fh :
                #except IOError :
                    #with open (os.path.join (fio.home, m, '1302ph5.log')) as fh :
    
                    while True :
                        line = fh.readline ()
                        if not line : break
                        line = line.strip ()
                        mo = processRE.match (line)
                        if mo :
                            flds = mo.groups ()
                            tdoy = timedoy.TimeDOY (int (flds[0]), 
                                                    int (flds[1]), 
                                                    int (flds[2]), 
                                                    int (flds[3]),
                                                    int (flds[4]),
                                                    int (flds[5]))
                            #sz = SZ[flds[6]]
                            sz = os.path.getsize (flds[6])
                            tot += sz
                            if tdoy.epoch () < mmin : mmin = tdoy.epoch ()
                            if tdoy.epoch () > mmax : mmax = tdoy.epoch ()
                
                        elif doneRE.match (line) :
                            flds = doneRE.match (line).groups ()
                            tdoy = timedoy.TimeDOY (int (flds[0]), 
                                                    int (flds[1]), 
                                                    int (flds[2]), 
                                                    int (flds[3]),
                                                    int (flds[4]),
                                                    int (flds[5]))
                
                            if tdoy.epoch () < mmin : mmin = tdoy.epoch ()
                            if tdoy.epoch () > mmax : mmax = tdoy.epoch ()			
                            rate = (tot / (mmax - mmin)) / 1024. / 1024.
                            s += rate
                            print fh.name, line
                            print "===>", rate, "MB/second"
                            tot = 0
                            mmin = sys.maxint
                            mmax = 0 
                        
        print "n: ", len (fio.nmini), "Ave: ", s / float (len (fio.nmini)), "Total: ", s
    
        
