from mock import patch
import sys
from StringIO import StringIO
from contextlib import contextmanager
from ph5.utilities import tabletokef


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


def remove_lines(mainStr, exclStrs):
    """
    remove all lines in mainStr that contain any strings in
    the list of exclStrs.
    :type mainStr: str
    :param mainStr: the string that has lines to be removed.
    :type exclStrs: list of str
    :param exclStrs: the list of strings on which the function bases to
    remove lines.
    :return the string which lines with exclStrs have been remove from.
    """
    lines = mainStr.split("\n")
    lines = [ln for ln in lines if not any(s in ln for s in exclStrs)]
    return "\n".join(lines)


def assertTable(options, pathtokef, exclStrs=[], pathtomaster=''):
    """
    use tabletokef to check a table (defined by options) agains a kef file.
    :type options: list of str
    :param options: the options defining the table that need to read from
    master.ph5.
    :type pathtokef: str
    :param pathtokef: path to kef file.
    :type exclStrs: list of str
    :para exclStrings: the strings whose lines will be exclude from the table
    before comparing the lines.
    :type pathtomaster: str
    :param pathtomaster: path to master.ph5.
    """
    exclStrs += ['time_stamp']
    testargs = ['tabletokef', '-n', 'master.ph5'] + options
    if pathtomaster != '':
        testargs += ['-p', pathtomaster]
    with patch.object(sys, 'argv', testargs):
        with captured_output() as (out, err):
            tabletokef.main()
    # in result_lines and comp_lines each element is a table
    result_rows = out.getvalue().strip().split("#   Table row ")[1:]

    with open(pathtokef) as content_file:
        comp_rows = \
            content_file.read().strip().split("#   Table row ")[1:]
    # sorted to make sure table are in order
    result_rows = sorted(result_rows)
    comp_rows = sorted(comp_rows)
    for i in range(len(result_rows)):
        result_rows[i] = remove_lines(result_rows[i].strip(), exclStrs)
        comp_rows[i] = remove_lines(comp_rows[i].strip(), exclStrs)
        assertStrEqual(result_rows[i], comp_rows[i])
