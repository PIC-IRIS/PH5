"""
Author: Derick Hess
Creates template csv for loading RESPS,
loads the RESP files and create new array and response kefs
"""

import sys
import os
import argparse
import logging
from datetime import datetime

import tables
import collections

from ph5 import LOGGING_FORMAT
from ph5.core import ph5utils, ph5api, columns
from ph5.utilities import tabletokef

PROG_VERSION = "2020.128"
LOGGER = logging.getLogger(__name__)


def write_backup(table, node_path, table_name):
    """
    get table with either type tabletokef.Rows_Keys or dict with keys 'rows'
    and 'keys' to create kef file for backup with format:
      [table_name]_[YYYY][DOY]_XX.kef
      XX is the order to distingushed when the same filename is created
    :param table: data to backup
    :type table: tabletokef.Rows_Keys or dict with keys 'rows' and 'keys'
    :param node_path: the path of the node in ph5 structure
    :type node_path: string
    :table_name: the name of table to be added
    :table_name: string
    """
    today = datetime.now().timetuple()
    tt = "{0:04d}{1:03d}".format(today.tm_year, today.tm_yday)
    prefix = "{0}_{1}".format(table_name, tt)
    backup_filename = "{0}_00.kef".format(prefix)
    # Do not overwite existing file
    i = 1
    while os.path.exists(backup_filename):
        backup_filename = "{0}_{1:02d}.kef".format(prefix, i)
        i += 1
    LOGGER.info("Writing table backup: %s." % backup_filename)
    with open(backup_filename, 'w') as backup_file:
        tabletokef.table_print(node_path, table, backup_file)


def group_list_dict(data, listed_keys):
    """"
    :param data: data to be grouped
    :type data: list of dictionaries
    :param listed_keys: keys that values will turn into lists
    :type listed_keys: a list of strings
    :return: all keys not in listed_keys are group keys, all entries that have
        the same values for group keys will be grouped into one entry with all
        values in each listed_key turned into a unique list under new key:
            a listed_key + 's'
    :ex: data = [{das:rt130, sr:100, srm:1, st_id:1001},
                 {das:rt130, sr:1, srm:1, st_id:1003},
                 {das:rt130, sr:100, srm:1, st_id:1002},
                 {das:rt130, sr:1, srm:1, st_id:1004},]
         listed_keys = [st_id]
         return: [{das:rt130, sr:100, srm:1, st_ids:[1001,1002]},
                  {das:rt130, sr:1, srm:1, st_ids:[1003,1004]}]
    """

    def keyfunc(dict, keys):
        # return a tuple of values of keys from dict
        ret = []
        for k in keys:
            ret.append((dict[k]))
        return tuple(ret)

    if data == []:
        LOGGER.error("No Data.")
        return []
    # group_keys: all keys that aren't listed_keys
    group_keys = []
    for key in data[0].keys():
        if key not in listed_keys:
            group_keys.append(key)
    grouped = collections.defaultdict(list)
    for item in data:
        grouped[keyfunc(item, group_keys)].append(item)
    group_data = []
    for key, group in grouped.items():
        data_item = {key: group[0][key] for key in group_keys}
        for key in listed_keys:
            data_item[key + 's'] = []
            for g_item in group:
                if g_item[key] not in data_item[key + 's']:
                    data_item[key + 's'].append(g_item[key])
        group_data.append(data_item)
    return group_data


class Station(object):

    def __init__(
            self,
            id_s,
            station,
            channel,
            sample_rate,
            sample_rate_multiplier,
            das_model,
            sensor_model,
            gain,
            response_n_i,
            receiver_n_i,
            bit_weight,
            bit_weight_units,
            gain_units,
            serial):
        self.id_s = id_s
        self.station_entry = station  # ref to update array's entry
        self.channel = channel
        self.sample_rate = sample_rate
        self.sample_rate_multiplier = sample_rate_multiplier
        self.das_model = das_model
        self.sensor_model = sensor_model
        self.gain = gain
        self.response_n_i = response_n_i
        self.receiver_n_i = receiver_n_i
        self.bit_weight = bit_weight
        self.bit_weight_units = bit_weight_units
        self.gain_units = gain_units
        self.response_file_das_a = None
        self.response_file_sensor_a = None
        self.serial = serial


