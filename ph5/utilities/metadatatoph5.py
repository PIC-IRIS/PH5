"""
Reads in metadata
and writes it to PH5
"""

import argparse
import os
import re
import sys
import logging
from ph5 import LOGGING_FORMAT
from ph5.utilities import initialize_ph5
from ph5.core import timedoy, kefx, experiment, columns
from ph5.core.ph5utils import PH5ResponseManager
from obspy.core.inventory.inventory import read_inventory as reader
from obspy.io.stationxml.core import _is_stationxml
from obspy.io.xseed.core import _is_seed
from obspy.io.stationtxt.core import is_fdsn_station_text_file
from obspy.core.inventory import Inventory, Network
from obspy import UTCDateTime
from obspy.core.util import AttribDict
import pickle

PROG_VERSION = "2024.227"
LOGGER = logging.getLogger(__name__)
DEPRECATION_WARNING = (
    'metadatatoph5 is no longer supported by the PH5 software. '
    'Please use different functions to format data as PH5.\n\n'
    'To force running the command anyway, please use flag --force\n\n')


def is_ph5_array_csv(fh):
    """
    :type file_handle
    :param fh:
    :return: Boolean
    """
    fh.seek(0, 0)
    line1 = False
    line2 = False
    length = kefx.file_len(fh)
    if length < 2:
        fh.seek(0, 0)
        return False
    head = [next(fh) for x in range(2)]
    for line in head:
        if line[0:5] == "table":
            line1 = True
        if line[0:30] == "/Experiment_g/Sorts_g/Array_t_":
            line2 = True
    if line1 and line2:
        fh.seek(0, 0)
        return True
    fh.seek(0, 0)
    return False


def array_csvtoinventory(fh):
    """
    Takes a ph5 array csv file and converts it
    to an obspy inventory object
    :type file
    :param fh
    :return: :class obspy.core.inventory
    """
    net = [Network('XX')]
    net[0].extra = AttribDict({"channel_num": 1})
    created = UTCDateTime.now()
    csv_inventory = Inventory(networks=net, source="",
                              sender="", created=created,
                              module="", module_uri="")
    return csv_inventory


