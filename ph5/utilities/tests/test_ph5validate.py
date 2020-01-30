'''
Tests for metadatatoph5
'''
import unittest
import logging
from StringIO import StringIO
from ph5 import logger, ch
from ph5.core import ph5api, experiment
from ph5.utilities import ph5validate, texan2ph5, kef2ph5
import os
import shutil
import tempfile
from contextlib import contextmanager


@contextmanager
def captured_log():
    capture = StringIO()
    try:
        chan = logging.StreamHandler(capture)
        logger.removeHandler(ch)
        logger.addHandler(chan)
        yield capture
    finally:
        logger.removeHandler(chan)
        logger.addHandler(ch)


def initialize_ph5(nickname, path, editmode=False):
    ex = experiment.ExperimentGroup(nickname=nickname, currentpath=path)
    ex.ph5open(editmode)
    ex.initgroup()
    return ex


def get_dir():
    home = os.getcwd()
    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)
    return home, tmpdir


class TestPh5Validate(unittest.TestCase):
    def setUp(self):
        # create tmpdir
        self.home, self.tmpdir = get_dir()
        kefpath = self.home + "/ph5/test_data/metadata/array_t_9_validate.kef"
        datapath = self.home + "/ph5/test_data/rt125a/I2183RAW.TRD"

        # initiate ph5
        ex = initialize_ph5("master.ph5", self.tmpdir, True)

        # add texan data
        texan2ph5.EX = ex
        texan2ph5.FILES = [datapath]
        texan2ph5.FIRST_MINI = 1
        texan2ph5.WINDOWS = None
        texan2ph5.SR = None
        with captured_log():
            texan2ph5.process()

        # add array table
        kef2ph5.EX = ex
        kef2ph5.KEFFILE = kefpath
        kef2ph5.PH5 = "master.ph5"
        kef2ph5.TRACE = False
        with captured_log():
            kef2ph5.populateTables()

        try:
            ex.ph5close()
            texan2ph5.EXREC.ph5close()
        except Exception:
            pass

        self.ph5_object = ph5api.PH5(
            nickname='master.ph5', path=self.tmpdir)
        self.ph5validate = ph5validate.PH5Validate(
            self.ph5_object, self.tmpdir,
            level="ERROR", outfile="ph5_validate.log")

    def tearDown(self):
        try:
            self.ph5_object.ph5close()
        except BaseException:
            pass

        if self._resultForDoCleanups.wasSuccessful():
            try:
                shutil.rmtree(self.tmpdir)
            except Exception as e:
                print("Cannot remove %s due to the error:%s" %
                      (self.tmpdir, str(e)))
        else:
            errmsg = "%s has FAILED. Inspect files created in %s." \
                % (self._testMethodName, self.tmpdir)
            print(errmsg)
        os.chdir(self.home)

    def test_analyze_time(self):
        """
        test analyze_method to see if das_time created has all time and station
        info. Does it catch the case data exists before or after the whole
        time range?
        """
        self.ph5validate.analyze_time()
        self.assertEqual(self.ph5validate.das_time.keys(), [('12183', 1, 500)])
        Dtime = self.ph5validate.das_time[('12183', 1, 500)]

        # 3 different deploy time
        self.assertEqual(len(Dtime['time_windows']), 3)

        # station 9001
        self.assertEqual(Dtime['time_windows'][0],
                         (1550849950, 1550850034, '9001'))
        # station 9002
        self.assertEqual(Dtime['time_windows'][1],
                         (1550850043, 1550850093, '9002'))
        # station 9003
        self.assertEqual(Dtime['time_windows'][2],
                         (1550850125, 1550850187, '9003'))

        self.assertEqual(Dtime['min_deploy_time'],
                         [1550849950,
                          'Data exists before deploy time: 7 seconds.'])

        self.assertEqual(Dtime['max_pickup_time'],
                         [1550850187,
                          'Data exists after pickup time: 2 seconds.'])

    def test_check_station_completeness(self):
        self.ph5validate.das_time = {
            ('12183', 1, 500):
            {'time_windows': [(1550849950, 1550850034, '9001'),
                              (1550850043, 1550850093, '9002'),
                              (1550850125, 1550850187, '9003')],
             'min_deploy_time': [1550849950,
                                 'Data exists before deploy time: 7 seconds.'],
             'max_pickup_time': [1550850187,
                                 'Data exists after deploy time: 2 seconds.']
             }
        }

        self.ph5validate.read_arrays('Array_t_009')
        arraybyid = self.ph5validate.ph5.Array_t['Array_t_009']['byid']
        DT = self.ph5validate.das_time[('12183', 1, 500)]

        # check warning before min_deploy_time
        station = arraybyid.get('9001')[1][0]
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertIn('Data exists before deploy time: 7 seconds.', warnings)

        # check warning after max_pickup_time
        station = arraybyid.get('9003')[1][0]
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertIn('Data exists after deploy time: 2 seconds.', warnings)

        # check warning data after pickup time
        station = arraybyid.get('9002')[1][0]
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertIn('Data exists after pickup time: 36 seconds.', warnings)

        # check error overlaping
        # => change deploy time of the 3rd station
        DT['time_windows'][2] = \
            (1550850090, 1550850187, '9003')
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn('Overlap time on station(s): 9002, 9003', errors)

        # check no data found for array's time
        # => change array's time to where there is no data
        station = arraybyid.get('9003')[1][0]
        station['deploy_time/epoch_l'] = 1550850190
        station['pickup_time/epoch_l'] = 1550850191
        DT['time_windows'][2] = (1550850190, 1550850191, '9003')
        with captured_log():
            ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn("No data found for das serial number 12183 during this "
                      "station's time. You may need to reload the raw data "
                      "for this station.",
                      errors)
        # check no data found errors
        station = arraybyid.get('9002')[1][0]
        station['das/serial_number_s'] = '1218'
        self.ph5validate.das_time[('1218', 1, 500)] = \
            self.ph5validate.das_time[('12183', 1, 500)]
        with captured_log():
            ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn("No data found for das serial number 1218. "
                      "You may need to reload the raw data for this station.",
                      errors)


if __name__ == "__main__":
    unittest.main()
