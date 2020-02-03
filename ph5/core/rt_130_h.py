#!/usr/bin/env pnpython3
#
# A low level rt-130 library
#
# RefTek 130, CPU firmware v2.9.0
#
# Steve Azevedo, July 2008
#

import sys
import logging
import exceptions
import os
import os.path
import string
import rt_130_py
import construct

PROG_VERSION = '2020.34'
LOGGER = logging.getLogger(__name__)

ver = construct.version[0] + construct.version[1] / 10.
if ver < 2.5:
    LOGGER.info("Exiting: construct version is {0}\n".format(ver))
    sys.exit()


def __version__():
    print PROG_VERSION


def pfloat():
    PFLOAT = "PFLOAT" / construct.Struct("X" / construct.Float32b)
    return PFLOAT


def puint():
    PINT = "PINT" / construct.Struct("x" / construct.Int32ub)
    return PINT


def psint():
    PINT = "PINT" / construct.Struct("x" / construct.Int32sb)
    return PINT


def psshort():
    PSHORT = "PSHORT" / construct.Struct("x" / construct.Int16sb)
    return PSHORT


pint_s = psint()


def build_int(x):
    global pint_s

    return pint_s.build(construct.Container(x=x))


pshort_s = psshort()


def build_short(x):
    global pshort_s

    return pshort_s.build(construct.Container(x=x))


class HeaderError(exceptions.Exception):

    def __init__(self, args=None):
        self.args = args


class CorruptPacketError(exceptions.Exception):

    def __init__(self, args=None):
        self.args = args


class EmptyDTPacketError(exceptions.Exception):

    def __init__(self, args=None):
        self.args = args


#
# Packet header
#


class PH_object(object):
    __slots__ = 'type', 'experiment', 'unit', 'year', 'doy', 'hr', 'mn', 'sc',\
                'ms', 'bytes', 'sequence'


def packet_header():
    PH = "PH" / construct.Struct("PacketType" / construct.BitsInteger(16),
                                 "ExperimentNumber" / construct.BitsInteger(8),
                                 "Year" / construct.BitsInteger(8),
                                 "UnitIDNumber" / construct.BitsInteger(16),
                                 "DOY" / construct.BitsInteger(12),
                                 "HH" / construct.BitsInteger(8),
                                 "MM" / construct.BitsInteger(8),
                                 "SS" / construct.BitsInteger(8),
                                 "TTT" / construct.BitsInteger(12),
                                 "ByteCount" / construct.BitsInteger(16),
                                 "PacketSequence" / construct.BitsInteger(16))
    return PH


class PacketHeader(object):
    __keys__ = (
        "PacketType",
        "ExperimentNumber",
        "Year",
        "UnitIDNumber",
        "Time",
        "ByteCount",
        "PacketSequence")

    def __init__(self):
        for b in PacketHeader.__keys__:
            self.__dict__[b] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable %s in packet"
                    " header.\n" %
                    k)

    def get(self):
        try:
            t = packet_header()
            ret = t.build(self)
        except Exception as e:
            raise HeaderError("Packet Header: " + e.message)

        return ret

    def parse(self, buf):
        try:
            t = packet_header()
            ret = t.parse(buf)
        except Exception as e:
            raise HeaderError("Packet Header: " + e.message)

        return ret

    def decode(self, buf):
        try:
            ph = PH_object()
            ret = rt_130_py.get_packet_header(buf)
            ph.type = ret[0]
            ph.experiment = ret[1]
            ph.year = ret[2]
            if ph.year > 80:
                ph.year += 1900
            else:
                ph.year += 2000
            ph.unit = hex(ret[3]).upper()[2:]
            ph.doy = ret[4]
            ph.hr = ret[5]
            ph.mn = ret[6]
            ph.sc = ret[7]
            ph.ms = ret[8]
            ph.bytes = ret[9]
            ph.sequence = ret[10]
        except Exception as e:
            raise HeaderError("Packet Header: " + e.message)
        return ph


#
# Data packet
#


class DT_object(object):
    __slots__ = 'event', 'data_stream', 'channel', 'samples', 'flags', \
                'data_format', 'data'


def data_packet():
    DT = "DT" / construct.Struct("PacketHeader" / construct.BitsInteger(128),
                                 "EventNumber" / construct.BitsInteger(16),
                                 "DataStream" / construct.BitsInteger(8),
                                 "Channel" / construct.BitsInteger(8),
                                 "Samples" / construct.BitsInteger(16),
                                 "Calibration" / construct.Flag,
                                 "Overscaled" / construct.Flag,
                                 "StackedData" / construct.Flag,
                                 "Unused" / construct.BitsInteger(2),
                                 "Second_EH_ET" / construct.Flag,
                                 "LastDataPacket" / construct.Flag,
                                 "FirstDataPacket" / construct.Flag,
                                 "DataFormat" / construct.BitsInteger(8),
                                 "Data" / construct.BitsInteger(8000))
    return DT


class DT(object):
    __keys__ = (
        "PacketHeader",
        "EventNumber",
        "DataStream",
        "Channel",
        "Samples",
        "Flags",
        "DataFormat",
        "Data")

    def __init__(self):
        for b in DT.__keys__:
            self.__dict__[b] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable %s in"
                    " data packet.\n" %
                    k)

    def get(self):
        try:
            t = data_packet()
            ret = t.build(self)
        except Exception as e:
            raise CorruptPacketError("DT Packet: " + e.message)

        return ret

    def parse(self, buf):
        try:
            t = data_packet()
            ret = t.parse(buf)
        except Exception as e:
            raise CorruptPacketError("DT Packet: " + e.message)

        return ret

    def decode(self, buf):
        try:
            dt = DT_object()
            ret = rt_130_py.get_data_header(buf)
            dt.event = ret[0]
            dt.data_stream = ret[1]
            dt.channel = ret[2]
            dt.samples = ret[3]
            dt.flags = ret[4]
            dt.data_format = ret[5]
            if dt.data_format == 0x16:
                dt.data = rt_130_py.read_int16(buf, dt.samples)
            elif dt.data_format == 0x32:
                dt.data = rt_130_py.read_int32(buf, dt.samples)
            elif dt.data_format == 0x33:
                dt = None
                raise Exception(
                    "Warning: Can't parse overscaled data formats\n")
            elif dt.data_format == 0xc0:
                dt.data = rt_130_py.read_steim1(buf, dt.samples)
            elif dt.data_format == 0xc1:
                dt = None
                raise Exception(
                    "Warning: Can't parse overscaled data formats\n")
            elif dt.data_format == 0xc2:
                dt.data = rt_130_py.read_steim2(buf, dt.samples)
            elif dt.data_format == 0xc3:
                dt = None
                raise Exception(
                    "Warning: Can't parse overscaled data formats\n")
            else:
                dt = None
                raise Exception(
                    "Warning: Unrecognized data format: %s\n" % hex(
                        dt.data_format))
        except Exception as e:
            raise CorruptPacketError("DT Packet: " + e.message)

        return dt


