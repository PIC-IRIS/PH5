# Tim Ronan, Aug 2019
# Nick Falco, Aug 2019

import os
import sys
import argparse
import logging
import obspy
from ph5.core import ph5api, timedoy, ph5utils
from ph5.utilities import obspytoph5

PROG_VERSION = "2019.246"
LOGGER = logging.getLogger(__name__)


# 1: Z, 2: NORTH, 3: EAST
SEGY_ORIENTATION_TO_SEED_ORIENTATION = {"1": "Z",
                                        "2": "1",
                                        "3": "2"}


class TestSegyData():

    def __init__(self, coordinate_units):
        self.test_map = {}
        self.coordinate_units = coordinate_units

    def has_errors(self):
        if self.test_map:
            return True
        else:
            return False

    def add_error(self, file_name, err_msg):
        if self.test_map.get(file_name):
            if err_msg not in self.test_map[file_name]:
                self.test_map[file_name].append(err_msg)
        else:
            self.test_map[file_name] = [err_msg]

    def check_segy(self, file_name, tr):
        th = tr.stats.segy.trace_header
        if ((th.coordinate_units < 1 or th.coordinate_units > 4) and
                self.coordinate_units is None):
            err_msg = ("SEG-Y contains an ambiguous value for coordinate "
                       "units in Trace Header [89-90]. Manually supply a "
                       "value using --coordinate_units.")
            self.add_error(file_name, err_msg)
        elif th.coordinate_units == 1 and self.coordinate_units is None:
            err_msg = ("Unsupported coordinate units. "
                       "Cannot convert meters to degrees. "
                       "If this is a mistake, manually supply a value "
                       "using --coordinate_units.")
            self.add_error(file_name, err_msg)
        elif th.coordinate_units == 4 and self.coordinate_units is None:
            err_msg = ("Unsupported coordinate units. "
                       "Cannot convert DMS to degrees. "
                       "If this is a mistake, manually supply a value "
                       "using --coordinate_units.")
            self.add_error(file_name, err_msg)

    def print_error_summary(self):
        for fn, errors in self.test_map.items():
            LOGGER.info("Errors for {}".format(fn))
            for e in errors:
                LOGGER.error("\t * {}".format(e))


