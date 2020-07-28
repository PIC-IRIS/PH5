'''
Tests for ph5tostationxml
'''
import unittest
import os
import sys
import logging

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.utilities import segd2ph5
from ph5.clients import ph5tostationxml
from ph5.clients.ph5tostationxml import box_intersection_err,\
    radial_intersection_err
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase, kef_to_ph5


def getParser(ph5path, nickname, level, minlat=None, maxlat=None, minlon=None,
              maxlon=None, lat=None, lon=None, minrad=None, maxrad=None):
    ph5sxml = [ph5tostationxml.PH5toStationXMLRequest(
        minlatitude=minlat,
        maxlatitude=maxlat,
        minlongitude=minlon,
        maxlongitude=maxlon,
        latitude=lat,
        longitude=lon,
        minradius=minrad,
        maxradius=maxrad
    )]
    mng = ph5tostationxml.PH5toStationXMLRequestManager(
        sta_xml_obj_list=ph5sxml,
        ph5path=ph5path,
        nickname=nickname,
        level=level,
        format="TEXT"
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
                   ["array_multi_deploy.kef", "experiment.kef"])
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

    def test_init_response_duplication(self):
        # response_t_dup_n_i.kef has n_i= 1,3,6 duplicated
        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ['response_t_dup_n_i.kef'])
        self.ph5sxml, self.mng, self.parser = getParser(
            self.tmpdir, 'master.ph5', 'NETWORK')
        self.assertEqual(
            self.parser.unique_errors,
            {('Response_t n_i(s) duplicated: 1,3,6', 'error')})


class TestPH5toStationXMLParser_no_experiment(LogTestCase, TempDirTestCase):
    def tearDown(self):
        self.mng.ph5.close()
        super(TestPH5toStationXMLParser_no_experiment, self).tearDown()

    def test_read_networks(self):
        kef_to_ph5(self.tmpdir, 'master.ph5', '', [])
        self.ph5sxml, self.mng, self.parser = getParser(
            '.', 'master.ph5', "NETWORK")
        with LogCapture() as log:
            ret = self.parser.read_networks()
            self.assertIsNone(ret)
            self.assertEqual(log.records[0].msg,
                             'No experiment_t in ./master.ph5')


