'''
Tests for ph5tostationxml
'''
import unittest
import os
import sys
import logging

from obspy.core import inventory as inv
from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.utilities import segd2ph5, initialize_ph5, kef2ph5,\
    resp_load, nuke_table
from ph5.clients import ph5tostationxml
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase, kef_to_ph5

from obspy.core.utcdatetime import UTCDateTime


def getParser(ph5path, nickname, level, minlat=None, maxlat=None, minlon=None,
              maxlon=None, lat=None, lon=None, minrad=None, maxrad=None,
              emp_resp=False, stationxml_on_error=True):
    ph5sxml = [ph5tostationxml.PH5toStationXMLRequest(
        minlatitude=minlat,
        maxlatitude=maxlat,
        minlongitude=minlon,
        maxlongitude=maxlon,
        latitude=lat,
        longitude=lon,
        minradius=minrad,
        maxradius=maxrad,
        emp_resp=emp_resp
    )]
    mng = ph5tostationxml.PH5toStationXMLRequestManager(
        sta_xml_obj_list=ph5sxml,
        ph5path=ph5path,
        nickname=nickname,
        level=level,
        format="TEXT",
        stationxml_on_error=stationxml_on_error
    )
    parser = ph5tostationxml.PH5toStationXMLParser(mng)
    return ph5sxml, mng, parser


class TestPH5toStationXMLParser_main_multideploy(LogTestCase, TempDirTestCase):
    def tearDown(self):
        try:
            self.mng.ph5.close()
        except AttributeError:
            pass
        super(TestPH5toStationXMLParser_main_multideploy, self).tearDown()

    def test_main(self):
        # array_multideploy: same station different deploy times
        # => check if network time cover all or only the first 1
        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["array_multi_deploy.kef", "experiment.kef",
                    "response_t.kef"])
        testargs = ['ph5tostationxml', '-n', 'master',
                    '--level', 'network', '-f', 'text']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5tostationxml.main()
                output = out.captured.strip().split("\n")
                self.assertEqual(
                    output[1],
                    "AA|PH5 TEST SET|2019-06-29T18:08:33|"
                    "2019-09-28T14:29:39|1")

    def test_main_created_time_format(self):
        # array_multideploy.kef: same station different deploy times
        # => check if network time cover all or only the first 1
        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["array_multi_deploy.kef", "experiment.kef",
                    "response_t.kef"])
        testargs = ['ph5tostationxml', '-n', 'master',
                    '--level', 'network', '-f', 'stationxml']

        try:
            from obspy.io.stationxml.core import _format_time as fmt
        except ImportError:
            fmt = UTCDateTime.__str__

        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5tostationxml.main()
                output = out.captured.strip().split("\n")
                timestr = output[6].split('>')[1].split('<')[0]
                time = UTCDateTime(timestr)
                convstr = fmt(time)

                self.assertIn('T', timestr)
                self.assertEqual(timestr, convstr)

    def test_main_location(self):
        args = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', args):
            with OutputCapture():
                initialize_ph5.main()
        # array_latlon_err.kef: station 1111-1117
        #                       out of range on 1111,1112
        #                       no unit for Y (latitude): 1114
        #                       no value for Z: 1115
        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["array_latlon_err.kef", "experiment.kef",
                    "response_t.kef"])
        # load response
        testargs = ['resp_load', '-n', 'master', '-a', '1', '-i',
                    os.path.join(self.home,
                                 'ph5/test_data/metadata/input.csv')]
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                resp_load.main()

        # There are errors in ph5 so there is no stationxml created
        testargs = ['ph5tostationxml', '-n', 'master',
                    '--level', 'CHANNEL', '-f', 'text']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5tostationxml.main()
                output = out.captured.strip().split("\n")
        self.assertEqual(len(output), 1)

        # use flag --stationxml_on_error to create stationxml on error
        testargs += ['--stationxml_on_error']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5tostationxml.main()
                output = out.captured.strip().split("\n")
        self.assertEqual(len(output), 6)
        self.assertEqual(output[1].split("|")[1], '1113')
        self.assertEqual(output[2].split("|")[1], '1114')
        self.assertEqual(output[3].split("|")[1], '1115')
        self.assertEqual(output[4].split("|")[1], '1116')
        self.assertEqual(output[5].split("|")[1], '1117')

        # excess box intersection on 1113, 1114
        # excess radius intersection on 1116, 1117
        testargs = ['ph5tostationxml', '-n', 'master',
                    '--level', 'CHANNEL', '-f', 'text',
                    '--minlat', '34', '--maxlat', '40',
                    '--minlon', '-111', '--maxlon', '-105',
                    '--latitude', '36', '--longitude', '-107',
                    '--minradius', '0', '--maxradius', '3',
                    '--stationxml_on_error']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5tostationxml.main()
                output = out.captured.strip().split("\n")
        self.assertEqual(len(output), 2)
        self.assertEqual(output[1].split("|")[1], '1115')


