#!/usr/bin/env pnpython3
#
#   Interface PH5 to PH5Viewer
#
#   Lan Dam, Steve Azevedo August 2015
#
#   Updated April 2018

import os
import numpy as np
from ph5.core import ph5api, timedoy
VER = 2018116


class PH5ReaderError(Exception):
    '''   Exception gets raised in PH5Reader   '''
    def __init__(self, message):
        super(PH5ReaderError, self).__init__(message)
        self.message = message


class PH5Reader():
    '''
       Read PH5 data and meta-data.
       For example: See __main__ below.
    '''
    def __init__(self):
        # This is the ph5api object.
        self.fio = None
        self.clear()
        self.set()

    def clear(self):
        self.graphExperiment = None
        self.graphArrays = None
        self.graphEvents = None
        self.data = np.array([])
        self.metadata = None

    def set(self, channel=[1], array=['Array_t_001']):
        '''
           Set channels and arrays
           Example:
             set (channel=[1,2,3], array = ['Array_t_001', 'Array_t_002'])
        '''
        # Channels to extract, a list.
        self.CHANNEL = channel
        # Arrays to extract, a list.
        self.ARRAY = array

    def initialize_ph5(self, path2file):
        '''
           Initialize ph5api and read meta-data...
           path2file => Absolute path to the master ph5 file.
        '''
        pathname = os.path.dirname(str(path2file))
        master = os.path.basename(str(path2file))

        self.fio = ph5api.PH5(path=pathname, nickname=master)

        self.fio.read_event_t_names()
        for n in self.fio.Event_t_names:
            self.fio.read_event_t(n)

        self.fio.read_array_t_names()
        for n in self.fio.Array_t_names:
            self.fio.read_array_t(n)

        # this table is required to identify events' endtime.
        # If missing, errors will be informed in createGraphEvents()
        self.fio.read_sort_t()

        # this table define orientation of data, required when reading trace
        self.fio.read_receiver_t()

        if len(self.fio.Receiver_t['rows']) == 0:
            msg = "There is no Receiver_t table in the dataset." + \
                  "which means it is not possible to read data correctly."
            raise PH5ReaderError(msg)

        # this table gives some non-displayed data
        # self.fio.read_response_t ()

        self.fio.read_das_g_names()
        if len(self.fio.Das_g_names) == 0:
            msg = "There are no Das_t tables in the dataset," + \
                  "which means there are no data to be viewed."
            raise PH5ReaderError(msg)

    def ph5close(self):
        self.fio.close()

    def _event_stop(self, event_epoch):
        '''   Find end of recording window that contains the event time.   '''
        try:
            for n in self.fio.Array_t_names:
                for s in self.fio.Sort_t[n]['rows']:
                    if event_epoch >= s['start_time/epoch_l'] \
                            and event_epoch <= s['end_time/epoch_l']:
                        tdoy = timedoy.TimeDOY(
                            epoch=s['end_time/epoch_l'],
                            microsecond=s['end_time/micro_seconds_i'])
                        return tdoy.epoch(fepoch=True)
        except KeyError:
            return None

        return None

    ##################################################
    # def createGraphEvents
    # Author: Lan Dam
    # Updated: 201802
    # read Experiment_t table
    def createGraphExperiment(self):
        '''
              Information about experiment
              Sets: self.GraphExperiment
        '''
        self.fio.read_experiment_t()
        rows = self.fio.Experiment_t['rows']
        if rows == []:
            raise PH5ReaderError(
                "The PH5 dataset does not have Experiment_t table." +
                "\nCannot identify the experiment's name")

        self.graphExperiment = rows[-1]
        pass

    ###################################################
    # def createGraphEvents
    # Author: Lan Dam
    # Updated: 201802
    def createGraphEvents(self):
        '''   Information about events info for ES_Gui,
              Sets: self.graphEvents
        '''
        self.graphEvents = {'shotLines': []}
        events = []
        for n in self.fio.Event_t_names:
            # take off 'Event_t' and change to '0' for n='Event_t'
            # for create to SEGY
            if n == 'Event_t':
                shot = '0'
            else:
                shot = n.replace('Event_t_', '')
            self.graphEvents['shotLines'].append(shot)
            rows = self.fio.Event_t[n]['byid']
            for o in self.fio.Event_t[n]['order']:
                r = rows[o]
                e = {}
                e['shotlineId'] = shot
                e['eventName'] = n
                e['eventId'] = r['id_s']
                e['lat.'] = r['location/Y/value_d']
                e['long.'] = r['location/X/value_d']
                e['elev.'] = r['location/Z/value_d']
                e['mag.'] = r['size/value_d']
                e['depth'] = r['depth/value_d']
                tdoy = timedoy.TimeDOY(
                    epoch=r['time/epoch_l'],
                    microsecond=r['time/micro_seconds_i'])
                e['eStart'] = tdoy.epoch(fepoch=True)
                e['eStop'] = self._event_stop(e['eStart'])
                events.append(e)
        self.graphEvents['events'] = \
            sorted(events, key=lambda k: k['eventId'])
        self.graphEvents['shotLines'] = \
            sorted(self.graphEvents['shotLines'], key=lambda k: k)
        if self.fio.Event_t_names == []:
            raise PH5ReaderError(
                "The PH5 dataset does not have any Event_t table.")

        if self.fio.Sort_t == {}:
            msg = "The PH5 dataset does not have any Sort_t table " + \
                "which means\nthere aren't enough information to identtify" + \
                " the events' end time."
            raise PH5ReaderError(msg)

    ######################################################
    # def createGraphArraysNStations
    # Author: Lan Dam
    # Updated: 201802
    def createGraphArraysNStations(self):
        '''
           Information about arrays and station info for ES_Gui,
           Sets: self.graphArrays
        '''
        self.graphArrays = []
        for n in self.fio.Array_t_names:
            # create array: {'arrayId': aId,
            #                {'stations':{stationId:
            #                 [list of data for each channel of that station]}
            a = {'arrayId': n.split('_')[-1], 'stations': {}, 'channels': []}
            rows = self.fio.Array_t[n]['byid']
            # byid: {statId:{chanId:[ {info of that channel-station} ]}}
            sta0 = rows.keys()[0]
            chan0 = rows[sta0].keys()[0]
            r0 = rows[sta0][chan0][0]
            a['deployT'] = r0['deploy_time/epoch_l']
            a['pickupT'] = r0['pickup_time/epoch_l']
            try:
                a['sampleRate'] = \
                    r0['sample_rate_i'] / float(r0['sample_rate_multiplier_i'])
            except KeyError:
                das = r0['das/serial_number_s']
                self.fio.read_das_t(
                    das, start_epoch=a['deployT'], stop_epoch=a['pickupT'])
                dasrow = self.fio.Das_t[das]['rows'][0]
                a['sampleRate'] = dasrow['sample_rate_i'] / \
                    float(dasrow['sample_rate_multiplier_i'])

            # self.fio.Array_t[n]['order']:
            #    list of station names in order of postion, time
            chNo = 0
            for o in self.fio.Array_t[n]['order']:
                for ch in rows[o].keys():
                    if ch not in a['channels']:
                        a['channels'].append(ch)

                    for stat in rows[o][ch]:
                        if stat['id_s'] in a['stations'].keys():
                            continue
                        s = {}
                        s['stationId'] = stat['id_s']
                        s['dasSer'] = stat['das/serial_number_s']
                        s['lat.'] = stat['location/Y/value_d']
                        s['long.'] = stat['location/X/value_d']
                        s['elev.'] = stat['location/Z/value_d']
                        # s['selected'] = False
                        a['stations'][stat['id_s']] = s
                        if stat['deploy_time/epoch_l'] < a['deployT']:
                            a['deployT'] = stat['deploy_time/epoch_l']
                        if stat['pickup_time/epoch_l'] > a['pickupT']:
                            a['pickupT'] = stat['pickup_time/epoch_l']

            keys = set(a['stations'].keys())

            a['orderedStationIds'] = sorted(
                keys, key=lambda item: (int(item), item))

            if len(a['channels']) > chNo:
                chNo = len(a['channels'])
            self.graphArrays.append(a)
        if self.fio.Array_t_names == []:
            raise PH5ReaderError(
                "The PH5 dataset does not have any Array_t table.")

        if chNo > 3:
            errMsg = "Limitation for number of channels is 3" + \
                     "\nwhile this experiment has up to %s channels " + \
                     "for one array."
            raise PH5ReaderError(errMsg % chNo)

    ###############################################
    # def readData_nonEvent
    # Author: Lan Dam
    # Updated: 201802
    # to populate data in case of lacking of events' information
    # (based on readData_shotGather)
    def readData_loiEvent(
            self, orgStartT, offset, timeLen, staSpc,
            appClockDriftCorr, redVel,                  # corrections
            PH5View, statusBar=None, beginMsg=None):
        '''
           Read trace data based on given start and stop epoch,
             arrays, and channels.
           Sets: self.metadata
           Returns: info
        '''
        sampleRate = PH5View.selectedArray['sampleRate']
        statusMsg = beginMsg + ": preparing event table"
        statusBar.showMessage(statusMsg)

        # For each event, loop through each station,
        # each channel in the requested array and extract trace data.
        self.data = {}
        info = {}
        # info['maxP2P'] =  -1 * (2**31 - 1)
        info['zeroDOffsetIndex'] = None
        info['LEN'] = {}
        info['quickRemoved'] = {}
        info['deepRemoved'] = {}
        info['numOfSamples'] = 0

        # secs = timeLen
        # ss = ""
        Offset_t = {}
        self.minOffset = None
        self.maxOffset = None

        a = self.ARRAY[0]  # currently allow to select one array at a time
        rows = self.fio.Array_t[a]['byid']
        order = self.fio.Array_t[a]['order']

        listOfStations = sorted(PH5View.selectedArray['seclectedStations'])
        self.metadata = [None] * len(listOfStations)
        info['distanceOffset'] = [None] * len(listOfStations)

        if orgStartT is not None:
            startTime = orgStartT + offset
            stopTime = startTime + timeLen

        info['noDataList'] = []
        listOfDataStations = []
        lenlist = {'less': {}, 'maybeless': {}}
        """
        #   If there is an associated event calculate offset distances
        for ev in PH5View.selectedEvents:
            #print "ev['eventId']:",ev['eventId']
            Offset_t[a] = self.fio.calc_offsets(
                a, ev['eventId'], ev['eventName'])

            if orgStartT is None:
                startTime = ev['eStart'] + offset
                stopTime = startTime + timeLen
        """
        ev = None
        sr = None
        # slen = None

        count = 0
        for o in order:
            for ch in self.CHANNEL:
                if ch not in self.data.keys():
                    self.data[ch] = [[]] * len(listOfStations)
                    info['LEN'][ch] = [0] * len(listOfStations)
                    lenlist['less'][ch] = []
                    lenlist['maybeless'][ch] = []
                    info['quickRemoved'][ch] = {}
                    info['deepRemoved'][ch] = []

                for r in rows[o][ch]:
                    try:
                        if r['id_s'] not in \
                                PH5View.selectedArray['seclectedStations']:
                            raise PH5ReaderError("Continue")
                        ii = listOfStations.index(r['id_s'])

                        if not ph5api.is_in(
                                r['deploy_time/epoch_l'],
                                r['pickup_time/epoch_l'],
                                startTime, stopTime):
                            raise PH5ReaderError("Continue")

                        das = r['das/serial_number_s']
                        corr = self.calcCorrection(
                            ii, das, ch, Offset_t, a, r, startTime,
                            sampleRate, staSpc, appClockDriftCorr, redVel)

                        # + 1.1/sampleRate: add a little bit than
                        # the time of one sample
                        traces = self.fio.cut(
                            das, startTime-corr[0]/1000.,
                            stopTime-corr[0]/1000. + 1.1/sampleRate,
                            ch, sampleRate, apply_time_correction=False)

                        trace = ph5api.pad_traces(traces)

                        if trace.nsamples == 0:
                            v = (PH5View.selectedArray['arrayId'],
                                 das, r['id_s'], ch)
                            noDataItem = \
                                "Array:%s  Das: %s  Station: %s  Chan: %s"
                            noDataItem %= v

                            if noDataItem not in info['noDataList']:
                                info['noDataList'].append(noDataItem)
                            raise PH5ReaderError("Continue")
                        if sr is None:
                            sr = trace.sample_rate
                            # slen = int ((secs * sr) + 0.5)

                        self.getMetadata(
                            info, lenlist, ii, trace, a, ev, r, ch, das,
                            Offset_t, corr, staSpc, orgStartT, startTime)

                        trace.data = np.array(trace.data, dtype=np.float32)
                        if len(self.data[ch][ii]) < trace.nsamples:
                            self.data[ch][ii] = (trace.data)
                            info['LEN'][ch][ii] = trace.nsamples
                            if r['id_s'] not in listOfDataStations:
                                listOfDataStations.append(r['id_s'])
                            if 'minmax' not in self.metadata[ii].keys():
                                self.metadata[ii]['minmax'] = \
                                    (np.amin(trace.data), np.amax(trace.data))
                            else:
                                minval = min(
                                    self.metadata[ii]['minmax'][0],
                                    np.amin(trace.data))
                                maxval = max(
                                    self.metadata[ii]['minmax'][1],
                                    np.amax(trace.data))
                                self.metadata[ii]['minmax'] = (minval, maxval)

                            count += 1
                            if statusBar is not None and count % 10 == 0:
                                statusMsg = beginMsg + ": reading data and" + \
                                    " metadata: %s station-channels"
                                statusBar.showMessage(statusMsg % count)

                    except PH5ReaderError, e:
                        if e.message == "Continue":
                            if r['id_s'] in listOfStations:
                                lenlist['less'][ch].append(ii)
                        else:
                            raise e

        for ch in self.CHANNEL:
            for i in lenlist['less'][ch]:
                replace = np.zeros(info['numOfSamples'])
                if info['LEN'][ch][i] != 0:
                    replace[:info['LEN'][ch][i]] = self.data[ch][i]
                self.data[ch][i] = replace

        # distance offset tend to increase
        info['up'] = True

        # list of stations that have distance offset different from the trend
        info['abnormal'] = []
        if staSpc is None and orgStartT is not None:
            up = []
            down = []
            for i in range(1, len(listOfDataStations)):
                staId = listOfStations.index(listOfDataStations[i])
                pStaId = listOfStations.index(listOfDataStations[i-1])
                if info['distanceOffset'][staId] > \
                        info['distanceOffset'][pStaId]:
                    up.append((pStaId, staId))
                else:
                    down.append((pStaId, staId))

            checkedList = down
            if len(down) > len(up):
                checkedList = up
                info['up'] = False

            for a1, a2 in checkedList:
                if a1 not in info['abnormal']:
                    info['abnormal'].append(a1)
                if a2 not in info['abnormal']:
                    info['abnormal'].append(a2)

        info['numOfStations'] = len(listOfStations)
        info['minOffset'] = self.minOffset

        info['sumD'] = self.maxOffset - self.minOffset
        info['numOfDataStations'] = len(listOfDataStations)

        return info

    ###############################################
    # def readData_receiverGather
    # Author: Lan Dam
    # Updated: 201701
    # to populate data for receiverGather
    def readData_receiverGather(
            self, orgStartT, offset, timeLen, staSpc,
            appClockDriftCorr, redVel,        # corrections
            PH5View, statusBar=None, beginMsg=None):
        '''
           Read trace data based on given start and stop epoch, arrays,
                and channels.
           receiverGather get the events from ONE selected station-channel
           Sets: self.metadata
           Returns: info
        '''
        sampleRate = PH5View.selectedArray['sampleRate']
        statusMsg = beginMsg + ": preparing event table"
        statusBar.showMessage(statusMsg)

        # For each event, loop through each station,
        # each channel in the requested array and extract trace data.
        self.data = []
        info = {}
        info['maxP2P'] = -1 * (2**31 - 1)
        info['zeroDOffsetIndex'] = None
        info['distanceOffset'] = []
        # secs = timeLen

        Offset_t = {}
        self.minOffset = None
        self.maxOffset = None

        # receiver gather has only one pair of station-channel
        staId = PH5View.selectedArray['seclectedStations'][0]
        ch = self.CHANNEL[0]
        self.metadata = []
        self.data = {ch: []}
        a = self.ARRAY[0]  # currently allow to select one array at a time

        if orgStartT is not None:
            startTime = orgStartT + offset
            stopTime = startTime + timeLen

        lenlist = {'less': {ch: []}, 'maybeless': {ch: []}}
        info['numOfSamples'] = 0
        info['noDataList'] = []
        info['LEN'] = {ch: []}

        # If there is an associated event calculate offset distances
        for ev in PH5View.selectedEvents:
            Offset_t[a] = self.fio.calc_offsets(
                a, ev['eventId'], ev['eventName'])

            if orgStartT is None:
                startTime = ev['eStart'] + offset
                stopTime = startTime + timeLen

            sr = None
            # slen = None
            rows = self.fio.Array_t[a]['byid']

            line_seq = 0

            r = rows[staId][ch][0]
            ii = len(self.metadata)
            try:
                if not ph5api.is_in(
                        r['deploy_time/epoch_l'],
                        r['pickup_time/epoch_l'], startTime, stopTime):
                    continue

                das = r['das/serial_number_s']

                corr = self.calcCorrection(
                        ii, das, ch, Offset_t, a, r, startTime,
                        sampleRate, staSpc, appClockDriftCorr, redVel)

                # + 1.1/sampleRate: add a little bit than the
                # time of one sample
                traces = self.fio.cut(
                    das, startTime-corr[0]/1000.,
                    stopTime-corr[0]/1000. + 1.1/sampleRate,
                    ch, sampleRate, apply_time_correction=False)

                trace = ph5api.pad_traces(traces)

                if trace.nsamples == 0:
                    v = (ev['eventId'], PH5View.selectedArray['arrayId'],
                         das, r['id_s'], ch)
                    noDataItem = "Event:%s  Array:%s  Das: %s  " + \
                        "Station: %s  Chan: %s"
                    noDataItem %= v

                    if noDataItem not in info['noDataList']:
                        info['noDataList'].append(noDataItem)
                    continue
                if sr is None:
                    sr = trace.sample_rate
                    # slen = int ((secs * sr) + 0.5)

                self.metadata.append(None)
                info['distanceOffset'].append(None)

                self.getMetadata(info, lenlist, ii, trace, a, ev, r, ch, das,
                                 Offset_t, corr, staSpc, orgStartT, startTime)

                trace.data = np.array(trace.data, dtype=np.float32)

                self.data[ch].append(trace.data)
                info['LEN'][ch].append(trace.nsamples)

                self.metadata[ii]['minmax'] = (np.amin(trace.data),
                                               np.amax(trace.data))

                if statusBar is not None and line_seq % 10 == 0:
                    statusMsg = beginMsg + ": reading data and metadata: " + \
                        "%s events"
                    statusBar.showMessage(statusMsg % line_seq)
            except PH5ReaderError, e:
                raise e

        for i in lenlist['less'][ch]:
            replace = np.zeros(info['numOfSamples'])
            if info['LEN'][ch][i] != 0:
                replace[:info['LEN'][ch][i]] = self.data[ch][i]
            self.data[ch][i] = replace

        # use fixed offset => offset always increase
        info['up'] = True
        info['abnormal'] = []

        info['quickRemoved'] = {ch: {}}
        info['deepRemoved'] = {ch: []}
        info['numOfDataStations'] = info['numOfStations'] = len(self.data[ch])
        info['zerosList'] = []

        info['minOffset'] = self.minOffset
        info['sumD'] = self.maxOffset - self.minOffset

        return info

    ###############################################
    # def readData_shotGather
    # Author: Lan Dam
    # Updated: 201701
    # to populate data for shotGather
    def readData_shotGather(
            self, orgStartT, offset, timeLen, staSpc,
            appClockDriftCorr, redVel,        # corrections
            PH5View, statusBar=None, beginMsg=None):
        '''
           Read trace data based on given start and stop epoch,
              arrays, and channels.
           Sets: self.metadata
           Returns: info
        '''
        sampleRate = PH5View.selectedArray['sampleRate']
        statusMsg = beginMsg + ": preparing event table"
        statusBar.showMessage(statusMsg)

        # For each event, loop through each station,
        # each channel in the requested array and extract trace data.
        self.data = {}
        info = {}
        # info['maxP2P'] =  -1 * (2**31 - 1)
        info['zeroDOffsetIndex'] = None
        info['LEN'] = {}
        info['quickRemoved'] = {}
        info['deepRemoved'] = {}
        info['numOfSamples'] = 0

        Offset_t = {}
        self.minOffset = None
        self.maxOffset = None

        a = self.ARRAY[0]  # currently allow to select one array at a time
        rows = self.fio.Array_t[a]['byid']
        order = self.fio.Array_t[a]['order']

        listOfStations = sorted(PH5View.selectedArray['seclectedStations'])
        self.metadata = [None] * len(listOfStations)
        info['distanceOffset'] = [None] * len(listOfStations)

        if orgStartT is not None:
            startTime = orgStartT + offset
            stopTime = startTime + timeLen

        info['noDataList'] = []
        listOfDataStations = []
        lenlist = {'less': {}, 'maybeless': {}}
        # If there is an associated event calculate offset distances
        for ev in PH5View.selectedEvents:
            Offset_t[a] = self.fio.calc_offsets(
                a, ev['eventId'], ev['eventName'])

            if orgStartT is None:
                startTime = ev['eStart'] + offset
                stopTime = startTime + timeLen

            sr = None
            count = 0
            for o in order:
                for ch in self.CHANNEL:
                    if ch not in self.data.keys():
                        self.data[ch] = [[]] * len(listOfStations)
                        info['LEN'][ch] = [0] * len(listOfStations)
                        lenlist['less'][ch] = []
                        lenlist['maybeless'][ch] = []
                        info['quickRemoved'][ch] = {}
                        info['deepRemoved'][ch] = []

                    for r in rows[o][ch]:
                        try:
                            if r['id_s'] not in \
                                    PH5View.selectedArray['seclectedStations']:
                                raise PH5ReaderError("Continue")
                            ii = listOfStations.index(r['id_s'])

                            if not ph5api.is_in(
                                    r['deploy_time/epoch_l'],
                                    r['pickup_time/epoch_l'],
                                    startTime, stopTime):
                                raise PH5ReaderError("Continue")

                            das = r['das/serial_number_s']
                            corr = self.calcCorrection(
                                ii, das, ch, Offset_t, a, r, startTime,
                                sampleRate, staSpc, appClockDriftCorr, redVel)

                            # + 1.1/sampleRate: add a little bit
                            # than the time of one sample
                            traces = self.fio.cut(
                                das, startTime-corr[0]/1000.,
                                stopTime-corr[0]/1000. + 1.1/sampleRate,
                                ch, sampleRate, apply_time_correction=False)

                            trace = ph5api.pad_traces(traces)

                            if trace.nsamples == 0:
                                v = (ev['eventId'],
                                     PH5View.selectedArray['arrayId'],
                                     das, r['id_s'], ch)
                                noDataItem = \
                                    "Event:%s  Array:%s  Das: %s  " + \
                                    "Station: %s  Chan: %s"
                                noDataItem %= v

                                if noDataItem not in info['noDataList']:
                                    info['noDataList'].append(noDataItem)

                                raise PH5ReaderError("Continue")
                            if sr is None:
                                sr = trace.sample_rate
                                # slen = int ((secs * sr) + 0.5)

                            self.getMetadata(info, lenlist, ii, trace, a, ev,
                                             r, ch, das, Offset_t, corr,
                                             staSpc, orgStartT, startTime)

                            trace.data = np.array(trace.data,
                                                  dtype=np.float32)
                            if len(self.data[ch][ii]) < trace.nsamples:
                                self.data[ch][ii] = (trace.data)
                                info['LEN'][ch][ii] = trace.nsamples
                                if r['id_s'] not in listOfDataStations:
                                    listOfDataStations.append(r['id_s'])
                                if 'minmax' not in self.metadata[ii].keys():
                                    self.metadata[ii]['minmax'] = \
                                        (np.amin(trace.data),
                                         np.amax(trace.data))
                                else:
                                    minval = min(
                                        self.metadata[ii]['minmax'][0],
                                        np.amin(trace.data))
                                    maxval = max(
                                        self.metadata[ii]['minmax'][1],
                                        np.amax(trace.data))
                                    self.metadata[ii]['minmax'] = \
                                        (minval, maxval)

                                count += 1
                                if statusBar is not None and count % 10 == 0:
                                    statusMsg = beginMsg + \
                                        ": reading data and " + \
                                        "metadata: %s station-channels"
                                    statusBar.showMessage(statusMsg % count)

                        except PH5ReaderError, e:
                            if e.message == "Continue":
                                if r['id_s'] in listOfStations:
                                    lenlist['less'][ch].append(ii)
                            else:
                                raise e

        for ch in self.CHANNEL:
            for i in lenlist['less'][ch]:
                replace = np.zeros(info['numOfSamples'])
                if info['LEN'][ch][i] != 0:
                    replace[:info['LEN'][ch][i]] = self.data[ch][i]
                self.data[ch][i] = replace

        # distance offset tend to increase
        info['up'] = True
        # list of stations that have distance offset different from the trend
        info['abnormal'] = []
        if staSpc is None and orgStartT is not None:
            up = []
            down = []
            for i in range(1, len(listOfDataStations)):
                staId = listOfStations.index(listOfDataStations[i])
                pStaId = listOfStations.index(listOfDataStations[i-1])
                if info['distanceOffset'][staId] > \
                        info['distanceOffset'][pStaId]:
                    up.append((pStaId, staId))
                else:
                    down.append((pStaId, staId))

            checkedList = down
            if len(down) > len(up):
                checkedList = up
                info['up'] = False

            for a1, a2 in checkedList:
                if a1 not in info['abnormal']:
                    info['abnormal'].append(a1)
                if a2 not in info['abnormal']:
                    info['abnormal'].append(a2)

        info['numOfStations'] = len(listOfStations)
        info['minOffset'] = self.minOffset

        info['sumD'] = self.maxOffset - self.minOffset
        info['numOfDataStations'] = len(listOfDataStations)

        return info

    ############################################
    # def readData_shotGather
    # Author: Lan Dam
    # Updated: 201803
    def getMetadata(self, info, lenlist, ii, trace, a, ev, r, ch,
                    das, Offset_t, corr, staSpc, orgStartT, startTime):
        '''
           Sets: self.metadata[ii]
        '''
        if self.metadata[ii] is not None:
            self.metadata[ii]['chans'].append(r['channel_number_i'])
        else:
            self.metadata[ii] = {}
            self.metadata[ii]['totalCorr'] = corr[0]
            self.metadata[ii]['clockDriftCorr'] = corr[1]
            self.metadata[ii]['redVelCorr'] = corr[2]
            self.metadata[ii]['absStartTime'] = \
                timedoy.epoch2passcal(startTime)
            self.metadata[ii]['arrayId'] = a[-3:]
            self.metadata[ii]['stationId'] = r['id_s']
            self.metadata[ii]['eventId'] = ev['eventId'] if ev is not None \
                else None
            self.metadata[ii]['dasSerial'] = das
            self.metadata[ii]['chans'] = [r['channel_number_i']]
            self.metadata[ii]['desc'] = r['description_s']
            self.metadata[ii]['lat'] = r['location/Y/value_d']
            self.metadata[ii]['long'] = r['location/X/value_d']
            self.metadata[ii]['elev'] = r['location/Z/value_d']
            self.metadata[ii]['elevUnit'] = r['location/Z/units_s'].strip()
            if staSpc is None and orgStartT is not None:
                # If no offset distance just set them to an
                # incremented sequence
                try:
                    offset_t = Offset_t[a]['byid'][r['id_s']]
                    info['distanceOffset'][ii] = (offset_t['offset/value_d'])
                    if offset_t['offset/value_d'] == 0:
                        info['zeroDOffsetIndex'] = ii

                    self.metadata[ii]['distanceOffsetUnit'] = \
                        offset_t['offset/units_s']
                    self.metadata[ii]['azimuth'] = \
                        offset_t['azimuth/value_f']
                    self.metadata[ii]['azimuthUnit'] = \
                        offset_t['azimuth/units_s']

                except Exception as e:

                    print e.message

                    info['distanceOffset'][ii] = ii
                    self.metadata[ii]['distanceOffsetUnit'] = 'm'
                    self.metadata[ii]['azimuth'] = 0
                    self.metadata[ii]['azimuthUnit'] = 'degrees'

                    raise PH5ReaderError("NoDOffset")

            else:
                info['distanceOffset'][ii] = (staSpc * ii)

            if self.minOffset is None:
                self.minOffset = info['distanceOffset'][ii]
                self.maxOffset = info['distanceOffset'][ii]
            else:
                if info['distanceOffset'][ii] < self.minOffset:
                    self.minOffset = info['distanceOffset'][ii]
                if info['distanceOffset'][ii] > self.maxOffset:
                    self.maxOffset = info['distanceOffset'][ii]

            self.metadata[ii]['sample_rate'] = trace.sample_rate
            self.metadata[ii]['numOfSamples'] = trace.nsamples

            # 201803: in case the first trace has less data than numOfSamples
            if ii == 0:
                lenlist['maybeless'][ch].append(ii)
            if trace.nsamples < info['numOfSamples']:
                lenlist['less'][ch].append(ii)
            elif trace.nsamples > info['numOfSamples']:
                info['numOfSamples'] = trace.nsamples
                lenlist['less'][ch] += lenlist['maybeless'][ch]
                lenlist['maybeless'][ch] = []
            else:
                lenlist['maybeless'][ch].append(ii)

            info['interval'] = 1000. / trace.sample_rate
            """
            # Non-displayed metadata. If need to be displayed,
            # in case Response table is missing,
            # should give user a warning about these parameters
            # having None Values.
            try:
                response = \
                    self.fio.Response_t['rows'][trace.das_t[0] \
                    ['response_table_n_i']]
            except IndexError:
                response = {'gain/value_i':None, 'gain/units_s':None,
                            'bit_weight/value_d':None,
                            'bit_weight/units_s':None}

            self.metadata[ii]['gain'] = response['gain/value_i']
            self.metadata[ii]['gainUnit'] = response['gain/units_s']
            self.metadata[ii]['bitWeight'] = response['bit_weight/value_d']
            self.metadata[ii]['bitWeightUnit'] = response['bit_weight/units_s']

            self.metadata[ii]['component'] = \
                self.fio.Receiver_t['rows'][trace.das_t[0]\
                ['receiver_table_n_i']]['orientation/description_s']
            self.metadata[ii]['azimuth'] = \
                self.fio.Receiver_t['rows'][trace.das_t[0]\
                ['receiver_table_n_i']]['orientation/azimuth/value_f']
            self.metadata[ii]['azimuthUnit'] = \
                self.fio.Receiver_t['rows'][trace.das_t[0] \
                ['receiver_table_n_i']]['orientation/azimuth/units_s']
            self.metadata[ii]['dip'] = \
                self.fio.Receiver_t['rows'][trace.das_t[0] \
                ['receiver_table_n_i']]['orientation/dip/value_f']
            self.metadata[ii]['dipUnit'] = \
                self.fio.Receiver_t['rows'][trace.das_t[0] \
                ['receiver_table_n_i']]['orientation/dip/units_s']
            """

    def calcCorrection(self, ii, das, c, Offset_t, a, r, startTime, sampleRate,
                       staSpc, appClockDriftCorr, redVel):
        totalCorr = 0
        redVelCorr = None
        if redVel is not None:
            if staSpc is None:
                try:
                    dOffset = Offset_t[a]['byid'][r['id_s']]['offset/value_d']

                except Exception:
                    raise PH5ReaderError("NoDOffset")
            else:
                dOffset = staSpc * ii
            redVelCorr = -1000*abs(dOffset/redVel)
            totalCorr += redVelCorr

        # check if apply_time_correction should be True or False
        traces = self.fio.cut(
            das, startTime, startTime + 1.1 /
            sampleRate, c, sampleRate, apply_time_correction=True)
        trace = ph5api.pad_traces(traces)
        clockDriftCorr = trace.time_correction_ms

        if appClockDriftCorr:
            totalCorr += clockDriftCorr

        return totalCorr, clockDriftCorr, redVelCorr


