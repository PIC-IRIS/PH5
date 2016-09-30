#!/usr/bin/env pnpython4
# from newDrawplot

PROG_VERSION = "2016.205 Developmental"

import sys, os, time, math, gc, re
sys.path.append(os.path.join(os.environ['KX'], 'apps', 'pn4'))

import Experiment, TimeDOY
import PH5ReaderwVispyAPI, TimeDOY

from copy import deepcopy

from PyQt4 import QtGui, QtCore, Qt,QtSvg
from PyQt4.QtCore import QPoint,QRectF
from PyQt4.QtGui import QPolygon, QImage, QPixmap, QColor, QPalette

import numpy as np
from tempfile import mkdtemp
import os.path as path
from vispy import gloo, visuals, app
from vispy.util.transforms import rotate

#import vispy.mpl_plot as plt
import matplotlib.pyplot as plt
PH5VALFILE = path.join(mkdtemp(), 'PH5VAL.dat')     # to keep PH5 values for reuse

#OpenGL vertex shader
#Defines how to draw and transform the graph
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

##fragment shader...just colors the graph
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
    statusMsg = "%s %s" % (curMsg , nextMsg)
    statusBar.showMessage(statusMsg)        
    
  
##########################################
############### CLASS ####################
# Author: Lan
# Updated: 201409
# CLASS: Seperator - is the line to separate in the Gui
class Seperator(QtGui.QFrame):
    def __init__(self, thick=2, orientation="horizontal", length=None):
        QtGui.QFrame.__init__(self)
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.setFrameShadow(QtGui.QFrame.Sunken)
        if orientation == 'horizontal':
            self.setFixedHeight(thick)
            if length != None:
                self.setFixedWidth(length)
        else:
            self.setFixedWidth(thick)
            if length != None:
                self.setFixedHeight(length)


class InfoPanel(QtGui.QFrame):
    def __init__(self, control ):
        QtGui.QFrame.__init__(self)
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.control = control
        
        #self.setWindowFlags(QtCore.Qt.Window)
        control.infoBox.addWidget(self)
        self.vbox = vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(0)
        hbox = QtGui.QHBoxLayout() ; vbox.addLayout(hbox)
        
        self.quickRemovedCkb = QtGui.QCheckBox('QuickRemoved', self)
        self.quickRemovedCkb.stateChanged.connect(self.onQuickRemove)
        hbox.addWidget(self.quickRemovedCkb)
        
        self.deepRemovedCkb = QtGui.QCheckBox('DeepRemoved', self)
        self.deepRemovedCkb.stateChanged.connect(self.onDeepRemove)
        hbox.addWidget(self.deepRemovedCkb)
        
        self.infoLabel = QtGui.QLabel('', self)    
        vbox.addWidget(self.infoLabel)
        
        
    def showInfo(self, txt, canvas, statId):
        self.canvas = canvas
        self.statId = statId
        self.seq = self.control.metadata[self.statId]['seq']
        self.infoLabel.setText(txt)
        self.allowRemove = False
        if self.statId in self.control.PH5Info['quickRemoved']: 
            self.quickRemovedCkb.setCheckState(QtCore.Qt.Checked)
        else: 
            self.quickRemovedCkb.setCheckState(QtCore.Qt.Unchecked)
        if 'Main' in canvas.parent.title:
            self.deepRemovedCkb.setEnabled(True)
            if self.statId in self.control.PH5Info['deepRemoved']: 
                self.deepRemovedCkb.setCheckState(QtCore.Qt.Checked)
            else: 
                self.deepRemovedCkb.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.deepRemovedCkb.setCheckState(QtCore.Qt.Unchecked)
            self.deepRemovedCkb.setEnabled(False)
            
        self.allowRemove = True
        self.show()
        
    def onQuickRemove(self, evt):
        print "onQuickRemove"
        if not self.allowRemove: return
        c = self.canvas.quickRemove(self.statId,self.quickRemovedCkb.isChecked() )
        self.canvas.otherCanvas.quickRemove(self.statId,self.quickRemovedCkb.isChecked(), c) 
        self.canvas.updateData()
        self.canvas.otherCanvas.updateData()
        
    
    def onDeepRemove(self, evt):
        if not self.allowRemove: return
        if self.deepRemovedCkb.isChecked() \
        and self.seq not in self.control.PH5Info['deepRemoved']:
            self.control.PH5Info['deepRemoved'].append(self.seq)
            
        if not self.deepRemovedCkb.isChecked() \
        and self.seq in self.control.PH5Info['deepRemoved']:
            self.control.PH5Info['deepRemoved'].remove(self.seq)
        
        print "deepRemoved List:", self.control.PH5Info['deepRemoved']     
##########################################
############### CLASS ####################
# Author: Lan
# Updated: 201410
# CLASS: Selector - showing the selected area
# due to the big amount of data, Selector is not shown on the move but only
# shown at the beginning (mouse press) and the end (mouse release 
class Selector(QtGui.QRubberBand):
    def __init__(self, *arg,**kwargs):
        super(Selector,self).__init__(*arg,**kwargs)
        
    def paintEvent(self, e):
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(QtCore.Qt.red,5))
        painter.drawRect(e.rect().x()+1,e.rect().y()+1,e.rect().width()-1, e.rect().height()-1)

##########################################
############### CLASS ####################
# Author: Lan
# Updated: 201410
# CLASS: SelectedStation - showing the selected station (1 to 2 stations)
class SelectedStation(QtGui.QWidget):
    def __init__(self, parent, showPos=False):  
        QtGui.QWidget.__init__(self, parent)
        #self.setAttribute(Qt.Qt.WA_NoSystemBackground)  # transparent to see the selected part under the widget
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color:transparent;")
        #self.setWindowFlags(QtCore.Qt.ToolTip)          # hide title bar of the widget
        self.showPos = showPos

    ###################################
    # Author: Lan
    # def: paintEvent():201409
    def paintEvent(self, e=None): 
        qp = QtGui.QPainter()
        qp.begin(self)
        if self.showPos: 
            # showing arrow (pointerWidget): intended to use for showing the point that user want to see the info 
            #    transparent if pre-created with no parent, 
            #    don't use because it show up too slow
            qp.setPen( QtGui.QPen(QtCore.Qt.red,3 ) )
            qp.drawLine(0, 0, 20, 20) 
            qp.drawLine(0, 0, 2, 10)
            qp.drawLine(0, 0, 10, 2 )
        else:
            # showing a tiny square at the select station(s)
            qp.setBrush(QtCore.Qt.red)
            qp.drawRect(0,0,self.rect().width(), self.rect().height())  # -1 or the right and bottom lines will be thinner than the rest
        qp.end()
            
       
##########################################
############### CLASS ####################
# Author: Lan
# Updated: 201410
# CLASS: FileParaDialog - GUI for setting the picture file's size and format
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
            mainbox.addWidget( QtGui.QLabel(notice % (w, h), self) )  
            w, h = w-0.5, h-0.5
            
        formLayout = QtGui.QFormLayout(); mainbox.addLayout(formLayout)
        self.type = typeStr

        self.widthCtrl = QtGui.QLineEdit(self)
        self.widthCtrl.setText(str(w))
        formLayout.addRow('Width (%s)' % unitStr, self.widthCtrl) 

        self.heightCtrl = QtGui.QLineEdit(self)
        self.heightCtrl.setText(str(h))
        formLayout.addRow('Height (%s)' % unitStr, self.heightCtrl)
        
        formatDir = plt.gcf().canvas.get_supported_filetypes()
        if 'save' in typeStr: 
            formats =[]
            for f in formatDir.keys():
                formats.append("%s: %s" % (f, formatDir[f]))
    
            svgindex = formats.index("svg: %s" % formatDir['svg'] )
            self.fileFormatCtrl = QtGui.QComboBox(self)
            self.fileFormatCtrl.addItems(formats)
            self.fileFormatCtrl.setCurrentIndex(svgindex)
            formLayout.addRow("File Format", self.fileFormatCtrl) 

        okLbl = 'Save' if 'save' in typeStr else 'Print'
        self.OKBtn = QtGui.QPushButton(okLbl, self)
        self.OKBtn.clicked.connect(self.accept)

        self.cancelBtn = QtGui.QPushButton('Cancel', self)
        self.cancelBtn.clicked.connect(self.reject)

        formLayout.addRow(self.OKBtn, self.cancelBtn)
        self.resize(250,100)     
    
    def getResult(self):
        if 'save' in self.type:
            try:
                w = int(self.widthCtrl.text())
                h = int(self.heightCtrl.text())            
            except ValueError, e:
                print str(e)
                errorMsg = "Values entered must be integers"
                QtGui.QMessageBox.question(self, 'Error', errorMsg, QtGui.QMessageBox.Ok)
                return 
            
            fileFormat = str(self.fileFormatCtrl.currentText()).split(":")[0]
            return w, h, self.type[5:],fileFormat
        else:
            try:
                w = float(self.widthCtrl.text())
                h = float(self.heightCtrl.text())            
            except ValueError, e:
                print str(e)
                errorMsg = "Values entered must be floats"
                QtGui.QMessageBox.question(self, 'Error', errorMsg, QtGui.QMessageBox.Ok)
                return                
            
            return w, h, self.type[5:]
        
            
        
    @staticmethod  
    def print_save(parent, typeStr, unitStr, defaultSize):  
        # this method to help PrintSaveDialog return values
        dialog = PrintSaveParaDialog(parent, typeStr, unitStr, defaultSize)
        result = dialog.exec_()
        if result==QtGui.QDialog.Rejected: return
        returnVal = dialog.getResult()
        
        if returnVal == None:
            returnVal = PrintSaveParaDialog.print_save(parent, typeStr, unitStr, defaultSize)

        return returnVal
    
  

