#!/usr/bin/env pnpython3

import sys, os, string, re
from ph5.core import columns

PROG_VERSION = '2016.106 Developmental'

#   This line contains a key/value entered as is
#keyValRE = re.compile ("(\w*)\s*=\s*(\w*)")
#   This line contains a key/file read in as an array
#keyFileRE = re.compile ("(\w*)\s*:\s*(\w*)")
keyValFileRE = re.compile ("(.*)\s*[;=]\s*(.*)")
#
updateRE = re.compile ("(/.*):Update:(.*)\s*")
#
deleteRE = re.compile ("(/.*):Delete:(.*)\s*")
#
receiverRE = re.compile ("/Experiment_g/Receivers_g/Das_g_.*")

arrayRE = re.compile ("/Experiment_g/Sorts_g/Array_t_(\d+)")
eventRE = re.compile ("/Experiment_g/Sorts_g/Event_t(_(\d+))?")
offsetRE = re.compile ("/Experiment_g/Sorts_g/Offset_t(_(\d+)_(\d+))?")

class KefError (Exception) :
    def __init__ (self, args = None) :
        self.args = args

class KefWarning (Exception) :
    def __init__ (self, args = None) :
        self.args = args

class Kef :
    '''
          Deal with kef (kitchen, exchange, format) files.
    '''
    def __init__ (self, filename) :
        self.filename = filename    #   The input file
        self.fh = None              #   The file handle
        self.parsed = {}            #   The file parsed: parsed[path] = [keyval, keyval, ...] keyval = (keys are table keys)
        self.updateMode = False     #
        self.keyvals = []           #   Current key value dictionary list
        self.current_path = None    #
        self.paths = []             #
        
    def open (self) :
        try :
            self.fh = file (self.filename)
        except Exception, e :
            self.fh = None
            raise KefError ("Failed to open %s. Exception: %s\n" % (self.filename, e))
            
    def close (self) :
        self.fh.close ()
            
    def read (self, num = None) :
        appnd = ""
        keyval = {}
        self.parsed = {}
        path = None
 
        EOF = False
        sincepath = 0
        nret = 0
        n = sys.maxint
        if num != None :
            n = num
        
        while n > 0 :
            n -= 1
            line = self.fh.readline ()
            if not line : 
                EOF = True
                break
            
            nchars = len (line)
            #   Skip empty lines and comments
            if line[0] == '#' or line[0] == '\n' :
                if sincepath != 0 :
                    sincepath -= nchars
                continue
            
            #   Remove all leading and trailing whitespace   
            line = string.strip (line)
            #   If the length of the stripped line is 0, continue to next line
            if not line : continue
            nret += 1
            #   If line ends in '\' it is continued on next line
            while line[-1] == '\\' :
                line = line[:-1]
                line = line + ' '
                appnd = self.fh.readline ()
                if not appnd : break
                nchar += len (appnd)
                appnd = string.strip (appnd)
                line = line + appnd
                
            #   This line contains the path to the table to update
            if line[0] == '/' :
                if path :
                    self.parsed[path].append (keyval)
                    keyval = {}
                    
                path = line
                sincepath = nchars * -1
                continue

            mo = keyValFileRE.match (line)
            if mo :
                key, value = mo.groups ()
                sincepath -= nchars
            else :
                sys.stderr.write ("Warning: unparsable line: %s\nSkipping\n" % line)
                continue
                
            key = string.strip (key); value = string.strip (value)
            if value != 'None' :
                if not self.parsed.has_key (path) :
                    self.parsed[path] = []
                    
                keyval[key] = value
            
        #   No limits on what to read
        if num == None or EOF :
            if keyval :
                self.parsed[path].append (keyval)
        else :
            self.fh.seek (sincepath, os.SEEK_CUR)
        
        return nret

    def _next_path (self) :
        try :
            path = self.paths.pop (0)
            self.keyvals = self.parsed[path]
        except IndexError :
            path = None
            self.keyvals = []
            
        if path and updateRE.match (path) :
            self.updateMode = True
        else :
            self.updateMode = False
            
        self.current_path = path
        return path
    
    def _next_keyval (self) :
        try :
            keyval = self.keyvals.pop (0)
        except IndexError :
            keyval = None
            
        return keyval
        
    #   Return next path and key value dictionary       
    def next (self) :
        path = self.current_path 
        keyval = self._next_keyval ()
        if not keyval :
            path = self._next_path ()
            keyval = self._next_keyval ()
        
        return path, keyval
    #   Rewind
    def rewind (self) :
        self.paths = self.parsed.keys ()
        self.keyvals = []
    #   
    def batch_update (self, trace = False) :
        '''   Batch update ph5 file from kef file   '''
        err = False
        self.rewind ()
        p, kv = self.next ()
        while p :
            if trace == True :
                kys = kv.keys ()
                sys.stderr.write ('=-' * 30)
                sys.stderr.write ("\n%s\n" % p)
                for k in kys :
                    sys.stderr.write ("\t%s = %s\n" % (k, kv[k]))
                    
            DELETE = False
            #   Update or Append or Delete
            mo = deleteRE.match (p)
            if mo :
                DELETE = True
            else :
                mo = updateRE.match (p)
            
            key = []
            if mo :
                p, k = mo.groups ()
                key.append (k)
                
            #if receiverRE.match (p) :
                ##   We are trying to update something in a Receivers_g
                #sys.stderr.write ("Warning: Attempting to modify something under /Experiment_g/Receivers_g.\n")
                
            #   columns.TABLES keeps a dictionary of key = table name, value = reference to table              
            if not columns.TABLES.has_key (p) :
                sys.stderr.write ("Warning: No table reference for key: %s\n" % p)
                sys.stderr.write ("Possibly ph5 file is not open or initialized?\n")
                p, kv = self.next ()
                continue
            
            #   Get handle
            ref = columns.TABLES[p]
            #   key needs to be list for columns.validate
            if trace == True :
                sys.stderr.write ("Validating...\n")
                
            errs_keys, errs_required = columns.validate (ref, kv, key)
            for e in errs_keys + errs_required :
                err = True
                sys.stderr.write (e + '\n')
                
            if trace == True :
                sys.stderr.write ("Done\n")
                
            if len (key) == 0 :
                key = None
            else :
                key = key.pop (0)
                
            if DELETE :
                if trace == True :
                    sys.stderr.write ("Deleting...")
                else :    
                    columns.delete (ref, kv[key], key)
            else :
                if trace == True :
                    sys.stderr.write ("Updating...")
                else :    
                    columns.populate (ref, kv, key)
            
            if trace == True :
                sys.stderr.write ("Skipped\n")
                
            p, kv = self.next ()
        
        return err
    
    def strip_receiver_g (self) :
        ret = []
        self.rewind ()
        
        for p in self.paths :
            #print p
            if receiverRE.match (p) :
                base = string.split (p, ':')[0]
                ret.append (base)
                
        return ret
    
    def strip_a_e_o (self) :
        reta = {}
        rete = {}
        reto = {}
        self.rewind ()
        
        for p in self.paths :
            #print p
            if arrayRE.match (p) :
                base = string.split (p, '/')[-1:]
                reta[base[0]] = True
            elif eventRE.match (p) :
                base = string.split (p, '/')[-1:]
                rete[base[0]] = True
            elif offsetRE.match (p) :
                base = string.split (p, '/')[-1:]
                reto[base[0]] = True
                
        a = reta.keys ()
        a.sort ()
        e = rete.keys ()
        e.sort ()
        o = reto.keys ()
        o.sort ()        
        
        return a, e, o
    
    def ksort (self, key) :
        def cmp_on_key (x, y) :
            return cmp (int (x[key]), int (y[key]))
        
        keys = self.parsed.keys ()
        for k in keys :
            elements = self.parsed[k]
            tmp = sorted (elements, cmp_on_key)
            self.parsed[k] = tmp
        
if __name__ == '__main__' :
    k = Kef ('Experiment_t.kef')
    k.open ()
    k.read ()
    #k.batch_update ()
    k.rewind ()
    
    p, kv = k.next ()
    while p :
        kall = kv.keys ()
        kall.sort ()
        for k1 in kall :
            print p, k1, kv[k1]
            
        p, kv = k.next ()
        
    k.close ()
    
