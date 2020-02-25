# This script is used to convert UTM coordinates to/from Latitude/Longitude
# Dave Thomas, 2020-02-24

from __future__ import (print_function)
from ph5.core import ph5utils
import argparse
import logging

PROG_VERSION = '2020.055'
LOGGER = logging.getLogger(__name__)


def convert_file_from_utm(infile, outfile):  # batch file method
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
                lat, lon = ph5utils.utm_to_lat_long(easting, northing,
                                                    hemisphere, zone)
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


def convert_file_from_latlong(infile, outfile):  # batch file method
    counter = 0
    with open(outfile, "w") as theoutfile, open(infile) as theinfile:
        ws = "Longitude, Latitude, =>Easting, Northing, Zone, Hemisphere\n"
        theoutfile.write(ws)
        for line in theinfile:
            counter = counter + 1
            if counter == 1:
                continue  # skip header line
            fieldset = line.strip().split(",")
            if len(fieldset) <= 1:
                continue
            lat = float(fieldset[0])
            lon = float(fieldset[1])
            try:
                utm = ph5utils.LatLongToUtmConvert(lat, lon)
                easting, northing, zone, hemisphere = utm.lat_long_to_utm()
                ps = "easting=%.1f, northing=%.1f, zone=%d, hemisphere=%s"
                printstr1 = "Lon = %.7f, Lat = %.7f" % (lon, lat)
                printstr2 = (ps % (easting, northing, zone, hemisphere))
                print (printstr1 + " => " + printstr2)
                outstr = "%.7f, %.7f, %.1f, %.1f, %d, %s" \
                    % (lon, lat, easting, northing, zone, hemisphere)
                theoutfile.write(outstr + "\n")
            except ValueError:
                print ("There was an error in UTM file conversion.")
                return


def doinline_from_utm(easting, northing, zone, hemisphere):  # interactive
    print ("easting=%s, northing=%s, zone=%s, hemisphere=%s"
           % (easting, northing, zone, hemisphere))
    try:
        indat = ("Input: easting=%.1f, northing=%.1f, zone=%d, hemisphere=%s"
                 % (float(easting), float(northing), int(zone), hemisphere))
        print (indat)

        lat, lon = ph5utils.utm_to_lat_long(easting, northing,
                                            hemisphere, zone)
        outstr = "Lon = %.7f, Lat = %.7f" % (lon, lat)
        print (outstr)
        print (''.join('*'*50))
    except ValueError:
        print ("There was an error in UTM data conversion.")
        return


def doinline_from_latlong(lon, lat):  # interactive
    try:
        if abs(float(lat)) > 90.0:
            msg = "Geodetic Error, your latitude, %.7f, is out of limit." \
                   % (float(lat))
            print (msg)
            return
        utm = ph5utils.LatLongToUtmConvert(lat, lon)
        indat = "Input: lon=%.7f, lat=%.7f" % (float(lon), float(lat))
        print (indat)
        easting, northing, zone, hemisphere = utm.lat_long_to_utm()
        outstr = "easting=%.1f, northing=%.1f, zone=%s, hemisphere=%s" \
            % (float(easting), float(northing), zone, hemisphere)
        print (outstr)
        print (''.join('*'*50))
    except ValueError:
        print ("There was an error in UTM data conversion.")
        return


def main():
    desc = 'Convert UTM locations to/from longitudes, latitudes, \
in batches (-i, -o) or inline (-e,-n,-z,-s), (-x,-y)'
    parser = argparse.ArgumentParser(description=desc)
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument("-u", "--utm", help="Convert UTM to Lat/Long",
                        action="store_true")
    group1.add_argument("-l", "--latlong", help="Convert Lat/Long to UTM",
                        action="store_true")
    parser.add_argument("-i", "--infile", help="Input file with UTM \
Easting, Northing, Zone, Hemisphere, or Lats and Longs")
    parser.add_argument("-o", "--outfile", help="Output file with \
converted longitudes, latitudes or UTM Coordinates")
    parser.add_argument("-e", "--easting", help="Enter UTM Easting")
    parser.add_argument("-n", "--northing", help="Enter UTM Northing")
    parser.add_argument("-z", "--zone", help="Enter UTM Zone")
    parser.add_argument("-s", "--side", help="Side=Hemisphere, N or S")
    parser.add_argument("-x", "--longitude", help="Enter longitude")
    parser.add_argument("-y", "--latitude", help="Enter latitude")

    args = parser.parse_args()

    if args.infile is not None and args.outfile is not None:
        if args.utm == 1:
            convert_file_from_utm(args.infile, args.outfile)
        elif args.latlong == 1:
            convert_file_from_latlong(args.infile, args.outfile)
        else:
            print ("Error, you must specify either -u/--utm, OR -l/--latlong")

    else:  # direct method
        if args.utm == 1:
            if args.easting is not None and args.northing is not None \
             and args.zone is not None and args.side is not None:
                doinline_from_utm(args.easting, args.northing,
                                  args.zone, args.side)
            else:
                print ("Error-you must specify easting, northing, zone, side")
        elif args.latlong == 1:
            if args.longitude is not None and args.latitude is not None:
                doinline_from_latlong(args.longitude, args.latitude)
            else:
                print ("Error, you must specify longitude and latitude.")
        else:
            print ("Error, you must choose -u/--utm, OR -l/--latlong")


if __name__ == '__main__':
    main()