##########################################
############### CLASS ####################
# Author: Lan
# Updated: 201507
# CLASS: Canvas - to show the graph
class Canvas(app.Canvas):
    def __init__(self, parent, control):
        app.Canvas.__init__(self, keys='interactive')
        self.zoomWidget = Selector(QtGui.QRubberBand.Rectangle, parent) 
        #self.filterEnabled = False
        self.parent = parent
        self.control = control
        self.PH5View = control.PH5View
        self.orgW, self.orgH = self.size
        self.labelPos = []
        self.select = False
        self.currDir = 'up'
        self.reset()
        self.tr_sys = visuals.transforms.TransformSystem(self)
        #self.model = np.eye(4, dtype=np.float32)
        #rotate(self.model, -90, 0, 0, 1)
        # use the following line b/c the version of vispy has been changed
        self.model=[[  6.12323426e-17,  -1.00000000e+00,   0.00000000e+00,   0.00000000e+00],
                    [  1.00000000e+00,   6.12323426e-17,   0.00000000e+00,   0.00000000e+00],
                    [  0.00000000e+00,   0.00000000e+00,   1.00000000e+00,   0.00000000e+00],
                    [  0.00000000e+00,   0.00000000e+00,   0.00000000e+00,   1.00000000e+00]]
        
        #labels' preparation: can't figure out a way to used SHADER in showing text
        #     have to use visuals to show text
        #     the more text is used, the slower the program is => limit to show 25 texts at a time
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
    # def: initData():201507
    #    initiate data for painting the whole data
    #    data to feed vispy drawing includes 4 parts: x, y, color, index
    #    => read each station's data: time + values, and create color + index , then feed data to self.program
    #    => if station in quickRemoved list, just turn it's color to white
    #    => if station in deepRemoved list, add no value for its drawing data
    #    because data for each station are fed separately, only use index=0 
    #    note: time was build from smaller to greater, the drawing from top to bottom
    #        if want to draw time go up, program must invert the time with variable direct
    #    => build data for grid lines, then feed data to gProgram
    #    => re-position labels: resiteLabels()
    #    => update to redraw canvas
    def initData(self, t=np.array([]), val=0, deepRemoving=False):
        global START, END, processInfo, countDRAW
        counData = 0
        #print "initData"
        start = time.time()
        direct = -1 if self.control.upRbtn.isChecked() else 1
        self.currDir = 'up' if self.control.upRbtn.isChecked() else 'down'     
        colors = [QColor(c).getRgbF()[:3] for c in self.control.conf['plotColor']]
        if not deepRemoving:
            self.parent.canvScaleT, self.parent.canvScaleV = (1.,1.)    # for resetting pan/scale
            self.parent.panT, self.parent.panV = (0.,0.)
            # for real scaling
            self.canvScaleT, self.canvScaleV =(1,1)
            self.panT, self.panV = (0.,0.)
        if val != None:
            # this operation to change the staLimitList to range (-1,1): to match with change in value
            self.control.statLimitList = 2*self.control.statLimitList/self.control.maxVal -1

        self.parent.setWindowTitle('Main Window:  %s %s' % (self.PH5View.graphName,self.control.conf['addingInfo']))
        if val!=None and len(t)!=0:
            self.reset(needUpdate=False)
            # onGetnPlot(), onApplySimplify_Replot
            #self.startStatId = self.parent.startStatId= 0
            if not deepRemoving:
                self.startStatId= 0
                self.endStatId = self.control.PH5Info['numOfStations'] - 1
                self.mainMinY = -1      # to define lim in self.painting
                self.mainMaxY = 1
                
            self.data=[]
            for i in range(len(val)):
                aSize = len(val[i])
                self.data.append( np.zeros(aSize,
                                    dtype=[('a_position', np.float32, 2),
                                           ('a_color', np.float32, 3),
                                           ('a_index', np.float32, 1)]) )

                # org: top2bottom, choose up - bottom2top: direct=-1
    
                if i in self.control.PH5Info['deepRemoved']:
                    self.data[i]['a_position'][:, 0] = np.ones(0)
                else:
                    self.data[i]['a_position'][:, 0] = direct*t[self.control.keepList[i]]  
                # change val to range (-1,1) - can't change in createVal() 
                #                              bc val is a list of nparray, not an nparray
                self.data[i]['a_position'][:, 1] = val[i]*2./self.control.maxVal -1
                
                # an np array of all 0s for each data will be fed separately
                self.data[i]['a_index'] = np.repeat(0,aSize)

            
        if val==None and len(t)!=0:
            # onApplyVel_RePlot(), onApplyCorrVel_RePlot()

                if i in self.control.PH5Info['deepRemoved']:
                    self.data[i]['a_position'][:, 0] = np.ones(0)
                else:
                    self.data[i]['a_position'][:, 0] = direct*t[self.control.keepList[i]]  

        if val!= None and len(t)==0:
            # onApplyOverlap_RePlot()
            for i in range(len(self.data)):
                self.data[i]['a_position'][:, 1] = val[i]*2./self.control.maxVal -1        
        
        # val==None, t==None: onApplyPropperty_RePlot()
        for i in range(len(self.data)):
            # always rebuild colors in case anything change in properties. This doesn't take lots of time
            aSize = len(self.data[i]['a_index'])
            if i in self.control.PH5Info['quickRemoved'].keys():
                c = QColor(QtCore.Qt.white).getRgbF()[:3]
            else:
                colorIndex = i % len(colors)
                c = colors[colorIndex]
            self.data[i]['a_color'] = np.tile(c, (aSize,1) )
            
            
        if self.control.conf.has_key('showAbnormalStat') and self.control.conf['showAbnormalStat']:
            for abn in self.control.PH5Info['abnormal']:
                aSize = len(self.data[abn]['a_index'])
                abColor = QColor(self.control.conf['abnormalColor']).getRgbF()[:3]
                self.data[abn]['a_color'] = np.tile(abColor, (aSize,1)) 
        # feedData() and feedGData() separately for buildGrid() require info created in feedData(): canvScaleT                   
        self.feedData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        self.update_scale()
        
        self.gtData, self.gdData,self.timeY, self.tLabels, self.dLabels = self.buildGrid()
        self.feedGData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        
        self.labelPos = self.resiteLabels()
        
        self.enableDrawing = True
        self.update()
        self.parent.update()
        END = time.time()
        print 'Finish Plotting in %s seconds. Total processing time %s seconds' % (END-start, END-START)
        processInfo += "\nPlotting: %s seconds" % (END-start)
        processInfo += "\n=> Total processing time %s seconds" % (END-START)
        processInfo += "\n" + "*"*45
        self.control.statusLbl.setText(processInfo)   
        showStatus('', 'Finish Plotting in %s seconds. Total processing time %s seconds' % (END-start, END-START))
        self.defineViewWindow(0, 0, self.width, self.height)
        

    ###################################
    # Author: Lan
    # def: initSupportData():201507
    #    Data is passed to Support Window when onPassSelectAction() in MainWindow is called
    def initSupportData(self, mainCanvas, LT, RB):
        self.reset(needUpdate=False)
        global countDRAW
        countDRAW = 0
        #print "initSupportData"
        start = time.time()
        direct = -1 if self.control.upRbtn.isChecked() else 1
        #self.startStatId = self.parent.startStatId = deepcopy(mainCanvas.startStatId)
        self.startStatId = deepcopy(mainCanvas.startStatId)
        self.LT = LT            # Left-Top: used in trimData()
        self.RB = RB            # Right-Bottom: used in trimData()
        self.data=self.trimData(mainCanvas.data) #create Vispy's datacd
        #print "pass data:", self.data[0]['a_position'][:, 1][:3]
        self._calcPanScale(self.LT, self.RB)     # calc pans, scales, limList for new data fit in the window
        
        self.mainMinY, self.mainMaxY = self.getMinMaxY(self.LT, self.RB)    # to define lim in self.painting
        self.parent.canvScaleT, self.parent.canvScaleV = (self.canvScaleT, self.canvScaleV)  # for resetting pan/scale
        self.parent.panT, self.parent.panV = (self.panT, self.panV)         # for resetting
        self.feedData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        self.gtData, self.gdData, self.timeY, self.tLabels, self.dLabels = self.buildGrid()
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
        self.parent.setWindowTitle('Support Window: %s %s' % (self.PH5View.graphName,self.control.conf['addingInfo']))


    ###################################
    # Author: Lan
    # def: reset():201509
    # initiate/reset info need for drawing especially for Support Window 
    # when some para. are changed and then redraw in MainWindow
    def reset(self, needUpdate=True):
        #self.filterEnabled = False
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
        #self.zoompan = False
        #self.select = False
        self.LT = None
        self.RB = None
        gc.collect()
        #print "%s - canvas' attribute=%s" % (self.parent.title,dir(self))
        
    ###################################
    # Author: Lan
    # def: feedData():201507    
    #    delete self.program to clear the drawing data, ignore if has no program to delete
    #    create program with vertex and fragment shader
    #    bind program with built data
    def feedData(self, tPan=0., vPan=0., tScale=1.,vScale=1.):
        #print "feedData"
        try:
            self.program.delete()
            del self.program
        except: pass
        self.program = []
        for i in range(len(self.data)):
            self.program.append(gloo.Program(VERT_SHADER, FRAG_SHADER))
            self.program[i].bind(gloo.VertexBuffer(self.data[i]))
            self.program[i]['u_model'] = self.model
            self.program[i]['u_pan'] = (tPan, vPan)        # time,val    (y,x) b/c the model has been turned 90 degree
            self.program[i]['u_scale'] = (tScale, vScale)      # time, val

       
    ###################################
    # Author: Lan
    # def: feedData():201507    
    #    delete gProgram to clear the drawing data, ignore if has no gProgram to delete
    #    create gProgram with same vertex and fragment shader with grogram
    #    bind gProgram with built gData
    def feedGData(self, tPan=0., vPan=0., tScale=1., vScale=1.):
        #print "feedGData"
        try:
            self.gtProgramdelete()
            self.gdProgram.delete()
            del self.gtProgram
            del self.gdProgram
        except: pass

        self.gtProgram = gloo.Program(VERT_SHADER, FRAG_SHADER)
        self.gtProgram.bind(gloo.VertexBuffer(self.gtData))
        self.gtProgram['u_model'] = self.model
        self.gtProgram['u_pan'] = (tPan, vPan)        # time,val  
        self.gtProgram['u_scale'] = (tScale, vScale)      # time, val
        if self.gdData != np.zeros(0):
            self.gdProgram = gloo.Program(VERT_SHADER, FRAG_SHADER)
            self.gdProgram.bind(gloo.VertexBuffer(self.gdData))
            self.gdProgram['u_model'] = self.model
            self.gdProgram['u_pan'] = (tPan, vPan)        # time,val  
            self.gdProgram['u_scale'] = (tScale, vScale)      # time, val
            
    ###################################
    # Author: Lan
    # def: timeDirection():201507
    #    called when changing direction ("Up"/"Down")
    #    after changing the time values according to direction
    #        need to resite the time labels
    #    refeed Data and gData
    #    self.timePos is used only in this function
    def timeDirection(self):
        #print "timeDirection"
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
                
        for i in range(len(self.data)):
            t = deepcopy(self.data[i]['a_position'][:, 0])
            self.data[i]['a_position'][:, 0] = f*t

        direct = -1 if self.control.upRbtn.isChecked() else 1
        self.gtData['a_position'][:,0] = np.repeat(direct * self.timeY, 2)
        
        self.labelPos = self.resiteLabels()
        self.feedData()
        self.feedGData()
        
    ###################################
    # Author: Lan
    # def: resiteLabels():201507
    #    calc Pos according to time value
    #    only use labels for value in view
    #    set the values and positions for labels
    #    set new self.needLablNo for self.drawing know how many labels need to be drawn
    def resiteLabels(self, panT=None, panV=None, canvScaleT=None, canvScaleV=None):
        if panT == None:
            panT = self.panT
            panV = self.panV
            canvScaleT = self.canvScaleT
            canvScaleV = self.canvScaleV
        #print "resiteLabels"
        #index = 0
        # used in painting() to know what timeY need to be kept 
        # b/c timeY and fed data are all in range -1,1;
        # don't need to recalculate for painting used matplotlib
        # only labelPosY need to recalculate position for labels used vispy.visuals
        #
        # only calculate label positions based on the beginning self.orgH 
        # w/ all fed data in range -1,1, scale of the drawing will affect labels' position as well
        labelPos = []
        # check to see if labels have to skip any grids
        F = 1
        numOfLabels = 30
        while True:
            numOfLabels = math.ceil(self.control.totalTime)/(F*self.control.horGridIntervalSB.value()*1000*canvScaleT)
            if numOfLabels<=25: break
            F += 1                
        
        z = self.zeroTIndex
        self.gridT = {}
        if self.control.upRbtn.isChecked():
            
            k = 0
            y = 1
            try:
                while y > 0:
                    #print "text:",self.tLabels[z+k]
                    y = self.height - int(0.5*self.height*( (self.timeY[z+k]-panT) * canvScaleT + 1 ))
                    labelPos.insert(0,{'t': self.timeY[z+k],'y':y +self.offsetY,'text': "%s" % self.tLabels[z+k]})
                    k += F
            except Exception, e: 
                #print "1:" + str(e)
                pass 
            self.gridT['end'] = z+k
             
            k = F
            try:
                while y< self.height and z-k>0:
                    y = self.height - int(0.5*self.height*( (self.timeY[z-k]-panT) * canvScaleT + 1 ))
                    labelPos.append({'t': self.timeY[z-k],'y':y +self.offsetY,'text': "%s" % self.tLabels[z-k]})
                    k += F
            except Exception, e: 
                #print "2:" + str(e)
                pass 
            self.gridT['start'] = z-k
        else: 
            k=0        
            y = 1
            try:
                while y > 0 and z-k>0:
                    y = int(0.5*self.height*( (self.timeY[z-k]+panT) * canvScaleT + 1 ))
                    labelPos.insert(0,{'t':self.timeY[z-k],'y':y +self.offsetY,'text': "%s" % self.tLabels[z-k]})
                    k += F
            except Exception, e: 
                #print "3:"+str(e)
                pass 
            self.gridT['start'] = z-k
            
            k = F
            try:
                while y< self.height:
                    y = int(0.5*self.height*( (self.timeY[z+k]+panT) * canvScaleT + 1 ))
                    labelPos.append({'t': self.timeY[z+k],'y':y +self.offsetY,'text': "%s" % self.tLabels[z+k]})
                    k += F    
            except Exception, e: 
                #print "4:"+str(e)
                pass                 
            self.gridT['end'] = z+k


        F = 0
        numOfDLabels = 15
        while True:
            F += 1
            numOfDLabels = int(self.control.totalSize/(F*self.control.verGridIntervalSB.value()*1000*canvScaleV))
            v= (self.control.totalSize,F*self.control.verGridIntervalSB.value()*1000,F, numOfDLabels)
            #print "totalsize: %s, part=%s, F=%s, LNum=%s" % v
            if numOfDLabels<=10: break
        
        #if self.control.PH5Info.has_key('zeroDOffsetIndex') \
        #  and self.control.PH5Info['zeroDOffsetIndex'] != None:
        k = 0    
        z = self.zeroDIndex
        x = 1
        try: 
            while x > 0 and z-k>0:   
                #print "k1:%s, z-k=%s, self.dLabels[z-k][0]=%s" % (k,z-k, self.dLabels[z-k][0])
                x = int(0.5*self.width*( (self.dLabels[z-k][1]+panV) * canvScaleV+1 ))
                labelPos.insert(0,{'d': self.dLabels[z-k][1],'x':x +self.offsetX,'text': "%s" % self.dLabels[z-k][0]})
                k += F
        except Exception, e: 
            #print "5:"+str(e)
            pass
        
        k = F 
        try:
            while x< self.width:
                #print "k2:%s, z+k=%s, self.dLabels[z+k][0]=%s" % (k,z+k, self.dLabels[z+k][0])
                x = int(0.5*self.width*( (self.dLabels[z+k][1]+panV) * canvScaleV+1 ))
                labelPos.append({'d': self.dLabels[z+k][1],'x':x +self.offsetX,'text': "%s" % self.dLabels[z+k][0]})
                k += F

        except Exception, e:
            #print "6:" + str(e)
            pass

        return labelPos

    ###################################
    # Author: Lan
    # def: buildGrid():201507
    # calculate drawing time data and displaying time data for time grid
    #    tList: drawing time data, calc from Zero out to [-1,1]
    #    tLabels: displaying time data
    def buildGrid(self):
        #print "buildGrid spWhole=", spWhole
        control=self.control

        # 1s=1000ms, scaled down to the scale of time data sent to draw           
        secondScaled = 1000*control.scaleT
        # number of seconds per Gap
        secondsNoPerGap = control.horGridIntervalSB.value()
            
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
        while t>-1:
            tList.insert(0,t)
            tLabels.insert(0, "%.1f" % realT )
            t -= gridGap
            realT -= secondsNoPerGap
            i += 1

        tList.insert(0,t)                          # make sure -1 is added
        tLabels.insert(0, "%.1f" % realT)
        self.zeroTIndex=i     
        # greater than 0 values
        t = control.zeroT + gridGap
        realT = secondsNoPerGap
        #i = 1
        # 0 -> 1: append to the end of the list 
        while t<1:
            tList.append(t)
            tLabels.append("%.1f" % realT)
            t += gridGap
            realT += secondsNoPerGap
            #i += 1
        tList.append(t)
        tLabels.append("%.1f" % realT)
        ####################### build time grid data #####################  
        needLblNo = len(tList)                      # number of grid lines needed
        direct = -1 if self.control.upRbtn.isChecked() else 1                                   
        gtData = np.zeros(2*needLblNo,               # 2: each grid line need 2 points 
                        dtype=[('a_position', np.float32, 2),
                               ('a_color', np.float32, 3),
                               ('a_index', np.float32, 1)])
        timeY = np.array(tList)
        gtData['a_position'][:,0] = np.repeat(direct * timeY,2)   # 2: each grid line need 2 points
        # -50,50: big value to make sure the line get through the whole screen (doesn't work in painting())
        gtData['a_position'][:,1] = np.tile([-50,50], len(tList)) 
        c = [QColor(self.control.conf['gridColor']).getRgbF()[:3]]
        gtData['a_color'] = np.tile(c, (len(tList)*2, 1))

        # change color for zero line
        gtData['a_color'][self.zeroTIndex*2] = QColor(QtCore.Qt.blue).getRgbF()[:3]
        gtData['a_color'][self.zeroTIndex*2+1] = QColor(QtCore.Qt.blue).getRgbF()[:3]

        gtData['a_index'] = np.repeat(np.arange(0, needLblNo ), 2)
        
        ####################### distance grid ######################
        gdData=np.zeros(0)
        dLabels = []

        kilometerScaled = 1000/control.totalSize
        kilometerPerGap = control.verGridIntervalSB.value()
        distanceGap = kilometerPerGap * kilometerScaled*2
 
        # 0 value
        self.zeroD = zeroD = -2*self.control.scaledDelta/self.control.maxVal -1
        
        dList = [zeroD]
        dLabels = [('0', zeroD)]
        
        # less than 0 values
        d = zeroD -distanceGap
        realD = -kilometerPerGap
        i = 1
        # 0 -> -1: insert to the start of the list
        while d>-1:
            dList.insert(0,d)
            dLabels.insert(0, ("%.1fkm" % realD,d))
            d -= distanceGap
            realD -= kilometerPerGap
            i += 1
            
        dList.insert(0,d)
        dLabels.insert(0, ("%.1fkm" % realD,d))
        self.zeroDIndex=i
        # greater than 0 values
        d = zeroD + distanceGap
        realD= kilometerPerGap
        i = 1
        # 0 -> 1: append to the end of the list 
        while d<1:
            dList.append(d)
            dLabels.append(("%.1fkm" % realD,d))
            d += distanceGap
            realD += kilometerPerGap
            #i += 1
            
        dList.append(d)
        dLabels.append(("%.1fkm" % realD,d)) 

        needLblNo = len(dList)            
        ####################### build distance grid data #####################                                  
        gdData = np.zeros(2*needLblNo,               # 2: each grid line need 2 points 
                        dtype=[('a_position', np.float32, 2),
                               ('a_color', np.float32, 3),
                               ('a_index', np.float32, 1)])
         
        #distanceY = np.tile([1,0.99], len(dList))
        
        gdData['a_position'][:,0] = np.tile([-50,50], len(dList))    # [1,0.99]
        gdData['a_position'][:,1] = np.repeat(np.array(dList),2)     # 2: each grid line need 2 points 
        gdData['a_color'] = np.tile(QColor(QtCore.Qt.blue).getRgbF()[:3],(len(dList)*2,1))
        gdData['a_index'] = np.repeat(np.arange(0, needLblNo ), 2)
        
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
        #print "onresize: ", event.size
        self.width, self.height = event.size
        self.offsetX = self.parent.mainFrame.x() + self.position[0]
        self.offsetY = self.parent.mainFrame.y() + self.position[1]
        #self.offsetX = 0
        #self.offsetY = self.parent.height() - self.height
        gloo.set_viewport(0, 0, self.width, self.height)
        if not self.enableDrawing: return
        self.update_scale()

    ###################################
    # Author: Vispy.org
    # Modifier: Lan
    # def: on_draw()  
    #    let user choose drawing style ( program.draw(xxx) )
    #    draw label for new texts and positions 
    def on_draw(self, event):
        #print "ondraw"
        gloo.set_viewport(0, 0, self.width, self.height)
        gloo.clear(color=('white'))
        if self.enableDrawing:
            try:
                for i in range(len(self.program)):
                    try:
                        if self.control.lineRbtn.isChecked():
                            self.program[i].draw('line_strip')
                        
                        else:
                            self.program[i].draw('points')
                    except: break
                try:
                    if self.gtProgram and self.control.horGridCkb.isChecked():
                        self.gtProgram.draw('lines')
                    if self.gdProgram and self.control.verGridCkb.isChecked():
                        self.gdProgram.draw('lines')
                except: return
            except RuntimeError, e:
                print "on_draw's error:", str(e)
                errorMsg = "Program can't draw the given data maybe because of the limitation of Graphic card.\n" + \
                            "You may want to try to increase the simplify factor then redraw the data.\n" + \
                            "You should also look at the terminal to see if there is other reasons for this error."
                 
                QtGui.QMessageBox.question(None, 'Error', errorMsg, QtGui.QMessageBox.Ok)
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
    #    define the range of time and stations in the view
    #    to show info in the control panel
    def defineViewWindow(self,left, top, right, bottom, setData=True):
        #print "defineViewWindow setData= left=%s right=%s" % (left, right)
        
        k1 = self.locateDataPoint(left, top)  
        #print "K1=", k1
        if k1==None or len(k1)<1 or k1.__class__.__name__!='list': 
            #print "defineViewWindow k1=%s, left=%s, top=%s" % (k1, left,top)
            return False
                                   
        k2 = self.locateDataPoint(right, bottom)
        #print "K2=", k2 
        if k2==None or len(k2)<1 or k2.__class__.__name__!='list': 
            #print "defineViewWindow k2=%s, right=%s, bottom=%s" % (k2,right, bottom)
            return False

        if setData: self.displayWinValues(k1[0], k2[-1])
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
        self.control.horGridIntervalSB.setRange(minInterval, maxInterval) 
        
        newD1 = (k1['sentVal'] - self.zeroD) * self.control.totalSize/2000
        newD2 = (k2['sentVal'] - self.zeroD) * self.control.totalSize/2000
        
        self.control.startDistanceLbl.setText(str(newD1))
        self.control.endDistanceLbl.setText(str(newD2))   
        #print "displayWinValues timeLen=%s, minInterval=%s, maxInterval=%s" % (timeLen, minInterval, maxInterval)    
        #print self.data()


    ###################################
    # Author: Lan
    # def: on_mouse_release() 201509
    # if zoompan or when there is a right-click (chance of new choosing on this window): 
    #    updating info in the control panel
    # if select=True: 
    #    show the window of selection
    #    update self.LT, self.RB for use in the selected option after this
    def on_mouse_release(self,event):
        #print "on_mouse_release"
        v = (self.enableDrawing, self.select, event)
        #print "on_mouse_release enableDrawing=%s, select=%s, event=%s" % v
        if not self.enableDrawing: return
        #print "on_mouse_release, self.parent.title=", self.parent.title
        if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier: return
        if event._button == 1:
            # this call is for showing info on the control panel
            self.defineViewWindow(0, 0, self.width, self.height)
        if not self.select: return
        if event == None: return
        x0, y0 = event.press_event.pos
        x1, y1 = event.last_event.pos
        self.zoomWidget.setGeometry(QtCore.QRect(QPoint(x0+self.offsetX,y0+self.offsetY), 
                                                 QPoint(x1+self.offsetX,y1+self.offsetY)).normalized())
        self.zoomWidget.show()   
        if x0 > x1: x0, x1 = x1, x0
        if y0 > y1: y0, y1 = y1, y0
        #print "x0=%s, y0=%s, x1=%s, y1=%s" % (x0,y0,x1,y1)
        v = self.defineViewWindow(x0, y0, x1, y1, setData=False)
        if v!=False:
            #print "on_mouse_release: ", v 
            self.LT, self.RB = v 
            
        else: self.zoomWidget.hide()


    ###################################
    # Author: Lan
    # def: calcPanScale() 201508
    #     apply new pans and scales into self.program and self.gProgram
    def applyNewPanScale(self):
        for i in range(len(self.data)):
            self.program[i]['u_scale'] = (self.canvScaleT, self.canvScaleV)
            self.program[i]['u_pan'] = (self.panT, self.panV )
        
        if self.gtProgram != None: 
            self.gtProgram[ 'u_scale'] = (self.canvScaleT, self.canvScaleV)
            self.gtProgram['u_pan'] = (self.panT, self.panV )
        if self.gdProgram != None: 
            self.gdProgram[ 'u_scale'] = (self.canvScaleT, self.canvScaleV)
            self.gdProgram['u_pan'] = (self.panT, self.panV )

    ###################################
    # Author: Lan
    # def: trimData() 201508
    #    cut off the stations and time outside the selection
    #     + if a station in deepRemoved list, it will have no value 
    #     + at the 2 edges if the time values need to be added, PH5 values will use center value
    def trimData(self, D):
        #print "\ntrimData"
        # self.startStatId: the start station Id of the beginning of this window
        # startStatId:  the start station Id of this zoomed section (LT)
        #    (may cut off one station if that part is minor)
        LT = self.LT
        RB = self.RB
        # in case of indexes go in opposite or der of distance offset, => need to switch index value
        # do it for trimData() only, if other parts have problem, will consider changing later
        if LT['index'] > RB['index']: LT, RB = self.RB, self.LT
        orgStartId = self.startStatId
        startStatId = LT['index'] 
        if LT['sentVal'] > LT['sentCenter']:
            startStatId +=1
        
        # self.endStatId: the end station Id consider the beginning of this window
        # startStatId:  the end station Id of this zoomed section (RB)
        #    (may cut off one station if that part is minor)
        endStatId = RB['index']
        if RB['sentVal'] < RB['sentCenter']:
            endStatId -=1
 
        index = 0
        newData = []
        timeTop = self.LT['sentTimeVal']
        timeBot = self.RB['sentTimeVal']
        
        for i in range(startStatId, endStatId+1):
            if self.control.metadata[i+orgStartId]['seq'] in self.control.PH5Info['deepRemoved']: 
                newData.append( np.zeros(0,
                                    dtype=[('a_position', np.float32, 2),
                                           ('a_color', np.float32, 3),
                                           ('a_index', np.float32, 1)]) )
                index +=1
                continue
            
            timeVals = D[i+orgStartId]['a_position'][:, 0]
            ADD = self._findTrimKeepList(i, timeVals, timeTop, timeBot)
            if ADD==False: return
            trimKeepList, addLT, addRB, aSize = ADD

            #try:                 
            
            newData.append( np.zeros(aSize,
                                dtype=[('a_position', np.float32, 2),
                                       ('a_color', np.float32, 3),
                                       ('a_index', np.float32, 1)]) )
            if aSize>0: 
                T = D[i]['a_position'][:, 0][trimKeepList]
                V = D[i]['a_position'][:, 1][trimKeepList]
                aColor = D[i]['a_color'][0]
                center = self.control.statLimitList[i+orgStartId].mean()

                    
                startT = [timeTop]
                endT = [timeBot]
                # use center as the value to add in
                # choose to add at the top or end of the list depend on the time direction
                if self.control.upRbtn.isChecked():
                    if addLT : 
                        T = np.append(T, startT )
                        V = np.append(V, center)
                    if addRB:
                        T = np.insert(T, 0, endT)
                        V = np.insert(V, 0, center)
                else:                       
                    if addLT : 
                        T = np.insert(T, 0, startT )
                        V = np.insert(V, 0, center)
                    if addRB:
                        T = np.append(T, endT)
                        V = np.append(V, center)

                newData[index]['a_position'][:, 0] = T
                newData[index]['a_position'][:, 1] = V
                newData[index]['a_color'] = np.tile(aColor,(aSize,1))
                newData[index]['a_index'] = np.repeat(0,aSize)

            index +=1
            """
            except Exception, e:   
                print e
                print "trimData:i=%s, aSize=%s, error2:%s" % (i,aSize,e)
                break
            """
        if self.parent.title == "Main Window":
            self.control.setAllReplotBtnsEnabled(False, resetCanvas=False)
            
        #self.parent.startStatId = self.startStatId = orgStartId + startStatId
        self.startStatId = orgStartId + startStatId
        self.parent.endStatId = self.endStatId = orgStartId + endStatId     
        return newData

    ###################################
    # Author: Lan
    # def: _findTrimKeepList() 201508
    #    For each station, based on the selection window, look for what values needed to be kept.
    #    If the time values at the 2 edges are not in the trimKeepList,
    #    require to add the time values
    def _findTrimKeepList(self, i, timeVals, timeTop, timeBot):
        addLT = False
        addRB = False
        aSize = 0
        #
        try:
            # the list of index inside LT and RB 
            trimKeepList = np.where( (timeTop<=timeVals) & (timeVals<=timeBot) )[0]

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
            
            if aSize==0 \
                and timeTop > timeVals.min() \
                and timeBot < timeVals.max():
                # this may happen because of the simplification cut off the data approx to avg
                aSize = 2
                addLT = True
                addRB = True
                #print "statId=%s change size of data[%s] from ZERO to %s" % (i+orgStartId,i, aSize)
                
            if aSize==0: pass
                #print "statId=%s size of data[%s] is ZERO" % (i+orgStartId,i)
            
        except Exception, e:   
            print e
            print "trimData:i=%s, aSize=%s, error1:%s" % (i,aSize,str(e))
            return False
        
        return trimKeepList, addLT, addRB, aSize

    ###################################
    # Author: Lan
    # def: onTrim4Select() 201508
    # cut off data outside the selected section
    # change pans, scale to fit the selected section into the displaying window 
    def onTrim4Select(self, evt):
        if self.LT ==None: return   
        self.zoomWidget.hide()
        self.data = self.trimData(self.data)
        self._calcPanScale(self.LT, self.RB)
        
        self.mainMinY, self.mainMaxY = self.getMinMaxY(self.LT, self.RB)    # to define lim in self.painting
        self.parent.canvScaleT, self.parent.canvScaleV = (self.canvScaleT, self.canvScaleV)
        self.parent.panT, self.parent.panV = (self.panT, self.panV)
        self.feedData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        self.gtData, self.gdData,self.timeY, self.tLabels, self.dLabels = self.buildGrid()
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
        if minY > maxY: minY, maxY = maxY, minY
        return minY, maxY

    ###################################
    # Author: Lan
    # def: onPassSelect() 201508
    # pass the job to supportWindow.initSupportData() which will:
    #    cut off data outside the selected section
    #    change pans, scale to fit the selected section into the displaying window         
    def onPassSelect(self, evt):
        self.zoomWidget.hide()      
        self.control.supportCanvas.initSupportData(self, self.LT, self.RB)
        self.control.supportPlot.setEnabled(True)
    ###################################
    # Author: Lan
    # def: update_scale(): 201507
    #    recalc limList (limit of displaying for each station)
    def update_scale(self):
        self.canvScaleT, self.canvScaleV = self.program[0]['u_scale']
        self.panT, self.panV = self.program[0]['u_pan']
        L1 = self.startStatId
        L2 = L1 + len(self.data)
        self.limList = ( self.canvScaleV*(self.control.statLimitList[L1:L2] + self.panV ) + 1 ) * self.width * 0.5

        
    ###################################
    # Author: Lan
    # def: calcPanScale() 201509
    #    recalc. pans, scales, limList for onTrim4SelectAction() 
    #        or initSupportData() which is call in onPassSelectAction
    def _calcPanScale(self, LT, RB):
        self.panT = -( LT['sentTimeVal'] + RB['sentTimeVal'])/2.
        self.panV = -( LT['sentVal'] + RB['sentVal'] )/2.
        
        self.canvScaleT = 2/abs( LT['sentTimeVal'] - RB['sentTimeVal'] )
        self.canvScaleV = 2/abs( LT['sentVal'] - RB['sentVal'] )
        
        L1 = self.startStatId
        L2 = L1 + len(self.data)
        self.limList = ( self.canvScaleV*(self.control.statLimitList[L1:L2] + self.panV ) + 1 ) * self.width * 0.5

    ###################################
    # Author: Lan
    # def: _zoomTo() 201511
    # change pans, scale to fit Left-Top, Right-Bottom positions into the displaying window    
    def _zoomTo(self, LT, RB):
        self._calcPanScale(LT, RB)
        self.applyNewPanScale()
        self.gtData, self.gdData, self.timeY, self.tLabels, self.dLabels = self.buildGrid()
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
        if self.LT == None: return
        self.zoomWidget.hide()
        self._zoomTo(self.LT, self.RB)

    ###################################
    # Author: Lan
    # def: onRight() 201511
    # zoom to the new section which move to the right self.parent.distance      
    def onRight(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)

        newLT = {}
        newLT['sentVal'] = LT['sentVal'] - float(self.parent.distance.text())*1000*2/self.control.totalSize
        newLT['sentTimeVal'] = LT['sentTimeVal']
        
        newRB = {}
        newRB['sentVal'] = RB['sentVal'] - float(self.parent.distance.text())*1000*2/self.control.totalSize
        newRB['sentTimeVal'] = RB['sentTimeVal']      
          
        if newRB['sentVal'] < -1: return
        self._zoomTo(newLT, newRB)

    ###################################
    # Author: Lan
    # def: onLeft() 201511
    # zoom to the new section which move to the left self.parent.distance   
    def onLeft(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)
        newLT = {}
        newLT['sentVal'] = LT['sentVal'] + float(self.parent.distance.text())*1000*2/self.control.totalSize
        newLT['sentTimeVal'] = LT['sentTimeVal']
        
        newRB = {}
        newRB['sentVal'] = RB['sentVal'] + float(self.parent.distance.text())*1000*2/self.control.totalSize
        newRB['sentTimeVal'] = RB['sentTimeVal']
        
        if newLT['sentVal'] > 1: return
        self._zoomTo(newLT, newRB)        

    ###################################
    # Author: Lan
    # def: onZoomOutW() 201511
    # zoom to the new section which horizontally zoom out self.parent.distance each side
    def onZoomOutW(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)
        newLT = {}
        newLT['sentVal'] = LT['sentVal'] - float(self.parent.distance.text())*1000*2/self.control.totalSize
        newLT['sentTimeVal'] = LT['sentTimeVal']
        
        newRB = {}
        newRB['sentVal'] = RB['sentVal'] + float(self.parent.distance.text())*1000*2/self.control.totalSize
        newRB['sentTimeVal'] = RB['sentTimeVal']
        if newRB['sentVal']-newLT['sentVal']>6: return
        self._zoomTo(newLT, newRB)    
        
        
    ###################################
    # Author: Lan
    # def: onZoomInW() 201511
    # zoom to the new section which horizontally zoom in self.parent.distance each side  
    def onZoomInW(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)
        newLT = {}
        newLT['sentVal'] = LT['sentVal'] + float(self.parent.distance.text())*1000*2/self.control.totalSize
        newLT['sentTimeVal'] = LT['sentTimeVal']
        
        newRB = {}
        newRB['sentVal'] = RB['sentVal'] - float(self.parent.distance.text())*1000*2/self.control.totalSize
        newRB['sentTimeVal'] = RB['sentTimeVal']

        if newLT['sentVal']>newRB['sentVal']: return
        self._zoomTo(newLT, newRB)  

    ###################################
    # Author: Lan
    # def: onUp() 201511
    # zoom to the new section which move up self.parent.time                 
    def onUp(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)
        
        newLT = {}
        newLT['sentTimeVal'] = LT['sentTimeVal'] + float(self.parent.time.text())*1000*self.control.scaleT
        newLT['sentVal'] = LT['sentVal']      
        
        newRB = {}
        newRB['sentTimeVal'] = RB['sentTimeVal'] + float(self.parent.time.text())*1000*self.control.scaleT
        newRB['sentVal'] = RB['sentVal'] 
        
        if newLT['sentTimeVal'] > 1: return
        self._zoomTo(newLT, newRB)    

    ###################################
    # Author: Lan
    # def: onDown() 201511
    # zoom to the new section which move down self.parent.time          
    def onDown(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)
        
        newLT = {}
        newLT['sentTimeVal'] = LT['sentTimeVal'] - float(self.parent.time.text())*1000*self.control.scaleT
        newLT['sentVal'] = LT['sentVal']      
        
        newRB = {}
        newRB['sentTimeVal'] = RB['sentTimeVal'] - float(self.parent.time.text())*1000*self.control.scaleT
        newRB['sentVal'] = RB['sentVal']
        
        if newRB['sentTimeVal'] < -1: return
        self._zoomTo(newLT, newRB)    

    ###################################
    # Author: Lan
    # def: onZoomInH() 201511
    # zoom to the new section which vertically zoom in self.parent.time each side                   
    def onZoomInH(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)
        #direct = -1 if self.control.upRbtn.isChecked() else 1
        
        newLT = {}
        newLT['sentTimeVal'] = LT['sentTimeVal'] + float(self.parent.time.text())*1000*self.control.scaleT
        newLT['sentVal'] = LT['sentVal']  
        
        newRB = {}
        newRB['sentTimeVal'] = RB['sentTimeVal'] - float(self.parent.time.text())*1000*self.control.scaleT
        newRB['sentVal'] = RB['sentVal'] 
        
        if newLT['sentTimeVal'] > newRB['sentTimeVal']: return
        self._zoomTo(newLT, newRB)    
        
    ###################################
    # Author: Lan
    # def: onZoomOutH() 201511
    # zoom to the new section which vertically zoom out self.parent.time each side   
    def onZoomOutH(self, evt):
        LT, RB = self.defineViewWindow(0, 0, self.width, self.height)
        #direct = -1 if self.control.upRbtn.isChecked() else 1
        
        newLT = {}
        newLT['sentTimeVal'] = LT['sentTimeVal'] - float(self.parent.time.text())*1000*self.control.scaleT
        newLT['sentVal'] = LT['sentVal']  
        
        newRB = {}
        newRB['sentTimeVal'] = RB['sentTimeVal'] + float(self.parent.time.text())*1000*self.control.scaleT
        newRB['sentVal'] = RB['sentVal'] 
        
        if newRB['sentTimeVal'] - newLT['sentTimeVal']>6: return
        self._zoomTo(newLT, newRB)    
        
    ###################################
    # Author: Lan
    # def: on_mouse_press(): 201507
    #    shit + right click on a station to show the info of that station
    #    self.select: show the starting point of selection section
    def on_mouse_press(self, event):
        v = (self.enableDrawing, self.select, event)
        #print "on_mouse_release enableDrawing=%s, select=%s, event=%s" % v
        #global pointerWidget; pointerWidget.hide()
        for i in range(3): self.parent.statSelectors[i].hide()
        #print "on_mouse_press, self.parent.title=", self.parent.title
        if not self.enableDrawing: return 
        control = self.control
        x,y = event._pos
        #pointerWidget.move(self.parent.mapToGlobal(QPoint(x, y+self.offset))); pointerWidget.show()
        #modifiers = QtGui.QApplication.keyboardModifiers()
        if event._button == 2:          
            dataList = self.locateDataPoint(x, y, getInfo=True)
            #print "on_mouse_press len(d)=", len(dataList)
            #print dataList
            for ip in control.infoPanels: ip.hide()

            count = 0
            for d in dataList:
                info = ""
                self.parent.statSelectors[count].setGeometry(d['statX']-2+self.offsetX,self.offsetY, 4, 4)
                self.parent.statSelectors[count].show() 
                #count +=1
                statData = control.metadata[d['statId']]
                #info += "statId:" + str(d['statId'])
                info += "Sequence: " + str(statData['seq'])
   
                if control.correctionCkb.isChecked() or control.vel!=None:
                    #print "don't need rel Time"
                    info += "\n** Time(ms): " + str(d['dispTimeVal'])
                    #info += "\n*****min:" + str(self.data[d['statId']]['a_position'][:, 0].min())
                    #info += "\n*****max:" + str(self.data[d['statId']]['a_position'][:, 0].max())
                else:
                    #print "need rel Time"
                    info += "\n** Displayed Time(ms) : " + str(d['dispTimeVal'])
                    info += "\n** Relative time(ms): " + str(d['dispTimeVal']+statData['clockDriftCorr'])
                    
                info += "\n** PH5Value:" + str(d['PH5Val']) 
                info += "\n** Min PH5Value:" + str(d['PH5Min'])
                info += "\n** Max PH5Value:" + str(d['PH5Max']) 
                info += "\nAbsolute Time:" + str(statData['absStartTime'])   
                info += "\nArrayId: " + str( statData['arrayId'])
                info += "\nEventId: " + str( statData['eventId'])
                info += "\nStationId: " + str(statData['stationId'])
                info += "\nDasSerial: " + str(statData['dasSerial'])
                #info += "\nStartTime: " + str(TimeDOY.epoch2passcal(statData['startTime']))
                #info += "\nStopTime: " + str(TimeDOY.epoch2passcal(statData['stopTime']))
                if control.stationSpacingUnknownCkb.isChecked():
                    v = (control.nominalStaSpace.text(), 'm')
                else:
                    #v = (str(statData['distanceOffset']), str(statData['distanceOffsetUnit']))
                    v = (str(control.PH5Info['distanceOffset'][d['statId']]), 'm')
                info += "\nDistanceOffset: %s (%s)" % v
                
                info += "\nClockDriftCorrection: %s (ms)" % str(statData['clockDriftCorr'])
                if not control.correctionCkb.isChecked():
                    info += "(Not apply)"
                
                vCorr = "N/A"
                if control.vel!=None:
                    vCorr = str(statData['redVelCorr']) + " (ms)" 
                info += "\nVelocityReductionCorrection: %s" % vCorr
                info += "\nTotalCorrection: %s (ms)" % str(statData['totalCorr'])
                #info += "\nClockOffset: " + str(statData['clockOffset'])
                info += "\nLattitude: " + str(statData['lat'])
                info += "\nLongtitude: " + str(statData['long'])
                info += "\nElevation: %s (%s)" % (statData['elev'], statData['elevUnit'])
                control.infoPanels[count].showInfo(info, self, d['statId'])
                if count>2: break
                count +=1
                
            if count>0:
                self.control.infoParentPanel.setGeometry(0, 10,200, 350)
                self.control.infoParentPanel.show()
                self.control.infoParentPanel.raise_()

        elif self.select:
            self.zoomWidget.setGeometry(QtCore.QRect(QPoint(x+self.offsetX,y+self.offsetY), 
                                            QPoint(x+self.offsetX+5,y+self.offsetY+5)).normalized())
            self.zoomWidget.show()
    ###################################
    # Author: Lan
    # def: locateDataPoint(): 201507
    #    calc the time, value, statId corresponding to the position  
    def locateDataPoint(self, x, y, getInfo=None):
        #print "locateDataPoint, x=%s, y=%s" % (x,y)
        returnVal = False
        secId = -1
        resultList = []
        direct = -1 if self.control.upRbtn.isChecked() else 1
        enough = False
        # self.limList: list of postion ranges on the display for stations 
        # - 2 contiguous stations can be overlaped
        for i in range(len(self.limList)):
            if returnVal != False:
                resultList.append(returnVal)
                # start secId from the first return value
                secId = i       
                returnVal = False
                if enough: break
            # once starting secId (secId>0), it is set to value 'i' until no more to return (returnVal=False), 
            # then i > secId => finish trying to get returnVal
            if secId>0 and i> secId: break  
            statId = None
            # when x belong to one station
            v = (self.limList[i][0],self.limList[i][1], x)
            if x>=self.limList[i][0] and x<=self.limList[i][1]:
                returnVal = False               # reset returnVal
                # i: index for stuffs belong to canvas
                # statId: index for stuffs belong to control
                statId = i + self.startStatId
            # when getting postion for selected section
            # if the edge not belong to any stations 
            #=> add the beginning or the last station respectively 
            elif getInfo==None:
                minLim = self.limList.min()
                maxLim = self.limList.max()
                if  x<=minLim:
                    i = np.where(self.limList==minLim)[0][0]
                    statId = i + self.startStatId
                    enough = True               # to prevent continuing looping through limList
                elif x>=maxLim:
                    i = np.where(self.limList==maxLim)[0][0]
                    statId = i + self.startStatId
                    enough = True               # to prevent continuing looping through limList
                elif i<len(self.limList)-1 and x>self.limList[i][1] and x<self.limList[i+1][0]:
                    #print "x=%s [%s - %s] [%s - %s]" % (x, self.limList[i][0],self.limList[i][1],self.limList[0][0], self.limList[-1][1])
                    statId = i + self.startStatId
                    enough = True
            # statId!=None: there is value to be processed
            
            if statId !=None:  
                statX = self.limList[i].mean()
                # sentTimeVal: timeVal in range (-1,1) that has been sent to canvas to draw
                sentTimeVal = ((2.*y/self.height-1)/self.canvScaleT - self.panT)
                # dispTimeVal: timeVal shown on the axisY
                # relVal: if choose not to apply any reductions on the drawing,
                #        the real timeVal on each station may be varied from the value on axisY.
                #        This relative  value is the value with all the reductions added
                dispTimeVal = (direct*sentTimeVal +1)/self.control.scaleT  + self.control.minT

                """#double check
                timeIndex = int(round(dispTimeVal / self.control.PH5Info['interval']))
                print "statId=%s, timeIndex:%s" %  (statId,timeIndex)
                if timeIndex in self.control.keepList[statId]:
                    newValIndex = self.control.keepList[statId].index(timeIndex)
                    comparePH5Val = self.control.ph5val[statId][newValIndex]
                    print "compare with PH5Val:", comparePH5Val
                """
                sentMin = self.control.statLimitList[statId][0]
                sentMax = self.control.statLimitList[statId][1]

                sentCenter = (sentMin+sentMax)/2
                orgCenter =  (sentCenter + 1)*self.control.maxVal/2
                valCenter =  (self.control.metadata[statId]['minmax'][1]+self.control.metadata[statId]['minmax'][0])/2
                
                orgZero = orgCenter - valCenter*self.control.scaleVList[statId]

                sentVal = (x*2./self.width -1)/self.canvScaleV  - self.panV
                """#double check
                if timeIndex in self.control.keepList[statId]:
                    val = self.data[i]['a_position'][:, 1][ newValIndex]
                    print "sentVal=%s compare with val=%s" % (sentVal,val)
                """   
                PH5Val = ((sentVal+1)*self.control.maxVal/2 - orgZero)/self.control.scaleVList[statId]

                PH5Min = ((sentMin+1)*self.control.maxVal/2 - orgZero)/self.control.scaleVList[statId]
                PH5Max = ((sentMax+1)*self.control.maxVal/2 - orgZero)/self.control.scaleVList[statId]
                returnVal = {'statId': statId, 
                             'index': i,
                             'PH5Val': int(round(PH5Val)), 
                             'dispTimeVal': dispTimeVal, 
                             'sentTimeVal': sentTimeVal, 
                             'sentVal': sentVal,
                             'sentCenter': sentCenter,
                             'PH5Min': PH5Min,
                             'PH5Max': PH5Max,
                             'statX': statX}
        # get the last value when loop is end (the returnVal is of the last station)
        if returnVal != False:  
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
        dialog.open(self.pr)    #don't know why dialog.exec_()doesn't work

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
        vals = PrintSaveParaDialog.print_save(self, self.printType, 'inch', (paperRect.width(),paperRect.height()) )
        if vals==None: return
        w, h, printType = vals[0], vals[1], vals[2]
        start = time.time()
        phase = "Printing"
        showStatus(phase, '')
        statusBar.showMessage(statusMsg)

        # clear the old figure
        plt.clf()
        fig = plt.figure(1,dpi=100)  
        # set new w, h for new image
        fig.set_size_inches(w, h, forward=True) # set forward=True or it always keep w, h of the first setting
        # set tight layout to save space for image
        fig.set_tight_layout(True)
        # plot data
        self.painting(printType)
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
        qp.drawPixmap(0,0, pixmap)
        qp.end()   

        end = time.time()
        showStatus("","Done Printing in %s seconds" % (end-start))
        # delete the file test.png that has been used as the media 
        # to send image from plt to printer 
        try:
            os.remove('temp.png')
        except: pass
        
    ###################################
    # Author: Lan
    # def: save2file():201509
    # receive saveType: save_M, save_MZ, save_S, save_SZ
    # let user adjust size of image and file format by calling PrintSaveParaDialog
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
        vals = PrintSaveParaDialog.print_save(self, saveType, 'pixels', (w, h) )
        if vals==None: return 
        w, h, saveType, fileformat = vals[0], vals[1],vals[2], vals[3]
        
        # QFileDialog to set the name of the new image file                
        dialog = QtGui.QFileDialog(self.parent)
        dialog.setFileMode(QtGui.QFileDialog.AnyFile)
        fname = dialog.getSaveFileName(self.parent, 'Save As', '', '*.%s' % fileformat)
        if fname =='': return
         
        if "." + fileformat not in fname:
            fname = fname + "." + fileformat
        print "Image will be saved to:", fname
        
        showStatus("Preparing","")
        start = time.time()
        staNo = self.control.PH5Info['numOfStations'] 
        # clear the old figure
        plt.clf()
        fig = plt.figure(1, dpi=100)
        #if fileformat=='svg':
        #    fig.set_size_inches(w/10, h/10, forward=True)
        #else:
        fig.set_size_inches(w/100, h/100, forward=True)
        # set tight layout to save space for image
        fig.set_tight_layout(True)
        # plot data
        self.painting(saveType)
        
        # remove the old five before saving the new one
        try:
            os.remove(fname)
        except: pass
        # save figure with dpi=100. The dpi and w, h has been tried to get the right size for the file
        if fileformat=='svg':
            plt.savefig(str(fname))
        else:
            plt.savefig(str(fname), dpi=1000)

        end = time.time()
        
        showStatus("","Done Saving in %s seconds" % (end-start))       
        
    ###################################
    # Author: Lan
    # def: painting():201509
    # plot data using matplotlib package
    # all data just need to be the same scale (using the sentXXX), 
    #   1. plot data    2. plot gridlines   3. plot H/V labels + title   4. plot axis labels 
    #   to paint the zoomview: 
    #    + limit stations
    #    + draw the whole data of the station in that window (data after trimming)
    #    + use ax.set_ylim to limit
    def painting(self, psType):
        conf = self.control.conf

        direct = -1 if self.control.upRbtn.isChecked() else 1
        labelPos = self.labelPos
        if 'Z' in psType:   # paint the zoomed view
            v = self.defineViewWindow(0, 0, self.width, self.height)
            if v!=False: LT, RB = v
            minY, maxY = self.getMinMaxY(LT, RB)
            startId = LT['index']
            if LT['sentVal'] > LT['sentCenter']: startId +=1
            endId = RB['index']
            if RB['sentVal'] < RB['sentCenter']: endId -=1

            timeY = self.timeY[self.gridT['start']:self.gridT['end']]
        else:               # paint the starting view ( after trimming)
            startId = 0
            endId = len(self.data) - 1
            # if this has been zoom from the starting scale
            # => need to rebuild grid
            if self.canvScaleT != self.parent.canvScaleT:
                #gtData, gdData, timeY, tLabels, dLabels = self.buildGrid()
                timeY = self.timeY
                p = self.parent
                # self.labelPos has been limitted, need to recreate
                labelPos = self.resiteLabels(p.panT, p.panV, p.canvScaleT, p.canvScaleV)
            else:
                timeY = self.timeY[self.gridT['start']:self.gridT['end']]
                
            minY = self.mainMinY
            maxY = self.mainMaxY         
            
        minX = self.data[startId]['a_position'][:, 1].min()
        maxX = self.data[endId]['a_position'][:, 1].max()
        thick = conf['plotThick'] if conf.has_key('plotThick') else .5
        # plot stations one by one
        for i in range(startId, endId+1):
            if i % 10 == 0: showStatus("Plotting: ", "%s/%s" % (i, endId-startId+1))
            if self.control.metadata[i+self.startStatId]['seq'] \
               in self.control.PH5Info['deepRemoved']: continue
            plt.plot(self.data[i]['a_position'][:, 1], 
                     direct*self.data[i]['a_position'][:, 0],
                     c=self.data[i]['a_color'][0], linewidth=thick)
                      
        showStatus("Gridding","")

        thick = conf['gridThick'] if conf.has_key('gridThick') else 1
    
        if self.gtProgram and self.control.horGridCkb.isChecked():
            for i in range(len(timeY)):
                plt.plot( [minX, maxX], 
                          [timeY[i], timeY[i]],'--',
                          c=QColor(conf['gridColor']).getRgbF()[:3], linewidth=thick )
            
        ax = plt.subplot(111)
        ax.set_xlim(minX, maxX)
        ax.set_ylim(minY, maxY)
        graphName = self.PH5View.graphName 
        if conf.has_key('addingInfo'): 
            graphName += conf['addingInfo']
        fSize = conf['titleFSize'] if conf.has_key('titleFSize') else 12
        plt.title(graphName, fontsize=fSize)
        if conf.has_key('hLabel'):
            fSize = conf['hLabelFSize'] if conf.has_key('hLabelFSize') else 9
            plt.xlabel(conf['hLabel'], fontsize=fSize)            
        if conf.has_key('vLabel'):
            fSize = conf['vLabelFSize'] if conf.has_key('vLabelFSize') else 9
            plt.ylabel(conf['vLabel'], fontsize=fSize)         
        x = []
        xLabel = []
        y = []
        yLabel = []
        for lbl in labelPos:
            if lbl.has_key('t'):
                if minY<=lbl['t']<=maxY:
                    y.append(lbl['t'])
                    yLabel.append(lbl['text'])
                #else: print "[%s-%s] lbl['t']=%s" % (minY, maxY, lbl['t'])
            else:
                if minX<=lbl['d']<=maxX:
                    x.append(lbl['d'])
                    xLabel.append(lbl['text'])
                    #print "xPos=%s, xtext=%s" % (lbl['d'],lbl['text'])
                #else: print "[%s-%s lbl['d']=%s" % (minX, maxX, lbl['d'])
        
        plt.tick_params(axis='both', which='major', labelsize=9)
        plt.xticks(x, xLabel)
        plt.yticks(y, yLabel)
        #plt.show()


    ###################################
    # Author: Lan
    # def: quickRemove():201511
    # to remove station:
    #    => add item to quickRemove list with key is station Id, value is color of the station
    #    => change color of station to white
    # to undo remove station:
    #    => change color of station back to the color saved in quickRemoved List
    #    => delete item corresponding to this station in quickRemoved list
    #    => b/c there are 2 canvas, item might already be deleted from quickRemoved List
    def quickRemove(self, statId, removedStatus, c=0):
        if not self.enableDrawing: return 1
        canvId = statId - self.startStatId
        if canvId<0 or canvId>=len(self.data): return 2 
        aSize = len(self.data[canvId]['a_index'])
        if removedStatus:
            self.control.PH5Info['quickRemoved'][statId] = deepcopy(self.data[canvId]['a_color'][0])
            #print self.control.PH5Info['removed'][statId].__class__.__name__
            c = QColor(QtCore.Qt.white).getRgbF()[:3]
            self.data[canvId]['a_color'] = np.tile(c, (aSize,1))
        else:  
            if c.__class__.__name__=='ndarray': c = c   
            else: c = deepcopy( self.control.PH5Info['quickRemoved'][statId] )

            self.data[canvId]['a_color'] = np.tile(c, (aSize,1))
            if statId in self.control.PH5Info['quickRemoved'].keys():
                del self.control.PH5Info['quickRemoved'][statId] 
                return c
                
        return 0         

    def updateData(self):
        if not self.enableDrawing: return
        self.feedData(self.panT, self.panV, 
                      self.canvScaleT, self.canvScaleV)
        self.update()
        self.parent.update()    
    
