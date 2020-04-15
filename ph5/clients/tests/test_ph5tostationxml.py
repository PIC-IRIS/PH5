'''
Tests for ph5tostationxml
'''
import unittest
import os
import sys
import logging

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.utilities import kef2ph5
from ph5.clients import ph5tostationxml
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


def getParser(level, minlat=None, maxlat=None, minlon=None,
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
        ph5path=".",
        nickname="master.ph5",
        level=level,
        format="TEXT"
    )
    parser = ph5tostationxml.PH5toStationXMLParser(mng)
    return ph5sxml, mng, parser


class TestPH5toStationXMLParser_main_multideploy(LogTestCase, TempDirTestCase):
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


class TestPH5toStationXMLParser_multideploy(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5toStationXMLParser_multideploy, self).setUp()
        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["array_multi_deploy.kef", "experiment.kef"])
        self.ph5sxml, self.mng, self.parser = getParser("NETWORK")

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
        ret = self.parser.read_networks('.')
        self.assertEqual(ret.start_date.isoformat(), '2019-06-29T18:08:33')
        self.assertEqual(ret.end_date.isoformat(), '2019-09-28T14:29:39')
        self.assertEqual(ret.code, 'AA')
        self.assertEqual(ret.description, 'PH5 TEST SET')


class TestPH5toStationXMLParser_latlon(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5toStationXMLParser_latlon, self).setUp()

        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["array_latlon_err.kef", "experiment.kef"])

        self.ph5sxml, self.mng, self.parser = getParser(
            "NETWORK", 34, 40, -111, -105, 36, -107, 0, 3)

        # errors in array_latlon_err.kef
        self.errmsgs = [
            "array 1111, station 001,"
            " channel 1: Lat -107.0 not in range [-90,90]",
            "array 1112, station 001, channel 1:"
            " Lon 182.0 not in range [-180,180]",
            "array 1113, station 001, channel 1: Box intersection: Lat 70.0"
            " not in range [34,40] or Lon 100.0 not in range [-111,-105]",
            "array 1114, station 001, channel 1: Box intersection: Lat 35.0"
            " not in range [34,40] or Lon 100.0 not in range [-111,-105]",
            "array 1116, station 001, channel 1: lat,lon=35.0,-111.0:"
            " radial intersection between a point radius boundary [0, 3]"
            " and a lat/lon point [36, -107]",
            "array 1117, station 001, channel 1: lat,lon=40.0,-106.0:"
            " radial intersection between a point radius boundary [0, 3]"
            " and a lat/lon point [36, -107]"]

    def tearDown(self):
        self.mng.ph5.close()
        super(TestPH5toStationXMLParser_latlon, self).tearDown()

    def test_is_lat_lon_match(self):
        # 1. latitude not in (-90, 90)
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], -107, 100)
        self.assertEqual(ret, 'Lat -107 not in range [-90,90]')

        # 2. longitude not in (-180, 180)
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], 35, 182)
        self.assertEqual(ret, 'Lon 182 not in range [-180,180]')

        # 3. latitude not in minlatitude=34 and maxlatitude=40
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], 70, 100)
        self.assertEqual(
            ret, "Box intersection: Lat 70 not in range [34,40] "
            "or Lon 100 not in range [-111,-105]")

        # 4. longitude not in minlongitude=-111 and maxlongitude=-105
        ret = self.parser.is_lat_lon_match(self.ph5sxml[0], 35, 100)
        self.assertEqual(
            ret, "Box intersection: Lat 35 not in range [34,40] "
            "or Lon 100 not in range [-111,-105]")

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
        self.parser.add_ph5_stationids()
        self.parser.read_stations()
        self.assertEqual(self.parser.unique_errmsg, self.errmsgs)

    def test_create_obs_network(self):
        self.parser.manager.ph5.read_experiment_t()
        self.parser.experiment_t = self.parser.manager.ph5.Experiment_t['rows']
        self.parser.add_ph5_stationids()
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            self.parser.create_obs_network()

            self.assertEqual(log.records[0].msg, self.errmsgs[0])
            self.assertEqual(log.records[1].msg, self.errmsgs[1])
            self.assertEqual(log.records[2].msg, self.errmsgs[2])
            self.assertEqual(log.records[3].msg, self.errmsgs[3])
            self.assertEqual(log.records[4].msg, self.errmsgs[4])
            self.assertEqual(log.records[5].msg, self.errmsgs[5])


if __name__ == "__main__":
    unittest.main()
