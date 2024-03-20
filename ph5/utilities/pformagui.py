#!/usr/bin/env pnpython3
#
# Steve Azevedo, February 2016
#

import os
import sys
import logging
from psutil import cpu_count, cpu_percent
from ph5.core import pmonitor
from ph5.utilities import pforma_io, watchit

PROG_VERSION = '2021.84'
LOGGER = logging.getLogger(__name__)
try:
    from PySide2 import QtCore, QtWidgets
except Exception:
    msg = ("\n\nNo module named PySide2. "
           "Please environment_gui.yml to install conda environment"
           "PySide2 is needed for pforma.")
    raise ImportError(msg)

UTMZone = '13N'


class GetInputs(QtWidgets.QWidget):
    '''
       Widget to set name of lst file, processing directory, and to start run
    '''

    def __init__(self, parent=None):
        super(GetInputs, self).__init__(parent)

        # Button to start run
        self.runButton = QtWidgets.QPushButton("Run")
        # Select master list of raw files
        self.lstButton = self.createButton("Browse...", self.getList)
        self.lstButton.setStatusTip(
            "Browse for raw list file. "
            "For SmartSolo, map file created by map_header can be used to "
            "reduce reading file headers when building ph5. ")
        self.lstCombo = self.createComboBox()
        lstText = QtWidgets.QLabel("MAP/RAW list file:")
        # Select processing directory
        lstLayout = QtWidgets.QHBoxLayout()
        lstLayout.addStretch(False)
        lstLayout.addWidget(lstText)
        lstLayout.addWidget(self.lstCombo)
        lstLayout.addWidget(self.lstButton)

        self.dirButton = self.createButton("Browse...", self.getDirectory)
        self.dirButton.setStatusTip(
            "Browse for or create processing directory.")
        self.dirCombo = self.createComboBox()
        dirText = QtWidgets.QLabel("Processing directory:")

        lstLayout.addWidget(dirText)
        lstLayout.addWidget(self.dirCombo)
        lstLayout.addWidget(self.dirButton)
        lstLayout.addSpacing(54)
        lstLayout.addWidget(self.runButton)

        self.setLayout(lstLayout)
        self.show()

    def createButton(self, text, member):
        '''
           Create a button and connect it to 'member'
        '''
        button = QtWidgets.QPushButton(text)
        button.clicked.connect(member)
        return button

    def createComboBox(self, text=""):
        '''
           Create a combo box
        '''
        comboBox = QtWidgets.QComboBox()
        comboBox.setEditable(True)
        comboBox.addItem(text)
        comboBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                               QtWidgets.QSizePolicy.Preferred)
        return comboBox

    def getList(self):
        '''
           Select the raw lst file
        '''
        lstfile, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'List file', QtCore.QDir.currentPath())

        if lstfile and os.path.exists(lstfile):
            if self.lstCombo.findText(lstfile) == -1:
                self.lstCombo.addItem(lstfile)

            self.lstCombo.setCurrentIndex(self.lstCombo.findText(lstfile))

    def getDirectory(self):
        '''
           Select or create the processing directory
        '''
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Working directory",
            QtCore.QDir.currentPath())
        if directory:
            if self.dirCombo.findText(directory) == -1:
                self.dirCombo.addItem(directory)

            self.dirCombo.setCurrentIndex(self.dirCombo.findText(directory))


class MdiChild(pmonitor.Monitor):
    '''
       Create instance of pmonitor.Monitor
    '''

    def __init__(self, fio, cmds, info, title='X', mmax=100, main_window=None):
        super(MdiChild, self).__init__(
            fio, cmds, info, title, mmax, main_window)


class MdiChildDos(QtWidgets.QProgressDialog):
    def __init__(self, home, title='X', main_window=None):
        super(MdiChildDos, self).__init__(title, "Close", 0, 0)
        self.home = home
        self.good = True
        self.setMinimumWidth(400)

        self.fio, self.cmds, self.info = init_fio(None, self.home,
                                                  main_window=main_window)
        if os.path.exists(os.path.join(self.fio.home, 'Sigma')):
            mess = QtWidgets.QMessageBox()
            mess.setText("Please remove existing directory {0}.".format(
                os.path.join(self.fio.home, 'Sigma')))
            mess.exec_()
            self.good = False

    def run(self):
        msgs = self.fio.unite('Sigma')
        self.setLabelText("Completed")
        self.setRange(1, 1)

        mess = QtWidgets.QMessageBox()
        mess.setWindowTitle("Merge Progress Summary")
        mess.setDetailedText('\n'.join(msgs))
        mess.exec_()


