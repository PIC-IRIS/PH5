#!/usr/bin/env pnpython3
#
#   Steve Azevedo, February 2016
#

import os, sys, time
from PySide import QtCore, QtGui
from psutil import cpu_count, cpu_percent
#import pformaGUI_rc
from ph5.core import pmonitor
from ph5.utilities import pforma_io, watchit

PROG_VERSION = "2017.032 Developmental"

UTMZone = None

class GetInputs (QtGui.QWidget) :
    '''
       Widget to set name of lst file, processing directory, and to start run
    '''
    def __init__ (self, parent=None) :
        super (GetInputs, self).__init__ (parent)
        
        #   Button to start run
        self.runButton = QtGui.QPushButton ("Run")
        #   Select master list of raw files
        self.lstButton = self.createButton ("Browse...", self.getList)
        self.lstButton.setStatusTip ("Browse for raw lst file.")
        self.lstCombo = self.createComboBox ()
        lstText = QtGui.QLabel ("RAW list file:")
        #   Select processing directory
        lstLayout = QtGui.QHBoxLayout ()
        lstLayout.addStretch (False)
        lstLayout.addWidget (lstText)
        lstLayout.addWidget (self.lstCombo)
        lstLayout.addWidget (self.lstButton)
        
        self.dirButton = self.createButton ("Browse...", self.getDirectory)
        self.dirButton.setStatusTip ("Browse for or create processing directory.")
        self.dirCombo = self.createComboBox ()
        dirText = QtGui.QLabel ("Processing directory:")
        
        lstLayout.addWidget (dirText)
        lstLayout.addWidget (self.dirCombo)
        lstLayout.addWidget (self.dirButton)
        lstLayout.addSpacing (54)
        lstLayout.addWidget (self.runButton)
        
        self.setLayout (lstLayout)
        self.show ()
        
    def createButton(self, text, member):
        '''
           Create a button and connect it to 'member'
        '''
        button = QtGui.QPushButton(text)
        button.clicked.connect(member)
        return button 
    
    def createComboBox(self, text=""):
        '''
           Create a combo box
        '''
        comboBox = QtGui.QComboBox()
        comboBox.setEditable(True)
        comboBox.addItem(text)
        comboBox.setSizePolicy(QtGui.QSizePolicy.Expanding,
                               QtGui.QSizePolicy.Preferred)
        return comboBox    
    
    def getList (self) :
        '''
           Select the raw lst file
        '''
        lstfile, _ = QtGui.QFileDialog.getOpenFileName (self, 'List file', QtCore.QDir.currentPath())
        
        if lstfile and os.path.exists (lstfile) :
            if self.lstCombo.findText (lstfile) == -1 :
                self.lstCombo.addItem (lstfile)
                
            self.lstCombo.setCurrentIndex (self.lstCombo.findText (lstfile))
    
    def getDirectory (self) :
        '''
           Select or create the processing directory
        '''
        directory = QtGui.QFileDialog.getExistingDirectory(self, "Working directory",
                                                           QtCore.QDir.currentPath())
        if directory:
            if self.dirCombo.findText(directory) == -1:
                self.dirCombo.addItem(directory)

            self.dirCombo.setCurrentIndex(self.dirCombo.findText(directory)) 
        pass
    
class MdiChild (pmonitor.Monitor) :
    '''
       Create instance of pmonitor.Monitor
    '''
    def __init__ (self, fio, cmds, info, title='X', mmax=100) :
        super (MdiChild, self).__init__ (fio, cmds, info, title, mmax)
        
class MdiChildDos (QtGui.QProgressDialog) :
    def __init__ (self, home, title='X') :
        super (MdiChildDos, self).__init__ (title, "Close", 0, 0)
        self.home = home
        self.good = True
        self.setMinimumWidth (400)
        
        self.fio, self.cmds, self.info = init_fio (None, self.home)
        if os.path.exists (os.path.join (self.fio.home, 'Sigma')) :
            mess = QtGui.QMessageBox ()
            mess.setText ("Please remove existing directory {0}.".format (os.path.join (self.fio.home, 'Sigma')))
            mess.exec_ ()
            self.good = False
        
        #self.wd = watchit.Watchdog (3, userHandler=self.run)
        #self.wd.start ()
        
    def run (self) :
        msgs = self.fio.unite ('Sigma')
        self.setLabelText ("Completed")
        self.setRange (1, 1)
        
        mess = QtGui.QMessageBox ()
        mess.setWindowTitle ("Merge Progress Summary")
        mess.setDetailedText ('\n'.join (msgs))
        #mess.setSizeGripEnabled (True)
        mess.exec_ ()
        #print "Done"
        #self.cancel ()
        
