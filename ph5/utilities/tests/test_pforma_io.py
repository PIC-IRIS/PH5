'''
Tests for pforma_io
'''
import unittest
import os
import sys

from mock import patch
from testfixtures import OutputCapture

from ph5.utilities import segd2ph5, pforma_io, tabletokef
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
                    os.path.join(self.home,
                                 "ph5/test_data/segd/fairfield/3ch.fcnt")]
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
        # (not duplicated)
        self.assertEqual(ARRAY_T_A.keys(), ARRAY_T_Sigma.keys())
        array_key = ARRAY_T_A.keys()[0]
        self.assertEqual(ARRAY_T_A[array_key].rows[0],
                         ARRAY_T_Sigma[array_key].rows[0])

        self.assertEqual(INDEX_T_A.rows[0],
                         INDEX_T_Sigma.rows[0])

    def test_guess_instrument_type(self):
        # SmartSolo filename
        filename = "453005513.2.2021.05.08.20.06.00.000.E.segd"
        abs_path = os.path.join(self.home,
                                "ph5/test_data/segd/smartsolo",
                                filename)
        with OutputCapture() as out:
            ret = pforma_io.guess_instrument_type(filename, abs_path)
            output = out.captured.strip()
        self.assertEqual(ret, ('nodal', '1X1'))
        self.assertEqual(output,
                         'Reading SmartSolo header from '
                         '453005513.2.2021.05.08.20.06.00.000.E.segd... '
                         'Please wait.')
        # unsimpleton fairfield
        filename = "PIC_1_1111_4886.0.0.rg16"
        ret = pforma_io.guess_instrument_type(filename, '.')
        self.assertEqual(ret, ('nodal', '1X1111'))
        # simpleton fairfield non standard
        filename = "1111.0.0.fcnt"
        ret = pforma_io.guess_instrument_type(filename, '.')
        self.assertEqual(ret, ('unknown', None))
        filename = "1111.fcnt"
        ret = pforma_io.guess_instrument_type(filename, '.')
        self.assertEqual(ret, ('nodal', 'lllsss'))

    def test_get_smartsolo_array_station(self):
        # SmartSolo filename
        filename = "453005513.2.2021.05.08.20.06.00.000.E.segd"
        abs_path = os.path.join(self.home,
                                "ph5/test_data/segd/smartsolo",
                                filename)
        expected_station_id = '1'
        expected_array_id = '1'
        ret = pforma_io.get_smartsolo_array_station(abs_path)
        self.assertEqual(ret[0], expected_array_id)
        self.assertEqual(ret[1], expected_station_id)


class TestPformaIONotRead(LogTestCase, TempDirTestCase):
    def test_rt130(self):
        rt130_dir = os.path.join(
            self.home, "ph5/test_data/rt130/2016139.9EEF.ZIP")
        with open('rt130_list', 'w') as list_file:
            list_file.write(rt130_dir)
        list_file_path = os.path.join(self.tmpdir, 'rt130_list')
        fio = pforma_io.FormaIO(infile=list_file_path, outdir=self.tmpdir)
        fio.open()
        with self.assertRaises(pforma_io.FormaIOError) as contxt:
            fio.read()
        self.assertEqual(
            contxt.exception.message,
            '2016139.9EEF.ZIP: RT130 data detected, '
            'exit and add data to PH5 with 130toph5.'
        )

    def test_seg2(self):
        seg2_dir = os.path.join(
            self.home, "ph5/test_data/seg2/15001.dat")
        with open('seg2_list', 'w') as list_file:
            list_file.write(seg2_dir)
        list_file_path = os.path.join(self.tmpdir, 'seg2_list')
        fio = pforma_io.FormaIO(infile=list_file_path, outdir=self.tmpdir)
        fio.open()
        with self.assertRaises(pforma_io.FormaIOError) as contxt:
            fio.read()
        self.assertEqual(
            contxt.exception.message,
            '15001.dat: SEG2 data detected, '
            'exit and add data to PH5 with seg2toph5.'
        )


if __name__ == "__main__":
    unittest.main()
