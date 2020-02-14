#!/usr/bin/env pnpython3
#
# A low level SAC library
#
# Steve Azevedo, August 2012
#

import exceptions
import sys
import construct


PROG_VERSION = '2020.34'


def __version__():
    print PROG_VERSION


ICONSTANTS = {"IREAL": 0,		# undocumented
              "ITIME": 1,		# file: time series data
              "IRLIM": 2,		# file: real&imag spectrum
              "IAMPH": 3,		# file: ampl&phas spectrum
              "IXY": 4,			# file: gen'l x vs y data
              "IUNKN": 5,		# x data: unknown type
              # zero time: unknown
              # event type: unknown
              "IDISP": 6,		# x data: displacement (nm)
              "IVEL": 7,		# x data: velocity (nm/sec)
              "IACC": 8,		# x data: accel (cm/sec/sec)
              "IB": 9,			# zero time: start of file
              "IDAY": 10,		# zero time: 0000 of GMT day
              "IO": 11,			# zero time: event origin
              "IA": 12,			# zero time: 1st arrival
              "IT0": 13,		# zero time: user timepick 0
              "IT1": 14,		# zero time: user timepick 1
              "IT2": 15,		# zero time: user timepick 2
              "IT3": 16,		# zero time: user timepick 3
              "IT4": 17,		# zero time: user timepick 4
              "IT5": 18,		# zero time: user timepick 5
              "IT6": 19,		# zero time: user timepick 6
              "IT7": 20,		# zero time: user timepick 7
              "IT8": 21,		# zero time: user timepick 8
              "IT9": 22,		# zero time: user timepick 9
              "IRADNV": 23,		# undocumented
              "ITANNV": 24,		# undocumented
              "IRADEV": 25,		# undocumented
              "ITANEV": 26,		# undocumented
              "INORTH": 27,		# undocumented
              "IEAST": 28,		# undocumented
              "IHORZA": 29,		# undocumented
              "IDOWN": 30,		# undocumented
              "IUP": 31,		# undocumented
              "ILLLBB": 32,		# undocumented
              "IWWSN1": 33,		# undocumented
              "IWWSN2": 34,		# undocumented
              "IHGLP": 35,		# undocumented
              "ISRO": 36,		# undocumented

              # Source types
              "INUCL": 37,  # event type: nuclear shot
              "IPREN": 38,  # event type: nuke pre-shot
              "IPOSTN": 39,  # event type: nuke post-shot
              "IQUAKE": 40,  # event type: earthquake
              "IPREQ": 41,  # event type: foreshock
              "IPOSTQ": 42,  # event type: aftershock
              "ICHEM": 43,  # event type: chemical expl
              "IOTHER": 44,  # event type: other source
              "IQB": 72,  # Quarry Blast or mine expl. confirmed by quarry
              "IQB1": 73,  # Quarry or mine blast with designed
                           # shot information-ripple fired
              "IQB2": 74,  # Quarry or mine blast with observed
                           # shot information-ripple fired
              "IQBX": 75,  # Quarry or mine blast - single shot
              "IQMT": 76,  # Quarry or mining-induced events:
                           # tremors and rockbursts
              "IEQ": 77,   # Earthquake
              "IEQ1": 78,  # Earthquakes in a swarm or aftershock sequence
              "IEQ2": 79,  # Felt earthquake
              "IME": 80,   # Marine explosion
              "IEX": 81,   # Other explosion
              "INU": 82,   # Nuclear explosion
              "INC": 83,   # Nuclear cavity collapse
              "IO_": 84,   # Other source of known origin
              "IL": 85,    # Local event of unknown origin
              "IR": 86,    # Regional event of unknown origin
              "IT": 87,    # Teleseismic event of unknown origin
              "IU": 88,    # Undetermined or conflicting information
              "IEQ3": 89,  # Damaging earthquake
              "IEQ0": 90,  # Probable earthquake
              "IEX0": 91,  # Probable explosion
              "IQC": 92,   # Mine collapse
              "IQB0": 93,  # Probable Mine Blast
              "IGEY": 94,  # Geyser
              "ILIT": 95,  # Light
              "IMET": 96,  # Meteoric Event
              "IODOR": 97,  # Odors
              "IOS": 103, 		# Other source: Known origin
              # data quality: other problm
              "IGOOD": 45,		# data quality: good
              "IGLCH": 46,		# data quality: has glitches
              "IDROP": 47,		# data quality: has dropouts
              "ILOWSN": 48,		# data quality: low s/n

              "IRLDTA": 49,		# data is real data
              "IVOLTS": 50,		# file: velocity (volts)

              # Magnitude type and source
              "IMB": 52,                # Bodywave Magnitude
              "IMS": 53,                # Surface Magnitude
              "IML": 54,                # Local Magnitude
              "IMW": 55,                # Moment Magnitude
              "IMD": 56,                # Duration Magnitude
              "IMX": 57,                # User Defined Magnitude
              "INEIC": 58,              # INEIC
              "IPDEQ": 59,              # IPDE
              "IPDEW": 60,              # IPDE
              "IPDE": 61,               # IPDE

              "IISC": 62,               # IISC
              "IREB": 63,               # IREB
              "IUSGS": 64,              # IUSGS
              "IBRK": 65,               # IBRK
              "ICALTECH": 66,           # ICALTECH
              "ILLNL": 67,              # ILLNL
              "IEVLOC": 68,             # IEVLOC
              "IJSOP": 69,              # IJSOP
              "IUSER": 70,              # IUSER
              "IUNKNOWN": 71}          # IUNKNOWN


