'''
Tests for ph5tostationxml
'''
import unittest
import logging
import os
import sys

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.clients import ph5tostationxml
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


class TestPH5toStationXMLParser(LogTestCase, TempDirTestCase):
    def tearDown(self):
        try:
            self.mng.ph5.close()
        except AttributeError:
            pass
        super(TestPH5toStationXMLParser, self).tearDown()

    def test_main_multideploy(self):
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
        self.assertEqual(self.parser.unique_errmsg,
                         ['Response_t n_i(s) duplicated: 1,3,6'])


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
            self.parser.unique_errmsg,
            ["No response entry for n_i=7.",
             "Response_t n_i=6: response_file_sensor_a is '' while sensor "
             "model exists.",
             "003-0407-1 response_table_n_i 6: Response das file name should "
             "be 'rt125a_100_1_1' or 'rt125a_gs11v_100DPZ' instead of "
             "'NoneQ330_NoneCMG3T_100LHN'.",
             "009-9001-1 response_table_n_i 4: Response sensor file name "
             "should be 'cmg_3t' instead of 'gs11v'.",
             "009-9001-1 response_table_n_i 4: Response das file name should "
             "be 'rt125a_200_1_32' instead of 'rt125a_500_1_32'.",
             "No response data loaded for gs11."])

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

        errors = ["No response entry for n_i=0.",
                  "Response_t n_i=5: response_file_sensor_a is '' while "
                  "sensor model exists.",
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
                  "No response entry for n_i=4."]
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            self.parser.create_obs_network()
        for i in range(len(log.records)):
            self.assertEqual(log.records[i].msg, errors[i])


if __name__ == "__main__":
    unittest.main()