class MainWindow(QtGui.QMainWindow):
    statsig = QtCore.Signal (str)
    def __init__(self):
        super(MainWindow, self).__init__ ()

        self.mdiArea = QtGui.QMdiArea()
        self.mdiArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.mdiArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setCentralWidget(self.mdiArea)

        self.windowMapper = QtCore.QSignalMapper(self)
        self.windowMapper.mapped.connect(self.setActiveSubWindow)

        self.createActions()
        self.createMenus()
        self.createStatusBar()
        self.updateMenus()
        self.createDockWidget ()
        self.timeout = 2000
        self.UTMZone = UTMZone
        self.combine = 1

        self.readSettings()

        self.setWindowTitle("pforma v{0}".format (PROG_VERSION))
        self.setUnifiedTitleAndToolBarOnMac(True)
        
    def killchildren (self) :
        #print 'kill'
        try :
            for f in self.children.keys () :
                c = self.children[f]
                c.endConversion ()
                self.mdiArea.removeSubWindow (c)
            self.mdiArea.closeAllSubWindows ()
        except Exception as e :
            print "Z", e.message
        
    def resetIt (self) :
        '''
           Reset (Kill) all family processes.
        '''
        reply = QtGui.QMessageBox.question(self, 'Message',
                                           "Are you sure you want to reset family processing?\nAll state information will be lost!!!", QtGui.QMessageBox.Yes | 
                                           QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        
        if reply == QtGui.QMessageBox.No :
            return
            
        self.killchildren ()

        self.inputs.runButton.setEnabled (True)
        self.runAct.setEnabled (True)
                

    def closeEvent(self, event):
        self.mdiArea.closeAllSubWindows()
        if self.activeMdiChild():
            event.ignore()
        else:
            self.writeSettings()
            event.accept()
            
    def checkOnChildren (self) :
        '''
           Check status of all mdi processes
        '''
        #self.wd.reset (); self.wd.start (); return
        done = []
        running = []
        somerunning = False
        #if False :
        #   Loop through all children
        for c in self.children.keys () :
            m = self.children[c]
            if m.running == True :
                somerunning = True
                running.append (c)
            else :
                done.append (c)
                
        if not somerunning :
            #print "Nobody running..."; sys.stdout.flush ()
            for c in self.children.keys () :
                m = self.children[c]
                #XXX
                m.fio.merge (m.processedFiles.keys ())
            
            #XXX    
            self.fio.write_cfg ()
            self.wd.stop ()
            self.statsig.emit ("All processes finished. Wrote pforma.cfg.")
        else :
            self.wd.reset ()
            self.wd.start ()
            load = cpu_percent ()
            self.statsig.emit ("Load: {0}%".format (load))
            #ter = len (done)
            #run = len (running)
            #self.statusBar().showMessage ("Processing {0}".format ("/".join (self.children.keys ())))
            #self.statusBar ().showMessage ("Familys terminated: {0}. Familys processing: {1}.".format (ter, run))
    
    def mergeFamily (self) :
        mydir = self.inputs.dirCombo.currentText ()
        if not mydir :
            mess = QtGui.QMessageBox ()
            mess.setText ("Processing directory must be set!")
            mess.exec_ ()
            return
        
        self.statsig.emit ("Merging PH5 families to Sigma. This may take awhile...")
        pd = MdiChildDos (mydir, "Merging to Sigma...")
        if pd.good :
            pd.canceled.connect (self.mdiArea.closeAllSubWindows)
            self.mdiArea.addSubWindow (pd)
            pd.show ()
            pd.run ()
        else :
            pd.close ()
             
    def newFamily (self) :
        '''
           Create a new mdi's
        '''
        self.statsig.emit ("Setting up/Checking processing area.")
        #   Set up family processing via fio
        if not self.setupProcessing () :
            return
        #   Ts is a list of family names
        Ts = self.info.keys ()
        Ts.sort ()
        self.children = {}
        self.inputs.runButton.setDisabled (True)
        self.runAct.setDisabled (True)
        for T in Ts :
            #   Commands to run for this family
            c = self.cmds[T]
            #   What are the types of data being converted?
            i = self.info[T]
            #   Get number of raw files to convert in this family
            m = 0
            for f in self.info[T]['lists'] :
                m += get_len (f)
             
            if m > 0 : 
                #   Create a new mdi child
                child = self.createMdiChild(c, i, T, m)
                child.show()
                self.children[T] = child
        #   Set up an after to check on children    
        self.wd = watchit.Watchdog (12, userHandler=self.checkOnChildren)
        self.wd.start ()
        self.statsig.emit ("Processing {0}".format ("/".join (self.children.keys ())))

    def about(self):
        QtGui.QMessageBox.about(self, "About pforma",
                                "The <b>pforma</b> program performs conversions to PH5 in parallel. "
                                "Note to self: Need a better about.")

    def updateMenus(self):
        hasMdiChild = (self.activeMdiChild() is not None)
        
        self.separatorAct.setVisible(hasMdiChild)

    def createMdiChild(self, c, i, t, m) :
        '''
           Create an instance of pmonitor.Monitor
        '''
        child = MdiChild(self.fio,
                         c,
                         i,
                         title=t,
                         mmax=m)
        
        child.setTimeout (self.timeout)
        
        self.mdiArea.addSubWindow(child)

        return child

    def createActions(self):
        self.runAct = QtGui.QAction ("&Run", self, statusTip="Initiate processing.",
                                     triggered=self.newFamily)
        self.mergeAct = QtGui.QAction ("&Merge", self, statusTip="Merge processed families to a single family.",
                                       triggered=self.mergeFamily)
        self.timeoutAct = QtGui.QAction ("Set &Timeout...", self, 
                                         statusTip="Change timeout to process a single raw file.",
                                         triggered=self.setTimeout)
        self.utmAct = QtGui.QAction ("&UTM zone...", self,
                                     statusTip="UTM zone. For some SEG-D data.",
                                     triggered=self.setUTMZone)
        self.combineAct = QtGui.QAction ("Combine # of SEG-D traces in ph5...", self,
                                         statusTip="Combine a number of SEG-D traces for faster processing.",
                                         triggered=self.setCombineSEGD)
        self.resetAct = QtGui.QAction ("R&eset", self, 
                                       statusTip="Reset all family processes.",
                                       triggered=self.resetIt)

        self.exitAct = QtGui.QAction("E&xit", self, shortcut="Ctrl+Q",
                                     statusTip="Exit the application",
                                     triggered=QtGui.qApp.closeAllWindows)

        self.separatorAct = QtGui.QAction(self)
        self.separatorAct.setSeparator(True)

        self.aboutAct = QtGui.QAction("&About", self,
                                      statusTip="Show pforma's About box",
                                      triggered=self.about)

        #self.aboutQtAct = QtGui.QAction("About &Qt", self,
                                        #statusTip="Show the Qt library's About box",
                                        #triggered=QtGui.qApp.aboutQt)

    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction (self.runAct)
        self.fileMenu.addAction (self.mergeAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction (self.timeoutAct)
        self.fileMenu.addAction (self.utmAct)
        self.fileMenu.addAction (self.combineAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction (self.resetAct)
        self.fileMenu.addAction(self.exitAct)

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpMenu.addAction(self.aboutAct)
        #self.helpMenu.addAction(self.aboutQtAct)
        
    def createDockWidget (self) :
        '''
           Put GetInputs widget in dock
        '''
        self.dockWidget = QtGui.QDockWidget(self)
        self.inputs = GetInputs ()
        self.inputs.runButton.clicked.connect (self.newFamily)
        self.inputs.runButton.setStatusTip ("Initiate processing.")
        self.dockWidget.setWidget(self.inputs)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.dockWidget)

    def createStatusBar(self):
        self.statsig.connect (self.statusBar().showMessage, type=QtCore.Qt.QueuedConnection)
        #QtCore.QObject.connect (self,
                                #QtCore.SIGNAL ("statsig()"),
                                #self,
                                #QtCore.SLOT ("showMessage()"),
                                #QtCore.Qt.QueuedConnection)
        self.statsig.emit ("Ready")

    def readSettings(self):
        '''
           Read position and size from QSettings
        '''
        settings = QtCore.QSettings('PH5', 'pforma')
        pos = settings.value('pos', QtCore.QPoint(200, 200))
        size = settings.value('size', QtCore.QSize(400, 400))
        self.move(pos)
        self.resize(size)

    def writeSettings(self):
        '''
            Save QSettings
        '''
        settings = QtCore.QSettings('PH5', 'pforma')
        settings.setValue('pos', self.pos())
        settings.setValue('size', self.size())

    def activeMdiChild(self):
        activeSubWindow = self.mdiArea.activeSubWindow()
        if activeSubWindow:
            return activeSubWindow.widget()
        return None

    def findMdiChild(self, fileName):
        canonicalFilePath = QtCore.QFileInfo(fileName).canonicalFilePath()

        for window in self.mdiArea.subWindowList():
            if window.widget().currentFile() == canonicalFilePath:
                return window
        return None

    def setActiveSubWindow(self, window):
        if window:
            self.mdiArea.setActiveSubWindow(window)
            
    def setTimeout (self) :
        a, _ = QtGui.QInputDialog.getInt (self, "Set Timeout", "Timeout seconds:", self.timeout)
        if _ :
            self.timeout = a
            
    def setUTMZone (self) :
        a, _ = QtGui.QInputDialog.getInt (self, "Set UTM zone", "UTM Zone:",
                                          minValue=1, maxValue=60)
        if _ :
            self.UTMZone = a
        else :
            self.UTMZone = None
            
    def setCombineSEGD (self) :
        a, _ = QtGui.QInputDialog.getInt (self, "Set number of traces to combine", "Combined number:",
                                          minValue=1, maxValue=120)
        if _ :
            self.combine = a
        else :
            self.combine = 1
            
    def setupProcessing (self) :
        '''
           Read inputs and start processing (Run)
        '''
        ##   XXX Set UTM zone for segd2ph5 if needed
        #if self.UTMZone : self.fio.set_utm (self.UTMZone)
        #if self.combine : self.fio.set_combine (self.combine)
        mydir = self.inputs.dirCombo.currentText ()
        mylst = self.inputs.lstCombo.currentText ()
        if not mydir or not mylst :
            #self.statusBar ().showMessage ("RAW list or processing directory not set.")
            mess = QtGui.QMessageBox ()
            mess.setText ("A RAW file list and processing directory must be set!")
            mess.exec_ ()
            return False
        self.statsig.emit ("Setting up processing of list {0} at {1}".format (mylst, mydir))
        self.fio, self.cmds, self.info = init_fio (mylst, mydir, utm=self.UTMZone, combine=self.combine)
        #if TSPF : fio.set_tspf (TSPF)          
        fams = self.cmds.keys ()
        self.statsig.emit ("Processing families {0}".format (" ".join (fams)))
        return True
#
###   Mix-ins
#
def get_len (f) :
    '''
        Read the number of lines in a text file. 
        Input: 
            f -> file name
        Output:
            num_lines -> number of lines in file
    '''
    num_lines = sum(1 for line in open (f))
    
    return num_lines

def init_fio (f, d, utm=None, combine=None) :
    '''
        Initialize parallel processing
        Inputs:
            f -> file name of file containing list of raw files
            d -> directory where families of PH5 files are processed
        Outputs:
            fio -> an instance of FormaIO
            cmds -> list of conversion commands
            lsts -> info about processing sub-lists and types of instruments
    '''
    #from multiprocessing import cpu_count
    fio = pforma_io.FormaIO (infile=f, outdir=d)
    if utm : fio.set_utm (utm)
    if combine : fio.set_combine (combine)
    if cpu_count (logical=False) > 3 :
        fio.set_nmini (cpu_count (logical=True) + 1)
    else :
        fio.set_nmini (cpu_count (logical=True))
        
    fio.initialize_ph5 ()
    
    try :
        fio.open ()
    except pforma_io.FormaIOError as e :
        print e.errno, e.message

    try :
        fio.read ()
        #gb = fio.total_raw / 1024. / 1024. / 1024.
        #timeout = (gb / get_len (f)) * 1000.
        #print "Total raw: {0}GB".format (int (fio.total_raw / 1024 / 1024 / 1024))
        #print "M:", fio.M
        #print "N:", fio.nmini
        #time.sleep (10)
    except pforma_io.FormaIOError as e :
        print e.errno, e.message
    
    try :
        fio.readDB ()
    except pforma_io.FormaIOError as e :
        print e.errno, e.message
        sys.exit (-1)
        
    fio.resolveDB ()
    cmds, lsts, i = fio.run (runit=False)
    return fio, cmds, lsts


def startapp():

    import sys

    app = QtGui.QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    startapp()
