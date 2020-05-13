#!/usr/bin/env pnpython3

#
# Simple program to read and display SEG-Y file
#
# Steve Azevedo
#

import argparse
import logging
import os
from ph5.core import segy_h, ibmfloat, ebcdic
import construct

PROG_VERSION = '2019.14'
LOGGER = logging.getLogger(__name__)

SAMPLE_LENGTH = {1: 4, 2: 4, 3: 2, 4: 4, 5: 4, 8: 1}

SIZEOF = {"lineSeq": 32, "reelSeq": 32, "event_number": 32,
          "channel_number": 32, "energySourcePt": 32, "cdpEns": 32,
          "traceInEnsemble": 32,
          "traceID": 16, "vertSum": 16, "horSum": 16, "dataUse": 16,
          "sourceToRecDist": 32, "recElevation": 32,
          "sourceSurfaceElevation": 32,
          "sourceDepth": 32, "datumElevRec": 32, "datumElevSource": 32,
          "sourceWaterDepth": 32, "recWaterDepth": 32, "elevationScale": 16,
          "coordScale": 16, "sourceLongOrX": 32, "sourceLatOrY": 32,
          "recLongOrX": 32, "recLatOrY": 32, "coordUnits": 16,
          "weatheringVelocity": 16,
          "subWeatheringVelocity": 16, "sourceUpholeTime": 16,
          "recUpholeTime": 16, "sourceStaticCor": 16, "recStaticCor": 16,
          "totalStatic": 16,
          "lagTimeA": 16, "lagTimeB": 16, "delay": 16, "muteStart": 16,
          "muteEnd": 16, "sampleLength": 16, "deltaSample": 16, "gainType": 16,
          "gainConst": 16, "initialGain": 16, "correlated": 16,
          "sweepStart": 16, "sweepEnd": 16, "sweepLength": 16, "sweepType": 16,
          "sweepTaperAtStart": 16, "sweepTaperAtEnd": 16, "taperType": 16,
          "aliasFreq": 16, "aliasSlope": 16, "notchFreq": 16, "notchSlope": 16,
          "lowCutFreq": 16, "hiCutFreq": 16, "lowCutSlope": 16,
          "hiCutSlope": 16, "year": 16, "day": 16, "hour": 16, "minute": 16,
          "second": 16,
          "timeBasisCode": 16, "traceWeightingFactor": 16, "phoneRollPos1": 16,
          "phoneFirstTrace": 16, "phoneLastTrace": 16, "gapSize": 16,
          "taperOvertravel": 16, "station_name": 48, "sensor_serial": 64,
          "channel_name": 16, "totalStaticHi": 16, "samp_rate": 32,
          "data_form": 16,
          "m_secs": 16, "trigyear": 16, "trigday": 16, "trighour": 16,
          "trigminute": 16, "trigsecond": 16, "trigmills": 16, "scale_fac": 32,
          "inst_no": 16, "unassigned": 16, "num_samps": 32, "max": 32,
          "min": 32, "start_usec": 32, "shot_size": 16, "shot_year": 16,
          "shot_doy": 16,
          "shot_hour": 16, "shot_minute": 16, "shot_second": 16, "shot_us": 32,
          "si_override": 32, "sensor_azimuth": 16, "sensor_inclination": 16,
          "lmo_ms": 32, "lmo_flag": 16, "inst_type": 16, "correction": 16,
          "azimuth": 16, "sensor_type": 16, "sensor_sn": 16, "das_sn": 16,
          "empty1": 16,
          "samples": 32, "empty2": 32, "clock_drift": 16, "empty3": 16,
          "waterDelay": 32, "startMute": 32, "endMute": 32, "sampleInt": 32,
          "waterBottomTime": 32, "endOfRp": 32, "dummy1": 32, "dummy2": 32,
          "dummy3": 32, "dummy4": 32, "dummy5": 32, "dummy6": 32, "dummy7": 32,
          "dummy8": 32, "dummy9": 32, "Xcoor": 32, "Ycoor": 32, "Inn": 32,
          "Cnn": 32, "Spn": 32, "Scal": 16, "Tvmu": 16, "Tucmant": 32,
          "Tucexp": 16,
          "Tdu": 16, "Dti": 16, "Tscaler": 16, "Sto": 16, "Sed": 48,
          "Smsmant": 32, "Smsexp": 16, "Smu": 16, "num_samps": 32,
          "samp_rate": 32, "Revision": 16,
          "ShotID": 32, "AuxChanSig": 8, "AuxChanID": 8, "SPL": 32, "SPS": 32,
          "unass01": 16, "unass02": 16, "SenInt": 8, "VectSens": 8,
          "HorAz": 16,
          "VertAngle": 16,
          "SourceType": 8, "SensorType": 8, "AuxChanSetType": 8,
          "NoiseEditType": 8, "NoiseEditGate": 16, "SystemDevice": 8, "FSU": 3,
          "DevChan": 8, "SourceCoCo": 8,
          "DevStatusBits": 8, "BITTest": 8, "SweepPhaseRot": 16, "unass03": 8,
          "BoxFun": 8, "SourceEffortM": 32, "SourceEffortE": 16,
          "SourceUnits": 16,
          "EventType": 8, "SensorTypeID": 8, "SensorSerial": 3,
          "SensorVersion": 8, "SensorRev": 8, "VOR": 8, }


