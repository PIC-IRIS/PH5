'''
Tests for ph5validate
'''
import unittest
import os
import sys
import logging
import shutil
from StringIO import StringIO

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.utilities import ph5validate, segd2ph5, nuke_table, kef2ph5
from ph5.core import ph5api
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase, kef_to_ph5


class TestPH5Validate_response_info(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5Validate_response_info, self).setUp()
        # copy ph5 data and tweak sensor model and sample rate in array 9
        # to test for inconsistencies between filenames and info
        orgph5path = os.path.join(self.home, "ph5/test_data/ph5")
        shutil.copy(os.path.join(orgph5path, 'master.ph5'),
                    os.path.join(self.tmpdir, 'master.ph5'))
        shutil.copy(os.path.join(orgph5path, 'miniPH5_00001.ph5'),
                    os.path.join(self.tmpdir, 'miniPH5_00001.ph5'))
        testargs = ['delete_table', '-n', 'master.ph5', '-A', '9']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                f = StringIO('y')
                sys.stdin = f
                nuke_table.main()
                f.close()
        kefpath = os.path.join(
            self.home,
            'ph5/test_data/metadata/array_9_test_resp_filename.kef')
        testargs = ['keftoph5', '-n', 'master.ph5', '-k', kefpath]
        with patch.object(sys, 'argv', testargs):
            kef2ph5.main()

        self.ph5API_object = ph5api.PH5(path=self.tmpdir,
                                        nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(self.ph5API_object, '.')

    def tearDown(self):
        self.ph5API_object.close()
        super(TestPH5Validate_response_info, self).tearDown()

    def test_check_array_t(self):
        # change response_file_sensor_a to
        # test for No response data loaded for gs11
        response_t = self.ph5validate.ph5.get_response_t_by_n_i(4)
        response_t['response_file_sensor_a'] = '/Experiment_g/Responses_g/gs11'
        with LogCapture():
            ret = self.ph5validate.check_array_t()
        for r in ret:
            if 'Station 9001' in r.heading:
                self.assertEqual(r.heading,
                                 "-=-=-=-=-=-=-=-=-\n"
                                 "Station 9001 Channel 1\n"
                                 "4 error, 1 warning, 0 info\n"
                                 "-=-=-=-=-=-=-=-=-\n"
                                 )
                # this error causes by changing samplerate
                errors = [
                    "No data found for das serial number 12183 during "
                    "this station's time. You may need to reload the "
                    "raw data for this station.",
                    'Response_t[4]:No response data loaded for gs11.',
                    "Response_t[4]:response_file_das_a 'rt125a_500_1_32' is "
                    "inconsistent with Array_t_009:sr=100. Please check with "
                    "resp_load format [das_model]_[sr]_[srm]_[gain].",
                    "Response_t[4]:response_file_sensor_a 'gs11' is "
                    "inconsistent with Array_t_009:sensor_model=cmg3t."]
                self.assertEqual(
                    set(r.error),
                    set(errors))
                self.assertEqual(
                    r.warning,
                    ['No station description found.'])
            if 'Station 0407 Channel -2' in r.heading:
                self.assertEqual(r.heading,
                                 "-=-=-=-=-=-=-=-=-\n"
                                 "Station 0407 Channel -2\n"
                                 "1 error, 2 warning, 0 info\n"
                                 "-=-=-=-=-=-=-=-=-\n"
                                 )
                self.assertEqual(
                    r.error,
                    ['Response_t[-1]:'
                     'Metadata response with n_i=-1 has no response data.'])
                # sample rate for station 0407 in array 4 is 0
                self.assertEqual(
                    r.warning,
                    ['No station description found.',
                     'Sample rate seems to be 0. Is this correct???'])


class TestPh5Validate_main_detect_data(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestPh5Validate_main_detect_data, self).setUp()
        kef_to_ph5(
            self.tmpdir, 'master.ph5',
            os.path.join(self.home, 'ph5/test_data'),
            ['rt125a/das_t_12183.kef', 'metadata/array_t_9_validate.kef'],
            das_sn_list=['12183'])

    def test_main(self):
        # test invalid level
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARN']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                self.assertRaises(SystemExit, ph5validate.main)
                output = out.captured.strip().split('\n')
        self.assertEqual(
            output[1],
            "ph5_validate: error: argument -l/--level: invalid choice: "
            "'WARN' (choose from 'ERROR', 'WARNING', 'INFO')")

        # test WARNING level
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARNING']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                ph5validate.main()
        with open('ph5_validate.log') as f:
            all_logs = f.read().split("-=-=-=-=-=-=-=-=-\n")

        self.assertEqual(
            all_logs[2],
            'ERROR: Experiment_t does not exist. '
            'run experiment_t_gen to create table\n')
        self.assertEqual(
            all_logs[3],
            'Station 9001 Channel 1\n2 error, 3 warning, 0 info\n')
        self.assertEqual(
            all_logs[4],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'ERROR: Response_t has no entry for n_i=7\n'
            'WARNING: No station description found.\n'
            'WARNING: Data exists before deploy time: 7 seconds.\n'
            'WARNING: Station 9001 [1550849950, 1550850034] is repeated '
            '2 time(s)\n')
        self.assertEqual(
            all_logs[5],
            'Station 9002 Channel 1\n2 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[6],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'ERROR: Response_t has no entry for n_i=7\n'
            'WARNING: No station description found.\n'
            'WARNING: Data exists after pickup time: 36 seconds.\n')
        self.assertEqual(
            all_logs[7],
            'Station 9003 Channel 1\n2 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[8],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'ERROR: Response_t has no entry for n_i=7\n'
            'WARNING: No station description found.\n'
            'WARNING: Data exists after pickup time: 2 seconds.\n')

        # test ERROR level
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'ERROR']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                ph5validate.main()
        with open('ph5_validate.log') as f:
            all_logs = f.read().split("-=-=-=-=-=-=-=-=-\n")

        self.assertEqual(
            all_logs[2],
            'ERROR: Experiment_t does not exist. '
            'run experiment_t_gen to create table\n')
        self.assertEqual(
            all_logs[3],
            'Station 9001 Channel 1\n2 error, 3 warning, 0 info\n')
        self.assertEqual(
            all_logs[4],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'ERROR: Response_t has no entry for n_i=7\n')
        self.assertEqual(
            all_logs[5],
            'Station 9002 Channel 1\n2 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[6],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'ERROR: Response_t has no entry for n_i=7\n')
        self.assertEqual(
            all_logs[7],
            'Station 9003 Channel 1\n2 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[8],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'ERROR: Response_t has no entry for n_i=7\n')

    def test_get_args(self):
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARN']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                self.assertRaises(SystemExit, ph5validate.get_args)
        output = out.captured.strip().split('\n')
        self.assertEqual(
            output[1],
            "ph5_validate: error: argument -l/--level: invalid choice: "
            "'WARN' (choose from 'ERROR', 'WARNING', 'INFO')")

        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARNING']
        with patch.object(sys, 'argv', testargs):
            ret = ph5validate.get_args()
        self.assertEqual(ret.level, 'WARNING')
        self.assertEqual(ret.nickname, 'master.ph5')
        self.assertEqual(ret.outfile, 'ph5_validate.log')
        self.assertEqual(ret.ph5path, self.tmpdir)
        self.assertEqual(ret.verbose, False)


class TestPh5Validate_conflict_time(TempDirTestCase, LogTestCase):
    """
    Check conflict times between array_t and das_t
    """
    def setUp(self):
        super(TestPh5Validate_conflict_time, self).setUp()
        kef_to_ph5(
            self.tmpdir, 'master.ph5',
            os.path.join(self.home, 'ph5/test_data'),
            ['rt125a/das_t_12183.kef', 'metadata/array_t_9_validate.kef'],
            das_sn_list=['12183'])
        self.ph5_object = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(
            self.ph5_object, self.tmpdir)

    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestPh5Validate_conflict_time, self).tearDown()

    def test_check_array_t(self):
        """
        check log messages, das_time and validation block return
        """
        with LogCapture() as log:
            log.setLevel(logging.INFO)
            vb = self.ph5validate.check_array_t()

        self.assertEqual(log.records[0].msg, "Validating Array_t")

        self.assertEqual(
            self.ph5validate.das_time,
            {('12183', 1, 500):
                {'max_pickup_time': [1550850187],
                 'time_windows': [(1550849950, 1550850034, '9001'),
                                  (1550849950, 1550850034, '9001'),
                                  (1550849950, 1550850034, '9001'),
                                  (1550850043, 1550850093, '9002'),
                                  (1550850125, 1550850187, '9003')],
                 'min_deploy_time':
                     [1550849950,
                      'Data exists before deploy time: 7 seconds.']}}
        )

        self.assertEqual(vb[0].heading,
                         '-=-=-=-=-=-=-=-=-\nStation 9001 Channel 1\n'
                         '2 error, 3 warning, 0 info\n-=-=-=-=-=-=-=-=-\n')
        self.assertEqual(vb[0].info, [])
        self.assertEqual(
            vb[0].warning,
            ['No station description found.',
             'Data exists before deploy time: 7 seconds.',
             'Station 9001 [1550849950, 1550850034] is repeated 2 time(s)'])
        self.assertEqual(
            vb[0].error,
            ['No Response table found. Have you run resp_load yet?',
             'Response_t has no entry for n_i=7']
        )

        self.assertEqual(vb[1].heading,
                         '-=-=-=-=-=-=-=-=-\nStation 9002 Channel 1\n'
                         '2 error, 2 warning, 0 info\n-=-=-=-=-=-=-=-=-\n')
        self.assertEqual(vb[1].info, [])
        self.assertEqual(
            vb[1].warning,
            ['No station description found.',
             'Data exists after pickup time: 36 seconds.'])
        self.assertEqual(
            vb[1].error,
            ['No Response table found. Have you run resp_load yet?',
             'Response_t has no entry for n_i=7']
        )

        self.assertEqual(vb[2].heading,
                         '-=-=-=-=-=-=-=-=-\nStation 9003 Channel 1\n'
                         '2 error, 2 warning, 0 info\n-=-=-=-=-=-=-=-=-\n')
        self.assertEqual(vb[2].info, [])
        self.assertEqual(
            vb[2].warning,
            ['No station description found.',
             'Data exists after pickup time: 2 seconds.'])
        self.assertEqual(
            vb[2].error,
            ['No Response table found. Have you run resp_load yet?',
             'Response_t has no entry for n_i=7']
        )

    def test_analyze_time(self):
        """
        + check if das_time created has all time and station info
        + check if it catch the case data exists before the whole time range
        """
        self.ph5validate.analyze_time()
        self.assertEqual(self.ph5validate.das_time.keys(), [('12183', 1, 500)])
        Dtime = self.ph5validate.das_time[('12183', 1, 500)]

        # 3 different deploy time
        self.assertEqual(len(Dtime['time_windows']), 5)

        # station 9001
        self.assertEqual(Dtime['time_windows'][0],
                         (1550849950, 1550850034, '9001'))
        self.assertEqual(Dtime['time_windows'][1],
                         (1550849950, 1550850034, '9001'))
        self.assertEqual(Dtime['time_windows'][2],
                         (1550849950, 1550850034, '9001'))
        # station 9002
        self.assertEqual(Dtime['time_windows'][3],
                         (1550850043, 1550850093, '9002'))
        # station 9003
        self.assertEqual(Dtime['time_windows'][4],
                         (1550850125, 1550850187, '9003'))

        self.assertEqual(Dtime['min_deploy_time'],
                         [1550849950,
                          'Data exists before deploy time: 7 seconds.'])

    def test_check_station_completeness(self):
        self.ph5validate.das_time = {
            ('12183', 1, 500):
            {'time_windows': [(1550849950, 1550850034, '9001'),
                              (1550849950, 1550850034, '9001'),
                              (1550849950, 1550850034, '9001'),
                              (1550849950, 1550850034, '9001'),
                              (1550850043, 1550850093, '9002'),
                              (1550850125, 1550850187, '9003')],
             'min_deploy_time': [1550849950,
                                 'Data exists before deploy time: 7 seconds.'],
             }
        }

        self.ph5validate.read_arrays('Array_t_009')
        arraybyid = self.ph5validate.ph5.Array_t['Array_t_009']['byid']
        DT = self.ph5validate.das_time[('12183', 1, 500)]

        # check lon/lat not in range
        # check warning data exist before min_deploy_time
        station = arraybyid.get('9001')[1][0]
        station['location/X/value_d'] = 190.0
        station['location/X/units_s'] = 'degrees'
        station['location/Y/value_d'] = -100.0
        station['location/Y/units_s'] = 'degrees'
        station['location/Z/value_d'] = 1403
        station['location/Z/units_s'] = 'm'
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertEqual(
            warnings,
            ['No station description found.',
             'Data exists before deploy time: 7 seconds.',
             'Station 9001 [1550849950, 1550850034] is repeated 3 time(s)'])
        errors = ret[2]
        self.assertEqual(
            errors,
            ['No Response table found. Have you run resp_load yet?',
             'Channel longitude 190.0 not in range [-180,180]',
             'Channel latitude -100.0 not in range [-90,90]'])
        # check lon/lat = 0, no units, no elevation value
        # check warning data after pickup time
        station = arraybyid.get('9002')[1][0]
        station['location/X/value_d'] = 0
        station['location/X/units_s'] = ''
        station['location/Y/value_d'] = 0
        station['location/Y/units_s'] = None
        station['location/Z/value_d'] = None
        station['location/Z/units_s'] = ''
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertEqual(
            warnings,
            ['No station description found.',
             'Channel longitude seems to be 0. Is this correct???',
             'No Station location/X/units_s value found.',
             'Channel latitude seems to be 0. Is this correct???',
             'No Station location/Y/units_s value found.',
             'No Station location/Z/units_s value found.',
             'Data exists after pickup time: 36 seconds.'])
        errors = ret[2]
        self.assertEqual(
            errors,
            ['No Response table found. Have you run resp_load yet?'])

        # check error overlaping
        # => change deploy time of the 3rd station
        DT['time_windows'][5] = (1550850090, 1550850187, '9003')
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn('Overlap time on station(s): 9002, 9003', errors)

        # check no data found for array's time
        # => change array's time to where there is no data
        station = arraybyid.get('9003')[1][0]
        station['deploy_time/epoch_l'] = 1550850190
        station['pickup_time/epoch_l'] = 1550850191
        DT['time_windows'][5] = (1550850190, 1550850191, '9003')
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn("No data found for das serial number 12183 during this "
                      "station's time. You may need to reload the raw data "
                      "for this station.",
                      errors)
        # check no data found errors
        station = arraybyid.get('9002')[1][0]
        station['das/serial_number_s'] = '1218'
        self.ph5validate.das_time[
            ('1218', 1, 500)] = self.ph5validate.das_time[('12183', 1, 500)]
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn("No data found for das serial number 1218. "
                      "You may need to reload the raw data for this station.",
                      errors)

    def test_check_station_completeness_duplicate_das_for_diff_stations(self):
        self.ph5validate.das_time = {
            ('12183', 1, 500):
            {'time_windows': [(1550849950, 1550850034, '9001'),
                              (1550849950, 1550850034, '9002')],
             'min_deploy_time': [1550849950],
             }
        }

        self.ph5validate.read_arrays('Array_t_009')
        arraybyid = self.ph5validate.ph5.Array_t['Array_t_009']['byid']
        station = arraybyid.get('9001')[1][0]
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertEqual(
            errors,
            ['No Response table found. Have you run resp_load yet?',
             'Das 12183 chan 1 spr 500 has been repeatly entered for '
             'time range [1550849950, 1550850034] on stations: 9001, 9002'])


class TestPh5Validate_currPH5(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestPh5Validate_currPH5, self).setUp()
        ph5path = os.path.join(self.home, 'ph5/test_data/ph5')
        self.ph5_object = ph5api.PH5(
            path=ph5path, nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(
            self.ph5_object, ph5path)

    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestPh5Validate_currPH5, self).tearDown()

    def test_check_experiment_t(self):
        # check no net_code_s
        experiment_t = self.ph5_object.Experiment_t['rows']
        experiment_t[0]['net_code_s'] = ''
        info, warning, error = \
            self.ph5validate.check_experiment_t_completeness(experiment_t)

        self.assertIn('Network code was not found: '
                      'A 2 character network code is required.',
                      error)

    def test_check_station_completeness(self):

        self.ph5validate.analyze_time()
        das_time = self.ph5validate.das_time

        station = self.ph5_object.Array_t['Array_t_008']['byid']['8001'][1][0]
        # id_s isn't a whole number => error
        das_time[('9EEF', 1, 100)]['time_windows'][0] = \
            (1463568480, 1463568540, '33a33')
        station['id_s'] = '33a33'
        inf, warn, err = self.ph5validate.check_station_completeness(station)
        self.assertIn("Station ID '33a33' not a whole number "
                      "between 0 and 32767.",
                      err)
        # id_s not in range [0,65535] => error
        das_time[('9EEF', 1, 100)]['time_windows'][0] = \
            (1463568480, 1463568540, '65536')
        station['id_s'] = '65536'
        inf, warn, err = self.ph5validate.check_station_completeness(station)
        # no more old error
        self.assertNotIn("Station ID '65536' not between 0 and 65535.",
                         err)
        self.assertIn("Station ID '65536' not between 0 and 32767.",
                      err)
        # id_s in range [32768, 65534] => no more old warning
        das_time[('9EEF', 1, 100)]['time_windows'][0] = \
            (1463568480, 1463568540, '33333')
        station['id_s'] = '33333'
        inf, warn, err = self.ph5validate.check_station_completeness(station)
        self.assertNotIn("Station ID '33333' is more than 32767. "
                         "Not compatible with SEGY revision 1.",
                         warn)

        # sample_rate=0 => warning
        das_time[('12183', 1, 0)] = das_time[('12183', 1, 500)]
        station = self.ph5_object.Array_t['Array_t_009']['byid']['9001'][1][0]
        station['sample_rate_i'] = 0
        inf, warn, err = self.ph5validate.check_station_completeness(station)
        self.assertIn("Sample rate seems to be 0. Is this correct???",
                      warn)
        # sample_rate<0 => error
        das_time[('12183', 1, -1)] = das_time[('12183', 1, 500)]
        station['sample_rate_i'] = -1
        inf, warn, err = self.ph5validate.check_station_completeness(station)
        self.assertIn("Sample rate = -1 not positive.",
                      err)

        # sample_rate_multiplier_i isn't a integer => error
        station['sample_rate_i'] = 500
        station['sample_rate_multiplier_i'] = 1.1
        inf, warn, err = self.ph5validate.check_station_completeness(station)
        self.assertIn("Sample rate multiplier = 1.1 is not an"
                      " integer greater than 1.",
                      err)
        # sample_rate_multiplier_i<1 => error
        station['sample_rate_multiplier_i'] = 0
        inf, warn, err = self.ph5validate.check_station_completeness(station)
        self.assertIn("Sample rate multiplier = 0 is not an integer "
                      "greater than 1.",
                      err)

    def test_check_event_t_completeness(self):
        self.ph5_object.read_event_t('Event_t_001')
        event = self.ph5_object.Event_t['Event_t_001']['byid']['7001']

        # id_s isn't a whole number => error
        event['id_s'] = '7a001'
        inf, warn, err = self.ph5validate.check_event_t_completeness(event)
        self.assertIn("Event ID '7a001' not a whole "
                      "number between 0 and 2147483647.",
                      err)
        # id_s isn't in range [0, 65535] => no more old error
        event['id_s'] = '65536'
        inf, warn, err = self.ph5validate.check_event_t_completeness(event)
        self.assertNotIn("Event ID '65536' not between 0 and 65535.",
                         err)
        # id_s in range [32768, 65534] => no more old warning
        event['id_s'] = '32769'
        inf, warn, err = self.ph5validate.check_event_t_completeness(event)
        self.assertNotIn("Event ID '32769' is more than 32767. "
                         "Not compatible with SEGY revision 1.",
                         warn)

        # id_s isn't in range [0, 2147483647] => error
        event['id_s'] = '-1'
        inf, warn, err = self.ph5validate.check_event_t_completeness(event)
        self.assertIn("Event ID '-1' not between 0 and 2147483647.",
                      err)

        # id_s isn't in range [0, 2147483647] => error
        event['id_s'] = '2147483648'
        inf, warn, err = self.ph5validate.check_event_t_completeness(event)
        self.assertIn("Event ID '2147483648' not between 0 and 2147483647.",
                      err)

        # no log for location/coordinate_system_s, projection_s, ellipsoid_s,
        # ellipsoid_s
        # warning for location/X,Y,Z/units_s
        event['id_s'] = '7001'
        event['location/Z/value_d'] = 0
        event['location/coordinate_system_s'] = ''
        event['location/projection_s'] = ''
        event['location/ellipsoid_s'] = ''
        event['location/description_s'] = ''
        event['location/X/units_s'] = ''
        event['location/Y/units_s'] = ''
        event['location/Z/units_s'] = ''
        inf, warn, err = self.ph5validate.check_event_t_completeness(event)
        self.assertEqual(warn,
                         ['Event description is missing.',
                          'No Event location/X/units_s value found.',
                          'No Event location/Y/units_s value found.',
                          'No Event location/Z/units_s value found.'])

        # remove error for location/Z/value_d = 0
        self.assertNotIn('No Event location/Z/value_d value found.', err)


class TestPh5Validate_noEvent(TempDirTestCase, LogTestCase):
    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestPh5Validate_noEvent, self).tearDown()

    def test_check_no_event(self):
        testargs = ['segd2ph5', '-n', 'master.ph5', '-r',
                    os.path.join(self.home, 'ph5/test_data/segd/fairfield/'
                                            '1111.1.0.fcnt')]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()
        self.ph5_object = ph5api.PH5(
            path=self.tmpdir, nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(
            self.ph5_object, self.tmpdir)
        vbs = self.ph5validate.check_event_t()
        self.assertEqual(len(vbs), 1)
        self.assertIn("Event_t table not found. "
                      "Did this experiment have shots???",
                      vbs[0]. warning)


class TestPH5Validate_no_response_filename(LogTestCase, TempDirTestCase):
    def tearDown(self):
        self.ph5API_object.close()
        super(TestPH5Validate_no_response_filename, self).tearDown()

    def test_check_response_t(self):
        testargs = ['segdtoph5', '-n', 'master.ph5', '-U', '13N', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/fairfield/3ch.fcnt')]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()
        self.ph5API_object = ph5api.PH5(path=self.tmpdir,
                                        nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(self.ph5API_object, '.')
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = self.ph5validate.check_response_t()
            self.assertEqual(
                ret[0].error,
                ["Response table does not contain any response file names. "
                 "Check if resp_load has been run or if deprecated tool "
                 "metadatatoph5 input contained response information."])
            self.assertEqual(
                log.records[0].msg,
                "Response table does not contain any response file names. "
                "Check if resp_load has been run or if deprecated tool "
                "metadatatoph5 input contained response information.")


class TestPH5Validate_das_t_order(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5Validate_das_t_order, self).setUp()
        segd_file = os.path.join(
            self.home, "ph5/test_data/segd/smartsolo/453005513.2.2021.05.08."
                       "20.06.00.000.E.segd")
        testargs = ['segdtoph5', '-n', 'master', '-r', segd_file]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        ph5_object = ph5api.PH5(
            path=self.tmpdir, nickname='master.ph5', editmode=True)
        ph5_object.ph5_g_receivers.truncate_das_t('1X4')
        kef_to_ph5(
            self.tmpdir, 'master.ph5',
            os.path.join(self.home, 'ph5/test_data/metadata'),
            ['das1X1_messed_order.kef'])
        ph5_object.close()

    def test_main(self):
        testargs = ['ph5validate', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            ph5validate.main()

        with open(os.path.join(self.tmpdir, 'ph5_validate.log'),
                  'r') as content_file:
            loglines = content_file.read().strip().split("\n")
        self.assertIn("ERROR: Das 1X1: Das_t isn't in channel/time order."
                      " Run fix_das_t_order to fix that.",
                      loglines)


if __name__ == "__main__":
    unittest.main()