class EH_object(object):
    __slots__ = (
        'EventNumber', 'DataStream', 'Flags', 'DataFormat',
        'TriggerTimeMessage',
        'TimeSource', 'TimeQuality', 'ExtStationName', 'StationName',
        'StreamName', 'SampleRate', 'TriggerType', 'TriggerTime',
        'FirstSampleTime',
        'DetriggerTime', 'LastSampleTime', 'NominalBitWeight', 'TrueBitWeight',
        'Gain', 'A_DResolution', 'FullScaleAnalog', 'ChannelCode', 'SensorFSA',
        'SensorVPU', 'SensorUnits', 'StationNumber', 'TotalChannels',
        'Comment',
        'FilterList', 'Position', 'RefTek120')


#
# Event header/Event trailer
#


def event_header():
    EH = "EH" / construct.Struct(
                            "PacketHeader" / construct.BitStruct(
                                "PacketHeader" / construct.BitsInteger(128),
                                "EventNumber" / construct.BitsInteger(16),
                                "DataStream" / construct.BitsInteger(8),
                                "Reserved" / construct.BitsInteger(24),
                                "Flags" / construct.BitsInteger(8),
                                "DataFormat" / construct.BitsInteger(8)
                             ),
                             "TriggerTimeMessage" / construct.Bytes(33),
                             "TimeSource" / construct.Bytes(1),
                             "TimeQuality" / construct.Bytes(1),
                             "ExtStationName" / construct.Bytes(1),
                             "StationName" / construct.Bytes(4),
                             "StreamName" / construct.Bytes(16),
                             "Reserved1" / construct.Bytes(8),
                             "SampleRate" / construct.Bytes(4),
                             "TriggerType" / construct.Bytes(4),
                             "TriggerTime" / construct.Bytes(16),
                             "FirstSampleTime" / construct.Bytes(16),
                             "DetriggerTime" / construct.Bytes(16),
                             "LastSampleTime" / construct.Bytes(16),
                             "NominalBitWeight" / construct.Bytes(128),
                             "TrueBitWeight" / construct.Bytes(128),
                             "Gain" / construct.Bytes(16),
                             "A_DResolution" / construct.Bytes(16),
                             "FullScaleAnalog" / construct.Bytes(16),
                             "ChannelCode" / construct.Bytes(64),
                             "SensorFSA" / construct.Bytes(16),
                             "SensorVPU" / construct.Bytes(96),
                             "SensorUnits" / construct.Bytes(16),
                             "StationNumber" / construct.Bytes(48),
                             "Reserved2" / construct.Bytes(156),
                             "TotalChannels" / construct.Bytes(2),
                             "Comment" / construct.Bytes(40),
                             "FilterList" / construct.Bytes(16),
                             "Position" / construct.Bytes(26),
                             "RefTek120" / construct.Bytes(80))
    return EH


GAIN_CODE = {
    ' ': 'Unknown',
    '1': 'x1',
    '2': 'x8',
    '3': 'x32',
    '4': 'x128',
    '5': 'x512',
    '6': 'x2048',
    '7': 'x8192',
    '8': 'x100',
    'A': '12dB',
    'B': '24dB',
    'C': '36dB',
    'D': '48dB',
    'E': '60dB',
    'F': 'x2',
    'G': 'x4',
    'H': 'x16',
    'I': 'x64',
    'J': 'x256'}
AD_CODE = {' ': 'Unknown', '1': '8', '2': '16', '3': '24'}
FSA_CODE = {
    ' ': 'Unknown',
    '1': '+/-3.75',
    '2': '+/-5.0',
    '3': '+/-10.0',
    '4': '+/-20.0'}
TIME_SOURCE = {' ': 'Unknown', '1': 'Internal', '2': 'GPS'}
TIME_QUALITY = {
    ' ': 'Unknown',
    '?': 'No PLL',
    '0': '0 days since PLL',
    '1': '1 days since PLL',
    '2': '2 days since PLL',
    '3': '3 days since PLL',
    '4': '4 days since PLL',
    '5': '5 days since PLL',
    '6': '6 days since PLL',
    '7': '7 days since PLL',
    '8': '8 days since PLL',
    '9': '9 days since PLL'}


