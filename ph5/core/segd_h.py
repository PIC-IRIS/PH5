#!/usr/bin/env pnpython3
#
# A low level SEG-D library
# Fairfield SEG-D version 1.6
# Fairfield SEG-D ZSystem 2.1 (In development July 2016)
#
# Steve Azevedo, April 2014
#

import exceptions
import sys
import construct
import bcd_py

PROG_VERSION = '2016.287 Developmental'


def __version__():
    print PROG_VERSION


class HeaderError (exceptions.Exception):
    def __init__(self, args=None):
        self.args = args

#
# 1.6 and 2.1
#


def storage_unit_label():
    BIN = construct.Struct("BIN",
                           construct.String("storage_unit_sequence_number", 4),
                           construct.String("fairfield_revision", 5),
                           construct.String("storage_unit_structure", 6),
                           construct.String("binding_edition", 4),
                           construct.String("max_block_size", 10),
                           construct.String("api_producer_code", 10),
                           construct.String("creation_date", 11),
                           construct.String("serial_number", 12),
                           construct.String("reserved01", 6),
                           construct.String("external_label_name", 12),
                           construct.String("recording_entity_name", 24),
                           construct.String("user_defined", 14),
                           construct.String("max_file_size_MB", 10))
    return BIN


class Storage_unit_label (object):
    __keys__ = ("storage_unit_sequence_number",
                # "FF1.6" => Fairfield 1.6, "2.1" => ZLand SEG-D 2.1
                "fairfield_revision",
                "storage_unit_structure",
                "binding_edition",
                "max_block_size",
                "api_producer_code",
                "creation_date",
                "serial_number",
                "reserved01",
                "external_label_name",
                "recording_entity_name",
                "user_defined",
                "max_file_size_MB")

    def __init__(self):
        for c in Storage_unit_label.__keys__:
            self.__dict__[c] = ''

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
        t = storage_unit_label()

        return t.build(self)

    def parse(self, buf):
        t = storage_unit_label()

        return t.parse(buf)
#
###
#


def swap_block_bits():
    B = construct.BitStruct("BIN",
                            construct.BitField('A', 256, swapped=True))

    L = construct.BitStruct("BIN",
                            construct.BitField('A', 256))

    return B, L


def swap_block_64():
    B = construct.Struct("BIN",
                         construct.UBInt64('A'),
                         construct.UBInt64('B'),
                         construct.UBInt64('C'),
                         construct.UBInt64('D')
                         )
    L = construct.Struct("BIN",
                         construct.ULInt64('A'),
                         construct.ULInt64('B'),
                         construct.ULInt64('C'),
                         construct.ULInt64('D')
                         )

    return B, L


def swap_block_32():
    B = construct.Struct("BIN",
                         construct.UBInt32('A'),
                         construct.UBInt32('B'),
                         construct.UBInt32('C'),
                         construct.UBInt32('D'),
                         construct.UBInt32('E'),
                         construct.UBInt32('F'),
                         construct.UBInt32('G'),
                         construct.UBInt32('H')
                         )
    L = construct.Struct("BIN",
                         construct.ULInt32('A'),
                         construct.ULInt32('B'),
                         construct.ULInt32('C'),
                         construct.ULInt32('D'),
                         construct.ULInt32('E'),
                         construct.ULInt32('F'),
                         construct.ULInt32('G'),
                         construct.ULInt32('H')
                         )

    return B, L


def swap_block_16():
    B = construct.Struct("BIN",
                         construct.UBInt16('A'),
                         construct.UBInt16('B'),
                         construct.UBInt16('C'),
                         construct.UBInt16('D'),
                         construct.UBInt16('E'),
                         construct.UBInt16('F'),
                         construct.UBInt16('G'),
                         construct.UBInt16('H'),
                         construct.UBInt16('I'),
                         construct.UBInt16('J'),
                         construct.UBInt16('K'),
                         construct.UBInt16('L'),
                         construct.UBInt16('M'),
                         construct.UBInt16('N'),
                         construct.UBInt16('O'),
                         construct.UBInt16('P')
                         )
    L = construct.Struct("BIN",
                         construct.ULInt16('A'),
                         construct.ULInt16('B'),
                         construct.ULInt16('C'),
                         construct.ULInt16('D'),
                         construct.ULInt16('E'),
                         construct.ULInt16('F'),
                         construct.ULInt16('G'),
                         construct.ULInt16('H'),
                         construct.ULInt16('I'),
                         construct.ULInt16('J'),
                         construct.ULInt16('K'),
                         construct.ULInt16('L'),
                         construct.ULInt16('M'),
                         construct.ULInt16('N'),
                         construct.ULInt16('O'),
                         construct.ULInt16('P')
                         )

    return B, L
#
# 1.6, 2.1
#