class SegyToPH5():

    def __init__(self, path, nickname, segydir, mini_size_max,
                 coordinate_units=None, id_field=None,
                 file_ext="sgy", array_name="001"):
        self.path = path
        self.nickname = nickname
        self.segydir = segydir
        self.mini_size_max = mini_size_max
        # create ph5 object
        self.ph5 = ph5api.PH5(path=path, nickname=nickname,
                              editmode=True)
        # read ph5 tables
        self.ph5.read_experiment_t()
        self.exp_t = self.ph5.Experiment_t['rows']
        self.array_t_list = self.ph5.get_sort_arrays()
        self.coordinate_units = coordinate_units
        self.id_field = id_field
        self.file_ext = file_ext
        self.array_name = "Array_t_{}".format(array_name)

    def prepopulate_trace(self, station, trace):
        trace.stats.network = self.exp_t[0]["net_code_s"]
        trace.stats.station = station['seed_station_name_s']
        trace.stats.location = station['seed_location_code_s']
        trace.stats.channel = "%s%s%s" % (station['seed_band_code_s'],
                                          station['seed_instrument_code_s'],
                                          station['seed_orientation_code_s'])
        return trace

    def tracetoph5(self, trace):
        LOGGER.info("Load %s" % trace)

        th = trace.stats.segy.trace_header
        if self.id_field == "channel_no":  # trace header [13-16]
            trace.stats.station = \
                th.trace_number_within_the_original_field_record
        elif self.id_field == "field_record_number":  # trace header [9-12]
            trace.stats.station = th.original_field_record_number
        else:  # trace header [173-174] (default)
            trace.stats.station = th.geophone_group_number_of_trace_number_one

        obs = obspytoph5.ObspytoPH5(self.ph5,
                                    self.path,
                                    first_mini=1,
                                    mini_size_max=self.mini_size_max)
        obs.verbose = True
        message, index_t = obs.toph5((trace, 'Trace'),
                                     self.path,
                                     dtype="float32")
        for entry in index_t:
            self.ph5.ph5_g_receivers.populateIndex_t(entry)
        obs.update_external_references(index_t)

    def set_coordinates(self, array, th):
        # coordinates in degrees
        coord_scaler = th.scalar_to_be_applied_to_all_coordinates
        depth_scaler = th.scalar_to_be_applied_to_all_elevations_and_depths

        elevation = th.receiver_group_elevation
        lat = th.group_coordinate_x
        lng = th.group_coordinate_y

        # scale appropriately
        if coord_scaler < 0:
            lat = float(th.group_coordinate_x / abs(coord_scaler))
            lng = float(th.group_coordinate_y / abs(coord_scaler))
        elif coord_scaler > 0:
            lat = float(th.group_coordinate_x * abs(coord_scaler))
            lng = float(th.group_coordinate_y * abs(coord_scaler))
        if depth_scaler < 0:
            elevation = float(th.receiver_group_elevation / abs(depth_scaler))
        elif depth_scaler > 0:
            elevation = float(th.receiver_group_elevation * depth_scaler)

        # convert to degrees if necessary
        coordinate_units = self.coordinate_units \
            if self.coordinate_units else th.coordinate_units
        if coordinate_units == 1:
            # meters
            raise NotImplementedError("Unsupported coordinate units. "
                                      "Cannot convert meters to degrees.")
        elif coordinate_units == 2:
            # arcseconds
            lat /= 3600.
            lng /= 3600.
        elif coordinate_units == 3:
            # degrees
            pass
        elif coordinate_units == 4:
            # dms
            raise NotImplementedError("Unsupported coordinate units. "
                                      "Cannot convert DMS to degrees.")
        else:
            raise RuntimeError("Encountered a unsupported coordinate unit "
                               "type. Manually supply a value using "
                               "--coordinate_units.")
        lat = round(lat, 6)
        lng = round(lng, 6)
        array['location/X/value_d'] = lat
        array['location/Y/value_d'] = lng
        array['location/Z/value_d'] = elevation
        array['location/X/units_s'] = 'degrees'
        array['location/Y/units_s'] = 'degrees'
        array['location/Z/units_s'] = 'meters'
        array['location/coordinate_system_s'] = 'geographic'
        array['location/projection_s'] = 'WGS84'
        array['location/ellipsoid_s'] = ''
        array['location/description_s'] = 'UTC'
        return array

    def trace_to_array_dict(self, tr):
        # create new record from the PH5 metadata
        array = {}
        th = tr.stats.segy.trace_header
        if self.id_field == "channel_no":  # trace header [13-16]
            array['id_s'] = th.trace_number_within_the_original_field_record
            array['seed_station_name_s'] = \
                th.trace_number_within_the_original_field_record
        elif self.id_field == "field_record_number":  # trace header [9-12]
            array['id_s'] = th.original_field_record_number
            array['seed_station_name_s'] = th.original_field_record_number
        else:  # trace header [173-174] (default)
            array['id_s'] = th.geophone_group_number_of_trace_number_one
            array['seed_station_name_s'] = \
                th.geophone_group_number_of_trace_number_one
        array = self.set_coordinates(array, th)

        st = ph5utils.roundSeconds(tr.stats.starttime.datetime)
        time = timedoy.fdsn2epoch(st.isoformat(), fepoch=True)
        array['deploy_time/ascii_s'] = st.isoformat()
        array['deploy_time/epoch_l'] = int(time)
        array['deploy_time/micro_seconds_i'] = 0
        array['deploy_time/type_s'] = 'BOTH'
        et = ph5utils.roundSeconds(tr.stats.endtime.datetime)
        time = timedoy.fdsn2epoch(et.isoformat(), fepoch=True)
        array['pickup_time/ascii_s'] = \
            et.isoformat()
        array['pickup_time/epoch_l'] = int(time)
        array['pickup_time/micro_seconds_i'] = 0
        array['pickup_time/type_s'] = 'BOTH'

        array['das/serial_number_s'] = '{}X{}'.format(array['id_s'],
                                                      array['id_s'])
        array['das/model_s'] = ''
        array['das/manufacturer_s'] = ''
        array['das/notes_s'] = ''
        array['sensor/serial_number_s'] = ''
        array['sensor/model_s'] = ''
        array['sensor/manufacturer_s'] = ''
        array['sensor/notes_s'] = ''
        array['description_s'] = ''
        array['sample_rate_i'] = tr.stats.sampling_rate
        array['sample_rate_multiplier_i'] = tr.stats.calib

        # Channel code. instrument and band codes are ? since they are unknown
        array['seed_instrument_code_s'] = '?'
        array['seed_band_code_s'] = '?'
        array['seed_orientation_code_s'] = (
            SEGY_ORIENTATION_TO_SEED_ORIENTATION
            .get(str(th.trace_identification_code),
                 str(th.trace_identification_code)))

        array['seed_location_code_s'] = ''
        array['channel_number_i'] = th.trace_identification_code
        array['receiver_table_n_i'] = 0
        array['response_table_n_i'] = 0
        return array

    def add_new_station_record(self, station):
        names = self.ph5.ph5_g_sorts.names()
        if self.array_name not in names:
            self.ph5.ph5_g_sorts.NewSort(self.array_name)
            self.ph5.initgroup()
        self.ph5.ph5_g_sorts.populateArray_t(
            station,
            name=self.array_name)

    def load_data(self, st, array_names):
        # Loops through segy traces
        for tr in st:
            array_dict = self.trace_to_array_dict(tr)
            # loops through the named arrays
            did_update = False
            found_match = False
            names = self.ph5.ph5_g_sorts.names()
            if self.array_name in names:
                self.ph5.ph5_g_sorts.read_arrays(self.array_name)
                array_t = self.ph5.ph5_g_sorts.ph5_t_array[self.array_name]
                for station in array_t:
                    if (int(station['id_s']) == int(array_dict['id_s']) and
                            float(station['location/X/value_d']) ==
                            float(array_dict["location/X/value_d"]) and
                            float(station['location/Y/value_d']) ==
                            float(array_dict["location/Y/value_d"]) and
                            float(station['location/Z/value_d']) ==
                            float(array_dict["location/Z/value_d"]) and
                            str(station['seed_orientation_code_s']) ==
                            str(array_dict['seed_orientation_code_s']) and
                            float(station['sample_rate_i']) ==
                            float(array_dict["sample_rate_i"])):
                        LOGGER.info("Update existing station id: {} lat: {} "
                                    "lng: {} elv: {} sr: {}"
                                    .format(array_dict["id_s"],
                                            array_dict["location/X/value_d"],
                                            array_dict["location/Y/value_d"],
                                            array_dict["location/Z/value_d"],
                                            array_dict["sample_rate_i"]))
                        found_match = True
                        # extend epoch
                        if (array_dict['pickup_time/ascii_s'] >
                                station['pickup_time/ascii_s']):
                            LOGGER.info("ADJUSTED PICKUP TIME")
                            station['pickup_time/ascii_s'] = \
                                array_dict['pickup_time/ascii_s']
                            station['pickup_time/epoch_l'] = \
                                array_dict['pickup_time/epoch_l']
                            station['pickup_time/micro_seconds_i'] = \
                                array_dict['pickup_time/micro_seconds_i']
                            station.update()
                            did_update = True
                        if (array_dict['deploy_time/ascii_s'] <
                                station['deploy_time/ascii_s']):
                            LOGGER.info("ADJUSTED DEPLOY TIME")
                            station['deploy_time/ascii_s'] = \
                                array_dict['deploy_time/ascii_s']
                            station['deploy_time/epoch_l'] = \
                                array_dict['deploy_time/epoch_l']
                            station['deploy_time/micro_seconds_i'] = \
                                array_dict['deploy_time/micro_seconds_i']
                            station.update()
                            did_update = True
                        trace = self.prepopulate_trace(station,
                                                       tr)
                        self.tracetoph5(trace)
            if found_match is False:
                # no match found so add a new record and load
                LOGGER.info("Add new station id: {} lat: {} lng: {} elv: {} "
                            "sr: {}"
                            .format(array_dict["id_s"],
                                    array_dict["location/X/value_d"],
                                    array_dict["location/Y/value_d"],
                                    array_dict["location/Z/value_d"],
                                    array_dict["sample_rate_i"]))
                self.add_new_station_record(array_dict)
                trace = self.prepopulate_trace(array_dict,
                                               tr)
                self.tracetoph5(trace)
            if did_update is True:
                self.ph5.ph5_g_sorts.ph5_t_array[self.array_name].flush()

    def get_files_sorted_by_first_trace(self):
        fns = []
        for root, dirs, files in os.walk(self.segydir, topdown=False):
            for name in files:
                if name.endswith(self.file_ext):
                    fn = os.path.join(root, name)
                    st = obspy.read(fn,
                                    format="SEGY",
                                    unpack_trace_headers=True,
                                    headonly=True)
                    starttime = st[0].stats.starttime
                    fns.append((starttime, fn))
        fns.sort(key=lambda tup: tup[0], reverse=False)
        if not fns:
            raise ValueError("No SEG-Y files with file extension '{}' "
                             "were found in the {} directory."
                             .format(self.file_ext,
                                     self.segydir))
        return [tup[1] for tup in fns]

    def run(self):
        files = self.get_files_sorted_by_first_trace()

        # index of array names matches array index
        array_names = self.ph5.ph5_g_sorts.names()

        LOGGER.info("Checking SEGY files for problems")
        test_handler = TestSegyData(self.coordinate_units)
        for fn in files:
            st = obspy.read(fn,
                            format="SEGY",
                            unpack_trace_headers=True,
                            headonly=True)
            for tr in st:
                test_handler.check_segy(fn, tr)
        if test_handler.has_errors():
            test_handler.print_error_summary()
            msg = ("There were problems found that need to "
                   "be resolved before loading this SEG-Y data. "
                   "Aborting load.")
            LOGGER.critical(msg)
            return False
        else:
            LOGGER.info("OK")

        # Loop through all of the segy files in a path
        for fn in files:
            LOGGER.info("Loading file %s:" % fn)
            st = obspy.read(fn,
                            format="SEGY",
                            unpack_trace_headers=True)
            self.load_data(st, array_names)
        self.ph5.ph5close()
        LOGGER.info('Conversion Completed.')


