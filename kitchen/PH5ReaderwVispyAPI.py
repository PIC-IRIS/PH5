#!/usr/bin/env pnpython4
#
#   Interface PH5 to PH5Viewer
#
#   Lan Dam, Steve Azevedo August 2015
#

import sys, os, time
#from numpy import array, vstack, amax, amin, float32
import numpy as np
sys.path.append(os.path.join(os.environ['KX'], 'apps', 'pn4'))
import ph5API, TimeDOY

PROG_VERSION = "2016.207 Developmental"

class PH5ReaderError (Exception) :
    '''   Exception gets raised in PH5Reader   '''
    def __init__ (self, message) :
        super (PH5ReaderError, self).__init__ (message)
        self.message = message
    
class PH5Reader () :
    '''
       Read PH5 data and meta-data.
       For example: See __main__ below.
    '''
    def __init__ (self) :
        #
        #   This is the ph5API object.
        self.fio = None
        self.clear ()
        self.set ()
    
    def clear (self) :
        #
        self.graphArrays = None
        self.graphEvents = None
        self.data = np.array ([])
        self.metadata = None
    
    def set (self, channel=[1], array=['Array_t_001']) :   
        '''
           Set channels and arrays
           Example: set (channel=[1,2,3], array = ['Array_t_001', 'Array_t_002'])
        '''
        #
        #   Channels to extract, a list.
        self.CHANNEL = channel
        #   Arrays to extract, a list.
        self.ARRAY = array
        #print "set channel=%s; array=%s" % (self.CHANNEL, self.ARRAY)

                    
    def initialize_ph5 (self, path2file) :
        '''
           Initialize ph5API and read meta-data...
           path2file => Absolute path to the master ph5 file.
        '''
        pathname = os.path.dirname (str (path2file))
        master = os.path.basename (str (path2file))
        try :
            self.fio = ph5API.ph5 (path=pathname, nickname=master)
            
            self.fio.read_event_t_names ()
            for n in self.fio.Event_t_names :
                self.fio.read_event_t (n)
                
            self.fio.read_array_t_names ()
            for n in self.fio.Array_t_names :
                self.fio.read_array_t (n)
                
            self.fio.read_sort_t ()
            
            self.fio.read_receiver_t ()
            
            self.fio.read_response_t ()
        except Exception as e :
            raise PH5ReaderError ("Failed to read {0}.\n{1}".format (path2file, e.message))
            
    def ph5close (self) :
        self.fio.close ()
        
    def _event_stop (self, event_epoch) :
        '''   Find end of recording window that contains the event time.   '''
        for n in self.fio.Array_t_names :
            for s in self.fio.Sort_t[n]['rows'] :
                if event_epoch >= s['start_time/epoch_l'] and event_epoch <= s['end_time/epoch_l'] :
                    tdoy = TimeDOY.TimeDOY (epoch=s['end_time/epoch_l'], microsecond=s['end_time/micro_seconds_i'])
                    return tdoy.epoch (fepoch=True)
            
        return None
    
    def createGraphExperiment (self) :
        '''
              Information about experiment
              Sets: self.GraphExperiment
        '''
        self.fio.read_experiment_t ()
        rows = self.fio.Experiment_t['rows']
        self.graphExperiment = rows[-1]
        pass

    def createGraphArrayNEvents (self) :
        '''   Information about events,
              Sets: self.graphEvents
        '''
        self.graphEvents = []
        for n in self.fio.Event_t_names :
            a = {}
            a['arrayId'] = n.split ('_')[-1]
            rows = self.fio.Event_t[n]['byid']
            a['events'] = []
            for o in self.fio.Event_t[n]['order'] :
                e = {}
                r = rows[o]
                e['eventId'] = r['id_s']
                e['lat.'] = r['location/Y/value_d']
                e['long.'] = r['location/X/value_d']
                e['elev.'] = r['location/Z/value_d']
                e['mag.'] = r['size/value_d']
                e['depth'] = r['depth/value_d']
                tdoy = TimeDOY.TimeDOY (epoch=r['time/epoch_l'], microsecond=r['time/micro_seconds_i'])
                e['eStart'] = tdoy.epoch (fepoch=True)
                e['eStop'] = self._event_stop (e['eStart'])
                a['events'].append (e)
                
            self.graphEvents.append (a)
        pass
                
    def createGraphArraysNStations (self) :
        '''
           Information about arrays,
           Sets: self.graphArrays
        '''
        self.graphArrays = []
        self.chs = [False, False, False]
        for n in self.fio.Array_t_names :
            a = {}
            a['arrayId'] = n.split ('_')[-1]
            rows = self.fio.Array_t[n]['byid']
            sta0 = rows.keys ()[0]
            chans = rows[sta0].keys ()
            r0 = rows[sta0][chans[0]]
            a['deployT'] = r0['deploy_time/epoch_l']
            a['pickupT'] = r0['pickup_time/epoch_l']
            das = r0['das/serial_number_s']
            self.fio.read_das_t (das, start_epoch = a['deployT'], stop_epoch=a['pickupT'])
            a['sampleRate'] = self.fio.Das_t[das]['rows'][chans[0]]['sample_rate_i'] / float (self.fio.Das_t[das]['rows'][chans[0]]['sample_rate_multiplier_i'])
            a['stations'] = []
            for o in self.fio.Array_t[n]['order'] :
                chans = rows[o].keys ()
                chans.sort ()
                #r = rows[o]
                for c in chans :
                    r = rows[o][c]
                    s = {}
                    self.chs[r['channel_number_i']-1] = r['channel_number_i']
                    s['stationId'] = r['id_s']
                    s['dasSer'] = r['das/serial_number_s']
                    s['lat.'] = r['location/Y/value_d']
                    s['long.'] = r['location/X/value_d']
                    s['elev.'] = r['location/Z/value_d']
                    s['component'] = r['channel_number_i']
                    a['stations'].append (s)
                
            self.graphArrays.append (a)
        #for l in self.graphArrays[0]['stations'] :
            #print l        
        pass
            
            
    def readData (self, orgStartT, offset, timeLen, staSpc, 
                  appClockDriftCorr, redVel,        # corrections
                  PH5View, statusBar=None, beginMsg=None) :
        '''
           Read trace data based on given start and stop epoch, arrays, and channels.
           Sets: self.metadata
           Returns: info
        '''
        sampleRate = PH5View.selectedArray['sampleRate']
        statusMsg = beginMsg + ": preparing event table"
        statusBar.showMessage(statusMsg)  
        
        channels = self.CHANNEL
        #print "channels:", channels 
        #arrays = self.ARRAY
        
        #print "arrays:", arrays
        #print arrays, channels, time.ctime (startTime), time.ctime (stopTime)
        #   Find relevant lines in Event_t        
        event_t = {}; event_name = None; event_id = None
        """
        if esGUI == None :
            for n in self.fio.Event_t_names :
                rows = self.fio.Event_t[n]['byid']
                order = self.fio.Event_t[n]['order']
                for o in order :
                    e = rows[o]
                    event_time = float (e['time/epoch_l']) + float (e['time/micro_seconds_i'] / 1000000.)
                    if event_time >= startTime and event_time <= stopTime :
                        event_name = n
                        event_id = e['id_s']
                        event_t.append (e)
        else :
        """
     
        
        for n in self.fio.Event_t_names :
            event_name = n
            #
            rows = self.fio.Event_t[n]['byid']
            order = self.fio.Event_t[n]['order']
            for o in order :
                e = rows[o]
                #print e['id_s']
                if e['id_s'] in PH5View.selectedEventIds:
                    if not event_t.has_key (event_name) :
                        event_t[event_name] = []
                    tdoy = TimeDOY.TimeDOY (epoch=e['time/epoch_l'], microsecond=e['time/micro_seconds_i'])                
                    e['eStart'] = tdoy.epoch (fepoch=True)
                    e['eStop'] = self._event_stop (e['eStart'])
                    #print "start:%s, end:%s" % (e['eStart'], e['eStop'])
                    event_t[event_name].append (e)
                    
        
        #   Loop through each station in each requested array and extract trace data.
        self.data = []
        info = {}
        info['maxP2P'] =  -1 * (2**31 - 1)
        info['zeroDOffsetIndex'] = None
        info['distanceOffset'] = []
        self.metadata = []
        up = []
        secs = timeLen
        ii = 0
        ss = ""
        Offset_t = {}
        
        a = self.ARRAY[0]  # currently allow to select one array at a time
        
        if orgStartT != None:
            startTime = orgStartT + offset
            stopTime = startTime + timeLen
        
        
        #   If there is an associated event calculate offset distances
        event_names = event_t.keys ()
        for event_name in event_names :
            for e in event_t[event_name] :
                Offset_t[a] = self.fio.calc_offsets (a, e['id_s'], event_name)
    
                if orgStartT == None:
                    startTime = e['eStart'] + offset
                    stopTime = startTime + timeLen
    
                sr = None
                slen = None
                rows = self.fio.Array_t[a]['byid']
                order = self.fio.Array_t[a]['order']
                line_seq = 0
                for o in order :
                    #if line_seq== 50: break
                    #if line_seq>60:
                    chans = rows[o].keys ()
                    chans.sort ()
                    rows[o]
                    for c in chans :
                        #c = int (c)
                        if not c in channels :
                            continue
                        r = rows[o][c]
                        if r['id_s'] not in PH5View.selectedStationIds: continue
                        if not ph5API.is_in (r['deploy_time/epoch_l'], r['pickup_time/epoch_l'], startTime, stopTime) :
                            continue                    
    
                        if c != r['channel_number_i'] :
                            continue
                        das = r['das/serial_number_s']
                        corr = self.calcCorrection(ii, 
                                                   das, 
                                                   c, 
                                                   Offset_t,
                                                   a, 
                                                   r,
                                                   startTime, 
                                                   stopTime,
                                                   sampleRate, 
                                                   staSpc, 
                                                   appClockDriftCorr, 
                                                   redVel)
        
                        ## + 1.1/sampleRate: add a little bit than the time of one sample
                        #trace = self.fio.cut (das, 
                                              #startTime-corr[0]/1000., 
                                              #stopTime-corr[0]/1000. + 1.1/sampleRate, 
                                              #c)
                        trace = self.fio.cut (das, startTime, stopTime, c)                        
                        if trace.nsamples == 0 : continue
                        if sr == None :
                            sr = trace.sample_rate
                            slen = int ((secs * sr) + 0.5)
                        
                        self.metadata.append ({})
                        
                        self.metadata[ii]['totalCorr'] = corr[0]       #   Total time correction
                        self.metadata[ii]['clockDriftCorr'] = corr[1]  #   Clock correction
                        self.metadata[ii]['redVelCorr'] = corr[2]      #   Reduction velocity correction
                        self.metadata[ii]['absStartTime'] = TimeDOY.epoch2passcal (startTime)
                        self.metadata[ii]['seq'] = line_seq
                        self.metadata[ii]['arrayId'] = a[-3:]
                        self.metadata[ii]['stationId'] = r['id_s']
                        self.metadata[ii]['eventId'] = e['id_s']
                        self.metadata[ii]['dasSerial'] = das
                        self.metadata[ii]['chanNum'] = r['channel_number_i']
                        self.metadata[ii]['desc'] = r['description_s']
                        self.metadata[ii]['lat'] = r['location/Y/value_d']
                        self.metadata[ii]['long'] = r['location/X/value_d']
                        self.metadata[ii]['elev'] = r['location/Z/value_d']
                        self.metadata[ii]['elevUnit'] = r['location/Z/units_s'].strip ()
                        if staSpc==None and orgStartT != None:
                            #   If no offset distance just set them to an incremented sequence
                            try :
                                offset_t = Offset_t[a]['byid'][r['id_s']]
                                info['distanceOffset'].append(offset_t['offset/value_d'])
                                if offset_t['offset/value_d'] == 0 : info['zeroDOffsetIndex'] = ii
                                self.metadata[ii]['distanceOffsetUnit'] = offset_t['offset/units_s']
                                self.metadata[ii]['azimuth'] = offset_t['azimuth/value_f']
                                self.metadata[ii]['azimuthUnit'] = offset_t['azimuth/units_s']
                        
                            except Exception as e :
                                
                                print e.message
                                
                                self.metadata[ii]['distanceOffset'] = ii
                                self.metadata[ii]['distanceOffsetUnit'] = 'm'
                                self.metadata[ii]['azimuth'] = 0
                                self.metadata[ii]['azimuthUnit'] = 'degrees'  
                                
                                raise PH5ReaderError("NoDOffset")
                            
                        else:
                            info['distanceOffset'].append(staSpc * ii)
                        
                        self.metadata[ii]['sample_rate'] = trace.sample_rate
                        self.metadata[ii]['numOfSamples'] = trace.nsamples
                        #self.metadata[ii]['timeCorrection'] = trace.time_correction_ms
                        
                        info['interval'] = 1000. / trace.sample_rate
                        self.metadata[ii]['gain'] = self.fio.Response_t['rows'][trace.das_t[0]['response_table_n_i']]['gain/value_i']
                        self.metadata[ii]['gainUnit'] = self.fio.Response_t['rows'][trace.das_t[0]['response_table_n_i']]['gain/units_s']
                        bit_weight = self.fio.Response_t['rows'][trace.das_t[0]['response_table_n_i']]
                        self.metadata[ii]['bitWeight'] = self.fio.Response_t['rows'][trace.das_t[0]['response_table_n_i']]['bit_weight/value_d']
                        self.metadata[ii]['bitWeightUnit'] = self.fio.Response_t['rows'][trace.das_t[0]['response_table_n_i']]['bit_weight/units_s']
                        
                        self.metadata[ii]['component'] = self.fio.Receiver_t['rows'][trace.das_t[0]['receiver_table_n_i']]['orientation/description_s']
                        self.metadata[ii]['azimuth'] = self.fio.Receiver_t['rows'][trace.das_t[0]['receiver_table_n_i']]['orientation/azimuth/value_f']
                        self.metadata[ii]['azimuthUnit'] = self.fio.Receiver_t['rows'][trace.das_t[0]['receiver_table_n_i']]['orientation/azimuth/units_s']
                        self.metadata[ii]['dip'] = self.fio.Receiver_t['rows'][trace.das_t[0]['receiver_table_n_i']]['orientation/dip/value_f']
                        self.metadata[ii]['dipUnit'] = self.fio.Receiver_t['rows'][trace.das_t[0]['receiver_table_n_i']]['orientation/dip/units_s']
                        #self.metadata[ii]['removed'] = False
                        trace.data = np.array (trace.data, dtype=np.float32)
                        if False :
                        #if bit_weight and bit_weight['bit_weight/units_s'] == 'volts/count' :
                            self.data.append (trace.data * bit_weight['bit_weight/value_d'])
                        else :
                            self.data.append (trace.data)
                        self.metadata[ii]['minmax'] = (np.amin (trace.data), np.amax (trace.data))  
                        newMaxP2P = abs(self.metadata[ii]['minmax'][0] - self.metadata[ii]['minmax'][1])
                        self.metadata[ii]['p2p'] = newMaxP2P
                        
                        if newMaxP2P > info['maxP2P']: info['maxP2P'] = newMaxP2P 
                        #print self.metadata[ii]['minmax']
                        
                        if ii>0: 
                            if info['distanceOffset'][ii]>info['distanceOffset'][ii-1]:
                                up.append(True)
                                #ss += '__%s>__' % ii
                            else:
                                up.append(False)
                                #ss += '**%s<**' % ii
                                
                        else:
                            self.metadata[0]['up']=None
                           
                        ii += 1; line_seq += 1
                        if statusBar!=None and line_seq % 10 == 0:
                            statusMsg = beginMsg + ": reading data and metadata: %s stations" % line_seq 
                            statusBar.showMessage(statusMsg)

        #print self.data
        minorTrend = False
        if up.count(False) > up.count(True): 
            minorTrend = True

        info['abnormal'] = [i for i in range(len(up)) if up[i]==minorTrend ]
        info['quickRemoved'] = {}
        info['deepRemoved'] = []
        info['numOfStations'] = len(self.data)
        info['numOfSamples'] = 0
        if info['numOfStations']>0:
            info['numOfSamples'] = trace.nsamples
        
        totalSamples = info['numOfSamples'] * info['numOfStations']
        
        if info['numOfStations'] > 0 :
            sumD = abs(info['distanceOffset'][-1] - info['distanceOffset'][0])
            #print "sumD=", sumD
            info['avgSize'] = sumD / info['numOfStations']
            #print "avgSize=", info['avgSize']

        return info
    
    
    def calcCorrection(self, ii, das, c, Offset_t, a, r, startTime, stopTime, sampleRate, 
                       staSpc, appClockDriftCorr, redVel):
        #print "calcCorrection"
        totalCorr = 0
        redVelCorr = None
        if redVel != None:
            if staSpc==None:
                try :
                    dOffset = Offset_t[a]['byid'][r['id_s']]['offset/value_d']
                    #print "ii=%s, offset=%s" % (ii, dOffset)
                except Exception as e :
                    raise PH5ReaderError("NoDOffset")
            else:
                dOffset = staSpc * ii
            redVelCorr = -1000*abs(dOffset/redVel)
            totalCorr += redVelCorr

        #trace = self.fio.cut (das, startTime, 1.1/sampleRate, c)
        #clockDriftCorr = trace.time_correction_ms
        Time_t = self.fio.get_time_t (das)
        clockDriftCorr = ph5API._cor (startTime, stopTime, Time_t)
        if appClockDriftCorr:
            totalCorr += clockDriftCorr
        
        return totalCorr, clockDriftCorr, redVelCorr
            

