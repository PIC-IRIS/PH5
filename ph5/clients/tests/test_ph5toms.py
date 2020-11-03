'''
Tests for ph5toms
'''

import unittest
from ph5.clients.ph5toms import StationCut, PH5toMSeed
import copy
import os
from ph5.core import ph5api
from ph5.clients.ph5availability import PH5Availability


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


class TestPH5CUT(unittest.TestCase):

    def setUp(self):
        super(TestPH5CUT, self).setUp()
        self.home = os.getcwd()
        self.ph5cut_object = ph5api.PH5(
            path=os.path.join(self.home, 'ph5/test_data/ph5'),
            nickname='master.ph5')

    def tearDown(self):
        self.ph5cut_object.close()
        super(TestPH5CUT, self).tearDown()

    def test_load_ph5(self):
        """
        Tries to load the PH5 test file.
        Checks if it is an instance of ph5.core.ph5api.PH5
        """
        self.assertTrue(isinstance(self.ph5cut_object, ph5api.PH5))
        self.assertTrue(self.ph5cut_object.ph5.isopen)

    def test_experiment_t(self):
        """
        check reading of experiment table
        """

        # experiment table is initally empty
        self.assertIsNone(self.ph5cut_object.Experiment_t)
        # load experiment table and it shouldn't be empty

        self.ph5cut_object.read_experiment_t()
        self.assertIsNotNone(self.ph5cut_object.Experiment_t)

        # keys should match
        keys = ['experiment_id_s', 'net_code_s', 'nickname_s', 'longname_s',
                'PIs_s', 'institutions_s', 'north_west_corner/X/value_d',
                'north_west_corner/X/units_s', 'north_west_corner/Y/value_d',
                'north_west_corner/Y/units_s', 'north_west_corner/Z/value_d',
                'north_west_corner/Z/units_s',
                'north_west_corner/coordinate_system_s',
                'north_west_corner/projection_s',
                'north_west_corner/ellipsoid_s',
                'north_west_corner/description_s',
                'south_east_corner/X/value_d', 'south_east_corner/X/units_s',
                'south_east_corner/Y/value_d', 'south_east_corner/Y/units_s',
                'south_east_corner/Z/value_d', 'south_east_corner/Z/units_s',
                'south_east_corner/coordinate_system_s',
                'south_east_corner/projection_s',
                'south_east_corner/ellipsoid_s',
                'south_east_corner/description_s', 'summary_paragraph_s',
                'time_stamp/ascii_s', 'time_stamp/epoch_l',
                'time_stamp/micro_seconds_i', 'time_stamp/type_s']
        self.assertEqual(keys, self.ph5cut_object.Experiment_t['keys'])

        # expect only one row in experiment table
        self.assertEqual(1, len(self.ph5cut_object.Experiment_t['rows']))

        # make sure experiment table matches what we think it should
        experiment_t = self.ph5cut_object.Experiment_t['rows']
        experiment_t[0]['net_code_s']
        self.assertEqual(experiment_t[0]['net_code_s'], 'AA')
        self.assertEqual(experiment_t[0]['experiment_id_s'], '99-999')
        self.assertEqual(experiment_t[0]['nickname_s'], 'PH5 Test')
        self.assertEqual(experiment_t[0]['longname_s'], 'PH5 TEST SET')
        self.assertEqual(experiment_t[0]['PIs_s'], 'Derick Hess')
        self.assertEqual(experiment_t[0]['institutions_s'], 'PASSCAL')

        ph5availability = PH5Availability(self.ph5cut_object)
        ph5tomseed = PH5toMSeed(self.ph5cut_object, out_dir=".",
                                reqtype="FDSN", netcode=None,
                                station=[], station_id=[],
                                channel=[], location=['01'],
                                component=[],
                                array=None, shotline=[],
                                eventnumbers=[], length=None,
                                starttime=None, stoptime=None,
                                offset=None, das_sn=None,
                                use_deploy_pickup=True,
                                decimation=None,
                                sample_rate_keep=None,
                                doy_keep=None, stream=False,
                                reduction_velocity=-1,
                                notimecorrect=True,
                                format='MSEED')
        self.ph5cut_object.read_array_t_names()
        array_names = sorted(self.ph5cut_object.Array_t_names)
        self.ph5cut_object.read_array_t('Array_t_001')
        keys = ['id_s', 'location/X/value_d', 'location/X/units_s',
                'location/Y/value_d', 'location/Y/units_s',
                'location/Z/value_d', 'location/Z/units_s',
                'location/coordinate_system_s', 'location/projection_s',
                'location/ellipsoid_s', 'location/description_s',
                'deploy_time/ascii_s', 'deploy_time/epoch_l',
                'deploy_time/micro_seconds_i', 'deploy_time/type_s',
                'pickup_time/ascii_s', 'pickup_time/epoch_l',
                'pickup_time/micro_seconds_i', 'pickup_time/type_s',
                'das/serial_number_s', 'das/model_s', 'das/manufacturer_s',
                'das/notes_s', 'sensor/serial_number_s', 'sensor/model_s',
                'sensor/manufacturer_s', 'sensor/notes_s', 'description_s',
                'seed_band_code_s', 'sample_rate_i',
                'sample_rate_multiplier_i', 'seed_instrument_code_s',
                'seed_orientation_code_s', 'seed_location_code_s',
                'seed_station_name_s', 'channel_number_i',
                'receiver_table_n_i', 'response_table_n_i']

        self.assertEqual(keys,
                         self.ph5cut_object.Array_t['Array_t_001']['keys'])

        # Block to get the table names from the array table
        for array_name in array_names:
            self.ph5cut_object.read_array_t(array_name)
            arraybyid = self.ph5cut_object.Array_t[array_name]['byid']
            arrayorder = self.ph5cut_object.Array_t[array_name]['order']

            for ph5_station in arrayorder:
                station_list = arraybyid.get(ph5_station)
                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        st = station_list[deployment][st_num]
                        ret = ph5availability.get_slc_info(st, '*', '*', '*')
                        if ret == -1:
                            continue
                        ph5_seed_station, ph5_loc, ph5_channel = ret
                        cuts = ph5tomseed.create_cut_list()
                        for cut in cuts:
                            self.assertEqual(str(cut),
                                             'net_code: AAexperiment_id:'
                                             + ' 99-999station:'
                                             + ' 8001seed_station:'
                                             + ' 8001array_code: 008location:'
                                             + ' 01seed_channel: HLZcomponent:'
                                             + ' 1das: 9EEFdas_manufacturer:'
                                             + ' reftekdas_model:'
                                             + ' rt130sensor_type:'
                                             + ' guralp cmg-3tstarttime:'
                                             + ' 1463568480.0endtime:'
                                             + ' 1463568540.0sample_rate:'
                                             + ' 100sample_rate_multiplier:'
                                             + ' 1notimecorrect: Truelatitude:'
                                             + ' 34.154673longitude:'
                                             + ' -106.916169elev:'
                                             + ' 1403.0receiver_n_i:'
                                             + ' 0response_n_i: 1shot_id:'
                                             + ' Noneshot_lat: Noneshot_lng:'
                                             + ' Noneshot_elevation: None')


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
