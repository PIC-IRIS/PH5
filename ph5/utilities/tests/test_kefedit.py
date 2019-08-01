"""
unit tests for nuke_table
"""

import unittest
from ph5.utilities import kefedit
from ph5.core import kefutility, ph5api
import sys
import os
import stat
from numpy import testing as numptest
from shutil import copyfile
from mock import patch
from StringIO import StringIO
from html.parser import HTMLParser
try:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtTest import QTest
except Exception:
    LOGGER.error("PyQt4 must be installed for this to run")



def getPushButton(widget, text):
    """
    Get the QPushButton identified by text on the widget
    """
    buttons = widget.findChildren(QtGui.QPushButton)
    return [btn for btn in buttons if btn.text() == text][0]


def tableViewClick(tableview, row, column):
    x = tableview.columnViewportPosition(column)
    y = tableview.rowViewportPosition(row)
    QTest.mouseClick(tableview.viewport(), QtCore.Qt.LeftButton,
                     pos=QtCore.QPoint(x + 2, y + 2))


class TestSeparator(unittest.TestCase):
    """
    test Separator class
    """
    def test_init(self):
        """
        test constructor
        """
        self.sep = kefedit.Separator(
            thick=3, orientation='horizontal', length=700)
        size = self.sep.size()
        self.assertEqual(3, size.height())
        self.assertEqual(700, size.width())
        del self.sep

        self.sep = kefedit.Separator(
            thick=3, orientation='vertical', length=700)
        size = self.sep.size()
        self.assertEqual(3, size.width())
        self.assertEqual(700, size.height())
        del self.sep

    def tearDown(self):
        try:
            del self.sep
        except Exception:
            pass

class TestManWindow(unittest.TestCase):
    """
    test ManWindow class
    """
    def test_init(self):
        """
        test constructor
        """
        # wrong mantype
        self.manwin = kefedit.ManWindow("manul")
        self.assertEqual('', self.manwin.view.toPlainText())
        del self.manwin
        # html_manual
        self.manwin = kefedit.ManWindow("manual")
        testview = QtGui.QTextBrowser(None)
        testview.setText(kefutility.html_manual)
        self.assertEqual(testview.toPlainText(), self.manwin.view.toPlainText())
        del self.manwin
        # whatsnew
        self.manwin = kefedit.ManWindow("whatsnew")
        testview = QtGui.QTextBrowser(None)
        testview.setText(kefutility.html_whatsnew % kefedit.PROG_VERSION)
        self.assertEqual(testview.toPlainText(), self.manwin.view.toPlainText())
        del self.manwin

    def tearDown(self):
        try:
            del self.manwin
        except Exception:
            pass