class TestPH5toStationXMLParser_no_experiment(LogTestCase, TempDirTestCase):
    def test_read_networks(self):
        kef_to_ph5(self.tmpdir, 'master.ph5', '', [])
        self.ph5sxml, self.mng, self.parser = getParser(
            '.', 'master.ph5', "NETWORK")
        with self.assertRaises(ph5tostationxml.PH5toStationXMLError) as contxt:
            self.parser.read_networks()
            self.assertEqual(
                contxt.exception.message,
                'No experiment_t in ./master.ph5')
        self.mng.ph5.close()

    def test_get_args(self):
        # check default level
        testargs = ['ph5tostationxml', '-n', 'master.ph5']
        with OutputCapture() as out:
            with patch.object(sys, 'argv', testargs):
                args = ph5tostationxml.get_args()
                self.assertEqual(args.level, 'RESPONSE')

        # check setting a level
        testargs = ['ph5tostationxml', '-n', 'master.ph5',
                    '--level', 'CHANNEL']
        with OutputCapture() as out:
            with patch.object(sys, 'argv', testargs):
                args = ph5tostationxml.get_args()
                self.assertEqual(args.level, 'CHANNEL')

        # wrong level
        testargs = ['ph5tostationxml', '-n', 'master.ph5', '--level', 'CHAN']
        with OutputCapture() as out:
            with patch.object(sys, 'argv', testargs):
                with self.assertRaises(SystemExit):
                    ph5tostationxml.get_args()
            self.assertEqual(
                out.captured.split('\n')[1],
                "ph5tostationxml: error: argument --level: "
                "invalid choice: 'CHAN' "
                "(choose from 'NETWORK', 'STATION', 'CHANNEL', 'RESPONSE')")


class TestPH5toStationXMLParser_multideploy(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5toStationXMLParser_multideploy, self).setUp()
        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["array_multi_deploy.kef", "experiment.kef",
                    "response_t.kef"])
        self.ph5sxml, self.mng, self.parser = getParser(
            self.tmpdir, 'master.ph5', 'NETWORK')

    def tearDown(self):
        self.mng.ph5.close()
        super(TestPH5toStationXMLParser_multideploy, self).tearDown()

    def test_get_network_date(self):
        self.parser.add_ph5_stationids()
        self.parser.read_stations()

        ret = self.parser.get_network_date()
        self.assertTupleEqual(ret, (1561831713.0, 1569680979.0))

    def test_create_obs_network(self):
        self.parser.manager.ph5.read_experiment_t()
        self.parser.experiment_t = self.parser.manager.ph5.Experiment_t['rows']
        self.parser.add_ph5_stationids()

        ret = self.parser.create_obs_network()
        self.assertEqual(ret.start_date.isoformat(), '2019-06-29T18:08:33')
        self.assertEqual(ret.end_date.isoformat(), '2019-09-28T14:29:39')
        self.assertEqual(ret.code, 'AA')
        self.assertEqual(ret.description, 'PH5 TEST SET')

    def test_read_networks(self):
        ret = self.parser.read_networks()
        self.assertEqual(ret.start_date.isoformat(), '2019-06-29T18:08:33')
        self.assertEqual(ret.end_date.isoformat(), '2019-09-28T14:29:39')
        self.assertEqual(ret.code, 'AA')
        self.assertEqual(ret.description, 'PH5 TEST SET')


