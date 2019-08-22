"""
unit tests for ph5availability
"""

import unittest
from ph5.core import columns
import tables
import os


class TestExperiment(unittest.TestCase):
    print("test colunms.Experiment")

    def setUp(self):
        """
        setup for tests
        """
        self.ex = columns.Experiment.columns

    def test_main_attributes(self):
        """
        test Experiment's attributes
        """
        self.assertIn('experiment_id_s', self.ex.keys())
        self.assertIsInstance(self.ex['experiment_id_s'], tables.StringCol)
        self.assertEqual(self.ex['experiment_id_s'].itemsize, 8)
        self.assertEqual(self.ex['experiment_id_s']._v_pos, 1)

        self.assertIn('net_code_s', self.ex.keys())
        self.assertIsInstance(self.ex['net_code_s'], tables.StringCol)
        self.assertEqual(self.ex['net_code_s'].itemsize, 8)
        self.assertEqual(self.ex['net_code_s']._v_pos, 2)

        self.assertIn('nickname_s', self.ex.keys())
        self.assertIsInstance(self.ex['nickname_s'], tables.StringCol)
        self.assertEqual(self.ex['nickname_s'].itemsize, 32)
        self.assertEqual(self.ex['nickname_s']._v_pos, 3)

        self.assertIn('longname_s', self.ex.keys())
        self.assertIsInstance(self.ex['longname_s'], tables.StringCol)
        self.assertEqual(self.ex['longname_s'].itemsize, 256)
        self.assertEqual(self.ex['longname_s']._v_pos, 4)

        self.assertIn('PIs_s', self.ex.keys())
        self.assertIsInstance(self.ex['PIs_s'], tables.StringCol)
        self.assertEqual(self.ex['PIs_s'].itemsize, 1024)
        self.assertEqual(self.ex['PIs_s']._v_pos, 5)

        self.assertIn('institutions_s', self.ex.keys())
        self.assertIsInstance(self.ex['institutions_s'], tables.StringCol)
        self.assertEqual(self.ex['institutions_s'].itemsize, 1024)
        self.assertEqual(self.ex['institutions_s']._v_pos, 6)

        self.assertIn('summary_paragraph_s', self.ex.keys())
        self.assertIsInstance(self.ex['summary_paragraph_s'], tables.StringCol)
        self.assertEqual(self.ex['summary_paragraph_s'].itemsize, 2048)
        self.assertEqual(self.ex['summary_paragraph_s']._v_pos, 9)

    def test_time_stamp(self):
        """
        test time_stamp's attributes
        """
        self.assertIn('time_stamp', self.ex.keys())
        time_stamp = self.ex['time_stamp'].columns

        self.assertIn('type_s', time_stamp.keys())
        self.assertIsInstance(time_stamp['type_s'], tables.StringCol)
        self.assertEqual(time_stamp['type_s'].itemsize, 8)

        self.assertIn('epoch_l', time_stamp.keys())
        self.assertIsInstance(time_stamp['epoch_l'], tables.Int64Col)

        self.assertIn('ascii_s', time_stamp.keys())
        self.assertIsInstance(time_stamp['ascii_s'], tables.StringCol)
        self.assertEqual(time_stamp['ascii_s'].itemsize, 32)

        self.assertIn('micro_seconds_i', time_stamp.keys())
        self.assertIsInstance(time_stamp['micro_seconds_i'], tables.Int32Col)

    def test_north_west_corner(self):
        """
        test north_west_corner's attributes
        """
        self.assertIn('north_west_corner', self.ex.keys())
        north_west_corner = self.ex['north_west_corner'].columns

        self.assertIn('_v_pos', north_west_corner.keys())
        self.assertEqual(north_west_corner['_v_pos'], 7)

        # ---------------------- X -------------------#
        self.assertIn('X', north_west_corner.keys())
        X = north_west_corner['X'].columns

        self.assertIn('_v_pos', X.keys())
        self.assertEqual(X['_v_pos'], 1)

        self.assertIn('units_s', X.keys())
        self.assertIsInstance(X['units_s'], tables.StringCol)
        self.assertEqual(X['units_s'].itemsize, 16)

        self.assertIn('value_d', X.keys())
        self.assertIsInstance(X['value_d'], tables.Float64Col)
        self.assertEqual(X['value_d']._v_pos, 1)

        # ---------------------- Y -------------------#
        self.assertIn('Y', north_west_corner.keys())
        Y = north_west_corner['Y'].columns

        self.assertIn('_v_pos', Y.keys())
        self.assertEqual(Y['_v_pos'], 2)

        self.assertIn('units_s', Y.keys())
        self.assertIsInstance(Y['units_s'], tables.StringCol)
        self.assertEqual(Y['units_s'].itemsize, 16)

        self.assertIn('value_d', Y.keys())
        self.assertIsInstance(Y['value_d'], tables.Float64Col)
        self.assertEqual(Y['value_d']._v_pos, 1)

        # ---------------------- Z -------------------#
        self.assertIn('Z', north_west_corner.keys())
        Z = north_west_corner['Z'].columns

        self.assertIn('_v_pos', Z.keys())
        self.assertEqual(Z['_v_pos'], 3)

        self.assertIn('units_s', Z.keys())
        self.assertIsInstance(Z['units_s'], tables.StringCol)
        self.assertEqual(Z['units_s'].itemsize, 16)

        self.assertIn('value_d', Z.keys())
        self.assertIsInstance(Z['value_d'], tables.Float64Col)
        self.assertEqual(Z['value_d']._v_pos, 1)

        # ------------- main attr -----------#
        self.assertIn('coordinate_system_s', north_west_corner.keys())
        self.assertIsInstance(
            north_west_corner['coordinate_system_s'], tables.StringCol)
        self.assertEqual(north_west_corner['coordinate_system_s'].itemsize, 32)
        self.assertEqual(north_west_corner['coordinate_system_s']._v_pos, 4)

        self.assertIn('projection_s', north_west_corner.keys())
        self.assertIsInstance(
            north_west_corner['projection_s'], tables.StringCol)
        self.assertEqual(north_west_corner['projection_s'].itemsize, 32)
        self.assertEqual(north_west_corner['projection_s']._v_pos, 5)

        self.assertIn('ellipsoid_s', north_west_corner.keys())
        self.assertIsInstance(
            north_west_corner['ellipsoid_s'], tables.StringCol)
        self.assertEqual(north_west_corner['ellipsoid_s'].itemsize, 32)
        self.assertEqual(north_west_corner['ellipsoid_s']._v_pos, 6)
        self.assertIn('description_s', north_west_corner.keys())
        self.assertIsInstance(
            north_west_corner['description_s'], tables.StringCol)
        self.assertEqual(north_west_corner['description_s'].itemsize, 1024)
        self.assertEqual(north_west_corner['description_s']._v_pos, 7)

    def test_south_east_corner(self):
        """
        test south_east_corner's attributes
        """
        self.assertIn('south_east_corner', self.ex.keys())
        south_east_corner = self.ex['south_east_corner'].columns

        self.assertIn('_v_pos', south_east_corner.keys())
        self.assertEqual(south_east_corner['_v_pos'], 8)

        # ---------------------- X -------------------#
        self.assertIn('X', south_east_corner.keys())
        X = south_east_corner['X'].columns

        self.assertIn('_v_pos', X.keys())
        self.assertEqual(X['_v_pos'], 1)

        self.assertIn('units_s', X.keys())
        self.assertIsInstance(X['units_s'], tables.StringCol)
        self.assertEqual(X['units_s'].itemsize, 16)

        self.assertIn('value_d', X.keys())
        self.assertIsInstance(X['value_d'], tables.Float64Col)
        self.assertEqual(X['value_d']._v_pos, 1)

        # ---------------------- Y -------------------#
        self.assertIn('Y', south_east_corner.keys())
        Y = south_east_corner['Y'].columns

        self.assertIn('_v_pos', Y.keys())
        self.assertEqual(Y['_v_pos'], 2)

        self.assertIn('units_s', Y.keys())
        self.assertIsInstance(Y['units_s'], tables.StringCol)
        self.assertEqual(Y['units_s'].itemsize, 16)

        self.assertIn('value_d', Y.keys())
        self.assertIsInstance(Y['value_d'], tables.Float64Col)
        self.assertEqual(Y['value_d']._v_pos, 1)

        # ---------------------- Z -------------------#
        self.assertIn('Z', south_east_corner.keys())
        Z = south_east_corner['Z'].columns

        self.assertIn('_v_pos', Z.keys())
        self.assertEqual(Z['_v_pos'], 3)

        self.assertIn('units_s', Z.keys())
        self.assertIsInstance(Z['units_s'], tables.StringCol)
        self.assertEqual(Z['units_s'].itemsize, 16)

        self.assertIn('value_d', Z.keys())
        self.assertIsInstance(Z['value_d'], tables.Float64Col)
        self.assertEqual(Z['value_d']._v_pos, 1)

        # ------------- main attr -----------#
        self.assertIn('coordinate_system_s', south_east_corner.keys())
        self.assertIsInstance(
            south_east_corner['coordinate_system_s'], tables.StringCol)
        self.assertEqual(south_east_corner['coordinate_system_s'].itemsize, 32)
        self.assertEqual(south_east_corner['coordinate_system_s']._v_pos, 4)

        self.assertIn('projection_s', south_east_corner.keys())
        self.assertIsInstance(
            south_east_corner['projection_s'], tables.StringCol)
        self.assertEqual(south_east_corner['projection_s'].itemsize, 32)
        self.assertEqual(south_east_corner['projection_s']._v_pos, 5)

        self.assertIn('ellipsoid_s', south_east_corner.keys())
        self.assertIsInstance(
            south_east_corner['ellipsoid_s'], tables.StringCol)
        self.assertEqual(south_east_corner['ellipsoid_s'].itemsize, 32)
        self.assertEqual(south_east_corner['ellipsoid_s']._v_pos, 6)
        self.assertIn('description_s', south_east_corner.keys())
        self.assertIsInstance(
            south_east_corner['description_s'], tables.StringCol)
        self.assertEqual(south_east_corner['description_s'].itemsize, 1024)
        self.assertEqual(south_east_corner['description_s']._v_pos, 7)


