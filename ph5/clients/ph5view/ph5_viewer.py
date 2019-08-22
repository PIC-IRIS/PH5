#!/usr/bin/env pnpython3
#
#   Plotting PH5 data
#
#   Lan Dam
#
#   Updated April 2018

import sys
import os
import time
import math
import gc
import warnings
import logging
from ph5.core import timedoy
from ph5.clients.ph5view import ph5_viewer_reader
import numpy as np
from tempfile import mkdtemp
import os.path as path
from vispy import gloo, visuals, app
import matplotlib.pyplot as plt
from copy import deepcopy

LOGGER = logging.getLogger(__name__)

try:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtCore import QPoint
    from PyQt4.QtGui import QColor
except Exception:
    msg = ("No module named PyQt4. "
           "Please install PyQt4 first, it is needed for ph5_viewer. "
           "\n\n"
           "If using Anaconda run 'conda install pyqt=4'"
           "For pip users, PyQt4 installation instructions are available at "
           "http://pyqt.sourceforge.net/Docs/PyQt4/installation.html.")
    LOGGER.error(msg)

VER = 201914
if ph5_viewer_reader.VER > VER:
    VER = ph5_viewer_reader.VER
VER_str = str(VER)
VER_str = VER_str[:4] + '.' + VER_str[4:]
PROG_VERSION = "%s Developmental" % VER_str

USERHOME = os.getenv("HOME")

# to keep PH5 values for reuse
PH5VALFILES = [path.join(mkdtemp(), 'PH5VAL%s.dat' % ch) for ch in range(3)]

# OpenGL vertex shader
# Defines how to draw and transform the graph
VERT_SHADER = """
#version 120
uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;
attribute vec2 a_position;
attribute float a_index;
varying float v_index;
attribute vec3 a_color;
varying vec3 v_color;
uniform vec2 u_pan;
uniform vec2 u_scale;
void main() {
    vec2 position_tr = u_scale * (a_position + u_pan);
    gl_Position =  u_model * vec4(position_tr, 0.0, 1.0);
    gl_PointSize = 1.5;
    v_color = a_color;
    v_index = a_index;
}
"""

# #fragment shader...just colors the graph
FRAG_SHADER = """
#version 120
varying vec3 v_color;
varying float v_index;
void main() {
    gl_FragColor = vec4(v_color, 1.0);
    if ((fract(v_index) > .00001) && (fract(v_index) < .99999))
        gl_FragColor.a = 0.;
}
"""

LSIZE = 30
totalSteps = 5
statusBar = None
statusMsg = ""
processInfo = ""
phase = ""

START = None
END = None

WARNINGMSG = """
WARNING: In some special case, the system may get crashed\n
   during the run of 'Get Data and Plot'. Please save all\n
   your works before continuing.\n
   NOTICE: Use Right Click to view Station's info\n
"""
WARNINGMSG += "*"*45


###################################
# Author: Lan
# def: showStatus():201409
# to show info on status bar
def showStatus(curMsg, nextMsg):
    global statusMsg
    statusMsg = "%s %s" % (curMsg, nextMsg)
    statusBar.showMessage(statusMsg)


###################################
# Author: Lan
# def: saveConfFile():201708
# save configuration file according to the configuration passed
def saveConfFile(conf):
    # save to conf. file
    if not os.path.exists(USERHOME + '/.PH5'):
        os.makedirs(USERHOME + '/.PH5')
    confFile = open(USERHOME + '/.PH5/PH5Viewer.cfg', 'w')

    if 'addingInfo' in conf:
        confFile.write("\naddingInfo:%s" % conf['addingInfo'])
    if 'hLabel' in conf:
        confFile.write("\nhLabel:%s" % conf['hLabel'])
    if 'vLabel' in conf:
        confFile.write("\nvLabel:%s" % conf['vLabel'])
    if 'showAbnormalStat' in conf:
        confFile.write("\nshowAbnormalStat:%s" % conf['showAbnormalStat'])
    if 'gridColor' in conf:
        confFile.write("\ngridColor:%s" % conf['gridColor'])
    if 'abnormalColor' in conf:
        confFile.write("\nabnormalColor:%s" % conf['abnormalColor'])
    if 'patternSize' in conf:
        confFile.write('\npatternSize:%s' % conf['patternSize'])
    if 'plotThick' in conf:
        confFile.write("\nplotThick:%s" % conf['plotThick'])
    if 'gridThick' in conf:
        confFile.write("\ngridThick:%s" % conf['gridThick'])

    for ch in range(len(conf['plotColor'])):
        for pc in conf['plotColor'][ch]:
            confFile.write("\nplotColor%s:%s" % (ch, pc))

    print "create PH5Viewer.cfg"
    confFile.close()


"""
___________________ CLASS _________________
Author: Lan
Updated: 201707
CLASS: ManWindow - show Manual of the app. (reuse from PH5View)
"""


class ManWindow(QtGui.QWidget):
    def __init__(self, mantype=""):
        QtGui.QWidget.__init__(self)
        self.setGeometry(100, 100, 900, 700)
        view = QtGui.QTextBrowser(self)

        if mantype == "manual":
            view.setText(ph5_viewer_reader.html_manual)

        elif mantype == "whatsnew":
            view.setText(ph5_viewer_reader.html_versionTraces)

        self.layout = QtGui.QHBoxLayout()
        self.layout.addWidget(view)

        self.setLayout(self.layout)
        self.show()


"""
____________________ CLASS _____________________
Author: Lan
Updated: 201409
CLASS: Seperator - is the line to separate in the Gui
"""


class Seperator(QtGui.QFrame):
    def __init__(self, thick=2, orientation="horizontal", length=None):
        QtGui.QFrame.__init__(self)
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.setFrameShadow(QtGui.QFrame.Sunken)
        if orientation == 'horizontal':
            self.setFixedHeight(thick)
            if length is not None:
                self.setFixedWidth(length)
        else:
            self.setFixedWidth(thick)
            if length is not None:
                self.setFixedHeight(length)


"""
_____________________ CLASS _______________________
Author: Lan
Updated: 201612
CLASS: To display long message that need scrollbar
"""


class ScrollDialog(QtGui.QDialog):
    def __init__(self, title='', header='', txt=''):
        QtGui.QDialog.__init__(self)
        self.setWindowTitle(title)
        self.resize(700, 400)
        vbox = QtGui.QVBoxLayout(self)
        # vbox.setSpacing(0)

        # for non-scrolled text
        if header != "":
            headerLbl = QtGui.QLabel('', self)
            vbox.addWidget(headerLbl)
            headerLbl.setText(header)

        # for scrolled text
        if txt != "":
            scrollArea = QtGui.QScrollArea(self)
            vbox.addWidget(scrollArea)
            scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            scrollArea.setWidgetResizable(True)

            itemsFrame = QtGui.QFrame()
            scrollArea.setWidget(itemsFrame)
            scrollBox = QtGui.QVBoxLayout()
            itemsFrame.setLayout(scrollBox)
            label = QtGui.QLabel('', self)
            scrollBox.addWidget(label)
            label.setText(txt)

        closeBtn = QtGui.QPushButton('OK', self)
        closeBtn.clicked.connect(self.onClose)
        vbox.addWidget(closeBtn)

        self.show()

    def onClose(self, evt):
        self.close()


"""
_____________________ CLASS ____________________
Author: Lan
Updated: 2016
CLASS: InfoPanel - to show info of trace(s)
"""


class InfoPanel(QtGui.QFrame):
    def __init__(self, control, txt, canvas, statId):
        QtGui.QFrame.__init__(self)
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.control = control
        self.canvas = canvas
        self.statId = statId

        control.infoBox.addWidget(self)
        self.vbox = vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(0)
        quickRemBox = QtGui.QHBoxLayout()
        vbox.addLayout(quickRemBox)
        quickRemBox.addWidget(QtGui.QLabel('QuickRemoved', self))
        self.quickRemCkbs = []
        for chIndex in range(3):
            self.quickRemCkbs.append(QtGui.QCheckBox(str(chIndex+1), self))
            self.quickRemCkbs[chIndex].stateChanged.connect(self.onQuickRemove)
            quickRemBox.addWidget(self.quickRemCkbs[chIndex])
        quickRemBox.addStretch(1)

        deepRemBox = QtGui.QHBoxLayout()
        vbox.addLayout(deepRemBox)
        deepRemBox.addWidget(QtGui.QLabel('DeepRemoved ', self))
        self.deepRemCkbs = []
        for chIndex in range(3):
            self.deepRemCkbs.append(QtGui.QCheckBox(str(chIndex+1), self))
            self.deepRemCkbs[chIndex].stateChanged.connect(self.onDeepRemove)
            deepRemBox.addWidget(self.deepRemCkbs[chIndex])
        deepRemBox.addStretch(1)

        self.infoLabel = QtGui.QLabel('', self)
        vbox.addWidget(self.infoLabel)

        control.infoBox.addWidget(self)

        self.infoLabel.setText(txt)
        self.allowRemove = False
        for chIndex in range(3):
            ch = chIndex + 1
            if ch not in self.control.channels \
                    or ch not in self.control.metadata[self.statId]['chans']:
                self.quickRemCkbs[chIndex].setEnabled(False)
                self.deepRemCkbs[chIndex].setEnabled(False)
                continue

            self.quickRemCkbs[chIndex].setEnabled(True)
            self.deepRemCkbs[chIndex].setEnabled(True)

            if self.statId in self.control.PH5Info['quickRemoved'][ch]:
                self.quickRemCkbs[chIndex].setCheckState(QtCore.Qt.Checked)
            else:
                self.quickRemCkbs[chIndex].setCheckState(QtCore.Qt.Unchecked)
            if 'Main' in self.canvas.parent.title:
                self.deepRemCkbs[chIndex].setEnabled(True)
                if self.statId in self.control.PH5Info['deepRemoved'][ch]:
                    self.deepRemCkbs[chIndex].setCheckState(QtCore.Qt.Checked)
                else:
                    self.deepRemCkbs[chIndex].setCheckState(
                        QtCore.Qt.Unchecked)
            else:
                self.deepRemCkbs[chIndex].setCheckState(QtCore.Qt.Unchecked)
                self.deepRemCkbs[chIndex].setEnabled(False)

        self.allowRemove = True
        self.show()

    ###################################
    # Author: Lan
    # def: onQuickRemove():201409
    # call quickRemove in canvas to turn the color of the trace to 'white'
    def onQuickRemove(self, evt):
        if not self.allowRemove:
            return
        chIndex = self.quickRemCkbs.index(self.sender())

        ch = chIndex + 1

        c = self.canvas.quickRemove(
            ch, self.statId, self.quickRemCkbs[chIndex].isChecked())
        self.canvas.otherCanvas.quickRemove(
            ch, self.statId, self.quickRemCkbs[chIndex].isChecked(), c)

        self.canvas.updateData()
        self.canvas.otherCanvas.updateData()

    ###################################
    # Author: Lan
    # def: onDeepRemove():201409
    # add id of the trace to PH5Info['deepRemoved']
    # all the the traces of 'deepRemoved' will
    # be removed completly from the plot
    # when click 'DeepRemove' on Plot Panel
    def onDeepRemove(self, evt):
        if not self.allowRemove:
            return

        chIndex = self.deepRemCkbs.index(self.sender())
        ch = chIndex + 1

        if self.deepRemCkbs[chIndex].isChecked() \
                and self.statId not in self.control.PH5Info['deepRemoved'][ch]:
            self.control.PH5Info['deepRemoved'][ch].append(self.statId)

        if not self.deepRemCkbs[chIndex].isChecked() \
                and self.statId in self.control.PH5Info['deepRemoved'][ch]:
            self.control.PH5Info['deepRemoved'][ch].remove(self.statId)


"""
_____________________ CLASS ____________________
Author: Lan
Updated: 201410
CLASS: Selector - showing the selected area
due to the big amount of data, Selector is not shown on the move but only
shown at the beginning (mouse press) and the end (mouse release)
"""


class Selector(QtGui.QRubberBand):
    def __init__(self, *arg, **kwargs):
        super(Selector, self).__init__(*arg, **kwargs)

    def paintEvent(self, e):
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(QtCore.Qt.red, 5))
        painter.drawRect(e.rect().x()+1, e.rect().y()+1,
                         e.rect().width()-1, e.rect().height()-1)


"""
_____________________ CLASS _____________________
Author: Lan
Updated: 201410
CLASS: SelectedStation - showing the selected station (1 to 2 stations)
"""


