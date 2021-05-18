#!/usr/bin/env pnpython3
#
# KefEdit
#
# Credit: Lan Dam
#
# Updated Feb 2018
import sys
import logging
import os
import time
import numpy
import os.path as path
from tempfile import mkdtemp
from copy import deepcopy
from operator import itemgetter
from ph5.core import kefutility
LOGGER = logging.getLogger(__name__)
try:
    from PySide2 import QtWidgets, QtCore, QtGui
except Exception:
    msg = ("\n\nNo module named PySide2. "
           "Please environment_gui.yml to install conda environment"
           "PySide2 is needed for kefedit.")
    raise ImportError(msg)
# added on 20180226 so that temp.kef will always be available
keftmpfile = path.join(mkdtemp(), 'temp.kef')
PROG_VERSION = 2021.84
EXPL = {}

# CLASS ####################
# Author: Lan
# Updated: 201702
# CLASS: KefEdit


class KefEdit(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setWindowTitle("KEF Editor Ver. %s" % PROG_VERSION)

        self.kefFilename = None
        self.path_tabs = []  # to keep the tabwidget to delete
        self.ph5api = None  # to resue when open tables from the current
        # opened ph5
        self.notsave = True  # to identify if the open data are save

        self.initMenu()
        mainFrame = QtWidgets.QFrame(self)
        self.setCentralWidget(mainFrame)
        mainLayout = QtWidgets.QVBoxLayout()
        mainFrame.setLayout(mainLayout)

        statusLayout = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(statusLayout)
        statusLayout.addWidget(QtWidgets.QLabel("Color keys:"))

        updateCol = QtWidgets.QLabel("UPDATE")
        updateCol.installEventFilter(self)
        EXPL[updateCol] = "Color for Changed Row"
        updateCol.setAlignment(QtCore.Qt.AlignHCenter)
        updateCol.setFixedWidth(85)
        updateCol.setStyleSheet(" background-color: %s" % updateColName)
        statusLayout.addWidget(updateCol)

        deleteCol = QtWidgets.QLabel("DELETE")
        deleteCol.installEventFilter(self)
        EXPL[deleteCol] = "Color for Deleted Row"
        deleteCol.setAlignment(QtCore.Qt.AlignHCenter)
        deleteCol.setFixedWidth(85)
        deleteCol.setStyleSheet(" background-color: %s" % deleteColName)
        statusLayout.addWidget(deleteCol)

        statusLayout.addStretch(1)

        self.path_tabWidget = QtWidgets.QTabWidget()  # each tab keep a table
        mainLayout.addWidget(self.path_tabWidget)

        self.statusBar = self.statusBar()

        self.setGeometry(0, 0, 1200, 900)
        self.showMaximized()

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.Enter:
            if object not in EXPL.keys():
                return False
            P = object.pos()
            QtWidgets.QToolTip.showText(
                self.mapToGlobal(QtCore.QPoint(P.x(), P.y() + 20)),
                EXPL[object])
            return True
        return False

    def initMenu(self):
        # HELP MENU  #################
        manualAction = QtWidgets.QAction('Manual', self)
        manualAction.setShortcut('F1')
        manualAction.triggered.connect(self.OnManual)

        whatsnewAction = QtWidgets.QAction("What's new?", self)
        whatsnewAction.setShortcut('F1')
        whatsnewAction.triggered.connect(self.OnWhatsnew)
        # FILE MENU  #################
        openKefAction = QtWidgets.QAction('Open Kef File', self)
        openKefAction.triggered.connect(self.OnOpenKef)

        openPH5Action = QtWidgets.QAction('Open PH5 File', self)
        openPH5Action.triggered.connect(self.OnOpenPH5)

        self.openTableAction = QtWidgets.QAction(
            'Open table(s) in the current PH5 File', self)
        self.openTableAction.triggered.connect(self.OnOpenCurrPH5)
        self.openTableAction.setEnabled(False)
        # ---------------- Save ----------------
        self.saveKefAction = QtWidgets.QAction('Save as Kef File', self)
        self.saveKefAction.triggered.connect(self.OnSaveKef)
        self.saveKefAction.setEnabled(False)

        self.savePH5Action = QtWidgets.QAction('Save as PH5 File', self)
        self.savePH5Action.triggered.connect(self.OnSavePH5)
        self.savePH5Action.setEnabled(False)

        self.updatePH5Action = QtWidgets.QAction(
            'Update the Current PH5 File', self)
        self.updatePH5Action.triggered.connect(self.OnUpdatePH5)
        self.updatePH5Action.setEnabled(False)

        self.saveCSVAction = QtWidgets.QAction('Save as CSV File', self)
        self.saveCSVAction.triggered.connect(self.OnSaveCSV)
        self.saveCSVAction.setEnabled(False)
        # ---------------- exit ----------------
        exitAction = QtWidgets.QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.closeEvent)

        # ADDING MENU #####################
        menubar = QtWidgets.QMenuBar()
        self.setMenuBar(menubar)

        fileMenu = menubar.addMenu('&File')

        fileMenu.addAction(openKefAction)
        fileMenu.addAction(openPH5Action)
        fileMenu.addAction(self.openTableAction)

        fileMenu.addAction(self.saveKefAction)
        fileMenu.addAction(self.savePH5Action)
        fileMenu.addAction(self.updatePH5Action)
        fileMenu.addAction(self.saveCSVAction)

        fileMenu.addAction(exitAction)

        fileMenu.insertSeparator(self.saveKefAction)
        fileMenu.insertSeparator(exitAction)

        helpMenu = menubar.addMenu('&Help')
        helpMenu.addAction(manualAction)
        helpMenu.addAction(whatsnewAction)

    ###############################
    # def closeEvent
    # author: Lan Dam
    # updated: 201704
    # * check if the changes haven't been saved, give user a chance to change
    # mind
    # * close the app when the widget is closed (to close the opened PH5)
    def closeEvent(self, evt=None):
        for tab in self.path_tabs:
            if self.notsave is True and \
                    (
                        tab.updateList != [] or tab.deleteList != [] or
                        tab.addDataList != []):
                msg = "There are still things you have worked on but haven't" \
                      "saved." + \
                      "\nClick on Cancel to cancel closing. " + \
                      "\nClick on Close to close KefEdit."
                result = QtWidgets.QMessageBox.question(
                    self, "Are you sure?", msg,
                    QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Close)
                if result == QtWidgets.QMessageBox.Cancel:
                    if evt.__class__.__name__ != 'bool':
                        evt.ignore()
                    return

        QtCore.QCoreApplication.instance().quit()
        sys.exit(application.exec_())

    def OnManual(self):
        self.manualWin = ManWindow("manual")

    def OnWhatsnew(self):
        self.whatsnewWin = ManWindow("whatsnew")

    ###############################
    # def OnOpenKef
    # author: Lan Dam
    # updated: 201702
    # * open Kef file, read data into self.dataTabel, keySets then into
    # labelSets
    # (each set represent for data in a path)
    # * then call self.setData() to set the given data in display
    def OnOpenKef(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            directory="/home/", filter="Kef Files(*.kef)")
        self.kefFilename = filename
        if not filename:
            return

        self.path2file = os.path.dirname(str(filename))
        self.filename = os.path.basename(str(filename))

        if self.ph5api is not None:
            self.ph5api.close()
            del self.ph5api
            self.ph5api = None
        self.openTableAction.setEnabled(False)
        self.updatePH5Action.setEnabled(False)
        self.dataTable, self.labelSets, self.totalLines, self.types =\
            kefutility.Kef2TableData(
                self.statusBar, filename)
        if self.totalLines > 10000:
            self.statusBar.showMessage(
                "Please be patient while displaying...")
        self.setData()
        self.notsave = True

    ###############################
    # def OnOpenPH5
    # author: Lan Dam
    # updated: 201703
    # Open PH5 file
    # * use kefutility.GetPrePH5Info give user list of tables and info to
    # select
    # to get info from kefutility.PH5toDataTable
    # * call SelectTableDialog for user to select which table(s) to display
    # * in SelectTableDialog, the following tasks will be perfomed:
    # [Read data into self.dataTable, keySets into labelSets
    # (each set represent for data in a path)
    # then call self.setData() to set the given data in display]
    def OnOpenPH5(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            directory="/home/", filter="PH5 Files(*.ph5)")
        if not filename:
            return

        self.path2file = os.path.dirname(str(filename))
        self.filename = os.path.basename(str(filename))
        if self.ph5api is not None:
            self.ph5api.close()
            del self.ph5api

        self.ph5api, availTables, arrays, shotLines, offsets, das =\
            kefutility.GetPrePH5Info(self.filename, self.path2file)

        self.selTableDlg = SelectTableDialog(self, availTables, arrays,
                                             shotLines, offsets, das)
        self.kefFilename = None

    ###############################
    # def OnOpenCurrPH5
    # author: Lan Dam
    # updated: 201704
    # Open other tables on the current opened PH5 File
    # * similar to onOpenPH5() but skip the part of opening file to
    # getPrePH5Info
    # * reshow SelTableDlg for user to select which table(s) to display
    # * in SelectTableDialog, the following tasks will be perfomed:
    # [Read data into self.dataTable, keySets into labelSets
    #  (each set represent for data in a path)
    #  then call self.setData() to set the given data in display]
    def OnOpenCurrPH5(self):
        self.selTableDlg.show()
        self.selTableDlg.move(70,
                              70)  # to move to the same position when
        # create new

    ###############################
    # def OnSaveKef
    # author: Lan Dam
    # updated: 201704
    # save current table(s) into a kef file
    # * user choose filename
    # * call _saveKeffile() to save kef format into the filename
    # * inform when successfully save and ask to close KefEdit
    def OnSaveKef(self):
        # print "onSaveKef"
        if not self._checkAddTableView():
            return

        # created suggestedFileName to recommend to user
        if 'kef' in self.filename:
            ss = self.filename.split(".")
            ss[0] += "_editted"
            suggestedFileName = ".".join(ss)
        else:
            arg = self.arg
            if self.tableType == 'Array_t':
                arg = "{0:03d}".format(int(arg))
            if arg is not None:
                suggestedFileName = self.tableType + "_" + arg
            else:
                suggestedFileName = self.tableType

        suggestedFileName = self.path2file + "/" + suggestedFileName +\
            '.kef'

        savefilename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save File", suggestedFileName, filter="Kef File (*.kef)")

        if not savefilename:
            return

        START = time.time()
        # start kef file with the version of KefEdit
        currText = "#\n#\t%s\tKefEdit version: %s" % (
            time.ctime(time.time()), PROG_VERSION)

        result = self._saveKeffile(savefilename, currText)
        if result is False:
            return
        END = time.time()
        self.statusBar.showMessage(
            "Successfully saving Kef file. Total processing time %s seconds"
            % (END - START))

        msg = "File %s has been saved successfully." \
              "\nDo you want to close KEF Editor?" % savefilename
        result = QtWidgets.QMessageBox.question(
            self, "Successfully Save File", msg,
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        self.notsave = False  # after saving, reset notsave

        if result == QtWidgets.QMessageBox.Yes:
            if self.ph5api is not None:
                self.ph5api.close()
            QtCore.QCoreApplication.instance().quit()
            sys.exit(application.exec_())

            ###############################

    # def OnSavePH5
    # author: Lan Dam
    # updated: 201704
    # update currently opened table(s) the current PH5 file using
    # tab.UpdatePH5()
    def OnUpdatePH5(self):
        START = time.time()
        for tab in self.path_tabs:
            tab.UpdatePH5()

        END = time.time()
        savefilename = self.path2file + "/" + self.filename
        self.statusBar.showMessage(
            "Successfully updating the current PH5 file. Total processing"
            "time %s seconds" % (
                END - START))
        msg = "File %s has been updated successfully." \
              "\nDo you want to close KEF Editor?" % savefilename
        QtWidgets.QMessageBox.question(
            self, "Successfully Save File", msg,
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        self.notsave = False  # after saving, reset notsave

    # def OnSavePH5
    # author: Lan Dam
    # updated: 201802
    # update currently opened table(s) to an existing PH5 file, or create new
    # PH5 file from the opened table(s)
    # ** if it is the currently opened one, call self.OnUpdatePH5 instead
    # * user choose filename to save
    # * call _saveKeffile() to save all tables into the a temp file in kef
    # format
    # * For each table (tab/path) call kefutility.NukeTable() to remove the
    # table from the PH5 file
    # * call os.system() to run kef2ph5 script to add the tables in temp.
    # kef file to the filename that user chose
    def OnSavePH5(self):
        if not self._checkAddTableView():
            return

        savefilename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save File", self.path2file, filter="PH5 File (*.ph5)")
        if not savefilename:
            return
        START = time.time()
        options = {}
        options['path2ph5'] = os.path.dirname(str(savefilename))
        options['outph5file'] = os.path.basename(str(savefilename))

        # the file that user choose is the currently opened one => update the
        # file
        if self.path2file == options['path2ph5'] and self.filename == options[
                'outph5file']:
            self.OnUpdatePH5()
            return

        # save in a temp kef file
        if not self.kefFilename:
            options['keffile'] = keftmpfile
            self._saveKeffile(keftmpfile)
        else:
            # add on 20180226 to reduce step when the opened file is a kef file
            options['keffile'] = self.kefFilename

        if path.exists(savefilename):
            for p in self.pathAll:
                self.statusBar.showMessage(
                    "Removing existing table %s from PH5file" % p)
                delResult = kefutility.NukeTable(self, options['outph5file'],
                                                 options['path2ph5'], p)
                if delResult is False:
                    return

        from subprocess import Popen, PIPE, STDOUT

        pathStr = ','.join(self.pathAll)
        cmdStr = "keftoph5 -n %(outph5file)s -k %(keffile)s -p %(path2ph5)s"\
                 % options
        self.statusBar.showMessage(
            "Inserting new table(s) %s into PH5file" % pathStr)
        print "Inserting new table(s) %s into PH5file" % pathStr
        p = Popen(cmdStr, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                  close_fds=True)
        output = p.stdout.read()
        print "The following command is running:\n", cmdStr
        print "Output: ", output

        doclose = False
        if 'error' not in output.lower():
            msg = "File %s has been saved successfully." \
                  "\nDo you want to close KEF Editor?" % savefilename
            result = QtWidgets.QMessageBox.question(
                self, "Successfully Save File",
                msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            self.notsave = False  # after saving, reset notsave

            if result == QtWidgets.QMessageBox.Yes:
                doclose = True
        else:
            QtWidgets.QMessageBox.warning(
                self, "Error in saving to PH5 file", output)
            msg = "Do you want to close KEF Editor?"
            result = QtWidgets.QMessageBox.question(
                self, "", msg,
                QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            if result == QtWidgets.QMessageBox.Yes:
                doclose = True

        END = time.time()
        self.statusBar.showMessage(
            "Successfully saving PH5 file. Total processing time %s seconds"
            % (END - START))
        if doclose:
            if self.ph5api is not None:
                self.ph5api.close()
            QtCore.QCoreApplication.instance().quit()
            sys.exit(application.exec_())
            try:
                os.unlink(keftmpfile)  # remove keftmpfile
            except BaseException:
                pass

    ###############################
    # def _checkAddTableView
    # author: Lan Dam
    # updated: 201704
    # when saving the table, check if the data in AddTableView are all
    # inserted into MainTableView
    def _checkAddTableView(self):
        for tab in self.path_tabs:
            if tab.addDataList != []:
                msg = "There are still data in Add Table View." + \
                      "\nClick 'Cancel' to cancel saving to work on the data."\
                      + \
                      "\nClick 'Save' to continue saving."

                result = QtWidgets.QMessageBox.question(
                    self, "Are you sure?", msg,
                    QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Save)
                if result == QtWidgets.QMessageBox.Cancel:
                    return False
        return True

    ###############################
    # def _saveKeffile
    # author: Lan Dam
    # updated: 201704
    # save all opened tables into the passed savefileme in kef format
    # * loop through tabs, for each tab call tab.ToString appen the table in
    # kef format to currText
    # * save currText into file 'savefilename'
    def _saveKeffile(self, savefilename, currText=""):
        i = 0
        for tab in self.path_tabs:
            currText, i = tab.ToString(currText, i)
        try:
            saveFile = open(savefilename, 'w')
            saveFile.write(currText)
        except Exception, e:
            msg = "Can't save the kef file %s due to the error:%s" % (
                savefilename, str(e))
            QtWidgets.QMessageBox.warning(self, "Error", msg)
            return False

        saveFile.close()
        return True

    def OnSaveCSV(self):
        if not self._checkAddTableView():
            return

        error = ""

        START = time.time()
        try:
            for tab in self.path_tabs:
                # created suggestedFileName to recommend to user
                suggestedFileName = tab.path.split("/")[-1]

                suggestedFileName = self.path2file + "/" + suggestedFileName\
                    + '.csv'

                savefilename, _ = QtWidgets.QFileDialog.getSaveFileName(
                    self, "Save File on Path: %s" % tab.path,
                    suggestedFileName, filter="CSV File (*.csv)")
                if not savefilename:
                    continue
                tab.SaveCSV(savefilename)
        except Exception, e:
            error = str(e)

        if error == "":
            msg = "File %s has been saved successfully." \
                  "\nDo you want to close KEF Editor?" % savefilename
            result = QtWidgets.QMessageBox.warning(
                self, "Successfully Save File",
                msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            if result == QtWidgets.QMessageBox.Yes:
                doclose = True
        else:
            QtWidgets.QMessageBox.warning(self, "Error in saving as CSV file")
            msg = "Do you want to close KEF Editor?"
            result = QtWidgets.QMessageBox.question(
                self, "", msg,
                QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            if result == QtWidgets.QMessageBox.Yes:
                doclose = True

        END = time.time()
        self.statusBar.showMessage(
            "Successfully saving as CSV file. Total processing time %s"
            "seconds" % (END - START))

        if doclose:
            if self.ph5api is not None:
                self.ph5api.close()
            QtCore.QCoreApplication.instance().quit()
            sys.exit(application.exec_())

    # def setData
    # author: Lan Dam
    # updated: 201702
    # display data for each path in a TablePanel placed in a tab
    # * remove all current tab
    # * loop through each path, create a new tab with that path's data
    # * add the tab to self.path_tabs to delete the tabWidget after removeTab
    # * enable save options
    def setData(self):
        self.addMsg = ""
        if self.totalLines > 100000:
            self.addMsg = "It will take a couple of minutes  to populate the" \
                          "table(s). Please wait..."

        # remove existing tab
        while self.path_tabs != []:
            self.path_tabWidget.removeTab(len(self.path_tabs) - 1)
            self.path_tabs.pop(len(self.path_tabs) - 1)

        self.processedLine = 0
        # set tab for each path
        self.pathAll = self.dataTable.keys()
        self.pathAll.sort()
        for p in self.pathAll:
            if self.dataTable[p] in [None, []]:
                errMsg = "There are no data for path %s.\n Please check if" \
                         "the selected PH5 is a master file."
                QtWidgets.QMessageBox.warning(self, "Error", errMsg % p)
                return
            pathWidget = TablePanel(self, p, self.dataTable[p],
                                    self.labelSets[p], self.types[p])
            self.path_tabWidget.addTab(pathWidget, p)
            self.path_tabs.append(pathWidget)

        self.saveKefAction.setEnabled(True)
        self.savePH5Action.setEnabled(True)
        self.saveCSVAction.setEnabled(True)
        self.statusBar.showMessage("")
        if self.totalLines > 100000:
            self.statusBar.showMessage(
                "Please be patient when clicking on each tab. Initially it"
                "takes some time to process.")


updateColName = QtGui.QColor(245, 225, 225,
                             100).name()  # because there is a difference
# between color in label and in
deleteColName = QtGui.QColor(180, 150, 180, 100).name()  # table cells
UPDATECOLOR = QtGui.QBrush(QtGui.QColor(225, 175, 175, 100))  # light pink
DELETECOLOR = QtGui.QBrush(QtGui.QColor(70, 10, 70, 100))  # light purple


# CLASS ####################
# class TablePanel: Each path will have a tableView to display its data
# with path: path in Kef/PH5
#   table: data in list
#   labels: list of columns/keys
class TablePanel(QtWidgets.QMainWindow):

    def __init__(self, parent, path, table, labels, types):
        QtWidgets.QMainWindow.__init__(self)
        self.parent = parent
        self.path = path
        self.table = table
        self.updatedTable = numpy.array(table)
        self.labels = labels
        self.types = types
        self.selectedCells = []
        self.minChangedRowId = None
        self.updateList = []  # list of rows that have been updated
        self.deleteList = []  # list of rows to delete
        self.addDataList = []  # list of data to add
        self.addCells = None

        mainFrame = QtWidgets.QFrame(self)
        self.setCentralWidget(mainFrame)
        mainLayout = QtWidgets.QVBoxLayout()
        mainFrame.setLayout(mainLayout)

        # set mainTableView
        self.mainTableView = QtWidgets.QTableWidget(self)
        self.mainTableView.installEventFilter(self)
        EXPL[self.mainTableView] = "MainView where main data are displayed."
        self.mainTableView.cellClicked.connect(self.OnMainTableClick)
        self.mainTableView.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        mainLayout.addWidget(self.mainTableView)

        # set view range
        self.mainTableView.setColumnCount(len(self.labels))
        self.mainTableView.setRowCount(len(self.table))

        # set data into cells
        for r in range(len(self.table)):
            parent.processedLine += 1
            if parent.processedLine % 10000 == 0:
                msg = "Displaying Data on TableView: %s/%s rows. %s" % (
                    parent.processedLine, parent.totalLines, parent.addMsg)
                parent.statusBar.showMessage(msg)
            for c in range(len(self.labels)):
                item = QtWidgets.QTableWidgetItem(self.table[r][c])
                item.setFlags(
                    QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                # disable cell editing
                self.mainTableView.setItem(r, c, item)

        # change to fit columns with its contents instead of having same
        # default size for all columns
        self.mainTableView.resizeColumnsToContents()

        # set horizontal Headers
        self.mainTableView.setHorizontalHeaderLabels(self.labels)
        self.mainTableView.horizontalHeader().setVisible(True)

        # set Tool tip for each horizontal header
        for c in range(len(self.labels)):
            self.mainTableView.horizontalHeaderItem(c).setToolTip(
                self.labels[c])

        # change tools ######################
        changeBox = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(changeBox)
        changeBox.setSpacing(25)

        changeBox.addStretch(1)
        changeBox.addWidget(QtWidgets.QLabel("Select Types:"))

        self.singleCell = QtWidgets.QRadioButton('Single Cell')
        self.singleCell.installEventFilter(self)
        EXPL[
            self.singleCell] = "Select one Single Cell only." \
                               "(in either MainView or AddRowView)"
        self.singleCell.clicked.connect(self.OnClearSelected)
        changeBox.addWidget(self.singleCell)

        self.allInStation = QtWidgets.QRadioButton(
            'All Similar Cells in Station')
        self.allInStation.installEventFilter(self)
        EXPL[
            self.allInStation] = "All cells that have the same station id and"\
                                 "value with the clicked cell will be" \
                                 "selected. Avalaible only for Array Table." \
                                 "(in either MainView or AddRowView)"
        self.allInStation.clicked.connect(self.OnClearSelected)
        changeBox.addWidget(self.allInStation)

        if 'Array_t' in path:
            self.allInStation.setChecked(True)
        else:
            self.singleCell.setChecked(True)
            self.allInStation.setEnabled(False)

        self.allInColumn = QtWidgets.QRadioButton(
            'All Similar Cells in Column')
        self.allInColumn.installEventFilter(self)
        EXPL[
            self.allInColumn] = "All cells that have the same value and" \
                                "column with the clicked cell will be" \
                                "selected.(in either MainView or AddRowView)"

        self.allInColumn.clicked.connect(self.OnClearSelected)
        changeBox.addWidget(self.allInColumn)

        self.changedValCtrl = QtWidgets.QLineEdit('')
        self.changedValCtrl.installEventFilter(self)
        EXPL[
            self.changedValCtrl] = "Values in the selected items will be" \
                                   "change to the value in this box when" \
                                   "'Change' button is clicked."
        self.changedValCtrl.setFixedWidth(400)
        changeBox.addWidget(self.changedValCtrl)

        self.changeBtn = QtWidgets.QPushButton('Change', self)
        self.changeBtn.installEventFilter(self)
        EXPL[
            self.changeBtn] = "Apply changing values in the selected items" \
                              "(in either MainView or AddRowView)."
        self.changeBtn.clicked.connect(self.OnChange)
        changeBox.addWidget(self.changeBtn)

        self.back2orgBtn = QtWidgets.QPushButton('Back to Org', self)
        self.back2orgBtn.installEventFilter(self)
        EXPL[
            self.back2orgBtn] = "Reset selected items back to their original" \
                                "values."
        self.back2orgBtn.clicked.connect(self.OnBack2org)
        changeBox.addWidget(self.back2orgBtn)

        changeBox.addStretch(1)

        mainLayout.addWidget(Seperator(thick=2, orientation="horizontal"))
        # column tools ######################
        columnBox1 = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(columnBox1)

        columnBox1.addStretch(1)

        columnBox1.addWidget(QtWidgets.QLabel("Selected Column"))
        self.selectedColumnCtrl = QtWidgets.QLineEdit('')
        self.selectedColumnCtrl.installEventFilter(self)
        EXPL[self.selectedColumnCtrl] = "The label of the selected column."
        self.selectedColumnCtrl.setReadOnly(True)
        self.selectedColumnCtrl.setFixedWidth(250)
        columnBox1.addWidget(self.selectedColumnCtrl)

        columnBox1.addWidget(
            QtWidgets.QLabel("    Position of Char. to change"))
        self.characterOrderCtrl = QtWidgets.QComboBox(self)
        self.characterOrderCtrl.installEventFilter(self)
        EXPL[
            self.characterOrderCtrl] = "The first position of character(s)" \
                                       "to change."
        self.characterOrderCtrl.currentIndexChanged.connect(
            self.OnChangeCharOrder)
        columnBox1.addWidget(self.characterOrderCtrl)

        columnBox1.addWidget(QtWidgets.QLabel("    Number of Char. to change"))
        self.noOfCharsCtrl = QtWidgets.QComboBox(self)
        self.noOfCharsCtrl.installEventFilter(self)
        EXPL[self.noOfCharsCtrl] = "The number of character(s) to change."
        self.noOfCharsCtrl.currentIndexChanged.connect(self.OnChangeNoOfChars)
        columnBox1.addWidget(self.noOfCharsCtrl)

        columnBox1.addWidget(QtWidgets.QLabel("   X"))
        self.XCtrl = QtWidgets.QLineEdit('')
        self.XCtrl.installEventFilter(self)
        EXPL[self.XCtrl] = "The value to be applied in column changing."
        self.XCtrl.textChanged.connect(self.OnXChanged)
        self.XCtrl.setFixedWidth(400)
        columnBox1.addWidget(self.XCtrl)
        columnBox1.addStretch(1)

        columnBox2 = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(columnBox2)

        columnBox2.addStretch(1)

        columnBox2.setSpacing(40)
        self.changeChar2XBtn = QtWidgets.QPushButton('Change Char. to X', self)
        self.changeChar2XBtn.installEventFilter(self)
        EXPL[
            self.changeChar2XBtn] = "Change the selected character(s) in" \
                                    "each item of the selected column to X."
        self.changeChar2XBtn.clicked.connect(self.OnChangeChar2X)
        columnBox2.addWidget(self.changeChar2XBtn)

        self.plusX2CharBtn = QtWidgets.QPushButton('Plus X to Char.', self)
        self.plusX2CharBtn.installEventFilter(self)
        EXPL[
            self.plusX2CharBtn] = "Plus X to the selected character(s) in" \
                                  "each item of the selected column."
        self.plusX2CharBtn.clicked.connect(self.OnPlusX2Char)
        columnBox2.addWidget(self.plusX2CharBtn)

        self.changeCol2XBtn = QtWidgets.QPushButton('Change Column to X', self)
        self.changeCol2XBtn.installEventFilter(self)
        EXPL[
            self.changeCol2XBtn] = "Change each item of the selected column" \
                                   "to X."
        self.changeCol2XBtn.clicked.connect(self.OnChangeCol2X)
        columnBox2.addWidget(self.changeCol2XBtn)

        self.plusX2ColBtn = QtWidgets.QPushButton('Plus X to Column', self)
        self.plusX2ColBtn.installEventFilter(self)
        EXPL[self.plusX2ColBtn] = "Plus X to each item of the selected column."
        self.plusX2ColBtn.clicked.connect(self.OnPlusX2Col)
        columnBox2.addWidget(self.plusX2ColBtn)

        self.resetColBtn = QtWidgets.QPushButton('Reset Column', self)
        self.resetColBtn.installEventFilter(self)
        EXPL[
            self.resetColBtn] = "Reset each item of the selected column back" \
                                "to its original value."
        self.resetColBtn.clicked.connect(self.OnResetCol)
        columnBox2.addWidget(self.resetColBtn)

        columnBox2.addStretch(1)

        mainLayout.addWidget(Seperator(thick=2, orientation="horizontal"))
        # move tools ######################
        moveBox = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(moveBox)

        moveBox.addStretch(1)
        moveBox.addWidget(QtWidgets.QLabel("Selected Row(s)"))
        self.selectedRowsCtrl = QtWidgets.QLineEdit('')
        self.selectedRowsCtrl.installEventFilter(self)
        EXPL[
            self.selectedRowsCtrl] = "Show list of Selected Items' rows." \
                                     "(User may want to look at these rows" \
                                     "when moving them to a position under" \
                                     "another row.)"
        self.selectedRowsCtrl.setReadOnly(True)
        self.selectedRowsCtrl.setFixedWidth(500)
        moveBox.addWidget(self.selectedRowsCtrl)

        moveBox.addWidget(
            QtWidgets.QLabel("         Move Selected Row(s) under Line No"))
        self.moveLineCtrl = QtWidgets.QComboBox(self)
        self.moveLineCtrl.installEventFilter(self)
        EXPL[
            self.moveLineCtrl] = "Line Number under which the Selected Row(s)"\
                                 "will be moved to. "
        self.moveLineCtrl.currentIndexChanged.connect(self.OnSelectMoveLine)
        self.moveLineCtrl.clear()
        lineNoList = [str(n) for n in
                      [' top '] + range(1, len(self.table) + 1)]
        self.moveLineCtrl.addItems(lineNoList)
        moveBox.addWidget(self.moveLineCtrl)

        self.moveBtn = QtWidgets.QPushButton('Move', self)
        self.moveBtn.installEventFilter(self)
        EXPL[
            self.moveBtn] = "Move the Selected Row(s) to under the Selected" \
                            "Line No."
        self.moveBtn.setFixedWidth(90)
        self.moveBtn.clicked.connect(self.OnMove)
        moveBox.addWidget(self.moveBtn)

        moveBox.addStretch(1)

        mainLayout.addWidget(Seperator(thick=2, orientation="horizontal"))

        # delete tools ######################
        deleteBox = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(deleteBox)

        deleteBox.addStretch(1)
        self.deleteBtn = QtWidgets.QPushButton(
            'Delete Row(s) on Selected Cell(s)', self)
        self.deleteBtn.installEventFilter(self)
        EXPL[self.deleteBtn] = "Mark deleted for the Selected Rows."
        self.deleteBtn.setFixedWidth(400)
        self.deleteBtn.clicked.connect(self.OnDelete)
        deleteBox.addWidget(self.deleteBtn)

        deleteBox.addSpacing(250)
        self.unDeleteBtn = QtWidgets.QPushButton('UnDelete', self)
        self.unDeleteBtn.installEventFilter(self)
        EXPL[self.unDeleteBtn] = "UnMark deleted for the Selected Rows."
        self.unDeleteBtn.setFixedWidth(400)
        self.unDeleteBtn.clicked.connect(self.OnUndelete)
        deleteBox.addWidget(self.unDeleteBtn)

        deleteBox.addStretch(1)

        mainLayout.addWidget(Seperator(thick=2, orientation="horizontal"))

        # add tools ######################
        addBox = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(addBox)

        addBox.addStretch(1)
        self.addBtn = QtWidgets.QPushButton(
            'Add Row(s) with Data Copy from Selected Cell(s)', self)
        self.addBtn.installEventFilter(self)
        EXPL[
            self.addBtn] = "Copy Selected Row(s) in MainView to the" \
                           "AddRowView at the bottom."
        self.addBtn.setFixedWidth(400)
        self.addBtn.clicked.connect(self.OnAdd)
        addBox.addWidget(self.addBtn)

        addBox.addSpacing(250)
        addBox.addWidget(
            QtWidgets.QLabel("Insert Selected Row(s) under Line No"))
        self.insertLineCtrl = QtWidgets.QComboBox(self)
        self.insertLineCtrl.installEventFilter(self)
        EXPL[
            self.insertLineCtrl] = "Select the Line No under which the" \
                                   "selected rows in AddRowView will be" \
                                   "inserted to."
        self.insertLineCtrl.currentIndexChanged.connect(self.OnSelectAddLine)
        self.insertLineCtrl.clear()
        lineNoList = [str(n) for n in
                      [' top '] + range(1, len(self.table) + 1)]
        self.insertLineCtrl.addItems(lineNoList)
        addBox.addWidget(self.insertLineCtrl)

        self.insertBtn = QtWidgets.QPushButton('Insert', self)
        self.insertBtn.installEventFilter(self)
        EXPL[
            self.insertBtn] = "Move the Selected Row(s) from AddRowView to" \
                              "under the Selected Line No in MainView."
        self.insertBtn.setFixedWidth(90)
        self.insertBtn.clicked.connect(self.OnInsert)
        addBox.addWidget(self.insertBtn)

        addBox.addStretch(1)

        # addTableView: to view all rows to add
        self.addTableView = QtWidgets.QTableWidget(self)
        self.addTableView.installEventFilter(self)
        EXPL[
            self.addTableView] = "AddRowView, where the rows to be added to" \
                                 "MainView can be editted before adding to" \
                                 "table."
        self.addTableView.setMaximumHeight(200)
        self.addTableView.cellClicked.connect(self.OnAddTableClick)
        self.addTableView.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        mainLayout.addWidget(self.addTableView)

        self._setButtonsDisabled()

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.Enter:
            if object not in EXPL.keys():
                return False
            P = object.pos()
            QtWidgets.QToolTip.showText(
                self.mapToGlobal(QtCore.QPoint(P.x(), P.y() + 20)),
                EXPL[object])
            return True
        return False

    # def _setButtonsDisabled
    # author: Lan Dam
    # updated: 201703
    # disabled all buttons (at the beginning and when change selectioncriteria)
    def _setButtonsDisabled(self):
        self.changeBtn.setEnabled(False)
        self.moveBtn.setEnabled(False)
        self.moveLineCtrl.setEnabled(False)
        self.deleteBtn.setEnabled(False)
        self.unDeleteBtn.setEnabled(False)
        self.addBtn.setEnabled(False)
        self.insertBtn.setEnabled(False)
        self.insertLineCtrl.setEnabled(False)
        self.characterOrderCtrl.setEnabled(False)
        self.changeChar2XBtn.setEnabled(False)
        self.plusX2CharBtn.setEnabled(False)
        self.plusX2ColBtn.setEnabled(False)
        self.changeCol2XBtn.setEnabled(False)
        self.changeChar2XBtn.setEnabled(False)
        self.XCtrl.setEnabled(False)
        self.back2orgBtn.setEnabled(False)
        self.resetColBtn.setEnabled(False)

    ###############################
    # def OnClearSelected
    # author: Lan Dam
    # updated: 201703
    # Clear all Selected cells on oth MainTableView and addTableView
    def OnClearSelected(self, event):
        self.mainTableView.clearSelection()
        self.addTableView.clearSelection()
        self.selectedCells = []
        self.addCells = None
        self._setButtonsDisabled()

    ###############################
    # def OnMainTableClick
    # author: Lan Dam
    # updated: 201703
    # when a cell is selected, mark all cells on MainTableView
    # with the same value that match the selection criteria chosen
    def OnMainTableClick(self, row, column):
        # print "OnMainTableClick"
        self.changeBtn.setEnabled(True)
        self.insertBtn.setEnabled(False)
        self.insertLineCtrl.setEnabled(False)
        self.XCtrl.setEnabled(True)
        self.changeCol2XBtn.setEnabled(True)
        self.back2orgBtn.setEnabled(True)
        self.resetColBtn.setEnabled(True)

        # clear selection in addTableView if there is some
        if self.addCells is not None:
            self.addTableView.clearSelection()
            self.addCells = None  # so that OnChange will take effect mainTable

        # Identify which cell(s) are selected
        value = self.mainTableView.item(row, column).text()
        if self.singleCell.isChecked():
            self.selectedCells = [(row, column)]
            selectedRows = [str(row + 1)]

        elif self.allInStation.isChecked():
            # get all entries that have the same stationName with the
            # selected cell
            statCol = self.labels.index('id_s')
            statName = self.mainTableView.item(row, statCol).text()
            # statRowList: all rows with station id similar to selected row's
            # stationid
            statRowList = [i for i in range(len(self.updatedTable)) if
                           self.updatedTable[i][statCol] == statName]
            # mark selected for that station's cells that have the same value
            self.selectedCells, selectedRows =\
                self._selectMatchInList(value,
                                        column,
                                        statRowList,
                                        self.mainTableView)

        elif self.allInColumn.isChecked():
            # mark selected for that column cells that have the same value
            self.selectedCells, selectedRows =\
                self._selectMatchInList(value,
                                        column,
                                        range(len(self.table)),
                                        self.mainTableView)

        self.changedValCtrl.setText(value)
        self.selectedRowsCtrl.setText('-'.join(selectedRows))

        # column tools
        self.selectedCol = column
        self.selectedColumnCtrl.setText(self.labels[column])
        self._afterUpdateCol()

        # Identify which options should be enable
        if self.allInStation.isChecked() or self.singleCell.isChecked():
            # enable add and delete options
            self.addBtn.setEnabled(True)
            noDel = True
            undelApplicable = True
            for r, c in self.selectedCells:
                if r not in self.deleteList:
                    undelApplicable = False
                else:
                    noDel = False
            if undelApplicable:  # all rows have been deleted allow
                # undelete option
                self.unDeleteBtn.setEnabled(True)
                self.deleteBtn.setEnabled(False)
            else:
                self.unDeleteBtn.setEnabled(False)
                self.deleteBtn.setEnabled(True)

            if noDel:  # no rows have been deleted allow move option
                self.moveBtn.setEnabled(True)
                self.moveLineCtrl.setEnabled(True)
            else:
                self.moveBtn.setEnabled(False)
                self.moveLineCtrl.setEnabled(False)

        else:
            # disable move, add, delete, undelete options when too many
            # cells are selected
            self.moveBtn.setEnabled(False)
            self.moveLineCtrl.setEnabled(False)
            self.addBtn.setEnabled(False)
            self.deleteBtn.setEnabled(False)
            self.unDeleteBtn.setEnabled(False)

    # def OnAddTableClick
    # author: Lan Dam
    # updated: 201703
    # when a cell is selected, mark all cells on AddTableView
    # with the same value that match the selection criteria chosen
    # * disable all options except change and insert options
    # * clear selection in mainTableView
    # * identify which cell(s) are selected
    # * set the selected value in changedValCtrl
    def OnAddTableClick(self, row, column):
        self.changeBtn.setEnabled(True)
        self.moveBtn.setEnabled(False)
        self.moveLineCtrl.setEnabled(False)
        self.addBtn.setEnabled(False)
        self.deleteBtn.setEnabled(False)
        self.unDeleteBtn.setEnabled(False)
        self.insertBtn.setEnabled(True)
        self.insertLineCtrl.setEnabled(True)
        self.characterOrderCtrl.setEnabled(False)
        self.XCtrl.setEnabled(False)
        self.changeCol2XBtn.setEnabled(False)
        self.changeChar2XBtn.setEnabled(False)
        self.back2orgBtn.setEnabled(False)
        self.resetColBtn.setEnabled(False)

        # clear selection in mainTableView
        self.mainTableView.clearSelection()
        self.selectedCells = []

        value = self.addTableView.item(row, column).text()
        if self.singleCell.isChecked():
            self.addCells = [(row, column)]
        elif self.allInStation.isChecked():
            # get all entries that have the same stationName with the
            # selected cell
            statCol = self.labels.index('id_s')
            statName = self.addTableView.item(row, statCol).text()
            statRowList = [i for i in range(len(self.addDataList)) if
                           self.addDataList[i][statCol] == statName]
            # mark selected for that station's cells that have the same value
            self.addCells, selectedRows =\
                self._selectMatchInList(value,
                                        column,
                                        statRowList,
                                        self.addTableView)
        else:
            # mark selected for that column cells that have the same value
            self.addCells, selectedRows =\
                self._selectMatchInList(value,
                                        column,
                                        range(len(self.addDataList)),
                                        self.addTableView)

        self.changedValCtrl.setText(value)

    ###############################
    # def _selectMatchInList
    # author: Lan Dam
    # updated: 201703
    # mark selected for all cells in _list that match the given value
    # return list of cells selected
    def _selectMatchInList(self, value, column, _list, tableView):
        selectedCells = []
        selectedRows = []
        for r in _list:
            currItem = tableView.item(r, column)
            if value == currItem.text():
                currItem.setSelected(True)
                selectedCells.append((r, column))
                selectedRows.append(str(r + 1))
        return selectedCells, selectedRows

    ###############################
    # def OnXChanged
    # author: Lan Dam
    # updated: 201705
    # check condition to decide to enable plusX__ buttons in need
    # if XCtrl is integer:
    # * enable plusX2CharBtn if all chars at the selected position(s) of
    # the selected column are digit
    # * enable plusX2ColBtn if type of col is int or float, in case of the
    # str type, check if all column's values are digit
    def OnXChanged(self, arg):
        # print "OnXChanged:", arg
        self.plusX2CharBtn.setEnabled(False)
        self.plusX2ColBtn.setEnabled(False)
        try:
            int(self.XCtrl.text())
        except BaseException:
            return

        if self.nondigitList == []:
            self.plusX2CharBtn.setEnabled(True)

        type_ = self.types[
            self.labels.index(str(self.selectedColumnCtrl.text()))]
        if type_ in [float, int]:
            self.plusX2ColBtn.setEnabled(True)
        else:
            col_nondigitList = [colVal for colVal in self.selectedColList if
                                not colVal.isdigit()]
            if col_nondigitList == []:
                self.plusX2ColBtn.setEnabled(True)

    ###############################
    # def OnChangeCharOrder
    # author: Lan Dam
    # updated: 201705
    # when characterOrderCtrl is changed:
    #  * change item list of noOfCharsCtrl
    #  * reset nondigitList (list of chars at the selected position(s) of
    # the selected column that are non-digit)
    def OnChangeCharOrder(self, arg):
        if not self.characterOrderCtrl.isEnabled():
            return
        self.noOfCharsCtrl.clear()
        self.nondigitList = []
        self.noOfCharsCtrl.addItems([str(item) for item in range(1, len(
            self.selectedColList[0]) - arg + 1)])

    ###############################
    # def OnChangeNoOfChars
    # author: Lan Dam
    # updated: 201705
    # when select characterOrderCtrl, build up nondigitList (list of chars
    # at the selected position(s) of the selected column that are non-digit)
    # if nondigitList is [] (all are digit, enable plus2CharBtn according
    # to XCtrl)
    def OnChangeNoOfChars(self, arg):
        order = self.characterOrderCtrl.currentIndex()
        noOfChars = arg + 1

        self.nondigitList = [i for i in range(len(self.selectedColList))
                             if not str(
            self.selectedColList[i][order:order + noOfChars]).isdigit()]

        self.plusX2CharBtn.setEnabled(False)
        if self.nondigitList == []:
            try:
                int(self.XCtrl.text())
                self.plusX2CharBtn.setEnabled(True)
            except BaseException:
                pass

    ###############################
    # def OnChangeChar2X
    # author: Lan Dam
    # updated: 201705
    # change selected chars in selected column to XCtrl.text()
    # convert new col value to right type of column
    # need to do it through newColumnList to be able to keep original
    # value in case checking type has error
    # then _updateColItem
    def OnChangeChar2X(self):
        if not self._checkEmpty("character"):
            return
        # check type
        type_ = self.types[
            self.labels.index(str(self.selectedColumnCtrl.text()))]
        try:
            index = 0
            newColumnList = []
            for val in self.selectedColList:
                val = str(val)
                order = self.characterOrderCtrl.currentIndex()
                noOfChars = self.noOfCharsCtrl.currentIndex() + 1
                if len(str(self.XCtrl.text())) != noOfChars:
                    msg = "On line %s, the character(s) need to change" \
                          "is/are '%s'," + \
                          "\nwhile the replace character(s) is/are '%s' " \
                          "of which length is different."
                    QtWidgets.QMessageBox.warning(self, "Error", msg % (
                        index + 1, val[order:order + noOfChars],
                        str(self.XCtrl.text())))
                    return
                val = list(val)
                val[order:order + noOfChars] = str(self.XCtrl.text())
                val = ''.join(val)
                newColumnList.append(type_(val))
                index += 1
        except ValueError:
            msg = "The new value of '%s', line %s is '%s' which doesn't match"\
                  "the required type: %s"
            QtWidgets.QMessageBox.warning(self, "Error", msg % (
                self.selectedColumnCtrl.text(), index + 1, val,
                type_.__name__))
            return

        for r in range(len(self.updatedTable)):
            self._updateColItem(r, newColumnList[r])
        self._afterUpdateCol()

    ###############################
    # def OnPlusX2Char
    # author: Lan Dam
    # updated: 201705
    # plus selected chars in selected column to XCtrl.text()
    # check the number of new chars is the same
    # convert new col value to right type of column
    # need to do it through newColumnList to be able to keep original value
    # in case checking type has error
    # then _updateColItem
    def OnPlusX2Char(self):
        type_ = self.types[
            self.labels.index(str(self.selectedColumnCtrl.text()))]
        try:
            index = 0
            newColumnList = []
            for val in self.selectedColList:
                val = str(val)
                order = self.characterOrderCtrl.currentIndex()
                noOfChars = self.noOfCharsCtrl.currentIndex() + 1
                insertChars = str(
                    int(val[order:order + noOfChars]) + int(self.XCtrl.text()))
                if len(insertChars) > noOfChars:
                    msg = "On line %s, the character(s) need to" \
                          "change is '%s'," + \
                          "\nwhile the replace character(s) is/are %s of" \
                          "which length is different."
                    QtWidgets.QMessageBox.warning(self, "Error", msg % (
                        index + 1, val[order:order + noOfChars], insertChars))
                    return

                val = list(val)
                val[order:order + noOfChars] = insertChars.zfill(noOfChars)
                val = ''.join(val)
                newColumnList.append(type_(val))
                index += 1
        except ValueError:
            msg = "The new value of '%s', line %s is '%s' which doesn't" \
                  "match the required type: %s"
            QtWidgets.QMessageBox.warning(self, "Error", msg % (
                self.selectedColumnCtrl.text(), index + 1, val,
                type_.__name__))
            return

        for r in range(len(self.updatedTable)):
            self._updateColItem(r, newColumnList[r])
        self._afterUpdateCol()

    ###############################
    # def _checkEmpty
    # author: Lan Dam
    # updated: 201705
    # return False if the value in XCtrl is empty
    def _checkEmpty(self, ctrlName):
        if str(self.XCtrl.text()).strip() == "":
            msg = "The value in the X box is '%s'.\n" \
                  "Are you sure you want to change the selected %s to it?" % (
                      self.XCtrl.text(), ctrlName)
            result = QtWidgets.QMessageBox.question(
                self, "Are you sure?", msg,
                QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.Cancel)
            if result == QtWidgets.QMessagedBox.Cancel:
                return False

        return True

    ###############################
    # def OnChangeCol2X
    # author: Lan Dam
    # updated: 201705
    # change the cells value of the selectedCol to the value in XCtrl
    def OnChangeCol2X(self):
        if not self._checkEmpty("column"):
            return

        type_ = self.types[
            self.labels.index(str(self.selectedColumnCtrl.text()))]

        try:
            newVal = type_(self.XCtrl.text())
        except ValueError:
            msg = "The new value of all cells in '%s' is '%s'," \
                  "\nwhich doesn't match the required type: %s"
            QtWidgets.QMessageBox.warning(self, "Error", msg % (
                self.selectedColumnCtrl.text(), self.XCtrl.text(),
                type_.__name__))
            return

        for r in range(len(self.updatedTable)):
            self._updateColItem(r, newVal)
        self._afterUpdateCol()

    ###############################
    # def OnResetCol
    # author: Lan Dam
    # updated: 201705
    # reset the values of cells on the selectedCol back to theirs original
    # values
    def OnResetCol(self):
        for r in range(len(self.updatedTable)):
            self._updateColItem(r, self.table[r][self.selectedCol])
        self._afterUpdateCol()

    ###############################
    # def OnPlusX2Col
    # author: Lan Dam
    # updated: 201705
    # plus the value in X to all cell in the selectedCol
    # plus as int first to avoid the result in float format then as float
    # (the button only available if value in XCtrl and in selectedColList
    # are number)
    def OnPlusX2Col(self):
        type_ = self.types[
            self.labels.index(str(self.selectedColumnCtrl.text()))]
        index = 0
        newColumnList = []
        for r in range(len(self.updatedTable)):
            try:
                newVal = int(self.XCtrl.text()) + int(self.selectedColList[r])
            except ValueError:
                newVal = float(self.XCtrl.text()) + float(
                    self.selectedColList[r])

            try:
                newColumnList.append(type_(newVal))
            except ValueError:
                msg = "The new value of %s, line %s is %s," \
                      "\nwhich doesn't match the required type: %s"
                QtWidgets.QMessageBox.warning(self, "Error", msg % (
                    self.selectedColumnCtrl.text(), index + 1, newVal,
                    type_.__name__))
                return

        for r in range(len(self.updatedTable)):
            self._updateColItem(r, newColumnList[r])
        self._afterUpdateCol()

    ###############################
    # def _updateColItem
    # author: Lan Dam
    # updated: 201705
    # update the item on given row, selectedCol to newVal
    # change color depend on the changed value is the original value or not
    def _updateColItem(self, r, newVal):
        currItem = self.mainTableView.item(r, self.selectedCol)
        currItem.setText(str(newVal))
        self.updatedTable[r][self.selectedCol] = newVal
        if self.table[r][self.selectedCol] != newVal:
            currItem.setForeground(QtCore.Qt.red)
            if r not in self.deleteList:
                self._changeRowBackground(r, UPDATECOLOR)
            if r not in self.updateList:
                self.updateList.append(r)
        else:
            currItem.setForeground(QtCore.Qt.black)
            updated = False
            for i in range(len(self.labels)):
                if self.updatedTable[r][i] != self.table[r][i]:
                    updated = True
                    break
            if updated is False:
                if r not in self.deleteList:
                    self._changeRowBackground(r, QtCore.Qt.white)
                if r in self.updateList:
                    self.updateList.remove(r)

    # def _afterUpdateCol
    # author: Lan Dam
    # updated: 201705
    # update selectedColList
    # set characterOrderCtrl, changeChar2XBtn, plusX2ColBtn, plusX2Col
    # depend on type and length of the selectedColList
    def _afterUpdateCol(self):
        self.selectedColList = self.updatedTable[:, self.selectedCol]
        difLen = [len(item) for item in self.selectedColList if
                  len(item.strip()) != len(self.selectedColList[0].strip())]
        if difLen == []:
            self.changeChar2XBtn.setEnabled(True)
            self.characterOrderCtrl.setEnabled(True)
            self.characterOrderCtrl.clear()
            self.characterOrderCtrl.addItems(
                [str(i + 1) for i in range(len(self.selectedColList[0]))])
        else:
            self.characterOrderCtrl.clear()
            self.characterOrderCtrl.setEnabled(False)
            self.changeChar2XBtn.setEnabled(False)

        self.plusX2ColBtn.setEnabled(False)
        type_ = self.types[
            self.labels.index(str(self.selectedColumnCtrl.text()))]
        if str(self.XCtrl.text()).isdigit() and type_ in [float, int]:
            self.plusX2ColBtn.setEnabled(True)

    ###############################
    # def OnChange
    # author: Lan Dam
    # updated: 201703
    # Change the values of the selected cells into the value in changedValCtrl
    #  on MainTableView if self.addCells == None
    #   * not change if there are any rows deleted
    #   * change text in cell(s)
    #   * if the change is back to the orginal value, cell color will be
    # resetted (then rows => remove from updateList)
    #   * else: change foreground color of cell(s), change background color
    # of row(s)  => add to updateList if not in updateList yet
    #      => get the rowdata from the table with the new value at the col,
    # but the type keep the same
    #  on AddTableView if self.addCells != None
    #   * change text & color in cell(s) and change the column value to the
    # one in changedValCtrl but type keep the same
    def OnChange(self, event):
        if self.addCells is None:
            for r, c in self.selectedCells:
                if r in self.deleteList:
                    msg = "Because the row %s has been deleted, cell" \
                          "(%s,%s) can't be changed." % (
                              r + 1, r + 1, c + 1)
                    QtWidgets.QMessageBox.warning(self, "Warning", msg)
                    continue

                currItem = self.mainTableView.item(r, c)
                currItem.setText(self.changedValCtrl.text())
                self.updatedTable[r][c] = type(self.updatedTable[r][c])(
                    self.changedValCtrl.text())

                if currItem.text() == self.table[r][c]:
                    currItem.setForeground(QtCore.Qt.black)
                    updated = False
                    for i in range(len(self.labels)):
                        if self.updatedTable[r][i] != self.table[r][i]:
                            updated = True
                            break
                    if updated is False:
                        self._changeRowBackground(r, QtCore.Qt.white)
                        if r in self.updateList:
                            self.updateList.remove(r)
                else:
                    currItem.setForeground(QtCore.Qt.red)
                    self._changeRowBackground(r, UPDATECOLOR)
                    if r not in self.updateList:
                        self.updateList.append(r)

        else:
            for r, c in self.addCells:
                currItem = self.addTableView.item(r, c)
                currItem.setText(self.changedValCtrl.text())
                currItem.setForeground(QtCore.Qt.red)
                self.addDataList[r][c] = type(self.addDataList[r][c])(
                    self.changedValCtrl.text())

    ###############################
    # def OnBack2org
    # author: Lan Dam
    # updated: 201705
    # reset all changes in selectedCells back to original (self.table)
    # accept change in delete rows, but still keep them as deleted
    # change the text color to black (unchanged)
    # but the row color change or not depend on other cells in the row
    def OnBack2org(self, event):
        for r, c in self.selectedCells:
            currItem = self.mainTableView.item(r, c)
            currItem.setText(str(self.table[r][c]))
            self.updatedTable[r][c] = self.table[r][c]
            currItem.setForeground(QtCore.Qt.black)
            updated = False
            for i in range(len(self.labels)):
                if self.updatedTable[r][i] != self.table[r][i]:
                    updated = True
                    break
            if updated is False:
                if r not in self.deleteList:
                    self._changeRowBackground(r, QtCore.Qt.white)
                if r in self.updateList:
                    self.updateList.remove(r)

                ###############################

    # def OnDelete
    # author: Lan Dam
    # updated: 201703
    # * change color of selected Cells to DELETECOLOR
    # * add those rows to self.deleteList
    # * disable delete option, enable undelete option
    def OnDelete(self, event):
        for row, column in self.selectedCells:
            self._changeRowBackground(row, DELETECOLOR)
            if row not in self.deleteList:
                self.deleteList.append(row)

        self.deleteBtn.setEnabled(False)
        self.unDeleteBtn.setEnabled(True)

    ###############################
    # def OnUndelete
    # author: Lan Dam
    # updated: 201703
    # * Change selected delete rows background back to white
    # * remove those rows from self.deleteList
    # * enable delete option, disable undelete option
    def OnUndelete(self, event):
        for row, column in self.selectedCells:
            if row in self.updateList:
                self._changeRowBackground(row, UPDATECOLOR)
            else:
                self._changeRowBackground(row, QtCore.Qt.white)
            if row in self.deleteList:
                self.deleteList.remove(row)

        self.deleteBtn.setEnabled(True)
        self.unDeleteBtn.setEnabled(False)

        ###############################

    # def OnAdd
    # author: Lan Dam
    # updated: 201703
    # Copy the selected Rows from MaintableView into the AddTableView
    # * append selected rows to self.addDataList
    # * clear AddTableView and display addDataList in AddTableView
    def OnAdd(self, event):
        for row, column in self.selectedCells:
            self.addDataList.append(deepcopy(self.updatedTable[row]))

        # clear existing data
        self.addTableView.clear()

        # set view range
        self.addTableView.setColumnCount(len(self.labels))
        self.addTableView.setRowCount(len(self.addDataList))

        # set data into cells
        for r in range(len(self.addDataList)):
            for c in range(len(self.labels)):
                item = QtWidgets.QTableWidgetItem(self.addDataList[r][c])
                item.setFlags(
                    QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                # disable cell editing
                self.addTableView.setItem(r, c, item)

        # change to fit columns with its contents instead of having same
        # default size for all columns
        self.addTableView.resizeColumnsToContents()

        # set horizontal Headers
        self.addTableView.setHorizontalHeaderLabels(self.labels)
        self.addTableView.horizontalHeader().setVisible(True)

        # set Tool tip for each horizontal header
        for c in range(len(self.labels)):
            self.addTableView.horizontalHeaderItem(c).setToolTip(
                self.labels[c])

    ###############################
    # def OnSelectMoveLine
    # author: Lan Dam
    # updated: 201703
    # set the row selected according to what line show in moveLineCtrl
    def OnSelectMoveLine(self, index):
        self._selectLine(self.moveLineCtrl)

    ###############################
    # def OnSelectAddLine
    # author: Lan Dam
    # updated: 201703
    # set the row selected according to what line show in insertLineCtrl
    def OnSelectAddLine(self, index):
        self._selectLine(self.insertLineCtrl)

    ###############################
    # def _selectLine
    # author: Lan Dam
    # updated: 201703
    # set the row selected according to what line show in passed lineCtrl
    # * if val=top => select line before the first line
    # * else: highlight the selected line
    def _selectLine(self, lineCtrl):
        val = str(lineCtrl.currentText())

        if val == " top ":
            self.mainTableView.clearSelection()
            self.mainTableView.scrollToTop()
        else:
            self.mainTableView.setSelectionMode(
                QtWidgets.QAbstractItemView.ExtendedSelection)
            lineId = int(val) - 1
            self.mainTableView.selectRow(lineId)
            # self.mainTableView.scrollTo(self.mainTableView.item(lineId,0))
            self.mainTableView.setSelectionMode(
                QtWidgets.QAbstractItemView.SingleSelection)

    ###############################
    # def OnInsert
    # author: Lan Dam
    # updated: 201704
    # remove selectedRows from self.addDataList + AddTableView and add to
    # MainTableView
    # * pop selected from their postions in addTableView
    # * insert into new postions in MainTableView
    def OnInsert(self, event):
        insertLineId = self.insertLineCtrl.currentIndex()
        if self.minChangedRowId is None:
            self.minChangedRowId = insertLineId
        if self.minChangedRowId > insertLineId:
            self.minChangedRowId =\
                insertLineId

        self.addCells.sort(key=itemgetter(0), reverse=True)

        # identify data to insert to mainTableView and
        # remove data from its current position in addDataList and addTableView
        insertedData = []
        for r, c in self.addCells:
            rowData = deepcopy(self.addDataList[r])
            insertedData.append(rowData)
            self.addDataList.remove(rowData)
            self.addTableView.removeRow(r)

        # insert the data to MainTableView
        self._insertDataToTable(insertLineId, insertedData, insertedData,
                                len(insertedData))

    ###############################
    # def OnMove
    # author: Lan Dam
    # updated: 201704
    # move selectedRows to new positions in MainTableView
    # * pop selected from their postions in MainTableView
    # * insert into new postions in MainTableView
    def OnMove(self, event):
        self.selectedCells.sort(key=itemgetter(0), reverse=True)
        selectedRows = [r[0] for r in self.selectedCells]

        moveLineId = self.moveLineCtrl.currentIndex()
        if moveLineId in selectedRows:
            msg = "Cannot move the select row(s) to a line No \nthat in the" \
                  "range of the selected rows"
            QtWidgets.QMessageBox.warning(self, "Warning", msg)
            return

        # reidentify new moveLineId when pop the selected Rows from table
        if moveLineId > max(selectedRows):
            moveLineId -= len(selectedRows)

        minId = min(selectedRows + [moveLineId])
        if self.minChangedRowId is None:
            self.minChangedRowId = minId
        if self.minChangedRowId > minId:
            self.minChangedRowId = minId

        # identify data to insert to mainTableView and
        # remove data from its current position in table and mainTableView
        insertedData = []
        insertedUpdData = []
        for r in selectedRows:
            rowData = deepcopy(self.table[r])
            insertedData.append(rowData)
            rowData = deepcopy(self.updatedTable[r])
            insertedUpdData.append(rowData)
            self.table.pop(r)
            self.updatedTable = numpy.delete(self.updatedTable, (r), axis=0)
            self.mainTableView.removeRow(r)

            # insert the data to MainTableView
        self._insertDataToTable(moveLineId, insertedData, insertedUpdData,
                                len(selectedRows), max(selectedRows))

    ###############################
    # def _insertDataToTable
    # author: Lan Dam
    # updated: 201704
    # insert the passed insertData into the passed lineId in MainTableView
    def _insertDataToTable(self, lineId, insertData, insertedUpdData,
                           lenInsert, maxRemovedRow=None):
        for i in range(len(insertData)):
            # add inserted data into self.table
            # since insertData in backward order, the previous insert can be
            # moved downward
            # lineId can be used for inserting without any changes
            self.table.insert(lineId, insertData[i])
            self.updatedTable = numpy.insert(self.updatedTable, lineId,
                                             insertedUpdData[i], 0)
            # create new empty row in mainTableView
            self.mainTableView.insertRow(lineId)
            # fill value in insertedUpdData[i] into the empty row
            for c in range(len(self.labels)):
                item = QtWidgets.QTableWidgetItem(insertedUpdData[i][c])
                item.setFlags(
                    QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                # disable cell editing
                self.mainTableView.setItem(lineId, c, item)

        # update values in deleteList and updateList
        lineId -= 1
        for i in range(len(self.deleteList)):
            # delete row ids should be moved downward when there are rows
            # inserted before them
            if self.deleteList[i] > lineId:
                self.deleteList[i] += lenInsert
            # delete row ids should be moved upward when there are rows
            # removed before them
            if maxRemovedRow is not None and\
               self.deleteList[i] > maxRemovedRow:
                self.deleteList[i] -= lenInsert

        for k in self.updateList:
            # update row ids should be moved downward when there are rows
            # inserted before them
            if self.updateList[i] > lineId:
                self.updateList[i] += lenInsert
            # update row ids should be moved upward when there are rows
            # removed before them
            if maxRemovedRow is not None and\
               self.updateList[i] > maxRemovedRow:
                self.updateList[i] -= lenInsert

    ###############################
    # def _changeRowBackground
    # author: Lan Dam
    # updated: 201703
    # change the background of the given row to the given color by changing
    # color of each cell
    def _changeRowBackground(self, row, color):
        for column in range(self.mainTableView.columnCount()):
            self.mainTableView.item(row, column).setBackground(color)

    ###############################
    # def ToString
    # author: Lan Dam
    # updated: 201703
    # convert the data in mainTableViews to string in kef format
    # * use data from updatedTable
    # * if the row in deleteList, skip
    def ToString(self, currText, tableCount):
        for r in range(len(self.updatedTable)):
            if r in self.deleteList:
                continue
            tableCount += 1
            if tableCount % 100 == 0:
                self.parent.statusBar.showMessage("Saving Kef file: %s/%s" % (
                    tableCount, self.parent.totalLines))
                print "Saving Kef file: %s/%s" % (
                    tableCount, self.parent.totalLines)
            currText += "\n# Table row %d" % tableCount
            # Print table name
            currText += "\n" + self.path
            for c in range(len(self.labels)):
                currText += "\n\t%s=%s" % (
                    self.labels[c], self.updatedTable[r][c])

        return currText, tableCount

    ###############################
    # def SaveCSV
    # author: Lan Dam
    # updated: 201705
    # save data into a CSV file with delimeter=';'
    def SaveCSV(self, savedFileName):
        # use updated data from updated table
        DAT = self.updatedTable
        # delete row in deleteList
        DAT = numpy.delete(DAT, self.deleteList, axis=0)
        # combine with labels
        DAT = numpy.vstack((numpy.array(self.labels), DAT))
        # save into a text file with the given savedFileName, delimiter=';'
        numpy.savetxt(savedFileName, DAT, fmt='%s', delimiter=';',
                      header="KEF Editor Ver. %s" % PROG_VERSION)

    ###############################
    # def UpdatePH5
    # author: Lan Dam
    # updated: 201705
    # update the table into the current PH5 file
    # (use data from updatedTable, the type already convert to org type
    # when updating)
    def UpdatePH5(self):
        pp = self.path.split('/')
        name = pp[-1]
        path = self.path.replace('/' + name, '')

        # get the node for the path
        ph5 = self.parent.ph5api.ph5
        node = ph5.get_node(where=path, name=name, classname='Table')

        # remove all the rows follow the lowest insert row because tables
        # class doesn't allow inserting
        if self.minChangedRowId is not None:
            node.remove_rows(self.minChangedRowId)
        # r: rowId
        # row: row in node
        r = 0
        # vtypes = node.coltypes
        for row in node.iterrows():
            # remove row in deleteList
            if r in self.deleteList:
                node.remove_row(r)
            # update item in updateList
            if r in self.updateList:
                for c in range(len(self.labels)):
                    try:
                        row.__setitem__(self.labels[c],
                                        self.updatedTable[r][c])
                    except IndexError as e:
                        pass
                row.update()
            r += 1

        # from lowest insert row, start to append the rest of the updated Table
        if self.minChangedRowId is not None:
            row = node.row
            for r in range(self.minChangedRowId, len(self.updatedTable)):
                if r in self.deleteList:
                    continue
                try:
                    for c in range(len(self.labels)):
                        row[self.labels[c]] = self.updatedTable[r][c]
                except Exception, e:
                    LOGGER.warning(
                        "Warning in append: Exception \'{0}\'".format(e))
                row.append()

        # flush all changes
        node.flush()


##########################################
# CLASS ####################
# Author: Lan
# Updated: 201703
# CLASS: SelectTableDialog - GUI for user to select parameters for table
class SelectTableDialog(QtWidgets.QDialog):

    def __init__(self, parent, availTables, arrays, shotLines, offsets, das):

        QtWidgets.QDialog.__init__(self)
        self.setWindowTitle("Select Tables")
        self.parent = parent
        mainLayout = QtWidgets.QVBoxLayout(self)

        mainLayout.addWidget(
            QtWidgets.QLabel('What table do you want to get info from?'))

        formLayout = QtWidgets.QFormLayout()
        mainLayout.addLayout(formLayout)

        self.tableCtrl = QtWidgets.QComboBox(self)
        self.tableCtrl.clear()
        self.tableCtrl.addItems([''] + availTables)
        formLayout.addRow("Table", self.tableCtrl)
        self.tableCtrl.currentIndexChanged.connect(self.OnSelectTable)

        self.arrayCtrl = QtWidgets.QComboBox(self)
        self.arrayCtrl.clear()
        self.arrayCtrl.addItems([''] + arrays)
        formLayout.addRow("Array", self.arrayCtrl)

        self.shotLineCtrl = QtWidgets.QComboBox(self)
        self.shotLineCtrl.clear()
        self.shotLineCtrl.addItems([''] + shotLines)
        formLayout.addRow("ShotLine", self.shotLineCtrl)

        self.offsetCtrl = QtWidgets.QComboBox(self)
        self.offsetCtrl.clear()
        self.offsetCtrl.addItems([''] + offsets)
        formLayout.addRow("Offset (array_event)", self.offsetCtrl)

        self.dasCtrl = QtWidgets.QComboBox(self)
        self.dasCtrl.clear()
        self.dasCtrl.addItems([''] + das)
        formLayout.addRow("Das", self.dasCtrl)

        btnLayout = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(btnLayout)

        btnLayout.stretch(1)
        submitBtn = QtWidgets.QPushButton('Submit', self)
        submitBtn.clicked.connect(self.OnSubmit)
        btnLayout.addWidget(submitBtn)
        btnLayout.stretch(1)
        cancelBtn = QtWidgets.QPushButton('Cancel', self)
        cancelBtn.clicked.connect(self.OnCancel)
        btnLayout.addWidget(cancelBtn)
        btnLayout.stretch(1)

        self._disableCtrls()
        self.show()

    def OnCancel(self, evt):
        self.close()

    def _disableCtrls(self):
        self.arrayCtrl.setEnabled(False)
        self.shotLineCtrl.setEnabled(False)
        self.dasCtrl.setEnabled(False)
        self.offsetCtrl.setEnabled(False)

    ###############################
    # def OnSelectTable
    # author: Lan Dam
    # updated: 201703
    # when a tableType is selected, enable the properties needed
    def OnSelectTable(self, index):
        self._disableCtrls()
        tableType = self.tableCtrl.currentText()
        if tableType == 'Array_t':
            self.arrayCtrl.setEnabled(True)
        elif tableType == 'Event_t':
            self.shotLineCtrl.setEnabled(True)
        elif tableType == 'Das_t':
            self.dasCtrl.setEnabled(True)
        elif tableType == 'Offset_t':
            self.offsetCtrl.setEnabled(True)

    ###############################
    # def OnSubmit
    # author: Lan Dam
    # updated: 201703
    # use kefutility.PH5toTableData to read the required table into dataTable
    # call parent.setData() to set dataTable into MainTableView
    def OnSubmit(self, evt):
        p = self.parent
        p.tableType = str(self.tableCtrl.currentText())
        errorCtrl = None
        if p.tableType == 'Array_t':
            p.arg = str(self.arrayCtrl.currentText())
            if p.arg == "":
                errorCtrl = 'Array'
        elif p.tableType == 'Event_t':
            p.arg = str(self.shotLineCtrl.currentText())
            if p.arg == "":
                errorCtrl = 'ShotLine'
        elif p.tableType == 'Das_t':
            p.arg = str(self.dasCtrl.currentText())
            if p.arg == "":
                errorCtrl = 'Das'
        elif p.tableType == 'Offset_t':
            p.arg = str(self.offsetCtrl.currentText())
            if p.arg == "":
                errorCtrl = 'Offset'
        else:
            p.arg = None

        if errorCtrl is not None:
            msg = "For Table '%s', %s must be selected." % (
                p.tableType, errorCtrl)
            QtWidgets.QMessageBox.warning(self, "Warning", msg)
            return

        p.dataTable, p.labelSets, p.totalLines, p.types =\
            kefutility.PH5toTableData(
                p.statusBar, p.ph5api, p.filename,
                p.path2file, p.tableType, p.arg)

        p.setData()
        p.openTableAction.setEnabled(True)
        p.updatePH5Action.setEnabled(True)
        p.notsave is True
        self.close()


# CLASS ####################
# Author: Lan
# Updated: 201409
# CLASS: Seperator - is the line to separate in the Gui (reuse from PH5View)
class Seperator(QtWidgets.QFrame):

    def __init__(self, thick=2, orientation="horizontal", length=None):
        QtWidgets.QFrame.__init__(self)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        if orientation == 'horizontal':
            self.setFixedHeight(thick)
            if length is not None:
                self.setFixedWidth(length)
        else:
            self.setFixedWidth(thick)
            if length is not None:
                self.setFixedHeight(length)


##########################################
# CLASS ####################
# Author: Lan
# Updated: 201707
# CLASS: ManWindow - show Manual of the app. (reuse from PH5View)
class ManWindow(QtWidgets.QWidget):

    def __init__(self, mantype=""):
        QtWidgets.QWidget.__init__(self)
        self.setGeometry(100, 100, 900, 700)
        view = QtWidgets.QTextBrowser(self)

        if mantype == "manual":
            view.setText(kefutility.html_manual)

        elif mantype == "whatsnew":
            view.setText(kefutility.html_whatsnew % PROG_VERSION)

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(view)

        self.setLayout(self.layout)
        self.show()


def startapp():
    global application
    application = QtWidgets.QApplication(sys.argv)

    win = KefEdit()

    sys.exit(application.exec_())
    return win


if __name__ == "__main__":
    startapp()
