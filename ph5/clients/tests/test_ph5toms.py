'''
Tests for ph5toms
'''

import unittest
import copy
import os
import sys
import logging

from mock import patch
from testfixtures import LogCapture
import obspy

from ph5.core.tests.test_base import LogTestCase, TempDirTestCase
from ph5.core import ph5api, experiment
from ph5.clients.ph5toms import StationCut, PH5toMSeed
from ph5.clients import ph5toms


class RestrictedRequest(object):
    """
    Container for the forbidden request information returned
    by the ws-restricted service
    """

    def __init__(self, network, station, location,
                 channel, starttime, endtime):
        self.network = network
        self.station = station
        self.location = location
        self.channel = channel
        self.starttime = starttime
        self.endtime = endtime


def get_restricted_request_testcase(st, et):
    return RestrictedRequest(network="8A", station="1001",
                             location="", channel="EPZ",
                             starttime=st, endtime=et)


class TestPH5toMSeed_SAC(LogTestCase, TempDirTestCase):

    def test_SAC_header(self):
        """
        Tests SAC header's incidence angle (CMPINC)
        channel 1: PMCINC = 90 - dip
        channel 2: PNCINC = 90 - dip
        channel Z: PNCINC = 90 + dip
        """
        ph5path = os.path.join(self.home, 'ph5/test_data/ph5')
        sacpath = os.path.join(self.tmpdir, 'sac_test')

        # get orientation/dip/value_f in ph5
        # (receiver_table_n_i corresponding to channel 1/2/Z from array_t)
        ph5API_object = ph5api.PH5(path=ph5path, nickname='master.ph5')
        Receiver_t = ph5API_object.get_receiver_t_by_n_i(1)
        dip1 = Receiver_t['orientation/dip/value_f']
        Receiver_t = ph5API_object.get_receiver_t_by_n_i(2)
        dip2 = Receiver_t['orientation/dip/value_f']
        Receiver_t = ph5API_object.get_receiver_t_by_n_i(0)
        dipZ = Receiver_t['orientation/dip/value_f']
        ph5API_object.close()

        testargs = [
            'ph5toms',
            '-n', 'master.ph5',
            '--station', '500',
            '-o', 'sac_test',
            '-p', ph5path,
            '-f', 'SAC']
        with patch.object(sys, 'argv', testargs):
            with LogCapture():
                ph5toms.main()

        saclist = os.listdir(sacpath)
        self.assertEqual(len(saclist), 6)
        for f in saclist:
            st = obspy.read(os.path.join(sacpath, f))
            self.assertIn(st[0].stats['channel'], ['DP1', 'DP2', 'DPZ'])
            if st[0].stats['channel'] == 'DP1':
                self.assertEqual(st[0].stats['sac']['cmpinc'], 90 - dip1)
            if st[0].stats['channel'] == 'DP2':
                self.assertEqual(st[0].stats['sac']['cmpinc'], 90 - dip2)
            if st[0].stats['channel'] == 'DPZ':
                self.assertEqual(st[0].stats['sac']['cmpinc'], 90 + dipZ)


