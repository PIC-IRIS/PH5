"""
unit tests for ph5availability
"""

import unittest
import os

from ph5.clients import ph5availability
from ph5.core import ph5api
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase
from ph5.clients.ph5toms import PH5toMSeed


def checkTupleAlmostEqualIn(tup, tupList, place):
    """
    check if a tuple in a list of tuples in which float items only
    need to be almost equal
    :type tup: tuple
    :param tup: tuple to be checked
    :type tupList: list of tuples
    :para tupList: list of tuples that tup need to be check with
    :place: decimal places to round the values to compare
    """
    for T in tupList:
        length = len(tup)
        if length != len(T):
            continue
        for i in range(length):
            if type(tup[i]) is float:
                if round(tup[i], place) != round(T[i], place):
                    break
            else:
                if tup[i] != T[i]:
                    break
            if i == length - 1:
                return True
    return False


def checkFieldsMatch(fieldNames, fieldsList, dictList):
    """
    check if given fieldslist match the dict dictList at field fieldNames
    :type fieldsName: list of str
    :param fieldsName: list of field names that their values are to be compared
       with items in dictList
    :type fieldsList: list of tuple
    :para fieldsList: list of tuple of fields' values
    :type dictList: list of dictionary
    :para dictList: list of dictionary to be compared with
    """
    if len(fieldsList) != len(dictList):
        return False
    for d in dictList:
        arow = ()
        for i in range(len(fieldNames)):
            arow += (d[fieldNames[i]], )
        if arow not in fieldsList:
            return False
        fieldsList.remove(arow)
    return True


class TestPH5AvailabilitySampleRate(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5AvailabilitySampleRate, self).setUp()
        self.ph5test_path_sr = os.path.join(self.home,
                                            'ph5/test_data/samplerate')
        self.ph5_sr = ph5api.PH5(path=self.ph5test_path_sr,
                                 nickname='master.ph5')
        self.sr_avail = ph5availability.PH5Availability(self.ph5_sr)

    def tearDown_sr(self):
        self.ph5_sr.close()
        super(TestPH5AvailabilitySampleRate, self).tearDown()

    def test_ms_samplerate(self):
        ph5toms = PH5toMSeed(self.ph5_sr)
        ph5toms.process_all()
        cuts = ph5toms.create_cut_list()
        for cut in cuts:
            trace = ph5toms.create_trace(cut)
            if trace is not None:
                self.assertEqual(trace[0].stats.station, '10075')
        self.ph5_sr.close()

    def test_availability_samplerate(self):
        ret = self.sr_avail.get_availability(station='10075',
                                             channel='*',
                                             starttime=None,
                                             endtime=None,
                                             include_sample_rate=True)
        self.assertEqual(6, len(ret))
        # Checks the sample rate of the test data set
        self.assertEqual(500.0, ret[0][5])
        ret2 = self.sr_avail.get_availability_extent(station='10075',
                                                     channel='*',
                                                     starttime=None,
                                                     endtime=None,
                                                     include_sample_rate=True)
        self.assertEqual(3, len(ret2))
        self.assertEqual(500.0, ret2[0][5])
        self.ph5_sr.close()


if __name__ == "__main__":
    unittest.main()
