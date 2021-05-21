from PySide2 import QtWidgets
from ph5.core import kefx, ph5api
from ph5.utilities import tabletokef

PROG_VERSION = "2021.84"

PH5TYPE = {'_s': str, '_a': str, '_d': float, '_f': float, '_l': int,
           '_i': int}
PH5PATH = {"Experiment_t": "/Experiment_g/Experiment_t",
           "Sort_t": "/Experiment_g/Sorts_g/Sort_t",
           "Offset_t": "/Experiment_g/Sorts_g/%s",
           "All_Offset_t": "/Experiment_g/Sorts_g/%s",
           "Event_t": "/Experiment_g/Sorts_g/%s",
           "All_Event_t": "/Experiment_g/Sorts_g/%s",
           "Index_t": "/Experiment_g/Receivers_g/Index_t",
           "Map_Index_t": "/Experiment_g/Maps_g/Index_t",
           "Time_t": "/Experiment_g/Receivers_g/Time_t",
           "Array_t": "/Experiment_g/Sorts_g/%s",
           "All_Array_t": "/Experiment_g/Sorts_g/%s",
           "Response_t": "/Experiment_g/Responses_g/Response_t",
           "Report_t": "/Experiment_g/Reports_g/Report_t",
           "Receiver_t": "/Experiment_g/Receivers_g/Receiver_t",
           "Das_t": "/Experiment_g/Receivers_g/Das_g_%s/Das_t"}


class KefUtilityError(Exception):
    '''   Exception gets raised in PH5Reader   '''

    def __init__(self, message):
        super(KefUtilityError, self).__init__(message)
        self.message = message


########################################
# def Kef2TableData
# updated: 201703
# use kefx module to read the Kef file into [(path, dict of values), ...]
# to kef variable,
# then convert to
# * table data {path1:[2_way_data], ...}: each row is a data set
# * ketSets {path1:[labels], ...}: label for each column in table data
def Kef2TableData(statusbar, filename):
    try:
        kef = kefx.Kef(filename)
        kef.open()
        kef.read()
        kef.rewind()
    except Exception:
        raise

    tables = {}
    types = {}
    count = 0
    totalLines = kef.pathCount
    for path, kVal in kef:
        if path not in tables:
            tables[path] = []
            types[path] = []
        if types[path] == []:
            for label in kef.keySets[path]:
                types[path].append(PH5TYPE[label[-2:]])

        entry = []
        for label in kef.keySets[path]:
            entry.append(kVal[label])
        tables[path].append(entry)
        count += 1

        if count % 10000 == 0:
            msg = "Converting Kef to Data: %s/%s."
            statusbar.showMessage(msg % (count, totalLines))

    kef.close()
    return tables, kef.keySets, totalLines, types


