#!/usr/bin/env pnpython3

# this script builds a kmz file for GoogleEarth users.  While it could surely have been written
# with fewer lines and more efficiently, nevertheless, it gets the job done.
# the script appends all the kml code together and then converts the list to a string and
# writes directly to a zip file.  It also depends on custom icons written found in a specific
# directory (refe to the iconpath variable).

import sys, os, os.path, time, re, zipfile, shutil, string

#   This provides the base functionality

import Experiment

PROG_VERSION = '2013.037.a'

lonRE = re.compile ('location/X/value_d')
latRE = re.compile ('location/Y/value_d')
elevRE = re.compile ('location/Z/value_d')
sizeRE = re.compile ('size/value_d')
sizeunitsRE = re.compile ('size/units_s')
shottimeRE = re.compile ('time/ascii_s')
idRE = re.compile ('id_s')
dataloggerRE = re.compile ('das/model_s')
dataloggersnRE = re.compile ('das/serial_number_s')
sensorRE = re.compile ('sensor/model_s')
compRE = re.compile ('channel_number_i')
nicknameRE = re.compile ('nickname_s')



kitchenpath = os.getenv('K3')
#print "kitchen path = "+kitchenpath

#
#   These are to hold different parts of the meta-data
#
#   /Experiment_g/Experiment_t
EXPERIMENT_T = None
#   /Experiment_g/Sorts_g/Event_t
EVENT_T = None
#   /Experiment_g/Sorts_g/Offset_t
#OFFSET_T = None
#   /Experiment_g/Sorts_g/Sort_t
SORT_T = None
#   /Experiment_g/Responses_g/Response_t
#RESPONSE_T = None
#   /Experiment_g/Sorts_g/Array_t_[nnn]
ARRAY_T = {}
#   /Experiment_g/Receivers_g/Das_g_[sn]/Das_t (keyed on DAS)
DAS_T = {}
#   /Experiment_g/Receivers_g/Das_g_[sn]/Receiver_t (keyed on DAS)
RECEIVER_T = {}
#   /Experiment_g/Receivers_g/Das_g_[sn]/SOH_a_[n] (keyed on DAS then by SOH_a_[n] name) 
SOH_A = {}
#   A list of das_groups that refers to Das_g_[sn]'s
DASS = []
#
# george's testing for array_t
ARRAY_DEP = {}

# the master list for building the kml file

kmlfile = []

def kml_top ():
  #defining the shot, station, and array icons
  kmlfile.append("""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
  <kml xmlns=\"http://www.opengis.net/kml/2.2\">
  <Document>

  <Style id=\"shoticon\">
  <IconStyle id=\"mystyle\">
  <scale>0.7</scale>
  <Icon>
  <href>shot.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>
  
  #station symbols - color coded (for differentiating between arrays - up to 20)
  <Style id=\"stationicon1\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station1.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>


  <Style id=\"stationicon2\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station2.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon3\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station3.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon4\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station4.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon5\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station5.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon6\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station6.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon7\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station7.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon8\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station8.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon9\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station9.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon10\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station10.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon11\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station11.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>


  <Style id=\"stationicon12\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station12.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon13\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station13.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon14\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station14.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon15\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station15.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon16\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station16.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon17\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station17.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon18\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station18.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon19\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station19.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"stationicon20\">
  <IconStyle id=\"mystyle\">
  <scale>0.4</scale>
  <Icon>
  <href>station20.png</href>
  </Icon>
  </IconStyle>
  <LabelStyle>
  <scale>0</scale>
  </LabelStyle>
  </Style>

  <Style id=\"liststyleshot\">
  <ListStyle>
  <ItemIcon>
  <href>shot.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle1\">
  <ListStyle>
  <ItemIcon>
  <href>station1.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle2\">
  <ListStyle>
  <ItemIcon>
  <href>station2.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle3\">
  <ListStyle>
  <ItemIcon>
  <href>station3.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle4\">
  <ListStyle>
  <ItemIcon>
  <href>station4.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle5\">
  <ListStyle>
  <ItemIcon>
  <href>station5.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle6\">
  <ListStyle>
  <ItemIcon>
  <href>station6.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle7\">
  <ListStyle>
  <ItemIcon>
  <href>station7.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle8\">
  <ListStyle>
  <ItemIcon>
  <href>station8.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle9\">
  <ListStyle>
  <ItemIcon>
  <href>station9.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle10\">
  <ListStyle>
  <ItemIcon>
  <href>station10.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle11\">
  <ListStyle>
  <ItemIcon>
  <href>station11.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle12\">
  <ListStyle>
  <ItemIcon>
  <href>station12.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle13\">
  <ListStyle>
  <ItemIcon>
  <href>station13.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle14\">
  <ListStyle>
  <ItemIcon>
  <href>station14.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle15\">
  <ListStyle>
  <ItemIcon>
  <href>station15.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle16\">
  <ListStyle>
  <ItemIcon>
  <href>station16.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle17\">
  <ListStyle>
  <ItemIcon>
  <href>station17.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle18\">
  <ListStyle>
  <ItemIcon>
  <href>station18.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle19\">
  <ListStyle>
  <ItemIcon>
  <href>station19.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>

  <Style id=\"liststyle20\">
  <ListStyle>
  <ItemIcon>
  <href>station20.png</href>
  </ItemIcon>
  </ListStyle>
  </Style>
  """)

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
#   To hold DAS sn and references to Das_g_[sn]
#
class das_groups (object) :
    __slots__ = ('das', 'node')
    def __init__ (self, das = None, node = None) :
        self.das = das
        self.node = node