html_manual = """
<html>
<head>
<style>
table, th, td {
    border: 1px solid black;
}
</style>
<title>Manual Page</title>
</head>
<body>
<h2>Manual</h2>
<hr />

<h2><a id="contents">Contents:</a></h2>
<ul>
    <li><a href="#generalInfo">General Information</a></li>
    <li><a href="#openPH5">Open PH5 file</a></li>

    <li><a href="#selectTraces">Select traces to plot</a></li>
    <ul>
        <li><a href="#shotGather">Shot Gather</a></li>
        <li><a href="#receiverGather">Receiver Gather</a></li>
        <li><a href="#eventLoi">Event LOI</a></li>
    </ul>

    <li>Plotting
    <ul>
        <li><a href="#setProp">Set properties</a></li>
        <li><a href="#setPara">Set parameters</a></li>
        <li><a href="#plot">Plotting</a></li>
    </ul>
    </li>

    <li><a href="#plotView">Plot View</a>
    <ul>
        <li><a href="#zoomPan">Zoom/Pan with navigation buttons</a></li>
        <li><a href="#zoomSelect">Zoom the selected area</a></li>
        <li><a href="#traceInfo">Info of traces</a></li>
        <li><a href="#quickRem">Quick remove traces</a></li>
        <li><a href="#deepRem">Deep remove traces</a></li>
    </ul>
    </li>

    <li><a href="#savePrint">Save/Print</a></li>
    <li><a href="#segy">Produce SEGY file</a></li>
</ul>
&nbsp;
<table style="width:100%">
<tbody>
<tr>
<td>

<h2><a id="generalInfo">General Information</a></h2>
<div>The application has three main panels:</div>
<ul>
    <li>Control Panel: the panel with the menu and three tabs
 (Control, Shot Gather, Receiver Gather).</li>
    <li>Main Window: the main panel for plotting.</li>
    <li>Support Window: the panel to show small portion of the plot (the idea
 is to reduce the amount of trace need to be analyzed.</li>
</ul>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>

<h2><a id="openPH5">Open PH5 file</a></h2>
<div>Menu: File - Open File</div>
<div>Select the master.ph5 file of the data then click Open.</div>
<div>The name of the Experiment will be assigned to Graphic Name.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>

<h2><a id="selectTraces">Select traces to plot</a></h2>
<div>After ph5 file is selected, user can select Shot Gather tab or Receiver
 Gather tab for plotting.</div>
<div>By default, Shot Gather tab will be opened.</div>
<div>In case of lacking of information for events (e.g. no event_t table, no
 sort_t table), Event LOI tab will be available for plotting.</div>
<div>&nbsp;</div>

<h3><a id="shotGather">Shot Gather</a></h3>
<div>Select an array tab to show the events for that array only.</div>
<div>&nbsp;</div>
<div>Select a shot line by clicking on a Shot Lines radio button to enable all
 the events belong to that</div>
<div>shot line while disable other events.</div>
<div>&nbsp;</div>
<div>Select one event by clicking on an Events radio button to pop up a new
 box which allow user to select</div>
<div>channels and stations for the plot.</div>
<div>&nbsp;</div>
<div>Select all needed channels by clicking on Channels check boxes.</div>
<div>&nbsp;</div>
<div>Select needed Stations:</div>
<ul>
    <li>Click on the check box on top to select/clear all stations<</li>
    <li>Click the check box on the left of each station to select/deselect
 that station.</li>
    <li>Shift+Left Click to select a range of stations from the current one
 to the closest one.</li>
</ul>

<div>Click Submit button to submit all traces' info for plotting, then the
 Control tab will be shown  for user to set parameters before plotting.</div>
<div align="right"><a href="#contents">Contents</a></div>

<h3><a id="receiverGather">Receiver Gather</a></h3>
<div>Select an array tab to show the events for that array only.</div>
<div>&nbsp;</div>
<div>Select a channel by clicking on a Channels radio button.</div>
<div>&nbsp;</div>
<div>Select one station by clicking on a Stations radio button to pop up a new
 box which allow user to select</div>
<div>events for the plot.</div>
<div>&nbsp;</div>
<div>
<div>Select a shot line by clicking on a Shot Lines radio button to enable all
 the events belong to that</div>
<div>shot line while disable other events.</div>
</div>
<div>&nbsp;</div>
<div>Select needed Events:</div>
<ul>
    <li>Click on the check box on top to select/clear all stations.</li>
    <li>Click the check box on the left of each event to select/deselect that
 event.</li>
    <li>Shift+Left Click to select a range of events from the current one to
 the closest one.</li>
</ul>
<div>Click Submit button to submit all traces' info for plotting, then the
 Control tab will be shown  for user to set parameters before plotting.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>

<h3><a id="eventLoi">Event LOI</a></h3>
<div>Select an array tab to show the events for that array only.</div>
<div>&nbsp;</div>
<div>Select all needed channels by clicking on Channels check boxes.</div>
<div>&nbsp;</div>
<div>Select needed Stations:</div>
<ul>
    <li>Click on the check box on top to select/clear all stations.</li>
    <li>Click the check box on the left of each station to select/deselect
 that station.</li>
    <li>Shift+Left Click to select a range of stations from the current one
 to the closest one.</li>
</ul>

<div>Click Submit button to submit all traces' info for plotting, then
 the Control tab will be shown  for user to set parameters before plotting.
</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</div></td>
</tr>
<tr>
<td>

<h2>Plotting </h2>

<h3><a id="setProp">Set properties</a></h3>
<div>Click on Name-Color Prop. to set the drawing properties for the plot:
</div>
<ul>
    <li>AddingInfo to Graphic Name: The additional info to the graphic name
 which show in the title of Main Window, Support Window, Saved Graphic,
 Printed Graphic.</li>
    <li>Horizontal Label: the label for x direction.</li>
    <li>Vertical Label: the label for y direction.</li>
    <li>Pattern Size: The number of traces in one color pattern which will
 be repeated through out plotted traces. The pattern can be defined on the
 right side of the properties. . Click on Update button to update the new
 size for the pattern</li>
    <li>Trace Thickness: The thickness of traces in Saved/Printed Graphic.</li>
    <li>Grid Thickness: The thickness of grid lines in Saved/printed Graphic.
 Click the Color button on the right side to define the color for grid
 lines.</li>
    <li>Abnormal Station(s): check/uncheck to allow/disallow the option of
 showing the trace with abnormal trend of distance offset in the color set
 by the button on the right.</li>
    <li>Pattern Colors: There are at most 3 channels with 3 pattern related
 to them. Click the button on the top to define color for all traces in each
 pattern. User can change color for individual traces in pattern by clicking
 on the corresponding buttons.</li>
</ul>
<div align="right"><a href="#contents">Contents</a></div>

<h3><a id="setPara">Set parameters</a></h3>
<div>User can set parameters before Click on "Get Data and Plot" to plot the
 traces </div>
<ul>
    <li>Start time: The start time for all traces. With Receiver Gather,
 Start time is non-applicable.</li>
    <li>Length: Length of time need to be viewed for each trace.</li>
    <li>Offset: Time offset in second. In the plot, the start time of the
 trace will be moved relative to the shot time.</li>
    <li>Ignore minor signal: In a trace, if signals are lower than this
 percentage value of the peak, it will be ignore to reduce the amount of
 drawing points (for faster performance).The new value can be applied without
 re-reading PH5 data by clicking on Apply button next to it.</li>
    <li>Overlap: Define the percentage of width given for each trace can be
 overlapped.The new value can be applied without re-reading PH5 data by
 clicking on Apply button next to it.</li>
    <li>NORMALIZE: If checked, each station's signal will grow to its entire
 given width.If not, use the same scale for all stations' signal so that the
 highest peak can use entire given width.</li>
    <li>STATION SPACING UNKNOWN: If not checked, use the real distance offset
 to locate each station in the plot. If checked, use 'Nominal station spacing'
 as space between two stations.(fixed distance)</li>
    <li>Nominal station spacing(m):If 'STATION SPACING UNKNOWN' is selected,
 this will be used as space between two stations.</li>
    <li>Reduction Velocity(m/s):Reduction Velocity applied to the plot.
 Applied when the given value is > 0</li>
    <li>Time Correction: Select to include clock drift correction.</li>
    <li>Properties: Check Default Prop. to use Default Properties;
 Previous Prop. to use the properties that were use prevously.Previous
 properties can be editted by clicking 'Name-Color Prop'. Click 'Apply and
 RePlot' to apply the selected property option.</li>
    <li>Distance grid: Select/deselect to show/hide distance grid lines.
 Take effect right after selected.</li>
    <li>Time grid: Select/deselect to show/hide time grid lines. Take effect
 right after selected</li>
    <li>ReGrid Panel: select if the new grid intervals will be applied on
 which window(s) when ReGrid button is clicked</li>
    <li>Time Grid Interval (s): Time Grid Interval in second (to be viewable,
 no more than 25 time grid lines in a plot).</li>
    <li>Dista. Grid Interval (km): Distance Grid Interval in kilometer (to be
 viewable, no more than 50 distance grid lines in a plot).</li>
    <li>ReGrid: Click to apply new grid intervals if the entered values are
 available.</li>
    <li>Channels: Check to select the channel(s) needed for the plot. Click
 Apply to apply the change without re-reading PH5 data</li>
    <li>Time Direction: Down => time grow from top to bottom. Up: time grow
 from bottom to top.</li>
    <li>Drawing Style: Lines or points - Take effect right after selected</li>
</ul>
<div align="right"><a href="#contents">Contents</a></div>

<h3><a id="plot">Plotting</a></h3>
Click 'Get Data and Plot' button to read PH5 data and plot with the settings.
Under 'Get and Data Plot' is the information of the current plot view of the
 selected Window.
<div align="right"><a href="#contents">Contents</a></div>
</td>
</tr>
<tr>
<td>

<h2><a id="plotView">Plot View</a></h2>
<div>When Zoom or Pan is performed, the displayed information under 'Get Data
 and Plot' button will be updated.</div>
<div>ResetZoom/Pan button is to get the view back to the beginning one.</div>
<div>&nbsp;</div>

<h3><a id="zoomPan">Zoom/Pan with navigation buttons</a></h3>
<div>This option is enabled when radio button Zoom/pan is selected.</div>
<div>&nbsp;</div>
<div><strong>Distance:</strong>The value d in the text box define how many
 kilometers (scaled) to the left/right the view can go when the navigation
 buttons for distance is click.</div>
<ul>
    <li><: Move the plot to the left of the window d km.</li>
    <li>>: Move the plot to the right of the window d km.</li>
    <li>+: Zoom out the plot d km to the left and d km to the right of
 the window.</li>
    <li>-: Zoom in the plot d km from the left and d km from the right of
 the window.</li>
</ul>
<div>&nbsp;</div>
<div><strong>Time:</strong>The value t in the text box define how many seconds
 (scaled) to the top/bottom the view can go when the navigation buttons for
 time is click.</div>
<ul>
    <li>A: Move the plot to the top of the window t seconds.</li>
    <li>V: Move the plot to the bottom of the window t seconds.</li>
    <li>+: Zoom out the plot t seconds to the top and t seconds to the
 bottom of the window.</li>
    <li>-: Zoom in the plot t seconds from the top and t seconds from the
 bottom of the window.</li>
</ul>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>

<h3><a id="zoomSelect">Zoom the selected area</a></h3>
<div>This option is enabled when radio button Selecting is selected</div>
<ul>
    <li>To create the selected area, drag the mouse from the starting
 point to the ending point. One small square will show up at the starting
 point when dragging, and the rectangle defining the whole selected area
 will only show up when the mouse is released.</li>
    <li>Click Zoom Selection: to zoom the selected area in the current
 window.</li>
    <li>Click Pass Selection to Support Window (this option for Main
 Window only): to zoom the selected area in the Support Window. In the new
 window, all other part will be cut off for better performance when the data
 need to analyzed is too big. User should chooses when working on the Main
 Window become too slow.</li>
</ul>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>

<h3><a id="traceInfo">Info of traces</a></h3>
<div>Right-click on trace(s) for the info of traces to pop up.</div>
<div>On top of the traces of which the values cover the position of the mouse,
 there will be red squares to mark those selected traces. However, there are
 at most 3 markers corresponding to 3 stations showed because of the following
 reasons:</div>
<ul>
    <li>Preset the markers to save time</li>
    <li>If many markers are close together, they will overlap each other,
 which makes user harder to observe.</li>
</ul>
<div>&nbsp;</div>

<h3><a id="quickRem">Quick remove traces</a></h3>
<div>In the trace info pop-up, User can choose QuickRemoved for the selected
 trace. It will take effect right away by turning the color of the trace to
 white.</div>
<div>Uncheck QuickRemoved to get the trace back or click Undo QuickRemove in
 the Window to get all QuickRemoved traces back.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>

<h3><a id="deepRem">Deep remove traces</a></h3>
<div>In the trace info pop-up, User can choose DeepRemoved for the selected
 trace. It will NOT take effect right away but only take effect to all
 DeepRemoved selected traces by removing them from the data set.</div>
<div>Click Undo Deep Removed  to get all DeepRemoved traces back.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div></td>
</tr>
<tr>
<td>

<h2><a id="savePrint">Save/Print</a></h2>
<div>Choose one Save/Print option in Save/Print Menu.
<ul>
    <li>Save/Print The Whole Image from Main Window: Save/Print the begging
 plot in the Main Window</li>
    <li>Save/Print The Part of Image Showed in Main Window: Only Save/Print
 the part that currently show in the Main Window after zooming/panning.</li>
    <li>Save/Print The Whole Image from Support Window: Save/Print the
 begging plot in the Support Window</li>
    <li>Save/Print The Part of Image Showed in Support Window: Only Save/Print
 the part that currently show in the Support Window after zooming/panning.</li>
</ul>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div></td>
</tr>
<tr>
<td>

<h2><a id="segy">Produce SEGY file</a></h2>
<div>To produce SEGY file, click SEGY in the menu. User will be required to
 select the folder where SEGY file need to be located. Then a pop-up named
 'Enter Sub Directory' will show up to allow user to add the sub-folder name
 if he wants, click cancel if don't want a sub folder.</div>
<div>The command to create SEGY file will be showed in the console for user
 to check.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div></td>
</tr>
</tbody>
</table>
</body>
</html>
"""

