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
    TEXT = "TEXT" / construct.Struct('_01_' / construct.Bytes(80),
                                     '_02_' / construct.Bytes(80),
                                     '_03_' / construct.Bytes(80),
                                     '_04_' / construct.Bytes(80),
                                     '_05_' / construct.Bytes(80),
                                     '_06_' / construct.Bytes(80),
                                     '_07_' / construct.Bytes(80),
                                     '_08_' / construct.Bytes(80),
                                     '_09_' / construct.Bytes(80),
                                     '_10_' / construct.Bytes(80),
                                     '_11_' / construct.Bytes(80),
                                     '_12_' / construct.Bytes(80),
                                     '_13_' / construct.Bytes(80),
                                     '_14_' / construct.Bytes(80),
                                     '_15_' / construct.Bytes(80),
                                     '_16_' / construct.Bytes(80),
                                     '_17_' / construct.Bytes(80),
                                     '_18_' / construct.Bytes(80),
                                     '_19_' / construct.Bytes(80),
                                     '_20_' / construct.Bytes(80),
                                     '_21_' / construct.Bytes(80),
                                     '_22_' / construct.Bytes(80),
                                     '_23_' / construct.Bytes(80),
                                     '_24_' / construct.Bytes(80),
                                     '_25_' / construct.Bytes(80),
                                     '_26_' / construct.Bytes(80),
                                     '_27_' / construct.Bytes(80),
                                     '_28_' / construct.Bytes(80),
                                     '_29_' / construct.Bytes(80),
                                     '_30_' / construct.Bytes(80),
                                     '_31_' / construct.Bytes(80),
                                     '_32_' / construct.Bytes(80),
                                     '_33_' / construct.Bytes(80),
                                     '_34_' / construct.Bytes(80),
                                     '_35_' / construct.Bytes(80),
                                     '_36_' / construct.Bytes(80),
                                     '_37_' / construct.Bytes(80),
                                     '_38_' / construct.Bytes(80),
                                     '_39_' / construct.Bytes(80),
                                     '_40_' / construct.Bytes(80))
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
                    "Warning: Attempt to set unknown variable "
                    "%s in reel header." % k)

    def get(self):
        t = text_header()
        return t.build(self.__dict__)

    def parse(self, buf):
        t = text_header()
        return t.parse(buf)


# 400 byte reel header
def reel_header():
    REEL = "REEL" / construct.Struct(
                            # Job identification number [3201-3204]
                            "jobid"/ construct.Int32ub,
                            # Line number [3205-3208]
                            "lino" / construct.Int32ub,
                            # Reel number [3209-3212]
                            "reno" / construct.Int32ub,
                            # Traces per ensemble [3213-3214]
                            "ntrpr" / construct.Int16ub,
                            # Aux traces per ensemble [3215-3216]
                            "nart" / construct.Int16ub,
                            # Sample interval us [3217-3218]
                            "hdt" / construct.Int16ub,
                            # Field sample interval [3219-3220]
                            "dto" / construct.Int16ub,
                            # Number of samples per trace [3221-3222]
                            "hns" / construct.Int16ub,
                            # Field samples per trace [3223-3224]
                            "nso" / construct.Int16ub,
                            # Data format, 5 = 4-byte IEEE [3225-3226]
                            "format" / construct.Int16ub,
                            # Ensemble fold [3227-3228]
                            "fold" / construct.Int16ub,
                            # Trace sorting code, 5 == shot gathers [3229-3230]
                            "tsort" / construct.Int16ub,
                            # Vertical sum code [3231-3232]
                            "vscode" / construct.Int16ub,
                            # Starting sweep frequency [3233-3234]
                            "hsfs" / construct.Int16ub,
                            # Ending sweep frequency [3235-3236]
                            "hsfe" / construct.Int16ub,
                            # Sweep length us [3237-3238]
                            "hslen" / construct.Int16ub,
                            # Sweep type code [3239-3240]
                            "hstyp" / construct.Int16ub,
                            # Trace number of sweep channel [3241-3242]
                            "schn" / construct.Int16ub,
                            # Sweep taper length ms at start [3243-3244]
                            "hstas" / construct.Int16ub,
                            # Sweep taper length ms at end [3245-3246]
                            "hstae" / construct.Int16ub,
                            # Taper type [3247-3248]
                            "htatyp" / construct.Int16ub,
                            # Correlated data traces [3249-3250]
                            "hcorr" / construct.Int16ub,
                            # Binary gain recovered [3251-3252]
                            "bgrcv" / construct.Int16ub,
                            # Amplitude recovery method [3253-3254]
                            "rcvm" / construct.Int16ub,
                            # Measurement system [3255-3256]
                            "mfeet" / construct.Int16ub,
                            # Impulse signal polarity [3257-3258]
                            "polyt" / construct.Int16ub,
                            # Vibratory polarity code [3259-3260]
                            "vpol" / construct.Int16ub,
                            # Unassigned [3261-3500]
                            "unass1" / construct.Bytes(240),
                            # SEG-Y Revision number [3501-3503]
                            "rev" / construct.Int16ub,
                            # Fixed length trace flag [3503-3504]
                            "trlen" / construct.Int16ub,
                            # Number of extended text headers [3505-3506]
                            "extxt" / construct.Int16ub,
                            # Unassigned [3507-3600]
                            "unass2" / construct.Bytes(94))
    
    return REEL

