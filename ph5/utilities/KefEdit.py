#!/usr/bin/env pnpython3
#
#   KefEdit
#
#   Credit: Lan Dam 
#   
#   Updated Feb 2017
PROG_VERSION = "2017.115 Developmental"
# import from python packages
import sys, os, time
import os.path as path

keftmpfile = 'tmp/temp.kef'
from copy import deepcopy
from operator import itemgetter

from PyQt4 import QtGui, QtCore
from PyQt4.QtWebKit import QWebView

# import from pn4
from ph5.core import Experiment

# module(s) for KefEdit only
from ph5.core import KefUtility


############### CLASS ####################
# Author: Lan
# Updated: 201702
# CLASS: KefEdit

class KefEdit(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setWindowTitle("KEF Editor Ver. %s" % PROG_VERSION)        
        
        self.path_tabs = []     # to keep the tabwidget to delete
        self.ph5 = None         # to resue when open tables from the current opened ph5
        self.notsave = True     # to identify if the open data are save
        
        self.initMenu()
        mainFrame = QtGui.QFrame(self); self.setCentralWidget(mainFrame)
        mainLayout = QtGui.QVBoxLayout(); mainFrame.setLayout(mainLayout)
        
        statusLayout = QtGui.QHBoxLayout(); mainLayout.addLayout(statusLayout)
        
        updateCol = QtGui.QLabel("UPDATE")
        updateCol.setAlignment(QtCore.Qt.AlignHCenter)
        updateCol.setFixedWidth(85)
        updateCol.setStyleSheet(" background-color: %s" % updateColName)
        statusLayout.addWidget(updateCol)
        
        deleteCol = QtGui.QLabel("DELETE")
        deleteCol.setAlignment(QtCore.Qt.AlignHCenter)
        deleteCol.setFixedWidth(85)
        deleteCol.setStyleSheet(" background-color: %s" % deleteColName)
        statusLayout.addWidget(deleteCol) 
        
        statusLayout.addSpacing(50)
        self.statusText = QtGui.QLabel()
        statusLayout.addWidget(self.statusText)

        statusLayout.addStretch(1)

        self.path_tabWidget = QtGui.QTabWidget()        # each tab keep a table
        mainLayout.addWidget(self.path_tabWidget)
        self.setGeometry(0, 0,1200, 900)
        self.showMaximized()  



    def initMenu(self):
        ################## HELP MENU  #################
        manualAction = QtGui.QAction('Manual', self)
        manualAction.setShortcut('F1')
        manualAction.triggered.connect(self.onManual)
        
        whatsnewAction = QtGui.QAction("What's new?", self)
        whatsnewAction.setShortcut('F1')
        whatsnewAction.triggered.connect(self.onWhatsnew)        
        ################## FILE MENU  #################
        openKefAction = QtGui.QAction('Open Kef File', self)        
        openKefAction.triggered.connect(self.onOpenKef)
        
        openPH5Action = QtGui.QAction('Open PH5 File', self)
        openPH5Action.triggered.connect(self.onOpenPH5)
        
        self.openTableAction = QtGui.QAction('Open table(s) in the current PH5 File', self)
        self.openTableAction.triggered.connect(self.onOpenCurrPH5)  
        self.openTableAction.setEnabled(False)
        #---------------- Save ----------------
        self.saveKefAction = QtGui.QAction('Save as Kef File', self)
        self.saveKefAction.triggered.connect(self.onSaveKef)  
        self.saveKefAction.setEnabled(False)  
        
        self.savePH5Action = QtGui.QAction('Save as PH5 File', self)
        self.savePH5Action.triggered.connect(self.onSavePH5)  
        self.savePH5Action.setEnabled(False) 
        #---------------- exit ----------------
        exitAction = QtGui.QAction( '&Exit', self)        
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.closeEvent)        
        
        ###############################################
        ################ ADDING MENU #####################
        menubar = QtGui.QMenuBar() 
        self.setMenuBar(menubar)
        
        fileMenu = menubar.addMenu('&File')
        
        fileMenu.addAction(openKefAction)
        fileMenu.addAction(openPH5Action)
        fileMenu.addAction(self.openTableAction)
        
        fileMenu.addAction(self.saveKefAction)
        fileMenu.addAction(self.savePH5Action)
        
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
    # * check if the changes haven't been saved, give user a chance to change mind
    # * close the app when the widget is closed (to close the opened PH5)
    def closeEvent(self, evt=None):
        for tab in self.path_tabs :
            if self.notsave==True and \
               (tab.updateList != [] or tab.deleteList != [] or tab.addDataList != []):
                msg = "There are still things you have worked on but haven't saved." + \
                      "\nClick on Cancel to cancel closing. " + \
                      "\nClick on Close to close KefEdit."
                result = QtGui.QMessageBox.question(self, "Are you sure?", msg, QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Close )
                if result == QtGui.QMessageBox.Cancel: 
                    if evt.__class__.__name__ != 'bool': evt.ignore()                 
                    return
            
        QtCore.QCoreApplication.instance().quit()
        sys.exit(application.exec_())
        

    def onManual(self):
        print "onManual"
        self.manualWin = ManWindow("manual")
        
        
    def onWhatsnew(self):
        print "onWhatsnew"
        self.whatsnewWin = ManWindow("whatsnew")
        
        
    ###############################
    # def onOpenKef
    # author: Lan Dam
    # updated: 201702
    # * open Kef file, read data into self.dataTabel, keySets then into labelSets
    #   (each set represent for data in a path)
    # * then call self.setData() to set the given data in display
    def onOpenKef(self):
        #print "onOpenKef"
        filename = str(QtGui.QFileDialog.getOpenFileName(directory="/home/", filter="Kef Files(*.kef)"))
        if not filename: return
        
        self.path2file = os.path.dirname (str (filename))
        self.filename = os.path.basename (str (filename)) 
        
        if self.ph5 != None: 
            self.ph5.close()
            del self.ph5
            self.ph5 = None
        self.openTableAction.setEnabled(False)
        #try:
        self.dataTable, self.labelSets, self.totalLines = KefUtility.Kef2TableData(self.statusText, filename)            
        #except Exception, e:
            #QtGui.QMessageBox.warning(self, "Error", str(e) )
            #return
        
        self.setData()
        self.notsave = True

        
    ###############################
    # def onOpenPH5
    # author: Lan Dam
    # updated: 201703
    # Open PH5 file
    # * use KefUtility.GetPrePH5Info give user list of tables and info to select
    #   to get info from KefUtility.PH5toDataTable
    # * call SelectTableDialog for user to select which table(s) to display
    # * in SelectTableDialog, the following tasks will be perfomed:
    #   [Read data into self.dataTable, keySets into labelSets
    #   (each set represent for data in a path)
    #   then call self.setData() to set the given data in display]
    def onOpenPH5(self):
        #print "onOpenPH5"
        filename = str(QtGui.QFileDialog.getOpenFileName(directory="/home/", filter="PH5 Files(*.ph5)"))
        if not filename: return        
        
        self.path2file = os.path.dirname (str (filename))
        self.filename = os.path.basename (str (filename))
        if self.ph5 != None: 
            self.ph5.close()
            del self.ph5
            
        self.ph5, availTables, arrays, shotLines, das = KefUtility.GetPrePH5Info( self.filename, self.path2file)
        
        self.selTableDlg = SelectTableDialog(self, availTables, arrays, shotLines, das)
        
        

    ###############################
    # def onOpenCurrPH5
    # author: Lan Dam
    # updated: 201704
    # Open other tables on the current opened PH5 File
    # * similar to onOpenPH5() but skip the part of opening file to getPrePH5Info
    # * reshow SelTableDlg for user to select which table(s) to display
    # * in SelectTableDialog, the following tasks will be perfomed:
    #   [Read data into self.dataTable, keySets into labelSets
    #    (each set represent for data in a path)
    #    then call self.setData() to set the given data in display]        
    def onOpenCurrPH5(self):
        self.selTableDlg.show()
        self.selTableDlg.move(70,70) # to move to the same position when create new
        
        
        
    ###############################
    # def onSaveKef
    # author: Lan Dam
    # updated: 201704
    # save current table(s) into a kef file
    # * user choose filename
    # * call _saveKeffile() to save kef format into the filename
    # * inform when successfully save and ask to close KefEdit
    def onSaveKef(self):
        #print "onSaveKef"
        if not self._checkAddTableView(): return

        # created suggestedFileName to recommend to user
        if 'kef' in self.filename:
            ss = self.filename.split(".")
            ss[0] += "_editted" 
            suggestedFileName = ".".join(ss)
        else:
            arg = self.arg
            if self.tableType == 'Array_t': arg = "{0:03d}".format( int(arg) )
            if arg!=None: suggestedFileName = self.tableType + "_" + arg
            else: suggestedFileName = self.tableType
            
        suggestedFileName = self.path2file + "/" + suggestedFileName + '.kef'
            
        savefilename = str(QtGui.QFileDialog.getSaveFileName(self,"Save File", suggestedFileName ,
                                                         filter="Kef Files(*.kef)"))
    
        if not savefilename: return        

        # start kef file with the version of KefEdit
        currText = "#\n#\t%s\tKefEdit version: %s" % (time.ctime (time.time ()), PROG_VERSION)

        result = self._saveKeffile(savefilename, currText)
        if result == False: return
        
        msg = "File %s has been saved successfully. \nDo you want to close KEF Editor?" % savefilename
        result = QtGui.QMessageBox.question(self, "Successfully Save File", msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No) 
        
        self.notsave = False        # after saving, reset notsave
        self.statusText.setText("")
        if result == QtGui.QMessageBox.Yes:
            if self.ph5 != None: self.ph5.close()
            QtCore.QCoreApplication.instance().quit()
            sys.exit(application.exec_())            

        
    ###############################
    # def onSavePH5
    # author: Lan Dam
    # updated: 201704
    # update currently opened table(s) to a PH5 file, or create new PH5 file from the opened table(s)
    # * user choose filename to save
    # * call _saveKeffile() to save all tables into the a temp file in kef format
    # * For each table (tab/path) call KefUtility.NukeTable() to remove the table from the PH5 file
    # * call os.system() to run kef2ph5 script to add the tables in temp. kef file to the filename that user chose
    def onSavePH5(self):
        #print "onSavePH5"
        if not self._checkAddTableView(): return
        
        savefilename = str(QtGui.QFileDialog.getSaveFileName(self,"Save File", self.path2file ,
                                                         filter="PH5 Files(*.ph5)"))
        if not savefilename: return 
        options = {}        
        options['path2ph5'] = os.path.dirname (str (savefilename))
        options['outph5file'] = os.path.basename (str (savefilename))        
        
        # save in a temp kef file
        options['keffile'] = keftmpfile
        self._saveKeffile(keftmpfile)
        
        if path.exists(savefilename):
            # remove the table from the ph5 file
            #exp = Experiment.ExperimentGroup (options['path2ph5'], options['outph5file'])
            #exp.ph5open (editmode=True)
            #exp.initgroup ()            
            #for p in self.pathAll: 
                #delResult = KefUtility.NukeTable(self, savefilename, exp, p)
                #if delResult == False: return
            #exp.ph5close ()
            #del exp
            for p in self.pathAll:
                print "Removing existing table %s from PH5file" % p
                self.statusText.setText("Removing existing table %s from PH5file" % p)
                delResult = KefUtility.NukeTable(self, options['outph5file'], options['path2ph5'], p)
                if delResult == False: return
        
        # add tables from kef file to ph5 file
        #cmdStr = "kef2ph5 -n %(outph5file)s -k %(keffile)s -p %(path2ph5)s" % options               
        #print cmdStr % options 
        #os.system(cmdStr % options)
        
        from subprocess import Popen, PIPE, STDOUT
        
        cmdStr = "kef2ph5 -n %(outph5file)s -k %(keffile)s -p %(path2ph5)s" % options  
        self.statusText.setText("Inserting new table %s into PH5file" % p)
        print "Inserting new table %s into PH5file" % p
        p = Popen(cmdStr, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        output = p.stdout.read()
        print "The following command is running:\n", cmdStr    
        print "Output: ", output

        doclose = False
        if 'error' not in output.lower():
            msg = "File %s has been saved successfully. \nDo you want to close KEF Editor?" % savefilename
            result = QtGui.QMessageBox.question(self, "Successfully Save File", msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No) 
            
            self.notsave = False        # after saving, reset notsave
            
            if result == QtGui.QMessageBox.Yes: doclose = True
        else:
            QtGui.QMessageBox.warning(self, "Error in saving to PH5 file", output)
            msg = "Do you want to close KEF Editor?"
            result = QtGui.QMessageBox.question(self, "", msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No) 
                        
            if result == QtGui.QMessageBox.Yes: doclose = True            
            
        self.statusText.setText("")     
        if doclose:
            if self.ph5 != None: self.ph5.close()
            QtCore.QCoreApplication.instance().quit()
            sys.exit(application.exec_())      
            os.unlink(keftmpfile)           # remove keftmpfile
        
        
    ###############################
    # def _checkAddTableView
    # author: Lan Dam
    # updated: 201704    
    # when saving the table, check if the data in AddTableView are all inserted into MainTableView
    def _checkAddTableView(self):
        for tab in self.path_tabs :
            if tab.addDataList != []:
                msg = "There are still data in Add Table View." + \
                      "\nClick 'Cancel' to cancel saving to work on the data." + \
                      "\nClick 'Save' to continue saving."
                      
                result = QtGui.QMessageBox.question(self, "Are you sure?", msg, QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Save )
                if result == QtGui.QMessageBox.Cancel: return False
        return True
    
    
    ###############################
    # def _saveKeffile
    # author: Lan Dam
    # updated: 201704    
    # save all opened tables into the passed savefileme in kef format
    # * loop through tabs, for each tab call tab.ToString appen the table in kef format to currText
    # * save currText into file 'savefilename'
    def _saveKeffile(self, savefilename, currText=""):
        i = 0
        for tab in self.path_tabs : 
            currText, i = tab.ToString(currText,i)
            #if i % 50 == 0: 
            

        try:
            saveFile = open(savefilename, 'w')
            saveFile.write(currText)
        except Exception, e:
            msg = "Can't save the kef file %s due to the error:%s" % (savefilename, str(e))
            QtGui.QMessageBox.warning(self, "Error", msg)            
            return False 
        
        saveFile.close() 
        return True


    ###############################
    # def setData
    # author: Lan Dam
    # updated: 201702 
    # display data for each path in a TablePanel placed in a tab
    # * remove all current tab
    # * loop through each path, create a new tab with that path's data
    # * add the tab to self.path_tabs to delete the tabWidget after removeTab
    # * enable save options
    def setData(self):
        # remove existing tab
        while self.path_tabs != []:
            self.path_tabWidget.removeTab(len(self.path_tabs)-1)
            ptab = self.path_tabs.pop(len(self.path_tabs)-1)
            del ptab
        
        self.processedLine = 0
        # set tab for each path
        self.pathAll = self.dataTable.keys()
        self.pathAll.sort()
        for p in self.pathAll:
            if self.dataTable[p] in [ None, [] ]:
                errMsg = "There are no data for path %s.\n Please check if the selected PH5 is a master file."
                QtGui.QMessageBox.warning(self, "Error", errMsg % p)
                return      
            pathWidget = TablePanel(self, p, self.dataTable[p], self.labelSets[p])
            self.path_tabWidget.addTab(pathWidget, p)
            self.path_tabs.append(pathWidget)
            
        self.saveKefAction.setEnabled(True)
        self.savePH5Action.setEnabled(True) 
        self.statusText.setText("")

        
        
updateColName = QtGui.QColor(245, 225, 225,100).name()            # because there is a difference between color in label and in 
deleteColName = QtGui.QColor(180, 150, 180, 100 ).name()          # table cells
UPDATECOLOR = QtGui.QBrush( QtGui.QColor(225, 175, 175,100) )     # light pink
DELETECOLOR = QtGui.QBrush( QtGui.QColor(70, 10, 70, 100 ) )      # light purple
############### CLASS ####################
#class TablePanel: Each path will have a tableView to display its data
#with path: path in Kef/PH5
#     table: data in list
#     labels: list of columns/keys
class TablePanel(QtGui.QMainWindow):
    def __init__(self, parent, path, table, labels):
        QtGui.QMainWindow.__init__(self)
        self.parent = parent
        self.path = path
        self.table = table
        self.labels = labels
        self.selectedCells = []
        self.updateList = []    # list of rows that have been updated
        self.deleteList = []    # list of rows to delete
        self.addDataList = []   # list of data to add
        self.addCells = None
        
        mainFrame = QtGui.QFrame(self); self.setCentralWidget(mainFrame)
        mainLayout = QtGui.QVBoxLayout(); mainFrame.setLayout(mainLayout)
        
        # set mainTableView
        self.mainTableView = QtGui.QTableWidget(self)
        self.mainTableView.cellClicked.connect(self.OnMainTableClick)
        #self.mainTableView.cellChanged.connect(self.OnCellChanged)
        self.mainTableView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        mainLayout.addWidget(self.mainTableView)        

        # set view range
        self.mainTableView.setColumnCount( len(self.labels) )
        self.mainTableView.setRowCount( len(self.table) )
        
        # set data into cells
        for r in range( len(self.table) ):
            parent.processedLine += 1
            if parent.processedLine % 50 == 0: 
                parent.statusText.setText("Displaying Data on TableView: %s/%s" % (parent.processedLine, parent.totalLines))
            for c in range( len(self.labels) ):
                self.mainTableView.setItem(r, c, QtGui.QTableWidgetItem(self.table[r][c]))

        # change to fit columns with its contents instead of having same default size for all columns   
        self.mainTableView.resizeColumnsToContents()
        
        # set horizontal Headers
        self.mainTableView.setHorizontalHeaderLabels(self.labels)
        self.mainTableView.horizontalHeader().setVisible(True)
        
        # set Tool tip for each horizontal header
        for c in range( len(self.labels) ):
            self.mainTableView.horizontalHeaderItem(c).setToolTip(self.labels[c])

        ###################### change tools ######################
        changeBox = QtGui.QHBoxLayout(); mainLayout.addLayout(changeBox)
        changeBox.setSpacing(40)
        
        changeBox.addStretch(1)
        changeBox.addWidget(QtGui.QLabel("Select Types:"))

        self.singleCell = QtGui.QRadioButton('Single Cell')
        self.singleCell.clicked.connect(self.OnClearSelected)
        changeBox.addWidget(self.singleCell)
        
        self.allInStation = QtGui.QRadioButton('All Similar Cells in Station')
        self.allInStation.clicked.connect(self.OnClearSelected)
        changeBox.addWidget(self.allInStation)
        
        if 'Array_t' in path: self.allInStation.setChecked(True)
        else: 
            self.singleCell.setChecked(True)
            self.allInStation.setEnabled(False)
        
        self.allInColumn = QtGui.QRadioButton('All Similar Cells in Column')
        self.allInColumn.clicked.connect(self.OnClearSelected)
        changeBox.addWidget(self.allInColumn)  
        
        self.changedValCtrl = QtGui.QLineEdit('')
        self.changedValCtrl.setFixedWidth(400)
        changeBox.addWidget(self.changedValCtrl)
        
        self.changeBtn = QtGui.QPushButton('Change', self)
        self.changeBtn.clicked.connect(self.OnChange)
        changeBox.addWidget(self.changeBtn)        
        
        changeBox.addStretch(1)
        
        mainLayout.addWidget(Seperator(thick=2, orientation="horizontal"))
        
        ###################### move tools ######################
        moveBox = QtGui.QHBoxLayout(); mainLayout.addLayout(moveBox)
        
        moveBox.addStretch(1)
        moveBox.addWidget(QtGui.QLabel("Selected Row(s)"))
        self.selectedRowsCtrl = QtGui.QLineEdit('')
        self.selectedRowsCtrl.setFixedWidth(500)
        moveBox.addWidget(self.selectedRowsCtrl)

        moveBox.addWidget(QtGui.QLabel("         Move Selected Row(s) under Line No"))
        self.moveLineCtrl = QtGui.QComboBox(self)
        self.moveLineCtrl.currentIndexChanged.connect(self.OnSelectMoveLine)
        self.moveLineCtrl.clear()
        lineNoList = [str(n) for n in [' top ']+range(1,len(self.table)+1)]
        self.moveLineCtrl.addItems( lineNoList )
        moveBox.addWidget(self.moveLineCtrl)  
    
        self.moveBtn = QtGui.QPushButton('Move', self)
        self.moveBtn.setFixedWidth(90)
        self.moveBtn.clicked.connect(self.OnMove)
        moveBox.addWidget(self.moveBtn) 
        
        moveBox.addStretch(1)
        
        mainLayout.addWidget(Seperator(thick=2, orientation="horizontal"))
        
        ###################### delete tools ######################
        deleteBox = QtGui.QHBoxLayout(); mainLayout.addLayout(deleteBox)
        
        deleteBox.addStretch(1) 
        self.deleteBtn = QtGui.QPushButton('Delete Row(s) on Selected Cell(s)', self)
        self.deleteBtn.setFixedWidth(400)
        self.deleteBtn.clicked.connect(self.OnDelete)
        deleteBox.addWidget(self.deleteBtn)
        
        deleteBox.addSpacing(250)
        self.unDeleteBtn = QtGui.QPushButton('UnDelete', self)
        self.unDeleteBtn.setFixedWidth(400)
        self.unDeleteBtn.clicked.connect(self.OnUndelete)
        deleteBox.addWidget(self.unDeleteBtn)        
        
        deleteBox.addStretch(1) 
        
        mainLayout.addWidget(Seperator(thick=2, orientation="horizontal"))
        
        ###################### add tools ######################
        addBox = QtGui.QHBoxLayout(); mainLayout.addLayout(addBox)
        
        addBox.addStretch(1) 
        self.addBtn = QtGui.QPushButton('Add Row(s) with Data Copy from Selected Cell(s)', self)
        self.addBtn.setFixedWidth(400)
        self.addBtn.clicked.connect(self.OnAdd)
        addBox.addWidget(self.addBtn)
        
        addBox.addSpacing(250)
        addBox.addWidget(QtGui.QLabel("Insert Selected Row(s) under Line No"))
        self.insertLineCtrl = QtGui.QComboBox(self)
        self.insertLineCtrl.currentIndexChanged.connect(self.OnSelectAddLine)
        self.insertLineCtrl.clear()
        lineNoList = [str(n) for n in [' top ']+range(1,len(self.table)+1)]
        self.insertLineCtrl.addItems( lineNoList )
        addBox.addWidget(self.insertLineCtrl)  
    
        self.insertBtn = QtGui.QPushButton('Insert', self)
        self.insertBtn.setFixedWidth(90)
        self.insertBtn.clicked.connect(self.OnInsert)
        addBox.addWidget(self.insertBtn) 
        
        addBox.addStretch(1) 
        
        # addTableView: to view all rows to add
        self.addTableView = QtGui.QTableWidget(self)
        self.addTableView.setMaximumHeight(200)
        self.addTableView.cellClicked.connect(self.OnAddTableClick)
        self.addTableView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        mainLayout.addWidget(self.addTableView)  
        
        self._setButtonsDisabled()
        
        
    ###############################
    # def _setButtonsDisabled
    # author: Lan Dam
    # updated: 201703
    # disabled all buttons (at the beginning and when change selection criteria)
    def _setButtonsDisabled(self):
        self.changeBtn.setEnabled(False)
        self.moveBtn.setEnabled(False)
        self.moveLineCtrl.setEnabled(False)
        self.deleteBtn.setEnabled(False)
        self.unDeleteBtn.setEnabled(False)
        self.addBtn.setEnabled(False)
        self.insertBtn.setEnabled(False)
        self.insertLineCtrl.setEnabled(False)


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
        #print "OnMainTableClick"
        self.changeBtn.setEnabled(True)
        self.insertBtn.setEnabled(False)
        self.insertLineCtrl.setEnabled(False) 

        # clear selection in addTableView if there is some
        if self.addCells != None:
            self.addTableView.clearSelection()
            self.addCells = None                # so that OnChange will take effect on mainTable
            
        ### Identify which cell(s) are selected
        value = self.mainTableView.item(row,column).text()
        if self.singleCell.isChecked():
            self.selectedCells = [(row,column)]
            selectedRows = [str(row + 1)]
            
        elif self.allInStation.isChecked():
            # get all entries that have the same stationName with the selected cell
            statCol = self.labels.index('id_s')
            statName = self.mainTableView.item(row,statCol).text()
            # statRowList: all rows with station id similar to selected row's stationid
            statRowList = [i for i in range(len(self.table)) if self.table[i][statCol]==statName]
            # mark selected for that station's cells that have the same value
            self.selectedCells, selectedRows = self._selectMatchInList(value, column, statRowList, self.mainTableView)
                    
        elif self.allInColumn.isChecked():
            # mark selected for that column cells that have the same value
            self.selectedCells, selectedRows = self._selectMatchInList(value, column, range(len(self.table)), self.mainTableView)
            
        self.changedValCtrl.setText(value)
        self.selectedRowsCtrl.setText('-'.join(selectedRows))
        
        ### Identify which options should be enable
        if self.allInStation.isChecked() or self.singleCell.isChecked():
            # enable add and delete options
            self.addBtn.setEnabled(True)      
            noDel = True
            undelApplicable = True
            for r,c in self.selectedCells:
                if r not in self.deleteList: 
                    undelApplicable = False
                else:
                    noDel = False
            if undelApplicable:                     # all rows have been deleted allow undelete option
                self.unDeleteBtn.setEnabled(True)
                self.deleteBtn.setEnabled(False)
            else:
                self.unDeleteBtn.setEnabled(False)
                self.deleteBtn.setEnabled(True)
                
            if noDel:                               # no rows have been deleted allow move option
                self.moveBtn.setEnabled(True)
                self.moveLineCtrl.setEnabled(True) 
            else:
                self.moveBtn.setEnabled(False)
                self.moveLineCtrl.setEnabled(False)                
                
        else:
            # disable move, add, delete, undelete options when too many cells are selected
            self.moveBtn.setEnabled(False)
            self.moveLineCtrl.setEnabled(False)   
            self.addBtn.setEnabled(False)            
            self.deleteBtn.setEnabled(False)
            self.unDeleteBtn.setEnabled(False)        


    ###############################
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
        
        # clear selection in mainTableView
        self.mainTableView.clearSelection()
        self.selectedCells = []
        
        value = self.addTableView.item(row,column).text()
        if self.singleCell.isChecked():
            self.addCells = [(row,column)]
        elif self.allInStation.isChecked():
            # get all entries that have the same stationName with the selected cell
            statCol = self.labels.index('id_s')
            statName = self.addTableView.item(row,statCol).text()
            statRowList = [i for i in range(len(self.addDataList)) if self.addDataList[i][statCol]==statName]            
            # mark selected for that station's cells that have the same value
            self.addCells, selectedRows = self._selectMatchInList(value, column, statRowList, self.addTableView) 
        else:
            # mark selected for that column cells that have the same value
            self.addCells, selectedRows = self._selectMatchInList(value, column, range(len(self.addDataList)), self.addTableView)
        
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
            currItem = tableView.item(r,column)
            if value == currItem.text():
                currItem.setSelected(True) 
                selectedCells.append((r,column))
                selectedRows.append(str(r+1))
                #print "%s-%s" % (self.table[r][0], self.table[r][-1])
        return selectedCells, selectedRows
                
                
    ###############################
    # def OnChange
    # author: Lan Dam
    # updated: 201703
    # Change the values of the selected cells into the value in changedValCtrl
    #    on MainTableView if self.addCells == None
    #     * not change if there are any rows deleted
    #     * change text in cell(s)
    #     * if the change is back to the orginal value, cell color will be resetted (then rows => remove from updateList)
    #     * else: change foreground color of cell(s), change background color of row(s) => add to updateList if not in updateList yet
    #    on AddTableView if self.addCells != None
    #     * change text & color in cell(s)
    def OnChange(self, event):
        if self.addCells == None:
            for r,c in self.selectedCells:
                if r in self.deleteList: 
                    msg = "Because the row %s has been deleted, cell (%s,%s) can't be changed." % (r+1, r+1,c+1)
                    QtGui.QMessageBox.warning(self, "Warning", msg )
                    continue                
   
                self.mainTableView.item(r,c).setText(self.changedValCtrl.text())
                # colors are changed in OnCellChanged
                currItem = self.mainTableView.item(r,c)
                
                if currItem.text() == self.table[r][c]:
                    currItem.setForeground(QtCore.Qt.black)
                    updated = False
                    for l in range(len(self.labels)):
                        if self.mainTableView.item(r,l).text() != self.table[r][l]:
                            updated = True
                            break
                    if updated == False:
                        self._changeRowBackground(r, QtCore.Qt.white)
                        if r in self.updateList: self.updateList.remove(r)
                else:
                    currItem.setForeground(QtCore.Qt.red)
                    self._changeRowBackground(r, UPDATECOLOR)
                    if r not in self.updateList: self.updateList.append(r)                

        else:
            for r,c in self.addCells:
                currItem = self.addTableView.item(r,c)
                currItem.setText(self.changedValCtrl.text())
                currItem.setForeground(QtCore.Qt.red)
                self.addDataList[r][c] = str(self.changedValCtrl.text())
                
            
    ###############################
    # def OnDelete
    # author: Lan Dam
    # updated: 201703
    # * change color of selected Cells to DELETECOLOR
    # * add those rows to self.deleteList
    # * disable delete option, enable undelete option
    def OnDelete(self, event):
        for row,column in self.selectedCells:
            currItem = self.mainTableView.item(row,column)
            self._changeRowBackground(row, DELETECOLOR)
            if row not in self.deleteList: self.deleteList.append(row)  
            
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
        for row,column in self.selectedCells:
            currItem = self.mainTableView.item(row,column)
            if row in self.updateList: 
                self._changeRowBackground(row, UPDATECOLOR)
            else:
                self._changeRowBackground(row, QtCore.Qt.white)
            if row in self.deleteList: self.deleteList.remove(row)
            
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
            self.addDataList.append(deepcopy(self.table[row]))
        
        # clear existing data
        self.addTableView.clear()
        
        # set view range
        self.addTableView.setColumnCount( len(self.labels) )
        self.addTableView.setRowCount( len(self.addDataList) )
        
        # set data into cells
        for r in range( len(self.addDataList) ):
            for c in range( len(self.labels) ):
                self.addTableView.setItem(r, c, QtGui.QTableWidgetItem(self.addDataList[r][c]))

        # change to fit columns with its contents instead of having same default size for all columns
        self.addTableView.resizeColumnsToContents()

        # set horizontal Headers
        self.addTableView.setHorizontalHeaderLabels(self.labels)
        self.addTableView.horizontalHeader().setVisible(True)
        
        # set Tool tip for each horizontal header
        for c in range( len(self.labels) ):
            self.addTableView.horizontalHeaderItem(c).setToolTip(self.labels[c])
            
            
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
            self.mainTableView.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
            lineId = int(val)-1
            self.mainTableView.selectRow(lineId)
            #self.mainTableView.scrollTo(self.mainTableView.item(lineId,0))
            self.mainTableView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
            
            
    ###############################    
    # def OnInsert
    # author: Lan Dam
    # updated: 201704 
    # remove selectedRows from self.addDataList + AddTableView and add to MainTableView
    # * pop selected from their postions in addTableView
    # * insert into new postions in MainTableView    
    def OnInsert(self, event):
        insertLineId = self.insertLineCtrl.currentIndex()
        self.addCells.sort(key=itemgetter(0),reverse=True)
        
        # identify data to insert to mainTableView and 
        # remove data from its current position in addDataList and addTableView
        insertedData = []
        for r,c in self.addCells:
            rowData = deepcopy(self.addDataList[r])
            insertedData.append(rowData)
            self.addDataList.remove(rowData)
            self.addTableView.removeRow(r)
        
        # insert the data to MainTableView
        self._insertDataToTable(insertLineId, insertedData, len(insertedData))
        
        
    ###############################    
    # def OnMove
    # author: Lan Dam
    # updated: 201704
    # move selectedRows to new positions in MainTableView
    # * pop selected from their postions in MainTableView
    # * insert into new postions in MainTableView
    def OnMove(self, event):
        self.selectedCells.sort(key=itemgetter(0),reverse=True)
        selectedRows = [r[0] for r in self.selectedCells]        

        moveLineId = self.moveLineCtrl.currentIndex()
        if moveLineId in selectedRows: 
            msg = "Cannot move the select row(s) to a line No \nthat in the range of the selected rows"
            QtGui.QMessageBox.warning(self, "Warning", msg )
            return
        
        # reidentify new moveLineId when pop the selected Rows from table 
        if moveLineId > max(selectedRows): moveLineId -= len(selectedRows)
        
        # identify data to insert to mainTableView and 
        # remove data from its current position in table and mainTableView
        insertedData = []
        for r in selectedRows:
            rowData = deepcopy(self.table[r])
            insertedData.append( rowData )
            self.table.remove(rowData) 
            self.mainTableView.removeRow(r)        
        
        # insert the data to MainTableView
        self._insertDataToTable( moveLineId, insertedData, len(selectedRows), max(selectedRows) )
                        

    ###############################    
    # def _insertDataToTable
    # author: Lan Dam
    # updated: 201704    
    # insert the passed insertData into the passed lineId in MainTableView
    def _insertDataToTable(self, lineId, insertData, lenInsert, maxRemovedRow=None):
        for rowData in insertData:  
            # add inserted data into self.table 
            # since insertData in backward order, the previous insert can be moved downward
            # lineId can be used for inserting without any changes 
            self.table.insert(lineId, rowData)    
            # create new empty row in mainTableView
            self.mainTableView.insertRow(lineId)
            # fill value in rowData into the empty row
            for c in range( len(self.labels) ):
                self.mainTableView.setItem(lineId, c, QtGui.QTableWidgetItem(rowData[c]))
        
        # update values in deleteList and updateList
        lineId -= 1
        for i in range(len(self.deleteList)):
            # delete row ids should be moved downward when there are rows inserted before them
            if self.deleteList[i] > lineId: self.deleteList[i] += lenInsert
            # delete row ids should be moved upward when there are rows removed before them
            if maxRemovedRow!=None and self.deleteList[i] > maxRemovedRow: self.deleteList[i] -= lenInsert
            
        for i in range(len(self.updateList)):
            # update row ids should be moved downward when there are rows inserted before them
            if self.updateList[i] > lineId: self.updateList[i] += lenInsert 
            # update row ids should be moved upward when there are rows removed before them
            if maxRemovedRow!=None and self.updateList[i] > maxRemovedRow: self.updateList[i] -= lenInsert
    

    ###############################    
    # def _changeRowBackground
    # author: Lan Dam
    # updated: 201703
    # change the background of the given row to the given color by changing color of each cell
    def _changeRowBackground(self,row, color):
        for column in range(self.mainTableView.columnCount()):
            self.mainTableView.item(row,column).setBackground(color)
        

    ###############################    
    # def ToString
    # author: Lan Dam
    # updated: 201703
    # convert the data in mainTableViews to string in kef format
    # * if the row in deleteList, skip
    # * if the row in updateList, its values are in the tableViews so just keep converting from mainTableView
    def ToString(self, currText, tableCount):
        for r in range( self.mainTableView.rowCount() ):
            if r in self.deleteList: continue
            tableCount += 1
            if tableCount % 100 == 0: 
                self.parent.statusText.setText("Saving Kef file: %s/%s" % ( tableCount, self.parent.totalLines))     
                print "Saving Kef file: %s/%s" % ( tableCount, self.parent.totalLines)             
            currText += "\n#   Table row %d" % tableCount            
            #   Print table name
            currText += "\n" + self.path
            for c in range( self.mainTableView.columnCount() ):  
                val = self.mainTableView.item(r,c).text()
                currText += "\n\t%s=%s" % (self.labels[c], val)
        
        return currText, tableCount


##########################################
############### CLASS ####################
# Author: Lan
# Updated: 201703
# CLASS: SelectTableDialog - GUI for user to select parameters for table
class SelectTableDialog(QtGui.QDialog):
    def __init__(self, parent, availTables, arrays, shotLines, das):
        
        QtGui.QWidget.__init__(self)
        self.setWindowTitle("Select Tables")
        self.parent = parent
        mainLayout = QtGui.QVBoxLayout(self)
        
        mainLayout.addWidget(QtGui.QLabel('What table do you want to get info from?'))
        
        formLayout = QtGui.QFormLayout() ; mainLayout.addLayout(formLayout)
        
        self.tableCtrl = QtGui.QComboBox(self)
        self.tableCtrl.clear()
        self.tableCtrl.addItems( [''] + availTables )
        formLayout.addRow("Table", self.tableCtrl)
        self.tableCtrl.currentIndexChanged.connect(self.OnSelectTable)

        self.arrayCtrl = QtGui.QComboBox(self)
        self.arrayCtrl.clear()
        self.arrayCtrl.addItems( [''] + arrays )
        formLayout.addRow("Array", self.arrayCtrl)
        
        self.shotLineCtrl = QtGui.QComboBox(self)
        self.shotLineCtrl.clear()
        self.shotLineCtrl.addItems( [''] + shotLines )
        formLayout.addRow("ShotLine", self.shotLineCtrl) 

        self.dasCtrl = QtGui.QComboBox(self)
        self.dasCtrl.clear()
        self.dasCtrl.addItems( [''] + das )
        formLayout.addRow("Das", self.dasCtrl)
        
        btnLayout = QtGui.QHBoxLayout() ; mainLayout.addLayout(btnLayout)
        
        btnLayout.stretch(1)
        submitBtn = QtGui.QPushButton('Submit', self)
        submitBtn.clicked.connect(self.OnSubmit)
        btnLayout.addWidget(submitBtn)
        btnLayout.stretch(1)
        cancelBtn = QtGui.QPushButton('Cancel', self)
        cancelBtn.clicked.connect(self.OnCancel)
        btnLayout.addWidget(cancelBtn)
        btnLayout.stretch(1)
        
        #self.setLayout(mainLayout)
        self._disableCtrls()
        self.show()  


    def OnCancel(self, evt):
        self.close()
        
        
    def _disableCtrls(self):
        self.arrayCtrl.setEnabled(False)
        self.shotLineCtrl.setEnabled(False)
        self.dasCtrl.setEnabled(False)
        
        
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
            self.arrayCtrl.setEnabled(True)
            self.shotLineCtrl.setEnabled(True)

        
    ###############################    
    # def OnSubmit
    # author: Lan Dam
    # updated: 201703   
    # use KefUtility.PH5toTableData to read the required table into dataTable
    # call parent.setData() to set dataTable into MainTableView
    def OnSubmit(self, evt):
        p = self.parent
        p.tableType = str( self.tableCtrl.currentText() )
        
        errorCtrls = []
        if p.tableType == 'Array_t':     
            p.arg = str( self.arrayCtrl.currentText() )
            if p.arg == "": errorCtrls.append('Array')
        elif p.tableType == 'Event_t':   
            p.arg = str( self.shotLineCtrl.currentText() )
            if p.arg == "": errorCtrls.append('ShotLine')
        elif p.tableType == 'Das_t':   
            p.arg = str( self.dasCtrl.currentText() )
            if p.arg == "": errorCtrls.append('Das')
        elif p.tableType == 'Offset_t': 
            a = str( self.arrayCtrl.currentText() )
            if a == "": errorCtrls.append("Array")
            s = str( self.shotLineCtrl.currentText() )
            if a == "": errorCtrls.append("ShotLine")
            p.arg = "%s_%s" % (a,s)
        else:
            p.arg = None
            
            
        if errorCtrls != []:
            msg = "For Table '%s', %s must be selected." % (p.tableType, ' and '.join(errorCtrls))
            QtGui.QMessageBox.warning(self, "Warning", msg )
            return
        
        #try:
        p.dataTable, p.labelSets, p.totalLines = KefUtility.PH5toTableData(p.statusText, p.ph5, p.filename, p.path2file, p.tableType, p.arg )            
        #except Exception, e:
            #QtGui.QMessageBox.warning(self, "Error", str(e) )
            #return

        p.setData() 
        p.openTableAction.setEnabled(True)
        p.notsave == True
        self.close()

        
############### CLASS ####################
# Author: Lan
# Updated: 201409
# CLASS: Seperator - is the line to separate in the Gui (reuse from PH5View)
class Seperator(QtGui.QFrame):
    def __init__(self, thick=2, orientation="horizontal", length=None):
        QtGui.QFrame.__init__(self)
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.setFrameShadow(QtGui.QFrame.Sunken)
        if orientation == 'horizontal':
            self.setFixedHeight(thick)
            if length != None:
                self.setFixedWidth(length)
        else:
            self.setFixedWidth(thick)
            if length != None:
                self.setFixedHeight(length)
                
                
##########################################
############### CLASS ####################
# Author: Lan
# Updated: 201702
# CLASS: ManWindow - show Manual of the app. (reuse from PH5View)
class ManWindow(QtGui.QWidget):
    def __init__(self, mantype=""):
        QtGui.QWidget.__init__(self)

        view = QWebView(self)
        if mantype=="manual":
            file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "KefEdit_Manual.html"))
            if os.path.isfile(file_path): 
                local_url = QtCore.QUrl.fromLocalFile(file_path)   
                #view.load(local_url )
                view.setUrl(local_url)
            else:
                msg = "The hyperlinks to bookmarks in the manual cannot work \n" + \
                      "becaulse the file KefEdit_Manual.html is missing.\n" +\
                      "To move to the interested section, use scrollbar."
                QtGui.QMessageBox.question(self, 'Warning', msg, QtGui.QMessageBox.Ok)
                view.setHtml(html_manual)
        
        elif mantype=="whatsnew":
            view.setHtml(html_whatsnew % PROG_VERSION)
        self.layout = QtGui.QHBoxLayout()
        self.layout.addWidget(view)

        self.setLayout(self.layout)
        self.show() 
        