class EH(object):
    __keys__ = ("BIN.PacketHeader", "BIN.EventNumber", "BIN.DataStream",
                "BIN.Reserved", "BIN.Flags", "BIN.DataFormat",
                "TriggerTimeMessage",
                "TimeSource", "TimeQuality", "ExtStationName", "StationName",
                "StreamName", "Reserved1",
                "SampleRate", "TriggerType", "TriggerTime", "FirstSampleTime",
                "DetriggerTime", "LastSampleTime", "NominalBitWeight",
                "TrueBitWeight", "Gain", "A-DResolution", "FullScaleAnalog",
                "ChannelCode", "SensorFSA", "SensorVPU", "SensorUnits",
                "StationNumber", "Reserved2", "TotalChannels", "Comment",
                "FilterList", "Position", "RefTek120")

    def __init__(self):
        for b in EH.__keys__:
            self.__dict__[b] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable %s in"
                    " event header packet.\n" %
                    k)

    def get(self):
        try:
            t = event_header()
            ret = t.build(self)
        except Exception as e:
            raise CorruptPacketError("EH Packet: " + e.message)

        return ret

    def parse(self, buf):
        try:
            t = event_header()
            ret = t.parse(buf)
        except Exception as e:
            raise CorruptPacketError("EH Packet: " + e.message)

        return ret

    def bit_weights(self, s):
        ret = []
        for i in range(16):
            offset = i * 8
            ret.append(s[offset:offset + 8])

        return ret

    def decode(self, buf):
        try:
            eh = EH_object()
            eh.EventNumber = rt_130_py.bcd2int(buf, 32, 4)
            eh.DataStream = rt_130_py.bcd2int(buf, 36, 2)
            c = self.parse(buf)
            eh.Flags = c.BIN.Flags
            eh.DataFormat = hex(c.BIN.DataFormat)
            eh.TriggerTimeMessage = c.TriggerTimeMessage
            eh.TimeSource = TIME_SOURCE[c.TimeSource]
            eh.TimeQuality = TIME_QUALITY[c.TimeQuality]
            eh.ExtStationName = c.ExtStationName
            eh.StationName = c.StationName
            eh.StreamName = c.StreamName
            eh.SampleRate = c.SampleRate
            eh.TriggerType = c.TriggerType
            eh.TriggerTime = c.TriggerTime
            eh.FirstSampleTime = c.FirstSampleTime
            eh.DetriggerTime = c.DetriggerTime
            eh.LastSampleTime = c.LastSampleTime
            eh.NominalBitWeight = self.bit_weights(c.NominalBitWeight)
            eh.TrueBitWeight = self.bit_weights(c.TrueBitWeight)
            eh.Gain = []
            g = c.Gain
            for i in range(16):
                try:
                    eh.Gain.append(GAIN_CODE[g[i]])
                except KeyError:
                    pass

            eh.A_DResolution = []
            ad = c.A_DResolution
            for i in range(16):
                try:
                    eh.A_DResolution.append(AD_CODE[ad[i]])
                except KeyError:
                    pass

            eh.FullScaleAnalog = []
            fsa = c.FullScaleAnalog
            for i in range(16):
                try:
                    eh.FullScaleAnalog.append(FSA_CODE[fsa[i]])
                except KeyError:
                    pass

            eh.ChannelCode = c.ChannelCode
            eh.SensorFSA = []
            fsa = c.SensorFSA
            for i in range(16):
                try:
                    eh.SensorFSA.append(FSA_CODE[fsa[i]])
                except KeyError:
                    pass

            eh.SensorVPU = c.SensorVPU
            eh.SensorUnits = c.SensorUnits
            eh.StationNumber = c.StationNumber
            eh.TotalChannels = c.TotalChannels
            eh.Comment = c.Comment
            eh.FilterList = c.FilterList
            eh.Position = c.Position
            eh.RefTek120 = c.RefTek120
        except Exception as e:
            raise CorruptPacketError("EH Packet: " + e.message)

        return eh


#
# State of Health packets
#
def SOH_packet():
    SH = "SH" / construct.Struct(
                            "BIN" / construct.BitStruct(
                              "PacketHeader" / construct.BitsInteger(128)
                            ),
                            "Reserved" / construct.Bytes(8),
                            "Information" / construct.Bytes(1000))
    return SH


class SH(object):
    __keys__ = ("BIN.PacketHeader", "Reserved", "Information")

    def __init__(self):
        for b in SH.__keys__:
            self.__dict__[b] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable %s in "
                    "SOH packet.\n" %
                    k)

    def get(self):
        try:
            t = SOH_packet()
            ret = t.build(self)
        except Exception as e:
            raise CorruptPacketError("SH Packet: " + e.message)

        return ret

    def parse(self, buf):
        try:
            t = SOH_packet()
            ret = t.parse(buf)
        except Exception as e:
            raise CorruptPacketError("SH Packet: " + e.message)

        return ret


#
# Station Channel packets


def station_channel():
    
    SC = "SC" / construct.Struct(
                            "BIN" / construct.BitStruct(
                              "PacketHeader" / construct.BitsInteger(128)
                            ),
                            "ExperimentNumber" / construct.Bytes(2),
                            "ExperimentName" / construct.Bytes(24),
                            "ExperimentComment" / construct.Bytes(40),
                            "StationNumber" / construct.Bytes(4),
                            "StationName" / construct.Bytes(24),
                            "StationComment" / construct.Bytes(40),
                            "DASModel" / construct.Bytes(12),
                            "DASSerial" / construct.Bytes(12),
                            "ExperimentStart" / construct.Bytes(14),
                            "TimeClockType" / construct.Bytes(4),
                            "TimeClockSN" / construct.Bytes(10),
                            "ChanInfo1" / construct.Struct(
                                "Channel" / construct.Bytes(2),
                                "ChannelName" / construct.Bytes(10),
                                "Azimuth" / construct.Bytes(10),
                                "Inclination" / construct.Bytes(10),
                                "XCoordinate" / construct.Bytes(10),
                                "YCoordinate" / construct.Bytes(10),
                                "ZCoordinate" / construct.Bytes(10),
                                "XYUnits" / construct.Bytes(4),
                                "ZUnits" / construct.Bytes(4),
                                "PreampGain" / construct.Bytes(4),
                                "SensorModel" / construct.Bytes(12),
                                "SensorSerial" / construct.Bytes(12),
                                "Comments" / construct.Bytes(40),
                                "AdjustedNominalBitWeight" / construct.Bytes(8)
                            ),
                            "ChanInfo2" / construct.Struct(
                                "Channel" / construct.Bytes(2),
                                "ChannelName" / construct.Bytes(10),
                                "Azimuth" / construct.Bytes(10),
                                "Inclination" / construct.Bytes(10),
                                "XCoordinate" / construct.Bytes(10),
                                "YCoordinate" / construct.Bytes(10),
                                "ZCoordinate" / construct.Bytes(10),
                                "XYUnits" / construct.Bytes(4),
                                "ZUnits" / construct.Bytes(4),
                                "PreampGain" / construct.Bytes(4),
                                "SensorModel" / construct.Bytes(12),
                                "SensorSerial" / construct.Bytes(12),
                                "Comments" / construct.Bytes(40),
                                "AdjustedNominalBitWeight" / construct.Bytes(8)
                            ),
                            "ChanInfo3" / construct.Struct(
                                "Channel" / construct.Bytes(2),
                                "ChannelName" / construct.Bytes(10),
                                "Azimuth" / construct.Bytes(10),
                                "Inclination" / construct.Bytes(10),
                                "XCoordinate" / construct.Bytes(10),
                                "YCoordinate" / construct.Bytes(10),
                                "ZCoordinate" / construct.Bytes(10),
                                "XYUnits" / construct.Bytes(4),
                                "ZUnits" / construct.Bytes(4),
                                "PreampGain" / construct.Bytes(4),
                                "SensorModel" / construct.Bytes(12),
                                "SensorSerial" / construct.Bytes(12),
                                "Comments" / construct.Bytes(40),
                                "AdjustedNominalBitWeight" / construct.Bytes(8)
                            ),
                            "ChanInfo4" / construct.Struct(
                                "Channel" / construct.Bytes(2),
                                "ChannelName" / construct.Bytes(10),
                                "Azimuth" / construct.Bytes(10),
                                "Inclination" / construct.Bytes(10),
                                "XCoordinate" / construct.Bytes(10),
                                "YCoordinate" / construct.Bytes(10),
                                "ZCoordinate" / construct.Bytes(10),
                                "XYUnits" / construct.Bytes(4),
                                "ZUnits" / construct.Bytes(4),
                                "PreampGain" / construct.Bytes(4),
                                "SensorModel" / construct.Bytes(12),
                                "SensorSerial" / construct.Bytes(12),
                                "Comments" / construct.Bytes(40),
                                "AdjustedNominalBitWeight" / construct.Bytes(8)
                            ),
                            "ChanInfo5" / construct.Struct(
                                "Channel" / construct.Bytes(2),
                                "ChannelName" / construct.Bytes(10),
                                "Azimuth" / construct.Bytes(10),
                                "Inclination" / construct.Bytes(10),
                                "XCoordinate" / construct.Bytes(10),
                                "YCoordinate" / construct.Bytes(10),
                                "ZCoordinate" / construct.Bytes(10),
                                "XYUnits" / construct.Bytes(4),
                                "ZUnits" / construct.Bytes(4),
                                "PreampGain" / construct.Bytes(4),
                                "SensorModel" / construct.Bytes(12),
                                "SensorSerial" / construct.Bytes(12),
                                "Comments" / construct.Bytes(40),
                                "AdjustedNominalBitWeight" / construct.Bytes(8)
                            ),
                          "Reserved" / construct.Bytes(76),
                          "ImplementTime" / construct.Bytes(16)          
                        )
    return SC