def general_header_block_1():
    swap = True
    if sys.byteorder == 'big':
        swap = False

    BIN = construct.BitStruct("BIN",
                              #
                              construct.BitField(
                                  "file_number", 16, swapped=swap),
                              # 8058 is IEEE 32 bit float
                              construct.BitField(
                                  "data_sample_format_code", 16, swapped=swap),
                              construct.BitField(
                                  "general_constant_1", 8, swapped=swap),
                              construct.BitField(
                                  "general_constant_2", 8, swapped=swap),
                              construct.BitField(
                                  "general_constant_3", 8, swapped=swap),
                              construct.BitField(
                                  "general_constant_4", 8, swapped=swap),
                              construct.BitField(
                                  "general_constant_5", 8, swapped=swap),
                              construct.BitField(
                                  "general_constant_6", 8, swapped=swap),
                              construct.BitField(
                                  "first_shot_point_year", 8, swapped=swap),
                              construct.BitField(
                                  "number_additional_general_header_blocks",
                                  4,
                                  swapped=swap),
                              construct.BitField(
                                  "first_shot_point_doy", 12, swapped=swap),
                              construct.BitField(
                                  "first_shot_point_time_utc",
                                  24,
                                  swapped=swap),
                              # 20 is Fairfield
                              construct.BitField(
                                  "manufactures_code", 8, swapped=swap),
                              construct.BitField(
                                  "manufactures_sn", 16, swapped=swap),
                              # Traces written in superblocks. 0=No, 1=Yes
                              construct.BitField(
                                  "super_blocks", 8, swapped=swap),
                              construct.BitField("user01", 16, swapped=swap),
                              # Sample interval in 1/16 msec
                              construct.BitField(
                                  "base_scan_interval", 8, swapped=swap),
                              construct.BitField(
                                  "polarity_code", 4, swapped=swap),
                              construct.BitField("user02", 12, swapped=swap),
                              construct.BitField(
                                  "record_type", 4, swapped=swap),
                              # From time zero, 0.5 X 1.024 seconds, if 0xFFF
                              # look in general header block 2
                              construct.BitField(
                                  "record_length", 12, swapped=swap),
                              construct.BitField(
                                  "scan_types_per_record", 8, swapped=swap),
                              # 0xFF look in general header block 2
                              construct.BitField(
                                  "chan_sets_per_scan", 8, swapped=swap),
                              construct.BitField(
                                  "number_skew_blocks", 8, swapped=swap),
                              # 0xFF look in general header block 2
                              construct.BitField(
                                  "number_extended_header_blocks",
                                  8,
                                  swapped=swap),
                              # 0xFF look in general header block 2
                              construct.BitField(
                                  "number_external_header_blocks",
                                  8,
                                  swapped=swap))

    return BIN


class General_header_block_1 (object):
    __keys__ = ("file_number",  # FFFF
                "data_sample_format_code",
                "general_constant_1",
                "general_constant_2",
                "general_constant_3",
                "general_constant_4",
                "general_constant_5",
                "general_constant_6",
                "first_shot_point_year",
                "number_additional_general_header_blocks",
                "first_shot_point_doy",
                "first_shot_point_time_utc",
                "manufactures_code",
                "manufactures_sn",
                "super_blocks",
                "user01",
                "base_scan_interval",
                "polarity_code",
                "user02",
                "record_type",
                "record_length",
                "scan_types_per_record",
                "chan_sets_per_scan",
                "number_skew_blocks",
                "number_extended_header_blocks",
                "number_external_header_blocks")

    NIBBLES = {"file_number": 4,
               "data_sample_format_code": 4,
               "general_constant_1": 2,
               "general_constant_2": 2,
               "general_constant_3": 2,
               "general_constant_4": 2,
               "general_constant_5": 2,
               "general_constant_6": 2,
               "first_shot_point_year": 2,
               "number_additional_general_header_blocks": 1,
               "first_shot_point_doy": 3,
               "first_shot_point_time_utc": 6,
               "manufactures_code": 2,
               "manufactures_sn": 4,
               "super_blocks": 2,
               "user01": 4,
               "base_scan_interval": 2,
               "polarity_code": 1,
               "user02": 3,
               "record_type": 1,
               "record_length": 3,
               "scan_types_per_record": 2,
               "chan_sets_per_scan": 2,
               "number_skew_blocks": 2,
               "number_extended_header_blocks": 2,
               "number_external_header_blocks": 2}

    BCD = ("file_number",
           "data_sample_format_code",
           "general_constant_1",
           "general_constant_2",
           "general_constant_3",
           "general_constant_4",
           "general_constant_5",
           "general_constant_6",
           "first_shot_point_year",
           "first_shot_point_doy",
           "first_shot_point_time_utc",
           "manufactures_code",
           "manufactures_sn",
           "super_blocks",
           "user01",
           "record_length",
           "scan_types_per_record",
           "chan_sets_per_scan",
           "number_skew_blocks",
           "number_extended_header_blocks",
           "number_external_header_blocks")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in General_header_block_1.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = general_header_block_1()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = general_header_block_1()
        else:
            raise HeaderError("Little endian byte order not supported.")
        # Convert BCD fields
        parsed = t.parse(buf)
        ret = convert_bcd_fields(parsed,
                                 General_header_block_1.BCD,
                                 General_header_block_1.NIBBLES)
        return ret

#
# 1.6, 2.1
#


def general_header_block_2():
    swap = False
    if sys.byteorder == 'big':
        swap = False

    BIN = construct.BitStruct("BIN",
                              construct.BitField(
                                  "extended_file_number", 24, swapped=swap),
                              construct.BitField(
                                  "extended_chan_sets_per_scan_type",
                                  16,
                                  swapped=swap),
                              construct.BitField(
                                  "extended_header_blocks", 16, swapped=swap),
                              # External header blocks is 3 bytes in Fairfield
                              # 1.6. Append user01.
                              construct.BitField(
                                  "external_header_blocks", 24, swapped=swap),
                              # construct.BitField ("user01", 8, swapped=swap),
                              # 0x0106, or 0x0201
                              construct.BitField(
                                  "file_version_number", 16, swapped=swap),
                              construct.BitField(
                                  "number_general_trailer_blocks",
                                  16,
                                  swapped=swap),
                              # Record length in milliseconds
                              construct.BitField(
                                  "extended_record_length", 24, swapped=swap),
                              construct.BitField("user02", 8, swapped=swap),
                              construct.BitField(
                                  "general_header_block_number",
                                  8,
                                  swapped=swap),
                              construct.BitField("user03", 8, swapped=swap),
                              # 2.1
                              construct.BitField(
                                  "sequence_number", 16, swapped=swap),
                              # 2.1
                              construct.BitField(
                                  "super_block_size", 32, swapped=swap),
                              construct.BitField("user04", 32, swapped=swap),
                              # 2.1
                              construct.BitField("zsystem_revision_number",
                                                 16,
                                                 swapped=swap))

    return BIN