class TestPH5toStationXMLParser_response(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5toStationXMLParser_response, self).setUp()
        ph5path = os.path.join(self.home, "ph5/test_data/ph5")
        self.ph5sxml, self.mng, self.parser = getParser(
            ph5path, "master.ph5", "CHANNEL", emp_resp=True)
        self.obs_channel = self.parser.create_obs_channel(
            sta_code='9001', loc_code='', cha_code='DPZ',
            start_date='2019-02-22T15:39',
            end_date='2019-02-22T15:44',
            cha_longitude=-106.906169, cha_latitude=34.054673,
            cha_elevation=1403.0,
            cha_component=1, receiver_id='9001', array_code='009',
            sample_rate=500.0, sample_rate_ration=500.0,
            azimuth=0.0, dip=90.0, sensor_manufacturer='geospace',
            sensor_model='gs11v', sensor_serial='',
            das_manufacturer='reftek', das_model='rt125a', das_serial='12183'
        )

    def tearDown(self):
        self.mng.ph5.close()
        super(TestPH5toStationXMLParser_response, self).tearDown()

    def test_get_response_inv(self):
        # emp_resp = False => throw error if no resp data to return

        # n_i=-1
        self.parser.response_table_n_i = -1
        with self.assertRaises(ph5tostationxml.PH5toStationXMLError) as contxt:
            self.parser.get_response_inv(
                self.obs_channel, a_id='004', sta_id='0407',
                cha_id=-2, spr=0, spr_m=1, emp_resp=False)
        self.assertEqual(
            contxt.exception.message,
            'array 004 station 0407, channel -2: Response_t[-1]:'
            'Metadata response with n_i=-1 has no response data.')

        # No response entry for n_i=7
        self.parser.response_table_n_i = 7
        with self.assertRaises(ph5tostationxml.PH5toStationXMLError) as contxt:
            self.parser.get_response_inv(
                self.obs_channel, a_id='009', sta_id='9001',
                cha_id=1, spr=50, spr_m=1, emp_resp=False)
        self.assertEqual(
            contxt.exception.message,
            'array 009 station 9001, channel 1: '
            'Response_t has no entry for n_i=7')

        # no response data for gs11 (only for gs11v)
        self.parser.response_table_n_i = 4
        response_t = self.mng.ph5.get_response_t_by_n_i(4)
        response_t['response_file_sensor_a'] = '/Experiment_g/Responses_g/gs11'
        self.obs_channel.sensor.model = 'gs11'
        with self.assertRaises(ph5tostationxml.PH5toStationXMLError) as contxt:
            self.parser.get_response_inv(
                self.obs_channel, a_id='009', sta_id='9001',
                cha_id=1, spr=500, spr_m=1, emp_resp=False)
        self.assertEqual(
            contxt.exception.message,
            'array 009 station 9001, channel 1: Response_t[4]:'
            'No response data loaded for gs11.')

        self.parser.unique_errors = set()
        # wrong response das file name (spr=200><500 in filename)
        # wrong response sensor name
        self.obs_channel.sensor.model = 'cmg_3t'
        response_t['response_file_sensor_a'] = \
            '/Experiment_g/Responses_g/gs11v'
        response = self.parser.get_response_inv(
            self.obs_channel, a_id='009', sta_id='9001',
            cha_id=1, spr=200, spr_m=1, emp_resp=False)
        self.assertIsInstance(response, inv.response.Response)
        self.assertIsNotNone(response.instrument_sensitivity)
        self.assertEqual(
            self.parser.unique_errors,
            set([("array 009 station 9001, channel 1: Response_t[4]:"
                  "response_file_das_a 'rt125a_500_1_32' is inconsistent with "
                  "Array_t_009:sr=200. Please check with resp_load format "
                  "[das_model]_[sr]_[srm]_[gain].", 'error'),
                 ("array 009 station 9001, channel 1: Response_t[4]:"
                  "response_file_sensor_a 'gs11v' is inconsistent with "
                  "Array_t_009:sensor_model=cmg_3t.", 'error')
                 ]))

        self.parser.unique_errors = set()
        # sensor model exist but no response sensor filename
        # wrong response das file name (chan=DPZ><LHN, dmodel=rt125a><NoneQ330)
        self.parser.response_table_n_i = 6
        self.obs_channel.sensor.model = 'NoneCMG3T'
        response = self.parser.get_response_inv(
            self.obs_channel, a_id='003', sta_id='0407',
            cha_id=1, spr=100, spr_m=1, emp_resp=False)
        self.assertIsInstance(response, inv.response.Response)
        self.assertIsNotNone(response.instrument_sensitivity)
        self.assertEqual(
            self.parser.unique_errors,
            set([("array 003 station 0407, channel 1: Response_t[6]:"
                  "response_file_das_a 'NoneQ330_NoneCMG3T_100LHN' is "
                  "inconsistent with Array_t_003:das_model=rt125a. "
                  "Please check with deprecated tool metadatatoph5 format "
                  "[das_model]_[sensor_model]_[sr][cha] "
                  "(check doesn't include [cha]).", 'error')
                 ]))

    def test_get_response_inv_emp_resp(self):
        # emp_resp = True => return empty response if no resp data to return
        # No response entry for n_i=7
        self.parser.response_table_n_i = 7
        response = self.parser.get_response_inv(
            self.obs_channel, a_id='009', sta_id='9001',
            cha_id=1, spr=50, spr_m=1, emp_resp=True)
        self.assertIsInstance(response, inv.response.Response)
        self.assertIsNone(response.instrument_sensitivity)
        self.assertEqual(
            self.parser.unique_errors,
            set([('array 009 station 9001, channel 1: '
                  'Response_t has no entry for n_i=7', 'error')])
        )

        self.parser.unique_errors = set()
        # no response data for gs11 (only for gs11v)
        self.parser.response_table_n_i = 4
        response_t = self.mng.ph5.get_response_t_by_n_i(4)
        response_t['response_file_sensor_a'] = '/Experiment_g/Responses_g/gs11'
        self.obs_channel.sensor.model = 'gs11'
        response = self.parser.get_response_inv(
            self.obs_channel, a_id='009', sta_id='9001',
            cha_id=1, spr=500, spr_m=1, emp_resp=True)
        self.assertIsInstance(response, inv.response.Response)
        self.assertIsNone(response.instrument_sensitivity)
        self.assertEqual(
            self.parser.unique_errors,
            set([('array 009 station 9001, channel 1: Response_t[4]:'
                  'No response data loaded for gs11.', 'error')])
        )

    def test_create_obs_network(self):
        self.parser.manager.ph5.read_experiment_t()
        self.parser.experiment_t = self.parser.manager.ph5.Experiment_t['rows']
        self.parser.add_ph5_stationids()
        # error on n_i=-1 has no response data.
        # This data exist in ph5/test_data/ph5/master.ph5
        # => set emp_resp=True to check other warnings

        # array 008-8001-2 n_i=2: sensor-model=cmg3t changed to CMS
        self.mng.ph5.Array_t['Array_t_008']['byid'][
            '8001'][2][0]['sensor/model_s'] = 'CMS'
        # array 008-8001-1 n_i=1: sr=100 changed to 10
        self.mng.ph5.Array_t['Array_t_008']['byid'][
            '8001'][1][0]['sample_rate_i'] = '10'
        # array 002-0407-1 n_i=5: sensor-model=NoneCMG3T changed to CMG
        # but warning for response_file_das_a because it seems to be from
        # metadata format with response_file_sensor_a=''
        # => this also has a warning on response_file_sensor_a
        # while model exist
        self.mng.ph5.Array_t['Array_t_002']['byid'][
            '0407'][1][0]['sensor/model_s'] = 'CMG'

        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            self.parser.create_obs_network()
            self.assertEqual(
                set(rec.msg for rec in log.records),
                {"array 002 station 0407, channel 1: Response_t[5]:"
                 "response_file_das_a 'NoneQ330_NoneCMG3T_200HHN' is "
                 "inconsistent with Array_t_002:sensor_model=CMG. Please "
                 "check with deprecated tool metadatatoph5 format "
                 "[das_model]_[sensor_model]_[sr][cha] "
                 "(check doesn't include [cha]).",
                 "array 008 station 8001, channel 1: Response_t[1]:"
                 "response_file_das_a 'rt130_100_1_1' is inconsistent with "
                 "Array_t_008:sr=10. Please check with resp_load format "
                 "[das_model]_[sr]_[srm]_[gain].",
                 "array 008 station 8001, channel 2: Response_t[2]:"
                 "response_file_sensor_a 'cmg3t' is inconsistent with "
                 "Array_t_008:sensor_model=CMS.",
                 'array 004 station 0407, channel -2: Response_t[-1]:'
                 'Metadata response with n_i=-1 has no response data.',
                 })