#
#   Read Command line arguments
#
def get_args () :
    global PH5, DEPFILE, PATH, DEBUG
    
    from optparse import OptionParser
    
    oparser = OptionParser ()
    
    oparser.usage = "kmz-builder --nickname ph5-file-prefix || [--path path-to-ph5-files]"
    
    oparser.description = "Version: {0:s}. Generates a GoogleEarth kmz file of receivers and sources.".format (PROG_VERSION)
    
    oparser.add_option ("-n", "--nickname", dest = "ph5_file_prefix",
                        help = "The ph5 file prefix .",
                        metavar = "ph5_file_prefix")
    
    #oparser.add_option ("-d", dest = "dep_file",
                        #help = "the dep file to plot",
                        #metavar = "dep_file")
    
    oparser.add_option ("-p", "--path", dest = "ph5_path",
                        help = "Path to ph5 files. Defaults to current directory.",
                        metavar = "ph5_path")
    
    oparser.add_option ("-b", dest = "debug", action = "store_true", default = False)
    
    options, args = oparser.parse_args ()
    
    if options.ph5_file_prefix != None :
        PH5 = options.ph5_file_prefix
    else :
        PH5 = None
        
    if options.ph5_path != None :
        PATH = options.ph5_path
    else :
        PATH = "."

    #if options.dep_file != None :
        #DEPFILE = options.dep_file
        ##print DEPFILE
    #else :
    DEPFILE = None
        
    if options.debug != None :
        DEBUG = options.debug
        
    if PH5 == None and DEPFILE == None:
        sys.stderr.write ("Error: Missing required option. Try --help\n")
        sys.exit (-1)
        
    if PH5 != None and DEPFILE != None:
        sys.stderr.write ("Specify either a PH5 file OR a dep file, not both. Try --help\n")
        sys.exit (-1)
        
    #ph5_path = os.path.join (PATH, PH5) + '.ph5'
    #if not os.path.exists (ph5_path) :
        #sys.stderr.write ("Error: %s does not exist.\n" % ph5_path)
        #sys.exit (-2)


#initialize ph5 file
#
def initialize_ph5 (editmode = False) :
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5
    
    EX = Experiment.ExperimentGroup (PATH, PH5)
    EX.ph5open (editmode)
    EX.initgroup ()

#
#   Print rows_keys
#
def debug_print (a) :
    i = 1
    #   Loop through table rows
    for r in a.rows :
        #   Print line number
        print "%d) " % i,
        i += 1
        #   Loop through each row column and print
        for k in a.keys :
            print k, "=>", r[k], ",",
            