class TestData(unittest.TestCase):
    print("test colunms.Data")

    def setUp(self):
        """
        setup for tests
        """
        self.data = columns.Data.columns

    def test_main_attributes(self):
        """
        test Data's attributes
        """
        self.assertIn('receiver_table_n_i', self.data.keys())
        self.assertIsInstance(self.data['receiver_table_n_i'], tables.Int32Col)

        self.assertIn('response_table_n_i', self.data.keys())
        self.assertIsInstance(self.data['response_table_n_i'], tables.Int32Col)

        self.assertIn('time_table_n_i', self.data.keys())
        self.assertIsInstance(self.data['time_table_n_i'], tables.Int32Col)

        self.assertIn('event_number_i', self.data.keys())
        self.assertIsInstance(self.data['event_number_i'], tables.Int32Col)

        self.assertIn('channel_number_i', self.data.keys())
        self.assertIsInstance(self.data['channel_number_i'], tables.Int8Col)

        self.assertIn('sample_rate_i', self.data.keys())
        self.assertIsInstance(self.data['sample_rate_i'], tables.Int16Col)

        self.assertIn('sample_rate_multiplier_i', self.data.keys())
        self.assertIsInstance(
            self.data['sample_rate_multiplier_i'], tables.Int16Col)

        self.assertIn('sample_count_i', self.data.keys())
        self.assertIsInstance(self.data['sample_count_i'], tables.Int32Col)

        self.assertIn('stream_number_i', self.data.keys())
        self.assertIsInstance(self.data['stream_number_i'], tables.Int8Col)

        self.assertIn('raw_file_name_s', self.data.keys())
        self.assertIsInstance(self.data['raw_file_name_s'], tables.StringCol)
        self.assertEqual(self.data['raw_file_name_s'].itemsize, 32)

        self.assertIn('array_name_data_a', self.data.keys())
        self.assertIsInstance(self.data['array_name_data_a'], tables.StringCol)
        self.assertEqual(self.data['array_name_data_a'].itemsize, 16)

        self.assertIn('array_name_SOH_a', self.data.keys())
        self.assertIsInstance(self.data['array_name_SOH_a'], tables.StringCol)
        self.assertEqual(self.data['array_name_SOH_a'].itemsize, 16)

        self.assertIn('array_name_event_a', self.data.keys())
        self.assertIsInstance(
            self.data['array_name_event_a'], tables.StringCol)
        self.assertEqual(self.data['array_name_event_a'].itemsize, 16)

        self.assertIn('array_name_log_a', self.data.keys())
        self.assertIsInstance(self.data['array_name_log_a'], tables.StringCol)
        self.assertEqual(self.data['array_name_log_a'].itemsize, 16)

    def test_time(self):
        """
        test time's attributes
        """
        self.assertIn('time', self.data.keys())
        time = self.data['time'].columns

        self.assertIn('type_s', time.keys())
        self.assertIsInstance(time['type_s'], tables.StringCol)
        self.assertEqual(time['type_s'].itemsize, 8)

        self.assertIn('epoch_l', time.keys())
        self.assertIsInstance(time['epoch_l'], tables.Int64Col)

        self.assertIn('ascii_s', time.keys())
        self.assertIsInstance(time['ascii_s'], tables.StringCol)
        self.assertEqual(time['ascii_s'].itemsize, 32)

        self.assertIn('micro_seconds_i', time.keys())
        self.assertIsInstance(time['micro_seconds_i'], tables.Int32Col)


class TestTime(unittest.TestCase):
    print("Test columns.Time")

    def setUp(self):
        """
        setup for tests
        """
        self.time = columns.Time.columns

    def test_main_attributes(self):
        """
        test Time's attributes
        """
        self.assertIn('slope_d', self.time.keys())
        self.assertIsInstance(self.time['slope_d'], tables.Float64Col)

        self.assertIn('offset_d', self.time.keys())
        self.assertIsInstance(self.time['offset_d'], tables.Float64Col)

        self.assertIn('description_s', self.time.keys())
        self.assertIsInstance(self.time['description_s'], tables.StringCol)
        self.assertEqual(self.time['description_s'].itemsize, 1024)

        self.assertIn('corrected_i', self.time.keys())
        self.assertIsInstance(self.time['corrected_i'], tables.Int16Col)

    def test_das(self):
        """
        test das's attributes
        """
        self.assertIn('das', self.time.keys())
        das = self.time['das'].columns

        self.assertIn('manufacturer_s', das.keys())
        self.assertIsInstance(das['manufacturer_s'], tables.StringCol)
        self.assertEqual(das['manufacturer_s'].itemsize, 64)
        self.assertEqual(das['manufacturer_s']._v_pos, 3)

        self.assertIn('model_s', das.keys())
        self.assertIsInstance(das['model_s'], tables.StringCol)
        self.assertEqual(das['model_s'].itemsize, 64)
        self.assertEqual(das['model_s']._v_pos, 2)

        self.assertIn('serial_number_s', das.keys())
        self.assertIsInstance(das['serial_number_s'], tables.StringCol)
        self.assertEqual(das['serial_number_s'].itemsize, 64)
        self.assertEqual(das['serial_number_s']._v_pos, 1)

        self.assertIn('notes_s', das.keys())
        self.assertIsInstance(das['notes_s'], tables.StringCol)
        self.assertEqual(das['notes_s'].itemsize, 1024)
        self.assertEqual(das['notes_s']._v_pos, 4)

    def test_start_time(self):
        """
        test start_time's attributes
        """
        self.assertIn('start_time', self.time.keys())
        start_time = self.time['start_time'].columns

        self.assertIn('type_s', start_time.keys())
        self.assertIsInstance(start_time['type_s'], tables.StringCol)
        self.assertEqual(start_time['type_s'].itemsize, 8)

        self.assertIn('epoch_l', start_time.keys())
        self.assertIsInstance(start_time['epoch_l'], tables.Int64Col)

        self.assertIn('ascii_s', start_time.keys())
        self.assertIsInstance(start_time['ascii_s'], tables.StringCol)
        self.assertEqual(start_time['ascii_s'].itemsize, 32)

        self.assertIn('micro_seconds_i', start_time.keys())
        self.assertIsInstance(start_time['micro_seconds_i'], tables.Int32Col)

    def test_end_time(self):
        """
        test end_time's attributes
        """
        self.assertIn('end_time', self.time.keys())
        end_time = self.time['end_time'].columns

        self.assertIn('type_s', end_time.keys())
        self.assertIsInstance(end_time['type_s'], tables.StringCol)
        self.assertEqual(end_time['type_s'].itemsize, 8)

        self.assertIn('epoch_l', end_time.keys())
        self.assertIsInstance(end_time['epoch_l'], tables.Int64Col)

        self.assertIn('ascii_s', end_time.keys())
        self.assertIsInstance(end_time['ascii_s'], tables.StringCol)
        self.assertEqual(end_time['ascii_s'].itemsize, 32)

        self.assertIn('micro_seconds_i', end_time.keys())
        self.assertIsInstance(end_time['micro_seconds_i'], tables.Int32Col)


