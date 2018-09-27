"""
Extracts station metadata from PH5 as StationXML or in other formats.
"""

import sys
import io
import os
import argparse
import fnmatch
import multiprocessing
import logging
import obspy
from datetime import datetime
from obspy import read_inventory  # noqa
from obspy.core.util import AttribDict
from obspy.core import UTCDateTime

from ph5.core import ph5utils, ph5api
from ph5.core.ph5utils import PH5ResponseManager

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser(
            description='Takes PH5 files and returns StationXML.',
            usage=('Version: {0} ph5tostationxml --nickname="Master_PH5_file" '
                   '[options]'.format(PROG_VERSION))
            )
    parser.add_argument("-n", "--nickname", action="store", required=True,
                        type=str, default="master.ph5", metavar="nickname")

    parser.add_argument("-p", "--ph5path", action="store",
                        help=("Comma separated list of paths to ph5 "
                              "experiments."),
                        type=str, metavar="ph5path")

    parser.add_argument("--network", action="store", dest="network_list",
                        help=("Comma separated list of networks. Wildcards "
                              "accepted"),
                        type=str, metavar="network_list")

    parser.add_argument("--reportnum", action="store", dest="reportnum_list",
                        help=("Comma separated list of report numbers. "
                              "Wildcards accepted"),
                        type=str, metavar="reportnum_list")

    parser.add_argument("-o", "--outfile", action="store",
                        default=sys.stdout, type=str, metavar="outfile")

    parser.add_argument("-f", "--format", action="store",
                        default="STATIONXML", dest="out_format",
                        type=str, metavar="out_format",
                        help="Output format: STATIONXML," +
                              "TEXT, SACPZ, or KML")

    parser.add_argument("--array", action="store", dest="array_list",
                        help="Comma separated list of arrays.",
                        type=str, metavar="array_list")

    parser.add_argument("--station", action="store", dest="station_list",
                        help=("Comma separated list of stations. Wildcards "
                              "accepted"),
                        type=str, metavar="station_list")

    parser.add_argument("--receiver", action="store", dest="receiver_list",
                        help=("Comma separated list of receiver id's. "
                              "Wildcards accepted"),
                        type=str, metavar="receiver_list")

    parser.add_argument("-c", "--channel", action="store", dest="channel_list",
                        help=("Comma separated list of channels. "
                              "Wildcards accepted"),
                        type=str, metavar="channel_list")

    parser.add_argument("--component", action="store", dest="component_list",
                        help=("Comma separated list of components. "
                              "Wildcards accepted"),
                        type=str, metavar="component_list")

    parser.add_argument("-l", "--location", action="store",
                        dest="location_list",
                        help=("Comma separated list of locations. "
                              "Wildcards accepted"),
                        type=str, metavar="location_list")

    parser.add_argument("-s", "--starttime", action="store",
                        help=("start time in FDSN time format or PASSCAL "
                              "time format"),
                        type=str, dest="start_time", metavar="start_time")

    parser.add_argument("-t", "--endtime", action="store",
                        help=("stop time in FDSN time format or PASSCAL "
                              "time format"),
                        type=str, dest="end_time", metavar="end_time")

    parser.add_argument("--level", action="store", default="channel",
                        help=("Specify level of detail using network, "
                              "station, channel,or response"),
                        type=str, dest="level", metavar="level")

    parser.add_argument("--minlat", action="store",
                        help=("Limit to stations with a latitude larger than "
                              "or equal to the specified minimum."),
                        type=float, dest="minlat", metavar="minlat")

    parser.add_argument("--maxlat", action="store",
                        help=("Limit to stations with a latitude smaller than "
                              "or equal to the specified maximum."),
                        type=float, dest="maxlat", metavar="maxlat")

    parser.add_argument("--minlon", action="store",
                        help=("Limit to stations with a longitude larger than "
                              "or equal to the specified minimum."),
                        type=float, dest="minlon", metavar="minlon")

    parser.add_argument("--maxlon", action="store",
                        help=("Limit to stations with a longitude smaller "
                              "than or equal to the specified maximum."),
                        type=float, dest="maxlon", metavar="maxlon")

    parser.add_argument("--latitude", action="store",
                        help=("Specify the central latitude point for a "
                              "radial geographic constraint."))

    parser.add_argument("--longitude", action="store",
                        help=("Specify the central longitude point for a "
                              "radial geographic constraint., "))

    parser.add_argument("--minradius", action="store",
                        help=("Specify minimum distance from the geographic "
                              "point defined by latitude and longitude."))

    parser.add_argument("--maxradius", action="store",
                        help=("Specify maximum distance from the geographic "
                              "point defined by latitude and longitude."))

    parser.add_argument("--uri", action="store", default="",
                        type=str, metavar="uri")
    args = parser.parse_args()
    return args