class TestPH5toMSeed(unittest.TestCase):

    def test_get_nonrestricted_segments(self):
        """
        Tests get_nonrestricted_segments()
        """
        st = 1416801600.0
        et = 1416805200.0
        station_to_cut = StationCut(net_code="8A",
                                    station="1001",
                                    seed_station="1001",
                                    das="13953",
                                    component="1",
                                    seed_channel="EPZ",
                                    starttime=st,
                                    endtime=et,
                                    sample_rate=250,
                                    sample_rate_multiplier=1,
                                    notimecorrect=False,
                                    location="",
                                    latitude=-18.26142,
                                    longitude=21.75392,
                                    experiment_id="13-005",
                                    array_code="001",
                                    das_manufacturer="REF TEK",
                                    das_model="RT 125 & 125A",
                                    sensor_type="Geo Space/OYO GS-11D",
                                    elev=997.6,
                                    receiver_n_i=1,
                                    response_n_i=1
                                    )
        station_to_cut_list = [station_to_cut]

        # nothing restricted
        restricted_list = []
        self.assertEqual(PH5toMSeed.get_nonrestricted_segments(
            station_to_cut_list, restricted_list),
                         station_to_cut_list, "None restricted")

        # entirely restricted
        restricted_list = [get_restricted_request_testcase(st, et)]
        self.assertEqual(PH5toMSeed.get_nonrestricted_segments(
            station_to_cut_list, restricted_list), [], "All restricted")
        restricted_list = [get_restricted_request_testcase(st - 1, et)]
        self.assertEqual(PH5toMSeed.get_nonrestricted_segments(
            station_to_cut_list, restricted_list), [], "All restricted")
        restricted_list = [get_restricted_request_testcase(st, et + 1)]
        self.assertEqual(PH5toMSeed.get_nonrestricted_segments(
            station_to_cut_list, restricted_list), [], "All restricted")
        restricted_list = [get_restricted_request_testcase(st - 1, et + 1)]
        self.assertEqual(PH5toMSeed.get_nonrestricted_segments(
            station_to_cut_list, restricted_list), [], "All restricted")

        # later half of requested segment is restricted
        rst = st + 1000  # restricted starttime
        ret = et  # restricted endtime
        restricted_list = [get_restricted_request_testcase(rst, ret)]
        expected = copy.deepcopy(station_to_cut)
        expected.endtime = rst - 1
        result = PH5toMSeed.get_nonrestricted_segments(
            station_to_cut_list, restricted_list)
        self.assertEqual(expected.__dict__,
                         result[0].__dict__, "Later half restricted")

        # first half of requested segment is restricted
        rst = st  # restricted starttime
        ret = et - 1000  # restricted endtime
        restricted_list = [get_restricted_request_testcase(rst, ret)]
        expected = copy.deepcopy(station_to_cut)
        expected.starttime = ret + 1
        result = PH5toMSeed.get_nonrestricted_segments(
            station_to_cut_list, restricted_list)
        self.assertEqual(expected.__dict__,
                         result[0].__dict__, msg="First half restricted")

        # restricted range inside requested segment
        rst = st + 1000  # restricted starttime
        ret = et - 1000  # restricted endtime
        restricted_list = [get_restricted_request_testcase(rst, ret)]
        expected1 = copy.deepcopy(station_to_cut)
        expected1.endtime = rst - 1
        expected2 = copy.deepcopy(station_to_cut)
        expected2.starttime = ret + 1
        result = PH5toMSeed.get_nonrestricted_segments(
            station_to_cut_list, restricted_list)
        self.assertEqual(
            expected1.__dict__, result[0].__dict__,
            msg="Restricted inside of request. 1st Segment")
        self.assertEqual(
            expected2.__dict__, result[1].__dict__,
            msg="Restricted inside of request. 2nd Segment")
        self.assertEqual(len(result), 2)

        # multiple restricted range inside requested segment
        # restricted segment 1
        rst1 = st
        ret1 = st + 300
        # restricted segment 2
        rst2 = st + 500
        ret2 = st + 1000
        # restricted segment 3
        rst3 = st + 1500
        ret3 = st + 2000
        # restricted segment 4
        rst4 = st + 2100
        ret4 = st + 2300
        # restricted segment 5
        rst5 = st + 2500
        ret5 = et
        restricted_list = [get_restricted_request_testcase(rst1, ret1),
                           get_restricted_request_testcase(rst2, ret2),
                           get_restricted_request_testcase(rst3, ret3),
                           get_restricted_request_testcase(rst4, ret4),
                           get_restricted_request_testcase(rst5, ret5)]
        expected1 = copy.deepcopy(station_to_cut)
        expected1.starttime = ret1 + 1
        expected1.endtime = rst2 - 1
        expected2 = copy.deepcopy(station_to_cut)
        expected2.starttime = ret2 + 1
        expected2.endtime = rst3 - 1
        expected3 = copy.deepcopy(station_to_cut)
        expected3.starttime = ret3 + 1
        expected3.endtime = rst4 - 1
        expected4 = copy.deepcopy(station_to_cut)
        expected4.starttime = ret4 + 1
        expected4.endtime = rst5 - 1
        result = PH5toMSeed.get_nonrestricted_segments(
            station_to_cut_list, restricted_list)
        self.assertEqual(
            expected1.__dict__, result[0].__dict__,
            msg="Restricted inside of request. 1st Segment")
        self.assertEqual(
            expected2.__dict__, result[1].__dict__,
            msg="Restricted inside of request. 2nd Segment")
        self.assertEqual(
            expected3.__dict__, result[2].__dict__,
            msg="Restricted inside of request. 3nd Segment")
        self.assertEqual(
            expected4.__dict__, result[3].__dict__,
            msg="Restricted inside of request. 4nd Segment")
        self.assertEqual(len(result), 4)

        # not in restricted list at all
        st = 1438794000.0
        et = 1489589791.0
        station_to_cut = StationCut(net_code="4C",
                                    station="1003",
                                    seed_station="DAN",
                                    das="10811",
                                    component="1",
                                    seed_channel="DPZ",
                                    starttime=st,
                                    endtime=et,
                                    sample_rate=250,
                                    sample_rate_multiplier=1,
                                    notimecorrect=False,
                                    location="",
                                    latitude=-123.14976,
                                    longitude=46.23013,
                                    experiment_id="13-005",
                                    array_code="001",
                                    das_manufacturer="REF TEK",
                                    das_model="RT 125 & 125A",
                                    sensor_type="Geo Space/OYO GS-11D",
                                    elev=997.6,
                                    receiver_n_i=1,
                                    response_n_i=1
                                    )
        station_to_cut_list = [station_to_cut]
        expected = copy.deepcopy(station_to_cut)
        result = PH5toMSeed.get_nonrestricted_segments(
            station_to_cut_list, restricted_list)
        self.assertEqual(result[0].__dict__, expected.__dict__)


