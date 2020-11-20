'''
Tests for ph5toms
'''

import unittest
import copy
import os
import sys
import itertools
from StringIO import StringIO

from mock import patch
from testfixtures import OutputCapture
from obspy.core import UTCDateTime

from ph5.utilities import initialize_ph5, segd2ph5, nuke_table, kef2ph5
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase
from ph5.core import ph5api
from ph5.clients.ph5toms import StationCut, PH5toMSeed


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


class TestPH5toMSeed_srm(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5toMSeed_srm, self).setUp()
        segdpath = os.path.join(self.home, 'ph5/test_data/segd/1111.0.0.fcnt')
        kefpath = os.path.join(self.home,
                               'ph5/test_data/segd/Das_t_1X1111.0.0_SRM0.kef')
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()

        testargs = ['segdtoph5', '-n', 'master.ph5', '-r', segdpath]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        # delete_table and keftoph5 to replace das table's
        # sample_rate_multiplier=0 for testing
        testargs = ['delete_table', '-n', 'master.ph5', '-D', '1X1111']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                f = StringIO('y')
                sys.stdin = f
                nuke_table.main()
                f.close()

        testargs = ['keftoph5', '-n', 'master.ph5', '-k', kefpath]
        with patch.object(sys, 'argv', testargs):
            kef2ph5.main()

        self.ph5_object = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        self.ph5ms = PH5toMSeed(self.ph5_object,
                                starttime='2019-06-29T18:03:13.000000')

    def tearDown(self):
        self.ph5_object.close()
        super(TestPH5toMSeed_srm, self).tearDown()

    def test_create_trace(self):
        seed_network = 'AA'
        ph5_station = '1111'
        seed_station = '1111'
        station_cut_times = []
        self.ph5ms.read_arrays('Array_t_001')
        arraybyid = self.ph5_object.Array_t['Array_t_001']['byid']
        station_list = arraybyid.get(ph5_station)
        deployment = 1
        st_num = 0
        array_code = '001'
        experiment_id = '99-999'
        cut = self.ph5ms.create_cut(
            seed_network, ph5_station, seed_station, station_cut_times,
            station_list, deployment, st_num, array_code, experiment_id)

        cuts = itertools.chain.from_iterable([cut])

        # test cut time in days
        time_cut_in_day = [
            (1561831393, 1561852800), (1561852800, 1561939200),
            (1561939200, 1562025600), (1562025600, 1562112000),
            (1562112000, 1562198400), (1562198400, 1562284800),
            (1562284800, 1562371200), (1562371200, 1562457600),
            (1562457600, 1562544000), (1562544000, 1562630400),
            (1562630400, 1562716800), (1562716800, 1562803200),
            (1562803200, 1562889600), (1562889600, 1562976000),
            (1562976000, 1563062400), (1563062400, 1563148800),
            (1563148800, 1563235200), (1563235200, 1563321600),
            (1563321600, 1563408000), (1563408000, 1563494400),
            (1563494400, 1563580800), (1563580800, 1563633604.726999)]
        trace_times = [(UTCDateTime(2019, 7, 4, 16, 0, 0, 329998),
                        UTCDateTime(2019, 7, 4, 16, 0, 30, 328998)),
                       (UTCDateTime(2019, 7, 4, 16, 0, 30, 329998),
                        UTCDateTime(2019, 7, 4, 16, 1, 0, 328998)),
                       (UTCDateTime(2019, 7, 4, 16, 1, 0, 329998),
                        UTCDateTime(2019, 7, 4, 16, 1, 30, 328998))]
        count_time_cut = 0
        count_stream = 0
        count_trace = 0
        # Before converting srm=0 in ph5api.PH5.query_das_t() to 1
        # all streams are None.
        # After converting, there is one stream with 3 traces
        for c in cuts:
            self.assertEqual((c.starttime, c.endtime),
                             time_cut_in_day[count_time_cut])
            stream = self.ph5ms.create_trace(c)
            if stream is not None:
                self.assertEqual(len(stream.traces), 3)
                for trace in stream.traces:
                    self.assertEqual(trace.get_id(), 'AA.1111..GP1')
                    self.assertEqual(
                        (trace.stats.starttime, trace.stats.endtime),
                        trace_times[count_trace])
                    self.assertEqual(trace.stats.sampling_rate, 1000)
                    self.assertEqual(trace.stats.npts, 30000)
                    count_trace += 1
                count_stream += 1
            count_time_cut += 1

        self.assertEqual(count_stream, 1)


if __name__ == "__main__":
    unittest.main()
