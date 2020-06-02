'''
Tests for ph5tostationxml
'''
import unittest
import os
import sys
import logging
from StringIO import StringIO

from mock import patch
from testfixtures import OutputCapture, LogCapture

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
                f = StringIO(ord('\r'))     # hit enter to continue
                sys.stdin = f
                ph5tostationxml.main()
                f.close()
                output = out.captured.strip().split("\n")
                self.assertEqual(
                    output[2],
                    "AA|PH5 TEST SET|2019-06-29T18:08:33|"
                    "2019-09-28T14:29:39|1")


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
        ret = self.parser.read_networks('.')
        self.assertEqual(ret.start_date.isoformat(), '2019-06-29T18:08:33')
        self.assertEqual(ret.end_date.isoformat(), '2019-09-28T14:29:39')
        self.assertEqual(ret.code, 'AA')
        self.assertEqual(ret.description, 'PH5 TEST SET')


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
        self.assertEqual(self.parser.unique_errmsg, self.errmsgs)

    def test_create_obs_network(self):
        self.parser.manager.ph5.read_experiment_t()
        self.parser.experiment_t = self.parser.manager.ph5.Experiment_t['rows']
        self.parser.add_ph5_stationids()
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            self.parser.create_obs_network()
            for i in range(len(self.errmsgs)):
                self.assertEqual(log.records[i].msg, self.errmsgs[i])


if __name__ == "__main__":
    unittest.main()