class TestPH5toStationXMLParser_gen_resp_issue(
        LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5toStationXMLParser_gen_resp_issue, self).setUp()
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()
        testargs = ['keftoph5', '-n', 'master.ph5', '-k',
                    os.path.join(self.home,
                                 'ph5/test_data/metadata/experiment.kef')]
        with patch.object(sys, 'argv', testargs):
            kef2ph5.main()
        testargs = ['segdtoph5', '-n', 'master.ph5', '-U', '13N', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/fairfield/3ch.fcnt')]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

    def tearDown(self):
        self.mng.ph5.close()
        super(TestPH5toStationXMLParser_gen_resp_issue, self).tearDown()

    def test_read_networks_no_resp_filename(self):
        self.ph5sxml, self.mng, self.parser = getParser(
            self.tmpdir, "master.ph5", "CHANNEL")
        with self.assertRaises(ph5tostationxml.PH5toStationXMLError) as contxt:
            self.parser.read_networks()
        self.assertEqual(
            contxt.exception.message,
            "Response table does not contain any response file names. "
            "Check if resp_load has been run or if deprecated tool "
            "metadatatoph5 input contained response information.")

    def test_read_networks_response_duplication(self):
        # response_t_dup_n_i.kef has n_i= 1,3,6 duplicated
        testargs = ['delete_table', '-n', 'master.ph5', '-R']
        with patch.object(sys, 'argv', testargs):
            nuke_table.main()

        kefpath = os.path.join(self.home,
                               'ph5/test_data/metadata/response_t_dup_n_i.kef')
        testargs = ['keftoph5', '-n', 'master.ph5', '-k', kefpath]
        with patch.object(sys, 'argv', testargs):
            kef2ph5.main()

        # stationxml_on_error=True => return network
        self.ph5sxml, self.mng, self.parser = getParser(
            self.tmpdir, 'master.ph5', 'NETWORK')
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = self.parser.read_networks()
            self.assertEqual(
                log.records[0].msg,
                'Response_t n_i(s) duplicated: 1,3,6. '
                'Try to rerun resp_load to see if it fix the problem.')
            self.assertIsInstance(ret, inv.network.Network)

        # stationxml_on_error=False => return None
        self.ph5sxml, self.mng, self.parser = getParser(
            self.tmpdir, 'master.ph5', 'NETWORK', stationxml_on_error=False)
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = self.parser.read_networks()
            self.assertEqual(
                log.records[0].msg,
                'Response_t n_i(s) duplicated: 1,3,6. '
                'Try to rerun resp_load to see if it fix the problem.')
            self.assertIsNone(ret)


class TestPH5toStationXMLParser_location(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5toStationXMLParser_location, self).setUp()
        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["array_latlon_err.kef", "experiment.kef",
                    "response_t.kef"])

        self.ph5sxml, self.mng, self.parser = getParser(
            self.tmpdir, 'master.ph5', "NETWORK",
            34, 40, -111, -105, 36, -107, 0, 3)

        # errors and warnings in array_latlon_err.kef
        self.errmsgs = ["array 001, station 1111, channel 1: "
                        "Channel latitude -107.0 not in range [-90,90]",
                        "array 001, station 1112, channel 1: "
                        "Channel longitude 182.0 not in range [-180,180]"]

    def tearDown(self):
        self.mng.ph5.close()
        super(TestPH5toStationXMLParser_location, self).tearDown()

    def test_check_intersection(self):
        # latitude not in minlatitude=34 and maxlatitude=40
        ret = self.parser.check_intersection(self.ph5sxml[0], 70, 100)
        self.assertFalse(ret)

        # longitude not in minlongitude=-111 and maxlongitude=-105
        ret = self.parser.check_intersection(self.ph5sxml[0], 35, 100)
        self.assertFalse(ret)

        # passed
        ret = self.parser.check_intersection(self.ph5sxml[0], 35, -106)
        self.assertTrue(ret)

        # longitude excess radius intersection
        ret = self.parser.check_intersection(self.ph5sxml[0], 35, -111)
        self.assertFalse(ret)

        # latitude excess radius intersection
        ret = self.parser.check_intersection(self.ph5sxml[0], 40, -106)
        self.assertFalse(ret)

    def test_read_station(self):
        self.parser.add_ph5_stationids()
        ret = self.parser.read_stations()
        issueset = set([(err, 'error') for err in self.errmsgs])
        self.assertEqual(issueset, self.parser.unique_errors)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].code, '1115')

    def test_create_obs_network(self):
        self.parser.manager.ph5.read_experiment_t()
        self.parser.experiment_t = self.parser.manager.ph5.Experiment_t['rows']
        self.parser.add_ph5_stationids()
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            ret = self.parser.create_obs_network()
            self.assertEqual(set(rec.msg for rec in log.records),
                             set(self.errmsgs))
            self.assertEqual(ret.code, 'AA')
            self.assertEqual(len(ret), 1)
            self.assertEqual(ret.stations[0].code, '1115')


