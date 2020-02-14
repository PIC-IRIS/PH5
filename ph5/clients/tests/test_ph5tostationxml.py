'''
Tests for pforma_io
'''
import unittest
import os
import shutil
import tempfile
import logging
from testfixtures import LogCapture
from ph5.clients import ph5tostationxml
from ph5.utilities import kef2ph5
from ph5.core import experiment


class TestPH5toStationXMLParser(unittest.TestCase):
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
