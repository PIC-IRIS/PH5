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

PROG_VERSION = "2021.130"


def __version__():
    print PROG_VERSION


class HeaderError (exceptions.Exception):
    def __init__(self, args=None):
        self.args = args


def convert_fixed_point_binary_16bit(uint):
    """
    convert fixed point binary 16 bit to float
    """
    return uint/float(2**16)


def unsigned2signed(uint, bitnum):
    """
    convert unsigned binary integer to signed binary integer
    """
    return uint - (uint >> (bitnum-1)) * 2**bitnum


def convert_bcd_field(val, bit_no):
    bcd = val
    if sys.byteorder == 'little':
        bcd = construct.ULInt64("xxx").build(bcd)
    else:
        bcd = construct.UBInt64("xxx").build(bcd)
    ret = bcd_py.bcd2int(bcd, 0, bit_no/4)      # nibble=4bit

    return ret


def get_doy(doy, ret):
    """
    combine all doy parts to make doy integer,
    delete all doy parts, replace with integer doy
    : doy param: list of all field start with 'first_shot_point_doy'
    : ret param: OrderedDict returned from Construct.parse()
    """
    doy_str = ''
    for d in doy:
        doy_str += str(d[1])
        del ret[d[0]]           # delete key
    ret.__keys_order__.insert(ret.__keys_order__.index('hour_of_day_utc'),
                              'first_shot_point_doy')
    ret['first_shot_point_doy'] = int(doy_str)
    return ret


def general_header_block(keys):
    swap = True
    if sys.byteorder == 'big':
        swap = False
    fields = []
    # swap with bcd only
    for k in keys:
        if len(k) < 3 or k[2] == 'signed':
            f = construct.BitField(k[0], k[1])
        elif k[2] == 'bcd':
            f = construct.BitField(k[0], k[1], swapped=swap)
        else:
            f = construct.BitField(k[0], k[1])
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
        doy = []
        has_doy = False
        for k in self.keys:
            if 'first_shot_point_doy' in k[0]:
                doy.append((k[0], ret[k[0]]))
                has_doy = True
            if 'fraction' in k[0]:
                ret[k[0]] = convert_fixed_point_binary_16bit(ret[k[0]])
            if len(k) < 3 or k[0] in ['record_length']:
                continue
            if k[2] == 'bcd':
                ret[k[0]] = convert_bcd_field(ret[k[0]], k[1])
            elif k[2] == 'signed':
                ret[k[0]] = unsigned2signed(ret[k[0]], k[1])
        if has_doy:
            get_doy(doy, ret)
        return ret


