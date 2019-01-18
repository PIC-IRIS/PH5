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

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)

ver = construct.version[0] + construct.version[1] / 10.
if ver < 2.5:
    LOGGER.info("Exiting: construct version is {0}\n".format(ver))
    sys.exit()


def __version__():
    print PROG_VERSION


def pfloat():
    PFLOAT = construct.Struct("PFLOAT",
                              construct.BFloat32("x"))
    return PFLOAT


def puint():
    PINT = construct.Struct("PINT",
                            construct.UBInt32("x"))
    return PINT


def psint():
    PINT = construct.Struct("PINT",
                            construct.SBInt32("x"))
    return PINT


def psshort():
    PSHORT = construct.Struct("PSHORT",
                              construct.SBInt16("x"))
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
    PH = construct.BitStruct("PH",
                             construct.BitField("PacketType", 16),
                             construct.BitField("ExperimentNumber", 8),
                             construct.BitField("Year", 8),
                             construct.BitField("UnitIDNumber", 16),
                             construct.BitField("DOY", 12),
                             construct.BitField("HH", 8),
                             construct.BitField("MM", 8),
                             construct.BitField("SS", 8),
                             construct.BitField("TTT", 12),
                             construct.BitField("ByteCount", 16),
                             construct.BitField("PacketSequence", 16))
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
    DT = construct.BitStruct("DT",
                             construct.BitField("PacketHeader", 128),
                             construct.BitField("EventNumber", 16),
                             construct.BitField("DataStream", 8),
                             construct.BitField("Channel", 8),
                             construct.BitField("Samples", 16),
                             # construct.BitField ("Flags", 8),
                             construct.Flag("Calibration"),
                             construct.Flag("Overscaled"),
                             construct.Flag("StackedData"),
                             construct.BitField("Unused", 2),
                             construct.Flag("Second_EH_ET"),
                             construct.Flag("LastDataPacket"),
                             construct.Flag("FirstDataPacket"),
                             construct.BitField("DataFormat", 8),
                             construct.BitField("Data", 8000))
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
    EH = construct.Struct("EH",
                          construct.BitStruct("BIN",
                                              construct.BitField(
                                                  "PacketHeader", 128),
                                              construct.BitField(
                                                  "EventNumber", 16),
                                              construct.BitField(
                                                  "DataStream", 8),
                                              construct.BitField(
                                                  "Reserved", 24),
                                              construct.BitField("Flags", 8),
                                              construct.BitField("DataFormat",
                                                                 8)),
                          construct.String("TriggerTimeMessage", 33),
                          construct.String("TimeSource", 1),
                          construct.String("TimeQuality", 1),
                          construct.String("ExtStationName", 1),
                          construct.String("StationName", 4),
                          construct.String("StreamName", 16),
                          construct.String("Reserved1", 8),
                          construct.String("SampleRate", 4),
                          construct.String("TriggerType", 4),
                          construct.String("TriggerTime", 16),
                          construct.String("FirstSampleTime", 16),
                          construct.String("DetriggerTime", 16),
                          construct.String("LastSampleTime", 16),
                          construct.String("NominalBitWeight", 128),
                          construct.String("TrueBitWeight", 128),
                          construct.String("Gain", 16),
                          construct.String("A_DResolution", 16),
                          construct.String("FullScaleAnalog", 16),
                          construct.String("ChannelCode", 64),
                          construct.String("SensorFSA", 16),
                          construct.String("SensorVPU", 96),
                          construct.String("SensorUnits", 16),
                          construct.String("StationNumber", 48),
                          construct.String("Reserved2", 156),
                          construct.String("TotalChannels", 2),
                          construct.String("Comment", 40),
                          construct.String("FilterList", 16),
                          construct.String("Position", 26),
                          construct.String("RefTek120", 80))
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
    SH = construct.Struct("SH",
                          construct.BitStruct("BIN",
                                              construct.BitField(
                                                  "PacketHeader", 128)),
                          construct.String("Reserved", 8),
                          construct.String("Information", 1000))
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
#


