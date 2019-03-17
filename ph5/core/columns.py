#
# This file defines the table organization of the PIC Kitchen HDF5 file,
# File suffix is ph5, and named: experimentnickname[nnn].ph5.
# Overall organization is defined in the Experiment module.
# Several mixins defined at end
# of this file.
#
# Overall Organization
# (as of October 2006, revised July 2007, revised April 2016)
# Groups and Tables
# _g is a grouping structure defined in Experiment module
# _t is a table as defined in this file,
#   instance defined in Experiment module
# _a is an array as defined in Experiment module
# Columns
# _a string name of array
# _i 8, 16, 32 bit integer
# _l 64 bit integer
# _f 32 bit float
# _d 64 bit float
# _s string
#
# /Experiment_g
#              /Experiment_t
#              /Maps_g
#                      /Das_g_[nnnn]
#                              /Hdr_a_[nnnn]
#                      /Sta_g_[nnnn]
#                      /Evt_g_[nnnn]
#                      */Guides_g_[nnnn]
#                              */Guide_t
#                              */Fn_a_[nnnn]
#                      */Blush_t
#                              *out_s
#                              *sub_s
#                              *n_i
#              /Sorts_g
#                      /Sort_t
#                      /Array_t_[nnn]
#                      */Offset_t(_[aaa]_[sss]) aaa -> array number,
#                                           sss -> shot line number
#                      */Event_t(_[nnn])
#              /Receivers_g
#                      /Das_g_[das_sn]
#                              /Das_t
#                              /Data_a_[nnnn]
#                              /SOH_a_[nnnn]
#                              /Event_a_[nnnn]
#                              /Log_a_[nnnn]
#                      /Time_t
#                      /Receiver_t
#                      /Index_t
#              /Reports_g
#                      /Report_t
#                      /Report_name
#              /Responses_g
#                      /Response_t
#                              /gain
#                                      /value_d
#                                      /units_s
#                              /bit_weight
#                                      /value_d
#                                      /units_s
#                     /Response_a_[n]   *** PZ or RESP file
#
#
# Steve Azevedo, August 21, 2006
#

import tables
import types
import os
import string
import logging

PH5VERSION = '4.1.2'
PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)

#  TIME_TYPE = tables.Enum (['EPOCH', 'ASCII', 'BOTH'])

# Nested column descriptors
# class Units32 (tables.IsDescription) :
# '''   32 bit float with units   '''
# units             = tables.StringCol (16)
# value             = tables.Float32Col ()

# class Units64 (tables.IsDescription) :
# '''   64 bit float with units   '''
# units             = tables.StringCol (16)
# value             = tables.Float64Col ()

# class Location (tables.IsDescription) :
# '''   Geographic position   '''
# coordinate_system = tables.StringCol (32) # UTM etc.
# projection        = tables.StringCol (32)  # Albers etc.
# ellipsoid         = tables.StringCol (32)  # WGS-84 etc.
# X                 = Units64 ()  # Latitude, Northing, etc.
# class X (tables.IsDescription) :
# units             = tables.StringCol (16)
# value             = tables.Float64Col ()
# Y                 = Units64 ()   # Longitude, Easting, etc.
# class Y (tables.IsDescription) :
# units             = tables.StringCol (16)
# value             = tables.Float64Col ()
# Z                 = Units64 ()   # Elevation
# class Z (tables.IsDescription) :
# units             = tables.StringCol (16)
# value             = tables.Float64Col ()
##
# description       = tables.StringCol (1024) # Any additional
# comments

# Need to define accepted refrences for Z

# class Time (tables.IsDescription) :
# '''   Time, either epoch or human readable   '''
# type        = tables.EnumCol (TIME_TYPE, 'EPOCH')#'EPOCH', 'ASCII', or 'BOTH'
# epoch       = tables.Int64Col ()             # Seconds since January 1, 1970
# ascii       = tables.StringCol (24)           # WWW MMM DD HH:MM:SS YYYY
# micro_seconds = tables.Int32Col ()

# class Instrument (tables.IsDescription) :
# '''   Generalized instrument of some sort   '''
# manufacturer      = tables.StringCol (64)
# model             = tables.StringCol (64)
# serial_number     = tables.StringCol (64)
# notes             = tables.StringCol (1024)

# versioning/firmware etc.should be included
# Define new table to reference Instrument type to response (require
# sensitivity).

