'''
Tests for ph5tostationxml
'''
import unittest
import os
import sys
import logging

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.clients import ph5tostationxml
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase, kef_to_ph5
from ph5.utilities import initialize_ph5

from obspy.core.utcdatetime import UTCDateTime


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
    def test_main_multideploy(self):
        # array_multideploy.kef: same station different deploy times
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

    def test_main_created_time_format(self):
        # array_multideploy.kef: same station different deploy times
        # => check if network time cover all or only the first 1
        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["array_multi_deploy.kef", "experiment.kef"])
        testargs = ['ph5tostationxml', '-n', 'master',
                    '--level', 'network', '-f', 'stationxml']

        try:
            from obspy.io.stationxml.core import _format_time as fmt
        except (ImportError, AttributeError) as e:
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
                   ["array_latlon_err.kef", "experiment.kef"])
        testargs = ['ph5tostationxml', '-n', 'master',
                    '--level', 'CHANNEL', '-f', 'text']
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
                    '--minradius', '0', '--maxradius', '3']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5tostationxml.main()
                output = out.captured.strip().split("\n")
        self.assertEqual(len(output), 2)
        self.assertEqual(output[1].split("|")[1], '1115')


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


class TestPH5toStationXMLParser_location(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5toStationXMLParser_location, self).setUp()

        kef_to_ph5(self.tmpdir,
                   'master.ph5',
                   os.path.join(self.home, "ph5/test_data/metadata"),
                   ["array_latlon_err.kef", "experiment.kef"])

        self.ph5sxml, self.mng, self.parser = getParser(
            self.tmpdir, 'master.ph5', "NETWORK",
            34, 40, -111, -105, 36, -107, 0, 3)

        # errors and warnings in array_latlon_err.kef
        self.errmsgs = ["array 001, station 1111, channel 1: "
                        "Channel latitude -107.0 not in range [-90,90]",
                        "array 001, station 1112, channel 1: "
                        "Channel longitude 182.0 not in range [-180,180]"]
        self.warnmsgs = ["array 001, station 1114, channel 1: "
                         "No Station location/Y/units_s value found.",
                         "array 001, station 1115, channel 1: "
                         "Channel elevation seems to be 0. Is this correct???"]

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
        issueset = set([(err, 'error') for err in self.errmsgs] +
                       [(warn, 'warning') for warn in self.warnmsgs])
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
                             set(self.errmsgs + self.warnmsgs))
            self.assertEqual(ret.code, 'AA')
            self.assertEqual(len(ret), 1)
            self.assertEqual(ret.stations[0].code, '1115')


if __name__ == "__main__":
    unittest.main()