def station_channel():
    SC = construct.Struct("SC",
                          construct.BitStruct("BIN",
                                              construct.BitField(
                                                  "PacketHeader", 128)),
                          construct.String("ExperimentNumber", 2),
                          construct.String("ExperimentName", 24),
                          construct.String("ExperimentComment", 40),
                          construct.String("StationNumber", 4),
                          construct.String("StationName", 24),
                          construct.String("StationComment", 40),
                          construct.String("DASModel", 12),
                          construct.String("DASSerial", 12),
                          construct.String("ExperimentStart", 14),
                          construct.String("TimeClockType", 4),
                          construct.String("TimeClockSN", 10),
                          construct.Struct("ChanInfo1",
                                           construct.String("Channel", 2),
                                           construct.String("ChannelName", 10),
                                           construct.String("Azimuth", 10),
                                           construct.String("Inclination", 10),
                                           construct.String("XCoordinate", 10),
                                           construct.String("YCoordinate", 10),
                                           construct.String("ZCoordinate", 10),
                                           construct.String("XYUnits", 4),
                                           construct.String("ZUnits", 4),
                                           construct.String("PreampGain", 4),
                                           construct.String("SensorModel", 12),
                                           construct.String(
                                               "SensorSerial", 12),
                                           construct.String("Comments", 40),
                                           construct.String(
                                               "AdjustedNominalBitWeight", 8)),
                          construct.Struct("ChanInfo2",
                                           construct.String("Channel", 2),
                                           construct.String("ChannelName", 10),
                                           construct.String("Azimuth", 10),
                                           construct.String("Inclination", 10),
                                           construct.String("XCoordinate", 10),
                                           construct.String("YCoordinate", 10),
                                           construct.String("ZCoordinate", 10),
                                           construct.String("XYUnits", 4),
                                           construct.String("ZUnits", 4),
                                           construct.String("PreampGain", 4),
                                           construct.String("SensorModel", 12),
                                           construct.String(
                                               "SensorSerial", 12),
                                           construct.String("Comments", 40),
                                           construct.String(
                                               "AdjustedNominalBitWeight", 8)),
                          construct.Struct("ChanInfo3",
                                           construct.String("Channel", 2),
                                           construct.String("ChannelName", 10),
                                           construct.String("Azimuth", 10),
                                           construct.String("Inclination", 10),
                                           construct.String("XCoordinate", 10),
                                           construct.String("YCoordinate", 10),
                                           construct.String("ZCoordinate", 10),
                                           construct.String("XYUnits", 4),
                                           construct.String("ZUnits", 4),
                                           construct.String("PreampGain", 4),
                                           construct.String("SensorModel", 12),
                                           construct.String(
                                               "SensorSerial", 12),
                                           construct.String("Comments", 40),
                                           construct.String(
                                               "AdjustedNominalBitWeight", 8)),
                          construct.Struct("ChanInfo4",
                                           construct.String("Channel", 2),
                                           construct.String("ChannelName", 10),
                                           construct.String("Azimuth", 10),
                                           construct.String("Inclination", 10),
                                           construct.String("XCoordinate", 10),
                                           construct.String("YCoordinate", 10),
                                           construct.String("ZCoordinate", 10),
                                           construct.String("XYUnits", 4),
                                           construct.String("ZUnits", 4),
                                           construct.String("PreampGain", 4),
                                           construct.String("SensorModel", 12),
                                           construct.String(
                                               "SensorSerial", 12),
                                           construct.String("Comments", 40),
                                           construct.String(
                                               "AdjustedNominalBitWeight", 8)),
                          construct.Struct("ChanInfo5",
                                           construct.String("Channel", 2),
                                           construct.String("ChannelName", 10),
                                           construct.String("Azimuth", 10),
                                           construct.String("Inclination", 10),
                                           construct.String("XCoordinate", 10),
                                           construct.String("YCoordinate", 10),
                                           construct.String("ZCoordinate", 10),
                                           construct.String("XYUnits", 4),
                                           construct.String("ZUnits", 4),
                                           construct.String("PreampGain", 4),
                                           construct.String("SensorModel", 12),
                                           construct.String(
                                               "SensorSerial", 12),
                                           construct.String("Comments", 40),
                                           construct.String(
                                               "AdjustedNominalBitWeight", 8)),
                          construct.String("Reserved", 76),
                          construct.String("ImplementTime", 16))
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
    AD = construct.Struct("AD",
                          construct.BitStruct("BIN",
                                              construct.BitField(
                                                  "PacketHeader", 128)),
                          construct.String("Marker", 2),
                          construct.String("Channels", 16),
                          construct.String("SamplePeriod", 8),
                          construct.String("DataFormat", 2),
                          construct.String("RecordLength", 8),
                          construct.String("RecordingDestination", 4),
                          construct.String("Reserved", 950),
                          construct.String("ImplementTime", 16))
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
    CD = construct.Struct("CD",
                          construct.BitStruct("BIN",
                                              construct.BitField(
                                                  "PacketHeader", 128)),
                          construct.Struct("_72ACalibration",
                                           construct.String("StartTime", 14),
                                           construct.String(
                                               "RepeatInterval", 8),
                                           construct.String("Intervals", 4),
                                           construct.String("Length", 8),
                                           construct.String("StepOnOff", 4),
                                           construct.String("StepPeriod", 8),
                                           construct.String("StepSize", 8),
                                           construct.String(
                                               "StepAmplitude", 8),
                                           construct.String("StepOutput", 4),
                                           construct.String("Reserved", 48)),
                          construct.Struct("_130AutoCenter1",
                                           construct.String("Sensor", 1),
                                           construct.String("Enable", 1),
                                           construct.String(
                                               "ReadingInterval", 4),
                                           construct.String(
                                               "CycleInterval", 2),
                                           construct.String("Level", 4),
                                           construct.String("Attempts", 2),
                                           construct.String("AttemptInterval",
                                                            2)),
                          construct.Struct("_130AutoCenter2",
                                           construct.String("Sensor", 1),
                                           construct.String("Enable", 1),
                                           construct.String(
                                               "ReadingInterval", 4),
                                           construct.String(
                                               "CycleInterval", 2),
                                           construct.String("Level", 4),
                                           construct.String("Attempts", 2),
                                           construct.String("AttemptInterval",
                                                            2)),
                          construct.Struct("_130AutoCenter3",
                                           construct.String("Sensor", 1),
                                           construct.String("Enable", 1),
                                           construct.String(
                                               "ReadingInterval", 4),
                                           construct.String(
                                               "CycleInterval", 2),
                                           construct.String("Level", 4),
                                           construct.String("Attempts", 2),
                                           construct.String("AttemptInterval",
                                                            2)),
                          construct.Struct("_130AutoCenter4",
                                           construct.String("Sensor", 1),
                                           construct.String("Enable", 1),
                                           construct.String(
                                               "ReadingInterval", 4),
                                           construct.String(
                                               "CycleInterval", 2),
                                           construct.String("Level", 4),
                                           construct.String("Attempts", 2),
                                           construct.String("AttemptInterval",
                                                            2)),
                          construct.Struct("_130Calibration1",
                                           construct.String("Sensor", 1),
                                           construct.String("Enable", 1),
                                           construct.String("Reserved", 2),
                                           construct.String("Duration", 4),
                                           construct.String("Amplitude", 4),
                                           construct.String("Signal", 4),
                                           construct.String("StepInterval", 4),
                                           construct.String("StepWidth", 4),
                                           construct.String("SineFrequency",
                                                            4)),
                          construct.Struct("_130Calibration2",
                                           construct.String("Sensor", 1),
                                           construct.String("Enable", 1),
                                           construct.String("Reserved", 2),
                                           construct.String("Duration", 4),
                                           construct.String("Amplitude", 4),
                                           construct.String("Signal", 4),
                                           construct.String("StepInterval", 4),
                                           construct.String("StepWidth", 4),
                                           construct.String("SineFrequency",
                                                            4)),
                          construct.Struct("_130Calibration3",
                                           construct.String("Sensor", 1),
                                           construct.String("Enable", 1),
                                           construct.String("Reserved", 2),
                                           construct.String("Duration", 4),
                                           construct.String("Amplitude", 4),
                                           construct.String("Signal", 4),
                                           construct.String("StepInterval", 4),
                                           construct.String("StepWidth", 4),
                                           construct.String("SineFrequency",
                                                            4)),
                          construct.Struct("_130Calibration4",
                                           construct.String("Sensor", 1),
                                           construct.String("Enable", 1),
                                           construct.String("Reserved", 2),
                                           construct.String("Duration", 4),
                                           construct.String("Amplitude", 4),
                                           construct.String("Signal", 4),
                                           construct.String("StepInterval", 4),
                                           construct.String("StepWidth", 4),
                                           construct.String("SineFrequency",
                                                            4)),
                          construct.Struct("_130CalibrationSequence1",
                                           construct.String("Sequence", 1),
                                           construct.String("Enable", 1),
                                           construct.String("Reserved1", 2),
                                           construct.String("StartTime", 14),
                                           construct.String("Interval", 8),
                                           construct.String("Count", 2),
                                           construct.String("RecordLength", 8),
                                           construct.String("Reserved2", 22)),
                          construct.Struct("_130CalibrationSequence2",
                                           construct.String("Sequence", 1),
                                           construct.String("Enable", 1),
                                           construct.String("Reserved1", 2),
                                           construct.String("StartTime", 14),
                                           construct.String("Interval", 8),
                                           construct.String("Count", 2),
                                           construct.String("RecordLength", 8),
                                           construct.String("Reserved2", 22)),
                          construct.Struct("_130CalibrationSequence3",
                                           construct.String("Sequence", 1),
                                           construct.String("Enable", 1),
                                           construct.String("Reserved1", 2),
                                           construct.String("StartTime", 14),
                                           construct.String("Interval", 8),
                                           construct.String("Count", 2),
                                           construct.String("RecordLength", 8),
                                           construct.String("Reserved2", 22)),
                          construct.Struct("_130CalibrationSequence4",
                                           construct.String("Sequence", 1),
                                           construct.String("Enable", 1),
                                           construct.String("Reserved1", 2),
                                           construct.String("StartTime", 14),
                                           construct.String("Interval", 8),
                                           construct.String("Count", 2),
                                           construct.String("RecordLength", 8),
                                           construct.String("Reserved2", 22)),
                          construct.String("Reserved", 470),
                          construct.String("ImplementTime", 16))
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
    DS = construct.Struct("DS",
                          construct.BitStruct("BIN",
                                              construct.BitField(
                                                  "PacketHeader", 128)),
                          construct.String("DataStreamInfo", 920),
                          construct.String("Reserved", 72),
                          construct.String("ImplementTime", 16))
    return DS


