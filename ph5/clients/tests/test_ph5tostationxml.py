'''
Tests for ph5tostationxml
'''
import unittest
import os
import logging
import shutil
import logging
from ph5.clients import ph5tostationxml
from ph5.core import ph5api
from ph5.core.tests.test_base_ import LogTestCase, TempDirTestCase, \
     initialize_ph5, kef_to_ph5
from testfixtures import LogCapture


class TestPH5toStationXMLParser(LogTestCase, TempDirTestCase):
    def tearDown(self):
        super(TestPH5toStationXMLParser, self).tearDown()
        self.mng.ph5.close()

    def getParser(self, path, nickname, level,
                  minlat=None, maxlat=None,
                  minlon=None, maxlon=None,
                  lat=None, lon=None,
                  minrad=None, maxrad=None):
        self.ph5sxml = [ph5tostationxml.PH5toStationXMLRequest(
            minlatitude=minlat,
            maxlatitude=maxlat,
            minlongitude=minlon,
            maxlongitude=maxlon,
            latitude=lat,
            longitude=lon,
            minradius=minrad,
            maxradius=maxrad
        )]
        self.mng = ph5tostationxml.PH5toStationXMLRequestManager(
            sta_xml_obj_list=self.ph5sxml,
            ph5path=".",
            nickname="master.ph5",
            level=level,
            format="TEXT"
        )
        return ph5tostationxml.PH5toStationXMLParser(self.mng)

    def test_check_resp_data(self):
        # copy file
        shutil.copy(self.home + "/ph5/test_data/ph5/master.ph5", self.tmpdir)
        parser = self.getParser(".", "master.ph5", "CHANNEL")
        parser.check_resp_data('rt130_100_1_1')
        parser.check_resp_data('rt130_200_1_1')
        parser.check_resp_data('cmg3t')
        parser.check_resp_data('cmg')
        self.assertListEqual(parser.unique_errmsg,
                             ["No response data loaded for rt130_200_1_1",
                              "No response data loaded for cmg"])

    def test_check_resp_file(self):
        shutil.copy(self.home + "/ph5/test_data/ph5/master.ph5", self.tmpdir)
        parser = self.getParser(".", "master.ph5", "CHANNEL")
        self.ph5 = ph5api.PH5(path='.', nickname='master.ph5')
        self.ph5.read_response_t()
        Response_t = self.ph5.get_response_t_by_n_i(4)
        parser.response_table_n_i = 4
        # 'rt125a_500_1_32' is response_das_file_name at n_i=4
        parser.check_resp_file(Response_t, 'STA', 'CHAN', 'das',
                               'rt125a_500_1_32')
        # 'rt125a_500_1_1' isn't response_das_file_name at n_i=4
        with LogCapture() as log:
            parser.check_resp_file(Response_t, 'STA', 'CHAN', 'das',
                                   'rt125a_500_1_1')
        self.assertEqual(log.records[0].msg,
                         "STA-CHAN-response_table_n_i 4: Response das file "
                         "name should be 'rt125a_500_1_1' while currently is "
                         "'rt125a_500_1_32'.")

        # 'gs11v' is response_sensor_file_name at n_i=4
        parser.check_resp_file(Response_t, 'STA', 'CHAN', 'sensor',
                               'gs11v')
        # 'cmg3t' isn't response_sensor_file_name at n_i=4
        with LogCapture() as log:
            parser.check_resp_file(Response_t, 'STA', 'CHAN', 'sensor',
                                   'cmg3t')
        self.assertEqual(log.records[0].msg,
                         "STA-CHAN-response_table_n_i 4: Response sensor file "
                         "name should be 'cmg3t' while currently is "
                         "'gs11v'.")
        Response_t = self.ph5.get_response_t_by_n_i(0)
        parser.response_table_n_i = 0
        parser.check_resp_file(Response_t, 'STA', 'CHAN', 'sensor',
                               'gs11v')
        self.assertListEqual(
            parser.unique_errmsg,
            ["Response_t's n_i 0: response_file_sensor_a is required."])

    def test_get_response_inv(self):
        shutil.copy(self.home + "/ph5/test_data/ph5/master.ph5", self.tmpdir)
        parser = self.getParser(".", "master.ph5", "CHANNEL")
        obs_channel = parser.create_obs_channel(
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
        parser.response_table_n_i = 7
        parser.get_response_inv(obs_channel, station='9001', chan='DPZ',
                                samplerate=500.0, samplerate_m=1)

        self.assertListEqual(
            parser.unique_errmsg,
            ["response_table_n_i=7 not found in response_t."])

    def test_create_obs_network(self):
        shutil.copy(self.home + "/ph5/test_data/ph5/master.ph5", self.tmpdir)
        # ex = initialize_ph5('master.ph5', '.')
        # ex.ph5_g_responses.nuke_response_t()  # remove response table
        # kef_to_ph5('.', self.home, ['response_t.kef'], ex, close=False)
        # need response files that can check:
        #   + only one response_table_n_i in array_t
        #   + n_i in Response_t is duplicated
        #   + wrong Response das filename
        #   + wrong Response sensor filename
        #   + No response das filename track from array_t to response_t
        #   + No response sensor filename track from array_t to response_t
        #   + No response data loaded for a response file
        parser = self.getParser(".", "master.ph5", "CHANNEL")
        
        parser.manager.ph5.read_experiment_t()
        parser.experiment_t = parser.manager.ph5.Experiment_t['rows']
        parser.add_ph5_stationids()
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            parser.create_obs_network()
        for l in log.records:
            print("log2:", l.msg)


if __name__ == "__main__":
    unittest.main()
