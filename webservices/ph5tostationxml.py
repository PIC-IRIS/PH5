import sys, os

import obspy

import ph5API

import decimate

import time

import calendar

import datetime

from TimeDOY import epoch2passcal

from TimeDOY import passcal2epoch

from obspy import read_inventory

import numpy

import argparse

import fnmatch

import StringIO

PROG_VERSION = "2016.264"

def get_args () :
    parser = argparse.ArgumentParser(description='Takes PH5 files and returns stationxml.',
                             usage='Version: {0} ph5tostationxml --nickname="Master_PH5_file" [options]'.format (PROG_VERSION))
    
    
    
    parser.add_argument ("-n", "--nickname", action="store", required=True,
                             type=str, metavar="nickname")
    
    
    
    parser.add_argument ("-p", "--ph5path", action="store", default=".",
                             help="Comma separated list of paths to ph5 experiments",
                             type=str, metavar="ph5path")
    
    parser.add_argument ("-o", "--outfile", action="store", default="something.xml",
                                 type=str, metavar="outfile")    
    
    #parser.add_argument ("-r", "--response", action="store", dest="response_list", 
    #                             help="Comma separated list of response files",
    #                             type=str, metavar="response_list")   
    
    parser.add_argument ("--station", action="store", dest="sta_list", 
                                     help="Comma separated list of stations. Wildcards accepted", 
                                     type=str, metavar="sta_list")     
    
    parser.add_argument ("-c", "--channel", action="store", dest="channel_list", 
                                     help="Comma separated list of channels. Wildcards accepted", 
                                     type=str, metavar="channel_list") 
    
    parser.add_argument ("-l", "--location", action="store", dest="location_list", 
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
    
    
    
    
    
    

    args = parser.parse_args()
        
    return args 



class PH5toStationXML(object):

    def __init__(self, args):
        
        self.args=args
        
        if args.nickname[-3:] == 'ph5':
        
            PH5FILE = os.path.join(args.ph5path, args.nickname)
        
        else:
        
            PH5FILE = os.path.join(args.ph5path, args.nickname + '.ph5')
        
            args.nickname = args.nickname + '.ph5'
        
            
            
        if not self.args.channel_list:
            self.args.channel_list="*"
         
        
        if not self.args.sta_list:
            self.args.sta_list="*"
            
        if not self.args.location_list:
            self.args.location_list="*"        
        
        if self.args.start_time and "T" in self.args.start_time:
            self.args.start_time = datetime.datetime.strptime(self.args.start_time, "%Y-%m-%dT%H:%M:%S+%f")
        elif self.args.start_time:
            self.args.start_time = datetime.datetime.strptime(self.args.start_time, "%Y:%j:%H:%M:%S.%f")
            
        if self.args.stop_time and "T" in self.args.stop_time:
            self.args.stop_time = datetime.datetime.strptime(self.args.stop_time, "%Y-%m-%dT%H:%M:%S+%f")
        elif self.args.stop_time:
            self.args.stop_time = datetime.datetime.strptime(self.args.stop_time, "%Y:%j:%H:%M:%S.%f")    
            
                     
        
        
        
    def read_arrays(self, name):
        if name is None:
            for n in self.ph5.Array_t_names:
                self.ph5.read_array_t(n)
        else:
            self.ph5.read_array_t(name)    
    
    def Read_Stations(self,sta_list):
        all_stations=[]
        cha_list_patterns = [x.strip() for x in self.args.channel_list.split(',')]
        location_patterns =[x.strip() for x in self.args.location_list.split(',')]
        
        for array_name in self.array_names:
            array = array_name[-3:] 
            arraybyid = self.ph5.Array_t[array_name]['byid']
            arrayorder = self.ph5.Array_t[array_name]['order'] 
                    
            for x in arrayorder:  
                station_list = arraybyid.get(x)
                channels=[]
                obs_channels=[]
                total_channels=0
                
                if x not in sta_list:
                    continue
                
                longitude= "{0:.6f}".format(station_list[1][0]['location/X/value_d'])
                latitude= "{0:.6f}".format(station_list[1][0]['location/Y/value_d'])
                elevation="{0:.6f}".format(station_list[1][0]['location/Z/value_d'])
                
                
                
                
                if self.args.minlat and float(self.args.minlat) > float(latitude):
                    continue
                
                if self.args.minlon and float(self.args.minlon) > float(longitude):
                    continue   
                
                if self.args.maxlat and float(self.args.maxlat) < float(latitude):
                    continue
                                
                if self.args.maxlon and float(self.args.maxlon) < float(longitude):
                    continue                    
                
                
                
                station = obspy.core.inventory.Station(station_list[1][0]['seed_station_name_s'],
                                                       latitude=latitude,
                                                       longitude=longitude,
                                                       elevation=elevation) 
                
                
                station.start_date = datetime.datetime.fromtimestamp(station_list[1][0]['deploy_time/epoch_l'])
                station.end_date = datetime.datetime.fromtimestamp(station_list[1][0]['pickup_time/epoch_l'])
                
                
                if self.args.start_time and (station.start_date <= self.args.start_time):   
                    continue
                
                if self.args.stop_time and (station.stop_date >= self.args.stop_time):   
                                    continue                
                
                
                station.creation_date = datetime.datetime.fromtimestamp(station_list[1][0]['deploy_time/epoch_l'])
                station.termination_date = datetime.datetime.fromtimestamp(station_list[1][0]['pickup_time/epoch_l'])                
                station.alternate_code=str(array_name)
                station.site=obspy.core.inventory.Site(name=station_list[1][0]['das/serial_number_s'])     
                
                if self.args.level and (self.args.level == "channel" or self.args.level == "response"):
    
                    for deployment in station_list:
                        total_channels=total_channels+1
                        location_match=False
                    
                        c=station_list[deployment][0]['seed_band_code_s']+station_list[deployment][0]['seed_instrument_code_s']+station_list[deployment][0]['seed_orientation_code_s']
                    
                        for pattern in cha_list_patterns:
                            if fnmatch.fnmatch(c, pattern):
                                channels.append(c)
                                
                                if station_list[deployment][0]['seed_location_code_s']:
                                    location = station_list[deployment][0]['seed_location_code_s']
                                else:
                                    location = "--"
                                
                                for pattern in location_patterns:
                                    if fnmatch.fnmatch(location, pattern):
                                        location_match =True
                                        
                                if not location_match:
                                    continue
                                    
                                
                                obs_channel=obspy.core.inventory.Channel(
                                                    code=c, location_code=location, latitude=latitude,
                                                    longitude=longitude, elevation=elevation, depth=0)
                                obs_channel.start_date = datetime.datetime.fromtimestamp(station_list[deployment][0]['deploy_time/epoch_l'])
                                obs_channel.end_date = datetime.datetime.fromtimestamp(station_list[deployment][0]['pickup_time/epoch_l']) 
                                obs_channel.sample_rate = station_list[deployment][0]['sample_rate_i'] 
                                obs_channel.sample_rate_ration = station_list[deployment][0]['sample_rate_multiplier_i']
                                obs_channel.storage_format="PH5"
                                                
                                obs_channel.sensor=obspy.core.inventory.Equipment(
                                                     type="", description="",
                                                    manufacturer=station_list[deployment][0]['sensor/manufacturer_s'], vendor="", model=station_list[deployment][0]['sensor/model_s'],
                                                    serial_number=station_list[deployment][0]['sensor/serial_number_s'], installation_date=datetime.datetime.fromtimestamp(station_list[deployment][0]['deploy_time/epoch_l']),
                                                    removal_date=datetime.datetime.fromtimestamp(station_list[deployment][0]['pickup_time/epoch_l']))
                                                
                                obs_channel.data_logger=obspy.core.inventory.Equipment(
                                                    type="", description="",
                                                    manufacturer=station_list[deployment][0]['das/manufacturer_s'], vendor="", model=station_list[deployment][0]['das/model_s'],
                                                    serial_number=station_list[deployment][0]['das/serial_number_s'], installation_date=datetime.datetime.fromtimestamp(station_list[deployment][0]['deploy_time/epoch_l']),
                                                    removal_date=datetime.datetime.fromtimestamp(station_list[deployment][0]['pickup_time/epoch_l']))   
                                
                                if self.args.start_time and (obs_channel.start_date <= self.args.start_time):   
                                    continue
                                                
                                if self.args.stop_time and (obs_channel.stop_date >= self.args.stop_time):   
                                    continue  
                                
                                if self.args.minlat and float(self.args.minlat) > float(latitude):
                                    continue
                                                
                                if self.args.minlon and float(self.args.minlon) > float(longitude):
                                    continue   
                                                
                                if self.args.maxlat and float(self.args.maxlat) < float(latitude):
                                    continue
                                                                
                                if self.args.maxlon and float(self.args.maxlon) < float(longitude):
                                    continue                    
                                
                                
                            
                                obs_channels.append(obs_channel)
                            
                            
                            
                            
                            
                            
                        longitude= "{0:.6f}".format(station_list[deployment][0]['location/X/value_d'])
                        latitude= "{0:.6f}".format(station_list[deployment][0]['location/Y/value_d'])
                        elevation="{0:.6f}".format(station_list[deployment][0]['location/Z/value_d'])     
                    
                                    
                    
                    
                    
                
                station.selected_number_of_channels = len(channels)
                station.total_number_of_channels = total_channels  
                station.channels=obs_channels
                all_stations.append(station)
                
                    
                            
                
        
        return all_stations
    
    def Parse_Station_list(self, sta_list):
        l =[]
        all_stations=[]
        sta_list_patterns = [x.strip() for x in sta_list.split(',')]
        
        for array_name in self.array_names:
            array = array_name[-3:] 
            arraybyid = self.ph5.Array_t[array_name]['byid']
            arrayorder = self.ph5.Array_t[array_name]['order'] 
            
            for station in arrayorder:
                all_stations.append(str(station))
        
        for pattern in sta_list_patterns:
            l.append(fnmatch.filter(all_stations, pattern))
            
        final_list =list(set([val for sublist in l for val in sublist]))
        return final_list
    
    
    
    
    
    
    
    
    def Process(self):
        networks =[]
        paths = self.args.ph5path.split(',')
        
        
        for path in paths:
            
            self.ph5 = ph5API.ph5(path=path, nickname=args.nickname) 
            self.ph5.read_array_t_names()   
            self.ph5.read_das_g_names()
            self.ph5.read_experiment_t() 
            self.read_arrays(None)
            self.experiment_t = self.ph5.Experiment_t['rows']
            self.array_names = self.ph5.Array_t_names
            self.array_names.sort()   
        
            network = obspy.core.inventory.Network(self.experiment_t[0]['net_code_s'])
            network.alternate_code=self.experiment_t[0]['experiment_id_s']
            
            if args.level and args.level != "network":
                
                sta_list = self.Parse_Station_list(self.args.sta_list)
                network.stations = self.Read_Stations(sta_list)
                
            
            networks.append(network)
            
            self.ph5.close()
            
        inv = obspy.core.inventory.Inventory(networks=networks, source="PIC-PH5",
                                                         sender="IRIS-DMC-PH5", created=datetime.datetime.now(),
                                                         module="PH5 WEB SERVICE: metadata | version: 1", module_uri="")          
        return inv
        
        
        
        
        
        





        
if __name__ == '__main__' :
    output = StringIO.StringIO()
    args = get_args ()
    ph5sxml = PH5toStationXML(args) 
    inv=ph5sxml.Process()
    
     
    
    inv.write(output, format='STATIONXML')  
    
    contents = output.getvalue()
    
    
    f = open(args.outfile, 'w')
    f.write(contents)
    f.close()
  
   
   

    
    
    