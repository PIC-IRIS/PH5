'''
Tests for segyfactory
'''
import unittest

from testfixtures import LogCapture

from ph5.core.tests.test_base import LogTestCase
from ph5.core.segyfactory import add_string_to_header


class TestAddStringToHeader(LogTestCase):
    def setUp(self):
        self.key = 'empty2'
        self.bit_number = 16
        self.string_name = "Array_t's description_s"

    def test_number_in_range(self):
        ext = {}
        text = '12345'
        add_string_to_header(ext, self.key, self.bit_number, text,
                             self.string_name)
        self.assertIn(self.key, ext)
        self.assertEqual(ext[self.key], int(text))

    def test_number_not_in_range(self):
        ext = {}
        text = '-1'
        with LogCapture() as log:
            add_string_to_header(ext, self.key, self.bit_number, text,
                                 self.string_name)
            self.assertEqual(
                log.records[0].msg,
                "Array_t's description_s, %s, not added to segy header: "
                "Descriptions must be numeric values in range [0,65535] to be "
                "added to header." % text)

        text = str(2 ** self.bit_number)
        with LogCapture() as log:
            add_string_to_header(ext, self.key, self.bit_number, text,
                                 self.string_name)
            self.assertEqual(
                log.records[0].msg,
                "Array_t's description_s, %s, not added to segy header: "
                "Descriptions must be numeric values in range [0,65535] to be "
                "added to header." % text)

    def test_empty_string(self):
        ext = {}
        text = ''

        with self.assertRaises(ValueError):
            add_string_to_header(
                ext, self.key, self.bit_number, text, self.string_name)

        self.assertNotIn(self.key, ext)

    def test_non_number(self):
        ext = {}
        text = 'A138'

        with self.assertRaises(ValueError):
            add_string_to_header(
                ext, self.key, self.bit_number, text, self.string_name)

        self.assertNotIn(self.key, ext)


if __name__ == "__main__":
    unittest.main()
