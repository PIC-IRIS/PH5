"""
unit tests for ph5availability
"""

import unittest
import os

from ph5.clients import ph5availability
from ph5.core import ph5api
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase
from ph5.clients.ph5toms import PH5toMSeed
from testfixtures import LogCapture


class TestPH5AvailabilitySampleRate(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5AvailabilitySampleRate, self).setUp()

        self.ph5test_path_sr = os.path.join(self.home,
                                            'ph5/test_data/ph5/samplerate')
        self.ph5_sr = ph5api.PH5(path=self.ph5test_path_sr,
                                 nickname='master.ph5')
        self.sr_avail = ph5availability.PH5Availability(self.ph5_sr)

    def tearDown(self):
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

    def test_availability_samplerate(self):
        with LogCapture() as log:
            ret = self.sr_avail.get_availability(station='10075',
                                                 channel='*',
                                                 starttime=None,
                                                 endtime=None,
                                                 include_sample_rate=True)
            self.assertEqual(6, len(ret))
            self.assertIsNotNone(log)
        # Checks the sample rate of the test data set
        self.assertEqual(500.0, ret[0][5])
        ret2 = self.sr_avail.get_availability_extent(station='10075',
                                                     channel='*',
                                                     starttime=None,
                                                     endtime=None,
                                                     include_sample_rate=True)
        self.assertEqual(3, len(ret2))
        self.assertEqual(500.0, ret2[0][5])
        with LogCapture() as log2:
            ret2 = self.sr_avail.get_availability_extent(station='10075',
                                                         channel='*',
                                                         starttime=None,
                                                         endtime=None)
            self.assertIsNotNone(log2)


class TestPH5AvailabilitySampleRate_error(LogTestCase, TempDirTestCase):
    def test_availability_error(self):
        self.ph5_path_eror = os.path.join(self.home,
                                          'ph5/test_data/ph5/samplerate/error')
        self.ph5_sr_error = ph5api.PH5(path=self.ph5_path_eror,
                                       nickname='master.ph5')
        self.avail_error = ph5availability.PH5Availability(self.ph5_sr_error)
        with LogCapture() as log_error:
            self.avail_error.get_availability(station='10075',
                                              channel='*',
                                              starttime=None,
                                              endtime=None,
                                              include_sample_rate=True)
        self.assertEqual(log_error.records[2].msg,
                         'DAS and Array Table sample rates do'
                         ' not match, DAS table sample rates'
                         ' do not match. Data must be'
                         ' updated.')
        self.ph5_sr_error.close()


if __name__ == "__main__":
    unittest.main()
