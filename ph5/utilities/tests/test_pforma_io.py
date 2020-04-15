'''
Tests for pforma_io
'''
import unittest
import os
import sys

from mock import patch

from ph5.utilities import segd2ph5, pforma_io, tabletokef
from testfixtures import OutputCapture
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


class TestPforma(LogTestCase, TempDirTestCase):

    def test_unite(self):
        """
        creating element folders and A's master.ph5 to imitate the "Run"
        in pforma
        """
        # create element folders
        MINIS = ['A', 'B', 'C', 'D']
        for n in MINIS:
            os.mkdir(os.path.join(self.tmpdir, n))

        # add data to A/master.ph5
        os.chdir(os.path.join(self.tmpdir, "A"))
        testargs = ['segdtoph5', '-n', 'master.ph5', '-r',
                    os.path.join(self.home, "ph5/test_data/segd/3ch.fcnt")]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()

        # run unite that create ph5 files in Sigma/
        fio = pforma_io.FormaIO(infile="", outdir=self.tmpdir)
        # fio.initialize_ph5 creates ph5 file and doesn't leave it open
        # so doesn't need to close
        fio.initialize_ph5()
        with OutputCapture():
            fio.unite("Sigma")

        # get array_t and index_t in A/
        tabletokef.PH5 = "master.ph5"
        tabletokef.PATH = os.path.join(self.tmpdir, "A")
        tabletokef.initialize_ph5()  # need to close
        ARRAY_T_A = tabletokef.readPH5(tabletokef.EX, "", "", "All_Array_t")
        INDEX_T_A = tabletokef.readPH5(tabletokef.EX, "", "", "Index_t")

        # get array_t and index_t in Sigma/
        self.path = os.path.join(self.tmpdir, "Sigma")
        tabletokef.EX.initgroup()
        ARRAY_T_Sigma = tabletokef.readPH5(
            tabletokef.EX, "", "", "All_Array_t")
        INDEX_T_Sigma = tabletokef.readPH5(tabletokef.EX, "", "", "Index_t")
        tabletokef.EX.ph5close()

        # check array_t and index_t in Sigma/ are the same as in A/
        self.assertEqual(ARRAY_T_A.keys(), ARRAY_T_Sigma.keys())
        array_key = ARRAY_T_A.keys()[0]
        self.assertDictEqual(ARRAY_T_A[array_key].rows[0],
                             ARRAY_T_Sigma[array_key].rows[0])

        self.assertDictEqual(INDEX_T_A.rows[0],
                             INDEX_T_Sigma.rows[0])


if __name__ == "__main__":
    unittest.main()
