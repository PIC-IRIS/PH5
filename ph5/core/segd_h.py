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

PROG_VERSION = '2020.34'


def __version__():
    print PROG_VERSION


class HeaderError (exceptions.Exception):
    def __init__(self, args=None):
        self.args = args

#
# 1.6 and 2.1
#


def storage_unit_label():
    BIN = "BIN" / construct.Struct(
            "storage_unit_sequence_number" / construct.Bytes(4),
            "fairfield_revision" / construct.Bytes(5),
            "storage_unit_structure" / construct.Bytes(6),
            "binding_edition" / construct.Bytes(4),
            "max_block_size" / construct.Bytes(10),
            "api_producer_code" / construct.Bytes(10),
            "creation_date" / construct.Bytes(11),
            "serial_number" / construct.Bytes(12),
            "reserved01" / construct.Bytes(6),
            "external_label_name" / construct.Bytes(12),
            "recording_entity_name" / construct.Bytes(24),
            "user_defined" / construct.Bytes(14),
            "max_file_size_MB" / construct.Bytes(10)
        )
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
    B = "BIN" / construct.BitStruct(
            "A" / construct.BitsInteger(256, swapped=True))
    L = "BIN" / construct.BitStruct(
            "A" / construct.BitsInteger(256))
    return B, L


def swap_block_64():
    B = "BIN" / construct.BitStruct(
            "A" / construct.Int64ub,
            "B" / construct.Int64ub,
            "C" / construct.Int64ub,
            "D" / construct.Int64ub)
    L = "BIN" / construct.BitStruct(
            "A" / construct.Int64ul,
            "B" / construct.Int64ul,
            "C" / construct.Int64ul,
            "D" / construct.Int64ul)
    return B, L


def swap_block_32():
    B = "BIN" / construct.BitStruct(
            "A" / construct.Int32ub,
            "B" / construct.Int32ub,
            "C" / construct.Int32ub,
            "D" / construct.Int32ub,
            "E" / construct.Int32ub,
            "F" / construct.Int32ub,
            "G" / construct.Int32ub,
            "H" / construct.Int32ub)
    L = "BIN" / construct.BitStruct(
            "A" / construct.Int32ul,
            "B" / construct.Int32ul,
            "C" / construct.Int32ul,
            "D" / construct.Int32ul,
            "E" / construct.Int32ul,
            "F" / construct.Int32ul,
            "G" / construct.Int32ul,
            "H" / construct.Int32ul)
    return B, L


def swap_block_16():
    B = "BIN" / construct.BitStruct(
            "A" / construct.Int16ub,
            "B" / construct.Int16ub,
            "C" / construct.Int16ub,
            "D" / construct.Int16ub,
            "E" / construct.Int16ub,
            "F" / construct.Int16ub,
            "G" / construct.Int16ub,
            "H" / construct.Int16ub,
            "I" / construct.Int16ub,
            "J" / construct.Int16ub,
            "K" / construct.Int16ub,
            "L" / construct.Int16ub,
            "M" / construct.Int16ub,
            "N" / construct.Int16ub,
            "O" / construct.Int16ub,
            "P" / construct.Int16ub)
    L = "BIN" / construct.BitStruct(
            "A" / construct.Int16ul,
            "B" / construct.Int16ul,
            "C" / construct.Int16ul,
            "D" / construct.Int16ul,
            "E" / construct.Int16ul,
            "F" / construct.Int16ul,
            "G" / construct.Int16ul,
            "H" / construct.Int16ul,
            "I" / construct.Int16ul,
            "J" / construct.Int16ul,
            "K" / construct.Int16ul,
            "L" / construct.Int16ul,
            "M" / construct.Int16ul,
            "N" / construct.Int16ul,
            "O" / construct.Int16ul,
            "P" / construct.Int16ul)

    return B, L
#
# 1.6, 2.1
#