class SC(object):
    __keys__ = ("BIN.PacketHeader", "ExperimentNumber", "ExperimentName",
                "ExperimentComment",
                "StationNumber", "StationName", "StationComment", "DASModel",
                "DASSerial",
                "ExperimentStart", "TimeClockType", "TimeClockSN",
                "ChanInfo1.Channel", "ChanInfo1.ChannelName",
                "ChanInfo1.Azimuth",
                "ChanInfo1.Inclination", "ChanInfo1.XCoordinate",
                "ChanInfo1.YCoordinate",
                "ChanInfo1.ZCoordinate", "ChanInfo1.XYUnits",
                "ChanInfo1.ZUnits",
                "ChanInfo1.PreampGain", "ChanInfo1.SensorModel",
                "ChanInfo1.SensorSerial",
                "ChanInfo1.Comments", "ChanInfo1.AdjustedNominalBitWeight",
                "ChanInfo2.Channel", "ChanInfo2.ChannelName",
                "ChanInfo2.Azimuth",
                "ChanInfo2.Inclination", "ChanInfo2.XCoordinate",
                "ChanInfo2.YCoordinate",
                "ChanInfo2.ZCoordinate", "ChanInfo2.XYUnits",
                "ChanInfo2.ZUnits",
                "ChanInfo2.PreampGain", "ChanInfo2.SensorModel",
                "ChanInfo2.SensorSerial",
                "ChanInfo2.Comments", "ChanInfo2.AdjustedNominalBitWeight",
                "ChanInfo3.Channel", "ChanInfo3.ChannelName",
                "ChanInfo3.Azimuth",
                "ChanInfo3.Inclination", "ChanInfo3.XCoordinate",
                "ChanInfo3.YCoordinate",
                "ChanInfo3.ZCoordinate", "ChanInfo3.XYUnits",
                "ChanInfo3.ZUnits",
                "ChanInfo3.PreampGain", "ChanInfo3.SensorModel",
                "ChanInfo3.SensorSerial",
                "ChanInfo3.Comments", "ChanInfo3.AdjustedNominalBitWeight",
                "ChanInfo4.Channel", "ChanInfo4.ChannelName",
                "ChanInfo4.Azimuth",
                "ChanInfo4.Inclination", "ChanInfo4.XCoordinate",
                "ChanInfo4.YCoordinate",
                "ChanInfo4.ZCoordinate", "ChanInfo4.XYUnits",
                "ChanInfo4.ZUnits",
                "ChanInfo4.PreampGain", "ChanInfo4.SensorModel",
                "ChanInfo4.SensorSerial",
                "ChanInfo4.Comments", "ChanInfo4.AdjustedNominalBitWeight",
                "ChanInfo5.Channel", "ChanInfo5.ChannelName",
                "ChanInfo5.Azimuth",
                "ChanInfo5.Inclination", "ChanInfo5.XCoordinate",
                "ChanInfo5.YCoordinate",
                "ChanInfo5.ZCoordinate", "ChanInfo5.XYUnits",
                "ChanInfo5.ZUnits",
                "ChanInfo5.PreampGain", "ChanInfo5.SensorModel",
                "ChanInfo5.SensorSerial",
                "ChanInfo5.Comments", "ChanInfo5.AdjustedNominalBitWeight",
                "Reserved", "ImplementTime")

    def __init__(self):
        for b in SC.__keys__:
            self.__dict__[b] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                # XXX   Needs proper exception handling   XXX
                raise HeaderError(
                    "Warning: Attempt to set unknown variable %s in station"
                    " channel packet.\n" %
                    k)

    def get(self):
        try:
            t = station_channel()
            ret = t.build(self)
        except Exception as e:
            raise CorruptPacketError("SC Packet: " + e.message)

        return ret

    def parse(self, buf):
        try:
            t = station_channel()
            ret = t.parse(buf)
        except Exception as e:
            raise CorruptPacketError("SC Packet: " + e.message)

        return ret


#
# Aux Data Parameter packets
#


def aux_data_parameter():
    AD = "AD" / construct.Struct(
                                "BIN" / construct.BitStruct(
                                  "PacketHeader" / construct.BitsInteger(128)
                                ),
                                "Marker" / construct.Bytes(2),
                                "Channels" / construct.Bytes(16),
                                "SamplePeriod" / construct.Bytes(8),
                                "DataFormat" / construct.Bytes(2),
                                "RecordLength" / construct.Bytes(8),
                                "RecordingDestination" / construct.Bytes(4),
                                "Reserved" / construct.Bytes(950),
                                "ImplementTime" / construct.Bytes(16))
    return AD


