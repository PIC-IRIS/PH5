'''
Tests for pforma_io
'''
import unittest
import os
import shutil
import tempfile
from ph5.utilities import segd2ph5, pforma_io, tabletokef
from testfixtures import OutputCapture


class TestPforma(unittest.TestCase):
    def setUp(self):
        # create tmpdir
        self.home = os.getcwd()
        self.tmpdir = tempfile.mkdtemp() + "/"

    def tearDown(self):
        if self._resultForDoCleanups.wasSuccessful():
            try:
                shutil.rmtree(self.tmpdir)
            except Exception as e:
                print("Cannot remove %s due to the error:%s" %
                      (self.tmpdir, str(e)))
        else:
            errmsg = "%s has FAILED. Inspect files created in %s." \
                % (self._testMethodName, self.tmpdir)
            print(errmsg)
        os.chdir(self.home)

    def test_unite(self):
        """
        Test unite method.
        Place creating element folders and A's PH5 in test to imitate the "Run"
        period in pforma and will not need in other tests for pforma_io.
        """
        # create element folders
        MINIS = ['A', 'B', 'C', 'D']
        for n in MINIS:
            os.mkdir(self.tmpdir + n)
        os.chdir(self.tmpdir + "A")

        # create ph5 in A/
        segd2ph5.TSPF = False
        segd2ph5.MANUFACTURERS_CODE = segd2ph5.FAIRFIELD
        segd2ph5.NUM_MINI = None
        segd2ph5.FIRST_MINI = 1
        segd2ph5.UTM = 0
        segd2ph5.PH5 = "master.ph5"
        segd2ph5.FILES = [self.home + "/ph5/test_data/segd/3ch.fcnt"]
        segd2ph5.initializeExperiment()
        segd2ph5.process()
        segd2ph5.EX.ph5close()
        segd2ph5.EXREC.ph5close()

        # create EX for tabletokef (cannot reuse segd2ph5 because the type
        # for ph5_t_array has been changed - issue #362)
        tabletokef.PH5 = "master.ph5"
        tabletokef.PATH = self.tmpdir + "A"
        tabletokef.initialize_ph5()
        # readPH5's filename and path are not neccessary, will be removed
        # later in another PR
        ARRAY_T_A = tabletokef.readPH5(tabletokef.EX, "", "", "All_Array_t")
        INDEX_T_A = tabletokef.readPH5(tabletokef.EX, "", "", "Index_t")
        tabletokef.EX.ph5close()

        # test unite
        fio = pforma_io.FormaIO(infile="", outdir=self.tmpdir)
        fio.initialize_ph5()
        with OutputCapture():
            fio.unite("Sigma")

        # check array_t and index_t in Sigma/ are the same as in A/
        self.path = self.tmpdir + "Sigma"
        tabletokef.initialize_ph5()
        ARRAY_T_Sigma = tabletokef.readPH5(
            tabletokef.EX, "", "", "All_Array_t")
        INDEX_T_Sigma = tabletokef.readPH5(tabletokef.EX, "", "", "Index_t")

        self.assertEqual(ARRAY_T_A.keys(), ARRAY_T_Sigma.keys())
        array_key = ARRAY_T_A.keys()[0]
        self.assertDictEqual(ARRAY_T_A[array_key].rows[0],
                             ARRAY_T_Sigma[array_key].rows[0])

        self.assertDictEqual(INDEX_T_A.rows[0],
                             INDEX_T_Sigma.rows[0])

        tabletokef.EX.ph5close()


if __name__ == "__main__":
    unittest.main()