class TestPH5toStationXML_Response_NI_MISMATCH(LogTestCase, TempDirTestCase):
    def test_Response_NI_MISMATCH(self):
        # Uncomment line 401 and comment line 402 to prove test
        # datapath = '../../test_data/ph5/'
        datapath = os.path.join(self.home,
                                'ph5/test_data/ph5/response_table_n_i')
        self.ph5_path_eror = os.path.join(self.home,
                                          datapath)
        self.ph5sxml, self.mng, self.parser = getParser(self.ph5_path_eror,
                                                        "master.ph5",
                                                        "RESPONSE")
        self.parser.add_ph5_stationids()
        station = self.parser.read_stations()
        self.assertEqual(len(station[0].channels[0].
                         response._get_overall_sensitivity_and_gain()), 2)
        try:
            station[0].channels[1].response._get_overall_sensitivity_and_gain()
        except IndexError:
            self.mng.ph5.close()
            self.fail("Response information is not present"
                      " in output stationxml.")
        self.mng.ph5.close()


class TestPh5ToStationxml(LogTestCase, TempDirTestCase):
    def test_different_response_for_same_models(self):
        datapath = os.path.join(self.home,
                                'ph5/test_data/ph5_different_response')
        arg_dict_list = [{
            'network_list': None, 'reportnum_list': None,
            'station_list': None, 'location_list': None,
            'channel_list': None, 'component_list': None,
            'receiver_list': None, 'array_list': ['001', '002'],
            'minlat': None, 'maxlat': None, 'minlon': None, 'maxlon': None,
            'latitude': None, 'longitude': None,
            'maxradius': None, 'minradius': None,
            'start_time': None, 'end_time': None, 'emp_resp': False,}]
        inv = ph5tostationxml.run_ph5_to_stationxml(
            [datapath], 'master.ph5', 'SACPZ', 'RESPONSE', '', arg_dict_list
        )
        # array 1 response n_i=0
        response = inv.get_response('XW.10006..DP1',
                                    UTCDateTime("2024-01-11T18:48:34"))

        self.assertEqual(response.instrument_sensitivity.frequency, 50.)
        self.assertAlmostEqual(response.instrument_sensitivity.value,
                               4902075.50872, 4)
        response = inv.get_response('XW.10006..DPZ',
                                    UTCDateTime("2024-01-11T18:48:34"))
        self.assertEqual(response.instrument_sensitivity.frequency, 50.)
        self.assertAlmostEqual(response.instrument_sensitivity.value,
                               4902075.50872, 4)

        # array 2 response n_i=1
        response = inv.get_response('XW.20134..DP1',
                                    UTCDateTime("2024-01-14T18:48:34"))
        self.assertEqual(response.instrument_sensitivity.frequency, 50.)
        self.assertAlmostEqual(response.instrument_sensitivity.value,
                               612759.438589, 4)
        response = inv.get_response('XW.20134..DP2',
                                    UTCDateTime("2024-01-14T18:48:34"))
        self.assertEqual(response.instrument_sensitivity.frequency, 50.)
        self.assertAlmostEqual(response.instrument_sensitivity.value,
                               612759.438589, 4)

if __name__ == "__main__":
    unittest.main()
