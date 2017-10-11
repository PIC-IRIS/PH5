"""
Author: Derick Hess
Creates template csv for loading RESPS,
loads the RESP files and create new array and response kefs
"""

import sys
import os
from ph5.core import ph5utils
from ph5.core import ph5api
import tables
import subprocess
import logging

logging.basicConfig(filename='resp_load.log', level=logging.DEBUG)
logging.info("###################################################\n\n")
PROG_VERSION = "2017.284"


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
            gain_units):
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


class n_i_fix(object):

    def __init__(self, ph5API_object, array=[]):
        self.ph5 = ph5API_object
        self.array = array

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
                        id_s = station_list[deployment][st_num]['id_s']
                        sample_rate = station_list[deployment][
                            st_num]['sample_rate_i']
                        sample_rate_multiplier = station_list[deployment][
                            st_num]['sample_rate_multiplier_i']
                        das_model = station_list[deployment][
                            st_num]['das/model_s']
                        das_model = das_model.replace(" ", "")
                        sensor_model = station_list[deployment][
                            st_num]['sensor/model_s']
                        sensor_model = sensor_model.replace(" ", "")
                        if das_model.startswith("ZLAND"):
                            sensor_model = ""
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
                            logging.warning(
                                "No DAS table found for das " +
                                str(serial) +
                                " channel " +
                                str(channel) +
                                ".\n")
                            sys.stderr.write(
                                "Error - No DAS table found for das " +
                                str(serial) +
                                " channel " +
                                str(channel) +
                                ".\n")

                        response_n_i = Das_t[0]['response_table_n_i']
                        receiver_n_i = Das_t[0]['receiver_table_n_i']
                        Response_t = self.ph5.get_response_t(Das_t)
                        if Response_t:
                            gain = Response_t['gain/value_i']
                            bit_weight = Response_t['bit_weight/value_d']
                            bit_weight_units = Response_t['bit_weight/units_s']
                            gain_units = Response_t['gain/units_s']
                        else:
                            logging.warning(
                                "No Response table found for das " +
                                str(serial) +
                                " channel " +
                                str(channel) +
                                ".\n")
                            sys.stderr.write(
                                "Error - No Response table found for das " +
                                str(serial) +
                                " channel " +
                                str(channel) +
                                ".\n")

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
                                gain_units))
        return stations

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
                                station.channel) == channel and int(x) == int(
                                station.array):
                            if station.response_n_i:
                                new_kef.append(
                                    "        response_table_n_i=" +
                                    str(station.response_n_i) + '\n')
                                break
                            else:
                                new_kef.append("        response_table_n_i=\n")
                                break
                else:
                    new_kef.append(line)
            outfile = open("array_t_" + str(x) + ".kef", 'w')
            for line in new_kef:
                outfile.write("%s" % line)
            logging.info(
                "array_t_" +
                str(x) +
                ".kef written. You will need to nuke_table the" +
                "old kef and use keftoph5 to load the new one.")
            sys.stdout.write(
                "array_t_" +
                str(x) +
                ".kef written. You will need to nuke_table the old kef" +
                "and use keftoph5 to load the new one.\n\n")

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
            if float(x[2])/float(x[3]) >= 1.0:
                unique_list_complete.append(x)
        outfile = open("input.csv", 'w')
        outfile.write(
            "Das Model, Sensor Model, Sample Rate, sample rate multiplier," +
            "Gain, Das RESP path, Sensor RESP path\n")
        for x in unique_list_complete:
            line = ",".join(x)
            outfile.write(line + "\n")
        logging.info("input.csv written. This is a template.\nYou will " +
                     "need to fill out the full path to each RESP file " +
                     "in the CSV file then re-run this progam with the " +
                     "-i input.csv option")
        sys.stdout.write(
            "input.csv written. This is a template.\n You will need to fill" +
            "out the full path to each RESP file in the CSV file then re-run" +
            "this progam with the -i input.csv option\n\n")

    def load_response(self, path, nickname, data, input_csv):
        ph5 = tables.open_file(os.path.join(path, nickname), "a")

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
                if line_list[5] is not "":
                    name = str(
                        line_list[0] +
                        "_" +
                        line_list[2] +
                        "_" +
                        line_list[3] +
                        "_" +
                        line_list[4])
                    if name not in loaded_das:
                        with open(line_list[5].rstrip(), "r") as f:
                            das_data = f.readlines()
                        f.close()
                        try:
                            ph5.create_array(
                                ph5.root.Experiment_g.Responses_g,
                                name.replace(
                                    " ", ""), das_data)
                            loaded_das.append(name)
                            sys.stdout.write(
                                "loaded " +
                                name.replace(
                                    " ",
                                    "") +
                                "\n")
                        except BaseException:
                            logging.warning(
                                "Could not load " +
                                name.replace(
                                    " ",
                                    ""))
                            sys.stderr.write(
                                "Could not load " +
                                name.replace(
                                    " ",
                                    "") +
                                "\n")

                if len(line_list) >= 6:
                    if line_list[6] == '\n':
                        continue
                    if line_list[1] not in loaded_sensor:
                        with open(line_list[6].rstrip(), "r") as f:
                            sensor_data = f.readlines()
                        f.close()
                        try:
                            ph5.create_array(
                                ph5.root.Experiment_g.Responses_g,
                                line_list[1].replace(
                                    " ", ""), sensor_data)
                            loaded_sensor.append(line_list[1])
                            sys.stdout.write(
                                "loaded " +
                                line_list[1].replace(
                                    " ",
                                    "") +
                                "\n")
                        except BaseException:
                            logging.warning(
                                "Could not load " +
                                line_list[1].replace(
                                    " ",
                                    ""))
                            sys.stderr.write(
                                "Could not load " +
                                line_list[1].replace(
                                    " ",
                                    "") +
                                "\n")

        ph5.close()

        process = subprocess.Popen(
            "ph5tokef -n " +
            nickname +
            " -p " +
            str(path) +
            " -R  > response_t.kef",
            shell=True,
            stdout=subprocess.PIPE)
        process.wait()
        process = subprocess.Popen(
            "nuke_table -n " +
            nickname +
            " -p " +
            str(path) +
            " -R ",
            shell=True,
            stdout=subprocess.PIPE)
        process.wait()
        process = subprocess.Popen(
            "keftoph5 -n " +
            nickname +
            " -p " +
            str(path) +
            " -k response_t.kef",
            shell=True,
            stdout=subprocess.PIPE)
        process.wait()
        process = subprocess.Popen(
            "ph5tokef -n " +
            nickname +
            " -p " +
            str(path) +
            " -R  > response_t.kef",
            shell=True,
            stdout=subprocess.PIPE)
        process.wait()

        data_list = []
        data_update = []
        for station in data:
            data_list.append([str(station.das_model),
                              str(station.sensor_model),
                              str(station.sample_rate),
                              str(station.sample_rate_multiplier),
                              str(station.gain),
                              str(station.bit_weight),
                              str(station.bit_weight_units),
                              str(station.gain_units)])
        unique_list = [list(x) for x in set(tuple(x) for x in data_list)]
        new_kef = []
        n_i = 0
        for x in unique_list:
            true_sr = float(x[2]) / float(x[3])
            if true_sr >= float(1.0):
                new_kef.append('#   Table Row ' + str(n_i) + '\n')
                new_kef.append('/Experiment_g/Responses_g/Response_t\n')
                new_kef.append('        n_i=' + str(n_i) + '\n')
                new_kef.append('        bit_weight/value_d=' +
                               str(x[5]) + '\n')
                new_kef.append('        bit_weight/units_s=' +
                               str(x[6]) + '\n')
                new_kef.append('        gain/units_s=' + str(x[7]) + '\n')
                new_kef.append('        gain/value_i=' + str(x[4]) + '\n')
                new_kef.append('        response_file_a=' + '\n')
                if x[0]:
                    name = str(x[0]) + "_" + str(x[2]) + "_" + \
                        str(x[3]) + "_" + str(x[4])
                    new_kef.append(
                        '        response_file_das_a=/Experiment_g/' +
                        'Responses_g/' +
                        name.replace(
                            " ",
                            "") +
                        '\n')
                else:
                    new_kef.append('        response_file_das_a=\n')
                if x[1]:
                    new_kef.append(
                        '        response_file_sensor_a=/Experiment_g/' +
                        'Responses_g/' + x[1] + '\n')
                else:
                    new_kef.append('        response_file_sensor_a=\n')

                data_update.append([x[0], x[1], x[2], x[3], x[4], n_i])
                n_i = n_i + 1

        outfile = open("response_t.kef", 'w')
        for line in new_kef:
            outfile.write("%s" % line)
        logging.info(
            "response_t.kef written. You will need to nuke_table the old" +
            " kef and use keftoph5 to load the new one.")
        sys.stdout.write(
            "response_t.kef written. You will need to nuke_table the old" +
            " kef and use keftoph5 to load the new one.\n\n")

        for station in data:
            for x in data_update:
                if station.das_model == x[0] and str(
                    station.sensor_model) == x[1] and int(
                    station.sample_rate) == int(
                    x[2]) and int(
                    station.sample_rate_multiplier) == int(
                    x[3]) and int(
                    station.gain) == int(
                        x[4]):
                    station.response_n_i = x[5]
            true_sr = float(station.sample_rate) / \
                float(station.sample_rate_multiplier)
            if true_sr < 1.0:
                station.response_n_i = None

        return data