if __name__ == '__main__' :
    #from time import time
    pr = PH5Reader ()
    #try :
        #pr.initialize_ph5 ('/media/sf_azevedo/Desktop/SL-65-backups/Experiments/xxx/master.ph5')
    #except PH5ReaderError as e :
        #print e.message
    #pr.clear ()
    try :
        pr.initialize_ph5 ('/home/azevedo/Data/10-016/master.ph5')
    except PH5ReaderError as e :
        print e.message
        
    pr.createGraphArrayNEvents ()
    
    pr.createGraphArraysNStations ()
    
    pr.createGraphExperiment ()
    
    then = time.time ()    
    info0 = pr.readData (1200895260, 1200895270, .5)
    #print "10s traces X {0} =".format (info0['numOfStations']), time.time () - then
    
    #for s in pr.data :
        #print s[0], s[-1]
    #print "API"
    #pr.set (channel=[1], array=['Array_t_002'])
    ##   Loop through Sort_t
    #for s in pr.fio.Sort_t['Array_t_002']['rows'] :
        ##print s
        #print '.',
    #print
    ##   Time of last event window in Sort_t for array 2
    #start = s['start_time/epoch_l']
    #then = time.time ()
    ##   No associated event and thus no offset
    #info1 = pr.readData (start, start + 130, .25)
    #print "130s traces", time.time () - then
    pr.fio.close ()
    pass