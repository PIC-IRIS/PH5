#!/usr/bin/env pnpython3
#
#   Program to convert kitchen version 2 ph5 file to kitchen version 3 file.
#   Steve Azevedo, February 2013
#

import os, sys, time, math, re, logging
from subprocess import Popen, PIPE
import columns, Experiment

PROG_VERSION = "2014.022.b"
MAX_PH5_BYTES = 1073741824 * 2   #   2GB (1024 X 1024 X 1024 X 2)
MINIPH5INDEX = 1
MINIPH5SIZE = 0

ph5RE = re.compile (".*\d\d-\d\d\d\.ph5")

CURRENT_DAS = None
DAS_INFO = {}
#
#   To hold table rows and keys
#
class rows_keys (object) :
    __slots__ = ('rows', 'keys')
    def __init__ (self, rows = None, keys = None) :
        self.rows = rows
        self.keys = keys
        
    def set (self, rows = None, keys = None) :
        if rows != None : self.rows = rows
        if keys != None : self.keys = keys
#
#
#
class index_t_info (object) :
    __slots__ = ('das', 'ph5file', 'ph5path', 'startepoch', 'stopepoch')
    def __init__ (self, das, ph5file, ph5path, startepoch, stopepoch) :
        self.das        = das
        self.ph5file    = ph5file
        self.ph5path    = ph5path
        self.startepoch = startepoch
        self.stopepoch  = stopepoch
#
#
#
def initializeExperiment (name, EDIT) :
    
    ex = Experiment.ExperimentGroup (nickname = name)
    #EDIT = True
    ex.ph5open (EDIT)
    ex.initgroup ()
    
    return ex
#
#
#
def read_das_groups () :
    '''   Get das groups   '''
    global EX
    
    #   Get references for all das groups keyed on das
    return EX.ph5_g_receivers.alldas_g ()
#
#
#
def update_index_t_info (tofile, starttime, samples, sps) :
    global DAS_INFO
    #tdoy = TimeDoy.TimeDoy ()
    ph5file = tofile
    ph5path = '/Experiment_g/Receivers_g/' + EX.ph5_g_receivers.current_g_das._v_name
    das = ph5path[32:]
    stoptime = starttime + (float (samples) / float (sps))
    di = index_t_info (das, ph5file, ph5path, starttime, stoptime)
    if not DAS_INFO.has_key (das) :
        DAS_INFO[das] = []
        
    DAS_INFO[das].append (di)
    #logging.info ("DAS: {0} File: {1} First Sample: {2} Last Sample: {3}".format (das, ph5file, time.ctime (starttime), time.ctime (stoptime)))
#
#
#
def writeINDEX () :
    global DAS_INFO, INDEX_T
    
    dass = DAS_INFO.keys ()
    dass.sort ()
    
    for das in dass :
        i = {}
        start = sys.maxint
        stop = 0.        
        das_info = DAS_INFO[das]
        for d in das_info :
            i['external_file_name_s'] = d.ph5file
            i['hdf5_path_s'] = d.ph5path
            i['serial_number_s'] = das
            if d.startepoch < start :
                start = d.startepoch
                
            if d.stopepoch > stop :
                stop = d.stopepoch
                
        i['time_stamp/epoch_l'] = int (time.time ())
        i['time_stamp/micro_seconds_i'] = 0
        i['time_stamp/type_s'] = 'BOTH'
        i['time_stamp/ascii_s'] = time.ctime (i['time_stamp/epoch_l'])
        
        i['start_time/epoch_l'] = int (math.modf (start)[1])
        i['start_time/micro_seconds_i'] = int (math.modf (start)[0] * 1000000)
        i['start_time/type_s'] = 'BOTH'
        i['start_time/ascii_s'] = time.ctime (start)
        
        i['end_time/epoch_l'] = math.modf (stop)[1]
        i['end_time/micro_seconds_i'] = int (math.modf (stop)[0] * 1000000)
        i['end_time/type_s'] = 'BOTH'
        i['end_time/ascii_s'] = time.ctime (stop)
                
        MASTER.ph5_g_receivers.populateIndex_t (i)
            
    rows, keys = MASTER.ph5_g_receivers.read_index ()
    INDEX_T = rows_keys (rows, keys)
    
    DAS_INFO = {}
