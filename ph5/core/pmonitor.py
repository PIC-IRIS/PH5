#!/usr/bin/env pnpython3
#
# Monitor parallel entries into PH5
#
# Steve Azevedo, November 2015
#
# Monitor conversions from various 'RAW' formats to PH5
#
# Set timeout of conversion process
# Texan and SEG-D about 120 sec/GB, RT-130 500 sec/GB
# Set for RT-130


import sys
import logging
import os
import re
from threading import Thread
from Queue import Queue, Empty
from ph5.utilities import watchit
import time

PROG_VERSION = '2023.12'
LOGGER = logging.getLogger(__name__)
TIMEOUT = 500 * 4

try:
    from PySide2 import QtCore, QtWidgets
except Exception:
    msg = ("\n\nNo module named PySide2. "
           "Please environment_gui.yml to install conda environment"
           "PySide2 is needed for pmonitor.")
    raise ImportError(msg)


# RE to detect when a raw data file has finished loading
fileDoneRE = re.compile(".*:<Finished>:(.*)$")
# RE to detect start of processing a raw file
fileStartRE = re.compile(".*:<Processing>:(.*)$")
# RE for end of processing
batchDoneRE = re.compile("Done.*")
# Error
fileErrorRE = re.compile(".*:<Error>:(.*)$")
readErrorRE = re.compile(".*[Ee]rror.*")
updatingRE = re.compile(r"Updating.*\.\.\.$")
notexistRE = re.compile("File does not exist:.*")

ON_POSIX = 'posix' in sys.builtin_module_names

# Style sheets for progress bar
DEFAULT_STYLE = """
QProgressBar{
    border: 2px solid darkgreen;
    border-radius: 5px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: lightgreen;
    width: 10px;
}
"""

START_STYLE = """
QProgressBar{
    border: 2px dashed darkgreen;
    border-radius: 5px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: lightgreen;
    width: 10px;
}
"""

WRONG_STYLE = """
QProgressBar{
    border: 2px solid red;
    border-radius: 5px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: orange;
    width: 10px;
}
"""


class FamilyProgress (QtWidgets.QDialog):
    '''
          Progress Bar with button.
    '''

    def __init__(self, title, mmax=100):
        super(FamilyProgress, self).__init__()

        self.setWindowTitle(title)
        self.setFixedHeight(48)
        self.pbar = QtWidgets.QProgressBar()
        self.pbar.setRange(0, mmax - 1)

        self.btn = QtWidgets.QPushButton("Starting", self)

        pbarvbox = QtWidgets.QVBoxLayout()
        pbarvbox.addStretch(False)
        pbarvbox.addWidget(self.pbar)
        buttonvbox = QtWidgets.QVBoxLayout()
        buttonvbox.addStretch(True)
        buttonvbox.addWidget(self.btn)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addLayout(pbarvbox, stretch=False)
        hbox.addLayout(buttonvbox)

        self.setLayout(hbox)
        self.pbar.setStyleSheet(START_STYLE)

    def processingStyle(self):
        '''
        # Show that processing has started
        '''
        self.pbar.setStyleSheet(DEFAULT_STYLE)

    def undefinedError(self):
        '''
              Something is wrong so set progress bar to orange
        '''
        self.pbar.setStyleSheet(WRONG_STYLE)


