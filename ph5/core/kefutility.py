# import from python packages
import tables
from PyQt4 import QtGui, QtCore

# import from pn4
from ph5.core import kefx, ph5api
from ph5.utilities import tabletokef


PH5PATH = { "Experiment_t":"/Experiment_g/Experiment_t",
            "Sort_t":"/Experiment_g/Sorts_g/Sort_t",
            "Offset_t" :"/Experiment_g/Sorts_g/%s",
            "Event_t":"/Experiment_g/Sorts_g/%s",
            "Index_t":"/Experiment_g/Receivers_g/Index_t",
            "Map_Index_t":"/Experiment_g/Maps_g/Index_t", 
            "Time_t":"/Experiment_g/Receivers_g/Time_t", 
            "Array_t":"/Experiment_g/Sorts_g/%s",
            "All_Array_t":"/Experiment_g/Sorts_g/%s",
            "Response_t":"/Experiment_g/Responses_g/Response_t",
            "Report_t":"/Experiment_g/Reports_g/Report_t",
            "Receiver_t":"/Experiment_g/Receivers_g/Receiver_t",
            "Das_t":"/Experiment_g/Receivers_g/Das_g_%s/Das_t"}


class KefUtilityError (Exception) :
    '''   Exception gets raised in PH5Reader   '''
    def __init__ (self, message) :
        super (KefUtilityError, self).__init__ (message)
        self.message = message

########################################
# def Kef2TableData
# updated: 201703
# use kefx module to read the Kef file into [(path, dict of values), ...] to kef variable, 
# then convert to 
# * table data {path1:[2_way_data], ...}: each row is a data set
# * ketSets {path1:[labels], ...}: label for each column in table data
def Kef2TableData(statustext, filename):
    try:
        kef = kefx.Kef (filename)
        kef.open ()
        kef.read ()
        kef.rewind ()
    except Exception: raise
    
    tables ={}
    count = 0
    totalLines = kef.pathCount
    for path, kVal in kef :
        if not tables.has_key(path):
            tables[path]=[]
        entry =[] 
        for label in kef.keySets[path] :
            entry.append( kVal[label] )
        tables[path].append(entry)
        count += 1
        if count % 100 == 0: statustext.setText("Converting Kef to Data: %s/%s" % (count, totalLines))

    kef.close()
    return tables, kef.keySets, totalLines

########################################
# def Kef2TableData
# updated: 201703
# use experiment.nuke_xxx depend on the table in path to remove the table from the PH5file
#def NukeTable(parent, PH5file, exp, path):
    #pathExist = True
    #try:
        ##   /Experiment_g/Experiment_t
        #if "Experiment_t" in path :
            #exp.nuke_experiment_t ()
            
        ##   /Experiment_g/Sorts_g/Sort_t
        #if "Sort_t" in path :
            #exp.ph5_g_sorts.nuke_sort_t ()
            
        ##   /Experiment_g/Sorts_g/Offset_t_[array]_[shotline]  (i.e. array: 001, shotline 001 )
        #if "Offset_t" in path :
            #offset_t = path.split("/")[-1]
            #if not exp.ph5_g_sorts.nuke_offset_t (offset_t) : raise KefUtilityError("%s Not found." % offset_t)    
            
        ##   /Experiment_g/Sorts_g/Event_t or /Experiment_g/Sorts_g/Event_t_[event]               (i.e. event: 001)
        #if "Event_t" in path :
            #event_t = path.split("/")[-1]
            #if not exp.ph5_g_sorts.nuke_event_t (event_t) : raise KefUtilityError("%s Not found." % event_t)
            
        ##   /Experiment_g/Sorts_g/Array_t_[array]               (i.e. array: 001)
        #if "Array_t" in path :
            #array_t = path.split("/")[-1]
            #array = int( path.split("_")[-1] )      # table name is recreated in nuke_array_t()
            #print "array: '%d'" % array
            #if not exp.ph5_g_sorts.nuke_array_t (array) : raise KefUtilityError("%s Not found." % array_t)
    
        ##   /Experiment_g/Receivers_g/Time_t
        #if "Time_t" in path:
            #exp.ph5_g_receivers.nuke_time_t ()
            
        ##   /Experiment_g/Receivers_g/Index_t
        #if "Receivers_g/Index_t" in path :
            #exp.ph5_g_receivers.nuke_index_t ()
            
        ##   /Experiment_g/Maps_g/Index_t
        #if "Maps_g/Index_t" in path :
            #exp.ph5_g_maps.nuke_index_t ()
            
        ##   /Experiment_g/Receivers_g/Receiver_t
        #if "Receiver_t" in path :
            #exp.ph5_g_receivers.nuke_receiver_t ()
            
        ##   /Experiment_g/Responses_g/Response_t
        #if "Response_t" in path :
            #exp.ph5_g_responses.nuke_response_t ()
            
        ##   /Experiment_g/Reports_g/Report_t
        #if "Report_t" in path :
            #exp.ph5_g_reports.nuke_report_t ()
            
        ##   /Experiment_g/Receivers_g/Das_g_[das]/Das_t     (i.e. das: 91E6)
        #if "Das_t" in path :
            #das = path.split("/")[-2].split("_")[-1]
            #exp.ph5_g_receivers.nuke_das_t (das)
    #except tables.exceptions.NoSuchNodeError:
        #pathExist = False
    #except KefUtilityError, e:
        #print "KefUtilityError: %s" % e.message
        #pathExist = False      
    #except Exception, e:
        #QtGui.QMessageBox.warning(parent, "Error in KefUtility.NukeTable()", str(e) )
        #return False
    
    #if pathExist == False:
        #msg = "PATH '%s' does not exist in PH5 FILE '%s'.\n\nDo you want to insert the table into this PH5 FILE." % (path, PH5file)
        #result = QtGui.QMessageBox.question(parent, "Insert table?", msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No )
        #if result == QtGui.QMessageBox.No:
            #QtGui.QMessageBox.warning(parent, "Warning", "Saving interupted" )
            #return False
    #return True
               
    