class TestSelectTableDialog(unittest.TestCase):
    """
    test ManWindow class
    """
    def setUp(self):
        # define kefedit for selTableDlg's parent
        self.kefedit = kefedit.KefEdit()
        self.kefedit.filename = 'master.ph5'
        self.kefedit.path2file = 'ph5/test_data/ph5'
        self.kefedit.ph5api = None
        self.availTables = None
        self.arrays = None
        self.shotLines = None
        self.offsets = None
        self.das = None
        # get data for selTableDlg
        self.kefedit.ph5api, self.availTables, self.arrays, self.shotLines, \
            self.offsets, self.das = \
            kefutility.GetPrePH5Info('master.ph5', 'ph5/test_data/ph5')
        # define selTableDlg
        self.selTableDlg = kefedit.SelectTableDialog(
            self.kefedit, self.availTables, self.arrays, self.shotLines,
            self.offsets, self.das)

    def assertComboBoxItems(self, srcList, comboBox):
        allItems = [str(comboBox.itemText(i))
                    for i in range(comboBox.count())]
        self.assertEqual(allItems, [''] + srcList)

    def test_init(self):
        """
        test constructor
        """
        # check items in ComboBox
        self.assertComboBoxItems(self.availTables, self.selTableDlg.tableCtrl)
        self.assertComboBoxItems(self.arrays, self.selTableDlg.arrayCtrl)
        self.assertComboBoxItems(self.shotLines, self.selTableDlg.shotLineCtrl)
        self.assertComboBoxItems(self.offsets, self.selTableDlg.offsetCtrl)
        self.assertComboBoxItems(self.das, self.selTableDlg.dasCtrl)

        # check if arrayCtrl, shotLineCtrl, dasCtrl, offsetCtrl
        self.assertFalse(self.selTableDlg.arrayCtrl.isEnabled())
        self.assertFalse(self.selTableDlg.shotLineCtrl.isEnabled())
        self.assertFalse(self.selTableDlg.dasCtrl.isEnabled())
        self.assertFalse(self.selTableDlg.offsetCtrl.isEnabled())

    def test_OnCancel(self):
        """
        test click Cancel button
        """
        cancelBtn = getPushButton(self.selTableDlg, 'Cancel')
        QTest.mouseClick(cancelBtn, QtCore.Qt.LeftButton)
        self.assertFalse(self.selTableDlg.isVisible())

    def test__disableCtrls(self):
        """
        test _disableCtrls method
        """
        self.selTableDlg.arrayCtrl.setEnabled(True)
        self.selTableDlg.shotLineCtrl.setEnabled(True)
        self.selTableDlg.dasCtrl.setEnabled(True)
        self.selTableDlg.offsetCtrl.setEnabled(True)
        self.selTableDlg._disableCtrls()
        self.assertFalse(self.selTableDlg.arrayCtrl.isEnabled())
        self.assertFalse(self.selTableDlg.shotLineCtrl.isEnabled())
        self.assertFalse(self.selTableDlg.dasCtrl.isEnabled())
        self.assertFalse(self.selTableDlg.offsetCtrl.isEnabled())

    def assertTXTvsCBOX(self, txtSelected, cbox=None):
        """
        when select txtSelected on ComboBox tableCtrl,
        check if comboBox cbox is enabled and others are disabled
        """
        self.selTableDlg.tableCtrl.setCurrentIndex(
            self.availTables.index(txtSelected) +1)

        comboBoxes = {self.selTableDlg.arrayCtrl: 'Array',
                      self.selTableDlg.shotLineCtrl: 'ShotLine',
                      self.selTableDlg.dasCtrl: 'Das',
                      self.selTableDlg.offsetCtrl: 'Offset'}
        if cbox is not None:
            self.assertTrue(cbox.isEnabled())
            removeCboxList = [o for o in comboBoxes if o is not cbox]
        else:
            removeCboxList = comboBoxes
        for o in removeCboxList:
            if o.isEnabled():
                raise AssertionError(
                    "ComboBox '%s' is enabled while it is supposed to be "
                    "disabled" % comboBoxes[cbox])

    def test_OnSelectTable(self):
        """
        test OnSelectTable method
        """
        # select table Array_t
        self.assertTXTvsCBOX('Array_t', self.selTableDlg.arrayCtrl)

        # select table offsetCtrl
        self.assertTXTvsCBOX('Offset_t', self.selTableDlg.offsetCtrl)

        # select table Event_t
        self.assertTXTvsCBOX('Event_t', self.selTableDlg.shotLineCtrl)

        # select table Das_t
        self.assertTXTvsCBOX('Das_t', self.selTableDlg.dasCtrl)

        # select table Sort_t
        self.assertTXTvsCBOX('Sort_t')
        
    def assertOnSubmit(self, submitBtn, txtSelected, paths, rowcounts,
                       comboBox=None, indexSelected=None):
        if len(paths) != len(rowcounts):
            raise Exception("'path' and 'rowCounts' must have the same len.")
        try:
            self.selTableDlg.tableCtrl.setCurrentIndex(
                        self.availTables.index(txtSelected) +1)
        except ValueError:
            raise AssertionError("%s isn't listed in tableCtrl." % txtSelected)
        if indexSelected is not None:
            comboBox.setCurrentIndex(indexSelected)

        QTest.mouseClick(submitBtn, QtCore.Qt.LeftButton)

        self.assertEqual(len(paths), len(self.kefedit.path_tabs))
        for i in range(len(paths)):
            self.assertEqual(paths[i], self.kefedit.path_tabs[i].path)
            self.assertEqual(
                rowcounts[i],
                self.kefedit.path_tabs[i].mainTableView.rowCount())
        self.assertTrue(self.kefedit.saveKefAction.isEnabled())
        self.assertTrue(self.kefedit.savePH5Action.isEnabled())
        self.assertTrue(self.kefedit.saveCSVAction.isEnabled())
        self.assertTrue(self.kefedit.openTableAction.isEnabled())
        self.assertTrue(self.kefedit.updatePH5Action.isEnabled())

    def test_OnSubmit(self):
        """
        test OnSubmit method
        """
        submitBtn = getPushButton(self.selTableDlg, 'Submit')
        self.assertOnSubmit(
            submitBtn, 'Array_t',
            ['/Experiment_g/Sorts_g/Array_t_001'], [3],
            self.selTableDlg.arrayCtrl, 1)

        self.assertOnSubmit(
            submitBtn, 'All_Array_t',
            ['/Experiment_g/Sorts_g/Array_t_001',
             '/Experiment_g/Sorts_g/Array_t_002',
             '/Experiment_g/Sorts_g/Array_t_003',
             '/Experiment_g/Sorts_g/Array_t_004',
             '/Experiment_g/Sorts_g/Array_t_008',
             '/Experiment_g/Sorts_g/Array_t_009'],
            [3, 1, 1, 1, 3, 1])

        self.assertOnSubmit(
            submitBtn, 'Event_t',
            ['/Experiment_g/Sorts_g/Event_t_001'], [1],
            self.selTableDlg.shotLineCtrl, 1)

        self.assertOnSubmit(
            submitBtn, 'All_Event_t',
            ['/Experiment_g/Sorts_g/Event_t_001'], [1])

        self.assertOnSubmit(
            submitBtn, 'Offset_t',
            ['/Experiment_g/Sorts_g/Offset_t_001_001'], [1],
            self.selTableDlg.offsetCtrl, 1)

        self.assertOnSubmit(
            submitBtn, 'All_Offset_t',
            ['/Experiment_g/Sorts_g/Offset_t_001_001',
             '/Experiment_g/Sorts_g/Offset_t_002_001',
             '/Experiment_g/Sorts_g/Offset_t_003_001',
             '/Experiment_g/Sorts_g/Offset_t_004_001',
             '/Experiment_g/Sorts_g/Offset_t_008_001',
             '/Experiment_g/Sorts_g/Offset_t_009_001'],
            [1, 1, 1, 1, 1, 1])

        self.assertOnSubmit(
            submitBtn, 'Das_t',
            ['/Experiment_g/Receivers_g/Das_g_12183/Das_t'], [9],
            self.selTableDlg.dasCtrl, 1)

        self.assertOnSubmit(
            submitBtn, 'Experiment_t',
            ['/Experiment_g/Experiment_t'], [1])

        # Report_t is not in the list
        self.assertRaises(
            AssertionError, self.assertOnSubmit,
            submitBtn, 'Report_t',['/Experiment_g/Reports_g/Report_t'], [1])
        def tearDown(self):
            try:
                self.ph5api.close()
                del self.selTableDlg
                del self.kefedit
            except Exception:
                pass

