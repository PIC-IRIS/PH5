# This script is used to convert UTM coordinates to/from Latitude/Longitude
# Dave Thomas, 2020-02-24

from __future__ import (print_function)
from ph5.core import ph5utils
import argparse
import logging

PROG_VERSION = '2020.091'
LOGGER = logging.getLogger(__name__)


def convert_file_from_utm(infile, outfile):
    # batch file method
    counter = 0
    with open(outfile, "w") as theoutfile, open(infile) as theinfile:
        ws = "Northing, Easting, Zone, Hemisphere, => Latitude, Longitude\n"
        theoutfile.write(ws)
        for line in theinfile:
            counter = counter + 1
            if counter == 1:
                # skip header line
                continue
            fieldset = line.strip().split(",")
            if len(fieldset) <= 1:
                continue
            easting = float(fieldset[0])
            northing = float(fieldset[1])
            zone = int(fieldset[2])
            hemisphere = str(fieldset[3]).upper()
            try:
                lat, lon = ph5utils.utm_to_lat_lon(northing, easting,
                                                   hemisphere, zone)
                ps = "northing=%.1f, easting=%.1f, zone=%d, hemisphere=%s"
                printstr1 = (ps % (northing, easting, zone, hemisphere))
                printstr2 = "Lat = %.7f, Lon = %.7f" % (lat, lon)
                LOGGER.info(printstr1 + " => " + printstr2)
                outstr = "%.1f, %.1f, %d, %s, %.7f, %.7f" \
                    % (northing, easting, zone, hemisphere, lat, lon)
                theoutfile.write(outstr + "\n")
            except ValueError:
                LOGGER.error("There was an error in UTM data conversion.")
                return


def convert_file_from_latlong(infile, outfile):
    # batch file method
    counter = 0
    with open(outfile, "w") as theoutfile, open(infile) as theinfile:
        ws = "Latitude, Longitude, =>Northing, Easting, Zone, Hemisphere\n"
        theoutfile.write(ws)
        for line in theinfile:
            counter = counter + 1
            if counter == 1:
                # skip header line
                continue
            fieldset = line.strip().split(",")
            if len(fieldset) <= 1:
                continue
            lat = float(fieldset[0])
            lon = float(fieldset[1])
            try:
                northing, easting, zone, hemisphere =\
                         ph5utils.lat_lon_to_utm(lat, lon)
                ps = "northing=%.1f, easting=%.1f, zone=%d, hemisphere=%s"
                printstr1 = "Lat = %.7f, Lon = %.7f" % (lat, lon)
                printstr2 = (ps % (northing, easting, zone, hemisphere))
                LOGGER.info(printstr1 + " => " + printstr2)
                outstr = "%.7f, %.7f, %.1f, %.1f, %d, %s" \
                    % (lat, lon, northing, easting, zone, hemisphere)
                theoutfile.write(outstr + "\n")
            except ValueError:
                LOGGER.error("There was an error in UTM data conversion.")
                return


def doinline_from_utm(easting, northing, zone, hemisphere):
    # interactive method
    try:
        indat = ("Input: easting=%.1f, northing=%.1f, zone=%d, hemisphere=%s"
                 % (float(easting), float(northing), int(zone), hemisphere))
        LOGGER.info(indat)

        lat, lon = ph5utils.utm_to_lat_lon(northing, easting,
                                           hemisphere, zone)
        outstr = "Lat = %.7f, Lon = %.7f" % (lat, lon)
        LOGGER.info(outstr)
        LOGGER.info(''.join('*'*50))
    except ValueError:
        LOGGER.error("There was an error in UTM data conversion.")
        return


def doinline_from_latlong(lat, lon):
    # interactive method
    try:
        if abs(float(lat)) > 90.0:
            LOGGER.error(
                "Your latitude, {0}, is out of limit."
                .format(lat))
            return
        northing, easting, zone, hemisphere = \
            ph5utils.lat_lon_to_utm(float(lat), float(lon))
        indat = "Input: lat=%.7f, lon=%.7f" % (float(lat), float(lon))
        LOGGER.info(indat)
        outstr = "northing =%.1f, easting =%.1f, zone =%s, hemisphere =%s" \
            % (float(northing), float(easting), zone, hemisphere)
        LOGGER.info(outstr)
        LOGGER.info(''.join('*'*50))
    except ValueError:
        LOGGER.error("There was an error in UTM data conversion.")
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

    # for batch file method
    if args.infile is not None and args.outfile is not None:
        if args.utm == 1:
            convert_file_from_utm(args.infile, args.outfile)
        elif args.latlong == 1:
            convert_file_from_latlong(args.infile, args.outfile)
        else:
            LOGGER.error("You must specify either -u/--utm, OR -l/--latlong")

    # for direct method
    else:
        if args.utm == 1:
            if args.easting is not None and args.northing is not None \
             and args.zone is not None and args.side is not None:
                doinline_from_utm(args.easting, args.northing,
                                  args.zone, args.side.upper())
            else:
                LOGGER.error("You must specify northing,easting,zone, & side")
        elif args.latlong == 1:
            if args.longitude is not None and args.latitude is not None:
                doinline_from_latlong(args.latitude, args.longitude)
            else:
                LOGGER.error("You must specify longitude and latitude.")
        else:
            LOGGER.error("You must choose -u/--utm, OR -l/--latlong")


if __name__ == '__main__':
    main()
