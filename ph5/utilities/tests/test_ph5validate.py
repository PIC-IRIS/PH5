'''
Tests for metadatatoph5
'''
import unittest
from ph5.core import ph5api
from ph5.utilities import ph5validate
import os
import shutil
import tempfile

import ph5.utilities

class TestPh5Validate(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.alltests_result = []
        self.home = os.getcwd()
        kefpath = self.home + "/ph5/test_data/metadata/array_t_9_validate.kef"
        datapath = self.home + "/ph5/test_data/rt125a/I2183RAW.TRD"
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)
        os.system("initialize_ph5 -n master.ph5")
        os.system("125atoph5 -n master.ph5 -r %s" % datapath)
        os.system(
            "keftoph5 -n master.ph5 -k %s" % kefpath)
        os.chdir(self.home)

    @classmethod
    def tearDownClass(self):
        if False in self.alltests_result:
            errmsg = "Some tests in TestPH5Validate have FAILED. "\
                "Inspect files created in %s." % self.tmpdir
            print(errmsg)
        else:
            try:
                shutil.rmtree(self.tmpdir)
            except Exception as e:
                print("Cannot remove %s due to the error:%s" %
                      (self.tmpdir, str(e)))
            filelist = os.listdir(".")
            for f in filelist:
                if f.endswith(".log"):
                    os.remove(f)

    def setUp(self):
        self.ph5_object = ph5api.PH5(
            nickname='master.ph5', path=self.tmpdir)
        self.ph5validate = ph5validate.PH5Validate(
            self.ph5_object, self.tmpdir,
            level="ERROR", outfile="ph5_validate.log")

    def tearDown(self):
        """"""
        try:
            self.ph5_object.ph5close()
        except BaseException:
            pass
        self.alltests_result.append(
            self._resultForDoCleanups.wasSuccessful())

    def test_analyze_time(self):
        """
        test analyze_method to see if das_time created has all time and station
        info. Does it catch the case data exists before or after the whole
        time range?
        """
        ph5.utilities.125a2ph5.FILES = []
        self.ph5validate.analyze_time()
        self.assertEqual(self.ph5validate.das_time.keys(), ['12183'])
        Dtime = self.ph5validate.das_time['12183']
        self.assertEqual(Dtime.keys(), [1])
        self.assertEqual(Dtime[1].keys(), [500])
        self.assertEqual(len(Dtime[1][500]), 3)  # for 3 different deploy time

        # station 9001: with the smallest deploy time,
        # check for "Data exists before deploy time"
        self.assertEqual([1550849950, 1550850034, '9001',
                          'Data exists before deploy time: 7 seconds.'],
                         Dtime[1][500][0])
        self.assertEqual([1550850043, 1550850093, '9002', ''],
                         Dtime[1][500][1])
        # station 9003: with the biggest pickup time,
        # check for "Data exists after pickup time"
        self.assertEqual([1550850125, 1550850187, '9003',
                          'Data exists after pickup time: 2 seconds.'],
                         Dtime[1][500][2])

    def test_check_station_completeness(self):
        self.ph5validate.das_time = \
            {'12183': {1: {500: [[1550849950, 1550850034, '9001',
                                  'Data exists before deploy time: 7 seconds.'
                                  ],
                                 [1550850043, 1550850093, '9002', ''],
                                 [1550850125, 1550850187, '9003',
                                  'Data exists after deploy time: 2 seconds.']
                                 ]}}}
        self.ph5validate.read_arrays('Array_t_009')
        arraybyid = self.ph5validate.ph5.Array_t['Array_t_009']['byid']

        # check returning warning from das_time
        station = arraybyid.get('9001')[1][0]
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertIn('Data exists before deploy time: 7 seconds.', warnings)
        # check warning data after pickup time
        station = arraybyid.get('9002')[1][0]
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertIn('Data exists after pickup time: 36 seconds.', warnings)
        # check error overlaping
        # => change deploy time of the 3rd station
        self.ph5validate.das_time['12183'][1][500][2][0] = 1550850090
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn('Overlap time on station(s): 9003, 9002', errors)
        # check no data found for array's time
        # => change array's time to where there is no data
        # this can only check if there is no data exit before deploy time
        # or after pickup time
        station = arraybyid.get('9003')[1][0]
        station['deploy_time/epoch_l'] = \
            self.ph5validate.das_time['12183'][1][500][2][0] = 1550850190
        station['pickup_time/epoch_l'] = \
            self.ph5validate.das_time['12183'][1][500][2][1] = 1550850191
        self.ph5validate.das_time['12183'][1][500][2][3] = ""
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn("No data found for das serial number 12183 during this "
                      "station's time. You may need to reload the raw data "
                      "for this station.",
                      errors)
        # check no data found errors
        station = arraybyid.get('9002')[1][0]
        station['das/serial_number_s'] = '1218'
        self.ph5validate.das_time['1218'] = self.ph5validate.das_time['12183']
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn("No data found for das serial number 1218. "
                      "You may need to reload the raw data for this station.",
                      errors)


if __name__ == "__main__":
    unittest.main()
