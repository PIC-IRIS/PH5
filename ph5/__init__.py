import logging
from mock import patch
from contextlib import contextmanager
from StringIO import StringIO
import sys
from ph5.utilities import tabletokef


LOGGING_FORMAT = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s"

# Setup the logger.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# Prevent propagating to higher loggers.
logger.propagate = 0
# Console log handler. By default any logs of level info and above are
# written to the console
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# Add formatter
formatter = logging.Formatter(LOGGING_FORMAT)
ch.setFormatter(formatter)
logger.addHandler(ch)


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def assertStrEqual(str1, str2):
    """
    return True if 2 strings are the same, othewise
    return the index of the first difference between 2 strings
    """
    if str1 == str2:
        return True
    else:
        for i in range(len(str1)):
            if str1[i] != str2[i]:
                errmsg = "The strings are different from %s.\n\n" % i
                if i > 0:
                    errmsg += "BEFORE the difference:\n\t'%s'\n\n" % \
                        str1[:i]
                errmsg += "Different at:\n\tstr1: '%s'\n\tstr2: '%s'\n"\
                    "AFTER:\n\tstr1: '%s'\n\tstr2: '%s'" % \
                    (str1[i], str2[i], str1[i+1:], str2[i+1:])
                raise AssertionError(errmsg)


def assertTable(options, pathtokef, pathtomaster=''):
    """
    use tabletokef to check a table (defined by options) agains a kef file
    :type options: list of strings
    :param options: the options defining the table that need to read from \
    master.ph5
    :type pathtokef: string
    :param pathtokef: path to kef file
    :type pathtomaster: string
    :param pathtomaster: path to master.ph5
    """
    testargs = ['tabletokef', '-n', 'master.ph5'] + options
    if pathtomaster != '':
        testargs += ['-p', pathtomaster]
    with patch.object(sys, 'argv', testargs):
        with captured_output() as (out, err):
            tabletokef.main()
    # in result_lines and comp_lines each element is a table
    result_lines = out.getvalue().strip().split("#   Table row ")[1:]
    with open(pathtokef) as content_file:
        comp_lines = \
            content_file.read().strip().split("#   Table row ")[1:]

    # sorted to make sure table are in order
    result_lines = sorted(result_lines)
    comp_lines = sorted(comp_lines)
    for i in range(len(result_lines)):
        if "time_stamp" in result_lines[i]:
            # lines with 'time_stamp' are at the end of each table
            # split("time_stamp")[0] to get the substring before the first
            # 'time_stamp'
            result_lines[i] = result_lines[i].split("time_stamp")[0]
            comp_lines[i] = comp_lines[i].split("time_stamp")[0]
        assertStrEqual(sorted(result_lines[i]), sorted(comp_lines[i]))