def parse_arguments():
    parser = argparse.ArgumentParser(
                         description="Load SEG-Y data into PH5")
    parser.add_argument("-n", "--nickname",
                        help="PH5 experiment nickname (e.g. master.ph5)",
                        default="master.ph5")
    parser.add_argument("-p", "--path",
                        help="Path to PH5 experiment",
                        default=".")
    parser.add_argument("--segydir",
                        help=("Path to the directory where"
                              "the SEG-Y files are stored"),
                        default=".")
    parser.add_argument("--coordinate_units",
                        help=("Manually specify coordinate units (optional). "
                              "(1: METERS, 2: ARCSECONDS, 3: DEGREES, "
                              "4: DMS)"),
                        default=None,
                        type=int)
    parser.add_argument("--id_field",
                        help=("Manually specify the field in the SEG-Y trace "
                              "header to extract the id_s from (optional). "
                              "Choose from 'geophone_group_firsttrace' "
                              "[173-174] (default), 'channel_no' [13-16], or "
                              "'field_record_number' [9-12]"),
                        default="geophone_group_firsttrace",
                        type=str)
    parser.add_argument("--array",
                        help=("Manually specify array id (optional) "
                              "(e.g. 001)"),
                        default="001",
                        type=str)
    parser.add_argument("--file_ext",
                        help=("Manually specify file extension (optional)."),
                        default="sgy")
    parser.add_argument("--mini_size_max",
                        help=("Approximate maximum size of a miniPH5 file "
                              "in bytes (optional)."),
                        default=None,
                        type=int)
    args = parser.parse_args()
    if len(args.array) != 3:
        raise AssertionError("Array code must be 3 characters. e.g. 001")
    if not os.path.isfile(os.path.join(args.path, args.nickname)):
        raise OSError("No file exists at the specified path {}"
                      .format(os.path.join(args.path, args.nickname)))
    return args


def main():
    try:
        args = parse_arguments()
        SegyToPH5(args.path,
                  args.nickname,
                  args.segydir,
                  args.mini_size_max,
                  coordinate_units=args.coordinate_units,
                  id_field=args.id_field,
                  file_ext=args.file_ext,
                  array_name=args.array).run()
    except Exception as e:
        LOGGER.error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
