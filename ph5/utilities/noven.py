#!/usr/bin/env pnpython3
#
# PH5 meta-data initializer GUI
#
# Steve Azevedo, refactor Feb 2015
#

import json
import os
import sys
import logging
from os.path import expanduser
from ph5.utilities import novenqc, novenkef


PROG_VERSION = '2021.84'
LOGGER = logging.getLogger(__name__)

try:
    from PySide2 import QtWidgets, QtCore
except Exception:
    msg = ("\n\nNo module named PySide2. "
           "Please environment_gui.yml to install conda environment"
           "PySide2 is needed for noven.")
    raise ImportError(msg)

RECEIVER_CFG_S = '{\n'\
    '   "description_s": {\n'\
    '      "required": "False",\n'\
    '      "type": "string1024",\n'\
    '      "help": "Station comments."\n'\
    '   },\n'\
    '   "pickup_time/ascii_s": {\n'\
    '      "required": "True",\n'\
    '      "type": "string32",\n'\
    '      "help": "Time:YYYY:JJJ:HH:MM:SS.sss'\
    'or YYYY-MM-DDTHH:MM:SS.ssssss.",\n'\
    '      "re": "(\\\\d\\\\d\\\\d\\\\d:\\\\d{1,3}:\\\\d{1,2}:\\\\d{1,2}:\\\\'\
    'd{1,2}(\\\\.\\\\d{1,3})?)|(\\\\d\\\\d\\\\d\\\\d-\\\\d{1,2}-\\\\d{1,2}'\
    'T\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2}\\\\.\\\\d{1,6})|(\\\\d\\\\d\\\\d\\\\'\
    'd:\\\\d{1,3}:\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2})"\n'\
    '   },\n'\
    '   "id_s": {\n'\
    '      "required": "True",\n'\
    '      "type": "int15",\n'\
    '      "help": "Valid SEG-Y station number."\n'\
    '   },\n'\
    '   "deploy_time/ascii_s": {\n'\
    '      "required": "True",\n'\
    '      "type": "string32",\n'\
    '      "help": "Time: YYYY:JJJ:HH:MM:SS.sss'\
    'or YYYY-MM-DDTHH:MM:SS.ssssss.",\n'\
    '      "re": "(\\\\d\\\\d\\\\d\\\\d:\\\\d{1,3}:\\\\d{1,2}:\\\\d{1,2}:\\\\'\
    'd{1,2}(\\\\.\\\\d{1,3})?)|(\\\\d\\\\d\\\\d\\\\d-\\\\d{1,2}-\\\\d{1,2}'\
    'T\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2}\\\\.\\\\d{1,6})|(\\\\d\\\\d\\\\d\\\\d:'\
    '\\\\d{1,3}:\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2})"\n'\
    '   },\n'\
    '   "location/X/value_d": {\n'\
    '      "required": "False",\n'\
    '      "type": "float64",\n'\
    '      "help": "Longitude in degrees."\n'\
    '   },\n'\
    '   "location/Y/value_d": {\n'\
    '      "required": "False",\n'\
    '      "type": "float64",\n'\
    '      "help": "Latitude in degrees."\n'\
    '   },\n'\
    '   "location/Z/value_d": {\n'\
    '      "required": "False",\n'\
    '      "type": "float64",\n'\
    '      "help": "Elevation in meters."\n'\
    '   },'\
    '   "Array": {\n'\
    '      "required": "True",\n'\
    '      "type": "int32",\n'\
    '      "help": "Array or line number."\n'\
    '   },\n'\
    '   "Deploy/Pickup" : {\n'\
    '      "required": "False",\n'\
    '      "type": "string1",\n'\
    '      "help": "Deploy \'D\' or Pickup \'P\' notes.",\n'\
    '      "re": "D|P"\n'\
    '   },\n'\
    '   "channel_number_i": {\n'\
    '      "required": "True",\n'\
    '      "type": "int15",\n'\
    '      "help": "Component, Possibly follows:'\
    '1 -> Z, 2 -> N/S, 3 -> E/W etc",\n'\
    '      "range": "1-6"\n'\
    '   },\n'\
    '   "das/serial_number_s": {\n'\
    '      "required": "True",\n'\
    '      "type": "string32",\n'\
    '      "help": "Full serial number of the data logger,'\
    'texans are 5 digits."\n'\
    '   },\n'\
    '   "das/model_s": {\n'\
    '      "required": "False",\n'\
    '      "type": "string32",\n'\
    '      "help": "The DAS model, rt-130, texan etc."\n'\
    '   },\n'\
    '   "das/manufacturer_s": {\n'\
    '      "required": "False",\n'\
    '      "type": "string32",\n'\
    '      "help": "The Das manufacturer, RefTek, kelco etc."\n'\
    '   },\n'\
    '   "sensor/serial_number_s": {\n'\
    '      "required": "False",\n'\
    '      "type": "string64",\n'\
    '      "help": "Full serial number of the sensor."\n'\
    '   },\n'\
    '   "sensor/model_s": {\n'\
    '      "required": "False",\n'\
    '      "type": "string64",\n'\
    '      "help": "Sensor model."\n'\
    '   },\n'\
    '   "sensor/manufacturer_s": {\n'\
    '      "required": "False",\n'\
    '      "type": "string64",\n'\
    '      "help": "Sensor manufacturer."\n'\
    '   },\n'\
    '   "SEED_Channel": {\n'\
    '      "required": "False",\n'\
    '      "type": "string3",\n'\
    '      "help": "SEED ch as described in Appendix A of SEED manual."\n'\
    '   },\n'\
    '   "seed_location_code_s": {\n'\
    '      "required": "False",\n'\
    '      "type": "string2",\n'\
    '      "help": "SEED loccode described chapter 8 of the SEED manual."\n'\
    '   },\n'\
    '   "seed_station_name_s": {\n'\
    '      "required": "False",\n'\
    '      "type": "string5",\n'\
    '      "help": "SEED ch name described in ch 8 of the SEED manual."\n'\
    '   },\n'\
    '   "sample_rate_i": {\n'\
    '      "required": "False",\n'\
    '      "type": "int16",\n'\
    '      "help": "The sample rate in samples per second as an integer."\n'\
    '   },\n'\
    '   "sample_rate_multiplier_i": {\n'\
    '      "required": "False",\n'\
    '      "type": "int16",\n'\
    '      "help": "Usually 1 unless the sample rate is less than 1."\n'\
    '   }\n'\
    '}'


