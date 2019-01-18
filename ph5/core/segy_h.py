#!/usr/bin/env pnpython3
#
# A low level SEG-Y library
#
# SEG-Y REV1, header file descriptions
#
# Optional PASSCAL and Menlo USGS extended trace headers
#
# Steve Azevedo, August 2006
#

import exceptions
import logging
import construct
from ph5.core import ibmfloat, ebcdic

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)


def __version__():
    print PROG_VERSION


class HeaderError (exceptions.Exception):
    def __init__(self, args=None):
        self.args = args

#
# "See SEG rev 1 Data Exchange format"
# SEG Technical Standards Committee
# Release 1.0, May 2002
#
# segy.h -- PASSCAL software release, 198?
#
# segy.h -- Colorado School of Mines, 2006
#

# 3200 byte text header


def text_header():
    TEXT = construct.Struct("TEXT",
                            construct.String("_01_", 80),
                            construct.String("_02_", 80),
                            construct.String("_03_", 80),
                            construct.String("_04_", 80),
                            construct.String("_05_", 80),
                            construct.String("_06_", 80),
                            construct.String("_07_", 80),
                            construct.String("_08_", 80),
                            construct.String("_09_", 80),
                            construct.String("_10_", 80),
                            construct.String("_11_", 80),
                            construct.String("_12_", 80),
                            construct.String("_13_", 80),
                            construct.String("_14_", 80),
                            construct.String("_15_", 80),
                            construct.String("_16_", 80),
                            construct.String("_17_", 80),
                            construct.String("_18_", 80),
                            construct.String("_19_", 80),
                            construct.String("_20_", 80),
                            construct.String("_21_", 80),
                            construct.String("_22_", 80),
                            construct.String("_23_", 80),
                            construct.String("_24_", 80),
                            construct.String("_25_", 80),
                            construct.String("_26_", 80),
                            construct.String("_27_", 80),
                            construct.String("_28_", 80),
                            construct.String("_29_", 80),
                            construct.String("_30_", 80),
                            construct.String("_31_", 80),
                            construct.String("_32_", 80),
                            construct.String("_33_", 80),
                            construct.String("_34_", 80),
                            construct.String("_35_", 80),
                            construct.String("_36_", 80),
                            construct.String("_37_", 80),
                            construct.String("_38_", 80),
                            construct.String("_39_", 80),
                            construct.String("_40_", 80))
    return TEXT


class Text (object):
    __keys__ = ('_01_', '_02_', '_03_', '_04_', '_05_', '_06_', '_07_', '_08_',
                '_09_', '_10_', '_11_', '_12_', '_13_', '_14_', '_15_', '_16_',
                '_17_', '_18_', '_19_', '_20_', '_21_', '_22_', '_23_', '_24_',
                '_25_', '_26_', '_27_', '_28_', '_29_', '_30_', '_31_', '_32_',
                '_33_', '_34_', '_35_', '_36_', '_37_', '_38_', '_39_', '_40_')

    def __init__(self):
        for c in Text.__keys__:
            # c = "_%02d_" % i
            self.__dict__[c] = ebcdic.AsciiToEbcdic("C" + " " * 79)

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in textural header.\n" %
                    k)

    def get(self):
        t = text_header()
        return t.build(self)

    def parse(self, buf):
        t = text_header()
        return t.parse(buf)


# 400 byte reel header
def reel_header():
    REEL = construct.Struct("REEL",
                            # Job identification number
                            construct.UBInt32("jobid"),
                            construct.UBInt32("lino"),  # Line number
                            construct.UBInt32("reno"),  # Reel number
                            construct.UBInt16("ntrpr"),  # Traces per ensemble
                            # Aux traces per ensemble
                            construct.UBInt16("nart"),
                            # ***   Sample interval us   ***
                            construct.UBInt16("hdt"),
                            construct.UBInt16("dto"),  # Field sample interval
                            # ***   Number of samples per trace   ***
                            construct.UBInt16("hns"),
                            # Field samples per trace
                            construct.UBInt16("nso"),
                            # ***  Data format, 5 = 4-byte IEEE   ***
                            construct.UBInt16("format"),
                            construct.UBInt16("fold"),  # Ensemble fold
                            # Trace sorting code, 5 == shot gathers
                            construct.UBInt16("tsort"),
                            construct.UBInt16("vscode"),  # Vertical sum code
                            # Starting sweep frequency
                            construct.UBInt16("hsfs"),
                            # Ending sweep frequency
                            construct.UBInt16("hsfe"),
                            construct.UBInt16("hslen"),  # Sweep length us
                            construct.UBInt16("hstyp"),  # Sweep type code
                            # Trace number of sweep channel
                            construct.UBInt16("schn"),
                            # Sweep taper length ms at start
                            construct.UBInt16("hstas"),
                            # Sweep taper length ms at end
                            construct.UBInt16("hstae"),
                            construct.UBInt16("htatyp"),  # Taper type
                            # Correlated data traces
                            construct.UBInt16("hcorr"),
                            # Binary gain recovered
                            construct.UBInt16("bgrcv"),
                            # Amplitude recovery method
                            construct.UBInt16("rcvm"),
                            construct.UBInt16("mfeet"),  # Measurement system
                            # Impulse signal polarity
                            construct.UBInt16("polyt"),
                            # Vibratory polarity code
                            construct.UBInt16("vpol"),
                            construct.BitField("unass1", 240),  # Unassigned
                            # *** SEG-Y Revision number   ***
                            construct.UBInt16("rev"),
                            construct.UBInt16("trlen"),  # *** Trace length ***
                            # *** Number of extended text headers ***
                            construct.UBInt16("extxt"),
                            construct.BitField("unass2", 94))  # Unassigned
    return REEL

# 400 byte reel header (Little Endian)


def reel_header_le():
    REEL = construct.Struct("REEL",
                            # Job identification number
                            construct.ULInt32("jobid"),
                            construct.ULInt32("lino"),  # Line number
                            construct.ULInt32("reno"),  # Reel number
                            construct.ULInt16("ntrpr"),  # Traces per ensemble
                            # Aux traces per ensemble
                            construct.ULInt16("nart"),
                            # ***   Sample interval us   ***
                            construct.ULInt16("hdt"),
                            construct.ULInt16("dto"),  # Field sample interval
                            # ***   Number of samples per trace   ***
                            construct.ULInt16("hns"),
                            # Field samples per trace
                            construct.ULInt16("nso"),
                            # ***  Data format, 5 = 4-byte IEEE   ***
                            construct.ULInt16("format"),
                            construct.ULInt16("fold"),  # Ensemble fold
                            # Trace sorting code, 5 == shot gathers
                            construct.ULInt16("tsort"),
                            construct.ULInt16("vscode"),  # Vertical sum code
                            # Starting sweep frequency
                            construct.ULInt16("hsfs"),
                            # Ending sweep frequency
                            construct.ULInt16("hsfe"),
                            construct.ULInt16("hslen"),  # Sweep length us
                            construct.ULInt16("hstyp"),  # Sweep type code
                            # Trace number of sweep channel
                            construct.ULInt16("schn"),
                            # Sweep taper length ms at start
                            construct.ULInt16("hstas"),
                            # Sweep taper length ms at end
                            construct.ULInt16("hstae"),
                            construct.ULInt16("htatyp"),  # Taper type
                            # Correlated data traces
                            construct.ULInt16("hcorr"),
                            # Binary gain recovered
                            construct.ULInt16("bgrcv"),
                            # Amplitude recovery method
                            construct.ULInt16("rcvm"),
                            construct.ULInt16("mfeet"),  # Measurement system
                            # Impulse signal polarity
                            construct.ULInt16("polyt"),
                            # Vibratory polarity code
                            construct.ULInt16("vpol"),
                            construct.BitField("unass1", 240),  # Unassigned
                            # *** SEG-Y Revision number   ***
                            construct.ULInt16("rev"),
                            construct.ULInt16("trlen"),  # *** Trace length ***
                            # *** Number of extended text headers ***
                            construct.ULInt16("extxt"),
                            construct.BitField("unass2", 94))  # Unassigned
    return REEL


