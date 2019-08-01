"""
unit tests for ph5availability
"""

import unittest
from ph5.core import ph5api, kefutility, experiment
from ph5.utilities import tabletokef
import sys
import os
import re
from HTMLParser import HTMLParser, HTMLParseError
from shutil import copyfile
from mock import patch
from contextlib import contextmanager
from StringIO import StringIO
from lxml import etree
from PyQt4 import QtGui, QtCore


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def checkTupleAlmostEqualIn(tup, tupList, place):
    """
    check if a tuple in a list of tuples in which float items only
    need to be almost equal
    :type tup: tuple
    :param tup: tuple to be checked
    :type tupList: list of tuples
    :para tupList: list of tuples that tup need to be check with
    :place: decimal places to round the values to compare
    """
    for T in tupList:
        length = len(tup)
        if length != len(T):
            continue
        for i in range(length):
            if type(tup[i]) is float:
                if round(tup[i], place) != round(T[i], place):
                    break
            else:
                if tup[i] != T[i]:
                    break
            if i == length - 1:
                return True
    return False


def checkFieldsMatch(fieldNames, fieldsList, dictList):
    """
    check if given fieldslist match the dict dictList at field fieldNames
    :type fieldsName: list of str
    :param fieldsName: list of field names that their values are to be compared
       with items in dictList
    :type fieldsList: list of tuple
    :para fieldsList: list of tuple of fields' values
    :type dictList: list of dictionary
    :para dictList: list of dictionary to be compared with
    """
    if len(fieldsList) != len(dictList):
        return False
    for d in dictList:
        arow = ()
        for i in range(len(fieldNames)):
            arow += (d[fieldNames[i]], )
        if arow not in fieldsList:
            return False
        fieldsList.remove(arow)
    return True

#
# To hold table rows and keys
#
class Rows_Keys(object):
    __slots__ = ('rows', 'keys')

    def __init__(self, rows=None, keys=None):
        self.rows = rows
        self.keys = keys

    def set(self, rows=None, keys=None):
        if rows is not None:
            self.rows = rows
        if keys is not None:
            self.keys = keys
    
class Status:
    """
    fake status bar for testing
    """
    def __init__(self):
        self.message = ''
    def showMessage(self, message):
        self.message = message