def general_header_block_1():
    swap = False
    BIN = "BIN" / construct.BitStruct(
            "file_number" / construct.BitsInteger(16, swapped=swap),
            # 8058 is IEEE 32 bit float
            "data_sample_format_code" / construct.BitsInteger(16, swapped=swap),
            "general_constant_1" / construct.BitsInteger(8, swapped=swap),
            "general_constant_2" / construct.BitsInteger(8, swapped=swap),
            "general_constant_3" / construct.BitsInteger(8, swapped=swap),
            "general_constant_4" / construct.BitsInteger(8, swapped=swap),
            "general_constant_5" / construct.BitsInteger(8, swapped=swap),
            "general_constant_6" / construct.BitsInteger(8, swapped=swap),
            "first_shot_point_year" / construct.BitsInteger(8, swapped=swap),
            "number_additional_general_header_blocks" /
            construct.BitsInteger(4, swapped=swap),
            "first_shot_point_doy" / construct.BitsInteger(12, swapped=swap),
            "first_shot_point_time_utc" / construct.BitsInteger(24, swapped=swap),
            # 20 is Fairfield
            "manufactures_code" / construct.BitsInteger(8, swapped=swap),
            "manufactures_sn" / construct.BitsInteger(16, swapped=swap),
            # Traces written in superblocks. 0=No, 1=Yes
            "super_blocks" / construct.BitsInteger(8, swapped=swap),
            "user01" / construct.BitsInteger(16, swapped=swap),
            # Sample interval in 1/16 msec
            "base_scan_interval" / construct.BitsInteger(8, swapped=swap),
            "polarity_code" / construct.BitsInteger(4, swapped=swap),
            "user02" / construct.BitsInteger(12, swapped=swap),
            "record_type" / construct.BitsInteger(4, swapped=swap),
            # From time zero, 0.5 X 1.024 seconds, if 0xFFF
            # look in general header block 2
            "record_length" / construct.BitsInteger(12, swapped=swap),
            "scan_types_per_record" / construct.BitsInteger(8, swapped=swap),
            # 0xFF look in general header block 2
            "chan_sets_per_scan" / construct.BitsInteger(8, swapped=swap),
            "number_skew_blocks" / construct.BitsInteger(8, swapped=swap),
            # 0xFF look in general header block 2
            "number_extended_header_blocks" / construct.BitsInteger(8, swapped=swap),
            # 0xFF look in general header block 2
            "number_external_header_blocks" / construct.BitsInteger(8, swapped=swap),
        )
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
    if sys.byteorder == 'little':
        swap = True
    BIN = "BIN" / construct.BitStruct(
            "extended_file_number" / construct.BitsInteger(24, swapped=swap),
            "extended_chan_sets_per_scan_type" /
            construct.BitsInteger(16, swapped=swap),
            "extended_header_blocks" / construct.BitsInteger(16, swapped=swap),
            # External header blocks is 3 bytes in Fairfield
            # 1.6. Append user01.
            "external_header_blocks" / construct.BitsInteger(24, swapped=swap),
            # construct.BitsInteger ("user01", 8, swapped=swap),
            # 0x0106, or 0x0201
            "file_version_number" / construct.BitsInteger(16, swapped=swap),
            "number_general_trailer_blocks" /
            construct.BitsInteger(16, swapped=swap),
            # Record length in milliseconds
            "extended_record_length" / construct.BitsInteger(24, swapped=swap),
            "user02" / construct.BitsInteger(8, swapped=swap),
            "general_header_block_number" / construct.BitsInteger(8, swapped=swap),
            "user03" / construct.BitsInteger(8, swapped=swap),
            # 2.1
            "sequence_number" / construct.BitsInteger(16, swapped=swap),
            # 2.1
            "super_block_size" / construct.BitsInteger(32, swapped=swap),
            "user04" / construct.BitsInteger(32, swapped=swap),
            # 2.1
            "zsystem_revision_number" / construct.BitsInteger(16, swapped=swap)
        )
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
    if sys.byteorder == 'little':
        swap = True
    BIN = "BIN" / construct.BitStruct(
        "extended_file_number" / construct.BitsInteger(24, swapped=swap),
        "source_line_number_int" / construct.BitsInteger(24, swapped=swap),
        "source_line_number_frac" / construct.BitsInteger(16, swapped=swap),
        "source_point_number_int" / construct.BitsInteger(24, swapped=swap),
        "source_point_number_frac" / construct.BitsInteger(16, swapped=swap),
        "source_point_index" / construct.BitsInteger(8, swapped=swap),
        "phase_control" / construct.BitsInteger(8, swapped=swap),
        "vibrator_type" / construct.BitsInteger(8, swapped=swap),
        "phase_angle" / construct.BitsInteger(16, swapped=swap),
        "general_header_block_number" / construct.BitsInteger(8, swapped=swap),
        "source_set_number" / construct.BitsInteger(8, swapped=swap),
        "user01" / construct.BitsInteger(96, swapped=swap)
    )
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
    swap = False
    BIN = "BIN" / construct.BitStruct(
        "scan_type_number" / construct.BitsInteger(8, swapped=swap),
        "chan_set_number" / construct.BitsInteger(8, swapped=swap),
        # Times 2 is milliseconds
        "chan_set_start_time" / construct.BitsInteger(16, swapped=swap),
        # Times 2 is milliseconds
        "chan_set_end_time" / construct.BitsInteger(16, swapped=swap),
        "optional_mp_factor_extension_byte" /
        construct.BitsInteger(8, swapped=swap),
        "mp_factor_scaler_multiplier" / construct.BitsInteger(8, swapped=swap),
        "number_of_chans_in_chan_set" / construct.BitsInteger(16, swapped=swap),
        "chan_type_code" / construct.BitsInteger(4, swapped=swap),
        "number_sub-scans" / construct.BitsInteger(4, swapped=swap),
        # 3 is fixed gain
        "gain_control_type" / construct.BitsInteger(4, swapped=swap),
        "alias_filter_freq" / construct.BitsInteger(16, swapped=swap),
        "alias_filter_slope_db" / construct.BitsInteger(16, swapped=swap),
        "low_cut_filter_freq" / construct.BitsInteger(16, swapped=swap),
        "low_cut_filter_slope_db" / construct.BitsInteger(16, swapped=swap),
        "notch_filter_freq" / construct.BitsInteger(16, swapped=swap),
        "second_notch_filter_freq" / construct.BitsInteger(16, swapped=swap),
        "third_notch_filter_freq" / construct.BitsInteger(16, swapped=swap),
        "extended_chan_set_number" / construct.BitsInteger(16, swapped=swap),
        "extended_header_flag" / construct.BitsInteger(4, swapped=swap),
        # Always 10 for Fairfield
        "number_trace_header_extensions" / construct.BitsInteger(4, swapped=swap),
        "vertical_stack_size" / construct.BitsInteger(8, swapped=swap),
        "streamer_cable_number" / construct.BitsInteger(8, swapped=swap),
        "array_forming" / construct.BitsInteger(8, swapped=swap)
    )
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
    BIN = "BIN" / construct.BitStruct(
        # Remote unit
        "part_number" / construct.Int32ub,
        "id_number" / construct.Int32ub,
        # All epochs in micro-seconds
        "epoch_deploy" / construct.Int64ub,
        "epoch_pickup" / construct.Int64ub,
        "remote_unit_epoch" / construct.Int64ub
    )
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
    BIN = "BIN" / construct.BitStruct(
        "shot_epoch_time" / construct.Int64ub,
        "shot_skew_time" / construct.Int32ub,
        "files_shot_point" / construct.Int16ub,
        "file_index" / construct.Int64ub,
        "user01" / construct.Int8ub,
        "data_decimation_flag" / construct.Int8ub,
        "number_decimation_filter_coefficients" / construct.Int16ub,
        "base_scan_interval_0" / construct.Int8ub,
        "pre_shot_guard_base" / construct.Int32ub,
        "post_shot_guard_base" / construct.Int32ub,
        "simultaneous_shots" / construct.Int16ub,
        "user02" / construct.Int8ub
    )
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
    BIN = "BIN" / construct.BitStruct(
        "drift_window" / construct.Float32b,
        "clock_drift_ns" / construct.Int64ub,
        # Clock stop method
        "clock_stop_method" / construct.Int8ub,
        # 0 - normal
        # 1 - storage full
        # 2 - power loss
        # 3 - reboot by command
        # Frequency drift flag
        "Frequency_drift" / construct.Int8ub,
        # 0 - not in spec
        # 1 - in spec
        # Oscillator type
        "oscillator_type" / construct.Int8ub,
        # 0 - control board
        # 1 - atomic
        # 2 - ovenized
        # 3 - double ovenized
        # 4 - disciplined
        # 0 - normal (shots)
        "collection_method" / construct.Int8ub,
        # 1 - continuous (fixed time slice)
        # 2 - shot sliced with guard band
        # Number of traces
        "number_records" / construct.Int32ub,
        "number_files" / construct.Int32ub,
        "file_number" / construct.Int32ub,
        # Decimation flag
        "decimation_flag" / construct.Int8ub,
        # 0 - not decimated
        # 1 - decimated
        "base_scan_interval" / construct.Int8ub,
        "decimation_filter_coefficients" / construct.Int16ub
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
    BIN = "BIN" / construct.BitStruct(
        "test_analysis_code" / Int32ub,
        "first_test_oscillator_attenuation" / Int32ub,
        "second_test_oscillator_attenuation" / Int32ub,
        "start_delay_usec" / Int32ub,
        # 00 - No filter, 01 - Apply filter
        "dc_filter_flag" / Int32ub,
        "dc_filter_frequency" / Float32b,
        # See page 9 of format spec
        "preamp_path" / Int32ub,
        "test_oscillator_signal_type" / Int32ub,
    )
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
    swap = False
    BIN = "BIN" / construct.BitStruct(
        "line_number" / construct.Int32ub,
        "receiver_point" / construct.Int32ub,
        "point_index" / construct.Int8ub,
        "first_shot_line" / construct.Int32ub,
        "first_shot_point" / construct.Int32ub,
        "first_shot_point_index" / construct.Int8ub,
        "last_shot_line" / construct.Int32ub,
        "last_shot_point" / construct.Int32ub,
        "last_shot_point_index" / construct.Int8ub,
        "reserved01" / construct.BitsInteger(5, swapped=swap)
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

    BIN = "BIN" / construct.BitStruct(
        "test_signal_type" / construct.Int32ub,
        "test_signal_frequency_1" / construct.Int32ub,
        "test_signal_frequency_2" / construct.Int32ub,
        "test_signal_amplitude_1" / construct.Int32ub,
        "test_signal_amplitude_2" / construct.Int32ub,
        "test_signal_duty_cycle" / construct.Float32b,
        "test_signal_active_duration" / construct.Int32ub,
        "test_signal_active_time" / construct.Int32ub
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
    BIN = "BIN" / construct.BitStruct(
        # Decimation filter coefficients
        "coef01" / construct.Float32b,
        "coef02" / construct.Float32b,
        "coef03" / construct.Float32b,
        "coef04" / construct.Float32b,
        "coef05" / construct.Float32b,
        "coef06" / construct.Float32b,
        "coef07" / construct.Float32b,
        "coef08" / construct.Float32b
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
    BIN = "BIN" / construct.BitStruct(
        "idle_level" / construct.Float32b,
        "active_level" / construct.Float32b,
        "pattern_01" / construct.Float32b,
        "pattern_02" / construct.Float32b,
        "channel_mask" / construct.Float32b,
        "user01" / construct.Float32b,
        "user02" / construct.Float32b,
        "user03" / construct.Float32b
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
    swap = False
    BIN = "BIN" / construct.BitStruct(
        "size" / construct.Int32ub,
        "receiver_line" / construct.Int32ub,
        "receiver_point" / construct.Int32ub,
        "receiver_point_index" / construct.Int8ub,
        "reserved01" / construct.BitsInteger(18, swapped=swap)
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
    BIN = "BIN" / construct.BitStruct(
        "shot_epoch" / construct.Int64ub,
        "shot_line" / construct.Int32ub,
        "shot_point" / construct.Int32ub,
        "shot_point_index" / construct.Int8ub,
        "shot_point_X" / construct.Int32ub,
        "shot_point_Y" / construct.Int32ub,
        "shot_point_depth" / construct.Int32ub,
        "shot_info" / construct.Int8ub,
        # 0 - Undefined
        # 1 - preplan
        # 2 - as shot
        # 3 - post processed
        "shot_status" / construct.Int8ub,
        # 0 - normal
        # 1 - Bad - operator defined
        # 2 - Bad Failed T0 QC test
        "reserved01" / construct.Int8ub,
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
    BIN = "BIN" / construct.BitStruct(
        "shot_line_number" / construct.Int32ub,
        "shot_point_number" / construct.Int32ub,
        "shot_point_index" / construct.Int8ub,
        "shot_point_pre_X" / construct.Int32ub,
        "shot_point_pre_Y" / construct.Int32ub,
        "shot_point_X" / construct.Int32ub,
        "shot_point_Y" / construct.Int32ub,
        "shot_point_depth" / construct.Int32ub,
        # See format spec ZSystem
        "shot_info_source" / construct.Int8ub,
        "energy_source_type" / construct.Int8ub,
        "shot_status_flag" / construct.Int8ub
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
    swap = False
    if sys.byteorder == 'little':
        swap = True
    BIN = "BIN" / construct.BitStruct(
        "tape_file" / construct.BitsInteger(16, swapped=swap),
        "scan_type" / construct.BitsInteger(8, swapped=swap),
        "channel_set" / construct.BitsInteger(8, swapped=swap),
        "trace_number" / construct.BitsInteger(16, swapped=swap),
        "first_timing_word" / construct.BitsInteger(24, swapped=swap),
        "trace_extension_blocks" / construct.BitsInteger(8, swapped=swap),
        "sample_skew_value" / construct.BitsInteger(8, swapped=swap),
        "trace_edit_code" / construct.BitsInteger(8, swapped=swap),
        "time_break_window" / construct.BitsInteger(24, swapped=swap),
        "extended_channel_set" / construct.BitsInteger(16, swapped=swap),
        "extended_file_number" / construct.BitsInteger(24, swapped=swap),
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
    swap = False
    if sys.byteorder == 'little':
        swap = True
    BIN = "BIN" / construct.BitStruct(
        "receiver_line" / construct.BitsInteger(24, swapped=swap),
        "receiver_point" / construct.BitsInteger(24, swapped=swap),
        "receiver_point_index" / construct.BitsInteger(8, swapped=swap),
        "samples_per_trace" / construct.BitsInteger(24, swapped=swap),
        "extended_receiver_line_number" / construct.BitsInteger(40, swapped=swap),
        "extended_receiver_point_number" / construct.BitsInteger(40, swapped=swap),
        # 00 - Not defined
        # 01 - Hydrophone
        # 02 - Vertical geophone
        # 03 - In-line geophone
        # 04 - Cross-line geophone
        # 05 - Other horizontal geophone
        # 06 - Vertical accelerometer
        # 07 - In-line accelerometer
        # 08 - Cross-line accelerometer
        # 09 - Other horizontal accelerometer
        "sensor_type" / construct.BitsInteger(8, swapped=swap),
        "reserved01" / construct.BitsInteger(88, swapped=swap)
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
    BIN = "BIN" / construct.BitStruct(
        "shot_line" / construct.Int32ub,
        "shot_point" / construct.Int32ub,
        "shot_point_index" / construct.Int8ub,
        "shot_point_X" / construct.Int32ub,
        "shot_point_Y" / construct.Int32ub,
        "shot_point_X_final" / construct.Int32ub,
        "shot_point_Y_final" / construct.Int32ub,
        "shot_point_depth_final" / construct.Int32ub,
        # 0 - Undefined
        # 1 - preplan
        # 2 - as shot
        # 3 - post processed
        "final_shot_info" / construct.Int8ub,
        # 0 - Undefined
        # 1 - Vibroseis
        # 2 - Dynamite
        # 3 - Air gun
        "energy_source" / construct.Int8ub,
        "reserved01" / construct.Int8ub,
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
    BIN = "BIN" / construct.BitStruct(
        "shot_line" / construct.Int64ub,
        "shot_skew_time" / construct.Int64ub,
        "clock_correction" / construct.Int64ub,
        "clock_correction_not_applied" / construct.Int64ub)
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
    BIN = "BIN" / construct.BitStruct(
        "remote_unit_id" / construct.Int64ub,
        "deployment_epoch" / construct.Int64ub,
        "pickup_epoch" / construct.Int64ub,
        "remote_start_epoch" / construct.Int64ub)
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
    BIN = "BIN" / construct.BitStruct(
        "acquisition_drift_window" / construct.Int64ub,
        "clock_drift" / construct.Int64ub,
        "applied_clock_correction" / construct.Int64ub,
        "remaining_clock_correction" / construct.Int64ub)
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
    BIN = "BIN" / construct.BitStruct(
        "pre_shot_guard_band" / construct.Int32ub,
        "post_shot_guard_band" / construct.Int32ub,
        "preamp_gain_db" / construct.Int8ub,
        "trace_flag" / construct.Int8ub,
        # 0 - not clipped
        # 1 - digital clip detected
        # 2 - analog clip detected
        # 0x8 - normal seismic data record
        # 0x2 - test data record
        "record_type" / construct.Int8ub,
        # 0 - normal
        # 1 - Bad operator says
        # 2 - Bad Failed T0 QC test
        "shot_status" / construct.Int8ub,
        "reserved01" / construct.Int32ub,
        "reserved02" / construct.Int64ub,
        "first_break_pick_time" / construct.Float32b,
        "rms_noise" / construct.Float32b
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
    BIN = "BIN" / construct.BitStruct(
        "line_number" / construct.Int32ub,
        "point" / construct.Int32ub,
        "point_index" / construct.Int8ub,
        "receiver_point_X" / construct.Int32ub,
        "receiver_point_Y" / construct.Int32ub,
        "receiver_point_X_final" / construct.Int32ub,
        "receiver_point_Y_final" / construct.Int32ub,
        "receiver_point_depth_final" / construct.Int32ub,
        # 1 - preplan
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
        "receiver_info" / construct.Int8ub,
        "reserved01" / construct.Int16ub
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
    BIN = "BIN" / construct.BitStruct(
        "preamp_gain" / construct.Int8ub,
        "clipped_flag" / construct.Int8ub,
        "record_type_code" / construct.Int8ub,
        "shot_status_flag" / construct.Int8ub,
        # See ZSystem format spec
        "periodic_data_type" / construct.Int8ub,
        "acquisition_stop_method" / construct.Int8ub,
        "frequency_drift_flag" / construct.Int8ub,
        "oscillator_type" / construct.Int8ub,
        "reserved01" / construct.Int64ub,
        "reserved02" / construct.Int64ub,
        "post_process_pick_time" / construct.Int32ub,
        "post_process_rms_noise" / construct.Int32ub,
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
    BIN = "BIN" / construct.BitStruct(
        "H1X" / construct.Float32b,
        "H2X" / construct.Float32b,
        "VX" / construct.Float32b,
        "H1Y" / construct.Float32b,
        "H2Y" / construct.Float32b,
        "VY" / construct.Float32b,
        "H1Z" / construct.Float32b,
        "H2Z" / construct.Float32b)
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
    BIN = "BIN" / construct.BitStruct(
        "VZ" / construct.Float32b,
        "azimuth" / construct.Float32b,
        "pitch" / construct.Float32b,
        "roll" / construct.Float32b,
        "remote_temp" / construct.Float32b,
        "remote_humidity" / construct.Float32b,
        "reserved01" / construct.Int64ub)
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
    BIN = "BIN" / construct.BitStruct(
        "test_code" / construct.Int32ub,
        "first_test_oscillator_attenuation" / construct.Int32ub,
        "second_test_oscillator_attenuation" / construct.Int32ub,
        "start_delay_usec" / construct.Int32ub,
        # 0 - no filter
        # 1 - apply filter
        "dc_filter" / construct.Int32ub,
        "dc_filter_freq" / construct.Int32ub,
        # 0 - external input selected (default)
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
        "pre_amp_path" / construct.Int32ub,
        # 0 - test oscillator path open
        # 1 - test signal selected
        # 2 - DC reference selected
        # 3 - test oscillator path grounded
        # 4 DC reference toggle selected
        "oscillator_siganl_type" / construct.Int32ub)
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
    BIN = "BIN" / construct.BitStruct(
        # 0 - pattern address ramp
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
        "generator_signal_type" / construct.Int32ub,
        "generator_freq_1" / construct.Int32ub,
        "generator_freq_2" / construct.Int32ub,
        "generator_amplitude_1" / construct.Int32ub,
        "generator_amplitude_2" / construct.Int32ub,
        "generator_duty_cycle" / construct.Int32ub,
        "generator_duration_usec" / construct.Int32ub,
        "generator_activation_time_usec" / construct.Int32ub
    )
    return BIN


class Trace_header_9 (object):
    __keys__ = ("generator_signal_type",
                "generator_freq_1",
                "generator_freq_2",
                "generator_amplitude_1",
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
    swap = False
    if sys.byteorder == 'little':
        swap = True
    BIN = "BIN" / construct.BitStruct(
        "idle_level" / construct.Int32ub,
        "active_level" / construct.Int32ub,
        "generator_pattern_1" / construct.Int32ub,
        "generator_patern_2" / construct.Int32ub,
        "reserved01" / construct.BitsInteger(16, swapped=swap)
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
        num_digits = nnibbles[k] * 2
        if sys.byteorder == 'little':
            bcd = construct.Int64ul.build(bcd)
        else:
            bcd = construct.Int64ub.build(bcd)

        ret[k] = bcd_py.bcd2int(bcd, 0, num_digits)

    return ret
