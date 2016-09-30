#!/usr/bin/env python

import shutil, os, stat, sys, time
from compileall import *

PROG_VERSION = '2016.133'

#   Location of PASSCAL distribution
ROOTDIR = '/opt/k4'
#
if len(sys.argv) > 1 :
    ROOTDIR = sys.argv[1]
elif os.environ.has_key ('KX') :
    ROOTDIR = os.environ['KX']
else :
    sys.stderr.write ("KX environment variable not set!\n")
    sys.exit ()

PROGDIR = os.getcwd ()
PROG = os.path.basename (PROGDIR)
LIBDIR = os.path.join (ROOTDIR, 'apps')
BINDIR = os.path.join (ROOTDIR, 'bin')
LIBPROG = os.path.join (LIBDIR, PROG)
PYTHON = os.path.join (BINDIR, 'pnpython4')
CONFIGDIR = os.path.join (ROOTDIR, 'config')

PROGS = ('125a2ph5',
         '1302ph5',
         'geod2kef',
         'initialize-ph5',
         'kef2ph5',
         'kmz-builder',
         'ph5toseg',
         'report2ph5',
         'report2ph5',
         'meta-data-gen',
         'sort-kef-gen',
         'table2kef',
         'time-kef-gen',
         'fix_num_samples',
         'set_deploy_pickup_times',
         'noven',
         'recvorder',
         'dumpsgy',
         'fix_3chan_texan',
         'obsipshot2dep',
         'index_offset_t',
         'recreate_external_references',
         'migrate_2to3',
         'nuke-table',
         'segy2ph5',
         'dumpsac',
         'ph5tosac',
         'sort-shot-kef',
         'sort-recv-kef',
         'ph5_merge_helper',
         'experiment_t-gen',
         'segd2ph5',
         'ph5_total',
	 'pformaCL',
         'pforma',
         'ph5toms',
         'ph5tods',
         'grao2ph5',
         'dumpfair',
         'ph5view',
         'unsimpleton',
         'ph5torec',
         'ph5toevt')

LIBS  = ('columns',
         'Dep',
         'decimate',
         'Experiment',
         'ebcdic',
         'firfilt_py',
         'ibmfloat',
         'Kef',
         'pn125',
         'pn130',
         'RT_130_h',
         'SEGYFactory',
         'SEGY_h',
         'TimeDoy',
         'TimeDOY',
         'SimpleMap',
         'cs2cs',
         'PH5DB',
         'PH5Helper',
         'SegyReader',
         'SACReader',
         'SACFactory',
         'SAC_h',
         'SEGD_h',
         'SegdReader',
         'mplTurkey',
         'ph5API',
	 'pformaIO',
         'PMonitor',
         'WatchIt')

EXTS = ('surt_130_py.py', 'sufirfilt_py.py', 'surt_125a_py.py', 'suibm2ieee_py.py', 'subcd_py.py',)

#   Delete libs
for p in LIBS :
    p = p + '.pyc'
    try :
        os.remove (p)
    except OSError :
        pass
    
#   Compile
compile_dir (".")
#   Make libs dir
command = 'mkdir -p ' + LIBDIR
os.system (command)
#   Make config directory
command = 'mkdir -p ' + CONFIGDIR
os.system (command)
#   Remove old libs
try :
    shutil.rmtree (LIBPROG)
except OSError :
    pass


command = 'mkdir -p ' + BINDIR
os.system (command)

#   install programs
for p in PROGS :
    src = p
    dst = BINDIR + '/' + p
    try :
        os.remove (dst)
    except OSError :
        pass
    
    print src, dst
    shutil.copy (src, dst)
    os.chmod (dst, 0755)

#   compile extensions
for e in EXTS :
    print "Compiling extension " + e
    command = PYTHON + " " + e + " clean --build-lib=."
    os.system (command)
    command = PYTHON + " " + e + " build --build-lib=."
    os.system (command)

#   install libraries
shutil.copytree (PROGDIR, LIBPROG)
fh = open (os.path.join (ROOTDIR, "install_date.txt"), 'w')
fh.write (time.ctime (time.time ())); fh.close ()

##   install configs
#if not os.path.exists (os.path.join (CONFIGDIR, 'PH5Server.cfg')) :
    #shutil.copy ('./config.cfg', os.path.join (CONFIGDIR, 'PH5Server.cfg'))

#if not os.path.exists (os.path.join (CONFIGDIR, 'ftpserver.cfg')) :
    #shutil.copy ('./config.cfg', os.path.join (CONFIGDIR, 'ftpserver.cfg'))

#if not os.path.exists (os.path.join (CONFIGDIR, 'pass.dat')) :
    #shutil.copy ('./pass.dat', os.path.join (CONFIGDIR, 'pass.dat'))
    
#if not os.path.exists (os.path.join (CONFIGDIR, 'PH5.db')) :
    #shutil.copy ('./PH5.db', os.path.join (CONFIGDIR, 'PH5.db'))

if not os.path.exists (os.path.join (CONFIGDIR, 'Event.cfg')) :
    shutil.copy ('./Event.cfg', os.path.join (CONFIGDIR, 'Event.cfg'))
else :
    print "Using existing {0}".format (os.path.join (CONFIGDIR, 'Event.cfg'))
    
if not os.path.exists (os.path.join (CONFIGDIR, 'Receiver.cfg')) :
    shutil.copy ('./Receiver.cfg', os.path.join (CONFIGDIR, 'Receiver.cfg'))
else :
    print "Using existing {0}".format (os.path.join (CONFIGDIR, 'Receiver.cfg'))
    
#   install ph5 GUIs
#print "Installing PH5GUI..."
#command = "cd PH5GUI; pnpython3 install.py"
#os.system (command)