#        print
        
def read_experiment_table () :
    '''   Read /Experiment_g/Experiment_t   '''
    global EX, EXPERIMENT_T
    
    exp, exp_keys = EX.read_experiment ()
    
    rowskeys = rows_keys (exp, exp_keys)
    
    EXPERIMENT_T = rowskeys
    
def read_event_table () :
    '''   Read /Experiment_g/Sorts_g/Event_t   '''
    global EX, EVENT_T
    events, event_keys = EX.ph5_g_sorts.read_events ()
    
    rowskeys = rows_keys (events, event_keys)
    
    EVENT_T = rowskeys
    
def read_offset_table () :
    '''   Read /Experinent_t/Sorts_g/Offset_t   '''
    global EX, OFFSET_T
    
    offsets, offset_keys = EX.ph5_g_sorts.read_offsets ()
    
    rowskeys = rows_keys (offsets, offset_keys)
    
    OFFSET_T = rowskeys

def read_sort_table () :
    '''   Read /Experiment_t/Sorts_g/Sort_g   '''
    global EX, SORT_T
    
    sorts, sorts_keys = EX.ph5_g_sorts.read_sorts ()
    
    rowskeys = rows_keys (sorts, sorts_keys)
    
    SORT_T = rowskeys
    
def read_sort_arrays () :
    '''   Read /Experiment_t/Sorts_g/Array_t_[n]   '''
    global EX, ARRAY_T
    
    #   We get a list of Array_t_[n] names here...
    #   (these are also in Sort_t)
    names = EX.ph5_g_sorts.names ()
    for n in names :
        arrays, array_keys = EX.ph5_g_sorts.read_arrays (n)
        
        rowskeys = rows_keys (arrays, array_keys)
        #   We key this on the name since there can be multiple arrays
        ARRAY_T[n] = rowskeys
    
def read_receivers () :
    '''   Read tables and arrays (except wiggles) in Das_g_[sn]   '''
    global EX, DAS_T, RECEIVER_T, DASS, SOH_A
    
    #   Get references for all das groups keyed on das
    dasGroups = EX.ph5_g_receivers.alldas_g ()
    dass = dasGroups.keys ()
    #   Sort by das sn
    dass.sort ()
    for d in dass :
        #   Get node reference
        g = dasGroups[d]
        dg = das_groups (d, g)
        #   Save a master list for later
        DASS.append (dg)
        
        #   Set the current das group
        EX.ph5_g_receivers.setcurrent (g)
        
        #   Read /Experiment_g/Receivers_g/Das_g_[sn]/Das_t
        das, das_keys = EX.ph5_g_receivers.read_das ()
        rowskeys = rows_keys (das, das_keys)
        DAS_T[d] = rowskeys
        
        #   Read /Experiment_g/Receivers_g/Receiver_t
        receiver, receiver_keys = EX.ph5_g_receivers.read_receiver ()
        rowskeys = rows_keys (receiver, receiver_keys)
        RECEIVER_T[d] = rowskeys
        
        #   Read SOH file(s) for this das
        SOH_A[d] = EX.ph5_g_receivers.read_soh ()
        #   Get all of the SOH_a_[n] names
        #soh_names = SOH_A[d].keys ()
        
        #LOG_A[d] = EX.ph5_g_receivers.read_log ()
        
        #EVENT_T[d] = EX.ph5_g_receivers.read_event ()
                
  #my new stuff. why do I need to use a definition (def?) for this? - a def is like a subroutine...

def kmlbody ():
  global EX, DAS_T, DASS, DEPFILE, PH5
  arrays = []

  #now building the kml for the stations
  i = 0
  i_old = -1
  arrayname = "x"
  oldarrayname = "y"
  recvlines = 0