def get_args():
    global FH, TYPE, PRINT, L, T, F, ENDIAN, EBCDIC

    FH = None
    TYPE = None
    PRINT = False
    L = None
    T = None
    F = None

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = "Version: {0} Usage: dumpsgy [options]".format(
        PROG_VERSION)

    parser.add_argument("-f", action="store", dest="infile", type=str,
                        required=True)

    parser.add_argument("-t", action="store", dest="ttype",
                        choices=['U', 'P', 'S', 'N', 'I'],
                        help=("Extended trace header style. U => USGS Menlo, "
                              "P => PASSCAL, S => SEG, I => SIOSEIS, "
                              "N => iNova FireFly"), default='S')

    parser.add_argument("-p", action="store_true",
                        dest="print_true", default=False)

    parser.add_argument("-L", action="store",
                        dest="bytes_per_trace", type=int)

    parser.add_argument("-T", action="store",
                        dest="traces_per_ensemble", type=int)

    parser.add_argument("-F", action="store", dest="trace_format", type=int,
                        help=("1 = IBM - 4 bytes, 2 = INT - 4 bytes, "
                              "3 = INT - 2 bytes, 5 = IEEE - 4 bytes, "
                              "8 = INT - 1 byte"))

    parser.add_argument("-e", action="store", dest="endian",
                        type=str, default='big',
                        help="Endianess: 'big' or 'little'. Default = 'big'")

    parser.add_argument("-i", action="store_false", dest="ebcdic",
                        default=True, help="EBCDIC textural header.")

    args = parser.parse_args()

    FH = open(args.infile, 'rb')
    TYPE = args.ttype
    PRINT = args.print_true
    L = args.bytes_per_trace
    T = args.traces_per_ensemble
    F = args.trace_format
    ENDIAN = args.endian
    EBCDIC = args.ebcdic


def read_text_header():
    buf = FH.read(3200)
    t = segy_h.Text()

    return t.parse(buf)


def last_extended_header(container):
    '''   Return True if this contains an EndText stanza?   '''
    import re
    lastRE = re.compile(r".*\(\(.*SEG\:.*[Ee][Nn][Dd][Tt][Ee][Xx][Tt].*\)\).*")
    keys = segy_h.Text().__keys__
    for k in keys:
        what = "container.{0}".format(k)
        if EBCDIC:
            t = ebcdic.EbcdicToAscii(eval(what))
        else:
            t = eval(what)

        if lastRE.match(t):
            return True

    return False


def print_text_header(container):
    global TYPE
    keys = segy_h.Text().__keys__
    print "--------------- Textural Header ---------------"
    for k in keys:
        what = "container.{0}".format(k)
        if EBCDIC:
            print "{0}\t-\t{1:s}".format(k, ebcdic.EbcdicToAscii(eval(what)))
        else:
            print "{0}\t-\t{1:s}".format(k, eval(what))

        if TYPE is None:
            if k == '_38_':
                try:
                    if EBCDIC:
                        s = ebcdic.EbcdicToAscii(eval(what))
                    else:
                        s = eval(what)

                    try:
                        flds = s.split()
                        if flds[1] == 'MENLO':
                            TYPE = 'U'
                        elif flds[1] == 'PASSCAL':
                            TYPE = 'P'
                        elif flds[1] == 'SEG':
                            TYPE = 'S'
                        elif flds[1] == 'SIOSEIS':
                            TYPE = 'I'
                        else:
                            TYPE = 'S'
                    except BaseException:
                        pass
                except BaseException:
                    TYPE = 'P'


def read_binary_header():
    buf = FH.read(400)
    b = segy_h.Reel(ENDIAN)

    ret = None
    try:
        ret = b.parse(buf)
    except Exception as e:
        LOGGER.error(e)

    return ret


def print_binary_header(container):
    if not container:
        return
    keys = segy_h.Reel().__keys__
    print "---------- Binary Header ----------"
    for k in keys:
        what = "container.{0}".format(k)
        print "{0:<20}\t---\t{1}".format(k, eval(what))


def read_trace_header():
    buf = FH.read(180)
    t = segy_h.Trace(ENDIAN)

    return t.parse(buf)