class TestReceiver(unittest.TestCase):
    print("test colunms.Receiver")

    def setUp(self):
        """
        setup for tests
        """
        self.receiver = columns.Receiver.columns

    def test_orientation(self):
        """
        test orientation's attributes
        """
        self.assertIn('orientation', self.receiver.keys())
        orientation = self.receiver['orientation'].columns

        self.assertIn('channel_number_i', orientation.keys())
        self.assertIsInstance(orientation['channel_number_i'], tables.Int8Col)

        self.assertIn('description_s', orientation.keys())
        self.assertIsInstance(orientation['description_s'], tables.StringCol)
        self.assertEqual(orientation['description_s'].itemsize, 1024)
        self.assertEqual(orientation['description_s']._v_pos, 3)

        # ------------------------ dip ---------------------- #
        self.assertIn('dip', orientation.keys())
        dip = orientation['dip'].columns

        self.assertIn('_v_pos', dip.keys())
        self.assertEqual(dip['_v_pos'], 2)

        self.assertIn('units_s', dip.keys())
        self.assertIsInstance(dip['units_s'], tables.StringCol)
        self.assertEqual(dip['units_s'].itemsize, 16)

        self.assertIn('value_f', dip.keys())
        self.assertIsInstance(dip['value_f'], tables.Float32Col)
        self.assertEqual(dip['value_f']._v_pos, 1)

        # ---------------------- azimuth --------------------- #
        self.assertIn('azimuth', orientation.keys())
        azimuth = orientation['azimuth'].columns

        self.assertIn('_v_pos', azimuth.keys())
        self.assertEqual(azimuth['_v_pos'], 1)

        self.assertIn('units_s', azimuth.keys())
        self.assertIsInstance(azimuth['units_s'], tables.StringCol)
        self.assertEqual(azimuth['units_s'].itemsize, 16)

        self.assertIn('value_f', azimuth.keys())
        self.assertIsInstance(azimuth['value_f'], tables.Float32Col)
        self.assertEqual(azimuth['value_f']._v_pos, 1)


class TestIndex(unittest.TestCase):
    print("test colunms.Index")

    def setUp(self):
        """
        setup for tests
        """
        self.index = columns.Index.columns

    def test_main_attributes(self):
        """
        test Time's attributes
        """
        self.assertIn('external_file_name_s', self.index.keys())
        self.assertIsInstance(
            self.index['external_file_name_s'], tables.StringCol)
        self.assertEqual(self.index['external_file_name_s'].itemsize, 32)

        self.assertIn('hdf5_path_s', self.index.keys())
        self.assertIsInstance(self.index['hdf5_path_s'], tables.StringCol)
        self.assertEqual(self.index['hdf5_path_s'].itemsize, 64)

        self.assertIn('serial_number_s', self.index.keys())
        self.assertIsInstance(self.index['serial_number_s'], tables.StringCol)
        self.assertEqual(self.index['serial_number_s'].itemsize, 64)

    def test_time_stamp(self):
        """
        test time_stamp's attributes
        """
        self.assertIn('time_stamp', self.index.keys())
        time_stamp = self.index['time_stamp'].columns

        self.assertIn('type_s', time_stamp.keys())
        self.assertIsInstance(time_stamp['type_s'], tables.StringCol)
        self.assertEqual(time_stamp['type_s'].itemsize, 8)

        self.assertIn('epoch_l', time_stamp.keys())
        self.assertIsInstance(time_stamp['epoch_l'], tables.Int64Col)

        self.assertIn('ascii_s', time_stamp.keys())
        self.assertIsInstance(time_stamp['ascii_s'], tables.StringCol)
        self.assertEqual(time_stamp['ascii_s'].itemsize, 32)

        self.assertIn('micro_seconds_i', time_stamp.keys())
        self.assertIsInstance(time_stamp['micro_seconds_i'], tables.Int32Col)

    def test_start_time(self):
        """
        test start_time's attributes
        """
        self.assertIn('start_time', self.index.keys())
        start_time = self.index['start_time'].columns

        self.assertIn('type_s', start_time.keys())
        self.assertIsInstance(start_time['type_s'], tables.StringCol)
        self.assertEqual(start_time['type_s'].itemsize, 8)

        self.assertIn('epoch_l', start_time.keys())
        self.assertIsInstance(start_time['epoch_l'], tables.Int64Col)

        self.assertIn('ascii_s', start_time.keys())
        self.assertIsInstance(start_time['ascii_s'], tables.StringCol)
        self.assertEqual(start_time['ascii_s'].itemsize, 32)

        self.assertIn('micro_seconds_i', start_time.keys())
        self.assertIsInstance(start_time['micro_seconds_i'], tables.Int32Col)

    def test_end_time(self):
        """
        test end_time's attributes
        """
        self.assertIn('end_time', self.index.keys())
        end_time = self.index['end_time'].columns

        self.assertIn('type_s', end_time.keys())
        self.assertIsInstance(end_time['type_s'], tables.StringCol)
        self.assertEqual(end_time['type_s'].itemsize, 8)

        self.assertIn('epoch_l', end_time.keys())
        self.assertIsInstance(end_time['epoch_l'], tables.Int64Col)

        self.assertIn('ascii_s', end_time.keys())
        self.assertIsInstance(end_time['ascii_s'], tables.StringCol)
        self.assertEqual(end_time['ascii_s'].itemsize, 32)

        self.assertIn('micro_seconds_i', end_time.keys())
        self.assertIsInstance(end_time['micro_seconds_i'], tables.Int32Col)


