#!/usr/bin/env pnpython3
#
# A simple class to read SEG-Y rev 1 files
#
# Steve Azevedo, April 2013
#

import sys
import logging
import os
import exceptions
import construct
import numpy as np
from ph5.core import segy_h, ebcdic

PROG_VERSION = '2018.268'
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
          "recUpholeTime": 16,
          "sourceStaticCor": 16, "recStaticCor": 16, "totalStatic": 16,
          "lagTimeA": 16, "lagTimeB": 16, "delay": 16, "muteStart": 16,
          "muteEnd": 16, "sampleLength": 16, "deltaSample": 16, "gainType": 16,
          "gainConst": 16, "initialGain": 16, "correlated": 16,
          "sweepStart": 16, "sweepEnd": 16, "sweepLength": 16, "sweepType": 16,
          "sweepTaperAtStart": 16, "sweepTaperAtEnd": 16, "taperType": 16,
          "aliasFreq": 16, "aliasSlope": 16, "notchFreq": 16, "notchSlope": 16,
          "lowCutFreq": 16, "hiCutFreq": 16, "lowCutSlope": 16,
          "hiCutSlope": 16,
          "year": 16, "day": 16, "hour": 16, "minute": 16, "second": 16,
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


class InputsError (exceptions.Exception):
    def __init__(self, args=None):
        self.args = args