# class Orientation (tables.IsDescription) :
# '''   Orientation of sensor   '''
# dip               = Units32 ()                         # Zero is up
# class dip (tables.IsDescription) :
# '''   32 bit float with units   '''
# units             = tables.StringCol (16)
# value             = tables.Float32Col ()
# azimuth           = Units32 ()                         # Zero is north
# class azimuth (tables.IsDescription) :
# '''   32 bit float with units   '''
# units             = tables.StringCol (16)
# value             = tables.Float32Col ()

# Enumeration for convention of Orientation Use SEED way by default

# Column descriptions: XXX THE MEAT STARTS HERE XXX


class Experiment (tables.IsDescription):
    # time_stamp        = Time ()                            # Time stamp
    # for these entries
    class time_stamp (tables.IsDescription):
        '''   Time, either epoch or human readable   '''
        type_s = tables.StringCol(
            8)               # 'EPOCH', 'ASCII', or 'BOTH'
        epoch_l = tables.Int64Col()            # Seconds since January 1, 1970
        ascii_s = tables.StringCol(32)         # WWW MMM DD HH:MM:SS YYYY
        micro_seconds_i = tables.Int32Col()
    #
    # Experiment ID, YY-nnn (Added Feb 25, 2013)
    experiment_id_s = tables.StringCol(8, pos=1)
    net_code_s = tables.StringCol(8, pos=2)
    nickname_s = tables.StringCol(32, pos=3)  # Experiment nickname
    longname_s = tables.StringCol(256, pos=4)  # Experiment name
    PIs_s = tables.StringCol(1024, pos=5)  # Experiment principal investigators
    institutions_s = tables.StringCol(1024, pos=6)  # Institutions
    # north_west_corner = Location ()                        # Bounding box
    # nw corner

    class north_west_corner (tables.IsDescription):
        '''   Geographic position   '''
        _v_pos = 7
        # UTM etc.
        coordinate_system_s = tables.StringCol(32, pos=4)
        projection_s = tables.StringCol(32, pos=5)              # Albers etc.
        ellipsoid_s = tables.StringCol(32, pos=6)              # WGS-84 etc.
        # X                 = Units64 ()                         # Latitude,
        # Northing, etc.

        class X (tables.IsDescription):
            _v_pos = 1
            units_s = tables.StringCol(16)
            value_d = tables.Float64Col(pos=1)
        # Y                 = Units64 ()                         # Longitude,
        # Easting, etc.

        class Y (tables.IsDescription):
            _v_pos = 2
            units_s = tables.StringCol(16)
            value_d = tables.Float64Col(pos=1)
        # Z                 = Units64 ()                         # Elevation

        class Z (tables.IsDescription):
            _v_pos = 3
            units_s = tables.StringCol(16)
            value_d = tables.Float64Col(pos=1)
        #
        # Any additional comments
        description_s = tables.StringCol(1024, pos=7)
    # south_east_corner = Location ()                        # Bounding box
    # se corner

    class south_east_corner (tables.IsDescription):
        '''   Geographic position   '''
        _v_pos = 8
        # UTM etc.
        coordinate_system_s = tables.StringCol(32, pos=4)
        projection_s = tables.StringCol(32, pos=5)              # Albers etc.
        ellipsoid_s = tables.StringCol(32, pos=6)              # WGS-84 etc.
        # X                 = Units64 ()                         # Latitude,
        # Northing, etc.

        class X (tables.IsDescription):
            _v_pos = 1
            units_s = tables.StringCol(16)
            value_d = tables.Float64Col(pos=1)
        # Y                 = Units64 ()                         # Longitude,
        # Easting, etc.

        class Y (tables.IsDescription):
            _v_pos = 2
            units_s = tables.StringCol(16)
            value_d = tables.Float64Col(pos=1)
        # Z                 = Units64 ()                         # Elevation

        class Z (tables.IsDescription):
            _v_pos = 3
            units_s = tables.StringCol(16)
            value_d = tables.Float64Col(pos=1)
        #
        # Any additional comments
        description_s = tables.StringCol(1024, pos=7)
    #
    summary_paragraph_s = tables.StringCol(
        2048, pos=9)  # Experiment description

# Need to generate experiment table with additions to what was in power point:
#  Short name, ie nick name
#  Principal Investigator
#  Change location to be bounding box
#  Net code, Report number,
#  Experiment number
#  Summary paragraph


