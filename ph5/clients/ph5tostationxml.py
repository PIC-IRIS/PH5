# Derick Hess
# Oct 2016
"""

The MIT License (MIT)
Copyright (c) 2016 Derick Hess

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), 
to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""

import sys
import os
import datetime
import argparse
import fnmatch
import obspy
from obspy import read_inventory
from obspy.core.util import AttribDict
from obspy.core import UTCDateTime
from obspy.io.xseed import Parser
# functions for reading networks in parallel
import multiprocessing
import copy_reg
import types

from ph5.core import ph5utils, ph5api


PROG_VERSION = "2017.198"


def get_args():
    parser = argparse.ArgumentParser(
        description='Takes PH5 files and returns stationxml.',
        usage='Version: {0} ph5tostationxml --nickname="Master_PH5_file" [options]'.format(PROG_VERSION))

    parser.add_argument("-n", "--nickname", action="store", required=True,
                        type=str, metavar="nickname")

    parser.add_argument("-p", "--ph5path", action="store",
                        help="Comma separated list of paths to ph5 experiments",
                        type=str, metavar="ph5path")

    parser.add_argument("--network", action="store", dest="network_list",
                        help="Comma separated list of networks. Wildcards accepted",
                        type=str, metavar="network_list")

    parser.add_argument("--reportnum", action="store", dest="reportnum_list",
                        help="Comma separated list of report numbers. Wildcards accepted",
                        type=str, metavar="reportnum_list")

    parser.add_argument("-o", "--outfile", action="store", default="something.xml",
                        type=str, metavar="outfile")

    parser.add_argument("-f", "--format", action="store", default="STATIONXML", dest="out_format",
                        type=str, metavar="out_format", help="Output format: STATIONXML or KML")

    parser.add_argument("--array", action="store", dest="array_list",
                        help="Comma separated list of arrays.",
                        type=str, metavar="array_list")

    parser.add_argument("--station", action="store", dest="sta_list",
                        help="Comma separated list of stations. Wildcards accepted",
                        type=str, metavar="sta_list")
    
    parser.add_argument("--receiver", action="store", dest="receiver_list",
                        help="Comma separated list of receiver id's. Wildcards accepted",
                        type=str, metavar="receiver_list")    

    parser.add_argument("-c", "--channel", action="store", dest="channel_list",
                        help="Comma separated list of channels. Wildcards accepted",
                        type=str, metavar="channel_list")
    
    parser.add_argument("--component", action="store", dest="component_list",
                        help="Comma separated list of components. Wildcards accepted",
                        type=str, metavar="component_list")    

    parser.add_argument("-l", "--location", action="store", dest="location_list",
                        help="Comma separated list of locations. Wildcards accepted",
                        type=str, metavar="location_list")

    parser.add_argument("-s", "--starttime", action="store",
                        help="start time in FDSN time format or PASSCAL time format",
                        type=str, dest="start_time", metavar="start_time")

    parser.add_argument("-t", "--stoptime", action="store",
                        help="stop time in FDSN time format or PASSCAL time format",
                        type=str, dest="stop_time", metavar="stop_time")

    parser.add_argument("--level", action="store", default="channel",
                        help="Specify level of detail using network, station, channel,or response",
                        type=str, dest="level", metavar="level")

    parser.add_argument("--minlat", action="store",
                        help="Limit to stations with a latitude larger than or equal to the specified minimum.",
                        type=float, dest="minlat", metavar="minlat")

    parser.add_argument("--maxlat", action="store",
                        help="Limit to stations with a latitude smaller than or equal to the specified maximum.",
                        type=float, dest="maxlat", metavar="maxlat")

    parser.add_argument("--minlon", action="store",
                        help="Limit to stations with a longitude larger than or equal to the specified minimum.",
                        type=float, dest="minlon", metavar="minlon")

    parser.add_argument("--maxlon", action="store",
                        help="Limit to stations with a longitude smaller than or equal to the specified maximum.",
                        type=float, dest="maxlon", metavar="maxlon")
    
    parser.add_argument("--latitude", action="store",
                        help="Specify the central latitude point for a radial geographic constraint.")
    
    parser.add_argument("--longitude", action="store",
                        help="Specify the central longitude point for a radial geographic constraint., ")
    
    parser.add_argument("--minradius", action="store",
                    help="Specify minimum distance from the geographic point defined by latitude and longitude.")
    
    parser.add_argument("--maxradius", action="store",
                        help="Specify maximum distance from the geographic point defined by latitude and longitude.")

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


class PH5ResponseManager(object):
    
    def __init__(self):
        self.responses = []
        
    def add_response(self, sensor_keys, datalogger_keys, response):
        self.responses.append(PH5Response(sensor_keys, datalogger_keys, response))
    
    def get_response(self, sensor_keys, datalogger_keys):
        for ph5_resp in self.responses:
            if set(sensor_keys) == set(ph5_resp.sensor_keys) and \
               set(datalogger_keys) == set(ph5_resp.datalogger_keys):
                return ph5_resp.response
    
    def is_already_requested(self, sensor_keys, datalogger_keys):
        for response in self.responses:
            if set(sensor_keys) == set(response.sensor_keys) and \
               set(datalogger_keys) == set(response.datalogger_keys):
                return True
        return False

class PH5Response(object):
    def __init__(self, sensor_keys, datalogger_keys, response):
        self.sensor_keys = sensor_keys
        self.datalogger_keys = datalogger_keys
        self.response = response

class PH5toStationXML(object):

    def __init__(self, args):

        self.args = args
        self.iris_custom_ns = "http://www.fdsn.org/xml/station/1/iris"
        self.cha_list_set=1
        self.sta_list_set=1
        self.receiver_list_set=1
        self.location_list_set=1
        self.response_table_n_i = None
        self.receiver_table_n_i = None        
        self.resp_manager = PH5ResponseManager()

        nickname, ext = os.path.splitext(args.get('nickname'))
        if ext != 'ph5':
            args['nickname'] = nickname + '.ph5'

        if not self.args.get('channel_list'):
            self.cha_list_set=0
            self.args['channel_list'] = ["*"]
            
        if not self.args.get('component_list'):
            self.component_list_set=0
            self.args['component_list'] = ["*"]

        if not self.args.get('sta_list'):
            self.sta_list_set=0
            self.args['sta_list'] = ["*"]
            
        if not self.args.get('receiver_list'):
            self.receiver_list_set=0
            self.args['receiver_list'] = ["*"]

        if not self.args.get('location_list'):
            self.location_list_set=0
            self.args['location_list'] = ["*"]

        if not self.args.get('network_list'):
            self.args['network_list'] = ["*"]

        if not self.args.get('reportnum_list'):
            self.args['reportnum_list'] = ["*"]

        if not self.args.get('array_list'):
            self.args['array_list'] = ["*"]

        if self.args.get('start_time'):
            self.args['start_time'] = ph5utils.datestring_to_datetime(self.args.get('start_time'))

        if self.args.get('stop_time'):
            self.args['stop_time'] = ph5utils.datestring_to_datetime(self.args.get('stop_time'))

    def read_arrays(self, name):
        if name is None:
            for n in self.ph5.Array_t_names:
                self.ph5.read_array_t(n)
        else:
            self.ph5.read_array_t(name)

    def is_lat_lon_match(self, latitude, longitude):
        """
        Checks if the given latitude/longitude matches geographic query constraints
        :param: latitude : the latitude to check against the arguments geographic constraints
        :param: longitude : the longitude to check against the arguments geographic constraints
        """
        if  not -90 <= float(latitude) <= 90:
            return False 
        elif not  -180 <= float(longitude) <= 180:
            return False
        # if lat/lon box intersection  
        elif not ph5utils.is_rect_intersection(self.args.get('minlat'),
                                           self.args.get('maxlat'),
                                           self.args.get('minlon'),
                                           self.args.get('maxlon'),
                                           latitude,
                                           longitude):
            return False
        # check if point/radius intersection
        elif not ph5utils.is_radial_intersection(self.args.get('latitude'),
                                             self.args.get('longitude'),
                                             self.args.get('minradius'),
                                             self.args.get('maxradius'),
                                             latitude,
                                             longitude):
            return False
        else:
            return True
        
    def create_obs_network(self, sta_list):
        obs_stations = self.read_stations(sta_list)
        if obs_stations:
            obs_network = obspy.core.inventory.Network(
                self.experiment_t[0]['net_code_s'])
            obs_network.alternate_code = self.experiment_t[0]['experiment_id_s']
            obs_network.description = self.experiment_t[0]['longname_s']
            start_time, end_time=self.get_network_date()   
            obs_network.start_date=UTCDateTime(start_time)
            obs_network.end_date=UTCDateTime(end_time)
            obs_network.total_number_of_stations = len(sta_list)
            obs_network.stations = obs_stations
            return obs_network
        else:
            return

    def create_obs_station(self, station_list, sta_code, 
                           array_name, start_date, end_date, sta_longitude,
                           sta_latitude, sta_elevation):

        obs_station = obspy.core.inventory.Station(sta_code,
                                               latitude=sta_latitude,
                                               longitude=sta_longitude,
                                               start_date=start_date,
                                               end_date=end_date,
                                               elevation=sta_elevation)                           
        obs_station.creation_date = UTCDateTime(
            station_list[1][0]['deploy_time/epoch_l'])
        obs_station.termination_date = UTCDateTime(
            station_list[1][0]['pickup_time/epoch_l'])
        extra = AttribDict({
            'PH5Array': {
                'value': str(array_name)[-3:],
                'namespace': self.iris_custom_ns,
                'type': 'attribute'
            }
        }) 
        obs_station.extra=extra        
        obs_station.site = obspy.core.inventory.Site(
            name=station_list[1][0]['location/description_s'])     

        return obs_station     

    def create_obs_channel(self, station_list, deployment, cha_code, loc_code,
                           cha_longitude, cha_latitude, cha_elevation):       
        obs_channel = obspy.core.inventory.Channel(
            code=cha_code, location_code=loc_code,
            latitude=cha_latitude,
            longitude=cha_longitude, elevation=cha_elevation,
            depth=0)
        obs_channel.start_date = UTCDateTime(
            station_list[deployment][0]['deploy_time/epoch_l'])
        obs_channel.end_date = UTCDateTime(
            station_list[deployment][0]['pickup_time/epoch_l'])
        obs_channel.sample_rate = float(station_list[
            deployment][0]['sample_rate_i'])/float(station_list[
            deployment][0]['sample_rate_multiplier_i'])
        obs_channel.sample_rate_ration = station_list[
            deployment][0]['sample_rate_multiplier_i']
        obs_channel.storage_format = "PH5"

        receiver_table_n_i =station_list[deployment][0]['receiver_table_n_i']  
        self.response_table_n_i= station_list[deployment][0]['response_table_n_i']
        Receiver_t=self.ph5.get_receiver_t_by_n_i (receiver_table_n_i)
        obs_channel.azimuth=Receiver_t['orientation/azimuth/value_f']
        obs_channel.dip=Receiver_t['orientation/dip/value_f']        
        
        sensor_type =  " ".join([x for x in [station_list[deployment][0]['sensor/manufacturer_s'], 
                                          station_list[deployment][0]['sensor/model_s']] if x])
        obs_channel.sensor = obspy.core.inventory.Equipment(
            type=sensor_type, description=station_list[deployment][0]['sensor/manufacturer_s']+' '+
                                          station_list[deployment][0]['sensor/model_s']+'/'+
                                          station_list[deployment][0]['das/manufacturer_s']+' '+
                                          station_list[deployment][0]['das/model_s'],
            manufacturer=station_list[deployment][0]['sensor/manufacturer_s'], vendor="", model=station_list[deployment][0]['sensor/model_s'],
            serial_number=station_list[deployment][0][
                'sensor/serial_number_s'], installation_date=UTCDateTime(station_list[deployment][0]['deploy_time/epoch_l']),
            removal_date=UTCDateTime(station_list[deployment][0]['pickup_time/epoch_l']))
        das_type =  " ".join([x for x in [station_list[deployment][0]['das/manufacturer_s'], 
                                          station_list[deployment][0]['das/model_s']] if x])
        obs_channel.data_logger = obspy.core.inventory.Equipment(
            type=das_type, description="",
            manufacturer=station_list[deployment][0]['das/manufacturer_s'], vendor="", model=station_list[deployment][0]['das/model_s'],
            serial_number=station_list[deployment][0][
                'das/serial_number_s'], installation_date=UTCDateTime(station_list[deployment][0]['deploy_time/epoch_l']),
            removal_date=UTCDateTime(station_list[deployment][0]['pickup_time/epoch_l']))
        extra = AttribDict({
                'PH5Component': {
                    'value': str(station_list[deployment][0]['channel_number_i']),
                    'namespace': self.iris_custom_ns,
                    'type': 'attribute'
                }
            }) 
        obs_channel.extra=extra
        
        if self.args.get('level').upper() == "RESPONSE" or \
                (self.args.get('level').upper() == "CHANNEL" and \
                 self.args.get('out_format').upper() == "TEXT"):
            # read response and add it to obspy channel inventory
            obs_channel.response = self.get_response_inv(obs_channel)

        return obs_channel
    
    def get_response_inv(self, obs_channel):
        self.ph5.read_response_t()
        Response_t = self.ph5.get_response_t_by_n_i(self.response_table_n_i)
        sensor_keys = [obs_channel.sensor.manufacturer,
                       obs_channel.sensor.model]
        datalogger_keys = [obs_channel.data_logger.manufacturer,
                           obs_channel.data_logger.model,
                           obs_channel.sample_rate]
        if not self.resp_manager.is_already_requested(sensor_keys, datalogger_keys):
            response_file_das_a_name = Response_t.get('response_file_das_a', None)
            response_file_sensor_a_name = Response_t.get('response_file_sensor_a', None)
            # parse datalogger response
            if response_file_das_a_name: 
                response_file_das_a = self.ph5.ph5_g_responses.get_response(response_file_das_a_name)
                dl = Parser(response_file_das_a)
            # parse sensor response if present
            if response_file_sensor_a_name:
                response_file_sensor_a = self.ph5.ph5_g_responses.get_response(response_file_sensor_a_name)
                sensor = Parser(response_file_sensor_a)
    
            inv_resp = None
            if response_file_das_a_name and response_file_sensor_a_name:
                # both datalogger and sensor response
                comp_resp = Parser.combine_sensor_dl_resps(sensor=sensor, datalogger=dl)
                inv_resp = comp_resp.get_response()
            elif response_file_das_a_name:
                # only datalogger response
                inv_resp = dl.get_response()
            elif response_file_sensor_a_name:
                # only sensor response
                inv_resp = sensor.get_response()
    
            if inv_resp:
                # update response manager and return response
                self.resp_manager.add_response(sensor_keys, datalogger_keys, inv_resp)
                return inv_resp
        else:
            return self.resp_manager.get_response(sensor_keys, datalogger_keys)
        
        

    def read_channels(self, station_list):

        obs_channels = []
        cha_list_patterns = self.args.get('channel_list')
        component_list_patterns = self.args.get('component_list')
        receiver_list_patterns = self.args.get('receiver_list')
        location_patterns = self.args.get('location_list')
        for deployment in station_list:
            receiver_id=str(station_list[deployment][0]['id_s'])          
            if not ph5utils.does_pattern_exists(receiver_list_patterns, receiver_id):
                continue           
            
            c_id= str(station_list[deployment][0]['channel_number_i'])
            if not ph5utils.does_pattern_exists(component_list_patterns, c_id):
                continue   

            seed_channel = station_list[deployment][0]['seed_band_code_s']+station_list[deployment][0]['seed_instrument_code_s']+station_list[deployment][0]['seed_orientation_code_s']

            for pattern in cha_list_patterns:
                if fnmatch.fnmatch(seed_channel, pattern):

                    if station_list[deployment][
                            0]['seed_location_code_s']:
                        location = station_list[deployment][
                            0]['seed_location_code_s']
                    else:
                        location = ""

                    if not ph5utils.does_pattern_exists(location_patterns, location):
                        continue 

                    cha_longitude = station_list[deployment][
                                                     0]['location/X/value_d']
                    cha_latitude = station_list[deployment][
                                                    0]['location/Y/value_d']
                    cha_elevation = station_list[deployment][
                                                     0]['location/Z/value_d'] 
                    
                    if not self.is_lat_lon_match(cha_latitude, cha_longitude):
                        continue

                    obs_channel = self.create_obs_channel(station_list, deployment,
                                                          seed_channel, location, cha_longitude, 
                                                          cha_latitude, cha_elevation)
                    
                    obs_channels.append(obs_channel)
        return obs_channels
    
    def read_stations(self, sta_list):

        all_stations = []
        array_patterns = self.args.get('array_list')      
       
        for array_name in self.array_names:

            array = array_name[-3:]
            
            if not ph5utils.does_pattern_exists(array_patterns, array):
                continue
                
            arraybyid = self.ph5.Array_t[array_name]['byid']
            arrayorder = self.ph5.Array_t[array_name]['order']
            
            for x in arrayorder:
                station_list = arraybyid.get(x)
                obs_channels = []

                if x not in sta_list:
                    continue
                
                sta_longitude = station_list[1][0]['location/X/value_d']
                sta_latitude = station_list[1][0]['location/Y/value_d']
                sta_elevation = station_list[1][0]['location/Z/value_d']

                if not self.is_lat_lon_match(sta_latitude, sta_longitude):
                    continue
                
                if station_list[1][0]['seed_station_name_s']:
                    station_name = station_list[1][0]['seed_station_name_s']
                else:
                    station_name = x

                start_date = station_list[1][0]['deploy_time/epoch_l']
                start_date = UTCDateTime(start_date)
                end_date = station_list[1][0]['pickup_time/epoch_l']
                end_date = UTCDateTime(end_date)
                if self.args.get('start_time') and self.args.get('start_time') > end_date:
                    # chosen start time after pickup
                    continue
                elif self.args.get('stop_time') and self.args.get('stop_time') < start_date:
                    # chosen end time before pickup
                    continue

                obs_station = self.create_obs_station(station_list, 
                                                      station_name, array_name, 
                                                      start_date, end_date,
                                                      sta_longitude, sta_latitude,
                                                      sta_elevation)
                   
                if self.args.get('level').upper() == "RESPONSE" or self.args.get('level').upper() == "CHANNEL" or \
                   self.args.get('location_list') != ['*'] or self.args.get('channel_list') != ['*'] or \
                   self.args.get('component_list') != ['*'] or self.args.get('receiver_list') != ['*']:
                    obs_channels = self.read_channels(station_list)    
                    obs_station.channels = obs_channels
                    obs_station.total_number_of_channels = len(station_list)
                    obs_station.selected_number_of_channels = len(obs_channels)
                    if obs_station and obs_station.selected_number_of_channels == 0:
                        continue
                else:
                    obs_station.total_number_of_channels = len(station_list)
                    obs_station.selected_number_of_channels = 0
                all_stations.append(obs_station)             
        return all_stations

    def parse_station_list(self, sta_list):
        l = []
        sta_list_patterns = sta_list
       
        for array_name in self.array_names:
            arraybyid = self.ph5.Array_t[array_name]['byid']
            arrayorder = self.ph5.Array_t[array_name]['order']
            
            for station in arrayorder:
                station_list = arraybyid.get(station)
                for deployment in station_list:
                    for pattern in sta_list_patterns:
                        if not station_list[deployment][0] ['seed_station_name_s'] and \
                            fnmatch.fnmatch(str(station), str(pattern)):
                            # no seed station code defined so compare against ph5 station-id
                            l.append(station)
                        elif fnmatch.fnmatch((station_list[deployment][0]
                                                ['seed_station_name_s']), pattern):
                            l.append(station)
        final_list = sorted(set(l))          
        return final_list

    def read_networks(self, path):
        self.ph5 = ph5api.PH5(path=path, nickname=self.args.get('nickname'))
        self.ph5.read_experiment_t()
        self.experiment_t = self.ph5.Experiment_t['rows']
           
        # read network code and compare to network list
        network_patterns = self.args.get('network_list')     
        if not ph5utils.does_pattern_exists(network_patterns, self.experiment_t[0]['net_code_s']):
            self.ph5.close()
            return

        # read reportnum and compare to reportnum list
        reportnum_patterns =  self.args.get('reportnum_list')
        if not ph5utils.does_pattern_exists(reportnum_patterns, self.experiment_t[0]['experiment_id_s']):
            self.ph5.close()
            return

        self.ph5.read_array_t_names()
        self.read_arrays(None)
        self.array_names = self.ph5.Array_t_names
        self.array_names.sort()
        
        sta_list = self.parse_station_list(self.args.get('sta_list'))
        obs_network = self.create_obs_network(sta_list)
        
        self.ph5.close()
        
        return obs_network
    
    def get_network_date(self):
        self.read_arrays(None)
        array_names = self.ph5.Array_t_names
        array_names.sort()
        min_start_time=7289567999
        max_end_time=0        
        
        for array_name in array_names:
            arraybyid = self.ph5.Array_t[array_name]['byid']
            arrayorder = self.ph5.Array_t[array_name]['order'] 
            
            for station in arrayorder:
                station_list = arraybyid.get(station)
                for deployment in station_list:
                    if float(station_list[deployment][0]['deploy_time/epoch_l']) < float(min_start_time):
                        min_start_time=float(station_list[deployment][0]['deploy_time/epoch_l'])
                        
                    if float(station_list[deployment][0]['pickup_time/epoch_l']) > float(max_end_time):
                        max_end_time=float(station_list[deployment][0]['pickup_time/epoch_l'])  
                        
        return min_start_time, max_end_time
    
    def trim_to_level(self, network):
        if self.args.get('level').upper() == "NETWORK":
            network.stations = []
        elif self.args.get('level').upper() == "STATION":
            # for station level show the selected_number_of_channels element
            for station in network.stations:
                station.selected_number_of_channels = 0
                station.channels = []
        elif self.args.get('level').upper() == "CHANNEL" and \
             self.args.get('out_format').upper() != "TEXT":
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


def _pickle_method(m):
    if m.im_self is None:
        return getattr, (m.im_class, m.im_func.func_name)
    else:
        return getattr, (m.im_self, m.im_func.func_name)

copy_reg.pickle(types.MethodType, _pickle_method)


def run_ph5_to_stationxml(sta_xml_obj):
    basepaths = sta_xml_obj.args.get('ph5path')
    paths = []
    for basepath in basepaths:
        for dirName, _, fileList in os.walk(basepath):
            for fname in fileList:
                if fname == "master.ph5":
                    paths.append(dirName)
    if paths:
        if len(paths) < 10:
            num_processes = len(paths)
        else:
            num_processes = 10
        pool = multiprocessing.Pool(processes=num_processes)
        networks = pool.map(sta_xml_obj.get_network, paths)
        networks = [n for n in networks if n]
        pool.close()
        pool.join()
        if networks:
            inv = obspy.core.inventory.Inventory(networks=networks, source="PIC-PH5",
                                                 sender="IRIS-PASSCAL-DMC-PH5", created=datetime.datetime.now(),
                                                 module="PH5 WEB SERVICE: metadata | version: 1", module_uri=sta_xml_obj.args.get('uri'))
            return inv
        else:
            return
    else:
        raise PH5toStationXMLError("No PH5 experiments were found "
                              "under basepath(s) {0}".format(basepaths))       


def main():
    args = get_args()
    args_dict = vars(args) 
    
    if args_dict.get('network_list'):
        args_dict['network_list'] = [x.strip()
                        for x in args_dict.get('network_list').split(',')]
    if args_dict.get('reportnum_list'):
        args_dict['reportnum_list'] = [x.strip()
                        for x in args_dict.get('reportnum_list').split(',')]
    if args_dict.get('sta_list'):
        args_dict['sta_list'] = [x.strip()
                        for x in args_dict.get('sta_list').split(',')]    
    if args_dict.get('receiver_list'):
        args_dict['receiver_list'] = [x.strip()
                        for x in args_dict.get('receiver_list').split(',')]
    if args_dict.get('array_list'):
        args_dict['array_list'] = [x.strip()
                        for x in args_dict.get('array_list').split(',')]    
    if args_dict.get('location_list'):
        args_dict['location_list'] = [x.strip()
                        for x in args_dict.get('location_list').split(',')]
    if args_dict.get('channel_list'):
        args_dict['channel_list'] = [x.strip()
                        for x in args_dict.get('channel_list').split(',')]
    if args_dict.get('component_list'):
        args_dict['component_list'] = [x.strip()
                        for x in args_dict.get('component_list').split(',')]    
    if args_dict.get('ph5path'):
        args_dict['ph5path'] = args_dict.get('ph5path').split(',')

    try:
        ph5sxml = PH5toStationXML(args_dict)
    
        inv = run_ph5_to_stationxml(ph5sxml)
        
        if args.out_format.upper() == "STATIONXML":
            inv.write(args.outfile, format='STATIONXML', nsmap={'iris': ph5sxml.iris_custom_ns})
        elif args.out_format.upper() == "KML":
            inv.write(args.outfile, format='KML')
        else:
            sys.stderr.write("Incorrect output format. Formats are STATIONXML or KML")
            sys.exit()
    except Exception as err:
        sys.stderr.write(str("Error - {0}\n".format(err.message)))        

                   
if __name__ == '__main__':
    main()