# 400 byte reel header (Little Endian)


def reel_header_le():
    REEL = "REEL" / construct.Struct(
                            # Job identification number [3201-3204]
                            "jobid"/ construct.Int32ul,
                            # Line number [3205-3208]
                            "lino" / construct.Int32ul,
                            # Reel number [3209-3212]
                            "reno" / construct.Int32ul,
                            # Traces per ensemble [3213-3214]
                            "ntrpr" / construct.Int16ul,
                            # Aux traces per ensemble [3215-3216]
                            "nart" / construct.Int16ul,
                            # Sample interval us [3217-3218]
                            "hdt" / construct.Int16ul,
                            # Field sample interval [3219-3220]
                            "dto" / construct.Int16ul,
                            # Number of samples per trace [3221-3222]
                            "hns" / construct.Int16ul,
                            # Field samples per trace [3223-3224]
                            "nso" / construct.Int16ul,
                            # Data format, 5 = 4-byte IEEE [3225-3226]
                            "format" / construct.Int16ul,
                            # Ensemble fold [3227-3228]
                            "fold" / construct.Int16ul,
                            # Trace sorting code, 5 == shot gathers [3229-3230]
                            "tsort" / construct.Int16ul,
                            # Vertical sum code [3231-3232]
                            "vscode" / construct.Int16ul,
                            # Starting sweep frequency [3233-3234]
                            "hsfs" / construct.Int16ul,
                            # Ending sweep frequency [3235-3236]
                            "hsfe" / construct.Int16ul,
                            # Sweep length us [3237-3238]
                            "hslen" / construct.Int16ul,
                            # Sweep type code [3239-3240]
                            "hstyp" / construct.Int16ul,
                            # Trace number of sweep channel [3241-3242]
                            "schn" / construct.Int16ul,
                            # Sweep taper length ms at start [3243-3244]
                            "hstas" / construct.Int16ul,
                            # Sweep taper length ms at end [3245-3246]
                            "hstae" / construct.Int16ul,
                            # Taper type [3247-3248]
                            "htatyp" / construct.Int16ul,
                            # Correlated data traces [3249-3250]
                            "hcorr" / construct.Int16ul,
                            # Binary gain recovered [3251-3252]
                            "bgrcv" / construct.Int16ul,
                            # Amplitude recovery method [3253-3254]
                            "rcvm" / construct.Int16ul,
                            # Measurement system [3255-3256]
                            "mfeet" / construct.Int16ul,
                            # Impulse signal polarity [3257-3258]
                            "polyt" / construct.Int16ul,
                            # Vibratory polarity code [3259-3260]
                            "vpol" / construct.Int16ul,
                            # Unassigned [3261-3500]
                            "unass1" / construct.Bytes(240),
                            # SEG-Y Revision number [3501-3503]
                            "rev" / construct.Int16ul,
                            # Fixed length trace flag [3503-3504]
                            "trlen" / construct.Int16ul,
                            # Number of extended text headers [3505-3506]
                            "extxt" / construct.Int16ul,
                            # Unassigned [3507-3600]
                            "unass2" / construct.Bytes(94))
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

        return r.build(self.__dict__)

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
    TRACE = "TRACE" / construct.Struct(
                         # Line trace sequence number [1-4]
                         "lineSeq" / construct.Int32sb,
                         # Reel trace sequence number [5-8]
                         "reelSeq" / construct.Int32sb,
                         # Original field record number [9-12]
                         "field_record_number" / construct.Int32sb,
                         # Trace number within the original field record
                         # [13-16]
                         "channel_number" / construct.Int32sb,
                         # Energy source point number [17-20]
                         "energySourcePt" / construct.Int32sb,
                         # Ensemble number [21-24]
                         "cdpEns" / construct.Int32sb,
                         # Trace number [25-28]
                         "traceInEnsemble" / construct.Int32sb,
                         # Trace ID code [29-30]
                         "traceID" / construct.Int16sb,
                         # Number of vertically summed traces [31-32]
                         "vertSum" / construct.Int16sb,
                         # Number of horizontally summed traces [33-34]
                         "horSum" / construct.Int16sb,
                         # Data use [35-36]
                         "dataUse" / construct.Int16sb,
                         # Offset (distance). Distance from center of the
                         # source point to the center of the receiver group
                         # (negative if opposite to direction in which line
                         # is shot). [37-40]
                         "sourceToRecDist" / construct.Int32sb,
                         # Receiver group elevation [41-44]
                         "recElevation" / construct.Int32sb,
                         # Source elevation [45-48]
                         "sourceSurfaceElevation" / construct.Int32sb,
                         # Source depth [49-52]
                         "sourceDepth" / construct.Int32sb,
                         # Seismic Datum elevation at receiver group
                         # [53-56]
                         "datumElevRec" / construct.Int32sb,
                         # Seismic Datum elevation at source [57-60]
                         "datumElevSource" / construct.Int32sb,
                         # Water depth at source [61-64]
                         "sourceWaterDepth" / construct.Int32sb,
                         # Water depth at group [65-68]
                         "recWaterDepth" / construct.Int32sb,
                         # Elevation and depth scalar [69-70]
                         "elevationScale" / construct.Int16sb,
                         # Coordinate scalar [71-72]
                         "coordScale" / construct.Int16sb,
                         # X coordinate of source [73-76]
                         "sourceLongOrX" / construct.Int32sb,
                         # Y coordinate of source [77-80]
                         "sourceLatOrY" / construct.Int32sb,
                         # X coordinate of receiver group [81-84]
                         "recLongOrX" / construct.Int32sb,
                         # Y coordinate of receiver group [85-88]
                         "recLatOrY" / construct.Int32sb,
                         # Coordinate system [89-90]
                         "coordUnits" / construct.Int16sb,
                         # Weathering velocity [91-92]
                         "weatheringVelocity" / construct.Int16sb,
                         # Sub-weathering velocity [93-94]
                         "subWeatheringVelocity" / construct.Int16sb,
                         # Uphole time at source in ms [95-96]
                         "sourceUpholeTime" / construct.Int16sb,
                         # Uphole time at group in ms [97-98]
                         "recUpholeTime" / construct.Int16sb,
                         # Source static correction in ms [99-100]
                         "sourceStaticCor" / construct.Int16sb,
                         # Group static correction in ms [101-102]
                         "recStaticCor" / construct.Int16sb,
                         # Total static applied in ms [103-104]
                         "totalStatic" / construct.Int16sb,
                         # Lag time A, ms [105-106]
                         "lagTimeA" / construct.Int16sb,
                         # Lag time B, ms [107-108]
                         "lagTimeB" / construct.Int16sb,
                         # Delay recording time, ms [109-110]
                         "delay" / construct.Int16sb,
                         # Mute start time, ms [111-112]
                         "muteStart" / construct.Int16sb,
                         # Mute end time, ms [113-114]
                         "muteEnd" / construct.Int16sb,
                         # Number of samples [115-116]
                         "sampleLength" / construct.Int16ub,
                         # Sample interval, us [117-118]
                         "deltaSample" / construct.Int16sb,
                         # Gain type [119-120]
                         "gainType" / construct.Int16sb,
                         # Gain constant [121-122]
                         "gainConst" / construct.Int16sb,
                         # Early gain [123-124]
                         "initialGain" / construct.Int16sb,
                         # Correlated? [125-126]
                         "correlated" / construct.Int16sb,
                         # Sweep frequency at start [127-128]
                         "sweepStart" / construct.Int16sb,
                         # Sweep frequency at end [129-130]
                         "sweepEnd" / construct.Int16sb,
                         # Sweep length in ms [131-132]
                         "sweepLength" / construct.Int16sb,
                         # Sweep type [133-134]
                         "sweepType" / construct.Int16sb,
                         # Sweep taper at start, ms [135-136]
                         "sweepTaperAtStart" / construct.Int16sb,
                         # Sweep taper at end, ms [137-138]
                         "sweepTaperAtEnd" / construct.Int16sb,
                         # Taper type [139-140]
                         "taperType" / construct.Int16sb,
                         # Alias filter frequency, Hz [141-142]
                         "aliasFreq" / construct.Int16sb,
                         # Alias filter slope, dB/octave [143-144]
                         "aliasSlope" / construct.Int16sb,
                         # Notch filter frequency, Hz [145-146]
                         "notchFreq" / construct.Int16sb,
                         # Notch filter slope, dB/octave [147-148]
                         "notchSlope" / construct.Int16sb,
                         # Low-cut frequency, Hz [149-150]
                         "lowCutFreq" / construct.Int16sb,
                         # High-cut frequency, Hz [151-152]
                         "hiCutFreq" / construct.Int16sb,
                         # Low-cut slope, dB/octave [153-154]
                         "lowCutSlope" / construct.Int16sb,
                         # High-cut slope, dB/octave [155-156]
                         "hiCutSlope" / construct.Int16sb,
                         "year" / construct.Int16sb,  # Year [157-158]
                         "day" / construct.Int16sb,  # Day of Year [159-160]
                         "hour" / construct.Int16sb,  # Hour [161-162]
                         "minute" / construct.Int16sb,  # Minute [163-164]
                         "second" / construct.Int16sb,  # Seconds [165-166]
                         # Time bias code [167-168]
                         "timeBasisCode" / construct.Int16sb,
                         # Trace weighting for LSB [169-170]
                         "traceWeightingFactor" / construct.Int16sb,
                         # Geophone group number [171-172]
                         "phoneRollPos1" / construct.Int16ub,
                         # Geophone group number (field) [173-174]
                         "phoneFirstTrace" / construct.Int16ub,
                         # Geophone group number, last trace (field)
                         # [175-176]
                         "phoneLastTrace" / construct.Int16ub,
                         # Gap size [177-178]
                         "gapSize" / construct.Int16sb,
                         # Over travel associated with taper at beginning
                         # or end of line [179-180]
                         "taperOvertravel" / construct.Int16ub)
    # Over travel
    return TRACE

