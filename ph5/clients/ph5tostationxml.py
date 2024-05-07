"""
Extracts station metadata from PH5 as StationXML or in other formats.
"""

import sys
import io
import os
import argparse
import fnmatch

import logging
import pickle

from obspy.core import inventory
from obspy import read_inventory  # NOQA
from obspy.core.util import AttribDict
from obspy.core import UTCDateTime
from obspy.core.inventory.response import Response
from obspy.io.xseed.core import _is_resp

from ph5.core import ph5utils, ph5api
from ph5.core.ph5utils import PH5ResponseManager
from ph5.utilities import validation

PROG_VERSION = '2021.47'
LOGGER = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser(
            description='Takes PH5 files and returns StationXML.',
            usage=('Version: {0} ph5tostationxml --nickname="Master_PH5_file" '
                   '[options]'.format(PROG_VERSION))
            )
    parser.add_argument("-n", "--nickname", action="store", required=True,
                        type=str, default="master.ph5", metavar="nickname")

    parser.add_argument("-p", "--ph5path", action="store", default=".",
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

    parser.add_argument("--level", action="store", default="RESPONSE",
                        help=("Specify level of detail using NETWORK, "
                              "STATION, CHANNEL, or RESPONSE."
                              " Default: RESPONSE"),
                        choices=('NETWORK', 'STATION', 'CHANNEL', 'RESPONSE'),
                        type=str.upper, metavar="level")

    parser.add_argument("--minlat", action="store",
                        help=("Limit to stations with a latitude larger than "
                              "or equal to the specified minimum."),
                        type=float, metavar="minlat")

    parser.add_argument("--maxlat", action="store",
                        help=("Limit to stations with a latitude smaller than "
                              "or equal to the specified maximum."),
                        type=float, metavar="maxlat")

    parser.add_argument("--minlon", action="store",
                        help=("Limit to stations with a longitude larger than "
                              "or equal to the specified minimum."),
                        type=float, metavar="minlon")

    parser.add_argument("--maxlon", action="store",
                        help=("Limit to stations with a longitude smaller "
                              "than or equal to the specified maximum."),
                        type=float, metavar="maxlon")

    parser.add_argument("--latitude", action="store",
                        help=("Specify the central latitude point for a "
                              "radial geographic constraint."),
                        type=float, metavar="latitude")

    parser.add_argument("--longitude", action="store",
                        help=("Specify the central longitude point for a "
                              "radial geographic constraint."),
                        type=float, metavar="longitude")

    parser.add_argument("--minradius", action="store",
                        help=("Specify minimum distance from the geographic "
                              "point defined by latitude and longitude."),
                        type=float, metavar="minradius")

    parser.add_argument("--maxradius", action="store",
                        help=("Specify maximum distance from the geographic "
                              "point defined by latitude and longitude."),
                        type=float, metavar="maxradius")

    parser.add_argument("--uri", action="store", default="",
                        type=str, metavar="uri")

    parser.add_argument("-E", "--emp_resp", action='store_true', default=False,
                        help='Print out Empty Response for debugging')

    parser.add_argument("--stationxml_on_error", action='store_true',
                        default=False,
                        help='Output stationxml even if bug is '
                             'present in data.')

    args = parser.parse_args()
    return args


class PH5toStationXMLError(Exception):
    """Exception raised when there is a problem with the request.
    :param: message -- explanation of the error
    """
    def __init__(self, message=""):
        self.message = message


class NoDataError(Exception):
    """Exception raised when no data matching request is returned.
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
                 end_time=None, emp_resp=None):

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
        self.emp_resp = emp_resp
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

    def __init__(self, sta_xml_obj_list, ph5path, nickname, level, format,
                 stationxml_on_error):
        self.request_list = sta_xml_obj_list
        self.ph5 = ph5api.PH5(path=ph5path, nickname=nickname)
        self.iris_custom_ns = "http://www.iris.edu/xml/station/1/"
        self.level = level.upper()
        self.format = format.upper()
        self.nickname = nickname
        self._obs_stations = {}
        self._obs_channels = {}
        self.stationxml_on_error = stationxml_on_error

    def get_station_key(self, station_code, start_date, end_date,
                        sta_longitude, sta_latitude, sta_elevation, site_name):
        return ".".join([str(x) for x in
                         [station_code, start_date.isoformat(),
                          end_date.isoformat(), sta_longitude, sta_latitude,
                          sta_elevation, site_name]])

    def get_obs_station(self, sta_key):
        """
        Returns a obspy station inventory instance if one has been added to the
        manager
        """
        return self._obs_stations.get(sta_key)

    def set_obs_station(self, sta_key, obs_station):
        """
        Add a obspy station inventory to the manager
        """
        self._obs_stations[sta_key] = obs_station

    def get_channel_key(self, sta_code, loc_code, cha_code, start_date,
                        end_date, cha_longitude, cha_latitude, cha_elevation,
                        cha_component, receiver_id, sample_rate,
                        sample_rate_ration, azimuth, dip, sensor_manufacturer,
                        sensor_model, sensor_serial, das_manufacturer,
                        das_model, das_serial):
        # array id is omitted since there can the same channel can belong to
        # more than one array.
        return ".".join([str(x) for x in
                         [sta_code, loc_code, cha_code, start_date.isoformat(),
                          end_date.isoformat(), cha_longitude, cha_latitude,
                          cha_elevation, cha_component, receiver_id,
                          sample_rate, sample_rate_ration, azimuth, dip,
                          sensor_manufacturer, sensor_model, sensor_serial,
                          das_manufacturer, das_model, das_serial]])

    def get_obs_channel(self, cha_key):
        """
        Returns a obspy channel inventory instance if one has been added to the
        manager
        """
        return self._obs_channels.get(cha_key)

    def set_obs_channel(self, cha_key, obs_channel):
        """
        Add a obspy station inventory to the manager
        """
        self._obs_channels[cha_key] = obs_channel


class PH5toStationXMLParser(object):

    def __init__(self, manager):
        self.manager = manager
        self.resp_manager = PH5ResponseManager()
        self.response_table_n_i = None
        self.response_by_n_i = {}
        self.receiver_table_n_i = None
        self.total_number_stations = 0
        self.unique_errors = set()
        self.checked_data_files = {}
        self.manager.ph5.read_response_t()

    def check_intersection(self, sta_xml_obj, latitude, longitude):
        """
        Checks latitude and longitude against geographic constraints
        :param: sta_xml_obj : PH5toStationXMLRequest object for the constraints
        :param: latitude : the given latitude
        :param: longitude : the given longitude
        """
        # check if lat/lon box intersection
        if not ph5utils.is_rect_intersection(sta_xml_obj.minlatitude,
                                             sta_xml_obj.maxlatitude,
                                             sta_xml_obj.minlongitude,
                                             sta_xml_obj.maxlongitude,
                                             latitude,
                                             longitude):
            return False
        # check if point/radius intersection
        if not ph5utils.is_radial_intersection(sta_xml_obj.latitude,
                                               sta_xml_obj.longitude,
                                               sta_xml_obj.minradius,
                                               sta_xml_obj.maxradius,
                                               latitude,
                                               longitude):
            return False
        return True

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
                    for deployment, station_entry in \
                            ((dk, se) for dk, dv in station_list.items()
                             for se in dv):
                        for sta_pattern in sta_xml_obj.station_list:
                            if not station_entry['seed_station_name_s'] and \
                                    fnmatch.fnmatch(str(station),
                                                    str(sta_pattern)):
                                # no seed station code defined so compare
                                # against ph5 station-id
                                sta_xml_obj.ph5_station_id_list.extend(
                                                                [station]
                                                            )
                            elif fnmatch.fnmatch(
                                        station_entry['seed_station_name_s'],
                                        sta_pattern):
                                sta_xml_obj.ph5_station_id_list.extend(
                                                                    [station]
                                                                )

            sta_xml_obj.ph5_station_id_list = \
                sorted(set(sta_xml_obj.ph5_station_id_list))
        self.total_number_stations = max([len(sta_xml_obj.ph5_station_id_list)
                                          for sta_xml_obj in
                                          self.manager.request_list])

    def get_network_date(self):
        self.read_arrays(None)
        array_names = self.manager.ph5.Array_t_names
        min_start_time = 7289567999
        max_end_time = 0
        for array_name in array_names:
            arraybyid = self.manager.ph5.Array_t[array_name]['byid']
            for station in arraybyid.values():
                for deployment in station.values():
                    for station_entry in deployment:
                        start_date = station_entry['deploy_time/epoch_l']
                        if start_date < min_start_time:
                            min_start_time = start_date
                        end_date = station_entry['pickup_time/epoch_l']
                        if end_date > max_end_time:
                            max_end_time = end_date
        return float(min_start_time), float(max_end_time+1)

    def trim_to_level(self, network):
        if self.manager.level == "NETWORK":
            network.stations = []
        elif self.manager.level == "STATION":
            # for station level show the selected_number_of_channels element
            for station in network.stations:
                station.selected_number_of_channels = 0
                station.channels = []
        return network

    def get_network(self):
        network = self.read_networks()
        if network:
            network = self.trim_to_level(network)
            return network
        else:
            return

    def get_response_inv(self, obs_channel, a_id, sta_id, cha_id,
                         spr, spr_m, emp_resp):

        sensor_keys = [obs_channel.sensor.manufacturer,
                       obs_channel.sensor.model]
        datalogger_keys = [obs_channel.data_logger.manufacturer,
                           obs_channel.data_logger.model,
                           obs_channel.sample_rate]

        info = {'n_i': self.response_table_n_i,
                'array': a_id,
                'sta': sta_id,
                'cha_id': cha_id,
                'cha_code': obs_channel.code,
                'dmodel': obs_channel.data_logger.model,
                'smodel': obs_channel.sensor.model,
                'spr': spr,
                'sprm': spr_m,
                }
        if info['dmodel'].startswith("ZLAND"):
            info['smodel'] = ''
        check_info = validation.check_response_info(
            info, self.manager.ph5,
            self.checked_data_files, self.unique_errors, None)

        if check_info[0] is False:
            if emp_resp:
                for errmsg in check_info[1]:
                    self.unique_errors.add((errmsg, 'error'))
                return Response()
            else:
                raise PH5toStationXMLError('\n'.join(check_info[1]))
        response_file_das_a_name, response_file_sensor_a_name = check_info

        # parse datalogger response
        if response_file_das_a_name:
            response_file_das_a = \
                self.manager.ph5.ph5_g_responses.get_response(
                                                response_file_das_a_name
                                        )

            with io.BytesIO(response_file_das_a) as buf:
                buf.seek(0, 0)
                if _is_resp(buf):
                    buf.seek(0, 0)
                    dl_resp = read_inventory(buf, format="RESP")
                    dl_resp = dl_resp[0][0][0].response
                else:
                    buf.seek(0, 0)
                    dl_resp = pickle.loads(response_file_das_a)

        # parse sensor response if present
        if response_file_sensor_a_name:
            response_file_sensor_a = \
                self.manager.ph5.ph5_g_responses.get_response(
                                            response_file_sensor_a_name
                                        )

            with io.BytesIO(response_file_sensor_a) as buf:
                buf.seek(0, 0)
                if _is_resp(buf):
                    buf.seek(0, 0)
                    sensor_resp = read_inventory(buf, format="RESP")
                    sensor_resp = sensor_resp[0][0][0].response
                else:
                    buf.seek(0, 0)
                    sensor_resp = pickle.loads(response_file_sensor_a)

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
            if self.manager.level == "CHANNEL":
                return Response(
                    instrument_sensitivity=inv_resp.instrument_sensitivity
                    )
            else:
                return inv_resp
        else:
            return Response()

    def create_obs_network(self):
        obs_stations = self.read_stations()
        has_error = False
        for errmsg, logtype in sorted(list(self.unique_errors)):
            if logtype == 'error':
                LOGGER.error(errmsg)
                has_error = True
            else:
                LOGGER.warning(errmsg)
        if obs_stations:
            obs_network = inventory.Network(
                self.experiment_t[0]['net_code_s'])
            obs_network.description = self.experiment_t[0]['longname_s']
            start_time, end_time = self.get_network_date()
            obs_network.start_date = UTCDateTime(start_time)
            obs_network.end_date = UTCDateTime(end_time)
            obs_network.total_number_of_stations = self.total_number_stations
            extra = AttribDict({
                    'PH5ReportNum': {
                        'value': self.experiment_t[0]['experiment_id_s'],
                        'namespace': self.manager.iris_custom_ns,
                        'type': 'attribute'
                    }
                })
            obs_network.extra = extra
            obs_network.stations = obs_stations
            if has_error:
                if self.manager.stationxml_on_error:
                    return obs_network
                return
            return obs_network
        else:
            return

    def create_obs_station(self, sta_code, start_date, end_date, sta_longitude,
                           sta_latitude, sta_elevation, creation_date,
                           termination_date, site_name):
        obs_station = inventory.Station(sta_code,
                                        latitude=round(sta_latitude, 6),
                                        longitude=round(sta_longitude, 6),
                                        start_date=start_date,
                                        end_date=end_date,
                                        elevation=round(sta_elevation, 1))
        obs_station.site = inventory.Site(name=(site_name if site_name
                                                else sta_code))
        obs_station.creation_date = creation_date
        obs_station.termination_date = termination_date
        obs_station.total_number_of_channels = 0  # initialized to 0
        obs_station.selected_number_of_channels = 0  # initialized to 0

        return obs_station

    def create_obs_channel(self, sta_code, loc_code,
                           cha_code, start_date, end_date,
                           cha_longitude, cha_latitude,
                           cha_elevation, cha_component, receiver_id,
                           array_code, sample_rate, sample_rate_ration,
                           azimuth, dip, sensor_manufacturer, sensor_model,
                           sensor_serial, das_manufacturer, das_model,
                           das_serial):

        obs_channel = inventory.Channel(
                                        code=cha_code,
                                        location_code=loc_code,
                                        latitude=round(cha_latitude, 6),
                                        longitude=round(cha_longitude, 6),
                                        elevation=round(cha_elevation, 1),
                                        depth=0
                                            )
        obs_channel.start_date = start_date
        obs_channel.end_date = end_date
        obs_channel.sample_rate = sample_rate
        obs_channel.sample_rate_ration = sample_rate_ration
        obs_channel.azimuth = azimuth
        obs_channel.dip = dip

        sensor_type = " ".join(
                        [x for x in
                         [sensor_manufacturer, sensor_model] if x])

        das_type = " ".join(
                        [x for x in
                         [das_manufacturer, das_model] if x])
        instrument_desc = "/".join(
                            [x for x in
                             [sensor_type, das_type] if x])
        obs_channel.sensor = inventory.Equipment(
            type=sensor_type,
            description=instrument_desc,
            manufacturer=sensor_manufacturer,
            vendor="",
            model=sensor_model,
            serial_number=sensor_serial,
            installation_date=UTCDateTime(start_date),
            removal_date=UTCDateTime(end_date))
        das_type = " ".join([x for x in [das_manufacturer, das_model] if x])
        obs_channel.data_logger = \
            inventory.Equipment(
                type=das_type,
                description="",
                manufacturer=das_manufacturer,
                vendor="",
                model=das_model,
                serial_number=das_serial,
                installation_date=UTCDateTime(start_date),
                removal_date=UTCDateTime(end_date)
            )
        extra = AttribDict({
                'PH5Component': {
                    'value': str(cha_component),
                    'namespace': self.manager.iris_custom_ns,
                    'type': 'attribute'
                },
                'PH5ReceiverId': {
                    'value': str(receiver_id),
                    'namespace': self.manager.iris_custom_ns,
                    'type': 'attribute'
                },
                'PH5Array': {
                    'value': str(array_code),
                    'namespace': self.manager.iris_custom_ns,
                    'type': 'attribute'
                }
            })
        obs_channel.extra = extra

        return obs_channel

    def read_networks(self):
        has_error = False
        self.manager.ph5.read_experiment_t()
        self.experiment_t = self.manager.ph5.Experiment_t['rows']
        if self.experiment_t == []:
            raise PH5toStationXMLError("No experiment_t in %s"
                                       % self.manager.ph5.filename)
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

        unique_resp = validation.check_resp_unique_n_i(
            self.manager.ph5, set(), None)
        if unique_resp is not True:
            LOGGER.error(unique_resp)
            has_error = True

        has_response_file = validation.check_has_response_filename(
            self.manager.ph5.Response_t, set(), None)
        if has_response_file is not True:
            raise PH5toStationXMLError(has_response_file)

        # update requests list to include ph5 station ids
        self.add_ph5_stationids()

        obs_network = self.create_obs_network()

        self.manager.ph5.close()
        if has_error:
            if self.manager.stationxml_on_error:
                return obs_network
            return
        return obs_network

    def read_stations(self):

        all_stations = []
        for sta_xml_obj in self.manager.request_list:
            array_patterns = sta_xml_obj.array_list
            for array_name in self.array_names:
                array_code = array_name[8:]
                if not ph5utils.does_pattern_exists(array_patterns,
                                                    array_code):
                    continue
                arraybyid = self.manager.ph5.Array_t[array_name]['byid']
                arrayorder = self.manager.ph5.Array_t[array_name]['order']
                for sta_id in arrayorder:
                    station_list = arraybyid.get(sta_id)
                    obs_channels = []
                    if sta_id not in sta_xml_obj.ph5_station_id_list:
                        continue
                    for deployment, station_epoch, station_entry in \
                            ((dk, dv, se) for dk, dv in station_list.items()
                             for se in dv):

                        longitude = station_entry['location/X/value_d']
                        latitude = station_entry['location/Y/value_d']
                        elevation = station_entry['location/Z/value_d']

                        if station_entry['seed_station_name_s']:
                            station_code = station_entry['seed_station_name_s']
                        else:
                            station_code = sta_id
                        errors, warnings = validation.check_lat_lon_elev(
                            station_entry)
                        header = "array %s, station %s, channel %s: " % \
                                 (array_code, station_code,
                                  station_entry['channel_number_i'])
                        for e in errors:
                            msg = header + str(e)
                            self.unique_errors.add((msg, 'error'))

                        if errors != []:
                            continue
                        if not self.check_intersection(sta_xml_obj, latitude,
                                                       longitude):
                            continue
                        start_date = UTCDateTime(
                                        station_entry['deploy_time/epoch_l'])
                        end_date = UTCDateTime(
                                        station_entry['pickup_time/epoch_l'])

                        if (sta_xml_obj.start_time and
                                sta_xml_obj.start_time > end_date):
                            # chosen start time after pickup
                            continue
                        elif (sta_xml_obj.end_time and
                                sta_xml_obj.end_time < start_date):
                            # chosen end time before pickup
                            continue

                        # run channel filters if necessary. we do this
                        # first to avoid creating a station that has no
                        # channels
                        if (self.manager.level.upper() == "RESPONSE" or
                                self.manager.level.upper() == "CHANNEL" or
                                sta_xml_obj.location_list != ['*'] or
                                sta_xml_obj.channel_list != ['*'] or
                                sta_xml_obj.component_list != ['*'] or
                                sta_xml_obj.receiver_list != ['*']):
                            obs_channels = self.read_channels(sta_xml_obj,
                                                              station_entry,
                                                              deployment,
                                                              station_code,
                                                              array_code)
                            # go to the next station if no channels were
                            # returned
                            if len(obs_channels) == 0:
                                continue

                        sta_key = self.manager.get_station_key(
                                    station_code,
                                    start_date,
                                    end_date,
                                    longitude,
                                    latitude,
                                    elevation,
                                    station_entry['location/description_s'])
                        if self.manager.get_obs_station(sta_key):
                            # station already created and added to metadata
                            obs_station = self.manager.get_obs_station(sta_key)
                        else:
                            # create and add a new station
                            obs_station = self.create_obs_station(
                                    station_code,
                                    start_date,
                                    end_date,
                                    longitude,
                                    latitude,
                                    elevation,
                                    start_date,  # creation_date
                                    end_date,  # termination date
                                    station_entry['location/description_s'])

                        # Add matching channels to station if necessary
                        if obs_channels:
                            obs_station.channels.extend(obs_channels)
                            obs_station.selected_number_of_channels = \
                                len(obs_station.channels)
                        else:
                            obs_station.selected_number_of_channels = 0

                        obs_station.total_number_of_channels += \
                            len(station_list)

                        if self.manager.get_obs_station(sta_key) is None:
                            all_stations.append(obs_station)
                            self.manager.set_obs_station(sta_key,
                                                         obs_station)
        return all_stations

    def read_channels(self, sta_xml_obj, station_entry, deployment,
                      sta_code, array_code):

        all_channels = []
        cha_list_patterns = sta_xml_obj.channel_list
        component_list_patterns = sta_xml_obj.component_list
        receiver_list_patterns = sta_xml_obj.receiver_list
        location_patterns = sta_xml_obj.location_list
        longitude = station_entry['location/X/value_d']
        latitude = station_entry['location/Y/value_d']
        elevation = station_entry['location/Z/value_d']

        receiver_id = str(station_entry['id_s'])
        if not ph5utils.does_pattern_exists(receiver_list_patterns,
                                            receiver_id):
            return

        c_id = str(station_entry['channel_number_i'])
        if not ph5utils.does_pattern_exists(component_list_patterns, c_id):
            return

        cha_code = (station_entry['seed_band_code_s'] +
                    station_entry['seed_instrument_code_s'] +
                    station_entry['seed_orientation_code_s'])

        for pattern in cha_list_patterns:
            if fnmatch.fnmatch(cha_code, pattern):
                if station_entry['seed_location_code_s']:
                    loc_code = station_entry['seed_location_code_s']
                else:
                    loc_code = ""

                if not ph5utils.does_pattern_exists(location_patterns,
                                                    loc_code):
                    continue

                start_date = UTCDateTime(station_entry['deploy_time/epoch_l'])
                end_date = UTCDateTime(station_entry['pickup_time/epoch_l'])

                # compute sample rate
                sample_rate_multiplier = \
                    float(station_entry['sample_rate_multiplier_i'])
                sample_rate_ration = float(station_entry['sample_rate_i'])
                try:
                    sample_rate = sample_rate_ration/sample_rate_multiplier
                except ZeroDivisionError:
                    raise PH5toStationXMLError(
                             "Error - Invalid sample_rate_multiplier_i == 0")

                receiver_table_n_i = station_entry['receiver_table_n_i']
                Receiver_t = self.manager.ph5.get_receiver_t_by_n_i(
                                                            receiver_table_n_i)

                cha_key = self.manager.get_channel_key(
                    sta_code, loc_code, cha_code, start_date, end_date,
                    longitude,
                    latitude,
                    elevation,
                    station_entry['channel_number_i'],  # component
                    receiver_id,
                    sample_rate,
                    sample_rate_ration,
                    Receiver_t['orientation/azimuth/value_f'],
                    Receiver_t['orientation/dip/value_f'],
                    station_entry['sensor/manufacturer_s'],
                    station_entry['sensor/model_s'],
                    station_entry['sensor/serial_number_s'],
                    station_entry['das/manufacturer_s'],
                    station_entry['das/model_s'],
                    station_entry['das/serial_number_s'])

                if self.manager.get_obs_channel(cha_key):
                    # update existing channe entry
                    obs_cha = self.manager.get_obs_channel(cha_key)
                    arrays_list = obs_cha.extra.PH5Array.value.split(",")
                    if array_code not in arrays_list:
                        arrays_list.append(array_code)
                        arrays_list.sort()
                        obs_cha.extra.PH5Array.value = ",".join(arrays_list)
                else:
                    # create new channel entry
                    obs_channel = self.create_obs_channel(
                        sta_code,
                        loc_code,
                        cha_code,
                        start_date,
                        end_date,
                        longitude,
                        latitude,
                        elevation,
                        station_entry['channel_number_i'],  # component
                        receiver_id,
                        array_code,
                        sample_rate,
                        sample_rate_ration,
                        Receiver_t['orientation/azimuth/value_f'],
                        Receiver_t['orientation/dip/value_f'],
                        station_entry['sensor/manufacturer_s'],
                        station_entry['sensor/model_s'],
                        station_entry['sensor/serial_number_s'],
                        station_entry['das/manufacturer_s'],
                        station_entry['das/model_s'],
                        station_entry['das/serial_number_s'])
                    self.manager.set_obs_channel(cha_key, obs_channel)

                    # read response and add it to response_by_n_i if
                    # it doesn't exist
                    self.response_table_n_i = n_i = \
                        station_entry['response_table_n_i']
                    if (self.response_table_n_i
                            not in self.response_by_n_i.keys()):
                        self.response_by_n_i[n_i] = \
                            self.get_response_inv(
                                obs_channel, array_code, sta_code, c_id,
                                station_entry['sample_rate_i'],
                                station_entry['sample_rate_multiplier_i'],
                                sta_xml_obj.emp_resp)
                    # Assign response to obspy channel inventory
                    obs_channel.response = self.response_by_n_i[n_i]

                    all_channels.append(obs_channel)
        return all_channels


def execute(path, args_dict_list, nickname, level, out_format):
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
                            end_time=args_dict.get('end_time'),
                            emp_resp=args_dict.get('emp_resp')
                            )
               for args_dict in args_dict_list]

    ph5sxmlmanager = PH5toStationXMLRequestManager(
        sta_xml_obj_list=ph5sxml,
        ph5path=path,
        nickname=nickname,
        level=level,
        format=out_format,
        stationxml_on_error=args_dict.get('stationxml_on_error'))
    ph5sxmlparser = PH5toStationXMLParser(ph5sxmlmanager)
    return ph5sxmlparser.get_network()


def run_ph5_to_stationxml(paths, nickname, out_format,
                          level, uri, args_dict_list):
    networks = []
    if paths:
        for path in paths:
            try:
                LOGGER.info("CHECKING %s" % os.path.join(path, nickname))
                n = execute(path,
                            args_dict_list,
                            nickname,
                            level,
                            out_format)
                if n is None:
                    LOGGER.info("NO STATIONXML DATA CREATED FOR %s" %
                                os.path.join(path, nickname))
                else:
                    networks.append(n)
                    LOGGER.info("STATIONXML DATA CREATED FOR %s" %
                                os.path.join(path, nickname))
            except PH5toStationXMLError as e:
                LOGGER.error(e.message)
                LOGGER.info("NO STATIONXML DATA CREATED FOR %s" %
                            os.path.join(path, nickname))

        if networks:
            inv = inventory.Inventory(
                                        networks=networks,
                                        source="PIC-PH5",
                                        sender="IRIS-PASSCAL-DMC-PH5",
                                        created=UTCDateTime.now(),
                                        module=("PH5 WEB SERVICE: metadata "
                                                "| version: 1"),
                                        module_uri=uri)
            return inv
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
        if not inv:
            raise NoDataError("Request resulted in no data.")

        if out_format == "STATIONXML":
            inv.write(args.outfile,
                      format='STATIONXML',
                      nsmap={'iris': "http://www.iris.edu/xml/station/1/"})
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
    except NoDataError as err:
        LOGGER.info(err.message)
    except Exception as err:
        LOGGER.error(err.message)


if __name__ == '__main__':
    main()
