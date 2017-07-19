#!/usr/bin/env pnpython3
#
#   PH5 meta-data initializer GUI
#
#   Steve Azevedo, refactor Feb 2015
#

import os, sys, json, time
from os.path import expanduser
from PyQt4 import QtGui, QtCore
from ph5.utilities import novenqc, novenkef

PROG_VERSION = '2017.199'


RECEIVER_CFG_S ='''
{
   "description_s": {
      "required": "False", 
      "type": "string1024", 
      "help": "Station comments."
   }, 
   "pickup_time/ascii_s": {
      "required": "True", 
      "type": "string32", 
      "help": "Time: YYYY:JJJ:HH:MM:SS.sss or YYYY-MM-DDTHH:MM:SS.ssssss.",
      "re": "(\\\\d\\\\d\\\\d\\\\d:\\\\d{1,3}:\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2}(\\\\.\\\\d{1,3})?)|(\\\\d\\\\d\\\\d\\\\d-\\\\d{1,2}-\\\\d{1,2}T\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2}\\\\.\\\\d{1,6})|(\\\\d\\\\d\\\\d\\\\d:\\\\d{1,3}:\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2})"
   }, 
   "id_s": {
      "required": "True", 
      "type": "int15", 
      "help": "Valid SEG-Y station number."
   }, 
   "deploy_time/ascii_s": {
      "required": "True", 
      "type": "string32", 
      "help": "Time: YYYY:JJJ:HH:MM:SS.sss or YYYY-MM-DDTHH:MM:SS.ssssss.",
      "re": "(\\\\d\\\\d\\\\d\\\\d:\\\\d{1,3}:\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2}(\\\\.\\\\d{1,3})?)|(\\\\d\\\\d\\\\d\\\\d-\\\\d{1,2}-\\\\d{1,2}T\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2}\\\\.\\\\d{1,6})|(\\\\d\\\\d\\\\d\\\\d:\\\\d{1,3}:\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2})"
   }, 
   "location/X/value_d": {
      "required": "False", 
      "type": "float64", 
      "help": "Longitude in degrees."
   }, 
   "location/Y/value_d": {
      "required": "False", 
      "type": "float64", 
      "help": "Latitude in degrees."
   }, 
   "location/Z/value_d": {
      "required": "False",     
      "type": "float64",                       
      "help": "Elevation in meters."
   },
   "Array": {
      "required": "True", 
      "type": "int32", 
      "help": "Array or line number."
   }, 
   "Deploy/Pickup" : {
      "required": "False",
      "type": "string1",
      "help": "Deploy 'D' or Pickup 'P' notes.",
      "re": "D|P"
   },
   "channel_number_i": {
      "required": "True", 
      "type": "int15", 
      "help": "Component, Possibly as follows: 1 -> Z, 2 -> N/S, 3 -> E/W etc..",
      "range": "1-6"
   },
   "das/serial_number_s": {
      "required": "True",
      "type": "string32",
      "help": "Full serial number of the data logger, ie. texans are 5 digits."
   },
   "das/model_s": {
      "required": "False",
      "type": "string32",
      "help": "The DAS model, rt-130, texan etc."
   },
   "das/manufacturer_s": {
      "required": "False",
      "type": "string32",
      "help": "The Das manufacturer, RefTek, kelco etc."
   },
   "sensor/serial_number_s": {
      "required": "False",
      "type": "string64",
      "help": "Full serial number of the sensor."
   },
   "sensor/model_s": {
      "required": "False",
      "type": "string64",
      "help": "Sensor model."
   },
   "sensor/manufacturer_s": {
      "required": "False",
      "type": "string64",
      "help": "Sensor manufacturer."
   },
   "SEED_Channel": {
      "required": "False",
      "type": "string3",
      "help": "SEED channel as described in Appendix A of SEED manual."
   },
   "seed_location_code_s": {
      "required": "False",
      "type": "string2",
      "help": "SEED location code as described in chapter 8 of the SEED manual."
   },
   "seed_station_name_s": {
      "required": "False",
      "type": "string5",
      "help": "SEED channel name as described in chapter 8 of the SEED manual."
   },
   "sample_rate_i": {
      "required": "False",
      "type": "int16",
      "help": "The sample rate in samples per second as an integer."
   },
   "sample_rate_multiplier_i": {
      "required": "False",
      "type": "int16",
      "help": "Usually 1 unless the sample rate is less than 1."
   }
}

'''

