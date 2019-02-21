"""
Reads in dataless SEED or StationXML
and writes it to PH5
"""

import argparse
import os
import sys
import warnings
import logging
import re
import time
import math
import json
from math import modf
from ph5 import LOGGING_FORMAT
from ph5.core import experiment, timedoy
from ph5.core import ph5api, timedoy

from obspy.io.xseed import Parser
from obspy.core.inventory.inventory import read_inventory as reader
from obspy.io.stationxml.core import _is_stationxml
from obspy.io.xseed.core import _is_seed
from obspy.io.stationtxt.core import is_fdsn_station_text_file

PROG_VERSION = "2019.51"
LOGGER = logging.getLogger(__name__)


class metadatatoph5(object):

    def __init__(self, ph5_object):
        """
        :type ph5_object: class: ph5.core.api
        :param ph5_object: The open PH5 object
        """
        self.ph5 = ph5_object

    def read_metadata(self, file_handle, file_name):

        # check if dataless or stationxml
        if _is_stationxml(file_handle):
            inventory = reader(file_handle, format='STATIONXML')
            LOGGER.info("File "+file_name+" is STATIONXML..."
                                          "read successful")

        elif _is_seed(file_handle):
            inventory = reader(file_handle, format='SEED')
            LOGGER.info("File "+file_name+" is dataless SEED..."
                                          "read successful")

        elif is_fdsn_station_text_file(file_handle):
            inventory = reader(file_handle, format='STATIONTXT')
            LOGGER.info("File "+file_name+" is FDSN TXT..."
                                          "read successful")
        else:
            LOGGER.info("Unknown file type: "+file_name)
            inventory = None

        return inventory

    def parse_inventory(self, inventory):
        """
        :type inventory: class: obspy.core.inventory.inventory.Inventory
        :param inventory:
        :return:

        TODO: channel_number, times epoch only seconds, microsecond
        """
        array_list = []
        array_channel = {}

        for Network in inventory:
            for Station in Network:
                array_channel = {}
                if Station.creation_date:
                    array_channel['deploy_time/ascii_s'] = (
                        Station.creation_date.isoformat())
                    array_channel['deploy_time/epoch_l'] = (
                        timedoy.fdsn2epoch(
                            Station.creation_date.isoformat()))
                else:
                    array_channel['deploy_time/ascii_s'] = ""
                    array_channel['deploy_time/epoch_l'] = ""
                array_channel['deploy_time/type_s'] = "BOTH"
                if Station.termination_date:
                    array_channel['pickup_time/ascii_s'] = (
                        Station.termination_date.isoformat())
                    array_channel['pickup_time/epoch_l'] = (
                        timedoy.fdsn2epoch(
                            Station.termination_date.isoformat()))
                else:
                    array_channel['pickup_time/ascii_s'] = ""
                    array_channel['pickup_time/epoch_l'] = ""
                array_channel['pickup_time/type_s'] = "BOTH"
                array_channel['id_s'] = Station.code.encode('ascii',
                                                            'ignore')

                array_channel['seed_station_name_s'] = Station.code.encode(
                    'ascii', 'ignore')
                channel_num = 0
                for Channel in Station:
                    channel_list = list(Channel.code)
                    array_channel['seed_band_code_s'] = (
                        channel_list[0].encode('ascii', 'ignore'))
                    array_channel['seed_instrument_code_s'] = (
                        channel_list[1].encode('ascii', 'ignore'))
                    array_channel['seed_orientation_code_s'] = (
                        channel_list[2].encode('ascii', 'ignore'))
                    array_channel['seed_location_code_s'] = (
                        Channel.location_code)
                    array_channel['sample_rate_i'] = Channel.sample_rate
                    array_channel['sample_rate_multiplier_i'] = 1
                    array_channel['location/X/value_d'] = Channel.longitude
                    array_channel['location/X/units_s'] = "degrees"
                    array_channel['location/Y/value_d'] = Channel.latitude
                    array_channel['location/Y/units_s'] = "degrees"
                    array_channel['location/Z/value_d'] = Channel.elevation
                    array_channel['location/Z/units_s'] = "m"
                    if Channel.sensor:
                        array_channel['sensor/model_s'] = str(
                            Channel.sensor.type)
                        array_channel['sensor/manufacturer_s'] = str((
                            Channel.sensor.manufacturer))
                        array_channel['sensor/serial_number_s'] = str((
                            Channel.sensor.serial_number))
                        array_channel['sensor/notes_s '] = str((
                            Channel.sensor.description))
                    else:
                        array_channel['sensor/model_s'] = ""
                        array_channel['sensor/manufacturer_s'] = ""
                        array_channel['sensor/serial_number_s'] = ""
                        array_channel['sensor/notes_s '] = ""

                    if Channel.data_logger:
                        array_channel['das/model_s'] = str(
                            Channel.data_logger.type)
                        array_channel['das/manufacturer_s'] = str((
                            Channel.data_logger.manufacturer))
                        array_channel['das/serial_number_s'] = str((
                            Channel.data_logger.serial_number))
                        array_channel['das/notes_s'] = str((
                            Channel.data_logger.description))
                    else:
                        array_channel['das/model_s'] = ""
                        array_channel['das/manufacturer_s'] = ""
                        array_channel['das/serial_number_s'] = ""
                        array_channel['das/notes_s'] = ""

                    print array_channel


def get_args():

    parser = argparse.ArgumentParser(
        description='Load metdata in to PH5.',
        usage='Version: {0} metdatatoph5 --nickname="Master_PH5_file"'
              '-f "FILE" [options]'
        .format(PROG_VERSION))

    parser.add_argument(
        "-n", "--nickname", action="store",
        type=str, metavar="nickname", default="master.ph5")

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    parser.add_argument(
        "-f", "--file", dest="infile",
        help="Input file containing metadata...stationxml, SEED, Stationtxt",
        metavar="file_list_file")

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
        LOGGER.error("{0} not found.\n".format(ph5file))
        sys.exit(-1)

    ph5API_object = ph5api.PH5(path=args.ph5path, nickname=args.nickname)

    metadata = metadatatoph5(ph5API_object)

    path, file_name = os.path.split(args.infile)
    f = open(args.infile, "r")
    inventory = metadata.read_metadata(f, file_name)
    if inventory:
        metadata.parse_inventory(inventory)

    ph5API_object.close()


if __name__ == '__main__':
    main()
