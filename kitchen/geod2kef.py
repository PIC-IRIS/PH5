#!/usr/bin/env pnpython3

import sys, os, string, math, time
import Experiment
from pyproj import Geod
import numpy as npy

PROG_VERSION = '2016.216 Developmental'

GEOD = 'geod'
ELLIPSOID = 'WGS84'
UNITS = 'm'

FACTS = { 'km':1000., 'm':1., 'dm':1./10., 'cm':1./100., 'mm':1./1000., 'kmi':1852.0, 'in':0.0254, 'ft':0.3048, 'yd':0.9144,
          'mi':1609.344, 'fath':1.8288, 'ch':20.1168, 'link':0.201168, 'us-in':1./39.37, 'us-ft':0.304800609601219, 'us-yd':0.914401828803658,
          'us-ch':20.11684023368047, 'us-mi':1609.347218694437, 'ind-yd':0.91439523, 'ind-ft':0.30479841, 'ind-ch':20.11669506 }
#
ARRAY_T = {}
#
EVENT_T = {}

class rows_keys :
    def __init__ (self, rows = None, keys = None) :
        self.rows = rows                             #   Table rows as returned by iterrows
        self.keys = keys                             #   Keys for each row
        
class location :
    def __init__ (self, name = None, X = None, Y = None, units = None) :
        self.name = name                             #   Stake ID
        self.lon = X                                 #   Easting
        self.lat = Y                                 #   Northing
        self.units = units                           #   Units (degrees)

def getargs () :
    global PH5, PATH, UNITS, ELLIPSOID, SHOTS
    
    from optparse import OptionParser

    oparser = OptionParser ()
    oparser.usage = "Version: %s\ngeod2kef --nickname output_file_prefix [--path][-h][--listellipsoids][--listunits][-U units][-E ellipsoid]" % PROG_VERSION
    
    oparser.description = "Read locations and calculate offsets from events to receivers. Produce kef file to populate ph5 file."
    
    oparser.add_option ("-n", "--nickname", dest = "outfile",
                        help="The ph5 file prefix (experiment nick name).",
                        metavar = "output_file_prefix")
    
    oparser.add_option ("-p", "--path", dest = "ph5path",
                        help = "Path to directory containing ph5 files. Defaults to current directory",
                        metavar = "output_file_path")
    
    oparser.add_option ("-l", "--eventlistfile", dest = "eventlistfile",
                        help="A file containing a list of shots to calculate offsets from, one per line.",
                        default = None, metavar = "event_list_file")
    
    oparser.add_option ("-U", dest = "outunits",
                        help = "Units to output offsets in. (Use -u to get list of acceptable units.) Default == 'm' (meters)",
                        metavar = "output_units")
    
    oparser.add_option ("-E", dest = "ellipsoid",
                        help = "Ellipsoid to use. (Use -e to get a list of acceptable ellipsoids.) Default == 'WGS84'",
                        metavar = "calculation_ellipsoid")
    
    oparser.add_option ("-e", "--listellipsoids", dest = 'ellip',
                        help = "List available ellipsoids.",
                        action = "store_true", default = False)
    
    oparser.add_option ("-u", "--listunits", dest = 'units',
                        help = "List all available output units.",
                        action = "store_true", default = False)
  
    #oparser.add_option ("-p", dest = "ph5path", help = "Path to where ph5 files are stored. Defaults to current directory")
    
    options, args = oparser.parse_args()
    #print options.outfile

    PH5 = None
    PATH = '.'
    UNITS = 'm'
    
    if options.units == True :
        command = GEOD + " -lu"
        os.system (command)
        sys.exit ()
        
    if options.ellip == True :
        command = GEOD + " -le"
        os.system (command)
        sys.exit ()
        
    if options.outunits != None :
        UNITS = options.outunits
        
    if options.ellipsoid != None :
        ELLIPSOID = options.ellipsoid
    
    if options.outfile != None :
        PH5 = options.outfile
    
    if options.eventlistfile != None :
        try :
            fh = open (options.eventlistfile)
            SHOTS = fh.readlines ()
            fh.close ()
            SHOTS = map(lambda s: s.strip(), SHOTS)
        except :
            sys.stderr.write ("Failed to read event list file.")
            sys.exit (-1)
    else :
        SHOTS = None

    if options.ph5path != None :
        PATH = options.ph5path
        
    if PH5 == None :
        #print H5, FILES
        sys.stderr.write ("Error: Missing required option. Try --help\n")
        sys.exit (-1)
    
    #tmp = os.path.join (PATH, PH5) + '.ph5'
    #if not os.path.exists (tmp) :
        #sys.stderr.write ("Error: %s does not exist!\n" % tmp)
        #sys.exit (-2)