EVENT_CFG_S='''
{
   "location/X/value_d": {
      "required": "True", 
      "type": "float64", 
      "help": "Longitude in degrees."
   }, 
   "description_s": {
      "required": "False", 
      "type": "string1024", 
      "help": "Comment."
   }, 
   "size/units_s": {
      "required": "False", 
      "type": "string32", 
      "help": "kg, lbs, or magnitude."
   }, 
   "size/value_d": {
      "required": "False", 
      "type": "float64", 
      "help": "Size of shot, kg, lbs, magnitude."
   }, 
   "location/Y/value_d": {
      "required": "True", 
      "type": "float64", 
      "help": "Latitude in degrees."
   }, 
   "id_s": {
      "required": "True", 
      "type": "int31", 
      "help": "Valid SEG-Y shot number."
   }, 
   "location/Z/value_d": {
      "required": "False", 
      "type": "float64", 
      "help": "Elevation in meters."
   }, 
   "depth/value_d": {
      "required": "False", 
      "type": "float64", 
      "help": "Depth of shot or event below surface in meters."
   }, 
   "Array": {
      "required": "False", 
      "type": "int32", 
      "help": "The shot line or array number."
   }, 
   "time/ascii_s": {
      "required": "True",
      "type": "string32",
      "help": "Time: YYYY:JJJ:HH:MM:SS.sss or YYYY-MM-DDTHH:MM:SS.ssssss.",
      "re": "(\\\\d\\\\d\\\\d\\\\d:\\\\d{1,3}:\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2}\\\\.\\\\d{1,3})|(\\\\d\\\\d\\\\d\\\\d-\\\\d{1,2}-\\\\d{1,2}T\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2}\\\\.\\\\d{1,6})"
   }
}
'''



#   
SEPMAP = {'tab':None, 'comma':',', 'semi-colon':';', 'colon':':', 'space':None}

class MyWorker (QtCore.QThread) :
    def __init__ (self, command, table=None, names=None, cols=None, sep=None, outfile=None) :
        super (MyWorker, self).__init__ ()
        self.command = command
        self.table = table
        self.names = names
        self.cols = cols
        self.sep = sep
        self.outfile = outfile
        self.working = True
        
    def run (self) :
        #print "Run"
        #time.sleep (5)
        if self.command == 'qc_receivers' :
            while self.working :
                #print '*'
                self.working = novenqc.qc_receivers (self.table, 
                                                     self.names, 
                                                     self.cols, 
                                                     self.sep)
        elif self.command == 'qc_shots' :
            while self.working :
                #print '!'
                self.working = novenqc.qc_shots (self.table, 
                                                 self.names, 
                                                 self.cols, 
                                                 self.sep)
        elif self.command == 'qc_map' :
            #print '#'
            while self.working :
                self.working = novenqc.qc_map (self.outfile)
        else :
            print "Fail"

class MyQComboBox (QtGui.QComboBox) :
    def __init__ (self, values = []) :
        super (MyQComboBox, self).__init__ ()
        if values :
            self.addItems (values)

class MyQTableWidget (QtGui.QTableWidget) :
    def __init__ (self, parent = None) :
        super (MyQTableWidget, self).__init__ (parent)

class MyMessageBox(QtGui.QMessageBox):
    '''
       Make QMesageBox expand properly
    '''
    def __init__(self, parent=None):
        QtGui.QMessageBox.__init__(self, parent=parent)
        self.setSizeGripEnabled(True)

    def event(self, e):
        result = QtGui.QMessageBox.event(self, e)

        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)

        textEdit = self.findChild(QtGui.QTextEdit)
        if textEdit != None :
            textEdit.setMinimumHeight(0)
            textEdit.setMaximumHeight(16777215)
            textEdit.setMinimumWidth(0)
            textEdit.setMaximumWidth(16777215)
            textEdit.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)

        return result
        