class Data (tables.IsDescription):
    '''   Description of data table, each row refers to an event/trace   '''
    receiver_table_n_i = tables.Int32Col()
    response_table_n_i = tables.Int32Col()
    time_table_n_i = tables.Int32Col()
    #
    # start_time       = Time ()                             # Start time of
    # trace

    class time (tables.IsDescription):
        '''   Time, either epoch or human readable   '''
        type_s = tables.StringCol(
            8)               # 'EPOCH', 'ASCII', or 'BOTH'
        epoch_l = tables.Int64Col()        # Seconds since January 1, 1970
        ascii_s = tables.StringCol(32)              # WWW MMM DD HH:MM:SS YYYY
        micro_seconds_i = tables.Int32Col()
    #
    event_number_i = tables.Int32Col()  # Event number
    channel_number_i = tables.Int8Col()  # Channel number
    sample_rate_i = tables.Int16Col()  # Trace sample rate
    # This will be needed for sample rates < 1 sps
    sample_rate_multiplier_i = tables.Int16Col()
    sample_count_i = tables.Int32Col()  # Version 2007.191a bleeding
    stream_number_i = tables.Int8Col()  # Stream
    raw_file_name_s = tables.StringCol(32)  # Original file name
    # Name of array that contains trace
    array_name_data_a = tables.StringCol(16)
    array_name_SOH_a = tables.StringCol(16)  # The SOH array name
    array_name_event_a = tables.StringCol(16)  # The event table array
    array_name_log_a = tables.StringCol(16)  # The log array


# Sample rate, int sample interval like SEGY (micro-seconds) or like SEED
# (BLOCKETTE 100)?

class Time (tables.IsDescription):
    '''   Time correction table   '''
    class das (tables.IsDescription):
        manufacturer_s = tables.StringCol(64, pos=3)
        model_s = tables.StringCol(64, pos=2)
        serial_number_s = tables.StringCol(64, pos=1)
        notes_s = tables.StringCol(1024, pos=4)
    # Time of first lock

    class start_time (tables.IsDescription):
        type_s = tables.StringCol(8)
        epoch_l = tables.Int64Col()
        ascii_s = tables.StringCol(32)
        micro_seconds_i = tables.Int32Col()
    # Time of ending lock

    class end_time (tables.IsDescription):
        type_s = tables.StringCol(8)
        epoch_l = tables.Int64Col()
        ascii_s = tables.StringCol(32)
        micro_seconds_i = tables.Int32Col()

    slope_d = tables.Float64Col()  # Slope
    offset_d = tables.Float64Col()  # Offset at end time
    description_s = tables.StringCol(1024)
    corrected_i = tables.Int16Col()


class Receiver (tables.IsDescription):
    '''   Additional information about sensor   '''
    # class deploy_time (tables.IsDescription) :
    # '''   Time, either epoch or human readable   '''
    # type_e = tables.EnumCol (TIME_TYPE, 'EPOCH')# 'EPOCH', 'ASCII', or 'BOTH'
    # epoch_l = tables.Int64Col ()        # Seconds since January 1, 1970
    # ascii_s  = tables.StringCol (32)              # WWW MMM DD HH:MM:SS YYYY
    # micro_seconds_i     = tables.Int32Col ()
    # class pickup_time (tables.IsDescription) :
    # '''   Time, either epoch or human readable   '''
    # type_e = tables.EnumCol (TIME_TYPE, 'EPOCH')# 'EPOCH', 'ASCII', or 'BOTH'
    # epoch_l = tables.Int64Col ()        # Seconds since January 1, 1970
    # ascii_s  = tables.StringCol (32)              # WWW MMM DD HH:MM:SS YYYY
    # micro_seconds_i     = tables.Int32Col ()
    # das              = Instrument ()                # The digitizer
    # class das (tables.IsDescription) :
    # '''   Generalized instrument of some sort   '''
    # manufacturer_s      = tables.StringCol (64)
    # model_s             = tables.StringCol (64)
    # serial_number_s     = tables.StringCol (64)
    # notes_s             = tables.StringCol (1024)
    # Should sensor info be moved to its own table?
    # sensor           = Instrument ()           # The geophone/seismometer
    # class sensor (tables.IsDescription) :
    # '''   Generalized instrument of some sort   '''
    # manufacturer_s      = tables.StringCol (64)
    # model_s             = tables.StringCol (64)
    # serial_number_s     = tables.StringCol (64)
    # notes_s             = tables.StringCol (1024)
    # location         = Location ()                    # The location
    # class location (tables.IsDescription) :
    # '''   Geographic position   '''
    # coordinate_system_s = tables.StringCol (32)       # UTM etc.
    # projection_s        = tables.StringCol (32)       # Albers etc.
    # ellipsoid_s         = tables.StringCol (32)       # WGS-84 etc.
    # X                 = Units64 ()                 # Latitude, Northing, etc.
    # class X (tables.IsDescription) :
    # units_s             = tables.StringCol (16)
    # value_d             = tables.Float64Col ()
    # Y                 = Units64 ()                 # Longitude, Easting, etc.
    # class Y (tables.IsDescription) :
    # units_s             = tables.StringCol (16)
    # value_d             = tables.Float64Col ()
    # Z                 = Units64 ()                         # Elevation
    # class Z (tables.IsDescription) :
    # units_s             = tables.StringCol (16)
    # value_d             = tables.Float64Col ()
    ##
    # description_s       = tables.StringCol (1024) # Any additional comments
    # orientation      = Orientation ()             # Orientation
    # of geophone/seismometer
    class orientation (tables.IsDescription):
        '''   Orientation of sensor   '''
        # dip               = Units32 ()                        # Zero is up
        class dip (tables.IsDescription):
            '''   32 bit float with units   '''
            _v_pos = 2
            units_s = tables.StringCol(16)
            value_f = tables.Float32Col(pos=1)
        # azimuth           = Units32 ()                         # Zero is
        # north

        class azimuth (tables.IsDescription):
            '''   32 bit float with units   '''
            _v_pos = 1
            units_s = tables.StringCol(16)
            value_f = tables.Float32Col(pos=1)

        channel_number_i = tables.Int8Col()
        # Any additional comments
        description_s = tables.StringCol(1024, pos=3)