##########################################
############### CLASS ####################
# Author: Lan
# Updated: 201410
# CLASS: PlottingPanel
#    To keep the canvas.
#    have the toolbar for zoom/pan, select
class PlottingPanel(QtGui.QMainWindow):
    def __init__(self, control, title, x, y, w, h, isMainPlot=True):
        self.isMainPlot = isMainPlot
        self.parent = control
        QtGui.QMainWindow.__init__(self)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.title = title
        self.EXPL = EXPL ={}
        self.helpEnable = False
        self.setWindowTitle(title)
        self.canvScaleT, self.canvScaleV = (None,None)
        self.panT, self.panV = (None, None)
        # not allow to close Support Window
        if not isMainPlot: 
            self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowMinMaxButtonsHint)
        self.canvas = Canvas(self, control)

        self.mainFrame = mainFrame = QtGui.QFrame(self);self.setCentralWidget(mainFrame)
        mainHBox = QtGui.QHBoxLayout(); mainFrame.setLayout(mainHBox)
        mainHBox.setSpacing(0)
        lbl1 = QtGui.QLabel("", self)   #to keep horizontal space
        mainHBox.addWidget(lbl1)
        lbl1.setFixedHeight(0)
        lbl1.setFixedWidth(40)
                
        mainVBox = QtGui.QVBoxLayout(); mainHBox.addLayout(mainVBox)
        mainVBox.setSpacing(0)
        mainCommandPanel = QtGui.QWidget(self); mainVBox.addWidget(mainCommandPanel)
        mainCommandPanel.setFixedHeight(110)
        mainCommandBox = QtGui.QHBoxLayout();   mainCommandPanel.setLayout(mainCommandBox)
        mainCommandBox.setSpacing(0)
        helpBtn = QtGui.QPushButton('Help', mainCommandPanel)
        helpBtn.setFixedWidth(50)
        helpBtn.setFixedHeight(72)
        helpBtn.clicked.connect(self.onHelp)
        mainCommandBox.addWidget(helpBtn)
        
        reset_removeBox = QtGui.QGridLayout();     mainCommandBox.addLayout(reset_removeBox)
        reset_removeBox.setSpacing(0)
        self.resetZPBtn = resetZPBtn = QtGui.QPushButton('Reset Zoom/Pan', mainCommandPanel)
        resetZPBtn.installEventFilter(self)
        EXPL[resetZPBtn] = "Zoom to the starting scale or the scale after trimming"
        resetZPBtn.setFixedWidth(140)
        resetZPBtn.clicked.connect(self.onResetZoomPan)
        reset_removeBox.addWidget(resetZPBtn, 0, 0)

        self.undoQuickRemovedBtn = undoQuickRemovedBtn = QtGui.QPushButton('Undo QuickRemove', mainCommandPanel)
        undoQuickRemovedBtn.installEventFilter(self)
        EXPL[undoQuickRemovedBtn] = "QuickRemove happens when user checks 'QuickRemoved' in the display panel" + \
                            "\nwhich will change color of the station to white." + \
                            "\n'Undo QuickRemove will turn the station's plot back to its orginal color."
        undoQuickRemovedBtn.setFixedWidth(140)
        undoQuickRemovedBtn.clicked.connect(self.onUndoQuickRemove)
        reset_removeBox.addWidget(undoQuickRemovedBtn, 1, 0)     
        if isMainPlot:
            self.deepRemovedBtn = deepRemovedBtn = QtGui.QPushButton('DeepRemove', mainCommandPanel)
            deepRemovedBtn.installEventFilter(self)
            EXPL[deepRemovedBtn] = "After user checks 'DeepRemoved' in the display panel for a group of stations" + \
                                "\nhe/she need to click this button to make it happen." + \
                                "\n DeepRemove will completely remove the stations' data, which require more time than QuickRemove."
            deepRemovedBtn.setFixedWidth(140)
            deepRemovedBtn.clicked.connect(self.onDeepRemove)
            reset_removeBox.addWidget(deepRemovedBtn, 0, 1)  
            
            self.undoDeepRemovedBtn = undoDeepRemovedBtn = QtGui.QPushButton('Undo DeepRemove', mainCommandPanel)
            undoDeepRemovedBtn.installEventFilter(self)
            EXPL[undoQuickRemovedBtn] = "Returnd the data for the all the deep removed stations."
            undoDeepRemovedBtn.setFixedWidth(140)
            undoDeepRemovedBtn.clicked.connect(self.onUndoDeepRemove)
            reset_removeBox.addWidget(undoDeepRemovedBtn, 1, 1)    

        vbox1 = QtGui.QVBoxLayout(); mainCommandBox.addLayout(vbox1)
        vbox1.setSpacing(0)
        self.zoompanRbtn = QtGui.QRadioButton("Zoom/pan",mainCommandPanel)
        self.zoompanRbtn.installEventFilter(self)
        EXPL[self.zoompanRbtn] = "Zoom/shift the plotting according to the selected action on the right"
        self.zoompanRbtn.setFixedWidth(200)
        self.zoompanRbtn.clicked.connect(self.onZoomORSelect)
        self.zoompanRbtn.setChecked(True)
        vbox1.addWidget(self.zoompanRbtn)
        
        self.selectRbtn = QtGui.QRadioButton("Selecting",mainCommandPanel)
        self.selectRbtn.installEventFilter(self)
        EXPL[self.selectRbtn] = "Drag mouse from the starting point to the ending point\n" + \
                                "then release to create the selected area.\n" + \
                                "Select one of the actions on the right for that area"
        self.selectRbtn.setFixedWidth(150)
        self.selectRbtn.clicked.connect(self.onZoomORSelect)
        vbox1.addWidget(self.selectRbtn)
        
        vbox2 = QtGui.QVBoxLayout(); mainCommandBox.addLayout(vbox2)
        vbox2.setSpacing(0)
        #############
        self.selectSet = QtGui.QWidget(self); vbox2.addWidget(self.selectSet)
        
        selectBox = QtGui.QHBoxLayout(); self.selectSet.setLayout(selectBox)
        selectBox.setSpacing(20)
        selectBox.setAlignment(QtCore.Qt.AlignJustify|QtCore.Qt.AlignLeft)
        zoomSelectBtn = QtGui.QPushButton('Zoom Selection', self.selectSet)
        zoomSelectBtn.installEventFilter(self)
        EXPL[zoomSelectBtn] = "Zoom to the selected area. No change to data"
        zoomSelectBtn.setFixedWidth(250)
        zoomSelectBtn.clicked.connect(self.canvas.onZoomSelect)
        selectBox.addWidget(zoomSelectBtn)
        """
        trim4SelectBtn = QtGui.QPushButton("Trim for Selection", self.selectSet)
        trim4SelectBtn.installEventFilter(self)
        EXPL[trim4SelectBtn] = "Trim away the sections outside the selected area.\n" + \
                "The trimed sections are actually removed from the data to give better performance."
        trim4SelectBtn.setFixedWidth(250)
        trim4SelectBtn.clicked.connect(self.canvas.onTrim4Select)
        selectBox.addWidget(trim4SelectBtn)
        """
        if isMainPlot:
            passSelectBtn = QtGui.QPushButton("Pass Selection to Support Window", self.selectSet)
            passSelectBtn.installEventFilter(self)
            EXPL[passSelectBtn] = "Pass the selected area to the support window for viewing\n" + \
                   "while keeping the drawing on Main Window the same to go back for later review."
            passSelectBtn.setFixedWidth(250)
            passSelectBtn.clicked.connect(self.canvas.onPassSelect)
            selectBox.addWidget(passSelectBtn)
        self.selectSet.hide()
        #############
        self.zoomSet = QtGui.QWidget(self); vbox2.addWidget(self.zoomSet)
        
        zoomBox = QtGui.QGridLayout(); self.zoomSet.setLayout(zoomBox)
        zoomBox.setSpacing(10)

        zoomBox.addWidget(QtGui.QLabel('Distance (km) '), 0 ,0)
        self.distance = QtGui.QLineEdit('5', self.zoomSet)
        self.distance.setFixedWidth(60)
        zoomBox.addWidget(self.distance, 0, 1)
        
        leftBtn = QtGui.QPushButton('<', self.zoomSet)
        leftBtn.installEventFilter(self)
        EXPL[leftBtn] = "Shift the plotting to the left according to value in distance box"
        leftBtn.clicked.connect(self.canvas.onLeft)
        leftBtn.setFixedWidth(30)
        zoomBox.addWidget(leftBtn, 0, 2)
        
        rightBtn = QtGui.QPushButton('>', self.zoomSet)
        rightBtn.installEventFilter(self)
        EXPL[rightBtn] = "Shift the plotting to the right according to value in distance box"
        rightBtn.clicked.connect(self.canvas.onRight)
        rightBtn.setFixedWidth(30)
        zoomBox.addWidget(rightBtn, 0, 3)
        
        zoomInWBtn = QtGui.QPushButton('+', self.zoomSet)
        zoomInWBtn.installEventFilter(self)
        EXPL[zoomInWBtn] = "Zoom in the plotting horizontally according to value in distance box"
        zoomInWBtn.clicked.connect(self.canvas.onZoomInW)
        zoomInWBtn.setFixedWidth(30)
        zoomBox.addWidget(zoomInWBtn, 0, 4)
        
        zoomOutWBtn = QtGui.QPushButton('-', self.zoomSet)
        zoomOutWBtn.installEventFilter(self)
        EXPL[zoomOutWBtn] = "Zoom out the plotting horizontally according to value in distance box"
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
        EXPL[downBtn] = "Shift down the plotting according to value in time box"
        downBtn.clicked.connect(self.canvas.onDown)
        downBtn.setFixedWidth(30)
        zoomBox.addWidget(downBtn, 1, 3)
        
        zoomInHBtn = QtGui.QPushButton('+', self.zoomSet)
        zoomInHBtn.installEventFilter(self)
        EXPL[zoomInHBtn] = "Zoom in the plotting vertically according to value in time box"
        zoomInHBtn.clicked.connect(self.canvas.onZoomInH)
        zoomInHBtn.setFixedWidth(30)
        zoomBox.addWidget(zoomInHBtn, 1, 4)
        
        zoomOutHBtn = QtGui.QPushButton('-', self.zoomSet)
        zoomOutHBtn.installEventFilter(self)
        EXPL[zoomOutHBtn] = "Zoom out the plotting vertically according to value in time box"
        zoomOutHBtn.clicked.connect(self.canvas.onZoomOutH)
        zoomOutHBtn.setFixedWidth(30)
        zoomBox.addWidget(zoomOutHBtn, 1, 5)       
        
        mainCommandBox.addStretch(1)

        mainVBox.addWidget(self.canvas.native)

        lbl2 = QtGui.QLabel("", self)   #to keep vertical space
        mainVBox.addWidget(lbl2)
        lbl2.setFixedHeight(10)
        lbl2.setFixedWidth(0)        
        
        ############## end of axis label on panel #############
    
        self.statSelectors = []
        for i in range(3): 
            self.statSelectors.append(SelectedStation( self))
            self.statSelectors[i].hide()
        """
        self.posArrow = SelectedStation(self, showPos=True)
        self.posArrow.move(500,500)
        self.posArrow.show()
        """
        #self.setSelect(False)
        self.setGeometry(x, y, w, h)   

        self.show() 
        self.setEnabled(False)
    
        
    def setEnabled(self,state):
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
        #print "eventFilter self.helpEnable=",self.helpEnable
        if not self.helpEnable: return False
        if event.type() == QtCore.QEvent.Enter:
            if object not in self.EXPL.keys(): return False
            #print object
            P = object.pos()
            #print P
            QtGui.QToolTip.showText(self.mapToGlobal(QtCore.QPoint(P.x(), P.y()+20)), self.EXPL[object])
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
        #print "paintEvent"
        index = 0
        for lbl in self.canvas.labelPos:
            if lbl.has_key('y'):
                indent = 6*(6-len(lbl['text']))
                indent = indent if indent>0 else 0
                #print "%s => indent=%s" % (lbl['text'], indent)
                qp.drawText(1+indent, lbl['y']+5, lbl['text'])
            else:
                #print "text:'%s' len(lbl)=%s" % (lbl['text'], len(lbl['text']))
                qp.drawText(int(lbl['x']-len(lbl['text'])*3.5), self.height()-10, lbl['text'])
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
        #print "onResetAction"
        if self.canvScaleT == None: return
        C = self.canvas
        #C.startStatId = self.startStatId
        C.canvScaleT = self.canvScaleT
        C.canvScaleV = self.canvScaleV
        C.panT = self.panT
        C.panV =self.panV
        C.feedData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        C.update_scale()
        
        C.gtData, C.gdData,C.timeY, C.tLabels, C.dLabels = C.buildGrid()
        C.feedGData(self.panT, self.panV, self.canvScaleT, self.canvScaleV)
        
        C.labelPos = C.resiteLabels()
        for i in range(2): 
            self.statSelectors[i].hide()
        C.update()
        self.update() 
        
        
    def onUndoQuickRemove(self, evt):
        for i in range(len(self.parent.PH5Info['quickRemoved'].keys())):
            removId = self.parent.PH5Info['quickRemoved'].keys()[-1]
            c = self.canvas.quickRemove(removId, False)
            self.canvas.otherCanvas.quickRemove(removId, False, c)
        
        self.canvas.updateData()
        self.canvas.otherCanvas.updateData()
        for p in self.parent.infoPanels:
            p.allowRemove = False
            p.quickRemovedCkb.setCheckState(QtCore.Qt.Unchecked)
            p.allowRemove = True


    def onDeepRemove(self, evt):
        self.parent.deepRemoveStations()
        
    def onUndoDeepRemove(self, evt):
        
        for p in self.parent.infoPanels:
            p.allowRemove = False
            p.deepRemovedCkb.setCheckState(QtCore.Qt.Unchecked)
            p.allowRemove = True

        self.parent.PH5Info['deepRemoved'] = []
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
            self.canvas.defineViewWindow(0, 0, self.canvas.width, self.canvas.height)

      