class TestPH5toMSeed_samplerate(LogTestCase, TempDirTestCase):
    def tearDown(self):
        self.ph5_object.close()
        super(TestPH5toMSeed_samplerate, self).tearDown()

    def test_create_trace(self):

        self.ph5_object = ph5api.PH5(
            path=os.path.join(self.home, 'ph5/test_data/ph5'),
            nickname='master.ph5')
        ph5toms = PH5toMSeed(self.ph5_object)
        ph5toms.process_all()
        cuts = ph5toms.create_cut_list()
        for cut in cuts:
            trace = ph5toms.create_trace(cut)
            if trace is not None:
                self.assertEqual(trace[0].stats.sampling_rate, cut.sample_rate)

    def test_mismatch_sample_rate(self):
        ph5test_srpath = os.path.join(self.home,
                                      'ph5/test_data/ph5/samplerate')
        self.ph5_object = ph5api.PH5(path=ph5test_srpath,
                                     nickname='master.ph5')
        ph5toms = PH5toMSeed(self.ph5_object)
        ph5toms.process_all()
        cuts = ph5toms.create_cut_list()
        with LogCapture() as log:
            for cut in cuts:
                trace = ph5toms.create_trace(cut)
                if trace is not None:
                    self.assertEqual(trace[0].stats.station, '10075')
        self.assertIsNotNone(log)