class Reel (object):
    __keys__ = ("jobid", "lino", "reno", "ntrpr", "nart", "hdt", "dto", "hns",
                "nso", "format", "fold", "tsort", "vscode", "hsfs", "hsfe",
                "hslen", "hstyp", "schn", "hstas", "hstae", "htatyp", "hcorr",
                "bgrcv", "rcvm", "mfeet", "polyt", "vpol", "unass1", "rev",
                "trlen", "extxt", "unass2")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Reel.__keys__:
            self.__dict__[c] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in reel header.\n" %
                    k)

    def get(self):
        if self.endian == 'big':
            r = reel_header()
        else:
            r = reel_header_le()

        return r.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            r = reel_header()
        else:
            r = reel_header_le()

        return r.parse(buf)
#
# Common trace header
#


def trace_header():
    TRACE = construct.Struct("TRACE",
                             # *** Line trace sequence number ***
                             construct.SBInt32("lineSeq"),
                             # Reel trace sequence number
                             construct.SBInt32("reelSeq"),
                             # *** Field record number ***
                             construct.SBInt32("event_number"),
                             # *** Field trace number ***
                             construct.SBInt32("channel_number"),
                             # Energy source point number
                             construct.SBInt32("energySourcePt"),
                             construct.SBInt32("cdpEns"),  # Ensemble number
                             construct.SBInt32(
                                 "traceInEnsemble"),  # Trace number
                             construct.SBInt16("traceID"),  # Trace ID code
                             # Number of vertically summed traces
                             construct.SBInt16("vertSum"),
                             # Number of horizontally summed traces
                             construct.SBInt16("horSum"),
                             construct.SBInt16("dataUse"),  # Data use
                             # Offset (distance)
                             construct.SBInt32("sourceToRecDist"),
                             # Receiver group elevation
                             construct.SBInt32("recElevation"),
                             # Source elevation
                             construct.SBInt32("sourceSurfaceElevation"),
                             construct.SBInt32("sourceDepth"),  # Source depth
                             # Elevation at receiver group
                             construct.SBInt32("datumElevRec"),
                             # Source elevation
                             construct.SBInt32("datumElevSource"),
                             # Water depth at source
                             construct.SBInt32("sourceWaterDepth"),
                             # Water depth at group
                             construct.SBInt32("recWaterDepth"),
                             # Elevation and depth scalar
                             construct.SBInt16("elevationScale"),
                             # Coordinate scalar
                             construct.SBInt16("coordScale"),
                             # X coordinate of source
                             construct.SBInt32("sourceLongOrX"),
                             # Y coordinate of source
                             construct.SBInt32("sourceLatOrY"),
                             # X coordinate of receiver group
                             construct.SBInt32("recLongOrX"),
                             # Y coordinate of receiver group
                             construct.SBInt32("recLatOrY"),
                             # Coordinate system
                             construct.SBInt16("coordUnits"),
                             # Weathering velocity
                             construct.SBInt16("weatheringVelocity"),
                             # Sub-weathering velocity
                             construct.SBInt16("subWeatheringVelocity"),
                             # Uphole time at source in ms
                             construct.SBInt16("sourceUpholeTime"),
                             # Uphole time at group in ms
                             construct.SBInt16("recUpholeTime"),
                             # Source static correction in ms
                             construct.SBInt16("sourceStaticCor"),
                             # Group static correction in ms
                             construct.SBInt16("recStaticCor"),
                             # Total static applied in ms
                             construct.SBInt16("totalStatic"),
                             construct.SBInt16("lagTimeA"),  # Lag time A, ms
                             construct.SBInt16("lagTimeB"),  # Lag time B, ms
                             # Delay recording time, ms
                             construct.SBInt16("delay"),
                             # Mute start time, ms
                             construct.SBInt16("muteStart"),
                             construct.SBInt16("muteEnd"),  # Mute end time, ms
                             # *** Number of samples ***
                             construct.UBInt16("sampleLength"),
                             # *** Sample interval, us ***
                             construct.SBInt16("deltaSample"),
                             construct.SBInt16("gainType"),  # Gain type
                             construct.SBInt16("gainConst"),  # Gain constant
                             construct.SBInt16("initialGain"),  # Early gain
                             construct.SBInt16("correlated"),  # Correlated?
                             # Sweep frequency at start
                             construct.SBInt16("sweepStart"),
                             # Sweep frequency at end
                             construct.SBInt16("sweepEnd"),
                             # Sweep length in ms
                             construct.SBInt16("sweepLength"),
                             construct.SBInt16("sweepType"),  # Sweep type
                             # Sweep taper at start, ms
                             construct.SBInt16("sweepTaperAtStart"),
                             # Sweep taper at end, ms
                             construct.SBInt16("sweepTaperAtEnd"),
                             construct.SBInt16("taperType"),  # Taper type
                             # Alias filter frequency, Hz
                             construct.SBInt16("aliasFreq"),
                             # Alias filter slope, dB/octave
                             construct.SBInt16("aliasSlope"),
                             # Notch filter frequency, Hz
                             construct.SBInt16("notchFreq"),
                             # Notch filter slope, dB/octave
                             construct.SBInt16("notchSlope"),
                             # Low-cut frequency, Hz
                             construct.SBInt16("lowCutFreq"),
                             # High-cut frequency, Hz
                             construct.SBInt16("hiCutFreq"),
                             # Low-cut slope, dB/octave
                             construct.SBInt16("lowCutSlope"),
                             # High-cut slope, dB/octave
                             construct.SBInt16("hiCutSlope"),
                             construct.SBInt16("year"),  # Year
                             construct.SBInt16("day"),  # Day of Year
                             construct.SBInt16("hour"),  # Hour
                             construct.SBInt16("minute"),  # Minute
                             construct.SBInt16("second"),  # Seconds
                             # Time bias code
                             construct.SBInt16("timeBasisCode"),
                             # Trace weighting for LSB
                             construct.SBInt16("traceWeightingFactor"),
                             # Geophone group number
                             construct.UBInt16("phoneRollPos1"),
                             # Geophone group number (field)
                             construct.UBInt16("phoneFirstTrace"),
                             # Geophone group number, last trace (field)
                             construct.UBInt16("phoneLastTrace"),
                             construct.SBInt16("gapSize"),  # Gap size
                             construct.SBInt16("taperOvertravel"))
    # Over travel
    return TRACE