class HeaderError (exceptions.Exception):
    def __init__(self, args=None):
        self.args = args

# SAC Little Endian binary header, float part


def bin_header_le_float():
    BIN = "BIN" / construct.Struct(
                            # Increment between evenly spaced samples (nominal
                            # value).
                            "delta" / construct.Float32l,
                            # Minimum value of dependent variable.
                            "depmin" / construct.Float32l,
                            # Maximum value of dependent variable.
                            "depmax" / construct.Float32l,
                            # Multiplying scale factor for dependent variable
                            "scale" / construct.Float32l,
                            # Observed increment if different from nominal
                            # value.
                            "odelta" / construct.Float32l,
                            # Beginning value of the independent variable.
                            # [required]
                            "b" / construct.Float32l,
                            # Ending value of the independent variable.
                            # [required]
                            "e" / construct.Float32l,
                            # Event origin time (seconds relative to reference
                            # time.)
                            "o" / construct.Float32l,
                            # First arrival time (seconds relative to reference
                            # time.)
                            "a" / construct.Float32l,
                            "fmt" / construct.Float32l,
                            "t0" / construct.Float32l,
                            "t1" / construct.Float32l,
                            "t2" / construct.Float32l,
                            "t3" / construct.Float32l,
                            "t4" / construct.Float32l,
                            "t5" / construct.Float32l,
                            "t6" / construct.Float32l,
                            "t7" / construct.Float32l,
                            "t8" / construct.Float32l,
                            "t9" / construct.Float32l,
                            # Fini or end of event time (seconds relative to
                            # reference time.)
                            "resp0" / construct.Float32l,
                            "resp1" / construct.Float32l,
                            "resp2" / construct.Float32l,
                            "resp3" / construct.Float32l,
                            "resp4" / construct.Float32l,
                            "resp5" / construct.Float32l,
                            "resp6" / construct.Float32l,
                            "resp7" / construct.Float32l,
                            "resp8" / construct.Float32l,
                            "resp9" / construct.Float32l,
                            # Station latitude (degrees, north positive)
                            "stla" / construct.Float32l,
                            # Station longitude (degrees, east positive).
                            "stlo" / construct.Float32l,
                            # Station elevation (meters). [not currently used]
                            "stel" / construct.Float32l,
                            # Station depth below surface (meters). [not
                            # currently
                            "stdp" / construct.Float32l,
                            # used]
                            # Event latitude (degrees north positive).
                            "evla" / construct.Float32l,
                            # Event longitude (degrees east positive).
                            "evlo" / construct.Float32l,
                            # Event elevation (meters). [not currently used]
                            "evel" / construct.Float32l,
                            # Event depth below surface (meters). [not currently
                            # used]
                            "evdp" / construct.Float32l,
                            # Event magnitude.
                            "mag" / construct.Float32l,
                            # User defined variable storage area {ai n}=0,9.
                            "user0" / construct.Float32l,
                            "user1" / construct.Float32l,
                            "user2" / construct.Float32l,
                            "user3" / construct.Float32l,
                            "user4" / construct.Float32l,
                            "user5" / construct.Float32l,
                            "user6" / construct.Float32l,
                            "user7" / construct.Float32l,
                            "user8" / construct.Float32l,
                            "user9" / construct.Float32l,
                            # Station to event distance (km).
                            "dist" / construct.Float32l,
                            # Event to station azimuth (degrees).
                            "az" / construct.Float32l,
                            # Station to event azimuth (degrees).
                            "baz" / construct.Float32l,
                            # Station to event great circle arc length
                            # (degrees).
                            "gcarc" / construct.Float32l,
                            "sb" / construct.Float32l,
                            "sdelta" / construct.Float32l,
                            # Mean value of dependent variable.
                            "depmen" / construct.Float32l,
                            # Component azimuth (degrees, clockwise from north).
                            "cmpaz" / construct.Float32l,
                            # Component incident angle (degrees, from vertical).
                            "xminimum" / construct.Float32l,
                            "xmaximum" / construct.Float32l,
                            "yminimum" / construct.Float32l,
                            "ymaximum" / construct.Float32l,
                            "unused6" / construct.Float32l,
                            "unused7" / construct.Float32l,
                            "unused8" / construct.Float32l,
                            "unused9" / construct.Float32l,
                            "unused10" / construct.Float32l,
                            "unused11" / construct.Float32l,
                            "unused12" / construct.Float32l,
                            )
    return BIN