class SelectedStation(QtGui.QWidget):
    def __init__(self, parent, showPos=False):
        QtGui.QWidget.__init__(self, parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color:transparent;")
        self.showPos = showPos

    ###################################
    # Author: Lan
    # def: paintEvent():201409
    def paintEvent(self, e=None):
        qp = QtGui.QPainter()
        qp.begin(self)
        if self.showPos:
            # showing arrow (pointerWidget):
            # intended to use for showing the point
            # that user want to see the info
            # transparent if pre-created with no parent,
            # don't use because it show up too slow
            qp.setPen(QtGui.QPen(QtCore.Qt.red, 3))
            qp.drawLine(0, 0, 20, 20)
            qp.drawLine(0, 0, 2, 10)
            qp.drawLine(0, 0, 10, 2)
        else:
            # showing a tiny square at the select station(s)
            qp.setBrush(QtCore.Qt.red)

            # -1 or the right and bottom lines will be thinner than the rest
            qp.drawRect(0, 0, self.rect().width(), self.rect().height())
        qp.end()


"""
___________________ CLASS _________________
Author: Lan
Updated: 201410
CLASS: FileParaDialog - GUI for setting the picture file's size and format
"""


class PrintSaveParaDialog(QtGui.QDialog):
    def __init__(self, parent, typeStr, unitStr, defaultSize):
        self.parent = parent
        QtGui.QDialog.__init__(self)
        mainbox = QtGui.QVBoxLayout(self)
        (w, h) = defaultSize
        if 'save' not in typeStr:
            notice = "The selected size %s x %s\n" + \
                "Due to each printer's configuration,\n" + \
                "user may need to adjust the size of the image \n" + \
                "so that it will fit the paper."
            mainbox.addWidget(QtGui.QLabel(notice % (w, h), self))
            w, h = w-0.5, h-0.5

        formLayout = QtGui.QFormLayout()
        mainbox.addLayout(formLayout)
        self.type = typeStr

        self.widthCtrl = QtGui.QLineEdit(self)
        self.widthCtrl.setText(str(w))
        formLayout.addRow('Width (%s)' % unitStr, self.widthCtrl)

        self.heightCtrl = QtGui.QLineEdit(self)
        self.heightCtrl.setText(str(h))
        formLayout.addRow('Height (%s)' % unitStr, self.heightCtrl)

        formatDir = plt.gcf().canvas.get_supported_filetypes()
        if 'save' in typeStr:
            formats = []
            for f in formatDir.keys():
                formats.append("%s: %s" % (f, formatDir[f]))

            svgindex = formats.index("svg: %s" % formatDir['svg'])
            self.fileFormatCtrl = QtGui.QComboBox(self)
            self.fileFormatCtrl.addItems(formats)
            self.fileFormatCtrl.setCurrentIndex(svgindex)
            formLayout.addRow("File Format", self.fileFormatCtrl)

        # allow to select option of showing legend in
        # saved graphic or printed graphic
        self.legendCkbox = QtGui.QCheckBox(self)
        self.legendCkbox.setChecked(True)
        formLayout.addRow("Legend", self.legendCkbox)

        okLbl = 'Save' if 'save' in typeStr else 'Print'
        self.OKBtn = QtGui.QPushButton(okLbl, self)
        self.OKBtn.clicked.connect(self.accept)

        self.cancelBtn = QtGui.QPushButton('Cancel', self)
        self.cancelBtn.clicked.connect(self.reject)

        formLayout.addRow(self.OKBtn, self.cancelBtn)
        self.resize(250, 100)

    def getResult(self):
        if 'save' in self.type:
            try:
                w = int(self.widthCtrl.text())
                h = int(self.heightCtrl.text())
            except ValueError, e:
                print str(e)
                errorMsg = "Values entered must be integers"
                QtGui.QMessageBox.question(self, 'Error', errorMsg,
                                           QtGui.QMessageBox.Ok)
                return

            fileFormat = str(self.fileFormatCtrl.currentText()).split(":")[0]
            return w, h, self.legendCkbox.isChecked(), \
                self.type[5:], fileFormat
        else:
            try:
                w = float(self.widthCtrl.text())
                h = float(self.heightCtrl.text())
            except ValueError, e:
                print str(e)
                errorMsg = "Values entered must be floats"
                QtGui.QMessageBox.question(self, 'Error', errorMsg,
                                           QtGui.QMessageBox.Ok)
                return

            return w, h, self.legendCkbox.isChecked(), self.type[5:]

    @staticmethod
    def print_save(parent, typeStr, unitStr, defaultSize):
        """
        this method to help PrintSaveDialog return values
        """
        dialog = PrintSaveParaDialog(parent, typeStr, unitStr, defaultSize)
        result = dialog.exec_()
        if result == QtGui.QDialog.Rejected:
            return
        returnVal = dialog.getResult()

        if returnVal is None:
            returnVal = PrintSaveParaDialog.print_save(
                parent, typeStr, unitStr, defaultSize)

        return returnVal


"""
____________________ CLASS ____________________
Author: Lan
Updated: 201507
CLASS: Canvas - to show the graph
"""


class Canvas(app.Canvas):
    def __init__(self, parent, control):
        app.Canvas.__init__(self, keys='interactive')
        self.zoomWidget = Selector(QtGui.QRubberBand.Rectangle, parent)

        self.parent = parent
        self.control = control
        self.PH5View = control.PH5View
        self.orgW, self.orgH = self.size
        self.labelPos = []
        self.select = False
        self.currDir = 'up'
        self.reset()
        self.tr_sys = visuals.transforms.TransformSystem(self)
        # self.model = np.eye(4, dtype=np.float32)
        # rotate(self.model, -90, 0, 0, 1)
        # use the following line b/c the version of vispy has been changed
        self.model = \
            [[6.12323426e-17, -1.00000000e+00, 0.00000000e+00, 0.00000000e+00],
             [1.00000000e+00, 6.12323426e-17, 0.00000000e+00, 0.00000000e+00],
             [0.00000000e+00, 0.00000000e+00, 1.00000000e+00, 0.00000000e+00],
             [0.00000000e+00, 0.00000000e+00, 0.00000000e+00, 1.00000000e+00]]

        # labels' preparation: can't figure out a way to used SHADER
        # in showing text have to use visuals to show text
        # the more text is used, the slower the program is
        # => limit to show 25 texts at a time
        """
        self.text=[]
        for i in range (30):
            self.text.append(visuals.TextVisual(''))
            self.text[i].font_size = 7
            self.text[i].draw(self.tr_sys)
        """

    def setOtherCanvas(self, c):
        self.otherCanvas = c

    ###################################
    # Author: Lan
    # def: initData():201507 - updated:2016:12
    # initiate data for painting the whole data
    #  data to feed vispy drawing includes 4 parts: x, y, color, index
    #  => read each station's data: time + values, and create color + index,
    #   then feed data to self.program
    #  => if station in quickRemoved list, just turn it's color to white
    #  => if station in deepRemoved list, add no value for its drawing data
    #  because data for each station are fed separately, only use index=0
    #  note: time was build from smaller to greater,
    #   the drawing from top to bottom
    #  if want to draw time go up, program
    #   must invert the time with variable direct
    #  => build data for grid lines, then feed data to gProgram
    #  => re-position labels: resiteLabels()
    #  => update to redraw canvas
    def initData(self, t=[], val=None, deepRemoving=False):
        global START, END, processInfo, countDRAW

        start = time.time()
        direct = -1 if self.control.upRbtn.isChecked() else 1
        self.currDir = 'up' if self.control.upRbtn.isChecked() else 'down'

        colors = []
        for ch in range(len(self.control.channels)):
            if ch < len(self.control.conf['plotColor']):
                colors.append(
                    [QColor(c).getRgbF()[:3]
                     for c in self.control.conf['plotColor'][ch]])
            else:
                colors.append(
                    [QColor(c).getRgbF()[:3]
                     for c in self.control.defaultConf['plotColor'][ch]])

        if not deepRemoving:
            # for resetting pan/scale
            self.parent.canvScaleT, self.parent.canvScaleV = (1., 1.)
            self.parent.panT, self.parent.panV = (0., 0.)
            # for real scaling
            self.canvScaleT, self.canvScaleV = (1, 1)
            self.panT, self.panV = (0., 0.)
        if val is not None:
            # this operation to change the staLimitList to range (-1,1):
            #   to match with change in value
            self.control.statLimitList = \
                2 * self.control.statLimitList / self.control.maxVal - 1

        self.parent.setWindowTitle(
            'Main Window:  %s %s' %
            (self.PH5View.graphName, self.control.conf['addingInfo']))
        if val is not None and len(t) != 0:
            self.reset(needUpdate=False)
            # print "onGetnPlot(), onApplySimplify_Replot"

            if not deepRemoving:
                self.startStatId = 0
                self.endStatId = self.control.PH5Info['numOfStations'] - 1
                self.mainMinY = -1      # to define lim in self.painting
                self.mainMaxY = 1

            self.data = {}
            for ch in self.control.channels:
                self.data[ch] = []
                for i in range(len(val[ch])):
                    # org: top2bottom, choose up - bottom2top: direct=-1
                    if self.control.metadata[i] is None \
                            or not self.control.channelCkbs[ch].isChecked() \
                            or i in self.control.PH5Info['deepRemoved'][ch] \
                            or self.control.PH5Info['LEN'][ch][i] == 0:
                        self.data[ch].append(
                            np.zeros(0,
                                     dtype=[('a_position', np.float32, 2),
                                            ('a_color', np.float32, 3),
                                            ('a_index', np.float32, 1)]))
                    else:
                        aSize = len(val[ch][i])
                        self.data[ch].append(
                            np.zeros(aSize,
                                     dtype=[('a_position', np.float32, 2),
                                            ('a_color', np.float32, 3),
                                            ('a_index', np.float32, 1)]))

                        self.data[ch][i]['a_position'][:, 0] = \
                            direct*t[self.control.keepList[ch][i]]

                        # change val to range (-1,1)
                        #   - can't change in createVal()
                        #   - bc val is a list of nparray, not an nparray
                        self.data[ch][i]['a_position'][:, 1] = \
                            val[ch][i]*2./self.control.maxVal - 1
                        # an np array of all 0s for each data will be
                        # fed separately
                        self.data[ch][i]['a_index'] = np.repeat(0, aSize)

        if val is None and len(t) != 0:
            # print "onApplyVel_RePlot(), onApplyCorrVel_RePlot()"

            for ch in self.control.channels:
                for i in range(len(self.data[ch])):
                    if not self.control.channelCkbs[ch].isChecked() \
                            or i in self.control.PH5Info['deepRemoved'][ch] \
                            or self.control.PH5Info['LEN'][ch][i] == 0:
                        self.data[ch][i]['a_position'][:, 0] = np.ones(0)
                    else:
                        self.data[ch][i]['a_position'][:, 0] = \
                            direct*t[self.control.keepList[ch][i]]

        if val is not None and len(t) == 0:
            # print "onApplyOverlapNormalize_RePlot()"
            for ch in self.control.channels:
                for i in range(len(self.data[ch])):
                    if not self.control.channelCkbs[ch].isChecked() \
                            or i in self.control.PH5Info['deepRemoved'][ch] \
                            or self.control.PH5Info['LEN'][ch][i] == 0:
                        self.data[ch][i]['a_position'][:, 1] = np.ones(0)
                    else:
                        self.data[ch][i]['a_position'][:, 1] = \
                            val[ch][i]*2./self.control.maxVal - 1

        # val==None, t==None: onApplyPropperty_RePlot()

        for ch in self.control.channels:
            for i in range(len(self.data[ch])):
                # always rebuild colors in case anything change in properties.
                # This doesn't take lots of time
                aSize = len(self.data[ch][i]['a_index'])
                if i in self.control.PH5Info['quickRemoved'][ch].keys():
                    c = QColor(QtCore.Qt.white).getRgbF()[:3]
                else:
                    colorIndex = \
                        i % len(colors[self.control.channels.index(ch)])

                    c = colors[self.control.channels.index(ch)][colorIndex]

                self.data[ch][i]['a_color'] = np.tile(c, (aSize, 1))

        if 'showAbnormalStat' in self.control.conf \
                and self.control.conf['showAbnormalStat']:
            for ch in self.control.channels:
                for abn in self.control.PH5Info['abnormal']:
                    aSize = len(self.data[ch][abn]['a_index'])
                    abColor = QColor(
                        self.control.conf['abnormalColor']).getRgbF()[:3]
                    self.data[ch][abn]['a_color'] = \
                        np.tile(abColor, (aSize, 1))
        # feedData() and feedGData() separately for buildGrid()
        # require info created in feedData(): canvScaleT
        self.feedData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        self.update_scale()

        self.gtData, self.gdData, self.timeY, self.tLabels, self.dLabels = \
            self.buildGrid()
        self.feedGData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)

        self.labelPos = self.resiteLabels()

        self.enableDrawing = True
        self.update()
        self.parent.update()
        END = time.time()

        stt = 'Finish Plotting in %s seconds. Total processing time %s seconds'
        print stt % (END-start, END-START)
        processInfo += "\nPlotting: %s seconds" % (END-start)
        processInfo += "\n=> Total processing time %s seconds" % (END-START)
        processInfo += "\n" + "*"*45
        self.control.statusLbl.setText(processInfo)
        stt = 'Finish Plotting in %s seconds. Total processing time %s seconds'
        showStatus('',  stt % (END-start, END-START))
        self.defineViewWindow(0, 0, self.width, self.height)

        self.parent.distance.setText("%.3f" % (self.control.totalSize/20000.))
        self.parent.time.setText("%.3f" % (self.control.dfltTimeLen/15.))

    ###################################
    # Author: Lan
    # def: initSupportData():201507
    #  Data is passed to Support Window when onPassSelectAction()
    #  in MainWindow is called
    def initSupportData(self, mainCanvas, LT, RB):
        self.reset(needUpdate=False)
        global countDRAW
        countDRAW = 0

        start = time.time()
        # direct = -1 if self.control.upRbtn.isChecked() else 1

        self.startStatId = deepcopy(mainCanvas.startStatId)
        self.LT = LT            # Left-Top: used in trimData()
        self.RB = RB            # Right-Bottom: used in trimData()
        self.data = self.trimData(mainCanvas.data)  # create Vispy's datacd

        # calc pans, scales, limList for new data fit in the window
        self._calcPanScale(self.LT, self.RB)

        # to define lim in self.painting
        self.mainMinY, self.mainMaxY = self.getMinMaxY(self.LT, self.RB)

        # for resetting pan/scale
        self.parent.canvScaleT, self.parent.canvScaleV = \
            (self.canvScaleT, self.canvScaleV)

        # for resetting
        self.parent.panT, self.parent.panV = (self.panT, self.panV)
        self.feedData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        self.gtData, self.gdData, self.timeY, self.tLabels, self.dLabels = \
            self.buildGrid()
        self.feedGData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        self.labelPos = self.resiteLabels()

        self.enableDrawing = True
        self.update()
        self.parent.update()
        end = time.time()

        print "Finish Plotting in %s seconds" % (end-start)
        self.parent.activateWindow()
        self.defineViewWindow(0, 0, self.width, self.height)
        self.PH5View.saveSAction.setEnabled(True)
        self.PH5View.saveSZAction.setEnabled(True)
        self.PH5View.printSAction.setEnabled(True)
        self.PH5View.printSZAction.setEnabled(True)
        self.parent.setWindowTitle(
            'Support Window: %s %s' %
            (self.PH5View.graphName, self.control.conf['addingInfo']))

    ###################################
    # Author: Lan
    # def: reset():201509
    # initiate/reset info need for drawing especially for Support Window
    # when some para. are changed and then redraw in MainWindow
    def reset(self, needUpdate=True):
        self.enableDrawing = False
        if needUpdate:
            self.update()
            self.parent.update()
        self.data = None
        self.program = None
        self.gtProgram = None
        self.gdProgram = None
        self.tLabels = None
        self.needLblNo = 0

        self.LT = None
        self.RB = None
        gc.collect()

    ###################################
    # Author: Lan
    # def: feedData():201507
    # delete self.program to clear the drawing data,
    #   ignore if has no program to delete
    # create program with vertex and fragment shader
    # bind program with built data
    def feedData(self, tPan=0., vPan=0., tScale=1., vScale=1.):
        try:
            self.program.delete()
            del self.program
        except Exception:
            pass
        self.program = {}
        for ch in self.data.keys():
            self.program[ch] = []
            for i in range(len(self.data[ch])):
                self.program[ch].append(gloo.Program(VERT_SHADER, FRAG_SHADER))
                self.program[ch][i].bind(gloo.VertexBuffer(self.data[ch][i]))
                self.program[ch][i]['u_model'] = self.model

                # (y,x) b/c the model has been turned 90 degree
                self.program[ch][i]['u_pan'] = (tPan, vPan)        # time,val
                self.program[ch][i]['u_scale'] = (tScale, vScale)  # time, val

    ###################################
    # Author: Lan
    # def: feedData():201507
    # delete gProgram to clear the drawing data,
    #   ignore if has no gProgram to delete
    # create gProgram with same vertex and fragment shader with grogram
    # bind gProgram with built gData
    def feedGData(self, tPan=0., vPan=0., tScale=1., vScale=1.):

        try:
            self.gtProgramdelete()
            self.gdProgram.delete()
            del self.gtProgram
            del self.gdProgram
        except Exception:
            pass

        self.gtProgram = gloo.Program(VERT_SHADER, FRAG_SHADER)
        self.gtProgram.bind(gloo.VertexBuffer(self.gtData))
        self.gtProgram['u_model'] = self.model
        self.gtProgram['u_pan'] = (tPan, vPan)            # time,val
        self.gtProgram['u_scale'] = (tScale, vScale)      # time, val
        with warnings.catch_warnings():
            warnings.simplefilter(action='ignore', category=FutureWarning)
            if self.gdData != np.zeros(0):
                self.gdProgram = gloo.Program(VERT_SHADER, FRAG_SHADER)
                self.gdProgram.bind(gloo.VertexBuffer(self.gdData))
                self.gdProgram['u_model'] = self.model
                self.gdProgram['u_pan'] = (tPan, vPan)        # time,val
                self.gdProgram['u_scale'] = (tScale, vScale)      # time, val

    ###################################
    # Author: Lan
    # def: timeDirection():201507
    # called when changing direction ("Up"/"Down")
    # after changing the time values according to direction
    #  need to resite the time labels
    # refeed Data and gData
    # self.timePos is used only in this function
    def timeDirection(self):
        if self.data is None:
            return
        if self.control.upRbtn.isChecked():
            if self.currDir == 'up':
                f = 1
            else:
                f = -1
                self.currDir = 'up'
        else:   # down direction
            if self.currDir == 'down':
                f = 1
            else:
                f = -1
                self.currDir = 'down'

        for ch in self.control.channels:
            for i in range(len(self.data[ch])):
                t = deepcopy(self.data[ch][i]['a_position'][:, 0])
                self.data[ch][i]['a_position'][:, 0] = f*t

        direct = -1 if self.control.upRbtn.isChecked() else 1
        self.gtData['a_position'][:, 0] = np.repeat(direct * self.timeY, 2)

        self.labelPos = self.resiteLabels()
        self.feedData()
        self.feedGData()

    ###################################
    # Author: Lan
    # def: resiteLabels():201507
    # calc Pos according to time value
    # only use labels for value in view
    # set the values and positions for labels
    # set new self.needLablNo for self.drawing
    # know how many labels need to be drawn
    def resiteLabels(self, panT=None, panV=None,
                     canvScaleT=None, canvScaleV=None):
        if panT is None:
            panT = self.panT
            panV = self.panV
            canvScaleT = self.canvScaleT
            canvScaleV = self.canvScaleV

        # index = 0
        # used in painting() to know what timeY need to be kept
        # b/c timeY and fed data are all in range -1,1;
        # don't need to recalculate for painting used matplotlib
        # only labelPosY need to recalculate position
        #   for labels used vispy.visuals
        #
        # only calculate label positions based on the beginning self.orgH
        # w/ all fed data in range -1,1, scale of the drawing will
        #   affect labels' position as well
        labelPos = []
        # check to see if labels have to skip any grids
        F = 1
        numOfLabels = 30
        while True:
            numOfLabels = math.ceil(self.control.totalTime) / \
                (F*self.control.timeGridIntervalSB.value()*1000*canvScaleT)
            if numOfLabels <= 25:
                break
            F += 1

        z = self.zeroTIndex
        self.gridT = {}
        if self.control.upRbtn.isChecked():
            k = 0
            y = 1
            try:
                while y > 0:
                    y = self.height - \
                        int(0.5 * self.height *
                            ((self.timeY[z+k]-panT) * canvScaleT + 1))
                    labelPos.insert(0, {'t': self.timeY[z+k],
                                        'y': y + self.offsetY,
                                        'text': "%s" % self.tLabels[z+k]})
                    k += F
            except Exception:
                pass
            self.gridT['end'] = z + k

            k = F
            try:
                while y < self.height and z-k > 0:
                    y = self.height - \
                        int(0.5 * self.height *
                            ((self.timeY[z-k]-panT) * canvScaleT + 1))
                    labelPos.append({'t': self.timeY[z-k],
                                     'y': y + self.offsetY,
                                     'text': "%s" % self.tLabels[z-k]})
                    k += F
            except Exception:
                pass
            self.gridT['start'] = z - k
        else:
            k = 0
            y = 1
            try:
                while y > 0 and z-k > 0:
                    y = int(0.5 * self.height *
                            ((self.timeY[z-k]+panT) * canvScaleT + 1))
                    labelPos.insert(0, {'t': self.timeY[z-k],
                                        'y': y + self.offsetY,
                                        'text': "%s" % self.tLabels[z-k]})
                    k += F
            except Exception:
                pass
            self.gridT['start'] = z - k

            k = F
            try:
                while y < self.height:
                    y = int(0.5 * self.height *
                            ((self.timeY[z+k]+panT) * canvScaleT + 1))
                    labelPos.append({'t': self.timeY[z+k],
                                     'y': y + self.offsetY,
                                     'text': "%s" % self.tLabels[z+k]})
                    k += F
            except Exception:
                pass
            self.gridT['end'] = z+k

        F = 0
        numOfDLabels = 15
        while True:
            F += 1
            numOfDLabels = \
                int(self.control.totalSize /
                    (F*self.control.distanceGridIntervalSB.value()
                     * 1000 * canvScaleV))

            if numOfDLabels <= 10:
                break

        k = 0
        z = self.zeroDIndex
        x = 1
        try:
            while x > 0 and z-k > 0:
                x = int(0.5 * self.width *
                        ((self.dLabels[z-k][1]+panV) * canvScaleV+1))
                labelPos.insert(0, {'d': self.dLabels[z-k][1],
                                    'x': x + self.offsetX,
                                    'text': "%s" % self.dLabels[z-k][0]})
                k += F
        except Exception:
            pass

        k = F
        try:
            while x < self.width:
                x = int(0.5 * self.width *
                        ((self.dLabels[z+k][1]+panV) * canvScaleV+1))
                labelPos.append({'d': self.dLabels[z+k][1],
                                 'x': x + self.offsetX,
                                 'text': "%s" % self.dLabels[z+k][0]})
                k += F

        except Exception:
            pass

        return labelPos

    ###################################
    # Author: Lan
    # def: buildGrid():201507
    # calculate drawing time data and displaying time data for time grid
    # tList: drawing time data, calc from Zero out to [-1,1]
    # tLabels: displaying time data
    def buildGrid(self):
        control = self.control

        # 1s=1000ms, scaled down to the scale of time data sent to draw
        secondScaled = 1000*control.scaleT
        # number of seconds per Gap
        secondsNoPerGap = control.timeGridIntervalSB.value()

        # recalc. gap length in (-1,1)
        gridGap = secondsNoPerGap * secondScaled

        # 0 values
        tLabels = ['0']
        tList = [control.zeroT]     # (-1,1): drawing time data

        # less than 0 values
        t = control.zeroT - gridGap
        realT = -secondsNoPerGap
        i = 1
        # 0 -> -1: insert to the start of the list
        while t > -1:
            tList.insert(0, t)
            tLabels.insert(0, "%.1f" % realT)
            t -= gridGap
            realT -= secondsNoPerGap
            i += 1

        tList.insert(0, t)                     # make sure -1 is added
        tLabels.insert(0, "%.1f" % realT)
        self.zeroTIndex = i
        # greater than 0 values
        t = control.zeroT + gridGap
        realT = secondsNoPerGap

        # 0 -> 1: append to the end of the list
        while t < 1:
            tList.append(t)
            tLabels.append("%.1f" % realT)
            t += gridGap
            realT += secondsNoPerGap

        tList.append(t)
        tLabels.append("%.1f" % realT)
        # ____________________ build time grid data ____________________
        needLblNo = len(tList)                # number of grid lines needed
        direct = -1 if self.control.upRbtn.isChecked() else 1
        gtData = np.zeros(2*needLblNo,        # 2: each grid line need 2 points
                          dtype=[('a_position', np.float32, 2),
                                 ('a_color', np.float32, 3),
                                 ('a_index', np.float32, 1)])

        timeY = np.array(tList)

        # 2: each grid line need 2 points
        gtData['a_position'][:, 0] = np.repeat(direct * timeY, 2)

        # -50,50: big value to make sure the line get through the whole screen
        #           (doesn't work in painting())
        gtData['a_position'][:, 1] = np.tile([-50, 50], len(tList))
        c = [QColor(self.control.conf['gridColor']).getRgbF()[:3]]
        gtData['a_color'] = np.tile(c, (len(tList)*2, 1))

        # change color for zero line
        gtData['a_color'][self.zeroTIndex*2] = \
            QColor(QtCore.Qt.blue).getRgbF()[:3]
        gtData['a_color'][self.zeroTIndex*2+1] = \
            QColor(QtCore.Qt.blue).getRgbF()[:3]

        gtData['a_index'] = np.repeat(np.arange(0, needLblNo), 2)

        # _____________________ distance grid ____________________
        gdData = np.zeros(0)
        dLabels = []

        kilometerScaled = 1000/control.totalSize
        kilometerPerGap = control.distanceGridIntervalSB.value()
        distanceGap = kilometerPerGap * kilometerScaled * 2

        # 0 value: delta is the left side of plot => -delta is zero
        self.zeroD = zeroD = -2*self.control.scaledMinD/self.control.maxVal - 1

        dList = [zeroD]
        dLabels = [('0', zeroD)]

        # less than 0 values
        d = zeroD - distanceGap
        realD = -kilometerPerGap
        i = 1
        # 0 -> -1: insert to the start of the list
        while d > -1:
            dList.insert(0, d)
            dLabels.insert(0, ("%.1fkm" % realD, d))
            d -= distanceGap
            realD -= kilometerPerGap
            i += 1

        dList.insert(0, d)
        dLabels.insert(0, ("%.1fkm" % realD, d))
        self.zeroDIndex = i
        # greater than 0 values
        d = zeroD + distanceGap
        realD = kilometerPerGap
        i = 1
        # 0 -> 1: append to the end of the list
        while d < 1:
            dList.append(d)
            dLabels.append(("%.1fkm" % realD, d))
            d += distanceGap
            realD += kilometerPerGap

        dList.append(d)
        dLabels.append(("%.1fkm" % realD, d))

        needLblNo = len(dList)
        # _____________________ build distance grid data _________________
        gdData = np.zeros(2*needLblNo,       # 2: each grid line need 2 points
                          dtype=[('a_position', np.float32, 2),
                                 ('a_color', np.float32, 3),
                                 ('a_index', np.float32, 1)])

        # [1,0.99]
        gdData['a_position'][:, 0] = np.tile([-50, 50], len(dList))

        # 2: each grid line need 2 points
        gdData['a_position'][:, 1] = np.repeat(np.array(dList), 2)
        gdData['a_color'] = \
            np.tile(QColor(QtCore.Qt.blue).getRgbF()[:3], (len(dList)*2, 1))
        gdData['a_index'] = np.repeat(np.arange(0, needLblNo), 2)

        return gtData, gdData, timeY, tLabels, dLabels

    ###################################
    # Author: Vispy.org
    # def: on_initialize()
    def on_initialize(self, event):
        gloo.set_state(clear_color=(1, 1, 1, 1), blend=True,
                       blend_func=('src_alpha', 'one_minus_src_alpha'))

    ###################################
    # Author: Vispy.org
    # Modifier: Lan
    # def: on_resize()
    def on_resize(self, event):
        self.width, self.height = event.size
        self.offsetX = self.parent.mainFrame.x() + self.position[0]
        self.offsetY = self.parent.mainFrame.y() + self.position[1]

        gloo.set_viewport(0, 0, self.width, self.height)
        if not self.enableDrawing:
            return
        self.update_scale()

    ###################################
    # Author: Vispy.org
    # Modifier: Lan
    # def: on_draw()
    # let user choose drawing style ( program.draw(xxx) )
    # draw label for new texts and positions
    def on_draw(self, event):
        # print "ondraw"
        gloo.set_viewport(0, 0, self.width, self.height)
        gloo.clear(color=('white'))
        if self.enableDrawing:
            try:
                for ch in self.program.keys():
                    for i in range(len(self.program[ch])):
                        try:
                            if self.control.lineRbtn.isChecked():
                                self.program[ch][i].draw('line_strip')

                            else:
                                self.program[ch][i].draw('points')
                        except Exception:
                            break
                try:
                    if self.gtProgram \
                            and self.control.timeGridCkb.isChecked():
                        self.gtProgram.draw('lines')
                    if self.gdProgram \
                            and self.control.distanceGridCkb.isChecked():
                        self.gdProgram.draw('lines')
                except Exception:
                    return
            except RuntimeError, e:
                print "on_draw's error:", str(e)
                errorMsg = \
                    "Program can't draw the given data maybe because of " + \
                    "the limitation of Graphic card.\n" + \
                    "You may want to try to increase the simplify factor " + \
                    "then redraw the data.\n" + \
                    "You should also look at the terminal to see if " + \
                    "there is other reasons for this error."

                QtGui.QMessageBox.question(None, 'Error', errorMsg,
                                           QtGui.QMessageBox.Ok)
                return
            """
            # labels
            for i in range(self.needLblNo):
                self.text[i].draw(self.tr_sys)
                #print "pos:%s  => %s" % (self.text[i].pos,self.text[i].text)
            """

    ###################################
    # Author: Vispy.org
    # def: _normalize()
    def _normalize(self, x_y):
        x, y = x_y
        w, h = float(self.width), float(self.height)
        return x/(w/2.)-1., y/(h/2.)-1.

    ###################################
    # Author: Lan
    # def: defineViewWindow() 201507
    #  define the range of time and stations in the view
    #  to show info in the control panel
    def defineViewWindow(self, left, top, right, bottom, setData=True):
        k1 = self.locateDataPoint(left, top)

        if k1 is None or len(k1) < 1 or k1.__class__.__name__ != 'list':
            return False

        k2 = self.locateDataPoint(right, bottom)

        if k2 is None or len(k2) < 1 or k2.__class__.__name__ != 'list':
            return False

        if setData:
            self.displayWinValues(k1[0], k2[-1])
        return k1[0], k2[-1]

    ###################################
    # Author: Lan
    # def: displayWinValues() 201509
    # for defineViewWindow to updating info in the control panel
    def displayWinValues(self, k1, k2):
        self.control.startStationIdLbl.setText(str(k1['statId']))
        self.control.endStationIdLbl.setText(str(k2['statId']))
        self.control.startTimeLbl.setText(str(k1['dispTimeVal']))
        self.control.endTimeLbl.setText(str(k2['dispTimeVal']))

        timeLen = self.control.totalTime/(self.canvScaleT*1000)
        minInterval = math.ceil(10*timeLen/25.)/10
        maxInterval = math.ceil(10*timeLen)/10
        self.control.timeGridIntervalSB.setRange(minInterval, maxInterval)

        newD1 = (k1['sentVal'] - self.zeroD) * self.control.totalSize/2000
        newD2 = (k2['sentVal'] - self.zeroD) * self.control.totalSize/2000

        self.control.startDistanceLbl.setText(str(newD1))
        self.control.endDistanceLbl.setText(str(newD2))

    ###################################
    # Author: Lan
    # def: on_mouse_release() 201609
    # if zoompan or when there is a right-click
    #   (chance of new choosing on this window):
    #  updating info in the control panel
    # if select=True:
    #  show the window of selection
    #  update self.LT, self.RB for use in the selected option after this
    def on_mouse_release(self, event):
        if not self.enableDrawing:
            return
        if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
            return
        if event._button == 1:
            # this call is for showing info on the control panel
            self.defineViewWindow(0, 0, self.width, self.height)
        if not self.select:
            return
        if event is None:
            return
        x0, y0 = event.press_event.pos
        x1, y1 = event.last_event.pos

        self.zoomWidget.setGeometry(
            QtCore.QRect(
                QPoint(x0+self.offsetX, y0+self.offsetY),
                QPoint(x1+self.offsetX, y1+self.offsetY)).normalized())
        self.zoomWidget.show()
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0

        v = self.defineViewWindow(x0, y0, x1, y1, setData=False)
        if v:
            self.LT, self.RB = v
            # save this new values for selection to zoom
            #   or pass to support window

        else:
            self.zoomWidget.hide()

    """
    # Author: Lan
    # def: on_mouse_move() 201508
    # use to expand zoomWidget with each move
    # But need to comment out because of its poor performance
    def on_mouse_move(self, event):
        if not self.enableDrawing:
            return
        if event.is_dragging and self.select:
            x0, y0 = event.press_event.pos
            x1, y1 = event.last_event.pos
            self.zoomWidget.setGeometry(
                QtCore.QRect(
                    QPoint(x0+self.offsetX,y0+self.offsetY),
                    QPoint(x1+self.offsetX,y1+self.offsetY)).normalized())
            self.zoomWidget.show()
    """

    ###################################
    # Author: Lan
    # def: calcPanScale() 201508
    # apply new pans and scales into self.program and self.gProgram
    def applyNewPanScale(self):
        for ch in self.control.channels:
            for i in range(len(self.data[ch])):
                self.program[ch][i]['u_scale'] = \
                    (self.canvScaleT, self.canvScaleV)
                self.program[ch][i]['u_pan'] = (self.panT, self.panV)

            if self.gtProgram is not None:
                self.gtProgram['u_scale'] = (self.canvScaleT, self.canvScaleV)
                self.gtProgram['u_pan'] = (self.panT, self.panV)
            if self.gdProgram is not None:
                self.gdProgram['u_scale'] = (self.canvScaleT, self.canvScaleV)
                self.gdProgram['u_pan'] = (self.panT, self.panV)

    ###################################
    # Author: Lan
    # def: trimData() 201601
    #  cut off the stations and time outside the selection
    # + if a station in deepRemoved list, it will have no value
    # + at the 2 edges if the time values need to be added,
    #   PH5 values will use center value
    def trimData(self, D):
        LT = self.LT
        RB = self.RB
        # if indexes go in opposite of distance offset
        #   => need to switch index value
        # do it for trimData() only, if other parts have problem,
        #   will consider changing later
        if LT['index'] > RB['index']:
            LT, RB = self.RB, self.LT

        # self.startStatId: the start station Id of
        #   the beginning of this window
        # startStatId:  the start station Id of this zoomed section (LT)
        #  (may cut off one station if that part is minor)
        orgStartId = self.startStatId
        startStatId = LT['index']
        if (self.control.PH5Info['up'] and LT['sentVal'] > LT['sentCenter'])\
                or (not self.control.PH5Info['up']
                    and LT['sentVal'] < LT['sentCenter']):
            startStatId += 1

        # self.endStatId: the end station Id consider the
        #   beginning of this window
        # endStatId:  the end station Id of this zoomed section (RB)
        #  (may cut off one station if that part is minor)
        endStatId = RB['index']
        if (self.control.PH5Info['up'] and RB['sentVal'] < RB['sentCenter']) \
                or (not self.control.PH5Info['up']
                    and RB['sentVal'] > RB['sentCenter']):
            endStatId -= 1

        newData = {}
        timeTop = self.LT['sentTimeVal']
        timeBot = self.RB['sentTimeVal']
        for ch in self.control.channels:
            newData[ch] = []
            index = 0
            for i in range(startStatId, endStatId+1):
                statId = i+orgStartId
                if not self.control.channelCkbs[ch].isChecked() \
                        or statId in self.control.PH5Info['deepRemoved'][ch] \
                        or self.control.PH5Info['LEN'][ch][i] == 0:
                    newData[ch].append(np.zeros(0,
                                       dtype=[('a_position', np.float32, 2),
                                              ('a_color', np.float32, 3),
                                              ('a_index', np.float32, 1)]))
                    index += 1
                    continue

                timeVals = D[ch][i+orgStartId]['a_position'][:, 0]
                ADD = self._findTrimKeepList(i, timeVals, timeTop, timeBot)
                if not ADD:
                    return
                trimKeepList, addLT, addRB, aSize = ADD

                # try:

                newData[ch].append(np.zeros(aSize,
                                   dtype=[('a_position', np.float32, 2),
                                          ('a_color', np.float32, 3),
                                          ('a_index', np.float32, 1)]))
                if aSize > 0:
                    T = D[ch][i]['a_position'][:, 0][trimKeepList]
                    V = D[ch][i]['a_position'][:, 1][trimKeepList]
                    aColor = D[ch][i]['a_color'][0]
                    center = self.control.statLimitList[i + orgStartId].mean()

                    startT = [timeTop]
                    endT = [timeBot]
                    # use center as the value to add in
                    # choose to add at the top or end of the list
                    #   depend on the time direction
                    if self.control.upRbtn.isChecked():
                        if addLT:
                            T = np.append(T, startT)
                            V = np.append(V, center)
                        if addRB:
                            T = np.insert(T, 0, endT)
                            V = np.insert(V, 0, center)
                    else:
                        if addLT:
                            T = np.insert(T, 0, startT)
                            V = np.insert(V, 0, center)
                        if addRB:
                            T = np.append(T, endT)
                            V = np.append(V, center)

                    newData[ch][index]['a_position'][:, 0] = T
                    newData[ch][index]['a_position'][:, 1] = V
                    newData[ch][index]['a_color'] = np.tile(aColor, (aSize, 1))
                    newData[ch][index]['a_index'] = np.repeat(0, aSize)

                index += 1
                """
                except Exception, e:
                    print e
                    print "trimData:i=%s, aSize=%s, error2:%s" % (i,aSize,e)
                    break
                """
        if self.parent.title == "Main Window":
            self.control.setAllReplotBtnsEnabled(False, resetCanvas=False)

        self.startStatId = orgStartId + startStatId
        self.parent.endStatId = self.endStatId = orgStartId + endStatId
        return newData

    ###################################
    # Author: Lan
    # def: _findTrimKeepList() 201508
    #  For each station, based on the selection window,
    # look for what values needed to be kept.
    #  If the time values at the 2 edges are not in the trimKeepList,
    #  require to add the time values
    def _findTrimKeepList(self, i, timeVals, timeTop, timeBot):
        addLT = False
        addRB = False
        aSize = 0

        try:
            # the list of index inside LT and RB
            trimKeepList = np.where((timeTop <= timeVals) &
                                    (timeVals <= timeBot))[0]

            aSize = len(trimKeepList)

            if aSize > 0:
                if timeVals.min() < timeTop < timeVals.max() \
                        and timeTop not in timeVals:
                    # decide if need to add timeTob
                    aSize += 1
                    addLT = True
                if timeVals.min() < timeBot < timeVals.max() \
                        and timeBot not in timeVals:
                    # decide if need to add timeBot
                    aSize += 1
                    addRB = True

            if aSize == 0 \
                    and timeTop > timeVals.min() \
                    and timeBot < timeVals.max():
                # this may happen because of the simplification cut off
                # the data approx to avg
                aSize = 2
                addLT = True
                addRB = True

            if aSize == 0:
                pass

        except Exception, e:
            print e
            return False

        return trimKeepList, addLT, addRB, aSize

    ###################################
    # Author: Lan
    # def: onTrim4Select() 201508
    # cut off data outside the selected section
    # change pans, scale to fit the selected section into the displaying window
    def onTrim4Select(self, evt):
        if self.LT is None:
            return
        self.zoomWidget.hide()
        self.data = self.trimData(self.data)
        self._calcPanScale(self.LT, self.RB)

        # to define lim in self.painting
        self.mainMinY, self.mainMaxY = self.getMinMaxY(self.LT, self.RB)

        self.parent.canvScaleT, self.parent.canvScaleV = \
            (self.canvScaleT, self.canvScaleV)
        self.parent.panT, self.parent.panV = (self.panT, self.panV)
        self.feedData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        self.gtData, self.gdData, self.timeY, self.tLabels, self.dLabels = \
            self.buildGrid()
        self.feedGData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        self.labelPos = self.resiteLabels()
        self.update()
        self.parent.update()
        self.defineViewWindow(0, 0, self.width, self.height)
        self.control.downRbtn.setEnabled(False)
        self.control.upRbtn.setEnabled(False)

    ###################################
    # Author: Lan
    # def: getMinMaxY() 201509
    def getMinMaxY(self, LT, RB):
        direct = -1 if self.control.upRbtn.isChecked() else 1
        minY = direct * LT['sentTimeVal']
        maxY = direct * RB['sentTimeVal']
        if minY > maxY:
            minY, maxY = maxY, minY
        return minY, maxY

    ###################################
    # Author: Lan
    # def: onPassSelect() 201508
    # pass the job to supportWindow.initSupportData() which will:
    # cut off data outside the selected section
    # change pans, scale to fit the selected section
    # into the displaying window
    def onPassSelect(self, evt):
        self.zoomWidget.hide()
        self.control.supportCanvas.initSupportData(self, self.LT, self.RB)
        self.control.supportPlot.setEnabled(True)

    ###################################
    # Author: Lan
    # def: update_scale(): 201507
    #  recalc limList (limit of displaying for each station)
    def update_scale(self):
        ch0 = self.program.keys()[0]
        self.canvScaleT, self.canvScaleV = self.program[ch0][0]['u_scale']
        self.panT, self.panV = self.program[ch0][0]['u_pan']

        L1 = self.startStatId
        L2 = L1 + self.control.PH5Info['numOfStations']
        self.limList = \
            (self.canvScaleV *
             (self.control.statLimitList[L1:L2] + self.panV) + 1) * \
            self.width * 0.5

    ###################################
    # Author: Lan
    # def: calcPanScale() 201509
    # recalc. pans, scales, limList for onTrim4SelectAction()
    # or initSupportData() which is call in onPassSelectAction
    def _calcPanScale(self, LT, RB):
        self.panT = -(LT['sentTimeVal'] + RB['sentTimeVal'])/2.
        self.panV = -(LT['sentVal'] + RB['sentVal'])/2.

        self.canvScaleT = 2/abs(LT['sentTimeVal'] - RB['sentTimeVal'])
        self.canvScaleV = 2/abs(LT['sentVal'] - RB['sentVal'])

        L1 = self.startStatId
        L2 = L1 + self.control.PH5Info['numOfStations']
        self.limList = \
            (self.canvScaleV *
             (self.control.statLimitList[L1:L2] + self.panV) + 1) * \
            self.width * 0.5

    ###################################
    # Author: Lan
    # def: _zoomTo() 201511
    # change pans, scale to fit Left-Top,
    # Right-Bottom positions into the displaying window
    def _zoomTo(self, LT, RB):
        self._calcPanScale(LT, RB)
        self.applyNewPanScale()
        self.gtData, self.gdData, self.timeY, self.tLabels, self.dLabels = \
            self.buildGrid()
        self.feedGData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        self.labelPos = self.resiteLabels()
        self.update()
        self.parent.update()
        self.defineViewWindow(0, 0, self.width, self.height)
        self.control.downRbtn.setEnabled(False)
        self.control.upRbtn.setEnabled(False)

    ###################################
    # Author: Lan
    # def: onZoomSelect() 201511
    # zoom to the selected section
    def onZoomSelect(self, evt):
        if self.LT is None:
            return
        self.zoomWidget.hide()
        self._zoomTo(self.LT, self.RB)

    ###################################
    # Author: Lan
    # def: onRight() 201511
    # zoom to the new section which move to the right self.parent.distance
    def onRight(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)

        newLT = {}
        newLT['sentVal'] = LT['sentVal'] - \
            float(self.parent.distance.text())*1000*2/self.control.totalSize
        newLT['sentTimeVal'] = LT['sentTimeVal']

        newRB = {}
        newRB['sentVal'] = RB['sentVal'] - \
            float(self.parent.distance.text())*1000*2/self.control.totalSize
        newRB['sentTimeVal'] = RB['sentTimeVal']

        if newRB['sentVal'] < -1:
            msg = "Cannot Move the plot Right any more." + \
                  "\nYou may want to reduce the zoom/pan distance."
            QtGui.QMessageBox.question(self, 'Warning', msg,
                                       QtGui.QMessageBox.Ok)
            return
        self._zoomTo(newLT, newRB)

    ###################################
    # Author: Lan
    # def: onLeft() 201511
    # zoom to the new section which move to the left self.parent.distance
    def onLeft(self, evt):
        v = self.defineViewWindow(0, 0, self.width, self.height)
        if not v:
            print "onLeft error in defineViewWindow"
        else:
            LT, RB = v
        newLT = {}
        newLT['sentVal'] = LT['sentVal'] + \
            float(self.parent.distance.text())*1000*2/self.control.totalSize
        newLT['sentTimeVal'] = LT['sentTimeVal']

        newRB = {}
        newRB['sentVal'] = RB['sentVal'] + \
            float(self.parent.distance.text())*1000*2/self.control.totalSize
        newRB['sentTimeVal'] = RB['sentTimeVal']

        if newLT['sentVal'] > 1:
            msg = "Cannot Move the plot Left any more." + \
                  "\nYou may want to reduce the zoom/pan distance."
            QtGui.QMessageBox.question(self, 'Warning', msg,
                                       QtGui.QMessageBox.Ok)
            return
        self._zoomTo(newLT, newRB)

    ###################################
    # Author: Lan
    # def: onZoomOutW() 201511
    # zoom to the new section which horizontally zoom out
    # self.parent.distance each side
    def onZoomOutW(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)
        newLT = {}
        newLT['sentVal'] = LT['sentVal'] - \
            float(self.parent.distance.text())*1000*2/self.control.totalSize
        newLT['sentTimeVal'] = LT['sentTimeVal']

        newRB = {}
        newRB['sentVal'] = RB['sentVal'] + \
            float(self.parent.distance.text())*1000*2/self.control.totalSize
        newRB['sentTimeVal'] = RB['sentTimeVal']

        if newRB['sentVal']-newLT['sentVal'] > 6:
            msg = "Cannot Zoom Out in distance/value direction any more." + \
                  "\nYou may want to reduce the zoom/pan distance."
            QtGui.QMessageBox.question(self, 'Warning', msg,
                                       QtGui.QMessageBox.Ok)
            return
        self._zoomTo(newLT, newRB)

    ###################################
    # Author: Lan
    # def: onZoomInW() 201511
    # zoom to the new section which horizontally zoom in
    # self.parent.distance each side
    def onZoomInW(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)
        newLT = {}
        newLT['sentVal'] = LT['sentVal'] + \
            float(self.parent.distance.text())*1000*2/self.control.totalSize
        newLT['sentTimeVal'] = LT['sentTimeVal']

        newRB = {}
        newRB['sentVal'] = RB['sentVal'] - \
            float(self.parent.distance.text())*1000*2/self.control.totalSize
        newRB['sentTimeVal'] = RB['sentTimeVal']

        if newLT['sentVal'] > newRB['sentVal']:
            msg = "Cannot Zoom In in distance/value direction any more." + \
                  "\nYou may want to reduce the zoom/pan distance."
            QtGui.QMessageBox.question(self, 'Warning', msg,
                                       QtGui.QMessageBox.Ok)
            return
        self._zoomTo(newLT, newRB)

    ###################################
    # Author: Lan
    # def: onUp() 201511
    # zoom to the new section which move up self.parent.time
    def onUp(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)

        newLT = {}
        newLT['sentTimeVal'] = LT['sentTimeVal'] + \
            float(self.parent.time.text())*1000*self.control.scaleT
        newLT['sentVal'] = LT['sentVal']

        newRB = {}
        newRB['sentTimeVal'] = RB['sentTimeVal'] + \
            float(self.parent.time.text())*1000*self.control.scaleT
        newRB['sentVal'] = RB['sentVal']

        if newLT['sentTimeVal'] > 1:
            msg = "Cannot Move the plot Up any more.\n" + \
                "You may want to reduce the zoom/pan time."
            QtGui.QMessageBox.question(self, 'Warning', msg,
                                       QtGui.QMessageBox.Ok)
            return
        self._zoomTo(newLT, newRB)

    ###################################
    # Author: Lan
    # def: onDown() 201511
    # zoom to the new section which move down self.parent.time
    def onDown(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)

        newLT = {}
        newLT['sentTimeVal'] = LT['sentTimeVal'] - \
            float(self.parent.time.text())*1000*self.control.scaleT
        newLT['sentVal'] = LT['sentVal']

        newRB = {}
        newRB['sentTimeVal'] = RB['sentTimeVal'] - \
            float(self.parent.time.text())*1000*self.control.scaleT
        newRB['sentVal'] = RB['sentVal']

        if newRB['sentTimeVal'] < -1:
            msg = "Cannot Move the plot Down any more.\n" + \
                "You may want to reduce the zoom/pan time."
            QtGui.QMessageBox.question(self, 'Warning', msg,
                                       QtGui.QMessageBox.Ok)
            return
        self._zoomTo(newLT, newRB)

    ###################################
    # Author: Lan
    # def: onZoomInH() 201511
    # zoom to the new section which vertically zoom
    # in self.parent.time each side
    def onZoomInH(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)
        # direct = -1 if self.control.upRbtn.isChecked() else 1

        newLT = {}
        newLT['sentTimeVal'] = LT['sentTimeVal'] + \
            float(self.parent.time.text())*1000*self.control.scaleT
        newLT['sentVal'] = LT['sentVal']

        newRB = {}
        newRB['sentTimeVal'] = RB['sentTimeVal'] - \
            float(self.parent.time.text())*1000*self.control.scaleT
        newRB['sentVal'] = RB['sentVal']

        if newLT['sentTimeVal'] > newRB['sentTimeVal']:
            msg = "Cannot Zoom In in time direction any more.\n" + \
                "You may want to reduce the zoom/pan time."
            QtGui.QMessageBox.question(self, 'Warning', msg,
                                       QtGui.QMessageBox.Ok)
            return
        self._zoomTo(newLT, newRB)

    ###################################
    # Author: Lan
    # def: onZoomOutH() 201511
    # zoom to the new section which vertically
    # zoom out self.parent.time each side
    def onZoomOutH(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)
        # direct = -1 if self.control.upRbtn.isChecked() else 1

        newLT = {}
        newLT['sentTimeVal'] = LT['sentTimeVal'] - \
            float(self.parent.time.text())*1000*self.control.scaleT
        newLT['sentVal'] = LT['sentVal']

        newRB = {}
        newRB['sentTimeVal'] = RB['sentTimeVal'] + \
            float(self.parent.time.text())*1000*self.control.scaleT
        newRB['sentVal'] = RB['sentVal']

        if newRB['sentTimeVal'] - newLT['sentTimeVal'] > 6:
            msg = "Cannot Zoom Out in time direction any more.\n" + \
                "You may want to reduce the zoom/pan time."
            QtGui.QMessageBox.question(self, 'Warning', msg,
                                       QtGui.QMessageBox.Ok)
            return
        self._zoomTo(newLT, newRB)

    ###################################
    # Author: Lan
    # def: on_mouse_press(): 201507
    #  shit + right click on a station to show the info of that station
    #  self.select: show the starting point of selection section
    def on_mouse_press(self, event):
        # global pointerWidget; pointerWidget.hide()
        for i in range(3):
            self.parent.statSelectors[i].hide()

        if not self.enableDrawing:
            return
        control = self.control
        x, y = event._pos

        # pointerWidget.move(self.parent.mapToGlobal(QPoint(x, y+self.offset)))
        # pointerWidget.show()

        if event._button == 2:
            dataList = self.locateDataPoint(x, y, getInfo=True)

            # for ip in control.infoPanels: ip.hide()
            control.infoParentPanel.hide()
            while len(control.infoPanels) > 0:
                ip = control.infoPanels.pop()
                control.infoBox.removeWidget(ip)
                ip.deleteLater()

            count = 0
            for d in dataList:
                info = ""
                if count < len(self.parent.statSelectors):
                    # only show maximum 3 selected station because
                    # 1. want to preset to save time
                    # 2. too many stations will overlap each other
                    #    so user can't see all anyway
                    self.parent.statSelectors[count].setGeometry(
                        d['statXMean']-2+self.offsetX, self.offsetY, 4, 4)
                    self.parent.statSelectors[count].show()

                statData = control.metadata[d['statId']]
                info += "Sequence: " + str(d['statId'])

                if control.correctionCkb.isChecked() \
                        or control.vel is not None:
                    # print "don't need rel Time"
                    info += "\n** Time(ms): " + str(d['dispTimeVal'])

                else:
                    # print "need rel Time"
                    info += "\n** Displayed Time(ms) : " + \
                        str(d['dispTimeVal'])
                    info += "\n** Relative time(ms): " + \
                        str(d['dispTimeVal']+statData['clockDriftCorr'])

                info += "\n** PH5Value:" + str(d['PH5Val'])
                info += "\n** Min PH5Value:" + str(d['PH5Min'])
                info += "\n** Max PH5Value:" + str(d['PH5Max'])
                info += "\nAbsolute Time:" + str(statData['absStartTime'])
                info += "\nArrayId: " + str(statData['arrayId'])
                info += "\nEventId: " + str(statData['eventId'])
                info += "\nStationId: " + str(statData['stationId'])
                info += "\nDasSerial: " + str(statData['dasSerial'])

                if control.stationSpacingUnknownCkb.isChecked():
                    v = (control.nominalStaSpace.text(), 'm')
                else:
                    v = (str(control.PH5Info['distanceOffset'][d['statId']]),
                         'm')
                info += "\nDistanceOffset: %s (%s)" % v

                info += "\nClockDriftCorrection: %s (ms)" % \
                    str(statData['clockDriftCorr'])
                if not control.correctionCkb.isChecked():
                    info += "(Not apply)"

                vCorr = "N/A"
                if control.vel is not None:
                    vCorr = str(statData['redVelCorr']) + " (ms)"
                info += "\nVelocityReductionCorrection: %s" % vCorr
                info += "\nTotalCorrection: %s (ms)" % \
                    str(statData['totalCorr'])
                info += "\nLattitude: " + str(statData['lat'])
                info += "\nLongtitude: " + str(statData['long'])
                info += "\nElevation: %s (%s)" % \
                    (statData['elev'], statData['elevUnit'])

                control.infoPanels.append(
                    InfoPanel(control, info, self, d['statId']))
                if count > 2:
                    break
                count += 1

            if count > 0:
                control.infoBox.addStretch(1)
                control.infoParentPanel.show()
                control.infoParentPanel.raise_()

        elif self.select:
            self.zoomWidget.setGeometry(
                QtCore.QRect(
                    QPoint(x+self.offsetX, y+self.offsetY),
                    QPoint(x+self.offsetX+5, y+self.offsetY+5)).normalized())
            self.zoomWidget.show()

    ###################################
    # Author: Lan
    # def: locateDataPoint(): 201601
    #  calc the time, value, statId corresponding to the position
    def locateDataPoint(self, x, y, getInfo=False):
        returnVal = False
        resultList = []
        direct = -1 if self.control.upRbtn.isChecked() else 1

        # self.limList: list of postion ranges on the display for traces
        # When getInfo: more than two indeces can be listed
        # indeces list of indeces in limList where x fall into
        k = np.where((self.limList[:, 0] <= x) &
                     (self.limList[:, 1] >= x) &
                     (self.limList[:, 0] != self.limList[:, 1]))
        indeces = k[0]
        if not getInfo:
            if len(k[0]) > 0:
                indeces = indeces[:1]
            else:
                # when getting postion for selected section
                # There are 3 cases that the position not belong to any traces
                minLim = self.limList.min()
                maxLim = self.limList.max()

                if x <= minLim:
                    # 1 when x is out of the left limit, use the left limit
                    indeces = np.where(self.limList == minLim)[0]

                elif x >= maxLim:
                    # 2 when x is out of the right limit, use the right limit
                    indeces = np.where(self.limList == maxLim)[0]

                else:
                    # when x is inside limit but not in any limList,
                    # use the next greater available
                    k = np.where(self.limList[:, 0] > x)[0]
                    if self.control.PH5Info['up']:
                        indeces = [k.min()]
                    else:
                        indeces = [k.max()]

        for i in indeces:
            statId = i + self.startStatId
            if self.control.metadata[statId] is None:
                continue
            statXMean = self.limList[i].mean()

            # sentTimeVal: timeVal in range (-1,1)
            # that has been sent to canvas to draw
            sentTimeVal = ((2.*y/self.height-1)/self.canvScaleT - self.panT)

            # dispTimeVal: timeVal shown on the axisY
            # relVal: if choose not to apply any reductions on the drawing,
            #   the real timeVal on each station may be varied
            #   from the value on axisY. This relative  value is the value
            #   with all the reductions added
            dispTimeVal = (direct*sentTimeVal + 1)/self.control.scaleT + \
                self.control.minT

            """#double check
            timeIndex = int(round(dispTimeVal /
                            self.control.PH5Info['interval']))
            print "statId=%s, timeIndex:%s" %  (statId,timeIndex)
            if timeIndex in self.control.keepList[statId]:
                newValIndex = self.control.keepList[statId].index(timeIndex)
                comparePH5Val = self.control.ph5val[statId][newValIndex]
                print "compare with PH5Val:", comparePH5Val
            """
            sentMin = self.control.statLimitList[statId][0]
            sentMax = self.control.statLimitList[statId][1]

            sentCenter = (sentMin+sentMax)/2
            orgCenter = (sentCenter + 1)*self.control.maxVal/2

            valCenter = (self.control.metadata[statId]['minmax'][1] +
                         self.control.metadata[statId]['minmax'][0])/2

            orgZero = orgCenter - valCenter*self.control.scaleVList[statId]

            sentVal = (x*2./self.width - 1)/self.canvScaleV - self.panV
            """# double check
            if timeIndex in self.control.keepList[statId]:
                val = self.data[i]['a_position'][:, 1][ newValIndex]
                print "sentVal=%s compare with val=%s" % (sentVal,val)
            """
            PH5Val = ((sentVal+1)*self.control.maxVal/2 - orgZero) / \
                self.control.scaleVList[statId]

            PH5Min = ((sentMin+1)*self.control.maxVal/2 - orgZero) / \
                self.control.scaleVList[statId]
            PH5Max = ((sentMax+1)*self.control.maxVal/2 - orgZero) / \
                self.control.scaleVList[statId]
            returnVal = {'statId': statId,
                         'index': i,
                         'PH5Val': int(round(PH5Val)),
                         'dispTimeVal': dispTimeVal,
                         'sentTimeVal': sentTimeVal,
                         'sentVal': sentVal,
                         'sentCenter': sentCenter,
                         'PH5Min': PH5Min,
                         'PH5Max': PH5Max,
                         'statXMean': statXMean}

            resultList.append(returnVal)

        return resultList

    ###################################
    # Author: Lan
    # def: printing():201409
    # receive printType: printM, printMZ, printS, printSZ
    # set orientation=landscape
    # call PrintDialog: for user to choose printing options
    # run self.pr() to paint the graphic on to printer
    def printing(self,  printType):
        self.printer = QtGui.QPrinter()
        self.printer.setOrientation(QtGui.QPrinter.Landscape)
        self.printType = printType
        dialog = QtGui.QPrintDialog(self.printer, self.parent)
        dialog.open(self.pr)    # don't know why dialog.exec_()doesn't work

    ###################################
    # Author: Lan
    # def: pr():201509
    # let user adjust size of image on PrintSaveParaDialog
    # preset plt.figure (matplotlib) for the size of image
    # call self.painting() to paint the image to the figure
    # save img to "temp.png" with the printer's resolution
    # load "temp.png" on to pixmap then paint it to printer
    # remove "temp.png" when done
    def pr(self):
        global phase
        paperRect = self.printer.paperRect(QtGui.QPrinter.Inch)
        # call dialog to change the size of the image
        vals = PrintSaveParaDialog.print_save(
            self, self.printType, 'inch',
            (paperRect.width(), paperRect.height()))
        if vals is None:
            return
        w, h, legend, printType = vals[0], vals[1], vals[2], vals[3]
        start = time.time()
        phase = "Printing"
        showStatus(phase, '')
        statusBar.showMessage(statusMsg)

        # clear the old figure
        plt.clf()
        fig = plt.figure(1, dpi=100)
        # set new w, h for new image
        # set forward=True or it always keep w, h of the first setting
        fig.set_size_inches(w, h, forward=True)
        # set tight layout to save space for image
        fig.set_tight_layout(True)
        # plot data
        self.painting(printType, legend)
        fname = 'temp.png'
        # get printer's resolution for saving the figure
        resolution = self.printer.resolution()
        # save figure into fname file
        plt.savefig(fname, dpi=resolution)
        # create QPixmap from image file
        pixmap = QtGui.QPixmap("temp.png")
        # use QPainter to send pixmap to printer
        qp = QtGui.QPainter()
        qp.begin(self.printer)    # device to display the image
        qp.drawPixmap(0, 0, pixmap)
        qp.end()

        end = time.time()
        showStatus("", "Done Printing in %s seconds" % (end-start))
        # delete the file test.png that has been used as the media
        # to send image from plt to printer
        try:
            os.remove('temp.png')
        except Exception:
            pass

    ###################################
    # Author: Lan
    # def: save2file():201509
    # receive saveType: save_M, save_MZ, save_S, save_SZ
    # let user adjust size of image and file format by
    #   calling PrintSaveParaDialog
    # call QFileDiaglog for user to choose a name for image file
    # preset plt.figure (matplotlib) for the size of image
    # call self.painting() to paint the image to the figure
    # save the img to the fileName that has been selected by user
    def save2file(self, saveType):
        w = self.width
        h = self.height
        if w == 0:
            w = 700
            h = 500
        # call dialog to change the size of the image
        vals = PrintSaveParaDialog.print_save(self, saveType, 'pixels', (w, h))
        if vals is None:
            return
        w, h, legend, saveType, fileformat = \
            vals[0], vals[1], vals[2], vals[3], vals[4]

        # QFileDialog to set the name of the new image file
        dialog = QtGui.QFileDialog(self.parent)
        dialog.setFileMode(QtGui.QFileDialog.AnyFile)
        fname = dialog.getSaveFileName(self.parent, 'Save As', '',
                                       '*.%s' % fileformat)
        if fname == '':
            return

        if "." + fileformat not in fname:
            fname = fname + "." + fileformat
        print "Image will be saved to:", fname

        showStatus("Preparing", "")
        start = time.time()

        # clear the old figure
        plt.clf()
        fig = plt.figure(1, dpi=100)

        fig.set_size_inches(w/100, h/100, forward=True)
        # set tight layout to save space for image
        fig.set_tight_layout(True)
        # plot data
        self.painting(saveType, legend)

        # remove the old five before saving the new one
        try:
            os.remove(fname)
        except Exception:
            pass
        # save figure with dpi=100.
        # The dpi and w, h has been tried to get the right size for the file
        if fileformat == 'svg':
            plt.savefig(str(fname))
        else:
            plt.savefig(str(fname), dpi=1000)

        end = time.time()

        showStatus("", "Done Saving in %s seconds" % (end-start))

    ###################################
    # Author: Lan
    # def: painting():201509
    # plot data using matplotlib package
    # all data just need to be the same scale (using the sentXXX),
    #   1. plot data
    #   2. plot gridlines
    #   3. plot H/V labels + title   4. plot axis labels
    # to paint the zoomview:
    #  + limit stations
    #  + draw the whole data of the station in that window
    #    (data after trimming)
    #  + use ax.set_ylim to limit
    def painting(self, psType, legend):
        conf = self.control.conf

        # direct = -1 if self.control.upRbtn.isChecked() else 1

        labelPos = self.labelPos

        if 'Z' in psType:   # paint the zoomed view
            v = self.defineViewWindow(0, 0, self.width, self.height)
            if v is not False:
                LT, RB = v
            minY, maxY = self.getMinMaxY(LT, RB)

            startId = LT['index']
            if LT['sentVal'] > LT['sentCenter']:
                startId += 1

            endId = RB['index']
            if RB['sentVal'] < RB['sentCenter']:
                endId -= 1

            timeY = self.timeY[self.gridT['start']:self.gridT['end']]

        else:               # paint the starting view ( after trimming)
            startId = 0
            for ch in self.data.keys():
                endId = len(self.data[ch]) - 1
                break

            # if this has been zoom from the starting scale
            # => need to rebuild grid
            if self.canvScaleT != self.parent.canvScaleT:
                timeY = self.timeY
                p = self.parent

                # self.labelPos has been limitted, need to recreate
                labelPos = self.resiteLabels(
                    p.panT, p.panV, p.canvScaleT, p.canvScaleV)
            else:
                timeY = self.timeY[self.gridT['start']:self.gridT['end']]

            minY = self.mainMinY
            maxY = self.mainMaxY

        minXList = []
        maxXList = []

        thick = conf['plotThick'] if 'plotThick' in conf else .5
        chLbls = []

        # plot stations one by one
        for ch in self.control.channels:
            if not self.control.channelCkbs[ch].isChecked():
                continue
            minXList.append(self.data[ch][startId]['a_position'][:, 1].min())
            maxXList.append(self.data[ch][endId]['a_position'][:, 1].max())

            for i in range(startId, endId+1):
                if i % 10 == 0:
                    showStatus("Plotting: ", "%s/%s" % (i, endId-startId+1))

                statId = i + self.startStatId

                if self.control.metadata[i] is None \
                        or statId in self.control.PH5Info['deepRemoved'][ch] \
                        or self.control.PH5Info['LEN'][ch][i] == 0:
                    continue

                p, = plt.plot(
                    self.data[ch][i]['a_position'][:, 1],
                    self.data[ch][i]['a_position'][:, 0],
                    c=self.data[ch][i]['a_color'][0], linewidth=thick)
                if ch not in chLbls:
                    chLbls.append(ch)
                    p.set_label("channel %s" % ch)

        minX = min(minXList)
        maxX = max(maxXList)

        showStatus("Gridding", "")

        thick = conf['gridThick'] if 'gridThick' in conf else 1

        if self.gtProgram and self.control.timeGridCkb.isChecked():
            for i in range(len(timeY)):
                plt.plot([minX, maxX],
                         [timeY[i], timeY[i]], '--',
                         c=QColor(conf['gridColor']).getRgbF()[:3],
                         linewidth=thick)

        plt.axis((minX, maxX, maxY, minY))

        graphName = self.PH5View.graphName
        if 'addingInfo' in conf:
            graphName += conf['addingInfo']
        fSize = conf['titleFSize'] if 'titleFSize' in conf else 12
        plt.title(graphName, fontsize=fSize)

        if 'hLabel' in conf:
            fSize = conf['hLabelFSize'] if 'hLabelFSize' in conf else 9
            # labelpad=: distance from xtick
            plt.xlabel(conf['hLabel'], fontsize=fSize)
        if 'vLabel' in conf:
            fSize = conf['vLabelFSize'] if 'vLabelFSize' in conf else 9
            plt.ylabel(conf['vLabel'], fontsize=fSize)
        x = []
        xLabel = []
        y = []
        yLabel = []
        for lbl in labelPos:
            if 't' in lbl:
                if minY <= lbl['t'] <= maxY:
                    y.append(lbl['t'])
                    yLabel.append(lbl['text'])

            else:
                if minX <= lbl['d'] <= maxX:
                    x.append(lbl['d'])
                    xLabel.append(lbl['text'])

        plt.tick_params(axis='both', which='major', labelsize=9)
        plt.xticks(x, xLabel)
        if self.control.upRbtn.isChecked():
            yLabel = yLabel[::-1]
        plt.yticks(y, yLabel)
        if legend:
            # http://matplotlib.org/api/pyplot_api.html: loc=2 => 'upper left'
            # with bbox_to_anchor=(xleft, ytop, xright, ybottom)
            # http://stackoverflow.com/questions/7125009
            # /how-to-change-legend-size-with-matplotlib-pyplot: prop
            plt.legend(bbox_to_anchor=(-.05, -.127, .2, .102), loc=2,
                       ncol=3, borderaxespad=0, prop={'size': 9})

    ###################################
    # Author: Lan
    # def: quickRemove():201511
    # to remove station:
    #   => add item to quickRemove list with key is station Id,
    #      value is color of the station
    #   => change color of station to white
    # to undo remove station:
    #   => change color of station back to the color saved in quickRemoved List
    #   => delete item corresponding to this station in quickRemoved list
    #   => b/c there are 2 canvas, item might already
    #      be deleted from quickRemoved List
    def quickRemove(self, ch, statId, removedStatus, c=0):
        if not self.enableDrawing:
            return 1

        canvId = statId - self.startStatId

        if canvId < 0 or canvId >= len(self.data[ch]):
            return 2
        aSize = len(self.data[ch][canvId]['a_index'])
        if removedStatus:
            self.control.PH5Info['quickRemoved'][ch][statId] = \
                deepcopy(self.data[ch][canvId]['a_color'][0])
            c = QColor(QtCore.Qt.white).getRgbF()[:3]
            self.data[ch][canvId]['a_color'] = np.tile(c, (aSize, 1))

        else:
            try:
                if c.__class__.__name__ == 'ndarray':
                    c = c
                else:
                    c = deepcopy(
                        self.control.PH5Info['quickRemoved'][ch][statId])

                self.data[ch][canvId]['a_color'] = np.tile(c, (aSize, 1))
                if statId in self.control.PH5Info['quickRemoved'][ch].keys():
                    del self.control.PH5Info['quickRemoved'][ch][statId]
                    return c

            except KeyError:
                return 3
        return 0

    def updateData(self):
        if not self.enableDrawing:
            return
        self.feedData(self.panT, self.panV,
                      self.canvScaleT, self.canvScaleV)
        self.update()
        self.parent.update()


