'''
Tests for ph5tostationxml
'''
import unittest
import os
import sys
import logging
from mock import patch
import shutil
import tempfile

from testfixtures import OutputCapture, LogCapture

from ph5.utilities import kef2ph5
from ph5.clients import ph5tostationxml
from ph5.core import experiment
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase,\
    initialize_ex


def kef_to_ph5(ph5path, nickname, kefpath, keflist, ex=None):
    """
    Add kef to ph5file or to experiment (if ex is passed).
    (The task of deleting table before adding the table should happen before
    calling this function. If it is required to have a delete function for all,
    it should be written in nuke_table.py)

    :para ph5path: path to ph5 file
    :type ph5path: string
    :para kefpath: path to kef files
    :type kefpath: string
    :para keflist: A list of kef file names
    :type keflist: list of string
    :para ex: ph5 experiment from caller
    :para ex: ph5 experiment object
    :result: the tables in the kef files will be added to ph5 file or the
    reference ex (if passed)
    """

    if ex is None:
        with OutputCapture():
            kef2ph5.EX = initialize_ex(nickname, ph5path, True)
    else:
        kef2ph5.EX = ex

    kef2ph5.PH5 = os.path.join(ph5path, nickname)
    kef2ph5.TRACE = False

    for kef in keflist:
        kef2ph5.KEFFILE = os.path.join(kefpath, kef)
        kef2ph5.populateTables()

    if ex is None:
        kef2ph5.EX.ph5close()


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
        ret = self.parser.read_networks('.')
        self.assertEqual(ret.start_date.isoformat(), '2019-06-29T18:08:33')
        self.assertEqual(ret.end_date.isoformat(), '2019-09-28T14:29:39')
        self.assertEqual(ret.code, 'AA')
        self.assertEqual(ret.description, 'PH5 TEST SET')


class TestPH5toStationXMLParser_latlon(unittest.TestCase):
    def setUp(self):
        # create tmpdir
        self.home = os.getcwd()
        self.tmpdir = tempfile.mkdtemp() + "/"

        # create ph5
        os.chdir(self.tmpdir)
        kef2ph5.EX = ex = experiment.ExperimentGroup(nickname="master.ph5")
        ex.ph5open(True)
        ex.initgroup()
        kef2ph5.PH5 = self.tmpdir + "/master.ph5"
        kef2ph5.TRACE = False

        # add array_t from array_ph5tostationxml with errors for:
        # 1: lat, lon based on param set for PH5toStationXMLRequest
        kef2ph5.KEFFILE = self.home + \
            "/ph5/test_data/metadata/array_ph5tostationxml.kef"
        kef2ph5.populateTables()
        # add experiment_t
        kef2ph5.KEFFILE = self.home + \
            "/ph5/test_data/metadata/experiment.kef"
        kef2ph5.populateTables()

        ex.ph5close()
        self.ph5sxml = [ph5tostationxml.PH5toStationXMLRequest(
            minlatitude=34.,
            maxlatitude=40.,
            minlongitude=-111,
            maxlongitude=-105.,
            latitude=36,
            longitude=-107,
            minradius=0,
            maxradius=3
        )]
        self.mng = ph5tostationxml.PH5toStationXMLRequestManager(
            sta_xml_obj_list=self.ph5sxml,
            ph5path=".",
            nickname="master.ph5",
            level="NETWORK",
            format="TEXT"
        )
        self.parser = ph5tostationxml.PH5toStationXMLParser(self.mng)

    def tearDown(self):
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
        try:
            self.mng.ph5.close()
        except Exception:
            pass
        os.chdir(self.home)

    def test_is_lat_lon_match(self):
        """
        test is_lat_lon_match
        """
        # 1. latitude not in (-90, 90)
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], -107, 100)
        self.assertEqual(ret, 'Lat -107 not in range [-90,90]')

        # 2. longitude not in (-180, 180)
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], 35, 182)
        self.assertEqual(ret, 'Lon 182 not in range [-180,180]')

        # 3. latitude not in minlatitude=34 and maxlatitude=40
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], 70, 100)
        self.assertEqual(
            ret, "Box intersection: Lat 70 not in range [34.0,40.0] "
            "or Lon 100 not in range [-111,-105.0]")

        # 4. longitude not in minlongitude=-111 and maxlongitude=-105
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], 35, 100)
        self.assertEqual(
            ret, "Box intersection: Lat 35 not in range [34.0,40.0] "
            "or Lon 100 not in range [-111,-105.0]")

        # 5. pass all checks
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], 35, -106)
        self.assertEqual(ret, True)

        # 6. longitude got radius intersection
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], 35, -111)
        self.assertEqual(
            ret, "lat,lon=35,-111: radial intersection between a point "
            "radius boundary [0, 3] and a lat/lon point [36, -107]")

        # 7. latitude got radius intersection
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], 40, -106)
        self.assertEqual(
            ret, "lat,lon=40,-106: radial intersection between a point "
            "radius boundary [0, 3] and a lat/lon point [36, -107]")

    def test_read_station(self):
        """
        test read station method
        """
        self.parser.add_ph5_stationids()
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            self.parser.read_stations()

        self.assertEqual(
            log.records[0].msg,
            "station 1111, array 001: Lat -107.0 not in range [-90,90]")

        self.assertEqual(
            log.records[1].msg,
            "station 1112, array 001: Lon 182.0 not in range [-180,180]")

        self.assertEqual(
            log.records[2].msg,
            "station 1113, array 001: Box intersection: Lat 70.0 "
            "not in range [34.0,40.0] or Lon 100.0 not in range [-111,-105.0]")

        self.assertEqual(
            log.records[3].msg,
            "station 1114, array 001: Box intersection: Lat 35.0 "
            "not in range [34.0,40.0] or Lon 100.0 not in range [-111,-105.0]")

        self.assertEqual(
            log.records[4].msg,
            "station 1116, array 001: lat,lon=35.0,-111.0: "
            "radial intersection between a point radius boundary [0, 3] and "
            "a lat/lon point [36, -107]")

        self.assertEqual(
            log.records[5].msg,
            "station 1117, array 001: lat,lon=40.0,-106.0: "
            "radial intersection between a point radius boundary [0, 3] and "
            "a lat/lon point [36, -107]")


if __name__ == "__main__":
    unittest.main()