class Reader ():
    def __init__(self, infile=None):
        self.infile = infile
        self.ext_hdr_type = 'S'  # S => SEG, U => MENLO,
        # P => PASSCAL, I => SIOSEIS, N => INOVA
        self.txt_hdr_type = 'A'  # A => ASCII, E => EBCDIC
        # 1 = IBM - 4 bytes, 2 = INT - 4 bytes, 3 = INT - 2 bytes, 5 = IEEE - 4
        # bytes, 8 = INT - 1 byte
        self.trace_fmt = 5
        self.endianess = 'big'  # big, little
        self.bytes_per_sample = None   #
        self.traces_per_ensemble = None  # ntrpr
        self.aux_traces_per_ensemble = None  # nart
        self.samples_per_trace = None  # hns
        self.sample_rate = None  # 1 / hdt X 10^6 (samples per second)
        self.segy_rev = None  # SEG-Y revision
        # Number of extended textural headers
        self.number_of_extended_text_headers = None
        self.FH = None

    def set_infile(self, infile):
        self.infile = infile

    def set_ext_hdr_type(self, hdrtype):
        choices = ['S', 'U', 'P', 'L', 'I', 'N']
        if hdrtype in choices:
            self.ext_hdr_type = hdrtype
        else:
            raise InputsError(
                "S => SEG, U => MENLO, P => PASSCAL,"
                "I => SIOSEIS, N => iNova FireFly")

    def set_txt_hdr_type(self, hdrtype):
        choices = ['A', 'E']
        if hdrtype in choices:
            self.txt_hdr_type = hdrtype
        else:
            raise InputsError("A => ASCII, E => EBCDIC")

    def set_trace_fmt(self, fmt):
        choices = [1, 2, 3, 5, 8]
        if fmt in choices:
            self.trace_fmt = fmt
        else:
            raise InputsError(
                "1 = IBM - 4 bytes, 2 = INT - 4 bytes, 3 = INT - 2 bytes,"
                "5 = IEEE - 4 bytes, 8 = INT - 1 byte")

        self.bytes_per_sample = SAMPLE_LENGTH[fmt]

    def set_endianess(self, endianess):
        choices = ['big', 'little']
        if endianess in choices:
            self.endianess = endianess
        else:
            raise InputsError("big, little")

    def set_samples_per_trace(self, n):
        self.samples_per_trace = n

    def set_sample_rate(self, i):
        self.sample_rate = int(1.0 / (i * 1000000))

    def set_traces_per_ensemble(self, n):
        self.traces_per_ensemble = n

    def set_aux_traces_per_ensemble(self, n):
        self.aux_traces_per_ensemble = n

    def set_segy_revision(self, n):
        hi = 0xFF00 & n
        lo = 0x00FF & n
        self.segy_rev = "{0:d}.{1:d}".format(hi, lo)

    def set_number_of_extended_text_headers(self, n):
        self.number_of_extended_text_headers = n

    def set_bytes_per_sample(self, fmt=None):
        if fmt is None:
            fmt = self.trace_fmt
        # Bytes per sample based on format
        BBS = {1: 4, 2: 4, 3: 2, 4: 4, 5: 4, 8: 1}
        self.bytes_per_sample = BBS[fmt]

    def open_infile(self):
        try:
            self.FH = open(self.infile)
        except Exception as e:
            LOGGER.error(e)
            self.FH = None

    def read_buf(self, size):
        buf = None
        if not self.FH:
            self.open_infile()

        try:
            buf = self.FH.read(size)
        except Exception as e:
            LOGGER.error(e)

        if not buf:
            self.FH.close()

        return buf

    def read_text_header(self):
        ret = {}
        buf = self.read_buf(3200)
        t = segy_h.Text()

        t.parse(buf)

        keys = segy_h.Text().__keys__

        for k in keys:
            what = "container.{0}".format(k)
            if self.txt_hdr_type == 'E':
                txt = ebcdic.EbcdicToAscii(eval(what))
            else:
                txt = eval(what)

            ret[k] = txt

            if k == '_38_':
                flds = txt.split()
                try:
                    if flds[1] == 'MENLO':
                        self.set_ext_hdr_type('U')
                    elif flds[1] == 'PASSCAL':
                        self.set_ext_hdr_type('P')
                    elif flds[1] == 'SIOSEIS':
                        self.set_ext_hdr_type('I')
                    elif flds[1] == 'SEG':
                        self.set_ext_hdr_type('S')
                    elif flds[1] == 'INOVA':
                        self.set_ext_hdr_type('N')
                    else:
                        pass
                except IndexError:
                    pass

        return ret

    def last_extended_header(self, txt_hdr):
        '''   Return True if this contains an EndText stanza?   '''
        import re
        lastRE = re.compile(
            r".*\(\(.*SEG\:.*[Ee][Nn][Dd][Tt][Ee][Xx][Tt].*\)\).*")

        keys = segy_h.Text().__keys__
        for k in keys:
            t = txt_hdr[k]

            if lastRE.match(t):
                return True

        return False

    def read_binary_header(self):
        buf = self.read_buf(400)
        b = segy_h.Reel(self.endianess)

        ret = {}
        b.parse(buf)

        keys = segy_h.Reel().__keys__
        for k in keys:
            what = "container.{0}".format(k)
            ret[k] = eval(what)

        return ret

    def read_trace_header(self):
        buf = self.read_buf(180)
        if not buf:
            return {}
        t = segy_h.Trace(self.endianess)

        ret = {}
        t.parse(buf)

        keys = segy_h.Trace().__keys__
        for k in keys:
            what = "container.{0}".format(k)
            ret[k] = eval(what)

        return ret

    def read_extended_header(self):
        ret = {}
        buf = self.read_buf(60)

        e = segy_h.Seg(self.endianess)
        keys = segy_h.Seg().__keys__
        if self.ext_hdr_type == 'U':
            e = segy_h.Menlo(self.endianess)
            keys = segy_h.Menlo().__keys__
        elif self.ext_hdr_type == 'S':
            e = segy_h.Seg(self.endianess)
            keys = segy_h.Seg().__keys__
        elif self.ext_hdr_type == 'P':
            e = segy_h.Passcal(self.endianess)
            keys = segy_h.Passcal().__keys__
        elif self.ext_hdr_type == 'I':
            e = segy_h.Sioseis(self.endianess)
            keys = segy_h.Sioseis().__keys__
        elif self.ext_hdr_type == 'N':
            e = segy_h.iNova(self.endianess)
            keys = segy_h.iNova().__keys__

        e.parse(buf)

        for k in keys:
            what = "container.{0}".format(k)
            ret[k] = eval(what)

        return ret

    def read_trace(self, number_of_samples, bytes_per_sample):
        '''   Read data trace and return as numpy array   '''
        # FIXED, NOT FULLY TESTED
        # First version using NumPy 2013.303.a
        f = self.trace_fmt
        buf = self.read_buf(bytes_per_sample * number_of_samples)
        # IBM floats - 4 byte - Should be big endian
        if f == 1:
            import ibmfloat
            ret = []
            ll = len(buf)
            i = 0
            while True:
                if ll <= 0:
                    break
                b = buf[i:4 + i]
                ret.append(construct.BFloat32(
                    "x").parse(ibmfloat.ibm2ieee32(b)))
                i += 4
                ll -= 4
        # INT - 4 byte or 2 byte
        elif f == 2:
            if self.endianess != sys.byteorder:
                # Swap 4 byte
                ret = np.fromstring(buf, dtype=np.int32)
                ret = ret.byteswap()
            else:
                ret = np.fromstring(buf, dtype=np.int32)
        elif f == 3:
            if self.endianess != sys.byteorder:
                # Swap 2 byte
                ret = np.fromstring(buf, dtype=np.int16)
                ret = ret.byteswap()
            else:
                ret = np.fromstring(buf, dtype=np.int16)
        # IEEE floats - 4 byte
        elif f == 5:
            if self.endianess != sys.byteorder:
                # Swap 4 byte
                ret = np.fromstring(buf, dtype=np.float32)
                ret = ret.byteswap()
            else:
                ret = np.fromstring(buf, dtype=np.float32)
        # INT - 1 byte
        elif f == 8:
            ret = np.fromstring(buf, dtype=np.int8)
        return ret

    def isEOF(self):
        if not self.FH:
            self.open_infile()
        try:
            n = len(self.FH.read(240))
            if n != 240:
                raise EOFError
            self.FH.seek(-240, os.SEEK_CUR)
            return False
        except EOFError:
            return True