########################################
# def NukeTable
# updated: 201705
# create command line using nuke-table script
# to remove the tables shown in GUI from the PH5
def NukeTable(parent, PH5file, path2file, tablepath):
    if "Experiment_t" in tablepath:
        op = '-E'
    if "Sort_t" in tablepath:
        op = '-S'
    if "Offset_t" in tablepath:
        arg = tablepath.split("/")[-1].replace('Offset_t_', '')
        op = '-O %s' % arg
    if "Event_t" in tablepath:
        arg = tablepath.split("/")[-1].replace('Event_t_', '')
        op = '-V %s' % arg
    if "Array_t" in tablepath:
        arg = tablepath.split("/")[-1].replace('Array_t_', '')
        op = '-A %s' % arg
    if "Time_t" in tablepath:
        op = '-T'
    if "Receivers_g/Index_t" in tablepath:
        op = '-I'
    if "Maps_g/Index_t" in tablepath:
        op = '-M'
    if "Receiver_t" in tablepath:
        op = '-C'
    if "Response_t" in tablepath:
        op = '-R'
    if "Report_t" in tablepath:
        op = '-P'
    if "Das_t" in tablepath:
        arg = tablepath.split("/")[-2].split("_")[-1]
        op = '-D %s' % arg

    from subprocess import Popen, PIPE, STDOUT

    cmdStr = "nuke_table -p %s -n %s %s" % (path2file, PH5file, op)
    p = Popen(cmdStr, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT,
              close_fds=True)
    output = p.stdout.read()
    print "The following command is running:\n", cmdStr
    print "Output: ", output

    if 'not found' in output.lower():
        msg = "PATH '%s' does not exist in PH5 FILE '%s'.\n\nDo you want to" \
              "insert the table into this PH5 FILE." % (tablepath, PH5file)
        result = QtWidgets.QMessageBox.question(
            parent, "Insert table?", msg,
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.No:
            QtWidgets.QMessageBox.warning(
                parent, "Warning", "Saving interupted.")
            return False
    if 'error' in output.lower():
        title = "Error in removing table %s from PH5 file" % tablepath
        result = QtWidgets.QMessageBox.warning(
            parent, title, output + "\n\nSaving interupted.")
        return False
    return True


########################################
# def PH5toTableData
# updated: 201703
# use tabletokef.readPH5 to read the PH5 file into ph5data {KEY:[keys,rows],
#  ...} or just keys, rows
# in which keys is list of labels, and rows is dict of values; KEYs are the
# array id/ eventid ...
# then convert to table data {path1:[2_way_data],...} and ketSets
# {path1:[labels], ...}
def PH5toTableData(statusbar, ph5, filename, path2file, tableType, arg=None):
    ph5data = tabletokef.readPH5(ph5, filename, path2file, tableType, arg)
    tables = {}
    keySets = {}
    types = {}
    count = 0
    TOTAL = 0
    if ph5data.__class__.__name__ == 'dict':
        for k in ph5data.keys():
            path = PH5PATH[tableType] % k
            if path not in tables:
                tables[path] = []
                keySets[path] = ph5data[k].keys
            count, totalLines, types[path] = _appendTable(tables[path],
                                                          ph5data[k], path,
                                                          statusbar, count)
            TOTAL += totalLines

    else:
        path = PH5PATH[tableType]
        if tableType == 'Array_t':
            path = path % "Array_t_{0:03d}".format(int(arg))
        tables[path] = []
        keySets[path] = ph5data.keys
        count, totalLines, types[path] = _appendTable(tables[path], ph5data,
                                                      path, statusbar, count)
        TOTAL += totalLines
    # print "types:", types
    return tables, keySets, TOTAL, types


########################################
# def _appendTable
# updated: 201703
# convert rows to 2 way data for tables of which columns in order of keys
# (rows and keys are attr. of ph5Vval)
def _appendTable(table, ph5Val, path, statusbar, count):
    totalLines = len(ph5Val.rows)
    type_ = []
    for r in ph5Val.rows:
        entry = []
        if type_ == []:
            for label in ph5Val.keys:
                type_.append(type(r[label]))
        for label in ph5Val.keys:
            entry.append(str(r[label]))
        table.append(entry)
        count += 1
        if count % 10000 == 0:
            statusbar.showMessage(
                "Converting PH5 to Data in %s: %s/%s" %
                (path, count, totalLines))
    return count, totalLines, type_


########################################
# def GetPrePH5Info
# updated: 201703
# read the given PH5 file and return ph5 available tables, arrays, events,
# shotlines, das
# for user to choose which table he want to edit
# (ph5 return to use to continue to read ph5data)
def GetPrePH5Info(filename, path2file=""):
    availTables = []
    # initialize
    ph5 = ph5api.PH5(path=path2file, nickname=filename, editmode=True)

    # event
    ph5.read_event_t_names()

    shotLines = []
    if len(ph5.Event_t_names) != 0:
        shotNames = sorted(ph5.Event_t_names)
        events = []
        for n in shotNames:
            if n == 'Event_t':
                shotLines.append('0')
            else:
                shotLines.append(n.replace('Event_t_', ''))
            ph5.read_event_t(n)
            events = events + ph5.Event_t[n]['order']
        if events != []:  # check this condition in case the read file is
            # not a master file
            availTables.append('Event_t')
            availTables.append('All_Event_t')
    # array
    ph5.read_array_t_names()
    if len(ph5.Array_t_names) != 0:
        availTables.append("Array_t")
        availTables.append("All_Array_t")
    arrays = sorted(
        [str(int(a.replace("Array_t_", ""))) for a in ph5.Array_t_names])

    # offset
    ph5.read_offset_t_names()

    if len(ph5.Offset_t_names) != 0:
        availTables.append('Offset_t')
        availTables.append('All_Offset_t')
    offsets = sorted([o.replace("Offset_t_", "") for o in ph5.Offset_t_names])

    # das
    ph5.read_das_g_names()
    if len(ph5.Das_g_names) != 0:
        availTables.append("Das_t")
    das = sorted([d.replace("Das_g_", "") for d in ph5.Das_g_names.keys()])

    # experiment
    ph5.read_experiment_t()
    if len(ph5.Experiment_t['rows']) != 0:
        availTables.append("Experiment_t")
    # receiver
    ph5.read_receiver_t()
    if len(ph5.Receiver_t['rows']) != 0:
        availTables.append('Receiver_t')
    # response
    ph5.read_response_t()
    if len(ph5.Response_t['rows']) != 0:
        availTables.append('Response_t')
    # time
    ph5.read_time_t()
    if len(ph5.Time_t['rows']) != 0:
        availTables.append('Time_t')
    # index
    ph5.read_index_t()
    if len(ph5.Index_t['rows']) != 0:
        availTables.append("Index_t")

    # map index
    rows, keys = ph5.ph5_g_maps.read_index()
    if len(rows) != 0:
        availTables.append("Map_Index_t")
    # report
    rows, keys = ph5.ph5_g_reports.read_reports()
    if len(rows) != 0:
        availTables.append("Report_t")

    # sort
    ph5.read_sort_t()
    if len(ph5.Sort_t) != 0:
        availTables.append('Sort_t')

    return ph5, sorted(availTables), arrays, shotLines, offsets, das


html_manual = '''
<html>
<head>
<style>
table, th, td {
    border: 1px solid black;
}
</style>
<title>Manual Page</title>
</head>
<body>
<h2>Manual</h2>
<hr />

<h2><a id="contents">Contents:</a></h2>
<ul>
    <li><a href="#OpenKef">Open Kef File</a></li>
    <li><a href="#OpenPH5">Open PH5 File</a></li>
    <li><a href="#OpenTableInCurr">Open table(s) in the current PH5 Fil
    </a></li>
    <li><a href="#SaveKef">Save as Kef File</a></li>
    <li><a href="#SavePH5">Save as PH5 File</a></li>
    <li><a href="#UpdatePH5">Update the current PH5 File</a></li>
    <li><a href="#SaveCSV">Save as CSV file</a></li>
    <li><a href="#EditTable">Edit Table</a></li>
    <ul>
        <li><a href="#Select">Select Cell(s)</a></li>
        <li><a href="#Change">Change value in (a) cell(s)</a></li>
        <li><a href="#EditCol">Editting the whole column</a></li>
        <li><a href="#Move">Move Selected Row(s) to a new position</a></li>
        <li><a href="#Delete">Delete Row(s) on Selected Cell(s)</a></li>
        <li><a href="#Add">Add Row(s) with Data Copy from Selected Cell(s
        </a></li>
    </ul>
</ul>

&nbsp;
<table style="width:100%">
<tbody>
<tr>
<td>
<h2><a id="OpenKef">Open Kef File</a></h2>
<div>Select Menu File - Open Kef File: to open all tables in a Kef file for
editing. Each table is placed in a tab.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>
<h2><a id="OpenPH5">Open PH5 File</a></h2>
<div>Select Menu File - Open PH5 File: to open (a) table(s) in a PH5 File for
editing. Each table is placed in a tab.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>
<h2><a id="OpenTableInCurr">Open table(s) in the current PH5 File</a></h2>
<div>Open (a) different table(s) in the currently opened PH5 File for editing.
Similar to Open a PH5 File but user doenn't need to select a file to open,
the app. doesn't need to reopen the file.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>
<h2><a id="SaveKef">Save as Kef File</a></h2>
<div>Save the opened table(s) to a Kef File.</div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>
<h2><a id="SavePH5">Save as PH5 File</a></h2>
<div>Update the a PH5 file with the opened tables OR create a new PH5 file
from the tables. </div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>
<h2><a id="UpdatePH5">Update the current PH5 File</a></h2>
<div>This option is similar to Save as PH5 File when choosing the current
opened file's name. This will run faster than saving as a different PH5 file
for it skip the step of removing table(s) and create kef file for new
table(s). </div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>
<h2><a id="SaveCSV">Save as CSV File</a></h2>
<div>Save each current tables in a CSV file with ";" deliminators. </div>
<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
<tr>
<td>
<h2><a id="EditTable">Edit Table</a></h2>

<h3><a id="Select">Select Cell(s)</a></h3>
<div>Select Type: Define which cell(s) will be selected when click on a cell.
</div>
<ul>
    <li>Single Cell: Only that cell will be selected.</li>
    <li>All Similar Cells in Station: All cells that have the same station id
    and value with the clicked cell will be selected. Avalaible only for
    Array Table.</li>
    <li>All Similar Cells in Column: All cells that have the same value and
    column with the clicked cell will be selected. (E.g. when user want to
    hange value for time, this option allow user to make sure all the necessary
     times are changed consistently.) When this option is selected, move,
     delete and add options are disabled to prevent going out of control.
</ul>

<h3><a id="Change">Change value in (a) cell(s)</a></h3>
<div>When a cell is clicked, its value will appear in the text box next to the
three Select Types so that its value can be editted.</div>
<div>User can click on button 'Change' to update the new value to the selected
cell(s). If the new value is different with the original values, the row(s) on
the selected cell(s) will change color to pink.</div>

<h3><a id="EditCol">Editting the whole column</a></h3>
<ul>
    <li>Selected Column: Show the label of the selected column.</li>
    <li>Position of Char. to change: Select the first position of character(s)
    to change.</li>
    <li>Number of Char. to change: Select the number of character(s) to change.
    </li>
    <li>X: The value to be applied in column changing.</li>
    <li>Change Char. to X: Change the selected character(s) in each item of the
     selected column to X.</li>
    <li>Plus X to Char.: Plus X to the selected character(s) in each item of
    the selected column.</li>
    <li>Change Column to X: Change each item of the selected column to X.</li>
    <li>Plus X to Column: Plus X to each item of the selected column.</li>
    <li>Reset Column: Reset each item of the selected column back to its
    original value.</li>
</ul>

<h3><a id="Move">Move Selected Row(s) to a new position</a></h3>
<div>When cell(s) are selected, the corresponding row(s) will be shown in
Selected Rows (for the ease of following up).</div>
<div>User will choose the Line No (next to 'Move Selected Row(s) under Line
No') under which the row(s) will be moved to, then click 'Move'.</div>

<h3><a id="delete">Delete Row(s) on Selected Cell(s)</a></h3>
<div>To delete Selected Row(s), just click on 'Delete Row(s) on Selected
Cell(s)', the row(s) will change color to purple to mark that the row(s) are
deleted.</div>
<div>User can change their mind by selecting the deleted row(s) again and
click on 'UnDelete'.</div>

<h3><a id="Add">Add Row(s) with Data Copy from Selected Cell(s)</a></h3>
<ul>
    <li>Copy Selected Row(s) to the Add Row View at the bottom of the GUI by
    clicking on 'Add Row(s) with Data Copy from Selected Cell(s)'</li>
    <li>Change value of (a) cell(s) in Add Row View by click on cell(s) to
    change its/their value(s) in the text box similar to 'Change value in (a)
    cell(s)' described <a href="#Change">above</a></li>
    <li>Insert Selected Rows in Add Row View to the Main View by select the the
     Line No (next to 'Insert Selected Row(s) under Line No') under which the
     row(s) will be inserted to, then click 'Insert'.</div>
</ul>

<div align="right"><a href="#contents">Contents</a></div>
<div>&nbsp;</div>
</td>
</tr>
</tbody>
</table>
</body>
</html>
'''

html_whatsnew = """
<html>
<head>
<title>What's new? Page</title>
</head>
<body>
<h2>What's new in version %s?</h2>
<hr />
<li>Menu File - Update the Current PH5 File:</li>
<ul>This option is similar to Save as PH5 File when choosing the current opened
 file's name. This will run faster than saving as a different PH5 file for it
 skip the step of removing table(s) and create kef file for new table(s).</ul>
<li>Save as CSV file:</li>
<ul>Save each current tables in a CSV file with ";" deliminators.</ul>
<li>Add table options</li>
<ul>When PH5 file is read, the following table option have been added:
All_Offset_t and All_Event_t
<li>Editting the whole column:</li>
<ul>
    <li>Selected Column: Show the label of selected column.</li>
    <li>Position of Char. to change: Select the first position of character(s)
    to change.</li>
    <li>Number of Char. to change: Select the number of character(s) to change.
    </li>
    <li>X: X: The value to be applied in column changing.</li>
    <li>Change Char. to X: Change the selected character(s) in each item of
    the selected column to X.</li>
    <li>Plus X to Char.: Plus X to the selected character(s) in each item of
    the selected column.</li>
    <li>Change Column to X: Change each item of the selected column to X.</li>
    <li>Plus X to Column: Plus X to each item of the selected column.</li>
    <li>Reset Column: Reset each item of the selected column back to its
    original value.</li>
</ul>
<li>Back to Org: Reset selected items back to their original values.</li>
</body>
</html>
"""
