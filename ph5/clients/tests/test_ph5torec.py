"""
unit tests for ph5availability
"""

import unittest
from ph5.clients import ph5torec
from ph5.core import ph5api
import sys
import os
import re
from mock import patch
from contextlib import contextmanager
from StringIO import StringIO


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


class TestPH5toRec(unittest.TestCase):

    def setUp(self):
        """
        setup for tests
        """
        self.conv = ph5torec.PH5toRec()


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

    def test_get_args(self):
        """
        test get_args method
        """
        """
        # no nick name
        testargs = ['ph5torec']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                self.conv.get_args()

        # wrong no stations to gather
        testargs = ['ph5torec', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                self.conv.get_args()

        # no length
        testargs = ['ph5torec', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-S', '500,0407']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                self.conv.get_args()

        # no station array
        testargs = ['ph5torec', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-S', '500,0407', '-l', '60']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                self.conv.get_args()

        # no shotline
        testargs = ['ph5torec', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-S', '500,0407', '-l', '60',
                    '-A', '1']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                self.conv.get_args()

        # assign para
        testargs = ['ph5torec', '-n', 'master.ph5',
                    '-p', 'ph5/test_data/ph5',
                    '--channel', 'DP1', '--network', 'AA',
                    '--location', '00', '-c', '1,2', '-S', '500,0407',
                    '--event_list', '7001','-l', '60', '-O', '1', '-A', '9',
                    '--shot_line', '1','--stream', '-V', '1.1', '-d', '4',
                    '--sort_by_offset','--use_deploy_pickup', '-U', '-x', 'P', 
                    '--ic', '--break_standard', '-N', '--debug']
        with patch.object(sys, 'argv', testargs):
            self.conv.get_args()
        ret = vars(self.conv.ARGS)
        self.assertEqual('master.ph5', ret['ph5_file_prefix'])
        self.assertEqual('ph5/test_data/ph5', ret['ph5_path'])
        self.assertEqual('DP1', ret['seed_channel'])
        self.assertEqual('AA', ret['seed_network'])
        self.assertEqual('00', ret['seed_location'])
        self.assertEqual([1, 2], ret['channels'])
        self.assertEqual(['500', '0407'], ret['stations_to_gather'])
        self.assertEqual(['7001'], ret['evt_list'])
        self.assertEqual(60, ret['length'])
        self.assertEqual(1.0, ret['seconds_offset_from_shot'])
        self.assertEqual('Array_t_009', ret['station_array'])
        self.assertEqual('Event_t_001', ret['shot_line'])
        self.assertTrue(ret['write_stdout'])
        self.assertEqual(1.1, ret['red_vel'])
        self.assertEqual('4', ret['decimation'])
        self.assertTrue(ret['sort_by_offset'])
        self.assertTrue(ret['deploy_pickup'])
        self.assertTrue(ret['use_utm'])
        self.assertEqual('P', ret['ext_header'])
        self.assertTrue(ret['ignore_channel'])
        self.assertFalse(ret['break_standard'])
        self.assertFalse(ret['do_time_correct'])
        self.assertTrue(ret['debug'])
        """
        # assign para
        testargs = ['ph5torec', '-n', 'master.ph5', '-p', 'ph5/test_data/ph5',
                    '-S', '500,0407','--event_list', '7001', '-l', '60',
                    '-A', '9','--shot_line', '1',
                    '--shot_file', 'ph5/test_data/metadata/event_t.kef',
                    '-o', 'ph5/test_data/metadata']
        with patch.object(sys, 'argv', testargs):
            self.conv.get_args()
        ret = vars(self.conv.ARGS)
        self.assertTrue(ret['do_time_correct'])
        self.assertEqual('ph5/test_data/metadata', ret['out_dir'])
        self.assertFalse(ret['deploy_pickup'])
        self.assertEqual(-1, ret['red_vel'])
        self.assertFalse(ret['use_utm'])
        self.assertEqual('U', ret['ext_header'])
        self.assertFalse(ret['ignore_channel'])
        self.assertTrue(ret['break_standard'])
        self.assertFalse(ret['debug'])
        for n in self.conv.P5.Event_t_names:
            self.conv.P5.read_event_t(n)
        self.assertEqual(self.conv.P5.Event_t.keys(), ret['shot_file'].keys())

    def test_main(self):
        """
        test main function
        """

        # no nick name
        testargs = ['ph5toevent']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                ph5torec.main()

        # wrong no stations to gather
        testargs = ['ph5torec', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                ph5torec.main()

        # no length
        testargs = ['ph5torec', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-S', '500,0407']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                ph5torec.main()

        # no station array
        testargs = ['ph5torec', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-S', '500,0407', '-l', '60']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                ph5torec.main()

        # no shotline
        testargs = ['ph5torec', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-S', '500,0407', '-l', '60',
                    '-A', '1']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                self.assertEqual(1, ph5torec.main())

        """
        # assign para (with -E)
        testargs = ['ph5torec', '-n', 'master.ph5', '-p',
                    'ph5/test_data/ph5', '-S', '500,0407', '-l', '60',
                    '-A', '1', '--shot_line', '1', '--stream']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5torec.main()
        output = out.getvalue().strip()
        print('output:', output)
        """
        
    #def tearDown(self):
        #"""
        #teardown for tests
        #"""
        #self.ph5_object.close()


if __name__ == "__main__":
    unittest.main()