"""
______________________ CLASS ___________________
Author: Lan
Updated: 201410
CLASS: PlottingPanel
   To keep the canvas.
   have the toolbar for zoom/pan, select
"""


class PlottingPanel(QtGui.QMainWindow):
    def __init__(self, control, title, x, y, w, h, isMainPlot=True):
        self.isMainPlot = isMainPlot
        self.parent = control
        QtGui.QMainWindow.__init__(self)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.title = title
        self.EXPL = EXPL = {}
        self.helpEnable = False
        self.setWindowTitle(title)
        self.canvScaleT, self.canvScaleV = (None, None)
        self.panT, self.panV = (None, None)
        # not allow to close Support Window
        if not isMainPlot:
            self.setWindowFlags(QtCore.Qt.Window |
                                QtCore.Qt.WindowMinMaxButtonsHint)
        self.canvas = Canvas(self, control)

        self.mainFrame = mainFrame = QtGui.QFrame(self)
        self.setCentralWidget(mainFrame)
        mainHBox = QtGui.QHBoxLayout()
        mainFrame.setLayout(mainHBox)
        mainHBox.setSpacing(0)
        lbl1 = QtGui.QLabel("", self)   # to keep horizontal space
        mainHBox.addWidget(lbl1)
        lbl1.setFixedHeight(0)
        lbl1.setFixedWidth(40)

        mainVBox = QtGui.QVBoxLayout()
        mainHBox.addLayout(mainVBox)
        mainVBox.setSpacing(0)
        mainCommandPanel = QtGui.QWidget(self)
        mainVBox.addWidget(mainCommandPanel)
        mainCommandPanel.setFixedHeight(110)
        mainCommandBox = QtGui.QHBoxLayout()
        mainCommandPanel.setLayout(mainCommandBox)
        mainCommandBox.setSpacing(0)
        helpBtn = QtGui.QPushButton('Help', mainCommandPanel)
        helpBtn.setFixedWidth(50)
        helpBtn.setFixedHeight(72)
        helpBtn.clicked.connect(self.onHelp)
        mainCommandBox.addWidget(helpBtn)

        reset_removeBox = QtGui.QGridLayout()
        mainCommandBox.addLayout(reset_removeBox)
        reset_removeBox.setSpacing(0)
        self.resetZPBtn = resetZPBtn = \
            QtGui.QPushButton('Reset Zoom/Pan', mainCommandPanel)
        resetZPBtn.installEventFilter(self)
        EXPL[resetZPBtn] = \
            "Zoom to the starting scale or the scale after trimming"
        resetZPBtn.setFixedWidth(140)
        resetZPBtn.clicked.connect(self.onResetZoomPan)
        reset_removeBox.addWidget(resetZPBtn, 0, 0)

        self.undoQuickRemovedBtn = undoQuickRemovedBtn = \
            QtGui.QPushButton('Undo QuickRemove', mainCommandPanel)
        undoQuickRemovedBtn.installEventFilter(self)
        EXPL[undoQuickRemovedBtn] = \
            "QuickRemove happens when user checks 'QuickRemoved' " + \
            "in the display panel" + \
            "\nwhich will change color of the station to white." + \
            "\n'Undo QuickRemove will turn the station's plot back " + \
            "to its orginal color."
        undoQuickRemovedBtn.setFixedWidth(140)
        undoQuickRemovedBtn.clicked.connect(self.onUndoQuickRemove)
        reset_removeBox.addWidget(undoQuickRemovedBtn, 1, 0)
        if isMainPlot:
            self.deepRemovedBtn = deepRemovedBtn = \
                QtGui.QPushButton('DeepRemove', mainCommandPanel)
            deepRemovedBtn.installEventFilter(self)
            EXPL[deepRemovedBtn] = \
                "After user checks 'DeepRemoved' in the display panel for " + \
                "a group of stations" + \
                "\nhe/she need to click this button to make it happen." + \
                "\n DeepRemove will completely remove the stations' data, " + \
                "which require more time than QuickRemove."
            deepRemovedBtn.setFixedWidth(140)
            deepRemovedBtn.clicked.connect(self.onDeepRemove)
            reset_removeBox.addWidget(deepRemovedBtn, 0, 1)

            self.undoDeepRemovedBtn = undoDeepRemovedBtn = QtGui.QPushButton(
                'Undo DeepRemove', mainCommandPanel)
            undoDeepRemovedBtn.installEventFilter(self)
            EXPL[undoQuickRemovedBtn] = \
                "Returnd the data for the all the deep removed stations."
            undoDeepRemovedBtn.setFixedWidth(140)
            undoDeepRemovedBtn.clicked.connect(self.onUndoDeepRemove)
            reset_removeBox.addWidget(undoDeepRemovedBtn, 1, 1)

        vbox1 = QtGui.QVBoxLayout()
        mainCommandBox.addLayout(vbox1)
        vbox1.setSpacing(0)
        self.zoompanRbtn = QtGui.QRadioButton("Zoom/pan", mainCommandPanel)
        self.zoompanRbtn.installEventFilter(self)
        EXPL[self.zoompanRbtn] = "Zoom/shift the plotting according to " + \
            "the selected action on the right"
        self.zoompanRbtn.setFixedWidth(200)
        self.zoompanRbtn.clicked.connect(self.onZoomORSelect)
        self.zoompanRbtn.setChecked(True)
        vbox1.addWidget(self.zoompanRbtn)

        self.selectRbtn = QtGui.QRadioButton("Selecting", mainCommandPanel)
        self.selectRbtn.installEventFilter(self)
        EXPL[self.selectRbtn] = \
            "Drag mouse from the starting point to the ending point\n" + \
            "then release to create the selected area.\n" + \
            "Select one of the actions on the right for that area"
        self.selectRbtn.setFixedWidth(150)
        self.selectRbtn.clicked.connect(self.onZoomORSelect)
        vbox1.addWidget(self.selectRbtn)

        vbox2 = QtGui.QVBoxLayout()
        mainCommandBox.addLayout(vbox2)
        vbox2.setSpacing(0)
        # ____________________________________
        self.selectSet = QtGui.QWidget(self)
        vbox2.addWidget(self.selectSet)

        selectBox = QtGui.QHBoxLayout()
        self.selectSet.setLayout(selectBox)
        selectBox.setSpacing(20)
        selectBox.setAlignment(QtCore.Qt.AlignJustify | QtCore.Qt.AlignLeft)
        zoomSelectBtn = QtGui.QPushButton('Zoom Selection', self.selectSet)
        zoomSelectBtn.installEventFilter(self)
        EXPL[zoomSelectBtn] = "Zoom to the selected area. No change to data"
        zoomSelectBtn.setFixedWidth(250)
        zoomSelectBtn.clicked.connect(self.canvas.onZoomSelect)
        selectBox.addWidget(zoomSelectBtn)

        if isMainPlot:
            passSelectBtn = QtGui.QPushButton(
                "Pass Selection to Support Window", self.selectSet)
            passSelectBtn.installEventFilter(self)
            EXPL[passSelectBtn] = \
                "Pass the selected area to the support window for viewing" + \
                "\nwhile keeping the drawing on Main Window the same to go" + \
                " back for later review."
            passSelectBtn.setFixedWidth(250)
            passSelectBtn.clicked.connect(self.canvas.onPassSelect)
            selectBox.addWidget(passSelectBtn)
        self.selectSet.hide()
        # _______________________________________
        self.zoomSet = QtGui.QWidget(self)
        vbox2.addWidget(self.zoomSet)

        zoomBox = QtGui.QGridLayout()
        self.zoomSet.setLayout(zoomBox)
        zoomBox.setSpacing(10)

        zoomBox.addWidget(QtGui.QLabel('Distance (km) '), 0, 0)
        self.distance = QtGui.QLineEdit('5', self.zoomSet)
        self.distance.setFixedWidth(60)
        zoomBox.addWidget(self.distance, 0, 1)

        leftBtn = QtGui.QPushButton('<', self.zoomSet)
        leftBtn.installEventFilter(self)
        EXPL[leftBtn] = "Shift the plotting to the left according to " + \
                        "value in distance box"
        leftBtn.clicked.connect(self.canvas.onLeft)
        leftBtn.setFixedWidth(30)
        zoomBox.addWidget(leftBtn, 0, 2)

        rightBtn = QtGui.QPushButton('>', self.zoomSet)
        rightBtn.installEventFilter(self)
        EXPL[rightBtn] = "Shift the plotting to the right according to " + \
                         "value in distance box"
        rightBtn.clicked.connect(self.canvas.onRight)
        rightBtn.setFixedWidth(30)
        zoomBox.addWidget(rightBtn, 0, 3)

        zoomInWBtn = QtGui.QPushButton('+', self.zoomSet)
        zoomInWBtn.installEventFilter(self)
        EXPL[zoomInWBtn] = "Zoom in the plotting horizontally according " + \
            "according  value in distance box"
        zoomInWBtn.clicked.connect(self.canvas.onZoomInW)
        zoomInWBtn.setFixedWidth(30)
        zoomBox.addWidget(zoomInWBtn, 0, 4)

        zoomOutWBtn = QtGui.QPushButton('-', self.zoomSet)
        zoomOutWBtn.installEventFilter(self)
        EXPL[zoomOutWBtn] = "Zoom out the plotting horizontally " + \
            "according to value in distance box"
        zoomOutWBtn.clicked.connect(self.canvas.onZoomOutW)
        zoomOutWBtn.setFixedWidth(30)
        zoomBox.addWidget(zoomOutWBtn, 0, 5)

        zoomBox.addWidget(QtGui.QLabel('Time (s) '), 1, 0)
        self.time = QtGui.QLineEdit('5', self.zoomSet)
        self.time.setFixedWidth(60)
        zoomBox.addWidget(self.time, 1, 1)

        upBtn = QtGui.QPushButton('A', self.zoomSet)
        upBtn.installEventFilter(self)
        EXPL[upBtn] = "Shift up the plotting according to value in time box"
        upBtn.clicked.connect(self.canvas.onUp)
        upBtn.setFixedWidth(30)
        zoomBox.addWidget(upBtn, 1, 2)

        downBtn = QtGui.QPushButton('V', self.zoomSet)
        downBtn.installEventFilter(self)
        EXPL[downBtn] = \
            "Shift down the plotting according to value in time box"
        downBtn.clicked.connect(self.canvas.onDown)
        downBtn.setFixedWidth(30)
        zoomBox.addWidget(downBtn, 1, 3)

        zoomInHBtn = QtGui.QPushButton('+', self.zoomSet)
        zoomInHBtn.installEventFilter(self)
        EXPL[zoomInHBtn] = \
            "Zoom in the plotting vertically according to value in time box"
        zoomInHBtn.clicked.connect(self.canvas.onZoomInH)
        zoomInHBtn.setFixedWidth(30)
        zoomBox.addWidget(zoomInHBtn, 1, 4)

        zoomOutHBtn = QtGui.QPushButton('-', self.zoomSet)
        zoomOutHBtn.installEventFilter(self)
        EXPL[zoomOutHBtn] = \
            "Zoom out the plotting vertically according to value in time box"
        zoomOutHBtn.clicked.connect(self.canvas.onZoomOutH)
        zoomOutHBtn.setFixedWidth(30)
        zoomBox.addWidget(zoomOutHBtn, 1, 5)

        mainCommandBox.addStretch(1)

        mainVBox.addWidget(self.canvas.native)

        lbl2 = QtGui.QLabel("", self)   # to keep vertical space
        mainVBox.addWidget(lbl2)
        lbl2.setFixedHeight(10)
        lbl2.setFixedWidth(0)

        # ___________ end of axis label on panel ______________
        self.statSelectors = []
        for i in range(3):
            self.statSelectors.append(SelectedStation(self))
            self.statSelectors[i].hide()

        self.setGeometry(x, y, w, h)

        self.show()
        self.setEnabled(False)

    def setEnabled(self, state):
        self.selectSet.setEnabled(state)
        self.zoomSet.setEnabled(state)
        self.resetZPBtn.setEnabled(state)
        self.zoompanRbtn.setEnabled(state)
        self.selectRbtn.setEnabled(state)
        self.undoQuickRemovedBtn.setEnabled(state)
        if self.isMainPlot:
            self.deepRemovedBtn.setEnabled(state)
            self.undoDeepRemovedBtn.setEnabled(state)

    ###################################
    # Author: Lan
    # def: eventFilter(): 20151022
    # detect enter event and show explaination for the widget on baloon tooltip
    def eventFilter(self, object, event):
        if not self.helpEnable:
            return False
        if event.type() == QtCore.QEvent.Enter:
            if object not in self.EXPL.keys():
                return False

            P = object.pos()
            QtGui.QToolTip.showText(self.mapToGlobal(QtCore.QPoint(P.x(),
                                    P.y()+20)), self.EXPL[object])
            return True

        return False

    def closeEvent(self, e):
        QtCore.QCoreApplication.instance().quit()
        sys.exit(application.exec_())

    def paintEvent(self, e):
        qp = QtGui.QPainter()

        qp.begin(self)
        pen = QtGui.QPen(QtCore.Qt.blue, 1.7, QtCore.Qt.DashLine)
        qp.setFont(QtGui.QFont('Decorative', 9))
        qp.setPen(pen)

        index = 0
        for lbl in self.canvas.labelPos:
            if 'y' in lbl:
                indent = 6*(6-len(lbl['text']))
                indent = indent if indent > 0 else 0
                qp.drawText(1+indent, lbl['y']+5, lbl['text'])
            else:
                qp.drawText(int(lbl['x']-len(lbl['text'])*3.5),
                            self.height()-10, lbl['text'])
            index += 1

        qp.end()

    def onHelp(self, evt):
        self.helpEnable = not self.helpEnable

        if self.helpEnable:
            cursor = QtGui.QCursor(QtCore.Qt.WhatsThisCursor)
        else:
            cursor = QtGui.QCursor(QtCore.Qt.ArrowCursor)

        self.setCursor(cursor)

    ###################################
    # Author: Lan
    # def: onResetZoomPan():201509
    # Zoom to the begining scale or the scale after trimming
    def onResetZoomPan(self, evt):
        if self.canvScaleT is None:
            return
        C = self.canvas
        C.canvScaleT = self.canvScaleT
        C.canvScaleV = self.canvScaleV
        C.panT = self.panT
        C.panV = self.panV
        C.feedData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        C.update_scale()

        C.gtData, C.gdData, C.timeY, C.tLabels, C.dLabels = C.buildGrid()
        C.feedGData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)

        C.labelPos = C.resiteLabels()
        for i in range(2):
            self.statSelectors[i].hide()
        C.update()
        self.update()

    def onUndoQuickRemove(self, evt):
        for ch in self.parent.channels:
            for i in range(
                    len(self.parent.PH5Info['quickRemoved'][ch].keys())):
                removId = self.parent.PH5Info['quickRemoved'][ch].keys()[-1]
                c = self.canvas.quickRemove(ch, removId, False)
                self.canvas.otherCanvas.quickRemove(ch, removId, False, c)

        self.canvas.updateData()
        self.canvas.otherCanvas.updateData()
        for ch in self.parent.channels:
            for p in self.parent.infoPanels:
                p.allowRemove = False
                p.quickRemCkbs[ch].setCheckState(QtCore.Qt.Unchecked)
                p.allowRemove = True

    def onDeepRemove(self, evt):
        totalTraces = 0
        for ch in self.parent.channels:
            totalTraces += self.parent.PH5Info['numOfStations'] - \
                len(self.parent.PH5Info['deepRemoved'][ch])

        if totalTraces == 0:
            errorMsg = "You are trying to remove all data." + \
                "\nThere must be at least one trace left in the plotting."
            QtGui.QMessageBox.question(self, 'Error', errorMsg,
                                       QtGui.QMessageBox.Ok)
            return
        self.parent.deepRemoveStations()

    def onUndoDeepRemove(self, evt):
        for ch in self.parent.channels:
            for p in self.parent.infoPanels:
                p.allowRemove = False
                p.deepRemCkbs[ch-1].setCheckState(QtCore.Qt.Unchecked)
                p.allowRemove = True

            self.parent.PH5Info['deepRemoved'][ch] = []
        self.parent.deepRemoveStations()

    def onZoomORSelect(self, evt):
        if self.zoompanRbtn.isChecked():
            self.selectSet.hide()
            self.zoomSet.show()
            self.canvas.zoomWidget.hide()
            self.canvas.select = False
            self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        else:
            self.zoomSet.hide()
            self.selectSet.show()
            self.canvas.select = True
            self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

    def focusInEvent(self, event=None):
        if self.canvas.enableDrawing:
            self.canvas.defineViewWindow(0, 0, self.canvas.width,
                                         self.canvas.height)