#
# Common trace header (Little Endian)
#


def trace_header_le():
    TRACE = construct.Struct("TRACE",
                             # *** Line trace sequence number ***
                             construct.SLInt32("lineSeq"),
                             # Reel trace sequence number
                             construct.SLInt32("reelSeq"),
                             # *** Field record number ***
                             construct.SLInt32("event_number"),
                             # *** Field trace number ***
                             construct.SLInt32("channel_number"),
                             # Energy source point number
                             construct.SLInt32("energySourcePt"),
                             construct.SLInt32("cdpEns"),  # Ensemble number
                             construct.SLInt32(
                                 "traceInEnsemble"),  # Trace number
                             construct.SLInt16("traceID"),  # Trace ID code
                             # Number of vertically summed traces
                             construct.SLInt16("vertSum"),
                             # Number of horizontally summed traces
                             construct.SLInt16("horSum"),
                             construct.SLInt16("dataUse"),  # Data use
                             # Offset (distance)
                             construct.SLInt32("sourceToRecDist"),
                             # Receiver group elevation
                             construct.SLInt32("recElevation"),
                             # Source elevation
                             construct.SLInt32("sourceSurfaceElevation"),
                             construct.SLInt32("sourceDepth"),  # Source depth
                             # Elevation at receiver group
                             construct.SLInt32("datumElevRec"),
                             # Source elevation
                             construct.SLInt32("datumElevSource"),
                             # Water depth at source
                             construct.SLInt32("sourceWaterDepth"),
                             # Water depth at group
                             construct.SLInt32("recWaterDepth"),
                             # Elevation and depth scalar
                             construct.SLInt16("elevationScale"),
                             # Coordinate scalar
                             construct.SLInt16("coordScale"),
                             # X coordinate of source
                             construct.SLInt32("sourceLongOrX"),
                             # Y coordinate of source
                             construct.SLInt32("sourceLatOrY"),
                             # X coordinate of receiver group
                             construct.SLInt32("recLongOrX"),
                             # Y coordinate of receiver group
                             construct.SLInt32("recLatOrY"),
                             # Coordinate system
                             construct.SLInt16("coordUnits"),
                             # Weathering velocity
                             construct.SLInt16("weatheringVelocity"),
                             # Sub-weathering velocity
                             construct.SLInt16("subWeatheringVelocity"),
                             # Uphole time at source in ms
                             construct.SLInt16("sourceUpholeTime"),
                             # Uphole time at group in ms
                             construct.SLInt16("recUpholeTime"),
                             # Source static correction in ms
                             construct.SLInt16("sourceStaticCor"),
                             # Group static correction in ms
                             construct.SLInt16("recStaticCor"),
                             # Total static applied in ms
                             construct.SLInt16("totalStatic"),
                             construct.SLInt16("lagTimeA"),  # Lag time A, ms
                             construct.SLInt16("lagTimeB"),  # Lag time B, ms
                             # Delay recording time, ms
                             construct.SLInt16("delay"),
                             # Mute start time, ms
                             construct.SLInt16("muteStart"),
                             construct.SLInt16("muteEnd"),  # Mute end time, ms
                             # *** Number of samples ***
                             construct.ULInt16("sampleLength"),
                             # *** Sample interval, us ***
                             construct.SLInt16("deltaSample"),
                             construct.SLInt16("gainType"),  # Gain type
                             construct.SLInt16("gainConst"),  # Gain constant
                             construct.SLInt16("initialGain"),  # Early gain
                             construct.SLInt16("correlated"),  # Correlated?
                             # Sweep frequency at start
                             construct.SLInt16("sweepStart"),
                             # Sweep frequency at end
                             construct.SLInt16("sweepEnd"),
                             # Sweep length in ms
                             construct.SLInt16("sweepLength"),
                             construct.SLInt16("sweepType"),  # Sweep type
                             # Sweep taper at start, ms
                             construct.SLInt16("sweepTaperAtStart"),
                             # Sweep taper at end, ms
                             construct.SLInt16("sweepTaperAtEnd"),
                             construct.SLInt16("taperType"),  # Taper type
                             # Alias filter frequency, Hz
                             construct.SLInt16("aliasFreq"),
                             # Alias filter slope, dB/octave
                             construct.SLInt16("aliasSlope"),
                             # Notch filter frequency, Hz
                             construct.SLInt16("notchFreq"),
                             # Notch filter slope, dB/octave
                             construct.SLInt16("notchSlope"),
                             # Low-cut frequency, Hz
                             construct.SLInt16("lowCutFreq"),
                             # High-cut frequency, Hz
                             construct.SLInt16("hiCutFreq"),
                             # Low-cut slope, dB/octave
                             construct.SLInt16("lowCutSlope"),
                             # High-cut slope, dB/octave
                             construct.SLInt16("hiCutSlope"),
                             construct.SLInt16("year"),  # Year
                             construct.SLInt16("day"),  # Day of Year
                             construct.SLInt16("hour"),  # Hour
                             construct.SLInt16("minute"),  # Minute
                             construct.SLInt16("second"),  # Seconds
                             # Time bias code
                             construct.SLInt16("timeBasisCode"),
                             # Trace weighting for LSB
                             construct.SLInt16("traceWeightingFactor"),
                             # Geophone group number
                             construct.ULInt16("phoneRollPos1"),
                             # Geophone group number (field)
                             construct.ULInt16("phoneFirstTrace"),
                             # Geophone group number, last trace (field)
                             construct.ULInt16("phoneLastTrace"),
                             construct.SLInt16("gapSize"),  # Gap size
                             construct.SLInt16("taperOvertravel"))
    # Over travel
    return TRACE


class Trace (object):
    __keys__ = ("lineSeq", "reelSeq", "event_number", "channel_number",
                "energySourcePt", "cdpEns", "traceInEnsemble", "traceID",
                "vertSum", "horSum", "dataUse", "sourceToRecDist",
                "recElevation", "sourceSurfaceElevation", "sourceDepth",
                "datumElevRec", "datumElevSource", "sourceWaterDepth",
                "recWaterDepth", "elevationScale", "coordScale",
                "sourceLongOrX", "sourceLatOrY", "recLongOrX", "recLatOrY",
                "coordUnits", "weatheringVelocity", "subWeatheringVelocity",
                "sourceUpholeTime", "recUpholeTime", "sourceStaticCor",
                "recStaticCor", "totalStatic", "lagTimeA", "lagTimeB", "delay",
                "muteStart", "muteEnd", "sampleLength", "deltaSample",
                "gainType", "gainConst", "initialGain", "correlated",
                "sweepStart", "sweepEnd", "sweepLength", "sweepType",
                "sweepTaperAtStart", "sweepTaperAtEnd", "taperType",
                "aliasFreq", "aliasSlope", "notchFreq", "notchSlope",
                "lowCutFreq", "hiCutFreq", "lowCutSlope", "hiCutSlope", "year",
                "day", "hour", "minute", "second", "timeBasisCode",
                "traceWeightingFactor", "phoneRollPos1", "phoneFirstTrace",
                "phoneLastTrace", "gapSize", "taperOvertravel")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace.__keys__:
            self.__dict__[c] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" %
                    k)

    def get(self):
        if self.endian == 'big':
            t = trace_header()
        else:
            t = trace_header_le()

        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = trace_header()
        else:
            t = trace_header_le()

        return t.parse(buf)