# SAC Little Endian binary header, int part


def bin_header_le_int():
    BIN = construct.Struct("BIN",
                           # GMT year corresponding to reference (zero) time in
                           # file.
                           "nzyear" / construct.Int32sl,
                           # GMT julian day.
                           "nzjday" / construct.Int32sl,
                           # GMT hour.
                           "nzhour" / construct.Int32sl,
                           # GMT minute.
                           "nzmin" / construct.Int32sl,
                           # GMT second.
                           "nzsec" / construct.Int32sl,
                           # GMT millisecond.
                           "nzmsec" / construct.Int32sl,
                           # Header version number. Current value is the
                           # integer 6.
                           "nvhdr" / construct.Int32sl,
                           # Older version data (NVHDR < 6) are automatically
                           # updated
                           "norid" / construct.Int32sl,
                           # Event ID (CSS 3.0)
                           "nevid" / construct.Int32sl,
                           # Number of points per data component. [required]
                           "npts" / construct.Int32sl,
                           "nsnpts" / construct.Int32sl,
                           # Waveform ID (CSS 3.0)
                           "nwfid" / construct.Int32sl,
                           "nxsize" / construct.Int32sl,
                           "nysize" / construct.Int32sl,
                           "unused15" / construct.Int32sl,
                           # Type of file [required]:
                           "iftype" / construct.Int32sl,
                           #    * ITIME {Time series file}
                           #    * IRLIM {Spectral file---real and imaginary}
                           #    * IAMPH {Spectral file---amplitude and phase}
                           #    * IXY {General x versus y data}
                           #    * IXYZ {General XYZ (3-D) file}
                           # Type of dependent variable:
                           "idep" / construct.Int32sl,
                           #    * IUNKN (Unknown)
                           #    * IDISP (Displacement in nm)
                           #    * IVEL (Velocity in nm/sec)
                           #    * IVOLTS (Velocity in volts)
                           #    * IACC (Acceleration in nm/sec/sec)
                           # Reference time equivalence:
                           "iztype" / construct.Int32sl,
                           #    * IUNKN (5): Unknown
                           #    * IB (9): Begin time
                           #    * IDAY (10): Midnight of refernece GMT day
                           #    * IO (11): Event origin time
                           #    * IA (12): First arrival time
                           #    * ITn (13-22): User defined time pick n,n=0,9
                           "unused16" / construct.Int32sl,
                           # Type of recording instrument. [currently not used]
                           "iinst" / construct.Int32sl,
                           # Station geographic region. [not currently used]
                           "istreg" / construct.Int32sl,
                           # Event geographic region. [not currently used]
                           "ievreg" / construct.Int32sl,
                           # Type of event:
                           "ievtyp" / construct.Int32sl,
                           # * IUNKN (Unknown)
                           # * INUCL (Nuclear event)
                           # * IPREN (Nuclear pre-shot event)
                           # * IPOSTN (Nuclear post-shot event)
                           # * IQUAKE (Earthquake)
                           # * IPREQ (Foreshock)
                           # * IPOSTQ (Aftershock)
                           # * ICHEM (Chemical explosion)
                           # * IQB (Quarry or mine blast confirmed by quarry)
                           # * IQB1 (Quarry/mine blast with designed shot
                           #   info-ripple fired)
                           # * IQB2 (Quarry/mine blast with observed shot
                           #   info-ripple fired)
                           # * IQMT (Quarry/mining-induced events:
                           #   tremors and rockbursts)
                           # * IEQ (Earthquake)
                           # * IEQ1 (Earthquakes in a swarm or aftershock
                           #   sequence)
                           # * IEQ2 (Felt earthquake)
                           # * IME (Marine explosion)
                           # * IEX (Other explosion)
                           # * INU (Nuclear explosion)
                           # * INC (Nuclear cavity collapse)
                           # * IO\_ (Other source of known origin)
                           # * IR (Regional event of unknown origin)
                           # * IT (Teleseismic event of unknown origin)
                           # * IU (Undetermined or conflicting information)
                           # Quality of data [not currently used]:
                           "iqual" / construct.Int32sl,
                           #    * IGOOD (Good data)
                           #    * IGLCH (Glitches)
                           #    * IDROP (Dropouts)
                           #    * ILOWSN (Low signal to noise ratio)
                           #    * IOTHER (Other)
                           # Synthetic data flag [not currently used]:
                           "isynth" / construct.Int32sl,
                           #    * IRLDTA (Real data)
                           #    * ?????
                           #    (Flags for various synthetic seismogram
                           #      codes)
                           "imagtyp" / construct.Int32sl,
                           "imagsrc" / construct.Int32sl,
                           "unused19" / construct.Int32sl,
                           "unused20" / construct.Int32sl,
                           "unused21" / construct.Int32sl,
                           "unused22" / construct.Int32sl,
                           "unused23" / construct.Int32sl,
                           "unused24" / construct.Int32sl,
                           "unused25" / construct.Int32sl,
                           "unused26" / construct.Int32sl,
                           # TRUE if data is evenly spaced. [required]
                           "leven" / construct.Int32sl,
                           # TRUE if station components have a positive
                           # polarity
                           "lpspol" / construct.Int32sl,
                           # (left-hand rule).
                           # TRUE if it is okay to overwrite this file on disk.
                           "lovrok" / construct.Int32sl,
                           # TRUE if DIST AZ BAZ and GCARC are to be calculated
                           # from
                           "lcalda" / construct.Int32sl,
                           # st event coordinates.
                           "unused27" / construct.Int32sl)
    return BIN
