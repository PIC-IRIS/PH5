#!/usr/bin/env pnpython3
#
# A low level SAC library
#
# Steve Azevedo, August 2012
#

import exceptions
import sys
import construct


PROG_VERSION = '2018.268'


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
    BIN = construct.Struct("BIN",
                           # Increment between evenly spaced samples (nominal
                           # value).
                           construct.LFloat32("delta"),
                           # Minimum value of dependent variable.
                           construct.LFloat32("depmin"),
                           # Maximum value of dependent variable.
                           construct.LFloat32("depmax"),
                           # Multiplying scale factor for dependent variable
                           construct.LFloat32("scale"),
                           # Observed increment if different from nominal
                           # value.
                           construct.LFloat32("odelta"),
                           # Beginning value of the independent variable.
                           # [required]
                           construct.LFloat32("b"),
                           # Ending value of the independent variable.
                           # [required]
                           construct.LFloat32("e"),
                           # Event origin time (seconds relative to reference
                           # time.)
                           construct.LFloat32("o"),
                           # First arrival time (seconds relative to reference
                           # time.)
                           construct.LFloat32("a"),
                           construct.LFloat32("fmt"),     #
                           construct.LFloat32("t0"),      #
                           construct.LFloat32("t1"),      #
                           construct.LFloat32("t2"),      #
                           construct.LFloat32("t3"),      #
                           construct.LFloat32("t4"),      #
                           construct.LFloat32("t5"),      #
                           construct.LFloat32("t6"),      #
                           construct.LFloat32("t7"),      #
                           construct.LFloat32("t8"),      #
                           construct.LFloat32("t9"),      #
                           # Fini or end of event time (seconds relative to
                           # reference
                           construct.LFloat32("f"),
                           # time.)
                           construct.LFloat32("resp0"),   #
                           construct.LFloat32("resp1"),   #
                           construct.LFloat32("resp2"),   #
                           construct.LFloat32("resp3"),   #
                           construct.LFloat32("resp4"),   #
                           construct.LFloat32("resp5"),   #
                           construct.LFloat32("resp6"),   #
                           construct.LFloat32("resp7"),   #
                           construct.LFloat32("resp8"),   #
                           construct.LFloat32("resp9"),   #
                           # Station latitude (degrees, north positive)
                           construct.LFloat32("stla"),
                           # Station longitude (degrees, east positive).
                           construct.LFloat32("stlo"),
                           # Station elevation (meters). [not currently used]
                           construct.LFloat32("stel"),
                           # Station depth below surface (meters). [not
                           # currently
                           construct.LFloat32("stdp"),
                           # used]
                           # Event latitude (degrees north positive).
                           construct.LFloat32("evla"),
                           # Event longitude (degrees east positive).
                           construct.LFloat32("evlo"),
                           # Event elevation (meters). [not currently used]
                           construct.LFloat32("evel"),
                           # Event depth below surface (meters). [not currently
                           # used]
                           construct.LFloat32("evdp"),
                           construct.LFloat32("mag"),  # Event magnitude.
                           # User defined variable storage area {ai n}=0,9.
                           construct.LFloat32("user0"),
                           construct.LFloat32("user1"),   #
                           construct.LFloat32("user2"),   #
                           construct.LFloat32("user3"),   #
                           construct.LFloat32("user4"),   #
                           construct.LFloat32("user5"),   #
                           construct.LFloat32("user6"),   #
                           construct.LFloat32("user7"),   #
                           construct.LFloat32("user8"),   #
                           construct.LFloat32("user9"),   #
                           # Station to event distance (km).
                           construct.LFloat32("dist"),
                           # Event to station azimuth (degrees).
                           construct.LFloat32("az"),
                           # Station to event azimuth (degrees).
                           construct.LFloat32("baz"),
                           # Station to event great circle arc length
                           # (degrees).
                           construct.LFloat32("gcarc"),
                           construct.LFloat32("sb"),      #
                           construct.LFloat32("sdelta"),  #
                           # Mean value of dependent variable.
                           construct.LFloat32("depmen"),
                           # Component azimuth (degrees, clockwise from north).
                           construct.LFloat32("cmpaz"),
                           # Component incident angle (degrees, from vertical).
                           construct.LFloat32("cmpinc"),
                           construct.LFloat32("xminimum"),
                           construct.LFloat32("xmaximum"),
                           construct.LFloat32("yminimum"),
                           construct.LFloat32("ymaximum"),
                           construct.LFloat32("unused6"),
                           construct.LFloat32("unused7"),
                           construct.LFloat32("unused8"),
                           construct.LFloat32("unused9"),
                           construct.LFloat32("unused10"),
                           construct.LFloat32("unused11"),
                           construct.LFloat32("unused12"))
    return BIN
