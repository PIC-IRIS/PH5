#!/usr/bin/env pnpython4
#
# A simple script to convert Array_t.kef or Event_t.kef into kml.
#
# Steve Azevedo, March 2017
#

import os
import logging
import simplekml
import re
from ph5.core import kefx

PROG_VERSION = '2019.058'
LOGGER = logging.getLogger(__name__)

arrayRE = re.compile(r".*Array_t_*(\d+)*")
eventRE = re.compile(r".*Event_t_*(\d+)*")

# Point colors
COLORS = {0: simplekml.Color.whitesmoke, 1: simplekml.Color.blue,
          2: simplekml.Color.green, 3: simplekml.Color.plum,
          4: simplekml.Color.lightblue,
          5: simplekml.Color.grey, 6: simplekml.Color.purple,
          7: simplekml.Color.pink, 8: simplekml.Color.brown,
          9: simplekml.Color.darkolivegreen, 10: simplekml.Color.wheat}


class Kef2KML():
    def get_args(self):
        '''   Get inputs
        '''
        from argparse import ArgumentParser

        aparser = ArgumentParser()

        aparser.add_argument(
            "-k", "--kef", dest="kefile", required=True,
            help="The input kef file,Array_t.kef or Event_t.kef.",
                             )

        aparser.add_argument(
            "-t", "--title", dest="title", required=True,
            help="Name of the output kml file.")

        self.ARGS = aparser.parse_args()

        if not os.path.exists(self.ARGS.kefile):
            raise Exception("Can not read {0}!".format(self.ARGS.kefile))

    def read_kef(self):
        '''   Open KEF and read ARGS.kefile
        '''
        try:
            self.KEF = kefx.Kef(self.ARGS.kefile)
            self.KEF.open()
            self.KEF.read()
            self.KEF.rewind()
        except Exception as e:
            raise Exception(e.message)

    def parseArray(self, kv, a):
        '''   Populate kml from Array_t.kef
        '''
        if int(kv['channel_number_i']) != 1:
            return

        nam = "{0}-{1}".format(a, kv['id_s'])
        lat = kv['location/Y/value_d']
        lon = kv['location/X/value_d']
        ele = kv['location/Z/value_d']
        x = a % len(COLORS)
        while True:
            if x <= 10:
                break
            else:
                x -= 10
        col = COLORS[x]

        pnt = self.KML.newpoint(name=nam)
        pnt.coords = [(lon, lat, ele)]
        pnt.style.iconstyle.icon.href =\
            'http://maps.google.com/mapfiles/kml/shapes/placemark_square.png'
        pnt.style.iconstyle.color = col
        pnt.style.labelstyle.scale = 0.5
        pnt.style.labelstyle.color = col
        pnt.style.iconstyle.scale = 0.75

    def parseEvent(self, kv, a=1):
        '''   Populate kml from Event_t.kef
        '''
        nam = "{0}-{1}".format(a, kv['id_s'])
        lat = kv['location/Y/value_d']
        lon = kv['location/X/value_d']
        ele = kv['location/Z/value_d']

        pnt = self.KML.newpoint(name=nam)
        pnt.coords = [(lon, lat, ele)]
        pnt.style.iconstyle.icon.href =\
            'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
        pnt.style.iconstyle.color = simplekml.Color.red
        pnt.style.labelstyle.color = simplekml.Color.red
        pnt.style.labelstyle.scale = 0.75

    def process_kef(self):
        '''   Process kef file into kml
        '''
        self.KML = simplekml.Kml()
        for p, kv in self.KEF:
            if arrayRE.match(p):
                mo = arrayRE.match(p)
                a = int(mo.groups()[0])
                try:
                    self.parseArray(kv, a)
                except Exception as e:
                    raise e
            elif eventRE.match(p):
                mo = eventRE.match(p)
                try:
                    a = int(mo.groups()[0])
                except TypeError:
                    a = 1
                self.parseEvent(kv, a)
            else:
                raise Exception("Can't convert {0}! Exiting.".format(p))

        self.KML.save(self.ARGS.title)


def main():
    try:
        conv = Kef2KML()
        conv.get_args()
        conv.read_kef()
        conv.process_kef()
    except Exception, err_msg:
        LOGGER.error(err_msg)
        return 1


if __name__ == '__main__':
    main()