class AD(object):
    __keys__ = (
        "BIN.PacketHeader",
        "Marker",
        "Channels",
        "SamplePeriod",
        "DataFormat",
        "RecordLength",
        "RecordingDestination",
        "Reserved",
        "ImplementTime")

    def __init__(self):
        for b in AD.__keys__:
            self.__dict__[b] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable %s in auxiliary"
                    " data packet.\n" %
                    k)

    def get(self):
        try:
            t = aux_data_parameter()
            ret = t.build(self)
        except Exception as e:
            raise CorruptPacketError("AD Packet: " + e.message)

        return ret

    def parse(self, buf):
        try:
            t = aux_data_parameter()
            ret = t.parse(buf)
        except Exception as e:
            raise CorruptPacketError("AD Packet: " + e.message)

        return ret


#
# Calibration Parameter packets
#


def cal_parameter():
    CD = "CD" / construct.Struct(
                                "BIN" / construct.BitStruct(
                                  "PacketHeader" / construct.BitsInteger(128)
                                ),
                                "_72ACalibration" / construct.Struct(
                                    "StartTime" / construct.Bytes(14),
                                    "RepeatInterval" / construct.Bytes(8),
                                    "Intervals" / construct.Bytes(4),
                                    "Length" / construct.Bytes(8),
                                    "StepOnOff" / construct.Bytes(4),
                                    "StepPeriod" / construct.Bytes(8),
                                    "StepSize" / construct.Bytes(8),
                                    "StepAmplitude" / construct.Bytes(8),
                                    "StepOutput" / construct.Bytes(4),
                                    "Reserved" / construct.Bytes(48)
                                ),
                                "_130AutoCenter1" / construct.Struct(
                                    "Sensor" / construct.Bytes(1),
                                    "Enable" / construct.Bytes(1),
                                    "ReadingInterval" / construct.Bytes(4),
                                    "CycleInterval" / construct.Bytes(2),
                                    "Level" / construct.Bytes(4),
                                    "Attempts" / construct.Bytes(2),
                                    "AttemptInterval" / construct.Bytes(2)
                                ),
                                "_130AutoCenter2" / construct.Struct(
                                    "Sensor" / construct.Bytes(1),
                                    "Enable" / construct.Bytes(1),
                                    "ReadingInterval" / construct.Bytes(4),
                                    "CycleInterval" / construct.Bytes(2),
                                    "Level" / construct.Bytes(4),
                                    "Attempts" / construct.Bytes(2),
                                    "AttemptInterval" / construct.Bytes(2)
                                ),
                                "_130AutoCenter3" / construct.Struct(
                                    "Sensor" / construct.Bytes(1),
                                    "Enable" / construct.Bytes(1),
                                    "ReadingInterval" / construct.Bytes(4),
                                    "CycleInterval" / construct.Bytes(2),
                                    "Level" / construct.Bytes(4),
                                    "Attempts" / construct.Bytes(2),
                                    "AttemptInterval" / construct.Bytes(2)
                                ),
                                "_130AutoCenter4" / construct.Struct(
                                    "Sensor" / construct.Bytes(1),
                                    "Enable" / construct.Bytes(1),
                                    "ReadingInterval" / construct.Bytes(4),
                                    "CycleInterval" / construct.Bytes(2),
                                    "Level" / construct.Bytes(4),
                                    "Attempts" / construct.Bytes(2),
                                    "AttemptInterval" / construct.Bytes(2)
                                ),
                                "_130Calibration1" / construct.Struct(
                                    "Sensor" / construct.Bytes(1),
                                    "Enable" / construct.Bytes(1),
                                    "Reserved" / construct.Bytes(2),
                                    "Duration" / construct.Bytes(4),
                                    "Amplitude" / construct.Bytes(4),
                                    "Signal" / construct.Bytes(4),
                                    "StepInterval" / construct.Bytes(4),
                                    "StepWidth" / construct.Bytes(4),
                                    "SineFrequency" / construct.Bytes(4)
                                ),
                                "_130Calibration2" / construct.Struct(
                                    "Sensor" / construct.Bytes(1),
                                    "Enable" / construct.Bytes(1),
                                    "Reserved" / construct.Bytes(2),
                                    "Duration" / construct.Bytes(4),
                                    "Amplitude" / construct.Bytes(4),
                                    "Signal" / construct.Bytes(4),
                                    "StepInterval" / construct.Bytes(4),
                                    "StepWidth" / construct.Bytes(4),
                                    "SineFrequency" / construct.Bytes(4)
                                ),
                                "_130Calibration3" / construct.Struct(
                                    "Sensor" / construct.Bytes(1),
                                    "Enable" / construct.Bytes(1),
                                    "Reserved" / construct.Bytes(2),
                                    "Duration" / construct.Bytes(4),
                                    "Amplitude" / construct.Bytes(4),
                                    "Signal" / construct.Bytes(4),
                                    "StepInterval" / construct.Bytes(4),
                                    "StepWidth" / construct.Bytes(4),
                                    "SineFrequency" / construct.Bytes(4)
                                ),
                                "_130Calibration4" / construct.Struct(
                                    "Sensor" / construct.Bytes(1),
                                    "Enable" / construct.Bytes(1),
                                    "Reserved" / construct.Bytes(2),
                                    "Duration" / construct.Bytes(4),
                                    "Amplitude" / construct.Bytes(4),
                                    "Signal" / construct.Bytes(4),
                                    "StepInterval" / construct.Bytes(4),
                                    "StepWidth" / construct.Bytes(4),
                                    "SineFrequency" / construct.Bytes(4)
                                ),
                                "_130CalibrationSequence1" / construct.Struct(
                                    "Sequence" / construct.Bytes(1),
                                    "Enable" / construct.Bytes(1),
                                    "Reserved1" / construct.Bytes(2),
                                    "StartTime" / construct.Bytes(14),
                                    "Interval" / construct.Bytes(8),
                                    "Count" / construct.Bytes(2),
                                    "RecordLength" / construct.Bytes(8),
                                    "Reserved2" / construct.Bytes(22),
                                ),
                                "_130CalibrationSequence2" / construct.Struct(
                                    "Sequence" / construct.Bytes(1),
                                    "Enable" / construct.Bytes(1),
                                    "Reserved1" / construct.Bytes(2),
                                    "StartTime" / construct.Bytes(14),
                                    "Interval" / construct.Bytes(8),
                                    "Count" / construct.Bytes(2),
                                    "RecordLength" / construct.Bytes(8),
                                    "Reserved2" / construct.Bytes(22),
                                ),
                                "_130CalibrationSequence3" / construct.Struct(
                                    "Sequence" / construct.Bytes(1),
                                    "Enable" / construct.Bytes(1),
                                    "Reserved1" / construct.Bytes(2),
                                    "StartTime" / construct.Bytes(14),
                                    "Interval" / construct.Bytes(8),
                                    "Count" / construct.Bytes(2),
                                    "RecordLength" / construct.Bytes(8),
                                    "Reserved2" / construct.Bytes(22),
                                ),
                                "_130CalibrationSequence4" / construct.Struct(
                                    "Sequence" / construct.Bytes(1),
                                    "Enable" / construct.Bytes(1),
                                    "Reserved1" / construct.Bytes(2),
                                    "StartTime" / construct.Bytes(14),
                                    "Interval" / construct.Bytes(8),
                                    "Count" / construct.Bytes(2),
                                    "RecordLength" / construct.Bytes(8),
                                    "Reserved2" / construct.Bytes(22),
                                ),
                                "Reserved" / construct.Bytes(470),
                                "ImplementTime" / construct.Bytes(16))
    return CD


