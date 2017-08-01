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

import os
import argparse
from pykml.factory import KML_ElementMaker as KML
from lxml import etree
from datetime import datetime
from obspy import Catalog, UTCDateTime
import obspy.core.event
import collections
# functions for reading networks in parallel
import multiprocessing
import copy_reg
import types

from ph5.core import ph5api, ph5utils


PROG_VERSION = "2017.139"


def get_args():
    
    parser = argparse.ArgumentParser(
            description='Takes PH5 files and returns eventxml.',
            usage='Version: {0} ph5toexml --nickname="Master_PH5_file" [options]'.format(PROG_VERSION))
    
    parser.add_argument("-n", "--nickname", action="store", required=True,
                            type=str, metavar="nickname")
    
    parser.add_argument("-p", "--ph5path", action="store",
                            help="Comma separated list of paths to ph5 experiments",
                            type=str, metavar="ph5path")
    
    parser.add_argument("-o", "--outfile", action="store", default="something.xml",
                        type=str, metavar="outfile")    
    
    parser.add_argument("--network", action="store", dest="network_list",
                           help="Comma separated list of networks. Wildcards accepted",
                           type=str, metavar="network_list")
   
    parser.add_argument("--reportnum", action="store", dest="reportnum_list",
                           help="Comma separated list of report numbers. Wildcards accepted",
                           type=str, metavar="reportnum_list")   
    
    parser.add_argument("-f","--format", action="store", dest="format", default="XML",
                        help="Out format: either QUAKEML, KML, EXML, or SHOTTEXT",
                        type=str, metavar="format")   
    
    parser.add_argument("-s", "--starttime", action="store",
                        help="start time in FDSN time format or PASSCAL time format",
                        type=str, dest="start_time", metavar="start_time")   
    
    parser.add_argument("-t", "--stoptime", action="store",
                            help="start time in FDSN time format or PASSCAL time format",
                            type=str, dest="stop_time", metavar="stop_time")      

    parser.add_argument("--minlat", action="store",
                        help="Limit to events with a latitude larger than or equal to the specified minimum.",
                        type=float, dest="minlat", metavar="minlat")

    parser.add_argument("--maxlat", action="store",
                        help="Limit to events with a latitude smaller than or equal to the specified maximum.",
                        type=float, dest="maxlat", metavar="maxlat")

    parser.add_argument("--minlon", action="store",
                        help="Limit to events with a longitude larger than or equal to the specified minimum.",
                        type=float, dest="minlon", metavar="minlon")

    parser.add_argument("--maxlon", action="store",
                        help="Limit to events with a longitude smaller than or equal to the specified maximum.",
                        type=float, dest="maxlon", metavar="maxlon")    

    parser.add_argument("--latitude", action="store",
                        help="Specify the central latitude point for a radial geographic constraint.")
    
    parser.add_argument("--longitude", action="store",
                        help="Specify the central longitude point for a radial geographic constraint., ")
    
    parser.add_argument("--minradius", action="store",
                    help="Specify minimum distance from the geographic point defined by latitude and longitude.")
    
    parser.add_argument("--maxradius", action="store",
                        help="Specify maximum distance from the geographic point defined by latitude and longitude.")
    
    parser.add_argument('--shotid', help="Specifies the shot (event) id for a request by shot. Accepts a comma" +
        "separated list if requesting multiple events.")

    parser.add_argument('--shotline', help="The shot line number that holds the shots.")
    
    args = parser.parse_args() 
    
    return args


class PH5toEventError(Exception):
    """Exception raised when there is a problem with the request.
    :param: message -- explanation of the error
    """
    def __init__(self, message=""):
        self.message = message


class NoDataError(Exception):
    """Exception raised when the request resulted in no data being returned.
    :param: message -- explanation of the error
    """
    def __init__(self, message=""):
        self.message = message


class Network(object):
    
    def __init__(self, code, reportnum, description):
        self.code = code
        self. reportnum=reportnum
        self.description=description
        self.shot_lines=[]