def have_geod () :
    try :
        fh = os.popen (GEOD + " 2>&1")
        while 1 :
            line = fh.readline ()
            if not line: break
            flds = line.split ()
            if flds[0] == 'Rel.' :
                sys.stderr.write ("#Using geod: %s" % line)            
    except Exception, e :
        sys.stderr.write ("Error: Can not execute %s." % GEOD)
        sys.exit (-1)
        
def deg2dms (dgs) :
    f, d = math.modf (dgs)
    f = abs (f)
    m = 60.0 * f
    f, m = math.modf (m)
    #print math.frexp (f), math.frexp (m)
    s = 60.0 * f
    dms = "%dd%02d'%09.6f\"" % (d, m, s)
    #print dms
    return dms
        
def run_geod (lat0, lon0, lat1, lon1) :
    #global UNITS, ELLIPSOID
    #lat0 = deg2dms (lat0)
    #lon0 = deg2dms (lon0)
    #lat1 = deg2dms (lat1)
    #lon1 = deg2dms (lon1)
    
    flds = []
    
    config = "+ellps={0}".format (ELLIPSOID)
    
    g = Geod (config)
    
    az, baz, dist = g.inv (lon0, lat0, lon1, lat1)
    
    if dist :
        dist /= FACTS[UNITS]
    
    #command = "%s +ellps=%s -f \"%%.6f\" <<EOF -I +units=%s\n%s %s %s %s\nEOF" % (GEOD, ELLIPSOID, UNITS, lat0, lon0, lat1, lon1)
    #print command
    #try :
        #fh = os.popen (command)
        #while 1 :
            #line = fh.readline ()
            #if not line : break
            #flds = line.split ()
            ##print flds
    #except Exception, e :
        #sys.stderr.write ("Error: failed to execute:\n%s" % command)
        #flds = None
        
    #   Return list containing azimuth, back azimuth, distance
    return az, baz, dist

def read_events () :
    '''   Read /Experiment_g/Sorts_g/Shots_t   '''
    global EX, EVENT_T, SHOTS, EVENT
    
    EVENT = EX.ph5_g_sorts.namesEvent_t ()
    EVENT.sort ()
    for n in EVENT :
        events, ekeys = EX.ph5_g_sorts.read_events (n)
        EVENT_T[n] = []
        #
        for e in events :
            name = e['id_s']
            if SHOTS :
                if name in SHOTS :
                    x = e['location/X/value_d']
                    y = e['location/Y/value_d']
                    units = e['location/X/units_s']
                    l = location (name, x, y, units)
                    EVENT_T[n].append (l)
            else :
                x = e['location/X/value_d']
                y = e['location/Y/value_d']
                units = e['location/X/units_s']
                l = location (name, x, y, units)
                EVENT_T[n].append (l)            
    
def read_sorts () :
    '''   Get a list of Array_t names   '''
    global EX, ARRAY
    
    #   ARRAY is a list of Array_t_nnn names  
    ARRAY = EX.ph5_g_sorts.namesArray_t ()
    ARRAY.sort ()
        
