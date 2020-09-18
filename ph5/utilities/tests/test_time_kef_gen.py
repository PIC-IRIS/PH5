'''
Tests for time_kef_gen.py
'''
import unittest
import sys

from mock import patch
from testfixtures import OutputCapture

from ph5.utilities import time_kef_gen, initialize_ph5
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase
from ph5.core import timedoy, ph5api


class TestTimeKefGen(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestTimeKefGen, self).setUp()
        self.soh = {
            'SOH_a_0013':
                ['1984:001:00:42:44.00 -- REFTEK 125A V1.0.30',
                 '1984:001:00:53:39.00 -- TIME CHANGED TO   '
                 '2017:295:17:08:32:000 AND 0000/2048 MS',
                 '2017:295:17:08:32.00 -- WRITE 2 pages to disk',
                 '2017:295:17:08:43.00 -- TIME CHANGED FROM '
                 '2017:300:18:34:08:984 AND 0422/2048 MS',
                 '2017:300:18:34:8.00 -- TIME CHANGED TO   '
                 '2017:300:18:34:09:000 AND 0000/2048 MS',
                 '2017:300:18:34:9.00 -- WRITE 1 pages to disk'],
            'SOH_a_0020':
                ['2017:083:20:29:43.00 -- REFTEK 125A V1.0.30',
                 '2017:083:20:50:23.00 -- TIME CHANGED TO   '
                 '2017:083:20:50:24:000 AND 0000/2048 MS',
                 '2017:083:20:50:24.00 -- WRITE 2 pages to disk',
                 '2017:083:20:50:36.00  -- TIME CHANGED FROM '
                 '2017:085:18:12:48:000 AND 1650/2048 MS',
                 '2017:085:18:12:47.00 -- TIME CHANGED TO   '
                 '2017:085:18:12:48:000 AND 0000/2048 MS',
                 '2017:094:03:16:27.00 -- BATTERY LEVEL BEFORE RECORD 2.91'],
            'SOH_a_0034':
                ['1984:001:00:33:45.00 -- REFTEK 125A V1.0.30',
                 '1984:001:00:46:46.00 -- TIME CHANGED TO   '
                 '2017:110:17:06:41:000 AND 0000/2048 MS',
                 '2017:110:17:06:41.00 -- WRITE 2 pages to disk',
                 '2017:114:16:55:49.00 -- TIME CHANGED FROM '
                 '2017:114:16:55:49:983 AND 1762/2048 MS',
                 '2017:114:16:55:49.00 -- TIME CHANGED TO   '
                 '2017:114:16:55:50:000 AND 0000/2048 MS']}

    def test_main(self):
        testargs = ['initialize_ph5', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            initialize_ph5.main()
        ph5 = ph5api.PH5(path='.', nickname='master.ph5', editmode=True)
        ph5.ph5_g_receivers.newdas('12537')
        for name, data in self.soh.items():
            ph5.ph5_g_receivers.newarray(name, data,
                                         description="Texan State of Health")
        ph5.close()
        slope_d = ['4.93494e-09', '-4.67895e-08', '-3.61306e-08']
        offset_d = ['0.000806093', '-0.01614', '-0.015794']
        testargs = ['time_kef_gen', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                time_kef_gen.main()
                output = out.captured.strip()
        self.assertEqual(output.count('/Experiment_g/Receivers_g/Time_t'), 3)
        outputlines = output.split("\n")
        i = 0
        for line in outputlines:
            if 'das/serial_number_s' in line:
                self.assertTrue(line.split("=")[1].strip(), '12357')
            if 'slope_d' in line:
                self.assertTrue(line.split("=")[1].strip(), slope_d[i])
            if 'offset_d' in line:
                self.assertTrue(line.split("=")[1].strip(), offset_d[i])
                i += 1

    def test_process_soh(self):
        to_froms = time_kef_gen.process_soh(self.soh)
        self.assertEqual(len(to_froms), 3)
        for i, (_, val) in enumerate(self.soh.items()):
            parseSOH = time_kef_gen.parse_soh(val)
            self.assertEqual(0, timedoy.compare(to_froms[i][0][0][0],
                                                parseSOH[0][0][0]))
            self.assertEqual(to_froms[i][0][0][1], parseSOH[0][0][1])


if __name__ == "__main__":
    unittest.main()