#
# Common trace header (Little Endian)
#


def trace_header_le():
    TRACE = "TRACE" / construct.Struct(
                         # Line trace sequence number [1-4]
                         "lineSeq" / construct.Int32sl,
                         # Reel trace sequence number [5-8]
                         "reelSeq" / construct.Int32sl,
                         # Original field record number [9-12]
                         "field_record_number" / construct.Int32sl,
                         # Trace number within the original field record
                         # [13-16]
                         "channel_number" / construct.Int32sl,
                         # Energy source point number [17-20]
                         "energySourcePt" / construct.Int32sl,
                         # Ensemble number [21-24]
                         "cdpEns" / construct.Int32sl,
                         # Trace number [25-28]
                         "traceInEnsemble" / construct.Int32sl,
                         # Trace ID code [29-30]
                         "traceID" / construct.Int16sl,
                         # Number of vertically summed traces [31-32]
                         "vertSum" / construct.Int16sl,
                         # Number of horizontally summed traces [33-34]
                         "horSum" / construct.Int16sl,
                         # Data use [35-36]
                         "dataUse" / construct.Int16sl,
                         # Offset (distance). Distance from center of the
                         # source point to the center of the receiver group
                         # (negative if opposite to direction in which line
                         # is shot). [37-40]
                         "sourceToRecDist" / construct.Int32sl,
                         # Receiver group elevation [41-44]
                         "recElevation" / construct.Int32sl,
                         # Source elevation [45-48]
                         "sourceSurfaceElevation" / construct.Int32sl,
                         # Source depth [49-52]
                         "sourceDepth" / construct.Int32sl,
                         # Seismic Datum elevation at receiver group
                         # [53-56]
                         "datumElevRec" / construct.Int32sl,
                         # Seismic Datum elevation at source [57-60]
                         "datumElevSource" / construct.Int32sl,
                         # Water depth at source [61-64]
                         "sourceWaterDepth" / construct.Int32sl,
                         # Water depth at group [65-68]
                         "recWaterDepth" / construct.Int32sl,
                         # Elevation and depth scalar [69-70]
                         "elevationScale" / construct.Int16sl,
                         # Coordinate scalar [71-72]
                         "coordScale" / construct.Int16sl,
                         # X coordinate of source [73-76]
                         "sourceLongOrX" / construct.Int32sl,
                         # Y coordinate of source [77-80]
                         "sourceLatOrY" / construct.Int32sl,
                         # X coordinate of receiver group [81-84]
                         "recLongOrX" / construct.Int32sl,
                         # Y coordinate of receiver group [85-88]
                         "recLatOrY" / construct.Int32sl,
                         # Coordinate system [89-90]
                         "coordUnits" / construct.Int16sl,
                         # Weathering velocity [91-92]
                         "weatheringVelocity" / construct.Int16sl,
                         # Sub-weathering velocity [93-94]
                         "subWeatheringVelocity" / construct.Int16sl,
                         # Uphole time at source in ms [95-96]
                         "sourceUpholeTime" / construct.Int16sl,
                         # Uphole time at group in ms [97-98]
                         "recUpholeTime" / construct.Int16sl,
                         # Source static correction in ms [99-100]
                         "sourceStaticCor" / construct.Int16sl,
                         # Group static correction in ms [101-102]
                         "recStaticCor" / construct.Int16sl,
                         # Total static applied in ms [103-104]
                         "totalStatic" / construct.Int16sl,
                         # Lag time A, ms [105-106]
                         "lagTimeA" / construct.Int16sl,
                         # Lag time B, ms [107-108]
                         "lagTimeB" / construct.Int16sl,
                         # Delay recording time, ms [109-110]
                         "delay" / construct.Int16sl,
                         # Mute start time, ms [111-112]
                         "muteStart" / construct.Int16sl,
                         # Mute end time, ms [113-114]
                         "muteEnd" / construct.Int16sl,
                         # Number of samples [115-116]
                         "sampleLength" / construct.Int16ul,
                         # Sample interval, us [117-118]
                         "deltaSample" / construct.Int16sl,
                         # Gain type [119-120]
                         "gainType" / construct.Int16sl,
                         # Gain constant [121-122]
                         "gainConst" / construct.Int16sl,
                         # Early gain [123-124]
                         "initialGain" / construct.Int16sl,
                         # Correlated? [125-126]
                         "correlated" / construct.Int16sl,
                         # Sweep frequency at start [127-128]
                         "sweepStart" / construct.Int16sl,
                         # Sweep frequency at end [129-130]
                         "sweepEnd" / construct.Int16sl,
                         # Sweep length in ms [131-132]
                         "sweepLength" / construct.Int16sl,
                         # Sweep type [133-134]
                         "sweepType" / construct.Int16sl,
                         # Sweep taper at start, ms [135-136]
                         "sweepTaperAtStart" / construct.Int16sl,
                         # Sweep taper at end, ms [137-138]
                         "sweepTaperAtEnd" / construct.Int16sl,
                         # Taper type [139-140]
                         "taperType" / construct.Int16sl,
                         # Alias filter frequency, Hz [141-142]
                         "aliasFreq" / construct.Int16sl,
                         # Alias filter slope, dB/octave [143-144]
                         "aliasSlope" / construct.Int16sl,
                         # Notch filter frequency, Hz [145-146]
                         "notchFreq" / construct.Int16sl,
                         # Notch filter slope, dB/octave [147-148]
                         "notchSlope" / construct.Int16sl,
                         # Low-cut frequency, Hz [149-150]
                         "lowCutFreq" / construct.Int16sl,
                         # High-cut frequency, Hz [151-152]
                         "hiCutFreq" / construct.Int16sl,
                         # Low-cut slope, dB/octave [153-154]
                         "lowCutSlope" / construct.Int16sl,
                         # High-cut slope, dB/octave [155-156]
                         "hiCutSlope" / construct.Int16sl,
                         "year" / construct.Int16sl,  # Year [157-158]
                         "day" / construct.Int16sl,  # Day of Year [159-160]
                         "hour" / construct.Int16sl,  # Hour [161-162]
                         "minute" / construct.Int16sl,  # Minute [163-164]
                         "second" / construct.Int16sl,  # Seconds [165-166]
                         # Time bias code [167-168]
                         "timeBasisCode" / construct.Int16sl,
                         # Trace weighting for Lsl [169-170]
                         "traceWeightingFactor" / construct.Int16sl,
                         # Geophone group number [171-172]
                         "phoneRollPos1" / construct.Int16ul,
                         # Geophone group number (field) [173-174]
                         "phoneFirstTrace" / construct.Int16ul,
                         # Geophone group number, last trace (field)
                         # [175-176]
                         "phoneLastTrace" / construct.Int16ul,
                         # Gap size [177-178]
                         "gapSize" / construct.Int16sl,
                         # Over travel associated with taper at beginning
                         # or end of line [179-180]
                         "taperOvertravel" / construct.Int16ul)
    # Over travel
    return TRACE


