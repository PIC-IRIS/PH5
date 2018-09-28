#!/usr/bin/env pnpython3
#
# Convert geographic coordinates to UTM and back.
# Assumes reference ellipsoids are the same and are 3D.
#
# Steve Azevedo, January 2013
#

# https://code.google.com/p/pyproj/
from pyproj import Proj

# The proj4 program cs2cs must be in your path
# CS2CS = 'cs2cs'


def _sign(val, latlon):
    ret = val
    try:
        nsew = str(val[0])
        nsew.upper()
        if nsew == 'N' or nsew == 'S' or nsew == 'E' or nsew == 'W':
            return ret

        if nsew == '+':
            val = val[1:]

        if latlon == 'lat':
            if nsew == '-':
                ret = 'S' + val[1:]
            else:
                ret = 'N' + val
        elif latlon == 'lon':
            if nsew == '-':
                ret = 'W' + val[1:]
            else:
                ret = 'E' + val

    except IndexError:
        pass

    return ret


def lon2zone(lon):
    '''   Get UTM zone from longitude, brute force method   '''
    # zone 1 = -180 -> -174
    # zone 2 = -174 -> -168
    for zone in range(1, 60):
        ebound = (zone * 6) - 180
        wbound = ebound - 6
        if lon >= wbound and lon <= ebound:
            return zone

    return None


def utm2geod(zn, datum, X, Y, Z):
    '''   Convert UTM coordinates to geodetic coordinates   '''
    p = Proj(proj='utm', zone=zn, ellps=datum)

    lon, lan = p(X, Y, inverse=True)

    return lat, lon, Z


def geod2utm(zn, datum, lat, lon, elev):
    '''   Convert geodetic coordinates to UTM   '''
    if zn is None:
        zn = lon2zone(lon)

    p = Proj(proj='utm', zone=zn, ellps=datum)

    X, Y = p(lon, lat)

    # Return Y, X, Z
    return Y, X, elev


if __name__ == '__main__':
    lat = 34.023786
    lon = -106.898492
    elev = 1456.0
    zone = 13

    z = lon2zone(lon)
    print z

    Y, X, Z = geod2utm(zone, 'WGS84', lat, lon, elev)
    print Y, X, Z

    lat, lon, elev = utm2geod(zone, 'WGS84', X, Y, Z)
    print lat, lon, elev
