'''
Tests for ph5toevt
'''
import os
import sys
import unittest

from mock import patch
from testfixtures import LogCapture

from ph5.utilities import segd2ph5, initialize_ph5
from ph5.clients import ph5toevt
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


class TestPh5toevt_main(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestPh5toevt_main, self).setUp()

        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()

        segd_file = os.path.join(
            self.home, "ph5/test_data/segd/smartsolo/453005513.2.2021.05.08."
                       "20.06.00.000.E.segd")
        testargs = ['segdtoph5', '-n', 'master', '-r', segd_file]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

    def test_main(self):
        testargs = ['ph5toevt', '-n', 'master.ph5', '-A', '1', '-c', '2', '-s',
                    '2021:128:20:06:14', '-l', '10', '--use_deploy_pickup']
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                ph5toevt.main()

        self.assertEqual(
            log.records[12].msg,
            "Overlaping between [1620504379.075999022, 1620504379.075999975]"
            " has been removed."
        )
        self.assertEqual(
            log.records[13].msg,
            "Overlaping between [1620504380.079998970, 1620504380.079999924]"
            " has been removed."
        )
        self.assertEqual(
            log.records[25].msg,
            "Wrote: 2500 samples with 0 sample padding."
        )


if __name__ == "__main__":
    unittest.main()