EVENT_CFG_S = '{\n'\
   '"location/X/value_d": {\n'\
   '  "required": "True",\n'\
   '  "type": "float64",\n'\
   '  "help": "Longitude in degrees."\n'\
   '},\n'\
   '"description_s": {\n'\
   '  "required": "False",\n'\
   '   "type": "string1024",\n'\
   '  "help": "Comment."\n'\
   '},\n'\
   '"size/units_s": {\n'\
   '  "required": "False",\n'\
   '  "type": "string32",\n'\
   '   "help": "kg, lbs, or magnitude."\n'\
   '},\n'\
   '"size/value_d": {\n'\
   '  "required": "False",\n'\
   '  "type": "float64",\n'\
   '  "help": "Size of shot, kg, lbs, magnitude."\n'\
   '},\n'\
   '"location/Y/value_d": {\n'\
   '  "required": "True",\n'\
   '   "type": "float64",\n'\
   '  "help": "Latitude in degrees."\n'\
   '},\n'\
   '"id_s": {\n'\
   '   "required": "True",\n'\
   '  "type": "int31",\n'\
   '  "help": "Valid SEG-Y shot number."\n'\
   '},\n'\
   '"location/Z/value_d": {\n'\
   '  "required": "False",\n'\
   '  "type": "float64",\n'\
   '  "help": "Elevation in meters."\n'\
   '},\n'\
   '"depth/value_d": {\n'\
   '  "required": "False",\n'\
   '  "type": "float64",\n'\
   '   "help": "Depth of shot or event below surface in meters."\n'\
   '},\n'\
   '"Array": {\n'\
   '   "required": "False",\n'\
   '  "type": "int32",\n'\
   '   "help": "The shot line or array number."\n'\
   '},\n'\
   '"time/ascii_s": {\n'\
   '  "required": "True",\n'\
   '  "type": "string32",\n'\
   '  "help": "Time: YYYY:JJJ:HH:MM:SS.sss or YYYY-MM-DDTHH:MM:SS.ssssss.",\n'\
   '  "re": "(\\\\d\\\\d\\\\d\\\\d:\\\\d{1,3}:\\\\d{1,2}:\\\\d{1,2}:\\\\'\
   'd{1,2}(\\\\.\\\\d{1,3})?)|(\\\\d\\\\d\\\\d\\\\d-\\\\d{1,2}-\\\\d{1,2}'\
   'T\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2}\\\\.\\\\d{1,6})|(\\\\d\\\\d\\\\d\\\\d:'\
   '\\\\d{1,3}:\\\\d{1,2}:\\\\d{1,2}:\\\\d{1,2})"\n'\
   '}\n'\
   '}'