class TestKefUtility(unittest.TestCase):
    def setUp(self):
        """
        setup for tests
        """
        self.statusbar = Status()

    def assertStrEqual(self, str1, str2):
        """
        return True if 2 strings are the same, othewise
        return the index of the first difference between 2 strings
        """
        if str1 == str2:
            return True
        else:
            for i in range(len(str1)):
                if str1[i] != str2[i]:
                    errmsg = "The strings are different from %s.\n" % i
                    if i > 0:
                        errmsg += "BEFORE:\n\tstr1: '%s'\n\tstr2: '%s'\n" % \
                            (str1[:i], str2[:i])
                    errmsg += "Different at:\n\tstr1: '%s'\n\tstr2: '%s'\n"\
                        "AFTER:\n\tstr1: '%s'\n\tstr2: '%s'" % \
                        (str1[i], str2[i], str1[i+1:], str2[i+1:])
                    raise AssertionError(errmsg)

    def test_Kef2TableData(self):
        """
        test Kef2TableData method
        """
        self.statusbar = Status()
        # wrong path
        self.assertRaises(Exception,
                         kefutility.Kef2TableData, self.statusbar, "wrongpath")
        # test return values
        ret = kefutility.Kef2TableData(
            self.statusbar, "ph5/test_data/ph5/array_t_9.kef")

        tables = {'/Experiment_g/Sorts_g/Array_t_009':
                  [['9001', '-106.906169', 'degrees', '34.054673', 'degrees',
                    '1403.0', 'm', '', '', '', '', 'Fri Feb 22 15:39:00 2019',
                    '1550849940', '0', 'BOTH', 'Fri Feb 22 15:44:00 2019',
                    '1550850240', '0', 'BOTH', '12183', 'rt125a', 'reftek',
                    '', '', 'gs11v', 'geospace', '', '', 'D', '500', '1', 'P',
                    'Z', '', '9001', '1', '0', '7']]}
        keySets = {'/Experiment_g/Sorts_g/Array_t_009':
                   ['id_s', 'location/X/value_d', 'location/X/units_s',
                    'location/Y/value_d', 'location/Y/units_s',
                    'location/Z/value_d', 'location/Z/units_s',
                    'location/coordinate_system_s', 'location/projection_s',
                    'location/ellipsoid_s', 'location/description_s',
                    'deploy_time/ascii_s', 'deploy_time/epoch_l',
                    'deploy_time/micro_seconds_i', 'deploy_time/type_s',
                    'pickup_time/ascii_s', 'pickup_time/epoch_l',
                    'pickup_time/micro_seconds_i', 'pickup_time/type_s',
                    'das/serial_number_s', 'das/model_s', 'das/manufacturer_s',
                    'das/notes_s', 'sensor/serial_number_s', 'sensor/model_s',
                    'sensor/manufacturer_s', 'sensor/notes_s', 'description_s',
                    'seed_band_code_s', 'sample_rate_i',
                    'sample_rate_multiplier_i', 'seed_instrument_code_s',
                    'seed_orientation_code_s', 'seed_location_code_s',
                    'seed_station_name_s', 'channel_number_i',
                    'receiver_table_n_i', 'response_table_n_i']}
        totalLines = 1
        types = ['', 0.0, '', 0.0, '', 0.0, '', '', '', '', '', '', 0, 0, '',
                  '', 0, 0, '', '', '', '', '', '', '', '', '', '', '', 0, 0,
                  '', '', '', '', 0, 0, 0]
        self.assertEqual(4, len(ret))
        self.assertEqual(tables, ret[0])
        self.assertEqual(keySets, ret[1])
        self.assertEqual(totalLines, ret[2])
        r = ret[3]['/Experiment_g/Sorts_g/Array_t_009']
        self.assertEqual(len(types), len(r))
        for i in range(len(r)):
            self.assertIsInstance(types[i], r[i])

    def assertTable(self, args, lookfor, boolRequired):
        testargs = ['tabletokef', '-n', 'master.ph5'] + args

        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        output = out.getvalue()

        if (lookfor in output) != boolRequired:
            if boolRequired:
                msg = "%s isn't in ph5 while it should be." % lookfor
            else:
                msg = "%s is in ph5 while it shouldn't be." % lookfor
            raise AssertionError(msg)



    def test_NukeTable(self):
        """
        test NukeTable method
        """
        # copy files: don't want to do this part in setup because this test
        # will delete tables in ph5, so when testing main, the tasks need to
        # be repeated
        copyfile('ph5/test_data/ph5/master.ph5', 'master.ph5')
        copyfile('ph5/test_data/ph5/miniPH5_00001.ph5', 'miniPH5_00001.ph5')

        orglistdir = os.listdir('.')

        """
        for each table:
          + check if the table is in ph5 file
          + nuke that table
          + check if the table has been removed from ph5
        """

        # nuke Experiment_t
        table_path = '/Experiment_g/Experiment_t'
        self.assertTable(['-E'], table_path, True)
        ret = kefutility.NukeTable(None, 'master.ph5', '.',table_path)
        self.assertTrue(ret)
        self.assertTable(['-E'], table_path, False)

        # nuke Sort_t
        table_path = '/Experiment_g/Sorts_g/Sort_t'
        self.assertTable(['-S'], table_path, True)
        ret = kefutility.NukeTable(None, 'master.ph5', '.', table_path)
        self.assertTrue(ret)
        self.assertTable(['-S'], table_path, False)

        # nuke Offset_t
        table_path = '/Experiment_g/Sorts_g/Offset_t_003_001'
        self.assertTable(['-O', '3_1'], table_path, True)
        ret = kefutility.NukeTable(None, 'master.ph5', '.', table_path)
        self.assertTrue(ret)
        self.assertTable(['-O', '3_1'], table_path, False)

        # nuke Event_t_
        table_path = '/Experiment_g/Sorts_g/Event_t_001'
        self.assertTable(['-V', '1'], table_path, True)
        ret = kefutility.NukeTable(None, 'master.ph5', '.', table_path)
        self.assertTrue(ret)
        self.assertTable(['-V', '1'], table_path, False)

        # nuke Array_t_
        table_path = '/Experiment_g/Sorts_g/Array_t_001'
        self.assertTable(['-A', '1'], table_path, True)
        ret = kefutility.NukeTable(None, 'master.ph5', '.', table_path)
        self.assertTrue(ret)
        self.assertTable(['-A', '1'], table_path, False)

        # nuke Time_t
        table_path = '/Experiment_g/Receivers_g/Time_t'
        self.assertTable(['-T'], table_path, True)
        ret = kefutility.NukeTable(None, 'master.ph5', '.', table_path)
        self.assertTrue(ret)
        self.assertTable(['-T'], table_path, False)

        # nuke Index_t
        table_path = '/Experiment_g/Receivers_g/Index_t'
        self.assertTable(['-I'], table_path, True)
        ret = kefutility.NukeTable(None, 'master.ph5', '.', table_path)
        self.assertTrue(ret)
        self.assertTable(['-I'], table_path, False)

        # nuke M_Index_t
        table_path = '/Experiment_g/Maps_g/Index_t'
        self.assertTable(['-M'], table_path, True)
        ret = kefutility.NukeTable(None, 'master.ph5', '.', table_path)
        self.assertTrue(ret)
        self.assertTable(['-M'], table_path, False)

        # nuke Receiver_t
        table_path = '/Experiment_g/Receivers_g/Receiver_t'
        self.assertTable(['-C'], table_path, True)
        ret = kefutility.NukeTable(None, 'master.ph5', '.', table_path)
        self.assertTrue(ret)
        self.assertTable(['-C'], table_path, False)

        # nuke Response_t
        table_path = '/Experiment_g/Responses_g/Response_t'
        self.assertTable(['-R'], table_path, True)
        ret = kefutility.NukeTable(None, 'master.ph5', '.', table_path)
        self.assertTrue(ret)
        self.assertTable(['-R'], table_path, False)

        # nuke Report_t: report t not exist

        # nuke Das_t_
        table_path = '/Experiment_g/Receivers_g/Das_g_5553/Das_t'
        self.assertTable(['-D', '5553'], table_path, True)
        f = StringIO('y')
        sys.stdin = f   # answer 'y' for question in kefutility.NukeTable()
        ret = kefutility.NukeTable(None, 'master.ph5', '.', table_path)
        self.assertTrue(ret)
        self.assertTable(['-D', '5553'], table_path, False)

        # wrong path to ph5 file
        table_path = '/Experiment_g/Sorts_g/Event_t_001'
        self.assertRaises(kefutility.KefUtilityError, kefutility.NukeTable,
                          None, 'master.ph5', './pj', table_path)

        # wrong table_path ################################################
        table_path = '/Experiment_g/Sorts_g/Event3_t_002'
        self.t = QtCore.QTimer(None)
        # answer Yes
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ['does not exist in PH5 FILE']
        self.buttonsClicked = [QtGui.QMessageBox.Yes]
        self.count = 0
        ret = kefutility.NukeTable(None, 'master.ph5', './ph5', table_path)
        self.assertTrue(ret)

        # answer No - Ok
        self.t.timeout.connect(self.qmessage_respond)
        self.t.start(2)
        self.messages = ['does not exist in PH5 FILE',
                         'Saving interupted.']
        self.buttonsClicked = [QtGui.QMessageBox.No, QtGui.QMessageBox.Ok]
        self.count = 0
        ret = kefutility.NukeTable(None, 'master.ph5', './ph5', table_path)
        self.assertFalse(ret)

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

    def _test_PH5toTableData(self, statusbar, ph5, filename, path2file,
                             tableType, arg, tablepath, total):
        ret = kefutility.PH5toTableData(
            self.statusbar, ph5, filename, path2file, tableType, arg)
        self.assertEqual(4, len(ret))
        # TOTAL
        self.assertEqual(total, ret[2])
        for tp in tablepath:
            # tables
            self.assertIn(tp, ret[0].keys())
            # keySets
            self.assertIn(tp, ret[1].keys())
            # types
            self.assertIn(tp, ret[3].keys())

    def test_PH5toTableData(self):
        """
        test PH5toTableData method
        """
        self.ph5 = ph5api.PH5(path='ph5/test_data/ph5', nickname='master.ph5',
                         editmode=True)
        filename = 'master.ph5'
        path2file = 'ph5/test_data/ph5'
        
        # Experiment_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'Experiment_t', None, ['/Experiment_g/Experiment_t'], 1)
        # Sort_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'Sort_t', '1', ['/Experiment_g/Sorts_g/Sort_t'], 14)
        # Offset_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'Offset_t', '3_1', ['/Experiment_g/Sorts_g/Offset_t_003_001'], 1)
        # All_Offset_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file,
            'All_Offset_t', None,
            ['/Experiment_g/Sorts_g/Offset_t_001_001',
            '/Experiment_g/Sorts_g/Offset_t_002_001',
            '/Experiment_g/Sorts_g/Offset_t_003_001',
            '/Experiment_g/Sorts_g/Offset_t_004_001',
            '/Experiment_g/Sorts_g/Offset_t_008_001',
            '/Experiment_g/Sorts_g/Offset_t_009_001'], 6)
        # Event_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'Event_t', '1', ['/Experiment_g/Sorts_g/Event_t_001'], 1)
        # All_Event_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'All_Event_t', None, ['/Experiment_g/Sorts_g/Event_t_001'], 1)
        # Array_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'Array_t', '1', ['/Experiment_g/Sorts_g/Array_t_001'], 3)
        # All_Array_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 'All_Array_t', None,
            ['/Experiment_g/Sorts_g/Array_t_001',
             '/Experiment_g/Sorts_g/Array_t_002',
             '/Experiment_g/Sorts_g/Array_t_003',
             '/Experiment_g/Sorts_g/Array_t_004',
             '/Experiment_g/Sorts_g/Array_t_008',
             '/Experiment_g/Sorts_g/Array_t_009'], 10)
        # Response_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'Response_t', None, ['/Experiment_g/Responses_g/Response_t'], 7)
        # Report_t: not exist
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'Report_t', None, [], 0)
        # Receiver_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'Receiver_t', None, ['/Experiment_g/Receivers_g/Receiver_t'], 4)
        # Index_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'Index_t', None, ['/Experiment_g/Receivers_g/Index_t'], 11)
        # Map_Index_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'Map_Index_t', None, ['/Experiment_g/Maps_g/Index_t'], 6)
        # Das_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'Das_t', '5553', ['/Experiment_g/Receivers_g/Das_g_5553/Das_t'], 3)
        # Time_t
        self._test_PH5toTableData(
            self.statusbar, self.ph5, filename, path2file, 
            'Time_t', None, ['/Experiment_g/Receivers_g/Time_t'], 1)

    def test__appendTable(self):
        """
        test _appendTable method
        """
        # begin with 2 rows data
        tables = {}
        path = "table/path"
        tables[path] = []
        keys = ['key1', 'key2', 'key3']
        rows = [{'key1': 'val11', 'key2': 'val12', 'key3': 13},
                {'key1': 'val21', 'key2': 'val22', 'key3': 23}]
        ph5Val = Rows_Keys(rows, keys)
        ret = kefutility._appendTable(
            tables[path], ph5Val, path, self.statusbar, 0)
        self.assertEqual(3, len(ret))
        # count:
        self.assertEqual(len(rows), ret[0])
        # totalLines
        self.assertEqual(len(rows), ret[1])
        # type_
        self.assertEqual([str, str, int], ret[2])

        # add 3 rows data, fake count = 9999 to show message on statusbar
        keys = ['key1', 'key2', 'key3']
        rows = [{'key1': 'val31', 'key2': 'val32', 'key3': 33},
                {'key1': 'val41', 'key2': 'val42', 'key3': 43},
                {'key1': 'val51', 'key2': 'val52', 'key3': 53}]
        ph5Val = Rows_Keys(rows, keys)
        ret = kefutility._appendTable(
            tables[path], ph5Val, path, self.statusbar, 9999)
        # count:
        self.assertEqual(len(rows) + 9999, ret[0])
        # totalLines
        self.assertEqual(len(rows), ret[1])
        # type_
        self.assertEqual([str, str, int], ret[2])
        # statusbar's message. In real, ret[1]should be >= 10000
        msg = "Converting PH5 to Data in %s: 10000/%s" % (path, ret[1])
        self.assertEqual(msg, self.statusbar.message)
        
    def test_GetPrePH5Info(self):
        """
        test GetPrePH5Info method
        """
        # wrong path
        self.assertRaises(kefutility.KefUtilityError, kefutility.GetPrePH5Info,
                          'master.ph5', 'ph5/test_data/ph')
        # not exist file
        self.assertRaises(kefutility.KefUtilityError, kefutility.GetPrePH5Info,
                          'maste.ph5', 'ph5/test_data/ph5')
        # right path ##########################################
        ret = kefutility.GetPrePH5Info(filename='master.ph5',
                                       path2file='ph5/test_data/ph5')
        self.assertEqual(6, len(ret))
        # ph5
        self.ph5 = ret[0]  # to be close in tearDown
        self.assertEqual('ph5/test_data/ph5/master.ph5',
                         ret[0].filename)
        # availTables
        self.assertEqual(
            ['All_Array_t', 'All_Event_t', 'All_Offset_t', 'Array_t', 'Das_t',
             'Event_t', 'Experiment_t', 'Index_t', 'Map_Index_t', 'Offset_t',
             'Receiver_t', 'Response_t', 'Sort_t', 'Time_t'],
            ret[1])
        # arrays
        self.assertEqual(['1', '2', '3', '4', '8', '9'], ret[2])
        # shotLines:
        self.assertEqual(['001'], ret[3])
        # offsets:
        self.assertEqual(['001_001', '002_001', '003_001',
                          '004_001', '008_001', '009_001'], ret[4])
        # das:
        self.assertEqual(['12183', '3X500', '5553', '9EEF'], ret[5])

    def assertHtmlTags(self, html):
        _html_parser = etree.HTMLParser(recover = False)
        try:
            etree.parse(StringIO(html), _html_parser)
        except etree.XMLSyntaxError, e:
            err_msg = str(e)
            errs = re.split(' |,', err_msg)
            line_col = [int(i) for i in errs if i.isdigit()]
            html_lines = html.split('\n')
            r = line_col[0] - 1
            err_msg += '\n' + '\n'.join(
                ["line %s:%s" % (r, html_lines[r-1]),
                 "line %s:%s" % (r + 1, html_lines[r]),
                 "line %s:%s" % (r + 2, html_lines[r+1])])
            raise AssertionError(err_msg)

    def test_html(self):
        """
        test if html_manual and html_whatnews are in the right syntax
        """
        self.assertHtmlTags(kefutility.html_manual)
        self.assertHtmlTags(kefutility.html_whatsnew)


    def tearDown(self):
        """
        teardown for tests
        """
        try:
            #self.parent.close()
            os.remove('master.ph5')
            os.remove('miniPH5_00001.ph5')
        except Exception:
            pass
        try:
            self.nukeT.close_ph5()
        except Exception:
            pass
        try:
            self.ph5.close()
        except Exception:
            pass
        listdir = os.listdir('.')
        for f in listdir:
            if f.endswith('.kef'):
                os.remove(f)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    unittest.main()
    sys.exit(app.exec_())