class General_header_block_2 (object):
    __keys__ = ("extended_file_number",
                "extended_chan_sets_per_scan_type",
                "extended_header_blocks",
                "external_header_blocks",
                "user01",
                "file_version_number",
                "number_general_trailer_blocks",
                "extended_record_length",
                "user02",
                "general_header_block_number",
                "user03",
                "sequence_number",
                "super_block_size",
                "user04",
                "zsystem_revision_number")

    NIBBLES = {"extended_file_number": 6,
               "extended_chan_sets_per_scan_type": 4,
               "extended_header_blocks": 4,
               "external_header_blocks": 4,
               "user01": 2,
               "file_version_number": 4,
               "number_general_trailer_blocks": 4,
               "extended_record_length": 6,
               "user02": 2,
               "general_header_block_number": 2,
               "user03": 2,
               "sequence_number": 4,
               "super_block_size": 8,
               "user04": 8,
               "zsystem_revision_number": 4}

    def __init__(self, endian='big'):
        self.endian = endian
        for c in General_header_block_2.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = general_header_block_2()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = general_header_block_2()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)

#
# 2.1
#


def general_header_block_3():
    swap = False
    if sys.byteorder == 'big':
        swap = False

    BIN = construct.BitStruct("BIN",
                              construct.BitField(
                                  "extended_file_number", 24, swapped=swap),
                              construct.BitField(
                                  "source_line_number_int", 24, swapped=swap),
                              construct.BitField(
                                  "source_line_number_frac", 16, swapped=swap),
                              construct.BitField(
                                  "source_point_number_int", 24, swapped=swap),
                              construct.BitField(
                                  "source_point_number_frac",
                                  16,
                                  swapped=swap),
                              construct.BitField(
                                  "source_point_index", 8, swapped=swap),
                              construct.BitField(
                                  "phase_control", 8, swapped=swap),
                              construct.BitField(
                                  "vibrator_type", 8, swapped=swap),
                              construct.BitField(
                                  "phase_angle", 16, swapped=swap),
                              construct.BitField(
                                  "general_header_block_number",
                                  8,
                                  swapped=swap),
                              construct.BitField(
                                  "source_set_number", 8, swapped=swap),
                              construct.BitField("user01", 96, swapped=swap))

    return BIN


class General_header_block_3 (object):
    __keys__ = ("extended_file_number",
                "source_line_number_int",
                "source_line_number_frac",
                "source_point_number_int",
                "source_point_number_frac",
                "source_point_index",
                "phase_control",
                "vibrator_type",
                "phase_angle",
                "general_header_block_number",
                "source_set_number",
                "user01")

    NIBBLES = {"extended_file_number": 6,
               "source_line_number_int": 6,
               "source_line_number_frac": 4,
               "source_point_number_int": 6,
               "source_point_number_frac": 4,
               "source_point_index": 2,
               "phase_control": 2,
               "vibrator_type": 2,
               "phase_angle": 4,
               "general_header_block_number": 2,
               "source_set_number": 2,
               "user01": 24}

    def __init__(self, endian='big'):
        self.endian = endian
        for c in General_header_block_3.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = general_header_block_3()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = general_header_block_3()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6, 2.1
#


def channel_set_descriptor():
    swap = True
    if sys.byteorder == 'big':
        swap = False

    BIN = construct.BitStruct("BIN",
                              construct.BitField(
                                  "scan_type_number", 8, swapped=swap),
                              construct.BitField(
                                  "chan_set_number", 8, swapped=swap),
                              # Times 2 is milliseconds
                              construct.BitField(
                                  "chan_set_start_time", 16, swapped=swap),
                              # Times 2 is milliseconds
                              construct.BitField(
                                  "chan_set_end_time", 16, swapped=swap),
                              construct.BitField(
                                  "optional_mp_factor_extension_byte",
                                  8,
                                  swapped=swap),
                              construct.BitField(
                                  "mp_factor_scaler_multiplier",
                                  8,
                                  swapped=swap),
                              construct.BitField(
                                  "number_of_chans_in_chan_set",
                                  16,
                                  swapped=swap),
                              construct.BitField(
                                  "chan_type_code", 4, swapped=swap),
                              construct.BitField("user01", 4, swapped=swap),
                              construct.BitField(
                                  "number_sub-scans", 4, swapped=swap),
                              # 3 is fixed gain
                              construct.BitField(
                                  "gain_control_type", 4, swapped=swap),
                              construct.BitField(
                                  "alias_filter_freq", 16, swapped=swap),
                              construct.BitField(
                                  "alias_filter_slope_db", 16, swapped=swap),
                              construct.BitField(
                                  "low_cut_filter_freq", 16, swapped=swap),
                              construct.BitField(
                                  "low_cut_filter_slope_db", 16, swapped=swap),
                              construct.BitField(
                                  "notch_filter_freq", 16, swapped=swap),
                              construct.BitField(
                                  "second_notch_filter_freq",
                                  16,
                                  swapped=swap),
                              construct.BitField(
                                  "third_notch_filter_freq",
                                  16,
                                  swapped=swap),
                              construct.BitField(
                                  "extended_chan_set_number",
                                  16,
                                  swapped=swap),
                              construct.BitField(
                                  "extended_header_flag", 4, swapped=swap),
                              # Always 10 for Fairfield
                              construct.BitField(
                                  "number_trace_header_extensions",
                                  4,
                                  swapped=swap),
                              construct.BitField(
                                  "vertical_stack_size", 8, swapped=swap),
                              construct.BitField(
                                  "streamer_cable_number", 8, swapped=swap),
                              construct.BitField("array_forming",
                                                 8,
                                                 swapped=swap))
    return BIN