# SAC Little Endian binary header, int part


def bin_header_le_int():
    BIN = construct.Struct("BIN",
                           # GMT year corresponding to reference (zero) time in
                           # file.
                           construct.SLInt32("nzyear"),
                           construct.SLInt32("nzjday"),  # GMT julian day.
                           construct.SLInt32("nzhour"),  # GMT hour.
                           construct.SLInt32("nzmin"),  # GMT minute.
                           construct.SLInt32("nzsec"),  # GMT second.
                           construct.SLInt32("nzmsec"),  # GMT millisecond.
                           # Header version number. Current value is the
                           # integer 6.
                           construct.SLInt32("nvhdr"),
                           # Older version data (NVHDR < 6) are automatically
                           # updated
                           construct.SLInt32("norid"),  # Origin ID (CSS 3.0)
                           construct.SLInt32("nevid"),  # Event ID (CSS 3.0)
                           # Number of points per data component. [required]
                           construct.SLInt32("npts"),
                           construct.SLInt32("nsnpts"),     #
                           construct.SLInt32("nwfid"),  # Waveform ID (CSS 3.0)
                           construct.SLInt32("nxsize"),     #
                           construct.SLInt32("nysize"),     #
                           construct.SLInt32("unused15"),   #
                           # Type of file [required]:
                           construct.SLInt32("iftype"),
                           #    * ITIME {Time series file}
                           #    * IRLIM {Spectral file---real and imaginary}
                           #    * IAMPH {Spectral file---amplitude and phase}
                           #    * IXY {General x versus y data}
                           #    * IXYZ {General XYZ (3-D) file}
                           # Type of dependent variable:
                           construct.SLInt32("idep"),
                           #    * IUNKN (Unknown)
                           #    * IDISP (Displacement in nm)
                           #    * IVEL (Velocity in nm/sec)
                           #    * IVOLTS (Velocity in volts)
                           #    * IACC (Acceleration in nm/sec/sec)
                           # Reference time equivalence:
                           construct.SLInt32("iztype"),
                           #    * IUNKN (5): Unknown
                           #    * IB (9): Begin time
                           #    * IDAY (10): Midnight of refernece GMT day
                           #    * IO (11): Event origin time
                           #    * IA (12): First arrival time
                           #    * ITn (13-22): User defined time pick n,n=0,9
                           construct.SLInt32("unused16"),   #
                           # Type of recording instrument. [currently not used]
                           construct.SLInt32("iinst"),
                           # Station geographic region. [not currently used]
                           construct.SLInt32("istreg"),
                           # Event geographic region. [not currently used]
                           construct.SLInt32("ievreg"),
                           construct.SLInt32("ievtyp"),  # Type of event:
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
                           construct.SLInt32("iqual"),
                           #    * IGOOD (Good data)
                           #    * IGLCH (Glitches)
                           #    * IDROP (Dropouts)
                           #    * ILOWSN (Low signal to noise ratio)
                           #    * IOTHER (Other)
                           # Synthetic data flag [not currently used]:
                           construct.SLInt32("isynth"),
                           #    * IRLDTA (Real data)
                           #    * ?????
                           #    (Flags for various synthetic seismogram
                           #      codes)
                           construct.SLInt32("imagtyp"),    #
                           construct.SLInt32("imagsrc"),    #
                           construct.SLInt32("unused19"),   #
                           construct.SLInt32("unused20"),   #
                           construct.SLInt32("unused21"),   #
                           construct.SLInt32("unused22"),   #
                           construct.SLInt32("unused23"),   #
                           construct.SLInt32("unused24"),   #
                           construct.SLInt32("unused25"),   #
                           construct.SLInt32("unused26"),   #
                           # TRUE if data is evenly spaced. [required]
                           construct.SLInt32("leven"),
                           # TRUE if station components have a positive
                           # polarity
                           construct.SLInt32("lpspol"),
                           # (left-hand rule).
                           # TRUE if it is okay to overwrite this file on disk.
                           construct.SLInt32("lovrok"),
                           # TRUE if DIST AZ BAZ and GCARC are to be calculated
                           # from
                           construct.SLInt32("lcalda"),
                           # st event coordinates.
                           construct.SLInt32("unused27"))
    return BIN