html_manual = '''
<html>
<head>
<style>
table, th, td {
    border: 1px solid black;
}
</style>
<title>Manual Page</title>
</head>
<body>
<h2>Manual</h2>
<hr />

<h2><a id="contents">Contents:</a></h2>
<ul>
    <li><a href="#OpenKef">Open Kef File</a></li> 	
    <li><a href="#OpenPH5">Open PH5 File</a></li>
    <li><a href="#OpenTableInCurr">Open table(s) in the current PH5 File</a></li>
    <li><a href="#SaveKef">Save as Kef File</a></li>
    <li><a href="#SavePH5">Save as PH5 File</a></li>
    <li><a href="#EditTable">Edit Table</a></li>
    <ul>
        <li><a href="#Select">Select Cell(s)</a></li> 
        <li><a href="#Change">Change value in (a) cell(s)</a></li> 
        <li><a href="#Move">Move Selected Row(s) to a new position</a></li> 
        <li><a href="#Delete">Delete Row(s) on Selected Cell(s)</a></li>
        <li><a href="#Add">Add Row(s) with Data Copy from Selected Cell(s)</a></li>
    </ul>
</ul>

&nbsp;
<table style="width:100%">
<tbody>
<tr>
<td>
<h2><a id="OpenKef">Open Kef File</a></h2>
<div>Select Menu File - Open Kef File: to open all tables in a Kef file for editing. Each table is placed in a tab.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>
<h2><a id="OpenPH5">Open PH5 File</a></h2>
<div>Select Menu File - Open PH5 File: to open (a) table(s) in a PH5 File for editing. Each table is placed in a tab.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>
<h2><a id="OpenTableInCurr">Open table(s) in the current PH5 File</a></h2>
<div>Open (a) different table(s) in the currently opened PH5 File for editing. Similar to Open a PH5 File but user doenn't need to select a file to open, the app. doesn't need to reopen the file.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>
<h2><a id="SaveKef">Save Kef File</a></h2>
<div>Save the opened table(s) to a Kef File.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>
<h2><a id="SavePH5">Save PH5 File</a></h2>
<div>Update the a PH5 file with the opened tables OR create a new PH5 file from the tables. </div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>
<h2><a id="EditTable">Edit Table</a></h2>

<h3><a id="Select">Select Cell(s)</a></h3> 
<div>Select Type: Define which cell(s) will be selected when click on a cell.</div>
<ul>
    <li>Single Cell: Only that cell will be selected.</li>
    <li>All Similar Cells in Station: All similar value cells that have the same station id with the clicked cell will be selected. Avalaible only for Array Table.</li>
    <li>All Similar Cells in Column: All similar value cells in that column will be selected. (E.g. when user want to change value for time, this option allow user to make sure all the necessary times are changed consistently.) When this option is selected, move, delete and add options are disabled to prevent going out of control.
</ul>

<h3><a id="Change">Change value in (a) cell(s)</a></h3>
<div>When a cell is clicked, its value will appear in the text box next to the three Select Types so that its value can be editted.</div>
<div>User can click on button 'Change' to update the new value to the selected cell(s). If the new value is different with the original values, the row(s) on the selected cell(s) will change color to pink.</div>

<h3><a id="Move">Move Selected Row(s) to a new position</a></h3>
<div>When cell(s) are selected, the corresponding row(s) will be shown in Selected Rows (for the ease of following up).</div>
<div>User will choose the Line No (next to 'Move Selected Row(s) under Line No') under which the row(s) will be moved to, then click 'Move'.</div>

<h3><a id="delete">Delete Row(s) on Selected Cell(s)</a></h3>
<div>To delete Selected Row(s), just click on 'Delete Row(s) on Selected Cell(s)', the row(s) will change color to purple to mark that the row(s) are deleted.</div>
<div>User can change their mind by selecting the deleted row(s) again and click on 'UnDelete'.</div>

<h3><a id="Add">Add Row(s) with Data Copy from Selected Cell(s)</a></h3>
<ul>
    <li>Move Selected Row(s) to the Add Row View at the bottom of the GUI by clicking on 'Add Row(s) with Data Copy from Selected Cell(s)'</li>
    <li>Change value of (a) cell(s) in Add Row View by click on cell(s) to change its/their value(s) in the text box similar to 'Change value in (a) cell(s)' described <a href="#Change">above</a></li>
    <li>Insert Selected Rows in Add Row View to the Main View by select the the Line No (next to 'Insert Selected Row(s) under Line No') under which the row(s) will be inserted to, then click 'Insert'.</div>
</ul>

<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
</tbody>
</table>
</body>
</html>
'''

html_whatsnew = """
<html>
<head>
<title>What's new? Page</title>
</head>
<body>
<h2>What's new in version %s?</h2>
<hr />
<div>This is the first version of KefEdit. Changes will be updated in need.</div>
</body>
</html>
"""
                        
if __name__ == "__main__":
    application = QtGui.QApplication(sys.argv)

    win = KefEdit()
    
    sys.exit(application.exec_())
