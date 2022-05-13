'''
Tests for ph5torec
'''
import os
import sys
import unittest

from mock import patch
from testfixtures import LogCapture

from ph5.utilities import segd2ph5, initialize_ph5
from ph5.clients import ph5torec
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase, kef_to_ph5


class TestPh5torec_main(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestPh5torec_main, self).setUp()
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()

        segd_file = os.path.join(
            self.home, "ph5/test_data/segd/smartsolo/453005513.2.2021.05.08."
                       "20.06.00.000.E.segd")
        testargs = ['segdtoph5', '-n', 'master', '-r', segd_file]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        metapath = os.path.join(self.home, "ph5/test_data/metadata")
        segd_metapath = os.path.join(metapath, 'smartsolo')
        kef_to_ph5(self.tmpdir, 'master.ph5', metapath, ['experiment.kef'])
        kef_to_ph5(self.tmpdir, 'master.ph5', segd_metapath,
                   ['event_t.kef', 'sort_t.kef', 'offset_t.kef'])

    def test_main(self):
        testargs = ['ph5torec', '-n', 'master.ph5', '-c', '2', '-A', '1',
                    '-S', '1', '--shot_line', '102',
                    '--event_list', '116807', '-N', '-l', '10']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                ph5torec.main()

        self.assertEqual(
            log.records[17].msg,
            "Overlaping between [1620504365.019999, 1620504365.020000]"
            " has been removed."
        )
        self.assertEqual(
            log.records[18].msg,
            "Overlaping between [1620504366.023999, 1620504366.024000]"
            " has been removed."
        )
        self.assertEqual(
            log.records[19].msg,
            "Overlaping between [1620504370.039999, 1620504370.040000]"
            " has been removed."
        )
        self.assertEqual(
            log.records[20].msg,
            "Overlaping between [1620504371.043999, 1620504371.044000]"
            " has been removed."
        )
        self.assertEqual(
            log.records[27].msg,
            "Wrote: 2500 samples with 0 sample padding."
        )


if __name__ == "__main__":
    unittest.main()