###############################################
# IMPORTANT FOR MAC: display the menubar to be inside application mainwindow
if sys.platform=="darwin": 
    QtGui.qt_mac_set_native_menubar(False)  

##########################################
############### CLASS ####################
# Author: Lan
# Updated: 201410
# CLASS: PH5Visualizer
# The Widget that keep 
#    + the menu for Open File, Save, Print, Exit
#    + the tab for Control Panel, Event Panel, Array Panel
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
        self.events =[]
        helpAction = QtGui.QAction('Help', self)
        helpAction.setShortcut('F1')
        helpAction.triggered.connect(self.onHelp)
        ################## FILE MENU  #################
        self.fileAction = fileAction = QtGui.QAction('Open File', self)        
        fileAction.triggered.connect(self.onFile)
        #---------------- exit ----------------
        self.exitAction = QtGui.QAction( '&Exit', self)        
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.triggered.connect(self.closeEvent)        
        
        ################## SAVE MENU ##################     
        self.saveMAction = QtGui.QAction('Save The Whole Image from Main Window', self)
        self.saveMAction.triggered.connect(self.onSaveMainWindow)  
        self.saveMAction.setEnabled(False)   
        
        self.saveMZAction = QtGui.QAction('Save The Part of Image Showed in Main Window', self)
        self.saveMZAction.triggered.connect(self.onSaveZoomMainWindow)  
        self.saveMZAction.setEnabled(False)  

        self.saveSAction = QtGui.QAction('Save The Whole Image from Support Window', self)
        self.saveSAction.triggered.connect(self.onSaveSupportWindow)  
        self.saveSAction.setEnabled(False)   
        
        self.saveSZAction = QtGui.QAction('Save The Part of Image Showed in Support Window', self)
        self.saveSZAction.triggered.connect(self.onSaveZoomSupportWindow)  
        self.saveSZAction.setEnabled(False)  

        ################### PRINT MENU #################
        self.printMAction = QtGui.QAction('Print The Whole Image from Main Window', self)
        self.printMAction.triggered.connect(self.onPrintMainWindow)  
        self.printMAction.setEnabled(False)   
        
        self.printMZAction = QtGui.QAction('Print The Part of Image Showed in Main Window', self)
        self.printMZAction.triggered.connect(self.onPrintZoomMainWindow)  
        self.printMZAction.setEnabled(False)  

        self.printSAction = QtGui.QAction('Print The Whole Image from Support Window', self)
        self.printSAction.triggered.connect(self.onPrintSupportWindow)  
        self.printSAction.setEnabled(False)   
        
        self.printSZAction = QtGui.QAction('Print The Part of Image Showed in Support Window', self)
        self.printSZAction.triggered.connect(self.onPrintZoomSupportWindow)  
        self.printSZAction.setEnabled(False)   

        #################### SEGY MENU ##################
        self.segyAction = QtGui.QAction('SEGY', self)
        self.segyAction.triggered.connect(self.onDevelopeSegy)  
        self.segyAction.setEnabled(False)         
        ################ add menu ################
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
        
        #fileMenu.insertSeparator(self.saveMAction)
        #fileMenu.insertSeparator(self.printMAction)
        
        self.menubar.addAction(self.segyAction) 
        
        self.menubar.addAction(helpAction)
        #######################################
        
        self.tabWidget = QtGui.QTabWidget(self); self.setCentralWidget(self.tabWidget)
        self.mainControl = MainControl(self)
        self.tabWidget.addTab(self.mainControl, "Control")

        self.eventGui = ArrayGui(self, ESType='EVENT')
        self.tabWidget.addTab(self.eventGui, 'Shot Gather')
        
        self.stationGui = ArrayGui(self, ESType='STATION')
        self.tabWidget.addTab(self.stationGui, 'Receiver Gather')
         
        self.setGeometry(0, 0,700, 700)

        self.show()



    def closeEvent(self, evt=None):
        QtCore.QCoreApplication.instance().quit()
        sys.exit(application.exec_())


    def onDevelopeSegy(self):
        segyDir = os.getcwd()
        
        try:
            confFile = open('PH5Viewer.cfg', 'r+')
        except IOError, e:
            return
         
        lines = confFile.readlines()
        confFile.seek(0)
        confFile.truncate()   
        
        for line in lines:
            l = line.split(":") 
            if l[0] == 'SegyDir': 
                segyDir = l[1].strip()
                lines.remove(line)
                break
        
        confFile.writelines( lines)
        
        segyDir = QtGui.QFileDialog.getExistingDirectory(self, 'SEGY output directory', segyDir,
                                                         QtGui.QFileDialog.ShowDirsOnly)
        
        confFile.write("\nSegyDir:%s" % segyDir)
        confFile.close()
        msg = "Enter sub directory name if you want to create a sub directory to save SEGY data,\n" + \
              "or leave it blank to save in the selected directory:"
        
        text, ok = QtGui.QInputDialog.getText(self, 'Enter Sub directory', msg)                 
        
        if ok: 
            if str(text).strip() != "": segyDir = segyDir + "/" + str(text).strip()
        else: return
        
        options = {}
        
        pathName = str(self.fname).split('/')
        options['ph5Path'] = "-p %s" % "/".join(pathName[:-1])
        options['nickname'] = "-n %s" % pathName[-1]
        options['outputDir'] = '-o %s' % segyDir

        options['length'] = "-l %s" % int(self.mainControl.timelenCtrl.text())
        options['chan'] = "-c %s" % ",".join( map(str,self.selectedChannels) )
        
        if str(self.mainControl.velocityCtrl.text()).strip() in ['0','']:
            options['redVel'] = ''
        else:
            rv = float(self.mainControl.velocityCtrl.text())/1000.0
            options['redVel'] = '-V %f' % rv

        if self.submitGui == 'STATION':
            #options['array'] = '-a %s' % self.selectedArray['arrayId']
            #options['stations'] = '.... %s' % ','.join( self.selectedStationIds )
            options['event'] = '-e %s' % self.selectedEventIds[0]
            
            options['offset'] = '-O %f' % float(self.mainControl.offsetCtrl.text())

            
            if self.mainControl.correctionCkb.isChecked():
                options['timeCorrect'] = ''
            else:
                options['timeCorrect'] = '-N'
                

            cmdStr = "ph5toseg %(event)s %(chan)s %(length)s %(offset)s " + \
                     "%(redVel)s %(timeCorrect)s %(ph5Path)s %(nickname)s %(outputDir)s" 
            
            
            
        elif self.submitGui == 'EVENT':
            options['station'] = '-S %s' % self.selectedStationIds[0]
            if len(self.selectedEventIds)==1:
                options['shotRange'] = '-r %s' % self.selectedEventIds[0]
            else:
                options['shotRange'] = '-r %s-%s' % (self.selectedEventIds[0], self.selectedEventIds[-1])
                
            cmdStr = "recvorder %(chan)s %(station)s %(shotRange)s %(length)s " + \
                     "%(redVel)s %(ph5Path)s %(nickname)s %(outputDir)s"
                
        print cmdStr % options
        os.system(cmdStr % options)       
        
    
    def onHelp(self):
        self.helpEnable = not self.helpEnable
        
        if self.helpEnable:
            cursor = QtGui.QCursor(QtCore.Qt.WhatsThisCursor)
        else: 
            cursor = QtGui.QCursor(QtCore.Qt.ArrowCursor)
            
        self.setCursor(cursor)

            
    def onFile(self):
        dialog = QtGui.QFileDialog(self)
        dialog.setFileMode(QtGui.QFileDialog.ExistingFile)
        fname = dialog.getOpenFileName(self, 'Open', '/home/field/Desktop/data', 'master.ph5') 
        #print fname

        if fname == "": return
        self.fname = fname
        self.eventGui.clearArrays()
        self.stationGui.clearArrays()
        del self.arrays
        del self.channels
        del self.events
        gc.collect()
        
        PH5Object = PH5ReaderwVispyAPI.PH5Reader()
        PH5Object.initialize_ph5(self.fname)
        PH5Object.createGraphExperiment()
        PH5Object.createGraphArrayNEvents()
        PH5Object.createGraphArraysNStations()
        self.channels = deepcopy(PH5Object.chs)
        #for l in PH5Object.graphArrays[0]['stations'] :
                #print l
        self.arrays = deepcopy(PH5Object.graphArrays)
        self.events = deepcopy(PH5Object.graphEvents)
        self.eventGui.setChannels()
        self.stationGui.setChannels()
        
        self.eventGui.setArrays()
        self.stationGui.setArrays()

        self.tabWidget.setCurrentIndex(1)    # view tab Events
        self.mainControl.setWidgetsEnabled(False)
        self.graphName = "%s %s" % (PH5Object.graphExperiment['experiment_id_s'], PH5Object.graphExperiment['nickname_s'])
        
        self.eventGui.setNotice(self.graphName)
        self.stationGui.setNotice(self.graphName)
        self.mainControl.mainPlot.setWindowTitle('Main Window -  %s' % (self.graphName))
        self.mainControl.supportPlot.setWindowTitle('Support Window -  %s' % (self.graphName))
        # close all opened files and remove PH5Object when done to save resources
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
        
    def focusInEvent(self, event): pass
        #print "FOCUSINEVENT PH5Visualizer"
        