class CD(object):
    __keys__ = (
        "BIN.PacketHeader",
        "72ACalibration",
        "130AutoCenter",
        "130Calibration",
        "ImplementTime")

    def __init__(self):
        for b in CD.__keys__:
            self.__dict__[b] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable %s in auxiliary"
                    " data packet.\n" %
                    k)

    def get(self):
        try:
            t = cal_parameter()
            ret = t.build(self)
        except Exception as e:
            raise CorruptPacketError("CD Packet: " + e.message)

        return ret

    def parse(self, buf):
        try:
            t = cal_parameter()
            ret = t.parse(buf)
        except Exception as e:
            raise CorruptPacketError("CD Packet: " + e.message)

        return ret


#
# Data Stream packets
#


class DS_object(object):
    __slots__ = "ImplementTime", "DataStream", "DataStreamName", \
                "RecordingDestination", "ChannelsIncluded", "SampleRate", \
                "DataFormat", "TriggerType", "Trigger"


def data_stream():
    DS = "DS" / construct.Struct(
                                "BIN" / construct.BitStruct(
                                  "PacketHeader" / construct.BitsInteger(128)
                                ),
                                "DataStreamInfo" / construct.Bytes(920),
                                "Reserved" / construct.Bytes(72),
                                "ImplementTime" / construct.Bytes(16))
    return DS


def data_stream_info():
    DSI = "DSI" / construct.Struct(
            "Info1" / construct.Struct(
                "DataStream" / construct.Bytes(2),
                "DataStreamName" / construct.Bytes(16),
                "RecordingDestination" / construct.Bytes(4),
                "Reserved" / construct.Bytes(4),
                "ChannelsIncluded" / construct.Bytes(16),
                "SampleRate" / construct.Bytes(4),
                "DataFormat" / construct.Bytes(2),
                "Reserved1" / construct.Bytes(16),
                "TriggerType" / construct.Bytes(4),
                "TriggerDescription" / construct.Bytes(162)
            ),
            "Info2" / construct.Struct(
                "DataStream" / construct.Bytes(2),
                "DataStreamName" / construct.Bytes(16),
                "RecordingDestination" / construct.Bytes(4),
                "Reserved" / construct.Bytes(4),
                "ChannelsIncluded" / construct.Bytes(16),
                "SampleRate" / construct.Bytes(4),
                "DataFormat" / construct.Bytes(2),
                "Reserved1" / construct.Bytes(16),
                "TriggerType" / construct.Bytes(4),
                "TriggerDescription" / construct.Bytes(162)
            ),
            "Info3" / construct.Struct(
                "DataStream" / construct.Bytes(2),
                "DataStreamName" / construct.Bytes(16),
                "RecordingDestination" / construct.Bytes(4),
                "Reserved" / construct.Bytes(4),
                "ChannelsIncluded" / construct.Bytes(16),
                "SampleRate" / construct.Bytes(4),
                "DataFormat" / construct.Bytes(2),
                "Reserved1" / construct.Bytes(16),
                "TriggerType" / construct.Bytes(4),
                "TriggerDescription" / construct.Bytes(162)
            ),
            "Info4" / construct.Struct(
                "DataStream" / construct.Bytes(2),
                "DataStreamName" / construct.Bytes(16),
                "RecordingDestination" / construct.Bytes(4),
                "Reserved" / construct.Bytes(4),
                "ChannelsIncluded" / construct.Bytes(16),
                "SampleRate" / construct.Bytes(4),
                "DataFormat" / construct.Bytes(2),
                "Reserved1" / construct.Bytes(16),
                "TriggerType" / construct.Bytes(4),
                "TriggerDescription" / construct.Bytes(162)
            )
        )
    return DSI


def continuous_trigger():
    CON = "CON" / construct.Struct("RecordLength" / construct.Bytes(8),
                                   "StartTime" / construct.Bytes(14),
                                   "Reserved" / construct.Bytes(140))
    return CON


def cross_stream_trigger():
    CRS = "CRS" / construct.Struct("TriggerStreamNo" / construct.Bytes(2),
                                   "PretriggerLength" / construct.Bytes(8),
                                   "RecordLength" / construct.Bytes(8),
                                   "Reserved" / construct.Bytes(144))
    return CRS


def event_trigger():
    EVT = "EVT" / construct.Struct("TriggerChannels" / construct.Bytes(16),
                                   "MinimumChannels" / construct.Bytes(2),
                                   "TriggerWindow" / construct.Bytes(8),
                                   "PretriggerLength" / construct.Bytes(8),
                                   "TriggerWindow" / construct.Bytes(8),
                                   "PretriggerLength" / construct.Bytes(8),
                                   "PosttriggerLength" / construct.Bytes(8),
                                   "RecordLength" / construct.Bytes(8),
                                   "Reserved1" / construct.Bytes(8),
                                   "STALength" / construct.Bytes(8),
                                   "LTALength" / construct.Bytes(8),
                                   "MeanRemoval" / construct.Bytes(8),
                                   "TriggerRatio" / construct.Bytes(8),
                                   "DetriggerRatio" / construct.Bytes(8),
                                   "LTAHold" / construct.Bytes(4),
                                   "LowPassCornerFreq" / construct.Bytes(4),
                                   "HighPassCornerFreq" / construct.Bytes(4),
                                   "Reserved2" / construct.Bytes(52))
    return EVT


def external_trigger():
    EXT = "EXT" / construct.Struct("PretriggerLength" / construct.Bytes(8),
                                   "RecordLength" / construct.Bytes(8),
                                   "Reserved" / construct.Bytes(146))
    return EXT


