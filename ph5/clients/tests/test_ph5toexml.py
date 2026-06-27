'''
Tests for ph5toevt
'''
import os
import sys
import unittest
import shutil

from mock import patch
import xml.etree.ElementTree as ET

from ph5.clients import ph5toexml
from ph5.core.tests.test_base import TempDirTestCase


class TestPh5toevt_description(TempDirTestCase):
    def test_output_event_description(self):
        ph5_path = os.path.join(
            self.home, "ph5/test_data/ph5/master.ph5")
        shutil.copy(ph5_path, self.tmpdir)

        testargs = ['ph5toexml', '-n', 'master.ph5',
                    '-p', self.tmpdir, '-o', 'quake.xml']

        with patch.object(sys, 'argv', testargs):
            ph5toexml.main()

        self.assertTrue(os.path.exists('quake.xml'))
        with open('quake.xml', 'r') as quake_xml:
            quake_xml_content = quake_xml.read()
            root = ET.fromstring(quake_xml_content)
            ns = {
                'q': 'http://quakeml.org/xmlns/quakeml/1.2',
                'bed': 'http://quakeml.org/xmlns/bed/1.2'
            }
            # Find first event
            first_event = root.find('.//bed:event', ns)

            # Find description/text
            text_value = first_event.find('bed:description/bed:text', ns).text
            self.assertEqual(text_value, 'sample description')


if __name__ == "__main__":
    unittest.main()