def read_arrays () :
    '''   Read all /Experiment_g/Sorts_g/Array_t_nnn   '''
    global EX, ARRAY, ARRAY_T
    
    for r in ARRAY :
        ARRAY_T[r] = []
        #if not ARRAY_T.has_key (a) :
            #ARRAY_T[a] = []
            
        arrays, akeys = EX.ph5_g_sorts.read_arrays (r)
        #akeys.sort ()
        #rk = rows_keys (arrays, akeys)
        #   ARRAY_T a dictionary keyed on Array_t_nnn name that points to a list of rows_keys
        #ARRAY_T[a].append (rk)
        first_chan_seen = None
        for a in arrays :
            if first_chan_seen == None : first_chan_seen = a['channel_number_i']
            if a['channel_number_i'] != first_chan_seen : continue
            name = a['id_s']
            x = a['location/X/value_d']
            y = a['location/Y/value_d']
            units = a['location/X/units_s']
            l = location (name, x, y, units)
            ARRAY_T[r].append (l)
            
def run_cart (y0, x0, y1, x1) :
    d = math.sqrt (((y0 - y1) ** 2) + ((x0 - x1) ** 2))
    a = math.degrees (math.atan2 (y1, x1))
    b = math.degrees (math.atan2 (y0, x0))
    #   Do we need to take the quadrant in to account?
    if a < 0 :
        a = 360. + a
        
    if b < 0 :
        b = 360. + b
    
    return a, b, d
    
def loop_events_arrays () :
    global UNITS, WHACKED
    WHACKED = {}
    print "#   %s   geod2kef version: %s   ph5 version: %s" % (time.ctime (time.time ()), PROG_VERSION, EX.version ())
    #print '#   Generated: %s' % time.ctime (time.time ())
    i = 0
    for n in EVENT :
        en = n[8:]
        for e in EVENT_T[n] :
            id0 = e.name
            lat0 = e.lat
            lon0 = e.lon
            units0 = e.units
            WHACKED[int (id0)] = {}
            for r in ARRAY :
                an = r[8:]
                for a in ARRAY_T[r] :
                    id1 = a.name
                    lat1 = a.lat
                    lon1 = a.lon
                    units1 = a.units
                    if units1 == 'degrees' and units0 == 'degrees' :
                        az_baz_dist = run_geod (lat0, lon0, lat1, lon1)
        
                    elif units1 != 'degrees' and units1 == units0 :
                        az_baz_dist = run_cart (lat0, lon0, lat1, lon1)
                    else : continue
        
                    if not az_baz_dist : continue
                    print "#   {0}".format (i); i += 1
                    print '/Experiment_g/Sorts_g/Offset_t_{0}_{1}'.format (an, en)
                    print '\tevent_id_s = %s' % str (id0)
                    print '\treceiver_id_s = %s' % str (id1)
                    print '\tazimuth/value_f = %s' % az_baz_dist[0]
                    print '\tazimuth/units_s = %s' % "degrees"
                    print '\toffset/value_d = %s' % az_baz_dist[2]
                    print '\toffset/units_s = %s' % UNITS
                    WHACKED[int (id0)][int (id1)] = abs (float (az_baz_dist[2]))
            
def look_at_offsets () :
    global WHACKED
    events = WHACKED.keys ()
    events.sort ()
    for e in events :
        stations = WHACKED[e].keys ()
        stations.sort ()
        deltas = []
        last = None
        for s in stations :
            d = WHACKED[e][s]
            if last :
                deltas.append (abs (last - d))
                
            last = d
            
        ave = npy.average (deltas)
        std = npy.std (deltas) * 20.
        last = None
        for s in stations :
            d = WHACKED[e][s]
            if last :
                dt = abs (last - d)
                
                if dt > (ave + std) :
                    #print ave, std
                    sys.stderr.write ("###   Warning: The offset between shot {0} and station {1}, {2:g} meters, may be incorrect!   ###\n".format (e, s, d))
                    
            last = d
    
if __name__ == '__main__' :
    global PH5, PATH, EX
    have_geod ()
    getargs ()
    
    EX = Experiment.ExperimentGroup (PATH, PH5)
    editmode = False
    EX.ph5open (editmode)
    EX.initgroup ()
    #print "Read events..."
    read_events ()
    #print "Read sorts..."
    read_sorts ()
    #print "Read arrays..."
    read_arrays ()
    #print "Looping..."
    loop_events_arrays ()
    
    EX.ph5close ()
    look_at_offsets ()
