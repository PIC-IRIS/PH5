#!/usr/bin/env pnpython4

import sys
import time
from ph5.core import columns
from PyQt4 import QtGui, QtCore

PROG_VERSION = "2016.245"

class KefMaker(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self)

        self.title = QtGui.QLabel("<b>Experiment_t Generator</b>")
        self.title.setAlignment(QtCore.Qt.AlignHCenter)

        #Kef Entry Labels/LineEdits
        self.nicknameLabel = QtGui.QLabel("nickname_s:")
        self.nickname = QtGui.QLineEdit()
        self.longnameLabel = QtGui.QLabel("longname_s:")
        self.longname = QtGui.QLineEdit()
        self.netcodeLabel = QtGui.QLabel("net_code_s:")
        self.netcode = QtGui.QLineEdit()
        self.pisLabel = QtGui.QLabel("PIs_s:")
        self.pis = QtGui.QLineEdit()
        self.institutionsLabel = QtGui.QLabel("institutions_s:")
        self.institutions = QtGui.QLineEdit()
        self.nwXValLabel = QtGui.QLabel("north_west_corner/X/value_d:")
        self.nwXVal = QtGui.QLineEdit()
        self.nwXUnitLabel = QtGui.QLabel("north_west_corner/X/units_s:")
        self.nwXUnit = QtGui.QLineEdit()
        self.nwYValLabel = QtGui.QLabel("north_west_corner/Y/value_d:")
        self.nwYVal = QtGui.QLineEdit()
        self.nwYUnitLabel = QtGui.QLabel("north_west_corner/Y/units_s:")
        self.nwYUnit = QtGui.QLineEdit()
        self.nwZValLabel = QtGui.QLabel("north_west_corner/Z/value_d:")
        self.nwZVal = QtGui.QLineEdit()
        self.nwZUnitLabel = QtGui.QLabel("north_west_corner/Z/units_s:")
        self.nwZUnit = QtGui.QLineEdit()
        self.nwCoordLabel = QtGui.QLabel(
            "north_west_corner/coordinate_system_s:")
        self.nwCoord = QtGui.QLineEdit()
        self.nwCoordLabel = QtGui.QLabel(
            "north_west_corner/coordinate_system_s:")
        self.nwCoord = QtGui.QLineEdit()
        self.nwProjLabel = QtGui.QLabel(
            "north_west_corner/projection_s:")
        self.nwProj = QtGui.QLineEdit()
        self.nwEllipLabel = QtGui.QLabel(
            "north_west_corner/ellipsoid_s:")
        self.nwEllip = QtGui.QLineEdit()    
        self.nwDescLabel = QtGui.QLabel(
            "north_west_corner/description_s:")
        self.nwDesc = QtGui.QLineEdit()
        self.seXValLabel = QtGui.QLabel("south_east_corner/X/value_d:")
        self.seXVal = QtGui.QLineEdit()
        self.seXUnitLabel = QtGui.QLabel("south_east_corner/X/units_s:")
        self.seXUnit = QtGui.QLineEdit()
        self.seYValLabel = QtGui.QLabel("south_east_corner/Y/value_d:")
        self.seYVal = QtGui.QLineEdit()
        self.seYUnitLabel = QtGui.QLabel("south_east_corner/Y/units_s:")
        self.seYUnit = QtGui.QLineEdit()
        self.seZValLabel = QtGui.QLabel("south_east_corner/Z/value_d:")
        self.seZVal = QtGui.QLineEdit()
        self.seZUnitLabel = QtGui.QLabel("south_east_corner/Z/units_s:")
        self.seZUnit = QtGui.QLineEdit()        
        self.seCoordLabel = QtGui.QLabel(
            "south_east_corner/coordinate_system_s:")
        self.seCoord = QtGui.QLineEdit()
        self.seCoordLabel = QtGui.QLabel(
            "south_east_corner/coordinate_system_s:")
        self.seCoord = QtGui.QLineEdit()
        self.seProjLabel = QtGui.QLabel(
            "south_east_corner/projection_s:")
        self.seProj = QtGui.QLineEdit()
        self.seEllipLabel = QtGui.QLabel(
            "south_east_corner/ellipsoid_s:")
        self.seEllip = QtGui.QLineEdit()    
        self.seDescLabel = QtGui.QLabel(
            "south_east_corner/description_s:")
        self.seDesc = QtGui.QLineEdit()
        self.summaryParagraphLabel = QtGui.QLabel(
            "summary_paragraph_s:")
        self.summaryParagraph = QtGui.QLineEdit()
        self.experimentIdLabel = QtGui.QLabel ("experiment_id_s:")
        self.experimentId = QtGui.QLineEdit()
        self.timeAsciiLabel = QtGui.QLabel(
            "time_stamp/ascii_s:")
        self.timeAscii = QtGui.QLineEdit(str(time.ctime(time.time())))
        self.timeEpochLabel = QtGui.QLabel(
            "time_stamp/epoch_l:")
        self.timeEpoch = QtGui.QLineEdit(str(int(time.time())))
        self.timeMSLabel = QtGui.QLabel(
            "time_stamp/micro_seconds_i:")
        self.timeMS = QtGui.QLineEdit('0')
        self.timeTypeLabel = QtGui.QLabel(
            "time_stamp/type_s:")
        self.timeType = QtGui.QLineEdit('BOTH')

        #Other Widgets / Layout Definition
        layoutMain = QtGui.QVBoxLayout(self)
        self.splitter = QtGui.QSplitter()
        self.layout = QtGui.QWidget()
        self.layout2 = QtGui.QWidget()
        self.layout3 = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(self.layout)
        layout2 = QtGui.QVBoxLayout(self.layout2)
        layout3 = QtGui.QVBoxLayout(self.layout3)
        self.generateButton = QtGui.QPushButton("Generate Kef")
        self.generateButton.clicked.connect(self.chooseFile)

        #Layout Presentation
        layoutMain.addWidget(self.title)
        layoutMain.addWidget(self.splitter)
        self.splitter.addWidget(self.layout)
        self.splitter.addWidget(self.layout2)
        self.splitter.addWidget(self.layout3)

        layout.addWidget(self.nicknameLabel)
        layout.addWidget(self.nickname)
        layout.addWidget(self.longnameLabel)
        layout.addWidget(self.longname)
        layout.addWidget (self.netcodeLabel)
        layout.addWidget (self.netcode)
        layout.addWidget(self.pisLabel)
        layout.addWidget(self.pis)
        layout.addWidget(self.institutionsLabel)
        layout.addWidget(self.institutions)
        layout.addWidget(self.nwXValLabel)
        layout.addWidget(self.nwXVal)
        layout.addWidget(self.nwXUnitLabel)
        layout.addWidget(self.nwXUnit) 
        layout.addWidget(self.nwYValLabel)
        layout.addWidget(self.nwYVal)
        layout.addWidget(self.nwYUnitLabel)
        layout.addWidget(self.nwYUnit)
        layout.addWidget(self.nwZValLabel)
        layout.addWidget(self.nwZVal)
        layout.addWidget(self.nwZUnitLabel)
        layout.addWidget(self.nwZUnit)

        layout2.addWidget(self.nwCoordLabel)
        layout2.addWidget(self.nwCoord)
        layout2.addWidget(self.nwProjLabel)
        layout2.addWidget(self.nwProj)
        layout2.addWidget(self.nwEllipLabel)
        layout2.addWidget(self.nwEllip)
        layout2.addWidget(self.nwDescLabel)
        layout2.addWidget(self.nwDesc)
        layout2.addWidget(self.seXValLabel)
        layout2.addWidget(self.seXVal)
        layout2.addWidget(self.seXUnitLabel)
        layout2.addWidget(self.seXUnit) 
        layout2.addWidget(self.seYValLabel)
        layout2.addWidget(self.seYVal)
        layout2.addWidget(self.seYUnitLabel)
        layout2.addWidget(self.seYUnit)
        layout2.addWidget(self.seZValLabel)
        layout2.addWidget(self.seZVal)
        layout2.addWidget(self.seZUnitLabel)
        layout2.addWidget(self.seZUnit)

        layout3.addWidget(self.seCoordLabel)
        layout3.addWidget(self.seCoord)
        layout3.addWidget(self.seProjLabel)
        layout3.addWidget(self.seProj)
        layout3.addWidget(self.seEllipLabel)
        layout3.addWidget(self.seEllip)
        layout3.addWidget(self.seDescLabel)
        layout3.addWidget(self.seDesc)
        layout3.addWidget(self.summaryParagraphLabel)
        layout3.addWidget(self.summaryParagraph)
        layout3.addWidget (self.experimentIdLabel)
        layout3.addWidget (self.experimentId)
        layout3.addWidget(self.timeAsciiLabel)
        layout3.addWidget(self.timeAscii)
        layout3.addWidget(self.timeEpochLabel)
        layout3.addWidget(self.timeEpoch)
        layout3.addWidget(self.timeMSLabel)
        layout3.addWidget(self.timeMS)     
        layout3.addWidget(self.timeTypeLabel)
        layout3.addWidget(self.timeType)  
        layout3.addWidget(self.generateButton)

        #For Saving
        self.kLabels = []
        self.kVals = {}
        self.kLabels.append(str(self.nicknameLabel.text()[:-1]))
        self.kLabels.append(str(self.longnameLabel.text()[:-1]))
        self.kLabels.append (str (self.netcodeLabel.text ()[:-1]))
        self.kLabels.append(str(self.pisLabel.text()[:-1]))
        self.kLabels.append(str(self.institutionsLabel.text()[:-1]))
        self.kLabels.append(str(self.nwXValLabel.text()[:-1]))
        self.kLabels.append(str(self.nwXUnitLabel.text()[:-1]))
        self.kLabels.append(str(self.nwYValLabel.text()[:-1]))
        self.kLabels.append(str(self.nwYUnitLabel.text()[:-1]))
        self.kLabels.append(str(self.nwZValLabel.text()[:-1]))
        self.kLabels.append(str(self.nwZUnitLabel.text()[:-1]))
        self.kLabels.append(str(self.nwCoordLabel.text()[:-1]))
        self.kLabels.append(str(self.nwProjLabel.text()[:-1]))
        self.kLabels.append(str(self.nwEllipLabel.text()[:-1]))
        self.kLabels.append(str(self.nwDescLabel.text()[:-1]))
        self.kLabels.append(str(self.seXValLabel.text()[:-1]))
        self.kLabels.append(str(self.seXUnitLabel.text()[:-1]))
        self.kLabels.append(str(self.seYValLabel.text()[:-1]))
        self.kLabels.append(str(self.seYUnitLabel.text()[:-1]))
        self.kLabels.append(str(self.seZValLabel.text()[:-1]))
        self.kLabels.append(str(self.seZUnitLabel.text()[:-1]))
        self.kLabels.append(str(self.seCoordLabel.text()[:-1]))
        self.kLabels.append(str(self.seProjLabel.text()[:-1]))
        self.kLabels.append(str(self.seEllipLabel.text()[:-1]))
        self.kLabels.append(str(self.seDescLabel.text()[:-1]))
        self.kLabels.append(str(self.summaryParagraphLabel.text()[:-1]))
        self.kLabels.append (str (self.experimentIdLabel.text ()[:-1]))
        self.kLabels.append(str(self.timeAsciiLabel.text()[:-1]))
        self.kLabels.append(str(self.timeEpochLabel.text()[:-1]))
        self.kLabels.append(str(self.timeMSLabel.text()[:-1]))
        self.kLabels.append(str(self.timeTypeLabel.text()[:-1]))

    def chooseFile(self):
        outFilename = str(QtGui.QFileDialog.getSaveFileName())
        if not outFilename: return
        self.generateKef(outFilename)

    def generateKef(self, out):
        self.kVals[0] = (str(self.nickname.text()))
        self.kVals[1] = (str(self.longname.text()))
        self.kVals[2] = (str (self.netcode.text ()))
        self.kVals[3] = (str(self.pis.text()))
        self.kVals[4] = (str(self.institutions.text()))
        self.kVals[5] = (str(self.nwXVal.text()))
        self.kVals[6] = (str(self.nwXUnit.text()))
        self.kVals[7] = (str(self.nwYVal.text()))
        self.kVals[8] = (str(self.nwYUnit.text()))
        self.kVals[9] = (str(self.nwZVal.text()))
        self.kVals[10] = (str(self.nwZUnit.text()))
        self.kVals[11] = (str(self.nwCoord.text()))
        self.kVals[12] = (str(self.nwProj.text()))
        self.kVals[13] = (str(self.nwEllip.text()))
        self.kVals[14] = (str(self.nwDesc.text()))
        self.kVals[15] = (str(self.seXVal.text()))
        self.kVals[16] = (str(self.seXUnit.text()))
        self.kVals[17] = (str(self.seYVal.text()))
        self.kVals[18] = (str(self.seYUnit.text()))
        self.kVals[19] = (str(self.seZVal.text()))
        self.kVals[20] = (str(self.seZUnit.text()))
        self.kVals[21] = (str(self.seCoord.text()))
        self.kVals[22] = (str(self.seProj.text()))
        self.kVals[23] = (str(self.seEllip.text()))
        self.kVals[24] = (str(self.seDesc.text()))
        for c in self.summaryParagraph.text():
            if c == '\n':
                c = ' '
        self.kVals[25] = (str(self.summaryParagraph.text()))
        self.kVals[26] = (str (self.experimentId.text ()))
        self.kVals[27] = (str(self.timeAscii.text ()))
        self.kVals[28] = (str(self.timeEpoch.text ()))
        self.kVals[29] = '0'
        self.kVals[30] = 'BOTH'

        outFile = open(out, "w")
        outFile.write("#\n")
        outFile.write("#%s\t%s\n" % (time.ctime(), columns.PH5VERSION))
        outFile.write("#\n")
        outFile.write("#   Table row 1\n")
        outFile.write("/Experiment_g/Experiment_t\n")
    
        for i in range(len(self.kLabels)):
            outFile.write("\t%s = %s\n" % (self.kLabels[i], self.kVals[i]))
        outFile.close()


def startapp():
    app = QtGui.QApplication(sys.argv)
    win = KefMaker()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    startapp()
