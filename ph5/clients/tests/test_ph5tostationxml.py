'''
Tests for pforma_io
'''
import unittest
import os
import sys
import shutil
import tempfile
from mock import patch
import logging
from StringIO import StringIO
from contextlib import contextmanager
from ph5.clients import ph5tostationxml
from ph5.utilities import kef2ph5
from ph5 import logger, ch as CH
from ph5.core import experiment


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def log_capture_string():
    capture = StringIO()
    logger.removeHandler(CH)
    ch = logging.StreamHandler(capture)
    logger.addHandler(ch)

    return capture


def initialize_ph5(nickname, path='.', editmode=False):
    ex = experiment.ExperimentGroup(nickname=nickname, currentpath=path)
    ex.ph5open(editmode)
    ex.initgroup()
    return ex


class TestPH5toStationXMLParser(unittest.TestCase):
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

    def createPH5(self, path, arraykef):
        kef2ph5.EX = ex = initialize_ph5("master.ph5", path, True)
        kef2ph5.PH5 = path + "/master.ph5"
        kef2ph5.TRACE = False

        kef2ph5.KEFFILE = self.home + arraykef

        kef2ph5.populateTables()
        # add experiment_t
        kef2ph5.KEFFILE = self.home + \
            "/ph5/test_data/metadata/experiment.kef"
        kef2ph5.populateTables()
        ex.ph5close()

    def setUp(self):
        log_capture_string()
        # create tmpdir
        self.home = os.getcwd()
        self.tmpdir = tempfile.mkdtemp() + "/"

        # create ph5
        os.chdir(self.tmpdir)

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

    def test_get_network_date(self):
        """
        test get_network_date
        """
        # add array_t from array_multideploy to test error of getting only the
        # first deploy time when calculating nettime
        self.createPH5(self.tmpdir,
                       "/ph5/test_data/metadata/array_multi_deploy.kef")
        parser = self.getParser("NETWORK")
        parser.add_ph5_stationids()
        parser.read_stations()
        ret = parser.get_network_date()
        self.assertTupleEqual(ret, (1561831713.0, 1569680979.0))

    def test_create_obs_network(self):
        """
        test create_obs_network
        """
        # add array_t from array_multideploy to test error of getting only the
        # first deploy time when calculating nettime
        self.createPH5(self.tmpdir,
                       "/ph5/test_data/metadata/array_multi_deploy.kef")
        parser = self.getParser("NETWORK")
        parser.manager.ph5.read_experiment_t()
        parser.experiment_t = parser.manager.ph5.Experiment_t['rows']
        parser.add_ph5_stationids()
        ret = parser.create_obs_network()
        self.assertEqual(ret.start_date.isoformat(), '2019-06-29T18:08:33')
        self.assertEqual(ret.end_date.isoformat(), '2019-09-28T14:29:39')
        self.assertEqual(ret.code, 'AA')
        self.assertEqual(ret.description, 'PH5 TEST SET')

    def test_read_networks(self):
        # add array_t from array_multideploy to test error of getting only the
        # first deploy time when calculating nettime
        self.createPH5(self.tmpdir,
                       "/ph5/test_data/metadata/array_multi_deploy.kef")
        parser = self.getParser("NETWORK")
        ret = parser.read_networks('.')
        self.assertEqual(ret.start_date.isoformat(), '2019-06-29T18:08:33')
        self.assertEqual(ret.end_date.isoformat(), '2019-09-28T14:29:39')
        self.assertEqual(ret.code, 'AA')
        self.assertEqual(ret.description, 'PH5 TEST SET')

    def test_main(self):
        # add array_t from array_multideploy to test error of getting only the
        # first deploy time when calculating nettime
        self.createPH5(self.tmpdir,
                       "/ph5/test_data/metadata/array_multi_deploy.kef")
        testargs = ['ph5tostationxml', '-n', 'master',
                    '--level', 'network', '-f', 'text']
        with patch.object(sys, 'argv', testargs):
            with captured_output() as (out, err):
                ph5tostationxml.main()
        output = out.getvalue().strip().split("\n")
        self.assertEqual(
            output[1],
            "AA|PH5 TEST SET|2019-06-29T18:08:33|2019-09-28T14:29:39|1")


if __name__ == "__main__":
    unittest.main()