#
#
#
def update_external_references () :
    #global EX, INDEX_T
    
    logging.info ("Updating external references...")
    #
    n = 0
    for i in INDEX_T.rows :
        external_file = i['external_file_name_s'][2:]
        external_path = i['hdf5_path_s']
        das = i['serial_number_s']
        target = external_file + ':' + external_path
        external_group = external_path.split ('/')[3]
        ###print external_file, external_path, das, target, external_group
        
        #   Nuke old node
        try :
            group_node = MASTER.ph5.get_node (external_path)
            group_node.remove ()
        except Exception, e :
            pass
            ###print "E1 ", e
            
        #   Re-create node
        try :
            MASTER.ph5.create_external_link ('/Experiment_g/Receivers_g', external_group, target)
            n += 1
        except Exception, e :
            pass
            ###print "E2 ", e
            
        #sys.exit ()
    logging.info ("Done, {0} nodes recreated.\n".format (n))
#
#
#
def recreate_index_t () :
    #   Remove and recreate empty Index_t table
    MASTER.ph5_g_receivers.nuke_index_t ()
#
#
#
def get_group_size (Group, Das_t) :
    ret = 0
    for das_t in Das_t.rows :
        leaf = EX.ph5.get_node ('/Experiment_g/Receivers_g/' + Group._v_name + '/' + das_t['array_name_data_a'])
        ret += leaf.size_on_disk
        
    return ret
#
#
#
def copygroup (fromg, tof) :
    f = '{0}:/Experiment_g/Receivers_g/{1}'.format (PH5, fromg)
    t = '{0}:/Experiment_g/Receivers_g/{1}'.format (tof, fromg)
    command = 'ptrepack --complevel 6 --overwrite-nodes --chunkshape="auto" {0} {1}'.format (f, t)
    #command = 'h5repack -f GZIP=6 {0} {1}'.format (f, t)
    #
    logging.info ("sh: {0}".format (command))
    os.system (command)
#
#
#
def copyother () :
    command = 'ptrepack --overwrite-nodes {0}:/Experiment_g/Reports_g master.ph5:/Experiment_g/Reports_g'.format (PH5)
    # 
    logging.info ("sh: {0}".format (command))
    os.system (command)
    command = 'ptrepack --overwrite-nodes {0}:/Experiment_g/Responses_g master.ph5:/Experiment_g/Responses_g'.format (PH5)
    #
    logging.info ("sh: {0}".format (command))
    os.system (command)
    command = 'ptrepack --overwrite-nodes {0}:/Experiment_g/Sorts_g master.ph5:/Experiment_g/Sorts_g'.format (PH5)
    logging.info ("sh: {0}".format (command))
    os.system (command)
    command = 'ptrepack --overwrite-nodes {0}:/Experiment_g/Receivers_g/Time_t master.ph5:/Experiment_g/Receivers_g/Time_t'.format (PH5)
    logging.info ("sh: {0}".format (command))
    os.system (command)
    #command = 'ptrepack --upgrade-flavors --overwrite-nodes {0}:/Experiment_g/Experiment_t master.ph5:/Experiment_g/Experiment_t'.format (PH5)
    #os.system (command)
#
#
#
def build_index_t_index () :
    global MINIPH5INDEX, MINIPH5SIZE, MAX_PH5_BYTES
    dasgroups = read_das_groups ()
    dass = dasgroups.keys (); dass.sort ()
    for das in dass :
        EX.ph5_g_receivers.setcurrent (dasgroups[das])
        das_r, das_keys = EX.ph5_g_receivers.read_das ()
        Das_t = rows_keys (das_r, das_keys)
        groupsize = get_group_size (dasgroups[das], Das_t)
        groupsize = int (groupsize * 1.15)
        if groupsize > MAX_PH5_BYTES :
            MAX_PH5_BYTES *= 2
            
        if groupsize + MINIPH5SIZE > MAX_PH5_BYTES :
            MINIPH5INDEX += 1
            MINIPH5SIZE = 0
        else :
            MINIPH5SIZE += groupsize
            
        minifile = './miniPH5_{0:05d}.ph5'.format (MINIPH5INDEX)
        if not os.path.exists (minifile) :
            initialize_ph5 (minifile)
            
        copygroup (dasgroups[das]._v_name, minifile)
        
        for das_t in Das_t.rows :
            update_index_t_info (minifile, das_t['time/epoch_l'] + (float (das_t['time/micro_seconds_i']) / 1000000.), das_t['sample_count_i'], das_t['sample_rate_i'] / das_t['sample_rate_multiplier_i'])