def get_args():

    import argparse

    parser = argparse.ArgumentParser(
        description='This fixes then n_i numbers in the arrays, creates ' +
        'new array.kef files, loads RESP files into PH5 and creates ' +
        'a new response.kef',
        usage='Version: {0} resp_load  --nickname="Master_PH5_file" [options]'
        .format(PROG_VERSION))

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
        help="input csv. If no input is given a template will be created " +
        "for you based on the experiment.",
        type=str,
        dest="input_csv",
        metavar="input_csv",
        default=None)

    the_args = parser.parse_args()
    return the_args


def main():

    args = get_args()

    if args.nickname[-3:] == 'ph5':
        ph5file = os.path.join(args.ph5path, args.nickname)
    else:
        ph5file = os.path.join(args.ph5path, args.nickname + '.ph5')
        args.nickname += '.ph5'

    if not os.path.exists(ph5file):
        logging.warning("{0} not found.\n".format(ph5file))
        sys.stderr.write("Error - {0} not found.\n".format(ph5file))
        sys.exit(-1)

    if args.array:
        args.array = args.array.split(',')

    ph5API_object = ph5api.PH5(path=args.ph5path, nickname=args.nickname)

    fix_n_i = n_i_fix(ph5API_object, args.array)

    data = fix_n_i.create_list()

    ph5API_object.close()

    if args.input_csv is None:
        fix_n_i.create_template(data)
    else:
        new_data = fix_n_i.load_response(
            args.ph5path, args.nickname, data, args.input_csv)

        fix_n_i.update_kefs(args.ph5path, args.array, new_data)


if __name__ == '__main__':
    main()