html_versionTraces = """
<html>
<head>
<title>What's new? Page</title>
</head>
<body>
<h2>What's new in version 2017.236?</h2>
<hr />
<div>Modifying code to meed Flake8.</div>
<hr />
<hr />
<h2>What's new in version 2018.067?</h2>
<hr />
<ul>
    <li>Event LOI tab is added to allow plotting when Event_t or Sort_t tables
 are missing.</li>
    <li>Bypassing the lack of Experiment_t by giving UNTITLED name to the
 graph.</li>
    <li>Informing user when Array_t, Das_t, Receiver_t tables are missing to
 explain why the graph cannot be drawn.</li>
    <li>Removing FutureWarning in feedGData().</li>
    <li>Fix bug when the trace that has less number of samples is the first
 one.</li>
</ul>
<hr />
<hr />
<h2>What's new in version 2017.236?</h2>
<hr />
<div>Change the code to work with new API</div>
<div>&nbsp;</div>
<div>Allow user to choose multi-channels when applicable:</div>
<ul>
    <li>Receiver Gather tab - allow to select one channel for the plot.</li>
    <li>Shot Gather tab - Select event to open Station Window -
 allow to select different channels for the plot.</li>
    <li>Control tab - Channels checkboxes: allow to quick remove/unremove
 from the selected channels in shot gather.</li>
    <li>Properties Dialog - Allow to select different color patterns
 for different channels.</li>
    <li>Info Panel - Allow user to choose different channels of the
 selected station to remove for both QuickRemoved and DeepRemoved.</li>
</ul>
<div>Allow user to choose shotline for plotting when applicable:</div>
<ul>
    <li>Receiver Gather tab - Select station to open Event Window -
 allow to select one shotline for the plot.</li>
    <li>Shot Gather tab - allow to select one shotline for the plot.</li>
</ul>
<div>Under Help menu there are 2 additional part:</div>
<ul>
    <li>The existing menu now have the name "What?": allow user to point
 the mouse to any of the control to get the explaination for it.</li>
    <li>The new menu "Manual": help user understand how the program work.</li>
    <li>The new menu "What's new?": to provide the new functions added
 to the current version in compare with the previous one.</li>
</ul>
</body>
</html>
"""