class Channel_set_descriptor (object):
    __keys__ = ("scan_type_number",
                "chan_set_number",
                "chan_set_start_time",
                "chan_set_end_time",
                "optional_mp_factor_extension_byte",
                "mp_factor_scaler_multiplier",
                "number_of_chans_in_chan_set",
                "chan_type_code",
                "user01",
                "number_sub-scans",
                "gain_control_type",
                "alias_filter_freq",
                "alias_filter_slope",
                "alias_filter_slope_db",
                "low_cut_filter_freq",
                "low_cut_filter_slope_db",
                "notch_filter_freq",
                "second_notch_filter_freq",
                "third_notch_filter_freq",
                "extended_chan_set_number",
                "extended_header_flag",
                "number_trace_header_extensions",
                "vertical_stack_size",
                "streamer_cable_number",
                "array_forming")

    NIBBLES = {"scan_type_number": 2,
               "chan_set_number": 2,
               "chan_set_start_time": 4,
               "chan_set_end_time": 4,
               "optional_mp_factor_extension_byte": 2,
               "mp_factor_scaler_multiplier": 2,
               "number_of_chans_in_chan_set": 4,
               "chan_type_code": 1,
               "user01": 1,
               "number_sub-scans": 1,
               "gain_control_type": 1,
               "alias_filter_freq": 4,
               "alias_filter_slope_db": 4,
               "low_cut_filter_freq": 4,
               "low_cut_filter_slope_db": 4,
               "notch_filter_freq": 4,
               "second_notch_filter_freq": 4,
               "third_notch_filter_freq": 4,
               "extended_chan_set_number": 4,
               "extended_header_flag": 1,
               "number_trace_header_extensions": 1,
               "vertical_stack_size": 2,
               "streamer_cable_number": 2,
               "array_forming": 2}

    BCD = ("scan_type_number",
           "chan_set_number",
           "number_of_chans_in_chan_set",
           "number_sub-scans",
           "alias_filter_freq",
           "alias_filter_slope_db",
           "low_cut_filter_freq",
           "low_cut_filter_slope_db",
           "notch_filter_freq",
           "second_notch_filter_freq",
           "third_notch_filter_freq")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Channel_set_descriptor.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = channel_set_descriptor()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = channel_set_descriptor()
        else:
            raise HeaderError("Little endian byte order not supported.")
        # Convert BCD fields
        ret = convert_bcd_fields(t.parse(buf),
                                 Channel_set_descriptor.BCD,
                                 Channel_set_descriptor.NIBBLES)
        return ret


#
# 1.6
#
def extended_header_1():
    BIN = construct.Struct("BIN",
                           # Remote unit
                           construct.UBInt32("part_number"),
                           construct.UBInt32("id_number"),
                           # All epochs in micro-seconds
                           construct.UBInt64("epoch_deploy"),
                           construct.UBInt64("epoch_pickup"),
                           construct.UBInt64("remote_unit_epoch"))
    return BIN


class Extended_header_1 (object):
    __keys__ = ("part_number", "id_number",
                "epoch_deploy",
                "epoch_pickup",
                "remote_unit_epoch")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Extended_header_1.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = extended_header_1()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = extended_header_1()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 2.1
#


def extended_header_1_shot():
    BIN = construct.Struct("BIN",
                           construct.UBInt64("shot_epoch_time"),
                           construct.UBInt32("shot_skew_time"),
                           construct.UBInt16("files_shot_point"),
                           construct.UBInt64("file_index"),
                           construct.UBInt8("user01"),
                           construct.UBInt8("data_decimation_flag"),
                           construct.UBInt16(
                               "number_decimation_filter_coefficients"),
                           construct.UBInt8("base_scan_interval_0"),
                           construct.UBInt32("pre_shot_guard_base"),
                           construct.UBInt32("post_shot_guard_base"),
                           construct.UBInt16("simultaneous_shots"),
                           construct.UBInt8("user02"))
    return BIN


class Extended_header_1_shot (object):
    __keys__ = ("shot_epoch_time",
                "shot_skew_time",
                "files_shot_point",
                "file_index",
                "user01",
                "data_decimation_flag",
                "number_decimation_filter_coefficients",
                "base_scan_interval_0",
                "pre_shot_guard_base",
                "post_shot_guard_base",
                "simultaneous_shots",
                "user02")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Extended_header_1_shot.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = extended_header_1_shot()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = extended_header_1_shot()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6
#


def extended_header_2():
    BIN = construct.Struct("BIN",
                           construct.BFloat32("drift_window"),
                           construct.UBInt64("clock_drift_ns"),
                           # Clock stop method
                           construct.UBInt8("clock_stop_method"),
                           # 0 - normal
                           # 1 - storage full
                           # 2 - power loss
                           # 3 - reboot by command
                           # Frequency drift flag
                           construct.UBInt8("Frequency_drift"),
                           # 0 - not in spec
                           # 1 - in spec
                           # Oscillator type
                           construct.UBInt8("oscillator_type"),
                           # 0 - control board
                           # 1 - atomic
                           # 2 - ovenized
                           # 3 - double ovenized
                           # 4 - disciplined
                           # 0 - normal (shots)
                           construct.UBInt8("collection_method"),
                           # 1 - continuous (fixed time slice)
                           # 2 - shot sliced with guard band
                           # Number of traces
                           construct.UBInt32("number_records"),
                           construct.UBInt32("number_files"),
                           construct.UBInt32("file_number"),
                           # Decimation flag
                           construct.UBInt8("decimation_flag"),
                           # 0 - not decimated
                           # 1 - decimated
                           construct.UBInt8("base_scan_interval"),
                           construct.UBInt16("decimation_filter_coefficients")
                           )
    return BIN


class Extended_header_2 (object):
    __keys__ = ("drift_window",
                "clock_drift_ns",
                "clock_stop_method",
                "Frequency_drift",
                "oscillator_type",
                "collection_method",
                "number_records",
                "number_files",
                "file_number",
                "decimation_flag",
                "base_scan_interval",
                "decimation_filter_coefficients")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Extended_header_2.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = extended_header_2()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = extended_header_2()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 2.1
#


def extended_header_2_test():
    BIN = construct.Struct("BIN",
                           construct.UBInt32("test_analysis_code"),
                           construct.UBInt32(
                               "first_test_oscillator_attenuation"),
                           construct.UBInt32(
                               "second_test_oscillator_attenuation"),
                           construct.UBInt32("start_delay_usec"),
                           # 00 - No filter, 01 - Apply filter
                           construct.UBInt32("dc_filter_flag"),
                           construct.BFloat32("dc_filter_frequency"),
                           # See page 9 of format spec
                           construct.UBInt32("preamp_path"),
                           construct.UBInt32("test_oscillator_signal_type"))
    return BIN


