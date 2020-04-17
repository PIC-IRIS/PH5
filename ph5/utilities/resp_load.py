
"""
Author: Derick Hess
Creates template csv for loading RESPS,
loads the RESP files and create new array and response kefs
"""

import sys
import os
import argparse
from ph5 import LOGGING_FORMAT
from ph5.core import ph5utils, ph5api, experiment, columns
import tables
import subprocess
import logging


PROG_VERSION = "2018.268"
LOGGER = logging.getLogger(__name__)


class Station(object):

    def __init__(
            self,
            id_s,
            array,
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
        self.array = array
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

    def __init__(self, ph5API_object, reload_resp, skip_response_t, array=[]):
        self.ph5 = ph5API_object
        self.array = array
        self.reload_resp = reload_resp
        self.skip_response_t = skip_response_t

        if not self.ph5.Array_t_names:
            self.ph5.read_array_t_names()
        if not self.ph5.Response_t:
            self.ph5.read_response_t()

        self.loaded_resp = []
        self.noloaded_resp = []
        self.last_loaded_n_i = -1
        for entry in self.ph5.Response_t['rows']:
            if entry['response_file_das_a'] or entry['response_file_sensor_a']:
                if not entry['response_file_das_a']:
                    LOGGER.warning("Response_t n_i=%s resonse_file_das_a has "
                                   "been deleted mannually." % entry['n_i'])
                if (('ZLAND' not in entry['response_file_das_a']) and
                        (not entry['response_file_sensor_a'])):
                    LOGGER.warning("Response_t n_i=%s resonse_file_sensor_a "
                                   "has been deleted mannually."
                                   % entry['n_i'])
                self.loaded_resp.append(entry)
            else:
                self.noloaded_resp.append(entry)
            if self.last_loaded_n_i < entry['n_i']:
                self.last_loaded_n_i = entry['n_i']

    def read_arrays(self, name):
        if name is None:
            for n in self.ph5.Array_t_names:
                self.ph5.read_array_t(n)
        else:
            self.ph5.read_array_t(name)

    def create_list(self):
        """
        create the list of stations from input array list with additional info
        from das_t and response_t to help load_response() in creating new
        n_i(s).
        The list with new n_i to is also be used to update array_t so its order
        need to be the same with the original array_t's.
        Process:
          + Read each row from array_t
          + Using that info to read das_t for response_table_n_i
          + Pass info from array_t and das_t to get_response_t() to identify
            the corresponding response_t's row and the info about if response
            file names has been loaded to response_t
        Return:
          A list of all the collected info wrapped in Station instances
        """
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
                        id_s = station['id_s']
                        sample_rate = station['sample_rate_i']
                        sample_rate_multiplier = station[
                            'sample_rate_multiplier_i']
                        das_model = station['das/model_s']
                        das_model = das_model.replace(" ", "")
                        sensor_model = station['sensor/model_s']
                        sensor_model = sensor_model.replace(" ", "")
                        if das_model.startswith("ZLAND"):
                            sensor_model = ""
                        channel = station['channel_number_i']
                        serial = station['das/serial_number_s']
                        pickup = station['pickup_time/epoch_l']
                        deploy = station['deploy_time/epoch_l']
                        a_response_n_i = station['response_table_n_i']

                        # give warning when das_model="" or sensor_model=""
                        # if das_model is not ZLAND to notice user that this
                        # station's response_table_n_i will not be updated
                        if das_model == "":
                            LOGGER.warning(
                                "Das Model is empty for %s station %s das %s "
                                "channel %s => no response_table_n_i updated" %
                                (array_name, id_s, serial, channel))
                        if ((not das_model.startswith("ZLAND"))
                           and sensor_model == ""):
                            LOGGER.warning(
                                "Sensor  is empty for %s station %s das %s "
                                "channel %s => no response_table_n_i updated" %
                                (array_name, id_s, serial, channel))

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

                        d_response_n_i = None
                        for entry in Das_t:
                            if (entry['sample_rate_i'] == sample_rate and
                                    entry['sample_rate_multiplier_i']
                                    == sample_rate_multiplier and entry[
                                        'channel_number_i'] == channel):
                                d_response_n_i = entry['response_table_n_i']
                                receiver_n_i = entry['receiver_table_n_i']
                                break
                        if d_response_n_i is None:
                            LOGGER.warning(
                                "No DAS table found for das {0} chan {1} - "
                                "spr {3} - msrpr {4}.\n".format(
                                    serial, channel, sample_rate,
                                    sample_rate_multiplier))
                            continue
                        try:
                            Response_t, resp_loaded = \
                                self.get_response_t(
                                    das_model, sensor_model, sample_rate,
                                    sample_rate_multiplier,
                                    d_response_n_i, a_response_n_i)
                        except AttributeError as e:
                            LOGGER.error(
                                "Error when processing array {0} "
                                "station{1} chan{2} spr{3} mspr{4}:{5}".
                                format(array_name, id_s, channel, sample_rate,
                                    sample_rate_multiplier, str(e)))
                            continue

                        response_n_i = None
                        if Response_t is not None:
                            gain = Response_t['gain/value_i']
                            bit_weight = Response_t['bit_weight/value_d']
                            bit_weight_units = Response_t['bit_weight/units_s']
                            gain_units = Response_t['gain/units_s']
                            if resp_loaded:
                                response_n_i = Response_t['n_i']
                        else:
                            LOGGER.warning(
                                "No Response table found for das {0} channel "
                                "{1}.\n".format(serial, channel))

                        self.ph5.forget_das_t(serial)
                        try:
                            stations.append(
                                Station(
                                    id_s,
                                    array,
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

    def get_response_t(self, d_model, s_model, s_rate, s_rate_m, d_n_i, a_n_i):
        """
        Receive:
          :para d_model: das_model from array_t
          :para s_model: sensor_model from array_t
          :para s_rate: sample_rate_i from array_t
          :para s_rate_m: sample_rate_multiplier_i from array_t
          :para n_i: response_table_n_i from das_t based on das info in array_t
        Process:
          + Look in noloaded_resp for row to return if can't find in
            loaded_resp and bit_weight, gain according to n_i
          + Use passed info and found (bit_weight, gain) to look for match row
            in loaded_resp
        Return:
          => loaded_resp row and resp_loaded=True if found in loaded_resp
          => noloaded_resp row and resp_loaded=False otherwise.
        """
        d_filename = "/Experiment_g/Responses_g/%s_%s_%s_" % \
            (d_model.replace(" ", ""), s_rate, s_rate_m)
        s_filename = "/Experiment_g/Responses_g/%s" % s_model.replace(" ", "")

        resp = None
        for response_t in self.noloaded_resp:
            if response_t['n_i'] == d_n_i:
                # Look for the matched n_i from original rows to get
                # bit_weight and gain to form response_file_das_a
                # for the condition when look in the loadeded_resp.
                # resp is is the row to return at the end when can't find
                # a match row in loaded_resp
                resp = response_t
                bit_weight = str(response_t['bit_weight/value_d'])
                gain = str(response_t['gain/value_i'])

        for response_t in self.loaded_resp:
            if response_t['n_i'] != a_n_i:
                continue
            b = str(response_t['bit_weight/value_d'])
            g = str(response_t['gain/value_i'])
            if b != bit_weight or g != gain:
                continue

            if response_t['response_file_das_a'] == d_filename + str(g):
                if response_t['response_file_sensor_a'] == s_filename:
                    return response_t, True
                elif response_t['response_file_sensor_a'] == '':
                    return response_t, True
        return resp, False

    def update_kefs(self, path, arrays, data):
        for x in arrays:
            process = subprocess.Popen(
                "ph5tokef -n master.ph5 -p " +
                str(path) +
                " -A " +
                str(x) +
                " > array_t_" +
                str(x) +
                ".kef",
                shell=True,
                stdout=subprocess.PIPE)
            process.wait()
        for x in arrays:
            process = subprocess.Popen(
                "nuke_table -n master.ph5 -p " +
                str(path) +
                " -A " +
                str(x),
                shell=True,
                stdout=subprocess.PIPE)
            process.wait()
        for x in arrays:
            process = subprocess.Popen(
                "keftoph5 -n master.ph5 -p " +
                str(path) +
                " -k array_t_" +
                str(x) +
                ".kef",
                shell=True,
                stdout=subprocess.PIPE)
            process.wait()
        for x in arrays:
            process = subprocess.Popen(
                "ph5tokef -n master.ph5 -p " +
                str(path) +
                " -A " +
                str(x) +
                " > array_t_" +
                str(x) +
                ".kef",
                shell=True,
                stdout=subprocess.PIPE)
            process.wait()

        for x in arrays:
            new_kef = []
            id_s = None
            channel = None
            with open("array_t_" + str(x) + ".kef") as f:
                kef = f.readlines()
            for line in kef:
                if line.startswith("	id_s="):
                    id_s = int(line[6:])
                    new_kef.append(line)
                elif line.startswith("	channel_number_i="):
                    channel = int(line[18:])
                    new_kef.append(line)

                elif "response_table_n_i=" in line:

                    for station in data:

                        if int(
                                station.id_s) == id_s and int(
                            station.channel) == channel and int(x) ==\
                                int(station.array):
                            if station.response_n_i:
                                new_kef.append(
                                    "        response_table_n_i=" +
                                    str(station.response_n_i) + '\n')
                                break
                            else:
                                new_kef.append(
                                    "        response_table_n_i=0\n")
                                break
                elif "receiver_table_n_i=" in line:

                    for station in data:

                        if int(
                                station.id_s) == id_s and int(
                            station.channel) == channel and int(x) ==\
                                int(station.array):
                            if station.receiver_n_i:
                                new_kef.append(
                                    "        receiver_table_n_i=" +
                                    str(station.receiver_n_i) + '\n')
                                break
                            else:
                                new_kef.append(
                                    "        receiver_table_n_i=0\n")
                                break
                else:
                    new_kef.append(line)
            outfile = open("array_t_" + str(x) + ".kef", 'w')
            file_name = "array_t_" + str(x) + ".kef"
            for line in new_kef:
                outfile.write("%s" % line)
            outfile.close()
            command = "nuke_table -n master.ph5 -p {0} -A {1}".format(
                path, str(x))
            subprocess.call(command, shell=True)
            import time
            time.sleep(1)
            command = "keftoph5 -n master.ph5 -p {1} -k {0}".format(
                file_name, path)
            subprocess.call(command, shell=True)
            time.sleep(0.5)
            LOGGER.info("array_t_{0} Loaded into PH5".format(str(x)))

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
        Receive:
          :para resp_filename: name of a response file
        Return
          List of lines read from the file
          If cannot read, return None with warning
        """
        data = None
        with open(resp_filename, "r") as f:
            data = f.readlines()
        if data is None:
            LOGGER.warning("Could not read {0}.".format(resp_filename))
        return data

    def load_respdata(self, ph5, name, data, loaded_list, first_load=True):
        """
        Receive:
          :para ph5: table ph5
          :para name: name of response file in ph5
              ie. rt130_100_1_1, Hyperion, etc.
          :para loaded_list: list to track which response_files have been
              loaded
          :para first_load:
               + first_load=True is when trying to load response data
                 the first time => create new node with the given dataanyway
               + first_load=False is when the first try is failed and reload
                 response flag (-r) is set, then load_respdata() is recalled
                 => remove node before recreating the node with new data
        """
        try:
            if not first_load:
                ph5.remove_node(ph5.root.Experiment_g.Responses_g, name)
            ph5.create_array(ph5.root.Experiment_g.Responses_g, name, data)
            loaded_list.append(name)
            if first_load:
                LOGGER.info("Loaded {0}".format(name))
            else:
                LOGGER.info("Reload {0}.".format(name))
        except Exception as e:
            if "already has a child" not in str(e):
                LOGGER.warning("Could not load {0}".format(name))
            else:
                if self.reload_resp:
                    self.load_respdata(
                        ph5, name, data, loaded_list, first_load=False)
                else:
                    LOGGER.warning(
                        "{0} has been loaded in another resp_load run."
                        .format(name.replace(" ", "")))

    def load_response(self, path, nickname, data, input_csv):
        """
        Receive:
          :para path: path to ph5 file's directory
          :para nickname: name of ph5 file
          :para data: list of station based rows created by self.create_list()
          :para input_csv: csv file that provide response file names for the
            associated das/sensor models, samplerate, samplerate multiplier,
            gain
        Process:
          + Read response files from input.csv to load response data into ph5
          + From para data, get a unique list of sensor model, das model,
            sample rate, sample rate multiplier, gain, bitweight, resp_loaded
            for n_i condition checking
          + In response_t, all existing are kept, n_i will be created
          corresponding to rows withresp_loaded=False
          + n_i will be updated for the rows in the input array_t
        """
        ph5 = tables.open_file(os.path.join(path, nickname), "a")

        # load response files from the paths in input.csv
        with open(input_csv, "r") as f:
            csv = f.readlines()
        f.close()
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
                    if name not in loaded_das:
                        das_data = self.read_respdata(line_list[5].rstrip())
                        if das_data is not None:
                            name = name.replace(" ", "")
                            name = name.translate(None, ',-=.')
                            self.load_respdata(ph5, name, das_data, loaded_das)

                if len(line_list) >= 6:
                    if line_list[6] == '\n':
                        continue
                    if line_list[1] not in loaded_sensor:
                        sensor_data = self.read_respdata(line_list[6].rstrip())
                        if sensor_data is not None:
                            name = line_list[1].replace(" ", "")
                            name = name.translate(None, ',-=.')
                            self.load_respdata(
                                ph5, name, sensor_data, loaded_sensor)

        ph5.close()
        if self.skip_response_t:
            return

        data_list = []
        data_update = []
        for station in data:
            data_list.append(
                {'d_model': str(station.das_model),
                 's_model': str(station.sensor_model),
                 's_rate': str(station.sample_rate),
                 's_rate_m': str(station.sample_rate_multiplier),
                 'gain': str(station.gain),
                 'bit_w': str(station.bit_weight),
                 'bit_w_u': str(station.bit_weight_units),
                 'gain_u': str(station.gain_units),
                 'n_i': station.response_n_i})

        unique_list = map(dict, set(tuple(sorted(x.items()))
                                    for x in data_list))
        unique_list = sorted(unique_list, key=lambda i:
                             (i['s_model'], i['d_model'], i['s_rate'],
                              i['s_rate_m'], i['gain'], float(i['bit_w'])))

        # ------------ add existing reponse entries to final_ret --------------
        # Keep all rows of the original response_t to keep track with
        # response_table_n_i in das table
        final_ret = self.noloaded_resp
        # add the rows that already has resp files
        final_ret += self.loaded_resp

        # ------------ add new response enstries to final_ret -----------------
        # increase n_i by 1 from the last n_i
        n_i = self.last_loaded_n_i + 1
        for x in unique_list:
            response_entry = {}
            item = [x['d_model'], x['s_model'], x['s_rate'], x['s_rate_m'],
                    x['gain'], x['bit_w']]
            if x['n_i'] is not None:
                data_update.append(item + [x['n_i']])
                continue
            if x['d_model']:
                name = str(x['d_model']) + "_" + str(x['s_rate']) + "_" + \
                    str(x['s_rate_m']) + "_" + str(x['gain'])
                name_full = '/Experiment_g/' +\
                            'Responses_g/' + name.replace(" ", "")
                name_full = name_full.translate(None, ',-=.')

                response_entry['response_file_das_a'] = name_full
            else:
                # skip updating if no d_model
                continue

            if x['s_model']:
                sens = x['s_model']
                sens = sens.translate(None, ',-=.')
                name = '/Experiment_g/' +\
                       'Responses_g/' + sens
                response_entry['response_file_sensor_a'] = name
            elif not x['d_model'].startswith('ZLAND'):
                # Skip updating if no s_model and d_model not ZLAND
                continue
            response_entry['bit_weight/value_d'] = x['bit_w']
            response_entry['bit_weight/units_s'] = x['bit_w_u']
            response_entry['gain/value_i'] = x['gain']
            response_entry['gain/units_s'] = x['gain_u']

            response_entry['n_i'] = n_i
            final_ret.append(response_entry)
            data_update.append(item + [n_i])
            n_i += 1

        # ---------------------- update response_t ----------------------------
        ph5_object = experiment.ExperimentGroup(nickname=nickname,
                                                currentpath=path)
        ph5_object.ph5open(True)
        ph5_object.initgroup()
        # delete response_t
        ph5_object.ph5_g_responses.nuke_response_t()

        # populate response_t with entries from final_ret
        for entry in final_ret:
            ref = columns.TABLES['/Experiment_g/Responses_g/Response_t']
            columns.populate(ref, entry, None)

        ph5_object.ph5close()

        LOGGER.info("response_t.kef written into PH5")

        # --------- update data with new n_i new response_t's entries ---------
        for station in data:
            # don't update station.array if not listed in option -a
            if station.array not in self.array:
                continue
            for x in data_update:
                if str(station.das_model) == x[0] and \
                   str(station.sensor_model) == x[1] and \
                   str(station.sample_rate) == x[2] and \
                   str(station.sample_rate_multiplier) == x[3] and \
                   str(station.gain) == x[4] and \
                   str(station.bit_weight) == x[5]:
                    station.response_n_i = x[6]
                    break
            """
            true_sr =\
                float(station.sample_rate) /\
                float(station.sample_rate_multiplier)
            if true_sr < 1.0:
                station.response_n_i = None
            """

        return data


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
        help=("When need to reload resp files."),
        dest="reload_resp",
        default=False)

    parser.add_argument(
        "-s",
        "--skip_response_t",
        action="store_true",
        help=("Load response data in response_g "
              "but skip updating response_t."),
        dest="skip_response_t",
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

    ph5API_object = ph5api.PH5(path=args.ph5path, nickname=args.nickname)

    fix_n_i = n_i_fix(ph5API_object, args.reload_resp, args.skip_response_t,
                      args.array)

    data = fix_n_i.create_list()

    ph5API_object.close()

    if args.input_csv is None:
        fix_n_i.create_template(data)
    else:
        new_data = fix_n_i.load_response(
            args.ph5path, args.nickname, data, args.input_csv)
        if args.skip_response_t:
            sys.exit()
        import time
        time.sleep(5)
        fix_n_i.update_kefs(args.ph5path, args.array, new_data)


if __name__ == '__main__':
    main()