class Trace (object):
    __keys__ = ("lineSeq", "reelSeq", "field_record_number", "channel_number",
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
    TRACE = "TRACE" / construct.Struct(
                        "station_name" / construct.Bytes(6),
                        "sensor_serial" / construct.Bytes(8),
                        "channel_name" / construct.Bytes(4),
                        "totalStaticHi" / construct.Int16sb,
                        "samp_rate" / construct.Int32sb,
                        "data_form" / construct.Int16sb,
                        "m_secs" / construct.Int16sb,
                        "trigyear" / construct.Int16sb,
                        "trigday" / construct.Int16sb,
                        "trighour" / construct.Int16sb,
                        "trigminute" / construct.Int16sb,
                        "trigsecond" / construct.Int16sb,
                        "trigmills" / construct.Int16sb,
                        "scale_fac" / construct.Float32b,
                        "inst_no" / construct.Int16ub,
                        "unassigned" / construct.Int16sb,
                        "num_samps" / construct.Int32sb,
                        "max" / construct.Int32sb,
                        "min" / construct.Int32sb
                        )
    return TRACE

#
# PASSCAL extended header (Little Endian)
#


def passcal_header_le():
    TRACE = "TRACE" / construct.Struct(
                        "station_name" / construct.Bytes(6),
                        "sensor_serial" / construct.Bytes(8),
                        "channel_name" / construct.Bytes(4),
                        "totalStaticHi" / construct.Int16sl,
                        "samp_rate" / construct.Int32sl,
                        "data_form" / construct.Int16sl,
                        "m_secs" / construct.Int16sl,
                        "trigyear" / construct.Int16sl,
                        "trigday" / construct.Int16sl,
                        "trighour" / construct.Int16sl,
                        "trigminute" / construct.Int16sl,
                        "trigsecond" / construct.Int16sl,
                        "trigmills" / construct.Int16sl,
                        "scale_fac" / construct.Float32l,
                        "inst_no" / construct.Int16ul,
                        "unassigned" / construct.Int16sl,
                        "num_samps" / construct.Int32sl,
                        "max" / construct.Int32sl,
                        "min" / construct.Int32sl
                        )
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
    TRACE = "TRACE" / construct.Struct(
                        # Microsec trace start time
                        "start_usec" / construct.Int32sb(),
                        # Charge size (kg)
                        "shot_size" / construct.Int16sb(),
                        # Shot/trigger time - year
                        "shot_year" / construct.Int16sb(),
                        # Shot/trigger time - Julian day
                        "shot_doy" / construct.Int16sb(),
                        # Shot/trigger time - hour
                        "shot_hour" / construct.Int16sb(),
                        # Shot/trigger time - minute
                        "shot_minute" / construct.Int16sb(),
                        # Shot/trigger time - second
                        "shot_second" / construct.Int16sb(),
                        # Shot/trigger time - microsec
                        "shot_us" / construct.Int32sb(),
                        # Override for sample interval (SET = 0)
                        "si_override" / construct.Int32sb(),
                        # Azimuth of sensor orient axis (empty)
                        "sensor_azimuth" / construct.Int16sb,
                        # Geophone inclination (empty)
                        "sensor_inclination" / construct.Int16sb,
                        # LMO static (x/v)  (ms) (empty)
                        "lmo_ms" / construct.Int32sb,
                        # LMO flag: (0=Y, 1=N) (SET = 1)
                        "lmo_flag" / construct.Int16sb,
                        # 13 = rt-130, 16 = texan
                        "inst_type" / construct.Int16sb,
                        "correction" / construct.Int16sb,
                        # Azimuth of source-receiver (min of arc)
                        "azimuth" / construct.Int16sb,
                        # 1--L28 (PASSCAL)(4.5 Hz)
                         # 2--L22 (2 Hz)
                         # 3--L10B (8 Hz)
                         # 4--L4 1 Hz
                         # 5--L4 2 Hz
                         # 6--FBA
                         # 7--TDC-10 (4.5 Hz)
                         # 8--L28 (GSC)
                         # 9--LRS1033 (4.5 HZ)
                         # 99--unknown
                         # Geophone number (empty)
                        "sensor_sn" / construct.Int16sb,
                        # Inst. ID number
                        "das_sn" / construct.Int16ub,
                        "empty1" / construct.Int16ub,
                        # Number of samples if > 2^15 (see 115-116)
                        "samples" / construct.Int32sb,
                        "empty2" / construct.Int32ub,
                        # Receiver clock drift removed
                        "clock_drift" / construct.Int16sb,
                        "empty3" / construct.Int16ub,
                        )
    return TRACE

#
# Menlo Park USGS extended header (Little Endian)
#


def menlo_header_le():
    TRACE = "TRACE" / construct.Struct(
                        # Microsec trace start time
                        "start_usec" / construct.Int32sl(),
                        # Charge size (kg)
                        "shot_size" / construct.Int16sl(),
                        # Shot/trigger time - year
                        "shot_year" / construct.Int16sl(),
                        # Shot/trigger time - Julian day
                        "shot_doy" / construct.Int16sl(),
                        # Shot/trigger time - hour
                        "shot_hour" / construct.Int16sl(),
                        # Shot/trigger time - minute
                        "shot_minute" / construct.Int16sl(),
                        # Shot/trigger time - second
                        "shot_second" / construct.Int16sl(),
                        # Shot/trigger time - microsec
                        "shot_us" / construct.Int32sl(),
                        # Override for sample interval (SET = 0)
                        "si_override" / construct.Int32sl(),
                        # Azimuth of sensor orient axis (empty)
                        "sensor_azimuth" / construct.Int16sl,
                        # Geophone inclination (empty)
                        "sensor_inclination" / construct.Int16sl,
                        # LMO static (x/v)  (ms) (empty)
                        "lmo_ms" / construct.Int32sl,
                        # LMO flag: (0=Y, 1=N) (SET = 1)
                        "lmo_flag" / construct.Int16sl,
                        # 13 = rt-130, 16 = texan
                        "inst_type" / construct.Int16sl,
                        "correction" / construct.Int16sl,
                        # Azimuth of source-receiver (min of arc)
                        "azimuth" / construct.Int16sl,
                        # 1--L28 (PASSCAL)(4.5 Hz)
                         # 2--L22 (2 Hz)
                         # 3--L10B (8 Hz)
                         # 4--L4 1 Hz
                         # 5--L4 2 Hz
                         # 6--FBA
                         # 7--TDC-10 (4.5 Hz)
                         # 8--L28 (GSC)
                         # 9--LRS1033 (4.5 HZ)
                         # 99--unknown
                         # Geophone number (empty)
                        "sensor_sn" / construct.Int16sl,
                        # Inst. ID number
                        "das_sn" / construct.Int16ul,
                        "empty1" / construct.Int16ul,
                        # Number of samples if > 2^15 (see 115-116)
                        "samples" / construct.Int32sl,
                        "empty2" / construct.Int32ul,
                        # Receiver clock drift removed
                        "clock_drift" / construct.Int16sl,
                        "empty3" / construct.Int16ul,
                        )

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
    TRACE = "TRACE" / construct.Struct(
                        # X coordinate of ensemble
                        "Xcoor" / construct.Int32sb,
                        # Y coordinate of ensemble
                        "Ycoor" / construct.Int32sb,
                        # Same as lino in reel header
                        "Inn" / construct.Int32sb,
                        # Same as cdp
                        "Cnn" / construct.Int32sb,
                        # Shot point number
                        "Spn" / construct.Int32sb,
                        # Scaler to apply to Spn
                        "Scal" / construct.Int16sb,
                        # Trace value measurement units
                        "Tvmu" / construct.Int16sb,
                        # Transduction constant mantissa
                        "Tucmant" / construct.Int32sb,
                        # Transduction constant exponent
                        "Tucexp" / construct.Int16sb,
                        # Transduction units
                        "Tdu" / construct.Int16sb,
                        # Device/Trace identifier
                        "Dti" / construct.Int16sb,
                        # Time scalar
                        "Tscaler" / construct.Int16sb,
                        # Source Type/Orientation
                        "Sto" / construct.Int16sb,
                        # Source Energy direction
                        "Sed" / construct.Bytes(6),
                          # Source measurement mantissa
                        "Smsmant" / construct.Int32sb,
                        # Source measurement exponent
                        "Smsexp" / construct.Int16sb,
                        # Source measurement Units
                        "Smu" / construct.Int16sb,
                        # Last 8 bytes undefined in rev1
                        # Trace start time usec
                        "start_usec" / construct.Int32ub,
                        # Shot time usec
                        "shot_us" / construct.Int32ub
                        )
    return TRACE

#
# SEG-Y Rev 1.0 extended header (Little Endian)
#


def seg_header_le():
    TRACE = "TRACE" / construct.Struct(
                        # X coordinate of ensemble
                        "Xcoor" / construct.Int32sl,
                        # Y coordinate of ensemble
                        "Ycoor" / construct.Int32sl,
                        # Same as lino in reel header
                        "Inn" / construct.Int32sl,
                        # Same as cdp
                        "Cnn" / construct.Int32sl,
                        # Shot point number
                        "Spn" / construct.Int32sl,
                        # Scaler to apply to Spn
                        "Scal" / construct.Int16sl,
                        # Trace value measurement units
                        "Tvmu" / construct.Int16sl,
                        # Transduction constant mantissa
                        "Tucmant" / construct.Int32sl,
                        # Transduction constant exponent
                        "Tucexp" / construct.Int16sl,
                        # Transduction units
                        "Tdu" / construct.Int16sl,
                        # Device/Trace identifier
                        "Dti" / construct.Int16sl,
                        # Time scalar
                        "Tscaler" / construct.Int16sl,
                        # Source Type/Orientation
                        "Sto" / construct.Int16sl,
                        # Source Energy direction
                        "Sed" / construct.Bytes(6),
                          # Source measurement mantissa
                        "Smsmant" / construct.Int32sl,
                        # Source measurement exponent
                        "Smsexp" / construct.Int16sl,
                        # Source measurement Units
                        "Smu" / construct.Int16sl,
                        # Last 8 bytes undefined in rev1
                        # Trace start time usec
                        "start_usec" / construct.Int32ul,
                        # Shot time usec
                        "shot_us" / construct.Int32ul
                        )
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
                            "Revision" / construct.Int16ub,
                            # Derived from POSIX time of shot
                            "ShotID" / construct.Int32ub,
                            # Aux channel description
                            "AuxChanSig" / construct.Int8ub,
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
                            "AuxChanID" / construct.Int8ub,  # Aux Channel ID
                            # Shot Point Line in hundredths
                            "SPL" / construct.Int32ub,
                            # Shot Point Station in hundredths
                            "SPS" / construct.Int32ub,
                            "unass01" / construct.Int16ub,  # Unassigned
                            "unass02" / construct.Int16ub,  # Unassigned
                            # Sensor Interface Unit Type
                            "SenInt" / construct.Int8ub,
                            #    18 -- VSM
                            #    21 -- Vectorseis
                            #    42 -- Geophone Digitizer Unit
                            #    49 -- iNova Standard Analog Channel GDC
                            # Vectorseis sensitivity
                            "VectSens" / construct.Int8ub,
                            #    0 = 40nG
                            #    3 = 160nG
                            # Absolute horizontal orientation azimuth of
                            # Vectorseis in
                            "HorAz" / construct.Int16ub,
                            # 0.0001 radians, measured from due-North
                            # Absolute vertical orientation angle, in 0.0001
                            # radians.
                            "VertAngle" / construct.Int16ub,
                            # A vertically planted sensor will
                            # have a value of
                            # 1416 (Pi * 10,000),
                            # while a horizontally planted sensor will have a
                            # value of 15708 (Pi/2 * 10,000)
                            "SourceType" / construct.Int8ub,  # Source type:
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
                            "SensorType" / construct.Int8ub,  # Sensor type:
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
                            "AuxChanSetType" / construct.Int8ub,
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
                            "NoiseEditType" / construct.Int8ub,
                            #    0 -- Raw Data, Vertical Stack
                            #    2 -- Diversity Stack
                            # Noise Edit Gate Size:
                            "NoiseEditGate" / construct.Int8ub,
                            #    0 -- Raw Data, Vertical Stack
                            #    n -- Number of Samples in Gate,
                            # Diversity Stack
                            # System Device type:
                            "SystemDevice" / construct.Int8ub,
                            #    7 -- MRX
                            #    9 -- RSR
                            #    17 -- VRSR
                            #    20 -- VRSR2
                            #    23 -- AuxUNIT-1C
                            #    25 -- DUNIT-3C
                            #    29 -- Analog-1C
                            #    37 -- FireFly
                            #    48 -- Node
                            "FSU" / construct.BitField(3),  # FSU Serial Number
                            # Device Channel Number
                            "DevChan" / construct.Int8ub,
                            # Source coordinate confidence indicator. Rates
                            # the level
                            "SourceCoCo" / construct.Int8ub,
                            # of confidence in the accuracy of source x,y,z.
                            # 0 -- Good
                            # Device status bits
                            "DevStatusBits" / construct.Int8ub,
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
                            "BITTest" / construct.Int8ub,
                            # Sweep Phase Rotation; 0 if undefined
                            "SweepPhaseRot" / construct.Int16ub,
                            "unass03" / construct.Int8ub,  # Unassigned
                            "BoxFun" / construct.Int8ub,  # Box function
                            # Source effort used to generate the trace
                            # (mantissa)
                            "SourceEffortM" / construct.Int32ub,
                            # Source effort, (exponent)
                            "SourceEffortE" / construct.Int16ub,
                            # Source measurement units
                            "SourceUnits" / construct.Int16ub,
                            #    -1 -- Other
                            #    0 -- Unknown
                            #    1 -- Joule
                            #    2 -- Kilowatt
                            #    3 -- Pascal
                            #    4 -- Bar
                            #    5 -- Bar-meter
                            #    6 -- Kilograms
                            #    7 -- Pounds
                            "EventType" / construct.Int8ub,  # Event type:
                            #    0x00 -- Zeroed or truncated trace
                            #    0x40 -- BIT data - Raw Trace
                            #    0x80 -- Seis data - Normal, Raw
                            #    0x88 -- Seis data - Normal, Stack
                            #    0x90 -- Seis data - Normal, Correlated
                            #    0xA0 -- Seis data - Test, Raw
                            #    0xA8 -- Seis data - Test, Stack
                            #    0xB0 -- Seis data - Test, Correlated
                            # Sensor type ID
                            "SensorTypeID" / construct.Int8ub,
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
                            "SensorSerial" / construct.BitField(3),
                            # Sensor version number
                            "SensorVersion" / construct.Int8ub,
                            # Sensor revision
                            "SensorRev" / construct.Int8ub,
                            # VOR applied
                            #    0 -- No VOR applied
                            #    2 -- VOR applied
                            "VOR" / construct.Int8ub)
    return TRACE