#
# PASSCAL extended header
#


def passcal_header():
    TRACE = construct.Struct("TRACE",
                             construct.String("station_name", 6),
                             construct.String("sensor_serial", 8),
                             construct.String("channel_name", 4),
                             construct.SBInt16("totalStaticHi"),
                             construct.SBInt32("samp_rate"),
                             construct.SBInt16("data_form"),
                             construct.SBInt16("m_secs"),
                             construct.SBInt16("trigyear"),
                             construct.SBInt16("trigday"),
                             construct.SBInt16("trighour"),
                             construct.SBInt16("trigminute"),
                             construct.SBInt16("trigsecond"),
                             construct.SBInt16("trigmills"),
                             construct.BFloat32("scale_fac"),
                             construct.UBInt16("inst_no"),
                             construct.SBInt16("unassigned"),
                             construct.SBInt32("num_samps"),
                             construct.SBInt32("max"),
                             construct.SBInt32("min"))

    return TRACE

#
# PASSCAL extended header (Little Endian)
#


def passcal_header_le():
    TRACE = construct.Struct("TRACE",
                             construct.String("station_name", 6),
                             construct.String("sensor_serial", 8),
                             construct.String("channel_name", 4),
                             construct.SLInt16("totalStaticHi"),
                             construct.SLInt32("samp_rate"),
                             construct.SLInt16("data_form"),
                             construct.SLInt16("m_secs"),
                             construct.SLInt16("trigyear"),
                             construct.SLInt16("trigday"),
                             construct.SLInt16("trighour"),
                             construct.SLInt16("trigminute"),
                             construct.SLInt16("trigsecond"),
                             construct.SLInt16("trigmills"),
                             construct.LFloat32("scale_fac"),
                             construct.ULInt16("inst_no"),
                             construct.SLInt16("unassigned"),
                             construct.SLInt32("num_samps"),
                             construct.SLInt32("max"),
                             construct.SLInt32("min"))

    return TRACE


class Passcal (object):
    __keys__ = ("station_name", "sensor_serial", "channel_name",
                "totalStaticHi", "samp_rate", "data_form", "m_secs",
                "trigyear", "trigday", "trighour", "trigminute", "trigsecond",
                "trigmills", "scale_fac", "inst_no", "unassigned", "num_samps",
                "max", "min")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Passcal.__keys__:
            self.__dict__[c] = 0x00

        self.__dict__['station_name'] = '      '
        self.__dict__['sensor_serial'] = '        '
        self.__dict__['channel_name'] = '    '

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" %
                    k)

    def get(self):
        if self.endian == 'big':
            t = passcal_header()
        else:
            t = passcal_header_le()

        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = passcal_header()
        else:
            t = passcal_header_le()

        return t.parse(buf)

#
# Menlo Park USGS extended header
#


def menlo_header():
    TRACE = construct.Struct("TRACE",
                             # Microsec trace start time
                             construct.SBInt32("start_usec"),
                             # Charge size (kg)
                             construct.SBInt16("shot_size"),
                             # Shot/trigger time - year
                             construct.SBInt16("shot_year"),
                             # Shot/trigger time- Julian day
                             construct.SBInt16("shot_doy"),
                             # Shot/trigger time - hour
                             construct.SBInt16("shot_hour"),
                             # Shot/trigger time - minute
                             construct.SBInt16("shot_minute"),
                             # Shot/trigger time - second
                             construct.SBInt16("shot_second"),
                             # Shot/trigger time - microsec
                             construct.SBInt32("shot_us"),
                             # Override for sample interval (SET = 0)
                             construct.SBInt32("si_override"),
                             # Azimuth of sensor orient axis (empty)
                             construct.SBInt16("sensor_azimuth"),
                             # Geophone inclination (empty)
                             construct.SBInt16("sensor_inclination"),
                             # LMO static (x/v)  (ms) (empty)
                             construct.SBInt32("lmo_ms"),
                             # LMO flag: (0=Y, 1=N) (SET = 1)
                             construct.SBInt16("lmo_flag"),
                             # 13 = rt-130, 16 = texan
                             construct.SBInt16("inst_type"),
                             construct.SBInt16("correction"),  # 0
                             # Azimuth of source-receiver (min of arc)
                             construct.SBInt16("azimuth"),
                             construct.SBInt16(
                                 "sensor_type"),  # 1--L28 (PASSCAL)(4.5 Hz)\
                             # 2--L22 (2 Hz)\
                             # 3--L10B (8 Hz)\
                             # 4--L4 1 Hz\
                             # 5--L4 2 Hz\
                             # 6--FBA\
                             # 7--TDC-10 (4.5 Hz)\
                             # 8--L28 (GSC)\
                             # 9--LRS1033 (4.5 HZ)\
                             # 99--unknown
                             # Geophone number (empty)
                             construct.SBInt16("sensor_sn"),
                             construct.UBInt16("das_sn"),  # Inst. ID number
                             construct.UBInt16("empty1"),
                             # Number of samples if > 2^15 (see 115-116)
                             construct.SBInt32("samples"),
                             construct.UBInt32("empty2"),
                             # Receiver clock drift removed
                             construct.SBInt16("clock_drift"),
                             construct.UBInt16("empty3"))

    return TRACE

#
# Menlo Park USGS extended header (Little Endian)
#