class PH5toStationXMLError(Exception):
    """Exception raised when there is a problem with the request.
    :param: message -- explanation of the error
    """
    def __init__(self, message=""):
        self.message = message


class PH5toStationXMLRequest(object):

    def __init__(self, network_list=None, reportnum_list=None,
                 station_list=None, location_list=None, channel_list=None,
                 component_list=None, receiver_list=None, array_list=None,
                 minlatitude=None, maxlatitude=None, minlongitude=None,
                 maxlongitude=None, latitude=None, longitude=None,
                 minradius=None, maxradius=None, start_time=None,
                 end_time=None):

        self.network_list = network_list
        self.reportnum_list = reportnum_list
        self.station_list = station_list
        self.location_list = location_list
        self.channel_list = channel_list
        self.component_list = component_list
        self.receiver_list = receiver_list
        self.array_list = array_list
        self.minlatitude = minlatitude
        self.maxlatitude = maxlatitude
        self.minlongitude = minlongitude
        self.maxlongitude = maxlongitude
        self.latitude = latitude
        self.longitude = longitude
        self.minradius = minradius
        self.maxradius = maxradius
        self.start_time = start_time
        self.end_time = end_time
        self.ph5_station_id_list = []  # updated by PH5toStationXMLParser

        # assign default values
        if not self.network_list:
            self.network_list = ["*"]
        if not self.reportnum_list:
            self.reportnum_list = ["*"]
        if not self.station_list:
            self.station_list = ["*"]
        if not self.location_list:
            self.location_list = ["*"]
        if not self.channel_list:
            self.channel_list = ["*"]
        if not self.component_list:
            self.component_list = ["*"]
        if not self.receiver_list:
            self.receiver_list = ["*"]
        if not self.array_list:
            self.array_list = ["*"]
        if self.start_time:
            self.start_time = UTCDateTime(start_time)
        if self.end_time:
            self.end_time = UTCDateTime(end_time)


class PH5toStationXMLRequestManager(object):
    """
    Manager for for the list of PH5toStationXMLRequest objects and
    ph5 api instance
    """

    def __init__(self, sta_xml_obj_list, ph5path, nickname, level, format):
        self.request_list = sta_xml_obj_list
        self.ph5 = ph5api.PH5(path=ph5path, nickname=nickname)
        self.iris_custom_ns = "http://www.fdsn.org/xml/station/1/iris"
        self.level = level.upper()
        self.format = format.upper()
        self.nickname = nickname