def data_stream_info():
    DSI = construct.Struct("DSI",
                           construct.Struct("Info1",
                                            construct.String("DataStream", 2),
                                            construct.String(
                                                "DataStreamName", 16),
                                            construct.String(
                                                "RecordingDestination", 4),
                                            construct.String("Reserved", 4),
                                            construct.String(
                                                "ChannelsIncluded", 16),
                                            construct.String("SampleRate", 4),
                                            construct.String("DataFormat", 2),
                                            construct.String("Reserved1", 16),
                                            construct.String("TriggerType", 4),
                                            construct.String(
                                                "TriggerDescription", 162)),
                           construct.Struct("Info2",
                                            construct.String("DataStream", 2),
                                            construct.String(
                                                "DataStreamName", 16),
                                            construct.String(
                                                "RecordingDestination", 4),
                                            construct.String("Reserved", 4),
                                            construct.String(
                                                "ChannelsIncluded", 16),
                                            construct.String("SampleRate", 4),
                                            construct.String("DataFormat", 2),
                                            construct.String("Reserved1", 16),
                                            construct.String("TriggerType", 4),
                                            construct.String(
                                                "TriggerDescription", 162)),
                           construct.Struct("Info3",
                                            construct.String("DataStream", 2),
                                            construct.String(
                                                "DataStreamName", 16),
                                            construct.String(
                                                "RecordingDestination", 4),
                                            construct.String("Reserved", 4),
                                            construct.String(
                                                "ChannelsIncluded", 16),
                                            construct.String("SampleRate", 4),
                                            construct.String("DataFormat", 2),
                                            construct.String("Reserved1", 16),
                                            construct.String("TriggerType", 4),
                                            construct.String(
                                                "TriggerDescription", 162)),
                           construct.Struct("Info4",
                                            construct.String("DataStream", 2),
                                            construct.String(
                                                "DataStreamName", 16),
                                            construct.String(
                                                "RecordingDestination", 4),
                                            construct.String("Reserved", 4),
                                            construct.String(
                                                "ChannelsIncluded", 16),
                                            construct.String("SampleRate", 4),
                                            construct.String("DataFormat", 2),
                                            construct.String("Reserved1", 16),
                                            construct.String("TriggerType", 4),
                                            construct.String(
                                                "TriggerDescription", 162)))
    return DSI


