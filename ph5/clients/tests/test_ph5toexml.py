'''
Tests for ph5toexml
'''
import unittest
import os
import sys
import shutil

from mock import patch
from xml.etree import ElementTree as ET

from ph5.utilities import nuke_table
from ph5.clients import ph5toexml
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase, kef_to_ph5


class TestPH5toexml_ResetShotsForEachShotline(
        LogTestCase, TempDirTestCase):
    def tearDown(self):
        try:
            self.mng.ph5.close()
        except AttributeError:
            pass
        super(TestPH5toexml_ResetShotsForEachShotline, self).tearDown()

    def test_main(self):
        """
        Test if shotline won't be accumulate with loop's increasement
        """
        metapath = os.path.join(
            self.home, "ph5/test_data/metadata")
        ph5_path = os.path.join(self.home, "ph5/test_data/ph5/master.ph5")
        shutil.copy(ph5_path, '.')
        # replace event table with event_t_2shotlines.kef that have
        # shotline 001 with shot 7001 and shotline 002 with shot 7002
        test_args = ['delete_table', '-n', 'master.ph5', '--all_events']
        with patch.object(sys, 'argv', test_args):
            nuke_table.main()
        kef_to_ph5(self.tmpdir, 'master.ph5',
                   metapath, ['event_t_2shotlines.kef'])

        # run exml and check total of event tags created
        # Before fixing so that shots is reset for each shot_line,
        # there were 4 event tags.
        # After fixing, there should be 2 event tags.
        testargs = ['ph5toexml', '-n', 'master.ph5', '-p', '.',
                    '-o', 'output.xml']
        count = 0
        with patch.object(sys, 'argv', testargs):
            ph5toexml.main()
            tree = ET.parse('output.xml')
            root = tree.getroot()
            for event in root.iter():
                if event.tag.endswith("event"):
                    count += 1
        self.assertEqual(count, 2)


class TestPh5toexml_description(TempDirTestCase):
    def test_output_event_description(self):
        """
        Test if event's description i added to tag <event><description>
        """
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