class MainWindow(QtWidgets.QMainWindow):
    statsig = QtCore.Signal(str)

    def __init__(self):
        super(MainWindow, self).__init__()

        self.mdiArea = QtWidgets.QMdiArea()
        self.mdiArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.mdiArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setCentralWidget(self.mdiArea)

        self.windowMapper = QtCore.QSignalMapper(self)
        self.windowMapper.mapped.connect(self.setActiveSubWindow)

        self.createActions()
        self.createMenus()
        self.createStatusBar()
        self.updateMenus()
        self.createDockWidget()
        self.timeout = 2000
        self.UTMZone = UTMZone
        self.combine = 1

        self.readSettings()

        self.setWindowTitle("pforma v{0}".format(PROG_VERSION))
        self.setUnifiedTitleAndToolBarOnMac(True)

    def killchildren(self):
        try:
            for f in self.children.keys():
                c = self.children[f]
                c.endConversion()
                self.mdiArea.removeSubWindow(c)
            self.mdiArea.closeAllSubWindows()
        except Exception as e:
            LOGGER.error("Z: {0}".format(e.message))

    def resetIt(self):
        '''
           Reset (Kill) all family processes.
        '''
        reply = QtWidgets.QMessageBox.question(
            self,
            'Message',
            "Are you sure you want to reset family processing?"
            "\nAll state information will be lost!!!",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.No:
            return

        self.killchildren()

        self.inputs.runButton.setEnabled(True)
        self.runAct.setEnabled(True)

    def closeEvent(self, event):
        self.mdiArea.closeAllSubWindows()
        if self.activeMdiChild():
            event.ignore()
        else:
            self.writeSettings()
            event.accept()

    def checkOnChildren(self):
        '''
           Check status of all mdi processes
        '''
        done = []
        running = []
        somerunning = False
        # Loop through all children
        for c in self.children.keys():
            m = self.children[c]
            if m.running is True:
                somerunning = True
                running.append(c)
            else:
                done.append(c)

        if not somerunning:
            for c in self.children.keys():
                m = self.children[c]
                m.fio.merge(m.processedFiles.keys())

            self.fio.write_cfg()
            self.wd.stop()
            self.statsig.emit("All processes finished. Wrote pforma.cfg.")
        else:
            self.wd.reset()
            self.wd.start()
            load = cpu_percent()
            self.statsig.emit("Load: {0}%".format(load))

    def mergeFamily(self):
        mydir = self.inputs.dirCombo.currentText()
        if not mydir:
            mess = QtWidgets.QMessageBox()
            mess.setText("Processing directory must be set!")
            mess.exec_()
            return

        self.statsig.emit(
            "Merging PH5 families to Sigma. This may take awhile...")
        pd = MdiChildDos(mydir, "Merging to Sigma...", main_window=self)
        if pd.good:
            pd.canceled.connect(self.mdiArea.closeAllSubWindows)
            self.mdiArea.addSubWindow(pd)
            pd.show()
            pd.run()
        else:
            pd.close()

    def newFamily(self):
        '''
           Create a new mdi's
        '''
        self.statsig.emit("Setting up/Checking processing area.")
        # Set up family processing via fio
        if not self.setupProcessing():
            return
        # Ts is a list of family names
        Ts = sorted(self.info.keys())
        self.children = {}
        self.inputs.runButton.setDisabled(True)
        self.runAct.setDisabled(True)
        for T in Ts:
            # Commands to run for this family
            c = self.cmds[T]
            # What are the types of data being converted?
            i = self.info[T]
            # Get number of raw files to convert in this family
            m = 0
            for f in self.info[T]['lists']:
                m += get_len(f)

            if m > 0:
                # Create a new mdi child
                child = self.createMdiChild(c, i, T, m)
                child.show()
                self.children[T] = child
        # Set up an after to check on children
        self.wd = watchit.Watchdog(12, userHandler=self.checkOnChildren)
        self.wd.start()
        self.statsig.emit("Processing {0}".format(
            "/".join(self.children.keys())))

    def about(self):
        QtWidgets.QMessageBox.about(self,
                                    "About pforma",
                                    "The <b>pforma</b> program performs"
                                    "conversions to PH5 in parallel. "
                                    "Note to self: Need a better about.")

    def updateMenus(self):
        hasMdiChild = (self.activeMdiChild() is not None)

        self.separatorAct.setVisible(hasMdiChild)

    def createMdiChild(self, c, i, t, m):
        '''
           Create an instance of pmonitor.Monitor
        '''
        child = MdiChild(self.fio,
                         c,
                         i,
                         title=t,
                         mmax=m,
                         main_window=self)

        child.setTimeout(self.timeout)

        self.mdiArea.addSubWindow(child)

        return child

    def createActions(self):
        self.runAct = QtWidgets.QAction(
            "&Run",
            self,
            statusTip="Initiate processing.",
            triggered=self.newFamily)
        self.mergeAct = QtWidgets.QAction(
            "&Merge",
            self,
            statusTip="Merge processed families to a single family.",
            triggered=self.mergeFamily)
        self.timeoutAct = QtWidgets.QAction(
            "Set &Timeout...",
            self,
            statusTip="Change timeout to process a single raw file.",
            triggered=self.setTimeout)
        self.utmAct = QtWidgets.QAction(
            "&UTM zone...",
            self,
            statusTip="UTM zone. For some SEG-D data. zone plus N or S (13N)",
            triggered=self.setUTMZone)
        self.combineAct = QtWidgets.QAction(
            "Combine # of SEG-D traces in ph5...",
            self,
            statusTip="Combine a number of SEG-D\
            traces for faster processing.",
            triggered=self.setCombineSEGD)
        self.resetAct = QtWidgets.QAction(
            "R&eset",
            self,
            statusTip="Reset all family processes.",
            triggered=self.resetIt)

        self.exitAct = QtWidgets.QAction(
            "E&xit",
            self,
            shortcut="Ctrl+Q",
            statusTip="Exit the application",
            triggered=QtWidgets.qApp.closeAllWindows)

        self.separatorAct = QtWidgets.QAction(self)
        self.separatorAct.setSeparator(True)

        self.aboutAct = QtWidgets.QAction("&About", self,
                                          statusTip="Show pforma's About box",
                                          triggered=self.about)

    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(self.runAct)
        self.fileMenu.addAction(self.mergeAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.timeoutAct)
        self.fileMenu.addAction(self.utmAct)
        self.fileMenu.addAction(self.combineAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.resetAct)
        self.fileMenu.addAction(self.exitAct)

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpMenu.addAction(self.aboutAct)

    def createDockWidget(self):
        '''
           Put GetInputs widget in dock
        '''
        self.dockWidget = QtWidgets.QDockWidget(self)
        self.inputs = GetInputs()
        self.inputs.runButton.clicked.connect(self.newFamily)
        self.inputs.runButton.setStatusTip("Initiate processing.")
        self.dockWidget.setWidget(self.inputs)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.dockWidget)

    def createStatusBar(self):
        self.statsig.connect(self.statusBar().showMessage,
                             type=QtCore.Qt.QueuedConnection)
        self.statsig.emit("Ready")

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

    def setTimeout(self):
        a, _ = QtWidgets.QInputDialog.getInt(
            self, "Set Timeout", "Timeout seconds:", self.timeout)
        if _:
            self.timeout = a

    def setUTMZone(self):
        a, _ = QtWidgets.QInputDialog.getText(self,
                                              "Set UTM zone",
                                              "UTM Zone: "+self.UTMZone +
                                              "(Zone number plus N or S"
                                              "designation)")
        if _:
            self.UTMZone = a

    def setCombineSEGD(self):
        a, _ = QtWidgets.QInputDialog.getInt(self,
                                             "Set number of traces to combine",
                                             "Combined number:",
                                             minValue=1, maxValue=120)
        if _:
            self.combine = a
        else:
            self.combine = 1

    def setupProcessing(self):
        '''
           Read inputs and start processing (Run)
        '''
        mydir = self.inputs.dirCombo.currentText()
        mylst = self.inputs.lstCombo.currentText()
        if not mydir or not mylst:
            mess = QtWidgets.QMessageBox()
            mess.setText(
                "A RAW file list and processing directory must be set!")
            mess.exec_()
            return False
        self.statsig.emit(
            "Setting up processing of list {0} at {1}".format(mylst, mydir))
        self.fio, self.cmds, self.info = init_fio(
            mylst, mydir, utm=self.UTMZone, combine=self.combine,
            main_window=self)
        fams = self.cmds.keys()
        self.statsig.emit("Processing families {0}".format(" ".join(fams)))
        return True