# reading from a dep file
  if DEPFILE != None:
    lines_of_depfile_w_color_array = []
    dep_object = open (DEPFILE,'r')
    all_dep_text = dep_object.read()
    dep_object.close()
    lines_of_depfile = all_dep_text.splitlines()

    # assigning a new variable as the first string in line for sorting shots and receiver 
    # lines into separate arrays for plotting.  SHOTs are "0", RECVs are
    # 1 - 20, arrays are based on numbers.  Adding leading zeroes for sorting

    linecount = 0
    array_count = 1
    for line in lines_of_depfile:
      if line.split(';')[0] == "SHOT":
        lines_of_depfile[linecount] = "0;"+line
      elif line.split(';')[0] == "RECV" and line.split(';')[3] != "" and line.split(';')[3] != "999":
        if len(line.split(';')[3]) == 1:
          lines_of_depfile[linecount] = "0"+line.split(';')[3]+";"+line
        elif len(line.split(';')[3]) == 2:
          lines_of_depfile[linecount] = line.split(';')[3]+";"+line
      elif line.split(';')[0] == "RECV" and ((line.split(';')[3]) == "" or line.split(';')[3] == "999"):
        if len(line.split(';')[2]) == 4:
          lines_of_depfile[linecount] = "00"+line.split(';')[2][:-3]+";"+line
        if len(line.split(';')[2]) == 5:
          lines_of_depfile[linecount] = "00"+line.split(';')[2][:-4]+";"+line
        elif len(line.split(';')[2]) == 6:
          lines_of_depfile[linecount] = "0"+line.split(';')[2][:-5]+";"+line
        elif len(line.split(';')[2]) == 7:
          lines_of_depfile[linecount] = line.split(';')[2][:-5]+";"+line
      linecount += 1

    lines_of_depfile.sort()

    # removing leading zeros so it looks "nice"
    linecount = 0
    for line in lines_of_depfile:
      try :
        lines_of_depfile[linecount] = [str(int(line.split(';')[0]))]+line.split(';')[1:]
        linecount += 1
      except :
        sys.stderr.write ("Error in dep file at line {0}:\n{1}\n".format (linecount, line))
        
          
    z = 0
    first_recv_array = 1
    for rows in lines_of_depfile:
      #print "rows = ",rows
      type = rows[1]
      if type == "RECV":
        X = rows[0] in arrays
        recvlines = 1
        if not X:
          arrays.append (rows[0])
          
        ARRAY_DEP = {'long': rows[10], 'lat': rows[9], 'elev': rows[11], 'id_s': rows[3], "array": rows[0], 'das_model': rows[5], 'das_sn': rows[2], 'sensor': rows[7], 'comp': rows[6] }
        #ARRAY_DEP = {'long': rows[9], 'lat': rows[8], 'elev': rows[10], 'id_s': rows[2], "array": rows[2][:-4], 'das_model': rows[4], 'das_sn': rows[1], 'sensor': rows[6], 'comp': rows[5] }

        x = ARRAY_DEP['lat']
        x = x.replace("N","")
        x = x.replace("S","-")
        ARRAY_DEP['lat'] = x  

        y = ARRAY_DEP['long']
        y = y.replace("E","")
        y = y.replace("W","-")
        ARRAY_DEP['long'] = y  
        z += 1

        if ARRAY_DEP['comp'] == "1" or ARRAY_DEP['comp'] == "":
          comp = ARRAY_DEP['comp']
          lat = ARRAY_DEP['lat']
          lon = ARRAY_DEP['long']
          elev = ARRAY_DEP['elev']
          id = ARRAY_DEP['id_s']
          arrayname = ARRAY_DEP['array']
          datalogger = ARRAY_DEP['das_model']
          dataloggersn = ARRAY_DEP['das_sn']
          sensor = ARRAY_DEP['sensor']

          #kmlfile.append("</Folder>\n")

          # first receiver array?
          if first_recv_array == 1:
            kmlfile.append("""
            <Folder><name>Array """+arrayname+"""</name>
            # <styleUrl>#liststyle"""+arrayname+"""</styleUrl>
            <styleUrl>#liststyle"""+str(array_count)+"""</styleUrl>
            """)
            first_recv_array = 0
            oldarrayname = arrayname
           
          # a new receiver array?
          elif arrayname != oldarrayname and first_recv_array == 0:
            array_count += 1
            kmlfile.append("""
            #Hello\n </Folder>
            <Folder><name>Array """+arrayname+"""</name>
            <styleUrl>#liststyle"""+str(array_count)+"""</styleUrl>
            """)
            oldarrayname = arrayname


          kmlfile.append("""<Placemark>
          <name>Station """+id+""", Array """+arrayname+"""</name>
          <description> das model: """+datalogger+""" \n das serial number:"""+dataloggersn+""" \n sensor model: """+sensor+""" </description>
          <styleUrl>#stationicon"""+str(array_count)+"""</styleUrl>
          <Point>
          <coordinates>"""+lon+""","""+lat+""","""+elev+"""</coordinates>
          </Point>
          </Placemark>
          """)

    # do receiver lines/folders exist

    if recvlines == 1:
      #closing the last array folder
      kmlfile.append("</Folder>\n")
      #print "at rec dep section"

    array_count = len(arrays)  
    #print "array count", array_count
         