class Shotline(object):
    def __init__(self, name):
        self.name =name
        self.description=''
        self.shots=[]

class Shot(object):

    def __init__(self, shot_id, mag, mag_units, start_time, lat, lon, elev, lat_lon_units, elev_units, description):
        self.shot_id=shot_id
        self.mag=mag
        self.mag_units=mag_units
        self.start_time=start_time
        self.lat_lon_units=lat_lon_units
        self.lat=lat
        self.lon=lon
        self.elev=elev
        self.elev_units=elev_units
        self.description=description
        self.depth=float(0.0)

class PH5toexml(object):

    def __init__(self, args):
        self.args = args 
        nickname = args.get('nickname')
        if nickname[-3:] != 'ph5':
            args['nickname'] = args['nickname'] + '.ph5' 
            
        if not self.args.get('network_list'):
            self.args['network_list'] = []
            
        if not self.args.get('reportnum_list'):
            self.args['reportnum_list'] = []  
            
        if self.args.get('start_time') and "T" in self.args.get('start_time'):
            self.args['start_time'] = datetime.strptime(
                    self.args.get('start_time'), "%Y-%m-%dT%H:%M:%S.%f")
                
        elif self.args.get('start_time'):
            self.args['start_time'] = datetime.strptime(
                    self.args.get('start_time'), "%Y:%j:%H:%M:%S.%f")
            
        if self.args.get('stop_time') and "T" in self.args.get('stop_time'):
                        self.args['stop_time'] = datetime.strptime(
                                self.args.get('stop_time'), "%Y-%m-%dT%H:%M:%S.%f")
                            
        elif self.args.get('stop_time'):
            self.args['stop_time'] = datetime.strptime(
                    self.args.get('stop_time'), "%Y:%j:%H:%M:%S.%f")

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

    def get_fdsn_time(self, epoch, microseconds):
        seconds = ph5utils.microsecs_to_sec(microseconds)
        fdsn_time=datetime.utcfromtimestamp(epoch+seconds).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return fdsn_time   
    
    def read_arrays(self, name):
        if name is None:
            for n in self.ph5.Array_t_names:
                self.ph5.read_array_t(n)
        else:
            self.ph5.read_array_t(name)    

    def read_events(self, name):
            try:
                if name is None:
                    for n in self.ph5.Event_t_names:
                        self.ph5.read_event_t(n)
                else:
                    self.ph5.read_event_t(name) 
            except Exception:            
                return -1
            return 0

    def Parse_Networks(self, path):
        network_list = self.args.get('network_list')
        if isinstance(network_list, collections.Iterable):
            network_patterns = network_list
        else:
            network_patterns =self.args.get('network_list').split(',')
           
        reportnum_list = self.args.get('reportnum_list')
        if isinstance(reportnum_list, collections.Iterable):
            reportnum_patterns = reportnum_list
        else:
            reportnum_patterns = self.args.get('reportnum_list').split(',')
        
        self.ph5 = ph5api.PH5(path=path, nickname=self.args.get('nickname'))
        self.ph5.read_experiment_t()
        self.experiment_t = self.ph5.Experiment_t['rows']
        self.ph5.read_event_t_names()
        self.ph5.read_array_t_names()
        test=self.read_events(None)
        shot_lines = self.ph5.Event_t_names
        shot_lines.sort()  
        if test == -1: 
            self.ph5.close()
            return None
        if network_patterns and reportnum_patterns:
            if not ph5utils.does_pattern_exists(network_patterns, self.experiment_t[0]['net_code_s']) and \
               not ph5utils.does_pattern_exists(reportnum_patterns, self.experiment_t[0]['experiment_id_s']):
                self.ph5.close()
                return None
        elif network_patterns:
            # read network code and compare to network list
            if not ph5utils.does_pattern_exists(network_patterns, self.experiment_t[0]['net_code_s']):
                self.ph5.close()
                return None
        elif reportnum_patterns:
            # read reportnum and compare to reportnum list
            if not ph5utils.does_pattern_exists(reportnum_patterns, self.experiment_t[0]['experiment_id_s']):
                self.ph5.close()
                return None
        else:
            self.ph5.close()
            return None
        
        self.read_arrays(None)
        array_names = self.ph5.Array_t_names
        array_names.sort()  
        
        # get the earliest deploy and latest pickup dates from the arrays table
        earliest_deploy = None
        latest_pickup =  None
        for array_name in array_names:
            arraybyid = self.ph5.Array_t[array_name]['byid']
            arrayorder = self.ph5.Array_t[array_name]['order']
            for x in arrayorder:
                station = arraybyid.get(x)
                deploy_time = station[1][0]['deploy_time/epoch_l']+ph5utils.microsecs_to_sec(station[1][0]['deploy_time/micro_seconds_i'])
                pickup_time = station[1][0]['pickup_time/epoch_l']+ph5utils.microsecs_to_sec(station[1][0]['pickup_time/micro_seconds_i'])
                if earliest_deploy == None or earliest_deploy > deploy_time:
                    earliest_deploy = deploy_time
                if latest_pickup == None or latest_pickup < pickup_time:
                    latest_pickup = pickup_time
      
        if self.args.get('start_time') and self.args.get('start_time') < datetime.fromtimestamp(earliest_deploy):
            self.args['start_time'] = datetime.fromtimestamp(earliest_deploy)
            
        if self.args.get('stop_time') and self.args.get('stop_time') > datetime.fromtimestamp(latest_pickup):
            self.args['stop_time'] = datetime.fromtimestamp(latest_pickup)

        network = Network(self.experiment_t[0]['net_code_s'], 
                         self.experiment_t[0]['experiment_id_s'],
                         self.experiment_t[0]['longname_s'])

        shot_lines_=[]
        shots=[]

        for shot_line in shot_lines:
            sl=Shotline(shot_line)
            event_t = self.ph5.Event_t[shot_line]['byid']
            if self.args.get('shotline') and \
               not ph5utils.does_pattern_exists(self.args.get('shotline'), str(shot_line[-3:])):
                continue
            for key, value in event_t.iteritems():
                if self.args.get('shotid') and \
                    not ph5utils.does_pattern_exists(self.args.get('shotid'), key):
                    continue
                cha_longitude = float(value['location/X/value_d'])
                cha_latitude = float(value['location/Y/value_d'])
                if not self.is_lat_lon_match(cha_latitude, cha_longitude):
                    continue
                
                if self.args.get('start_time') and (
                    datetime.fromtimestamp(value['time/epoch_l']) < self.args.get('start_time')):
                    continue 
                    
                if self.args.get('stop_time') and (
                    datetime.fromtimestamp(value['time/epoch_l']) > self.args.get('stop_time')):
                    continue
                
                restricted = self.args.get('restricted')
                if restricted:
                    is_restricted = False
                    for r in restricted:
                        if r.network == network.code and \
                           value['time/epoch_l'] >= r.starttime and \
                           value['time/epoch_l'] <= r.endtime:
                            is_restricted = True
                            break
                    if is_restricted:
                        continue

                shot=Shot(key, value['size/value_d'],value['size/units_s'], 
                          self.get_fdsn_time(value['time/epoch_l'], value['time/micro_seconds_i']), 
                          value['location/Y/value_d'], value['location/X/value_d'], 
                          value['location/Z/value_d'], value['location/X/units_s'], 
                          value['location/Z/units_s'], value['description_s'])
                shot.depth=value['depth/value_d']
                shots.append(shot)

            sl.shots=shots
            shot_lines_.append(sl)
            
        network.shot_lines=shot_lines_

        self.ph5.close()
        
        return network

    def write(self,outfile, list_of_networks, out_format):
        
        def write_exml(list_of_networks):
            out=[]

            out.append("<?xml version='1.0' encoding='UTF-8'?>")
            out.append("<PH5eventXML schemaVersion='1.0' xmlns='https://www.passcal.nmt.edu/~dhess/PH5EventXML/'>")
            for network in list_of_networks:
                out.append("  <Network reportnum='"+network.reportnum+"' code='"+network.code+"'>")
                out.append("    <Description>"+network.description+"</Description>")
                for shot_line in network.shot_lines:
                    out.append("    <ShotLine code='"+shot_line.name[-3:]+"' >")
                    for shot in shot_line.shots:
                        out.append("      <Shot code='"+shot.shot_id+"' StartTime='"+str(shot.start_time)+"'>")
                        if shot.description != '':
                            out.append("        <Description>"+shot.description+"</Description>")
                        out.append("        <Latitude unit='"+shot.lat_lon_units.upper()+"'>"+str(shot.lat)+"</Latitude>")
                        out.append("        <Longitude unit='"+shot.lat_lon_units.upper()+"'>"+str(shot.lon)+"</Longitude>")
                        out.append("        <Elevation unit='"+shot.elev_units.upper()+"'>"+str(shot.elev)+"</Elevation>")
                        out.append("        <Magnitude unit='"+shot.mag_units.upper()+"'>"+str(shot.mag)+"</Magnitude>")
                        out.append("      </Shot>")
                    out.append("    </ShotLine>")
                out.append("  </Network>")
            out.append("</PH5eventXML>")
            
            if out:
                if hasattr(outfile, 'write'):
                    target = outfile
                else:
                    target = open(outfile, 'w')
                
                for line in out:
                    target.write(line.encode(encoding='UTF-8',errors='strict')+"\n")
            else:
                raise NoDataError()

        def write_kml(list_of_networks):

            doc=KML.Document(
                KML.name("PH5 Events"),
                KML.Style(
                    KML.IconStyle(
                        KML.color('FF1400FF'),
                        KML.scale('1.25'),
                        KML.Icon(
                                KML.href('http://maps.google.com/mapfiles/kml/shapes/open-diamond.png')
                                )
                            ),
                                id = 'star'
                        ),                
                )
            
            for network in list_of_networks:
                network_folder=KML.Folder(KML.name("Network Code: "+str(network.code)+" reportnum: "+network.reportnum))
                for shot_line in network.shot_lines:
                    folder = KML.Folder(KML.name("ShotLine "+str(shot_line.name[-3:])))
                    for shot in shot_line.shots:
                        place_marker=(KML.Placemark(
                            KML.styleUrl("#star"),
                            KML.name(network.code+'.'+str(shot.shot_id)),
                            KML.description('Shot size: '+str(shot.mag)+' '+shot.mag_units+'\n Shot Time: '+shot.start_time+'\n\n'+shot.description),
                            KML.Point(
                                KML.coordinates(str(shot.lon)+','+str(shot.lat)+','+str(shot.elev))
                                )
                        ))
                        folder.append(place_marker)
                    network_folder.append(folder)
                doc.append(network_folder)
            
            if doc:
                if hasattr(outfile, 'write'):
                    target = outfile
                else:
                    target = open(outfile, 'w')
    
                target.write(etree.tostring(etree.ElementTree(doc),pretty_print=True))
            else:
                raise NoDataError()
        
        def write_text(list_of_networks):

            out=[]
            for network in list_of_networks:
                for shot_line in network.shot_lines:
                    for shot in shot_line.shots:
                        out.append(str(network.code)+"|"+network.reportnum+"|"+str(shot_line.name[-3:])+"|"+str(shot.shot_id)+"|"+shot.start_time+"|"+str(shot.lat)+"|"+str(shot.lon)+"|"+str(shot.elev)+"|"+str(shot.mag)+"|"+shot.mag_units)
            if out:
                header = ["#Network|ReportNum|ShotLine|Shot|ShotTime|Latitude|Longitude|Elevation|ShotSize|ShotUnits"]
                out = header + out
                if hasattr(outfile, 'write'):
                    target = outfile
                else:
                    target = open(outfile, 'w')
            
                for line in out:
                    target.write(line.encode(encoding='UTF-8',errors='strict')+"\n") 
            else:
                raise NoDataError()
        
        def write_quakeml(list_of_networks):
            events=[]
            catalog=Catalog()
            for network in list_of_networks:
                for shot_line in network.shot_lines:
                    for shot in shot_line.shots:
                        origins =[]
                        magnitudes=[]
                        iris_custom_ns = "http://www.fdsn.org/xml/event/1/iris"
                        origin= obspy.core.event.origin.Origin()
                        origin.time=shot.start_time
                        origin.latitude=shot.lat
                        origin.longitude=shot.lon
                        origin.extra={'Elevation':{'value':str(shot.elev), 'namespace': iris_custom_ns}}
                        if shot.depth != 0:
                            origin.depth=shot.depth
                        origins.append(origin)
                        magnitudes.append(obspy.core.event.magnitude.Magnitude(mag=shot.mag, magnitude_type=shot.mag_units))
                        
                        identifier = obspy.core.event.base.ResourceIdentifier(id=str(network.code)+"."+str(shot_line.name[-3:])+"."+str(shot.shot_id))
                        event=(obspy.core.event.Event(resource_id=identifier, event_type="Controlled Explosion", origins=origins, magnitudes=magnitudes))
                        event.extra={'Network':{'value': str(network.code), 'type': 'attribute', 'namespace': iris_custom_ns},
                                     'ReportNum':{'value': str(network.reportnum), 'type': 'attribute','namespace': iris_custom_ns}, 
                                     'ShotLine':{'value': str(shot_line.name[-3:]),'type': 'attribute', 'namespace':iris_custom_ns},
                                     'Shot_id':{'value': str(shot.shot_id),'type': 'attribute', 'namespace': iris_custom_ns}
                                     }
                        events.append(event)

                catalog.events=events
            
            if catalog.events:
                catalog.write(outfile, "QUAKEML",  nsmap={"iris": iris_custom_ns})
            else:
                raise NoDataError()
        
        
        if out_format.upper() == "EXML":
            write_exml(list_of_networks)
        elif out_format.upper() == "KML":
            write_kml(list_of_networks)
        elif out_format.upper() == "SHOTTEXT":
            write_text(list_of_networks)  
        elif out_format.upper() == "XML":
            write_quakeml(list_of_networks)          
        else:
            raise PH5toEventError("Output format not supported - {0}.".format(out_format.upper()))

    def get_network(self, path):
        return self.Parse_Networks(path)