class TestPH5toStationXMLParser_multideploy(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5toStationXMLParser_multideploy, self).setUp()
        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["array_multi_deploy.kef", "experiment.kef"])
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
            ph5path, "master.ph5", "CHANNEL")

    def tearDown(self):
        self.mng.ph5.close()
        super(TestPH5toStationXMLParser_response, self).tearDown()

    def test_get_response_inv(self):
        obs_channel = self.parser.create_obs_channel(
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

        # No response entry for n_i=7
        self.parser.response_table_n_i = 7
        self.parser.get_response_inv(
            obs_channel, a_id='009', sta_id='9001', cha_id=1, spr=50, spr_m=1)

        # sensor model exist but no response sensor filename
        # wrong response das file name either by resp_load or metadata
        # while no response sensor file name
        self.parser.response_table_n_i = 6
        self.parser.get_response_inv(
            obs_channel, a_id='003', sta_id='0407', cha_id=1, spr=100, spr_m=1)

        # wrong response das file name
        # wrong response sensor name
        obs_channel.sensor.model = 'cmg_3t'
        self.parser.response_table_n_i = 4
        self.parser.get_response_inv(
            obs_channel, a_id='009', sta_id='9001', cha_id=1, spr=200, spr_m=1)

        # no response data for gs11 (only for gs11v)
        response_t = self.mng.ph5.get_response_t_by_n_i(4)
        response_t['response_file_sensor_a'] = '/Experiment_g/Responses_g/gs11'
        obs_channel.sensor.model = 'gs11'
        self.parser.get_response_inv(
            obs_channel, a_id='009', sta_id='9001', cha_id=1, spr=200, spr_m=1)

        self.assertEqual(
            set(errmsg for errmsg, logtype in self.parser.unique_errors),
            {"No response entry for n_i=7.",
             "003-0407-1 response_table_n_i 6: response_file_sensor_a is "
             "blank while sensor model exists.",
             "003-0407-1 response_table_n_i 6: Response das file name should "
             "be 'rt125a_100_1_1' or 'rt125a_gs11v_100DPZ' instead of "
             "'NoneQ330_NoneCMG3T_100LHN'.",
             "009-9001-1 response_table_n_i 4: Response sensor file name "
             "should be 'cmg_3t' instead of 'gs11v'.",
             "009-9001-1 response_table_n_i 4: Response das file name should "
             "be 'rt125a_200_1_32' instead of 'rt125a_500_1_32'.",
             "No response data loaded for gs11."})

    def test_create_obs_network(self):
        # modify response_t to produce errors:
        # remove n_i=0,6,-1,3,4
        # n_i=1: sensor resp:cmg3t=>gs11v das resp:rt130_100_1_1=>rt130_200_1_1
        # n_1=2: das resp: rt130_100_1_1=>rt130_10_1_1
        #      sensor resp:cmg3t=>cmg_3t and array's sensor model:cmg3t=>cmg_3t
        # n_i=5: das resp:NoneQ330_NoneCMG3T_200HHN=>NoneQ330_CMG3T_200HHN
        self.mng.ph5.Response_t['rows'] = [
            {'n_i': 1, 'gain/value_i': 1,
             'response_file_das_a': '/Experiment_g/Responses_g/rt130_200_1_1',
             'response_file_sensor_a': '/Experiment_g/Responses_g/gs11v'},
            {'n_i': 2, 'gain/value_i': 1,
             'response_file_das_a': '/Experiment_g/Responses_g/rt130_10_1_1',
             'response_file_sensor_a': '/Experiment_g/Responses_g/cmg_3t'},
            {'n_i': 5, 'gain/value_i': 1,
             'response_file_das_a':
                 '/Experiment_g/Responses_g/NoneQ330_CMG3T_200HHN',
             'response_file_sensor_a': ''}]
        self.parser.manager.ph5.read_experiment_t()
        self.parser.experiment_t = self.parser.manager.ph5.Experiment_t['rows']
        self.parser.add_ph5_stationids()
        self.mng.ph5.Array_t['Array_t_008']['byid'][
            '8001'][2][0]['sensor/model_s'] = 'cmg_3t'

        errors = {"No response entry for n_i=0.",
                  "002-0407-1 response_table_n_i 5: response_file_sensor_a is "
                  "blank while sensor model exists.",
                  "002-0407-1 response_table_n_i 5: Response das file name "
                  "should be 'NoneQ330_200_1_1' or 'NoneQ330_NoneCMG3T_200HHN'"
                  " instead of 'NoneQ330_CMG3T_200HHN'.",
                  "No response entry for n_i=6.",
                  "No response entry for n_i=-1.",
                  "008-8001-1 response_table_n_i 1: Response sensor file name "
                  "should be 'cmg3t' instead of 'gs11v'.",
                  "008-8001-1 response_table_n_i 1: Response das file name "
                  "should be 'rt130_100_1_1' instead of 'rt130_200_1_1'.",
                  "No response data loaded for cmg_3t.",
                  "008-8001-2 response_table_n_i 2: Response das file name "
                  "should be 'rt130_100_1_1' instead of 'rt130_10_1_1'.",
                  "No response entry for n_i=3.",
                  "No response entry for n_i=4."}
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            self.parser.create_obs_network()
            self.assertEqual(set(rec.msg for rec in log.records),
                             set(errors))


class TestPH5toStationXMLParser_resp_load_not_run(
        LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5toStationXMLParser_resp_load_not_run, self).setUp()
        testargs = ['segdtoph5', '-n', 'master.ph5', '-U', '13N', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/3ch.fcnt')]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()
        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["receiver_t.kef", "experiment.kef"])

        self.ph5sxml, self.mng, self.parser = getParser(
            self.tmpdir, "master.ph5", "CHANNEL")


    def tearDown(self):
        self.mng.ph5.close()
        super(TestPH5toStationXMLParser_resp_load_not_run, self).tearDown()

    def test_create_obs_network(self):
        self.parser.manager.ph5.read_experiment_t()
        self.parser.experiment_t = self.parser.manager.ph5.Experiment_t['rows']
        self.parser.add_ph5_stationids()
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            self.parser.create_obs_network()
            self.assertEqual(log.records[0].msg,
                             'All response file names are blank in response '
                             'table. Check if resp_load has been run.')


def combine_header(st_id, errlist):
    err_pattern = "array 001, station {0}, channel 1: {1}"
    err_with_header_list = []
    for err in errlist:
        err_with_header_list.append(err_pattern.format(st_id, err))
    return err_with_header_list


class TestPH5toStationXMLParser_latlon(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5toStationXMLParser_latlon, self).setUp()
        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["array_latlon_err.kef", "experiment.kef"])

        self.ph5sxml, self.mng, self.parser = getParser(
            self.tmpdir, 'master.ph5', "NETWORK",
            34, 40, -111, -105, 36, -107, 0, 3)

        # errors in array_latlon_err.kef
        self.err_dict = {
            '1111': ["Channel latitude -107.0 not in range [-90,90]",
                     box_intersection_err(-107.0, 34, 40, 100.0, -111, -105),
                     radial_intersection_err(-107.0, 100.0, 0, 3, 36, -107)],
            '1112': ["Channel longitude 182.0 not in range [-180,180]",
                     box_intersection_err(35.0, 34, 40, 182.0, -111, -105),
                     radial_intersection_err(35.0, 182.0, 0, 3, 36, -107)],
            '1113': [box_intersection_err(70.0, 34, 40, 100.0, -111, -105),
                     radial_intersection_err(70.0, 100.0, 0, 3, 36, -107)],
            '1114': [box_intersection_err(35.0, 34, 40, 100.0, -111, -105),
                     radial_intersection_err(35.0, 100.0, 0, 3, 36, -107)],
            '1116': [radial_intersection_err(35.0, -111.0, 0, 3, 36, -107)],
            '1117': [radial_intersection_err(40.0, -106.0, 0, 3, 36, -107)]
        }

        self.errmsgs = []
        for st_id in sorted(self.err_dict.keys()):
            self.errmsgs += combine_header(st_id, self.err_dict[st_id])

    def tearDown(self):
        self.mng.ph5.close()
        super(TestPH5toStationXMLParser_latlon, self).tearDown()

    def test_is_lat_lon_match(self):
        station = {'location/X/units_s': 'degrees',
                   'location/Y/units_s': 'degrees',
                   'location/Z/value_d': 1403,
                   'location/Z/units_s': 'm'}
        # 1. latitude not in (-90, 90)
        station['location/Y/value_d'] = -107.0
        station['location/X/value_d'] = 100.0
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], station)
        self.assertEqual(ret, self.err_dict['1111'])

        # 2. longitude not in (-180, 180)
        station['location/Y/value_d'] = 35.0
        station['location/X/value_d'] = 182.0
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], station)
        self.assertEqual(ret, self.err_dict['1112'])

        # 3. latitude not in minlatitude=34 and maxlatitude=40
        station['location/Y/value_d'] = 70.0
        station['location/X/value_d'] = 100.0
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], station)
        self.assertEqual(ret, self.err_dict['1113'])

        # 4. longitude not in minlongitude=-111 and maxlongitude=-105
        station['location/Y/value_d'] = 35.0
        station['location/X/value_d'] = 100.0
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], station)
        self.assertEqual(ret, self.err_dict['1114'])

        # 5. pass all checks
        station['location/Y/value_d'] = 35.0
        station['location/X/value_d'] = -106.0
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], station)
        self.assertEqual(ret, [])

        # 6. longitude got radius intersection
        station['location/Y/value_d'] = 35.0
        station['location/X/value_d'] = -111.0
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], station)
        self.assertEqual(ret, self.err_dict['1116'])

        # 7. latitude got radius intersection
        station['location/Y/value_d'] = 40.0
        station['location/X/value_d'] = -106.0
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], station)
        self.assertEqual(ret, self.err_dict['1117'])

    def test_read_station(self):
        self.parser.add_ph5_stationids()
        self.parser.read_stations()
        warningset = {(err, 'warning') for err in self.errmsgs}
        warningset.add(('All response file names are blank in response table.'
                        ' Check if resp_load has been run.', 'error'))
        self.assertEqual(self.parser.unique_errors,
                         warningset)

    def test_create_obs_network(self):
        self.parser.manager.ph5.read_experiment_t()
        self.parser.experiment_t = self.parser.manager.ph5.Experiment_t['rows']
        self.parser.add_ph5_stationids()
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            self.parser.create_obs_network()
            self.errmsgs.append('All response file names are blank in response'
                                ' table. Check if resp_load has been run.')
            self.assertEqual(set(rec.msg for rec in log.records),
                             set(self.errmsgs))


if __name__ == "__main__":
    unittest.main()