class ErrorsDialog (QtWidgets.QMainWindow):
    '''
       Dialog for displaying problems with input file
    '''

    def __init__(self, errors, parent=None):
        super(ErrorsDialog, self).__init__(parent)

        errors.reverse()
        self.parent = parent
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        saveAction = QtWidgets.QAction('Save log...', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.setStatusTip('Save displayed log file.')
        saveAction.triggered.connect(self.saveFile)

        saveErrAction = QtWidgets.QAction('Save unprocessed list...', self)
        saveErrAction.setShortcut('Ctrl+U')
        saveErrAction.setStatusTip('Save a list of unprocessed raw files.')
        saveErrAction.triggered.connect(self.saveErrFile)

        closeAction = QtWidgets.QAction('Close', self)
        closeAction.setShortcut('Ctrl+Q')
        closeAction.setStatusTip('Close error display')
        closeAction.triggered.connect(self.close)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(saveAction)
        fileMenu.addAction(saveErrAction)
        fileMenu.addAction(closeAction)

        self.text = QtWidgets.QTextEdit(self)

        self.setCentralWidget(self.text)
        self.setGeometry(300, 300, 800, 300)
        self.setWindowTitle('Errors X')
        self.show()
        self.setIt(errors)
        self.whatsLeft()

    def whatsLeft(self):
        # Open current list of raw files, read through it until we find file
        # that is being processed
        self.notProcessed = []
        lstfh = open(self.parent.current_list, 'a+')
        write_it = False
        # File that is being processed at time of timeout
        try:
            base = os.path.basename(self.parent.current_file)
        except BaseException:
            base = None

        while True:
            line = lstfh.readline()
            if not line:
                break
            line = line.strip()
            if base is None:
                self.notProcessed.append(line)
                continue

            if os.path.basename(line) == base and write_it is False:
                write_it = True
                # This is the file that caused the timeout so write it to error
                # list.
                self.notProcessed.append('#' + line)
                continue
            if write_it is True:
                # Write rest of list
                self.notProcessed.append(line)

        lstfh.close()

    def setIt(self, text):
        self.text.clear()
        text = '\n'.join(text)
        self.text.setText(text)

    def saveFile(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save File', os.getenv('HOME'))
        if not filename:
            return
        f = open(filename, 'w')
        filedata = self.text.toPlainText()
        f.write(filedata)
        f.close()

    def saveErrFile(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save lst file', os.getenv('HOME'))
        if not filename:
            return
        f = open(filename, 'w')
        filedata = '\n'.join(self.notProcessed)
        f.write(filedata + '\n')
        f.close()


class Monitor (QtWidgets.QWidget):
    '''
       Monitor conversions
    '''
    # Signal to connect to progress bar setValue slot
    trddone = QtCore.Signal(int)
    # This holds the start epoch of the conversion of a raw file
    NOW = None

    def __init__(self, fio, cmds, info, title='X', mmax=100, main_window=None):
        '''
            fio -> pforma_io object
            cmds -> list of commands
            title -> window title
            mmax -> max value for progress bar
        '''
        QtWidgets.QWidget.__init__(self)
        self.fio = fio  # pforma_io instance
        self.cmds = cmds  # List of commands to monitor
        self.info = info  # Info about files to convert
        self.family = title  # Name of family A, B, C etc.
        self.cmdN = 0  # Command that is currently executing
        self.pee = None  # Process as returned by subprocess.Popen
        self.fifo = None  # STDOUT + STDERR of process (a pipe)
        self.fifoerr = None
        self.mmax = mmax
        self.main_window = main_window
        self.fp = FamilyProgress(title, mmax)  # The progress bar and friends
        box = QtWidgets.QVBoxLayout()
        box.addWidget(self.fp)
        # Set button to start conversion
        self.fp.btn.clicked.connect(self.startConversion)
        self.running = False  # Not looping on output of fifo
        self.numFiles = mmax  # Number of files to convert
        self.cnt = 0  # Number of files converted
        self.seconds = TIMEOUT  # Time out for conversion of a raw file
        self.log = []  # Running log of conversion (mostly from fifo)
        # trddone is signal to progress bar
        # self.trddone.connect (self.fp.pbar.setValue)
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("trddone(int)"),
                               self.fp.pbar,
                               QtCore.SLOT("setValue(int)"),
                               QtCore.Qt.QueuedConnection)
        # Wait for progress bar to display
        # before starting to monitor conversion
        wd = watchit.Watchdog(1, userHandler=self.startConversion)
        wd.start()
        self.setLayout(box)
        self.setWindowTitle(self.family)
        self.processedFiles = {}
        # Lists of files successfully converted keyed by DAS sn
        self.monPercent = 0.01

    def setTimeout(self, secs):
        '''Set timeout in seconds to process a single SEG-D, TRD or ZIP.'''
        self.seconds = secs

    def setundefinedError(self):
        self.fp.undefinedError()

    def timedOut(self):
        '''Go here in case of timeout.'''
        self.log.append("Conversion process timed out...")
        self.running = False

        self.endConversion()

    def startpee(self):
        '''
            Start process.
            self.pee -> The process
            self.fifo -> The fifo from the process
            self.current_list -> Current list of raw files
            self.cmdN -> The index of the command that is running
        '''
        self.pee, self.fifo = self.fio.run_simple(
            self.cmds, self.cmdN, self.family)
        if self.pee is None:
            self.running = False
        else:
            self.current_list = self.info['lists'][self.cmdN]
            self.cmdN += 1

    def startConversion(self):
        '''   Start the conversion process.   '''
        if self.running is True:
            return
        else:
            self.running = True

        self.startpee()
        # Set button to end conversion 'Kill'
        self.fp.btn.clicked.disconnect(self.startConversion)
        self.fp.btn.clicked.connect(self.endConversion)
        self.setTimeout(self.seconds)
        self.fp.btn.setText('Kill')
        # Loop On FIFO
        self.loop_on_fifo()

    def endConversion(self):
        '''   Go here to end conversion process.
              Kill button
        '''
        from signal import SIGINT
        import psutil

        self.running = False
        self.fp.btn.setText('Killing...')
        self.fp.btn.setDisabled(True)
        if self.pee is not None:
            self.log.append("Killing: {0} {1}".format(
                self.pee.pid, self.pee.args))
        try:
            # pp is the parent process (the shell)
            pp = psutil.Process(self.pee.pid)
            # ppp is all of the children processes
            ppp = pp.children(recursive=True)
            # kill all of the sub-processes
            for p in ppp:
                os.kill(p.pid, SIGINT)

            time.sleep(1)
            # Kill the shell
            self.pee.send_signal(SIGINT)
        except Exception as e:
            LOGGER.error("W {0}".format(e.message))

        if self.cnt < self.numFiles:
            self.log.append("{0} of {1} raw files processed.".format(
                self.cnt, self.numFiles))
            self.setundefinedError()

    def readlog(self):
        '''
           Show the running log of fifo
        '''
        ed = ErrorsDialog(self.log, self)
        ed.setWindowTitle("Log: {0}".format(self.family))
        ed.show()

    def clearSig(self, o):
        def print_signals_and_slots(obj):
            for i in xrange(obj.metaObject().methodCount()):
                m = obj.metaObject().method(i)
                if m.methodType() == QtCore.QMetaMethod.MethodType.Signal:
                    print "SIGNAL: sig=",
                    m.signature(),
                    "hooked to nslots=",
                    obj.receivers(
                        QtCore.SIGNAL(m.signature()))
                elif m.methodType() == QtCore.QMetaMethod.MethodType.Slot:
                    print "SLOT: sig=", m.signature()

        print_signals_and_slots(o)

    def process_line(self, line):
        '''
           Process a line from fifo
        '''
        # The list of raw files that we are trying to read does not exist
        if notexistRE.match(line):
            LOGGER.info('File not exist {0}'.format(line))

        # From the fifo it appears that the conversion process is 'Done'.
        elif batchDoneRE.match(line):
            self.trddone.emit(self.cnt)
            self.log.append("Time minutes: {0}".format(
                int((time.time() - Monitor.NOW) / 60)))
        # We finished processing a raw file according to the fifo
        # :<Finished>:
        elif fileDoneRE.match(line):
            self.log.append("Time processing {0} seconds.".format(
                int(time.time() - Monitor.NOW)))
            dtype = self.fio.file_das_type[self.current_file]['type']
            das = self.fio.file_das_type[self.current_file]['das']
            # Update the list of successfully processed file
            if dtype != 'unknown':
                if das not in self.processedFiles:
                    self.processedFiles[das] = []

                self.processedFiles[das].append(self.current_file)
            # Reset the watchdog
            if self.WD:
                self.WD.reset()
                self.WD.start()
            # Update the progressbar
            self.cnt += 1
            # self.trddone.emit (self.cnt)
            # Only update pbar 100 times (or so)
            if (self.mmax / self.cnt) >= self.monPercent:
                if self.monPercent == 0.01:
                    self.monPercent = .02
                else:
                    self.monPercent += .01
                self.trddone.emit(self.cnt)
        # :<Processing>:
        elif fileStartRE.match(line):
            #
            Monitor.NOW = time.time()
            mo = fileStartRE.match(line)
            self.current_file = mo.groups()[0].strip()
            # We really only need to do this once
            if self.monPercent == 0.01:
                self.fp.processingStyle()
        # Updating (ph5)   Do we need this
        elif updatingRE.match(line):
            pass
        # This file didn't read cleanly.
        # :<Error>:
        elif fileErrorRE.match(line):
            self.log.append(
                "Processing error at about line {0} in file list."
                .format(self.cnt + 1))

        return line.strip()

    def read_queue(self, Q):
        '''
           Read fifo queue
        '''
        try:
            ret = Q.get_nowait()
        except Empty:
            ret = None

        return ret

    def loop_on_fifo(self):
        '''   Read from fifo to process running conversion.   '''
        # There is no process (possibly these files have already been added to
        # PH5)
        if not self.pee:
            return

        # Set up read queue and watchdog timer
        Q, T, self.WD = set_up_queue(self.fifo, self.seconds, self.timedOut)

        # While the conversion is running
        self.log.append("Process started: {0}".format(self.pee.args))
        while self.running:
            line = ''
            try:
                # Try to read a line...
                line = Q.get_nowait()
                # Process the line for messages from processing program
                tmp = self.process_line(line)
                self.log.append(tmp)
            except Empty:
                # Queue is empty
                self.pee.poll()
                if self.pee.returncode is None:
                    # Process is not done
                    continue
                else:
                    # Need to check fifo
                    try:
                        line = Q.get_nowait()
                        tmp = self.process_line(line)
                        self.log.append(tmp)
                    except Exception as e:
                        LOGGER.info('X {0}'.format(e.message))
                    # The process if finished, are there more commands that
                    # need to be executed
                    self.log.append(
                        "Process finished: {0}".format(self.pee.returncode))
                    self.startpee()
                    if self.pee is not None:
                        self.log.append(
                            "Process started: {0}".format(self.pee.args))
                        Q, T, WD = set_up_queue(
                            self.fifo, self.seconds, self.timedOut)

        self.trddone.emit(self.cnt)
        if self.cnt < self.numFiles:
            self.log.append(
                "Process finished but not all files processed: {0}/{1}."
                .format(self.cnt, self.numFiles))
            self.setundefinedError()
        self.fp.btn.setDisabled(False)
        self.fp.btn.clicked.disconnect(self.endConversion)
        self.fp.btn.clicked.connect(self.readlog)
        self.fp.btn.setText('Log')
        if self.WD:
            self.WD.stop()
        self.log.append(
            "Files processed: {0}/{1}.".format(self.cnt, self.numFiles))

#
# Mix-ins
#


def enqueue_output(out, queue):
    try:
        for line in iter(out.readline, b''):
            queue.put(line)
    except Exception as e:
        LOGGER.error("Exception in read queue: {0}.\n".format(e.message))

    try:
        out.close()
    except Exception as e:
        LOGGER.error("Y {0}".format(e.message))


def set_up_queue(fifo, timeout, handler):
    '''
        Set up non-blocking read and watchdog
    '''
    # Set up non-blocking read.
    q = Queue()
    t = Thread(target=enqueue_output, args=(fifo, q))
    t.daemon = True  # thread dies with the program
    t.start()
    # Set up watchdog for each raw file conversion.
    if timeout > 0:
        wd = watchit.Watchdog(timeout, userHandler=handler)
        wd.start()
    else:
        wd = None
    return q, t, wd


if __name__ == '__main__':
    import pforma_io

    def get_len(f):
        num_lines = sum(1 for line in open(f))

        return num_lines

    def init_fio(f, d):
        from multiprocessing import cpu_count
        fio = pforma_io.FormaIO(infile=f, outdir=d)
        if cpu_count() > 3:
            fio.set_nmini(cpu_count() + 1)
        else:
            fio.set_nmini(cpu_count())

        fio.initialize_ph5()

        try:
            fio.open()
        except pforma_io.FormaIOError as e:
            LOGGER.error("{0}: {1}".format(e.errno, e.message))

        try:
            fio.read()
        except pforma_io.FormaIOError as e:
            LOGGER.error("{0}: {1}".format(e.errno, e.message))

        try:
            fio.readDB()
        except pforma_io.FormaIOError as e:
            LOGGER.error("{0}: {1}".format(e.errno, e.message))
            sys.exit(-1)

        fio.resolveDB()
        cmds, lsts, i = fio.run(runit=False)
        return fio, cmds, lsts

    f = os.path.join(os.getcwd(), sys.argv[1])
    d = os.path.join(os.getcwd(), sys.argv[2])
    fio, cmds, info = init_fio(f, d)
    fams = sorted(cmds.keys())
    application = QtWidgets.QApplication(sys.argv)
    MMM = {}
    for F in fams:
        bl = info[F]['lists']
        blah = 0
        for b in bl:
            blah += get_len(b)
        if True:
            LOGGER.info("Files in {0} {1}".format(F, blah))
            MMM[F] = Monitor(fio, cmds[F], title=F, mmax=blah)
            MMM[F].show()
    application.exec_()