# reading from a PH5 file
  else:
    for a in ARRAY_T.keys ():
      arrayname = str (int (a[-3:]))
      rs = ARRAY_T[a]
      for r in rs.rows:
        #print r
        for k in rs.keys:
          #print r[k]
          if lonRE.match (k):
            lon = str(r[k])
          elif latRE.match (k):
            lat = str(r[k])
          elif elevRE.match (k):
            elev = str(r[k])
          elif idRE.match (k):
            id = str(r[k])
            #arrayname = id[:1]
            #arrayname = id[:1]
          elif dataloggerRE.match (k):
            datalogger = str(r[k])
            #print datalogger
            try :
              if datalogger[-1] == "k":
                datalogger = "RT-130"
                #print "datalogger changed to ",datalogger
              elif datalogger[-1] == "n":
                datalogger = "Texan"
              else :
                datalogger = "Unknown"
            except IndexError :
              datalogger = "Unknown"

           # my fix when the datalogger is not defined (didn't no about the "try" statement)
           # if datalogger != "":
           #   if datalogger[-1] == "k":
           #     datalogger = "RT-130"
           #   #print "datalogger changed to ",datalogger
           #   elif datalogger[-1] == "n":
           #     datalogger = "Texan"
              #print "datalogger changed to ",datalogger

          elif dataloggersnRE.match (k):
            dataloggersn = str(r[k])
          elif sensorRE.match (k):
            sensor = str(r[k]) 
        
          if compRE.match (k) :
            # looking for a vertical component
            if r[k] < 2 :
              comp = r[k] 
              #print "Comp: ", comp
              # building the first folder
              if i_old == -1:
              #if i == 0 and i != i_old:
                kmlfile.append("""<Folder><name>Array """+arrayname+"""</name>
                <styleUrl>#liststyle"""+arrayname+"""</styleUrl>
                """)
              #  closing the first folder and building subsequent folders
              elif i != 0 and i != i_old:
                kmlfile.append("""
                </Folder>
                <Folder><name>Array """+arrayname+"""</name>
                <styleUrl>#liststyle"""+arrayname+"""</styleUrl>
                """)
                
              kmlfile.append("""<Placemark>
              <name>Station """+id+""", Array """+arrayname+"""</name>
              <description> das model: """+datalogger+""" \n das serial number:"""+dataloggersn+""" \n sensor model: """+sensor+""" </description>
              <styleUrl>#stationicon"""+arrayname+"""</styleUrl>
              <Point>
              <coordinates>"""+lon+""","""+lat+""","""+elev+"""</coordinates>
              </Point>
              </Placemark>
              """)
              i_old = i
            # if the comp is undefined or 0 the receiver is not plotted.
            elif r[k] < 1 :
              sys.stderr.write ("Warning: component set to {0}\n".format (r[k]))
             
          # the comp must equal 1, otherwise (undefined, 2, 3, etc) the folder and station 
          # are not added to the kmz file! - above code more robust
          if compRE.match (k) and str(r[k]) == "1":
            comp = r[k] 

            # building the first folder
            if i_old == -1:
            #if i == 0 and i != i_old:
              kmlfile.append("""<Folder><name>Array """+arrayname+"""</name>
              <styleUrl>#liststyle"""+arrayname+"""</styleUrl>
              """)
            #  closing the first folder and building subsequent folders
            elif i != 0 and i != i_old:
              kmlfile.append("""
              </Folder>
              <Folder><name>Array """+arrayname+"""</name>
              <styleUrl>#liststyle"""+arrayname+"""</styleUrl>
              """)
            kmlfile.append("""<Placemark>
            <name>Station """+id+""", Array """+arrayname+"""</name>
            <description> das model: """+datalogger+""" \n das serial number:"""+dataloggersn+""" \n sensor model: """+sensor+""" </description>
            <styleUrl>#stationicon"""+arrayname+"""</styleUrl>
            <Point>
            <coordinates>"""+lon+""","""+lat+""","""+elev+"""</coordinates>
            </Point>
            </Placemark>
            """)
            i_old = i
      i = i + 1 
    #closing the last array folder
    kmlfile.append("</Folder>\n")
    #print "at the ph5 - rec section"
  # building the kml for the shots
  
  # reading from the depfile
  if DEPFILE != None:
    shotlines = 0
    for rows in lines_of_depfile:
    #for line in lines_of_depfile:
      #rows = line.split(';') 
      type = rows[1]
      if type == "SHOT":
        # is this the first shot line? If so, builder a shot folder.
        if shotlines == 0:
          kmlfile.append("""<Folder><name>Shots</name>
          <styleUrl>#liststyleshot</styleUrl>
          """)
        X = rows[2][:1] in arrays
        shotlines = 1
        if not X:
          arrays.append (rows[2][:1])
        ARRAY_DEP = {'long': rows[6], 'lat': rows[5], 'elev': rows[7], 'id_s': rows[2], "array": rows[0], 'shottime': rows[8], 'depth': rows[12], 'size': rows[13], 'comments': rows[16]}
        #if "N" in ARRAY_DEP['lat']:
        x = ARRAY_DEP['lat']
        #print "x = ",x
        x = x.replace("N","")
        x = x.replace("S","-")
        ARRAY_DEP['lat'] = x  
        y = ARRAY_DEP['long']
        #print "y = ",y
        y = y.replace("E","")
        y = y.replace("W","-")
        ARRAY_DEP['long'] = y  
        #print ARRAY_DEP
        z += 1
        lat = ARRAY_DEP['lat']
        lon = ARRAY_DEP['long']
        elev = ARRAY_DEP['elev']
        id = ARRAY_DEP['id_s']
        shottime = ARRAY_DEP['shottime']
        size = ARRAY_DEP['size']
        comments = ARRAY_DEP['comments']

        kmlfile.append("""<Placemark>
        <name>Shot """+id+"""</name>
        <description> shot time: """+shottime+""" \n shot size: """+size+""" \n comments: """+comments+"""</description>
        <styleUrl>#shoticon</styleUrl>
        <Point>
        <coordinates>"""+lon+""","""+lat+""","""+elev+"""</coordinates>
        </Point>
        </Placemark>
         """)
    #do shot lines exist?  If so close the shot folder
    if shotlines == 1:
      kmlfile.append("</Folder>\n")
      #print "at the dep - shot section" 

  # from the PH5 file
  else:
    kmlfile.append("""<Folder><name>Shots</name>
    <styleUrl>#liststyleshot</styleUrl>
    """)
    for r in EVENT_T.rows :
      for k in EVENT_T.keys : 
        if lonRE.match (k):
          lon = str(r[k])
        elif latRE.match (k):
          lat = str(r[k])
        elif elevRE.match (k):
          elev = str(r[k])
        elif sizeRE.match (k):
          size = str(r[k])
        elif sizeunitsRE.match (k):
          sizeunits = str(r[k])
        elif shottimeRE.match (k):
          shottime = str(r[k])
        elif idRE.match (k):
          id = str(r[k])
  
      kmlfile.append("""<Placemark>
      <name>Shot """+id+"""</name>
      <description> shot time: """+shottime+""" \n shot size: """+size+""" """+sizeunits+""" </description>
      <styleUrl>#shoticon</styleUrl>
      <Point>
      <coordinates>"""+lon+""","""+lat+""","""+elev+"""</coordinates>
      </Point>
      </Placemark>
      """)
    kmlfile.append("</Folder>\n")
    #print "at the ph5 shot shot section"
