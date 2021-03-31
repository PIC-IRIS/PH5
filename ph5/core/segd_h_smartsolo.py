#!/usr/bin/env pnpython3
#
# A low level SEG-D library
# SmartSolo SEG-D 2.1
# based on segd_h.py by Steve Azevedo
#
# Lan Dam, March 2021
#

import exceptions
import sys
import construct
import bcd_py

PROG_VERSION = "2021.90"


def __version__():
    print PROG_VERSION


class HeaderError (exceptions.Exception):
    def __init__(self, args=None):
        self.args = args


def unsigned2signed(uint, bitnum):
    return uint - (uint >> (bitnum-1)) * 2**bitnum


def convert_bcd_field(val, nibble):
    bcd = val
    if sys.byteorder == 'little':
        bcd = construct.ULInt64("xxx").build(bcd)
    else:
        bcd = construct.UBInt64("xxx").build(bcd)
    ret = bcd_py.bcd2int(bcd, 0, nibble)

    return ret


def general_header_block(keys):
    swap = True
    if sys.byteorder == 'big':
        swap = False
    fields = []
    # swap with bcd only
    for k in keys:
        if len(k) < 3 or k[2] == 'signed':
            f = construct.BitField(k[0], k[1] * 4)
        elif k[2] == 'bcd':
            f = construct.BitField(k[0], k[1] * 4, swapped=swap)
        else:
            f = construct.BitField(k[0], k[1] * 4)
        fields.append(f)
    BIN = construct.BitStruct("BIN", *fields)
    return BIN


class Header_block (object):
    keys = ()

    def __init__(self, endian='big'):
        self.endian = endian
        for c in Header_block.keys:
            self.__dict__[c[0]] = 0

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
            t = general_header_block(self.keys)
        else:
            raise HeaderError("Little endian byte order not supported.")
        return t.build(self)

    def parse(self, buf):
        if self.endian == 'big':
            t = general_header_block(self.keys)
        else:
            raise HeaderError("Little endian byte order not supported.")
        ret = t.parse(buf)
        for k in self.keys:
            if len(k) < 3 or k[0] in ['record_length']:
                continue
            if k[2] == 'bcd':
                ret[k[0]] = convert_bcd_field(ret[k[0]], k[1])
            elif k[2] == 'signed':
                ret[k[0]] = unsigned2signed(ret[k[0]], k[1]*4)
        return ret