# SAC Little Endian binary header, string part


def bin_header_le_char():
    BIN = construct.Struct("BIN",
                           # Station name.
                           "kstnm" / constrct.Bytes(8),
                           # Event name.
                           "kevnm" / constrct.Bytes(16),
                           # Hole identification if nuclear event.
                           "khole" / constrct.Bytes(8),
                           "ko" / constrct.Bytes(8),
                           # First arrival time identification.
                           "ka" / constrct.Bytes(8),
                           # A User defined time {ai n}=0,9.  pick
                           # identifications
                           "kt0" / constrct.Bytes(8),
                           "kt1" / constrct.Bytes(8),
                           "kt2" / constrct.Bytes(8),
                           "kt3" / constrct.Bytes(8),
                           "kt4" / constrct.Bytes(8),
                           "kt5" / constrct.Bytes(8),
                           "kt6" / constrct.Bytes(8),
                           "kt7" / constrct.Bytes(8),
                           "kt8" / constrct.Bytes(8),
                           "kt9" / constrct.Bytes(8),
                           "kf" / constrct.Bytes(8),
                           # User defined variable storage area {ai n}=0,9.
                           "kuser0" / constrct.Bytes(8),
                           "kuser1" / constrct.Bytes(8),
                           "kuser2" / constrct.Bytes(8),
                           # Component name.
                           "kcmpnm" / constrct.Bytes(8),
                           # Name of seismic network.
                           "knetwk" / constrct.Bytes(8),
                           "kdatrd" / constrct.Bytes(8),
                           # Generic name of recording instrument
                           "kinst" / constrct.Bytes(8))
    return BIN