#
SEPMAP = {'tab': None, 'comma': ',',
          'semi-colon': ';', 'colon': ':', 'space': None}


class MyWorker(QtCore.QThread):
    def __init__(self, command, table=None, names=None,
                 cols=None, sep=None, outfile=None):
        super(MyWorker, self).__init__()
        self.command = command
        self.table = table
        self.names = names
        self.cols = cols
        self.sep = sep
        self.outfile = outfile
        self.working = True

    def run(self):
        if self.command == 'qc_receivers':
            while self.working:
                self.working = novenqc.qc_receivers(self.table,
                                                    self.names,
                                                    self.cols,
                                                    self.sep)
        elif self.command == 'qc_shots':
            while self.working:
                self.working = novenqc.qc_shots(self.table,
                                                self.names,
                                                self.cols,
                                                self.sep)
        elif self.command == 'qc_map':
            while self.working:
                self.working = novenqc.qc_map(self.outfile)
        else:
            print "Fail"


class MyQComboBox(QtWidgets.QComboBox):
    def __init__(self, values=[]):
        super(MyQComboBox, self).__init__()
        if values:
            self.addItems(values)


class MyQTableWidget(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super(MyQTableWidget, self).__init__(parent)


class MyMessageBox(QtWidgets.QMessageBox):
    '''
       Make QMesageBox expand properly
    '''

    def __init__(self, parent=None):
        QtWidgets.QMessageBox.__init__(self, parent=parent)
        self.setSizeGripEnabled(True)

    def event(self, e):
        result = QtWidgets.QMessageBox.event(self, e)

        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)

        textEdit = self.findChild(QtWidgets.QTextEdit)
        if textEdit is not None:
            textEdit.setMinimumHeight(0)
            textEdit.setMaximumHeight(16777215)
            textEdit.setMinimumWidth(0)
            textEdit.setMaximumWidth(16777215)
            textEdit.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)

        return result