class General_header_block (Header_block):

    def __init__(self, n):
        super(General_header_block, self).__init__()
        if n == 0:
            # (key, number of bits, bcd/signed/_)
            self.keys = (
                ("file_number", 2*8, 'bcd'),                        # 0-9999
                ("data_sample_format_code", 2*8, 'bcd'),            # 8058
                ("general_constant_1", 8, 'bcd'),
                ("general_constant_2", 8, 'bcd'),
                ("general_constant_3", 8, 'bcd'),
                ("general_constant_4", 8, 'bcd'),
                ("general_constant_5", 8, 'bcd'),
                ("general_constant_6", 8, 'bcd'),                   # 05
                ("first_shot_point_year", 8, 'bcd'),                # 0-99
                ("number_additional_general_header_blocks", 8/2),   # 2
                # defined bcd in doc but it doesn't give correct result w/ bcd
                ("first_shot_point_doy1", 8/2),                      # 1-366
                ("first_shot_point_doy2", 8/2),
                ("first_shot_point_doy3", 8/2),
                # doc: 1 bytes for HHMMSS
                # but Byte No.=14-16 which actually 3 bytes
                ("hour_of_day_utc", 8, 'bcd'),
                ("minute_of_hour_utc", 8, 'bcd'),
                ("second_of_minute_utc", 8, 'bcd'),
                ("manufactures_code", 8, 'bcd'),                    # 0x61
                ("manufactures_sn", 2*8, 'bcd'),                    # 0
                ("bytes_per_scan", 3*8, 'bcd'),
                # 4:.25ms; 8:.5ms; 10:1ms; 20:2ms; 40: 4ms
                ("base_scan_interval", 8),
                # 0 = Untested; 4=135degrees; 8= 315 degrees; 1=Zero
                # 5= 180 degree; 12= unassigned; 2= 45 degrees
                # 6= 225 degrees; 3= 90 degrees; 7= 270 degrees
                ("polarity", 8/2),
                # 0: SG; 1:RG; 2:CG
                # doc 1-1/2 but byte is 24L only
                ("gather_type", 8/2),
                ("not_used", 8),
                # 8:normal; 2:test record
                ("record_type", 8/2),                               # 8
                # extended_record_length used
                ("record_length", 3*8/2, 'bcd'),                    # FFF
                ("scan_types_per_record", 8, 'bcd'),                # 1
                ("chan_sets_per_scan", 8, 'bcd'),                   # 16
                ("number_sample_skew_32_extensions", 8, 'bcd'),     # 00
                ("extended_header_length", 8, 'bcd'),
                ("external_header_length", 8, 'bcd'))

        if n == 1:
            self. keys = (
                ("extended_file_number", 3*8),
                ("extended_channel_set_per_scan_type", 2*8),        # 0
                ("extended_header_blocks", 2*8),                    # 0
                # doc 3bytes but say at byte 8-9 which is 2 bytes
                ("number_32-byte_fields_in_external_header", 2*8),  # 0
                ("not_used", 8),
                ("SEGD_revision_number1", 8),                       # 1.0
                ("SEGD_revision_number2", 8),  # 1.0
                ("number_32-byte_general_trailer_blocks", 2*8),     # 0
                # 0-128000ms
                ("extended_record_length", 3*8),
                ("undefined1", 8),                                  # 0
                ("general_header_block_number", 8),                 # 2
                ("undefined2", 13*8))                               # 0
        if n == 2:
            self.keys = (
                ("expanded_file_number", 3*8),
                ("source_line_number_integer", 3*8),
                ("source_line_number_fraction", 2*8),
                ("source_point_number_integer", 3*8),
                ("source_point_number_fraction", 2*8),
                ("source_point_index", 8),
                ("phase_control", 8),                               # 0
                ("vibrator_type", 8),                               # 0
                ("phase_angle", 2*8),                               # 0
                ("general_header_block_number", 8),                 # 3
                ("source_set_number_default", 8),
                ("not_used", 12*8))                                 # 0


class Channel_set_descriptor (Header_block):
    # (key, number of bits, bcd/signed/_)
    keys = (("scan_type_number", 8, 'bcd'),                         # 01
            ("chan_set_number", 8, 'bcd'),
            ("chan_set_start_time_ms", 2*8),                        # ms
            ("chan_set_end_time_ms", 2*8),                          # ms
            ("optional_MP_factor_extension_byte", 8),
            ("MP_factor_descaler_multiplier", 8),
            ("number_of_chans_in_chan_set", 2*8, 'bcd'),
            # 1=Seis; 9=Aux
            ("chan_type_code", 8/2),
            ("not_used", 8/2),                                      # 0
            ("number_sub-scans", 8/2, 'bcd'),                       # 0
            ("gain_control_type", 8/2),                             # 3
            ("alias_filter_freq_Hz", 2*8, 'bcd'),
            ("alias_filter_slope_dB_per_octave", 2*8, 'bcd'),
            ("low_cut_filter_freq_Hz", 2*8, 'bcd'),
            ("low_cut_filter_slope_db_per_octave", 2*8, 'bcd'),
            ("first_notch_filter_freq", 2*8, 'bcd'),                # 0
            ("second_notch_filter_freq", 2*8, 'bcd'),               # 0
            ("third_notch_filter_freq", 2*8, 'bcd'),                # 0
            ("extended_chan_set_number", 2*8),                      # 0
            ("extended_header_flag", 8/2),                          # 0
            ("number_trace_header_extensions", 8/2),                # 7
            ("vertical_stack_size", 8),                             # 1
            ("streamer_cable_number", 8),                           # 0 in land
            ("array_forming", 8))                                   # 1