class Index (tables.IsDescription):
    '''   Index for multiple file ph5, /Experiment_g/Receivers_g/Index_t   '''
    external_file_name_s = tables.StringCol(
        32)  # Name of external file. Example: 08-005_0001_of_0009
    hdf5_path_s = tables.StringCol(64)  # HDF5 path in external file.
    # Example: /Experiment_g/Receivers_g/Das_g_xxxxx
    serial_number_s = tables.StringCol(64)  # DAS serial number
    # Time stamp (last write time)

    class time_stamp (tables.IsDescription):
        type_s = tables.StringCol(8)
        epoch_l = tables.Int64Col()
        ascii_s = tables.StringCol(32)
        micro_seconds_i = tables.Int32Col()
    # First sample time

    class start_time (tables.IsDescription):
        type_s = tables.StringCol(8)
        epoch_l = tables.Int64Col()
        ascii_s = tables.StringCol(32)
        micro_seconds_i = tables.Int32Col()
    # Last sample time

    class end_time (tables.IsDescription):
        type_s = tables.StringCol(8)
        epoch_l = tables.Int64Col()
        ascii_s = tables.StringCol(32)
        micro_seconds_i = tables.Int32Col()

# class Sort (tables.IsDescription) :
    # '''   Table to describe a data subset, such as a gather.
    # Also associates an instrument with a location on the ground   '''
    # id               = tables.StringCol (16)     # Station ID/stake number
    # receiver_sn      = tables.StringCol (64)     # DAS serial number
    # channel_number   = tables.Int8Col ()         # Channel number
    # start_time       = Time ()                   # Start time
    # end_time         = Time ()                   # End time
    # array_name       = tables.StringCol (16)     # Name of array
    # that contains the trace

# Time stamp on sort table
# Save information about requestor