def continuous_trigger():
    CON = construct.Struct("CON",
                           construct.String("RecordLength", 8),
                           construct.String("StartTime", 14),
                           construct.String("Reserved", 140))
    return CON


def cross_stream_trigger():
    CRS = construct.Struct("CRS",
                           construct.String("TriggerStreamNo", 2),
                           construct.String("PretriggerLength", 8),
                           construct.String("RecordLength", 8),
                           construct.String("Reserved", 144))
    return CRS


def event_trigger():
    EVT = construct.Struct("EVT",
                           construct.String("TriggerChannels", 16),
                           construct.String("MinimumChannels", 2),
                           construct.String("TriggerWindow", 8),
                           construct.String("PretriggerLength", 8),
                           construct.String("PosttriggerLength", 8),
                           construct.String("RecordLength", 8),
                           construct.String("Reserved1", 8),
                           construct.String("STALength", 8),
                           construct.String("LTALength", 8),
                           construct.String("MeanRemoval", 8),
                           construct.String("TriggerRatio", 8),
                           construct.String("DetriggerRatio", 8),
                           construct.String("LTAHold", 4),
                           construct.String("LowPassCornerFreq", 4),
                           construct.String("HighPassCornerFreq", 4),
                           construct.String("Reserved2", 52))
    return EVT