class TestSort(unittest.TestCase):
    print("test colunms.Sort")

    def setUp(self):
        """
        setup for tests
        """
        self.sort = columns.Sort.columns

    def test_main_attributes(self):
        """
        test Sort's attributes
        """
        self.assertIn('event_id_s', self.sort.keys())
        self.assertIsInstance(self.sort['event_id_s'], tables.StringCol)
        self.assertEqual(self.sort['event_id_s'].itemsize, 16)

        self.assertIn('array_name_s', self.sort.keys())
        self.assertIsInstance(self.sort['array_name_s'], tables.StringCol)
        self.assertEqual(self.sort['array_name_s'].itemsize, 16)
        self.assertEqual(self.sort['array_name_s']._v_pos, 2)

        self.assertIn('array_t_name_s', self.sort.keys())
        self.assertIsInstance(self.sort['array_t_name_s'], tables.StringCol)
        self.assertEqual(self.sort['array_t_name_s'].itemsize, 16)
        self.assertEqual(self.sort['array_t_name_s']._v_pos, 1)

        self.assertIn('description_s', self.sort.keys())
        self.assertIsInstance(self.sort['description_s'], tables.StringCol)
        self.assertEqual(self.sort['description_s'].itemsize, 1024)
        self.assertEqual(self.sort['description_s']._v_pos, 5)

    def test_time_stamp(self):
        """
        test time_stamp's attributes
        """
        self.assertIn('time_stamp', self.sort.keys())
        time_stamp = self.sort['time_stamp'].columns

        self.assertIn('_v_pos', time_stamp.keys())
        self.assertEqual(time_stamp['_v_pos'], 6)

        self.assertIn('type_s', time_stamp.keys())
        self.assertIsInstance(time_stamp['type_s'], tables.StringCol)
        self.assertEqual(time_stamp['type_s'].itemsize, 8)

        self.assertIn('epoch_l', time_stamp.keys())
        self.assertIsInstance(time_stamp['epoch_l'], tables.Int64Col)

        self.assertIn('ascii_s', time_stamp.keys())
        self.assertIsInstance(time_stamp['ascii_s'], tables.StringCol)
        self.assertEqual(time_stamp['ascii_s'].itemsize, 32)

        self.assertIn('micro_seconds_i', time_stamp.keys())
        self.assertIsInstance(time_stamp['micro_seconds_i'], tables.Int32Col)

    def test_start_time(self):
        """
        test start_time's attributes
        """
        self.assertIn('start_time', self.sort.keys())
        start_time = self.sort['start_time'].columns

        self.assertIn('_v_pos', start_time.keys())
        self.assertEqual(start_time['_v_pos'], 3)

        self.assertIn('type_s', start_time.keys())
        self.assertIsInstance(start_time['type_s'], tables.StringCol)
        self.assertEqual(start_time['type_s'].itemsize, 8)

        self.assertIn('epoch_l', start_time.keys())
        self.assertIsInstance(start_time['epoch_l'], tables.Int64Col)

        self.assertIn('ascii_s', start_time.keys())
        self.assertIsInstance(start_time['ascii_s'], tables.StringCol)
        self.assertEqual(start_time['ascii_s'].itemsize, 32)

        self.assertIn('micro_seconds_i', start_time.keys())
        self.assertIsInstance(start_time['micro_seconds_i'], tables.Int32Col)

    def test_end_time(self):
        """
        test end_time's attributes
        """
        self.assertIn('end_time', self.sort.keys())
        end_time = self.sort['end_time'].columns

        self.assertIn('_v_pos', end_time.keys())
        self.assertEqual(end_time['_v_pos'], 4)

        self.assertIn('type_s', end_time.keys())
        self.assertIsInstance(end_time['type_s'], tables.StringCol)
        self.assertEqual(end_time['type_s'].itemsize, 8)

        self.assertIn('epoch_l', end_time.keys())
        self.assertIsInstance(end_time['epoch_l'], tables.Int64Col)

        self.assertIn('ascii_s', end_time.keys())
        self.assertIsInstance(end_time['ascii_s'], tables.StringCol)
        self.assertEqual(end_time['ascii_s'].itemsize, 32)

        self.assertIn('micro_seconds_i', end_time.keys())
        self.assertIsInstance(end_time['micro_seconds_i'], tables.Int32Col)