##########################################
############### CLASS ####################
# Author: Lan
# Updated: 201410
# CLASS: MainControl - The control Gui - set the properties for graphic
# it has 3 panels which always open: 
#    + Main Window: display data's plot
#    + Support Window: give user the option of viewing 
#    + a smaller part of data, then go back to do other task quicker
#    + infoPanel: showing the info of a station when shift + right-click at that station
class MainControl(QtGui.QMainWindow):
    def __init__(self, parent):
        QtGui.QMainWindow.__init__(self)
        self.PH5View = parent
        self.conf = {}
        self.initConfig()
        self.eventId = None
        self.initUI()
        self.dfltOffset = 0
        self.dfltTimeLen = 60
        
        #self.setWindowTitle('Points')
        self.mainPlot = PlottingPanel(self, "Main Window", 270,0,1200,1100, isMainPlot=True)
        self.mainCanvas = self.mainPlot.canvas
        self.supportPlot = PlottingPanel(self, "Support Window", 290,0,1200,1100, isMainPlot=False)
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
        #self.simpSize = None
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
        #print "MainControl's attributes:", dir(self)
    ###################################
    # Author: Lan
    # def: createInfoPanel():201504
    def createInfoPanel(self):
        self.infoParentPanel = QtGui.QWidget()
        self.infoParentPanel.setWindowFlags(QtCore.Qt.Window)
        self.infoBox = QtGui.QVBoxLayout(self.infoParentPanel)
        self.infoBox.setSpacing(0)
        self.infoPanels = []
        for i in range(3):
            self.infoPanels.append(InfoPanel(self))

        
    ###################################
    # Author: Lan
    # def: setDefaultConf():201410
    # create default configuration for name and color properties
    def initConfig(self):
        # setDefaultConf
        self.defaultConf = {}
        self.defaultConf['addingInfo'] = ""    # on the title bar or at the top of saved file/ print paper
        self.defaultConf['hLabel'] = "STATION SEQUENCE"   # horizontal labels
        self.defaultConf['vLabel'] = "TIME (ms)"     # vertical labels
        self.defaultConf['patternSize'] = 15    # number of stations in the color pattern 
        self.defaultConf['plotThick'] = 0.6
        self.defaultConf['gridThick'] = 0.4
        self.defaultConf['gridColor'] = QColor(150,150,150).name()
        self.defaultConf['abnormalColor'] = QColor(QtCore.Qt.gray).name()
        self.defaultConf['showAbnormalStat'] = True
        
        self.defaultConf['plotColor'] = []      # define color in the pattern
        for i in range(self.defaultConf['patternSize']):
            self.defaultConf['plotColor'].append(QColor(QtCore.Qt.gray).name())
        
        # setFileConf
        self.fileConf = {}
        try:
            confFile = open('PH5Viewer.cfg', 'r')
        except IOError, e:
            return
        
        self.fileConf['plotColor'] = []
        lines = confFile.readlines()
        confFile.close()
        for line in lines:
            l = line.split(":") 
            if l[0] == 'addingInfo': self.fileConf['addingInfo'] = l[1].strip()
            elif l[0] == 'hLabel': self.fileConf['hLabel'] = l[1].strip()
            elif l[0] == 'vLabel': self.fileConf['vLabel'] = l[1].strip()
            elif l[0] == 'gridColor': self.fileConf['gridColor'] = l[1].strip()
            elif l[0] == 'pointColor': self.fileConf['pointColor'] = l[1].strip()
            elif l[0] == 'patternSize': self.fileConf['patternSize'] = int(l[1].strip())
            elif l[0] == 'plotThick': self.fileConf['plotThick'] = float(l[1].strip())
            elif l[0] == 'gridThick': self.fileConf['gridThick'] = float(l[1].strip())
            elif l[0] == 'abnormalColor': self.fileConf['abnormalColor'] = l[1].strip()
            elif l[0] == 'plotColor': self.fileConf['plotColor'].append(QColor(l[1].strip()))
            elif l[0] == 'showAbnormalStat':
                self.fileConf['showAbnormalStat'] = True if l[1].strip()=='True' else False

    ###################################
    # Author: Lan
    # def: initUI(): updated 201509
    # Layout of MainControl
    def initUI(self):
        self.EXPL ={}  
        mainFrame = QtGui.QFrame(self);self.setCentralWidget(mainFrame)
        mainbox = QtGui.QHBoxLayout(); mainFrame.setLayout(mainbox)
        
        vbox = QtGui.QVBoxLayout(); mainbox.addLayout(vbox)

        ############################ Time ############################
        #vbox.addWidget(QtGui.QLabel("TIME RANGE", self))
        startrangeHBox = QtGui.QHBoxLayout(); vbox.addLayout(startrangeHBox)
        startrangeHBox.addWidget(QtGui.QLabel('Start time'))
        self.startrangetimeCtrl = QtGui.QLineEdit('');  self.startrangetimeCtrl.installEventFilter(self)
        self.EXPL[self.startrangetimeCtrl] = "The start time for plotting."
        #self.startrangetimeCtrl.textChanged.connect(self.onStartTimeChange)       
        startrangeHBox.addWidget(self.startrangetimeCtrl)
        
        timerangeHBox = QtGui.QHBoxLayout(); vbox.addLayout(timerangeHBox)
        timerangeHBox.addWidget(QtGui.QLabel('Length(s) '))
        self.timelenCtrl = QtGui.QLineEdit();   self.timelenCtrl.installEventFilter(self)
        self.EXPL[self.timelenCtrl] = "The length of time for plotting."
        #self.timelenCtrl.setFixedWidth(50)
        self.timelenCtrl.textChanged.connect(self.onChangeTimeLen)
        timerangeHBox.addWidget(self.timelenCtrl )
        
        timerangeHBox.addWidget(QtGui.QLabel('Offset'))
        self.offsetCtrl = QtGui.QLineEdit('');  self.offsetCtrl.installEventFilter(self)
        self.EXPL[self.offsetCtrl] = "Move the start time of the plot relative to the shot time, seconds."
        #self.offsetCtrl.setFixedWidth(50)
        #self.offsetCtrl.textChanged.connect(self.onOffsetChange)
        timerangeHBox.addWidget(self.offsetCtrl)
        
        vbox.addStretch(1)
        vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        vbox.addStretch(1)
        ########################### Simplify  ########################
        gridBox = QtGui.QGridLayout(); vbox.addLayout(gridBox) 
        #simplifyBox = QtGui.QHBoxLayout(); vbox.addLayout(simplifyBox) 
        gridBox.addWidget(QtGui.QLabel('Ignore minor signal (0-20%)',self),0,0)

        self.distance2AvgSB = QtGui.QSpinBox(self); self.distance2AvgSB.installEventFilter(self)
        self.EXPL[self.distance2AvgSB] = "Define how low is the percentage of the signal to be ignored."
               
        #self.distance2AvgSB.setFixedWidth(45)
        self.distance2AvgSB.setRange(0,20)
        self.distance2AvgSB.setSingleStep(1)
        self.distance2AvgSB.setValue(5)
        gridBox.addWidget(self.distance2AvgSB, 0,1)
        
        self.simplifyReplotBtn = QtGui.QPushButton('Apply', self); self.simplifyReplotBtn.installEventFilter(self)
        self.EXPL[self.simplifyReplotBtn] = "Apply new percentage of signal to be ignored and replot without reread PH5 data."
        self.simplifyReplotBtn.clicked.connect(self.onApplySimplify_RePlot)
        self.simplifyReplotBtn.setFixedWidth(60)
        gridBox.addWidget(self.simplifyReplotBtn,0,2)
        
        ########################### Overlap  ########################
        #overlapBox = QtGui.QHBoxLayout(); vbox.addLayout(overlapBox)
        gridBox.addWidget(QtGui.QLabel('Overlap (0-80%):', self),1,0)
        self.overlapSB = QtGui.QSpinBox(self); self.overlapSB.installEventFilter(self)
        self.EXPL[self.overlapSB] = "Define the growing percentage of the width given for each signal."
        self.overlapSB.setRange(0,80)
        self.overlapSB.setValue(25)
        gridBox.addWidget(self.overlapSB,1,1)    
        
        self.overlapReplotBtn = QtGui.QPushButton('Apply', self)    ;   self.overlapReplotBtn.installEventFilter(self)
        self.EXPL[self.overlapReplotBtn] = "Apply new Overlap setting and replot without\n" + \
                              "reread PH5 data and recreate time values"
        self.overlapReplotBtn.clicked.connect(self.onApplyOverlapNormalize_RePlot)
        self.overlapReplotBtn.setFixedWidth(60)
        gridBox.addWidget(self.overlapReplotBtn,1,2)
        
        vbox.addStretch(1)
        
        ########################### NORMALIZE  ########################
        #normalizeBox = QtGui.QHBoxLayout(); vbox.addLayout(normalizeBox)
        self.normalizeCkb = QtGui.QCheckBox('NORMALIZE          ', self);   self.normalizeCkb.installEventFilter(self)
        self.EXPL[self.normalizeCkb] = "If selected, each station's signal will " + \
                                "grow to its entire width.\n" + \
                                "If not, use the same scale for all stations' signal.\n" + \
                                "Click 'Get Data and Plot' to replot."
        self.normalizeCkb.setCheckState(QtCore.Qt.Checked)
        gridBox.addWidget(self.normalizeCkb,2,0)     
        
        self.normalizeReplotBtn = QtGui.QPushButton('Apply', self)    ;   self.normalizeReplotBtn.installEventFilter(self)
        self.normalizeReplotBtn.clicked.connect(self.onApplyOverlapNormalize_RePlot)
        self.normalizeReplotBtn.setFixedWidth(60)
        gridBox.addWidget(self.normalizeReplotBtn, 2,2)
        
        ########################### Dirty way ########################   
        stationSpacingUnknownBox = QtGui.QHBoxLayout(); vbox.addLayout(stationSpacingUnknownBox)     
        self.stationSpacingUnknownCkb = QtGui.QCheckBox('STATION SPACING UNKNOWN', self);   self.stationSpacingUnknownCkb.installEventFilter(self)
        self.EXPL[self.stationSpacingUnknownCkb] = "If selected, use 'Nominal station spacing' " + \
                    "as space between two stations.\nClick 'Get Data and Plot' to replot."
        stationSpacingUnknownBox.addWidget(self.stationSpacingUnknownCkb)   
        self.stationSpacingUnknownCkb.clicked.connect(self.onChangeApplyStationSpacingUnknown)
        
        dOffsetBox = QtGui.QHBoxLayout(); vbox.addLayout(dOffsetBox)
        dOffsetBox.addWidget(QtGui.QLabel("Nominal station spacing(m):", self))
        self.nominalStaSpace = QtGui.QLineEdit('1000');   self.nominalStaSpace.installEventFilter(self) 
        self.EXPL[self.nominalStaSpace] = "If 'STATION SPACING UNKNOWN' is selected, " + \
                            "this will be used as space between two stations." 
        dOffsetBox.addWidget(self.nominalStaSpace)

        vbox.addStretch(1)
        #vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        vbox.addStretch(1)
        ########### apply correction/ velocity reduction? #################
        velHBox = QtGui.QHBoxLayout(); vbox.addLayout(velHBox)
        
        velHBox.addWidget(QtGui.QLabel('Reduction Velocity(m/s):     '))
        self.velocityCtrl = QtGui.QLineEdit('0',self); self.velocityCtrl.installEventFilter(self)
        self.EXPL[self.velocityCtrl] = "Reduction Velocity to apply to the plot.\n" + \
                              "Apply when the given value is > 0"
        #self.velocityCtrl.setFixedWidth(45)
        velHBox.addWidget(self.velocityCtrl)
        
        self.correctionCkb = QtGui.QCheckBox('Time Correction', self);   self.correctionCkb.installEventFilter(self)
        self.EXPL[self.correctionCkb] = "Select to include clock drift correction."
        self.correctionCkb.setCheckState(QtCore.Qt.Checked)
        vbox.addWidget(self.correctionCkb)
                    
        vbox.addStretch(1)
        vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        vbox.addStretch(1)

        ################ Properties selection ##################
        propBox = QtGui.QHBoxLayout(); vbox.addLayout(propBox)
        
        propV1Box = QtGui.QVBoxLayout(); propBox.addLayout(propV1Box)
        self.defaultPropRbtn = QtGui.QRadioButton('Default Prop.')  ; self.defaultPropRbtn.installEventFilter(self)
        self.EXPL[self.defaultPropRbtn] = "Use the default properties for names and colors."
        propV1Box.addWidget(self.defaultPropRbtn)
        
        self.fromFilePropRbtn = QtGui.QRadioButton('Previous Prop.');self.fromFilePropRbtn.installEventFilter(self)
        self.EXPL[self.fromFilePropRbtn] = "Use the properties that were use prevously.\n" + \
                              "These properties can be editted by clicking 'Name-Color Prop."
        propV1Box.addWidget(self.fromFilePropRbtn)
        self.fromFilePropRbtn.setChecked(True)

        propGroup = QtGui.QButtonGroup(self)
        propGroup.addButton(self.defaultPropRbtn)
        propGroup.addButton(self.fromFilePropRbtn)
        
        propV2Box = QtGui.QVBoxLayout(); propBox.addLayout(propV2Box)
        self.changePropBtn = QtGui.QPushButton('Name-Color Prop.', self); self.changePropBtn.installEventFilter(self)
        self.EXPL[self.changePropBtn] = "Open the Properties window for user to edit."
        self.changePropBtn.clicked.connect(self.onChangeProperties)
        self.changePropBtn.resize(self.changePropBtn.sizeHint())
        propV2Box.addWidget(self.changePropBtn)

        self.propReplotBtn = QtGui.QPushButton('Apply and RePlot', self);self.propReplotBtn.installEventFilter(self)
        self.EXPL[self.propReplotBtn] = "Apply the selected property option."
        self.propReplotBtn.clicked.connect(self.onApplyPropperty_RePlot)
        self.propReplotBtn.resize(self.propReplotBtn.sizeHint())
        propV2Box.addWidget(self.propReplotBtn)
        
        vbox.addStretch(1)
        vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        vbox.addStretch(1)      
        
        ################ grid lines ################
        gridBox = QtGui.QHBoxLayout(); vbox.addLayout(gridBox)
        self.verGridCkb = QtGui.QCheckBox('Vertical grid', self);   self.verGridCkb.installEventFilter(self)
        self.EXPL[self.verGridCkb] = "Apply vertical grid lines. Take effect right after selected"
        self.verGridCkb.setCheckState(QtCore.Qt.Checked)
        gridBox.addWidget(self.verGridCkb)   
        self.verGridCkb.clicked.connect(self.onChangeApplyGrids)
        
        self.horGridCkb = QtGui.QCheckBox('Horizontal grid', self);   self.horGridCkb.installEventFilter(self)
        self.EXPL[self.horGridCkb] = "Apply horizontal grid lines. Take effect right after selected"
        self.horGridCkb.setCheckState(QtCore.Qt.Checked)
        gridBox.addWidget(self.horGridCkb)   
        self.horGridCkb.clicked.connect(self.onChangeApplyGrids)
        
        paneBox = QtGui.QHBoxLayout(); vbox.addLayout(paneBox)
        
        paneBox.addWidget(QtGui.QLabel("ReGrid Panel"))
        self.mainWindowRbtn = QtGui.QRadioButton('Main'); self.mainWindowRbtn.installEventFilter(self)
        self.EXPL[self.mainWindowRbtn] = "New grid interval will be applied on Main Window"
        paneBox.addWidget(self.mainWindowRbtn)
        self.supportWindowRbtn = QtGui.QRadioButton('Support'); self.supportWindowRbtn.installEventFilter(self)
        self.EXPL[self.supportWindowRbtn] = "New grid interval will be applied on Support Window"
        paneBox.addWidget(self.supportWindowRbtn)
        self.mainWindowRbtn.setChecked(True)
        self.bothWindowRbtn = QtGui.QRadioButton('Both'); self.bothWindowRbtn.installEventFilter(self)
        paneBox.addWidget(self.bothWindowRbtn)
        #self.mainWindowRbtn.setChecked(True)        
        
        panelGroup = QtGui.QButtonGroup(self)
        panelGroup.addButton(self.mainWindowRbtn)
        panelGroup.addButton(self.supportWindowRbtn)
        panelGroup.addButton(self.bothWindowRbtn)
         
        gridHBox = QtGui.QHBoxLayout(); vbox.addLayout(gridHBox)
        gridVBox = QtGui.QVBoxLayout(); gridHBox.addLayout(gridVBox)
        
        horGridHBox = QtGui.QHBoxLayout(); gridVBox.addLayout(horGridHBox)
        horGridHBox.addWidget(QtGui.QLabel("H. Grid Interval (s)"))
        self.horGridIntervalSB = QtGui.QDoubleSpinBox(self)        ; self.horGridIntervalSB.installEventFilter(self)
        self.EXPL[self.horGridIntervalSB] = "Horizontal Grid Interval in second"
        self.horGridIntervalSB.setDecimals(1)
        self.horGridIntervalSB.setSingleStep(.1)
        self.horGridIntervalSB.setFixedWidth(80)
        horGridHBox.addWidget(self.horGridIntervalSB)
        
        verGridHBox = QtGui.QHBoxLayout(); gridVBox.addLayout(verGridHBox)
        verGridHBox.addWidget(QtGui.QLabel("V. Grid Interval (km)"))
        self.verGridIntervalSB = QtGui.QSpinBox(self)        ; self.verGridIntervalSB.installEventFilter(self)
        self.EXPL[self.verGridIntervalSB] = "Horizontal Grid Interval in second"
        self.verGridIntervalSB.setFixedWidth(80)
        self.verGridIntervalSB.setValue(10)
        verGridHBox.addWidget(self.verGridIntervalSB)
                
        self.regridBtn = QtGui.QPushButton('ReGrid', self)  ; self.regridBtn.installEventFilter(self)
        self.EXPL[self.regridBtn] = "Apply new grid intervals"
        self.regridBtn.setFixedWidth(70)
        self.regridBtn.setFixedHeight(70)
        self.regridBtn.clicked.connect(self.onRegrid) 
        gridHBox.addWidget(self.regridBtn)
        self.regridBtn.setEnabled(False)
        
        vbox.addStretch(1)
        vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        ########################### which direction? #################
        directionBox = QtGui.QHBoxLayout(); vbox.addLayout(directionBox)
        directionBox.addWidget(QtGui.QLabel("Time Direction"))
        self.downRbtn = QtGui.QRadioButton('Down ')     ; self.downRbtn.installEventFilter(self)
        self.EXPL[self.downRbtn] = "Drawing with time grow from top to bottom.\n" +\
                              "Take effect right after selected"
        directionBox.addWidget(self.downRbtn)
        self.downRbtn.clicked.connect(self.onChangeDirection)
        
        self.upRbtn = QtGui.QRadioButton('Up   ')       ; self.upRbtn.installEventFilter(self)
        self.EXPL[self.upRbtn] = "Drawing with time grow from bottom to top.\n" +\
                              "Take effect right after selected"
        directionBox.addWidget(self.upRbtn)
        self.upRbtn.clicked.connect(self.onChangeDirection)
        self.upRbtn.setChecked(True)
        
        direction = QtGui.QButtonGroup(self)
        direction.addButton(self.downRbtn)
        direction.addButton(self.upRbtn)    
                  
        ########### Drawing Style #################
        styleBox = QtGui.QHBoxLayout(); vbox.addLayout(styleBox)
        styleBox.addWidget(QtGui.QLabel("Drawing Style "))
        self.lineRbtn = QtGui.QRadioButton('Lines')     ; self.lineRbtn.installEventFilter(self)
        self.EXPL[self.lineRbtn] = "The style of drawing is line. Take effect right after selected."
        styleBox.addWidget(self.lineRbtn)
        self.lineRbtn.clicked.connect(self.onChangeStyle)
        self.lineRbtn.setChecked(True)
        
        self.pointRbtn = QtGui.QRadioButton('Points')   ; self.pointRbtn.installEventFilter(self)
        self.EXPL[self.pointRbtn] = "The style of drawing is points. Take effect right after selected."
        styleBox.addWidget(self.pointRbtn)
        self.pointRbtn.clicked.connect(self.onChangeStyle)
        
        styleGroup = QtGui.QButtonGroup(self)
        styleGroup.addButton(self.lineRbtn)
        styleGroup.addButton(self.pointRbtn)

        ############################################
        
        self.getnPlotBtn = QtGui.QPushButton('Get Data and Plot', self); self.getnPlotBtn.installEventFilter(self)
        self.EXPL[self.getnPlotBtn] = "Read PH5 data and plot according to all the settings."
        self.getnPlotBtn.setStyleSheet("QWidget { background-color: #d7deff }" )
        self.getnPlotBtn.clicked.connect(self.onGetnPlot) 
        vbox.addWidget(self.getnPlotBtn)        
        ########################## showing info #########################
        formDisplay1 = QtGui.QFormLayout(); vbox.addLayout(formDisplay1)

        self.sampleNoLbl = QtGui.QLabel("", self)
        formDisplay1.addRow(self.tr('No of Samp./Station:'), self.sampleNoLbl )
        
        self.intervalLbl = QtGui.QLabel("", self)
        formDisplay1.addRow(self.tr('Sample Interval (ms):'), self.intervalLbl )

        vbox.addStretch(1)
        #vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        #vbox.addWidget(Seperator(thick=2, orientation="horizontal"))
        
        gridDisplay2 = QtGui.QGridLayout(); vbox.addLayout(gridDisplay2)
        gridDisplay2.addWidget(QtGui.QLabel("TIME (ms)"), 0, 0)
        self.startTimeLbl = QtGui.QLabel('')    ;   self.startTimeLbl.installEventFilter(self)
        self.EXPL[self.startTimeLbl] = "Plotting Window's start time in milisecond"
        self.startTimeLbl.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.startTimeLbl.setFixedWidth(100)
        gridDisplay2.addWidget(self.startTimeLbl,0, 1)
        self.endTimeLbl = QtGui.QLabel('')      ;   self.endTimeLbl.installEventFilter(self)
        self.EXPL[self.endTimeLbl] = "Plotting Window's end time"
        self.endTimeLbl.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.endTimeLbl.setFixedWidth(100)
        gridDisplay2.addWidget(self.endTimeLbl, 0, 2)

        gridDisplay2.addWidget(QtGui.QLabel("STATION"), 1, 0)
        self.startStationIdLbl = QtGui.QLabel('')    ;   self.startStationIdLbl.installEventFilter(self)
        self.EXPL[self.startStationIdLbl] = "Plotting Window's start station"
        self.startStationIdLbl.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.startStationIdLbl.setFixedWidth(100)
        gridDisplay2.addWidget(self.startStationIdLbl,1, 1)
        self.endStationIdLbl = QtGui.QLabel('')      ;   self.endStationIdLbl.installEventFilter(self)
        self.EXPL[self.endStationIdLbl] = "Plotting Widnow's end station"
        self.endStationIdLbl.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.endStationIdLbl.setFixedWidth(100)
        gridDisplay2.addWidget(self.endStationIdLbl, 1, 2)
        
        gridDisplay2.addWidget(QtGui.QLabel("DISTANCE (km)"), 2, 0)
        self.startDistanceLbl = QtGui.QLabel('')    ;   self.startDistanceLbl.installEventFilter(self)
        self.EXPL[self.startDistanceLbl] = "Plotting Window's start distance in kilometer"
        self.startDistanceLbl.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.startDistanceLbl.setFixedWidth(100)
        gridDisplay2.addWidget(self.startDistanceLbl,2, 1)
        self.endDistanceLbl = QtGui.QLabel('')      ;   self.endDistanceLbl.installEventFilter(self)
        self.EXPL[self.endDistanceLbl] = "Plotting Widnow's end distance in kilometer"
        self.endDistanceLbl.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.endDistanceLbl.setFixedWidth(100)
        gridDisplay2.addWidget(self.endDistanceLbl, 2, 2)
        
        vbox.addStretch(1)
        mainbox.addStretch(1)
        extraBox = QtGui.QVBoxLayout(); mainbox.addLayout(extraBox)
        self.statusLbl = QtGui.QLabel()
        extraBox.addWidget(self.statusLbl)
        extraBox.addStretch(1)
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
            if object not in self.EXPL.keys(): return False
            #print object
            P = object.pos()
            #print P
            QtGui.QToolTip.showText(self.mapToGlobal(QtCore.QPoint(P.x(), P.y()+20)), self.EXPL[object])
            return True
        
        if self.eventId == None: return False
        errorMsg = ''
        if object == self.offsetCtrl and event.type() == QtCore.QEvent.Leave:
            try:
                offset = float(self.offsetCtrl.text())
                if offset>20 or offset<-20:
                    errorMsg = "Offset value should not be greater than 20 or less than -20"

            except Exception, e:
                errorMsg = "Offset value must be a number."
            if errorMsg != '':
                    QtGui.QMessageBox.question(self, 'Error', errorMsg, QtGui.QMessageBox.Ok)
                    self.offsetCtrl.setText("-0")
        elif object == self.timelenCtrl:
            if event.type() in [QtCore.QEvent.Leave, QtCore.QEvent.FocusOut] :
                errorMsg = self.onChangeTimeLen()
                if errorMsg != '':
                    QtGui.QMessageBox.question(self, 'Error', errorMsg, QtGui.QMessageBox.Ok)

        
        return False

    def onChangeTimeLen(self, evt=None):
        errorMsg = ''
        try:
            timeLen = float(self.timelenCtrl.text())
            # add timeLen limit here
            if timeLen > self.upperTimeLen:
                errorMsg = "Time length value must be less than event's time: %ss" % self.upperTimeLen 
                self.timelenCtrl.setText("60") 
                if evt == None:
                    return errorMsg
                else:
                    QtGui.QMessageBox.question(self, 'Error', errorMsg, QtGui.QMessageBox.Ok)
                    
            minInterval = math.ceil(10*timeLen/25)/10
            maxInterval = math.ceil(timeLen*10)/10
            self.horGridIntervalSB.setRange(minInterval, maxInterval)
            self.horGridIntervalSB.setValue(math.ceil(timeLen*10/15)/10)
            #print "timeLen=%s,minInterval=%s, maxInterval=%s, gridInterval=%s" % (timeLen, minInterval, maxInterval, math.ceil(timeLen*10/15)/10)
            
        except Exception,e:   
            #print e  
            if (evt!= None and self.timelenCtrl.text() not in ['','.']) \
              or evt == None:
                errorMsg = "Time length value must be a number."
                self.timelenCtrl.setText("60") 
                if evt==None: return errorMsg
                else: 
                    QtGui.QMessageBox.question(self, 'Error', errorMsg, QtGui.QMessageBox.Ok)
                    
        return ''
    
    ###################################
    # Author: Lan
    # def: addDisplay2(): updated 201506
    # special layout for View Window info
    def addDisplay2(self, grid, rowId, text, ctrl1, ctrl2 ):    
        grid.addWidget( QtGui.QLabel(text), rowId, 0 )
            
        grid.addWidget( ctrl1, rowId+1, 0)
        ctrl1.setStyleSheet("QWidget { background-color: white }" )
        ctrl1.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        #ctrl1.setFixedWidth(100)
        
        grid.addWidget(ctrl2, rowId+1, 1)
        ctrl2.setStyleSheet("QWidget { background-color: white }" )
        ctrl2.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        #ctrl2.setFixedWidth(100)

    ###################################
    # Author: Lan
    # def: check(): updated 201509
    # check valid sof start time range
    # check the valid of length of time range: a number>0
    # check valid of distance Offset: a number>0
    # check velocity: 
    #    if val>0: apply reduction velocity
    #    if val<=0 or not a number: not apply
    def check(self, checkTRange=False, checkDOffset=False, checkVelocity=False):
        errorMsg = ""
        if self.PH5View.submitGui=='STATION' and checkTRange:
            try:
                self.startTime = TimeDOY.passcal2epoch(self.startrangetimeCtrl.text())
            except Exception,e:
                errorMsg += "Start time format is invalid.Correct your format to:\n\tYYYY:DOY:HH:MM:SS[.MSE]\n"
            try:
                l = float(self.timelenCtrl.text())
                if l <= 0:
                    errorMsg += "Length of TIME RANGE must be greater than zero.\n"
                    
            except Exception,e:
                #print str(e)
                errorMsg += "Length of TIME RANGE must be a number greater than zero.\n"
        
        errorMsg += self.onChangeTimeLen()
        if self.stationSpacingUnknownCkb.isChecked() and checkDOffset:
            try:
                dOff = float(self.nominalStaSpace.text())
                if dOff <= 0:
                    errorMsg += "Distance Offset must be greater than zero.\n"
                    
            except Exception,e:
                #print str(e)
                errorMsg += "Distance Offset must be a number greater than zero.\n"
        
        if checkVelocity:  
            try:
                self.vel = float(self.velocityCtrl.text())
                if self.vel <= 0: self.vel = None
                    
            except Exception,e: self.vel = None
            
        if errorMsg != "" :
            QtGui.QMessageBox.question(self, 'Error', errorMsg, QtGui.QMessageBox.Ok)
            return False
        return True


    ###################################
    # Author: Lan
    # def: onChangeProperties(): updated 201411
    #   open Properties window for user to change settings for 
    #   name, color, line thickness
    def onChangeProperties(self, evt):
        Properties(self).exec_() 

    ###################################
    # Author: Lan
    # def: onChangeDirection(): updated 201506
    #    => change direction of the display vertically (according to time)
    def onChangeDirection(self, evt):
        self.mainCanvas.timeDirection()
        self.mainCanvas.update()
        self.mainPlot.update()
        self.mainPlot.activateWindow()
        self.supportCanvas.reset()
    
 
    ###################################
    # Author: Lan
    # def: onChangeStyle(): updated 201507
    #    => change displaying of the plots to lines or points
    def onChangeStyle(self, evt):
        self.mainCanvas.update()
        self.mainPlot.update()
        self.mainPlot.activateWindow()
        self.supportCanvas.update()
        self.supportPlot.update()

    ###################################
    # Author: Lan
    # def: onChangeApplystationSpacingUnknown(): updated 201509
    #    selected: 
    #        + require fake Distance Offset
    #        + applicable for non-normalized mode when all stations use the same scale
    #    not selected: (always normalize: spread to use all of the value range)
    #        + use real Distance Offset => no need to care about the fake one
    #        + although normalizeCkb is disabled, still need to check that so user won't be confused
    def onChangeApplyStationSpacingUnknown(self,evt):
        if self.stationSpacingUnknownCkb.isChecked():
            self.nominalStaSpace.setEnabled(True)
            #self.normalizeCkb.setEnabled(True)
        else:
            self.nominalStaSpace.setEnabled(False)
            #self.normalizeCkb.setCheckState(QtCore.Qt.Checked)
            #self.normalizeCkb.setEnabled(False)
    """
    ###################################
    # Author: Lan
    # def: onChangeApplyVelocity(): updated 201509
    # when apply velocity, user can set value for velocity and replot the new value           
    def onChangeApplyVelocity(self, evt=None):
        if self.velocityCkb.isChecked():
            self.velocityCtrl.setEnabled(True)
            self.velReplotBtn.setEnabled(self.allowReplot)
        else:
            self.velocityCtrl.setEnabled(False)
            self.velReplotBtn.setEnabled(False)
    
    
    ###################################
    # Author: Lan
    # def: onChangeApplySimplify(): updated 201509
    # when apply simplify, user can set value for simplifyFactor (distance2Avg) and replot the new value 
    def onChangeApplySimplify(self, evt):
        if self.simplifyCkb.isChecked():
            self.distance2AvgSB.setEnabled(True)
            self.simplifyReplotBtn.setEnabled(self.allowReplot)
        else:
            self.distance2AvgSB.setEnabled(False) 
            self.simplifyReplotBtn.setEnabled(False)     
            
    
    ###################################
    # Author: Lan
    # def: onOverlapChange(): updated 201502
    #    => change displaying number go with the slide for overlap
    def onOverlapChange(self, evt):
        overlaping = self.overlapSB.value()
        self.overlapLbl.setText(str(overlaping))
    """

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
            #print "mainWindowRbt gridIntervalSB.value()=", self.gridIntervalSB.value()
            self._regrid(self.mainCanvas, self.mainPlot)
            #print "mainWindowRbt 1 gridIntervalSB.value()=", self.gridIntervalSB.value()
        elif self.supportWindowRbtn.isChecked():
            #print "supportWindowRbt gridIntervalSB.value()=", self.gridIntervalSB.value()
            self._regrid(self.supportCanvas, self.supportPlot)
            #print "supportWindowRbt 1 gridIntervalSB.value()=", self.gridIntervalSB.value()
        else:
            #print "bothWindowRbt gridIntervalSB.value()=", self.gridIntervalSB.value()
            self._regrid(self.mainCanvas, self.mainPlot)
            #print "bothWindowRbt 1 gridIntervalSB.value()=", self.gridIntervalSB.value()
            self._regrid(self.supportCanvas, self.supportPlot)  
            #print "bothWindowRbt 2 gridIntervalSB.value()=", self.gridIntervalSB.value()          

    def _regrid(self, canvas, plot):    
        if not canvas.enableDrawing: return
        canvas.gtData, canvas.gdData, canvas.timeY, canvas.tLabels, canvas.dLabels \
            = canvas.buildGrid()
        canvas.feedGData(canvas.panT, canvas.panV, canvas.canvScaleT, canvas.canvScaleV)
        canvas.labelPos = canvas.resiteLabels()
        canvas.update()
        plot.update()
        plot.activateWindow()
        

        
    ###################################
    # Author: Lan
    # def: onGetnPlot(): updated 201509
    #    => building 2 members of data: val, time
    #    => Send data to canvas to draw
    def onGetnPlot(self, evt):
        if not self.check(checkTRange=True, checkDOffset=True, checkVelocity=True):
            return
        self.reset()
        global START, processInfo
        START = time.time()
        showStatus('', 'Starting - set status of menu')
        
        processInfo = WARNINGMSG
        
        self.statusLbl.setText(processInfo)    
    
        val = self.createVal()
    
        if val==False: return
        t = self.createTime()
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
    # simplify affect keepList -> recalc both val and time, but don't need to reread PH5data
    def onApplySimplify_RePlot(self, event):
        global START
        START = time.time()
        #self.downRbtn.setEnabled(True)
        #self.upRbtn.setEnabled(True)
          
        val = self.createVal(createFromBeg=False, appNewSimpFactor=True)
        if val == False: return  
        t = self.createTime()

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
        if val == False: return

        #self.downRbtn.setEnabled(True)
        #self.upRbtn.setEnabled(True)
        self.mainCanvas.initData(val=val)
        self.mainPlot.activateWindow()
           
        
    ###################################
    # Author: Lan
    # def: createTime():201506
    # create time array 
    #    => time is at first created evenly for each station
    #    => then changed according to correction and velocity reduction of each station
    #    => scale to range (-1,1)
    #    => only keep the time index in the self.keepList
    def createTime(self):
        global processInfo
        start = time.time()
        samNo = self.PH5Info['numOfSamples']
        staNo =self.PH5Info['numOfStations']
        #print "samNo=",samNo
        #print "start:", 0+self.offset*1000
        #print "end:", (samNo-1)*self.PH5Info['interval']+self.offset*1000
        #t = np.tile(np.linspace(0+self.offset*1000, (samNo-1)*self.PH5Info['interval']+self.offset*1000, samNo), ( staNo,1) )
        t = np.linspace(0+self.offset*1000, (samNo-1)*self.PH5Info['interval']+self.offset*1000, samNo)
        #print "len org t=", len(t[0])
        #print "max t=",t.max()

        self.minT = minT = t.min()
        self.maxT = maxT = t.max()
        #print "new minT=%s, maxT=%s" % (minT, maxT)
        self.totalTime = abs(maxT - minT)
        t -= minT
        self.scaleT = 2/(maxT-minT)
        t *= self.scaleT
        
        t -= 1
        self.zeroT = - minT*self.scaleT - 1 
        
        end = time.time()
        showStatus('Step 4 took %s seconds. Next: 5/%s' % (end-start, totalSteps), "Plotting")
        processInfo += "\nCreate Time value: %s seconds" % (end-start)
        self.statusLbl.setText(processInfo)
        
        return t

    ###################################
    # Author: Lan
    # def: getKeepList():201504 
    # modified: 201508
    # create the list of indexes of values that the program can ignore when drawing
    # build the list of values for each station that are:
    #    + greater than the simpFactor*abs(ymax-ymean) 
    #    + the peeks only (this takes too much time => look in old file if needed)
    #    + the start and end time of each station
    def getKeepList(self, val, samNo, staNo, simplFactor):
        keepList = []
        prevVal = 0
        #print "len(val)=", len(val)
        for i in range(staNo):
            if i in self.PH5Info['deepRemoved']:
                keepList.append([])
                continue
            #print "val[%s].shape=%s" % (i,val[i].shape)
            # remove center
            a = np.where( abs(val[i]-val[i].mean()) > abs(val[i].max()-val[i].mean())*simplFactor)[0]
            o = []
            d = val[i]
            phase = 0   # 1:increasing; -1: decreasing
            for k in range(len(a)):
                try:
                    # increasing
                    if d[a[k]] <= d[a[k+1]]:
                        if phase == 1:    #end of avg or decreasing
                            o.append(k)
                        phase=1
                    # decreasing
                    elif d[a[i]] >= d[a[k+1]]:
                        if phase == -1:    #end of avg or increasing
                            o.append(k)
                        phase=-1
                except IndexError: break

            a = np.delete(a,o).tolist()

            if 0 not in a:  a.insert(0, 0)

            if samNo-1 not in a: a.append(samNo-1)
            keepList.append(a)

            if i == staNo-1: break
        #print "keepList =", keepList[0]   
        return keepList

    ###################################
    # Author: Lan
    # def: getPH5Data():201504
    #    => read PH5 data and metadata
    def getPH5Data(self, orgStartT, offset, timeLen, staSpc):
        # create PH5Object
        PH5Object = PH5ReaderwVispyAPI.PH5Reader()
        # initiate PH5Object with filename
        PH5Object.initialize_ph5(self.PH5View.fname)
        PH5Object.set(self.PH5View.selectedChannels, ['Array_t_' + self.PH5View.selectedArray['arrayId']])
        # read trunk of data 
        #try:
        
        self.PH5Info = PH5Object.readData(orgStartT,offset, timeLen, staSpc, 
                                          self.correctionCkb.isChecked(), 
                                          self.vel, self.PH5View, statusBar, statusMsg)
        
        #except Exception, e:
            #print e
            #msg = "There must be something wrong in processing the data.\n" + \
                  #"Please try again"
            #if e.message=="NoDOffset":
                #msg = "The PH5 metadata has no distance offset.\n" + \
                      #"Please select the station spacing unknown for processing the data."
            #QtGui.QMessageBox.question(self, 'Error', msg, QtGui.QMessageBox.Ok)  
            #return False
        
        showStatus("1/5:Getting PH5Data - ", "copy metadata")          
        self.metadata = deepcopy(PH5Object.metadata)
        # convert list to numpy array => check to see if can create numpy array from creating section ??????????????
        y = PH5Object.data
        #print "y[2]:",y[2]
        """
        try :
            print "len org data =", len(y[0])
            print "No of station=" , len(y)
        except : pass
        """
        showStatus("1/5:Getting PH5Data - ", "save PH5 data to file to use in replotting")
        PH5Val = np.array(y).ravel()
        #self.PH5Size = 
        #np.set_printoptions(threshold=np.nan) #to show all data in np.array
        try :
            ph5Valfile = np.memmap(PH5VALFILE, dtype='float32', mode='w+', shape=(1,PH5Val.size))
            ph5Valfile[:] = PH5Val[:]
            del ph5Valfile
        except IOError :
            pass
            
        # close all files opened for PH5Object
        PH5Object.ph5close()
        showStatus("1/5:Getting PH5Data - ", "delete PH5Object to save resources")
        # delete PH5Object to save memory
        del PH5Object
        gc.collect()
        return y        

    ###################################
    # Author: Lan
    # def: createVal():201506
    # Create val file with the following steps:
    #    + read PH5 data
    #    + calc. data with the required properties: nomalized, overlaping, velocity
    #    + calc. center and scaling for each station so that the plot can span maximizedly on its room 
    #    + include the overlaping in calculating center
    def createVal(self, createFromBeg=True, appNewSimpFactor=False):
        global processInfo
        start = time.time()
        showStatus('1/%s' % totalSteps, 'Getting PH5Data ')
        if self.timelenCtrl.text()=='': 
            QtGui.QMessageBox.question(self, 'Error',
            "Length of time box is empty. You must enter a valid value for length of time", 
            QtGui.QMessageBox.Ok)

        #array = self.parent.eventStationGui.selectedArray
        #arrayIds = [array['arrayId']]
        #sampleRate = array['sampleRate']

        overlap = self.overlapSB.value() / 100.0
        if createFromBeg:
            if self.PH5View.submitGui == 'STATION':
                orgStartT = float(TimeDOY.passcal2epoch(self.startrangetimeCtrl.text())) 
            elif self.PH5View.submitGui == 'EVENT': 
                orgStartT = None
            else:
                print "Error in MainControl.createVal self.PH5View.submitGui ='%s'" % self.PH5View.submitGui
            
            self.dfltOffset = self.offset = float(self.offsetCtrl.text())
            self.dfltTimeLen = float(self.timelenCtrl.text())
            #startT = orgStartT + self.offset
            # add a little bit than the time of one sample
            #endT = orgStartT + float(self.timelenCtrl.text())
            if self.stationSpacingUnknownCkb.isChecked():
                staSpc = float(self.nominalStaSpace.text())
            else:
                staSpc = None
            
            
            #val = self.getPH5Data(startT, endT, 
                                  #['Array_t_' + esGUI.selectedArray['arrayId']], 
                                  #esGUI.selectedChannels, 
                                  #esGUI.selectedArray['sampleRate'], staSpc )
            val = self.getPH5Data(orgStartT, self.offset, self.dfltTimeLen, staSpc )            

            if val == False: return False
            if val==[]: 
                msg = "In the selected range of time: " + \
                    "\n+ There is no station belong to the selected array(s)." + \
                    "\n+ OR The selected array and the selected event aren't match."
                QtGui.QMessageBox.question(self, 'Error', msg, QtGui.QMessageBox.Ok)
                return False
            
            try:
                self.PH5Info['velocity'] = int(self.velocityCtrl.text())
            except ValueError:pass
            
        else:
            val = np.memmap(PH5VALFILE, dtype='float32', mode='r', 
                            shape=(self.PH5Info['numOfStations'], self.PH5Info['numOfSamples']))

        self.PH5Info['overlap'] = overlap
        samNo = self.PH5Info['numOfSamples'] 
        staNo = self.PH5Info['numOfStations'] 
        
        self.processData()
        
        if self.defaultPropRbtn.isChecked():  self.conf = self.defaultConf
        else: self.conf = self.fileConf

        end = time.time()
        processInfo += "\nGetting PH5Data: %s seconds" % (end-start)
        self.statusLbl.setText(processInfo)
        showStatus('Step 1 took %s seconds. Next: 2/%s - Getting keep list' % (end-start, totalSteps), "Calculating ")
        
        start = time.time()
        if appNewSimpFactor or createFromBeg:
            if self.distance2AvgSB.value() > 0:
                simplFactor = self.distance2AvgSB.value()/100.
                self.keepList = self.getKeepList(val, samNo, staNo, simplFactor)

        end = time.time()
        processInfo += "\nGetting keep list: %s seconds" % (end-start)
        self.statusLbl.setText(processInfo)
        showStatus('Step 2 took %s seconds. Next: 3/%s - Prepare drawing data' % (end-start, totalSteps), "Calculating ")
        
        start = time.time()
        #self.ph5val = []    # for double-check 
        PH5Val = []    

        self.statLimitList = stm = np.zeros((staNo,2))
        self.scaleVList = []
        lastEnd = 0
        
        if self.stationSpacingUnknownCkb.isChecked():
            sizeV4aplot = float(self.nominalStaSpace.text()) * (1+overlap)
        else:
            sizeV4aplot = self.PH5Info['avgSize'] * (1+overlap)
        #print "sizeV4aplot=",sizeV4aplot
            
        # signal is drawn on 2 sides of each distanceOffset
        # => at the start and end, add half of a sizeV4aPlot
        delta = self.PH5Info['distanceOffset'][0] - sizeV4aplot/2.
        #print "delta:", delta

        if self.PH5Info['distanceOffset'][0] > self.PH5Info['distanceOffset'][-1]:
            delta = self.PH5Info['distanceOffset'][-1] - sizeV4aplot/2.
        self.totalSize = abs(self.PH5Info['distanceOffset'][-1]-self.PH5Info['distanceOffset'][0]) \
                    + sizeV4aplot
        print "self.totalSize=",self.totalSize
        self.scaledDelta = delta/self.totalSize
        self.verGridIntervalSB.setRange(1,int(self.totalSize/1000))
        scaledSizeV4aplot = sizeV4aplot/self.totalSize
        
        maxP2P = max([abs(m['minmax'][0] - m['minmax'][1]) for m in self.metadata 
                      if m['seq'] not in self.PH5Info['deepRemoved']])
        
        if not self.normalizeCkb.isChecked():
            self.scaleVList = [scaledSizeV4aplot/float(maxP2P)]*self.PH5Info['numOfStations']
            #self.scaleVList = [scaledSizeV4aplot]*self.PH5Info['numOfStations']

        #if self.keepList!=None: print "keepList[2]=", self.keepList[2]
        for i in range(staNo):
            if self.metadata[i]['seq'] in self.PH5Info['deepRemoved']: 
                PH5Val.append(val[i][[]])
            else:
                if self.distance2AvgSB.value()>0: 
                    PH5Val.append(val[i][self.keepList[i]])     
                else:
                    #self.ph5val.append(val[i][self.keepList[i]])    # for double-check 
                    PH5Val.append(val[i])
                
            if self.normalizeCkb.isChecked():
                # difference bw min and max (peak to peak)
                p2p = abs(self.metadata[i]['minmax'][1]-self.metadata[i]['minmax'][0])
                # scale of a value of this plot over d
                self.scaleVList.append( scaledSizeV4aplot / float(p2p) )
            
            centerPos = self.PH5Info['distanceOffset'][i] - delta
            
            self.statLimitList[i][:] = [( centerPos - sizeV4aplot/2.)/self.totalSize,
                                        ( centerPos + sizeV4aplot/2.)/self.totalSize]  

            centerVal = (self.metadata[i]['minmax'][1]+self.metadata[i]['minmax'][0])/2
            zero = self.statLimitList[i].mean() - centerVal * self.scaleVList[i]
            
            if i % 10 ==0: showStatus("Step3: Prepare drawing data" , "%s/%s" % (i,staNo))
            PH5Val[i] = PH5Val[i]*self.scaleVList[i] + zero


        self.maxVal = max([stm[0][0],stm[0][1],stm[-1][0], stm[-1][1]])

        end = time.time()
        showStatus('Step 3 took %s seconds. Next: 4/%s' % (end-start, totalSteps), "Create Time value")
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
        #self.wholeDistanceLbl.setText("%s" % self.PH5Info['sumOverlappedSize'])
        self.sampleNoLbl.setText("%s" % self.PH5Info['numOfSamples'])
        self.intervalLbl.setText("%s" % self.PH5Info['interval'])
        realRange = self.PH5Info['numOfSamples']*self.PH5Info['interval']/1000
        #print "realRange:", realRange
        if realRange < float(self.timelenCtrl.text()):
            msg = "\nMaximum length of time has been read \nfor this time range is %s" % realRange
            #QtGui.QMessageBox.question(self, 'Notice', msg, QtGui.QMessageBox.Ok)
            self.timelenCtrl.setText(str(realRange))
            processInfo += msg
            print processInfo
            self.statusLbl.setText(msg)


    def deepRemoveStations(self):
        global START, processInfo
        START = time.time()
        showStatus('', 'Starting - set status of menu')
        
        processInfo = WARNINGMSG
        
        self.statusLbl.setText(processInfo)    
    
        val = self.createVal(createFromBeg=False, appNewSimpFactor=False)
    
        if val==False: return
        t = self.createTime()
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
        ctrl.setText(TimeDOY.epoch2passcal(realT))  
        
    ###################################
    # Author: Lan
    # def: setWidgetsEnabled():201410  
    def setWidgetsEnabled(self, state):
        #self.parent.fileAction.setEnabled(not state)

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
        #self.simplifyCkb.setEnabled(state)
        self.correctionCkb.setEnabled(state)
        self.overlapSB.setEnabled(state)
        self.stationSpacingUnknownCkb.setEnabled(state)
        self.normalizeCkb.setEnabled(state)

        self.velocityCtrl.setEnabled(state)

        self.verGridCkb.setEnabled(state)
        self.horGridCkb.setEnabled(state)
        self.horGridIntervalSB.setEnabled(state)
        self.verGridIntervalSB.setEnabled(state)
        self.mainWindowRbtn.setEnabled(state)
        self.supportWindowRbtn.setEnabled(state)
        self.bothWindowRbtn.setEnabled(state)
 
        self.distance2AvgSB.setEnabled(state)

            
        if self.stationSpacingUnknownCkb.isChecked():
            self.nominalStaSpace.setEnabled(state)            
        else:
            self.nominalStaSpace.setEnabled(False)

    def setAllReplotBtnsEnabled(self, state, resetCanvas=True):
        #self.allowReplot = state
        #print "setAllReplotBtnsEnabled:", state
        self.simplifyReplotBtn.setEnabled(state)   
        self.propReplotBtn.setEnabled(state)
        self.overlapReplotBtn.setEnabled(state)
        self.normalizeReplotBtn.setEnabled(state)
        if resetCanvas and state==False:
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
##########################################
############### CLASS ####################
# Author: StackOverflow
# Modifier: Lan
# Updated: 201409
# CLASS: Filter - Detect event from widgets
class Filter(QtCore.QObject):
    def eventFilter(self, widget, event):
        # FocusOut event
        #if event.type() == QtCore.QEvent.FocusOut:
            #owner = widget.parent().parent()
            #if owner.__class__.__name__ != "MainControl": return False
            #if widget in [owner.startStationSB,owner.endStationSB]:
            #    owner.stationLostFocus()
            #elif widget in [owner.startTimeSB,owner.endTimeSB]:
            #    owner.timeLostFocus()
            # return False so that the widget will also handle the event
            # otherwise it won't focus out
            #return False
        #if event.type() == QtCore.QEvent.FocusIn:
            #print widget.__class__.__name__
        if event.type()== QtCore.Qt.RightButton:
            try:
                owner = widget.parent().parent().parent().parent().parent()
            except TypeError:
                return False
            
            if owner.__class__.__name__ != "EAS_Gui": return False
            if widget in owner.stationViewBtns:
                owner.onStationView(owner.stationViewBtns.index(widget))
            return False
        else:
            # we don't care about other events
            return False