class Extended_header_2_test (object):
    __keys__ = ("test_analysis_code",
                "first_test_oscillator_attenuation",
                "second_test_oscillator_attenuation",
                "start_delay_usec",
                "dc_filter_flag",
                "dc_filter_frequency",
                "preamp_path",
                "test_oscillator_signal_type")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Extended_header_2_test.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = extended_header_2_test()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = extended_header_2_test()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6
#


def extended_header_3():
    swap = True
    if sys.byteorder == 'big':
        swap = False

    BIN = construct.Struct("BIN",
                           construct.UBInt32("line_number"),
                           construct.UBInt32("receiver_point"),
                           construct.UBInt8("point_index"),
                           construct.UBInt32("first_shot_line"),
                           construct.UBInt32("first_shot_point"),
                           construct.UBInt8("first_shot_point_index"),
                           construct.UBInt32("last_shot_line"),
                           construct.UBInt32("last_shot_point"),
                           construct.UBInt8("last_shot_point_index"),
                           construct.BitField("reserved01", 5, swapped=swap)
                           )
    return BIN


class Extended_header_3 (object):
    __keys__ = ("line_number",
                "receiver_point",
                "point_index",
                "first_shot_line",
                "first_shot_point",
                "first_shot_point_index",
                "last_shot_line",
                "last_shot_point",
                "last_shot_point_index",
                "reserved01")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Extended_header_3.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = extended_header_3()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = extended_header_3()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 2.1
#


def extended_header_3_test():
    if sys.byteorder == 'big':
        pass

    BIN = construct.Struct("BIN",
                           construct.UBInt32("test_signal_type"),
                           construct.UBInt32("test_signal_frequency_1"),
                           construct.UBInt32("test_signal_frequency_2"),
                           construct.UBInt32("test_signal_amplitude_1"),
                           construct.UBInt32("test_signal_amplitude_2"),
                           construct.BFloat32("test_signal_duty_cycle"),
                           construct.UBInt32("test_signal_active_duration"),
                           construct.UBInt32("test_signal_active_time")
                           )
    return BIN


class Extended_header_3_test (object):
    __keys__ = ("test_signal_type",
                "test_signal_frequency_1",
                "test_signal_frequency_2",
                "test_signal_amplitude_1",
                "test_signal_amplitude_2",
                "test_signal_duty_cycle",
                "test_signal_active_duration",
                "test_signal_active_time")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Extended_header_3_test.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = extended_header_3_test()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = extended_header_3_test()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6, 2.1 (as extended header 5)
#


def extended_header_4():
    BIN = construct.Struct("BIN",
                           # Decimation filter coefficients
                           construct.BFloat32("coef01"),
                           construct.BFloat32("coef02"),
                           construct.BFloat32("coef03"),
                           construct.BFloat32("coef04"),
                           construct.BFloat32("coef05"),
                           construct.BFloat32("coef06"),
                           construct.BFloat32("coef07"),
                           construct.BFloat32("coef08")
                           )
    return BIN


class Extended_header_4 (object):
    __keys__ = ("coef01",
                "coef02",
                "coef03",
                "coef04",
                "coef05",
                "coef06",
                "coef07",
                "coef08")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Extended_header_4.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = extended_header_4()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = extended_header_4()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 2.1
#


def extended_header_4_test():
    BIN = construct.Struct("BIN",
                           construct.BFloat32("idle_level"),
                           construct.BFloat32("active_level"),
                           construct.BFloat32("pattern_01"),
                           construct.BFloat32("pattern_02"),
                           construct.BFloat32("channel_mask"),
                           construct.BFloat32("user01"),
                           construct.BFloat32("user02"),
                           construct.BFloat32("user03")
                           )
    return BIN


class Extended_header_4_test (object):
    __keys__ = ("idle_level",
                "active_level",
                "pattern_01",
                "pattern_02",
                "channel_mask",
                "user01",
                "user02",
                "user03")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Extended_header_4_test.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = extended_header_4_test()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = extended_header_4_test()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6, 2.1
#


def external_header():
    swap = True
    if sys.byteorder == 'big':
        swap = False

    BIN = construct.Struct("BIN",
                           construct.UBInt32("size"),
                           construct.UBInt32("receiver_line"),
                           construct.UBInt32("receiver_point"),
                           construct.UBInt8("receiver_point_index"),
                           construct.BitField("reserved01", 18, swapped=swap)
                           )
    return BIN


class External_header (object):
    __keys__ = ("size",
                "receiver_line",
                "receiver_point",
                "receiver_point_index",
                "reserved01")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in External_header.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = external_header()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = external_header()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6
#


def external_header_shot():
    BIN = construct.Struct("BIN",
                           construct.UBInt64("shot_epoch"),
                           construct.UBInt32("shot_line"),
                           construct.UBInt32("shot_point"),
                           construct.UBInt8("shot_point_index"),
                           construct.UBInt32("shot_point_X"),
                           construct.UBInt32("shot_point_Y"),
                           construct.UBInt32("shot_point_depth"),
                           construct.UBInt8("shot_info"),  # 0 - Undefined
                           # 1 - preplan
                           # 2 - as shot
                           # 3 - post processed
                           construct.UBInt8("shot_status"),  # 0 - normal
                           # 1 - Bad - operator defined
                           # 2 - Bad Failed T0 QC test
                           construct.UBInt8("reserved01")
                           )
    return BIN


class External_header_shot (object):
    __keys__ = ("shot_epoch",
                "shot_line",
                "shot_point",
                "shot_point_index",
                "shot_point_X",
                "shot_point_Y",
                "shot_point_depth",
                "shot_info",
                "shot_status",
                "reserved01")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in External_header.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = external_header_shot()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = external_header_shot()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 2.1
#