class TestArray(unittest.TestCase):
    print("test colunms.Array")

    def setUp(self):
        """
        setup for tests
        """
        self.array = columns.Array.columns

    def test_main_attributes(self):
        """
        test Array's attributes
        """
        self.assertIn('channel_number_i', self.array.keys())
        self.assertIsInstance(self.array['channel_number_i'], tables.Int8Col)

        self.assertIn('seed_band_code_s', self.array.keys())
        self.assertIsInstance(self.array['seed_band_code_s'], tables.StringCol)
        self.assertEqual(self.array['seed_band_code_s'].itemsize, 1)
        self.assertEqual(self.array['seed_band_code_s']._v_pos, 8)

        self.assertIn('sample_rate_i', self.array.keys())
        self.assertIsInstance(self.array['sample_rate_i'], tables.Int16Col)
        self.assertEqual(self.array['sample_rate_i']._v_pos, 9)

        self.assertIn('sample_rate_multiplier_i', self.array.keys())
        self.assertIsInstance(
            self.array['sample_rate_multiplier_i'], tables.Int16Col)
        self.assertEqual(self.array['sample_rate_multiplier_i']._v_pos, 10)

        self.assertIn('seed_instrument_code_s', self.array.keys())
        self.assertIsInstance(
            self.array['seed_instrument_code_s'], tables.StringCol)
        self.assertEqual(self.array['seed_instrument_code_s'].itemsize, 1)
        self.assertEqual(self.array['seed_instrument_code_s']._v_pos, 11)

        self.assertIn('seed_orientation_code_s', self.array.keys())
        self.assertIsInstance(
            self.array['seed_orientation_code_s'], tables.StringCol)
        self.assertEqual(self.array['seed_orientation_code_s'].itemsize, 1)
        self.assertEqual(self.array['seed_orientation_code_s']._v_pos, 12)

        self.assertIn('seed_location_code_s', self.array.keys())
        self.assertIsInstance(
            self.array['seed_location_code_s'], tables.StringCol)
        self.assertEqual(self.array['seed_location_code_s'].itemsize, 2)
        self.assertEqual(self.array['seed_location_code_s']._v_pos, 13)

        self.assertIn('seed_station_name_s', self.array.keys())
        self.assertIsInstance(
            self.array['seed_station_name_s'], tables.StringCol)
        self.assertEqual(self.array['seed_station_name_s'].itemsize, 5)
        self.assertEqual(self.array['seed_station_name_s']._v_pos, 14)

        self.assertIn('response_table_n_i', self.array.keys())
        self.assertIsInstance(
            self.array['response_table_n_i'], tables.Int32Col)

        self.assertIn('receiver_table_n_i', self.array.keys())
        self.assertIsInstance(
            self.array['receiver_table_n_i'], tables.Int32Col)

        self.assertIn('description_s', self.array.keys())
        self.assertIsInstance(self.array['description_s'], tables.StringCol)
        self.assertEqual(self.array['description_s'].itemsize, 1024)
        self.assertEqual(self.array['description_s']._v_pos, 7)

    def test_deploy_time(self):
        """
        test deploy_time's attributes
        """
        self.assertIn('deploy_time', self.array.keys())
        deploy_time = self.array['deploy_time'].columns

        self.assertIn('_v_pos', deploy_time.keys())
        self.assertEqual(deploy_time['_v_pos'], 3)

        self.assertIn('type_s', deploy_time.keys())
        self.assertIsInstance(deploy_time['type_s'], tables.StringCol)
        self.assertEqual(deploy_time['type_s'].itemsize, 8)
        self.assertEqual(deploy_time['type_s']._v_pos, 4)

        self.assertIn('epoch_l', deploy_time.keys())
        self.assertIsInstance(deploy_time['epoch_l'], tables.Int64Col)
        self.assertEqual(deploy_time['epoch_l']._v_pos, 2)

        self.assertIn('ascii_s', deploy_time.keys())
        self.assertIsInstance(deploy_time['ascii_s'], tables.StringCol)
        self.assertEqual(deploy_time['ascii_s'].itemsize, 32)
        self.assertEqual(deploy_time['ascii_s']._v_pos, 1)

        self.assertIn('micro_seconds_i', deploy_time.keys())
        self.assertIsInstance(deploy_time['micro_seconds_i'], tables.Int32Col)
        self.assertEqual(deploy_time['micro_seconds_i']._v_pos, 3)

    def test_pickup_time(self):
        """
        test pickup_time's attributes
        """
        self.assertIn('pickup_time', self.array.keys())
        pickup_time = self.array['pickup_time'].columns

        self.assertIn('_v_pos', pickup_time.keys())
        self.assertEqual(pickup_time['_v_pos'], 4)

        self.assertIn('type_s', pickup_time.keys())
        self.assertIsInstance(pickup_time['type_s'], tables.StringCol)
        self.assertEqual(pickup_time['type_s'].itemsize, 8)
        self.assertEqual(pickup_time['type_s']._v_pos, 4)

        self.assertIn('epoch_l', pickup_time.keys())
        self.assertIsInstance(pickup_time['epoch_l'], tables.Int64Col)
        self.assertEqual(pickup_time['epoch_l']._v_pos, 2)

        self.assertIn('ascii_s', pickup_time.keys())
        self.assertIsInstance(pickup_time['ascii_s'], tables.StringCol)
        self.assertEqual(pickup_time['ascii_s'].itemsize, 32)
        self.assertEqual(pickup_time['ascii_s']._v_pos, 1)

        self.assertIn('micro_seconds_i', pickup_time.keys())
        self.assertIsInstance(pickup_time['micro_seconds_i'], tables.Int32Col)
        self.assertEqual(pickup_time['micro_seconds_i']._v_pos, 3)

    def test_das(self):
        """
        test das's attributes
        """
        self.assertIn('das', self.array.keys())
        das = self.array['das'].columns

        self.assertIn('_v_pos', das.keys())
        self.assertEqual(das['_v_pos'], 5)

        self.assertIn('manufacturer_s', das.keys())
        self.assertIsInstance(das['manufacturer_s'], tables.StringCol)
        self.assertEqual(das['manufacturer_s'].itemsize, 64)
        self.assertEqual(das['manufacturer_s']._v_pos, 3)

        self.assertIn('model_s', das.keys())
        self.assertIsInstance(das['model_s'], tables.StringCol)
        self.assertEqual(das['model_s'].itemsize, 64)
        self.assertEqual(das['model_s']._v_pos, 2)

        self.assertIn('serial_number_s', das.keys())
        self.assertIsInstance(das['serial_number_s'], tables.StringCol)
        self.assertEqual(das['serial_number_s'].itemsize, 64)
        self.assertEqual(das['serial_number_s']._v_pos, 1)

        self.assertIn('notes_s', das.keys())
        self.assertIsInstance(das['notes_s'], tables.StringCol)
        self.assertEqual(das['notes_s'].itemsize, 1024)
        self.assertEqual(das['notes_s']._v_pos, 5)

    def test_sensor(self):
        """
        test sensor's attributes
        """
        self.assertIn('sensor', self.array.keys())
        sensor = self.array['sensor'].columns

        self.assertIn('_v_pos', sensor.keys())
        self.assertEqual(sensor['_v_pos'], 6)

        self.assertIn('manufacturer_s', sensor.keys())
        self.assertIsInstance(sensor['manufacturer_s'], tables.StringCol)
        self.assertEqual(sensor['manufacturer_s'].itemsize, 64)
        self.assertEqual(sensor['manufacturer_s']._v_pos, 3)

        self.assertIn('model_s', sensor.keys())
        self.assertIsInstance(sensor['model_s'], tables.StringCol)
        self.assertEqual(sensor['model_s'].itemsize, 64)
        self.assertEqual(sensor['model_s']._v_pos, 2)

        self.assertIn('serial_number_s', sensor.keys())
        self.assertIsInstance(sensor['serial_number_s'], tables.StringCol)
        self.assertEqual(sensor['serial_number_s'].itemsize, 64)
        self.assertEqual(sensor['serial_number_s']._v_pos, 1)

        self.assertIn('notes_s', sensor.keys())
        self.assertIsInstance(sensor['notes_s'], tables.StringCol)
        self.assertEqual(sensor['notes_s'].itemsize, 1024)
        self.assertEqual(sensor['notes_s']._v_pos, 4)

    def test_location(self):
        """
        test location's attributes
        """
        self.assertIn('location', self.array.keys())
        location = self.array['location'].columns

        self.assertIn('_v_pos', location.keys())
        self.assertEqual(location['_v_pos'], 2)

        self.assertIn('coordinate_system_s', location.keys())
        self.assertIsInstance(
            location['coordinate_system_s'], tables.StringCol)
        self.assertEqual(location['coordinate_system_s'].itemsize, 32)
        self.assertEqual(location['coordinate_system_s']._v_pos, 4)

        self.assertIn('projection_s', location.keys())
        self.assertIsInstance(
            location['projection_s'], tables.StringCol)
        self.assertEqual(location['projection_s'].itemsize, 32)
        self.assertEqual(location['projection_s']._v_pos, 5)

        self.assertIn('ellipsoid_s', location.keys())
        self.assertIsInstance(
            location['ellipsoid_s'], tables.StringCol)
        self.assertEqual(location['ellipsoid_s'].itemsize, 32)
        self.assertEqual(location['ellipsoid_s']._v_pos, 6)
        self.assertIn('description_s', location.keys())
        self.assertIsInstance(location['description_s'], tables.StringCol)
        self.assertEqual(location['description_s'].itemsize, 1024)
        self.assertEqual(location['description_s']._v_pos, 7)

        # ---------------------- X -------------------#
        self.assertIn('X', location.keys())
        X = location['X'].columns

        self.assertIn('_v_pos', X.keys())
        self.assertEqual(X['_v_pos'], 1)

        self.assertIn('units_s', X.keys())
        self.assertIsInstance(X['units_s'], tables.StringCol)
        self.assertEqual(X['units_s'].itemsize, 16)

        self.assertIn('value_d', X.keys())
        self.assertIsInstance(X['value_d'], tables.Float64Col)
        self.assertEqual(X['value_d']._v_pos, 1)

        # ---------------------- Y -------------------#
        self.assertIn('Y', location.keys())
        Y = location['Y'].columns

        self.assertIn('_v_pos', Y.keys())
        self.assertEqual(Y['_v_pos'], 2)

        self.assertIn('units_s', Y.keys())
        self.assertIsInstance(Y['units_s'], tables.StringCol)
        self.assertEqual(Y['units_s'].itemsize, 16)

        self.assertIn('value_d', Y.keys())
        self.assertIsInstance(Y['value_d'], tables.Float64Col)
        self.assertEqual(Y['value_d']._v_pos, 1)

        # ---------------------- Z -------------------#
        self.assertIn('Z', location.keys())
        Z = location['Z'].columns

        self.assertIn('_v_pos', Z.keys())
        self.assertEqual(Z['_v_pos'], 3)

        self.assertIn('units_s', Z.keys())
        self.assertIsInstance(Z['units_s'], tables.StringCol)
        self.assertEqual(Z['units_s'].itemsize, 16)

        self.assertIn('value_d', Z.keys())
        self.assertIsInstance(Z['value_d'], tables.Float64Col)
        self.assertEqual(Z['value_d']._v_pos, 1)