#
#
#
def initialize_ph5 (filename) :
    global NEWPH5FILES
    
    command = "initialize-ph5 -n {0} 2>&1 > /dev/null".format (filename)
    logging.info ("sh: {0}".format (command))
    os.system (command)
    NEWPH5FILES.append (filename)
    #return initializeExperiment (filename)
#
#
#
def read_experiment_table () :
    '''   Read /Experiment_g/Experiment_t   '''
    exp, exp_keys = EX.read_experiment ()
    
    rowskeys = rows_keys (exp, exp_keys)
    
    return rowskeys
#
#
#
def convert_response () :
    '''   Convert to new gain format, gain/value_d   '''
    response_t = []
    ret = {}
    for r in RESPONSE_T.rows :
        for K in r.keys () :
            if K == 'gain_i' :
                ret['gain/value_i'] = r[K]
            else :    
                ret[K] = r[K]
            
        response_t.append (ret)
        ret = {}
            
    return response_t
                
#
#
#
def read_response_table () :
    '''   Read /Experiment_g/Responses_g/Response_t   '''
    res, res_keys = EX.ph5_g_responses.read_responses ()
    
    rowskeys = rows_keys (res, res_keys)
    
    return rowskeys
#
#
#
def update_response_t (response_t) :
    if not response_t : return
    
    for r in response_t :
        MASTER.ph5_g_responses.populateResponse_t (r)
#
#
#
def update_experiment_t () :
    for experiment_t in EXPERIMENT_T.rows :
        pass
    
    if EXPERIMENT_ID :
        experiment_t['experiment_id_s'] = EXPERIMENT_ID
    else :
        experiment_t['experiment_id_s'] = EXPERIMENT_ID
        
    MASTER.populateExperiment_t (experiment_t)
#
#
#
def run_h5check () :
    errs = []
    for f in NEWPH5FILES :
        command = 'h5check -v0 -e -f18 {0} 2>&1'.format (f)
        logging.info ("sh: {0}".format (command))
        #ret = os.system (command)
        p = Popen (command, shell=True, stdout=PIPE)
        O = p.stdout.readlines ()
        for o in O :
            o = o.strip ('\n')
            logging.info (o)
        
if __name__ == '__main__' :
    global PH5, EX, MASTER, EXPERIMENT_T, EXPERIMENT_ID, NEWPH5FILES, RESPONSE_T
    EXPERIMENT_ID = None
    NEWPH5FILES = []
    
    def usage () :
        print "Version: {0} migrate_2to3 ph5_version_2_file.ph5".format (PROG_VERSION)
        sys.exit ()
        
    try :
        PH5 = sys.argv[1]
        if not os.path.exists (PH5) :
            raise IndexError
        if ph5RE.match (PH5) :
            EXPERIMENT_ID = os.path.basename (PH5)[:-4]
    except IndexError :
        usage ()
       
    logging.basicConfig (
        filename = os.path.join ('.', "migrate_2to3.log"),
        format = "%(asctime)s %(message)s",
        level = logging.INFO
    ) 
    logging.info ("Opening: {0}".format (PH5))
    #EX = initializeExperiment (PH5, True)
    #EX.ph5close ()
    EX = initializeExperiment (PH5, False)
    EXPERIMENT_T = read_experiment_table ()
    RESPONSE_T = read_response_table ()
    logging.info ("Opening: master.ph5 and miniPH5_00001.ph5")
    initialize_ph5 ('master.ph5')
    MASTER = initializeExperiment ('master.ph5', True)
    initialize_ph5 ('miniPH5_00001.ph5')
    build_index_t_index ()
    recreate_index_t ()
    writeINDEX ()
    update_external_references ()
    #copyother ()
    update_experiment_t ()
    EX.ph5close (); MASTER.ph5close ()
    copyother ()
    MASTER = initializeExperiment ('master.ph5', True)
    MASTER.ph5_g_responses.nuke_response_t ()
    ret = convert_response ()
    update_response_t (ret)
    MASTER.ph5close ()
    run_h5check ()
    logging.info ("Done")
        
    
    