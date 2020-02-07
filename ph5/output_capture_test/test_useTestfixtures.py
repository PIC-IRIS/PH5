import unittest
from ph5.output_capture_test import outputEx
from testfixtures import OutputCapture


class TestLogEx(unittest.TestCase):

    def test_makeOutput(self):
        with OutputCapture() as output:
            outputEx.makeOutput()
        output.compare('\n'.join(["First Output",
                                  "Second Output"]))


if __name__ == "__main__":
    unittest.main()