"""

##########################################
############### CLASS ####################
# Author: Lan
# Updated: 201410
# CLASS: Properties - 
# the following properties can be set for the Graphic
#     . display color on plots according the color pattern
#     . display axis color
#     . horizontal/vertical labels
#     . Graphic name - title of the panel
class Properties(QtGui.QDialog):
    def __init__(self, parent):
        self.parent = parent
        self.initUI()
        
    def initUI(self): 
        QtGui.QDialog.__init__(self)
        mainbox = QtGui.QVBoxLayout(self)
        self.EXPL = EXPL = {}
        self.helpEnable = False
        #hbox = QtGui.QHBoxLayout(); mainbox.addLayout(hbox)
        grid = QtGui.QGridLayout() ; mainbox.addLayout(grid)
        grid.setSpacing(10)        
        cancelBtn = QtGui.QPushButton('Cancel', self); cancelBtn.installEventFilter(self)
        EXPL[cancelBtn] = "Cancel any edition and exit Properties Window"
        cancelBtn.clicked.connect(self.onCancel)
        cancelBtn.resize(cancelBtn.sizeHint())
        grid.addWidget(cancelBtn, 0, 0)

        helpBtn = QtGui.QPushButton('Help', self)
        #helpBtn.setFixedWidth(75)
        helpBtn.clicked.connect(self.onHelp)
        grid.addWidget(helpBtn, 0, 1)
        
        saveBtn = QtGui.QPushButton('Apply', self);    saveBtn.installEventFilter(self)
        EXPL[saveBtn] = "Save all properties to file to use for next time.\n" + \
                            "Apply the properties to new plotting if keeping selecting Prevous Prop. in the Control Window." + \
                            "Exit Properties Window"
        saveBtn.clicked.connect(self.onApply)
        saveBtn.resize(saveBtn.sizeHint())
        grid.addWidget(saveBtn, 0, 2)
        
        setting_group = QtGui.QButtonGroup(self)                # only one radio button in the group can be set
        
        grid.addWidget(QtGui.QLabel("SETTING", self), 1, 0, QtCore.Qt.AlignHCenter)
        
        self.defaultRbtn = defaultRbtn = QtGui.QRadioButton("Default"); self.defaultRbtn.installEventFilter(self)
        EXPL[self.defaultRbtn] = "Show all default properties so that user can continue to edit from these"
        defaultRbtn.toggled.connect(self.selectConf)
        setting_group.addButton(defaultRbtn)
        grid.addWidget(defaultRbtn, 1, 1)
        
        self.previousRbtn = previousRbtn = QtGui.QRadioButton("Previous"); self.previousRbtn.installEventFilter(self)
        EXPL[self.previousRbtn] = "Show all previously saved properties so that user can continue to edit from these"
        setting_group.addButton(previousRbtn)
        previousRbtn.toggled.connect(self.selectConf)
        grid.addWidget(previousRbtn, 1, 2)
    
        propertiesPanel = QtGui.QWidget()    ; mainbox.addWidget(propertiesPanel)
        propertiesHbox = QtGui.QHBoxLayout(propertiesPanel)    
        propertiesGrid = QtGui.QGridLayout()   
        propertiesGrid.setSpacing(10) 
        propertiesHbox.addLayout(propertiesGrid)

        propertiesGrid.addWidget(QtGui.QLabel("AddingInfo to GraphicName",propertiesPanel), 0, 0, QtCore.Qt.AlignRight)
        self.addingInfoText = QtGui.QLineEdit(propertiesPanel); self.addingInfoText.installEventFilter(self)
        EXPL[self.addingInfoText] = "Adding info to the name of the drawing"
        self.addingInfoText. setFixedWidth(180)
        propertiesGrid.addWidget(self.addingInfoText, 0,1)
        
        propertiesGrid.addWidget(QtGui.QLabel("Horizontal Label", propertiesPanel), 2, 0, QtCore.Qt.AlignRight)
        self.hLabelText = QtGui.QLineEdit(propertiesPanel); self.hLabelText.installEventFilter(self)
        EXPL[self.hLabelText] = "Name of the horizontal axis"
        propertiesGrid.addWidget(self.hLabelText, 2, 1)
        
        propertiesGrid.addWidget(QtGui.QLabel("Vertical Label", propertiesPanel), 3, 0, QtCore.Qt.AlignRight)
        self.vLabelText = QtGui.QLineEdit(propertiesPanel); self.vLabelText.installEventFilter(self)
        EXPL[self.vLabelText] = "Name of the vertical axis"
        propertiesGrid.addWidget(self.vLabelText, 3, 1 )
        
        propertiesGrid.addWidget(QtGui.QLabel("Pattern Size", propertiesPanel), 4, 0, QtCore.Qt.AlignRight)
        self.patternSizeText = QtGui.QLineEdit(propertiesPanel); self.patternSizeText.installEventFilter(self)
        EXPL[self.patternSizeText] = "Number of stations in one pattern. These pattern color will be repeated through the plotting"
        propertiesGrid.addWidget(self.patternSizeText, 4, 1 )
        
        self.updateBtn = QtGui.QPushButton('Update', propertiesPanel); self.updateBtn.installEventFilter(self)
        EXPL[self.updateBtn] = "Change the number of color buttons in the pattern color panel on the right"
        self.updateBtn.clicked.connect(self.onUpdate)
        self.updateBtn.resize(self.updateBtn.sizeHint())
        propertiesGrid.addWidget(self.updateBtn, 4, 2 )
        
        propertiesGrid.addWidget(QtGui.QLabel("Plot thickness", propertiesPanel), 5, 0, QtCore.Qt.AlignRight)
        self.plotThickText = QtGui.QLineEdit(propertiesPanel)       ; self.plotThickText.installEventFilter(self)
        EXPL[self.plotThickText] = "Adjust the thickness of signals in file saving or printing"
        propertiesGrid.addWidget(self.plotThickText, 5, 1 )            
        
        propertiesGrid.addWidget(QtGui.QLabel("Grid thickness", propertiesPanel), 7, 0, QtCore.Qt.AlignRight)
        self.gridThickText = QtGui.QLineEdit(propertiesPanel)       ; self.gridThickText.installEventFilter(self)
        EXPL[self.gridThickText] = "Adjust the thickness of signals in file saving or printing"
        propertiesGrid.addWidget(self.gridThickText, 7, 1 )
        self.gridColBtn = QtGui.QPushButton('Color', propertiesPanel); self.gridColBtn.installEventFilter(self)
        EXPL[self.gridColBtn] = "Change color of grid line"
        self.gridColBtn.clicked.connect(self.onChangeColor)
        self.gridColBtn.resize(10,10)
        propertiesGrid.addWidget(self.gridColBtn, 7, 2 )

        propertiesGrid.addWidget(QtGui.QLabel("Abnormal Station(s)", propertiesPanel), 8, 0, QtCore.Qt.AlignRight)
        self.showAbnormalStatCkb = QtGui.QCheckBox('', self);   self.showAbnormalStatCkb.installEventFilter(self)
        self.EXPL[self.showAbnormalStatCkb] = "If selected, the station(s) with abnormal offset's growth will be shown in this color."
        self.showAbnormalStatCkb.setCheckState(QtCore.Qt.Checked)
        propertiesGrid.addWidget(self.showAbnormalStatCkb, 8, 1 )
        self.abnormalColBtn = QtGui.QPushButton('Color', propertiesPanel); self.abnormalColBtn.installEventFilter(self)
        EXPL[self.abnormalColBtn] = "Change color of station with abnormal distance offset"
        self.abnormalColBtn.clicked.connect(self.onChangeColor)
        self.abnormalColBtn.resize(10,10)
        propertiesGrid.addWidget(self.abnormalColBtn, 8, 2 )
        
        scrollArea = QtGui.QScrollArea(self)
        propertiesHbox.addWidget(scrollArea)
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scrollArea.setWidgetResizable(True)
        
        self.patternColorPanel = QtGui.QWidget()    ; self.patternColorPanel.installEventFilter(self)
        EXPL[self.patternColorPanel] = "Click to the buttons corresponding to the plot lines of which colors you want to change."
        main_patternColorVBox = QtGui.QVBoxLayout(self.patternColorPanel)
        
        self.patternColorVBox = QtGui.QVBoxLayout() ; main_patternColorVBox.addLayout(self.patternColorVBox)
        self.patternColorVBox.addWidget(QtGui.QLabel("Pattern Colors"))
        
        scrollArea.setWidget(self.patternColorPanel)
        
        self.plotColBtns = []
        
        main_patternColorVBox.addStretch(1)

        self.resize(650,600)
        
        if self.parent.defaultPropRbtn.isChecked():
            defaultRbtn.setChecked(True)
        else:
            previousRbtn.setChecked(True)


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
    # using baloon tooltip to help user understand the use of the widget (only the one install event filter)
    def eventFilter(self, object, event):
        if not self.helpEnable: return False
        if event.type() == QtCore.QEvent.Enter:
            if object not in self.EXPL.keys(): return False
            #print object
            P = object.pos()
            #print P
            QtGui.QToolTip.showText(self.mapToGlobal(QtCore.QPoint(P.x(), P.y()+20)), self.EXPL[object])
            return True
        return False
    
    def onCancel(self, evt):
        self.close()

    ###################################
    # Author: Lan
    # def: onApply():201410
    # save info from GUI to parent.conf
    # call parent.saveConfFile() to save that info to file
    # set plot.plottingPanel.clear=true to not start painting on panel right away
    # set the data for plot
    def onApply(self, evt):
        self.parent.fileConf['addingInfo'] = self.addingInfoText.text()
        self.parent.fileConf['hLabel'] = self.hLabelText.text()
        self.parent.fileConf['vLabel'] = self.vLabelText.text()
        self.parent.fileConf['showAbnormalStat'] = self.showAbnormalStatCkb.isChecked()
        errorItm = None
        try: self.parent.fileConf['patternSize'] = int(self.patternSizeText.text())
        except ValueError: errorItm = "pattern size"; expectType = "an integer"

        try: self.parent.fileConf['plotThick'] = float(self.plotThickText.text())
        except ValueError: errorItm = "plot thickness"; expectType = "a float"        

        try: self.parent.fileConf['gridThick'] = float(self.gridThickText.text())
        except ValueError: errorItm = "grid thickness"; expectType = "a float"
                            
        if errorItm!= None:
            errorMsg = "%s must be %s number"
            QtGui.QMessageBox.question(self, 'Error', errorMsg, QtGui.QMessageBox.Ok)
            return
            
        self.parent.fileConf['gridColor'] = self.gridColBtn.palette().color(1).name()
        self.parent.fileConf['abnormalColor'] = self.abnormalColBtn.palette().color(1).name()
        
        self.parent.fileConf['plotColor'] = []
        for cb in self.plotColBtns:
            self.parent.fileConf['plotColor'].append(cb.palette().color(1).name())
        
        # save to conf. file
        confFile = open('PH5Viewer.cfg', 'w')
        conf = self.parent.fileConf
        if conf.has_key('addingInfo'):
            confFile.write("\naddingInfo:%s" % conf['addingInfo'])
        if conf.has_key("hLabel"):
            confFile.write("\nhLabel:%s" % conf['hLabel'])
        if conf.has_key("vLabel"):
            confFile.write("\nvLabel:%s" % conf['vLabel'])
        if conf.has_key("showAbnormalStat"):
            confFile.write("\nshowAbnormalStat:%s" % conf['showAbnormalStat'])
        if conf.has_key("gridColor"):
            confFile.write("\ngridColor:%s" % conf['gridColor'])
        if conf.has_key("abnormalColor"):
            confFile.write("\nabnormalColor:%s" % conf['abnormalColor'])
        if conf.has_key('patternSize'):
            confFile.write('\npatternSize:%s' % conf['patternSize'])
        if conf.has_key('plotThick'):
            confFile.write("\nplotThick:%s" % conf['plotThick'])
        if conf.has_key('gridThick'):
            confFile.write("\ngridThick:%s" % conf['gridThick'])
            
        for pc in conf['plotColor']:
            confFile.write("\nplotColor:%s" % pc)
            
        confFile.close()
        
        self.parent.fromFilePropRbtn.setChecked(True)
        self.close()
        
    ###################################
    # Author: Lan
    # def: onChangeColor():201409
    # when click on the button, pop-up QColorDialog for user to select one color, change color of the button to the selected color    
    def onChangeColor(self, evt):
        col = QtGui.QColorDialog.getColor()
        if col.isValid():
            self.sender().setStyleSheet("QWidget { background-color: %s }" % col.name())

    ###################################
    # Author: Lan
    # def: defaultChoice():201410
    # select default => use defaultConf created from PH5Visualizer      
    def selectConf(self, evt):
        
        if self.defaultRbtn.isChecked():
            #print "select defaultConf"
            self.conf = self.parent.defaultConf
        else:
            #print "select fileConf"
            self.conf = self.parent.fileConf
        self.setConf()
            
    ###################################
    # Author: Lan
    # def: setConf():201409
    # set info from self.conf onto GUI 
    def setConf(self):
        if self.conf.has_key('addingInfo'):    self.addingInfoText.setText(self.conf['addingInfo'])
        if self.conf.has_key('hLabel'):         self.hLabelText.setText(self.conf['hLabel'])
        if self.conf.has_key('vLabel'):         self.vLabelText.setText(self.conf['vLabel'])
        
        if self.conf.has_key('gridColor'):      
            self.gridColBtn.setStyleSheet("QWidget { background-color: %s }" % QColor(self.conf['gridColor']).name())
            
        if self.conf.has_key('abnormalColor'):
            self.abnormalColBtn.setStyleSheet("QWidget { background-color: %s }" % QColor(self.conf['abnormalColor']).name())
        
        if self.conf.has_key('patternSize'):
            pSize = self.conf['patternSize']
            self.patternSizeText.setText(str(pSize))
            self.updatePlotColorButton(pSize)
        
        if self.conf.has_key('showAbnormalStat'):
            if self.conf['showAbnormalStat']:
                self.showAbnormalStatCkb.setCheckState(QtCore.Qt.Checked)
            else:
                self.showAbnormalStatCkb.setCheckState(QtCore.Qt.Unchecked)
            
        if self.conf.has_key('plotThick'):  self.plotThickText.setText(str(self.conf['plotThick']))
        if self.conf.has_key('gridThick'):  self.gridThickText.setText(str(self.conf['gridThick']))
        
    ###################################
    # Author: Lan
    # def: updatePlotColorButton():201409
    # delete all the color buttons
    # add color buttons according to pattern; any extra button, use default color
    def updatePlotColorButton(self, pSize):        
        for pb in self.plotColBtns:
            self.patternColorVBox.removeWidget(pb)
            pb.deleteLater()
            
        self.plotColBtns = []
        for i in range(pSize):
            cb = QtGui.QPushButton(str(i), self.patternColorPanel)
            self.plotColBtns.append(cb)
            cb.clicked.connect(self.onChangeColor)
            cb.resize(1,1)
            self.patternColorVBox.addWidget(cb)
            if i < self.conf['patternSize']: 
                cb.setStyleSheet("QWidget { background-color: %s }" % QColor(self.conf['plotColor'][i]).name())    
            else:
                cb.setStyleSheet("QWidget { background-color: %s }" % QColor(self.parent.defaultConf['plotColor'][0]).name())
        
    ###################################
    # Author: Lan
    # def: onUpdate():201409
    # reset the color buttons according to the number entered in patternSizeText
    def onUpdate(self):
        pSize = int(self.patternSizeText.text())
        self.updatePlotColorButton(pSize)

class ArrayGui(QtGui.QWidget): 
    def __init__(self, parent, ESType=None):    #ESType=EVENT/STATION
        QtGui.QWidget.__init__(self)
        self.PH5View = parent
        self.control = parent.mainControl
        self.ESType = ESType   
        self.initUI()

    def initUI(self):
        #print "ArrayGui.initUI(self)"
        #mainFrame = QtGui.QFrame(self);self.setCentralWidget(mainFrame)
        mainVbox = QtGui.QVBoxLayout(); #mainFrame.setLayout(mainbox)
        self.setLayout(mainVbox)
        
        self.chBox = QtGui.QHBoxLayout(); mainVbox.addLayout(self.chBox)
        self.chBox.addWidget(QtGui.QLabel('Channels:'))
        #self.chWidget = QtGui.QWidget()
        #chBox.addWidget(self.chWidget)  
        #channelBox = QtGui.QHBoxLayout(); self.chWidget.setLayout(channelBox)
        
        arrayBox = QtGui.QHBoxLayout(); mainVbox.addLayout(arrayBox) 
        self.arrayTabs = QtGui.QTabWidget(self); arrayBox.addWidget(self.arrayTabs)
        
        mainVbox.addWidget(QtGui.QLabel('NOTICE:'))
        self.statusCtrl = QtGui.QLabel('')
        mainVbox.addWidget(self.statusCtrl)        
     
        #mainVbox.addStretch(1)    
    
    def setChannels(self):
        
        self.channelChks = channelChks = []
        for i in range(len(self.PH5View.channels)):
            if self.PH5View.channels[i]!=False:
                channelChks.append(QtGui.QCheckBox(str(self.PH5View.channels[i]), self))
                self.chBox.addWidget(channelChks[i])   
                channelChks[i].setCheckState(QtCore.Qt.Checked)             
        self.chBox.addStretch(1)          
        
    def setArrays(self):
        #self.sampleRates = []
        for a in self.PH5View.arrays: 
            a[self.ESType] = ES_Gui(self, ESType=self.ESType, array=a, submitType=False)
            self.arrayTabs.addTab(a[self.ESType], "Array_t_%s" % a['arrayId'])
            
        self.selectedArray = self.PH5View.arrays[0]    
        
    def clearArrays(self):
        self.arrayTabs.clear()

    def setNotice(self, graphName):
        self.statusCtrl.setText("Graph Name is '%s'. Click on Properties in Control tab to change name of the graph" % graphName)


# Event_Station
class ES_Gui(QtGui.QWidget):   
    def __init__(self, parent, ESType, array, submitType=False):     #ESType=EVENT/STATION; submitType=True/False
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


    def initUI(self): 
        #print "ES_Gui.initUI(self)"
        #mainFrame = QtGui.QFrame(self);self.setCentralWidget(mainFrame)
        mainVbox = QtGui.QVBoxLayout(); #mainFrame.setLayout(mainbox)
        self.setLayout(mainVbox)
        if not self.submitType:
            v = ( self.array['sampleRate'], TimeDOY.epoch2passcal(self.array['deployT']), 
                  TimeDOY.epoch2passcal(self.array['pickupT']) )
            mainVbox.addWidget(QtGui.QLabel("Array Info: %s sps || %s - %s" % v))
        
        scrollArea = QtGui.QScrollArea(self); mainVbox.addWidget(scrollArea)
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scrollArea.setWidgetResizable(True)
        itemsFrame = QtGui.QFrame(); scrollArea.setWidget(itemsFrame)
        mainScrollBox = QtGui.QVBoxLayout() ; itemsFrame.setLayout(mainScrollBox)
        scrollPanel = QtGui.QWidget(); mainScrollBox.addWidget(scrollPanel)
        ESHbox = QtGui.QHBoxLayout(scrollPanel); 
        ESVbox = QtGui.QVBoxLayout(); ESHbox.addLayout(ESVbox)    
        self.ESPane = QtGui.QWidget(scrollPanel)
        ESVbox.addWidget(self.ESPane)
        self.ESGrid = QtGui.QGridLayout(); self.ESPane.setLayout(self.ESGrid)   
        
        if self.ESType == 'STATION': self.setStations()
        elif self.ESType == 'EVENT': self.setEvents()
        
        
        ESVbox.addStretch(1)
        ESHbox.addStretch(1)        
        
        if self.submitType:
            botLayout = QtGui.QHBoxLayout(); mainVbox.addLayout(botLayout)
            self.submitBtn = QtGui.QPushButton('Submit'); self.submitBtn.installEventFilter(self)
            if self.ESType == 'STATION':
                self.EXPL[self.submitBtn] = "Submit the list of stations to be plotted"
            if self.ESType == 'STATION':
                self.EXPL[self.submitBtn] = "Submit the list of events to be plotted"
            self.submitBtn.clicked.connect(self.onSubmit)
            self.submitBtn.resize(25, 70) #self.submitBtn.sizeHint())
            botLayout.addWidget(self.submitBtn )

            botLayout.insertSpacing(-1, 15)

            self.cancelBtn = QtGui.QPushButton('Cancel')
            self.cancelBtn.clicked.connect(self.onCancel)
            self.cancelBtn.resize(25,75)
            botLayout.addWidget(self.cancelBtn )            

            botLayout.insertSpacing(-1, 15)

            self.helpBtn = QtGui.QPushButton('Help')
            self.helpBtn.clicked.connect(self.onHelp)
            self.helpBtn.resize(25,75)
            botLayout.addWidget(self.helpBtn ) 
                        
            botLayout.addStretch(1)
        
    def onHelp(self, evt):
        self.helpEnable = not self.helpEnable
        if self.helpEnable:
            cursor = QtGui.QCursor(QtCore.Qt.WhatsThisCursor)
        else: 
            cursor = QtGui.QCursor(QtCore.Qt.ArrowCursor)
            
        self.setCursor(cursor)        
        
    
    def onCancel(self, evt):
        self.close()

        
    def onSubmit(self, evt):
        PH5View = self.PH5View
        control = self.parent.control
        arrayGui = self.parent.parent
        
        PH5View.submitGui = self.ESType
        PH5View.selectedArray = self.array
        PH5View.selectedChannels = []
        ############ CHANNEL #############
        for i in range(len(arrayGui.channelChks)):
            if arrayGui.channelChks[i].isChecked():
                PH5View.selectedChannels.append(PH5View.channels[i])  

        control.setWidgetsEnabled(True)
        if self.ESType == 'EVENT':
            PH5View.selectedEvents = [e for e in self.array['events'] if 
                                      e['eventChk'].checkState() == QtCore.Qt.Checked]
            
            if PH5View.selectedEvents == []:
                msg = "You must select at least one events before continue."
                QtGui.QMessageBox.question(self, 'Warning', msg, QtGui.QMessageBox.Ok)
                return
            
            control.startrangetimeCtrl.setText('')
            control.startrangetimeCtrl.setEnabled(False)
            control.stationSpacingUnknownCkb.setCheckState(QtCore.Qt.Checked)
            control.stationSpacingUnknownCkb.setEnabled(False)
            control.correctionCkb.setCheckState(QtCore.Qt.Unchecked)
            control.correctionCkb.setEnabled(False) 
            control.offsetCtrl.setText("0")
            control.offsetCtrl.setEnabled(False)            
            e = PH5View.selectedEvents[0]
            
        elif self.ESType == 'STATION':
            PH5View.selectedStations = [s for s in self.array['stations'] if 
                                            s['stationChk'].checkState() == QtCore.Qt.Checked]
            
            if PH5View.selectedStations == []:
                msg = "You must select at least one stations before continue."
                QtGui.QMessageBox.question(self, 'Warning', msg, QtGui.QMessageBox.Ok)
                return
            
            e = PH5View.selectedEvents[0]           
            control.startrangetimeCtrl.setText(TimeDOY.epoch2passcal(e['eStart']))
            control.startrangetimeCtrl.setEnabled(True)
            
            if len(PH5View.selectedStations)==1:
                control.stationSpacingUnknownCkb.setCheckState(QtCore.Qt.Checked)
                control.stationSpacingUnknownCkb.setEnabled(False)  
            else:
                control.stationSpacingUnknownCkb.setCheckState(QtCore.Qt.Unchecked)
                control.stationSpacingUnknownCkb.setEnabled(True)  
                
            control.correctionCkb.setCheckState(QtCore.Qt.Checked)
            control.correctionCkb.setEnabled(True) 
            control.offsetCtrl.setText(str(control.dfltOffset))
            control.offsetCtrl.setEnabled(True)
        else: 
            print "Error in ES_GUI.onSubmit(): self.ESType='%s'" % self.ESType
     
        
        control.eventId = e['eventId']
        control.upperTimeLen = e['eStop'] - e['eStart']
        newTimeLen = control.dfltTimeLen - control.dfltOffset
        minInterval = int(newTimeLen/25)
        maxInterval = int(newTimeLen)
        control.horGridIntervalSB.setRange(minInterval, maxInterval)
        control.horGridIntervalSB.setValue(int(newTimeLen/15))       
        
        control.timelenCtrl.setText(str(control.dfltTimeLen))
        control.setAllReplotBtnsEnabled(False)
        PH5View.selectedEventIds = [e['eventId'] for e in PH5View.selectedEvents]
        PH5View.selectedStationIds = [s['stationId'] for s in PH5View.selectedStations]
        
        PH5View.tabWidget.setCurrentIndex(0)
        #print "selected Channels=", PH5View.selectedChannels
        #print "selected Array=", PH5View.selectedArray['arrayId']
        #print "*"*30
        #for e in PH5View.selectedEvents:
        #    print "selected Event=", e['eventId']
        
        #print "*"*30
        #for s in PH5View.selectedStations:
            #print "selectedStations:", s['stationId']
        #print "No of selected Station=", len(PH5View.selectedStations)
        
        self.close()
        
        del self
        
            
        
        
    def setEvents(self): 
        if self.submitType :
            allChk = QtGui.QCheckBox('')
            allChk.setChecked(True)
            self.ESGrid.addWidget(allChk,0,0)
            allChk.installEventFilter(self)
            self.EXPL[allChk] = "Click to select/unselect ALL events"
            allChk.clicked.connect(self.onSelectAllEvents)
        self.ESGrid.addWidget(QtGui.QLabel('ID'),0,1)
        self.ESGrid.addWidget(QtGui.QLabel('Time'),0,2)
        self.ESGrid.addWidget(QtGui.QLabel('Latitude'),0,3)
        self.ESGrid.addWidget(QtGui.QLabel('Longitude'),0,4)
        self.ESGrid.addWidget(QtGui.QLabel('Elevation(m)'),0,5)
        self.ESGrid.addWidget(QtGui.QLabel('Mag'),0,6)
        self.ESGrid.addWidget(QtGui.QLabel('Depth(m)'),0,7)
        self.array['events'] = []
        lineSeq = 1
        for evts in self.PH5View.events:
            lineId = evts["arrayId"]
            for e in evts['events'] :
                if e['eStart']<self.array['deployT'] or e['eStart']>self.array['pickupT']: continue
                self.array['events'].append(e)
                if not self.submitType:
                    e['eventRbtn'] = QtGui.QRadioButton(self.ESPane)
                    e['eventRbtn'].installEventFilter(self)
                    self.EXPL[e['eventRbtn']] = "Click this event to select/unselect."
                    e['eventRbtn'].clicked.connect(self.onSelectEvent)
                    self.ESGrid.addWidget(e['eventRbtn'], lineSeq, 0)
                else:
                    e['eventChk'] = QtGui.QCheckBox('', self.ESPane)
                    e['eventChk'].setChecked(True)
                    e['eventChk'].installEventFilter(self)
                    self.EXPL[e['eventChk']] = "Click to select this event"
                    self.ESGrid.addWidget(e['eventChk'], lineSeq, 0)
                self.addLabel(self.ESGrid, str(e['eventId']), lineSeq, 1)
                self.addLabel(self.ESGrid, TimeDOY.epoch2passcal(e['eStart']), lineSeq, 2)
                self.addLabel(self.ESGrid, str(e['lat.']), lineSeq, 3)
                self.addLabel(self.ESGrid, str(e['long.']), lineSeq, 4)
                self.addLabel(self.ESGrid, str(e['elev.']), lineSeq, 5)
                self.addLabel(self.ESGrid, str(e['mag.']), lineSeq, 6)
                self.addLabel(self.ESGrid, str(e['depth']), lineSeq, 7)
                lineSeq += 1

    def setStations(self):
        if self.submitType:
            allChk = QtGui.QCheckBox('')
            allChk.setChecked(True)
            self.ESGrid.addWidget(allChk,0,0)
            allChk.installEventFilter(self)
            self.EXPL[allChk] = "Click to select/unselect ALL stations"
            allChk.clicked.connect(self.onSelectAllStations)
        self.ESGrid.addWidget(QtGui.QLabel('ID'),0,1)
        self.ESGrid.addWidget(QtGui.QLabel('DAS'),0,2)
        self.ESGrid.addWidget(QtGui.QLabel('Latitude'),0,3)
        self.ESGrid.addWidget(QtGui.QLabel('Longitude'),0,4)
        self.ESGrid.addWidget(QtGui.QLabel('Elevation(m)'),0,5)
        self.ESGrid.addWidget(QtGui.QLabel('Component'),0,6)
        
        lineSeq = 1
        for s in self.array['stations']:
            if not self.submitType: 
                s['stationRbtn'] = QtGui.QRadioButton(self.ESPane)
                s['stationRbtn'].installEventFilter(self)
                self.EXPL[s['stationRbtn']] = "Click this station to select/unselect"
                s['stationRbtn'].clicked.connect(self.onSelectStation)
                self.ESGrid.addWidget(s['stationRbtn'], lineSeq, 0)
            else:
                s['stationChk'] = QtGui.QCheckBox('', self.ESPane)
                s['stationChk'].setChecked(True)
                s['stationChk'].installEventFilter(self)
                self.EXPL[s['stationChk']] = "Click to select this station"
                self.ESGrid.addWidget(s['stationChk'], lineSeq, 0)
            self.addLabel(self.ESGrid, str(s['stationId']), lineSeq, 1)
            self.addLabel(self.ESGrid, str(s['dasSer']), lineSeq, 2)
            self.addLabel(self.ESGrid, str(s['lat.']), lineSeq, 3)
            self.addLabel(self.ESGrid, str(s['long.']), lineSeq, 4)
            self.addLabel(self.ESGrid, str(s['elev.']), lineSeq, 5)
            self.addLabel(self.ESGrid, str(s['component']), lineSeq, 6)
            lineSeq += 1
            
    def addLabel(self, grid, text, row, col):
        lbl = QtGui.QLabel(text)
        lbl.setStyleSheet("QWidget { background-color: white }" )
        lbl.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        grid.addWidget(lbl,row,col)    


    def onSelectAllStations(self,evt):
        allChk = self.sender()
        for s in self.array['stations']:
            s['stationChk'].setCheckState(allChk.checkState())
        
        
    def onSelectAllEvents(self,evt):
        allChk = self.sender()
        for e in self.array['events']:
            e['eventChk'].setCheckState(allChk.checkState())
                
                
    def onSelectEvent(self, state):     # select one event => list of stations for the array of this GUI to will show up
        sndr = self.sender ()
        self.PH5View.selectedEvents = [e for e in self.array['events'] if e['eventRbtn'] == self.sender()]    #only one event in the selectedEvents
        self.stationsWidget = stationsWidget = ES_Gui(self, ESType='STATION', array=self.array, submitType=True)
        stationsWidget.setGeometry(130, 100, 650,700)
        v = (self.array['arrayId'], self.PH5View.selectedEvents[0]['eventId'])
        stationsWidget.setWindowTitle("Array %s - Event %s" % v)
        stationsWidget.show()
        
    
    def onSelectStation(self, state):   # select one station => list of events of which times belong to the time of this GUI's array
        sndr = self.sender ()
        self.PH5View.selectedStations = [s for s in self.array['stations'] if s['stationRbtn'] == self.sender()] #only one station in the selectedStations
        self.eventsWidget = eventsWidget = ES_Gui(self, ESType='EVENT', array=self.array, submitType=True)
        eventsWidget.setGeometry(130, 100, 650,700)
        v = (self.array['arrayId'], self.PH5View.selectedStations[0]['stationId'])
        eventsWidget.setWindowTitle("Array %s - Station %s" % v)
        eventsWidget.show()
        

        
    ###################################
    # Author: Lan
    # def: eventFilter(): 20151022
    # using baloon tooltip to help user understand the use of the widget (only the one install event filter)
    def eventFilter(self, object, event):
        if not self.submitType and not self.PH5View.helpEnable: return False
        if self.submitType and not self.helpEnable: return False

        if event.type() == QtCore.QEvent.Enter:

            if object not in self.EXPL.keys(): return False
            #print object
            P = object.pos()
            #print P
            if object.__class__.__name__ == 'QRadioButton' \
            or (not self.submitType and object.__class__.__name__ == 'QCheckBox'):
                QtGui.QToolTip.showText(self.scrollPanel.mapToGlobal(QtCore.QPoint(P.x(), P.y()+20)), self.EXPL[object])
            else:
                QtGui.QToolTip.showText(self.mapToGlobal(QtCore.QPoint(P.x(), P.y()+20)), self.EXPL[object])

            return True
        return False

            
        
        
            
def changedFocusSlot(old, now):
    if (now==None and QtGui.QApplication.activeWindow()!=None):
        #print "set focus to the active window"
        QtGui.QApplication.activeWindow().setFocus()
        
        
if __name__ == '__main__':
    global application #, pointerWidget
     
    application = QtGui.QApplication(sys.argv)
    QtCore.QObject.connect(application, QtCore.SIGNAL("focusChanged(QWidget *, QWidget *)"), changedFocusSlot)
    #pointerWidget = SelectedStation(None, showPos=True); pointerWidget.hide()
    ex = PH5Visualizer()
    #ex = PH5Visualizer(order='shot')
    #win = OptionPanel(None)
    app.run()
    app.deleteLater()
    sys.exit(application.exec_())