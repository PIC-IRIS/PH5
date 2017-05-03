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
import obspy 
import ph5API
import datetime
from obspy import read_inventory
from obspy.geodetics import locations2degrees
import argparse
import fnmatch
from obspy.core.util import AttribDict
import math

PROG_VERSION = "2017.085"


def get_args():
    parser = argparse.ArgumentParser(
        description='Takes PH5 files and returns stationxml.',
        usage='Version: {0} ph5tostationxml --nickname="Master_PH5_file" [options]'.format(PROG_VERSION))

    parser.add_argument("-n", "--nickname", action="store", required=True,
                        type=str, metavar="nickname")

    parser.add_argument("-p", "--ph5path", action="store",
                        help="Comma separated list of paths to ph5 experiments",
                        type=str, metavar="ph5path")

    parser.add_argument("--basepath", action="store",
                        type=str, metavar="basepath", help="Specify a base directory containing any number of PH5 experiments. All PH5 files foudn will be used")

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


class PH5toStationXML(object):

    def __init__(self, args):

        self.args = args
        self.iris_custom_ns = "http://www.fdsn.org/xml/station/1/iris"
        self.cha_list_set=1
        self.sta_list_set=1
        self.receiver_list_set=1
        self.location_list_set=1

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

        if self.args.get('start_time') and "T" in self.args.get('start_time'):
            self.args['start_time'] = datetime.datetime.strptime(
                self.args.get('start_time'), "%Y-%m-%dT%H:%M:%S.%f")
        elif self.args.get('start_time'):
            self.args['start_time'] = datetime.datetime.strptime(
                self.args.get('start_time'), "%Y:%j:%H:%M:%S.%f")

        if self.args.get('stop_time') and "T" in self.args.get('stop_time'):
            self.args['stop_time'] = datetime.datetime.strptime(
                self.args.get('stop_time'), "%Y-%m-%dT%H:%M:%S.%f")
        elif self.args.get('stop_time'):
            self.args['stop_time'] = datetime.datetime.strptime(
                self.args.get('stop_time'), "%Y:%j:%H:%M:%S.%f")

    def does_pattern_exists(self, patterns_list, other_pattern):
        for pattern in patterns_list:
            if fnmatch.fnmatch(other_pattern, pattern):
                return True
        return False
    
    def does_experiment_pattern_exists(self, request_patterns, code):
        l = []
        for pattern in request_patterns:
            if fnmatch.fnmatch(self.experiment_t[0][code], pattern):
                l.append(1)
        if not l:
            return False
        else:
            return True

    def read_arrays(self, name):
        if name is None:
            for n in self.ph5.Array_t_names:
                self.ph5.read_array_t(n)
        else:
            self.ph5.read_array_t(name)
    
    @classmethod
    def is_radial_intersection(cls, point_lat, point_lon, 
                               minradius, maxradius, 
                               latitude, longitude):
        """
        Checks if there is a radial intersection between a point radius boundary
        and a latitude/longitude point.
        :param: point_lat : the latitude of the point radius boundary :type: float
        :param: point_lon : the longitude of the point radius boundary :type: float
        :param: minradius : the minimum radius boundary :type: float
        :param: maxradius : the maximum radius boundary :type: float
        :param: latitude : the latitude of the point to check :type: float
        :param: longitude : the longitude of the point to check :type: float
        """
        if minradius or maxradius or point_lat or point_lon:
            # min radius default to 0.0
            if not minradius:
                minradius = 0.0
            # make max radius default to min radius when not defined
            if not maxradius:
                maxradius = minradius
            # latitude and longitude default to 0.0 when not defined
            if not point_lat:
                point_lat = 0.0
            if not point_lon:
                point_lon = 0.0
            dist = locations2degrees(latitude, longitude, point_lat, point_lon)
            if dist < minradius:
                return False
            elif dist > maxradius:
                return False
            else:
                return True
        else:
            return True
    
    @classmethod
    def is_rect_intersection(cls, minlat, maxlat, minlon, maxlon, latitude, longitude):
        """
        Checks if there is a radial intersection between a point radius boundary
        and a latitude/longitude point.
        :param: minlat : the minimum rectangular latitude :type: float
        :param: maxlat : the maximum rectangular latitude :type: float
        :param: minlon : the minimum rectangular longitude :type: float
        :param: maxlon : the maximum rectangular longitude :type: float
        :param: latitude : the latitude of the point to check :type: float
        :param: longitude : the longitude of the point to check :type: float
        """
        if minlat and float(
                minlat) > float(latitude):
            return False
        elif minlon and float(
                minlon) > float(longitude):
            return False
        elif maxlat and float(
                maxlat) < float(latitude):
            return False
        elif maxlon and float(
                maxlon) < float(longitude):
            return False
        else:
            return True

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
        elif not PH5toStationXML.is_rect_intersection(self.args.get('minlat'),
                                           self.args.get('maxlat'),
                                           self.args.get('minlon'),
                                           self.args.get('maxlon'),
                                           latitude,
                                           longitude):
            return False
        # check if point/radius intersection
        elif not PH5toStationXML.is_radial_intersection(self.args.get('latitude'),
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
            obs_network.start_date=datetime.datetime.fromtimestamp(start_time)
            obs_network.end_date=datetime.datetime.fromtimestamp(end_time)
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
        obs_station.creation_date = datetime.datetime.fromtimestamp(
            station_list[1][0]['deploy_time/epoch_l'])
        obs_station.termination_date = datetime.datetime.fromtimestamp(
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
            name=station_list[1][0]['seed_station_name_s'])     

        return obs_station     

    def create_obs_channel(self, station_list, deployment, cha_code, loc_code,
                           cha_longitude, cha_latitude, cha_elevation):       
        obs_channel = obspy.core.inventory.Channel(
            code=cha_code, location_code=loc_code,
            latitude=cha_latitude,
            longitude=cha_longitude, elevation=cha_elevation,
            depth=0)
        obs_channel.start_date = datetime.datetime.fromtimestamp(
            station_list[deployment][0]['deploy_time/epoch_l'])
        obs_channel.end_date = datetime.datetime.fromtimestamp(
            station_list[deployment][0]['pickup_time/epoch_l'])
        obs_channel.sample_rate = station_list[
            deployment][0]['sample_rate_i']
        obs_channel.sample_rate_ration = station_list[
            deployment][0]['sample_rate_multiplier_i']
        obs_channel.storage_format = "PH5"
        sensor_type =  " ".join([x for x in [station_list[deployment][0]['sensor/manufacturer_s'], 
                                          station_list[deployment][0]['sensor/model_s']] if x])
        obs_channel.sensor = obspy.core.inventory.Equipment(
            type=sensor_type, description="",
            manufacturer=station_list[deployment][0]['sensor/manufacturer_s'], vendor="", model=station_list[deployment][0]['sensor/model_s'],
            serial_number=station_list[deployment][0][
                'sensor/serial_number_s'], installation_date=datetime.datetime.fromtimestamp(station_list[deployment][0]['deploy_time/epoch_l']),
            removal_date=datetime.datetime.fromtimestamp(station_list[deployment][0]['pickup_time/epoch_l']))
        das_type =  " ".join([x for x in [station_list[deployment][0]['das/manufacturer_s'], 
                                          station_list[deployment][0]['das/model_s']] if x])
        obs_channel.data_logger = obspy.core.inventory.Equipment(
            type=das_type, description="",
            manufacturer=station_list[deployment][0]['das/manufacturer_s'], vendor="", model=station_list[deployment][0]['das/model_s'],
            serial_number=station_list[deployment][0][
                'das/serial_number_s'], installation_date=datetime.datetime.fromtimestamp(station_list[deployment][0]['deploy_time/epoch_l']),
            removal_date=datetime.datetime.fromtimestamp(station_list[deployment][0]['pickup_time/epoch_l']))
        extra = AttribDict({
                'PH5Component': {
                    'value': str(station_list[deployment][0]['channel_number_i']),
                    'namespace': self.iris_custom_ns,
                    'type': 'attribute'
                }
            }) 
        obs_channel.extra=extra
        return obs_channel
    
    def read_response(self, station_list, deployment):
        das = station_list[deployment][0]['das/serial_number_s'] 
        self.ph5.read_das_t(das, reread=False)   
        if self.ph5.Das_t.get(das):
            Das_t = ph5API.filter_das_t(self.ph5.Das_t[das]['rows'],
                                       station_list[deployment][0][
                                           'channel_number_i'])
            self.ph5.read_response_t()
            Response_t = self.ph5.get_response_t(Das_t[0])
            response_file = Response_t['response_file_a']
            if response_file:
                # TODO: Add code for reading locally stored repsonse information
                pass
            else:
                # TODO: Add code for reading RESP form the NRL
                pass

    def read_channels(self, station_list):

        obs_channels = []
        cha_list_patterns = self.args.get('channel_list')
        component_list_patterns = self.args.get('component_list')
        receiver_list_patterns = self.args.get('receiver_list')
        location_patterns = self.args.get('location_list')
        for deployment in station_list:
            receiver_id=str(station_list[deployment][0]['id_s'])          
            if not self.does_pattern_exists(receiver_list_patterns, receiver_id):
                continue           
            
            c_id= str(station_list[deployment][0]['channel_number_i'])
            if not self.does_pattern_exists(component_list_patterns, c_id):
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

                    if not self.does_pattern_exists(location_patterns, location):
                        continue 

                    cha_longitude = station_list[deployment][
                                                     0]['location/X/value_d']
                    cha_latitude = station_list[deployment][
                                                    0]['location/Y/value_d']
                    cha_elevation = station_list[deployment][
                                                     0]['location/Z/value_d'] 
                    
                    if not self.is_lat_lon_match(cha_latitude, cha_longitude):
                        continue

                    response_inv = self.read_response(station_list, deployment)

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
            
            if not self.does_pattern_exists(array_patterns, array):
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
                start_date = datetime.datetime.fromtimestamp(start_date)
                end_date = station_list[1][0]['pickup_time/epoch_l']
                end_date = datetime.datetime.fromtimestamp(end_date)
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
                   
                obs_channels = self.read_channels(station_list)
                
                obs_station.total_number_of_channels = len(sta_list)
                obs_station.selected_number_of_channels = len(obs_channels)

                obs_station.channels = obs_channels
                if obs_station and obs_station.selected_number_of_channels == 0:
                    continue
                else:
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
        network_patterns = self.args.get('network_list')
        reportnum_patterns =  self.args.get('reportnum_list')
        
        self.ph5 = ph5API.ph5(path=path, nickname=self.args.get('nickname'))
        self.ph5.read_array_t_names()
        self.ph5.read_das_g_names()
        self.ph5.read_experiment_t()
        self.read_arrays(None)
        self.experiment_t = self.ph5.Experiment_t['rows']
        self.array_names = self.ph5.Array_t_names
        self.array_names.sort()

        # read network code and compare to network list
        if not self.does_experiment_pattern_exists(network_patterns, 'net_code_s'):
            self.ph5.close()
            return

        # read reportnum and compare to reportnum list
        if not self.does_experiment_pattern_exists(reportnum_patterns, 'experiment_id_s'):
            self.ph5.close()
            return
        
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
            array = array_name[-3:] 
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
        elif self.args.get('level').upper() == "CHANNEL":
            for station in network.stations:
                for channel in station.channels:
                    channel.response = None
        return network
 
    def Process(self):
        networks = []

        paths = self.args.get('ph5path')

        if self.args.get('basepath'):
            paths = []
            for dirName, subdirList, fileList in os.walk(self.args.get('basepath')):
                for fname in fileList:
                    if fname == "master.ph5":
                        paths.append(dirName)

        for path in paths:
            network = self.read_networks(path)
            if network:
                network = self.trim_to_level(network)
                networks.append(network)
        if networks:
            inv = obspy.core.inventory.Inventory(networks=networks, source="PIC-PH5",
                                                 sender="IRIS-PASSCAL-DMC-PH5", created=datetime.datetime.now(),
                                                 module="PH5 WEB SERVICE: metadata | version: 1", module_uri=self.args.get('uri'))
            return inv
        else:
            return

                    
if __name__ == '__main__':

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

    ph5sxml = PH5toStationXML(args_dict)

    inv = ph5sxml.Process()
    
    if args.out_format.upper() == "STATIONXML":
        inv.write(args.outfile, format='STATIONXML', nsmap={'iris': ph5sxml.iris_custom_ns})

    elif args.out_format.upper() == "KML":
        inv.write(args.outfile, format='KML')
        
    else:
        print "Incorrect output format. Formats are STATIONXML or KML"
        sys.exit()