class TestEvent(unittest.TestCase):
    print("test colunms.Event")

    def setUp(self):
        """
        setup for tests
        """
        self.event = columns.Event.columns

    def test_main_attributes(self):
        """
        test Event's attributes
        """
        self.assertIn('id_s', self.event.keys())
        self.assertIsInstance(self.event['id_s'], tables.StringCol)
        self.assertEqual(self.event['id_s'].itemsize, 16)
        self.assertEqual(self.event['id_s']._v_pos, 1)

        self.assertIn('description_s', self.event.keys())
        self.assertIsInstance(self.event['description_s'], tables.StringCol)
        self.assertEqual(self.event['description_s'].itemsize, 1024)
        self.assertEqual(self.event['description_s']._v_pos, 6)

    def test_location(self):
        """
        test location's attributes
        """
        self.assertIn('location', self.event.keys())
        location = self.event['location'].columns

        self.assertIn('_v_pos', location.keys())
        self.assertEqual(location['_v_pos'], 2)

        self.assertIn('coordinate_system_s', location.keys())
        self.assertIsInstance(
            location['coordinate_system_s'], tables.StringCol)
        self.assertEqual(location['coordinate_system_s'].itemsize, 32)
        self.assertEqual(location['coordinate_system_s']._v_pos, 4)

        self.assertIn('projection_s', location.keys())
        self.assertIsInstance(
            location['projection_s'], tables.StringCol)
        self.assertEqual(location['projection_s'].itemsize, 32)
        self.assertEqual(location['projection_s']._v_pos, 5)

        self.assertIn('ellipsoid_s', location.keys())
        self.assertIsInstance(
            location['ellipsoid_s'], tables.StringCol)
        self.assertEqual(location['ellipsoid_s'].itemsize, 32)
        self.assertEqual(location['ellipsoid_s']._v_pos, 6)
        self.assertIn('description_s', location.keys())
        self.assertIsInstance(location['description_s'], tables.StringCol)
        self.assertEqual(location['description_s'].itemsize, 1024)
        self.assertEqual(location['description_s']._v_pos, 7)

        # ---------------------- X -------------------#
        self.assertIn('X', location.keys())
        X = location['X'].columns

        self.assertIn('_v_pos', X.keys())
        self.assertEqual(X['_v_pos'], 1)

        self.assertIn('units_s', X.keys())
        self.assertIsInstance(X['units_s'], tables.StringCol)
        self.assertEqual(X['units_s'].itemsize, 16)

        self.assertIn('value_d', X.keys())
        self.assertIsInstance(X['value_d'], tables.Float64Col)
        self.assertEqual(X['value_d']._v_pos, 1)

        # ---------------------- Y -------------------#
        self.assertIn('Y', location.keys())
        Y = location['Y'].columns

        self.assertIn('_v_pos', Y.keys())
        self.assertEqual(Y['_v_pos'], 2)

        self.assertIn('units_s', Y.keys())
        self.assertIsInstance(Y['units_s'], tables.StringCol)
        self.assertEqual(Y['units_s'].itemsize, 16)

        self.assertIn('value_d', Y.keys())
        self.assertIsInstance(Y['value_d'], tables.Float64Col)
        self.assertEqual(Y['value_d']._v_pos, 1)

        # ---------------------- Z -------------------#
        self.assertIn('Z', location.keys())
        Z = location['Z'].columns

        self.assertIn('_v_pos', Z.keys())
        self.assertEqual(Z['_v_pos'], 3)

        self.assertIn('units_s', Z.keys())
        self.assertIsInstance(Z['units_s'], tables.StringCol)
        self.assertEqual(Z['units_s'].itemsize, 16)

        self.assertIn('value_d', Z.keys())
        self.assertIsInstance(Z['value_d'], tables.Float64Col)
        self.assertEqual(Z['value_d']._v_pos, 1)

    def test_time(self):
        """
        test time's attributes
        """
        self.assertIn('time', self.event.keys())
        time = self.event['time'].columns

        self.assertIn('_v_pos', time.keys())
        self.assertEqual(time['_v_pos'], 3)

        self.assertIn('type_s', time.keys())
        self.assertIsInstance(time['type_s'], tables.StringCol)
        self.assertEqual(time['type_s'].itemsize, 8)
        self.assertEqual(time['type_s']._v_pos, 4)

        self.assertIn('epoch_l', time.keys())
        self.assertIsInstance(time['epoch_l'], tables.Int64Col)
        self.assertEqual(time['epoch_l']._v_pos, 2)

        self.assertIn('ascii_s', time.keys())
        self.assertIsInstance(time['ascii_s'], tables.StringCol)
        self.assertEqual(time['ascii_s'].itemsize, 32)
        self.assertEqual(time['ascii_s']._v_pos, 1)

        self.assertIn('micro_seconds_i', time.keys())
        self.assertIsInstance(time['micro_seconds_i'], tables.Int32Col)
        self.assertEqual(time['micro_seconds_i']._v_pos, 3)

    def test_size(self):
        """
        test size's attributes
        """
        self.assertIn('size', self.event.keys())
        size = self.event['size'].columns

        self.assertIn('_v_pos', size.keys())
        self.assertEqual(size['_v_pos'], 4)

        self.assertIn('units_s', size.keys())
        self.assertIsInstance(size['units_s'], tables.StringCol)
        self.assertEqual(size['units_s'].itemsize, 16)

        self.assertIn('value_d', size.keys())
        self.assertIsInstance(size['value_d'], tables.Float64Col)
        self.assertEqual(size['value_d']._v_pos, 1)

    def test_depth(self):
        """
        test depth's attributes
        """
        self.assertIn('depth', self.event.keys())
        depth = self.event['depth'].columns

        self.assertIn('_v_pos', depth.keys())
        self.assertEqual(depth['_v_pos'], 5)

        self.assertIn('units_s', depth.keys())
        self.assertIsInstance(depth['units_s'], tables.StringCol)
        self.assertEqual(depth['units_s'].itemsize, 16)

        self.assertIn('value_d', depth.keys())
        self.assertIsInstance(depth['value_d'], tables.Float64Col)
        self.assertEqual(depth['value_d']._v_pos, 1)


class TestReport(unittest.TestCase):
    print("test colunms.Report")

    def setUp(self):
        """
        setup for tests
        """
        self.report = columns.Report.columns

    def test_main_attributes(self):
        """
        test Event's attributes
        """
        self.assertIn('title_s', self.report.keys())
        self.assertIsInstance(self.report['title_s'], tables.StringCol)
        self.assertEqual(self.report['title_s'].itemsize, 64)

        self.assertIn('format_s', self.report.keys())
        self.assertIsInstance(self.report['format_s'], tables.StringCol)
        self.assertEqual(self.report['format_s'].itemsize, 32)

        self.assertIn('description_s', self.report.keys())
        self.assertIsInstance(self.report['description_s'], tables.StringCol)
        self.assertEqual(self.report['description_s'].itemsize, 1024)

        self.assertIn('array_name_a', self.report.keys())
        self.assertIsInstance(self.report['array_name_a'], tables.StringCol)
        self.assertEqual(self.report['array_name_a'].itemsize, 32)


class TestOffset(unittest.TestCase):
    print("test colunms.Offset")

    def setUp(self):
        """
        setup for tests
        """
        self.offset = columns.Offset.columns

    def test_main_attributes(self):
        """
        test Offset's attributes
        """
        self.assertIn('event_id_s', self.offset.keys())
        self.assertIsInstance(self.offset['event_id_s'], tables.StringCol)
        self.assertEqual(self.offset['event_id_s'].itemsize, 16)

        self.assertIn('receiver_id_s', self.offset.keys())
        self.assertIsInstance(self.offset['receiver_id_s'], tables.StringCol)
        self.assertEqual(self.offset['receiver_id_s'].itemsize, 16)

    def test_offset(self):
        """
        test offset's attributes
        """
        self.assertIn('offset', self.offset.keys())
        offset = self.offset['offset'].columns

        self.assertIn('units_s', offset.keys())
        self.assertIsInstance(offset['units_s'], tables.StringCol)
        self.assertEqual(offset['units_s'].itemsize, 16)

        self.assertIn('value_d', offset.keys())
        self.assertIsInstance(offset['value_d'], tables.Float64Col)
        self.assertEqual(offset['value_d']._v_pos, 1)

    def test_azimuth(self):
        """
        test azimuth's attributes
        """
        self.assertIn('azimuth', self.offset.keys())
        azimuth = self.offset['azimuth'].columns

        self.assertIn('units_s', azimuth.keys())
        self.assertIsInstance(azimuth['units_s'], tables.StringCol)
        self.assertEqual(azimuth['units_s'].itemsize, 16)

        self.assertIn('value_f', azimuth.keys())
        self.assertIsInstance(azimuth['value_f'], tables.Float32Col)
        self.assertEqual(azimuth['value_f']._v_pos, 1)


