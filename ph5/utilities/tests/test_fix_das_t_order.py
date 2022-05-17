'''
Tests for fix_das_t_order
'''
import unittest
import os
import sys
import operator

from mock import patch

from ph5.utilities import fix_das_t_order, segd2ph5
from ph5.core import ph5api, experiment
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase, kef_to_ph5


class TestFix_das_t_order(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestFix_das_t_order, self).setUp()
        segd_file = os.path.join(
            self.home, "ph5/test_data/segd/smartsolo/453005513.2.2021.05.08."
                       "20.06.00.000.E.segd")
        testargs = ['segdtoph5', '-n', 'master', '-r', segd_file]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        ph5_object = ph5api.PH5(
            path=self.tmpdir, nickname='master.ph5', editmode=True)
        ph5_object.ph5_g_receivers.truncate_das_t('1X4')
        kef_to_ph5(
            self.tmpdir, 'master.ph5',
            os.path.join(self.home, 'ph5/test_data/metadata'),
            ['das1X1_messed_order.kef'])
        ph5_object.close()

    def tearDown(self):
        self.ph5object.ph5close()
        super(TestFix_das_t_order, self).tearDown()

    def test_main(self):
        testargs = ['fix_das_t_order', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            fix_das_t_order.main()

        self.ph5object = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        das_g = self.ph5object.ph5_g_receivers.getdas_g('1X1')
        self.ph5object.ph5_g_receivers.setcurrent(das_g)
        das_rows, das_keys = experiment.read_table(
            self.ph5object.ph5_g_receivers.current_t_das)

        ordered_das_rows = sorted(
            das_rows,
            key=operator.itemgetter('channel_number_i',
                                    'time/epoch_l',
                                    'time/micro_seconds_i'))
        self.assertEqual(das_rows, ordered_das_rows)


if __name__ == "__main__":
    unittest.main()