class PH5toStationXMLParser(object):

    def __init__(self, manager):
        self.manager = manager
        self.resp_manager = PH5ResponseManager()
        self.response_table_n_i = None
        self.receiver_table_n_i = None
        self.total_number_stations = 0

    def is_lat_lon_match(self, sta_xml_obj, latitude, longitude):
        """
        Checks if the given latitude/longitude matches geographic query
        constraints
        :param: latitude : the latitude to check against the arguments
            geographic constraints
        :param: longitude : the longitude to check against the arguments
            geographic constraints
        """
        if not -90 <= float(latitude) <= 90:
            return False
        elif not -180 <= float(longitude) <= 180:
            return False
        # if lat/lon box intersection
        elif not ph5utils.is_rect_intersection(sta_xml_obj.minlatitude,
                                               sta_xml_obj.maxlatitude,
                                               sta_xml_obj.minlongitude,
                                               sta_xml_obj.maxlongitude,
                                               latitude,
                                               longitude):
            return False
        # check if point/radius intersection
        elif not ph5utils.is_radial_intersection(sta_xml_obj.latitude,
                                                 sta_xml_obj.longitude,
                                                 sta_xml_obj.minradius,
                                                 sta_xml_obj.maxradius,
                                                 latitude,
                                                 longitude):
            return False
        else:
            return True

    def create_obs_network(self):
        obs_stations = self.read_stations()
        if obs_stations:
            obs_network = obspy.core.inventory.Network(
                self.experiment_t[0]['net_code_s'])
            obs_network.alternate_code = \
                self.experiment_t[0]['experiment_id_s']
            obs_network.description = self.experiment_t[0]['longname_s']
            start_time, end_time = self.get_network_date()
            obs_network.start_date = UTCDateTime(start_time)
            obs_network.end_date = UTCDateTime(end_time)
            obs_network.total_number_of_stations = self.total_number_stations
            obs_network.stations = obs_stations
            return obs_network
        else:
            return

    def create_obs_station(self, station_list, sta_code, array_name,
                           start_date, end_date, sta_longitude,
                           sta_latitude, sta_elevation, deployment):

        obs_station = obspy.core.inventory.Station(sta_code,
                                                   latitude=sta_latitude,
                                                   longitude=sta_longitude,
                                                   start_date=start_date,
                                                   end_date=end_date,
                                                   elevation=sta_elevation)

        obs_station.creation_date = UTCDateTime(station_list[deployment][0]
                                                ['deploy_time/epoch_l'])
        obs_station.termination_date = UTCDateTime(station_list[deployment][0]
                                                   ['pickup_time/epoch_l'])

        extra = AttribDict({
            'PH5Array': {
                'value': str(array_name)[8:],
                'namespace': self.manager.iris_custom_ns,
                'type': 'attribute'
            }
        })
        obs_station.extra = extra
        obs_station.site = obspy.core.inventory.Site(
            name=station_list[deployment][0]['location/description_s'])
        return obs_station

    def create_obs_channel(self, station_list, deployment, cha_code, loc_code,
                           cha_longitude, cha_latitude, cha_elevation,
                           receiver_id):

        obs_channel = obspy.core.inventory.Channel(
                                                   code=cha_code,
                                                   location_code=loc_code,
                                                   latitude=cha_latitude,
                                                   longitude=cha_longitude,
                                                   elevation=cha_elevation,
                                                   depth=0
                                            )
        obs_channel.start_date = UTCDateTime(station_list[deployment][0]
                                             ['deploy_time/epoch_l'])
        obs_channel.end_date = UTCDateTime(station_list[deployment][0]
                                           ['pickup_time/epoch_l'])

        # compute sample rate
        sample_rate_multiplier = float(station_list[deployment]
                                       [0]['sample_rate_multiplier_i'])
        sample_rate_ration = float(station_list[deployment]
                                   [0]['sample_rate_i'])
        obs_channel.sample_rate_ration = sample_rate_ration
        try:
            obs_channel.sample_rate = sample_rate_ration/sample_rate_multiplier
        except ZeroDivisionError:
            raise PH5toStationXMLError(
                            "Error - Invalid sample_rate_multiplier_i == 0")

        obs_channel.storage_format = "PH5"
        receiver_table_n_i = station_list[deployment][0]['receiver_table_n_i']
        Receiver_t = self.manager.ph5.get_receiver_t_by_n_i(receiver_table_n_i)
        obs_channel.azimuth = Receiver_t['orientation/azimuth/value_f']
        obs_channel.dip = Receiver_t['orientation/dip/value_f']

        sensor_type = " ".join(
                        [x for x in
                         [station_list[deployment][0]['sensor/manufacturer_s'],
                          station_list[deployment][0]['sensor/model_s']] if x])

        obs_channel.sensor = obspy.core.inventory.Equipment(
            type=sensor_type,
            description=("%s %s/%s %s" %
                         (station_list[deployment][0]['sensor/manufacturer_s'],
                          station_list[deployment][0]['sensor/model_s'],
                          station_list[deployment][0]['das/manufacturer_s'],
                          station_list[deployment][0]['das/model_s'])),
            manufacturer=station_list[deployment][0]['sensor/manufacturer_s'],
            vendor="",
            model=station_list[deployment][0]['sensor/model_s'],
            serial_number=station_list[deployment][0]
                                      ['sensor/serial_number_s'],
            installation_date=UTCDateTime(station_list[deployment][0]
                                          ['deploy_time/epoch_l']),
            removal_date=UTCDateTime(station_list[deployment][0]
                                     ['pickup_time/epoch_l']))
        das_type = " ".join([x for x in [station_list[deployment][0]
                                                     ['das/manufacturer_s'],
                                         station_list[deployment][0]
                                                     ['das/model_s']] if x])
        obs_channel.data_logger = \
            obspy.core.inventory.Equipment(
                type=das_type,
                description="",
                manufacturer=station_list[deployment][0]['das/manufacturer_s'],
                vendor="",
                model=station_list[deployment][0]['das/model_s'],
                serial_number=station_list[deployment][0]
                                          ['das/serial_number_s'],
                installation_date=UTCDateTime(
                        station_list[deployment][0]['deploy_time/epoch_l']
                        ),
                removal_date=UTCDateTime(
                        station_list[deployment][0]['pickup_time/epoch_l']
                        )
            )
        extra = AttribDict({
                'PH5Component': {
                    'value': str(station_list[deployment][0]
                                 ['channel_number_i']),
                    'namespace': self.manager.iris_custom_ns,
                    'type': 'attribute'
                },
                'PH5ReceiverId': {
                    'value': str(receiver_id),
                    'namespace': self.manager.iris_custom_ns,
                    'type': 'attribute'
                }
            })
        obs_channel.extra = extra

        if self.manager.level == "RESPONSE" or \
                (self.manager.level == "CHANNEL" and
                 self.manager.format == "TEXT"):
            # read response and add it to obspy channel inventory
            self.response_table_n_i = \
                station_list[deployment][0]['response_table_n_i']
            obs_channel.response = self.get_response_inv(obs_channel)

        return obs_channel

    def get_response_inv(self, obs_channel):

        sensor_keys = [obs_channel.sensor.manufacturer,
                       obs_channel.sensor.model]
        datalogger_keys = [obs_channel.data_logger.manufacturer,
                           obs_channel.data_logger.model,
                           obs_channel.sample_rate]
        if not self.resp_manager.is_already_requested(sensor_keys,
                                                      datalogger_keys):
            self.manager.ph5.read_response_t()
            Response_t = \
                self.manager.ph5.get_response_t_by_n_i(self.response_table_n_i)
            response_file_das_a_name = Response_t.get('response_file_das_a',
                                                      None)
            response_file_sensor_a_name = Response_t.get(
                                                    'response_file_sensor_a',
                                                    None)
            # parse datalogger response
            if response_file_das_a_name:
                response_file_das_a = \
                    self.manager.ph5.ph5_g_responses.get_response(
                                                    response_file_das_a_name
                                            )
                with io.BytesIO(response_file_das_a) as buf:
                    buf.seek(0, 0)
                    dl_resp = obspy.read_inventory(buf, format="RESP")
                dl_resp = dl_resp[0][0][0].response
            # parse sensor response if present
            if response_file_sensor_a_name:
                response_file_sensor_a = \
                    self.manager.ph5.ph5_g_responses.get_response(
                                                response_file_sensor_a_name
                                            )
                with io.BytesIO(response_file_sensor_a) as buf:
                    buf.seek(0, 0)
                    sensor_resp = obspy.read_inventory(buf, format="RESP")
                sensor_resp = sensor_resp[0][0][0].response

            inv_resp = None
            if response_file_das_a_name and response_file_sensor_a_name:
                # both datalogger and sensor response
                dl_resp.response_stages.pop(0)
                dl_resp.response_stages.insert(0,
                                               sensor_resp.response_stages[0])
                dl_resp.recalculate_overall_sensitivity()
                inv_resp = dl_resp
            elif response_file_das_a_name:
                # only datalogger response
                inv_resp = dl_resp
            elif response_file_sensor_a_name:
                # only sensor response
                inv_resp = sensor_resp

            if inv_resp:
                # update response manager and return response
                self.resp_manager.add_response(sensor_keys,
                                               datalogger_keys,
                                               inv_resp)
                return inv_resp
        else:
            return self.resp_manager.get_response(sensor_keys,
                                                  datalogger_keys)

    def read_channels(self, sta_xml_obj, station_list):

        all_channels = []
        cha_list_patterns = sta_xml_obj.channel_list
        component_list_patterns = sta_xml_obj.component_list
        receiver_list_patterns = sta_xml_obj.receiver_list
        location_patterns = sta_xml_obj.location_list
        for deployment in station_list:
            receiver_id = str(station_list[deployment][0]['id_s'])
            if not ph5utils.does_pattern_exists(receiver_list_patterns,
                                                receiver_id):
                continue

            c_id = str(station_list[deployment][0]['channel_number_i'])
            if not ph5utils.does_pattern_exists(component_list_patterns, c_id):
                continue

            seed_channel = \
                station_list[deployment][0]['seed_band_code_s'] + \
                station_list[deployment][0]['seed_instrument_code_s'] + \
                station_list[deployment][0]['seed_orientation_code_s']

            for pattern in cha_list_patterns:
                if fnmatch.fnmatch(seed_channel, pattern):

                    if station_list[deployment][
                            0]['seed_location_code_s']:
                        location = station_list[deployment][
                            0]['seed_location_code_s']
                    else:
                        location = ""

                    if not ph5utils.does_pattern_exists(location_patterns,
                                                        location):
                        continue

                    cha_longitude = \
                        station_list[deployment][0]['location/X/value_d']
                    cha_latitude = \
                        station_list[deployment][0]['location/Y/value_d']
                    cha_elevation = \
                        station_list[deployment][0]['location/Z/value_d']

                    if not self.is_lat_lon_match(sta_xml_obj,
                                                 cha_latitude,
                                                 cha_longitude):
                        continue

                    obs_channel = self.create_obs_channel(station_list,
                                                          deployment,
                                                          seed_channel,
                                                          location,
                                                          cha_longitude,
                                                          cha_latitude,
                                                          cha_elevation,
                                                          receiver_id)
                    if obs_channel not in all_channels:
                        all_channels.append(obs_channel)
        return all_channels

    def read_stations(self):

        all_stations = []
        all_stations_keys = []
        for sta_xml_obj in self.manager.request_list:
            array_patterns = sta_xml_obj.array_list
            for array_name in self.array_names:
                array = array_name[8:]
                if not ph5utils.does_pattern_exists(array_patterns, array):
                    continue

                arraybyid = self.manager.ph5.Array_t[array_name]['byid']
                arraybyid = self.manager.ph5.Array_t[array_name]['byid']
                arrayorder = self.manager.ph5.Array_t[array_name]['order']
                for x in arrayorder:

                    station_list = arraybyid.get(x)
                    obs_channels = []
                    if x not in sta_xml_obj.ph5_station_id_list:
                        continue
                    for deployment in station_list:

                        sta_longitude = station_list[deployment][0][
                            'location/X/value_d']
                        sta_latitude = station_list[deployment][0][
                            'location/Y/value_d']
                        sta_elevation = station_list[deployment][0][
                            'location/Z/value_d']

                        if not self.is_lat_lon_match(sta_xml_obj,
                                                     sta_latitude,
                                                     sta_longitude):
                            continue

                        if station_list[deployment][0]['seed_station_name_s']:
                            station_name = station_list[deployment][0][
                                                        'seed_station_name_s']
                        else:
                            station_name = x

                        start_date = station_list[deployment][0][
                                                        'deploy_time/epoch_l']
                        start_date = UTCDateTime(start_date)
                        end_date = station_list[deployment][0][
                                                        'pickup_time/epoch_l']
                        end_date = UTCDateTime(end_date)
                        if sta_xml_obj.start_time and \
                                sta_xml_obj.start_time > end_date:
                            # chosen start time after pickup
                            continue
                        elif sta_xml_obj.end_time and \
                                sta_xml_obj.end_time < start_date:
                            # chosen end time before pickup
                            continue

                        obs_station = self.create_obs_station(station_list,
                                                              station_name,
                                                              array_name,
                                                              start_date,
                                                              end_date,
                                                              sta_longitude,
                                                              sta_latitude,
                                                              sta_elevation,
                                                              deployment)

                        if self.manager.level.upper() == "RESPONSE" or \
                           self.manager.level.upper() == "CHANNEL" or \
                           sta_xml_obj.location_list != ['*'] or \
                           sta_xml_obj.channel_list != ['*'] or \
                           sta_xml_obj.component_list != ['*'] or \
                           sta_xml_obj.receiver_list != ['*']:
                            obs_channels = self.read_channels(sta_xml_obj,
                                                              station_list)
                            obs_station.channels = obs_channels
                            obs_station.total_number_of_channels = len(
                                station_list)
                            obs_station.selected_number_of_channels = len(
                                obs_channels)
                            if obs_station and \
                                    obs_station.selected_number_of_channels \
                                    == 0:
                                continue
                        else:
                            obs_station.total_number_of_channels = len(
                                station_list)
                            obs_station.selected_number_of_channels = 0
                        hash = "{}.{}.{}.{}.{}.{}.{}".format(
                            obs_station.code,
                            obs_station.latitude,
                            obs_station.longitude,
                            obs_station.start_date,
                            obs_station.end_date,
                            obs_station.elevation,
                            obs_station.extra)
                        if hash not in all_stations_keys:
                            all_stations_keys.append(hash)
                            all_stations.append(obs_station)
        return all_stations

    def read_arrays(self, name):
        if name is None:
            for n in self.manager.ph5.Array_t_names:
                self.manager.ph5.read_array_t(n)
        else:
            self.manager.ph5.read_array_t(name)

    def add_ph5_stationids(self):
        """
        For each PH5toStationXML object in self.manager.request_list add the
        respective ph5 station ids for the requested stations in the object.
        """
        self.manager.ph5.read_array_t_names()
        self.read_arrays(None)
        self.array_names = self.manager.ph5.Array_t_names
        self.array_names.sort()
        for sta_xml_obj in self.manager.request_list:
            for array_name in self.array_names:
                arraybyid = self.manager.ph5.Array_t[array_name]['byid']
                arrayorder = self.manager.ph5.Array_t[array_name]['order']
                for station in arrayorder:
                    station_list = arraybyid.get(station)
                    for deployment in station_list:
                        for sta_pattern in sta_xml_obj.station_list:
                            if not station_list[deployment][0][
                                                'seed_station_name_s'] and \
                                    fnmatch.fnmatch(str(station),
                                                    str(sta_pattern)):
                                # no seed station code defined so compare
                                # against ph5 station-id
                                sta_xml_obj.ph5_station_id_list.extend(
                                                                [station]
                                                            )
                            elif fnmatch.fnmatch((station_list[deployment][0]
                                                  ['seed_station_name_s']),
                                                 sta_pattern):
                                sta_xml_obj.ph5_station_id_list.extend(
                                                                    [station]
                                                                )

            sta_xml_obj.ph5_station_id_list = \
                sorted(set(sta_xml_obj.ph5_station_id_list))
        self.total_number_stations = max([len(sta_xml_obj.ph5_station_id_list)
                                          for sta_xml_obj in
                                          self.manager.request_list])

    def read_networks(self, path):
        self.manager.ph5.read_experiment_t()
        self.experiment_t = self.manager.ph5.Experiment_t['rows']

        # read network codes and compare to network list
        network_patterns = []
        for obj in self.manager.request_list:
            netcode_list = obj.network_list
            network_patterns.extend(netcode_list)
        if not ph5utils.does_pattern_exists(
                                    network_patterns,
                                    self.experiment_t[0]['net_code_s']):
            self.manager.ph5.close()
            return

        # read reportnums and compare to reportnum list
        reportnum_patterns = []
        for obj in self.manager.request_list:
            reportnum_list = obj.reportnum_list
            reportnum_patterns.extend(reportnum_list)
        if not ph5utils.does_pattern_exists(
                                    reportnum_list,
                                    self.experiment_t[0]['experiment_id_s']):
            self.manager.ph5.close()
            return

        # update requests list to include ph5 station ids
        self.add_ph5_stationids()

        obs_network = self.create_obs_network()

        self.manager.ph5.close()

        return obs_network

    def get_network_date(self):
        self.read_arrays(None)
        array_names = self.manager.ph5.Array_t_names
        array_names.sort()
        min_start_time = 7289567999
        max_end_time = 0
        for array_name in array_names:
            arraybyid = self.manager.ph5.Array_t[array_name]['byid']
            arrayorder = self.manager.ph5.Array_t[array_name]['order']

            for station in arrayorder:
                station_list = arraybyid.get(station)
                for deployment in station_list:
                    if float(station_list[deployment][0]
                             ['deploy_time/epoch_l']) < float(min_start_time):
                        min_start_time = float(station_list[deployment][0]
                                               ['deploy_time/epoch_l']
                                               )

                    if float(station_list[deployment][0]
                             ['pickup_time/epoch_l']) > float(max_end_time):
                        max_end_time = float(station_list[deployment][0]
                                             ['pickup_time/epoch_l'])
        return min_start_time, max_end_time

    def trim_to_level(self, network):
        if self.manager.level == "NETWORK":
            network.stations = []
        elif self.manager.level == "STATION":
            # for station level show the selected_number_of_channels element
            for station in network.stations:
                station.selected_number_of_channels = 0
                station.channels = []
        elif self.manager.level == "CHANNEL" and \
                self.manager.format != "TEXT":
            for station in network.stations:
                for channel in station.channels:
                    channel.response = None
        return network

    def get_network(self, path):
        network = self.read_networks(path)
        if network:
            network = self.trim_to_level(network)
            return network
        else:
            return