class Extended_header_block (Header_block):
    # (key, number of bits, bcd/signed/_)
    keys = (("acquisition_length", 4*8),
            ("sample_rate_microsec", 4*8),
            ("number_of_traces", 4*8),
            ("number_of_samples_in_traces", 4*8),
            ("number_of_seis_traces", 4*8),
            ("number_of_auxes", 4*8),
            ("number_of_dead_seis_traces", 4*8),
            ("number_of_live_seis_traces", 4*8),
            # 0: no source, 1: impulsive
            ("source_type", 4*8),
            # 0:shot/ 1:receiver/ 2:continuous receiver
            ("gather_type", 2*8),
            ("reserved", 986*8))


class External_header_block (Header_block):
    # (key, number of bits, bcd/signed/_)
    keys = (("field_file_number", 4*8),                         # External FFID
            ("file_number", 4*8),
            ("souce_easting_cm", 4*8),
            ("source_northing_cm", 4*8),
            ("source_elevation_cm", 4*8),
            ("source_or_receiver_GPS_lat_integer", 4*8),        # DDMMSS.sss
            ("source_or_receiver_GPS_lat_fraction", 2*8),       # DDMMSS.sss
            ("source_or_receiver_GPS_lon_integer", 4*8),        # DDMMSS.sss
            ("source_or_receiver_GPS_lon_fraction", 2*8),       # DDMMSS.sss
            ("TB_GPS_time_ms", 8*8),
            ("not_used", 2*8),
            ("source_GPS_height_cm", 4*8),
            ("reserved", 978*8))


class Trace_header (Header_block):
    # (key, number of bits, bcd/signed/_)
    # filenumber = 0-9999, if >9999, set to FFFF, extended file number is used
    keys = (("4_digit_file_number", 2*8, 'bcd'),
            ("scan_type", 8, 'bcd'),                            # 01
            ("channel_set", 8, 'bcd'),
            ("trace_number", 2*8, 'bcd'),
            ("first_timing_word", 3*8),                         # Bin24
            ("trace_extension_blocks", 8),                      # 7 Bin8
            ("sample_skew_value", 8),
            # 00 No edit applied; 02: muted or dead prior to qcquisition
            ("trace_edit_code", 8),
            ("time_break_window", 3*8),                         # Bin24
            ("extended_channel_set", 2*8),                      # 0 Bin16
            ("extended_file_number", 3*8))                      # Bin16


class Trace_header_extension(Header_block):

    def __init__(self, n):
        # (key, number of bits, bcd/signed/_)
        super(Trace_header_extension, self).__init__()
        if n == 0:
            self.keys = (
                ("receiver_line_number", 3*8, 'signed'),
                ("receiver_point_number", 3*8, 'signed'),
                ("receiver_point_index", 8),
                ("samples_per_trace", 3*8),
                ("extended_receiver_line_number_integer", 3*8, 'signed'),
                ("extended_receiver_line_number_fraction", 2*8),
                ("extended_receiver_point_number_integer", 3*8, 'signed'),
                ("extended_receiver_point_number_fraction", 2*8),
                ("not_used", 12*8))
        if n == 1:
            self.keys = (
                ("TB_GPS_time_microsec", 8*8),
                ("TB offset_microsec", 2*8),
                ("external_file_id", 4*8),
                ("not_used", 14*8),
                ("extended_trace_number", 4*8))
        if n == 2:
            self.keys = (
                ("receiver_easting_4_bytes_integer_cm", 4*8),
                ("receiver_northing_4_bytes_integer_cm", 4*8),
                ("receiver_elevation_4_bytes_integer_cm", 4*8),
                ("not_used", 20*8))
        if n == 3:
            self.keys = (
                ("IGU_GPS_lat_integer", 4*8, "signed"),  # new format=>signed
                ("IGU_GPS_lat_fraction", 2*8),
                ("IGU_GPS_lon_integer", 4*8, "signed"),  # new format=>signed
                ("IGU_GPS_lon_fraction", 2 * 8),
                ("IGU_GPS_height", 4*8),                              # float
                ("not_used", 16*8))
        if n == 4:
            self.keys = (("not_used", 32*8),)
        if n == 5:
            self.keys = (
                ("unit_type", 8),
                ("unit_serial_number", 4*8),
                ("channel_number", 8),
                ("not_used", 26*8))
        if n == 6:
            self.keys = (
                ("not_used", 32*8),)
