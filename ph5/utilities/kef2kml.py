#!/usr/bin/env pnpython4
#
# A simple script to convert Array_t.kef or Event_t.kef into kml.
#
# Steve Azevedo, March 2017
#

import os
import sys
import logging
import simplekml
import re
from ph5.core import kefx

PROG_VERSION = '2019.14'
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


def get_args():
    '''   Get inputs
    '''
    global ARGS

    from argparse import ArgumentParser

    aparser = ArgumentParser()

    aparser.add_argument("-k", "--kef", dest="kefile",
                         help="The input kef file,Array_t.kef or Event_t.kef.",
                         required=True)

    aparser.add_argument("-t", "--title", dest="title",
                         help="Name of the output kml file.",
                         required=True)

    ARGS = aparser.parse_args()

    if not os.path.exists(ARGS.kefile):
        LOGGER.error("Can not read {0}!".format(ARGS.kefile))
        sys.exit()


def read_kef():
    '''   Open KEF and read ARGS.kefile
    '''
    global KEF
    try:
        KEF = kefx.Kef(ARGS.kefile)
        KEF.open()
        KEF.read()
        KEF.rewind()
    except Exception as e:
        LOGGER.error(e.message)
        sys.exit()


def parseArray(kv, a):
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

    pnt = KML.newpoint(name=nam)
    pnt.coords = [(lon, lat, ele)]
    pnt.style.iconstyle.icon.href =\
        'http://maps.google.com/mapfiles/kml/shapes/placemark_square.png'
    pnt.style.iconstyle.color = col
    pnt.style.labelstyle.scale = 0.5
    pnt.style.labelstyle.color = col
    pnt.style.iconstyle.scale = 0.75


def parseEvent(kv, a=1):
    '''   Populate kml from Event_t.kef
    '''
    nam = "{0}-{1}".format(a, kv['id_s'])
    lat = kv['location/Y/value_d']
    lon = kv['location/X/value_d']
    ele = kv['location/Z/value_d']

    pnt = KML.newpoint(name=nam)
    pnt.coords = [(lon, lat, ele)]
    pnt.style.iconstyle.icon.href =\
        'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
    pnt.style.iconstyle.color = simplekml.Color.red
    pnt.style.labelstyle.color = simplekml.Color.red
    pnt.style.labelstyle.scale = 0.75


def process_kef():
    '''   Process kef file into kml
    '''
    global KML
    KML = simplekml.Kml()
    for p, kv in KEF:
        if arrayRE.match(p):
            mo = arrayRE.match(p)
            a = int(mo.groups()[0])
            parseArray(kv, a)
        elif eventRE.match(p):
            mo = eventRE.match(p)
            try:
                a = int(mo.groups()[0])
            except TypeError:
                a = 1
            parseEvent(kv, a)
        else:
            LOGGER.error("Can't convert {0}! Exiting.".format(p))
            sys.exit()

    KML.save(ARGS.title)


def main():
    get_args()
    read_kef()
    process_kef()


if __name__ == '__main__':
    main()