def execute(path, args_dict_list, nickname, level, out_format, out_q):
    ph5sxml = [PH5toStationXMLRequest(
                            network_list=args_dict.get('network_list'),
                            reportnum_list=args_dict.get('reportnum_list'),
                            station_list=args_dict.get('station_list'),
                            location_list=args_dict.get('location_list'),
                            channel_list=args_dict.get('channel_list'),
                            component_list=args_dict.get('component_list'),
                            receiver_list=args_dict.get('receiver_list'),
                            array_list=args_dict.get('array_list'),
                            minlatitude=args_dict.get('minlat'),
                            maxlatitude=args_dict.get('maxlat'),
                            minlongitude=args_dict.get('minlon'),
                            maxlongitude=args_dict.get('maxlon'),
                            latitude=args_dict.get('latitude'),
                            longitude=args_dict.get('longitude'),
                            maxradius=args_dict.get('maxradius'),
                            minradius=args_dict.get('minradius'),
                            start_time=args_dict.get('start_time'),
                            end_time=args_dict.get('end_time')
                            )
               for args_dict in args_dict_list]

    ph5sxmlmanager = PH5toStationXMLRequestManager(
                                                    sta_xml_obj_list=ph5sxml,
                                                    ph5path=path,
                                                    nickname=nickname,
                                                    level=level,
                                                    format=out_format
                                                  )
    ph5sxmlparser = PH5toStationXMLParser(ph5sxmlmanager)
    out_q.put(ph5sxmlparser.get_network(path))