# ##############################################
# IMPORTANT FOR MAC: display the menubar to be inside application mainwindow
if sys.platform == "darwin":
    QtGui.qt_mac_set_native_menubar(False)


"""
____________________ CLASS ____________________
Author: Lan
Updated: 201410
CLASS: PH5Visualizer
The Widget that keep
   + the menu for Open File, Save, Print, Exit
   + the tab for Control Panel, Event Panel, Array Panel
"""


class PH5Visualizer(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setWindowTitle("PH5 View Ver. %s" % PROG_VERSION)
        self.helpEnable = False
        self.submitGui = None
        self.fname = None
        self.arrays = []
        self.channels = []
        self.events = []
        explainAction = QtGui.QAction('What?', self)
        explainAction.setShortcut('Ctrl+E')
        explainAction.triggered.connect(self.onExplain)

        manualAction = QtGui.QAction('Manual', self)
        manualAction.setShortcut('F1')
        manualAction.triggered.connect(self.onManual)

        whatsnewAction = QtGui.QAction("What's new?", self)
        whatsnewAction.setShortcut('F1')
        whatsnewAction.triggered.connect(self.onWhatsnew)

        # __________________ FILE MENU ____________________
        self.fileAction = fileAction = QtGui.QAction('Open File', self)
        fileAction.triggered.connect(self.onFile)

        # ____________________ exit ________________________
        self.exitAction = QtGui.QAction('&Exit', self)
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.triggered.connect(self.closeEvent)

        # ____________________ SAVE MENU ____________________
        self.saveMAction = QtGui.QAction(
            'Save The Whole Image from Main Window', self)
        self.saveMAction.triggered.connect(self.onSaveMainWindow)
        self.saveMAction.setEnabled(False)

        self.saveMZAction = QtGui.QAction(
            'Save The Part of Image Showed in Main Window', self)
        self.saveMZAction.triggered.connect(self.onSaveZoomMainWindow)
        self.saveMZAction.setEnabled(False)

        self.saveSAction = QtGui.QAction(
            'Save The Whole Image from Support Window', self)
        self.saveSAction.triggered.connect(self.onSaveSupportWindow)
        self.saveSAction.setEnabled(False)

        self.saveSZAction = QtGui.QAction(
            'Save The Part of Image Showed in Support Window', self)
        self.saveSZAction.triggered.connect(self.onSaveZoomSupportWindow)
        self.saveSZAction.setEnabled(False)

        # ________________ PRINT MENU __________________
        self.printMAction = QtGui.QAction(
            'Print The Whole Image from Main Window', self)
        self.printMAction.triggered.connect(self.onPrintMainWindow)
        self.printMAction.setEnabled(False)

        self.printMZAction = QtGui.QAction(
            'Print The Part of Image Showed in Main Window', self)
        self.printMZAction.triggered.connect(self.onPrintZoomMainWindow)
        self.printMZAction.setEnabled(False)

        self.printSAction = QtGui.QAction(
            'Print The Whole Image from Support Window', self)
        self.printSAction.triggered.connect(self.onPrintSupportWindow)
        self.printSAction.setEnabled(False)

        self.printSZAction = QtGui.QAction(
            'Print The Part of Image Showed in Support Window', self)
        self.printSZAction.triggered.connect(self.onPrintZoomSupportWindow)
        self.printSZAction.setEnabled(False)

        # ________________ SEGY MENU _________________
        self.segyAction = QtGui.QAction('SEGY', self)
        self.segyAction.triggered.connect(self.onDevelopeSegy)
        self.segyAction.setEnabled(False)

        # _________________ add menu __________________
        self.menubar = QtGui.QMenuBar()
        self.setMenuBar(self.menubar)

        fileMenu = self.menubar.addMenu('&File')

        fileMenu.addAction(fileAction)
        fileMenu.addAction(self.exitAction)
        fileMenu.insertSeparator(self.exitAction)

        self.saveMenu = self.menubar.addMenu('&Save')
        self.saveMenu.setEnabled(False)
        self.saveMenu.addAction(self.saveMAction)
        self.saveMenu.addAction(self.saveMZAction)
        self.saveMenu.addAction(self.saveSAction)
        self.saveMenu.addAction(self.saveSZAction)
        self.saveMenu.insertSeparator(self.saveSAction)

        self.printMenu = self.menubar.addMenu('&Print')
        self.printMenu.setEnabled(False)
        self.printMenu.addAction(self.printMAction)
        self.printMenu.addAction(self.printMZAction)
        self.printMenu.addAction(self.printSAction)
        self.printMenu.addAction(self.printSZAction)
        self.printMenu.insertSeparator(self.printSAction)

        self.menubar.addAction(self.segyAction)

        self.helpMenu = self.menubar.addMenu('&Help')
        self.helpMenu.addAction(explainAction)
        self.helpMenu.addAction(manualAction)
        self.helpMenu.addAction(whatsnewAction)

        # ______________________________________________

        self.tabWidget = QtGui.QTabWidget(self)
        self.setCentralWidget(self.tabWidget)
        self.mainControl = MainControl(self)
        self.tabWidget.addTab(self.mainControl, "Control")

        self.eventGui = ArrayGui(self, ESType='EVENT')
        self.tabWidget.addTab(self.eventGui, 'Shot Gather')

        self.stationGui = ArrayGui(self, ESType='STATION')
        self.tabWidget.addTab(self.stationGui, 'Receiver Gather')

        # LOI: lack of info
        self.loiEventGui = ArrayGui(self, ESType='EVENT_LOI')
        self.tabWidget.addTab(self.loiEventGui, 'Event LOI')

        self.setGeometry(0, 0, 700, 700)

        self.show()

    def closeEvent(self, evt=None):
        try:
            for f in PH5VALFILES:
                os.unlink(f)            # remove tmp file
        except Exception:
            pass
        QtCore.QCoreApplication.instance().quit()
        sys.exit(application.exec_())

    def onDevelopeSegy(self):
        segyDir = os.getcwd()

        try:
            confFile = open(USERHOME + '/.PH5/PH5Viewer.cfg', 'r+')
        except IOError:
            return

        print "fname:", self.fname
        dataPath = os.path.dirname(os.path.abspath(str(self.fname)))
        segyDir = dataPath + "/SEGY"
        print "segyDir:", segyDir
        lines = confFile.readlines()
        confFile.seek(0)
        confFile.truncate()

        for line in lines:
            leng = line.split(":")
            if leng[0] == 'SegyDir':
                segyDir = leng[1].strip()
                lines.remove(line)
                break

        confFile.writelines(lines)

        segyDir = QtGui.QFileDialog.getExistingDirectory(
                    self, 'SEGY output directory', segyDir,
                    QtGui.QFileDialog.ShowDirsOnly)

        confFile.write("\nSegyDir:%s" % segyDir)
        confFile.close()
        if segyDir == "":
            return
        msg = "Enter sub directory name if you want to create a sub " + \
              "directory to save SEGY data,\n" + \
              "or leave it blank to save in the selected directory:"

        text, ok = QtGui.QInputDialog.getText(self, 'Enter Sub directory', msg)

        if ok:
            if str(text).strip() != "":
                segyDir = segyDir + "/" + str(text).strip()
        else:
            return

        options = {}
        PH5View = self.mainControl.PH5View
        pathName = str(self.fname).split('/')
        options['ph5Path'] = "-p %s" % "/".join(pathName[:-1])
        options['nickname'] = "-n %s" % pathName[-1]
        options['outputDir'] = '-o %s' % segyDir
        options['shotLine'] = '--shot_line %s' % PH5View.shotLine

        timeLength = float(self.mainControl.timelenCtrl.text())
        if timeLength < 1:
            timeLength = 1
        else:
            timeLength = int(round(timeLength))
        options['length'] = "-l %s" % timeLength
        channels = [str(ch) for ch in self.mainControl.channels
                    if self.mainControl.channelCkbs[ch].isChecked()]

        options['array'] = "-A %s" % PH5View.selectedArray['arrayId']
        options['chan'] = "-c %s" % ",".join(channels)

        if str(self.mainControl.velocityCtrl.text()).strip() in ['0', '']:
            options['redVel'] = ''
            options['offset'] = ''
        else:
            rv = float(self.mainControl.velocityCtrl.text())/1000.0
            options['redVel'] = '-V %f' % rv
            options['offset'] = '-O %f' % \
                float(self.mainControl.offsetCtrl.text())

        if self.submitGui == 'STATION':
            print "shot gather"
            options['stations'] = '--station_list %s' % \
                ','.join(PH5View.selectedArray['seclectedStations'])
            options['event'] = '-e %s' % \
                PH5View.selectedEvents[0]['eventId']
            options['offset'] = '-O %f' % \
                float(self.mainControl.offsetCtrl.text())

            if self.mainControl.correctionCkb.isChecked():
                options['timeCorrect'] = ''
            else:
                options['timeCorrect'] = '-N'

            cmdStr = "ph5toevt % (shotLine)s % (array)s % (event)s % " + \
                "(chan)s % (length)s % (offset)s % (stations)s % (redVel)s" + \
                " % (timeCorrect)s % (ph5Path)s % (nickname)s % (outputDir)s"

        elif self.submitGui == 'EVENT':
            print "receiver gather"
            options['station'] = '-S %s' % \
                PH5View.selectedArray['seclectedStations'][0]
            events = [ev['eventId'] for ev in PH5View.selectedEvents]
            options['events'] = '--event_list %s' % ','.join(events)

            cmdStr = "ph5torec %(shotLine)s %(array)s %(chan)s " + \
                "%(station)s %(events)s %(length)s %(redVel)s " + \
                "%(offset)s %(ph5Path)s %(nickname)s %(outputDir)s"

        from subprocess import Popen, PIPE, STDOUT

        p = Popen(cmdStr % options, shell=True, stdin=PIPE, stdout=PIPE,
                  stderr=STDOUT, close_fds=True)
        output = p.stdout.read()
        print "The following command is running:"
        print cmdStr % options
        print "Output: ", output
        # os.system(cmdStr % options)
        if 'Done' in output:
            msg = "SEGY file has been saved successfully into directory %s" % \
                segyDir
            QtGui.QMessageBox.warning(
                self, "Successfully Saving SEGY File", msg)
        else:
            msg = "Unsuccessfully creating SEGY file due to the error: %s" % \
                output
            QtGui.QMessageBox.warning(
                self, "Unsuccessfully Saving SEGY File", msg)

    def onExplain(self):
        self.helpEnable = not self.helpEnable

        if self.helpEnable:
            cursor = QtGui.QCursor(QtCore.Qt.WhatsThisCursor)
        else:
            cursor = QtGui.QCursor(QtCore.Qt.ArrowCursor)

        self.setCursor(cursor)

    def onManual(self):
        self.manualWin = ManWindow("manual")

    def onWhatsnew(self):
        self.whatsnewWin = ManWindow("whatsnew")

    def onFile(self):
        self.isLoiEvent = False
        dialog = QtGui.QFileDialog(self)
        dialog.setFileMode(QtGui.QFileDialog.ExistingFile)
        fname = dialog.getOpenFileName(
            self, 'Open', '/home/field/Desktop/data', 'master.ph5')
        print fname

        if fname == "":
            errorMsg = "Can't find the ph5 file: %s" % fname
            QtGui.QMessageBox.question(self, 'Error', errorMsg,
                                       QtGui.QMessageBox.Ok)
            return

        self.fname = fname

        self.eventGui.clearArrayTabs()
        self.stationGui.clearArrayTabs()
        self.loiEventGui.clearArrayTabs()
        try:
            del self.arrays
        except Exception:
            pass
        try:
            del self.events
        except Exception:
            pass
        gc.collect()

        PH5Object = ph5_viewer_reader.PH5Reader()
        try:
            PH5Object.initialize_ph5(self.fname)
        except ph5_viewer_reader.PH5ReaderError, e:
            msg = e.message + \
                  "\n\nYou should choose another dataset (ph5 file) to view."
            QtGui.QMessageBox.warning(self, "No Das_t", msg)

        try:
            PH5Object.createGraphExperiment()
        except ph5_viewer_reader.PH5ReaderError, e:
            msg = e.message + "\n\nThe graphic will be named UNTITLED."
            QtGui.QMessageBox.warning(self, "No Experiment_t", msg)

        try:
            PH5Object.createGraphArraysNStations()
        except ph5_viewer_reader.PH5ReaderError, e:
            msg = e.message + "\n\nYou should choose another dataset " + \
                 "(ph5 file) to view."
            title = ""
            if "Array_t" in e.message:
                title = "No Array_t"
            elif "channels" in e.message:
                title = "Number of channels exceeds limit"
            QtGui.QMessageBox.warning(self, title, msg)
            # disable shot gather tab
            self.tabWidget.setTabEnabled(1, False)
            # disable receiver gather tab
            self.tabWidget.setTabEnabled(2, False)
            # disable non-event_t tab
            self.tabWidget.setTabEnabled(3, False)
            self._closePH5(PH5Object)
            self.tabWidget.setCurrentIndex(0)    # view ctrl tab
            return

        try:
            PH5Object.createGraphEvents()
            # enable shot gather tab
            self.tabWidget.setTabEnabled(1, True)
            # enable receiver gather tab
            self.tabWidget.setTabEnabled(2, True)
            # disable non-event_t tab
            self.tabWidget.setTabEnabled(3, False)
            # view shot gather tab
            self.tabWidget.setCurrentIndex(1)
        except ph5_viewer_reader.PH5ReaderError, e:
            msg = e.message + \
                "\n\nThe time in the 'Start time' box is " + \
                "the array's deploy time" + \
                "\n\nYou need to enter the shot's time yourself " + \
                "to set up window time for the graph." + \
                "\n\nP.S. LOI stands for Lack Of Information"
            QtGui.QMessageBox.warning(self, "Lack of Events' information", msg)
            # disable shot gather tab
            self.tabWidget.setTabEnabled(1, False)
            # disable receiver gather tab
            self.tabWidget.setTabEnabled(2, False)
            # enable non-event_t tab
            self.tabWidget.setTabEnabled(3, True)
            # view non-event_t tab
            self.tabWidget.setCurrentIndex(3)
            self.isLoiEvent = True

        self.arrays = deepcopy(PH5Object.graphArrays)
        self.events = deepcopy(PH5Object.graphEvents)

        if self.isLoiEvent:
            self.loiEventGui.setArrays()
        else:
            self.eventGui.setArrays()
            self.stationGui.setArrays()

        self.mainControl.setWidgetsEnabled(False)

        self.graphName = "UNTITLED"
        if PH5Object.graphExperiment is not None:
            self.graphName = \
                "%s %s" % (PH5Object.graphExperiment['experiment_id_s'],
                           PH5Object.graphExperiment['nickname_s'])

        self.eventGui.setNotice(self.graphName)
        self.stationGui.setNotice(self.graphName)
        self.loiEventGui.setNotice(self.graphName)
        self.mainControl.mainPlot.setWindowTitle(
            'Main Window -  %s' % (self.graphName))
        self.mainControl.supportPlot.setWindowTitle(
            'Support Window -  %s' % (self.graphName))
        # close all opened files and remove PH5Object
        # when done to save resources
        self._closePH5(PH5Object)

    def _closePH5(self, PH5Object):
        PH5Object.ph5close()
        del PH5Object
        gc.collect()

    ###################################
    # Author: Lan
    # def: onSaveMainWindow():201410
    def onSaveMainWindow(self):
        self.mainControl.mainCanvas.save2file('save_M')

    def onSaveZoomMainWindow(self):
        self.mainControl.mainCanvas.save2file('save_MZ')

    ###################################
    # Author: Lan
    # def: onSaveSupportWindow():201507
    def onSaveSupportWindow(self):
        self.mainControl.supportCanvas.save2file('save_S')

    def onSaveZoomSupportWindow(self):
        self.mainControl.supportCanvas.save2file('save_SZ')

    ###################################
    # Author: Lan
    # def: onPrintMainWindow():201410
    def onPrintMainWindow(self):
        self.mainControl.mainCanvas.printing('printM')

    def onPrintZoomMainWindow(self):
        self.mainControl.mainCanvas.printing('printMZ')

    ###################################
    # Author: Lan
    # def: onPrintSupportWindow():201410
    def onPrintSupportWindow(self):
        self.mainControl.supportCanvas.printing('printS')

    def onPrintZoomSupportWindow(self):
        self.mainControl.supportCanvas.printing('printSZ')

    def focusInEvent(self, event):
        pass
        # print "FOCUSINEVENT PH5Visualizer"


"""
_______________________ CLASS ____________________
Author: Lan
Updated: 201410
CLASS: MainControl - The control Gui - set the properties for graphic
it has 3 panels which always open:
   + Main Window: display data's plot
   + Support Window: give user the option of viewing
   + a smaller part of data, then go back to do other task quicker
   + infoPanel: showing the info of a station
        when shift + right-click at that station
"""


class MainControl(QtGui.QMainWindow):
    def __init__(self, parent):
        QtGui.QMainWindow.__init__(self)
        self.PH5View = parent
        self.conf = {}
        self.initConfig()
        self.eventId = None
        self.channels = None
        self.shotLine = None
        self.PH5Info = None
        self.initUI()
        self.dfltOffset = 0
        self.dfltTimeLen = 60
        self.gather = ""
        # self.dfltTimeLen = .6    ### TESTING .6

        self.mainPlot = \
            PlottingPanel(self, "Main Window", 270, 0, 1200, 1100,
                          isMainPlot=True)
        self.mainCanvas = self.mainPlot.canvas
        self.supportPlot = \
            PlottingPanel(self, "Support Window", 290, 0, 1200, 1100,
                          isMainPlot=False)
        self.supportCanvas = self.supportPlot.canvas
        self.mainCanvas.setOtherCanvas(self.supportCanvas)
        self.supportCanvas.setOtherCanvas(self.mainCanvas)
        self.createInfoPanel()
        global processInfo
        processInfo = WARNINGMSG
        self.statusLbl.setText(processInfo)

    def reset(self):
        self.PH5Info = None
        self.keepList = None
        self.corrList = None
        self.redVelList = None
        self.statLimitList = None
        self.scaleVList = None
        self.totalSize = None
        self.metadata = None
        self.scaleVList = None
        self.eventId = None
        self.mainCanvas.reset(needUpdate=True)
        self.supportCanvas.reset(needUpdate=True)
        gc.collect()

    ###################################
    # Author: Lan
    # def: createInfoPanel():201504
    def createInfoPanel(self):
        self.infoParentPanel = QtGui.QWidget()
        self.infoParentPanel.setGeometry(-10, 10, 315, 1100)
        self.infoParentPanel.setWindowFlags(QtCore.Qt.Window)
        vbox = QtGui.QVBoxLayout(self.infoParentPanel)
        vbox.setSpacing(0)

        scrollArea = QtGui.QScrollArea(self.infoParentPanel)
        vbox.addWidget(scrollArea)
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scrollArea.setWidgetResizable(True)

        itemsFrame = QtGui.QFrame()
        scrollArea.setWidget(itemsFrame)
        self.infoBox = QtGui.QVBoxLayout()
        itemsFrame.setLayout(self.infoBox)

        self.infoPanels = []

    ###################################
    # Author: Lan
    # def: setDefaultConf():201410
    # create default configuration for name and color properties
    def initConfig(self):
        # setDefaultConf
        self.defaultConf = {}

        # on the title bar or at the top of saved file/ print paper
        self.defaultConf['addingInfo'] = ""
        # horizontal labels
        self.defaultConf['hLabel'] = "STATION SEQUENCE"

        # vertical labels
        self.defaultConf['vLabel'] = "TIME (ms)"

        # number of stations in the color pattern
        self.defaultConf['patternSize'] = 15

        self.defaultConf['plotThick'] = 0.6
        self.defaultConf['gridThick'] = 0.4
        self.defaultConf['gridColor'] = QColor(150, 150, 150).name()
        self.defaultConf['showAbnormalStat'] = True

        self.defaultConf['abnormalColor'] = '#ff0000'
        colorSet = ['#a0a0a4', '#ffff00', '#00ffff']  # gray, yellow, cyan
        # define color in the pattern
        self.defaultConf['plotColor'] = [[], [], []]
        for ch in range(len(self.defaultConf['plotColor'])):
            for i in range(self.defaultConf['patternSize']):
                self.defaultConf['plotColor'][ch].append(colorSet[ch])

        # preset FileConf with default value
        self.fileConf = deepcopy(self.defaultConf)

        try:
            confFile = open(USERHOME + '/.PH5/PH5Viewer.cfg', 'r')

            ncolor = None
            lines = confFile.readlines()
            confFile.close()
            colorChan = -1
            for line in lines:
                leng = line.split(":")
                if leng[0] == 'addingInfo':
                    self.fileConf['addingInfo'] = leng[1].strip()
                elif leng[0] == 'hLabel':
                    self.fileConf['hLabel'] = leng[1].strip()
                elif leng[0] == 'vLabel':
                    self.fileConf['vLabel'] = leng[1].strip()
                elif leng[0] == 'gridColor':
                    self.fileConf['gridColor'] = leng[1].strip()
                elif leng[0] == 'patternSize':
                    self.fileConf['patternSize'] = int(leng[1].strip())
                elif leng[0] == 'plotThick':
                    self.fileConf['plotThick'] = float(leng[1].strip())
                elif leng[0] == 'gridThick':
                    self.fileConf['gridThick'] = float(leng[1].strip())
                elif leng[0] == 'abnormalColor':
                    self.fileConf['abnormalColor'] = leng[1].strip()
                elif 'plotColor' in leng[0]:
                    # plotColor1: 1 is channel,
                    # when channel index changed, create new list
                    if ncolor != leng[0][-1]:
                        ncolor = leng[0][-1]
                        colorChan += 1
                        count = -1
                    count += 1
                    try:
                        self.fileConf['plotColor'][colorChan][count] = \
                            leng[1].strip()
                    except Exception:
                        pass

                elif leng[0] == 'showAbnormalStat':
                    self.fileConf['showAbnormalStat'] = \
                        True if leng[1].strip() == 'True' else False

        except Exception:
            print "PH5Viewer.cfg does not exist."
            saveConfFile(self.fileConf)

        # each plotColor has been assiged default plotColor
        if self.fileConf['patternSize'] < self.defaultConf['patternSize']:
            # if new patternSize is smaller,
            # need to trim the extra value assigned before
            for plotColor in self.fileConf['plotColor']:
                plotColor = plotColor[:self.fileConf['patternSize']]
        elif self.fileConf['patternSize'] > self.defaultConf['patternSize']:
            # if new patternSize is smaller,
            # some missed channel need to be filled up
            for ch in range(len(self.fileConf['plotColor'])):
                plotColor = self.fileConf['plotColor'][ch]
                if len(plotColor) < self.fileConf['patternSize']:
                    plotColor[len(plotColor):self.fileConf['patternSize']] = \
                        self.defaultConf['plotColor'][ch]

    def onChangePropertyType(self, evt=None):
        if self.defaultPropRbtn.isChecked():
            self.conf = deepcopy(self.defaultConf)
        else:
            self.conf = deepcopy(self.fileConf)

        for ch in range(len(self.channels)):
            if ch < len(self.conf['plotColor']):
                self.channelCkbs[self.channels[ch]].setStyleSheet(
                    "QWidget { background-color: %s }" %
                    QColor(self.conf['plotColor'][ch][0]).name())
            else:
                self.channelCkbs[self.channels[ch]].setStyleSheet(
                    "QWidget { background-color: %s }" %
                    QColor(self.defaultConf['plotColor'][ch][0]).name())

    ###################################
    # Author: Lan
    # def: initUI(): updated 201509
    # Layout of MainControl
    def initUI(self):
        self.EXPL = {}
        mainFrame = QtGui.QFrame(self)
        self.setCentralWidget(mainFrame)
        mainbox = QtGui.QHBoxLayout()
        mainFrame.setLayout(mainbox)

        vbox = QtGui.QVBoxLayout()
        mainbox.addLayout(vbox)

        # _______________________ Time _________________________
        startrangeHBox = QtGui.QHBoxLayout()
        vbox.addLayout(startrangeHBox)
        startrangeHBox.addWidget(QtGui.QLabel('Start time'))
        self.startrangetimeCtrl = QtGui.QLineEdit('')
        self.startrangetimeCtrl.installEventFilter(self)
        self.EXPL[self.startrangetimeCtrl] = "The start time for plotting."
        startrangeHBox.addWidget(self.startrangetimeCtrl)

        timerangeHBox = QtGui.QHBoxLayout()
        vbox.addLayout(timerangeHBox)
        timerangeHBox.addWidget(QtGui.QLabel('Length (s)'))
        self.timelenCtrl = QtGui.QLineEdit()
        self.timelenCtrl.installEventFilter(self)
        self.EXPL[self.timelenCtrl] = "The length of time for plotting."
        self.timelenCtrl.textChanged.connect(self.onChangeTimeLen)
        timerangeHBox.addWidget(self.timelenCtrl)

        timerangeHBox.addWidget(QtGui.QLabel('Offset'))
        self.offsetCtrl = QtGui.QLineEdit('')
        self.offsetCtrl.installEventFilter(self)
        self.EXPL[self.offsetCtrl] = "Move the start time of the plot " + \
                                     "relative to the shot time, seconds."
        timerangeHBox.addWidget(self.offsetCtrl)

        vbox.addStretch(1)
        vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        vbox.addStretch(1)

        # _______________________ Simplify _____________________
        gridBox = QtGui.QGridLayout()
        vbox.addLayout(gridBox)
        gridBox.addWidget(QtGui.QLabel('Ignore minor signal (0-20%)', self),
                          0, 0)

        self.distance2AvgSB = QtGui.QSpinBox(self)
        self.distance2AvgSB.installEventFilter(self)
        self.EXPL[self.distance2AvgSB] = \
            "Define how low is the percentage of the signal to be ignored."

        # self.distance2AvgSB.setFixedWidth(45)
        self.distance2AvgSB.setRange(0, 20)
        self.distance2AvgSB.setSingleStep(1)
        self.distance2AvgSB.setValue(5)
        # self.distance2AvgSB.setValue(20)  # ###TESTING 20
        gridBox.addWidget(self.distance2AvgSB, 0, 1)

        self.simplifyReplotBtn = QtGui.QPushButton('Apply', self)
        self.simplifyReplotBtn.installEventFilter(self)
        self.EXPL[self.simplifyReplotBtn] = \
            "Apply new percentage of signal to be ignored and " + \
            "replot without rereading PH5 data."
        self.simplifyReplotBtn.clicked.connect(self.onApplySimplify_RePlot)
        self.simplifyReplotBtn.setFixedWidth(60)
        gridBox.addWidget(self.simplifyReplotBtn, 0, 2)

        # ________________________ Overlap ________________________
        gridBox.addWidget(QtGui.QLabel('Overlap (0-80%):', self), 1, 0)
        self.overlapSB = QtGui.QSpinBox(self)
        self.overlapSB.installEventFilter(self)
        self.EXPL[self.overlapSB] = \
            "Define the growing percentage of the width given for each signal."
        self.overlapSB.setRange(0, 80)
        self.overlapSB.setValue(25)
        gridBox.addWidget(self.overlapSB, 1, 1)

        self.overlapReplotBtn = QtGui.QPushButton('Apply', self)
        self.overlapReplotBtn.installEventFilter(self)
        self.EXPL[self.overlapReplotBtn] = \
            "Apply new Overlap setting and replot without\n" + \
            "reread PH5 data and recreate time values"
        self.overlapReplotBtn.clicked.connect(
            self.onApplyOverlapNormalize_RePlot)
        self.overlapReplotBtn.setFixedWidth(60)
        gridBox.addWidget(self.overlapReplotBtn, 1, 2)

        vbox.addStretch(1)

        # ______________________ NORMALIZE _______________________
        self.normalizeCkb = QtGui.QCheckBox('NORMALIZE          ', self)
        self.normalizeCkb.installEventFilter(self)
        self.EXPL[self.normalizeCkb] = \
            "If selected, each station's signal will " + \
            "grow to its entire width.\n" + \
            "If not, use the same scale for all stations' signal.\n" + \
            "Click 'Get Data and Plot' to replot."
        self.normalizeCkb.setCheckState(QtCore.Qt.Checked)
        gridBox.addWidget(self.normalizeCkb, 2, 0)

        self.normalizeReplotBtn = QtGui.QPushButton('Apply', self)
        self.normalizeReplotBtn.installEventFilter(self)
        self.normalizeReplotBtn.clicked.connect(
            self.onApplyOverlapNormalize_RePlot)
        self.normalizeReplotBtn.setFixedWidth(60)
        gridBox.addWidget(self.normalizeReplotBtn, 2, 2)

        # ______________________ Dirty way ______________________
        stationSpacingUnknownBox = QtGui.QHBoxLayout()
        vbox.addLayout(stationSpacingUnknownBox)
        self.stationSpacingUnknownCkb = \
            QtGui.QCheckBox('STATION SPACING UNKNOWN', self)
        self.stationSpacingUnknownCkb.installEventFilter(self)
        self.EXPL[self.stationSpacingUnknownCkb] = \
            "If selected, use 'Nominal station spacing' " + \
            "as space between two stations." + \
            "\nClick 'Get Data and Plot' to replot."
        stationSpacingUnknownBox.addWidget(self.stationSpacingUnknownCkb)
        self.stationSpacingUnknownCkb.clicked.connect(
            self.onChangeApplyStationSpacingUnknown)

        dOffsetBox = QtGui.QHBoxLayout()
        vbox.addLayout(dOffsetBox)
        dOffsetBox.addWidget(QtGui.QLabel("Nominal station spacing(m):", self))
        self.nominalStaSpace = QtGui.QLineEdit('1000')
        self.nominalStaSpace.installEventFilter(self)
        self.EXPL[self.nominalStaSpace] = \
            "If 'STATION SPACING UNKNOWN' is selected, " + \
            "this will be used as space between two stations."
        dOffsetBox.addWidget(self.nominalStaSpace)

        vbox.addStretch(1)
        # vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        vbox.addStretch(1)
        # ____________ apply correction/ velocity reduction? ________________
        velHBox = QtGui.QHBoxLayout()
        vbox.addLayout(velHBox)

        velHBox.addWidget(QtGui.QLabel('Reduction Velocity(m/s):     '))
        self.velocityCtrl = QtGui.QLineEdit('0', self)
        self.velocityCtrl.installEventFilter(self)
        self.EXPL[self.velocityCtrl] = \
            "Reduction Velocity applied to the plot.\n" + \
            "Applied when the given value is > 0"
        # self.velocityCtrl.setFixedWidth(45)
        velHBox.addWidget(self.velocityCtrl)

        self.correctionCkb = QtGui.QCheckBox('Time Correction', self)
        self.correctionCkb.installEventFilter(self)
        self.EXPL[self.correctionCkb] = \
            "Select to include clock drift correction."
        self.correctionCkb.setCheckState(QtCore.Qt.Checked)
        vbox.addWidget(self.correctionCkb)

        vbox.addStretch(1)
        vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        vbox.addStretch(1)

        # ____________________ Properties selection __________________
        propBox = QtGui.QHBoxLayout()
        vbox.addLayout(propBox)

        propV1Box = QtGui.QVBoxLayout()
        propBox.addLayout(propV1Box)
        self.defaultPropRbtn = QtGui.QRadioButton('Default Prop.')
        self.defaultPropRbtn.installEventFilter(self)
        self.defaultPropRbtn.clicked.connect(self.onChangePropertyType)
        self.EXPL[self.defaultPropRbtn] = \
            "Use the default properties for names and colors."
        propV1Box.addWidget(self.defaultPropRbtn)

        self.fromFilePropRbtn = QtGui.QRadioButton('Previous Prop.')
        self.fromFilePropRbtn.installEventFilter(self)
        self.fromFilePropRbtn.clicked.connect(self.onChangePropertyType)
        self.EXPL[self.fromFilePropRbtn] = \
            "Use the properties that were use prevously.\n" + \
            "These properties can be editted by clicking 'Name-Color Prop."
        propV1Box.addWidget(self.fromFilePropRbtn)
        self.fromFilePropRbtn.setChecked(True)

        propGroup = QtGui.QButtonGroup(self)
        propGroup.addButton(self.defaultPropRbtn)
        propGroup.addButton(self.fromFilePropRbtn)

        propV2Box = QtGui.QVBoxLayout()
        propBox.addLayout(propV2Box)
        self.changePropBtn = QtGui.QPushButton('Name-Color Prop.', self)
        self.changePropBtn.installEventFilter(self)
        self.EXPL[self.changePropBtn] = \
            "Open the Properties window for user to edit."
        self.changePropBtn.clicked.connect(self.onChangeProperties)
        self.changePropBtn.resize(self.changePropBtn.sizeHint())
        propV2Box.addWidget(self.changePropBtn)

        self.propReplotBtn = QtGui.QPushButton('Apply and RePlot', self)
        self.propReplotBtn.installEventFilter(self)
        self.EXPL[self.propReplotBtn] = "Apply the selected property option."
        self.propReplotBtn.clicked.connect(self.onApplyPropperty_RePlot)
        self.propReplotBtn.resize(self.propReplotBtn.sizeHint())
        propV2Box.addWidget(self.propReplotBtn)

        vbox.addStretch(1)
        vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        vbox.addStretch(1)

        # ___________________ grid lines _______________
        gridBox = QtGui.QHBoxLayout()
        vbox.addLayout(gridBox)
        self.distanceGridCkb = QtGui.QCheckBox('Distance grid', self)
        self.distanceGridCkb.installEventFilter(self)
        self.EXPL[self.distanceGridCkb] = \
            "Apply distance grid lines. Take effect right after selected"
        gridBox.addWidget(self.distanceGridCkb)
        self.distanceGridCkb.clicked.connect(self.onChangeApplyGrids)

        self.timeGridCkb = QtGui.QCheckBox('time grid', self)
        self.timeGridCkb.installEventFilter(self)
        self.EXPL[self.timeGridCkb] = \
            "Apply time grid lines. Take effect right after selected"
        self.timeGridCkb.setCheckState(QtCore.Qt.Checked)
        gridBox.addWidget(self.timeGridCkb)
        self.timeGridCkb.clicked.connect(self.onChangeApplyGrids)

        paneBox = QtGui.QHBoxLayout()
        vbox.addLayout(paneBox)

        paneBox.addWidget(QtGui.QLabel("ReGrid Panel"))
        self.mainWindowRbtn = QtGui.QRadioButton('Main')
        self.mainWindowRbtn.installEventFilter(self)
        self.EXPL[self.mainWindowRbtn] = \
            "New grid intervals will be applied on Main Window"
        paneBox.addWidget(self.mainWindowRbtn)
        self.supportWindowRbtn = QtGui.QRadioButton('Support')
        self.supportWindowRbtn.installEventFilter(self)
        self.EXPL[self.supportWindowRbtn] = \
            "New grid intervals will be applied on Support Window"
        paneBox.addWidget(self.supportWindowRbtn)
        self.mainWindowRbtn.setChecked(True)
        self.bothWindowRbtn = QtGui.QRadioButton('Both')
        self.bothWindowRbtn.installEventFilter(self)
        paneBox.addWidget(self.bothWindowRbtn)

        panelGroup = QtGui.QButtonGroup(self)
        panelGroup.addButton(self.mainWindowRbtn)
        panelGroup.addButton(self.supportWindowRbtn)
        panelGroup.addButton(self.bothWindowRbtn)

        gridHBox = QtGui.QHBoxLayout()
        vbox.addLayout(gridHBox)
        gridVBox = QtGui.QVBoxLayout()
        gridHBox.addLayout(gridVBox)

        horGridHBox = QtGui.QHBoxLayout()
        gridVBox.addLayout(horGridHBox)
        horGridHBox.addWidget(QtGui.QLabel("Time Grid Interval (s)"))
        self.timeGridIntervalSB = QtGui.QDoubleSpinBox(self)
        self.timeGridIntervalSB.installEventFilter(self)
        self.EXPL[self.timeGridIntervalSB] = \
            "Horizontal Grid Interval in second"
        self.timeGridIntervalSB.setDecimals(1)
        self.timeGridIntervalSB.setSingleStep(.1)
        self.timeGridIntervalSB.setFixedWidth(80)
        horGridHBox.addWidget(self.timeGridIntervalSB)

        verGridHBox = QtGui.QHBoxLayout()
        gridVBox.addLayout(verGridHBox)
        verGridHBox.addWidget(QtGui.QLabel("Dista. Grid Interval (km)"))
        self.distanceGridIntervalSB = QtGui.QSpinBox(self)
        self.distanceGridIntervalSB.installEventFilter(self)
        self.EXPL[self.distanceGridIntervalSB] = \
            "Vertical Grid Interval in second"
        self.distanceGridIntervalSB.setFixedWidth(80)
        self.distanceGridIntervalSB.setValue(10)
        verGridHBox.addWidget(self.distanceGridIntervalSB)

        self.regridBtn = QtGui.QPushButton('ReGrid', self)
        self.regridBtn.installEventFilter(self)
        self.EXPL[self.regridBtn] = "Apply new grid intervals"
        self.regridBtn.setFixedWidth(70)
        self.regridBtn.setFixedHeight(70)
        self.regridBtn.clicked.connect(self.onRegrid)
        gridHBox.addWidget(self.regridBtn)
        self.regridBtn.setEnabled(False)

        vbox.addStretch(1)
        vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        # ___________________ which channel? ___________________
        channelBox = QtGui.QHBoxLayout()
        vbox.addLayout(channelBox)
        channelBox.addWidget(QtGui.QLabel("Channels"))
        self.channelCkbs = {}
        for ch in range(1, 4):
            self.channelCkbs[ch] = QtGui.QCheckBox(str(ch), self)

            self.channelCkbs[ch].setEnabled(False)
            self.EXPL[self.channelCkbs[ch]] = \
                "Remove/Add this channel to the plot."
            channelBox.addWidget(self.channelCkbs[ch])

        self.changeChanReplotBtn = QtGui.QPushButton('Apply', self)
        self.changeChanReplotBtn.installEventFilter(self)
        self.EXPL[self.changeChanReplotBtn] = "Apply the selected Channels."
        self.changeChanReplotBtn.clicked.connect(self.onChangeChannels)
        self.changeChanReplotBtn.setFixedWidth(60)
        channelBox.addWidget(self.changeChanReplotBtn)

        vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        # __________________ which direction? __________________
        directionBox = QtGui.QHBoxLayout()
        vbox.addLayout(directionBox)
        directionBox.addWidget(QtGui.QLabel("Time Direction"))
        self.downRbtn = QtGui.QRadioButton('Down ')
        self.downRbtn.installEventFilter(self)
        self.EXPL[self.downRbtn] = "Drawing with time grow from " +\
            "top to bottom.\nTake effect right after selected"
        directionBox.addWidget(self.downRbtn)
        self.downRbtn.clicked.connect(self.onChangeDirection)
        self.downRbtn.setChecked(True)

        self.upRbtn = QtGui.QRadioButton('Up   ')
        self.upRbtn.installEventFilter(self)
        self.EXPL[self.upRbtn] = "Drawing with time grow from " +\
            "bottom to top.\nTake effect right after selected"
        directionBox.addWidget(self.upRbtn)
        self.upRbtn.clicked.connect(self.onChangeDirection)

        direction = QtGui.QButtonGroup(self)
        direction.addButton(self.downRbtn)
        direction.addButton(self.upRbtn)

        # ____________________ Drawing Style ____________________
        styleBox = QtGui.QHBoxLayout()
        vbox.addLayout(styleBox)
        styleBox.addWidget(QtGui.QLabel("Drawing Style "))
        self.lineRbtn = QtGui.QRadioButton('Lines')
        self.lineRbtn.installEventFilter(self)
        self.EXPL[self.lineRbtn] = \
            "The style of drawing is line. Take effect right after selected."
        styleBox.addWidget(self.lineRbtn)
        self.lineRbtn.clicked.connect(self.onChangeStyle)
        self.lineRbtn.setChecked(True)

        self.pointRbtn = QtGui.QRadioButton('Points')
        self.pointRbtn.installEventFilter(self)
        self.EXPL[self.pointRbtn] = \
            "The style of drawing is points. Take effect right after selected."
        styleBox.addWidget(self.pointRbtn)
        self.pointRbtn.clicked.connect(self.onChangeStyle)

        styleGroup = QtGui.QButtonGroup(self)
        styleGroup.addButton(self.lineRbtn)
        styleGroup.addButton(self.pointRbtn)

        # ________________________________________________________

        self.getnPlotBtn = QtGui.QPushButton('Get Data and Plot', self)
        self.getnPlotBtn.installEventFilter(self)
        self.EXPL[self.getnPlotBtn] = \
            "Read PH5 data and plot according to all the settings."
        self.getnPlotBtn.setStyleSheet("QWidget { background-color: #d7deff }")
        self.getnPlotBtn.clicked.connect(self.onGetnPlot)
        vbox.addWidget(self.getnPlotBtn)
        # _____________________ showing info ______________________
        formDisplay1 = QtGui.QFormLayout()
        vbox.addLayout(formDisplay1)

        self.sampleNoLbl = QtGui.QLabel("", self)
        formDisplay1.addRow(self.tr('No of Samp./Station:'), self.sampleNoLbl)

        self.intervalLbl = QtGui.QLabel("", self)
        formDisplay1.addRow(self.tr('Sample Interval (ms):'), self.intervalLbl)

        vbox.addStretch(1)

        gridDisplay2 = QtGui.QGridLayout()
        vbox.addLayout(gridDisplay2)
        gridDisplay2.addWidget(QtGui.QLabel("TIME (ms)"), 0, 0)
        self.startTimeLbl = QtGui.QLabel('')
        self.startTimeLbl.installEventFilter(self)
        self.EXPL[self.startTimeLbl] = \
            "Plotting Window's start time in milisecond"
        self.startTimeLbl.setFrameStyle(
            QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.startTimeLbl.setFixedWidth(100)
        gridDisplay2.addWidget(self.startTimeLbl, 0, 1)
        self.endTimeLbl = QtGui.QLabel('')
        self.endTimeLbl.installEventFilter(self)
        self.EXPL[self.endTimeLbl] = "Plotting Window's end time"
        self.endTimeLbl.setFrameStyle(
            QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.endTimeLbl.setFixedWidth(100)
        gridDisplay2.addWidget(self.endTimeLbl, 0, 2)

        gridDisplay2.addWidget(QtGui.QLabel("STATION"), 1, 0)
        self.startStationIdLbl = QtGui.QLabel('')
        self.startStationIdLbl.installEventFilter(self)
        self.EXPL[self.startStationIdLbl] = "Plotting Window's start station"
        self.startStationIdLbl.setFrameStyle(
            QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.startStationIdLbl.setFixedWidth(100)
        gridDisplay2.addWidget(self.startStationIdLbl, 1, 1)
        self.endStationIdLbl = QtGui.QLabel('')
        self.endStationIdLbl.installEventFilter(self)
        self.EXPL[self.endStationIdLbl] = "Plotting Widnow's end station"
        self.endStationIdLbl.setFrameStyle(
            QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.endStationIdLbl.setFixedWidth(100)
        gridDisplay2.addWidget(self.endStationIdLbl, 1, 2)

        gridDisplay2.addWidget(QtGui.QLabel("DISTANCE (km)"), 2, 0)
        self.startDistanceLbl = QtGui.QLabel('')
        self.startDistanceLbl.installEventFilter(self)
        self.EXPL[self.startDistanceLbl] = \
            "Plotting Window's start distance in kilometer"
        self.startDistanceLbl.setFrameStyle(
            QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.startDistanceLbl.setFixedWidth(100)
        gridDisplay2.addWidget(self.startDistanceLbl, 2, 1)
        self.endDistanceLbl = QtGui.QLabel('')
        self.endDistanceLbl.installEventFilter(self)
        self.EXPL[self.endDistanceLbl] = \
            "Plotting Widnow's end distance in kilometer"
        self.endDistanceLbl.setFrameStyle(
            QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.endDistanceLbl.setFixedWidth(100)
        gridDisplay2.addWidget(self.endDistanceLbl, 2, 2)

        vbox.addStretch(1)
        mainbox.addStretch(1)

        scrollArea = QtGui.QScrollArea(self)
        mainbox.addWidget(scrollArea)
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scrollArea.setWidgetResizable(True)

        itemsFrame = QtGui.QFrame()
        scrollArea.setWidget(itemsFrame)
        scrollBox = QtGui.QVBoxLayout()
        itemsFrame.setLayout(scrollBox)
        self.statusLbl = QtGui.QLabel('', self)
        scrollBox.addWidget(self.statusLbl)

        scrollBox.addStretch(1)
        global statusBar
        statusBar = self.statusBar()
        self.setWidgetsEnabled(False)
        self.setAllReplotBtnsEnabled(False, resetCanvas=False)

    ###################################
    # Author: Lan
    # def: eventFilter(): 20151022
    # detect enter event and show explaination for the widget on baloon tooltip
    def eventFilter(self, object, event):
        if self.PH5View.helpEnable and event.type() == QtCore.QEvent.Enter:
            if object not in self.EXPL.keys():
                return False

            P = object.pos()

            QtGui.QToolTip.showText(self.mapToGlobal(
                QtCore.QPoint(P.x(), P.y()+20)), self.EXPL[object])
            return True

        if self.eventId is None:
            return False
        errorMsg = ''
        if object == self.offsetCtrl and event.type() == QtCore.QEvent.Leave:
            try:
                offset = float(self.offsetCtrl.text())
                if offset > 20 or offset < -20:
                    errorMsg = "Offset value should not be greater " + \
                               "than 20 or less than -20"

            except Exception:
                errorMsg = "Offset value must be a number."
            if errorMsg != '':
                QtGui.QMessageBox.question(self, 'Error', errorMsg,
                                           QtGui.QMessageBox.Ok)
                self.offsetCtrl.setText("-0")
        elif object == self.timelenCtrl:
            if event.type() in [QtCore.QEvent.Leave, QtCore.QEvent.FocusOut]:
                errorMsg = self.onChangeTimeLen()
                if errorMsg != '':
                    QtGui.QMessageBox.question(self, 'Error', errorMsg,
                                               QtGui.QMessageBox.Ok)

        return False

    def onChangeTimeLen(self, evt=None):
        errorMsg = ''
        try:
            timeLen = float(self.timelenCtrl.text())
            # add timeLen limit here
            if timeLen > self.upperTimeLen:
                errorMsg = "Time length value must be less than " + \
                           "event's time: %ss" % self.upperTimeLen
                self.timelenCtrl.setText("60")
                if evt is None:
                    return errorMsg
                else:
                    QtGui.QMessageBox.question(self, 'Error', errorMsg,
                                               QtGui.QMessageBox.Ok)

            minInterval = math.ceil(10*timeLen/25)/10
            maxInterval = math.ceil(timeLen*10)/10
            self.timeGridIntervalSB.setRange(minInterval, maxInterval)
            self.timeGridIntervalSB.setValue(math.ceil(timeLen*10/15)/10)

        except Exception:
            if (evt is not None and self.timelenCtrl.text() not in ['', '.']) \
              or evt is None:
                errorMsg = "Time length value must be a number."
                self.timelenCtrl.setText("60")
                if evt is None:
                    return errorMsg
                else:
                    QtGui.QMessageBox.question(self, 'Error', errorMsg,
                                               QtGui.QMessageBox.Ok)

        return ''

    ###################################
    # Author: Lan
    # def: addDisplay2(): updated 201506
    # special layout for View Window info
    def addDisplay2(self, grid, rowId, text, ctrl1, ctrl2):
        grid.addWidget(QtGui.QLabel(text), rowId, 0)

        grid.addWidget(ctrl1, rowId+1, 0)
        ctrl1.setStyleSheet("QWidget { background-color: white }")
        ctrl1.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)

        grid.addWidget(ctrl2, rowId+1, 1)
        ctrl2.setStyleSheet("QWidget { background-color: white }")
        ctrl2.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)

    ###################################
    # Author: Lan
    # def: check(): updated 201509
    # check valid sof start time range
    # check the valid of length of time range: a number>0
    # check valid of distance Offset: a number>0
    # check velocity:
    #  if val>0: apply reduction velocity
    #  if val<=0 or not a number: not apply
    def check(self, checkTRange=False, checkDOffset=False,
              checkVelocity=False):
        errorMsg = ""
        if self.PH5View.submitGui == 'STATION' and checkTRange:
            try:
                self.startTime = timedoy.passcal2epoch(
                    self.startrangetimeCtrl.text())
            except Exception:
                errorMsg += "Start time format is invalid. Correct " + \
                            "your format to:\n\tYYYY:DOY:HH:MM:SS[.MSE]\n"
            try:
                len = float(self.timelenCtrl.text())
                if len <= 0:
                    errorMsg += "Length of TIME RANGE must be " + \
                                "greater than zero.\n"

            except Exception:
                errorMsg += "Length of TIME RANGE must be " + \
                            "a number greater than zero.\n"

        errorMsg += self.onChangeTimeLen()
        if self.stationSpacingUnknownCkb.isChecked() and checkDOffset:
            try:
                dOff = float(self.nominalStaSpace.text())
                if dOff <= 0:
                    errorMsg += "Distance Offset must be greater than zero.\n"

            except Exception:
                errorMsg += "Distance Offset must be " + \
                            "a number greater than zero.\n"

        if checkVelocity:
            try:
                self.vel = float(self.velocityCtrl.text())
                if self.vel <= 0:
                    self.vel = None

            except Exception:
                self.vel = None

        if errorMsg != "":
            QtGui.QMessageBox.question(self, 'Error', errorMsg,
                                       QtGui.QMessageBox.Ok)
            return False
        return True

    ###################################
    # Author: Lan
    # def: onChangeProperties(): updated 201411
    # open Properties window for user to change settings for
    # name, color, line thickness
    def onChangeProperties(self, evt):
        Properties(self).exec_()

    ###################################
    # Author: Lan
    # def: onChangeChannels():
    def onChangeChannels(self, evt):
        if self.PH5Info is None:
            return
        count = 0
        for ch in self.channelCkbs.keys():
            if self.channelCkbs[ch].isChecked():
                count += 1

        if count == 0:
            errorMsg = "There must be at least one channel selected."
            QtGui.QMessageBox.question(self, 'Error', errorMsg,
                                       QtGui.QMessageBox.Ok)
            return

        self.deepRemoveStations()

    ###################################
    # Author: Lan
    # def: onChangeDirection(): updated 201506
    #  => change direction of the display vertically (according to time)
    def onChangeDirection(self, evt):
        self.mainCanvas.timeDirection()
        self.mainCanvas.update()
        self.mainPlot.update()
        self.mainPlot.activateWindow()
        self.supportCanvas.reset()

    ###################################
    # Author: Lan
    # def: onChangeStyle(): updated 201507
    #  => change displaying of the plots to lines or points
    def onChangeStyle(self, evt):
        self.mainCanvas.update()
        self.mainPlot.update()
        self.mainPlot.activateWindow()
        self.supportCanvas.update()
        self.supportPlot.update()

    ###################################
    # Author: Lan
    # def: onChangeApplystationSpacingUnknown(): updated 201509
    #  selected:
    #    + require fake Distance Offset
    #    + applicable for non-normalized mode when all stations
    #      use the same scale
    #  not selected: (always normalize: spread to use all of the value range)
    #    + use real Distance Offset => no need to care about the fake one
    #    + although normalizeCkb is disabled, still need to check that
    #      so user won't be confused
    def onChangeApplyStationSpacingUnknown(self, evt):
        if self.stationSpacingUnknownCkb.isChecked():
            self.nominalStaSpace.setEnabled(True)

        else:
            self.nominalStaSpace.setEnabled(False)

    def onChangeApplyGrids(self, evt):
        self.mainCanvas.update()
        self.mainPlot.activateWindow()
        self.supportCanvas.update()

    ###################################
    # Author: Lan
    # def: onRegrid(): updated 201507
    # regrid so that the current view have "gridLineNo" of lines
    # The affected panel decided by mainWindowRbtn or supportWindowRbtn
    def onRegrid(self):

        if self.mainWindowRbtn.isChecked():
            self._regrid(self.mainCanvas, self.mainPlot)
        elif self.supportWindowRbtn.isChecked():
            self._regrid(self.supportCanvas, self.supportPlot)
        else:
            self._regrid(self.mainCanvas, self.mainPlot)
            self._regrid(self.supportCanvas, self.supportPlot)

    def _regrid(self, canvas, plot):
        if not canvas.enableDrawing:
            return
        canvas.gtData, canvas.gdData, canvas.timeY, \
            canvas.tLabels, canvas.dLabels = canvas.buildGrid()
        canvas.feedGData(canvas.panT, canvas.panV,
                         canvas.canvScaleT, canvas.canvScaleV)
        canvas.labelPos = canvas.resiteLabels()
        canvas.update()
        plot.update()
        plot.activateWindow()

    ###################################
    # Author: Lan
    # def: onGetnPlot(): updated 201509
    #  => building 2 members of data: val, time
    #  => Send data to canvas to draw
    def onGetnPlot(self, evt):
        if not self.check(checkTRange=True, checkDOffset=True,
                          checkVelocity=True):
            return

        count = 0
        for ch in self.channelCkbs.keys():
            if self.channelCkbs[ch].isChecked():
                count += 1

        if count == 0:
            errorMsg = "There is must be at least one channel selected."
            QtGui.QMessageBox.question(self, 'Error', errorMsg,
                                       QtGui.QMessageBox.Ok)
            return

        self.reset()
        global START, processInfo
        START = time.time()
        showStatus('', 'Starting - set status of menu')

        processInfo = WARNINGMSG
        self.statusLbl.setText(processInfo)

        val = self.createVal()
        if not val:
            return
        t = self.createTime(val)
        self.mainCanvas.initData(t=t, val=val)

        self.mainPlot.activateWindow()
        self.supportCanvas.reset()

        self.PH5View.saveMenu.setEnabled(True)
        self.PH5View.printMenu.setEnabled(True)
        self.PH5View.saveSAction.setEnabled(False)
        self.PH5View.saveSZAction.setEnabled(False)
        self.PH5View.printSAction.setEnabled(False)
        self.PH5View.printSAction.setEnabled(False)
        self.PH5View.saveMAction.setEnabled(True)
        self.PH5View.saveMZAction.setEnabled(True)
        self.PH5View.printMAction.setEnabled(True)
        self.PH5View.printMZAction.setEnabled(True)

        self.downRbtn.setEnabled(True)
        self.upRbtn.setEnabled(True)
        self.setAllReplotBtnsEnabled(True)
        self.mainPlot.setEnabled(True)

    ###################################
    # Author: Lan
    # def: onApplyPropperty_RePlot(): updated 201507
    # no need to do anything with time and data
    # call initData() to apply new properties to the graphic
    def onApplyPropperty_RePlot(self):
        global START
        START = time.time()
        self.mainCanvas.initData()
        self.mainPlot.activateWindow()
        self.supportCanvas.reset()

    ###################################
    # Author: Lan
    # def: onApplySimplify_RePlot(): updated 201509
    # simplify affect keepList
    #   -> recalc both val and time, but don't need to reread PH5data
    def onApplySimplify_RePlot(self, event):
        global START
        START = time.time()

        val = self.createVal(createFromBeg=False, appNewSimpFactor=True)
        if not val:
            return
        t = self.createTime(val)

        self.mainCanvas.initData(val=val, t=t)
        self.mainPlot.activateWindow()
        self.supportCanvas.reset()

    ###################################
    # Author: Lan
    # def: onApplyOverlap_RePlot(): updated 201509
    # overlap affect val only => don't need to reread PH5 data or recalc time
    def onApplyOverlapNormalize_RePlot(self, event):
        global START
        START = time.time()
        self.downRbtn.setEnabled(True)
        self.upRbtn.setEnabled(True)

        val = self.createVal(createFromBeg=False)
        if not val:
            return

        self.mainCanvas.initData(val=val)
        self.mainPlot.activateWindow()

    ###################################
    # Author: Lan
    # def: createTime():201506
    # create time array
    #  => time is at first created evenly for each station
    #  => then changed according to correction and
    #     velocity reduction of each station
    #  => scale to range (-1,1)
    #  => only keep the time index in the self.keepList
    def createTime(self, val):
        global processInfo
        start = time.time()
        samNo = self.PH5Info['numOfSamples']

        t = np.linspace(0+self.offset*1000, (samNo-1) *
                        self.PH5Info['interval']+self.offset*1000, samNo)

        self.minT = t.min()
        self.maxT = t.max()
        self.totalTime = abs(self.maxT - self.minT)
        self.scaleT = 2/(self.maxT-self.minT)
        self.zeroT = - self.minT*self.scaleT - 1

        t -= self.minT

        t *= self.scaleT

        t -= 1

        end = time.time()
        showStatus('Step 4 took %s seconds. Next: 5/%s' %
                   (end-start, totalSteps), "Plotting")
        processInfo += "\nCreate Time value: %s seconds" % (end-start)
        self.statusLbl.setText(processInfo)

        return t

    ###################################
    # Author: Lan
    # def: getKeepList():201504
    # modified: 201508
    # create the list of indexes of values
    #   that the program can ignore when drawing
    # build the list of values for each station that are:
    #   + greater than the simpFactor*abs(ymax-ymean)
    #   + the peeks only (this takes too much time
    #     => look in old file if needed)
    #   + the start and end time of each station
    def getKeepList(self, val, simplFactor):
        keepList = {}

        if simplFactor == 0:
            for ch in self.channels:
                keepList[ch] = []
                staNo = len(val[ch])
                for i in range(staNo):
                    keepList[ch].append(range(len(val[ch][i])))
            return keepList

        for ch in self.channels:
            keepList[ch] = []
            staNo = len(val[ch])
            for i in range(staNo):
                samNo = self.PH5Info['LEN'][ch][i]
                if i in self.PH5Info['deepRemoved'][ch] or samNo == 0:
                    keepList[ch].append([])
                    continue

                # remove center
                V = val[ch][i][:samNo]
                a = np.where(abs(V-V.mean()) > abs(V.max()-V.mean())
                             * simplFactor)[0]
                o = []
                d = V
                # phase value 1:increasing; -1: decreasing
                phase = 0
                for k in range(len(a)):
                    try:
                        # increasing
                        if d[a[k]] <= d[a[k+1]]:
                            # end of avg or decreasing
                            if phase == 1:
                                o.append(k)
                            phase = 1
                        # decreasing
                        elif d[a[i]] >= d[a[k+1]]:
                            # end of avg or increasing
                            if phase == -1:
                                o.append(k)
                            phase = -1
                    except IndexError:
                        break

                a = np.delete(a, o).tolist()

                if 0 not in a:
                    a.insert(0, 0)

                if samNo-1 not in a:
                    a.append(samNo-1)
                keepList[ch].append(a)

                if i == staNo-1:
                    break

        return keepList

    ###################################
    # Author: Lan
    # def: getPH5Data():
    # updated: 201803
    #  => read PH5 data and metadata
    def getPH5Data(self, orgStartT, offset, timeLen, staSpc):
        # create PH5Object
        PH5Object = ph5_viewer_reader.PH5Reader()
        # initiate PH5Object with filename
        try:
            PH5Object.initialize_ph5(self.PH5View.fname)
        except ph5_viewer_reader.PH5ReaderError, e:
            msg = e.message + \
                  "\nPlease choose another dataset (ph5 file) to view."
            QtGui.QMessageBox.warning(self, "No Das_t", msg)
            return False

        PH5Object.set(self.channels,
                      ['Array_t_' + self.PH5View.selectedArray['arrayId']])
        # read trunk of data
        try:
            if self.gather == 'shot':
                self.PH5Info = PH5Object.readData_shotGather(
                    orgStartT, offset, timeLen, staSpc,
                    self.correctionCkb.isChecked(),
                    self.vel, self.PH5View, statusBar, statusMsg)
            elif self.gather == 'receiver':
                self.PH5Info = PH5Object.readData_receiverGather(
                    orgStartT, offset, timeLen, staSpc,
                    self.correctionCkb.isChecked(),
                    self.vel, self.PH5View, statusBar, statusMsg)
            elif self.gather == 'event_loi':
                self.PH5Info = PH5Object.readData_loiEvent(
                    orgStartT, offset, timeLen, staSpc,
                    self.correctionCkb.isChecked(),
                    self.vel, self.PH5View, statusBar, statusMsg)
        except TypeError:
            msg = "There is no data in the time window selected." + \
                  "\nPlease check Start time, Length and Offset entered."
            QtGui.QMessageBox.warning(self, 'Error', msg)
            return False
        """
        except Exception, e:
            print e
            msg = "There must be something wrong in processing the data.\n" + \
                  "Please try again"
            if e.message=="NoDOffset":
                msg = "The PH5 metadata has no distance offset.\n" + \
                      "Please select the station spacing unknown " + \
                      "for processing the data."
            QtGui.QMessageBox.question(self, 'Error', msg,
                                       QtGui.QMessageBox.Ok)
            return False
        """

        showStatus("1/5:Getting PH5Data - ", "copy metadata")
        self.metadata = deepcopy(PH5Object.metadata)
        # convert list to numpy array => check to see
        # if can create numpy array from creating section ??????????????
        y = PH5Object.data

        showStatus("1/5:Getting PH5Data - ",
                   "save PH5 data to file to use in replotting")

        self.PH5Info['LEN']
        for chId in range(len(self.channels)):
            PH5Val = np.array(y[self.channels[chId]]).ravel()
            # to show all data in np.array
            # np.set_printoptions(threshold=np.nan)
            # try :
            ph5Valfile = np.memmap(PH5VALFILES[chId], dtype='float32',
                                   mode='w+', shape=(1, PH5Val.size))
            ph5Valfile[:] = PH5Val[:]
            del ph5Valfile
            # except :
            #   pass

        if self.PH5Info['noDataList'] != []:
            msg = "The following items have no data return:\n" + \
                  "\n".join(self.PH5Info['noDataList'])
            if len(self.PH5Info['noDataList']) <= 50:
                QtGui.QMessageBox.question(self, 'Information', msg,
                                           QtGui.QMessageBox.Ok)
            else:
                ScrollDialog(title='Information',
                             header="The following items have no data return:",
                             txt=msg).exec_()

        # close all files opened for PH5Object
        PH5Object.ph5close()
        showStatus("1/5:Getting PH5Data - ",
                   "delete PH5Object to save resources")
        # delete PH5Object to save memory
        del PH5Object
        gc.collect()
        return y

###################################
# Author: Lan
# def: createVal():201506
# Create val file with the following steps:
#  + read PH5 data
#  + calc. data with the required properties: nomalized, overlaping, velocity
#  + calc. center and scaling for each station so that the plot can
#     span maximizedly on its room
#  + include the overlaping in calculating center
    def createVal(self, createFromBeg=True, appNewSimpFactor=False):

        global processInfo
        start = time.time()
        showStatus('1/%s' % totalSteps, 'Getting PH5Data ')
        if self.timelenCtrl.text() == '':
            QtGui.QMessageBox.question(
                self, 'Error',
                "Length of time box is empty. You must enter a valid value" +
                " for length of time",
                QtGui.QMessageBox.Ok)

        overlap = self.overlapSB.value() / 100.0
        if createFromBeg:
            # shot gather + non-event
            if self.PH5View.submitGui in ['STATION', 'EVENT_LOI']:
                orgStartT = float(timedoy.passcal2epoch
                                  (self.startrangetimeCtrl.text()))
            elif self.PH5View.submitGui == 'EVENT':  # receiver gather
                orgStartT = None
            else:
                print "Error in MainControl.createVal " + \
                    "self.PH5View.submitGui ='%s'" % self.PH5View.submitGui

            self.dfltOffset = self.offset = float(self.offsetCtrl.text())
            self.dfltTimeLen = float(self.timelenCtrl.text())

            if self.stationSpacingUnknownCkb.isChecked():
                staSpc = float(self.nominalStaSpace.text())
            else:
                staSpc = None

            val = self.getPH5Data(orgStartT, self.offset,
                                  self.dfltTimeLen, staSpc)

            if not val:
                return False
            if val == {}:
                msg = "In the selected range of time: " + \
                    "\n + There is no station belong to " + \
                    "the selected array(s)." + \
                    "\n + OR The selected array and " + \
                    "the selected event aren't match."
                QtGui.QMessageBox.question(self, 'Error', msg,
                                           QtGui.QMessageBox.Ok)
                return False

            try:
                self.PH5Info['velocity'] = int(self.velocityCtrl.text())
            except ValueError:
                pass

        else:
            val = {}
            for chId in range(len(self.channels)):
                val[self.channels[chId]] = \
                    np.memmap(PH5VALFILES[chId], dtype='float32', mode='r',
                              shape=(self.PH5Info['numOfStations'],
                              self.PH5Info['numOfSamples']))

        self.PH5Info['overlap'] = overlap
        staNo = self.PH5Info['numOfStations']

        self.processData()

        end = time.time()
        processInfo += "\nGetting PH5Data: %s seconds" % (end-start)
        self.statusLbl.setText(processInfo)
        showStatus('Step 1 took %s seconds. Next: 2/%s - Getting keep list'
                   % (end-start, totalSteps), "Calculating ")

        start = time.time()
        if appNewSimpFactor or createFromBeg:
            simplFactor = self.distance2AvgSB.value()/100.
            self.keepList = self.getKeepList(val, simplFactor)

        end = time.time()
        processInfo += "\nGetting keep list: %s seconds" % (end-start)
        self.statusLbl.setText(processInfo)
        showStatus('Step 2 took %s seconds. Next: 3/%s - Prepare drawing data'
                   % (end-start, totalSteps), "Calculating ")

        start = time.time()
        # self.ph5val = []    # for double-check

        # lastEnd = 0

        if self.PH5Info['numOfDataStations'] > 1:
            # need to subtract 1 because each offset is
            # only the center of each plot, not the min side or max side
            sizeV4aplot = self.PH5Info['sumD'] / \
                (self.PH5Info['numOfDataStations'] - 1) / (1-overlap)
        elif self.PH5Info['numOfDataStations'] == 1:
            self.totalSize = sizeV4aplot = 1000.

        # signal is drawn on 2 sides of each distanceOffset
        # => at the start and end, add half of a sizeV4aPlot
        self.minD = self.PH5Info['minOffset'] - sizeV4aplot/2.

        if self.PH5Info['numOfDataStations'] > 1:
            self.totalSize = self.PH5Info['sumD'] + sizeV4aplot

        self.scaledMinD = self.minD/self.totalSize

        self.distanceGridIntervalSB.setRange(int(self.totalSize/(1000*50)),
                                             int(self.totalSize/1000))
        scaledSizeV4aplot = sizeV4aplot/self.totalSize

        self.scaleVList = []
        if not self.normalizeCkb.isChecked():
            maxP2Plist = []
            for ch in self.channels:
                try:
                    maxP2Plist.append(
                        max([abs(m['minmax'][0] - m['minmax'][1])
                            for m in self.metadata
                            if m is not None and
                            self.PH5Info['LEN'][ch]
                            [self.metadata.index(m)] != 0
                            and self.metadata.index(m)
                            not in self.PH5Info['deepRemoved'][ch]]))
                except ValueError:
                    pass

            maxP2P = max(maxP2Plist)

            self.scaleVList = [scaledSizeV4aplot/float(maxP2P)] * \
                self.PH5Info['numOfStations']

        PH5Val = {}
        self.statLimitList = np.zeros((staNo, 2))

        for ch in self.channels:
            PH5Val[ch] = []
        zeroList = []
        for i in range(len(self.metadata)):
            # when no data for that station, metadata will not be created
            if self.metadata[i] is None:
                self.scaleVList.append(1)  # not used. just add to keep index
                zeroList.append(0)         # not used. just add to keep index
                continue
            if self.normalizeCkb.isChecked():
                # difference bw min and max (peak to peak)
                p2p = abs(self.metadata[i]['minmax'][1] -
                          self.metadata[i]['minmax'][0])
                # scale of a value of this plot over d
                self.scaleVList.append(scaledSizeV4aplot / float(p2p))

            centerPos = self.PH5Info['distanceOffset'][i] - self.minD

            self.statLimitList[i][:] = \
                [(centerPos - sizeV4aplot/2.)/self.totalSize,
                 (centerPos + sizeV4aplot/2.)/self.totalSize]

            centerVal = \
                (self.metadata[i]['minmax'][1]+self.metadata[i]['minmax'][0])/2
            zeroList.append(
                self.statLimitList[i].mean() - centerVal * self.scaleVList[i])

        self.maxVal = self.statLimitList.max()

        for ch in self.channels:
            for i in range(len(self.metadata)):
                if self.metadata[i] is None:
                    PH5Val[ch].append([])
                    continue

                # (i,ch) in self.PH5Info['zerosList']
                if i in self.PH5Info['deepRemoved'][ch] \
                        or self.PH5Info['LEN'][ch][i] == 0:
                    PH5Val[ch].append([])
                    continue
                else:
                    if self.distance2AvgSB.value() > 0:
                        PH5Val[ch].append(val[ch][i][self.keepList[ch][i]])

                    else:
                        # for double-check
                        # self.ph5val.append(val[i][self.keepList[i]])
                        PH5Val[ch].append(val[ch][i])

                if i % 10 == 0:
                    showStatus("Step3: Prepare drawing data",
                               "%s/%s" % (i, len(val[ch])))
                PH5Val[ch][i] = PH5Val[ch][i]*self.scaleVList[i] + zeroList[i]

        end = time.time()
        showStatus('Step 3 took %s seconds. Next: 4/%s' %
                   (end-start, totalSteps), "Create Time value")
        processInfo += "\nPrepare drawing data: %s seconds" % (end-start)
        self.statusLbl.setText(processInfo)
        return PH5Val

    ###################################
    # Author: Lan
    # def: processData():201410
    # set info get from data onto the GUI
    # inform user the maximum of time for this time range
    def processData(self):
        global processInfo

        self.sampleNoLbl.setText("%s" % self.PH5Info['numOfSamples'])
        self.intervalLbl.setText("%s" % self.PH5Info['interval'])
        realRange = self.PH5Info['numOfSamples']*self.PH5Info['interval']/1000

        if realRange < float(self.timelenCtrl.text()):
            msg = "\nMaximum length of time has been read " + \
                "\nfor this time range is %s" % realRange

            self.timelenCtrl.setText(str(realRange))
            processInfo += msg
            print processInfo
            self.statusLbl.setText(msg)

###################################
# Author: Lan
# def: deepRemoveStations():201410
    def deepRemoveStations(self):
        global START, processInfo
        START = time.time()
        showStatus('', 'Starting - set status of menu')

        processInfo = WARNINGMSG
        self.statusLbl.setText(processInfo)

        val = self.createVal(createFromBeg=False, appNewSimpFactor=False)
        if not val:
            return
        t = self.createTime(val)
        self.mainCanvas.initData(t=t, val=val, deepRemoving=True)

        self.mainPlot.activateWindow()
        self.supportCanvas.reset()

        self.PH5View.saveMenu.setEnabled(True)
        self.PH5View.printMenu.setEnabled(True)
        self.PH5View.saveSAction.setEnabled(False)
        self.PH5View.saveSZAction.setEnabled(False)
        self.PH5View.printSAction.setEnabled(False)
        self.PH5View.printSAction.setEnabled(False)
        self.PH5View.saveMAction.setEnabled(True)
        self.PH5View.saveMZAction.setEnabled(True)
        self.PH5View.printMAction.setEnabled(True)
        self.PH5View.printMZAction.setEnabled(True)

        self.downRbtn.setEnabled(True)
        self.upRbtn.setEnabled(True)
        self.setAllReplotBtnsEnabled(True)
        self.mainPlot.setEnabled(True)

    ###################################
    # Author: Lan
    # def: setRealTime():201410
    def setRealTime(self, t, ctrl):
        realT = t/1000.0 + self.startTime
        ctrl.setText(timedoy.epoch2passcal(realT))

    ###################################
    # Author: Lan
    # def: setWidgetsEnabled():201410
    def setWidgetsEnabled(self, state):

        self.PH5View.segyAction.setEnabled(state)
        self.getnPlotBtn.setEnabled(state)

        self.startrangetimeCtrl.setEnabled(state)
        self.offsetCtrl.setEnabled(state)
        self.timelenCtrl.setEnabled(state)

        self.upRbtn.setEnabled(state)
        self.downRbtn.setEnabled(state)
        self.lineRbtn.setEnabled(state)
        self.pointRbtn.setEnabled(state)

        self.defaultPropRbtn.setEnabled(state)
        self.fromFilePropRbtn.setEnabled(state)
        self.changePropBtn.setEnabled(state)

        self.correctionCkb.setEnabled(state)
        self.overlapSB.setEnabled(state)
        self.stationSpacingUnknownCkb.setEnabled(state)
        self.normalizeCkb.setEnabled(state)

        self.velocityCtrl.setEnabled(state)

        self.distanceGridCkb.setEnabled(state)
        self.timeGridCkb.setEnabled(state)
        self.timeGridIntervalSB.setEnabled(state)
        self.distanceGridIntervalSB.setEnabled(state)
        self.mainWindowRbtn.setEnabled(state)
        self.supportWindowRbtn.setEnabled(state)
        self.bothWindowRbtn.setEnabled(state)

        self.distance2AvgSB.setEnabled(state)

        if self.stationSpacingUnknownCkb.isChecked():
            self.nominalStaSpace.setEnabled(state)
        else:
            self.nominalStaSpace.setEnabled(False)

        if self.channels is not None:
            for ch in range(1, 4):
                if ch in self.channels:
                    self.channelCkbs[ch].setEnabled(state)
                    self.channelCkbs[ch].setChecked(state)

    ###################################
    # Author: Lan
    # def: setAllReplotBtnsEnabled():201410
    def setAllReplotBtnsEnabled(self, state, resetCanvas=True):
        self.simplifyReplotBtn.setEnabled(state)
        self.propReplotBtn.setEnabled(state)
        self.overlapReplotBtn.setEnabled(state)
        self.normalizeReplotBtn.setEnabled(state)
        self.changeChanReplotBtn.setEnabled(state)
        if resetCanvas and not state:
            self.mainCanvas.reset()
            self.supportCanvas.reset()
        if resetCanvas:
            self.regridBtn.setEnabled(state)

        """
        self.upRbtn.setEnabled(state)
        self.downRbtn.setEnabled(state)
        self.lineRbtn.setEnabled(state)
        self.pointRbtn.setEnabled(state)
        """


"""
____________________ CLASS ___________________
Author: Lan
Updated: 201410
CLASS: Properties -
the following properties can be set for the Graphic
    . display color on plots according the color pattern
    . display axis color
    . horizontal/vertical labels
    . Graphic name - title of the panel
"""


class Properties(QtGui.QDialog):
    def __init__(self, parent):
        self.parent = parent
        self.initUI()

    def initUI(self):
        QtGui.QDialog.__init__(self)
        self.setWindowTitle('Properties')
        mainbox = QtGui.QVBoxLayout(self)
        self.EXPL = EXPL = {}
        self.helpEnable = False

        grid = QtGui.QGridLayout()
        mainbox.addLayout(grid)
        grid.setSpacing(10)
        cancelBtn = QtGui.QPushButton('Cancel', self)
        cancelBtn.installEventFilter(self)
        EXPL[cancelBtn] = "Cancel any edition and exit Properties Window"
        cancelBtn.clicked.connect(self.onCancel)
        cancelBtn.resize(cancelBtn.sizeHint())
        grid.addWidget(cancelBtn, 0, 0)

        helpBtn = QtGui.QPushButton('Help', self)
        helpBtn.clicked.connect(self.onHelp)
        grid.addWidget(helpBtn, 0, 1)

        saveBtn = QtGui.QPushButton('Apply', self)
        saveBtn.installEventFilter(self)
        EXPL[saveBtn] = \
            "Save all properties to file to use for next time.\n" + \
            "Apply the properties to new plotting if keeping " + \
            "selecting Prevous Prop. in the Control Window." + \
            "Exit Properties Window"
        saveBtn.clicked.connect(self.onApply)
        saveBtn.resize(saveBtn.sizeHint())
        grid.addWidget(saveBtn, 0, 2)

        # only one radio button in the group can be set
        setting_group = QtGui.QButtonGroup(self)

        grid.addWidget(QtGui.QLabel("SETTING", self),
                       1, 0, QtCore.Qt.AlignHCenter)

        self.defaultRbtn = defaultRbtn = QtGui.QRadioButton("Default")
        self.defaultRbtn.installEventFilter(self)
        EXPL[self.defaultRbtn] = \
            "Show all default properties so that user can " + \
            "continue to edit from these"
        defaultRbtn.toggled.connect(self.selectConf)
        setting_group.addButton(defaultRbtn)
        grid.addWidget(defaultRbtn, 1, 1)

        self.previousRbtn = previousRbtn = QtGui.QRadioButton("Previous")
        self.previousRbtn.installEventFilter(self)
        EXPL[self.previousRbtn] = "Show all previously saved properties " + \
            "so that user can continue to edit from these"
        setting_group.addButton(previousRbtn)
        previousRbtn.toggled.connect(self.selectConf)
        grid.addWidget(previousRbtn, 1, 2)

        propertiesPanel = QtGui.QWidget()
        mainbox.addWidget(propertiesPanel)
        propertiesHbox = QtGui.QHBoxLayout(propertiesPanel)
        propertiesGrid = QtGui.QGridLayout()
        propertiesGrid.setSpacing(10)
        propertiesHbox.addLayout(propertiesGrid)

        propertiesGrid.addWidget(
            QtGui.QLabel("AddingInfo to GraphicName", propertiesPanel),
            0, 0, QtCore.Qt.AlignRight)
        self.addingInfoText = QtGui.QLineEdit(propertiesPanel)
        self.addingInfoText.installEventFilter(self)
        EXPL[self.addingInfoText] = "Adding info to the name of the drawing"
        self.addingInfoText.setFixedWidth(180)
        propertiesGrid.addWidget(self.addingInfoText, 0, 1)

        propertiesGrid.addWidget(
            QtGui.QLabel("Horizontal Label", propertiesPanel),
            2, 0, QtCore.Qt.AlignRight)
        self.hLabelText = QtGui.QLineEdit(propertiesPanel)
        self.hLabelText.installEventFilter(self)
        EXPL[self.hLabelText] = "Name of the horizontal axis"
        propertiesGrid.addWidget(self.hLabelText, 2, 1)

        propertiesGrid.addWidget(
            QtGui.QLabel("Vertical Label", propertiesPanel),
            3, 0, QtCore.Qt.AlignRight)
        self.vLabelText = QtGui.QLineEdit(propertiesPanel)
        self.vLabelText.installEventFilter(self)
        EXPL[self.vLabelText] = "Name of the vertical axis"
        propertiesGrid.addWidget(self.vLabelText, 3, 1)

        propertiesGrid.addWidget(
            QtGui.QLabel("Pattern Size", propertiesPanel),
            4, 0, QtCore.Qt.AlignRight)
        self.patternSizeText = QtGui.QLineEdit(propertiesPanel)
        self.patternSizeText.installEventFilter(self)
        EXPL[self.patternSizeText] = "Number of stations in one pattern. " + \
            "These pattern color will be repeated through the plotting"
        propertiesGrid.addWidget(self.patternSizeText, 4, 1)

        self.updateBtn = QtGui.QPushButton('Update', propertiesPanel)
        self.updateBtn.installEventFilter(self)
        EXPL[self.updateBtn] = "Change the number of color buttons " + \
            "in the pattern color panel on the right"
        self.updateBtn.clicked.connect(self.onUpdate)
        self.updateBtn.resize(self.updateBtn.sizeHint())
        propertiesGrid.addWidget(self.updateBtn, 4, 2)

        propertiesGrid.addWidget(
            QtGui.QLabel("Trace Thickness", propertiesPanel),
            5, 0, QtCore.Qt.AlignRight)
        self.plotThickText = QtGui.QLineEdit(propertiesPanel)
        self.plotThickText.installEventFilter(self)
        EXPL[self.plotThickText] = \
            "Adjust the thickness of traces in Saved/Printed Graphic"
        propertiesGrid.addWidget(self.plotThickText, 5, 1)

        propertiesGrid.addWidget(
            QtGui.QLabel("Grid Thickness", propertiesPanel),
            7, 0, QtCore.Qt.AlignRight)
        self.gridThickText = QtGui.QLineEdit(propertiesPanel)
        self.gridThickText.installEventFilter(self)
        EXPL[self.gridThickText] = \
            "Adjust the thickness of grids in Saved/Printed Graphic"
        propertiesGrid.addWidget(self.gridThickText, 7, 1)
        self.gridColBtn = QtGui.QPushButton('Color', propertiesPanel)
        self.gridColBtn.installEventFilter(self)
        EXPL[self.gridColBtn] = "Change color of grid line"
        self.gridColBtn.clicked.connect(self.onChangeColor)
        self.gridColBtn.resize(10, 10)
        propertiesGrid.addWidget(self.gridColBtn, 7, 2)

        propertiesGrid.addWidget(
            QtGui.QLabel("Abnormal Station(s)", propertiesPanel),
            8, 0, QtCore.Qt.AlignRight)
        self.showAbnormalStatCkb = QtGui.QCheckBox('', self)
        self.showAbnormalStatCkb.installEventFilter(self)
        self.EXPL[self.showAbnormalStatCkb] = \
            "If selected, the station(s) with abnormal offset's growth " + \
            "will be shown in this color."
        self.showAbnormalStatCkb.setCheckState(QtCore.Qt.Checked)
        propertiesGrid.addWidget(self.showAbnormalStatCkb, 8, 1)
        self.abnormalColBtn = QtGui.QPushButton('Color', propertiesPanel)
        self.abnormalColBtn.installEventFilter(self)
        EXPL[self.abnormalColBtn] = \
            "Change color of station with abnormal distance offset"
        self.abnormalColBtn.clicked.connect(self.onChangeColor)
        self.abnormalColBtn.resize(10, 10)
        propertiesGrid.addWidget(self.abnormalColBtn, 8, 2)

        colorVBox = QtGui.QVBoxLayout()
        propertiesHbox.addLayout(colorVBox)

        colorVBox.addWidget(QtGui.QLabel("Pattern Colors"))

        colorAllHBox = QtGui.QHBoxLayout()
        colorVBox.addLayout(colorAllHBox)
        colorAllHBox.addSpacing(10)
        self.allColorBtns = []
        for i in range(len(self.parent.channels)):
            self.allColorBtns.append(QtGui.QPushButton('All', propertiesPanel))
            self.allColorBtns[-1].setFixedWidth(50)
            self.allColorBtns[-1].clicked.connect(self.onAllColorBtns)
            colorAllHBox.addWidget(self.allColorBtns[-1])
        colorAllHBox.addStretch(1)

        scrollArea = QtGui.QScrollArea(self)
        colorVBox.addWidget(scrollArea)
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scrollArea.setWidgetResizable(True)

        self.patternColorPanel = QtGui.QWidget()
        self.patternColorPanel.installEventFilter(self)
        EXPL[self.patternColorPanel] = \
            "Click to the buttons corresponding to the plot lines of " + \
            "which colors you want to change."
        main_patternColorHBox = QtGui.QHBoxLayout(self.patternColorPanel)

        scrollArea.setWidget(self.patternColorPanel)

        self.patternColorVBoxes = []
        for i in range(len(self.parent.channels)):
            self.patternColorVBoxes.append(QtGui.QVBoxLayout())
            self.patternColorVBoxes[i].addStretch(1)
            main_patternColorHBox.addLayout(self.patternColorVBoxes[i])

        self.plotColBtns = []

        main_patternColorHBox.addStretch(1)

        self.resize(700, 600)

        if self.parent.defaultPropRbtn.isChecked():
            defaultRbtn.setChecked(True)
        else:
            previousRbtn.setChecked(True)

    ###################################
    def onHelp(self, evt):
        self.helpEnable = not self.helpEnable

        if self.helpEnable:
            cursor = QtGui.QCursor(QtCore.Qt.WhatsThisCursor)
        else:
            cursor = QtGui.QCursor(QtCore.Qt.ArrowCursor)

        self.setCursor(cursor)

    ###################################
    # Author: Lan
    # def: eventFilter(): 20151022
    # using baloon tooltip to help user understand the use of the widget
    #   (only the one install event filter)
    def eventFilter(self, object, event):
        if not self.helpEnable:
            return False
        if event.type() == QtCore.QEvent.Enter:
            if object not in self.EXPL.keys():
                return False
            P = object.pos()
            QtGui.QToolTip.showText(
                self.mapToGlobal(
                    QtCore.QPoint(P.x(), P.y()+20)), self.EXPL[object])
            return True
        return False

    def onCancel(self, evt):
        self.close()

    ###################################
    # Author: Lan
    # def: onApply():201410
    # save info from GUI to parent.conf
    # call saveConfFile() to save that info to file
    # set plot.plottingPanel.clear=true to not start painting
    # on panel right away
    # set the data for plot
    def onApply(self, evt):
        self.parent.fileConf['addingInfo'] = self.addingInfoText.text()
        self.parent.fileConf['hLabel'] = self.hLabelText.text()
        self.parent.fileConf['vLabel'] = self.vLabelText.text()
        self.parent.fileConf['showAbnormalStat'] = \
            self.showAbnormalStatCkb.isChecked()
        errorItm = None
        try:
            self.parent.fileConf['patternSize'] = \
                int(self.patternSizeText.text())
        except ValueError:
            errorItm = "Pattern Size"
            expectType = "an integer"

        try:
            self.parent.fileConf['plotThick'] = \
                float(self.plotThickText.text())
        except ValueError:
            errorItm = "Trace Thickness"
            expectType = "a float"

        try:
            self.parent.fileConf['gridThick'] = \
                float(self.gridThickText.text())
        except ValueError:
            errorItm = "Grid Thickness"
            expectType = "a float"

        if errorItm is not None:
            errorMsg = "%s must be %s number" % (errorItm, expectType)
            QtGui.QMessageBox.question(
                self, 'Error', errorMsg, QtGui.QMessageBox.Ok)
            return

        self.parent.fileConf['gridColor'] = \
            self.gridColBtn.palette().color(1).name()
        self.parent.fileConf['abnormalColor'] = \
            self.abnormalColBtn.palette().color(1).name()

        self.parent.fileConf['plotColor'] = []
        for ch in range(len(self.parent.channels)):
            self.parent.fileConf['plotColor'].append([])
            for cb in self.plotColBtns[ch]:
                self.parent.fileConf['plotColor'][ch].append(
                    cb.palette().color(1).name())

        saveConfFile(self.parent.fileConf)
        self.parent.fromFilePropRbtn.setChecked(True)
        self.parent.onChangePropertyType()
        self.close()

    ###################################
    # Author: Lan
    # def: onAllColorBtns():201707
    # allColorBtns allow to set all the buttons in the channel's column
    # to the "All" button's color
    # (allColorBtns are set to the color of the first button in that channel)
    def onAllColorBtns(self, evt):
        col = QtGui.QColorDialog.getColor()
        if col.isValid():
            self.sender().setStyleSheet(
              "QWidget { background-color: %s }" % col.name())

        ch = self.allColorBtns.index(self.sender())
        for bIndex in range(len(self.plotColBtns[ch])):
            self.plotColBtns[ch][bIndex].setStyleSheet(
              "QWidget { background-color: %s }" % col.name())
            self.conf['plotColor'][ch][bIndex] = str(col.name())

    ###################################
    # Author: Lan
    # def: onChangeColor():201409
    # when click on the button,
    # pop-up QColorDialog for user to select one color,
    # change color of the button to the selected color
    def onChangeColor(self, evt):
        col = QtGui.QColorDialog.getColor()
        if col.isValid():
            self.sender().setStyleSheet(
              "QWidget { background-color: %s }" % col.name())

        for ch in range(len(self.plotColBtns)):
            if self.sender() in self.plotColBtns[ch]:
                bIndex = self.plotColBtns[ch].index(self.sender())
                self.conf['plotColor'][ch][bIndex] = str(col.name())
                if bIndex == 0:
                    """
                    allColorBtns are set to the color of the first button
                    in that channel. So when the first button's color is
                    changed, the allColorBtns for that channel
                    should be changed
                    """
                    self.allColorBtns[ch].setStyleSheet(
                      "QWidget { background-color: %s }" % col.name())

    ###################################
    # Author: Lan
    # def: defaultChoice():201410
    # select default => use defaultConf created from PH5Visualizer
    def selectConf(self, evt):
        if self.defaultRbtn.isChecked():
            self.conf = deepcopy(self.parent.defaultConf)
        else:
            self.conf = deepcopy(self.parent.fileConf)
        self.setConf()

    ###################################
    # Author: Lan
    # def: setConf():201409
    # set info from self.conf onto GUI
    def setConf(self):
        if 'addingInfo' in self.conf:
            self.addingInfoText.setText(self.conf['addingInfo'])
        if 'hLabel' in self.conf:
            self.hLabelText.setText(self.conf['hLabel'])
        if 'vLabel' in self.conf:
            self.vLabelText.setText(self.conf['vLabel'])

        if 'gridColor' in self.conf:
            self.gridColBtn.setStyleSheet(
              "QWidget { background-color: %s }"
              % QColor(self.conf['gridColor']).name())

        if 'abnormalColor' in self.conf:
            self.abnormalColBtn.setStyleSheet(
              "QWidget { background-color: %s }"
              % QColor(self.conf['abnormalColor']).name())

        if 'patternSize' in self.conf:
            pSize = self.conf['patternSize']
            self.patternSizeText.setText(str(pSize))
            self.updatePlotColorButton(pSize)

        if 'showAbnormalStat' in self.conf:
            if self.conf['showAbnormalStat']:
                self.showAbnormalStatCkb.setCheckState(QtCore.Qt.Checked)
            else:
                self.showAbnormalStatCkb.setCheckState(QtCore.Qt.Unchecked)

        if 'plotThick' in self.conf:
            self.plotThickText.setText(str(self.conf['plotThick']))
        if 'gridThick' in self.conf:
            self.gridThickText.setText(str(self.conf['gridThick']))

    ###################################
    # Author: Lan
    # def: updatePlotColorButton():201409
    # delete all the color buttons
    # add color buttons according to pattern;
    # any extra button, use default color
    def updatePlotColorButton(self, pSize):
        for ch in range(len(self.plotColBtns)):
            for pb in self.plotColBtns[ch]:
                self.patternColorVBoxes[ch].removeWidget(pb)
                pb.deleteLater()

        self.plotColBtns = []
        for ch in range(len(self.parent.channels)):
            # allColorBtns are set to the color
            # of the first button in that channel
            if ch < len(self.conf['plotColor']):
                self.allColorBtns[ch].setStyleSheet(
                  "QWidget { background-color: %s }"
                  % QColor(self.conf['plotColor'][ch][0]).name())
            else:
                self.allColorBtns[ch].setStyleSheet(
                  "QWidget { background-color: %s }"
                  % QColor(self.parent.defaultConf['plotColor'][ch][0]).name())
            self.plotColBtns.append([])

            for i in range(pSize):
                cb = QtGui.QPushButton(str(i), self.patternColorPanel)
                cb.setFixedWidth(50)
                self.plotColBtns[ch].append(cb)
                cb.clicked.connect(self.onChangeColor)
                cb.resize(1, 1)
                self.patternColorVBoxes[ch].addWidget(cb)

                if ch < len(self.conf['plotColor']):
                    if i < self.conf['patternSize']:
                        cb.setStyleSheet(
                          "QWidget { background-color: %s }"
                          % QColor(self.conf['plotColor'][ch][i]).name())
                    else:
                        cb.setStyleSheet(
                          "QWidget { background-color: %s }"
                          % QColor(self.conf['plotColor'][ch][0]).name())
                else:
                    cb.setStyleSheet(
                      "QWidget { background-color: %s }"
                      % QColor(
                        self.parent.defaultConf['plotColor'][ch][0]).name())
            self.patternColorVBoxes[ch].addStretch(1)

    ###################################
    # Author: Lan
    # def: onUpdate():201409
    # reset the color buttons according to
    # the number entered in patternSizeText
    def onUpdate(self):
        pSize = int(self.patternSizeText.text())
        self.updatePlotColorButton(pSize)


class ArrayGui(QtGui.QWidget):
    # ESType=EVENT/STATION
    def __init__(self, parent, ESType=None):
        QtGui.QWidget.__init__(self)
        self.PH5View = parent
        self.control = parent.mainControl
        self.ESType = ESType
        self.initUI()

    def initUI(self):
        mainVbox = QtGui.QVBoxLayout()
        self.setLayout(mainVbox)

        arrayBox = QtGui.QHBoxLayout()
        mainVbox.addLayout(arrayBox)
        self.arrayTabs = QtGui.QTabWidget(self)
        arrayBox.addWidget(self.arrayTabs)

        mainVbox.addWidget(QtGui.QLabel('NOTICE:'))
        self.statusCtrl = QtGui.QLabel('')
        mainVbox.addWidget(self.statusCtrl)

    def setArrays(self):
        if self.ESType != 'EVENT_LOI':
            submitType = False
        else:
            submitType = True
        # self.clearArrayTabs()

        for a in self.PH5View.arrays:
            a[self.ESType] = ES_Gui(
                self, ESType=self.ESType, array=a, submitType=submitType)
            self.arrayTabs.addTab(a[self.ESType], "Array_t_%s" % a['arrayId'])

        self.selectedArray = self.PH5View.arrays[0]

    def clearArrayTabs(self):
        # remove old tabs and delete them as well
        # self.arrayTabs.clear() can remove old tabs but doesn't delete them
        for i in range(len(self.arrayTabs)-1, -1, -1):
            tab = self.arrayTabs.widget(i)
            self.arrayTabs.removeTab(i)
            tab.deleteLater()

    def setNotice(self, graphName):
        txt = "Graph Name is '%s'. Click on Properties in " + \
              "Control tab to change name of the graph"
        self.statusCtrl.setText(txt % graphName)


# _________________________________________________________
ENABLEDCOLOR = QtGui.QColor(100, 100, 250, 100).name()
DISABLEDCOLOR = QtGui.QColor(225, 225, 225, 100).name()
# Event_Station


class ES_Gui(QtGui.QWidget):
    # ESType=EVENT/STATION; submitType=True/False
    def __init__(self, parent, ESType, array, submitType=False):
        QtGui.QWidget.__init__(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.parent = parent
        self.PH5View = self.parent.PH5View
        self.control = parent.control
        self.helpEnable = False
        self.array = array
        self.ESType = ESType
        self.submitType = submitType
        self.EXPL = {}
        self.initUI()
        self.selectedEvents = []
        self.selectedStations = []
        self.shotLine = None

    def initUI(self):
        # mainFrame = QtGui.QFrame(self);self.setCentralWidget(mainFrame)
        mainVbox = QtGui.QVBoxLayout()
        self.setLayout(mainVbox)

        """
        station form need channelCtrls:
          If submit form (shot gather):
            channelCtrls need to be checkbox to allow to select multi,
            need to get shotCtrls from parents
          If not submit form (receiver gather):
            channelCtrls need radio button to allow
            selecting only one channel at a time
         event form need shotCtrls (shotline) which should be radio button
          to allow selecting only one shotline at a time
        """
        self.headBox = QtGui.QHBoxLayout()
        mainVbox.addLayout(self.headBox)

        if self.ESType in ['STATION', 'EVENT_LOI']:
            if self.submitType and self.ESType == 'STATION':
                self.shotCtrls = self.parent.shotCtrls
            self.headBox.addWidget(QtGui.QLabel('Channels:'))
            self.headBox.insertSpacing(-1, 15)
            self.channelCtrls = channelCtrls = []
            channelGroup = QtGui.QButtonGroup(self)
            for ch in self.array['channels']:
                if self.submitType:
                    channelCtrls.append(QtGui.QCheckBox(str(ch), self))
                else:
                    channelCtrls.append(QtGui.QRadioButton(str(ch), self))
                i = len(channelCtrls) - 1
                self.headBox.addWidget(channelCtrls[i])
                if self.submitType:
                    channelCtrls[i].setCheckState(QtCore.Qt.Checked)
                else:
                    channelGroup.addButton(channelCtrls[i])
                channelCtrls[i].installEventFilter(self)
                self.EXPL[channelCtrls[i]] = \
                    "Click this channel to select/deselect."
            if not self.submitType:
                channelCtrls[0].setChecked(True)

        elif self.ESType == 'EVENT':
            if self.PH5View.events['shotLines'] != []:
                if self.parent.__class__.__name__ == 'ES_Gui':
                    self.channelCtrls = self.parent.channelCtrls
                self.headBox.addWidget(QtGui.QLabel('Shot Lines:'))
                self.headBox.insertSpacing(-1, 15)
                self.shotCtrls = shotCtrls = []
                shotGroup = QtGui.QButtonGroup(self)
                for shot in self.PH5View.events['shotLines']:
                    shotCtrls.append(QtGui.QRadioButton(shot, self))
                    i = len(shotCtrls) - 1
                    self.headBox.addWidget(shotCtrls[i])
                    shotGroup.addButton(shotCtrls[i])
                    shotCtrls[i].clicked.connect(self.onSelectShot)
                shotCtrls[0].setChecked(True)

        self.headBox.addStretch(1)

        if not self.submitType or self.ESType == 'EVENT_LOI':
            v = (self.array['sampleRate'],
                 timedoy.epoch2passcal(self.array['deployT']),
                 timedoy.epoch2passcal(self.array['pickupT']))
            mainVbox.addWidget(
                QtGui.QLabel("Array Info: %s sps || %s - %s" % v))

        scrollArea = QtGui.QScrollArea(self)
        mainVbox.addWidget(scrollArea)
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scrollArea.setWidgetResizable(True)
        itemsFrame = QtGui.QFrame()
        scrollArea.setWidget(itemsFrame)
        mainScrollBox = QtGui.QVBoxLayout()
        itemsFrame.setLayout(mainScrollBox)
        self.scrollPanel = scrollPanel = QtGui.QWidget()
        mainScrollBox.addWidget(scrollPanel)
        ESHbox = QtGui.QHBoxLayout(scrollPanel)
        ESVbox = QtGui.QVBoxLayout()
        ESHbox.addLayout(ESVbox)
        self.ESPane = QtGui.QWidget(scrollPanel)
        ESVbox.addWidget(self.ESPane)
        self.ESGrid = QtGui.QGridLayout()
        self.ESPane.setLayout(self.ESGrid)

        if self.ESType == 'EVENT':
            self.setEvents()
        elif self.ESType in ['STATION', 'EVENT_LOI']:
            self.ESType
            self.setStations()

        ESVbox.addStretch(1)
        ESHbox.addStretch(1)

        if self.submitType:
            botLayout = QtGui.QHBoxLayout()
            mainVbox.addLayout(botLayout)
            self.submitBtn = QtGui.QPushButton('Submit')
            self.submitBtn.installEventFilter(self)
            if self.ESType in ['STATION', 'EVENT_LOI']:
                item = "stations"
                self.EXPL[self.submitBtn] = \
                    "Submit the list of stations to be plotted"
            elif self.ESType == 'EVENT':
                item = "events"
                self.EXPL[self.submitBtn] = \
                    "Submit the list of events to be plotted"
            self.submitBtn.clicked.connect(self.onSubmit)
            self.submitBtn.resize(25, 70)  # self.submitBtn.sizeHint())
            botLayout.addWidget(self.submitBtn)

            botLayout.insertSpacing(-1, 15)

            self.cancelBtn = QtGui.QPushButton('Cancel')
            self.cancelBtn.clicked.connect(self.onCancel)
            self.cancelBtn.resize(25, 75)
            botLayout.addWidget(self.cancelBtn)

            botLayout.insertSpacing(-1, 15)

            self.helpBtn = QtGui.QPushButton('Help')
            self.helpBtn.clicked.connect(self.onHelp)
            self.helpBtn.resize(25, 75)
            botLayout.addWidget(self.helpBtn)

            botLayout.addStretch(1)
            mainVbox.addWidget(
                QtGui.QLabel(
                    "Shift + Left Click to select a range of %s" % item))

    def onHelp(self, evt):
        self.helpEnable = not self.helpEnable
        if self.helpEnable:
            cursor = QtGui.QCursor(QtCore.Qt.WhatsThisCursor)
        else:
            cursor = QtGui.QCursor(QtCore.Qt.ArrowCursor)

        self.setCursor(cursor)

    def onCancel(self, evt):
        self.close()

    ###################################
    # Author: Lan
    # def: onSubmit()
    # updated: 201803
    # get neccessary info for plotting
    def onSubmit(self, evt):
        PH5View = self.PH5View
        control = self.parent.control

        PH5View.submitGui = self.ESType
        PH5View.selectedArray = self.array
        # _____________ CHANNEL _____________
        control.channels = []
        for ch in self.channelCtrls:
            if ch.isChecked():
                control.channels.append(
                    self.array['channels'][self.channelCtrls.index(ch)])

        if control.channels == []:
            msg = "There is no Channels selected."
            QtGui.QMessageBox.question(
                self, 'Error', msg, QtGui.QMessageBox.Ok)
            return

        control.setWidgetsEnabled(True)
        control.stationSpacingUnknownCkb.setChecked(True)
        if self.ESType == 'EVENT':
            """
            receiver gather:
                selectedEvents from check state
                selectedStations was the selected station
                    that open the events-submit form
                no start time for receiver gather because
                    multi events may be selected with different start time
                space between traces is fixed because
                    all selected event should belong to one station
                no correction
            """
            control.gather = "receiver"
            PH5View.selectedEvents = [
                    e for e in self.array['events'] if
                    e['eventChk'].checkState() == QtCore.Qt.Checked]

            if PH5View.selectedEvents == []:
                msg = "You must select at least one events before continue."
                QtGui.QMessageBox.question(
                    self, 'Warning', msg, QtGui.QMessageBox.Ok)
                return

            control.startrangetimeCtrl.setText('')
            control.startrangetimeCtrl.setEnabled(False)
            control.stationSpacingUnknownCkb.setEnabled(False)
            control.correctionCkb.setCheckState(QtCore.Qt.Unchecked)
            control.correctionCkb.setEnabled(False)
            control.offsetCtrl.setText("0")
            control.offsetCtrl.setEnabled(False)
            e = PH5View.selectedEvents[0]

        elif self.ESType == 'STATION':
            """
            shot gather:
                selectedStations from check state
                selectedEvents was the selected event
                    that open the stations-submit form
                default start time is the start time of the selected event
                if more than one channel selected, fixed space
                    between traces is required for better view
                offset: keep the previous offset used
            """
            control.gather = "shot"
            self.array['seclectedStations'] = []
            # use orderedStationIds to have
            # the station sorted from the reader
            for sId in self.array['orderedStationIds']:
                s = self.array['stations'][sId]
                if s['stationChk'].checkState() == QtCore.Qt.Checked:
                    self.array['seclectedStations'].append(sId)

            if self.array['seclectedStations'] == []:
                msg = "You must select at least one stations before continue."
                QtGui.QMessageBox.question(
                    self, 'Warning', msg, QtGui.QMessageBox.Ok)
                return

            e = PH5View.selectedEvents[0]
            control.startrangetimeCtrl.setText(
                timedoy.epoch2passcal(e['eStart']))
            control.startrangetimeCtrl.setEnabled(True)

            control.correctionCkb.setCheckState(QtCore.Qt.Checked)
            control.correctionCkb.setEnabled(True)
            control.offsetCtrl.setText(str(control.dfltOffset))
            control.offsetCtrl.setEnabled(True)

            if len(control.channels) > 1:
                control.overlapSB.setValue(0)
                control.stationSpacingUnknownCkb.setEnabled(False)
                control.nominalStaSpace.setText('1000')
            else:
                control.overlapSB.setValue(25)
                control.stationSpacingUnknownCkb.setEnabled(True)
        elif self.ESType == 'EVENT_LOI':
            """
            event_t LOI:
                selectedStations from check state
                selectedEvents is None
                default start time is the start time of the selected event
                if more than one channel selected, fixed space
                    between traces is required for better view
                offset: keep the previous offset used
            """
            control.gather = "event_loi"
            self.array['seclectedStations'] = []
            # use orderedStationIds to have
            # the station sorted from the reader
            for sId in self.array['orderedStationIds']:
                s = self.array['stations'][sId]
                if s['stationChk'].checkState() == QtCore.Qt.Checked:
                    self.array['seclectedStations'].append(sId)

            if self.array['seclectedStations'] == []:
                msg = "You must select at least one stations before continue."
                QtGui.QMessageBox.question(
                    self, 'Warning', msg, QtGui.QMessageBox.Ok)
                return

            e = None
            control.startrangetimeCtrl.setText(
                timedoy.epoch2passcal(self.array['deployT']))
            control.startrangetimeCtrl.setEnabled(True)

            control.correctionCkb.setCheckState(QtCore.Qt.Checked)
            control.correctionCkb.setEnabled(True)
            control.offsetCtrl.setText(str(control.dfltOffset))
            control.offsetCtrl.setEnabled(True)

            control.overlapSB.setValue(0)
            control.stationSpacingUnknownCkb.setEnabled(False)

        else:
            print "Error in ES_GUI.onSubmit(): self.ESType='%s'" % self.ESType

        for ch in range(1, 4):
            if ch in control.channels:
                control.channelCkbs[ch].setEnabled(True)
                control.channelCkbs[ch].setChecked(True)
            else:
                control.channelCkbs[ch].setEnabled(False)
                control.channelCkbs[ch].setChecked(False)

        control.onChangePropertyType()
        if self.ESType != 'EVENT_LOI':
            control.eventId = e['eventId']
            PH5View.selectedEventIds = [ev['eventId']
                                        for ev in PH5View.selectedEvents]
            control.upperTimeLen = e['eStop'] - e['eStart']
        else:
            control.eventId = None
            PH5View.selectedEventIds = None
            control.upperTimeLen = \
                self.array['pickupT'] - self.array['deployT']

        newTimeLen = control.dfltTimeLen - control.dfltOffset
        minInterval = int(newTimeLen/25)
        maxInterval = int(newTimeLen)
        control.timeGridIntervalSB.setRange(minInterval, maxInterval)
        control.timeGridIntervalSB.setValue(int(newTimeLen/15))

        control.timelenCtrl.setText(str(control.dfltTimeLen))
        control.setAllReplotBtnsEnabled(False)

        PH5View.tabWidget.setCurrentIndex(0)

        if self.ESType != 'EVENT_LOI':
            self.close()
            del self

    ###################################
    # Author: Lan
    # def: setEvents():201701
    # set GUI for user to select Event(s)
    def setEvents(self):
        if self.submitType:
            allChk = QtGui.QCheckBox('')
            allChk.setChecked(True)
            self.ESGrid.addWidget(allChk, 0, 1)
            allChk.installEventFilter(self)
            self.EXPL[allChk] = "Click to select/deselect ALL events"
            allChk.clicked.connect(self.onSelectAllEvents)
        else:
            eventGroup = QtGui.QButtonGroup(self)

        self.ESGrid.addWidget(QtGui.QLabel('eventId'), 0, 2)
        self.ESGrid.addWidget(QtGui.QLabel('Time'), 0, 3)
        self.ESGrid.addWidget(QtGui.QLabel('Latitude'), 0, 4)
        self.ESGrid.addWidget(QtGui.QLabel('Longitude'), 0, 5)
        self.ESGrid.addWidget(QtGui.QLabel('Elevation(m)'), 0, 6)
        self.ESGrid.addWidget(QtGui.QLabel('Mag'), 0, 7)
        self.ESGrid.addWidget(QtGui.QLabel('Depth(m)'), 0, 8)

        self.eventChks = []
        self.evenIDList = []
        self.selectedEventChks = []
        self.array['events'] = []

        lineSeq = 1
        for e in self.PH5View.events['events']:
            if e['eStop'] < self.array['deployT'] \
                    or e['eStart'] > self.array['pickupT']:
                continue
            self.array['events'].append(e)
            self.evenIDList.append(e['eventId'])
            e['markLbl'] = QtGui.QLabel(self.ESPane)
            e['markLbl'].setFixedWidth(20)
            e['markLbl'].setFixedHeight(20)
            self.ESGrid.addWidget(e['markLbl'], lineSeq, 0)

            # shot gather: user click on an event to open stations' form
            if not self.submitType:
                e['eventRbtn'] = QtGui.QRadioButton(self.ESPane)
                e['eventRbtn'].installEventFilter(self)
                self.EXPL[e['eventRbtn']] = \
                    "Click this event to select/deselect."
                e['eventRbtn'].clicked.connect(self.onSelectEvent)
                self.ESGrid.addWidget(e['eventRbtn'], lineSeq, 1)
                eventGroup.addButton(e['eventRbtn'])

            # receiver gather. This form was opened when user
            # select a station. User can select multi events befor submitting
            else:
                e['eventChk'] = QtGui.QCheckBox('', self.ESPane)
                self.eventChks.append(e['eventChk'])
                e['eventChk'].setChecked(True)
                e['eventChk'].installEventFilter(self)
                e['eventChk'].clicked.connect(self.onSelectEventRange)
                self.EXPL[e['eventChk']] = "Click to select this event"
                self.ESGrid.addWidget(e['eventChk'], lineSeq, 1)
            self.addLabel(self.ESGrid, str(e['eventId']), lineSeq, 2)
            self.addLabel(self.ESGrid,
                          timedoy.epoch2passcal(e['eStart']), lineSeq, 3)
            self.addLabel(self.ESGrid, str(e['lat.']), lineSeq, 4)
            self.addLabel(self.ESGrid, str(e['long.']), lineSeq, 5)
            self.addLabel(self.ESGrid, str(e['elev.']), lineSeq, 6)
            self.addLabel(self.ESGrid, str(e['mag.']), lineSeq, 7)
            self.addLabel(self.ESGrid, str(e['depth']), lineSeq, 8)
            lineSeq += 1
        self.selectedEventChks = list(range(len(self.eventChks)))
        self.onSelectShot()

    ###################################
    # Author: Lan
    # def: setStations():201701
    # set GUI for user to select Station(s)
    def setStations(self):
        if self.submitType:
            allChk = QtGui.QCheckBox('')
            allChk.setChecked(True)
            self.ESGrid.addWidget(allChk, 0, 0)
            allChk.installEventFilter(self)
            self.EXPL[allChk] = "Click to select/deselect ALL stations"
            allChk.clicked.connect(self.onSelectAllStations)
        else:
            stationGroup = QtGui.QButtonGroup(self)

        self.ESGrid.addWidget(QtGui.QLabel('staId'), 0, 1)
        self.ESGrid.addWidget(QtGui.QLabel('DAS'), 0, 2)
        self.ESGrid.addWidget(QtGui.QLabel('Latitude'), 0, 3)
        self.ESGrid.addWidget(QtGui.QLabel('Longitude'), 0, 4)
        self.ESGrid.addWidget(QtGui.QLabel('Elevation(m)'), 0, 5)
        self.stationChks = []

        lineSeq = 1
        for sId in self.array['orderedStationIds']:
            s = self.array['stations'][sId]
            # receiver gather: user click on a station to open events' form
            if not self.submitType:
                s['stationRbtn'] = QtGui.QRadioButton(self.ESPane)
                s['stationRbtn'].installEventFilter(self)
                self.EXPL[s['stationRbtn']] = \
                    "Click this station to select/deselect"
                s['stationRbtn'].clicked.connect(self.onSelectStation)
                self.ESGrid.addWidget(s['stationRbtn'], lineSeq, 0)
                stationGroup.addButton(s['stationRbtn'])

            # shot gather. This form was opened when user select an event.
            # User can select multi stations befor submitting
            else:
                s['stationChk'] = QtGui.QCheckBox('', self.ESPane)
                self.stationChks.append(s['stationChk'])
                s['stationChk'].setChecked(True)
                s['stationChk'].clicked.connect(self.onSelectStationRange)
                s['stationChk'].installEventFilter(self)
                self.EXPL[s['stationChk']] = "Click to select this station"
                self.ESGrid.addWidget(s['stationChk'], lineSeq, 0)

            self.addLabel(self.ESGrid, str(s['stationId']), lineSeq, 1)
            self.addLabel(self.ESGrid, str(s['dasSer']), lineSeq, 2)
            self.addLabel(self.ESGrid, str(s['lat.']), lineSeq, 3)
            self.addLabel(self.ESGrid, str(s['long.']), lineSeq, 4)
            self.addLabel(self.ESGrid, str(s['elev.']), lineSeq, 5)
            lineSeq += 1

        self.selectedStationChks = list(range(len(self.stationChks)))

    ###################################
    # Author: Lan
    # def: addLabel():2015
    # set info labels with background white
    def addLabel(self, grid, text, row, col):
        lbl = QtGui.QLabel(text)
        lbl.setStyleSheet("QWidget { background-color: white }")
        lbl.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        grid.addWidget(lbl, row, col)

    ###################################
    # Author: Lan
    # def: onSelectAllStations():201612
    # check/uncheck all stations
    # set values in self.selectedStationChks to help in onSelectStationRange()
    def onSelectAllStations(self, evt):
        allChk = self.sender()
        for sId in self.array['stations'].keys():
            s = self.array['stations'][sId]
            s['stationChk'].setCheckState(allChk.checkState())
        if allChk.checkState():
            self.selectedStationChks = list(range(len(self.stationChks)))
        else:
            self.selectedStationChks = []

###################################
# Author: Lan
# def: onSelectAllEvents():201612
# check/uncheck all events
# set values in self.selectedEventChks to help in onSelectEventRange()
    def onSelectAllEvents(self, evt):
        allChk = self.sender()
        for e in self.array['events']:
            if e['shotlineId'] == self.PH5View.shotLine:
                e['eventChk'].setCheckState(allChk.checkState())

        if allChk.checkState():
            self.selectedEventChks = list(range(len(self.eventChks)))
        else:
            self.selectedEventChks = []

    ###################################
    # Author: Lan
    # def: onSelectEvent():201612
    # select one event => list of stations
    # for the array of this GUI to will show up
    def onSelectEvent(self, state):
        # only one event in the selectedEvents
        self.PH5View.selectedEvents = [e for e in self.array['events']
                                       if e['eventRbtn'] == self.sender()]

        self.stationsWidget = stationsWidget = ES_Gui(
            self, ESType='STATION', array=self.array, submitType=True)
        stationsWidget.setGeometry(130, 100, 650, 700)
        v = (self.array['arrayId'], self.PH5View.selectedEvents[0]['eventId'])
        stationsWidget.setWindowTitle("Array %s - Event %s" % v)
        stationsWidget.show()

    ###################################
    # Author: Lan
    # def: onSelectEvent():201612
    # select one station => list of events
    # of which times belong to the time of this GUI's array
    def onSelectStation(self, state):
        self.array['seclectedStations'] = []

        for sId in self.array['stations'].keys():
            s = self.array['stations'][sId]
            if s['stationRbtn'] == self.sender():
                self.array['seclectedStations'] = [sId]
                break  # only one station is selected
        self.eventsWidget = eventsWidget = ES_Gui(
            self, ESType='EVENT', array=self.array, submitType=True)
        eventsWidget.setGeometry(130, 100, 650, 700)

        # 0: only one channel-station is selected, 1: index of station
        v = (self.array['arrayId'], self.array['seclectedStations'][0])
        eventsWidget.setWindowTitle("Array %s - Station %s" % v)
        eventsWidget.show()

    ###################################
    # Author: Lan
    # def: onSelectEventRange():201701
    def onSelectEventRange(self, state):
        index = self.eventChks.index(self.sender())
        # if uncheck, remove that event from selectedEventChks
        if not self.sender().isChecked():
            self.selectedEventChks.remove(index)
            return

        modifiers = QtGui.QApplication.keyboardModifiers()

        # if first check with shift or check with no shift at all,
        # add that sigle event to selectedEventChks
        if len(self.selectedEventChks) == 0 \
                or modifiers != QtCore.Qt.ShiftModifier:
            self.selectedEventChks.append(index)
            return

        # check with shift, add the range from this event
        # to the closest one to selectedEventChks
        minId = min(self.selectedEventChks)
        maxId = max(self.selectedEventChks)

        if index < minId:
            maxId = minId
            minId = index
        else:
            minId = maxId
            maxId = index

        for i in range(minId, maxId+1):
            if i in self.selectedEventChks:
                continue
            self.selectedEventChks.append(i)
            self.eventChks[i].setCheckState(QtCore.Qt.Checked)

    ###################################
    # Author: Lan
    # def: onSelectStationRange():201701
    def onSelectStationRange(self, state):
        index = self.stationChks.index(self.sender())
        # if uncheck, remove that station from selectedStationChks
        if not self.sender().isChecked():
            print "remove:%s in %s" % (index, self.selectedStationChks)
            self.selectedStationChks.remove(index)
            return

        modifiers = QtGui.QApplication.keyboardModifiers()
        # if first check with shift or check with no shift at all,
        # add that sigle station to selectedStationChks
        if len(self.selectedStationChks) == 0 \
                or modifiers != QtCore.Qt.ShiftModifier:
            self.selectedStationChks.append(index)
            return

        # check with shift, add the range from this station
        # to the closest one to selectedStationChks
        minId = min(self.selectedStationChks)
        maxId = max(self.selectedStationChks)

        if index < minId:
            maxId = minId
            minId = index
        else:
            minId = maxId
            maxId = index

        for i in range(minId, maxId+1):
            if i in self.selectedStationChks:
                continue
            self.selectedStationChks.append(i)
            self.stationChks[i].setCheckState(QtCore.Qt.Checked)

###################################
# Author: Lan
# def: onSelectShot
# updated: 201702
# When select a shot Line, all the events belong to that shot line
# will be enabled otherwise will be disabled
    def onSelectShot(self, state=None):

        if state is not None:
            index = self.shotCtrls.index(self.sender())
        else:
            index = 0  # new form, default index=0
        self.PH5View.shotLine = self.PH5View.events['shotLines'][index]

        if self.submitType:
            ctrlName = 'eventChk'
        else:
            ctrlName = 'eventRbtn'

        for e in self.PH5View.events['events']:
            if e['eventId'] not in self.evenIDList:
                continue
            if e['shotlineId'] == self.PH5View.events['shotLines'][index]:
                e[ctrlName].setEnabled(True)
                e[ctrlName].setChecked(True)
                e['markLbl'].setStyleSheet(
                    " background-color: %s" % ENABLEDCOLOR)
            else:
                e[ctrlName].setEnabled(False)
                e[ctrlName].setChecked(False)
                e['markLbl'].setStyleSheet(
                    " background-color: %s" % DISABLEDCOLOR)

###################################
# Author: Lan
# def: eventFilter
# updated: 20151022
# using baloon tooltip to help user understand the use of the widget
# (only the one install event filter)
    def eventFilter(self, object, event):
        if not self.submitType and not self.PH5View.helpEnable:
            return False
        if self.submitType and not self.helpEnable:
            return False

        if event.type() == QtCore.QEvent.Enter:

            if object not in self.EXPL.keys():
                return False
            P = object.pos()
            if object.__class__.__name__ == 'QRadioButton' \
                    or (not self.submitType and
                        object.__class__.__name__ == 'QCheckBox'):
                QtGui.QToolTip.showText(
                    self.scrollPanel.mapToGlobal(
                        QtCore.QPoint(P.x(), P.y()+20)),
                    self.EXPL[object])
            else:
                QtGui.QToolTip.showText(
                    self.mapToGlobal(QtCore.QPoint(P.x(), P.y()+20)),
                    self.EXPL[object])

            return True
        return False


def changedFocusSlot(old, now):
    if (now is None and QtGui.QApplication.activeWindow() is not None):
        QtGui.QApplication.activeWindow().setFocus()


def startapp():
    global application  # , pointerWidget

    application = QtGui.QApplication(sys.argv)
    QtCore.QObject.connect(
        application,
        QtCore.SIGNAL("focusChanged(QWidget *, QWidget *)"),
        changedFocusSlot)
    # pointerWidget = SelectedStation(None, showPos=True);
    # pointerWidget.hide()
    PH5Visualizer()
    #  ex = PH5Visualizer(order='shot')
    #  win = OptionPanel(None)
    app.run()
    app.deleteLater()
    sys.exit(application.exec_())


if __name__ == '__main__':
    startapp()