def menlo_header_le():
    TRACE = construct.Struct("TRACE",
                             # Microsec trace start time
                             construct.SLInt32("start_usec"),
                             # Charge size (kg)
                             construct.SLInt16("shot_size"),
                             # Shot/trigger time - year
                             construct.SLInt16("shot_year"),
                             # Shot/trigger time- Julian day
                             construct.SLInt16("shot_doy"),
                             # Shot/trigger time - hour
                             construct.SLInt16("shot_hour"),
                             # Shot/trigger time - minute
                             construct.SLInt16("shot_minute"),
                             # Shot/trigger time - second
                             construct.SLInt16("shot_second"),
                             # Shot/trigger time - microsec
                             construct.SLInt32("shot_us"),
                             # Override for sample interval (SET = 0)
                             construct.SLInt32("si_override"),
                             # Azimuth of sensor orient axis (empty)
                             construct.SLInt16("sensor_azimuth"),
                             # Geophone inclination (empty)
                             construct.SLInt16("sensor_inclination"),
                             # LMO static (x/v)  (ms) (empty)
                             construct.SLInt32("lmo_ms"),
                             # LMO flag: (0=Y, 1=N) (SET = 1)
                             construct.SLInt16("lmo_flag"),
                             # 13 = rt-130, 16 = texan
                             construct.SLInt16("inst_type"),
                             construct.SLInt16("correction"),  # 0
                             # Azimuth of source-receiver (min of arc)
                             construct.SLInt16("azimuth"),
                             construct.SLInt16(
                                 "sensor_type"),  # 1--L28 (PASSCAL)(4.5 Hz)\
                             # 2--L22 (2 Hz)\
                             # 3--L10B (8 Hz)\
                             # 4--L4 1 Hz\
                             # 5--L4 2 Hz\
                             # 6--FBA\
                             # 7--TDC-10 (4.5 Hz)\
                             # 8--L28 (GSC)\
                             # 9--LRS1033 (4.5 HZ)\
                             # 99--unknown
                             # Geophone number (empty)
                             construct.SLInt16("sensor_sn"),
                             construct.ULInt16("das_sn"),  # Inst. ID number
                             construct.ULInt16("empty1"),
                             # Number of samples if > 2^15 (see 115-116)
                             construct.SLInt32("samples"),
                             construct.ULInt32("empty2"),
                             # Receiver clock drift removed
                             construct.SLInt16("clock_drift"),
                             construct.ULInt16("empty3"))

    return TRACE


class Menlo (object):
    __keys__ = ("start_usec", "shot_size", "shot_year", "shot_doy",
                "shot_hour", "shot_minute",
                "shot_second", "shot_us", "si_override", "sensor_azimuth",
                "sensor_inclination",
                "lmo_ms", "lmo_flag", "inst_type", "correction", "azimuth",
                "sensor_type", "sensor_sn",
                "das_sn", "empty1", "samples", "empty2", "clock_drift",
                "empty3")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Menlo.__keys__:
            self.__dict__[c] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" %
                    k)

    def get(self):
        if self.endian == 'big':
            t = menlo_header()
        else:
            t = menlo_header_le()

        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = menlo_header()
        else:
            t = menlo_header_le()

        return t.parse(buf)

#
# SEG-Y Rev 1.0 extended header
#


def seg_header():
    TRACE = construct.Struct("TRACE",
                             # X coordinate of ensemble
                             construct.SBInt32("Xcoor"),
                             # Y coordinate of ensemble
                             construct.SBInt32("Ycoor"),
                             # Same as lino in reel header
                             construct.SBInt32("Inn"),
                             construct.SBInt32("Cnn"),  # Same as cdp
                             construct.SBInt32("Spn"),  # Shot point number
                             # Scaler to apply to Spn
                             construct.SBInt16("Scal"),
                             # Trace value measurement units
                             construct.SBInt16("Tvmu"),
                             # Transduction constant mantissa
                             construct.SBInt32("Tucmant"),
                             # Transduction constant exponent
                             construct.SBInt16("Tucexp"),
                             construct.SBInt16("Tdu"),  # Transduction units
                             # Device/Trace identifier
                             construct.SBInt16("Dti"),
                             construct.SBInt16("Tscaler"),  # Time scalar
                             # Source Type/Orientation
                             construct.SBInt16("Sto"),
                             # Source Energy direction
                             construct.String("Sed", 6),
                             # Source measurement mantissa
                             construct.SBInt32("Smsmant"),
                             # Source measurement exponent
                             construct.SBInt16("Smsexp"),
                             # Source measurement Units
                             construct.SBInt16("Smu"),
                             # Last 8 bytes undefined in rev1
                             # Trace start time usec
                             construct.UBInt32("start_usec"),
                             construct.UBInt32("shot_us"))  # Shot time usec
    return TRACE

#
# SEG-Y Rev 1.0 extended header (Little Endian)
#


def seg_header_le():
    TRACE = construct.Struct("TRACE",
                             # X coordinate of ensemble
                             construct.SLInt32("Xcoor"),
                             # Y coordinate of ensemble
                             construct.SLInt32("Ycoor"),
                             # Same as lino in reel header
                             construct.SLInt32("Inn"),
                             construct.SLInt32("Cnn"),  # Same as cdp
                             construct.SLInt32("Spn"),  # Shot point number
                             # Scaler to apply to Spn
                             construct.SLInt16("Scal"),
                             # Trace value measurement units
                             construct.SLInt16("Tvmu"),
                             # Transduction constant mantissa
                             construct.SLInt32("Tucmant"),
                             # Transduction constant exponent
                             construct.SLInt16("Tucexp"),
                             construct.SLInt16("Tdu"),  # Transduction units
                             # Device/Trace identifier
                             construct.SLInt16("Dti"),
                             construct.SLInt16("Tscaler"),  # Time scalar
                             # Source Type/Orientation
                             construct.SLInt16("Sto"),
                             # Source Energy direction
                             construct.String("Sed", 6),
                             # Source measurement mantissa
                             construct.SLInt32("Smsmant"),
                             # Source measurement exponent
                             construct.SLInt16("Smsexp"),
                             # Source measurement Units
                             construct.SLInt16("Smu"),
                             # Last 8 bytes undefined in rev1
                             # Trace start time usec
                             construct.UBInt32("start_usec"),
                             construct.UBInt32("shot_us"))  # Shot time usec
    return TRACE


class Seg (object):
    __keys__ = ("Xcoor", "Ycoor", "Inn", "Cnn", "Spn", "Scal", "Tvmu",
                "Tucmant", "Tucexp", "Tdu",
                "Dti", "Tscaler", "Sto", "Sed", "Smsmant", "Smsexp", "Smu",
                "start_usec", "shot_us")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Seg.__keys__:
            self.__dict__[c] = 0x00

        self.__dict__['Sed'] = '      '

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" %
                    k)

    def get(self):
        if self.endian == 'big':
            t = seg_header()
        else:
            t = seg_header_le()

        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = seg_header()
        else:
            t = seg_header_le()

        return t.parse(buf)

#
# iNova FireFly extened header version 3.0 (Big endian)
#