class n_i_fix(object):

    def __init__(self, ph5API_object, reload_resp_data, skip_update_resp,
                 array=[]):
        self.ph5 = ph5API_object
        self.array = array
        self.reload_resp_data = reload_resp_data
        self.skip_update_resp = skip_update_resp
        if not self.ph5.Array_t_names:
            self.ph5.read_array_t_names()

    def read_arrays(self, name):
        if name is None:
            for n in self.ph5.Array_t_names:
                self.ph5.read_array_t(n)
        else:
            self.ph5.read_array_t(name)

    def create_list(self):
        array_names = sorted(self.ph5.Array_t_names)
        stations = []
        for array_name in array_names:
            if self.array:
                array = str(int(array_name[-3:]))
                array_patterns = self.array
                if not ph5utils.does_pattern_exists(
                        array_patterns, str(array)):
                    continue

            self.read_arrays(array_name)
            arraybyid = self.ph5.Array_t[array_name]['byid']
            arrayorder = self.ph5.Array_t[array_name]['order']

            for ph5_station in arrayorder:
                station_list = arraybyid.get(ph5_station)
                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        station = station_list[deployment][st_num]
                        id_s = station_list[deployment][st_num]['id_s']
                        sample_rate = station_list[deployment][
                            st_num]['sample_rate_i']
                        sample_rate_multiplier = station_list[deployment][
                            st_num]['sample_rate_multiplier_i']
                        das_model = station_list[deployment][
                            st_num]['das/model_s']
                        das_model = das_model.replace(" ", "")
                        if das_model.strip() == "":
                            LOGGER.error(
                                "No Das model for array %s, station %s" %
                                (array, id_s))
                        sensor_model = station_list[deployment][
                            st_num]['sensor/model_s']
                        sensor_model = sensor_model.replace(" ", "")
                        if das_model.startswith("ZLAND"):
                            sensor_model = ""
                        elif sensor_model.strip() == "":
                            LOGGER.error(
                                "No Sensor model for array %s, station %s" %
                                (array, id_s))
                        channel = station_list[deployment][
                            st_num]['channel_number_i']
                        serial = station_list[deployment][
                            st_num]['das/serial_number_s']
                        pickup = station_list[deployment][
                            st_num]['pickup_time/epoch_l']
                        deploy = station_list[deployment][
                            st_num]['deploy_time/epoch_l']

                        self.ph5.read_das_t(
                            serial, deploy, pickup, reread=False)
                        try:
                            Das_t = ph5api.filter_das_t(
                                self.ph5.Das_t[serial]['rows'], channel)
                        except BaseException:
                            LOGGER.warning(
                                "No DAS table found for das {0} channel "
                                "{1}.\n".format(serial, channel))
                            break
                        for entry in Das_t:
                            if (entry['sample_rate_i'] == sample_rate and
                                    entry['sample_rate_multiplier_i']
                                    == sample_rate_multiplier and entry[
                                        'channel_number_i'] == channel):
                                response_n_i = entry['response_table_n_i']
                                receiver_n_i = entry['receiver_table_n_i']
                                break
                        if channel == -2:
                            # in metadata
                            # channel=-2 for no resp => n_i=-1
                            response_n_i = -1
                        Response_t = self.ph5.get_response_t_by_n_i(
                            response_n_i)
                        if Response_t:
                            gain = Response_t['gain/value_i']
                            bit_weight = Response_t['bit_weight/value_d']
                            bit_weight_units = Response_t['bit_weight/units_s']
                            gain_units = Response_t['gain/units_s']
                        else:
                            LOGGER.warning(
                                "No Response table found for das {0} channel "
                                "{1}.\n".format(serial, channel))
                        try:
                            stations.append(
                                Station(
                                    id_s,
                                    station,
                                    channel,
                                    sample_rate,
                                    sample_rate_multiplier,
                                    das_model.strip(),
                                    sensor_model.strip(),
                                    gain,
                                    response_n_i,
                                    receiver_n_i,
                                    bit_weight,
                                    bit_weight_units,
                                    gain_units,
                                    serial))
                        except BaseException:
                            LOGGER.error("Couldn't add station.")
                            continue
        return stations

    def create_template(self, data):
        data_list = []
        unique_list_complete = []
        for station in data:
            data_list.append([str(station.das_model),
                              str(station.sensor_model),
                              str(station.sample_rate),
                              str(station.sample_rate_multiplier),
                              str(station.gain),
                              "",
                              ""])
        unique_list = [list(x) for x in set(tuple(x) for x in data_list)]
        for x in unique_list:
            unique_list_complete.append(x)
        outfile = open("input.csv", 'w')
        outfile.write(
            "Das Model, Sensor Model, Sample Rate, sample rate multiplier,"
            "Gain, Das RESP path, Sensor RESP path\n")
        for x in unique_list_complete:
            line = ",".join(x)
            outfile.write(line + "\n")
        LOGGER.info("input.csv written. This is a template.\nYou will "
                    "need to fill out the full path to each RESP file "
                    "in the CSV file then re-run this program with the "
                    "-i input.csv option")

    def read_respdata(self, resp_filename):
        """
        :param resp_filename: name of a response file
        :return: List of lines read from the file
            or None with warning if cannot read
        """
        data = None
        try:
            with open(resp_filename, "r") as f:
                data = f.readlines()
        except IOError:
            LOGGER.warning("%s not exist." % resp_filename)
            return None
        if data is None:
            LOGGER.warning("Could not read %s." % resp_filename)
        return data

    def load_respdata(self, ph5, name, data, checked_list, first_load=True):
        """
        Receive:
          :param ph5: table ph5
          :param name: name of response file in ph5
              ie. rt130_100_1_1 (das), Hyperion (sensor), etc.
          :param checked_list: list to track which response_files have been
              checked for loading data
          :param first_load:
               + first_load=True is when trying to load response data
                 the first time => create new node with the given data
               + first_load=False is when the first try is failed and reload
                 response data flag (-r) is set
                 => remove node before recreating the node with new data
        """
        if name not in checked_list:
            checked_list.append(name)
        try:
            if not first_load:
                ph5.remove_node(ph5.root.Experiment_g.Responses_g, name)
            ph5.create_array(ph5.root.Experiment_g.Responses_g, name, data)
            if first_load:
                LOGGER.info("Loaded {0}".format(name))
            else:
                LOGGER.info("Reloaded {0}.".format(name))
        except tables.NodeError as e:
            if "already has a child" not in str(e):
                LOGGER.warning("Could not load {0} due to error: {1}".format(
                    name, str(e)))
            else:
                if self.reload_resp_data:
                    # -r flag
                    self.load_respdata(
                        ph5, name, data, checked_list, first_load=False)
                else:
                    LOGGER.warning(
                        "{0} has been loaded in another resp_load run."
                        .format(name.replace(" ", "")))

    def get_resp_file_names(self, x):
        """
        return full path response file names for das and sensor
        return False when requirement for models not met
        """
        if x['d_model']:
            full_das_name = '/Experiment_g/Responses_g/%s_%s_%s_%s' % (
                x['d_model'].replace(" ", "").translate(None, ',-=.'),
                x['s_rate'], x['s_rate_m'], x['gain'])
        else:
            return False

        if x['s_model']:
            full_sens_name = '/Experiment_g/Responses_g/' + x[
                's_model'].replace(" ", "").translate(None, ',-=.')

        elif x['d_model'].startswith('ZLAND'):
            full_sens_name = ''
        else:
            return False
        return full_das_name, full_sens_name

    def check_metadata_format(self, response_entry, x):
        """
        :param response_entry: an entry in response table
        :type response_entry: dictionary
        :param x: an entry of unique_list in load_response()
        :type x: dictionary
        :return: True if x['d_model'] match and
                    response_entry['response_file_das_a'] is in metadata format
                 Otherwise, return False
        """
        if not response_entry['response_file_das_a']:
            # no das response file
            return False

        das_name_parts = response_entry['response_file_das_a'].replace(
            '/Experiment_g/Responses_g/', '').split('_')
        if das_name_parts[0] != x['d_model']:
            # das model from x not match with das model from file name
            return False
        if not das_name_parts[1].isdigit():
            # format created by resp_load: [dasmodel_sr_srm_g]
            # format created by metadata: [dasmodel_sensmodel_sr_chancode]
            return True
        return False

    def update_array(self, x, new_n_i):
        """
        update all entries in x['station_entrys'] with new_n_i
        """
        for s_entry in x['station_entrys']:
            s_entry['response_table_n_i'] = new_n_i

    def check_filenames(self, x, all_resp, response_entry, filenames):
        """
        :param x: an entry of unique list in load_response()
        :param all_resp: dict created from Response_t[rows] with keys are n_i
        :param response_entry: a response entry with n_i from Das_t
        :param filenames: (response_file_das_a, response_file_sensor_a) from
                          x's info
        :return:
            x[n_i]: If filenames with response_entry match
            n_i: If filenames match with response_entry got from n_i in array_t
            None: Otherwise
        """
        # check response_entry with n_i das_t n_i
        if (filenames[0] == response_entry['response_file_das_a'] and
                filenames[1] == response_entry['response_file_sensor_a']):
            return x['n_i']
        # n_i from das_t won't be changed,
        # check once more with n_i from array_t
        # (need if run resp_load multiple times)
        n_i = x['station_entrys'][0]['response_table_n_i']
        response_entry = all_resp[n_i]
        if (filenames[0] == response_entry['response_file_das_a'] and
                filenames[1] == response_entry['response_file_sensor_a']):
            return n_i
        return None

    def load_response(self, backup_path, array_data, input_csv):
        """
        Receive:
          :param backup_path: path for backup file
          :param array_data: list of station based data
          :param input_csv: csv file that provide response file names for the
           associated das/sensor model, samplerate, samplerate multiplier, gain
        Process:
          + Read response files from input.csv to load response data into ph5
          + Create backup for Response_t and array_t(s) and delete them the
             tables in ph5 structure
          + From array_data, get a unique list that group same sensor model,
            das model, sample rate, sample rate multiplier, gain, bitweight and
            n_i with all station entries of those will be turned into a list
            Go through the unique list use n_i to get response entry, check if:
             . match with response file names in entry: update n_i of station
                entries in list
             . response entry has no response files filled: fill response file
                names, and update n_i of station entries in list
             . otherwise, create new response entry increase 1 from max n_i,
                update n_i of station entries in list
          + populate response table and array table with updated response
            entries and array entries
        """
        # use this instead of open ph5 file as table
        ph5table = self.ph5.ph5

        # load response files from the paths in input.csv
        # U in the mode so that \r will be considered as next line
        with open(input_csv, "rU") as f:
            csv = f.readlines()
        loaded_das = []
        loaded_sensor = []
        for line in csv:
            line_list = line.split(",")
            if line_list[0] == 'Das Model':
                continue
            else:
                if line_list[5] != "":
                    name = str(
                        line_list[0] +
                        "_" +
                        line_list[2] +
                        "_" +
                        line_list[3] +
                        "_" +
                        line_list[4])
                    name = name.replace(" ", "").translate(None, ',-=.')
                    if name not in loaded_das:
                        das_data = self.read_respdata(line_list[5].rstrip())
                        if das_data is not None:
                            self.load_respdata(
                                ph5table, name, das_data, loaded_das)

                if len(line_list) >= 6:
                    if line_list[6] == '\n':
                        continue
                    if line_list[1] not in loaded_sensor:
                        sensor_data = self.read_respdata(line_list[6].rstrip())
                        if sensor_data is not None:
                            name = line_list[1].replace(" ", "")
                            name = name.translate(None, ',-=.')
                            self.load_respdata(
                                ph5table, name, sensor_data, loaded_sensor)

        if self.skip_update_resp:
            # -s flag
            LOGGER.info("Skip updating response index in response_t "
                        "and array_t.")
            return

        # assign global variables in tabletokef
        tabletokef.EX = self.ph5
        tabletokef.TABLE_KEY = None
        tabletokef.PATH = backup_path
        tabletokef.ARRAY_T = {}
        if not self.ph5.Response_t:
            self.ph5.read_response_t()
        response_t = tabletokef.Rows_Keys(self.ph5.Response_t['rows'],
                                          self.ph5.Response_t['keys'])
        # backup and delete response_t
        write_backup(response_t,
                     '/Experiment_g/Responses_g/Response_t',
                     'Response_t')
        self.ph5.ph5_g_responses.nuke_response_t()

        # backup and delete array_t(s)
        tabletokef.read_sort_table()
        tabletokef.read_sort_arrays()
        for a in self.array:
            array_name = 'Array_t_%03d' % int(a)
            if array_name in tabletokef.ARRAY_T.keys():
                write_backup(tabletokef.ARRAY_T[array_name],
                             '/Experiment_g/Sorts_g/%s' % array_name,
                             array_name)
                self.ph5.ph5_g_sorts.nuke_array_t(int(a))

        unique_list = []
        for station in array_data:
            if station.receiver_n_i not in [None, '']:
                station.station_entry[
                    'receiver_table_n_i'] = station.receiver_n_i
            else:
                station.station_entry['receiver_table_n_i'] = 0
            item = {'d_model': station.das_model,
                    's_model': station.sensor_model,
                    's_rate': str(station.sample_rate),
                    's_rate_m': str(station.sample_rate_multiplier),
                    'gain': str(station.gain),
                    'gain_u': station.gain_units,
                    'bit_w': str(station.bit_weight),
                    'bit_w_u': station.bit_weight_units,
                    'n_i': station.response_n_i,
                    'station_entry': station.station_entry}
            if item not in unique_list:
                unique_list.append(item)

        unique_list = group_list_dict(unique_list, ['station_entry'])

        """
        update/add entries in self.ph5.Response_t
        using update_array() to update station entries of the array
        """
        # all_resp: help access response entry through n_i
        all_resp = {item['n_i']: item for item in self.ph5.Response_t['rows']}
        # max_n_i: used for new response entry added
        max_n_i = max(all_resp.keys())
        for x in unique_list:
            if x['n_i'] == -1:
                # no response signal
                continue
            response_entry = all_resp[x['n_i']]
            if self.check_metadata_format(response_entry, x):
                # x match with entry created by metadata
                continue
            filenames = self.get_resp_file_names(x)
            if not filenames:
                continue
            das_resp_name, sen_resp_name = filenames
            if response_entry['response_file_das_a'] == '':
                # n_i haven't been used, use it
                response_entry['response_file_das_a'] = das_resp_name
                response_entry['response_file_sensor_a'] = sen_resp_name
                self.update_array(x, x['n_i'])
                continue

            n_i = self.check_filenames(x, all_resp, response_entry, filenames)
            if n_i is not None:
                # match with n_i created by another resp_load run
                self.update_array(x, n_i)
                continue

            # n_i already used, need new entry
            new_response_entry = {}
            max_n_i += 1
            new_response_entry['n_i'] = max_n_i
            new_response_entry['bit_weight/value_d'] = x['bit_w']
            new_response_entry['bit_weight/units_s'] = x['bit_w_u']
            new_response_entry['gain/value_i'] = x['gain']
            new_response_entry['gain/units_s'] = x['gain_u']
            new_response_entry['response_file_das_a'] = das_resp_name
            new_response_entry['response_file_sensor_a'] = sen_resp_name
            new_response_entry['response_file_a'] = ''
            self.ph5.Response_t['rows'].append(new_response_entry)
            self.update_array(x, max_n_i)
            LOGGER.info("%s-%s-%s-%s: n_i %s=>%s" %
                        (x['s_model'], x['d_model'], x['s_rate'],
                         x['s_rate_m'], x['n_i'], max_n_i))

        # populate response_t with updated entries in self.ph5.Response_t
        for entry in self.ph5.Response_t['rows']:
            ref = columns.TABLES['/Experiment_g/Responses_g/Response_t']
            columns.populate(ref, entry, None)

        LOGGER.info("Update Response_t.")

        # populate array_t(s) with updated station entries
        for a in self.array:
            array_name = 'Array_t_%03d' % int(a)
            try:
                arraybyid = self.ph5.Array_t[array_name]['byid']
                arrayorder = self.ph5.Array_t[array_name]['order']
            except KeyError:
                LOGGER.warning("%s not in ph5." % array_name)
                continue
            ref = self.ph5.ph5_g_sorts.newArraySort(array_name)
            for ph5_station in arrayorder:
                station_list = arraybyid.get(ph5_station)
                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        station = station_list[deployment][st_num]
                        columns.populate(ref, station)
            LOGGER.info("Update %s." % array_name)