class ErrorsDialog(QtWidgets.QMainWindow):
    '''
       Dialog for displaying problems with input file
    '''

    def __init__(self, errors, parent=None):
        super(ErrorsDialog, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        saveAction = QtWidgets.QAction('Save', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.setStatusTip('Save current file')
        saveAction.triggered.connect(self.saveFile)

        closeAction = QtWidgets.QAction('Close', self)
        closeAction.setShortcut('Ctrl+Q')
        closeAction.setStatusTip('Close error display')
        closeAction.triggered.connect(self.close)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(saveAction)
        fileMenu.addAction(closeAction)

        self.text = QtWidgets.QTextEdit(self)

        self.setCentralWidget(self.text)
        self.setGeometry(300, 300, 800, 300)
        self.setWindowTitle('Errors')
        self.show()
        self.setIt(errors)

    def setIt(self, text):
        self.text.clear()
        text = '\n'.join(text)
        self.text.setText(text)

    def saveFile(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save File', os.getenv('HOME'))
        filename = str(filename)
        if not filename:
            return
        f = open(filename, 'w')
        filedata = self.text.toPlainText()
        f.write(filedata)
        f.close()


class SetupDialog(QtWidgets.QDialog):
    '''
       Main configuration dialog
    '''
    changed = QtCore.Signal()

    def __init__(self, settings, parent=None):
        super(SetupDialog, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        inputFileTypeLabel = QtWidgets.QLabel("Input Type")
        self.inputFileType = QtWidgets.QComboBox()
        inputFileTypeLabel.setBuddy(self.inputFileType)
        self.inputFileType.addItems(['receiver', 'event'])
        self.inputFileType.setCurrentIndex(
            self.inputFileType.findText(settings['inFormat']))

        outfileFormatLabel = QtWidgets.QLabel("Output Format")
        self.outfileFormat = QtWidgets.QComboBox()
        outfileFormatLabel.setBuddy(self.outfileFormat)
        self.outfileFormat.addItems(["kef", "kef"])
        self.outfileFormat.setCurrentIndex(
            self.outfileFormat.findText(settings['outFormat']))

        fieldSeparatorLabel = QtWidgets.QLabel("Column Separator")
        self.fieldSeparator = QtWidgets.QComboBox()
        fieldSeparatorLabel.setBuddy(self.fieldSeparator)
        self.fieldSeparator.addItems(
            ["comma", "semi-colon", "colon", "tab", "space"])
        self.fieldSeparator.setCurrentIndex(
            self.fieldSeparator.findText(settings['colSep']))

        skipLinesLabel = QtWidgets.QLabel("Skip Lines")
        self.skipLines = QtWidgets.QSpinBox()
        skipLinesLabel.setBuddy(self.skipLines)
        self.skipLines.setRange(0, 12)
        self.skipLines.setValue(settings['linesSkip'])

        viewLinesLabel = QtWidgets.QLabel("View Lines")
        self.viewLines = QtWidgets.QSpinBox()
        viewLinesLabel.setBuddy(self.viewLines)
        self.viewLines.setRange(1, 60)
        self.viewLines.setValue(settings['linesView'])

        self.settings = settings

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Apply |
            QtWidgets.QDialogButtonBox.Close)

        grid = QtWidgets.QGridLayout()
        grid.addWidget(inputFileTypeLabel, 0, 0)
        grid.addWidget(self.inputFileType, 0, 1)
        grid.addWidget(outfileFormatLabel, 1, 0)
        grid.addWidget(self.outfileFormat, 1, 1)
        grid.addWidget(fieldSeparatorLabel, 2, 0)
        grid.addWidget(self.fieldSeparator, 2, 1)
        grid.addWidget(skipLinesLabel, 3, 0)
        grid.addWidget(self.skipLines, 3, 1)
        grid.addWidget(viewLinesLabel, 4, 0)
        grid.addWidget(self.viewLines, 4, 1)

        grid.addWidget(buttonBox, 5, 0, 2, -1)
        self.setLayout(grid)

        self.connect(buttonBox.button(QtWidgets.QDialogButtonBox.Apply),
                     QtCore.SIGNAL("clicked ()"), self.apply)

        self.connect(buttonBox, QtCore.SIGNAL("rejected ()"),
                     self, QtCore.SLOT("reject ()"))

        self.setWindowTitle("Configure")

    def apply(self):
        self.settings['linesView'] = int(self.viewLines.value())
        self.settings['colSep'] = str(self.fieldSeparator.currentText())
        self.settings['outFormat'] = str(self.outfileFormat.currentText())
        self.settings['linesSkip'] = int(self.skipLines.value())
        self.settings['inFormat'] = str(self.inputFileType.currentText())
        self.changed.emit()

    def rejected(self):
        LOGGER.info("Reject")


class Novitiate(QtWidgets.QMainWindow):
    '''
       Program parent
    '''

    def __init__(self, parent=None):
        super(Novitiate, self).__init__(parent)

        self.settings = dict(inFormat='receiver', outFormat='kef',
                             colSep='comma', linesSkip=0, linesView=3)
        self.setWindowTitle('Noven Version: ' + PROG_VERSION)

        self.readFileLines = []

        self.comboBoxes = []
        self.last_maxY = None

        self.TOP = {}

        main()
        #
        # Setup menus
        #
        openin = QtWidgets.QAction('Open...', self)
        openin.setShortcut('Ctrl+O')
        openin.setStatusTip('Open input file.')
        self.connect(openin, QtCore.SIGNAL('triggered ()'), self.openInfile)

        checkin = QtWidgets.QAction('Check input', self)
        checkin.setShortcut('Ctrl+c')
        checkin.setStatusTip('Check validity of input csv.')
        self.connect(checkin, QtCore.SIGNAL('triggered ()'), self.checkInFile)

        mapin = QtWidgets.QAction('Map locations...', self)
        mapin.setShortcut('Ctrl+m')
        mapin.setStatusTip('Produce a map of locations.')
        self.connect(mapin, QtCore.SIGNAL('triggered ()'), self.mapInFile)

        # menuBar doesn't accept 'Configuration' or 'Setting'
        config = QtWidgets.QAction('Change Parameters...', self)
        config.setShortcut('Ctrl+C')
        config.setStatusTip('Set input file field separator etc.')
        self.connect(config, QtCore.SIGNAL('triggered ()'), self.configure)

        saveas = QtWidgets.QAction('Save As...', self)
        saveas.setShortcut('Ctrl+S')
        saveas.setStatusTip('Save output (kef) file.')
        self.connect(saveas, QtCore.SIGNAL('triggered ()'), self.saveAs)

        exit = QtWidgets.QAction('Exit', self)
        exit.setShortcut('Ctrl+Q')
        exit.setStatusTip('Exit application')
        self.connect(exit, QtCore.SIGNAL(
            'triggered()'), QtCore.SLOT('close()'))

        help = QtWidgets.QAction('Help', self)
        help.setShortcut('Ctrl+h')
        help.setStatusTip('Get help on column names.')
        self.connect(help, QtCore.SIGNAL('triggered()'), self.cbhelp)

        menubar = self.menuBar()
        file = menubar.addMenu('&File')
        file.addAction(openin)
        file.addAction(checkin)
        file.addAction(mapin)
        file.addAction(saveas)
        file.addAction(config)
        file.addAction(help)
        if not parent:
            file.addAction(exit)

        #
        # Table
        #
        self.table = MyQTableWidget()
        self.setCentralWidget(self.table)

        self.status = self.statusBar()
        self.status.setSizeGripEnabled(False)

        self.setGeometry(300, 300, 1200, 300)

    def configure(self):
        self.settingsDialog = SetupDialog(self.settings, self)
        self.settingsDialog.changed.connect(self.refreshTable)
        self.settingsDialog.show()

    def refreshTable(self):
        self.TOP = {}
        key = self.settings['colSep']
        sep = SEPMAP[str(key)]

        maxY = 0
        LINES = []
        for line in self.readFileLines:
            line = line.strip()
            flds = line.split(sep)
            if len(flds) > maxY:
                maxY = len(flds)
            LINES.append(flds)

        maxX = self.settings['linesView'] + 1
        if self.last_maxY != maxY:
            self.comboBoxes = []
            self.last_maxY = maxY

        self.table.clear()

        self.table.setColumnCount(maxY)
        self.table.setRowCount(maxX)
        hh = self.table.horizontalHeader()
        hh.hide()
        vh = self.table.verticalHeader()
        vh.hide()

        try:
            if self.table.cols:
                y = 0
                for t in self.table.cols:
                    item = QtWidgets.QTableWidgetItem(t)
                    self.table.setItem(0, y, item)
                    y += 1

        except AttributeError:
            if self.settings['inFormat'] == 'receiver':
                cvalues = RECEIVER_CFG.keys()
            else:
                cvalues = EVENT_CFG.keys()

            cvalues.sort()
            cvalues.insert(0, u'Ignore')
            for y in range(maxY):
                try:
                    ci = self.comboBoxes[y].currentIndex()
                except Exception:
                    ci = None

                cb = MyQComboBox(values=cvalues)
                if ci:
                    try:
                        cb.setCurrentIndex(ci)
                    except BaseException:
                        cb.setCurrentIndex(0)
                else:
                    cb.setCurrentIndex(0)

                if len(self.comboBoxes) < maxY:
                    self.comboBoxes.append(cb)
                else:
                    self.comboBoxes[y] = cb

                cb.highlighted.connect(self.huh)

                self.table.setCellWidget(0, y, cb)

        s = self.settings['linesSkip']
        for x in range(maxX):
            try:
                FLDS = LINES[x + s]
            except IndexError:
                continue

            for y in range(maxY):
                try:
                    text = "{0}".format(FLDS[y])
                except IndexError:
                    continue

                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignRight |
                                      QtCore.Qt.AlignVCenter)

                self.table.setItem(x + 1, y, item)

        self.table.resizeColumnsToContents()
        self.table.setAcceptDrops(True)
        self.setWindowTitle(self.settings['inFormat'])

    # Slot for QCombobox highlight signal
    def huh(self, x):
        if x == 0:
            return
        x -= 1
        if self.settings['inFormat'] == 'receiver':
            cols = RECEIVER_CFG
        else:
            cols = EVENT_CFG

        keys = cols.keys()
        keys = sorted(map(str, keys))
        help = cols[keys[x]]['help']
        self.status.showMessage(help)

    def cbhelp(self):
        if self.settings['inFormat'] == 'receiver':
            cols = RECEIVER_CFG
        else:
            cols = EVENT_CFG

        help = "{0:<25}{1}".format("Ignore:", "Ignore this entire column.\n\n")
        keys = sorted(cols.keys())
        for k in keys:
            help += "{0:<25}{1}\n\n".format(k +
                                            ':', str(cols[k]['help']).strip())

        mb = MyMessageBox(parent=None)
        mb.setFont(QtWidgets.QFont('Courier', 10, QtWidgets.QFont.Bold))
        mb.setWindowTitle('Socorro')
        mb.setText(help)
        mb.setModal(False)
        mb.open()
        mb.exec_()

    def qcDone(self):
        self.status.showMessage("Done")
        if novenqc.ERR is not None and len(novenqc.ERR) != 0:
            self.errorsDialog = ErrorsDialog(novenqc.ERR, self)
            self.errorsDialog.show()
        else:
            QtWidgets.QMessageBox.information(
                self, "Information", "Nothing funky found!")

        self.TOP = novenqc.TOP

    def openInfile(self):
        filters = 'CSV files: (*.csv);; Text files: (*.txt);; All: (*)'
        selected = 'CSV files: (*.csv)'
        inFileName, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open input file", os.getcwd(), filters, selected)
        if os.path.exists(inFileName):
            fh = open(inFileName, 'U')
            self.readFileLines = fh.readlines()
            fh.close()
            self.table.clear()
            self.refreshTable()
        else:
            self.readFileLines = None

    def mapInFile(self):
        if self.TOP == {}:
            QtWidgets.QMessageBox.information(
                self, "Can't continue.", "Must check inputs first.")
            return

        outFileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Output KML file name.', os.getcwd(), filter='*.kml')
        if outFileName:
            if outFileName[-4:] != '.kml':
                outFileName += '.kml'

            self.status.showMessage("Working on kml...")
            worker = MyWorker('qc_map', outfile=outFileName)
            worker.start()
            worker.wait()

    def checkInFile(self):
        if not self.readFileLines:
            QtWidgets.QMessageBox.information(
                self, "Can't continue.",
                "Must open and configure csv file first.")
            return
        names = map(lambda x: str(x.currentText()), self.comboBoxes)
        tmp = []
        for n in names:
            if n in tmp:
                QtWidgets.QMessageBox.information(
                    self, "Can't continue.",
                    "Duplicated column: {0}".format(n))
                return
            if n != 'Ignore':
                tmp.append(n)
        if self.settings['inFormat'] == 'receiver':
            worker = MyWorker('qc_receivers',
                              self.readFileLines[self.settings['linesSkip']:],
                              names,
                              RECEIVER_CFG,
                              sep=SEPMAP[self.settings['colSep']])
        elif self.settings['inFormat'] == 'event':
            worker = MyWorker('qc_shots',
                              self.readFileLines[self.settings['linesSkip']:],
                              names,
                              EVENT_CFG,
                              sep=SEPMAP[self.settings['colSep']])
        self.status.showMessage("Working on QC...")
        worker.finished.connect(self.qcDone)
        worker.start()
        worker.wait()

    def saveAs(self):
        if self.TOP == {}:
            QtWidgets.QMessageBox.information(
                self, "Can't continue.",
                "Must open csv and check inputs first.")
            return

        saveFileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save output as', os.getcwd(), filter="*.kef")
        novenkef.write_kef(self.TOP, saveFileName)


#
# Mix-ins
#


def read_cfg(filename):
    fh = open(filename)
    ret = json.load(fh)
    fh.close()

    return ret


def main():
    return


def startapp():
    global RECEIVER_CFG, EVENT_CFG
    home = expanduser("~")
    if not os.path.isfile(
            os.path.join(home, '.PH5', 'Receiver.cfg')) or not os.path.isfile(
            os.path.join(home, '.PH5', 'Event.cfg')):
        create_config = raw_input(
            "It appears your home directory doesn't contain config files for"
            " noven.\nIt is advised you have config files created. "
            "Do you want config files to be created for you(y/n)?:")
        if create_config.upper() == "Y":
            print "Installing to: " + str(os.path.join(home, '.PH5'))
            if not os.path.exists(os.path.join(home, '.PH5')):
                os.makedirs(os.path.join(home, '.PH5'))
            f = open(os.path.join(home, '.PH5', 'Receiver.cfg'), 'w')
            f.write(str(RECEIVER_CFG_S))
            f.close()
            f = open(os.path.join(home, '.PH5', 'Event.cfg'), 'w')
            f.write(str(EVENT_CFG_S))
            f.close()
            RECEIVER_CFG = json.loads(RECEIVER_CFG_S)
            EVENT_CFG = json.loads(EVENT_CFG_S)
    else:
        RECEIVER_CFG = read_cfg(os.path.join(home, '.PH5', 'Receiver.cfg'))
        EVENT_CFG = read_cfg(os.path.join(home, '.PH5', 'Event.cfg'))

    app = QtWidgets.QApplication(sys.argv)
    form = Novitiate()
    form.show()
    app.exec_()


if __name__ == '__main__':
    startapp()
