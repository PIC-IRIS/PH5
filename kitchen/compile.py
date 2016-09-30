#!/usr/bin/env python

import shutil, os, stat, sys, time
from compileall import *

PROG_VERSION = '2014.005.a'

#   Location of PASSCAL distribution
ROOTDIR = '/opt/k3'
#
if len(sys.argv) > 1 :
    ROOTDIR = sys.argv[1]
elif os.environ.has_key ('K3') :
    ROOTDIR = os.environ['K3']
else :
    sys.stderr.write ("K3 environment variable not set!\n")
    sys.exit ()

PROGDIR = os.getcwd ()
PROG = os.path.basename (PROGDIR)
LIBDIR = os.path.join (ROOTDIR, 'apps')
BINDIR = os.path.join (ROOTDIR, 'bin')
LIBPROG = os.path.join (LIBDIR, PROG)
PYTHON = os.path.join (BINDIR, 'pnpython3')
CONFIGDIR = os.path.join (ROOTDIR, 'config')

PROGS = ('125a2ph5',
         '1302ph5',
	 'batch2dep',
         'churn-array-deploy-times',
	 'das_start_stop',
	 'das_start_stop_kef_gen',
         'dumpreports',
         'dep2ph5',
	 'depcheck',
         'geod2kef',
         'initialize-ph5',
         'kef2ph5',
         'kmz-builder',
         'ph5toseg',
         'report2ph5',
         'query-ph5',
         'report2ph5',
	 'meta-data-gen',
         'sort-kef-gen',
         'tabletokef',
         'time-kef-gen',
         'tsp2dep',
         'txn2segy2dep',
	 'map-gen',
         'fix_num_samples',
	 'fix_das_chan_num',
	 'set_deploy_pickup_times',
         'create_empty_sort_array',
	 'noven',
	 'recvorder',
         'dumpsgy',
         'fix_3chan_texan',
         'obsipshot2dep',
         'sort-recv-dep',
         'index_offset_t',
	 'recreate_external_references',
         'PH5Server',
         'ftpserver',
         'servers',
         'cleanup',
         'migrate_2to3',
         'nuke-table',
         'segy2ph5',
         'dumpsac',
         'ph5tosac')

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
	 'SimpleMap',
         'cs2cs',
         'PH5DB',
         'PH5Helper',
	 'SegyReader',
         'SACReader',
         'SACFactory',
         'SAC_h')

EXTS = ('surt_130_py.py', 'sufirfilt_py.py', 'surt_125a_py.py', 'suibm2ieee_py.py',)

#   Delete libs
for p in LIBS :
    p = p + '.pyc'
    try :
        os.remove (p)
    except OSError :
        pass
    
#   Compile
compile_dir (".")
'''
#   Make libs dir
command = 'mkdir -p ' + LIBDIR
os.system (command)

#   Make config directory
command = 'mkdir -p ' + CONFIGDIR
os.system (command)
'''
#   Remove old libs
try :
    shutil.rmtree (LIBPROG)
except OSError :
    pass


'''
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
'''
#   compile extensions
for e in EXTS :
    print "Compiling extension " + e
    command = PYTHON + " " + e + " clean --build-lib=."
    os.system (command)
    command = PYTHON + " " + e + " build --build-lib=."
    os.system (command)
'''
#   install libraries
shutil.copytree (PROGDIR, LIBPROG)
fh = open (os.path.join (ROOTDIR, "install_date.txt"), 'w')
fh.write (time.ctime (time.time ())); fh.close ()

#   install configs
if not os.path.exists (os.path.join (CONFIGDIR, 'PH5Server.cfg')) :
    shutil.copy ('./config.cfg', os.path.join (CONFIGDIR, 'PH5Server.cfg'))

if not os.path.exists (os.path.join (CONFIGDIR, 'ftpserver.cfg')) :
    shutil.copy ('./config.cfg', os.path.join (CONFIGDIR, 'ftpserver.cfg'))

if not os.path.exists (os.path.join (CONFIGDIR, 'pass.dat')) :
    shutil.copy ('./pass.dat', os.path.join (CONFIGDIR, 'pass.dat'))
    
if not os.path.exists (os.path.join (CONFIGDIR, 'PH5.db')) :
    shutil.copy ('./PH5.db', os.path.join (CONFIGDIR, 'PH5.db'))

#   install ph5 GUIs
print "Installing PH5GUI..."
command = "cd PH5GUI; pnpython3 install.py"
os.system (command)
'''