class General_header_block (Header_block):

    def __init__(self, n):
        super(General_header_block, self).__init__()
        if n == 0:
            # (key, nibble, bcd)
            # 1 nibble = 4 bit
            self.keys = (
                ("file_number", 4, 'bcd'),                        # 0-9999
                ("data_sample_format_code", 4, 'bcd'),            # 8058
                ("general_constant_1", 2, 'bcd'),
                ("general_constant_2", 2, 'bcd'),
                ("general_constant_3", 2, 'bcd'),
                ("general_constant_4", 2, 'bcd'),
                ("general_constant_5", 2, 'bcd'),
                ("general_constant_6", 2, 'bcd'),                 # 05
                ("first_shot_point_year", 2, 'bcd'),              # 0-99
                ("number_additional_general_header_blocks", 1),   # 2
                # defined bcd in doc but it doesn't give correct result w/ bcd
                ("first_shot_point_doy", 3),                      # 1-366
                ("hour_of_day_utc", 2, 'bcd'),
                ("minute_of_hour_utc", 2, 'bdc'),
                ("second_of_minute_utc", 2, 'bdc'),
                ("manufactures_code", 2, 'bcd'),                  # 0x61
                ("manufactures_sn", 4, 'bcd'),                    # 0
                ("bytes_per_scan", 6, 'bcd'),
                # 4:.25ms; 8:.5ms; 10:1ms; 20:2ms; 40: 4ms
                ("base_scan_interval", 2),
                # 0 = Untested; 4=135degrees; 8= 315 degrees; 1=Zero
                # 5= 180 degree; 12= unassigned; 2= 45 degrees
                # 6= 225 degrees; 3= 90 degrees; 7= 270 degrees
                ("polarity", 1),
                # 0: SG; 1:RG; 2:CG
                ("gather_type", 1),
                ("not_used", 2),
                # 8:normal; 2:test record
                ("record_type", 1),                               # 8
                # extended_record_length used
                ("record_length", 3, 'bcd'),                      # FFF
                ("scan_types_per_record", 2, 'bcd'),              # 1
                ("chan_sets_per_scan", 2, 'bcd'),                 # 16
                ("number_sample_skew_32_extensions", 2, 'bcd'),   # 00
                ("extended_header_length", 2, 'bcd'),
                ("external_header_length", 2, 'bcd'))

        if n == 1:
            self. keys = (
                ("extended_file_number", 6),
                ("extended_channel_set_per_scan_type", 4),        # 0
                ("extended_header_blocks", 4),                    # 0
                ("number_32-byte_fields_in_external_header", 4),  # 0
                ("not_used", 2),
                ("SEGD_revision_number", 4),                        # 1.0
                ("number_32-byte_general_trailer_blocks", 4),       # 0
                # 0-128000ms
                ("extended_record_length", 6),
                ("undefined1", 2),                                  # 0
                ("general_header_block_number", 2),                 # 2
                ("undefined2", 26))                                 # 0
        if n == 2:
            self.keys = (
                ("expanded_file_number", 6),
                ("source_line_number_integer", 6),
                ("source_line_number_fraction", 4),
                ("source_point_number_integer", 6),
                ("source_point_number_fraction", 4),
                ("source_point_index", 2),
                ("phase_control", 2),                               # 0
                ("vibrator_type", 2),                               # 0
                ("phase_angle", 4),                                 # 0
                ("general_header_block_number", 2),                 # 3
                ("source_set_number_default", 2),
                ("not_used", 24))                                   # 0


class Channel_set_descriptor (Header_block):
    # (key, nibble, bcd)
    # 1 nibble = 4 bit
    keys = (("scan_type_number", 2, 'bcd'),                         # 01
            ("chan_set_number", 2, 'bcd'),
            ("chan_set_start_time_ms", 4),                          # ms
            ("chan_set_end_time_ms", 4),                            # ms
            ("optional_mp_factor_extension_byte", 2),
            ("mp_factor_scaler_multiplier", 2),
            ("number_of_chans_in_chan_set", 4, 'bcd'),
            # 1=Seis; 9=Aux
            ("chan_type_code", 1),
            ("not_used", 1),                                        # 0
            ("number_sub-scans", 1, 'bcd'),                         # 0
            ("gain_control_type", 1),                               # 3
            ("alias_filter_freq_Hz", 4, 'bcd'),
            ("alias_filter_slope_dB_per_octave", 4, 'bcd'),
            ("low_cut_filter_freq_Hz", 4, 'bcd'),
            ("low_cut_filter_slope_db_per_octave", 4, 'bcd'),
            ("first_notch_filter_freq", 4, 'bcd'),                  # 0
            ("second_notch_filter_freq", 4, 'bcd'),                 # 0
            ("third_notch_filter_freq", 4, 'bcd'),                  # 0
            ("extended_chan_set_number", 4),                        # 0
            ("extended_header_flag", 1),                            # 0
            ("number_trace_header_extensions", 1),                  # 7
            ("vertical_stack_size", 2),                             # 1
            ("streamer_cable_number", 2),                           # 0 in land
            ("array_forming", 2))                                   # 1