def level_trigger():
    LEV = "LEV" / construct.Struct("Level" / construct.Bytes(8),
                                   "PretriggerLength" / construct.Bytes(8),
                                   "RecordLength" / construct.Bytes(8),
                                   "LowPassCornerFreq" / construct.Bytes(4),
                                   "HighPassCornerFreq" / construct.Bytes(4),
                                   "Reserved" / construct.Bytes(130))
    return LEV


def time_trigger():
    TIM = "TIM" / construct.Struct("StartTime" / construct.Bytes(14),
                                   "RepeatInterval" / construct.Bytes(8),
                                   "Intervals" / construct.Bytes(4),
                                   "Reserved1" / construct.Bytes(8),
                                   "RecordLength" / construct.Bytes(8),
                                   "Reserved2" / construct.Bytes(120))
    return TIM


def time_list_trigger():
    TML = "TML" / construct.Struct("StartTime01" / construct.Bytes(14),
                                   "StartTime02" / construct.Bytes(14),
                                   "StartTime03" / construct.Bytes(14),
                                   "StartTime04" / construct.Bytes(14),
                                   "StartTime05" / construct.Bytes(14),
                                   "StartTime06" / construct.Bytes(14),
                                   "StartTime07" / construct.Bytes(14),
                                   "StartTime08" / construct.Bytes(14),
                                   "StartTime09" / construct.Bytes(14),
                                   "StartTime10" / construct.Bytes(14),
                                   "StartTime11" / construct.Bytes(14),
                                   "RecordLength" / construct.Bytes(8))
    return TML


class DS(object):
    __keys__ = (
        "BIN.PacketHeader",
        "DataStreamInfo",
        "Reserved",
        "ImplementTime")

    def __init__(self):
        for b in DS.__keys__:
            self.__dict__[b] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable %s in "
                    "auxiliary data packet.\n" %
                    k)

    def get(self):
        try:
            t = data_stream()
            ret = t.build(self)
        except Exception as e:
            raise CorruptPacketError("DS Packet: " + e.message)

        return ret

    def parse(self, buf):
        try:
            t = data_stream()
            ret = t.parse(buf)
        except Exception as e:
            raise CorruptPacketError("DS Packet: " + e.message)

        return ret

    def parse_dsi(self, buf):
        try:
            t = data_stream_info()
            ret = t.parse(buf)
        except Exception as e:
            raise CorruptPacketError("DS Packet: " + e.message)

        return ret

    def parse_trigger(self, trig, buf):
        try:
            if trig == 'EVT':
                t = event_trigger()
            elif trig == 'TIM':
                t = time_trigger()
            elif trig == 'LEV':
                t = level_trigger()
            elif trig == 'CON':
                t = continuous_trigger()
            elif trig == 'RAD' or trig == 'TML':
                t = time_list_trigger()
            elif trig == 'EXT':
                t = external_trigger()
            elif trig == 'CRS':
                t = cross_stream_trigger()
            else:
                ret = None

            ret = t.parse(buf)
        except Exception as e:
            raise CorruptPacketError("DS Packet: " + e.message)

        return ret

    def decode(self, buf):
        try:
            dataStreams = []
            ds = self.parse(buf)
            for i in range(1, 5):
                pre = "dsi.Info%s." % i
                stream = eval(pre + "DataStream")
                if stream[0] != " ":
                    trigger = string.strip(eval(pre + "TriggerType"))
                    tbuf = eval(pre + "TriggerDescription")
                    td = self.parse_trigger(trigger, tbuf)
                    wo_no = DS_object()
                    wo_no.ImplementTime = ds.ImplementTime
                    wo_no.DataStream = eval(pre + "DataStream")
                    wo_no.DataStreamName = eval(pre + "DataStreamName")
                    wo_no.RecordingDestination = eval(
                        pre + "RecordingDestination")
                    wo_no.ChannelsIncluded = eval(pre + "ChannelsIncluded")
                    tmp = []
                    for j in range(16):
                        if wo_no.ChannelsIncluded[j] != ' ':
                            tmp.append("%d," % (j + 1))

                    wo_no.ChannelsIncluded = string.join(tmp)
                    wo_no.SampleRate = eval(pre + "SampleRate")
                    wo_no.DataFormat = eval(pre + "DataFormat")
                    wo_no.TriggerType = eval(pre + "TriggerType")
                    wo_no.Trigger = td
                    dataStreams.append(wo_no)
        except Exception as e:
            raise CorruptPacketError("DS Packet: " + e.message)

        return dataStreams


#
# Filter Description packets
#


def filter_description():
    FD = "FD" / construct.Struct(
                    "BIN" / construct.BitStruct(
                        "PacketHeader" / construct.BitsInteger(128),
                        "FilterInfo" / construct.Bytes(992),
                    ),
                    "ImplementTime" / construct.Bytes(16)
                )
    return FD


def filter_info():
    FI = "FI" / construct.Struct("FilterBlockCount" / construct.Int8ub,
                                   "FilterID" / construct.Bytes(1),
                                   "FilterDecimation" / construct.Int8ub,
                                   "FilterScaler" / construct.Int8ub,
                                   "FilterCoefficientCount" / construct.Int8ub,
                                   "PacketCoefficientCount" / construct.Int8ub,
                                   "CoefficientPacketCount" / construct.Int8ub,
                                   "CoefficientFormat" / construct.Int8ub)
    return FI


class FD_object(object):
    __slots__ = "ImplementTime", "FilterBlockCount", "FilterID", \
                "FilterDecimation", "FilterScaler", "FilterCoefficientCount", \
                "PacketCoefficientCount", "CoefficientPacketCount", \
                "CoefficientFormat", "Coefficients"