# SAC Big Endian binary header, float part


def bin_header_be_float():
    BIN = construct.Struct("BIN",
                           "delta" / construct.Float32b,
                           "depmin" / construct.Float32b,
                           "depmax" / construct.Float32b,
                           "scale" / construct.Float32b,
                           "odelta" / construct.Float32b,
                           "b" / construct.Float32b,
                           "e" / construct.Float32b,
                           "o" / construct.Float32b,
                           "a" / construct.Float32b,
                           "t0" / construct.Float32b,
                           "t1" / construct.Float32b,
                           "t2" / construct.Float32b,
                           "t3" / construct.Float32b,
                           "t4" / construct.Float32b,
                           "t5" / construct.Float32b,
                           "t6" / construct.Float32b,
                           "t7" / construct.Float32b,
                           "t8" / construct.Float32b,
                           "t9" / construct.Float32b,
                           "f" / construct.Float32b,
                           "resp0" / construct.Float32b,
                           "resp1" / construct.Float32b,
                           "resp2" / construct.Float32b,
                           "resp3" / construct.Float32b,
                           "resp4" / construct.Float32b,
                           "resp5" / construct.Float32b,
                           "resp6" / construct.Float32b,
                           "resp7" / construct.Float32b,
                           "resp8" / construct.Float32b,
                           "resp9" / construct.Float32b,
                           "stala" / construct.Float32b,
                           "stalo" / construct.Float32b,
                           "stel" / construct.Float32b,
                           "stdp" / construct.Float32b,
                           "evla" / construct.Float32b,
                           "evlo" / construct.Float32b,
                           "evel" / construct.Float32b,
                           "evdp" / construct.Float32b,
                           "mag" / construct.Float32b,
                           "user0" / construct.Float32b,
                           "user1" / construct.Float32b,
                           "user2" / construct.Float32b,
                           "user3" / construct.Float32b,
                           "user4" / construct.Float32b,
                           "user5" / construct.Float32b,
                           "user6" / construct.Float32b,
                           "user7" / construct.Float32b,
                           "user8" / construct.Float32b,
                           "user9" / construct.Float32b,
                           "dist" / construct.Float32b,
                           "az" / construct.Float32b,
                           "baz" / construct.Float32b,
                           "gcarc" / construct.Float32b,
                           "sb" / construct.Float32b,
                           "sdelta" / construct.Float32b,
                           "depmen" / construct.Float32b,
                           "cmpaz" / construct.Float32b,
                           "cmpinc" / construct.Float32b,
                           "xminimum" / construct.Float32b,
                           "xmaximum" / construct.Float32b,
                           "yminimum" / construct.Float32b,
                           "ymaximum" / construct.Float32b,
                           "unused6" / construct.Float32b,
                           "unused7" / construct.Float32b,
                           "unused8" / construct.Float32b,
                           "unused9" / construct.Float32b,
                           "unused10" / construct.Float32b,
                           "unused11" / construct.Float32b,
                           "unused12" / construct.Float32b)
    return BIN
