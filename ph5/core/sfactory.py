#!/usr/bin/env pnpython3

#
#   Build SEG-Y or PASSCAL SEGY file.
#
#   This sits between the code that talks to the ph5
#   file, and the code that generates the SEG file.
#
#   Steve Azevedo, August 2007
#

from ph5.core import segy_h, ebcdic
#from cs2cs import *
import math, numpy, os, time, string, sys

PROG_VERSION = "2013.232.2"

os.environ['TZ'] = 'UTC'
time.tzset ()

MAX_16 = 32767.
MAX_32 = 2147483648.

def __version__ () :
    print PROG_VERSION

#   Map channel number to Trace ID (29-30 in trace header)
#CHAN2TID = { 1:15, 2:16, 3:17, 4:15, 5:16, 6:17 }
CHAN2TID = { 1:1, 2:16, 3:17, 4:15, 5:16, 6:17 }
COUNTMULT = { 'nV/count':1000000000., 'uV/count':1000000., 'mV/count':1000., 'volts/count':1. }
EXT_HEADER_CHOICES = [ 'P', 'S', 'U', 'I' ]

class Ssegy :
    '''
       
    '''
    def __init__ (self,
                  #start_point,     #   Starting point integer
                  #length_points,   #   Number of points
                  #das_t,           #   Das_t row
                  sort_t,          #   Sort_t row
                  #array_t,         #   Array_t row
                  #time_t,          #   Time_t row
                  event_t,         #   Event_t row
                  #response_t,      #   Response_t row
                  #receiver_t,      #   Receiver_t row (orientation)
                  #offset_t,        #   Offset_t
                  pas = 'U',        #   'P' -> PASSCAL extended header
                                    #   'S' -> SEG extended header
                                    #   'U' -> Menlo USGS extended header
                                    #   'I' -> SIOSEIS
                                    #   'N' -> iNova firefly
                  length_points = 0,
                  seq = 1,          #   Line sequence number
                  utm = False) :    #   Populate trace header with UTM coordinates    
    
        self.start_point = 0
        self.length_points = length_points
        if length_points == 0 :
            self.length_points_all = 0
        else :
            self.length_points_all = length_points
            
        self.das_t = None
        self.sample_rate = None
        self.sort_t = sort_t
        #self.array_t = array_t
        self.time_t = None
        self.event_t = event_t
        self.response_t = None
        self.offset_t = None
        self.pas = pas
        self.utm = utm
        self.seq = seq
        self.text_header = segy_h.Text ()
        self.reel_header = segy_h.Reel ()
        #   Allow non-standard SEG-Y
        self.break_standard = False
        self.trace_type = None              #   Current data trace type (int, float)
        self.trace_byteorder = None         #   Current data trace byteorder
    
    def write_text_header (self, fd) :
        #os.write (fd, self.text_header.get ())
        #   3200 bytes
        fd.write (self.text_header.get ()[:3200])
        
    def write_reel_header (self, fd) :
        #os.write (fd, self.reel_header.get ())
        #   400 bytes
        fd.write (self.reel_header.get ()[:400])
        
    def write_trace_header (self, fd) :
        #os.write (fd, self.trace_header.get ())
        #   180 bytes
        try :
            fd.write (self.trace_header.get ()[:180])
        except Exception, e :
            sys.stderr.write ("{0:s}\n{1:s}\n".format (e, repr (self.trace_header.__dict__)))
        #os.write (fd, self.extended_header.get ())
        #   60 bytes
        try :
            fd.write (self.extended_header.get ()[:60])
        except Exception, e :
            sys.stderr.write ("{0:s}\n{1:s}\n".format (e, repr (self.extended_header.__dict__)))
    
    def write_data_array (self, fd) :
        #   Pad data to correct length with the median value
        pad = numpy.array ([])
        if len (self.data) < self.length_points_all :
            if len (self.data) == 0 :
                m = 0
            else :
                m = numpy.median (self.data)
            
            short = self.length_points_all - len (self.data)
            pad = [m] * short
            #for i in range (short) :
                #pad = numpy.append (pad, m)
        #print "Pad: ", len (pad)
        #
        data = numpy.append (self.data, pad)
        #print "Len: ", len (data)
        i = 0
        #   Use PASSCAL extended header
        if self.pas == 'P' :
            #   PASSCAL SEGY should be the endianess of the machine
            if self.trace_type == 'int' :
                x_d = numpy.array (data, numpy.int32)
            ##   Float trace elements
            elif self.trace_type == 'float' :
                x_d = numpy.array (data, numpy.float32)
            else :
                sys.stderr.write ("Trace type unknown: {0}\n".format (self.trace_type))
                
            #   Write the data on the end of the file
            x_d.tofile (file=fd)
            #   Get the number of points we wrote
            i += x_d.shape[0]
            #x_d = [segy_h.build_int (x) for x in data]
            #for x in x_d :
                #os.write (fd, x)
                
            #i += len (x_d)
            #for x in map (segy_h.build_int, data) :
                #i += 1
                #os.write (fd, x)
                
        else :
            #
            ###   Need to look in self.response_t for bit_weight/value_d and scale trace values.
            #
            x_f = numpy.array (data, numpy.float32)
            try :
                bw = float (self.response_t['bit_weight/value_d'])
                if bw == 0 : bw = 1.
                x_f *= bw
            except Exception as e :
                sys.stderr.write ("Warning: Problem applying trace bit weight.\n{0}\n".format (e))
                
            #if sys.byteorder == 'little' :
                #x_f = x_f.byteswap ()
            
            #   Little endian machine
            ###   We always want big endian in the SEG-Y file
            if sys.byteorder == 'little' :
                #   Little endian trace
                if self.trace_byteorder == 'little' :
                    #   Int trace elements
                    if self.trace_type == 'int' :
                        x_d = numpy.array (data, numpy.int32).byteswap ()
                    #   Float trace elements
                    elif self.trace_type == 'float' :
                        x_d = numpy.array (data, numpy.float32).byteswap ()
                        
                ##   Big endian trace
                #elif self.trace_byteorder == 'big' :
                    #if self.trace_type == 'int' :
                        #x_d = numpy.array (data, numpy.int32).byteswap ()
                    #elif self.trace_type == 'float' :
                        #x_d = numpy.array (data, numpy.float32).byteswap () 
                        
            elif sys.byteorder == 'big' :
                ##   Little endian trace
                #if self.trace_byteorder == 'little' :
                    ##   Int trace elements
                    #if self.trace_type == 'int' :
                        #x_d = numpy.array (data, numpy.int32).byteswap ()
                    ##   Float trace elements
                    #elif self.trace_type == 'float' :
                        #x_d = numpy.array (data, numpy.float32).byteswap ()
                        
                #   Big endian trace
                if self.trace_byteorder == 'big' :
                    if self.trace_type == 'int' :
                        x_d = numpy.array (data, numpy.int32)
                    elif self.trace_type == 'float' :
                        x_d = numpy.array (data, numpy.float32)            
            
            x_f.tofile (file=fd)
            i += x_f.shape[0]
            
            #x_f = [segy_h.build_ieee (x) for x in data]
            #for x in x_f :
                #os.write (fd, x_f)
                
            #i += len (x_f)
            #for x in map (segy_h.build_ieee, data) :
                #i += 1
                #os.write (fd, x)
                
        return i
    
    def set_event_t (self, event_t) :
        self.event_t = event_t
    
    def set_array_t (self, array_t) :
        self.array_t = array_t
                
    #   PASSCAL extended header
    def set_pas (self) :
        self.pas = 'P'
    #   SEG extended header
    def set_seg (self) :
        self.pas = 'S'
    #   USGS Menlo extended header
    def set_usgs (self) :
        self.pas = 'U'
    #   Set extended header type
    def set_ext_header_type (self, ext_type) :
        if ext_type in EXT_HEADER_CHOICES :
            self.pas = ext_type
                
    def set_data (self, data) :
        self.data = data
                
    def set_trace_type (self, t, o) :
        '''   Set trace type, and byteorder   '''
        self.trace_type = t
        self.trace_byteorder = o
        
    def set_das_t (self, das_t) :
        self.das_t = das_t
        self.sample_rate = das_t['sample_rate_i']
        
    def set_sample_rate (self, sample_rate) :
        self.sample_rate = sample_rate
        
    def set_time_t (self, time_t) :
        self.time_t = time_t
        
    def set_response_t (self, response_t) :
        self.response_t = response_t
    
    #   Orientation info
    def set_receiver_t (self, receiver_t) :
        self.receiver_t = receiver_t
        
    def set_offset_t (self, offset_t) :
        self.offset_t = offset_t
        
    def set_length_points (self, length_points) :
        #print "Set length points to: {0}".format (length_points)
        self.length_points = length_points
        if self.length_points_all == 0 :
            #print "Set lenght points all {0}".format (length_points)
            self.length_points_all = length_points
        
    def set_line_sequence (self, seq) :
        self.seq = seq
        
    def set_cut_start_epoch (self, start) :
        self.cut_start_epoch = start
            
    def set_text_header (self) :
        txt = {}
        if self.pas == 'U' :
            style = 'MENLO'
        elif self.pas == 'P' :
            style = 'PASSCAL'
        elif self.pas == 'S' :
            style = 'SEG'
        elif self.pas == 'I' :
            style = 'SIOSEIS'
        elif self.pas == 'N' :
            style = 'INOVA'

        if self.break_standard == True :
            txt['_06_'] = ebcdic.AsciiToEbcdic ("C 6                         SAMPLES/TRACE {0:6d}                                ".format (int (self.length_points)))
        
        txt['_38_'] = ebcdic.AsciiToEbcdic ("C38 {0:<7} STYLE EXTENDED TRACE HEADER".format (style) + " " * 41)
        txt['_39_'] = ebcdic.AsciiToEbcdic ("C39 SEG Y REV1" + " " * 66)
        txt['_40_'] = ebcdic.AsciiToEbcdic ("C40 END TEXTURAL HEADER" + " " * 57)
        
        try :
            self.text_header.set (txt)
        except segy_h.HeaderError, e :
            sys.stderr.write (e + "\n")
            
    def set_reel_header (self, traces) :
        rel = {}
        
        try :
            rel['lino'] = int (self.sort_t['array_name_s'])
        except (ValueError, TypeError) :
            rel['lino'] = 1
            
        rel['reno'] = 1
        rel['ntrpr'] = traces
        rel['hdt'] = int ((1.0 / float (self.sample_rate)) * 1000000.0)
        if self.length_points <= MAX_16 :
            rel['hns'] = self.length_points
            rel['nso'] = self.length_points
        #   Non-standard sample length
        elif self.break_standard == True :
            rel['hns'] = 0
            rel['nso'] = 0        
        else :
            rel['hns'] = int (MAX_16)
            rel['nso'] = int (MAX_16)
            
        rel['format'] = 5   #   IEEE floats
        rel['mfeet'] = 1    #   meters
        rel['rev'] = 0x0100 #   rev 1.0
        rel['trlen'] = 1    #   all traces the same length
        rel['extxt'] = 0    #   no extra text headers
        
        try :
            self.reel_header.set (rel)
        except segy_h.HeaderError, e :
            sys.stderr.write (e + '\n')
    
    def set_break_standard (self, tof = False) :
        self.break_standard = tof

    def _cor (self, max_drift_rate = 0.01) :
        '''
           Calculate start, end, drift and offset of clock
        '''
        if self.sort_t :
            sort_start_time = fepoch (self.sort_t['start_time/epoch_l'], self.sort_t['start_time/micro_seconds_i'])
        else :
            sort_start_time = self.cut_start_epoch
            
        if self.time_t == None :
            return 0, 0, sort_start_time

        if self.sort_t :
            sort_end_time = fepoch (self.sort_t['end_time/epoch_l'], self.sort_t['end_time/micro_seconds_i'])
        else :
            sort_end_time = sort_start_time + (self.length_points / self.sample_rate)
            
        sort_mid_time = sort_start_time + ((sort_end_time - sort_start_time) / 2.0)
        data_start_time = fepoch (self.time_t['start_time/epoch_l'], self.time_t['start_time/micro_seconds_i'])
        delta_time = sort_mid_time - data_start_time
        
        #   1% drift is excessive, don't time correct.
        if abs (self.time_t['slope_d']) >= max_drift_rate :
            time_correction_ms = 0
        else :
            time_correction_ms = int (self.time_t['slope_d'] * 1000.0 * delta_time)
        
        #   Sample interval
        si = 1.0 / float (int (self.sample_rate))
        #   Check if we need to time correct?
        if abs (self.time_t['offset_d']) < (si / 2.0) :
            time_correction_ms = 0
        #    KLUDGE reverse sign here
        if time_correction_ms < 0 :
            time_correction_ms *= -1
            sgn = 1
        else :
            sgn = -1
        
        new_start_time = (float (time_correction_ms * sgn) / 1000.0) + sort_start_time
        #print self.time_t['das/serial_number_s'], time_correction_ms & 0xFFFF * sgn, sort_start_time, new_start_time
        
        return (0xFFFF & time_correction_ms) * sgn, (0xFFFF & (time_correction_ms << 16)) * sgn, new_start_time
    
    def set_ext_header_seg (self) :
        '''   SEG-Y rev 01 extended header   '''
        ext = {}
        self.extended_header = segy_h.Seg ()
        #   Same as lino from reel header
        try :
            ext['Inn'] = int (self.sort_t['array_name_s'])
        except (ValueError, TypeError) :
            ext['Inn'] = 1
        #   Shot point number
        try :
            ext['Spn'] = int (self.event_t['id_s'])
        except ValueError :
            ext['Spn'] = 0
        #   Spn scaler
        ext['Scal'] = 1
        #   Trace value measurement units
        ext['Tvmu'] = 0
        #   Size of shot
        ext['Smsmant'] = int (self.event_t['size/value_d'])
        ext['Smsexp'] = 1
        ext['Smu'] = 0
        #   Number of samples
        ext['num_samps'] = self.length_points
        #   Sample interval in microseconds
        ext['samp_rate'] = int ((1.0 / self.sample_rate) * 1000000.0)
        
        return ext
    
    def set_ext_header_pas (self) :
        ext = {}
        self.extended_header = segy_h.Passcal ()
        
        cor_low, cor_high, sort_start_time = self._cor ()
        if cor_high < -MAX_16 or cor_high > MAX_16 :
            #print cor_high
            cor_high = int (MAX_16)
            
        ext['totalStaticHi'] = cor_high
        ext['num_samps'] = int (self.length_points)
        ext['max'] = numpy.max (self.data)
        ext['min'] = numpy.min (self.data)
        ext['samp_rate'] = int ((1.0 / self.sample_rate) * 1000000.0)
        ext['data_form'] = 1   #   32 bit
        ext['scale_fac'] = float (self.response_t['bit_weight/value_d'])
        
        corrected_start_time = self.cut_start_epoch + (cor_low / 1000.0)
        m_secs = int (math.modf (corrected_start_time)[0] * 1000.0)
        ext['m_secs'] = m_secs
        
        try :
            ttuple = time.gmtime ([self.event_t['time/epoch_l']])
            ext['trigyear'] = ttuple[0]
            ext['trigday'] = ttuple[7]
            ext['trighour'] = ttuple[3]
            ext['trigminute'] = ttuple[4]
            ext['trigsecond'] = ttuple[5]
            ext['trigmills'] = int (self.event_t['time/micro_seconds_i'] / 1000.0)
        except :
            pass
        
        try :
            try :
                ext['inst_no'] = int (self.array_t['das/serial_number_s'])
            except ValueError :
                ext['inst_no'] = int (self.array_t['das/serial_number_s'], 16)
        except :
            ext['inst_no'] = 0
            
        try :
            ext['station_name'] = string.ljust (string.strip (self.array_t['id_s']), 6)
        except :
            ext['station_name'] = string.ljust (string.strip (self.array_t['das/serial_number_s']), 6)
            
        return ext
    
    def set_ext_header_menlo (self) :
        '''   Use USGS Menlo's idea of extended trace header   '''
        ext = {}
        self.extended_header = segy_h.Menlo ()
        
        #   Start of trace
        cor_low, cor_high, sort_start_time = self._cor ()
        corrected_start_time = self.cut_start_epoch + (cor_low / 1000.0)
        u_secs = int (math.modf (corrected_start_time)[0] * 1000000.0)
        ext['start_usec'] = u_secs
        #   Shot size in Kg
        try :
            if self.event_t['size/units_s'][0] == 'k' or self.event_t['size/units_s'][0] == 'K' :
                ext['shot_size'] = self.event_t['size/value_d']
        except TypeError :
            pass
            
        #   Shot time
        try :
            ttuple = time.gmtime (float (self.event_t['time/epoch_l']))
            ext['shot_year'] = ttuple[0]
            ext['shot_doy'] = ttuple[7]
            ext['shot_hour'] = ttuple[3]
            ext['shot_minute'] = ttuple[4]
            ext['shot_second'] = ttuple[5]
            ext['shot_us'] = self.event_t['time/micro_seconds_i']
        except :
            pass
        
        #   Always set to 0
        ext['si_override'] = 0
        #   Azimuth and inclination, set to 0?
        ext['sensor_azimuth'] = 0
        ext['sensor_inclination'] = 0
        #   Linear moveout static x/v ms
        ext['lmo_ms'] = 0
        #   LMO flag, 1 -> n
        ext['lmo_flag'] = 1
        #   Inst type, 16 == texan
        if self.array_t['das/model_s'].find ('130') != -1 :
            ext['inst_type'] = 13   #   RT-130
        else :
            ext['inst_type'] = 16   #   texan
            
        #   Always set to 0
        ext['correction'] = 0
        #   Uphole azimuth set to zero
        ext['azimuth'] = 0
        #   Sensor type
        if self.array_t['sensor/model_s'].find ('28') != -1 :
            ext['sensor_type'] = 1   #   L28
        elif self.array_t['sensor/model_s'].find ('22') != -1 :
            ext['sensor_type'] = 2   #   L22
        elif self.array_t['sensor/model_s'].find ('4') != -1 :
            ext['sensor_type'] = 4   #   L4
        else :
            ext['sensor_type'] = 99  #   Don't know, don't care
            
        #   Sensor sn
        try :
            ext['sensor_sn'] = int (self.array_t['sensor/serial_number_s'])
        except :
            pass
        
        #   DAS sn
        try :
            ext['das_sn'] = int (self.array_t['das/serial_number_s'])
        except ValueError :
            ext['das_sn'] = 0xFFFF & int (self.array_t['das/serial_number_s'], 16)
        else :
            pass
        
        #   16 free bits
        try :
            ext['empty1'] = self.array_t['channel_number_i']
        except :
            pass
        
        #   Number of samples
        ext['samples'] = self.length_points
        #   32 free bits
        try :
            ext['empty2'] = int (self.array_t['description_s'])
        except :
            pass
        
        #   clock correction
        try :
            ext['clock_drift'] = self._cor ()[0]
            if ext['clock_drift'] > MAX_16 or ext['clock_drift'] < -MAX_16 :
                ext['clock_drift'] = int (MAX_16)
        except :
            pass
        
        #   16 free bits
        try :
            ext['empty3'] = int (self.event_t['description_s'])
        except :
            pass
        
        return ext
        
    def set_ext_header_sioseis (self) :
        '''   Use SIOSEIS extended header   '''
        ext = {}
        self.extended_header = segy_h.Sioseis ()
        ext['sampleInt'] = 1.0 / self.sample_rate
        '''
        if self.seq >= traces :
            ext['endOfRp'] = 
        '''
        return ext
    
    def set_trace_header (self) :
        '''
           Set values in trace header.
        '''
        tra = {}
        self.trace_header = segy_h.Trace ()
        
        #   Get time correction
        cor_low, cor_high, sort_start_time = self._cor ()
        if cor_low < -MAX_16 or cor_low > MAX_16 :
            #print cor_low
            cor_low = int (MAX_16)
        
        tra['totalStatic'] = cor_low
        
        tra['lineSeq'] = self.seq
        #   das_t['event_number'] is the FFID or recording window
        tra['event_number'] = self.das_t['event_number_i']
        tra['channel_number'] = self.seq
        #tra['channel_number'] = self.array_t['channel_number_i']
        #   Set the traceID to the channel, 15 => Z, 16 => N, 17 => E
        #   Fallback is to set it to 1 => seismic data 
        try :
            tra['traceID'] = CHAN2TID[self.array_t['channel_number_i']]
        except :
            #   Changed for Mark Goldman, Aug 2011
            tra['traceID'] = 1
        
        length_points = int (self.length_points)
        if length_points < MAX_16 :
            tra['sampleLength'] = length_points
        #   Non-standard sample length
        elif self.break_standard == True :
            tra['sampleLength'] = 0            
        else :
            tra['sampleLength'] = int (MAX_16)
        
        sample_rate = float (int (self.sample_rate))
        if sample_rate > 30.0 :
            tra['deltaSample'] = int ((1.0 / sample_rate) * 1000000.0)
        else :
            tra['deltaSample'] = 1
                
        tra['gainType'] = 1
        tra['gainConst'] = int (self.response_t['gain/value_i'])
        
        corrected_start_time = self.cut_start_epoch + (cor_low / 1000.0)
        #m_secs = int (math.modf (corrected_start_time)[0] * 1000.0)
        ttuple = time.gmtime (corrected_start_time)
        tra['year'] = ttuple[0]
        tra['day'] = ttuple[7]
        tra['hour'] = ttuple[3]
        tra['minute'] = ttuple[4]
        tra['second'] = ttuple[5]        
        tra['timeBasisCode'] = 4   #   UTC
        
        twfUnits = self.response_t['bit_weight/units_s'].strip ()
        try :
            mult = COUNTMULT[twfUnits]
        except :
            mult = 1.
        
        try :
            tra['traceWeightingFactor'] = int (math.log (self.response_t['bit_weight/value_d'] / mult, 2) + 0.5)
        except ValueError :
            tra['traceWeightingFactor'] = 1.
            
        #print twfUnits, self.response_t['bit_weight/value_d'], tra['traceWeightingFactor']
        #   Limit size of phoneFirstTrace to 65535 maximum
        tra['phoneFirstTrace'] = 0xFFFF & int (self.array_t['id_s'])
        
        #   Set receiver location here
        try :
            multiplier = units_stub (string.strip (self.array_t['location/Z/units_s']), 'decimeters')
            tra['recElevation'] = int (float (self.array_t['location/Z/value_d']) * multiplier)
            tra['elevationScale'] = -10
        except :
            tra['recElevation'] = 0
            tra['elevationScale'] = 0
            
        if self.utm == True :
            try :
                Y, X, Z = geod2utm (None,        #   Zone goes here
                                    "WGS84", 
                                    self.array_t['location/Y/value_d'], 
                                    self.array_t['location/X/value_d'],
                                    self.array_t['location/Z/value_d'])
                #print 'X: ', X, 'Y: ', Y, 'Z:', Z
                tra['coordScale'] = -10
                tra['recLongOrX'] = int ((X * 10.0) + 0.5)
                tra['recLatOrY'] = int ((Y * 10.0) + 0.5)
                tra['coordUnits'] = 1   #   meters
            except :
                tra['coordScale'] = 0
                tra['recLongOrX'] = 0
                tra['recLatOrY'] = 0
                tra['coordUnits'] = 0
        else :
            try :
                tra['coordScale'] = -10000
                tra['recLongOrX'] = int ((self.array_t['location/X/value_d'] * 10000.0) + 0.5)
                tra['recLatOrY'] = int ((self.array_t['location/Y/value_d'] * 10000.0) + 0.5)
                tra['coordUnits'] = 3
            except :
                tra['coordScale'] = 0
                tra['recLongOrX'] = 0
                tra['recLatOrY'] = 0
                tra['coordUnits'] = 0
        
        if self.event_t :
            try :
                tra['energySourcePt'] = int (self.event_t['id_s'])
                #sys.stderr.write ("Shot: {0:d}\n".format (int (self.event_t['id_s'])))
            except Exception, e :
                tra['energySourcePt'] = 0
                #sys.stderr.write ("Error: {0:s} Shot ID: {1:s}\n".format (e, self.event_t['id_s']))
            
            #   Set source location here
            try :
                multiplier = units_stub (string.strip (self.event_t['location/Z/units_s']), 'decimeters')
                tra['sourceSurfaceElevation'] = int (float (self.event_t['location/Z/value_d']) * multiplier)
                tra['sourceDepth'] = int (float (self.event_t['depth/value_d']) * multiplier)
            except :
                tra['sourceSurfaceElevation'] = 0
                tra['sourceDepth'] = 0
            
            if self.utm :
                try :
                    Y, X, Z = geod2utm (None,        #   Zone goes here
                                        "WGS84", 
                                        self.event_t['location/Y/value_d'], 
                                        self.event_t['location/X/value_d'],
                                        self.event_t['location/Z/value_d'])
                    
                    tra['sourceLongOrX'] = int ((X * 10.0) + 0.5)
                    tra['sourceLatOrY'] = int ((Y * 10.0) + 0.5)
                except :
                    tra['sourceLongOrX'] = 0
                    tra['sourceLatOrY'] = 0
                    
            else :
                try :
                    tra['sourceLongOrX'] = int ((self.event_t['location/X/value_d'] * 10000.0) + 0.5)
                    tra['sourceLatOrY'] = int ((self.event_t['location/Y/value_d'] * 10000.0) + 0.5)
                except :
                    tra['sourceLongOrX'] = 0
                    tra['sourceLatOrY'] = 0
                
        if self.offset_t :
            tra['sourceToRecDist'] = self.offset_t['offset/value_d']
        
        #try :
        self.trace_header.set (tra)
        #except reconstruct.core.FieldError, e :
            #sys.stderr.write (e + "\n")
            #sys.stderr.write (repr (tra))
            
        #try :
        if self.pas == 'P' :
            #print "Set PASSCAL header"
            ext = self.set_ext_header_pas ()
        elif self.pas == 'U' :
            #print "Set Menlo header"
            ext = self.set_ext_header_menlo ()
        elif self.pas == 'S' :
            #print "Set SEG header"
            ext = self.set_ext_header_seg ()
        elif self.pas == 'I' :
            ext = self.set_ext_header_sioseis ()
            
        #   XXX
        #print len (ext), len (tra)
        self.extended_header.set (ext)
        #except reconstruct.core.FieldError, e :
            #sys.stderr.write (e + "\n")
            #sys.stderr.write (repr (ext))
        
#   MixIns
def units_stub (have, want) :
    """
       Finds the conversion multiplier needed.
    """
    # Add more prefixes?
    pref = {'yocto':1e-24,'micro':1e-6,'milli':1e-3,'centi':1e-2,'deci':1e-1,'deka':1e1,'hecto':1e2,'kilo':1e3,'mega':1e6}
    h = None
    w = None
    for p in pref.keys() :
        if have[:len(p)] == p :
            h = pref[p]
        if want[:len(p)] == p :
            w = pref[p]

    if h == None : h = 1.0
    if w == None : w = 1.0
        
    ret = h / w
    
    return ret

def fepoch (epoch, ms) :
    '''
    Given ascii epoch and miliseconds return epoch as a float.
    '''
    epoch = float (int (epoch))
    secs = float (int (ms)) / 1000000.0
    
    return epoch + secs