# SAC Little Endian binary header, string part


def bin_header_le_char():
    BIN = construct.Struct("BIN",
                           construct.String("kstnm", 8),  # Station name.
                           construct.String("kevnm", 16),  # Event name.
                           # Hole identification if nuclear event.
                           construct.String("khole", 8),
                           construct.String("ko", 8),       #
                           # First arrival time identification.
                           construct.String("ka", 8),
                           # A User defined time {ai n}=0,9.  pick
                           # identifications
                           construct.String("kt0", 8),
                           construct.String("kt1", 8),      #
                           construct.String("kt2", 8),      #
                           construct.String("kt3", 8),      #
                           construct.String("kt4", 8),      #
                           construct.String("kt5", 8),      #
                           construct.String("kt6", 8),      #
                           construct.String("kt7", 8),      #
                           construct.String("kt8", 8),      #
                           construct.String("kt9", 8),      #
                           construct.String("kf", 8),       #
                           # User defined variable storage area {ai n}=0,9.
                           construct.String("kuser0", 8),
                           construct.String("kuser1", 8),   #
                           construct.String("kuser2", 8),   #
                           construct.String("kcmpnm", 8),  # Component name.
                           # Name of seismic network.
                           construct.String("knetwk", 8),
                           construct.String("kdatrd", 8),   #
                           construct.String("kinst", 8))  # Generic name of
    # recording instrument
    return BIN

# SAC Big Endian binary header, float part


def bin_header_be_float():
    BIN = construct.Struct("BIN",
                           construct.BFloat32("delta"),
                           construct.BFloat32("depmin"),
                           construct.BFloat32("depmax"),
                           construct.BFloat32("scale"),
                           construct.BFloat32("odelta"),
                           construct.BFloat32("b"),
                           construct.BFloat32("e"),
                           construct.BFloat32("o"),
                           construct.BFloat32("a"),
                           construct.BFloat32("fmt"),
                           construct.BFloat32("t0"),
                           construct.BFloat32("t1"),
                           construct.BFloat32("t2"),
                           construct.BFloat32("t3"),
                           construct.BFloat32("t4"),
                           construct.BFloat32("t5"),
                           construct.BFloat32("t6"),
                           construct.BFloat32("t7"),
                           construct.BFloat32("t8"),
                           construct.BFloat32("t9"),
                           construct.BFloat32("f"),
                           construct.BFloat32("resp0"),
                           construct.BFloat32("resp1"),
                           construct.BFloat32("resp2"),
                           construct.BFloat32("resp3"),
                           construct.BFloat32("resp4"),
                           construct.BFloat32("resp5"),
                           construct.BFloat32("resp6"),
                           construct.BFloat32("resp7"),
                           construct.BFloat32("resp8"),
                           construct.BFloat32("resp9"),
                           construct.BFloat32("stla"),
                           construct.BFloat32("stlo"),
                           construct.BFloat32("stel"),
                           construct.BFloat32("stdp"),
                           construct.BFloat32("evla"),
                           construct.BFloat32("evlo"),
                           construct.BFloat32("evel"),
                           construct.BFloat32("evdp"),
                           construct.BFloat32("mag"),
                           construct.BFloat32("user0"),
                           construct.BFloat32("user1"),
                           construct.BFloat32("user2"),
                           construct.BFloat32("user3"),
                           construct.BFloat32("user4"),
                           construct.BFloat32("user5"),
                           construct.BFloat32("user6"),
                           construct.BFloat32("user7"),
                           construct.BFloat32("user8"),
                           construct.BFloat32("user9"),
                           construct.BFloat32("dist"),
                           construct.BFloat32("az"),
                           construct.BFloat32("baz"),
                           construct.BFloat32("gcarc"),
                           construct.BFloat32("sb"),
                           construct.BFloat32("sdelta"),
                           construct.BFloat32("depmen"),
                           construct.BFloat32("cmpaz"),
                           construct.BFloat32("cmpinc"),
                           construct.BFloat32("xminimum"),
                           construct.BFloat32("xmaximum"),
                           construct.BFloat32("yminimum"),
                           construct.BFloat32("ymaximum"),
                           construct.BFloat32("unused6"),
                           construct.BFloat32("unused7"),
                           construct.BFloat32("unused8"),
                           construct.BFloat32("unused9"),
                           construct.BFloat32("unused10"),
                           construct.BFloat32("unused11"),
                           construct.BFloat32("unused12"))
    return BIN