class Sort (tables.IsDescription):
    '''   Provides a way to group data   '''
    event_id_s = tables.StringCol(16)  # The event that this covers
    array_name_s = tables.StringCol(16, pos=2)  # Name of array
    # time_stamp       = Time ()                              # Time this
    # was first requested

    class time_stamp (tables.IsDescription):
        '''   Time, either epoch or human readable   '''
        _v_pos = 6
        # 'EPOCH', 'ASCII', or 'BOTH'
        type_s = tables.StringCol(8)
        epoch_l = tables.Int64Col()             # Seconds since January 1, 1970
        ascii_s = tables.StringCol(32)          # WWW MMM DD HH:MM:SS YYYY
        micro_seconds_i = tables.Int32Col()
    #
    array_t_name_s = tables.StringCol(16, pos=1)  # Name Array_t
    # start_time       = Time ()                              # Deployment
    # time of array

    class start_time (tables.IsDescription):
        '''   Time, either epoch or human readable   '''
        _v_pos = 3
        type_s = tables.StringCol(8)  # 'EPOCH', 'ASCII', or 'BOTH'
        # Seconds since January 1, 1970
        epoch_l = tables.Int64Col(pos=2)
        # WWW MMM DD HH:MM:SS YYYY
        ascii_s = tables.StringCol(32, pos=1)
        micro_seconds_i = tables.Int32Col(pos=3)
    # end_time         = Time ()                              # Pickup time
    # of array

    class end_time (tables.IsDescription):
        '''   Time, either epoch or human readable   '''
        _v_pos = 4
        # 'EPOCH', 'ASCII', or 'BOTH'
        type_s = tables.StringCol(8, pos=4)
        # Seconds since January 1, 1970
        epoch_l = tables.Int64Col(pos=2)
        # WWW MMM DD HH:MM:SS YYYY
        ascii_s = tables.StringCol(32, pos=1)
        micro_seconds_i = tables.Int32Col(pos=3)
    #
    # Description of this data grouping
    description_s = tables.StringCol(1024, pos=5)


class Array (tables.IsDescription):
    '''   Provides a way to group stations   '''
    class deploy_time (tables.IsDescription):
        '''   Time, either epoch or human readable   '''
        _v_pos = 3
        type_s = tables.StringCol(8, pos=4)  # 'EPOCH', 'ASCII', or 'BOTH'
        epoch_l = tables.Int64Col(pos=2)        # Seconds since January 1, 1970
        # WWW MMM DD HH:MM:SS YYYY
        ascii_s = tables.StringCol(32, pos=1)
        micro_seconds_i = tables.Int32Col(pos=3)

    class pickup_time (tables.IsDescription):
        '''   Time, either epoch or human readable   '''
        _v_pos = 4
        type_s = tables.StringCol(8, pos=4)    # 'EPOCH', 'ASCII', or 'BOTH'
        epoch_l = tables.Int64Col(pos=2)        # Seconds since January 1, 1970
        # WWW MMM DD HH:MM:SS YYYY
        ascii_s = tables.StringCol(32, pos=1)
        micro_seconds_i = tables.Int32Col(pos=3)
    # order_i            = tables.Int32Col ()       #  Order of trace in gather
    # event_number_i     = tables.Int32Col ()       #  Event number
    id_s = tables.StringCol(16, pos=1)  # Stake ID
    # das              = Instrument ()              #  Instrument
    # at stake

    class das (tables.IsDescription):
        '''   Time, either epoch or human readable   '''
        _v_pos = 5
        manufacturer_s = tables.StringCol(64, pos=3)
        model_s = tables.StringCol(64, pos=2)
        serial_number_s = tables.StringCol(64, pos=1)
        notes_s = tables.StringCol(1024, pos=5)

    class sensor (tables.IsDescription):
        '''   Generalized instrument of some sort   '''
        _v_pos = 6
        manufacturer_s = tables.StringCol(64, pos=3)
        model_s = tables.StringCol(64, pos=2)
        serial_number_s = tables.StringCol(64, pos=1)
        notes_s = tables.StringCol(1024, pos=4)
    # location         = Location ()                         # The location

    class location (tables.IsDescription):
        '''   Geographic position   '''
        _v_pos = 2
        # UTM etc.
        coordinate_system_s = tables.StringCol(32, pos=4)
        projection_s = tables.StringCol(32, pos=5)              # Albers etc.
        ellipsoid_s = tables.StringCol(32, pos=6)              # WGS-84 etc.
        # X                 = Units64 ()                         # Latitude,
        # Northing, etc.

        class X (tables.IsDescription):
            _v_pos = 1
            units_s = tables.StringCol(16)
            value_d = tables.Float64Col(pos=1)
        # Y                 = Units64 ()                         # Longitude,
        # Easting, etc.

        class Y (tables.IsDescription):
            _v_pos = 2
            units_s = tables.StringCol(16)
            value_d = tables.Float64Col(pos=1)
        # Z                 = Units64 ()                         # Elevation

        class Z (tables.IsDescription):
            _v_pos = 3
            units_s = tables.StringCol(16)
            value_d = tables.Float64Col(pos=1)

        # Any additional comments
        description_s = tables.StringCol(1024, pos=7)
    # class start_time (tables.IsDescription) :
        # type_e = tables.EnumCol (TIME_TYPE, 'EPOCH')#'EPOCH','ASCII',or'BOTH'
        # epoch_l = tables.Int64Col ()          # Seconds since January 1, 1970
        # ascii_s = tables.StringCol (32)       # WWW MMM DD HH:MM:SS YYYY
        # micro_seconds_i = tables.Int32Col ()
    #
    # data_array_a       = tables.StringCol (16)                # Name of
    # data array
    channel_number_i = tables.Int8Col()  # Channel number
    # SEEDling (This belongs in the Maps_g!)
    seed_band_code_s = tables.StringCol(1, pos=8)
    # Trace sample rate (samples per second)
    sample_rate_i = tables.Int16Col(pos=9)
    # This will be needed for sample rates < 1 sps
    sample_rate_multiplier_i = tables.Int16Col(pos=10)
    seed_instrument_code_s = tables.StringCol(1, pos=11)
    seed_orientation_code_s = tables.StringCol(1, pos=12)
    seed_location_code_s = tables.StringCol(2, pos=13)
    seed_station_name_s = tables.StringCol(5, pos=14)
    response_table_n_i = tables.Int32Col()  # Offset into Response_t
    receiver_table_n_i = tables.Int32Col()  # Offset into Receiver_t
    # Description of this station grouping
    description_s = tables.StringCol(1024, pos=7)