class FD(object):
    __keys__ = ("BIN.PacketHeader", "BIN.FilterInfo", "ImplementTime")

    def __init__(self):
        for b in FD.__keys__:
            self.__dict__[b] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable %s in "
                    "filter description packet.\n" %
                    k)

    def get(self):
        try:
            t = filter_description()
            ret = t.build(self)
        except Exception as e:
            raise CorruptPacketError("FD Packet: " + e.message)

        return ret

    def parse_fi(self, buf):
        try:
            t = filter_info()
            ret = t.parse(buf)
        except Exception as e:
            raise CorruptPacketError("FD Packet: " + e.message)

        return ret

    def parse(self, buf):
        try:
            t = filter_description()
            ret = t.parse(buf)
        except Exception as e:
            raise CorruptPacketError("FD Packet: " + e.message)

        return ret

    def decode(self, buf):
        '''   XXX   decode filter info here   XXX
              Untested as of Nov 3 2008
        '''
        F = []
        fiptr = 0
        coeffptr = 0
        try:
            fd = self.parse(buf)
            ibuf = fd.BIN.FilterInfo
            try:
                while True:
                    coeff = []
                    coeffptr += 8
                    fi = self.parse_fi(ibuf[0:])
                    if fi.FilterBlockCount == 0:
                        break
                    format = rt_130_py.bcd2int(ibuf, 14, 2)
                    # Read filter coefficients
                    for i in range(fi.PacketCoefficientCount):
                        n = i + coeffptr
                        if format == 16:
                            n = (i * 2) + coeffptr
                            coeff.append(build_short(ibuf[n:n + 2]))
                        elif format == 32:
                            n = (i * 4) + coeffptr
                            coeff.append(build_short(ibuf[n:n + 4]))

                    fdo = FD_object()
                    fdo.ImplementTime = fd.ImplementTime
                    fdo.FilterBlockCount = fi.FilterBlockCount
                    fdo.FilterID = fi.FilterID
                    fdo.FilterDecimation = fi.FilterDecimation
                    fdo.FilterScaler = fi.FilterScaler
                    fdo.FilterCoefficientCount = fi.FilterCoefficientCount
                    fdo.PacketCoefficientCount = fi.PacketCoefficientCount
                    fdo.CoefficientPacketCount = fi.CoefficientPacketCount
                    fdo.CoefficientFormat = fi.CoefficientFormat
                    fdo.Coefficients = coeff
                    F.append(fdo)
                    fiptr = fiptr + 8 + coeffptr
                    fd = self.parse(buf[fiptr:])
                    ibuf = fd.BIN.FilterInfo
            except Exception as e:
                F = []
                raise Exception(
                    "Error parsing FD packet. This appears to be a bug!"
                    "\n{0}\n".format(e.message))

        except Exception as e:
            raise CorruptPacketError("FD Packet: {0:s}".format(e.message))

        return F


#
# Operating Mode Parameter packets
#


def operating_mode():
    OM = "OM" / construct.Struct(
                    "BIN" / construct.BitStruct(
                        "PacketHeader" / construct.BitsInteger(128),
                    ),
                    "_72APowerState" / construct.Bytes(2),
                    "RecordingMode" / construct.Bytes(2),
                    "Reserved1" / construct.Bytes(4),
                    "AutoDumpOnET" / construct.Bytes(1),
                    "Reserved2" / construct.Bytes(1),
                    "AutoDumpThreshold" / construct.Bytes(),
                    "_72APowerDownDelay" / construct.Bytes(4),
                    "DiskWrap" / construct.Bytes(1),
                    "Reserved3" / construct.Bytes(1),
                    "_72ADiskPower" / construct.Bytes(1),
                    "_72ATerminatorPower" / construct.Bytes(1),
                    "DiskRetry" / construct.Bytes(1),
                    "Reserved4" / construct.Bytes(11),
                    "Reserved5" / construct.Bytes(2),
                    "_72AWakeUpStartTime" / construct.Bytes(12),
                    "_72AWakeUpDuration" / construct.Bytes(6),
                    "_72AWakeUpRepeatInterval" / construct.Bytes(6),
                    "_72AWakeUpNumberOfIntervals" / construct.Bytes(2),
                    "Reserved6" / construct.Bytes(484),
                    "Reserved7" / construct.Bytes(448),
                    "ImplementTime" / construct.Bytes(16),
                    )
    return OM


class OM(object):
    __keys__ = (
        "BIN.PacketHeader", "_72APowerState", "RecordingMode", "Reserved1",
        "AutoDumpOnET",
        "Reserved2", "AutoDumpThreshold", "_72APowerDownDelay", "DiskWrap",
        "Reserved3",
        "_72ADiskPower", "_72ATerminatorPower", "DiskRetry", "Reserved4",
        "Reserved5",
        "_72AWakeUpStartTime", "_72AWakeUpDuration",
        "_72AWakeUpRepeatInterval",
        "_72AWakeUpNumberOfIntervals",
        "Reserved6", "Reserved7", "ImplementTime")

    def __init__(self):
        for b in OM.__keys__:
            self.__dict__[b] = 0x00

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable %s in "
                    "filter description packet.\n" %
                    k)

    def get(self):
        try:
            t = operating_mode()
            ret = t.build(self)
        except Exception as e:
            raise CorruptPacketError("OM Packet: " + e.message)

        return ret

    def parse(self, buf):
        try:
            t = operating_mode()
            ret = t.parse(buf)
        except Exception as e:
            raise CorruptPacketError("OM Packet: " + e.message)

        return ret


def main():
    fh = os.open("./RAW/REF/2008_243_16_30_9461.ref", os.O_RDONLY)
    DTcnt = 0
    EHcnt = 0
    SHcnt = 0
    SCcnt = 0
    ADcnt = 0
    CDcnt = 0
    DScnt = 0
    FDcnt = 0
    OMcnt = 0
    while True:
        buf = os.read(fh, 1024)
        if not buf:
            break
        ph = PacketHeader()
        ret = ph.decode(buf)
        if ret.type == 'DT':
            DTcnt += 1
            dt = DT()
            c = dt.decode(buf)
        elif ret.type == 'EH' or ret.type == 'ET':
            EHcnt += 1
            eh = EH()
            c = eh.parse(buf)
            print c
        elif ret.type == 'SH':
            SHcnt += 1
            sh = SH()
            c = sh.parse(buf)
            print SHcnt
        elif ret.type == 'SC':
            SCcnt += 1
            sc = SC()
            c = sc.parse(buf)
            print c
        elif ret.type == 'AD':
            ADcnt += 1
            ad = AD()
            c = ad.parse(buf)
            print c
        elif ret.type == 'CD':
            CDcnt += 1
            cd = CD()
            c = cd.parse(buf)
            print c
        elif ret.type == 'DS':
            DScnt += 1
            ds = DS()
            c = ds.parse(buf)
            print c
        elif ret.type == 'FD':
            FDcnt += 1
            fd = FD()
            c = fd.parse(buf)
            print c
        elif ret.type == 'OM':
            OMcnt += 1
            om = OM()
            c = om.parse(buf)
            print c

    print "DT: %d EH: %d SH: %d SC: %d AD: %d CD: %d DS: %d FD: %d OM: %d\n"\
          % (
              DTcnt,
              EHcnt,
              SHcnt,
              SCcnt,
              ADcnt,
              CDcnt,
              DScnt,
              FDcnt,
              OMcnt)


if __name__ == '__main__':
    main()
