# Derick Hess, Oct 2017
#
"""
Runs a set of checks on PH5 archive to test for
errors and make sur eit is ready for archival at IRIS DMC
"""
import logging
import os
import argparse
import subprocess
from ph5 import LOGGING_FORMAT
from ph5.core import ph5api


PROG_VERSION = "2018.268"
LOGGER = logging.getLogger(__name__)


class PH5Validate(object):

    def __init__(self, ph5API_object, ph5path, level):
        # Set up logging
        # Write log to file
        ch = logging.FileHandler(os.path.join('.', "PH5Validate.log"))
        # Add formatter
        formatter = logging.Formatter(LOGGING_FORMAT)
        ch.setFormatter(formatter)
        if level == "error":
            ch.setLevel(logging.ERROR)
        else:
            ch.setLevel(logging.DEBUG)
        LOGGER.addHandler(ch)

        self.ph5 = ph5API_object
        self.path = ph5path
        if not self.ph5.Array_t_names:
            self.ph5.read_array_t_names()
        if not self.ph5.Experiment_t:
            self.ph5.read_experiment_t()

    def read_arrays(self, name):
        if name is None:
            for n in self.ph5.Array_t_names:
                self.ph5.read_array_t(n)
        else:
            self.ph5.read_array_t(name)

    def read_events(self, name):
        if name is None:
            for n in self.ph5.Event_t_names:
                self.ph5.read_event_t(n)
        else:
            self.ph5.read_event_t(name)

    def check_experiment_t(self):
        experiment_t = self.ph5.Experiment_t['rows']
        LOGGER.info("Checking Experiment Table")
        if len(experiment_t) == 0:
            LOGGER.error("Experiment_t does not exist. "
                         "run experiment_t_gen to create table")
            return
        if not experiment_t[0]['net_code_s']:
            LOGGER.error("Network code was not found: "
                         "A 2 character network code is required.")

        if not experiment_t[0]['net_code_s'][0].isdigit() and \
                experiment_t[0]['net_code_s'][0] != "X" and \
                experiment_t[0]['net_code_s'][0] != "Y" and \
                experiment_t[0]['net_code_s'][0] != "z":
            LOGGER.warning("Network code is a permanent FDSN: "
                           "Network code should be a temporary code.")

        if not experiment_t[0]['experiment_id_s']:
            LOGGER.error("Experiment ID was not found: "
                         "An experiment id (YY-XXX) is required.")

        if not experiment_t[0]['nickname_s']:
            LOGGER.warning("Nickname was not found: "
                           "It is suggested you include a nickname "
                           "for your experiment")

        if not experiment_t[0]['longname_s']:
            LOGGER.warning("Long name was not found: "
                           "It is suggested you include a long name "
                           "for your experiment")

        if not experiment_t[0]['PIs_s']:
            LOGGER.warning("PIs were not found: "
                           "It is suggested you include the PIs "
                           "for your experiment ")

        if not experiment_t[0]['institutions_s']:
            LOGGER.warning("Institutions were not found: "
                           "It is suggested you include the institutions "
                           "for your experiment")

        if (experiment_t[0]['north_west_corner/X/value_d'] == 0.0):
            LOGGER.warning("A bounding box was not detected: "
                           "A suggested bounding box has been calculated "
                           "and saved in 'experiment_t_bounding_box.kef'")
            max_lat = None
            min_lat = None
            max_lon = None
            min_lon = None

            array_names = sorted(self.ph5.Array_t_names)

            for array_name in array_names:
                self.read_arrays(array_name)
                arraybyid = self.ph5.Array_t[array_name]['byid']
                arrayorder = self.ph5.Array_t[array_name]['order']
                for ph5_station in arrayorder:
                    station_list = arraybyid.get(ph5_station)
                    for deployment in station_list:
                        station_len = len(station_list[deployment])
                        for st_num in range(0, station_len):

                            latitude = station_list[deployment][
                                st_num]['location/Y/value_d']
                            longitude = station_list[deployment][
                                st_num]['location/X/value_d']

                            if max_lat is None:
                                max_lat = latitude
                            elif latitude > max_lat:
                                max_lat = latitude
                            if min_lat is None:
                                min_lat = latitude
                            elif latitude < min_lat:
                                min_lat = latitude
                            if max_lon is None:
                                max_lon = longitude
                            elif longitude > max_lon:
                                max_lon = longitude
                            if min_lon is None:
                                min_lon = longitude
                            elif longitude < min_lon:
                                min_lon = longitude

            shot_lines = sorted(self.ph5.Event_t_names)

            for line in shot_lines:
                event_t = self.ph5.Event_t[line]['byid']
                for shot_id, _ in event_t.iteritems():
                    event_t = self.ph5.Event_t[
                        line]['byid'][shot_id]
                    latitude = event_t[
                        'location/Y/value_d']
                    longitude = event_t[
                        'location/X/value_d']
                    if max_lat is None:
                        max_lat = latitude
                    elif latitude > max_lat:
                        max_lat = latitude
                    if min_lat is None:
                        min_lat = latitude
                    elif latitude < min_lat:
                        min_lat = latitude
                    if max_lon is None:
                        max_lon = longitude
                    elif longitude > max_lon:
                        max_lon = longitude
                    if min_lon is None:
                        min_lon = longitude
                    elif longitude < min_lon:
                        min_lon = longitude

            process = subprocess.Popen(
                ("ph5tokef -n master.ph5 -p {0} -E >"
                 "experiment_t_bounding_box.kef"
                 .format(self.path)),
                shell=True,
                stdout=subprocess.PIPE)
            process.wait()
            new_kef = []
            with open("experiment_t_bounding_box.kef") as f:
                kef = f.readlines()
            for line in kef:
                if line.startswith("	north_west_corner/X/value_d="):
                    new_kef.append("	north_west_corner/X/value_d=" +
                                   str(min_lon) + "\n")
                elif line.startswith("	north_west_corner/Y/value_d="):
                    new_kef.append("	north_west_corner/Y/value_d=" +
                                   str(max_lat) + "\n")
                elif line.startswith("	south_east_corner/X/value_d="):
                    new_kef.append("	south_east_corner/X/value_d=" +
                                   str(max_lon) + "\n")
                elif line.startswith("	south_east_corner/Y/value_d"):
                    new_kef.append("	south_east_corner/Y/value_d=" +
                                   str(min_lat) + "\n")
                else:
                    new_kef.append(line)
            outfile = open("experiment_t_bounding_box.kef", 'w')
            for line in new_kef:
                outfile.write("%s" % line)
        return

    def checK_stations(self):
        LOGGER.info("Checking Stations...")
        array_names = sorted(self.ph5.Array_t_names)
        for array_name in array_names:
            self.read_arrays(array_name)
            arraybyid = self.ph5.Array_t[array_name]['byid']
            arrayorder = self.ph5.Array_t[array_name]['order']
            for ph5_station in arrayorder:
                station_list = arraybyid.get(ph5_station)
                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        station_id = station_list[deployment][
                            st_num]['id_s']
                        serial = station_list[deployment][
                            st_num]['das/serial_number_s']
                        channel = station_list[deployment][
                            st_num]['channel_number_i']
                        LOGGER.info("##############")
                        LOGGER.info("Station {0} Channel {1}"
                                    .format(str(station_id),
                                            str(channel)))
                        try:
                            if not (0 <= int(station_list[deployment]
                                             [st_num]['id_s']) <= 65535):
                                LOGGER.error("Station ID not "
                                             "between 0 and 65535")
                        except ValueError:
                            LOGGER.error("Station ID not a whole "
                                         "number between 0 "
                                         "and 65535 ")

                        if not (1 <= len(station_list[deployment][st_num][
                                             'seed_station_name_s']) <= 5):
                            LOGGER.error("SEED station name not "
                                         "between 1 and 5 characters.")

                        if not station_list[deployment][
                                st_num]['seed_station_name_s']:
                            LOGGER.error("SEED station name required.")

                        if not station_list[deployment][
                                st_num]['seed_band_code_s']:
                            LOGGER.error("SEED band code required. ")

                        if not station_list[deployment][
                                st_num]['seed_instrument_code_s']:
                            LOGGER.error("SEED instrument code required.")

                        if not station_list[deployment][
                                st_num]['seed_orientation_code_s']:
                            LOGGER.error("SEED orientation code "
                                         "required.")

                        response_t = self.ph5.get_response_t_by_n_i(
                            station_list[deployment][st_num][
                                'response_table_n_i'])
                        if response_t is None:
                            LOGGER.error("No Response table found. "
                                         "Have you run load_resp yet?")

                        deploy_time = station_list[deployment][
                                st_num]['deploy_time/epoch_l']
                        pickup_time = station_list[deployment][
                                st_num]['pickup_time/epoch_l']

                        if deploy_time > pickup_time:
                            LOGGER .error("Deploy time is after pickup time")
                        else:
                            self.ph5.read_das_t(serial, pickup_time,
                                                deploy_time, reread=False)

                        if serial not in self.ph5.Das_t:
                            LOGGER .error("No data found for station {0}. "
                                          "You may need to reload the raw "
                                          "data for this station."
                                          .format(str(station_id)))
                        try:
                            ph5api.filter_das_t(self.ph5.Das_t[
                                                serial]['rows'],
                                                channel)
                        except BaseException:
                            LOGGER .error("No data found for channel {0}. "
                                          "Other channels seem to exist"
                                          .format(str(channel)))

                        if station_list[deployment][st_num][
                                'location/X/value_d'] == 0:
                            LOGGER.warning("Location/X/value_d "
                                           "'longitude'seems to be 0. "
                                           "Is this correct???")

                        if station_list[deployment][st_num][
                                'location/Y/value_d'] == 0:
                            LOGGER.warning("Location/Y/value_d "
                                           "'latitude' seems to be 0. "
                                           "Is this correct???")

                        if station_list[deployment][st_num][
                                'sample_rate_i'] == 0:
                            LOGGER.warning("Sample rate seems to be 0. "
                                           "Is this correct???")

                        if station_list[deployment][st_num][
                                'sample_rate_multiplier_i'] == 0:
                            LOGGER.warning("Sample rate multiplier 0. "
                                           "Is this correct???")

                        if not station_list[deployment][st_num][
                                'das/manufacturer_s']:
                            LOGGER.warning("DAS manufacturer is missing. "
                                           "Is this correct???")

                        if not station_list[deployment][st_num][
                                'das/model_s']:
                            LOGGER.warning("DAS model is missing. "
                                           "Is this correct???")
                        if not station_list[deployment][st_num][
                                'sensor/manufacturer_s']:
                            LOGGER.warning("Sensor manufacturer is "
                                           "missing. Is this correct???")

                        if not station_list[deployment][st_num][
                                'sensor/model_s']:
                            LOGGER.warning("Sensor model is missing. "
                                           "Is this correct???")


def get_args():
    parser = argparse.ArgumentParser(
        description='Runs set of checks on PH5 archvive',
        usage='Version: {0} ph5validate--nickname="Master_PH5_file" [options]'
        .format(PROG_VERSION))

    parser.add_argument(
        "-n", "--nickname", action="store", required=True,
        type=str, metavar="nickname")

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    parser.add_argument(
        "-l", "--level", action="store", default="error",
        type=str, metavar="level")

    the_args = parser.parse_args()
    return the_args


def main():
    args = get_args()
    ph5API_object = ph5api.PH5(path=args.ph5path, nickname=args.nickname,)
    ph5validate = PH5Validate(ph5API_object, args.ph5path, level=args.level)
    ph5validate.check_experiment_t()
    ph5validate.checK_stations()
    ph5API_object.close()
    LOGGER.info("\nWarnings, Errors and suggests written to logfile: "
                "PH5Validate.log\n\n")


if __name__ == '__main__':
    main()