class Event (tables.IsDescription):
    '''   Table to describe an event, such as a shot   '''
    id_s = tables.StringCol(16, pos=1)  # Event ID/stake number
    # location         = Location ()                         # Location of
    # event

    class location (tables.IsDescription):
        '''   Geographic position   '''
        _v_pos = 2
        # UTM etc.
        coordinate_system_s = tables.StringCol(32, pos=4)
        projection_s = tables.StringCol(32, pos=5)              # Albers etc.
        ellipsoid_s = tables.StringCol(32, pos=6)              # WGS-84 etc.
        # X                 = Units64 ()                         # Latitude,
        # Northing, etc.

        class X (tables.IsDescription):
            _v_pos = 1
            units_s = tables.StringCol(16)
            value_d = tables.Float64Col(pos=1)
        # Y                 = Units64 ()                         # Longitude,
        # Easting, etc.

        class Y (tables.IsDescription):
            _v_pos = 2
            units_s = tables.StringCol(16)
            value_d = tables.Float64Col(pos=1)
        # Z                 = Units64 ()                         # Elevation

        class Z (tables.IsDescription):
            _v_pos = 3
            units_s = tables.StringCol(16)
            value_d = tables.Float64Col(pos=1)
        # Any additional comments
        description_s = tables.StringCol(1024, pos=7)
    # time             = Time ()                             # Time of event

    class time (tables.IsDescription):
        '''   Time, either epoch or human readable   '''
        _v_pos = 3
        # 'EPOCH', 'ASCII', or 'BOTH'
        type_s = tables.StringCol(8, pos=4)
        # Seconds since January 1, 1970
        epoch_l = tables.Int64Col(pos=2)
        # WWW MMM DD HH:MM:SS YYYY
        ascii_s = tables.StringCol(32, pos=1)
        micro_seconds_i = tables.Int32Col(pos=3)
    # size             = Units64 ()                          # Size of
    # event, lbs of dynamite, Mb etc.

    class size (tables.IsDescription):
        '''   64 bit float with units   '''
        _v_pos = 4
        units_s = tables.StringCol(16)
        value_d = tables.Float64Col(pos=1)
    # depth            = Units64 ()                          # Depth of event

    class depth (tables.IsDescription):
        '''   64 bit float with units   '''
        _v_pos = 5
        units_s = tables.StringCol(16)
        value_d = tables.Float64Col(pos=1)
    #
    description_s = tables.StringCol(1024, pos=6)  # Description of event
# Change description to comment globally


class Report (tables.IsDescription):
    '''   Table to describe data reports   '''
    title_s = tables.StringCol(64)  # Title of report, report number
    format_s = tables.StringCol(32)  # Format report is in, pdf, odt, doc, etc.
    description_s = tables.StringCol(1024)  # Description of report
    # Name of the array that contains the report
    array_name_a = tables.StringCol(32)

# Allow URL to report.
# Define formats or,
# Define rigid format such as PDF (best).


class Offset (tables.IsDescription):
    '''   Offsets from events to receivers   '''
    event_id_s = tables.StringCol(16)  # Event ID
    receiver_id_s = tables.StringCol(16)  # Receiver ID
    # offset           = Units64 ()                           # The distance

    class offset (tables.IsDescription):
        '''   64 bit float with units   '''
        units_s = tables.StringCol(16)
        value_d = tables.Float64Col(pos=1)
    # azimuth

    class azimuth (tables.IsDescription):
        '''   32 bit float with units   '''
        units_s = tables.StringCol(16)
        value_f = tables.Float32Col(pos=1)