class TestPH5toMSeed_SRM(TempDirTestCase, LogTestCase):
    '''
    Test sample_rate_multiplier=0 or missing
    '''
    def assert_create_cut_list_trace(self, ph5path, errortype, errno, errmsg):
        self.ph5_object = ph5api.PH5(path=ph5path, nickname='master.ph5')
        ph5toms = PH5toMSeed(self.ph5_object,
                             starttime='2019-06-29T18:03:13.000000',
                             component='1')
        ph5toms.process_all()
        with self.assertRaises(errortype) as context:
            cuts = ph5toms.create_cut_list()
            for cut in cuts:
                ph5toms.create_trace(cut)
        self.assertEqual(context.exception.errno, errno)
        self.assertEqual(context.exception.msg, errmsg)
        self.ph5_object.ph5.close()

    def test_create_cut_list_srm0(self):
        # sample_rate_multiplier_i=0
        # => create_cut_list() raise error from read_arrays()
        ph5path = os.path.join(
            self.home,
            'ph5/test_data/ph5/sampleratemultiplier0/array_das')
        self.assert_create_cut_list_trace(
            ph5path,
            experiment.HDF5InteractionError,
            7,
            'Array_t_001 has sample_rate_multiplier_i with value 0. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')

    def test_create_trace_srm0(self):
        # sample_rate_multiplier_i=0
        # => create_trace() raise error from query_das_t()
        ph5path = os.path.join(
            self.home,
            'ph5/test_data/ph5/sampleratemultiplier0/das')
        self.assert_create_cut_list_trace(
            ph5path,
            ph5api.APIError,
            -1,
            'Das_t_1X1111 has sample_rate_multiplier_i with value 0. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')

    def test_create_cut_list_nosrm(self):
        # sample_rate_multiplier_i missing
        # => create_cut_list raise error from read_arrays()
        ph5path = os.path.join(self.home,
                               'ph5/test_data/ph5_no_srm/array_das')
        self.assert_create_cut_list_trace(
            ph5path,
            experiment.HDF5InteractionError,
            7,
            'Array_t_001 has sample_rate_multiplier_i missing. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')

    def test_create_trace_nosrm(self):
        # sample_rate_multiplier_i missing
        # => create_trace() raise error from query_das_t()
        ph5path = os.path.join(
            self.home,
            'ph5/test_data/ph5_no_srm/das')
        self.assert_create_cut_list_trace(
            ph5path,
            ph5api.APIError,
            -1,
            'Das_t_1X1111 has sample_rate_multiplier_i missing. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')

    def assert_main(self, ph5path, errmsg):
        testargs = ['ph5toms', '-n', 'master.ph5', '-p', ph5path,
                    '--station', '1111']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                ph5toms.main()
        self.assertEqual(len(log.records), 1)
        self.assertEqual(
            log.records[0].msg,
            errmsg)

    def test_main_srm0(self):
        # sample_rate_multiplier_i=0
        # Array_t will be check first when running create_cut_list()
        nosrmpath = os.path.join(
            self.home,
            'ph5/test_data/ph5/sampleratemultiplier0/array_das')
        self.assert_main(
            nosrmpath,
            'Array_t_001 has sample_rate_multiplier_i with value 0. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')

        # Das_t will be check first when running create_trace()
        nosrmpath = os.path.join(
            self.home,
            'ph5/test_data/ph5/sampleratemultiplier0/das')
        self.assert_main(
            nosrmpath,
            'Das_t_1X1111 has sample_rate_multiplier_i with value 0. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')

    def test_main_nosrm(self):
        # sample_rate_multiplier_i missing
        # Array_t will be check first when running create_cut_list()
        nosrmpath = os.path.join(
            self.home,
            'ph5/test_data/ph5_no_srm/array_das')
        self.assert_main(
            nosrmpath,
            'Array_t_001 has sample_rate_multiplier_i missing. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')

        # Das_t will be check first when running create_trace()
        nosrmpath = os.path.join(
            self.home,
            'ph5/test_data/ph5_no_srm/das')
        self.assert_main(
            nosrmpath,
            'Das_t_1X1111 has sample_rate_multiplier_i missing. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')


if __name__ == "__main__":
    unittest.main()