def inova_header():
    TRACE = construct.Struct("TRACE",
                             # iNova revision (322)
                             construct.UBInt16("Revision"),
                             # Derived from POSIX time of shot
                             construct.UBInt32("ShotID"),
                             # Aux channel description
                             construct.UBInt8("AuxChanSig"),
                             #    0x08 -- Master Clock Timebreak
                             #    0x09 -- Master Confirmation Timebreak
                             #    0x0A -- Slave Clock Timebreak
                             #    0x0B -- Slave Confirmation Timebreak
                             #    0x0C -- Analog Uphole
                             #    0x0E -- Digital Uphole
                             #    0x10 -- Waterbreak
                             #    0x14 -- User Specified #1
                             #    0x18 -- User Specified #2
                             #    0x1C -- User Specified #3
                             #    0x20 -- Unfiltered Pilot
                             #    0x24 -- Filtered Pilot
                             #    0x28 -- User Specified #4
                             #    0x2C -- User Specified #5
                             #    0x30 -- User Specified #6
                             #    0x31 -- Vibrator Reference
                             #    0x32 -- Vibrator Out
                             #    0x33 -- Vibrator User
                             #    0x34 -- User Specified #7
                             #    0x38 -- User Specified #8
                             #    0x3C -- User Specified #9
                             #    0x3D -- Aux Channel from iNova Image System
                             #    0x3E -- GPS Aux / External Data
                             #    0x3F -- Unused Channel
                             construct.UBInt8("AuxChanID"),  # Aux Channel ID
                             # Shot Point Line in hundredths
                             construct.UBInt32("SPL"),
                             # Shot Point Station in hundredths
                             construct.UBInt32("SPS"),
                             construct.UBInt16("unass01"),  # Unassigned
                             construct.UBInt16("unass02"),  # Unassigned
                             # Sensor Interface Unit Type
                             construct.UBInt8("SenInt"),
                             #    18 -- VSM
                             #    21 -- Vectorseis
                             #    42 -- Geophone Digitizer Unit
                             #    49 -- iNova Standard Analog Channel GDC
                             # Vectorseis sensitivity
                             construct.UBInt8("VectSens"),
                             #    0 = 40nG
                             #    3 = 160nG
                             # Absolute horizontal orientation azimuth of
                             # Vectorseis in
                             construct.UBInt16("HorAz"),
                             # 0.0001 radians, measured from due-North
                             # Absolute vertical orientation angle, in 0.0001
                             # radians.
                             construct.UBInt16("VertAngle"),
                             # A vertically planted sensor will
                             # have a value of
                             # 1416 (Pi * 10,000),
                             # while a horizontally planted sensor will have a
                             # value of 15708 (Pi/2 * 10,000)
                             construct.UBInt8("SourceType"),  # Source type:
                             #    0 -- Built-in test
                             #    1 -- Dynamite
                             #    2 -- Vibrator
                             #    3 -- AirGun
                             #    4 -- WaterGun
                             #    5 -- WeightDrop
                             #    6 -- Other
                             #    7 -- MixedSources
                             #    8 -- NoSource or Unknown
                             #    9 -- TestOsc (For GDC this is an
                             # external test
                             # oscillator)
                             #    10 -- Impulsive
                             construct.UBInt8("SensorType"),  # Sensor type:
                             #    0 -- Unknown
                             #    1 -- Hydrophone
                             #    2 -- Geo-Vertical Geophone, Marshphone,
                             # or Z
                             #    3 -- Geo-Horiz Inline Geophone -- X
                             #    4 -- Geo-Horiz Cross-Line Geophone -- Y
                             #    5 -- Geo-Horiz Other
                             #    6 -- SVSM Vertical -- Z
                             #    7 -- SVSM Horizontal Inline -- X
                             #    8 -- SVSM Horizontal Crossline -- Y
                             #    9 -- Acc-Horiz Other
                             # Auxillary Channel Set type
                             construct.UBInt8("AuxChanSetType"),
                             #    0x00 -- Unused channel
                             #    0x02 -- Timebreak
                             #    0x03 -- Uphole
                             #    0x04 -- Waterbreak
                             #    0x05 -- Time Counter
                             #    0x06 -- External Data
                             #    0x07 -- Other
                             #    0x08 -- Unfiltered Pilot
                             #    0x09 -- Filtered Pilot
                             #    0x0A -- Special #1
                             #    0x0B -- Special #2
                             #    0x0D -- Special #3
                             #    0x0E -- Special #4
                             #    0x0F -- Special #5
                             #    0xFA -- Reserved (T2 only)
                             # Noise Edit Type:
                             construct.UBInt8("NoiseEditType"),
                             #    0 -- Raw Data, Vertical Stack
                             #    2 -- Diversity Stack
                             # Noise Edit Gate Size:
                             construct.UBInt16("NoiseEditGate"),
                             #    0 -- Raw Data, Vertical Stack
                             #    n -- Number of Samples in Gate,
                             # Diversity Stack
                             # System Device type:
                             construct.UBInt8("SystemDevice"),
                             #    7 -- MRX
                             #    9 -- RSR
                             #    17 -- VRSR
                             #    20 -- VRSR2
                             #    23 -- AuxUNIT-1C
                             #    25 -- DUNIT-3C
                             #    29 -- Analog-1C
                             #    37 -- FireFly
                             #    48 -- Node
                             construct.BitField("FSU", 3),  # FSU Serial Number
                             # Device Channel Number
                             construct.UBInt8("DevChan"),
                             # Source coordinate confidence indicator. Rates
                             # the level
                             construct.UBInt8("SourceCoCo"),
                             # of confidence in the accuracy of source x,y,z.
                             # 0 -- Good
                             # Device status bits
                             construct.UBInt8("DevStatusBits"),
                             #    Bit 0 -- A/D Modulator Over-range
                             #    Bit 1 -- A/D Decimator Numerical Overflow
                             #    Bit 2 -- Analog Preamp Overscale or
                             # VSMT Data Invalid
                             #    Bit 3 -- SVSM VLFF error
                             #    Bit 4 -- Invalid Receiver Line/Station
                             #    Bit 5 -- Trace was Zero filled (T2 only)
                             #    Bit 6 -- Battery improperly removed
                             #    Bit 7 -- SVSM Dynamic Offset Filter mode,
                             # 0 = static
                             # BIT test type and codes (0 - 28) See FireFly SEG
                             # Y Ver 3.0 Tech Bulletin
                             construct.UBInt8("BITTest"),
                             # Sweep Phase Rotation; 0 if undefined
                             construct.UBInt16("SweepPhaseRot"),
                             construct.UBInt8("unass03"),  # Unassigned
                             construct.UBInt8("BoxFun"),  # Box function
                             # Source effort used to generate the trace
                             # (mantissa)
                             construct.UBInt32("SourceEffortM"),
                             # Source effort, (exponent)
                             construct.UBInt16("SourceEffortE"),
                             # Source measurement units
                             construct.UBInt16("SourceUnits"),
                             #    -1 -- Other
                             #    0 -- Unknown
                             #    1 -- Joule
                             #    2 -- Kilowatt
                             #    3 -- Pascal
                             #    4 -- Bar
                             #    5 -- Bar-meter
                             #    6 -- Kilograms
                             #    7 -- Pounds
                             construct.UBInt8("EventType"),  # Event type:
                             #    0x00 -- Zeroed or truncated trace
                             #    0x40 -- BIT data - Raw Trace
                             #    0x80 -- Seis data - Normal, Raw
                             #    0x88 -- Seis data - Normal, Stack
                             #    0x90 -- Seis data - Normal, Correlated
                             #    0xA0 -- Seis data - Test, Raw
                             #    0xA8 -- Seis data - Test, Stack
                             #    0xB0 -- Seis data - Test, Correlated
                             # Sensor type ID
                             construct.UBInt8("SensorTypeID"),
                             #    0x00 -- No sensor defined
                             #    0x01 -- Geophone - 1 component vertical
                             #    0x02 -- Marshphone
                             #    0x03 -- Hydrophone
                             #    0x04 -- Aux
                             #    0x05 -- Geophone-3c Horizontal,
                             # X -- In-line
                             #    0x06 -- Geophone-3c Horizontal,
                             # Y -- Cross-line
                             #    0x07 -- Geophone-3c Vertical, Z
                             #    0x08 -- Reserved
                             #    0x0C -- Accelerometer-3c Horizontal,
                             # X -- In-line
                             #    0x0C -- Accelerometer-3c Horizontal,
                             # Y -- Cross-line
                             #    0x0C -- Accelerometer-3c Vertical, Z
                             # Sensor serial number
                             construct.BitField("SensorSerial", 3),
                             # Sensor version number
                             construct.UBInt8("SensorVersion"),
                             construct.UBInt8("SensorRev"),  # Sensor revision
                             construct.UBInt8("VOR"))  # VOR applied
    #    0 -- No VOR applied
    #    2 -- VOR applied
    return TRACE
