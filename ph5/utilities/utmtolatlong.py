# This script can be used to convert UTM coordinates to Latitude/Longitude
# Dave Thomas, 2019-08-01

from __future__ import (print_function)
from ph5.core import ph5utils
import argparse
import logging

PROG_VERSION = '2019.239'
LOGGER = logging.getLogger(__name__)


def convert_file(infile, outfile):
    counter = 0
    with open(outfile, "w") as theoutfile, open(infile) as theinfile:
        ws = "Easting, Northing, Zone, Hemisphere, => Longitude, Latitude\n"
        theoutfile.write(ws)
        for line in theinfile:
            counter = counter + 1
            if counter == 1:
                continue  # skip header line
            fieldset = line.strip().split(",")
            if len(fieldset) <= 1:
                continue
            easting = float(fieldset[0])
            northing = float(fieldset[1])
            zone = int(fieldset[2])
            hemisphere = str(fieldset[3]).upper()
            try:
                utm = ph5utils.UTMConversions()
                lat, lon = utm.lat_long(easting, northing, zone, hemisphere)
                ps = "easting=%.1f, northing=%.1f, zone=%d, hemisphere=%s"
                printstr1 = (ps % (easting, northing, zone, hemisphere))
                printstr2 = "Lon = %.7f, Lat = %.7f" % (lon, lat)
                print (printstr1 + " => " + printstr2)
                outstr = "%.1f, %.1f, %d, %s, %.7f, %.7f" \
                    % (easting, northing, zone, hemisphere, lon, lat)
                theoutfile.write(outstr + "\n")
            except ValueError:
                print ("There was an error in UTM file conversion.")
                return


def doinline(easting, northing, zone, hemisphere):
    print ("easting=%s, northing=%s, zone=%s, hemisphere=%s"
           % (easting, northing, zone, hemisphere))
    try:
        utm = ph5utils.UTMConversions()
        indat = ("Input: easting=%.1f, northing=%.1f, zone=%d, hemisphere=%s"
                 % (float(easting), float(northing), int(zone), hemisphere))
        print (indat)
        lat, lon = utm.lat_long(float(easting), float(northing),
                                int(zone), hemisphere)
        outstr = "Lon = %.7f, Lat = %.7f" % (lon, lat)
        print (outstr)
        print (''.join('*'*50))
    except ValueError:
        print ("There was an error in UTM data conversion.")
        return


def main():
    desc = 'Convert UTM locations to longitudes, latitudes, \
in batches (-i, -o) or inline (-e,-n,-z,-s)'
    parser = argparse.ArgumentParser(description=desc)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--infile", help="Input file with UTM \
Easting, Northing, Zone, Hemisphere")
    parser.add_argument("-o", "--outfile", help="Output file with \
converted longitudes, latitudes")
    group.add_argument("-e", "--easting", help="Enter UTM Easting")
    parser.add_argument("-n", "--northing", help="Enter UTM Northing")
    parser.add_argument("-z", "--zone", help="Enter UTM Zone")
    parser.add_argument("-s", "--side", help="Side=Hemisphere, N or S")

    args = parser.parse_args()

    if args.infile is not None and args.outfile is not None:
        convert_file(args.infile, args.outfile)

    else:  # direct method
        doinline(args.easting, args.northing, args.zone, args.side)


if __name__ == '__main__':
    main()