def get_args():
    parser = argparse.ArgumentParser(
        description=("This fixes then n_i numbers in the arrays, creates "
                     "new array.kef files, loads RESP files into PH5 and "
                     "creates a new 'response.kef'."),
        usage=('Version: {0} resp_load  --nickname="Master_PH5_file [options]'
               .format(PROG_VERSION)))

    parser.add_argument(
        "-n", "--nickname", action="store", required=True,
        type=str, metavar="nickname")

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    parser.add_argument(
        "-a", "--array", action="store",
        help="Comma separated list of arrays to update",
        type=str, dest="array", metavar="array")

    parser.add_argument(
        "-i",
        "--input_csv",
        action="store",
        help=("input csv. If no input is given a template will be created "
              "for you based on the experiment."),
        type=str,
        dest="input_csv",
        metavar="input_csv",
        default=None)

    parser.add_argument(
        "-r",
        "--reload",
        action="store_true",
        help=("When need to reload resp data."),
        dest="reload_resp_data",
        default=False)

    parser.add_argument(
        "-s",
        "--skip_update_resp",
        action="store_true",
        help=("Skip updating response's index and file names."),
        dest="skip_update_resp",
        default=False)

    args = parser.parse_args()
    return args


def main():
    args = get_args()

    if args.nickname[-3:] == 'ph5':
        ph5file = os.path.join(args.ph5path, args.nickname)
    else:
        args.nickname = '{0}.ph5'.format(args.nickname)
        ph5file = os.path.join(args.ph5path, args.nickname)

    if not os.path.exists(ph5file):
        LOGGER.warning("{0} not found.\n".format(ph5file))
        sys.exit(-1)
    else:
        # Set up logging
        # Write log to file
        ch = logging.FileHandler(os.path.join('.', "resp_load.log"))
        ch.setLevel(logging.INFO)
        # Add formatter
        formatter = logging.Formatter(LOGGING_FORMAT)
        ch.setFormatter(formatter)
        LOGGER.addHandler(ch)

    if args.array:
        args.array = args.array.split(',')

    ph5API_object = ph5api.PH5(path=args.ph5path,
                               nickname=args.nickname,
                               editmode=True)

    fix_n_i = n_i_fix(ph5API_object,
                      args.reload_resp_data,
                      args.skip_update_resp,
                      args.array)

    data = fix_n_i.create_list()

    if args.input_csv is None:
        fix_n_i.create_template(data)
    else:
        fix_n_i.load_response(args.ph5path, data, args.input_csv)
    ph5API_object.close()


if __name__ == '__main__':
    main()