#
# iNova FireFly extened header version 3.0 (Little endian)
#


def inova_header_le():
    TRACE = construct.Struct("TRACE",
                            # iNova revision (322)
                            "Revision" / construct.Int16ub,
                            # Derived from POSIX time of shot
                            "ShotID" / construct.Int32ub,
                            # Aux channel description
                            "AuxChanSig" / construct.Int8ub,
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
                            "AuxChanID" / construct.Int8ub,  # Aux Channel ID
                            # Shot Point Line in hundredths
                            "SPL" / construct.Int32ub,
                            # Shot Point Station in hundredths
                            "SPS" / construct.Int32ub,
                            "unass01" / construct.Int16ub,  # Unassigned
                            "unass02" / construct.Int16ub,  # Unassigned
                            # Sensor Interface Unit Type
                            "SenInt" / construct.Int8ub,
                            #    18 -- VSM
                            #    21 -- Vectorseis
                            #    42 -- Geophone Digitizer Unit
                            #    49 -- iNova Standard Analog Channel GDC
                            # Vectorseis sensitivity
                            "VectSens" / construct.Int8ub,
                            #    0 = 40nG
                            #    3 = 160nG
                            # Absolute horizontal orientation azimuth of
                            # Vectorseis in
                            "HorAz" / construct.Int16ub,
                            # 0.0001 radians, measured from due-North
                            # Absolute vertical orientation angle, in 0.0001
                            # radians.
                            "VertAngle" / construct.Int16ub,
                            # A vertically planted sensor will
                            # have a value of
                            # 1416 (Pi * 10,000),
                            # while a horizontally planted sensor will have a
                            # value of 15708 (Pi/2 * 10,000)
                            "SourceType" / construct.Int8ub,  # Source type:
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
                            "SensorType" / construct.Int8ub,  # Sensor type:
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
                            "AuxChanSetType" / construct.Int8ub,
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
                            "NoiseEditType" / construct.Int8ub,
                            #    0 -- Raw Data, Vertical Stack
                            #    2 -- Diversity Stack
                            # Noise Edit Gate Size:
                            "NoiseEditGate" / construct.Int8ub,
                            #    0 -- Raw Data, Vertical Stack
                            #    n -- Number of Samples in Gate,
                            # Diversity Stack
                            # System Device type:
                            "SystemDevice" / construct.Int8ub,
                            #    7 -- MRX
                            #    9 -- RSR
                            #    17 -- VRSR
                            #    20 -- VRSR2
                            #    23 -- AuxUNIT-1C
                            #    25 -- DUNIT-3C
                            #    29 -- Analog-1C
                            #    37 -- FireFly
                            #    48 -- Node
                            "FSU" / construct.BitField(3),  # FSU Serial Number
                            # Device Channel Number
                            "DevChan" / construct.Int8ub,
                            # Source coordinate confidence indicator. Rates
                            # the level
                            "SourceCoCo" / construct.Int8ub,
                            # of confidence in the accuracy of source x,y,z.
                            # 0 -- Good
                            # Device status bits
                            "DevStatusBits" / construct.Int8ub,
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
                            "BITTest" / construct.Int8ub,
                            # Sweep Phase Rotation; 0 if undefined
                            "SweepPhaseRot" / construct.Int16ub,
                            "unass03" / construct.Int8ub,  # Unassigned
                            "BoxFun" / construct.Int8ub,  # Box function
                            # Source effort used to generate the trace
                            # (mantissa)
                            "SourceEffortM" / construct.Int32ub,
                            # Source effort, (exponent)
                            "SourceEffortE" / construct.Int16ub,
                            # Source measurement units
                            "SourceUnits" / construct.Int16ub,
                            #    -1 -- Other
                            #    0 -- Unknown
                            #    1 -- Joule
                            #    2 -- Kilowatt
                            #    3 -- Pascal
                            #    4 -- Bar
                            #    5 -- Bar-meter
                            #    6 -- Kilograms
                            #    7 -- Pounds
                            "EventType" / construct.Int8ub,  # Event type:
                            #    0x00 -- Zeroed or truncated trace
                            #    0x40 -- BIT data - Raw Trace
                            #    0x80 -- Seis data - Normal, Raw
                            #    0x88 -- Seis data - Normal, Stack
                            #    0x90 -- Seis data - Normal, Correlated
                            #    0xA0 -- Seis data - Test, Raw
                            #    0xA8 -- Seis data - Test, Stack
                            #    0xB0 -- Seis data - Test, Correlated
                            # Sensor type ID
                            "SensorTypeID" / construct.Int8ub,
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
                            "SensorSerial" / construct.BitField(3),
                            # Sensor version number
                            "SensorVersion" / construct.Int8ub,
                            # Sensor revision
                            "SensorRev" / construct.Int8ub,
                            # VOR applied
                            #    0 -- No VOR applied
                            #    2 -- VOR applied
                            "VOR" / construct.Int8ub)
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
