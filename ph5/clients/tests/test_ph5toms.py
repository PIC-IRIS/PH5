'''
Tests for ph5toms
'''

import unittest
from ph5.clients.ph5toms import StationCut, PH5toMSeed
import copy


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


if __name__ == "__main__":
    unittest.main()
