import unittest
import sys
from StringIO import StringIO
from contextlib import contextmanager
from unittest_ex.output_capture_test import outputEx


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = new_out, new_err
    try:
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class TestLogEx(unittest.TestCase):

    def test_makeOutput(self):
        with captured_output() as (out, err):
            outputEx.makeOutput()
        output = out.getvalue().strip()
        self.assertEqual(output, '\n'.join(["First Output",
                                            "Second Output"]))


if __name__ == "__main__":
    unittest.main()