#
# Mix-ins
#


def get_len(f):
    '''
        Read the number of lines in a text file.
        Input:
            f -> file name
        Output:
            num_lines -> number of lines in file
    '''
    num_lines = sum(1 for line in open(f))

    return num_lines


def init_fio(f, d, utm=None, combine=None, main_window=None):
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
    fio = pforma_io.FormaIO(infile=f, outdir=d, main_window=main_window)
    if utm:
        fio.set_utm(utm)
    if combine:
        fio.set_combine(combine)
    if cpu_count(logical=False) > 3:
        fio.set_nmini(cpu_count(logical=True) + 1)
    else:
        fio.set_nmini(cpu_count(logical=True))

    fio.initialize_ph5()

    try:
        fio.open()
    except pforma_io.FormaIOError as e:
        LOGGER.error("{0}: {1}".format(e.errno, e.message))

    try:
        fio.read()
    except pforma_io.FormaIOError as e:
        LOGGER.error("{0}: {1}".format(e.errno, e.message))

    try:
        fio.readDB()
    except pforma_io.FormaIOError as e:
        LOGGER.error("{0}: {1}".format(e.errno, e.message))
        sys.exit(-1)

    fio.resolveDB()
    cmds, lsts, i = fio.run(runit=False)
    return fio, cmds, lsts


def startapp():
    app = QtWidgets.QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    startapp()
