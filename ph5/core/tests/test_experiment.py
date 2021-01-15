'''
Tests for experiment
'''
import os
import sys
import unittest

from mock import patch

from ph5.utilities import initialize_ph5, segd2ph5
from ph5.core import ph5api, experiment
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


def create_testPH5_from_segd(segdpath):
    testargs = ['initialize_ph5', '-n', 'master.ph5']
    with patch.object(sys, 'argv', testargs):
        initialize_ph5.main()

    testargs = ['segdtoph5', '-n', 'master.ph5', '-r', segdpath]
    with patch.object(sys, 'argv', testargs):
        segd2ph5.main()


class TestExperiment_srm(TempDirTestCase, LogTestCase):
    '''
    Test sample_rate_multiplier in Experiment.ReceiversGroup.PH5.read_das
    '''
    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestExperiment_srm, self).tearDown()

    def set_current_das(self, das_sn):
        das = self.ph5_object.ph5_g_receivers.getdas_g(das_sn)
        self.ph5_object.ph5_g_receivers.setcurrent(das)

    def assert_read_das(self, ignore_srm0=False, no_srm=False):
        """
        all checks for read_das() including:
        + data has 9 rows
        + has 'sample_rate_multiplier_i' key
        + 'sample_rate_multiplier_i' value is 0 or 1

        """
        ret, keys = self.ph5_object.ph5_g_receivers.read_das(ignore_srm0)
        self.assertEqual(len(ret), 9)
        self.assertIn('sample_rate_multiplier_i', keys)
        for i in range(9):
            if ignore_srm0:
                self.assertEqual(ret[i]['sample_rate_multiplier_i'], 0)
            else:
                self.assertEqual(ret[i]['sample_rate_multiplier_i'], 1)

    def test_read_das(self):
        # test read_das with normal sample_rate_multiplier
        # => pass assert_read_das()
        segdpath = os.path.join(self.home, 'ph5/test_data/segd/1111.0.0.fcnt')
        create_testPH5_from_segd(segdpath)
        self.ph5_object = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        self.set_current_das('1X1111')
        self.assert_read_das()

    def test_read_das_srm0(self):
        # test read_das with sample_rate_multiplier_i=0
        # => raise error if ignore_srm0=False (default)
        # => pass assert_read_das() if ignore_srm0=True

        ph5path = os.path.join(self.home,
                               'ph5/test_data/ph5/sampleratemultiplier0')
        self.ph5_object = ph5api.PH5(path=ph5path, nickname='master.ph5')

        self.set_current_das('1X1111')
        with self.assertRaises(experiment.HDF5InteractionError) as context:
            self.ph5_object.ph5_g_receivers.read_das()
            self.assertEqual(context.exception.errno, 7)
            self.assertEqual(
                context.exception.msg,
                'Das_g_1X1111 has 9 sample_rate_multiplier_i(s) with values 0.'
                ' Run fix_srm to fix those values in that Das.')

        # same condition but with ignore_srm0==True, read_das return no error
        self.assert_read_das(ignore_srm0=True)

    def test_read_das_nosrm(self):
        # test read_das with the data format that has no
        # sample_rate_multiplier_i
        # => pass assert_read_das

        nosrmpath = os.path.join(self.home,
                                 'ph5/test_data/ph5_no_srm/')
        self.ph5_object = ph5api.PH5(path=nosrmpath, nickname='master.ph5')
        self.set_current_das('1X1111')
        self.assert_read_das()


if __name__ == "__main__":
    unittest.main()
