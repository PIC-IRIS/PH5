#!/usr/bin/env pnpython2

import sys
import TimeDoy

PROG_VERSION = "2011.287"

#class Shot (object) :
    #__slots__ = ('shotNumber', 'date', 'time', 'sourceLat', 'sourceLon', 'shipLat', 'shipLon', 'waterDepth', 'sciTag')
    #def __init__ (self) :
        #self.shotnumber = None
        #self.date = None
        #self.time = None
        #self.sourceLat = None
        #self.sourceLon = None
        #self.shipLat = None
        #self.shipLon = None
        #self.waterDepth = None
        #self.sciTag = None

def get_order (line) :
    '''   Reads order of fields in OBSIP shot file file   '''
    order = {}
    line = line[1:]
    flds = line.split ()
    i = 0
    for f in flds :
        order[f.strip ()] = i
        i += 1
        
    return order

def read_shot_file (file) :
    '''
       
    '''
    tdoy = TimeDoy.TimeDoy ()
    
    global PARAMETERS
    PARAMETERS = {}
    try :
        fh = open (file, 'U')
        #   Skip first line
        fh.readline ()
    except :
        return False
    
    order = None
    n = 0
    while 1 :
        line = fh.readline ()
        if not line : break
        line = line[:-1]
        n += 1
        if line[0] == '#' :
            order = get_order (line)
            
            continue
        
        flds = line.split ()
        
        if order == None :
            sys.stderr.write ("Error: Second line in OBSIP shot file does not describe columns!")
            return False
        
        if len (flds) != len (order.keys ()) :
            sys.stderr.write ('Error in OBSIP shot file: %d\n%s\n' % (n, line))
            return False
        
        #   shotNumber = flds[order['shotNumber']]   Required
        try :
            shotNumber = flds[order['shotNumber']]
        except KeyError, e :
            sys.stderr.write ("Error: Required field shotNumber missing at line number {0}.\n".format (n))
            sys.exit ()
        #
        #   yr, mo, da = flds[order['date']].split ('-')   Required
        #      jd = tdoy.doy (int (mo), int (da), int (yr))   Calculated
        try :
            yr, mo, da = flds[order['date']].split ('-')
            jd = tdoy.doy (int (mo), int (da), int (yr))
        except KeyError, e :
            sys.stderr.write ("Error: Required field date missing at line number {0}.\n".format (n))
            sys.exit ()
        #
        #   time = flds[order['time']]   Required
        try :
            time = flds[order['time']]
        except KeyError, e :
            sys.stderr.write ("Error: Required field time missing at line number {0}.\n".format (n))
            sys.exit ()
        #
        #   pictime = "{0:04d}:{1:03d}:{2:14s}".format (yr, jd, time)   Calculated
        pictime = "{0:4s}:{1:03d}:{2:14s}".format (yr, jd, time)
        #   
        #   sourceLat = flds[order['sourceLat']]   Required
        try :
            sourceLat = flds[order['sourceLat']]
        except KeyError, e :
            sys.stderr.write ("Error: Required field sourceLat missing at line number {0}.\n".format (n))
            sys.exit ()
        #
        #   sourceLon = flds[order['sourceLon']]   Required
        try :
            sourceLon = flds[order['sourceLon']]
        except KeyError, e :
            sys.stderr.write ("Error: Required field sourceLon missing at line number {0}.\n".format (n))
            sys.exit ()
        #
        #   shipLat = flds[order['shipLat']]   Optional
        try :
            shipLat = flds[order['shipLat']]
        except KeyError, e :
            shipLat = " "
        #
        #   shipLon = flds[order['shipLon']]   Optional
        try :
            shipLon = flds[order['shipLon']]
        except KeyError, e :
            shipLon = " "
        #
        #   waterDepth = flds[order['waterDepth']]   Optional
        try :
            waterDepth = flds[order['waterDepth']]
        except KeyError, e :
            waterDepth = " "
        #
        #   sciTag = flds[order['sciTag']]   Optional
        try :
            sciTag = flds[order['sciTag']]
        except KeyError, e :
            sciTag = " "
        #
        #   sourceDepth = flds[order['sourceDepth']]   Optional
        try :
            sourceDepth = flds[order['sourceDepth']]
        except KeyError, e :
            sourceDepth = " "
        #
        #   sourceID = flds[order['sourceID']]   Optional
        try :
            sourceID = flds[order['sourceID']]
        except KeyError, e :
            sourceID = " "
        #
        #   comment1 = "shipLat={0} shipLon={1} waterDepth={2}".format (shipLat, shipLon, waterDepth)
        comment1 = "shipLat={0} shipLon={1} waterDepth={2}".format (shipLat, shipLon, waterDepth)
        #
        #   comment2 = "sciTag={0} sourceDepth={1} sourceID={2}".format (sciTag, sourceDepth, sourceID)
        comment2 = "sciTag={0} sourceDepth={1} sourceID={2}".format (sciTag, sourceDepth, sourceID)
        #
        #   comment = comment2 + " " + comment1
        comment = comment2 + " " + comment1
        
        # SHOT line description:
        #   Inactive - Ignore this entry (SHOTX;)
        #   ID - Shot ID --- shotNumber
        #   Station - Station name --- sourceID
        #   Line - Line designation --- lineNumber
        ###   Channel - Receiver channel number   ###    Removed
        #   Lat - Latitude (NDD.ddd) --- sourceLat
        #   Lon - Longitude (EDDD.ddd) --- sourceLon
        #   Elev - Elevation (meters) --- waterDepth
        #   Time - Time of the shot --- pictime
        #   Pre - Pre-trigger length (sec) --- 0
        #   Post - Post-trigger length (sec) --- 0
        #   SR - Samplerate (sps) --- ""
        #   Depth - Shot depth (m) --- sourceDepth
        #   Size - Shot size (kg) --- ""
        #   RVel - Reduction velocity (km/s) --- ""
        #   Radius - Of receivers to include in gather (km) --- ""
        #   Comment - Comments
        # SHOT;...
        #SHOT; 1; S05; A; XXX1XXX; N34.073680; W106.921900; 4719; 2006:164:17:05:00.000; 0.000; 10.000; 1000; 0; 0.00; 0.000; 1000.000;
        print "SHOT;{0};{1};{2};{3};{4};{5};{6};{7};{8};{9};{10};{11};{12};{13};{14}".format (shotNumber,
                                                                                              sourceID,
                                                                                              shotNumber,
                                                                                              sourceLat,
                                                                                              sourceLon,
                                                                                              " ",
                                                                                              pictime,
                                                                                              0,
                                                                                              0,
                                                                                              " ",
                                                                                              waterDepth,
                                                                                              " ",
                                                                                              " ",
                                                                                              " ",
                                                                                              comment)

        
    return True

def usage () :
    sys.stderr.write ("Version: {1}\nUsage: {0} obsipfile > shotdepfile.dep\n".format (sys.argv[0], PROG_VERSION))
    sys.stderr.write ("\t\t\tOBSIP File Keys\n\tRequired Keys: shotNumber, date YYYY-MM-DD, time HH:MM:SS.ssss,\n\t sourceLat +/-DD.dddddd, sourceLon +/-DDD.dddddd\n")
    sys.stderr.write ("\tDesired Keys: shipLat +/-DD.dddddd, shipLon +/-DDD.dddddd,\n\t waterDepth (meters)\n")
    sys.stderr.write ("\tOther Keys: sciTag (16 chars, no spaces), sourceDepth (meters),\n\t sourceID (16 chars, no spaces)\n")
    
if __name__ == '__main__' :
    try :
        obsipfile = sys.argv[1]
        if obsipfile == '-h' : raise
    except :
        usage ()
        sys.exit ()
        
    read_shot_file (obsipfile)