def _pickle_method(m):
    if m.im_self is None:
        return getattr, (m.im_class, m.im_func.func_name)
    else:
        return getattr, (m.im_self, m.im_func.func_name)

copy_reg.pickle(types.MethodType, _pickle_method)


def run_ph5_to_event(ph5exml):
    basepaths = ph5exml.args.get('ph5path')
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
        networks = pool.map(ph5exml.get_network, paths)
        networks = [n for n in networks if n]
        pool.close()
        pool.join()
        return networks
    else:
        raise PH5toEventError("No PH5 experiments were found "
                              "under basepath(s) {0}".format(basepaths))


if __name__ == '__main__':

    args = get_args()
    args_dict = vars(args) 
    
    if args_dict.get('network_list'):
        args_dict['network_list'] = [x.strip()
                        for x in args_dict.get('network_list').split(',')]
    if args_dict.get('reportnum_list'):
        args_dict['reportnum_list'] = [x.strip()
                        for x in args_dict.get('reportnum_list').split(',')]
    if args_dict.get('ph5path'):
        args_dict['ph5path'] = args_dict.get('ph5path').split(',')     
    if args_dict.get('shotid'):
        args_dict['shotid'] = [x.strip()
                        for x in args_dict.get('shotid').split(',')]
    if args_dict.get('shotline'):
        args_dict['shotline'] = [x.strip()
                        for x in args_dict.get('shotline').split(',')]    

    ph5exml = PH5toexml(args_dict)
    networks= run_ph5_to_event(ph5exml)
    ph5exml.write(args_dict.get('outfile'),networks, args_dict.get("format"))
    