# SAC Big Endian binary header, int part


def bin_header_be_int():
    BIN = construct.Struct("BIN",
                           "nzyear" / construct.Int32sb,
                           "nzjday" / construct.Int32sb,
                           "nzhour" / construct.Int32sb,
                           "nzmin" / construct.Int32sb,
                           "nzsec" / construct.Int32sb,
                           "nzmsec" / construct.Int32sb,
                           "nvhdr" / construct.Int32sb,
                           "norid" / construct.Int32sb,
                           "nevid" / construct.Int32sb,
                           "npts" / construct.Int32sb,
                           "nsnpts" / construct.Int32sb,
                           "nwfid" / construct.Int32sb,
                           "nxsize" / construct.Int32sb,
                           "nysize" / construct.Int32sb,
                           "unused15" / construct.Int32sb,
                           "iftype" / construct.Int32sb,
                           "idep" / construct.Int32sb,
                           "iztype" / construct.Int32sb,
                           "unused16" / construct.Int32sb,
                           "iinst" / construct.Int32sb,
                           "istreg" / construct.Int32sb,
                           "ievreg" / construct.Int32sb,
                           "ievtyp" / construct.Int32sb,
                           "iqual" / construct.Int32sb,
                           "isynth" / construct.Int32sb,
                           "imagtyp" / construct.Int32sb,
                           "imagsrc" / construct.Int32sb,
                           "unused19" / construct.Int32sb,
                           "unused20" / construct.Int32sb,
                           "unused21" / construct.Int32sb,
                           "unused22" / construct.Int32sb,
                           "unused23" / construct.Int32sb,
                           "unused24" / construct.Int32sb,
                           "unused25" / construct.Int32sb,
                           "unused26" / construct.Int32sb,
                           "leven" / construct.Int32sb,
                           "lpspol" / construct.Int32sb,
                           "lovrok" / construct.Int32sb,
                           "lcalda" / construct.Int32sb,
                           "unused27" / construct.Int32sb)
    return BIN
# SAC Big Endian binary header, string part


def bin_header_be_char():
    BIN = construct.Struct("BIN",
                           "kstnm" / constrct.Bytes(8),
                           "kevnm" / constrct.Bytes(16),
                           "khole" / constrct.Bytes(8),
                           "ko" / constrct.Bytes(8),
                           "ka" / constrct.Bytes(8),
                           "kt0" / constrct.Bytes(8),
                           "kt1" / constrct.Bytes(8),
                           "kt2" / constrct.Bytes(8),
                           "kt3" / constrct.Bytes(8),
                           "kt4" / constrct.Bytes(8),
                           "kt5" / constrct.Bytes(8),
                           "kt6" / constrct.Bytes(8),
                           "kt7" / constrct.Bytes(8),
                           "kt8" / constrct.Bytes(8),
                           "kt9" / constrct.Bytes(8),
                           "kf" / constrct.Bytes(8),
                           "kuser0" / constrct.Bytes(8),
                           "kuser1" / constrct.Bytes(8),
                           "kuser2" / constrct.Bytes(8),
                           "kcmpnm" / constrct.Bytes(8),
                           "knetwk" / constrct.Bytes(8),
                           "kdatrd" / constrct.Bytes(8),
                           "kinst" / constrct.Bytes(8))
    return BIN