def run_ph5_to_stationxml(paths, nickname, out_format,
                          level, uri, args_dict_list):
    if paths:
        processes = []
        out_q = multiprocessing.Queue()
        for path in paths:
            p = multiprocessing.Process(target=execute,
                                        args=(path,
                                              args_dict_list,
                                              nickname,
                                              level,
                                              out_format,
                                              out_q)
                                        )
            processes.append(p)
            p.start()

        results = [out_q.get() for proc in processes]

        networks = [n for n in results if n is not None]

        for p in processes:
            p.join()

        if networks:
            inv = obspy.core.inventory.Inventory(
                                        networks=networks,
                                        source="PIC-PH5",
                                        sender="IRIS-PASSCAL-DMC-PH5",
                                        created=datetime.now(),
                                        module=("PH5 WEB SERVICE: metadata "
                                                "| version: 1"),
                                        module_uri=uri)
            return inv
        else:
            return
    else:
        raise PH5toStationXMLError("No PH5 experiments were found "
                                   "under path(s) {0}".format(paths))


def main():
    args = get_args()
    args_dict = vars(args)

    if args_dict.get('network_list'):
        args_dict['network_list'] = \
            [x.strip() for x in args_dict.get('network_list').split(',')]
    if args_dict.get('reportnum_list'):
        args_dict['reportnum_list'] = \
            [x.strip() for x in args_dict.get('reportnum_list').split(',')]
    if args_dict.get('station_list'):
        args_dict['station_list'] = \
            [x.strip() for x in args_dict.get('station_list').split(',')]
    if args_dict.get('receiver_list'):
        args_dict['receiver_list'] = \
            [x.strip() for x in args_dict.get('receiver_list').split(',')]
    if args_dict.get('array_list'):
        args_dict['array_list'] = \
            [x.strip() for x in args_dict.get('array_list').split(',')]
    if args_dict.get('location_list'):
        args_dict['location_list'] = \
            [x.strip() for x in args_dict.get('location_list').split(',')]
    if args_dict.get('channel_list'):
        args_dict['channel_list'] = \
            [x.strip() for x in args_dict.get('channel_list').split(',')]
    if args_dict.get('component_list'):
        args_dict['component_list'] = \
            [x.strip() for x in args_dict.get('component_list').split(',')]
    if args_dict.get('ph5path'):
        args_dict['ph5path'] = args_dict.get('ph5path').split(',')

    nickname, ext = os.path.splitext(args_dict.get('nickname'))
    if ext != 'ph5':
        nickname = nickname + '.ph5'

    try:
        basepaths = args_dict.get('ph5path')
        paths = []
        for basepath in basepaths:
            for dirName, _, fileList in os.walk(basepath):
                for fname in fileList:
                    if fname == nickname:
                        paths.append(dirName)

        args_dict_list = [args_dict]
        out_format = args_dict.get('out_format').upper()
        level = args_dict.get('level').upper()
        uri = args_dict.get('uri')

        inv = run_ph5_to_stationxml(paths,
                                    nickname,
                                    out_format,
                                    level,
                                    uri,
                                    args_dict_list)

        if out_format == "STATIONXML":
            inv.write(args.outfile,
                      format='STATIONXML',
                      nsmap={'iris': "http://www.fdsn.org/xml/station/1/iris"})
        elif out_format == "KML":
            inv.write(args.outfile, format='KML')
        elif out_format == "SACPZ":
            inv.write(args.outfile, format="SACPZ")
        elif out_format == "TEXT":
            inv.write(args.outfile, format="STATIONTXT", level=level)
        else:
            LOGGER.error("Incorrect output format. "
                         "Formats are STATIONXML, KML, SACPZ, and TEXT.")
            sys.exit()
    except Exception as err:
        LOGGER.error(err.message)


if __name__ == '__main__':
    main()