#
# iNova FireFly extened header version 3.0 (Little endian)
#


def inova_header_le():
    TRACE = construct.Struct("TRACE",
                             # iNova revision (322)
                             construct.ULInt16("Revision"),
                             # Derived from POSIX time of shot
                             construct.ULInt32("ShotID"),
                             # Aux channel description
                             construct.ULInt8("AuxChanSig"),
                             #    0x08 -- Master Clock Timebreak
                             #    0x09 -- Master Confirmation Timebreak
                             #    0x0A -- Slave Clock Timebreak
                             #    0x0B -- Slave Confirmation Timebreak
                             #    0x0C -- Analog Uphole
                             #    0x0E -- Digital Uphole
                             #    0x10 -- Waterbreak
                             #    0x14 -- User Specified #1
                             #    0x18 -- User Specified #2
                             #    0x1C -- User Specified #3
                             #    0x20 -- Unfiltered Pilot
                             #    0x24 -- Filtered Pilot
                             #    0x28 -- User Specified #4
                             #    0x2C -- User Specified #5
                             #    0x30 -- User Specified #6
                             #    0x31 -- Vibrator Reference
                             #    0x32 -- Vibrator Out
                             #    0x33 -- Vibrator User
                             #    0x34 -- User Specified #7
                             #    0x38 -- User Specified #8
                             #    0x3C -- User Specified #9
                             #    0x3D -- Aux Channel from iNova Image System
                             #    0x3E -- GPS Aux / External Data
                             #    0x3F -- Unused Channel
                             construct.ULInt8("AuxChanID"),  # Aux Channel ID
                             # Shot Point Line in hundredths
                             construct.ULInt32("SPL"),
                             # Shot Point Station in hundredths
                             construct.ULInt32("SPS"),
                             construct.ULInt16("unass01"),  # Unassigned
                             construct.ULInt16("unass02"),  # Unassigned
                             # Sensor Interface Unit Type
                             construct.ULInt8("SenInt"),
                             #    18 -- VSM
                             #    21 -- Vectorseis
                             #    42 -- Geophone Digitizer Unit
                             #    49 -- iNova Standard Analog Channel GDC
                             # Vectorseis sensitivity
                             construct.ULInt8("VectSens"),
                             #    0 = 40nG
                             #    3 = 160nG
                             # Absolute horizontal orientation azimuth of
                             # Vectorseis in
                             construct.ULInt16("HorAz"),
                             # 0.0001 radians, measured from due-North
                             # Absolute vertical orientation angle, in 0.0001
                             # radians.
                             construct.ULInt16("VertAngle"),
                             # A vertically planted sensor will
                             # have a value of
                             # 31416 (Pi * 10,000),
                             # while a horizontally planted sensor will have a
                             # value of 15708 (Pi/2 * 10,000)
                             construct.ULInt8("SourceType"),  # Source type:
                             #    0 -- Built-in test
                             #    1 -- Dynamite
                             #    2 -- Vibrator
                             #    3 -- AirGun
                             #    4 -- WaterGun
                             #    5 -- WeightDrop
                             #    6 -- Other
                             #    7 -- MixedSources
                             #    8 -- NoSource or Unknown
                             #    9 -- TestOsc (For GDC this is an external
                             # test oscillator)
                             #    10 -- Impulsive
                             construct.ULInt8("SensorType"),  # Sensor type:
                             #    0 -- Unknown
                             #    1 -- Hydrophone
                             #    2 -- Geo-Vertical Geophone, Marshphone,
                             # or Z
                             #    3 -- Geo-Horiz Inline Geophone -- X
                             #    4 -- Geo-Horiz Cross-Line Geophone -- Y
                             #    5 -- Geo-Horiz Other
                             #    6 -- SVSM Vertical -- Z
                             #    7 -- SVSM Horizontal Inline -- X
                             #    8 -- SVSM Horizontal Crossline -- Y
                             #    9 -- Acc-Horiz Other
                             # Auxillary Channel Set type
                             construct.ULInt8("AuxChanSetType"),
                             #    0x00 -- Unused channel
                             #    0x02 -- Timebreak
                             #    0x03 -- Uphole
                             #    0x04 -- Waterbreak
                             #    0x05 -- Time Counter
                             #    0x06 -- External Data
                             #    0x07 -- Other
                             #    0x08 -- Unfiltered Pilot
                             #    0x09 -- Filtered Pilot
                             #    0x0A -- Special #1
                             #    0x0B -- Special #2
                             #    0x0D -- Special #3
                             #    0x0E -- Special #4
                             #    0x0F -- Special #5
                             #    0xFA -- Reserved (T2 only)
                             # Noise Edit Type:
                             construct.ULInt8("NoiseEditType"),
                             #    0 -- Raw Data, Vertical Stack
                             #    2 -- Diversity Stack
                             # Noise Edit Gate Size:
                             construct.ULInt16("NoiseEditGate"),
                             #    0 -- Raw Data, Vertical Stack
                             #    n -- Number of Samples in Gate,
                             # Diversity Stack
                             # System Device type:
                             construct.ULInt8("SystemDevice"),
                             #    7 -- MRX
                             #    9 -- RSR
                             #    17 -- VRSR
                             #    20 -- VRSR2
                             #    23 -- AuxUNIT-1C
                             #    25 -- DUNIT-3C
                             #    29 -- Analog-1C
                             #    37 -- FireFly
                             #    48 -- Node
                             construct.BitField("FSU", 3),  # FSU Serial Number
                             # Device Channel Number
                             construct.ULInt8("DevChan"),
                             # Source coordinate confidence indicator. Rates
                             # the level
                             construct.ULInt8("SourceCoCo"),
                             # of confidence in the accuracy of source x,y,z.
                             # 0 -- Good
                             # Device status bits
                             construct.ULInt8("DevStatusBits"),
                             #    Bit 0 -- A/D Modulator Over-range
                             #    Bit 1 -- A/D Decimator Numerical Overflow
                             #    Bit 2 -- Analog Preamp Overscale or
                             # VSMT Data Invalid
                             #    Bit 3 -- SVSM VLFF error
                             #    Bit 4 -- Invalid Receiver Line/Station
                             #    Bit 5 -- Trace was Zero filled (T2 only)
                             #    Bit 6 -- Battery improperly removed
                             #    Bit 7 -- SVSM Dynamic Offset Filter mode,
                             # 0 = static
                             # BIT test type and codes (0 - 28) See FireFly SEG
                             # Y Ver 3.0 Tech Bulletin
                             construct.ULInt8("BITTest"),
                             # Sweep Phase Rotation; 0 if undefined
                             construct.ULInt16("SweepPhaseRot"),
                             construct.ULInt8("unass03"),  # Unassigned
                             construct.ULInt8("BoxFun"),  # Box function
                             # Source effort used to generate the trace
                             # (mantissa)
                             construct.ULInt32("SourceEffortM"),
                             # Source effort, (exponent)
                             construct.ULInt16("SourceEffortE"),
                             # Source measurement units
                             construct.ULInt16("SourceUnits"),
                             #    -1 -- Other
                             #    0 -- Unknown
                             #    1 -- Joule
                             #    2 -- Kilowatt
                             #    3 -- Pascal
                             #    4 -- Bar
                             #    5 -- Bar-meter
                             #    6 -- Kilograms
                             #    7 -- Pounds
                             construct.ULInt8("EventType"),  # Event type:
                             #    0x00 -- Zeroed or truncated trace
                             #    0x40 -- BIT data - Raw Trace
                             #    0x80 -- Seis data - Normal, Raw
                             #    0x88 -- Seis data - Normal, Stack
                             #    0x90 -- Seis data - Normal, Correlated
                             #    0xA0 -- Seis data - Test, Raw
                             #    0xA8 -- Seis data - Test, Stack
                             #    0xB0 -- Seis data - Test, Correlated
                             # Sensor type ID
                             construct.ULInt8("SensorTypeID"),
                             #    0x00 -- No sensor defined
                             #    0x01 -- Geophone - 1 component vertical
                             #    0x02 -- Marshphone
                             #    0x03 -- Hydrophone
                             #    0x04 -- Aux
                             #    0x05 -- Geophone-3c Horizontal,
                             # X -- In-line
                             #    0x06 -- Geophone-3c Horizontal,
                             # Y -- Cross-line
                             #    0x07 -- Geophone-3c Vertical, Z
                             #    0x08 -- Reserved
                             #    0x0C -- Accelerometer-3c Horizontal,
                             # X -- In-line
                             #    0x0C -- Accelerometer-3c Horizontal,
                             # Y -- Cross-line
                             #    0x0C -- Accelerometer-3c Vertical, Z
                             # Sensor serial number
                             construct.BitField("SensorSerial", 3),
                             # Sensor version number
                             construct.ULInt8("SensorVersion"),
                             construct.ULInt8("SensorRev"),  # Sensor revision
                             construct.ULInt8("VOR"))  # VOR applied
    #    0 -- No VOR applied
    #    2 -- VOR applied
    return TRACE