class TestResponse(unittest.TestCase):
    print("test colunms.Response")

    def setUp(self):
        """
        setup for tests
        """
        self.response = columns.Response.columns

    def test_main_attributes(self):
        """
        test Offset's attributes
        """
        self.assertIn('n_i', self.response.keys())
        self.assertIsInstance(self.response['n_i'], tables.Int32Col)
        self.assertEqual(self.response['n_i']._v_pos, 1)

        self.assertIn('response_file_a', self.response.keys())
        self.assertIsInstance(
            self.response['response_file_a'], tables.StringCol)
        self.assertEqual(self.response['response_file_a'].itemsize, 32)

        self.assertIn('response_file_das_a', self.response.keys())
        self.assertIsInstance(
            self.response['response_file_das_a'], tables.StringCol)
        self.assertEqual(self.response['response_file_das_a'].itemsize, 128)

        self.assertIn('response_file_sensor_a', self.response.keys())
        self.assertIsInstance(
            self.response['response_file_sensor_a'], tables.StringCol)
        self.assertEqual(self.response['response_file_sensor_a'].itemsize, 128)

    def test_gain(self):
        """
        test gain's attributes
        """
        self.assertIn('gain', self.response.keys())
        gain = self.response['gain'].columns

        self.assertIn('units_s', gain.keys())
        self.assertIsInstance(gain['units_s'], tables.StringCol)
        self.assertEqual(gain['units_s'].itemsize, 16)

        self.assertIn('value_i', gain.keys())
        self.assertIsInstance(gain['value_i'], tables.Int16Col)

    def test_bit_weight(self):
        """
        test bit_weight's attributes
        """
        self.assertIn('bit_weight', self.response.keys())
        bit_weight = self.response['bit_weight'].columns

        self.assertIn('_v_pos', bit_weight.keys())
        self.assertEqual(bit_weight['_v_pos'], 3)

        self.assertIn('units_s', bit_weight.keys())
        self.assertIsInstance(bit_weight['units_s'], tables.StringCol)
        self.assertEqual(bit_weight['units_s'].itemsize, 16)

        self.assertIn('value_d', bit_weight.keys())
        self.assertIsInstance(bit_weight['value_d'], tables.Float64Col)
        self.assertEqual(bit_weight['value_d']._v_pos, 1)