def external_header_shot_blocks():
    BIN = construct.Struct("BIN",
                           construct.UBInt32("shot_line_number"),
                           construct.UBInt32("shot_point_number"),
                           construct.UBInt8("shot_point_index"),
                           construct.UBInt32("shot_point_pre_X"),
                           construct.UBInt32("shot_point_pre_Y"),
                           construct.UBInt32("shot_point_X"),
                           construct.UBInt32("shot_point_Y"),
                           construct.UBInt32("shot_point_depth"),
                           # See format spec ZSystem
                           construct.UBInt8("shot_info_source"),
                           construct.UBInt8("energy_source_type"),
                           construct.UBInt8("shot_status_flag")
                           )
    return BIN


class External_header_shot_blocks (object):
    __keys__ = ()

    def __init__(self, endian='big'):
        self.endian = endian
        for c in External_header.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = external_header_shot_blocks()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = external_header_shot_blocks()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)


def trace_header():
    swap = True
    if sys.byteorder == 'big':
        swap = False

    BIN = construct.BitStruct("BIN",
                              construct.BitField(
                                  "tape_file", 16, swapped=swap),
                              construct.BitField("scan_type", 8, swapped=swap),
                              construct.BitField(
                                  "channel_set", 8, swapped=swap),
                              construct.BitField(
                                  "trace_number", 16, swapped=swap),
                              construct.BitField(
                                  "first_timing_word", 24, swapped=swap),
                              construct.BitField(
                                  "trace_extension_blocks", 8, swapped=swap),
                              construct.BitField(
                                  "sample_skew_value", 8, swapped=swap),
                              construct.BitField(
                                  "trace_edit_code", 8, swapped=swap),
                              construct.BitField(
                                  "time_break_window", 24, swapped=swap),
                              construct.BitField(
                                  "extended_channel_set", 16, swapped=swap),
                              construct.BitField(
                                  "extended_file_number", 24, swapped=swap)
                              )
    return BIN
#
# 1.6, 2.1
#


class Trace_header (object):
    __keys__ = ("tape_file",
                "scan_type",
                "channel_set",
                "trace_number",
                "first_timing_word",
                "trace_extension_blocks",
                "sample_skew_value",
                "trace_edit_code",
                "time_break_window",
                "extended_channel_set",
                "extended_file_number")

    NIBBLES = {"tape_file": 4,
               "scan_type": 2,
               "channel_set": 2,
               "trace_number": 4,
               "first_timing_word": 6,
               "trace_extension_blocks": 2,
               "sample_skew_value": 2,
               "trace_edit_code": 2,
               "time_break_window": 6,
               "extended_channel_set": 4,
               "extended_file_number": 6}

    BCD = ("tape_file",
           "scan_type",
           "channel_set",
           "trace_number",
           "first_timing_word")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = trace_header()
        else:
            raise HeaderError("Little endian byte order not supported.")
        # Convert BCD fields
        ret = convert_bcd_fields(t.parse(buf),
                                 Trace_header.BCD,
                                 Trace_header.NIBBLES)

        return ret
#
# 1.6, 2.1 (trace header #2)
#


def trace_header_1():
    # Don't byte swap
    swap = False
    if sys.byteorder == 'big':
        swap = False

    BIN = construct.BitStruct("BIN",
                              construct.BitField(
                                  "receiver_line", 24, swapped=swap),
                              construct.BitField(
                                  "receiver_point", 24, swapped=swap),
                              construct.BitField(
                                  "receiver_point_index", 8, swapped=swap),
                              construct.BitField(
                                  "samples_per_trace", 24, swapped=swap),
                              construct.BitField(
                                  "extended_receiver_line_number",
                                  40,
                                  swapped=swap),
                              construct.BitField(
                                  "extended_receiver_point_number",
                                  40,
                                  swapped=swap),
                              # 00 - Not defined
                              construct.BitField(
                                  "sensor_type", 8, swapped=swap),
                              # 01 - Hydrophone
                              # 02 - Vertical geophone
                              # 03 - In-line geophone
                              # 04 - Cross-line geophone
                              # 05 - Other horizontal geophone
                              # 06 - Vertical accelerometer
                              # 07 - In-line accelerometer
                              # 08 - Cross-line accelerometer
                              # 09 - Other horizontal accelerometer
                              construct.BitField(
                                  "reserved01", 88, swapped=swap)
                              )
    return BIN


class Trace_header_1 (object):
    __keys__ = ("receiver_line",
                "receiver_point",
                "receiver_point_index",
                "samples_per_trace",
                "extended_receiver_line_number",
                "extended_receiver_point_number",
                "sensor_type",
                "reserved01")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_1.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_1()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_1()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6
#


def trace_header_2():
    BIN = construct.Struct("BIN",
                           construct.UBInt32("shot_line"),
                           construct.UBInt32("shot_point"),
                           construct.UBInt8("shot_point_index"),
                           construct.UBInt32("shot_point_X"),
                           construct.UBInt32("shot_point_Y"),
                           construct.UBInt32("shot_point_X_final"),
                           construct.UBInt32("shot_point_Y_final"),
                           construct.UBInt32("shot_point_depth_final"),
                           # 0 - Undefined
                           construct.UBInt8("final_shot_info"),
                           # 1 - preplan
                           # 2 - as shot
                           # 3 - post processed
                           construct.UBInt8("energy_source"),  # 0 - Undefined
                           # 1 - Vibroseis
                           # 2 - Dynamite
                           # 3 - Air gun
                           construct.UBInt8("reserved01")
                           )
    return BIN


class Trace_header_2 (object):
    __keys__ = ("shot_line",
                "shot_point",
                "shot_point_index",
                "shot_point_X",
                "shot_point_Y",
                "shot_point_X_final",
                "shot_point_Y_final",
                "shot_point_depth_final",
                "final_shot_info",
                "energy_source",
                "reserved01")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_2.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_2()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_2()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6
#


