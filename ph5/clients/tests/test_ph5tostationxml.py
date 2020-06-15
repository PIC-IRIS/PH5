'''
Tests for ph5tostationxml
'''
import unittest
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


class TestPH5toStationXMLParser_main(LogTestCase, TempDirTestCase):
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


class TestPH5toStationXMLParser(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5toStationXMLParser, self).setUp()
        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["array_multi_deploy.kef", "experiment.kef"])
        self.parser = self.getParser("NETWORK")

    def tearDown(self):
        self.mng.ph5.close()
        super(TestPH5toStationXMLParser, self).tearDown()

    def getParser(self, level, minlat=None, maxlat=None, minlon=None,
                  maxlon=None, lat=None, lon=None, minrad=None, maxrad=None):
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


if __name__ == "__main__":
    unittest.main()