class ErrorsDialog (QtGui.QMainWindow) :
    '''
       Dialog for displaying problems with input file
    '''
    def __init__ (self, errors, parent = None) :
        super (ErrorsDialog, self).__init__ (parent)
        self.setAttribute (QtCore.Qt.WA_DeleteOnClose)

        saveAction = QtGui.QAction('Save', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.setStatusTip('Save current file')
        saveAction.triggered.connect(self.saveFile)

        closeAction = QtGui.QAction('Close', self)
        closeAction.setShortcut('Ctrl+Q')
        closeAction.setStatusTip('Close error display')
        closeAction.triggered.connect(self.close)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(saveAction)
        fileMenu.addAction(closeAction)

        self.text = QtGui.QTextEdit(self)

        self.setCentralWidget(self.text)
        self.setGeometry(300,300,800,300)
        self.setWindowTitle('Errors')
        self.show()
        self.setIt (errors)

    def setIt(self, text):
        self.text.clear()
        text = '\n'.join (text)
        #print text
        self.text.setText (text)

    def saveFile(self):
        filename = QtGui.QFileDialog.getSaveFileName(self, 'Save File', os.getenv('HOME'))
        filename = str (filename)
        if not filename : return
        #f = open(filename[0], 'w')
        f = open(filename, 'w')
        filedata = self.text.toPlainText()
        f.write(filedata)
        f.close()

class SetupDialog (QtGui.QDialog) :
    '''
       Main configuration dialog
    '''
    changed = QtCore.pyqtSignal ()
    def __init__ (self, settings, parent = None) :
        super (SetupDialog, self).__init__ (parent)
        self.setAttribute (QtCore.Qt.WA_DeleteOnClose)
        
        inputFileTypeLabel = QtGui.QLabel ("Input Type")
        self.inputFileType = QtGui.QComboBox ()
        inputFileTypeLabel.setBuddy (self.inputFileType)
        self.inputFileType.addItems (['receiver', 'event'])
        self.inputFileType.setCurrentIndex (self.inputFileType.findText (settings['inFormat']))
        
        outfileFormatLabel = QtGui.QLabel ("Output Format")
        self.outfileFormat = QtGui.QComboBox ()
        outfileFormatLabel.setBuddy(self.outfileFormat)
        self.outfileFormat.addItems(["kef", "kef"])
        self.outfileFormat.setCurrentIndex (self.outfileFormat.findText (settings['outFormat']))
        
        fieldSeparatorLabel = QtGui.QLabel ("Column Separator")
        self.fieldSeparator = QtGui.QComboBox ()
        fieldSeparatorLabel.setBuddy (self.fieldSeparator)
        self.fieldSeparator.addItems (["comma", "semi-colon", "colon", "tab", "space"])
        self.fieldSeparator.setCurrentIndex (self.fieldSeparator.findText (settings['colSep']))
        
        skipLinesLabel = QtGui.QLabel ("Skip Lines")
        self.skipLines = QtGui.QSpinBox ()
        skipLinesLabel.setBuddy (self.skipLines)
        self.skipLines.setRange (0, 12)
        self.skipLines.setValue (settings['linesSkip'])
        
        viewLinesLabel = QtGui.QLabel ("View Lines")
        self.viewLines = QtGui.QSpinBox ()
        viewLinesLabel.setBuddy (self.viewLines)
        self.viewLines.setRange (1, 60)
        self.viewLines.setValue (settings['linesView'])
        
        self.settings = settings
        
        buttonBox = QtGui.QDialogButtonBox (QtGui.QDialogButtonBox.Apply |
                                            QtGui.QDialogButtonBox.Close)
        
        grid = QtGui.QGridLayout ()
        #
        grid.addWidget (inputFileTypeLabel, 0, 0); grid.addWidget (self.inputFileType, 0, 1)
        grid.addWidget (outfileFormatLabel, 1, 0); grid.addWidget (self.outfileFormat, 1, 1)
        grid.addWidget (fieldSeparatorLabel, 2, 0); grid.addWidget (self.fieldSeparator, 2, 1)
        grid.addWidget (skipLinesLabel, 3, 0); grid.addWidget (self.skipLines, 3, 1)
        grid.addWidget (viewLinesLabel, 4, 0); grid.addWidget (self.viewLines, 4, 1)
        
        grid.addWidget (buttonBox, 5, 0, 2, -1)
        self.setLayout (grid)
        
        self.connect (buttonBox.button (QtGui.QDialogButtonBox.Apply),
                      QtCore.SIGNAL ("clicked ()"), self.apply)
        
        self.connect (buttonBox, QtCore.SIGNAL ("rejected ()"),
                      self, QtCore.SLOT ("reject ()"))
        
        self.setWindowTitle ("Configure")
        #self.changed = QtCore.Signal ()
                      
    def apply (self) :
        #
        #print "Apply"
        self.settings['linesView'] = int (self.viewLines.value ())
        self.settings['colSep'] = str (self.fieldSeparator.currentText ())
        self.settings['outFormat'] = str (self.outfileFormat.currentText ())
        self.settings['linesSkip'] = int (self.skipLines.value ())
        self.settings['inFormat'] = str (self.inputFileType.currentText ())
        #print "Emit"
        #self.emit (QtCore.Signal ("changed"))
        self.changed.emit ()
        #print "Emitted"
    
    def rejected (self) :
        sys.stdout.write ("Reject\n")

class Novitiate (QtGui.QMainWindow) : 
    '''
       Program parent
    '''
    def __init__(self, parent=None) :
        super(Novitiate, self).__init__(parent)
        
        self.settings = dict (inFormat='receiver', outFormat='kef', colSep='comma', linesSkip=0, linesView=3)
        #
        self.setWindowTitle ('Noven Version: ' + PROG_VERSION)
        
        self.readFileLines = []
        
        self.comboBoxes = []; 
        self.last_maxY = None
        
        self.TOP = {}
        
        main ()
        #
        #   Setup menus
        #
        openin = QtGui.QAction ('Open...', self)
        openin.setShortcut ('Ctrl+O')
        openin.setStatusTip ('Open input file.')
        self.connect (openin, QtCore.SIGNAL ('triggered ()'), self.openInfile)
        
        checkin = QtGui.QAction ('Check input', self)
        checkin.setShortcut ('Ctrl+c')
        checkin.setStatusTip ('Check validity of input csv.')
        self.connect (checkin, QtCore.SIGNAL ('triggered ()'), self.checkInFile)
        
        mapin = QtGui.QAction ('Map locations...', self)
        mapin.setShortcut ('Ctrl+m')
        mapin.setStatusTip ('Produce a map of locations.')
        self.connect (mapin, QtCore.SIGNAL ('triggered ()'), self.mapInFile)
        
        saveas = QtGui.QAction ('Save As...', self)
        saveas.setShortcut ('Ctrl+S')
        saveas.setStatusTip ('Save output (kef) file.')
        self.connect (saveas, QtCore.SIGNAL ('triggered ()'), self.saveAs)
        
        config = QtGui.QAction ('Configure...', self)
        config.setShortcut ('Ctrl+C')
        config.setStatusTip ('Set input file field separator etc.')
        self.connect (config, QtCore.SIGNAL ('triggered ()'), self.configure)
        
        exit = QtGui.QAction('Exit', self)
        exit.setShortcut('Ctrl+Q')
        exit.setStatusTip('Exit application')
        self.connect(exit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))
        
        help = QtGui.QAction('Help', self)
        help.setShortcut('Ctrl+h')
        help.setStatusTip('Get help on column names.')
        self.connect(help, QtCore.SIGNAL('triggered()'), self.cbhelp)

        menubar = self.menuBar()
        file = menubar.addMenu('&File')
        file.addAction (openin)
        file.addAction (checkin)
        file.addAction (mapin)
        file.addAction (saveas)
        file.addAction (config)
        file.addAction (help)
        if not parent :
            file.addAction (exit)
        
        #
        #   Table
        #
        self.table = MyQTableWidget()
        self.setCentralWidget(self.table)
        
        self.status = self.statusBar()
        self.status.setSizeGripEnabled(False)
        
        self.setGeometry (300,300, 1200, 300)
        
    def configure (self) :
        #
        self.settingsDialog = SetupDialog (self.settings, self)
        #self.connect (self.settingsDialog, QtCore.SIGNAL ("changed"), self.refreshTable)
        self.settingsDialog.changed.connect (self.refreshTable)
        self.settingsDialog.show ()
        
    def refreshTable (self) :
        self.TOP = {}
        key = self.settings['colSep']
        #
        sep = SEPMAP[str (key)]
            
        maxY = 0
        LINES = []
        for line in self.readFileLines :
            line = line.strip ()
            flds = line.split (sep)
            if len (flds) > maxY : maxY = len (flds)
            LINES.append (flds)
            
        maxX = self.settings['linesView'] + 1
        if self.last_maxY != maxY :
            self.comboBoxes = []
            self.last_maxY = maxY
            
        self.table.clear ()
        
        self.table.setColumnCount (maxY)
        self.table.setRowCount (maxX)
        #
        hh = self.table.horizontalHeader ()
        hh.hide ()
        vh = self.table.verticalHeader ()
        vh.hide ()
        
        try :
            if self.table.cols :
                y = 0
                for t in self.table.cols :
                    item = QtGui.QTableWidgetItem (t)
                    self.table.setItem (0, y, item)
                    y += 1
                    
        except AttributeError as e :
            #print e.message
            if self.settings['inFormat'] == 'receiver' :
                cvalues = RECEIVER_CFG.keys ()
            else :
                cvalues = EVENT_CFG.keys ()
        
            cvalues.sort ()
            cvalues.insert (0, u'Ignore')
            for y in range (maxY) :
                try :
                    ci = self.comboBoxes[y].currentIndex ()
                except Exception as e :
                    #print e.message
                    ci = None
                    
                    
                cb = MyQComboBox (values=cvalues)
                if ci :
                    try :
                        cb.setCurrentIndex (ci)
                    except :
                        cb.setCurrentIndex (0)
                else :
                    cb.setCurrentIndex (0)
                    
                if len (self.comboBoxes) < maxY :
                    self.comboBoxes.append (cb)
                else :
                    self.comboBoxes[y] = cb
                    
                cb.highlighted.connect (self.huh)
                    
                self.table.setCellWidget (0, y, cb)
                
            
        s = self.settings['linesSkip']
        for x in range (maxX) :
            try :
                FLDS = LINES[x + s]
            except IndexError :
                continue
            
            for y in range (maxY) :
                try :
                    text = "{0}".format(FLDS[y])
                except IndexError :
                    continue
                
                item = QtGui.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignRight |
                                      QtCore.Qt.AlignVCenter)
                
                #
                self.table.setItem (x + 1, y, item)
                
        self.table.resizeColumnsToContents ()
        self.table.setAcceptDrops (True)
        self.setWindowTitle (self.settings['inFormat'])
        
    #   Slot for QCombobox highlight signal
    def huh (self, x) :
        #print x
        if x == 0 : return
        x -= 1
        if self.settings['inFormat'] == 'receiver' :
            cols = RECEIVER_CFG
        else :
            cols = EVENT_CFG
            
        keys = cols.keys ()
        keys = map (str, keys); keys.sort ()
        #keys = ["Ignore"] + keys
        #cols["Ignore"] = {}; cols["Ignore"]['help'] = "Ignore the entire column."
        #print keys
        help = cols[keys[x]]['help']
        self.status.showMessage(help)
        
    def cbhelp (self) :
        if self.settings['inFormat'] == 'receiver' :
            cols = RECEIVER_CFG
        else :
            cols = EVENT_CFG
        
        
        help = "{0:<25}{1}".format ("Ignore:", "Ignore this entire column.\n\n")
        keys = cols.keys ()
        keys.sort ()
        for k in keys : 
            help += "{0:<25}{1}\n\n".format (k + ':', str (cols[k]['help']).strip ())
         
        mb = MyMessageBox (parent=None)
        mb.setFont (QtGui.QFont ('Courier', 10, QtGui.QFont.Bold))
        mb.setWindowTitle ('Socorro')
        mb.setText (help)
        mb.setModal (False)
        mb.open ()
        mb.exec_ ()
        
        
    def qcDone (self) :
        self.status.showMessage ("Done")
        if novenqc.ERR != None and len (novenqc.ERR) != 0 :
            self.errorsDialog = ErrorsDialog (novenqc.ERR, self)
            self.errorsDialog.show ()
        else :
            QtGui.QMessageBox.information(self, "Information", "Nothing funky found!")
    
        self.TOP = novenqc.TOP
            
    def openInfile (self) :
        #
        filters = 'CSV files: (*.csv);; Text files: (*.txt);; All: (*)'
        selected = 'CSV files: (*.csv)'
        inFileName = QtGui.QFileDialog.getOpenFileName (self, "Open input file", os.getcwd (), filters, selected)
        #
        #if os.path.exists (inFileName[0]) :
        if os.path.exists (inFileName) :
            #
            #fh = open (inFileName[0], 'U')
            fh = open (inFileName, 'U')
            self.readFileLines = fh.readlines ()
            fh.close ()
            self.table.clear ()
            self.refreshTable ()
        else :
            self.readFileLines = None
            
    def mapInFile (self) :
        if self.TOP == {} :
            reply = QtGui.QMessageBox.information(self, "Can't continue.", "Must check inputs first.") 
            return
        
        outFileName = QtGui.QFileDialog.getSaveFileName (self, 'Output KML file name.', os.getcwd (), filter='*.kml') 
        #print outFileName
        if outFileName :
            if outFileName[-4:] != '.kml' :
                outFileName += '.kml'
            
            self.status.showMessage ("Working on kml...")
            worker = MyWorker ('qc_map', outfile=outFileName)
            #worker.finished.connect (self.qcDone)
            worker.start ()
            worker.wait ()
            #novenqc.qc_map (outFileName)
        
    def checkInFile (self) :
        if not self.readFileLines :
            reply = QtGui.QMessageBox.information(self, "Can't continue.", "Must open and configure csv file first.") 
            return
        #print 'Checking infile...'
        names = map (lambda x : str (x.currentText ()), self.comboBoxes)
        tmp = []
        for n in names :
            if n in tmp :
                QtGui.QMessageBox.information(self, "Can't continue.", "Duplicated column: {0}".format (n))
                return
            if n != 'Ignore' :
                tmp.append (n)
            
        if self.settings['inFormat'] == 'receiver' :
            #print 'Receiver check'
            worker = MyWorker ('qc_receivers',
                               self.readFileLines[self.settings['linesSkip']:],
                               names,
                               RECEIVER_CFG,
                               sep=SEPMAP[self.settings['colSep']])
            #ret = novenqc.qc_receivers (self.readFileLines[self.settings['linesSkip']:], 
                                        #map (lambda x : str (x.currentText ()), self.comboBoxes),
                                        #RECEIVER_CFG,
                                        #sep=SEPMAP[self.settings['colSep']])
        elif self.settings['inFormat'] == 'event' :
            #print 'Event check'
            worker = MyWorker ('qc_shots',
                               self.readFileLines[self.settings['linesSkip']:], 
                               names,
                               EVENT_CFG,
                               sep=SEPMAP[self.settings['colSep']])
            #ret = novenqc.qc_shots (self.readFileLines[self.settings['linesSkip']:], 
                                    #map (lambda x : str (x.currentText ()), self.comboBoxes),
                                    #EVENT_CFG,
                                    #sep=SEPMAP[self.settings['colSep']])
        #print worker
        self.status.showMessage ("Working on QC...") 
        worker.finished.connect (self.qcDone)
        worker.start ()
        worker.wait ()
        #print '.'
        
    def saveAs (self) :
        #
        if self.TOP == {} :
            reply = QtGui.QMessageBox.information(self, "Can't continue.", "Must open csv and check inputs first.") 
            return  
        
        saveFileName = QtGui.QFileDialog.getSaveFileName(self, 'Save output as', os.getcwd (), filter="*.kef")
        novenkef.write_kef (self.TOP, saveFileName)
        