# Azimuth optional field.
# Define rigid units as meters like SEED.
# Allow negative and positive offsets


class Response (tables.IsDescription):
    n_i = tables.Int32Col(pos=1)  # Response number
    # gain_i                  = tables.Int16Col (pos=2)         # Gain

    class gain (tables.IsDescription):
        units_s = tables.StringCol(16)
        value_i = tables.Int16Col()
    # bit_weight_d            = tables.Float64Col (pos=3)      # Bit weight
    # nV/count

    class bit_weight (tables.IsDescription):
        '''   64 bit float with units   '''
        _v_pos = 3
        units_s = tables.StringCol(16)  # Volts/Count?
        value_d = tables.Float64Col(pos=1)

    response_file_a = tables.StringCol(32)  # Response file name
    response_file_das_a = tables.StringCol(128)  # DAS Response file name
    response_file_sensor_a = tables.StringCol(128)  # Sensor Response file name


#
# -=-=-=-=-=-=-=-=-=-= Mixins =-=-=-=-=-=-=-=-=-=-
#

# Table name to handle lookup
TABLES = {}


def add_reference(key, ref):
    if isinstance(key, types.StringType):
        key = key.strip()

    TABLES[key] = ref


LAST_ARRAY_NODE_MAPS = {}


def add_last_array_node_maps(mapsgroup, key, ref):
    name = mapsgroup._v_name
    if name not in LAST_ARRAY_NODE_MAPS:
        LAST_ARRAY_NODE_MAPS[name] = {}

    LAST_ARRAY_NODE_MAPS[name][key] = ref


LAST_ARRAY_NODE_DAS = {}


def add_last_array_node_das(dasgroup, key, ref):
    name = dasgroup._v_name
    if name not in LAST_ARRAY_NODE_DAS:
        LAST_ARRAY_NODE_DAS[name] = {}

    LAST_ARRAY_NODE_DAS[name][key] = ref


def rowstolist(rows, keys):
    retl = []
    for r in rows:
        retd = {}
        for k in keys:
            retd[k] = r[k]

        retl.append(retd)

    return retl


def _flatten(sequence, result=None, pre=None):
    '''
          Read in a nested list sequence as returned by table.colnames
          and flatten it into a dictionary of table column key.
          Inputs: sequence -- nested structure as returned by table.colnames
                  result -- A dictionary holding keys
                  pre -- A list holding node names
          Output: result -- As above
    '''
    if result is None:
        result = {}

    if pre is None:
        pre = []

    # Loop through each item
    for item in sequence:
        # This is a leaf, so add it to the result
        # print item
        if isinstance(item, str):
            # If this leaf has a node above it then include it
            if pre:
                key = string.join(pre, '/') + '/' + item
            else:
                key = item

            result[key] = True
        # This is not a leaf so push it on the stack and recurse
        elif isinstance(item, tuple):
            pre.append(item[0])
            item = item[1][:]
            _flatten(item, result, pre)
        else:
            # If we ever get here something is really wrong!
            print "oops: ", item

    if len(pre) > 0:
        pre.pop()

    return result


def keys(ltable):
    names = ltable.colnames
    all = []
    cols = ltable.cols._v_colpathnames
    try:
        all_keys = {}
        for k in ltable.colpathnames:
            all_keys[k] = True
    except AttributeError:
        all_keys = _flatten(names)

    for k in cols:
        if k in all_keys:
            all.append(k)

    return all, names

# XXX   Should required_keys be a single key???   XXX


def validate(ltable, p, required_keys=[]):
    '''
          Validate that key/value p has keys that match column names in ltable,
          and optionally that the required keys in list
          required_keys exist in p.
    '''
    fail_keys = []
    fail_required = []
    #
    # Try colpathnames, version 2 only, first
    try:
        all_keys = {}
        for k in ltable.colpathnames:
            all_keys[k] = True

    except AttributeError:
        all_keys = _flatten(ltable.colnames)

    for k in p.keys():
        if k not in all_keys:
            # Column does not exist so remove it from p
            del p[k]
            fail_keys.append("Error: No such column: " + k)

    for k in required_keys:
        if k not in p:
            fail_required.append("Error: Required key missing: " + k)

    return fail_keys, fail_required