def NukeTable(parent, PH5file, path2file, tablepath):
    if "Experiment_t" in tablepath : op = '-E'
    if "Sort_t" in tablepath : op = '-S'
    if "Offset_t" in tablepath : 
        arg = tablepath.split("/")[-1].replace('Offset_t_','')
        op = '-O %s' % arg
    if "Event_t" in tablepath :
        arg = tablepath.split("/")[-1].replace('Event_t_','')
        op = '-V %s' % arg
    if "Array_t" in tablepath :
        arg = tablepath.split("/")[-1].replace('Array_t_','')
        op = '-A %s' % arg
    if "Time_t" in tablepath: op = '-T'
    if "Receivers_g/Index_t" in tablepath : op = '-I'
    if "Maps_g/Index_t" in tablepath : op = '-M'
    if "Receiver_t" in tablepath : op = '-C'
    if "Response_t" in tablepath : op = '-R'
    if "Report_t" in tablepath : op = '-P'
    if "Das_t" in tablepath :
        arg = tablepath.split("/")[-2].split("_")[-1]
        op = '-D %s' % arg
    
    from subprocess import Popen, PIPE, STDOUT

    cmdStr = "nuke-table -p %s -n %s %s" % (path2file, PH5file, op)
    p = Popen(cmdStr, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    output = p.stdout.read()
    print "The following command is running:\n", cmdStr   
    print "Output: ", output
    
    if 'not found' in output.lower():
        msg = "PATH '%s' does not exist in PH5 FILE '%s'.\n\nDo you want to insert the table into this PH5 FILE." % (tablepath, PH5file)
        result = QtGui.QMessageBox.question(parent, "Insert table?", msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No )
        if result == QtGui.QMessageBox.No:
            QtGui.QMessageBox.warning(parent, "Warning", "Saving interupted." )
            return False
    if 'error' in output.lower():
        title = "Error in removing table %s from PH5 file" % tablepath
        result = QtGui.QMessageBox.warning(parent, title, output + "\n\nSaving interupted.")
        return False       
    return True    
    
    
########################################
# def PH5toTableData
# updated: 201703
# use tabletokef.readPH5 to read the PH5 file into ph5data {KEY:[keys,rows], ...} or just keys, rows
# in which keys is list of labels, and rows is dict of values; KEYs are the array id/ eventid ...
# then convert to table data {path1:[2_way_data],...} and ketSets {path1:[labels], ...}
def PH5toTableData(statustext, ph5, filename, path2file, tableType, arg=None):
    ph5data = tabletokef.readPH5(ph5, filename, path2file, tableType, arg)
    tables = {}
    keySets = {}
    count = 0
    TOTAL = 0
    if ph5data.__class__.__name__ == 'dict':
        for k in ph5data.keys():
            path = PH5PATH[tableType] % k
            if not tables.has_key(path): 
                tables[path] = []  
                keySets[path] = ph5data[k].keys
            count, totalLines = _appendTable(tables[path], ph5data[k], path, statustext, count)
            TOTAL += totalLines
                
    else:
        path = PH5PATH[tableType]
        if tableType == 'Array_t': path = path % "Array_t_{0:03d}".format( int(arg) )
        tables[path] = []
        keySets[path] = ph5data.keys
        count, totalLines = _appendTable(tables[path], ph5data, path, statustext, count)    
        TOTAL += totalLines
    return tables, keySets, TOTAL

########################################
# def _appendTable
# updated: 201703
# convert rows to 2 way data for tables of which columns in order of keys (rows and keys are attr. of ph5Vval)
def _appendTable(table , ph5Val, path, statustext, count):
    totalLines = len(ph5Val.rows)
    for r in ph5Val.rows:
        entry = []
        for label in ph5Val.keys: 
            entry.append( str(r[label]) )
        table.append(entry)    
        count += 1
        if count % 100 == 0: statustext.setText("Converting PH5 to Data in %s: %s/%s" % (path, count, totalLines))
    return count, totalLines
        
########################################
# def GetPrePH5Info
# updated: 201703
# read the given PH5 file and return ph5 available tables, arrays, events, shotlines, das
# for user to choose which table he want to edit
# (ph5 return to use to continue to read ph5data)
def GetPrePH5Info(filename, path2file=""):
    availTables = []
    # initialize
    ph5 = ph5api.PH5 (path=path2file, nickname=filename, editmode=False)
  
    # event
    ph5.read_event_t_names ()

    shotLines = []
    if len(ph5.Event_t_names) != 0: 
        shotNames = sorted( ph5.Event_t_names )    
        events = []
        for n in shotNames :
            if n == 'Event_t': shotLines.append('0')
            else: shotLines.append( n.replace('Event_t_', '') )
            ph5.read_event_t (n)    
            events = events + ph5.Event_t[n]['order']      
        if events != []: availTables.append('Event_t')          # check this condition in case the read file is not a master file

    # array
    ph5.read_array_t_names ()
    if len(ph5.Array_t_names) != 0: 
        availTables.append("Array_t")
        availTables.append("All_Array_t")
    arrays = sorted( [str(int(a.replace("Array_t_", ""))) for a in ph5.Array_t_names] )
    # offset
    ph5.read_offset_t_names ()
    if len(ph5.Offset_t_names) != 0 and len(ph5.Array_t_names) != 0 \
    and len(ph5.Event_t_names) != 0:                            # check this condition in case the read file is not a master file
        availTables.append('Offset_t')
    # das
    ph5.read_das_g_names ()
    if len(ph5.Das_g_names) != 0 : availTables.append("Das_t")
    das = sorted( [d.replace("Das_g_", "") for d in ph5.Das_g_names.keys()] )
    
    # experiment
    ph5.read_experiment_t ()
    if len(ph5.Experiment_t['rows']) != 0 : availTables.append("Experiment_t")
    # receiver
    ph5.read_receiver_t ()
    if len(ph5.Receiver_t['rows']) != 0: availTables.append('Receiver_t')
    # response
    ph5.read_response_t ()
    if len(ph5.Response_t['rows']) != 0: availTables.append('Response_t')
    # time
    ph5.read_time_t ()
    if len(ph5.Time_t['rows']) != 0: availTables.append('Time_t')
    # index
    ph5.read_index_t ()
    if len(ph5.Index_t['rows']) != 0 : availTables.append("Index_t")
    
    # map index
    rows, keys = ph5.ph5_g_maps.read_index()
    if len(rows) != 0: availTables.append("Map_Index_t")
    # report
    rows, keys = ph5.ph5_g_reports.read_reports()
    if len(rows) != 0: availTables.append("Report_t")
    
    # sort    
    ph5.read_sort_t()
    if len(ph5.Sort_t) != 0: availTables.append('Sort_t')
    
    return ph5, sorted( availTables ), arrays, shotLines, das


if __name__ == '__main__' :
    path2file = "/home/field/Desktop/data/Sigma"
    #path2file = "/home/field/Desktop/data/10-016"
    #path2file = "/home/field/Desktop/data/13-005"
    filename = 'master.ph5'
    #tableType = "All_Array"
    #tableType = "Das_t"
    #PH5toDataTable(filename, path2file, tableType, '9D5B')
    #tables, labels =PH5toDataTable(filename, path2file, tableType )
    #t = tabletokef.readPH5(filename, path, tableType,"1")

    
    #path2file = "/home/field/Desktop/KefEdit/KeftestingFile"
    #filename = 'testph5.ph5'
    GetPrePH5Info(filename, path2file)
    
    #print "Available Tables:", availTables