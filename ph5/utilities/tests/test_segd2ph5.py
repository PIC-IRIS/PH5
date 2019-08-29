'''
Tests for segd2ph5
'''
import unittest
import sys
import os
from mock import patch
from ph5.utilities import segd2ph5, tabletokef
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


class TestSegdtoph5(unittest.TestCase):
    print "Test segd2ph5"

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
                        errmsg += "BEFORE the difference:\n\t'%s'\\n" % \
                            str1[:i]
                    errmsg += "Different at:\n\tstr1: '%s'\n\tstr2: '%s'\n"\
                        "AFTER:\n\tstr1: '%s'\n\tstr2: '%s'" % \
                        (str1[i], str2[i], str1[i+1:], str2[i+1:])
                    raise AssertionError(errmsg)

    def start_segd2ph5(self):
        self.conv = segd2ph5.SEGD2PH5()
        self.files = ["ph5/test_data/segd/rg16/PIC_9_9050_2875.0.0.rg16",
                      "ph5/test_data/segd/rg16/PIC_9_9050_2901.0.0.rg16",
                      "ph5/test_data/segd/3ch.fcnt"]
        self.conv.PH5 = "master.ph5"
        self.conv.initialize_ph5()

    def tearDown(self):
        filelist = os.listdir(".")
        try:
            self.conv.EX.ph5close()
            self.conv.EXREC.ph5close()
            del self.conv.SD
            del self.conv
        except Exception:
            pass
        for f in filelist:
            if f.endswith(".ph5") or f.endswith(".log"):
                os.remove(f)

    def read_first_trace_in_file(self, f):
        SIZE = os.path.getsize(f)
        SD = self.conv.process_SD(f)
        self.conv.Das = segd2ph5.get_das(SD)
        self.conv.RESP = segd2ph5.Resp(self.conv.EX.ph5_g_responses)
        rows, keys = self.conv.EX.ph5_g_receivers.read_index()
        self.conv.INDEX_T_DAS = segd2ph5.Rows_Keys(rows, keys)
        self.conv.EXREC = self.conv.get_current_data_only(SIZE, self.conv.Das)

        trace, cs = self.conv.SD.process_trace()
        T = segd2ph5.Trace(trace, SD.trace_headers)
        return T

    def test_process_traces(self):
        """
        test process_traces
        """
        self.start_segd2ph5()
        T = self.read_first_trace_in_file(self.files[2])
        self.conv.process_traces(self.conv.SD.reel_headers, T.headers, T.trace)

        # check ARRAY_T
        array_line = self.conv.ARRAY_T.keys()[0]
        self.assertEqual(array_line, 1)

        das = self.conv.ARRAY_T[array_line].keys()[0]
        self.assertEqual(das, '3X500')

        deploy_time = self.conv.ARRAY_T[array_line][das].keys()[0]
        self.assertEqual(deploy_time, 1502293592)

        chan = self.conv.ARRAY_T[array_line][das][deploy_time].keys()[0]
        self.assertEqual(chan, 1)

        # DAS_INFO
        self.assertEqual(self.conv.DAS_INFO.keys()[0], '3X500')
        das_info = self.conv.DAS_INFO['3X500'][0]
        self.assertEqual(das_info.ph5file, './miniPH5_00001.ph5')
        self.assertEqual(das_info.ph5path,
                         "/Experiment_g/Receivers_g/Das_g_3X500")
        self.assertEqual(das_info.startepoch,  1502294400.38)
        self.assertEqual(das_info.stopepoch,  1502294430.38)
        self.assertEqual(das_info.das, '3X500')

        # MAP_INFO
        self.assertEqual(self.conv.MAP_INFO.keys()[0], '3X500')
        map_info = self.conv.MAP_INFO['3X500'][0]
        self.assertEqual(map_info.ph5file, './miniPH5_00001.ph5')
        self.assertEqual(map_info.ph5path,
                         "/Experiment_g/Maps_g/Das_g_3X500")
        self.assertEqual(map_info.startepoch,  1502294400.38)
        self.assertEqual(map_info.stopepoch,  1502294430.38)
        self.assertEqual(map_info.das, '3X500')

        # RESP
        R_KEYS = ['n_i', 'bit_weight/value_d', 'bit_weight/units_s',
                  'gain/units_s', 'gain/value_i', 'response_file_a',
                  'response_file_das_a', 'response_file_sensor_a']
        LINE = {'gain/value_i': 24, 'response_file_das_a': '',
                'bit_weight/units_s': 'mV/count',
                'bit_weight/value_d': 1.8596649169921875e-05,
                'gain/units_s': 'dB', 'response_file_a': '',
                'response_file_sensor_a': '', 'n_i': 0}
        self.assertEqual(self.conv.RESP.keys, R_KEYS)
        self.assertEqual(len(self.conv.RESP.lines), 1)
        for k in R_KEYS:
            self.assertEqual(self.conv.RESP.lines[0][k], LINE[k])

    def test_process_array(self):
        """
        test process_array
        """
        self.start_segd2ph5()
        # test process_array to read the first deploy of the first 2 files
        # in self.files.
        # the result ARRAY_T should have 2 different deploy times
        # for the same das 9X9050 (need to change file to put into git)
        for i in range(2):
            T = self.read_first_trace_in_file(self.files[i])
            self.conv.process_array(self.conv.SD.reel_headers, T.headers)

        array_line = self.conv.ARRAY_T.keys()[0]
        self.assertEqual(array_line, 9)

        das = self.conv.ARRAY_T[array_line].keys()[0]
        self.assertEqual(das, '9X9050')

        deploy_total = len(self.conv.ARRAY_T[array_line][das])
        self.assertEqual(deploy_total, 2)

        # deploy_time 1st
        deploy_time = self.conv.ARRAY_T[array_line][das].keys()[0]
        self.assertEqual(deploy_time, 1544545576)
        chan = self.conv.ARRAY_T[array_line][das][deploy_time].keys()[0]
        self.assertEqual(chan, 1)

        # deploy_time 2nd
        deploy_time = self.conv.ARRAY_T[array_line][das].keys()[1]
        self.assertEqual(deploy_time, 1546021724)
        chan = self.conv.ARRAY_T[array_line][das][deploy_time].keys()[0]
        self.assertEqual(chan, 1)

    def test_write_arrays(self):
        """
        test write_arrays
        """
        self.start_segd2ph5()
        T = self.read_first_trace_in_file(self.files[2])
        self.conv.process_traces(self.conv.SD.reel_headers, T.headers, T.trace)
        self.conv.write_arrays(self.conv.ARRAY_T)
        self.conv.EX.ph5close()
        self.conv.EXREC.ph5close()
        testargs = ['tabletokef', '-n', 'master.ph5', '--all_arrays']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        lines = out.getvalue().strip().split("Array_t_")[1].split("\n")

        array_line = self.conv.ARRAY_T.keys()[0]
        das = self.conv.ARRAY_T[array_line].keys()[0]
        deploy_time = self.conv.ARRAY_T[array_line][das].keys()[0]
        chan = self.conv.ARRAY_T[array_line][das][deploy_time].keys()[0]
        row = self.conv.ARRAY_T[array_line][das][deploy_time][chan][0]
        self.assertEqual(int(lines[0]), array_line)
        for i in range(1, len(lines)):
            ss = lines[i].strip().split("=")
            if 'location' in ss[0] or 'response' in ss[0] \
               or 'receiver' in ss[0] or 'sensor' in ss[0]:
                continue
            self.assertEqual(ss[1], str(row[ss[0]]))

    def test_get_args(self):
        """
        test get_args
        """

    def assertTable(self, options, pathtokef, pathtomaster=''):
        testargs = ['tabletokef', '-n', 'master.ph5'] + options
        if pathtomaster != '':
            testargs += ['-p', pathtomaster]
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                tabletokef.main()
        result_lines = out.getvalue().strip().split("#   Table row ")[1:]
        with open(pathtokef) as content_file:
            comp_lines = \
                content_file.read().strip().split("#   Table row ")[1:]

        for i in range(len(result_lines)):
            if "time_stamp" in result_lines[i]:
                result_lines[i] = result_lines[i].split("time_stamp")[0]
                comp_lines[i] = comp_lines[i].split("time_stamp")[0]
            self.assertStrEqual(result_lines[i], comp_lines[i])

    def test_main(self):
        """
        test main
        """
        # run list file with path to 2 segd files for the same das, same array
        # different deploy times
        testargs = ['segdtoph5', '-n', 'master.ph5',
                    '-f', 'ph5/test_data/segd/rg16/RG16_list']
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()
        # check array
        self.assertTable(
            ['--all_arrays'], 'ph5/test_data/segd/rg16/all_arrays.kef')
        # check das_t_9X9050
        self.assertTable(
            ['--Das_t', '9X9050'], 'ph5/test_data/segd/rg16/das_t_9X9050.kef')
        # check index_t
        self.assertTable(
            ['--Index_t'], 'ph5/test_data/segd/rg16/index_t.kef')
        # check M_index_t
        self.assertTable(
            ['--M_Index_t'], 'ph5/test_data/segd/rg16/M_index_t.kef')


if __name__ == "__main__":
    unittest.main()
