"""
unit tests for ph5availability
"""

import unittest
from ph5.core import external_file, kefx
import ph5 as ph5pkg


class Test_external_file(unittest.TestCase):
    print("test external_file")

    def setUp(self):
        self.FILENAME = 'ph5/test_data/metadata/event_t.kef'

    def test_External_constructor(self):
        """
        test External's constructor
        """
        ext = external_file.External(self.FILENAME)
        self.assertEqual(ext.filename, self.FILENAME)
        self.assertIsInstance(ext.kx, kefx.Kef)
        self.assertEqual(ext.kx.filename, self.FILENAME)

        keys = ext.Event_t.keys()
        self.assertEqual(keys, ['Event_t_001'])
        del ext

        # non exist file
        self.assertRaises(kefx.KefError, external_file.External, "filename")

    def test_kef_open(self):
        """
        test kef_open method
        """
        kx = external_file.kef_open(self.FILENAME)
        self.assertIsInstance(kx, kefx.Kef)
        self.assertEqual(kx.filename, self.FILENAME)

        # non exist file
        self.assertRaises(kefx.KefError,
                          external_file.kef_open, "filename")

        # wrong format file - catch logging
        self.log_capture_string = ph5pkg.unittest_logging(ph5pkg.ch)
        external_file.kef_open("ph5/test_data/metadata/avail_time.txt")
        log_contents = self.log_capture_string.getvalue()
        self.assertIn("Unparsable line:", log_contents)


if __name__ == "__main__":
    unittest.main()