class Test_columns(unittest.TestCase):
    print("test colunms' methods")

    def setUp(self):
        """
        setup for tests
        """
        class TestClass(tables.IsDescription):
            type_s = tables.StringCol(8)
            epoch_l = tables.Int64Col()
            row_id = tables.StringCol(1)

        self.columns = columns
        self.ph5 = tables.open_file("master.ph5", 'w')
        self.mygroup = self.ph5.create_group('/', 'A_group', '')
        self.mytable = self.ph5.create_table(
            self.mygroup, 'A_table', TestClass)
        myrow = self.mytable.row
        datarows = [('EPOCH', 1550854299, '1'), ('EPOCH', 1550855362, '2')]
        for d in datarows:
            myrow['type_s'] = d[0]
            myrow['epoch_l'] = d[1]
            myrow['row_id'] = d[2]
            myrow.append()
        self.mytable.flush()

    def test_add_reference(self):
        """
        test add_reference method
        """
        self.columns.add_reference('test_table  ', 'test_reference')
        self.assertEqual(self.columns.TABLES['test_table'], 'test_reference')

    def test_add_last_array_node_maps(self):
        """
        test add_last_array_node_maps method
        """
        # mygroup = self.ph5.get_node('/','A_group', 'Group')
        self.columns.add_last_array_node_maps(
            self.mygroup, 'Hdr_a_', 'Hdr_a_0001')
        self.assertEqual(self.columns.LAST_ARRAY_NODE_MAPS,
                         {'A_group': {'Hdr_a_': 'Hdr_a_0001'}})

    def test_add_last_array_node_das(self):
        """
        test add_last_array_node_das method
        """
        # mygroup = self.ph5.get_node('/','A_group', 'Group')
        self.columns.add_last_array_node_das(
            self.mygroup, 'Data_a_', 'Data_a_0001')
        self.assertEqual(self.columns.LAST_ARRAY_NODE_DAS,
                         {'A_group': {'Data_a_': 'Data_a_0001'}})

    def test_rowstolist(self):
        """
        test rowstolist method
        """
        # mytable = self.ph5.get_node('/A_group', 'A_table', 'Table')
        tableiterator = self.mytable.iterrows()
        keys = ['type_s', 'epoch_l']
        ret = self.columns.rowstolist(tableiterator, keys)

        self.assertEqual(ret, [{'type_s': 'EPOCH', 'epoch_l': 1550854299},
                               {'type_s': 'EPOCH', 'epoch_l': 1550855362}])

    def test__flatten(self):
        """
        test _flatten method
        """
        # without pre
        ret = self.columns._flatten(['epoch_l', 'type_s', ('aaa', 'bbb'), 1])
        self.assertEqual(ret,
                         {'type_s': True, 'epoch_l': True, 'aaa/bbb': True})

        # with pre
        ret = self.columns._flatten(['epoch_l', 'type_s'], pre=["end_time"])
        self.assertEqual(
            ret, {'end_time/type_s': True, 'end_time/epoch_l': True})

    def test_keys(self):
        """
        test keys method
        """
        # mytable = self.ph5.get_node('/A_group', 'A_table', 'Table')
        keys, names = self.columns.keys(self.mytable)

        self.assertEqual(sorted(keys),
                         sorted(['epoch_l', 'type_s', 'row_id']))
        self.assertEqual(sorted(names),
                         sorted(['epoch_l', 'type_s', 'row_id']))

    def test_validate(self):
        """
        test validate method
        """
        # mytable = self.ph5.get_node('/A_group', 'A_table', 'Table')
        p = {'type_s': 'EPOCH', 'epoch_ll': 1550854299}
        required_keys = ['epoch_l']

        fail_keys, fail_required = self.columns.validate(
            self.mytable, p, required_keys)

        self.assertEqual(
            fail_keys, ['Error: No such column: epoch_ll'])
        self.assertEqual(
            fail_required, ['Error: Required key missing: epoch_l'])

    def test_node(self):
        """
        test node method
        """
        # mygroup = self.ph5.get_node('/','A_group', 'Group')
        ret = self.columns.node(self.ph5, '/A_group', 'Group')
        self.assertEqual(ret, self.mygroup)

        # mytable = self.ph5.get_node('/A_group', 'A_table', 'Table')
        ret = self.columns.node(self.ph5, '/A_group/A_table', 'Table')
        self.assertEqual(ret, self.mytable)

    def test__cast(self):
        """
        test _cast method
        """
        # float
        ret = self.columns._cast('Float64', '123')
        self.assertIsInstance(ret, float)

        ret = self.columns._cast('float64', '123')
        self.assertIsInstance(ret, float)

        ret = self.columns._cast('Float32', '123')
        self.assertIsInstance(ret, float)

        ret = self.columns._cast('float32', '123')
        self.assertIsInstance(ret, float)

        ret = self.columns._cast('float32', '12a')
        self.assertIsNone(ret)

        # long
        ret = self.columns._cast('Int64', '123')
        self.assertIsInstance(ret, long)

        ret = self.columns._cast('int64', '123')
        self.assertIsInstance(ret, long)

        ret = self.columns._cast('UInt64', '123')
        self.assertIsInstance(ret, long)

        ret = self.columns._cast('uint64', '123')
        self.assertIsInstance(ret, long)

        ret = self.columns._cast('uint64', '12a')
        self.assertIsNone(ret)

        # int
        ret = self.columns._cast('Int32', '123')
        self.assertIsInstance(ret, int)

        ret = self.columns._cast('int32', '123')
        self.assertIsInstance(ret, int)

        ret = self.columns._cast('UInt32', '123')
        self.assertIsInstance(ret, int)

        ret = self.columns._cast('uint32', '123')
        self.assertIsInstance(ret, int)

        ret = self.columns._cast('uint32', '12a')
        self.assertIsNone(ret)

        ret = self.columns._cast('Int16', '123')
        self.assertIsInstance(ret, int)

        ret = self.columns._cast('int16', '123')
        self.assertIsInstance(ret, int)

        ret = self.columns._cast('UInt16', '123')
        self.assertIsInstance(ret, int)

        ret = self.columns._cast('uint16', '123')
        self.assertIsInstance(ret, int)

        ret = self.columns._cast('uint16', '12a')
        self.assertIsNone(ret)

        ret = self.columns._cast('Int8', '123')
        self.assertIsInstance(ret, int)

        ret = self.columns._cast('int8', '123')
        self.assertIsInstance(ret, int)

        ret = self.columns._cast('UInt8', '123')
        self.assertIsInstance(ret, int)

        ret = self.columns._cast('uint8', '123')
        self.assertIsInstance(ret, int)

        ret = self.columns._cast('uint8', '12a')
        self.assertIsNone(ret)

        ret = self.columns._cast(None, '123')
        self.assertIsNone(ret)

    def test_search(self):
        """
        test search method
        """
        # mytable = self.ph5.get_node('/A_group', 'A_table', 'Table')

        # search existing value
        ret = self.columns.search(self.mytable, 'row_id', '1')
        self.assertEqual(sorted(ret.fetch_all_fields()),
                         sorted(('EPOCH', 1550854299, '1')))

        # search non-existing value
        ret = self.columns.search(self.mytable, 'row_id', '3')
        self.assertIsNone(ret)

        # search non-str value
        ret = self.columns.search(self.mytable, 'epoch_l', 1550854299)
        self.assertEqual(sorted(ret.fetch_all_fields()),
                         sorted(('EPOCH', 1550854299, '1')))

    def test_lindex(self):
        """
        test lindex method
        """
        # mytable = self.ph5.get_node('/A_group', 'A_table', 'Table')

        # get index existing value
        ret = self.columns.lindex(self.mytable, '2', 'row_id')
        self.assertEqual(ret, 1)

        # get index non-existing value
        ret = self.columns.lindex(self.mytable, '3', 'row_id')
        self.assertIsNone(ret)

        # get index non-str value
        ret = self.columns.lindex(self.mytable, 1550854299, 'epoch_l')
        self.assertEqual(ret, 0)

    def test_delete(self):
        """
        test delete method
        """
        # mytable = self.ph5.get_node('/A_group', 'A_table', 'Table')

        # exist before deleting
        ret = self.columns.search(self.mytable, 'row_id', '1')
        self.assertIsNotNone(ret)

        self.columns.delete(self.mytable, '1', 'row_id')

        # not exist after deleting
        ret = self.columns.search(self.mytable, 'row_id', '1')
        self.assertIsNone(ret)

    def test_update(self):
        """
        test update method
        """
        # check value in row with row_id=1 (str)
        ret = self.columns.search(self.mytable, 'row_id', '1')
        self.assertEqual(sorted(ret.fetch_all_fields()),
                         sorted(('EPOCH', 1550854299, '1')))

        # update row with row_id=1
        p = {'type_s': 'EPOCH', 'epoch_l': 1234567890, 'row_id': '1'}
        self.columns.update(self.mytable, p, 'row_id')

        # check if value in row with row_id=1 is updated
        ret = self.columns.search(self.mytable, 'row_id', '1')
        self.assertEqual(sorted(ret.fetch_all_fields()),
                         sorted(('EPOCH', 1234567890, '1')))

        # check value in row with epoch_l= 1550855362 (non str)
        ret = self.columns.search(self.mytable, 'epoch_l', 1550855362)
        self.assertEqual(sorted(ret.fetch_all_fields()),
                         sorted(('EPOCH', 1550855362, '2')))

        # update row with epoch_l= 1550855362, type_s doen't need exist
        p = {'epoch_l': 1550855362, 'row_id': '3'}
        self.columns.update(self.mytable, p, 'epoch_l')

        # check if value in row with epoch_l= 1550855362 is updated
        ret = self.columns.search(self.mytable, 'epoch_l', 1550855362)
        self.assertEqual(sorted(ret.fetch_all_fields()),
                         sorted(('EPOCH', 1550855362, '3')))

    def test_append(self):
        """
        test append method
        """
        # check if row with row_id=3 not exist
        ret = self.columns.search(self.mytable, 'row_id', '3')
        self.assertIsNone(ret)
        p = {'type_s': 'EPOCH', 'epoch_l': 1234567890, 'row_id': '3'}
        self.columns.append(self.mytable, p)

        # check if row with row_id=3 is added to table
        ret = self.columns.search(self.mytable, 'row_id', '3')
        self.assertEqual(sorted(ret.fetch_all_fields()),
                         sorted(('EPOCH', 1234567890, '3')))

    def test_is_mini(self):
        """
        test is_mini method
        """
        # open table to Dass 9EEF
        path_to_file = "ph5/test_data/PH5/miniPH5_00001.ph5"
        path_to_table = '/Experiment_g/Receivers_g/Das_g_9EEF/Das_t'
        ph5 = tables.open_file(path_to_file, 'r')
        mytable = ph5.get_node(path_to_table)

        # run is_mini and check result
        ret = self.columns.is_mini(mytable)
        self.assertIsInstance(ret, tables.Table)
        self.assertEqual(
            ret._v_pathname, path_to_table)

        tablefile = ret._v_file
        self.assertEqual(tablefile.filename, path_to_file)
        self.assertEqual(tablefile.mode, 'a')

        # close ph5
        # ph5.close()
        tablefile.close()

    def test_populate(self):
        """
        test populate method
        """
        # check if row with row_id=3 not exist
        ret = self.columns.search(self.mytable, 'row_id', '3')
        self.assertIsNone(ret)
        p = {'type_s': 'EPOCH', 'epoch_l': 1234567890, 'row_id': '3'}
        self.columns.populate(self.mytable, p)

        # check if row with row_id=3 is added to table
        ret = self.columns.search(self.mytable, 'row_id', '3')
        self.assertEqual(sorted(ret.fetch_all_fields()),
                         sorted(('EPOCH', 1234567890, '3')))

        p = {'type_s': 'EPOCH', 'epoch_l': 1030507090, 'row_id': '3'}
        self.columns.populate(self.mytable, p, key='row_id')

        # check if row with row_id=3 is updated with new value
        ret = self.columns.search(self.mytable, 'row_id', '3')
        self.assertEqual(sorted(ret.fetch_all_fields()),
                         sorted(('EPOCH', 1030507090, '3')))

    def tearDown(self):
        if self.ph5 is not None and self.ph5.isopen:
            self.ph5.close()
            self.ph5 = None
        os.remove("master.ph5")


if __name__ == "__main__":
    unittest.main()