#

if __name__ == "__main__" :
    #   Get program arguments
    get_args ()
    if PH5 != None:
      #   Initialize ph5 file
      initialize_ph5 ()
    
      #   Read experiment table
      read_experiment_table ()
      if False :
          debug_print (EXPERIMENT_T)
    
      #   Read event table (shots)
      read_event_table ()
      if False :
          debug_print (EVENT_T)
    
      ##   Read offsets
      #read_offset_table ()
      #if DEBUG :
          #debug_print (OFFSET_T)
    
      #   Read sort table (Start time, Stop time, and Array)
      read_sort_table ()
      if False :
          debug_print (SORT_T)
        
      ##   Read response information
      #read_response_table ()
      #if DEBUG :
          #debug_print (RESPONSE_T)
        
      #   Read sort arrays
      read_sort_arrays ()
      if False :
          for a in ARRAY_T.keys () :
              debug_print (ARRAY_T[a])
    
      ##   Read tables in Das_g_[sn]
      #read_receivers ()
      #if DEBUG :
          ##   *** Print SOH_A, DAS_T, RECEIVER_T here ***
          #pass
    
      #sd, pts = read_data ()
      #if True :
          #epochs = sd.keys ()
          #epochs.sort ()
        
          #for e in epochs :
              #print e, numpy.mean (sd[e])            
    
      #Total samples in ph5: %d\n" % pts,
    
      #   Close ph5 file

    
    kml_top ()
    kmlbody ()

    kmlfile.append("""</Document> 
    </kml>\n """)

    # getting experiment nickname to name the kmz file
    if PH5 == None:
      nickname = "PH5"
      print "kmz filename = PH5.kmz"
    else:
      # just in case the experiment nickname is not defined and the exp table is...
      nickname = PH5
      #nickname = PH5[:-4]

      # if the experiment table and nickname field are populated use the exp kef file
      # nickname as the kmz file name
      for r in EXPERIMENT_T.rows :
        for k in EXPERIMENT_T.keys :
          if nicknameRE.match (k):
            alphanum = re.compile (r'\w')
            if alphanum.search(r[k]) and str(r[k]) !=  "":
              nickname = str(r[k])
              print "nickname = "+nickname
              #print "kmz filename = "+nickname+".kmz"
      
      print "kmz filename = "+nickname+".kmz"

    output = open('doc.kml','w')
    biglist = "".join(kmlfile)

    output.writelines(biglist)
    output.close()

    # copy the icon files from $KITCHEN/apps/pn2/kmlicons/
    # may not be elegant but it allows us to use our own icons and not rely on downloading icons
    # from Google

    iconpath = kitchenpath+"/apps/pn3/kmlicons/"

    shutil.copyfile(iconpath+"shot.png", "shot.png")
    i = 1
    while i <= 20:
      shutil.copyfile(iconpath+"station"+str(i)+".png", "station"+str(i)+".png")
      i = i + 1
  
    # preparing the kmz (zip) file

    zipobject = zipfile.ZipFile(nickname+'.kmz','w')
    zipobject.writestr('doc.kml', biglist)
    zipobject.close()

    zipobject = zipfile.ZipFile(nickname+'.kmz','a')
    zipobject.write('shot.png')

    i = 1
    while i <= 20:
      zipobject.write("station"+str(i)+".png")
      i = i + 1
    zipobject.close()

    # removing the unneeded icon files and doc.kml file
  
    os.remove("doc.kml")
    os.remove("shot.png")
    i = 1
    while i <= 20:
      os.remove("station"+str(i)+".png")
      i = i + 1
    