def trace_header_3():
    BIN = construct.Struct("BIN",
                           construct.UBInt64("shot_epoch"),
                           construct.UBInt64("shot_skew_time"),
                           construct.UBInt64("clock_correction"),
                           construct.UBInt64("clock_correction_not_applied")
                           )
    return BIN


class Trace_header_3 (object):
    __keys__ = ("shot_epoch",
                "shot_skew_time",
                "clock_correction",
                "clock_correction_not_applied")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_3.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_3()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_3()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 2.1
#


def trace_header_3_remote_unit():
    BIN = construct.Struct("BIN",
                           construct.UBInt64("remote_unit_id"),
                           construct.UBInt64("deployment_epoch"),
                           construct.UBInt64("pickup_epoch"),
                           construct.UBInt64("remote_start_epoch")
                           )
    return BIN


class Trace_header_3_remote_unit (object):
    __keys__ = ("remote_unit_id",
                "deployment_epoch",
                "pickup_epoch",
                "remote_start_epoch")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_3_remote_unit.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_3_remote_unit()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_3_remote_unit()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 2.1 (trace header #4)
#


def trace_header_3_timing_block():
    BIN = construct.Struct("BIN",
                           construct.UBInt64("acquisition_drift_window"),
                           construct.UBInt64("clock_drift"),
                           construct.UBInt64("applied_clock_correction"),
                           construct.UBInt64("remaining_clock_correction")
                           )
    return BIN


class Trace_header_3_timing_block (object):
    __keys__ = ("acquisition_drift_window",
                "clock_drift",
                "applied_clock_correction",
                "remaining_clock_correction")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_3_timing_block.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_3_timing_block()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_3_timing_block()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6
#


def trace_header_4():
    BIN = construct.Struct("BIN",
                           construct.UBInt32("pre_shot_guard_band"),
                           construct.UBInt32("post_shot_guard_band"),
                           construct.UNInt8("preamp_gain_db"),
                           construct.UBInt8("trace_flag"),  # 0 - not clipped
                           # 1 - digital clip detected
                           # 2 - analog clip detected
                           # 0x8 - normal seismic data record
                           construct.UBInt8("record_type"),
                           # 0x2 - test data record
                           construct.UBInt8("shot_status"),  # 0 - normal
                           # 1 - Bad operator says
                           # 2 - Bad Failed T0 QC test
                           construct.UBInt32("reserved01"),
                           construct.UBInt64("reserved02"),
                           construct.BFloat32("first_break_pick_time"),
                           construct.BFloat32("rms_noise")
                           )
    return BIN


class Trace_header_4 (object):
    __keys__ = ("pre_shot_guard_band",
                "post_shot_guard_band",
                "preamp_gain_db",
                "trace_flag",
                "record_type",
                "shot_status",
                "reserved01",
                "reserved02",
                "first_break_pick_time",
                "rms_noise")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_4.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_4()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_4()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6
#


def trace_header_5():
    BIN = construct.Struct("BIN",
                           construct.UBInt32("line_number"),
                           construct.UBInt32("point"),
                           construct.UBInt8("point_index"),
                           construct.UBInt32("receiver_point_X"),
                           construct.UBInt32("receiver_point_Y"),
                           construct.UBInt32("receiver_point_X_final"),
                           construct.UBInt32("receiver_point_Y_final"),
                           construct.UBInt32("receiver_point_depth_final"),
                           construct.UBInt8("receiver_info"),  # 1 - preplan
                           # 2 - as laid (no navigation sensor)
                           # 3 - as laid (HiPAP only)
                           # 4 - as laid (HiPAP and INS)
                           # 5 - as laid (HiPAP and DVL)
                           # 6 - as laid (HiPAP, DVL and INS)
                           # 7 - post processed (HiPAP only)
                           # 8 - post processed (HiPAP and INS)
                           # 9 - post processed (HiPAP and DVL)
                           # 10 - post processed (HiPAP, DVL and INS)
                           # 11 - first break analysis
                           construct.UBInt16("reserved01")
                           )
    return BIN


class Trace_header_5 (object):
    __keys__ = ("line_number",
                "point",
                "point_index",
                "receiver_point_X",
                "receiver_point_Y",
                "receiver_point_X_final",
                "receiver_point_Y_final",
                "receiver_point_depth_final",
                "receiver_info",
                "reserved01")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_5.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_5()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_5()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 2.1
#


def trace_header_5_acquisition_data_block():
    BIN = construct.Struct("BIN",
                           construct.UBInt8("preamp_gain"),
                           construct.UBInt8("clipped_flag"),
                           construct.UBInt8("record_type_code"),
                           construct.UBInt8("shot_status_flag"),
                           construct.UBInt8("periodic_data_type"),
                           # See ZSystem format spec
                           construct.UBInt8("acquisition_stop_method"),
                           construct.UBInt8("frequency_drift_flag"),
                           construct.UBInt8("oscillator_type"),
                           construct.UBInt64("reserved01"),
                           construct.UBInt64("reserved02"),
                           construct.BFloat32("post_process_pick_time"),
                           construct.BFloat32("post_process_rms_noise")
                           )
    return BIN


class Trace_header_5_acquisition_data_block (object):
    __keys__ = ("preamp_gain",
                "clipped_flag",
                "record_type_code",
                "shot_status_flag",
                "periodic_data_type",
                "acquisition_stop_method",
                "frequency_drift_flag",
                "oscillator_type",
                "reserved01",
                "reserved02",
                "post_process_pick_time",
                "post_process_rms_noise")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_5_acquisition_data_block.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_5_acquisition_data_block()
        else:
            raise HeaderError("Little endian byte order not supported.")
            # t = general_header_block_2_le ()

        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_5_acquisition_data_block()
        else:
            raise HeaderError("Little endian byte order not supported.")
            # t = general_header_block_2_le ()

        return t.parse(buf)
#
# 1.6, 2.1
#


def trace_header_6():
    BIN = construct.Struct("BIN",
                           construct.BFloat32("H1X"),
                           construct.BFloat32("H2X"),
                           construct.BFloat32("VX"),
                           construct.BFloat32("H1Y"),
                           construct.BFloat32("H2Y"),
                           construct.BFloat32("VY"),
                           construct.BFloat32("H1Z"),
                           construct.BFloat32("H2Z")
                           )
    return BIN


class Trace_header_6 (object):
    __keys__ = ("H1X",
                "H2X",
                "VX",
                "H1Y",
                "H2Y",
                "VY",
                "H1Z",
                "H2Z")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_6.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_6()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_6()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6, 2.1
#


def trace_header_7():
    BIN = construct.Struct("BIN",
                           construct.BFloat32("VZ"),
                           construct.BFloat32("azimuth"),
                           construct.BFloat32("pitch"),
                           construct.BFloat32("roll"),
                           construct.BFloat32("remote_temp"),
                           construct.BFloat32("remote_humidity"),
                           construct.UBInt64("reserved01")
                           )
    return BIN


class Trace_header_7 (object):
    __keys__ = ("VZ",
                "azimuth",
                "pitch",
                "roll",
                "remote_temp",
                "remote_humidity",
                "reserved01")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_7.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_7()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_7()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6
#


def trace_header_8():
    BIN = construct.Struct("BIN",
                           construct.UBInt32("test_code"),
                           construct.UBInt32(
                               "first_test_oscillator_attenuation"),
                           construct.UBInt32(
                               "second_test_oscillator_attenuation"),
                           construct.UBInt32("start_delay_usec"),
                           construct.UBInt32("dc_filter"),  # 0 - no filter
                           # 1 - apply filter
                           construct.UBInt32("dc_filter_freq"),
                           # 0 - external input selected (default)
                           construct.UBInt32("pre_amp_path"),
                           # 1 - simulated data delected
                           # 2 - pre-amp input shorted to ground
                           # 3 - test oscillator with sensors
                           # 4 - test oscillator without sensors
                           # 5 - common mode test oscillator with sensors
                           # 6 - common mode test oscillator without sensors
                           # 7 - test oscillator on positive sensors with
                           # neg sensor grounded
                           # 8 - test oscillator on negative sensors with pos
                           # sensor grounded
                           # 9 - test oscillator on positive PA input, with
                           # neg PA input grounded
                           # 10 - test oscillator on negative PA input, with
                           # pos PA input grounded
                           # 11 - test oscillator on positive PA input, with
                           # neg PA input ground, no sensors
                           # 12 - test oscillator on negative PA input, with
                           # pos PA input ground, no sensors
                           # 0 - test oscillator path open
                           construct.UBInt32("oscillator_siganl_type")
                           # 1 - test signal selected
                           # 2 - DC reference selected
                           # 3 - test oscillator path grounded
                           # 4 DC reference toggle selected
                           )
    return BIN


class Trace_header_8 (object):
    __keys__ = ("test_code",
                "first_test_oscillator_attenuation",
                "second_test_oscillator_attenuation",
                "start_delay_usec",
                "dc_filter",
                "dc_filter_freq",
                "pre_amp_path",
                "oscillator_siganl_type")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_8.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_8()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_8()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6
#


def trace_header_9():
    BIN = construct.Struct("BIN",
                           # 0 - pattern address ramp
                           construct.UBInt32("generator_signal_type"),
                           # 1 - pattern is RU address ramp
                           # 2 - pattern is built from provided values
                           # 3 - pattern is random numbers
                           # 4 - pattern is a walking 1s
                           # 5 - pattern is a walking 0s
                           # 6 - test signal is a specified DC value
                           # 7 - test signal is a pulse train with
                           # specified duty cycle
                           # 8 - test signal is a sine wave
                           # 9 - test signal is a dual tone sine
                           # 10 - test signal is an impulse
                           # 11 - test signal is a step function
                           construct.UBInt32("generator_freq_1"),
                           construct.UBInt32("generator_freq_2"),
                           construct.UBInt32("generator amplitude_1"),
                           construct.UBInt32("generator_amplitude_2"),
                           construct.UBInt32("generator_duty_cycle"),
                           construct.UBInt32("generator_duration_usec"),
                           construct.UBInt32("generator_activation_time_usec")
                           )
    return BIN


class Trace_header_9 (object):
    __keys__ = ("generator_signal_type",
                "generator_freq_1",
                "generator_freq_2",
                "generator amplitude_1",
                "generator_amplitude_2",
                "generator_duty_cycle",
                "generator_duration_usec",
                "generator_activation_time_usec")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_9.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_9()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_9()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)