# SAC Big Endian binary header, int part


def bin_header_be_int():
    BIN = construct.Struct("BIN",
                           construct.SBInt32("nzyear"),
                           construct.SBInt32("nzjday"),
                           construct.SBInt32("nzhour"),
                           construct.SBInt32("nzmin"),
                           construct.SBInt32("nzsec"),
                           construct.SBInt32("nzmsec"),
                           construct.SBInt32("nvhdr"),
                           construct.SBInt32("norid"),
                           construct.SBInt32("nevid"),
                           construct.SBInt32("npts"),
                           construct.SBInt32("nsnpts"),
                           construct.SBInt32("nwfid"),
                           construct.SBInt32("nxsize"),
                           construct.SBInt32("nysize"),
                           construct.SBInt32("unused15"),
                           construct.SBInt32("iftype"),
                           construct.SBInt32("idep"),
                           construct.SBInt32("iztype"),
                           construct.SBInt32("unused16"),
                           construct.SBInt32("iinst"),
                           construct.SBInt32("istreg"),
                           construct.SBInt32("ievreg"),
                           construct.SBInt32("ievtyp"),
                           construct.SBInt32("iqual"),
                           construct.SBInt32("isynth"),
                           construct.SBInt32("imagtyp"),
                           construct.SBInt32("imagsrc"),
                           construct.SBInt32("unused19"),
                           construct.SBInt32("unused20"),
                           construct.SBInt32("unused21"),
                           construct.SBInt32("unused22"),
                           construct.SBInt32("unused23"),
                           construct.SBInt32("unused24"),
                           construct.SBInt32("unused25"),
                           construct.SBInt32("unused26"),
                           construct.SBInt32("leven"),
                           construct.SBInt32("lpspol"),
                           construct.SBInt32("lovrok"),
                           construct.SBInt32("lcalda"),
                           construct.SBInt32("unused27"))
    return BIN
# SAC Big Endian binary header, string part


def bin_header_be_char():
    BIN = construct.Struct("BIN",
                           construct.String("kstnm", 8),
                           construct.String("kevnm", 16),
                           construct.String("khole", 8),
                           construct.String("ko", 8),
                           construct.String("ka", 8),
                           construct.String("kt0", 8),
                           construct.String("kt1", 8),
                           construct.String("kt2", 8),
                           construct.String("kt3", 8),
                           construct.String("kt4", 8),
                           construct.String("kt5", 8),
                           construct.String("kt6", 8),
                           construct.String("kt7", 8),
                           construct.String("kt8", 8),
                           construct.String("kt9", 8),
                           construct.String("kf", 8),
                           construct.String("kuser0", 8),
                           construct.String("kuser1", 8),
                           construct.String("kuser2", 8),
                           construct.String("kcmpnm", 8),
                           construct.String("knetwk", 8),
                           construct.String("kdatrd", 8),
                           construct.String("kinst", 8))
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