#
###   Mix-ins
#
def read_cfg (filename) :
    fh = open (filename)
    ret = json.load (fh)
    fh.close ()
    
    return ret

def main () :
    return
def startapp():
    global RECEIVER_CFG, EVENT_CFG
    home = expanduser("~")
    if not os.path.isfile(os.path.join (home,'.PH5', 'Receiver.cfg')) or not os.path.isfile(os.path.join (home,'.PH5', 'Event.cfg')):
        create_config = raw_input("It appears your home directory doesn't contain config files for noven.\nIt is advised you have config files created. Do you want config files to be created for you(y/n)?:")
        if create_config.upper() == "Y":
            print "Installing to: "+str(os.path.join (home,'.PH5'))
            if not os.path.exists(os.path.join (home,'.PH5')):
                os.makedirs(os.path.join (home,'.PH5'))            
            f = open(os.path.join (home,'.PH5', 'Receiver.cfg'), 'w')
            f.write(str(RECEIVER_CFG_S))
            f.close()
            f = open(os.path.join (home,'.PH5', 'Event.cfg'), 'w')
            f.write(str(EVENT_CFG_S))
            f.close()
        else:
            RECEIVER_CFG = json.loads(RECEIVER_CFG_S)
            EVENT_CFG = json.loads(EVENT_CFG_S)
    else:
        RECEIVER_CFG = read_cfg (os.path.join (home,'.PH5', 'Receiver.cfg'))
        EVENT_CFG = read_cfg (os.path.join (home,'.PH5', 'Event.cfg'))
    
    app = QtGui.QApplication(sys.argv)
    form = Novitiate ()
    form.show ()
    app.exec_ ()    
    
if __name__ == '__main__' :
    startapp()