class Extended_header_block (Header_block):
    # (key, nibble)
    # 1 nibble = 4 bit
    keys = (("acquisition_lenth", 8),
            ("sample_rate", 8),
            ("number_of_traces", 8),
            ("number_of_samples_in_traces", 8),
            ("number_of_seis_traces", 8),
            ("number_of_auxes", 8),
            ("number_of_dead_seis_traces", 8),
            ("number_of_live_seis_traces", 8),
            # 0: no source, 1: impulsive
            ("source_type", 8),
            # 0:shot/ 1:receiver/ 2:continuous receiver
            ("gather_type", 4),
            ("reserved", 1972))


class External_header_block (Header_block):
    # (key, nibble)
    # 1 nibble = 4 bit
    keys = (("field_file_number", 8),                           # External FFID
            ("file_number", 8),
            ("souce_easting_cm", 8),
            ("source_northing_cm", 8),
            ("source_elevation_cm", 8),
            ("source_or_receiver_GPS_lat_integer", 8),          # DDMMSS.sss
            ("source_or_receiver_GPS_lat_fraction", 4),         # DDMMSS.sss
            ("source_or_receiver_GPS_lon_integer", 8),          # DDMMSS.sss
            ("source_or_receiver_GPS_lon_fraction", 4),         # DDMMSS.sss
            ("TB_GPS_time_ms", 16),
            ("not_used", 4),
            ("source_GPS_height_cm", 8),
            ("reserved", 1956))


class Trace_header (Header_block):
    # (key, nibble)
    # 1 nibble = 4 bit

    # filenumber = 0-9999, if >9999, set to FFFF, extended file number is used
    keys = (("4_digit_file_number", 4, 'bcd'),
            ("scan_type_number", 2, 'bcd'),                     # 01
            ("channel_set_number", 2, 'bcd'),
            ("trace_number", 4, 'bcd'),
            ("first_timing_word", 6),                           # Bin24
            ("number_trace_header_extension", 2),               # 7 Bin8
            ("sample_skew", 2),
            # 00 No edit applied; 02: muted or dead prior to qcquisition
            ("trace_edit", 2),
            ("time_break_window", 6),                           # Bin24
            ("extended_channel_set_number", 4),                 # 0 Bin16
            ("extended_file_number", 6))                        # Bin16


class Trace_header_extension(Header_block):

    def __init__(self, n):
        # (key, nibble, bcd/signed)
        # 1 nibble = 4 bit
        super(Trace_header_extension, self).__init__()
        if n == 0:
            self.keys = (
                ("receiver_line_number", 6, 'signed'),
                ("receiver_point_number", 6, 'signed'),
                ("receiver_point_index", 2),
                ("samples_per_trace", 6),
                ("extended_receiver_line_number_integer", 6, 'signed'),
                ("extended_receiver_line_number_fraction", 4),
                ("extended_receiver_point_number_integer", 6, 'signed'),
                ("extended_receiver_point_number_fraction", 4),
                ("not_used", 24))
        if n == 1:
            self.keys = (
                ("TB_GPS_time_microsec", 16),
                ("TB offset_microsec", 4),
                ("external_file_id", 8),
                ("not_used", 28),
                ("extended_trace_number", 8))
        if n == 2:
            self.keys = (
                ("receiver_easting_4_bytes_integer_cm", 8),
                ("receiver_northing_4_bytes_integer_cm", 8),
                ("receiver_elevation_4_bytes_integer_cm", 8),
                ("not_used", 40))
        if n == 3:
            self.keys = (
                ("IGU_GPS_lat_integer", 8),
                ("IGU_GPS_lat_fraction", 4),
                ("IGU_GPS_lon_integer", 8),
                ("IGU_GPS_lon_fraction", 4),
                ("IGU_GPS_height", 8),                              # float
                ("not_used", 32))
        if n == 4:
            self.keys = (("not_used", 64),)
        if n == 5:
            self.keys = (
                ("unit_type", 2),
                ("unit_serial_number", 8),
                ("channel_number", 2),
                ("not_used", 52))
        if n == 6:
            self.keys = (
                ("not_used", 64),)
