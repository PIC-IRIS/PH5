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

import ph5API

import numpy

import argparse

import fnmatch

import StringIO

from pykml.factory import KML_ElementMaker as KML

from lxml import etree

from datetime import datetime


PROG_VERSION = "2016.291 Developmental"


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
    
    parser.add_argument("--basepath", action="store",
                            type=str, metavar="basepath", help="Specify a base directory containing any number of PH5 experiments. All PH5 files foudn will be used")  
    
    parser.add_argument("--network", action="store", dest="network_list",
                           help="Comma separated list of networks. Wildcards accepted",
                           type=str, metavar="network_list")
   
    parser.add_argument("--reportnum", action="store", dest="reportnum_list",
                           help="Comma separated list of report numbers. Wildcards accepted",
                           type=str, metavar="reportnum_list")   
    
    parser.add_argument("-f","--format", action="store", dest="format",
                        help="Out format: either XML or KML",
                        type=str, metavar="format")   
    
    parser.add_argument("-s", "--starttime", action="store",
                        help="start time in FDSN time format or PASSCAL time format",
                        type=str, dest="start_time", metavar="start_time")    

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
    
    args = parser.parse_args() 
    
    return args 


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
        
    
    


class PH5toexml(object):
    
    def __init__(self, args):
        
        self.args = args 
        
        nickname = args.get('nickname')
        if nickname[-3:] == 'ph5':
            PH5FILE = os.path.join(args.get('ph5path'), args.get('nickname'))
        else:
            PH5FILE = os.path.join(args.get('ph5path'), args.get('nickname') + '.ph5')
            args['nickname'] = args['nickname'] + '.ph5' 
            
        if not self.args.get('network_list'):
            self.args['network_list'] = "*"
            
        if not self.args.get('reportnum_list'):
            self.args['reportnum_list'] = "*"  
            
        if self.args.get('start_time') and "T" in self.args.get('start_time'):
            self.args['start_time'] = datetime.strptime(
                    self.args.get('start_time'), "%Y-%m-%dT%H:%M:%S+%f")
                
        elif self.args.get('start_time'):
            self.args['start_time'] = datetime.strptime(
                    self.args.get('start_time'), "%Y:%j:%H:%M:%S.%f")
        
            
    def get_fdsn_time(self, epoch, microseconds):
            
        fdsn_time=datetime.utcfromtimestamp(epoch+microseconds).strftime("%Y-%m-%dT%H:%M:%S+%f")
            
        return fdsn_time    
            
    def read_events(self, name):
            try:
                if name is None:
                    for n in self.ph5.Event_t_names:
                        self.ph5.read_event_t(n)
                else:
                    self.ph5.read_event_t(name) 
            except Exception as e :            
                return -1
            
            return 0
                
        
            
    def Parse_Networks(self, path):
            network_patterns = [x.strip()
                                for x in self.args.get('network_list').split(',')]
            reportnum_patterns = [x.strip()
                                for x in self.args.get('reportnum_list').split(',')]
            
            self.ph5 = ph5API.ph5(path=path, nickname=self.args.get('nickname'))
            self.ph5.read_experiment_t()
            self.experiment_t = self.ph5.Experiment_t['rows']
            self.ph5.read_event_t_names()
            test=self.read_events(None)
            shot_lines = self.ph5.Event_t_names
            shot_lines.sort()  
            
            if test == -1:
                self.ph5.close()
                return None
            
            
            # read network code and compare to network list
            l = []
            for pattern in network_patterns:
                if fnmatch.fnmatch(self.experiment_t[0]['net_code_s'], pattern):
                    l.append(1)
            if not l:
                self.ph5.close()
                return None
            
            # read reportnum and compare to reportnum list
            l = []
            for pattern in reportnum_patterns:
                if fnmatch.fnmatch(self.experiment_t[0][
                                    'experiment_id_s'], pattern):
                    l.append(1)
            if not l:
                self.ph5.close()
                return None
            
            network =Network(self.experiment_t[0]['net_code_s'], 
                             self.experiment_t[0]['experiment_id_s'],
                             self.experiment_t[0]['longname_s'])
            
            
            
            shot_lines_=[]
            shots=[]
            
            for shot_line in shot_lines:
                sl=Shotline(shot_line)
                event_t = self.ph5.Event_t[shot_line]['byid']
                
                for key, value in event_t.iteritems():
                    
                    if self.args.get('minlat') and float(
                            self.args.get('minlat')) > float(value['location/Y/value_d']):
                        continue
                    
                    if self.args.get('minlon') and float(
                            self.args.get('minlon')) > float(value['location/X/value_d']):
                        continue
                    
                    if self.args.get('maxlat') and float(
                            self.args.get('maxlat')) < float(value['location/Y/value_d']):
                        continue
                    
                    if self.args.get('maxlon') and float(
                            self.args.get('maxlon')) < float(value['location/X/value_d']):
                        continue
                    
                    if self.args.get('start_time') and (
                        datetime.fromtimestamp(value['time/epoch_l']) <= self.args.get('start_time')):
                        continue                    
                    
                    
                    shot=Shot(key, value['size/value_d'],value['size/units_s'], 
                              self.get_fdsn_time(value['time/epoch_l'], value['time/micro_seconds_i']), 
                              value['location/Y/value_d'], value['location/X/value_d'], 
                              value['location/Z/value_d'], value['location/X/units_s'], 
                              value['location/Z/units_s'], value['description_s'])
                    shots.append(shot)

                sl.shots=shots
                shot_lines_.append(sl)
                
            network.shot_lines=shot_lines_
           
            self.ph5.close()
            
            return network
        
        
    def Process(self):
            
        networks = []
        paths = self.args.get('ph5path').split(',')
            
        if self.args.get('basepath'):
            paths = []
            for dirName, subdirList, fileList in os.walk(self.args.get('basepath')):
                for fname in fileList:
                    if fname == "master.ph5":
                        paths.append(dirName) 
                            
        for path in paths:
                            
            network = self.Parse_Networks(path)
            if network:
                networks.append(network)
                    
        return networks
    
    
    def write(self,outfile, list_of_networks, out_format):
        
        def write_xml(list_of_networks):
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

            target = open(outfile, 'w')
            
            for line in out:
                target.write(line.encode(encoding='UTF-8',errors='strict')+"\n")
                
            
                
            
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
            
            target = open(outfile, 'w')    
            target.write(etree.tostring(etree.ElementTree(doc),pretty_print=True))
            
    
                
            return
        
        
        if out_format.upper() == "XML":
            write_xml(list_of_networks)
            
        elif out_format.upper() == "KML":
            
            write_kml(list_of_networks)
        else:
            print "output format not supported. XML or KML only"

        return
            
                
    
    




if __name__ == '__main__':

    args = get_args()
    args_dict = vars(args)
    
    ph5exml = PH5toexml(args_dict)
    networks= ph5exml.Process()
    ph5exml.write(args_dict.get('outfile'),networks, args_dict.get("format"))
    