class MetadatatoPH5Error(Exception):
    """Exception raised when there is a problem with the request.
    :param: message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class MetadatatoPH5(object):

    def __init__(self, ph5_object):
        """
        :type class: ph5.core.experiment
        :param ph5API_object:
        """
        self.ph5 = ph5_object
        self.resp_manager = PH5ResponseManager()
        self.response_t = list()

    def read_metadata(self, file_handle, file_name):
        """
        :type file
        :param file_handle:
        :type str
        :param file_name:
        :return: :class obspy.core.inventory
        """

        if file_handle.closed:
            LOGGER.error("File handle is closed")
            return None

        # check if dataless or stationxml
        if _is_stationxml(file_handle):
            inventory = reader(file_handle, format='STATIONXML')
            LOGGER.info("File "+file_name+" is STATIONXML...")

        elif _is_seed(file_handle):
            inventory = reader(file_handle, format='SEED')
            LOGGER.info("File "+file_name+" is dataless SEED...")

        elif is_fdsn_station_text_file(file_handle):
            inventory = reader(file_handle, format='STATIONTXT')
            LOGGER.info("File "+file_name+" is FDSN TXT...")

        elif kefx.is_array_kef(file_handle):
            LOGGER.info("File "+file_name+" is Array KEF...")
            inventory = []

        elif is_ph5_array_csv(file_handle):
            inventory = array_csvtoinventory(file_handle)
            LOGGER.info("File "+file_name+" is Array csv...")

        else:
            LOGGER.info("Unknown file type: "+file_name)
            inventory = None

        return inventory

    def parse_inventory(self, inventory):
        """
        :type inventory: class: obspy.core.inventory.inventory.Inventory
        :param inventory:
        :return: list of dictionaries containing array data to write to PH5
        """
        array_list = []
        for network in inventory:
            for station in network:

                array_station = {}
                array_station['seed_station_name_s'] = station.code.encode(
                    'ascii', 'ignore')
                array_station['id_s'] = station.code.encode('ascii',
                                                            'ignore')
                LOGGER.info('*****************')
                LOGGER.info('Found station {0}'.format(station.code))
                for channel in station:
                    LOGGER.info('Found channel {0}'.format(channel.code))
                    array_channel = {}
                    if channel.start_date:
                        array_channel['deploy_time/ascii_s'] = (
                            channel.start_date.isoformat())
                        time = timedoy.fdsn2epoch(
                            channel.start_date.isoformat(), fepoch=True)
                        microsecond = (time % 1) * 1000000
                        array_channel['deploy_time/epoch_l'] = (int(time))
                        array_channel['deploy_time/micro_seconds_i'] = (
                            microsecond)
                    else:
                        array_channel['deploy_time/ascii_s'] = ""
                        array_channel['deploy_time/epoch_l'] = ""
                        array_channel['deploy_time/micro_seconds_i'] = ""
                    array_channel['deploy_time/type_s'] = "BOTH"

                    if channel.end_date:
                        array_channel['pickup_time/ascii_s'] = (
                            channel.end_date.isoformat())
                        time = timedoy.fdsn2epoch(
                            channel.end_date.isoformat(), fepoch=True)
                        microsecond = (time % 1) * 1000000
                        array_channel['pickup_time/epoch_l'] = (int(time))
                        array_channel['pickup_time/micro_seconds_i'] = (
                            microsecond)
                    else:
                        array_channel['pickup_time/ascii_s'] = ""
                        array_channel['pickup_time/epoch_l'] = ""
                        array_channel['pickup_time/micro_seconds_i'] = ""
                    array_channel['pickup_time/type_s'] = "BOTH"

                    channel_list = list(channel.code)
                    array_channel['seed_band_code_s'] = (
                        channel_list[0].encode('ascii', 'ignore'))
                    array_channel['seed_instrument_code_s'] = (
                        channel_list[1].encode('ascii', 'ignore'))
                    array_channel['seed_orientation_code_s'] = (
                        channel_list[2].encode('ascii', 'ignore'))

                    if array_channel['seed_orientation_code_s'] in (
                            {'3', 'Z', 'z'}):
                        array_channel['channel_number_i'] = 3
                    elif array_channel['seed_orientation_code_s'] in (
                            {'2', 'E', 'e'}):
                        array_channel['channel_number_i'] = 2
                    elif array_channel['seed_orientation_code_s'] in (
                            {'1', 'N', 'n'}):
                        array_channel['channel_number_i'] = 1
                    elif array_channel['seed_orientation_code_s'].isdigit():
                        array_channel['channel_number_i'] = array_channel
                        ['seed_orientation_code_s']
                    elif channel.code == 'LOG':
                        array_channel['channel_number_i'] = -2
                    else:
                        array_channel['channel_number_i'] = -5

                    array_channel['seed_location_code_s'] = (
                        channel.location_code)

                    if channel.sample_rate >= 1 or channel.sample_rate == 0:
                        array_channel['sample_rate_i'] = channel.sample_rate
                        array_channel['sample_rate_multiplier_i'] = 1
                    else:
                        array_channel['sample_rate_i'] = 1
                        array_channel['sample_rate_multiplier_i'] = (
                                1/channel.sample_rate)
                    if channel.longitude != 0.0:
                        array_channel['location/X/value_d'] = channel.longitude
                        array_channel['location/X/units_s'] = "degrees"
                        array_channel['location/Y/value_d'] = channel.latitude
                        array_channel['location/Y/units_s'] = "degrees"
                        array_channel['location/Z/value_d'] = channel.elevation
                        array_channel['location/Z/units_s'] = "m"
                    else:
                        array_channel['location/X/value_d'] = station.longitude
                        array_channel['location/X/units_s'] = "degrees"
                        array_channel['location/Y/value_d'] = station.latitude
                        array_channel['location/Y/units_s'] = "degrees"
                        array_channel['location/Z/value_d'] = station.elevation
                        array_channel['location/Z/units_s'] = "m"
                    if channel.sensor:
                        array_channel['sensor/model_s'] = str(
                            channel.sensor.type)
                        array_channel['sensor/manufacturer_s'] = str((
                            channel.sensor.manufacturer))
                        array_channel['sensor/serial_number_s'] = str((
                            channel.sensor.serial_number))
                        array_channel['sensor/notes_s'] = str((
                            channel.sensor.description))
                    else:
                        array_channel['sensor/model_s'] = ""
                        array_channel['sensor/manufacturer_s'] = ""
                        array_channel['sensor/serial_number_s'] = ""
                        array_channel['sensor/notes_s'] = ""

                    if channel.data_logger:
                        array_channel['das/model_s'] = str(
                            channel.data_logger.type)
                        array_channel['das/manufacturer_s'] = str((
                            channel.data_logger.manufacturer))
                        array_channel['das/serial_number_s'] = str((
                            channel.data_logger.serial_number))
                        if not channel.data_logger.serial_number:
                            LOGGER.error(
                                "Datalogger serial required for Station {0} "
                                "before data "
                                "can be loaded".format(
                                    array_station['seed_station_name_s']))
                        array_channel['das/notes_s'] = str((
                            channel.data_logger.description))
                    else:
                        array_channel['das/model_s'] = ""
                        array_channel['das/manufacturer_s'] = ""
                        array_channel['das/serial_number_s'] = ""
                        array_channel['das/notes_s'] = ""
                        LOGGER.error(
                            "Datalogger serial required for Station {0} "
                            "Channel {1} before data can be loaded".format(
                                array_station['seed_station_name_s'],
                                channel.code))
                    if hasattr(channel, 'response'):
                        if hasattr(channel.response, 'response_stages'):
                            if len(channel.response.response_stages) > 0:

                                LOGGER.info('Response found for station {0} '
                                            'channel {1}'.format(station.code,
                                                                 channel.code)
                                            )
                                array_channel['response_table_n_i'] = (
                                    self.load_response(array_channel,
                                                       channel, station.code))
                            else:
                                array_channel['response_table_n_i'] = -1
                                response_t = {}
                                response_t['n_i'] = -1
                                self.response_t.append(response_t)
                    else:
                        array_channel['response_table_n_i'] = -1
                        response_t = {}
                        response_t['n_i'] = -1
                        self.response_t.append(response_t)

                    # Select receiver table n_i
                    if channel.azimuth == 0.0 and channel.dip == 90.0:
                        array_channel['receiver_table_n_i'] = 0

                    elif channel.azimuth == 0.0 and channel.dip == 0:
                        array_channel['receiver_table_n_i'] = 1

                    elif channel.azimuth == 90.0 and channel.dip == 0:
                        array_channel['receiver_table_n_i'] = 2

                    elif channel.azimuth == 0.0 and channel.dip == -90.0:
                        array_channel['receiver_table_n_i'] = 3
                    elif channel.code == 'LOG':
                        # new receiver table entry
                        array_channel['receiver_table_n_i'] = 1
                    else:
                        array_channel['receiver_table_n_i'] = -1

                    array_dict = array_station.copy()
                    array_dict.update(array_channel)

                    array_list.append(array_dict)
                    LOGGER.info("Loaded channel {0}".format(channel.code))
                LOGGER.info("Loaded Station {0}".format(station.code))
                LOGGER.info("******************\n")

        return array_list

    def load_response(self, array_channel, channel, station_code):

        sensor_keys = [array_channel['sensor/manufacturer_s'],
                       array_channel['sensor/model_s']]
        datalogger_keys = [array_channel['das/manufacturer_s'],
                           array_channel['das/model_s'],
                           channel.sample_rate]

        # check for response table and any entries already in it
        response_t = {}
        response_are = re.compile(r"\W*")
        responses, blah = self.ph5.ph5_g_responses.read_responses()

        # check response table already in PH5
        n_i = -1
        for response in responses:
            if response['n_i'] >= n_i:
                n_i = response['n_i']
        n_i = n_i

        # Only load if not in response manager
        if not self.resp_manager.is_already_requested(sensor_keys,
                                                      datalogger_keys,
                                                      channel.response):

            LOGGER.info("Loading response for "
                        ""
                        "{0} {1}".format(station_code, channel.code))
            if channel.data_logger:
                try:
                    name = (array_channel['das/model_s'] + "_" +
                            array_channel['sensor/model_s']+"_"+str(int(
                                channel.sample_rate))+channel.code).replace(
                        " ", "").encode('ascii', 'ignore')

                    name = name.translate(None, ',/-=.')

                    nodes = experiment.get_nodes_by_name(
                        self.ph5.ph5,
                        '/Experiment_g/Responses_g/',
                        response_are, None)

                    if name not in nodes.keys():
                        for response in self.response_t:
                            if response['n_i'] >= n_i:
                                n_i = response['n_i']
                        n_i = n_i + 1
                        response_t['n_i'] = n_i

                        # doesn't exist, so create and load data
                        self.ph5.ph5.create_array(
                                self.ph5.ph5.root.Experiment_g.Responses_g,
                                name,
                                pickle.dumps(channel.response))
                        self.resp_manager.add_response(sensor_keys,
                                                       datalogger_keys,
                                                       channel.response,
                                                       n_i)

                        if hasattr(channel.response, 'response_stages'):
                            if len(channel.response.response_stages) > 1:
                                s2 = channel.response.response_stages[1].\
                                    __dict__
                                response_t['gain/value_i'] = \
                                    s2['stage_gain']

                        # response_t['bit_weight/value_d']
                        # response_t['bit_weight/units_s']
                        # response_t['gain/units_s']
                        response_t['response_file_das_a'] = (
                                '/Experiment_g/Responses_g/' + name)
                        self.response_t.append(response_t)
                        LOGGER.info("Response loaded")
                        return n_i
                except MetadatatoPH5Error:
                    Exception("Could not load response into PH5")

            else:
                LOGGER.error("Datalogger required to load response")
        else:
            # response is in PH5, so send that n_i
            LOGGER.info("Response already in PH5")
            return self.resp_manager.get_n_i(sensor_keys, datalogger_keys)

    def toph5(self, parsed_array):
        """
        takes a list of dictionaries containing station metadata
        and loads them in to PH5
        :type list of dictionaries
        :param parsed_array
        :return:

        TODO: Check if data exists in array
        """
        sample_rates = []
        for entry in parsed_array:
            if entry['sample_rate_i'] not in sample_rates:
                sample_rates.append(entry['sample_rate_i'])
        array_count = 1
        # create arrays for each sample rate and assign sample_rate to array
        arrays = {}
        for sample_rate in sample_rates:
            array_name = self.ph5.ph5_g_sorts.nextName()
            self.ph5.ph5_g_sorts.newArraySort(array_name)
            arrays[sample_rate] = array_name
            array_count = array_count + 1

        # iterate through parsed_array and add each entry to the correct
        # array based on it's sample rate
        for entry in parsed_array:
            if entry['sample_rate_i'] in arrays:
                array_name = "/Experiment_g/Sorts_g/"+arrays[
                    entry['sample_rate_i']]
            ref = columns.TABLES[array_name]
            columns.populate(ref, entry, None)

        for entry in self.response_t:
            ref = columns.TABLES['/Experiment_g/Responses_g/Response_t']
            columns.populate(ref, entry, None)

        return True


def get_args(args):
    """
    :return: class: argparse
    """

    parser = argparse.ArgumentParser(
        description='Load metdata in to PH5.',
        usage='Version: {0} metdatatoph5 --nickname="Master_PH5_file"'
              '-f "FILE" [options]\n'
              'IMPORTANT: {1}'.format(PROG_VERSION, DEPRECATION_WARNING))

    parser.add_argument(
        "-n", "--nickname", action="store",
        type=str, metavar="nickname", default="master.ph5", required=True)

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    parser.add_argument(
        "-f", "--file", dest="infile",
        help="Input file containing metadata...stationxml, SEED, Stationtxt",
        metavar="file", required=True)

    parser.add_argument(
        "--force", dest="force_run",
        help="Force to run the command.",
        action="store_true", default=False)

    return parser.parse_args(args)


def main():

    args = get_args(sys.argv[1:])
    if not args.force_run:
        LOGGER.warning(DEPRECATION_WARNING)
        sys.exit()

    if args.nickname[-3:] == 'ph5':
        ph5file = os.path.join(args.ph5path, args.nickname)
    else:
        ph5file = os.path.join(args.ph5path, args.nickname + '.ph5')
        args.nickname += '.ph5'

    PATH = os.path.dirname(args.ph5path) or '.'
    # Debugging
    os.chdir(PATH)
    # Write log to file
    ch = logging.FileHandler(os.path.join(".", "metadatatoph5.log"))
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)

    if not os.path.exists(ph5file):
        LOGGER.warning("{0} not found. Creating...".format(ph5file))
        # Create ph5 file
        ex = experiment.ExperimentGroup(nickname=ph5file,
                                        currentpath=args.ph5path)
        ex.ph5open(True)  # Open ph5 file for editing
        ex.initgroup()
        # Update /Experiment_g/Receivers_g/Receiver_t
        default_receiver_t = initialize_ph5.create_default_receiver_t()
        initialize_ph5.set_receiver_t(default_receiver_t)
        LOGGER.info("Removing temporary {0} kef file."
                    .format(default_receiver_t))
        os.remove(default_receiver_t)
        ex.ph5close()
        LOGGER.info("Done... Created new PH5 file {0}."
                    .format(ph5file))
    ph5_object = experiment.ExperimentGroup(nickname=args.nickname,
                                            currentpath=args.ph5path)
    ph5_object.ph5open(True)
    ph5_object.initgroup()
    metadata = MetadatatoPH5(ph5_object)
    path, file_name = os.path.split(args.infile)
    f = open(args.infile, "r")
    inventory = metadata.read_metadata(f, file_name)
    if inventory:
        parsed_array = metadata.parse_inventory(inventory)
        metadata.toph5(parsed_array)

    ph5_object.ph5close()


if __name__ == '__main__':
    main()