#
# 1.6
#


def trace_header_10():
    swap = True
    if sys.byteorder == 'big':
        swap = False

    BIN = construct.Struct("BIN",
                           construct.UBInt32("idle_level"),
                           construct.UBInt32("active_level"),
                           construct.UBInt32("generator_pattern_1"),
                           construct.UBInt32("generator_patern_2"),
                           construct.BitField("reserved01", 16, swapped=swap)
                           )
    return BIN


class Trace_header_10 (object):
    __keys__ = ("idle_level",
                "active_level",
                "generator_pattern_1",
                "generator_patern_2",
                "reserved01")

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Trace_header_10.__keys__:
            self.__dict__[c] = 0

    def set(self, keyval):
        for k in keyval.keys():
            if k in self.__dict__:
                self.__dict__[k] = keyval[k]
            else:
                raise HeaderError(
                    "Warning: Attempt to set unknown variable\
                    %s in trace header.\n" % k)

    def get(self):
        if self.endian == 'big':
            t = Trace_header_10()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = Trace_header_10()
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.parse(buf)

#
# Mixins
#


def convert_bcd_fields(ret, nbcd, nnibbles):
    for k in nbcd:
        bcd = ret[k]
        n = nnibbles[k]
        if sys.byteorder == 'little':
            bcd = construct.ULInt64("xxx").build(bcd)
        else:
            bcd = construct.UBInt64("xxx").build(bcd)

        ret[k] = bcd_py.bcd2int(bcd, 0, n)

    return ret