class TestTablePanel(unittest.TestCase):
    def setUp(self):
        filename = 'master.ph5'
        path2file = 'ph5/test_data/ph5'
        self.kefedit = kefedit.KefEdit()
        self.kefedit.ph5api = ph5api.PH5(path=path2file, nickname=filename,
                              editmode=True)
        self.kefedit.processedLine = 0
        self.dataTable, self.labelSets, totalLines, self.types = \
            kefutility.PH5toTableData(
                None, self.kefedit.ph5api, filename, path2file, 'Array_t', '1')

        self.path = p = self.dataTable.keys()[0]
        self.tablePanel = kefedit.TablePanel(
            parent=self.kefedit, path=p, table=self.dataTable[p],
            labels=self.labelSets[p], types=self.types[p])

    def qmessage_respond(self):
        """
        automatically click buttons for QMessageBoxes in sequence
        Pre-declared:
        self.t = QtCore.QTimer(None)
        # call repond() to run per 2ms
        self.t.timeout.connect(self.respond)
        self.t.start(2)
        # messages: list of messages' part in QMessageBoxes to identify
        # which QMessageBoxes is being processed
        self.messages = ['does not exist in PH5 FILE']
        # buttonsClicked: list of QMessageBox's standardButton that will
        # be automatically clicked in sequence
        self.buttonClicked = [QtGui.QMessageBox.Yes]
        # count the buttons that has been clicked
        self.count = 0
        """
        if self.count == len(self.buttonsClicked):
            # stop timer when all QMessageBoxes have been processed
            self.t.stop()
            return
        for wid in app.topLevelWidgets():
            if wid.__class__ == QtGui.QMessageBox:
                if self.messages[self.count] not in wid.text():
                    # if count is increased before wid is the right
                    # QMessageBox to be processed,
                    # wait for next wid to be checked
                    listcorrect = False
                    # The following lines will check if developer has assigned
                    # wrong self.messages for QMessageBoxes
                    for m in self.messages:
                        if m in wid.text():
                            listcorrect = True
                    if not listcorrect:
                        self.t.stop()
                        msg = "Currently checking the QMessage with message:"\
                            "\n\t%s.\nWhile list of messages to check for "\
                            "are:\n\t%s.\nPlease close the currently opened "\
                            "QMessage yourselves." % \
                            (wid.text(), '\n\t'.join(self.messages))
                        raise Exception(msg)
                    return
                # identify what button to be clicked
                button = wid.button(self.buttonsClicked[self.count])
                # click the button in 0 second
                QtCore.QTimer.singleShot(0, button.clicked)
                # increase the count to move on to next QMessageBox
                self.count += 1

    def test_init(self):
        """
        test constructor
        """
        # --------------- test parameters
        self.assertEqual(self.labelSets[self.path], self.tablePanel.labels)
        self.assertEqual(self.types[self.path], self.tablePanel.types)
        # --------------- test mainTableView
        self.assertEqual(self.path, self.tablePanel.path)
        self.assertEqual(len(self.dataTable[self.path]),
                         self.tablePanel.mainTableView.rowCount())
        self.assertEqual(len(self.dataTable[self.path][0]),
                         self.tablePanel.mainTableView.columnCount())
        for i in range(len(self.dataTable[self.path][0])):
            self.assertEqual(
                self.labelSets[self.path][i],
                self.tablePanel.mainTableView.horizontalHeaderItem(i).text())
        
        # ---------------- test which radio button is selected
        # for Array_t: allInStation is checked
        self.assertTrue(self.tablePanel.allInStation.isChecked())
        # for others, singleCell is checked because allInStation is disable
        # => only need to test for Array_t
        
        # check if all buttons are disabled
        buttons = self.tablePanel.findChildren(QtGui.QPushButton)
        for btn in buttons:
            self.assertFalse(btn.isEnabled())

    """
    mouseMove doesn't emit any event:
    https://bugreports.qt.io/browse/QTBUG-5232
    => can't trigger event Enter

    => skip this test for now
    def test_eventFilter(self):
        buttons = self.tablePanel.findChildren(QtGui.QPushButton)
        for btn in buttons:
            QTest.mouseMove(btn)
            print QtGui.QToolTip.text()
    """

    def test__setButtonsDisabled(self):
        """
        test _setButtonsDisabled method
        """        
        # get all push buttons in table Panel
        buttons = self.tablePanel.findChildren(QtGui.QPushButton)
        
        # Enable all buttons
        for btn in buttons:
            btn.setEnabled(True)

        # run _setButtonsDisabled()
        self.tablePanel._setButtonsDisabled()
        
        # check if all buttons are disabled
        for btn in buttons:
            self.assertFalse(btn.isEnabled())
            
    def test_OnClearSelected(self):
        """
        test OnClearSelected method
        """
        pos = self.tablePanel.mainTableView.pos()
        # ____________in mainTableView_______________
        # select item at position 1,1
        item = self.tablePanel.mainTableView.item(1, 1)
        item.setSelected(True)
        # run OnClearSelected() by select one of the radio buttons:
        # singleCell, allInStation,allInColumn
        self.tablePanel.singleCell.click()
        # check if the above item is clear
        self.assertFalse(item.isSelected())

        # _____________in addTableView________________
        # click item (0,0) in mainTableView
        QTest.mouseClick(self.tablePanel.mainTableView.viewport(),
                         QtCore.Qt.LeftButton,
                         pos=QtCore.QPoint(pos.x() + 5, pos.y() + 5))
        # click on copyBtn to add the above row to addTableView
        QTest.mouseClick(self.tablePanel.copyBtn, QtCore.Qt.LeftButton)
        # select item at position
        item = self.tablePanel.addTableView.item(0, 1)
        item.setSelected(True)
        # run OnClearSelected() by select one of the radio buttons:
        # singleCell, allInStation,allInColumn
        self.tablePanel.singleCell.click()
        # check if the above item is clear
        self.assertFalse(item.isSelected())

    def test_OnMainTableClick(self):
        """
        test OnMainTableClick method
        """
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        # check general
        self.assertTrue(self.tablePanel.changeBtn.isEnabled())
        self.assertFalse(self.tablePanel.insertBtn.isEnabled())
        self.assertFalse(self.tablePanel.insertLineCtrl.isEnabled())
        self.assertTrue(self.tablePanel.XCtrl.isEnabled())
        self.assertTrue(self.tablePanel.changeCol2XBtn.isEnabled())
        self.assertTrue(self.tablePanel.back2orgBtn.isEnabled())
        self.assertTrue(self.tablePanel.resetColBtn.isEnabled())

        # click on copyBtn to add the above row to addTableView
        QTest.mouseClick(self.tablePanel.copyBtn, QtCore.Qt.LeftButton)
        # select addTableView's item at position 0,0
        tableViewClick(self.tablePanel.addTableView, 0, 0)
        # check value from clicking on addTableView
        self.assertGreater(
            len(self.tablePanel.addTableView.selectedIndexes()), 0)
        self.assertGreater(len(self.tablePanel.addCells), 0)

        # check if all selected in addTableView have been cleared
        # when clicking on mainTableView
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        self.assertEqual(
                    len(self.tablePanel.addTableView.selectedIndexes()), 0)
        self.assertEqual(self.tablePanel.addCells, None)

        # --------- single cell + delete + move ------------
        # setup
        self.tablePanel.singleCell.click()
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        # check values
        self.assertEqual(self.tablePanel.selectedCells, [(0, 0)])
        self.assertEqual(self.tablePanel.changedValCtrl.text(), '500')
        self.assertEqual(self.tablePanel.selectedRowsCtrl.text(), '1')
        self.assertEqual(self.tablePanel.selectedCol, 0)
        self.assertEqual(self.tablePanel.selectedColumnCtrl.text(), 'id_s')

        # check buttons
        self.assertTrue(self.tablePanel.copyBtn.isEnabled())
        # this row is not in deleteList
        self.assertFalse(self.tablePanel.unDeleteBtn.isEnabled())
        self.assertTrue(self.tablePanel.deleteBtn.isEnabled())
        # no row have been deleted: move option is allowed
        self.assertTrue(self.tablePanel.moveBtn.isEnabled())
        self.assertTrue(self.tablePanel.moveLineCtrl.isEnabled())

        # DELETE one row then check
        QTest.mouseClick(self.tablePanel.deleteBtn, QtCore.Qt.LeftButton)
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        # check buttns
        # this row is in deleteList
        self.assertTrue(self.tablePanel.unDeleteBtn.isEnabled())
        self.assertFalse(self.tablePanel.deleteBtn.isEnabled())
        # one row have been deleted: move option is NOT allowed
        self.assertFalse(self.tablePanel.moveBtn.isEnabled())
        self.assertFalse(self.tablePanel.moveLineCtrl.isEnabled())

        # --------- all similar cells (of the same column) in station --------
        # setup
        self.tablePanel.allInStation.click()
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        # check values
        self.assertEqual(self.tablePanel.selectedCells,
                         [(0, 0), (1, 0), (2, 0)])
        self.assertEqual(self.tablePanel.changedValCtrl.text(), '500')
        self.assertEqual(self.tablePanel.selectedRowsCtrl.text(), '1-2-3')
        self.assertEqual(self.tablePanel.selectedCol, 0)
        self.assertEqual(self.tablePanel.selectedColumnCtrl.text(), 'id_s')

        #check buttons
        self.assertTrue(self.tablePanel.copyBtn.isEnabled())
        # one row is in deleteList but others not in deleteList
        self.assertFalse(self.tablePanel.unDeleteBtn.isEnabled())
        self.assertTrue(self.tablePanel.deleteBtn.isEnabled())
        # one row have been deleted: move option is NOT allowed
        self.assertFalse(self.tablePanel.moveBtn.isEnabled())
        self.assertFalse(self.tablePanel.moveLineCtrl.isEnabled())

        # since there is only one station in the array, the result is somewhat
        # similar. The only difference is the buttons' availability

        # --------- all similar cells in column ------------
        # setup
        self.tablePanel.allInColumn.click()
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        # check values
        self.assertEqual(self.tablePanel.selectedCells,
                         [(0, 0), (1, 0), (2, 0)])
        self.assertEqual(self.tablePanel.changedValCtrl.text(), '500')
        self.assertEqual(self.tablePanel.selectedRowsCtrl.text(), '1-2-3')
        self.assertEqual(self.tablePanel.selectedCol, 0)
        self.assertEqual(self.tablePanel.selectedColumnCtrl.text(), 'id_s')

        # check buttons: all should be disabled
        self.assertFalse(self.tablePanel.copyBtn.isEnabled())
        self.assertFalse(self.tablePanel.unDeleteBtn.isEnabled())
        self.assertFalse(self.tablePanel.deleteBtn.isEnabled())
        self.assertFalse(self.tablePanel.moveBtn.isEnabled())
        self.assertFalse(self.tablePanel.moveLineCtrl.isEnabled())

    def test_OnAddTableClick(self):
        """
        test OnAddTableClick method
        """
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        # click on copyBtn to add the above row to addTableView
        QTest.mouseClick(self.tablePanel.copyBtn, QtCore.Qt.LeftButton)

        # --------- single cell ------------
        # setup
        self.tablePanel.singleCell.click()
        # click on MainTableView
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        # check values before they are changed by clicking on addTableView
        self.assertGreater(
            len(self.tablePanel.mainTableView.selectedIndexes()), 0)
        self.assertGreater(len(self.tablePanel.selectedCells), 0)

        # click addTableView
        tableViewClick(self.tablePanel.addTableView, 0, 0)
        # check buttons
        self.assertTrue(self.tablePanel.changeBtn.isEnabled())
        self.assertFalse(self.tablePanel.moveBtn.isEnabled())
        self.assertFalse(self.tablePanel.moveLineCtrl.isEnabled())
        self.assertFalse(self.tablePanel.copyBtn.isEnabled())
        self.assertFalse(self.tablePanel.deleteBtn.isEnabled())
        self.assertFalse(self.tablePanel.unDeleteBtn.isEnabled())
        self.assertTrue(self.tablePanel.insertBtn.isEnabled())
        self.assertTrue(self.tablePanel.insertLineCtrl.isEnabled())
        self.assertFalse(self.tablePanel.characterOrderCtrl.isEnabled())
        self.assertFalse(self.tablePanel.XCtrl.isEnabled())
        self.assertFalse(self.tablePanel.changeCol2XBtn.isEnabled())
        self.assertFalse(self.tablePanel.changeChar2XBtn.isEnabled())
        self.assertFalse(self.tablePanel.back2orgBtn.isEnabled())
        self.assertFalse(self.tablePanel.resetColBtn.isEnabled())

        # check if all selected in mainTableView have been cleared
        # when clicking on addTableView
        self.assertEqual(
            len(self.tablePanel.mainTableView.selectedIndexes()), 0)
        self.assertEqual(self.tablePanel.selectedCells, [])

        # check values
        self.assertEqual(self.tablePanel.addCells, [(0, 0)])
        self.assertEqual(self.tablePanel.changedValCtrl.text(), '500')

        # --------- all similar cells (of the same column) in station --------
        # setup
        self.tablePanel.allInStation.click()
        tableViewClick(self.tablePanel.addTableView, 0, 0)

        # check values
        self.assertEqual(self.tablePanel.addCells, [(0, 0), (1, 0), (2, 0)])
        self.assertEqual(self.tablePanel.changedValCtrl.text(), '500')

        # --------- all similar cells in column ---------------------
        # setup
        self.tablePanel.allInColumn.click()
        tableViewClick(self.tablePanel.addTableView, 0, 0)

        # check values
        self.assertEqual(self.tablePanel.addCells, [(0, 0), (1, 0), (2, 0)])
        self.assertEqual(self.tablePanel.changedValCtrl.text(), '500')

    def test__selectMatchInList(self):
        """
        test _selectMatchInList method
        """
        ret = self.tablePanel._selectMatchInList(
            '500', 0, range(3), self.tablePanel.mainTableView)
        self.assertEqual(ret[0], [(0, 0), (1, 0), (2, 0)])
        self.assertEqual(ret[1], ['1', '2', '3'])

    def test_OnChange(self):
        """
        test OnChange method
        """
        # mainTableView's item (0,0) - default all in station
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        # copy to addTableView
        QTest.mouseClick(self.tablePanel.copyBtn, QtCore.Qt.LeftButton)
        
        # test change to alphabet for column type float
        tableViewClick(self.tablePanel.mainTableView, 0, 1)
        self.tablePanel.changedValCtrl.setText('aaa')
        self.t = QtCore.QTimer(None)
        # enter a number
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ["type is 'float' while the changed text is"]
        self.buttonsClicked = [QtGui.QMessageBox.Ok]
        self.count = 0
        # click change
        QTest.mouseClick(self.tablePanel.changeBtn, QtCore.Qt.LeftButton)
        """
        Change on mainTableView
        case's description:
        mainTableView has row 0 in deletedList
        Change value in changedValCtrl to '501' then click change
        The expected result is (only check the first column):
          message dialog with part of message: 'can't be changed' to deny
            changing in row 0
        cell (0,0): value remain unchanged: 500, color: DELETECOLOR (0,1)
        cell (1,0), (2,0): value changed to 501, color: UPDATECOLOR (1,1)(2,1)
        """
        # ======  mainTableView's item (0,0) - singleCell ====================
        self.tablePanel.singleCell.click()
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        # delete mainTableView's item (0,0)
        QTest.mouseClick(self.tablePanel.deleteBtn, QtCore.Qt.LeftButton)

        # ====================================================================
        # mainTableView's item (0,0) - all in Station => affect(0,0)(0,1)(0,2)
        self.tablePanel.allInStation.click()
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        # change text in changedValCtrl to 501:
        # => change in row 1,2; row 0 not changed because it has been deleted
        self.tablePanel.changedValCtrl.setText('50')

        # enter a number
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ["can't be changed."]
        self.buttonsClicked = [QtGui.QMessageBox.Ok]
        self.count = 0
        # click change
        QTest.mouseClick(self.tablePanel.changeBtn, QtCore.Qt.LeftButton)

        # check (0,0) - row 0
        item = self.tablePanel.mainTableView.item(0, 0)
        self.assertEqual(item.text(), '500')
        self.assertEqual(item.background(), kefedit.DELETECOLOR)
        item = self.tablePanel.mainTableView.item(0, 1)
        self.assertEqual(item.background(), kefedit.DELETECOLOR)

        # check (1,0) - row 1
        item = self.tablePanel.mainTableView.item(1, 0)
        self.assertEqual(item.text(), '50')
        # UPDATECOLOR for background for row with changed cell(s)
        # red for foreground for changed cell
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)
        self.assertEqual(item.foreground(), kefedit.RED)
        # UPDATECOLOR for background for row with changed cell(s)
        # black for foreground for cell in that row but no changed
        item = self.tablePanel.mainTableView.item(1, 1)
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)
        self.assertEqual(item.foreground(), kefedit.BLACK)

        # check (2,0) - row 2
        item = self.tablePanel.mainTableView.item(2, 0)
        self.assertEqual(item.text(), '50')
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)
        self.assertEqual(item.foreground(), kefedit.RED)

        """
        change value in changedValCtrl back to 500:
        still get message cell 0,0 remain unchanged
        cell (0,0): 500, background DELETECOLOR,
        cell (1,0), (2,0) changed back to 500, background: QtCore.Qt.white,
                           foreground black
        """
        self.tablePanel.changedValCtrl.setText('500')
        # enter a number
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ["can't be changed."]
        self.buttonsClicked = [QtGui.QMessageBox.Ok]
        self.count = 0
        # click change
        QTest.mouseClick(self.tablePanel.changeBtn, QtCore.Qt.LeftButton)

        # check (0,0)
        item = self.tablePanel.mainTableView.item(0, 0)
        self.assertEqual(item.text(), '500')
        self.assertEqual(item.background(), kefedit.DELETECOLOR)
        self.assertEqual(item.foreground(), kefedit.BLACK)

        item = self.tablePanel.mainTableView.item(0, 1)
        self.assertEqual(item.background(), kefedit.DELETECOLOR)
        self.assertEqual(item.foreground(), kefedit.BLACK)

        # check (1,0)
        item = self.tablePanel.mainTableView.item(1, 0)
        self.assertEqual(item.text(), '500')
        self.assertEqual(item.background(), QtGui.QBrush(QtCore.Qt.white))
        self.assertEqual(item.foreground(), kefedit.BLACK)
        item = self.tablePanel.mainTableView.item(1, 1)
        self.assertEqual(item.background(), QtGui.QBrush(QtCore.Qt.white))
        self.assertEqual(item.foreground(), kefedit.BLACK)

        # check (2,0)
        item = self.tablePanel.mainTableView.item(2, 0)
        self.assertEqual(item.text(), '500')
        self.assertEqual(item.background(), QtGui.QBrush(QtCore.Qt.white))
        self.assertEqual(item.foreground(), kefedit.BLACK)
        item = self.tablePanel.mainTableView.item(2, 1)
        self.assertEqual(item.background(), QtGui.QBrush(QtCore.Qt.white))
        self.assertEqual(item.foreground(), kefedit.BLACK)

        """
        Change on addTableView
        Description:
        Select one cell on addTableView (1,0)
        Change value in changedValCtrl to '502' then click change
        The expected result for celles only, not for row:
          cell (1,0) has been changed to 502, text color is kefedit.RED
            other cell on this row still kefedit.BLACK
          cell (0,0) (2,0): 500, text color kefedit.BLACK
        """
        # addTableView's item (1,0) - singleCell
        self.tablePanel.singleCell.click()
        tableViewClick(self.tablePanel.addTableView, 1, 0)
        
        # change value in changedValCtrl the click Change
        self.tablePanel.changedValCtrl.setText('502')
        QTest.mouseClick(self.tablePanel.changeBtn, QtCore.Qt.LeftButton)

        # check (0,0): no change: text color remain black
        item = self.tablePanel.addTableView.item(0, 0)
        self.assertEqual(item.text(), '500')
        self.assertEqual(item.foreground(), kefedit.BLACK)

        # check (1,0): change: text color change to red
        item = self.tablePanel.addTableView.item(1, 0)
        self.assertEqual(item.text(), '502')
        self.assertEqual(item.foreground(), kefedit.RED)

        # check (1,1): in changed row but not a changed cell
        item = self.tablePanel.addTableView.item(1, 1)
        self.assertEqual(item.foreground(), kefedit.BLACK)

        # check (2,0)
        item = self.tablePanel.addTableView.item(2, 0)
        self.assertEqual(item.text(), '500')
        self.assertEqual(item.foreground(), kefedit.BLACK)
        
    def test_OnBack2org(self):
        """
        test OnBack2org method
        """        
        # mainTableView's item (0,0) - all in Station => affect(0,0)(0,1)(0,2)
        self.tablePanel.allInStation.click()
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        # change text in changedValCtrl to 501:
        self.tablePanel.changedValCtrl.setText('501')

        QTest.mouseClick(self.tablePanel.changeBtn, QtCore.Qt.LeftButton)

        # check (0,0)(1,0)(2,0): check text and color changed because
        # the cells have been changed because changeBtn has been clicked on
        item = self.tablePanel.mainTableView.item(0, 0)
        self.assertEqual(item.text(), '501')
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)
        self.assertEqual(item.foreground(), kefedit.RED)

        # check (1,0) - row 1
        item = self.tablePanel.mainTableView.item(1, 0)
        self.assertEqual(item.text(), '501')
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)
        self.assertEqual(item.foreground(), kefedit.RED)

        # check (2,0) - row 2
        item = self.tablePanel.mainTableView.item(2, 0)
        self.assertEqual(item.text(), '501')
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)
        self.assertEqual(item.foreground(), kefedit.RED)

        """
        click on Back to Org: change value  back to 500 though the value in
        changedValCtrl still remain 501:
        cell (0,0)(1,0), (2,0) changed back to 500, background:
        QtCore.Qt.white,foreground black
        """
        QTest.mouseClick(self.tablePanel.back2orgBtn, QtCore.Qt.LeftButton)
        self.assertEqual(self.tablePanel.changedValCtrl.text(), '501')

        # check (0,0)
        item = self.tablePanel.mainTableView.item(0, 0)
        self.assertEqual(item.text(), '500')
        self.assertEqual(item.background(), QtGui.QBrush(QtCore.Qt.white))
        self.assertEqual(item.foreground(), kefedit.BLACK)

        # check (1,0)
        item = self.tablePanel.mainTableView.item(1, 0)
        self.assertEqual(item.text(), '500')
        self.assertEqual(item.background(), QtGui.QBrush(QtCore.Qt.white))
        self.assertEqual(item.foreground(), kefedit.BLACK)

        # check (2,0)
        item = self.tablePanel.mainTableView.item(2, 0)
        self.assertEqual(item.text(), '500')
        self.assertEqual(item.background(), QtGui.QBrush(QtCore.Qt.white))
        self.assertEqual(item.foreground(), kefedit.BLACK)

    def _test__afterUpdateCol(self, samelen, XIsDigit, columnItemsAreNum=True):
        """
        test _afterUpdateCol inside the following functions:
        samelen: all items in selected column have the same len
        XIsNum: value in X is digit
        """
        numptest.assert_array_equal(
            self.tablePanel.selectedColList,
            self.tablePanel.updatedTable[:, self.tablePanel.selectedCol])
        if samelen:
            self.assertTrue(self.tablePanel.changeChar2XBtn.isEnabled())
            self.assertTrue(self.tablePanel.characterOrderCtrl.isEnabled())
            self.assertEqual(self.tablePanel.characterOrderCtrl.count(),
                             len(self.tablePanel.selectedColList[0]))
            self.assertEqual(self.tablePanel.characterOrderCtrl.itemText(0),
                             '1')
        else:
            self.assertFalse(self.tablePanel.changeChar2XBtn.isEnabled())
            self.assertFalse(self.tablePanel.characterOrderCtrl.isEnabled())
            self.assertEqual(self.tablePanel.characterOrderCtrl.count(), 0)
        if XIsDigit and columnItemsAreNum:
            self.assertTrue(self.tablePanel.plusX2ColBtn.isEnabled())
        else:
            self.assertFalse(self.tablePanel.plusX2ColBtn.isEnabled())
            
    def test_afterUpdateCol(self):
        """
        test _afterUpdateCol method
        """
        # check _afterUpdateCol for item is a number
        self.tablePanel.singleCell.click()

        tableViewClick(self.tablePanel.mainTableView, 0, 0)
        # XCtrl is enable after mainTableView is clicked
        self.tablePanel.XCtrl.setText('1')
        self._test__afterUpdateCol(samelen=True, XIsDigit=True)

        # check _afterUpdateCol for item isn't a number
        tableViewClick(self.tablePanel.mainTableView, 0, 2)
        self._test__afterUpdateCol(samelen=True, XIsDigit=False)

        # change item (1,0) to 50, item (0,0)(2,0) remain 500 => item (1,0)
        # has different length in compare with others in the same column
        tableViewClick(self.tablePanel.mainTableView, 0, 1)
        self.tablePanel.changedValCtrl.setText('50')
        QTest.mouseClick(self.tablePanel.changeBtn, QtCore.Qt.LeftButton)
        self._test__afterUpdateCol(samelen=False, XIsDigit=True)

    def test_OnChangeCharOrder(self):
        """
        test OnChangeCharOrder method:
           change ComboBox next to "Position of Char. to change"
        """
        tableViewClick(self.tablePanel.mainTableView, 0, 0)
        self.tablePanel.characterOrderCtrl.setCurrentIndex(1)
        self.assertEqual(self.tablePanel.nondigitList, [])
        noOfCharsCtrlList = \
            [self.tablePanel.noOfCharsCtrl.itemText(i)
             for i in range(self.tablePanel.noOfCharsCtrl.count())]
        self.assertEqual(noOfCharsCtrlList, ['1', '2'])

    def test_OnXChanged(self):
        """
        test OnXChanged method
           change text in text box next to 'X'
        """
        tableViewClick(self.tablePanel.mainTableView, 0, 0)
        self.tablePanel.characterOrderCtrl.setCurrentIndex(1)
        # item (0,0):XCtrl is not integer
        self.tablePanel.XCtrl.clear()
        QTest.keyClicks(self.tablePanel.XCtrl, "AAA")
        self.assertFalse(self.tablePanel.plusX2CharBtn.isEnabled())
        self.assertFalse(self.tablePanel.plusX2ColBtn.isEnabled())

        # item (0,0):XCtrl is not integer
        self.tablePanel.XCtrl.clear()
        QTest.keyClicks(self.tablePanel.XCtrl, "1")
        self.assertTrue(self.tablePanel.plusX2CharBtn.isEnabled())
        self.assertTrue(self.tablePanel.plusX2ColBtn.isEnabled())

    def test_OnChangeNoOfChars(self):
        """
        test OnChangeNoOfChars method
           change ComboBox nex to " Number of Char. to change"
        """
        # item (0,19)'s text=3X500
        # all items'position in range[order:order+noOfChars] are digit
        tableViewClick(self.tablePanel.mainTableView, 0, 19)
        self.tablePanel.characterOrderCtrl.setCurrentIndex(0)
        self.tablePanel.XCtrl.clear()
        QTest.keyClicks(self.tablePanel.XCtrl, "1")
        # characterOrderCtrl's text=1 noOfCharsCtrl's text=1 => check '3'
        self.tablePanel.noOfCharsCtrl.setCurrentIndex(0)
        self.assertEqual(self.tablePanel.nondigitList, [])
        self.assertTrue(self.tablePanel.plusX2CharBtn.isEnabled())

        # some items'position in range[order:order+noOfChars] aren't digit
        # characterOrderCtrl's text=1 noOfCharsCtrl's text=2 => check '3X'
        self.tablePanel.noOfCharsCtrl.setCurrentIndex(1)
        self.assertNotEqual(self.tablePanel.nondigitList, [])
        self.assertFalse(self.tablePanel.plusX2CharBtn.isEnabled())

    def test__checkEmpty(self):
        """
        test _checkEmpty
        """
        # enable XCtrl
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        self.t = QtCore.QTimer(None)
        # answer = Cancel
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ["The value in the X box is ''."]
        self.buttonsClicked = [QtGui.QMessageBox.Cancel]
        self.count = 0
        ret = self.tablePanel._checkEmpty("characters")
        self.assertFalse(ret)

        # answer = Cancel
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ["The value in the X box is ''."]
        self.buttonsClicked = [QtGui.QMessageBox.Yes]
        self.count = 0
        ret = self.tablePanel._checkEmpty("characters")
        self.assertTrue(ret)

    def test_OnChangeChar2X(self):
        """
        test OnChangeChar2X method
           click on "Change Char. to X"
        """
        # enable XCtrl
        # item's text=500, type=str
        tableViewClick(self.tablePanel.mainTableView, 0, 0)

        self.t = QtCore.QTimer(None)
        # answer = Cancel
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ["The value in the X box is ''."]
        self.buttonsClicked = [QtGui.QMessageBox.Cancel]
        self.count = 0
        QTest.mouseClick(self.tablePanel.changeChar2XBtn, QtCore.Qt.LeftButton)
        item = self.tablePanel.mainTableView.item(0, 0)
        self.assertEqual(item.text(), '500')

        # answer = Yes - Ok
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ["The value in the X box is ''.",
                         "of which length is different."]
        self.buttonsClicked = [QtGui.QMessageBox.Cancel, 
                               QtGui.QMessageBox.Ok]
        self.count = 0
        QTest.mouseClick(self.tablePanel.changeChar2XBtn, QtCore.Qt.LeftButton)
        self.assertEqual(item.text(), '500')

        # X=65
        self.tablePanel.XCtrl.clear()
        QTest.keyClicks(self.tablePanel.XCtrl, "65")
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ["of which length is different."]
        self.buttonsClicked = [QtGui.QMessageBox.Ok]
        self.count = 0
        QTest.mouseClick(self.tablePanel.changeChar2XBtn, QtCore.Qt.LeftButton)
        self.assertEqual(item.text(), '500')

        # X=6 => change 5 to 6
        self.tablePanel.XCtrl.clear()
        QTest.keyClicks(self.tablePanel.XCtrl, "6")
        QTest.mouseClick(self.tablePanel.changeChar2XBtn, QtCore.Qt.LeftButton)
        self.assertEqual(item.text(), '600')

        # item's text=-105.405489539, type=float
        tableViewClick(self.tablePanel.mainTableView, 0, 1)  # type=float
        # X=a => non-digit
        self.tablePanel.XCtrl.clear()
        QTest.keyClicks(self.tablePanel.XCtrl, "a")
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ["which doesn't match the required type: float"]
        self.buttonsClicked = [QtGui.QMessageBox.Ok]
        self.count = 0
        QTest.mouseClick(self.tablePanel.changeChar2XBtn, QtCore.Qt.LeftButton)
        item = self.tablePanel.mainTableView.item(0, 1)
        self.assertEqual(item.text(), '-105.405489539')

    def test__updateColItem(self):
        """
        test _updateColItem method
        """
        # item's text=3X500 change to 5X655
        tableViewClick(self.tablePanel.mainTableView, 0, 19)
        self.tablePanel._updateColItem(1, "5X655")
        self.assertEqual(self.tablePanel.updatedTable[1][19], "5X655")
        item = self.tablePanel.mainTableView.item(1, 19)
        self.assertEqual(item.text(), "5X655")
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)
        self.assertEqual(item.foreground(), kefedit.RED)
        self.assertEqual(self.tablePanel.updateList, [1])

        # item's text original=3X500 now is 5X655, change to original value
        self.tablePanel._updateColItem(1, "3X500")
        self.assertEqual(self.tablePanel.updatedTable[1][19], "3X500")
        item = self.tablePanel.mainTableView.item(1, 19)
        self.assertEqual(item.text(), "3X500")
        self.assertEqual(item.background(), QtCore.Qt.white)
        self.assertEqual(item.foreground(), kefedit.BLACK)
        self.assertEqual(self.tablePanel.updateList, [])

    def test_OnPlusX2Char(self):
        """
        test OnPlusX2Char method
           click on "Plus X to Char."
        """
        # item's text=3X500
        tableViewClick(self.tablePanel.mainTableView, 0, 19)
        self.tablePanel.characterOrderCtrl.setCurrentIndex(0)
        self.tablePanel.noOfCharsCtrl.setCurrentIndex(0)  # changed len=1

        # plus 2 to '3'
        self.tablePanel.XCtrl.clear()
        QTest.keyClicks(self.tablePanel.XCtrl, "2")
        QTest.mouseClick(self.tablePanel.plusX2CharBtn, QtCore.Qt.LeftButton)
        item = self.tablePanel.mainTableView.item(0, 19)
        self.assertEqual(item.text(), "5X500")
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)
        self.assertEqual(item.foreground(), kefedit.RED)
        self.assertEqual(self.tablePanel.updateList, [0, 1, 2])
        self._test__afterUpdateCol(samelen=True, XIsDigit=True,
                                   columnItemsAreNum=False)

        # X=9 => replace character is 12 of which len is 2 > changed len =1
        self.tablePanel.XCtrl.clear()
        QTest.keyClicks(self.tablePanel.XCtrl, "9")
        self.t = QtCore.QTimer(None)
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ["of which length is different."]
        self.buttonsClicked = [QtGui.QMessageBox.Ok]
        self.count = 0
        QTest.mouseClick(self.tablePanel.plusX2CharBtn, QtCore.Qt.LeftButton)

    def test_OnChangeCol2X(self):
        """
        test OnChangeCol2X method
           click on "Change Column to X"
        """
        # enable XCtrl
        # seed_orientation_code_s item's text=1,2,Z, type=str
        tableViewClick(self.tablePanel.mainTableView, 0, 32)
        self.tablePanel.XCtrl.clear()
        QTest.keyClicks(self.tablePanel.XCtrl, "2")
        QTest.mouseClick(self.tablePanel.changeCol2XBtn, QtCore.Qt.LeftButton)
        item = self.tablePanel.mainTableView.item(0, 32)
        self.assertEqual(item.text(), "2")
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)
        self.assertEqual(item.foreground(), kefedit.RED)
        self.assertEqual(self.tablePanel.updateList, [0, 2])
        self._test__afterUpdateCol(samelen=True, XIsDigit=True,
                                   columnItemsAreNum=True)

        # sample_rate_i item's text=500, type=int
        tableViewClick(self.tablePanel.mainTableView, 0, 29)
        self.tablePanel.XCtrl.clear()
        QTest.keyClicks(self.tablePanel.XCtrl, "a")
        self.t = QtCore.QTimer(None)
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ["which doesn't match the required type: int"]
        self.buttonsClicked = [QtGui.QMessageBox.Ok]
        self.count = 0
        QTest.mouseClick(self.tablePanel.changeCol2XBtn, QtCore.Qt.LeftButton)

    def test_OnPlusX2Col(self):
        """
        test OnPlusX2Col method
           click on "Plus X to Column"
        """
        # sample_rate_i item's text=500, type=int
        tableViewClick(self.tablePanel.mainTableView, 0, 29)
        self.tablePanel.XCtrl.clear()
        QTest.keyClicks(self.tablePanel.XCtrl, "5")
        item = self.tablePanel.mainTableView.item(0, 29)
        QTest.mouseClick(self.tablePanel.plusX2ColBtn, QtCore.Qt.LeftButton)
        self.assertEqual(item.text(), "505")
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)
        self.assertEqual(item.foreground(), kefedit.RED)
        self.assertEqual(self.tablePanel.updateList, [0, 1, 2])
        self._test__afterUpdateCol(samelen=True, XIsDigit=True,
                                   columnItemsAreNum=True)

    def test_OnResetCol(self):
        """
        test OnResetCol method
           click on "Reset Column"
        """
        # work on column 0: id_s
        # change all cell on column 0 to 505
        tableViewClick(self.tablePanel.mainTableView, 0, 0)
        self.tablePanel.changedValCtrl.setText('505')
        QTest.mouseClick(self.tablePanel.changeBtn, QtCore.Qt.LeftButton)
        # delete row 1
        self.tablePanel.singleCell.click()
        tableViewClick(self.tablePanel.mainTableView, 1, 0)
        QTest.mouseClick(self.tablePanel.deleteBtn, QtCore.Qt.LeftButton)
        
        # =========== check before reset =====================
        # check value of cells on column 0: 505
        # color of cells on row 0, 2: UPDATECOLOR
        # color of cell on row 1: DELETECOLOR
        item = self.tablePanel.mainTableView.item(0, 0)
        self.assertEqual(item.text(), '505')
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)
        item = self.tablePanel.mainTableView.item(1, 0)
        self.assertEqual(item.text(), '505')
        self.assertEqual(item.background(), kefedit.DELETECOLOR)
        item = self.tablePanel.mainTableView.item(2, 0)
        self.assertEqual(item.text(), '505')
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)
        
        # still remain selection on cell(0,1)
        # click reset
        QTest.mouseClick(self.tablePanel.resetColBtn, QtCore.Qt.LeftButton)
        # check value of cells on column 0 go back to 500
        # color of cells on row 0, 2: go back to white
        # color of cell on row 1: remain DELETECOLOR
        item = self.tablePanel.mainTableView.item(0, 0)
        self.assertEqual(item.text(), '500')
        self.assertEqual(item.background(), QtGui.QBrush(QtCore.Qt.white))
        item = self.tablePanel.mainTableView.item(1, 0)
        self.assertEqual(item.text(), '500')
        self.assertEqual(item.background(), QtGui.QBrush(kefedit.DELETECOLOR))
        item = self.tablePanel.mainTableView.item(2, 0)
        self.assertEqual(item.text(), '500')
        self.assertEqual(item.background(), QtGui.QBrush(QtCore.Qt.white))

    def test_OnSelectMoveLine(self):
        """
        test OnSelectMoveLine method => _selectLine method
           Change selection of the combo box next to
           "Move Selected Row(s) under Line No"
        """
        print ("test_OnSelectMoveLine")

        self.tablePanel.singleCell.click()
        tableViewClick(self.tablePanel.mainTableView, 2, 0)

        # select '2'
        self.tablePanel.moveLineCtrl.setCurrentIndex(2)  # 2
        self.assertEqual(self.tablePanel.mainTableView.currentIndex().row, 2)
        
        # select top
        self.tablePanel.moveLineCtrl.setCurrentIndex(0)  # top
        self.assertEqual(
            self.tablePanel.mainTableView.verticalScrollBar().value(), 0)
        self.assertEqual(self.tablePanel.mainTableView.selectedIndexes(), [])
        # select 2
        
        
        
    def test_OnDelete(self):
        """
        test OnDelete method
           click on "Delete Row(s) on Selected Cells"
        """
        # delete row 1
        self.tablePanel.singleCell.click()
        tableViewClick(self.tablePanel.mainTableView, 1, 0)
        QTest.mouseClick(self.tablePanel.deleteBtn, QtCore.Qt.LeftButton)
        # check color of selected cell
        item = self.tablePanel.mainTableView.item(1, 0)
        self.assertEqual(item.background(), kefedit.DELETECOLOR)
        # check color of another cell on row
        item = self.tablePanel.mainTableView.item(1, 1)
        self.assertEqual(item.background(), kefedit.DELETECOLOR)
        # check deleteList: row 1
        self.assertEqual(self.tablePanel.deleteList, [1])
        # check if deleteBtn is disabled and unDeleteBtn is enabled
        self.assertFalse(self.tablePanel.deleteBtn.isEnabled())
        self.assertTrue(self.tablePanel.unDeleteBtn.isEnabled())

    def test_OnUnDelete(self):
        """
        test OnUnDelete method
           click on "UnDelete"
        """
        # CASE1: delete row 1 like the case in test_OnDelete
        self.tablePanel.singleCell.click()
        tableViewClick(self.tablePanel.mainTableView, 1, 0)
        QTest.mouseClick(self.tablePanel.deleteBtn, QtCore.Qt.LeftButton)

        # click unDeleteBtn
        QTest.mouseClick(self.tablePanel.unDeleteBtn, QtCore.Qt.LeftButton)

        # color of selected cell should go back to white
        item = self.tablePanel.mainTableView.item(1, 0)
        self.assertEqual(item.background(), QtGui.QBrush(QtCore.Qt.white))
        # 1 should have been removed from deleteList, so it should be [] now
        self.assertEqual(self.tablePanel.deleteList, [])
        # check if deleteBtn is re-enabled and unDeleteBtn is re-disabled
        self.assertTrue(self.tablePanel.deleteBtn.isEnabled())
        self.assertFalse(self.tablePanel.unDeleteBtn.isEnabled())

        # CASE2: change row 1 then delete
        self.tablePanel.changedValCtrl.setText('505')
        QTest.mouseClick(self.tablePanel.changeBtn, QtCore.Qt.LeftButton)
        QTest.mouseClick(self.tablePanel.deleteBtn, QtCore.Qt.LeftButton)
        # check if item's color is DELETECOLOR
        self.assertEqual(item.background(), kefedit.DELETECOLOR)

        # click unDeleteBtn
        QTest.mouseClick(self.tablePanel.unDeleteBtn, QtCore.Qt.LeftButton)
        # item's color is supposed to change back to it previous state:
        #   UPDATECOLOR
        self.assertEqual(item.background(), kefedit.UPDATECOLOR)

    def tearDown(self):
        try:
            self.ph5api.close()
            del self.kefedit
        except Exception:
            pass

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    unittest.main()
    sys.exit(app.exec_())