if __name__ == "__main__":
    infile = sys.argv[1]  # segy file
    sr = Reader(infile)
    # Set header type to ASCII
    sr.set_txt_hdr_type("A")
    # Set endianess of file
    sr.set_endianess('little')
    # Read the first text header and print contents
    th = sr.read_text_header()
    keys = sorted(th.keys())
    for k in keys:
        print th[k]

    # Read reel header
    bh = sr.read_binary_header()
    for k in bh.keys():
        print k, bh[k]

    # Set format of trace sample (needed)
    sr.set_trace_fmt(bh['format'])
    # Set number of traces per ensemble (needed)
    sr.set_traces_per_ensemble(bh['ntrpr'])
    if sr.traces_per_ensemble == 0:
        sr.set_traces_per_ensemble(1)
    # Set samples per trace
    sr.set_samples_per_trace(bh['hns'])
    # Set sample rate
    sr.set_sample_rate(bh['hdt'])

    # Print SEG-Y revision
    print "\nRev: ", bh['rev']

    # Read and print all extended textural headers
    number_of_extended_headers = bh['extxt']
    # Un-defined number of extended headers
    if number_of_extended_headers == -1:
        while True:
            th = sr.read_text_header()
            keys = sorted(th.keys())
            for k in keys:
                print th[k]
            # Check if last header
            if sr.last_extended_header():
                break
    # Defined number of extended headers
    elif number_of_extended_headers > 0:
        for n in range(number_of_extended_headers):
            th = sr.read_text_header()
            keys = sorted(th.keys())
            for k in keys:
                print th[k]

    for x in range(bh['hns']):
        print "x =", x
        th = sr.read_trace_header()
        eh = sr.read_extended_header()
        number_of_samples = th['sampleLength']
        bytes_per_sample = sr.bytes_per_sample
        for y in range(sr.traces_per_ensemble):
            print "\ty =", y
            trace = sr.read_trace(number_of_samples, bytes_per_sample)
            for z in trace:
                print "\t\tz =", z