class SAC_float (object):
    __keys__ = ("delta", "depmin", "depmax", "scale", "odelta", "b", "e", "o",
                "a", "fmt",
                "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9",
                "f", "resp0",
                "resp1", "resp2", "resp3", "resp4", "resp5", "resp6", "resp7",
                "resp8", "resp9",
                "stla", "stlo", "stel", "stdp", "evla", "evlo", "evel", "evdp",
                "mag", "user0",
                "user1", "user2", "user3", "user4", "user5", "user6", "user7",
                "user8", "user9",
                "dist", "az", "baz", "gcarc", "sb", "sdelta", "depmen",
                "cmpaz",
                "cmpinc", "xminimum",
                "xmaximum", "yminimum", "ymaximum", "unused6", "unused7",
                "unused8", "unused9",
                "unused10", "unused11", "unused12")

    def __init__(self):
        for c in SAC_float.__keys__:
            self.__dict__[c] = -12345.0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                # XXX   Needs proper exception handling   XXX
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" %
                    k)

    def get(self, byteorder=sys.byteorder):
        if byteorder == 'little':
            t = bin_header_le_float()
        else:
            t = bin_header_be_float()

        return t.build(self)

    def parse(self, buf, byteorder=sys.byteorder):
        if byteorder == 'little':
            t = bin_header_le_float()
        else:
            t = bin_header_be_float()

        return t.parse(buf)


class SAC_int (object):
    __keys__ = ("nzyear", "nzjday", "nzhour", "nzmin", "nzsec", "nzmsec",
                "nvhdr", "norid",
                "nevid", "npts", "nsnpts", "nwfid", "nxsize", "nysize",
                "unused15", "iftype",
                "idep", "iztype", "unused16", "iinst", "istreg", "ievreg",
                "ievtyp", "iqual",
                "isynth", "imagtyp", "imagsrc", "unused19", "unused20",
                "unused21", "unused22",
                "unused23", "unused24", "unused25", "unused26", "leven",
                "lpspol", "lovrok",
                "lcalda", "unused27")

    def __init__(self):
        for c in SAC_int.__keys__:
            self.__dict__[c] = -12345

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                # XXX   Needs proper exception handling   XXX
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" %
                    k)

    def get(self, byteorder=sys.byteorder):
        if byteorder == 'little':
            t = bin_header_le_int()
        else:
            t = bin_header_be_int()

        return t.build(self)

    def parse(self, buf, byteorder=sys.byteorder):
        if byteorder == 'little':
            t = bin_header_le_int()
        else:
            t = bin_header_be_int()

        return t.parse(buf)


class SAC_char (object):
    __keys__ = ("kstnm", "kevnm", "khole", "ko", "ka", "kt0", "kt1", "kt2",
                "kt3", "kt4", "kt5",
                "kt6", "kt7", "kt8", "kt9", "kf", "kuser0", "kuser1", "kuser2",
                "kcmpnm", "knetwk",
                "kdatrd", "kinst")

    def __init__(self):
        for c in SAC_char.__keys__:
            self.__dict__[c] = "-12345  "

        self.__dict__["kevnm"] = "-12345          "

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                # XXX   Needs proper exception handling   XXX
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" %
                    k)

    def get(self, byteorder=sys.byteorder):
        if byteorder == 'little':
            t = bin_header_le_char()
        else:
            t = bin_header_be_char()

        return t.build(self)

    def parse(self, buf, byteorder=sys.byteorder):
        if byteorder == 'little':
            t = bin_header_le_char()
        else:
            t = bin_header_be_char()

        return t.parse(buf)

# Mixins


def bfloat():
    PFLOAT = construct.Struct("PFLOAT",
                              construct.BFloat32("x"))
    return PFLOAT


def lfloat():
    PFLOAT = construct.Struct("PFLOAT",
                              construct.LFloat32("x"))
    return PFLOAT


def build_floats(x, byteorder=sys.byteorder):
    if byteorder == 'little':
        c = construct.Array(len(x), construct.LFloat32("x"))
    else:
        c = construct.Array(len(x), construct.BFloat32("x"))

    return c.build(x)
