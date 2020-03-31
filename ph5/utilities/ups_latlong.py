# This script is used to convert UPS coordinates to/from Latitude/Longitude
# Dave Thomas, 2020-03-27

from __future__ import (print_function)
from ph5.core import ph5utils
import argparse
import logging

PROG_VERSION = '2020.091'
LOGGER = logging.getLogger(__name__)


def convert_file_from_ups(infile, outfile):
    # batch file method
    counter = 0
    with open(outfile, "w") as theoutfile, open(infile) as theinfile:
        ws = "Hemisphere, Northing, Easting, => Latitude, Longitude\n"
        theoutfile.write(ws)
        for line in theinfile:
            counter = counter + 1
            if counter == 1:
                # skip header line
                continue
            fieldset = line.strip().split(",")
            if len(fieldset) <= 1:
                continue
            hemisphere = str(fieldset[0]).upper()
            northing = float(fieldset[1])
            easting = float(fieldset[2])
            try:
                if hemisphere == 'N':
                    lat, lon = ph5utils.ups_north_to_lat_lon(northing, easting)
                else:
                    # default to southern hemisphere
                    lat, lon = ph5utils.ups_south_to_lat_lon(northing, easting)
                ps = "hemisphere=%s, northing=%.1f, easting=%.1f"
                printstr1 = (ps % (hemisphere, northing, easting))
                printstr2 = "Lat = %.7f, Lon = %.7f" % (lat, lon)
                LOGGER.info(printstr1 + " => " + printstr2)
                outstr = "%s, %.1f, %.1f, %.7f, %.7f" \
                    % (hemisphere, northing, easting, lat, lon)
                theoutfile.write(outstr + "\n")
            except ValueError:
                LOGGER.error("There was an error in ups data conversion.")
                return


def convert_file_from_latlong(infile, outfile):
    # batch file method
    counter = 0
    with open(outfile, "w") as theoutfile, open(infile) as theinfile:
        ws = "Latitude, Longitude, => Hemisphere, Northing, Easting\n"
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
                if lat > 0.0:
                    hemisphere = 'N'
                    northing, easting =\
                        ph5utils.lat_lon_to_ups_north(lat, lon)
                else:
                    hemisphere = 'S'
                    northing, easting =\
                        ph5utils.lat_lon_to_ups_south(lat, lon)
                ps = "hemisphere=%s, northing=%.1f, easting=%.1f"
                printstr1 = "Lat = %.7f, Lon = %.7f" % (lat, lon)
                printstr2 = (ps % (hemisphere, northing, easting))
                LOGGER.info(printstr1 + " => " + printstr2)
                outstr = "%.7f, %.7f, %s, %.1f, %.1f" \
                    % (lat, lon, hemisphere, northing, easting)
                theoutfile.write(outstr + "\n")
            except ValueError:
                LOGGER.error("There was an error in ups data conversion.")
                return


def doinline_from_ups(easting, northing, hemisphere='S'):
    # interactive method
    try:
        indat = ("Input: easting=%.1f, northing=%.1f, hemisphere=%s"
                 % (float(easting), float(northing), hemisphere))
        LOGGER.info(indat)

        if hemisphere == 'N':
            lat, lon = ph5utils.ups_north_to_lat_lon(northing, easting)
        else:
            lat, lon = ph5utils.ups_south_to_lat_lon(northing, easting)
        outstr = "Lat = %.7f, Lon = %.7f" % (lat, lon)
        LOGGER.info(outstr)
        LOGGER.info(''.join('*'*50))
    except ValueError:
        LOGGER.error("There was an error in ups data conversion.")
        return


def doinline_from_latlong(lat, lon):
    # interactive method
    try:
        if abs(float(lat)) > 90.0:
            LOGGER.error(
                "Your latitude, {0}, is out of limit."
                .format(lat))
            return
        if float(lat) > 0.0:
            hemisphere = 'Northern'
            northing, easting = \
                ph5utils.lat_lon_to_ups_north(float(lat), float(lon))
        else:
            hemisphere = 'Southern'
            northing, easting = \
                ph5utils.lat_lon_to_ups_south(float(lat), float(lon))
        indat = "Input: lat=%.7f, lon=%.7f" % (float(lat), float(lon))
        LOGGER.info(indat)
        outstr = "%s hemisphere, northing =%.1f, easting =%.1f" \
            % (hemisphere, float(northing), float(easting))
        LOGGER.info(outstr)
        LOGGER.info(''.join('*'*50))
    except ValueError:
        LOGGER.error("There was an error in ups data conversion.")
        return


def main():
    desc = 'Convert UPS locations to/from longitudes, latitudes, \
in batches (-i, -o) or inline (-e,-n,-s), (-x,-y)'
    parser = argparse.ArgumentParser(description=desc)
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument("-u", "--ups", help="Convert UPS to Lat/Long",
                        action="store_true")
    group1.add_argument("-l", "--latlong", help="Convert Lat/Long to UPS",
                        action="store_true")
    parser.add_argument("-i", "--infile", help="Input file with UPS \
Easting, Northing, Hemisphere, or Lats and Longs")
    parser.add_argument("-o", "--outfile", help="Output file with \
converted longitudes, latitudes or ups Coordinates")
    parser.add_argument("-e", "--easting", help="Enter UPS Easting")
    parser.add_argument("-n", "--northing", help="Enter UPS Northing")
    parser.add_argument("-s", "--side", help="Side=Hemisphere, N or S")
    parser.add_argument("-x", "--longitude", help="Enter longitude")
    parser.add_argument("-y", "--latitude", help="Enter latitude")

    args = parser.parse_args()

    # for batch file method
    if args.infile is not None and args.outfile is not None:
        if args.ups == 1:
            convert_file_from_ups(args.infile, args.outfile)
        elif args.latlong == 1:
            convert_file_from_latlong(args.infile, args.outfile)
        else:
            LOGGER.error("You must specify either -u/--ups, OR -l/--latlong")

    # for direct method
    else:
        if args.ups == 1:
            if args.easting is not None and args.northing is not None:
                if args.side is not None:
                    doinline_from_ups(args.easting, args.northing,
                                      args.side.upper())
                else:
                    # default = Southern Hemisphere
                    doinline_from_ups(args.easting, args.northing,
                                      'S')
            else:
                LOGGER.error("You must specify northing and easting")
        elif args.latlong == 1:
            if args.longitude is not None and args.latitude is not None:
                doinline_from_latlong(args.latitude, args.longitude)
            else:
                LOGGER.error("You must specify longitude and latitude.")
        else:
            LOGGER.error("You must choose -u/--ups, OR -l/--latlong")


if __name__ == '__main__':
    main()