def node(ph5, path, classname):
    handle = None
    dir, file = os.path.split(path)

    handle = ph5.get_node(dir, name=file, classname=classname)

    return handle


def _cast(vtype, val):
    if not vtype:
        return None

    if isinstance(val, types.StringType):
        val = val.strip()
        if val == "":
            val = None
        elif (vtype == 'Float64' or vtype == 'float64' or
              vtype == 'Float32' or vtype == 'float32'):
            try:
                val = float(val)
            except ValueError:
                val = None
        elif (vtype == 'Int64' or vtype == 'int64' or vtype == 'UInt32' or
              vtype == 'uint32'):
            try:
                val = long(val)
            except ValueError:
                val = None
        elif (vtype == 'Int32' or vtype == 'int32' or vtype == 'UInt32' or
              vtype == 'uint32'):
            try:
                val = int(val)
            except ValueError:
                val = None
        elif (vtype == 'Int16' or vtype == 'int16' or vtype == 'UInt16' or
              vtype == 'uint16'):
            try:
                val = int(val)
            except ValueError:
                val = None
        elif (vtype == 'Int8' or vtype == 'int8' or vtype == 'UInt8' or
              vtype == 'uint8'):
            try:
                val = int(val)
            except ValueError:
                val = None
    return val


def search(ltable, key, value):
    # XXX   More sophisticated searches using table.where???
    if isinstance(value, types.StringType):
        v = value.strip()

    for r in ltable.iterrows():
        if isinstance(r[key], types.StringType):
            rk = r[key].strip()
        else:
            rk = str(r[key])

        if rk == v:
            return r

    return None


def lindex(ltable, value, key):
    if isinstance(value, types.StringType):
        v = value.strip()

    i = 0
    for r in ltable.iterrows():
        if isinstance(r[key], types.StringType):
            rk = r[key].strip()
        else:
            rk = str(r[key])

        if rk == v:
            return i
        else:
            i = i + 1

    return None


def delete(ltable, value, key):
    r = lindex(ltable, value, key)
    if r is not None:
        ltable.remove_rows(r)
        ltable.flush()


def update(ltable, p, key):
    #
    # Find row and update
    #
    if isinstance(p[key], types.StringType):
        v = p[key].strip()

    # Not sure why this does not work using the search proceedure above?
    for r in ltable.iterrows():
        if isinstance(r[key], types.StringType):
            rk = r[key].strip()
        else:
            rk = str(r[key])

        if rk == v:
            for k in p.keys():
                try:
                    r.__setitem__(k, p[k])
                except IndexError:
                    # Not all columns need exist
                    pass

            r.update()

    ltable.flush()


def append(ltable, p):
    r = ltable.row
    try:
        vtypes = ltable.coltypes
    except AttributeError:
        vtypes = ltable.colstypes

    for k in p.keys():
        t = vtypes[k]
        # print k, t
        val = p[k]
        val = _cast(t, val)
        if val is None:
            continue

        try:
            r[k] = val
        except Exception as e:
            LOGGER.warning("Warning in append: Exception \'%s\'" % e)

    r.append()
    ltable.flush()


def is_mini(ltable):
    '''
       Check to see if this is an external file, and re-open 'a'
    '''
    from tables import openFile
    from re import compile
    # Das_t is always in an external file
    Das_tRE = compile("(/Experiment_g/Receivers_g/Das_g_.*)/Das_t")
    ltablepath = ltable._v_pathname
    if Das_tRE.match(ltablepath):
        ltablefile = ltable._v_file
        if ltablefile.mode != 'a':
            filename = ltablefile.filename
            ltablefile.close()
            mini = openFile(filename, 'a')
            ltable = mini.get_node(ltablepath)
            add_reference(ltablepath, ltable)

    return ltable


def populate(ltable, p, key=None):
    '''   Populate a row in the table ltable.
          p is a dictionary of key/values to update.
          If key is set then update, otherwise append.
    '''
    # ltable = is_mini (ltable)
    # key is set so update
    if key:
        if key in p:
            # print "update"
            update(ltable, p, key)
            # ltable.flush ()
        else:
            LOGGER.warning("No data for key. p.has_key (key) fails")
            return
    # no key so get a new row to append
    else:
        # print "append"
        append(ltable, p)
        # ltable.flush ()


if __name__ == '__main__':
    pass

# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

# Use dep file as standardized update format. Would need to be extended??


# Addition of picks table