class iNova (object):
    __keys__ = ("Revision", "ShotID", "AuxChanSig", "AuxChanID", "SPL", "SPS",
                "unass01", "unass02", "SenInt",
                "VectSens", "HorAz", "VertAngle", "SourceType", "SensorType",
                "AuxChanSetType", "NoiseEditType",
                "NoiseEditGate", "SystemDevice", "FSU", "DevChan",
                "SourceCoCo",
                "DevStatusBits", "BITTest",
                "SweepPhaseRot", "unass03", "BoxFun", "SourceEffortM",
                "SourceEffortE", "SourceUnits", "EventType",
                "SensorTypeID", "SensorSerial", "SensorVersion",
                "SensorRev", "VOR")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in iNova.__keys__:
            self.__dict__[c] = 0x00

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

    def get(self):
        if self.endian == 'big':
            t = inova_header()
        else:
            t = inova_header_le()

        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = inova_header()
        else:
            t = inova_header_le()

        return t.parse(buf)

#
# Place holder for now
#


class Sioseis (Seg):
    def __init__(self, endian='big'):
        LOGGER.info("SioSeis extended header not implemented.")
        Seg.__init__(self, endian)


#
# Mixins
#
pfloat_s = ibmfloat.pfloat()


def build_ieee(x):
    global pfloat_s

    return pfloat_s.build(construct.Container(x=float(x)))


def build_ibm(x):
    global pfloat_s

    return ibmfloat.ieee2ibm32(build_ieee(float(x)))


pint_s = ibmfloat.psint()


def build_int(x):
    global pint_s

    return pint_s.build(construct.Container(x=x))


#
# MAIN
#
if __name__ == '__main__':
    import math
    #
    # Usage example
    #

    # Get an instance of Text
    t = Text()
    # Load d with header values we want to set
    d = {}
    s = 'C SEG Y REV 1' + " " * 67
    val = ebcdic.AsciiToEbcdic(s)
    d['_39_'] = val
    # Now set the instance of this textural header
    t.set(d)
    # Get a binary image of the textural header
    to = t.get()
    # Open and write header
    fh = open("test.sgy", "w")
    fh.write(to)
    # Get an instance of Reel, set and write as above
    d = {}
    r = Reel()
    d['rev'] = 0x0100  # Rev 1.0
    d['extxt'] = 0
    # Write it using SU naming scheme
    d['jobid'] = 99
    r.set(d)
    ro = r.get()
    fh.write(ro)
    # Now do the same thing for Trace
    d = {}
    t = Trace()
    d['lineSeq'] = 0x7D00
    d['deltaSample'] = 0x2710  # 100 sps
    t.set(d)
    to = t.get()
    p = Passcal()
    po = p.get()
    fh.write(to)
    fh.write(po)
    # Now write some ibm floats
    for i in range(3600):
        dval = math.sin(math.radians(i))
        pfloat_s = ibmfloat.pfloat()
        c = construct.Container(x=dval)
        pval = pfloat_s.build(c)
        ival = ibmfloat.ieee2ibm32(pval)
        fh.write(ival)

    fh.close()
    # Write to here
    #
    # Now read the file back
    t = None
    t = Text()
    fh = open("test.sgy")
    # Read and parse the textural header
    container = t.parse(fh.read(3200))  # Read textural header
    # Print field _39_
    print ebcdic.EbcdicToAscii(container._39_)
    print dir(container._39_)

    # Read and parse the reel header
    r = None
    r = Reel()
    container = r.parse(fh.read(400))  # Read reel header
    # See the SEG-Y rev 1 to see how this works ;^)
    dec = container.rev >> 8
    flt = container.rev & 0x0F
    # Read it using PASSCAL naming scheme
    job = container.jobid
    print job
    print "%d.%d" % (dec, flt)

    # Read and parse the trace header
    t = None
    t = Trace()
    container = t.parse(fh.read(180))  # Read common trace header
    #
    print 1.0 / container.deltaSample / 1000000.0
    # Skip over the extended header
    fh.seek(60, 1)
    # Now read and convert the trace
    for i in range(3600):
        v = ibmfloat.ibm2ieee32(fh.read(4))
        v = pfloat_s.parse(v)
        print v.x

    fh.close()

    ex1 = Menlo()
    ex2 = Passcal()
    ex3 = Seg()
    ex4 = iNova()
    ex4.get()