def external_trigger():
    EXT = construct.Struct("EXT",
                           construct.String("PretriggerLength", 8),
                           construct.String("RecordLength", 8),
                           construct.String("Reserved", 146))
    return EXT


def level_trigger():
    LEV = construct.Struct("LEV",
                           construct.String("Level", 8),
                           construct.String("PretriggerLength", 8),
                           construct.String("RecordLength", 8),
                           construct.String("LowPassCornerFreq", 4),
                           construct.String("HighPassCornerFreq", 4),
                           construct.String("Reserved", 130))
    return LEV


def time_trigger():
    TIM = construct.Struct("TIM",
                           construct.String("StartTime", 14),
                           construct.String("RepeatInterval", 8),
                           construct.String("Intervals", 4),
                           construct.String("Reserved1", 8),
                           construct.String("RecordLength", 8),
                           construct.String("Reserved2", 120))
    return TIM


def time_list_trigger():
    TML = construct.Struct("TML",
                           construct.String("StartTime01", 14),
                           construct.String("StartTime02", 14),
                           construct.String("StartTime03", 14),
                           construct.String("StartTime04", 14),
                           construct.String("StartTime05", 14),
                           construct.String("StartTime06", 14),
                           construct.String("StartTime07", 14),
                           construct.String("StartTime08", 14),
                           construct.String("StartTime09", 14),
                           construct.String("StartTime10", 14),
                           construct.String("StartTime11", 14),
                           construct.String("RecordLength", 8))
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
    FD = construct.Struct("FD",
                          construct.BitStruct("BIN",
                                              construct.BitField(
                                                  "PacketHeader", 128),
                                              construct.String("FilterInfo",
                                                               992)),
                          construct.String("ImplementTime", 16))
    return FD


def filter_info():
    FI = construct.Struct("FI",
                          construct.UBInt8("FilterBlockCount"),
                          construct.String("FilterID", 1),
                          construct.UBInt8("FilterDecimation"),
                          construct.UBInt8("FilterScaler"),
                          construct.UBInt8("FilterCoefficientCount"),
                          construct.UBInt8("PacketCoefficientCount"),
                          construct.UBInt8("CoefficientPacketCount"),
                          construct.UBInt8("CoefficientFormat"))
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
    OM = construct.Struct("OM",
                          construct.BitStruct("BIN",
                                              construct.BitField(
                                                  "PacketHeader", 128)),
                          construct.String("_72APowerState", 2),
                          construct.String("RecordingMode", 2),
                          construct.String("Reserved1", 4),
                          construct.String("AutoDumpOnET", 1),
                          construct.String("Reserved2", 1),
                          construct.String("AutoDumpThreshold", 2),
                          construct.String("_72APowerDownDelay", 4),
                          construct.String("DiskWrap", 1),
                          construct.String("Reserved3", 1),
                          construct.String("_72ADiskPower", 1),
                          construct.String("_72ATerminatorPower", 1),
                          construct.String("DiskRetry", 1),
                          construct.String("Reserved4", 11),
                          construct.String("Reserved5", 2),
                          construct.String("_72AWakeUpStartTime", 12),
                          construct.String("_72AWakeUpDuration", 6),
                          construct.String("_72AWakeUpRepeatInterval", 6),
                          construct.String("_72AWakeUpNumberOfIntervals", 2),
                          construct.String("Reserved6", 484),
                          construct.String("Reserved7", 448),
                          construct.String("ImplementTime", 16))
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