def print_trace_header(container):
    keys = segy_h.Trace().__keys__
    tt = 0
    print "---------- Trace Header ----------"
    for k in keys:
        what = "container.{0}".format(k)
        try:
            if tt == 9999:
                raise
            s = SIZEOF[k] / 8
            foffset = "{0:<3} - {1:>3}".format(tt, tt + s - 1)
            tt += s
        except BaseException:
            tt = 9999
            foffset = "{0:<3} - {1:>3}".format('_', '_')

        print "{2} {0:<20}\t---\t{1}".format(k, eval(what), foffset)


def read_extended_header():
    buf = FH.read(60)

    if TYPE == 'U':
        e = segy_h.Menlo(ENDIAN)
    elif TYPE == 'S':
        e = segy_h.Seg(ENDIAN)
    elif TYPE == 'P':
        e = segy_h.Passcal(ENDIAN)
    elif TYPE == 'I':
        e = segy_h.Sioseis(ENDIAN)
    elif TYPE == 'N':
        e = segy_h.iNova(ENDIAN)
    else:
        return None

    return e.parse(buf)


def print_extended_header(container):
    if TYPE == 'U':
        keys = segy_h.Menlo().__keys__
    elif TYPE == 'S':
        keys = segy_h.Seg().__keys__
    elif TYPE == 'P':
        keys = segy_h.Passcal().__keys__
    elif TYPE == 'I':
        keys = segy_h.Sioseis().__keys__
    elif TYPE == 'N':
        keys = segy_h.iNova().__keys__
    else:
        return None

    tt = 180
    print "---------- Extended Header ----------"
    for k in keys:
        what = "container.{0}".format(k)

        try:
            if tt == 9999:
                raise
            s = SIZEOF[k] / 8
            if s < 1:
                raise
            foffset = "{0:<3} - {1:>3}".format(tt, tt + s - 1)
            tt += s
        except BaseException:
            tt = 9999
            foffset = "{0:<3} - {1:>3}".format('_', '_')

        print "{2} {0:<20}\t---\t{1}".format(k, eval(what), foffset)


def read_trace(n, length, f=5):
    ret = []
    if PRINT is True:
        for i in range(n):
            buf = FH.read(length)
            # IBM floats - 4 byte - Must be big endian
            if f == 1:
                ret.append(construct.BFloat32(
                    "x").parse(ibmfloat.ibm2ieee32(buf)))
            # INT - 4 byte or 2 byte
            elif f == 2:
                if ENDIAN == 'little':
                    # Swap 4 byte
                    b = construct.SLInt32("x").parse(buf)
                else:
                    b = construct.SBInt32("x").parse(buf)

                ret.append(b)
            elif f == 3:
                if ENDIAN == 'little':
                    # Swap 2 byte
                    b = construct.SLInt16("x").parse(buf)
                else:
                    b = construct.SBInt16("x").parse(buf)

                ret.append(b)
            # IEEE floats - 4 byte
            elif f == 5:
                if ENDIAN == 'little':
                    # Swap 4 byte
                    b = construct.LFloat32("x").parse(buf)
                else:
                    b = construct.BFloat32("x").parse(buf)

                ret.append(b)
            # INT - 1 byte
            elif f == 8:
                ret.append(construct.SBInt8("x").parse(buf))

    else:
        FH.read(n * length)

    return ret


def isEOF():
    try:
        n = FH.read(240)
        if n != 240:
            raise EOFError
        FH.seek(-240, os.SEEK_CUR)
        return False
    except EOFError:
        return True


def main():
    global L, F, T

    get_args()

    text_container = read_text_header()
    print_text_header(text_container)

    binary_container = read_binary_header()
    print_binary_header(binary_container)

    if binary_container:
        # Number of Extended Textural Headers
        nt = binary_container.extxt
        # Samples per trace
        n = binary_container.hns
        # Trace sample format
        if F is None:
            F = binary_container.format
        # Bytes per sample
        try:
            ll = SAMPLE_LENGTH[binary_container.format]
        except KeyError:
            ll = 4

        # Bytes per trace
        if L is None:
            L = ll * n
        else:
            n = int(L) / ll

        # Traces per record
        if T is None:
            T = binary_container.ntrpr
    else:
        T = 1
        n = ll = F = 0

    # Print Extended Textural Headers
    if nt > 0:
        for x in range(nt):
            text_container = read_text_header()
            print_text_header(text_container)
    elif nt == -1:
        while True:
            text_container = read_text_header()
            print_text_header(text_container)
            if last_extended_header(text_container):
                break

    while True:
        for t in range(T):
            trace_container = read_trace_header()
            extended_header = read_extended_header()
            # print t,
            print_trace_header(trace_container)
            print_extended_header(extended_header)
            trace = read_trace(n, ll, F)
            if trace:
                print '------------------------'
            for t in trace:
                print t

        if isEOF():
            break


if __name__ == "__main__":
    main()
