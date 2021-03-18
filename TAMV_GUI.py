#!/usr/bin/env python3

# TAMV version 2.0RC1
# Python Script to align multiple tools on Jubilee printer with Duet3d Controller
# Using images from USB camera and finding circles in those images
#
# TAMV originally Copyright (C) 2020 Danal Estes all rights reserved.
# TAMV 2.0 Copyright (C) 2021 Haytham Bennani all rights reserved.
# Released under The MIT License. Full text available via https://opensource.org/licenses/MIT
#
# Requires OpenCV to be installed on Pi
# Requires running via the OpenCV installed python (that is why no shebang)
# Requires network connection to Duet based printer running Duet/RepRap V2 or V3
#

#from PyQt5 import QtGui
from PyQt5.QtWidgets import (
    QWidget, 
    QApplication, 
    QLabel, 
    QGridLayout,
    QMainWindow,
    QPushButton,
    QLineEdit,
    QDialog,
    QStatusBar,
    QDialogButtonBox,
    QMenuBar,
    QMenu,
    QAction,
    QTextEdit,
    QSpinBox,
    QCheckBox,
    QInputDialog,
    QMessageBox,
    QDesktopWidget,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QSlider
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QIcon
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread, QMutex, QPoint, QSize

import os
import sys
import cv2
import numpy as np
import math
import DuetWebAPI as DWA
from time import sleep, time
import datetime
import json
# styles
global style_green, style_red, style_disabled, style_orange
style_green = 'background-color: green; color: white;'
style_red = 'background-color: red; color: white;'
style_disabled = 'background-color: #cccccc; color: #999999; border-style: solid;'
style_orange = 'background-color: dark-grey; color: orange;'


class printerDriver:
    # Constructor used to connect to printerURL
    def __init__(self, printerURL):
        None

    # Generic gcode command, returns 0 if success, error_code otherwise
    def gCode(self, command):
        None

    # get user coordinates (not absolute machine coordinates) and return as tuple array (axis_name: position)
    def getCoords(self):
        None

    # get firmware version and board type
    def printerType(self):
        None

    # get number of tools defined on the machine
    def getNumTools(self):
        None

    # get tool offset definitions
    def getToolOffsets(self,tool):
        None

    # reset jerk, max acceleration, max feedrate, and print and travel acceleration
    def resetMovementParameters(self):
        None

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    change_status = pyqtSignal(str)

    def __init__(self, src=0, width=640, height=480):
        super().__init__()
        self._run_flag = True
        self.src = src
        self.width = width
        self.height = height
        self.brightness_default = 0
        self.contrast_default = 0
        self.saturation_default = 0
        self.hue_default = 0
        self.brightness = -1
        self.contrast = -1
        self.saturation = -1
        self.hue = -1

        self.test_flag = False

    def run(self):
        try:
            # capture from web cam
            self.cap = cv2.VideoCapture(self.src,cv2.CAP_ANY)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
            self.cap.set(cv2.CAP_PROP_FPS,25)
            #self.backendName = self.cap.getBackendName()
            self.brightness_default = self.cap.get(cv2.CAP_PROP_BRIGHTNESS)
            self.contrast_default = self.cap.get(cv2.CAP_PROP_CONTRAST)
            self.saturation_default = self.cap.get(cv2.CAP_PROP_SATURATION)
            self.hue_default = self.cap.get(cv2.CAP_PROP_HUE)
            
            while self._run_flag:
                ret, cv_img = self.cap.read()
                if ret:
                    self.change_pixmap_signal.emit(cv_img)
                app.processEvents()
        except Exception as v1:
            self.change_status.emit('VERROR: ' + str(v1))
        # shut down capture system
        self.cap.release()

    def stop(self):
        # Sets run flag to False and waits for thread to finish
        self._run_flag = False
        self.wait()

    def setProperty(self,brightness=-1, contrast=-1, saturation=-1, hue=-1):
        try:
            if int(brightness) >= 0:
                self.brightness = brightness
                self.cap.set(cv2.CAP_PROP_BRIGHTNESS,self.brightness)
        except Exception as b1: 
            print('Brightness exception: ', b1 )
        try:
            if int(contrast) >= 0:
                self.contrast = contrast
                self.cap.set(cv2.CAP_PROP_CONTRAST,self.contrast)
        except Exception as c1:
            print('Contrast exception: ', c1 )
        try:
            if int(saturation) >= 0:
                self.saturation = saturation
                self.cap.set(cv2.CAP_PROP_SATURATION,self.saturation)
        except Exception as s1:
            print('Saturation exception: ', s1 )
        try:
            if int(hue) >= 0:
                self.hue = hue
                self.cap.set(cv2.CAP_PROP_HUE,self.hue)
        except Exception as h1:
            print('Hue exception: ', h1 )

    def getProperties(self):
        return (self.brightness_default, self.contrast_default, self.saturation_default,self.hue_default)

    def resetProperties(self):
        self.setProperty(brightness=self.brightness_default, contrast = self.contrast_default, saturation=self.saturation_default, hue=self.hue_default)

class CPDialog(QDialog):
    def __init__(self,
                parent=None,
                title='Set Controlled Point',
                summary='<b>Instructions:</b><br>Jog until controlled point is centered in the window.<br>Click OK to save and return to main window.',
                disabled = False):
        super(CPDialog,self).__init__(parent=parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
        self.setWindowTitle(title)
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QGridLayout()
        self.layout.setSpacing(3)
        # add information panel
        self.cp_info = QLabel(summary)
        # add jogging grid
        self.buttons={}
        buttons_layout = QGridLayout()

        # X
        self.button_x1 = QPushButton('-1')
        self.button_x2 = QPushButton('-0.1')
        self.button_x3 = QPushButton('-0.01')
        self.button_x4 = QPushButton('+0.01')
        self.button_x5 = QPushButton('+0.1')
        self.button_x6 = QPushButton('+1')
        # set X sizes
        self.button_x1.setFixedSize(60,60) 
        self.button_x2.setFixedSize(60,60)
        self.button_x3.setFixedSize(60,60)
        self.button_x4.setFixedSize(60,60)
        self.button_x5.setFixedSize(60,60)
        self.button_x6.setFixedSize(60,60)
        # attach actions
        self.button_x1.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 X-1 G90'))
        self.button_x2.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 X-0.1 G90'))
        self.button_x3.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 X-0.01 G90'))
        self.button_x4.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 X0.01 G90'))
        self.button_x5.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 X0.1 G90'))
        self.button_x6.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 X1 G90'))
        # add buttons to window
        x_label = QLabel('X')
        buttons_layout.addWidget(x_label,0,0)
        buttons_layout.addWidget(self.button_x1,0,1)
        buttons_layout.addWidget(self.button_x2,0,2)
        buttons_layout.addWidget(self.button_x3,0,3)
        buttons_layout.addWidget(self.button_x4,0,4)
        buttons_layout.addWidget(self.button_x5,0,5)
        buttons_layout.addWidget(self.button_x6,0,6)

        # Y
        self.button_y1 = QPushButton('-1')
        self.button_y2 = QPushButton('-0.1')
        self.button_y3 = QPushButton('-0.01')
        self.button_y4 = QPushButton('+0.01')
        self.button_y5 = QPushButton('+0.1')
        self.button_y6 = QPushButton('+1')
        # set X sizes
        self.button_y1.setFixedSize(60,60)
        self.button_y2.setFixedSize(60,60)
        self.button_y3.setFixedSize(60,60)
        self.button_y4.setFixedSize(60,60)
        self.button_y5.setFixedSize(60,60)
        self.button_y6.setFixedSize(60,60)
        # attach actions
        self.button_y1.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Y-1 G90'))
        self.button_y2.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Y-0.1 G90'))
        self.button_y3.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Y-0.01 G90'))
        self.button_y4.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Y0.01 G90'))
        self.button_y5.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Y0.1 G90'))
        self.button_y6.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Y1 G90'))
        # add buttons to window
        y_label = QLabel('Y')
        buttons_layout.addWidget(y_label,1,0)
        buttons_layout.addWidget(self.button_y1,1,1)
        buttons_layout.addWidget(self.button_y2,1,2)
        buttons_layout.addWidget(self.button_y3,1,3)
        buttons_layout.addWidget(self.button_y4,1,4)
        buttons_layout.addWidget(self.button_y5,1,5)
        buttons_layout.addWidget(self.button_y6,1,6)

        # Z
        self.button_z1 = QPushButton('-1')
        self.button_z2 = QPushButton('-0.1')
        self.button_z3 = QPushButton('-0.01')
        self.button_z4 = QPushButton('+0.01')
        self.button_z5 = QPushButton('+0.1')
        self.button_z6 = QPushButton('+1')
        # set X sizes
        self.button_z1.setFixedSize(60,60) 
        self.button_z2.setFixedSize(60,60)
        self.button_z3.setFixedSize(60,60)
        self.button_z4.setFixedSize(60,60)
        self.button_z5.setFixedSize(60,60)
        self.button_z6.setFixedSize(60,60)
        # attach actions
        self.button_z1.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Z-1 G90'))
        self.button_z2.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Z-0.1 G90'))
        self.button_z3.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Z-0.01 G90'))
        self.button_z4.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Z0.01 G90'))
        self.button_z5.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Z0.1 G90'))
        self.button_z6.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Z1 G90'))
        # add buttons to window
        z_label = QLabel('Z')
        buttons_layout.addWidget(z_label,2,0)
        buttons_layout.addWidget(self.button_z1,2,1)
        buttons_layout.addWidget(self.button_z2,2,2)
        buttons_layout.addWidget(self.button_z3,2,3)
        buttons_layout.addWidget(self.button_z4,2,4)
        buttons_layout.addWidget(self.button_z5,2,5)
        buttons_layout.addWidget(self.button_z6,2,6)

        #self.macro_field = QLineEdit()
        #self.button_macro = QPushButton('Run macro')
        #buttons_layout.addWidget(self.button_macro,3,1,2,1)
        #buttons_layout.addWidget(self.macro_field,3,2,1,-1)


        # Set up items on dialog grid
        self.layout.addWidget(self.cp_info,0,0,1,-1)
        self.layout.addLayout(buttons_layout,1,0,3,7)
        # OK/Cancel buttons
        self.layout.addWidget(self.buttonBox)
                
        # apply layout
        self.setLayout(self.layout)
    
    def setSummaryText(self, message):
        self.cp_info.setText(message)

class DebugDialog(QDialog):
    def __init__(self,parent=None, message=''):
        super(DebugDialog,self).__init__(parent=parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
        self.setWindowTitle('Debug Information')
        # Set layout details
        self.layout = QGridLayout()
        self.layout.setSpacing(3)
        
        # text area
        self.textarea = QTextEdit()
        self.textarea.setAcceptRichText(False)
        self.textarea.setReadOnly(True)
        self.layout.addWidget(self.textarea,0,0)
        # apply layout
        self.setLayout(self.layout)
        temp_text = ''
        try:
            if self.parent().video_thread.isRunning():
                temp_text += 'Video thread running\n'
        except Exception as e1:
            None
        if len(message) > 0:
            temp_text += '\nCalibration Debug Messages:\n' + message
        self.textarea.setText(temp_text)

class CameraSettingsDialog(QDialog):
    def __init__(self,parent=None, message=''):
        super(CameraSettingsDialog,self).__init__(parent=parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
        self.setWindowTitle('Camera Settings')
        
        QBtn = QDialogButtonBox.Close
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        # Get camera settings from video thread
        try:
            (brightness_input, contrast_input, saturation_input, hue_input) = self.parent().video_thread.getProperties()
        except Exception as set1:
            self.updateStatusbar('Error fetching camera parameters.')
            print('ERROR: Camera Settings: ' + str(set1))
        
        # Set layout details
        self.layout = QVBoxLayout()
        self.layout.setSpacing(3)
        # apply layout
        self.setLayout(self.layout)

        # Brightness slider
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setMinimum(0)
        self.brightness_slider.setMaximum(32)
        self.brightness_slider.setValue(int(brightness_input))
        self.brightness_slider.valueChanged.connect(self.changeBrightness)
        self.brightness_slider.setTickPosition(QSlider.TicksBelow)
        self.brightness_slider.setTickInterval(1)
        self.brightness_label = QLabel(str(int(brightness_input)))
        # Contrast slider
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setMinimum(0)
        self.contrast_slider.setMaximum(32)
        self.contrast_slider.setValue(int(contrast_input))
        self.contrast_slider.valueChanged.connect(self.changeContrast)
        self.contrast_slider.setTickPosition(QSlider.TicksBelow)
        self.contrast_slider.setTickInterval(1)
        self.contrast_label = QLabel(str(int(contrast_input)))
        # Saturation slider
        self.saturation_slider = QSlider(Qt.Horizontal)
        self.saturation_slider.setMinimum(0)
        self.saturation_slider.setMaximum(32)
        self.saturation_slider.setValue(int(saturation_input))
        self.saturation_slider.valueChanged.connect(self.changeSaturation)
        self.saturation_slider.setTickPosition(QSlider.TicksBelow)
        self.saturation_slider.setTickInterval(1)
        self.saturation_label = QLabel(str(int(saturation_input)))
        # Hue slider
        self.hue_slider = QSlider(Qt.Horizontal)
        self.hue_slider.setMinimum(0)
        self.hue_slider.setMaximum(16)
        self.hue_slider.setValue(int(hue_input))
        self.hue_slider.valueChanged.connect(self.changeHue)
        self.hue_slider.setTickPosition(QSlider.TicksBelow)
        self.hue_slider.setTickInterval(1)
        self.hue_label = QLabel(str(int(hue_input)))
        # Reset button
        self.reset_button = QPushButton("Reset to defaults")
        self.reset_button.setToolTip('Reset camera settings to defaults.')
        self.reset_button.clicked.connect(self.resetDefaults)
        
        # Layout objects
        # Brightness
        self.brightness_box =QGroupBox('Brightness')
        self.layout.addWidget(self.brightness_box)
        bvbox = QHBoxLayout()
        self.brightness_box.setLayout(bvbox)
        bvbox.addWidget(self.brightness_slider)
        bvbox.addWidget(self.brightness_label)
        # Contrast
        self.contrast_box =QGroupBox('Contrast')
        self.layout.addWidget(self.contrast_box)
        cvbox = QHBoxLayout()
        self.contrast_box.setLayout(cvbox)
        cvbox.addWidget(self.contrast_slider)
        cvbox.addWidget(self.contrast_label)
        # Saturation
        self.saturation_box =QGroupBox('Saturation')
        self.layout.addWidget(self.saturation_box)
        svbox = QHBoxLayout()
        self.saturation_box.setLayout(svbox)
        svbox.addWidget(self.saturation_slider)
        svbox.addWidget(self.saturation_label)
        # Hue
        self.hue_box =QGroupBox('Hue')
        self.layout.addWidget(self.hue_box)
        hvbox = QHBoxLayout()
        self.hue_box.setLayout(hvbox)
        hvbox.addWidget(self.hue_slider)
        hvbox.addWidget(self.hue_label)
        # Reset button
        self.layout.addWidget(self.reset_button)
        # OK Cancel buttons
        self.layout.addWidget(self.buttonBox)

    def resetDefaults(self):
        self.parent().video_thread.resetProperties()
        (brightness_input, contrast_input, saturation_input, hue_input) = self.parent().video_thread.getProperties()
        
        brightness_input = int(brightness_input)
        contrast_input = int(contrast_input)
        saturation_input = int(saturation_input)
        hue_input = int(hue_input)
        self.brightness_slider.setValue(brightness_input)
        self.brightness_label.setText(str(brightness_input))
        self.contrast_slider.setValue(contrast_input)
        self.contrast_label.setText(str(contrast_input))
        self.saturation_slider.setValue(saturation_input)
        self.saturation_label.setText(str(saturation_input))
        self.hue_slider.setValue(hue_input)
        self.hue_label.setText(str(hue_input))

    def changeBrightness(self):
        parameter = int(self.brightness_slider.value())
        try:
            self.parent().video_thread.setProperty(brightness=parameter)
        except:
            None
        self.brightness_label.setText(str(parameter))

    def changeContrast(self):
        parameter = int(self.contrast_slider.value())
        try:
            self.parent().video_thread.setProperty(contrast=parameter)
        except:
            None
        self.contrast_label.setText(str(parameter))

    def changeSaturation(self):
        parameter = int(self.saturation_slider.value())
        try:
            self.parent().video_thread.setProperty(saturation=parameter)
        except:
            None
        self.saturation_label.setText(str(parameter))

    def changeHue(self):
        parameter = int(self.hue_slider.value())
        try:
            self.parent().video_thread.setProperty(hue=parameter)
        except:
            None
        self.hue_label.setText(str(parameter))

class OverlayLabel(QLabel):
    def __init__(self):
        super(OverlayLabel, self).__init__()
        self.display_text = 'Welcome to TAMV. Enter your printer address and click \"Connect..\" to start.'

    def paintEvent(self, event):
        super(OverlayLabel, self).paintEvent(event)
        pos = QPoint(10, 470)
        painter = QPainter(self)
        painter.setBrush(QColor(255,255,255,160))
        painter.setPen(QColor(255, 255, 255,0))
        painter.drawRect(0,450,640,50)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(pos, self.display_text)
    
    def setText(self, textToDisplay):
        self.display_text = textToDisplay

class CalibrateNozzles(QThread):
    # Signals
    status_update = pyqtSignal(str)
    message_update = pyqtSignal(str)
    change_pixmap_signal = pyqtSignal(np.ndarray)
    calibration_complete = pyqtSignal()
    detection_error = pyqtSignal(str)

    display_crosshair = False
    detection_on = False

    def __init__(self, parent=None, th1=1, th2=50, thstep=1, minArea=600, minCircularity=0.8,numTools=0,cycles=1, align=False):
        super(QThread,self).__init__(parent=parent)
        self.xray = False
        self.loose = False
        self.detector_changed = False
        self.detect_th1 = th1
        self.detect_th2 = th2
        self.detect_thstep = thstep
        self.detect_minArea = minArea
        self.detect_minCircularity = minCircularity
        self.numTools = numTools
        self.cycles = cycles
        self.alignment = align
        self.message_update.emit('Detector created, waiting for tool..')

        # start with detection off
        self.display_crosshair = False
        self.detection_on = False

        # Video Parameters
        self.brightness_default = 0
        self.contrast_default = 0
        self.saturation_default = 0
        self.hue_default = 0
        self.brightness = -1
        self.contrast = -1
        self.saturation = -1
        self.hue = -1

        # Start Video feed
        self.cap = cv2.VideoCapture(video_src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
        self.cap.set(cv2.CAP_PROP_FPS,25)
        self.brightness_default = self.cap.get(cv2.CAP_PROP_BRIGHTNESS)
        self.contrast_default = self.cap.get(cv2.CAP_PROP_CONTRAST)
        self.saturation_default = self.cap.get(cv2.CAP_PROP_SATURATION)
        self.hue_default = self.cap.get(cv2.CAP_PROP_HUE)

        self.ret, self.cv_img = self.cap.read()
        if self.ret:
            self.change_pixmap_signal.emit(self.cv_img)

    def toggleXray(self):
        if self.xray:
            self.xray = False
        else: self.xray = True

    def toggleLoose(self):
        self.detector_changed = True
        if self.loose:
            self.loose = False
        else: self.loose = True

    def setProperty(self,brightness=-1, contrast=-1, saturation=-1, hue=-1):
        try:
            if int(brightness) >= 0:
                self.brightness = brightness
                self.cap.set(cv2.CAP_PROP_BRIGHTNESS,self.brightness)
        except Exception as b1: 
            print('Brightness exception: ', b1 )
        try:
            if int(contrast) >= 0:
                self.contrast = contrast
                self.cap.set(cv2.CAP_PROP_CONTRAST,self.contrast)
        except Exception as c1:
            print('Contrast exception: ', c1 )
        try:
            if int(saturation) >= 0:
                self.saturation = saturation
                self.cap.set(cv2.CAP_PROP_SATURATION,self.saturation)
        except Exception as s1:
            print('Saturation exception: ', s1 )
        try:
            if int(hue) >= 0:
                self.hue = hue
                self.cap.set(cv2.CAP_PROP_HUE,self.hue)
        except Exception as h1:
            print('Hue exception: ', h1 )

    def getProperties(self):
        return (self.brightness_default, self.contrast_default, self.saturation_default,self.hue_default)

    def resetProperties(self):
        self.setProperty(brightness=self.brightness_default, contrast = self.contrast_default, saturation=self.saturation_default, hue=self.hue_default)

    def run(self):
        if self.detection_on:
            if self.alignment:
                try:
                    if self.loose:
                        self.detect_minCircularity = 0.3
                    else: self.detect_minCircularity = 0.8
                    self.createDetector()
                    self._running = True
                    # transformation matrix
                    self.transform_matrix = []
                    while self._running:
                        for rep in range(self.cycles):
                            for tool in range(self.parent().num_tools):
                                # process GUI events
                                app.processEvents()
                                # Update status bar
                                self.status_update.emit('Calibrating T' + str(tool) + ', cycle: ' + str(rep+1) + '/' + str(self.cycles))
                                # Load next tool for calibration
                                self.parent().printer.gCode('T'+str(tool))
                                # Move tool to CP coordinates
                                self.parent().printer.gCode('G1 X' + str(self.parent().cp_coords['X']))
                                self.parent().printer.gCode('G1 Y' + str(self.parent().cp_coords['Y']))
                                # Wait for moves to complete
                                while self.parent().printer.getStatus() not in 'idle':
                                    # process GUI events
                                    app.processEvents()
                                    self.ret, self.cv_img = self.cap.read()
                                    if self.ret:
                                        self.change_pixmap_signal.emit(self.cv_img)
                                # Update message bar
                                self.message_update.emit('Searching for nozzle..')
                                # Fetch a new frame from the inspection camera
                                self.ret, self.cv_img = self.cap.read()
                                if self.ret:
                                    self.change_pixmap_signal.emit(self.cv_img)
                                self.frame = self.cv_img
                                
                                # Process runtime algorithm changes
                                if self.loose:
                                    self.detect_minCircularity = 0.3
                                else: self.detect_minCircularity = 0.8
                                if self.detector_changed:
                                    self.createDetector()
                                    self.detector_changed = False
                                # Analyze frame for blobs
                                (c, transform, mpp) = self.calibrateTool(tool, rep)
                                
                                # process GUI events
                                app.processEvents()                        
                                
                                #(xy, target, rotation, radius) = self.analyzeFrame()

                        # signal end of execution
                        self._running = False
                    # Update status bar
                    self.status_update.emit('Calibration complete: Resetting machine.')
                    # Update debug window with results
                    self.parent().debugString += '\n\nCalibration output:\n'
                    for tool_result in self.parent().calibration_results:
                        self.parent().debugString += tool_result + '\n'
                    self.parent().printer.gCode('T-1')
                    self.parent().printer.gCode('G1 X' + str(self.parent().cp_coords['X']))
                    self.parent().printer.gCode('G1 Y' + str(self.parent().cp_coords['Y']))
                    self.status_update.emit('Calibration complete: Done.')
                    self.alignment = False
                    self.detection_on = False
                    self.display_crosshair = False
                    self._running = False
                    self.calibration_complete.emit()
                except Exception as mn1:
                    self.alignment = False
                    self.detection_on = False
                    self.display_crosshair = False
                    self._running = False
                    self.detection_error.emit(str(mn1))
                    self.cap.release()
                self.stop()
            else:
                # don't run alignment - fetch frames and detect only
                try:
                    if self.loose:
                        self.detect_minCircularity = 0.3
                    else: self.detect_minCircularity = 0.8
                    self.createDetector()
                    self._running = True
                    # transformation matrix
                    self.transform_matrix = []
                    while self._running:
                        # Update status bar
                        self.status_update.emit('Detection mode: ON')
                        # Fetch a new frame from the inspection camera
                        self.ret, self.cv_img = self.cap.read()
                        if self.ret:
                            self.change_pixmap_signal.emit(self.cv_img)
                        self.frame = self.cv_img
                        
                        # Process runtime algorithm changes
                        if self.loose:
                            self.detect_minCircularity = 0.3
                        else: self.detect_minCircularity = 0.8
                        if self.detector_changed:
                            self.createDetector()
                            self.detector_changed = False
                        # Run detection and update output
                        (xy, target, rotation, radius) = self.analyzeFrame()
                        # process GUI events
                        app.processEvents()
                except Exception as mn1:
                    self._running = False
                    self.detection_error.emit(str(mn1))
                    self.cap.release()
                self.stop()
        else:
            while not self.detection_on:
                try:
                    self.ret, self.cv_img = self.cap.read()
                    if self.ret:
                        self.change_pixmap_signal.emit(self.cv_img)
                    app.processEvents()
                except Exception as mn2:
                    self.status_update( 'Error: ' + str(mn2) )
                    self.cap.release()
                    self.detection_on = False
                    self._running = False
                    break
        self.cap.release()

    def analyzeFrame(self):
        # Placeholder coordinates
        xy = [0,0]
        # Counter of frames with no circle.
        nocircle = 0
        # Random time offset
        rd = int(round(time()*1000))

        while True:
            self.ret, self.frame = self.cap.read()
            try:
                # capture tool location in machine space before processing
                toolCoordinates = self.parent().printer.getCoords()
            except: continue
            # capture first clean frame for display
            cleanFrame = self.frame
            # apply nozzle detection algorithm
            # Detection algorithm 1:
            #    gamma correction -> use Y channel from YUV -> GaussianBlur (7,7),6 -> adaptive threshold
            gammaInput = 1.2
            self.frame = self.adjust_gamma(image=self.frame, gamma=gammaInput)
            yuv = cv2.cvtColor(self.frame, cv2.COLOR_BGR2YUV)
            yuvPlanes = cv2.split(yuv)
            yuvPlanes[0] = cv2.GaussianBlur(yuvPlanes[0],(7,7),6)
            yuvPlanes[0] = cv2.adaptiveThreshold(yuvPlanes[0],255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,35,1)
            self.frame = cv2.cvtColor(yuvPlanes[0],cv2.COLOR_GRAY2BGR)
            target = [int(np.around(self.frame.shape[1]/2)),int(np.around(self.frame.shape[0]/2))]
            # Process runtime algorithm changes
            if self.loose:
                self.detect_minCircularity = 0.3
            else: self.detect_minCircularity = 0.8
            if self.detector_changed:
                #print('Creating new detector..')
                self.createDetector()
                self.detector_changed = False
            # run nozzle detection for keypoints
            keypoints = self.detector.detect(self.frame)
            # draw the timestamp on the frame AFTER the circle detector! Otherwise it finds the circles in the numbers.
            if self.xray:
                cleanFrame = self.frame
            # check if we are displaying a crosshair
            if self.display_crosshair:
                self.frame = cv2.line(cleanFrame, (target[0],    target[1]-25), (target[0],    target[1]+25), (0, 255, 0), 1)
                self.frame = cv2.line(self.frame, (target[0]-25, target[1]   ), (target[0]+25, target[1]   ), (0, 255, 0), 1)
            else: self.frame = cleanFrame
            # update image
            self.change_pixmap_signal.emit(self.frame)

            if(nocircle> 25):
                self.message_update.emit( 'Error in detecting nozzle.' )
                nocircle = 0
                continue
            num_keypoints=len(keypoints)
            if (num_keypoints == 0):
                if (25 < (int(round(time() * 1000)) - rd)):
                    nocircle += 1
                    self.frame = self.putText(self.frame,'No circles found',offsety=3)
                    self.message_update.emit( 'No circles found.' )
                    self.change_pixmap_signal.emit(self.frame)
                continue
            if (num_keypoints > 1):
                if (25 < (int(round(time() * 1000)) - rd)):
                    self.message_update.emit( 'Too many circles found. Please stop and clean the nozzle.' )
                    self.frame = self.putText(self.frame,'Too many circles found '+str(num_keypoints),offsety=3, color=(255,255,255))
                    self.frame = cv2.drawKeypoints(self.frame, keypoints, np.array([]), (255,255,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
                    self.change_pixmap_signal.emit(self.frame)
                continue
            # Found one and only one circle.  Put it on the frame.
            nocircle = 0 
            xy = np.around(keypoints[0].pt)
            r = np.around(keypoints[0].size/2)
            # draw the blobs that look circular
            self.frame = cv2.drawKeypoints(self.frame, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
            # Note its radius and position
            ts =  'U{0:3.0f} V{1:3.0f} R{2:2.0f}'.format(xy[0],xy[1],r)
            xy = np.uint16(xy)
            #self.frame = self.putText(self.frame, ts, offsety=2, color=(0, 255, 0), stroke=2)
            self.message_update.emit(ts)
            # show the frame
            self.change_pixmap_signal.emit(self.frame)
            rd = int(round(time() * 1000))
            #end the loop
            break

        # and tell our parent.
        return (xy, target, toolCoordinates, r)

    def calibrateTool(self, tool, rep):
        # timestamp for caluclating tool calibration runtime
        self.startTime = time()
        # average location of keypoints in frame
        self.average_location=[0,0]
        # current location
        self.current_location = {'X':0,'Y':0}
        # guess position used for camera calibration
        self.guess_position  = [1,1]
        # current keypoint location
        self.xy = [0,0]
        # previous keypoint location
        self.oldxy  = self.xy
        # Tracker flag to set which state algorithm is running in
        self.state = 0
        # detected blob counter
        self.detect_count = 0
        # Save CP coordinates to local class
        self.cp_coordinates = self.parent().cp_coords
        # number of average position loops
        self.position_iterations = 5
        # calibration move set (0.5mm radius circle over 10 moves)
        self.calibrationCoordinates = [ [0,-0.5], [0.294,-0.405], [0.476,-0.155], [0.476,0.155], [0.294,0.405], [0,0.5], [-0.294,0.405], [-0.476,0.155], [-0.476,-0.155], [-0.294,-0.405] ]

        # Check if camera calibration matrix is already defined
        if len(self.transform_matrix) > 1:
            # set state flag to Step 2: nozzle alignment stage
            self.state = 200
            self.parent().debugString += 'Calibrating T'+str(tool)+':C'+str(rep)+': '
        
        # Space coordinates
        self.space_coordinates = []
        self.camera_coordinates = []
        self.calibration_moves = 0

        while True:
            (self.xy, self.target, self.tool_coordinates, self.radius) = self.analyzeFrame()
            # analyzeFrame has returned our target coordinates, average its location and process according to state
            self.average_location[0] += self.xy[0]
            self.average_location[1] += self.xy[1]
            
            self.detect_count += 1

            # check if we've reached our number of detections for average positioning
            if self.detect_count >= self.position_iterations:
                # calculate average X Y position from detection
                self.average_location[0] /= self.detect_count
                self.average_location[1] /= self.detect_count
                # round to 3 decimal places
                self.average_location = np.around(self.average_location,3)
                # get another detection validated
                (self.xy, self.target, self.tool_coordinates, self.radius) = self.analyzeFrame()
                
                #### Step 1: camera calibration and transformation matrix calculation
                if self.state == 0:
                    self.parent().debugString += 'Camera calibrating.\n'
                    # Update GUI thread with current status and percentage complete
                    self.status_update.emit('Calibrating camera..')
                    self.message_update.emit('Calibrating rotation.. (10%)')
                    # Save position as previous location
                    self.oldxy = self.xy
                    # Reset space and camera coordinates
                    self.space_coordinates = []
                    self.camera_coordinates = []
                    # save machine coordinates for detected nozzle
                    self.space_coordinates.append( (self.tool_coordinates['X'], self.tool_coordinates['Y']) )
                    # save camera coordinates
                    self.camera_coordinates.append( (self.xy[0],self.xy[1]) )
                    # move carriage for calibration
                    self.offsetX = self.calibrationCoordinates[0][0]
                    self.offsetY = self.calibrationCoordinates[0][1]
                    self.parent().printer.gCode('G91 G1 X' + str(self.offsetX) + ' Y' + str(self.offsetY) +' F3000 G90 ')
                    # Update state tracker to second nozzle calibration move
                    self.state = 1
                    continue
                # Check if camera is still being calibrated
                elif self.state >= 1 and self.state < len(self.calibrationCoordinates):
                    # Update GUI thread with current status and percentage complete
                    self.status_update.emit('Calibrating camera..')
                    self.message_update.emit('Calibrating rotation.. (' + str(self.state*10) + '%)')
                    # check if we've already moved, and calculate mpp value
                    if self.state == 1:
                        self.mpp = np.around(0.5/self.getDistance(self.oldxy[0],self.oldxy[1],self.xy[0],self.xy[1]),4)
                    # save position as previous position
                    self.oldxy = self.xy
                    # save machine coordinates for detected nozzle
                    self.space_coordinates.append( (self.tool_coordinates['X'], self.tool_coordinates['Y']) )
                    # save camera coordinates
                    self.camera_coordinates.append( (self.xy[0],self.xy[1]) )
                    # return carriage to relative center of movement
                    self.offsetX = -1*self.offsetX
                    self.offsetY = -1*self.offsetY
                    self.parent().printer.gCode('G91 G1 X' + str(self.offsetX) + ' Y' + str(self.offsetY) +' F3000 G90 ')
                    # move carriage a random amount in X&Y to collect datapoints for transform matrix
                    self.offsetX = self.calibrationCoordinates[self.state][0]
                    self.offsetY = self.calibrationCoordinates[self.state][1]
                    self.parent().printer.gCode('G91 G1 X' + str(self.offsetX) + ' Y' + str(self.offsetY) +' F3000 G90 ')
                    # increment state tracker to next calibration move
                    self.state += 1
                    continue
                # check if final calibration move has been completed
                elif self.state == len(self.calibrationCoordinates):
                    calibration_time = np.around(time() - self.startTime,3)
                    self.parent().debugString += 'Camera calibration complete. (' + str(calibration_time) + 's)\n'
                    # Update GUI thread with current status and percentage complete
                    self.message_update.emit('Calibrating rotation.. (100%) - MPP = ' + str(self.mpp))
                    self.status_update.emit('Calibrating T' + str(tool) + ', cycle: ' + str(rep+1) + '/' + str(self.cycles))
                    # save position as previous position
                    self.oldxy = self.xy
                    # save machine coordinates for detected nozzle
                    self.space_coordinates.append( (self.tool_coordinates['X'], self.tool_coordinates['Y']) )
                    # save camera coordinates
                    self.camera_coordinates.append( (self.xy[0],self.xy[1]) )
                    # calculate camera transformation matrix
                    self.transform_input = [(self.space_coordinates[i], self.normalize_coords(camera)) for i, camera in enumerate(self.camera_coordinates)]
                    self.transform_matrix, self.transform_residual = self.least_square_mapping(self.transform_input)
                    # define camera center in machine coordinate space
                    self.newCenter = self.transform_matrix.T @ np.array([0, 0, 0, 0, 0, 1])
                    self.guess_position[0]= np.around(self.newCenter[0],3)
                    self.guess_position[1]= np.around(self.newCenter[1],3)
                    self.parent().printer.gCode('G90 G1 X{0:-1.3f} Y{1:-1.3f} F1000 G90 '.format(self.guess_position[0],self.guess_position[1]))
                    # update state tracker to next phase
                    self.state = 200
                    # start tool calibration timer
                    self.startTime = time()
                    self.parent().debugString += 'Calibrating T'+str(tool)+':C'+str(rep)+': '
                    continue
                #### Step 2: nozzle alignment stage
                elif self.state == 200:
                    self.parent().debugString += str(self.calibration_moves) + ', '
                    # Update GUI thread with current status and percentage complete
                    self.message_update.emit('Tool calibration move #' + str(self.calibration_moves))
                    self.status_update.emit('Calibrating T' + str(tool) + ', cycle: ' + str(rep+1) + '/' + str(self.cycles))
                    # increment moves counter
                    self.calibration_moves += 1
                    # nozzle detected, frame rotation is set, start
                    self.cx,self.cy = self.normalize_coords(self.xy)
                    self.v = [self.cx**2, self.cy**2, self.cx*self.cy, self.cx, self.cy, 0]
                    self.offsets = -1*(0.55*self.transform_matrix.T @ self.v)
                    self.offsets[0] = np.around(self.offsets[0],3)
                    self.offsets[1] = np.around(self.offsets[1],3)
                    # Move it a bit
                    self.parent().printer.gCode( 'M564 S1' )
                    self.parent().printer.gCode( 'G91 G1 X{0:-1.3f} Y{1:-1.3f} F1000 G90 '.format(self.offsets[0],self.offsets[1]) )
                    # save position as previous position
                    self.oldxy = self.xy
                    if ( self.offsets[0] == 0.0 and self.offsets[1] == 0.0 ):
                        # Save offset to output variable
                        _return = self.tool_coordinates
                        _return['MPP'] = self.mpp
                        _return['time'] = np.around(time() - self.startTime,3)
                        # Update GUI with progress
                        self.message_update.emit('Nozzle calibrated: offset coordinates X' + str(_return['X']) + ' Y' + str(_return['Y']) )
                        self.parent().debugString += '\nNozzle calibrated (' +str(_return['time']) + 's): offset coordinates X' + str(_return['X']) + ' Y' + str(_return['Y']) + '\n'
                        self.parent().printer.gCode( 'G1 F13200' )
                        # calculate and apply offsets to printer
                        self.tool_offsets = self.parent().printer.getG10ToolOffset(tool)
                        final_x = np.around( (self.cp_coordinates['X'] + self.tool_offsets['X']) - self.tool_coordinates['X'], 3 )
                        final_y = np.around( (self.cp_coordinates['Y'] + self.tool_offsets['Y']) - self.tool_coordinates['Y'], 3 )
                        self.parent().debugString += '\nG10 P' + str(tool) + ' X' + str(final_x) + ' Y' + str(final_y)
                        x_tableitem = QTableWidgetItem(str(np.around(final_x, 2)))
                        x_tableitem.setBackground(QColor(100,255,100,255))
                        y_tableitem = QTableWidgetItem(str(np.around(final_y, 2)))
                        y_tableitem.setBackground(QColor(100,255,100,255))
                        self.parent().offsets_table.setItem(tool,0,x_tableitem)
                        self.parent().offsets_table.setItem(tool,1,y_tableitem)
                        
                        self.parent().calibration_results.append('G10 P' + str(tool) + ' X' + str(final_x) + ' Y' + str(final_y))
                        return(_return, self.transform_matrix, self.mpp)
                    else:
                        self.state = 200
                        continue
                self.avg = [0,0]
                self.location = {'X':0,'Y':0}
                self.count = 0

    def normalize_coords(self,coords):
        xdim, ydim = camera_width, camera_height
        return (coords[0] / xdim - 0.5, coords[1] / ydim - 0.5)

    def least_square_mapping(self,calibration_points):
        # Compute a 2x2 map from displacement vectors in screen space to real space.
        n = len(calibration_points)
        real_coords, pixel_coords = np.empty((n,2)),np.empty((n,2))
        for i, (r,p) in enumerate(calibration_points):
            real_coords[i] = r
            pixel_coords[i] = p
        x,y = pixel_coords[:,0],pixel_coords[:,1]
        A = np.vstack([x**2,y**2,x * y, x,y,np.ones(n)]).T
        transform = np.linalg.lstsq(A, real_coords, rcond = None)
        return transform[0], transform[1].mean()

    def getDistance(self, x1, y1, x0, y0 ):
        x1_float = float(x1)
        x0_float = float(x0)
        y1_float = float(y1)
        y0_float = float(y0)
        x_dist = (x1_float - x0_float) ** 2
        y_dist = (y1_float - y0_float) ** 2
        retVal = np.sqrt((x_dist + y_dist))
        return np.around(retVal,3)

    def stop(self):
        self._running = False
        self.detection_on = False
        try:
            self.parent().printer.gCode('T-1')
            self.parent().printer.gCode('G1 X' + str(self.parent().cp_coords['X']) + ' Y' + str(self.parent().cp_coords['Y']))
            while self.parent().printer.getStatus() not in 'idle':
                sleep(1)
        except: None
        self.cap.release()
        self.exit()

    def createDetector(self):
        # Setup SimpleBlobDetector parameters.
        params = cv2.SimpleBlobDetector_Params()
        # Thresholds
        params.minThreshold = self.detect_th1
        params.maxThreshold = self.detect_th2
        params.thresholdStep = self.detect_thstep

        # Area
        params.filterByArea = True         # Filter by Area.
        params.minArea = self.detect_minArea

        # Circularity
        params.filterByCircularity = True  # Filter by Circularity
        params.minCircularity = self.detect_minCircularity
        params.maxCircularity= 1

        # Convexity
        params.filterByConvexity = True    # Filter by Convexity
        params.minConvexity = 0.3
        params.maxConvexity = 1

        # Inertia
        params.filterByInertia = True      # Filter by Inertia
        params.minInertiaRatio = 0.3

        # create detector
        self.detector = cv2.SimpleBlobDetector_create(params)

    def adjust_gamma(self, image, gamma=1.2):
        # build a lookup table mapping the pixel values [0, 255] to
        # their adjusted gamma values
        invGamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** invGamma) * 255
            for i in np.arange(0, 256)]).astype('uint8')
        # apply gamma correction using the lookup table
        return cv2.LUT(image, table)

    def putText(self, frame,text,color=(0, 0, 255),offsetx=0,offsety=0,stroke=1):  # Offsets are in character box size in pixels. 
        if (text == 'timestamp'): text = datetime.datetime.now().strftime('%m-%d-%Y %H:%M:%S')
        fontScale = 1
        if (frame.shape[1] > 640): fontScale = stroke = 2
        if (frame.shape[1] < 640):
            fontScale = 0.8
            stroke = 1
        offpix = cv2.getTextSize('A',   cv2.FONT_HERSHEY_SIMPLEX ,fontScale, stroke)
        textpix = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX ,fontScale, stroke)
        offsety=max(offsety, (-frame.shape[0]/2 + offpix[0][1])/offpix[0][1]) # Let offsety -99 be top row
        offsetx=max(offsetx, (-frame.shape[1]/2 + offpix[0][0])/offpix[0][0]) # Let offsetx -99 be left edge
        offsety=min(offsety,  (frame.shape[0]/2 - offpix[0][1])/offpix[0][1]) # Let offsety  99 be bottom row. 
        offsetx=min(offsetx,  (frame.shape[1]/2 - offpix[0][0])/offpix[0][0]) # Let offsetx  99 be right edge. 
        cv2.putText(frame, text, 
            (int(offsetx * offpix[0][0]) + int(frame.shape[1]/2) - int(textpix[0][0]/2)
            ,int(offsety * offpix[0][1]) + int(frame.shape[0]/2) + int(textpix[0][1]/2)),
            cv2.FONT_HERSHEY_SIMPLEX, fontScale, color, stroke)
        return(frame)

class App(QMainWindow):
    cp_coords = {}
    numTools = 0
    current_frame = np.ndarray
    mutex = QMutex()
    debugString = ''

    def __init__(self, parent=None):
        super().__init__()
        self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
        self.setWindowTitle('TAMV')
        self.setWindowIcon(QIcon('jubilee.png'))
        global display_width, display_height
        screen = QDesktopWidget().availableGeometry()
        self.small_display = False
        # HANDLE DIFFERENT DISPLAY SIZES
        # 800x600 display - fullscreen app
        if int(screen.width()) >= 800 and int(screen.height()) >= 550 and int(screen.height() < 600):
            self.small_display = True
            print('800x600 desktop detected')
            display_width = 512
            display_height = 384
            self.setWindowFlag(Qt.FramelessWindowHint)
            self.showFullScreen()
            self.setGeometry(0,0,700,500)
            app_screen = self.frameGeometry()
        # 848x480 display - fullscreen app
        elif int(screen.width()) >= 800 and int(screen.height()) < 550:
            self.small_display = True
            print('848x480 desktop detected')
            display_width = 448
            display_height = 336
            self.setWindowFlag(Qt.FramelessWindowHint)
            self.showFullScreen()
            self.setGeometry(0,0,700,400)
            app_screen = self.frameGeometry()
        # larger displays - normal window
        else:
            self.small_display = False
            display_width = 640
            display_height = 480
            self.setGeometry(QStyle.alignedRect(Qt.LeftToRight,Qt.AlignHCenter,QSize(800,600),screen))
            app_screen = self.frameGeometry()
            app_screen.moveCenter(screen.center())
            self.move(app_screen.topLeft())

        # SET UP STYLESHEETS FOR GUI ELEMENTS
        self.setStyleSheet(
            '\
            QPushButton {\
                border: 1px solid #adadad;\
                border-style: outset;\
                border-radius: 4px;\
                font: 14px;\
                padding: 6px;\
            }\
            QPushButton:hover,QPushButton:enabled:hover,QPushButton:enabled:!checked:hover {\
                background-color: #27ae60;\
                border: 1px solid #aaaaaa;\
            }\
            QPushButton:pressed,QPushButton:enabled:pressed,QPushButton:enabled:checked {\
                background-color: #ae2776;\
                border: 1px solid #aaaaaa;\
            }\
            QPushButton:enabled {\
                background-color: green;\
                color: white;\
            }\
            QPushButton#debug {\
                background-color: blue;\
                color: white;\
            }\
            QPushButton#debug:hover {\
                background-color: green;\
                color: white;\
            }\
            QPushButton#debug:pressed {\
                background-color: #ae2776;\
                border-style: inset;\
                color: white;\
            }\
            QPushButton#active {\
                background-color: green;\
                color: white;\
            }\
            QPushButton#active:pressed {\
                background-color: #ae2776;\
            }\
            QPushButton#terminate {\
                background-color: red;\
                color: white;\
            }\
            QPushButton#terminate:pressed {\
                background-color: #c0392b;\
            }\
            QPushButton:disabled, QPushButton#terminate:disabled {\
                background-color: #cccccc;\
                color: #999999;\
            }\
            QInputDialog QDialogButtonBox > QPushButton:enabled, QDialog QPushButton:enabled,QPushButton[checkable="true"]:enabled {\
                background-color: none;\
                color: black;\
                border: 1px solid #adadad;\
                border-style: outset;\
                border-radius: 4px;\
                font: 14px;\
                padding: 6px;\
            }\
            QPushButton:enabled:checked {\
                background-color: #ae2776;\
                border: 1px solid #aaaaaa;\
            }\
            QInputDialog QDialogButtonBox > QPushButton:pressed, QDialog QPushButton:pressed {\
                background-color: #ae2776;\
            }\
            QInputDialog QDialogButtonBox > QPushButton:hover:!pressed, QDialog QPushButton:hover:!pressed {\
                background-color: #27ae60;\
            }\
            '
        )

        # LOAD USER SAVED PARAMETERS OR CREATE DEFAULTS
        self.loadUserParameters()
        
        # GUI ELEMENTS DEFINITION
        # Menubar
        if not self.small_display:
            self._createActions()
            self._createMenuBar()
            self._connectActions()
        
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        
        # create the label that holds the image
        self.image_label = OverlayLabel()
        self.image_label.setFixedSize( display_width, display_height )
        pixmap = QPixmap( display_width, display_height )
        self.image_label.setPixmap(pixmap)
        
        # create a status bar
        self.statusBar = QStatusBar()
        self.statusBar.showMessage('Loading up video feed and libraries..',5000)
        self.setStatusBar( self.statusBar )

        # CP location on statusbar
        self.cp_label = QLabel('<b>CP:</b> <i>undef</i>')
        self.statusBar.addPermanentWidget(self.cp_label)
        self.cp_label.setStyleSheet(style_red)

        # Connection status on statusbar
        self.connection_status = QLabel('Disconnected')
        self.connection_status.setStyleSheet(style_red)
        self.statusBar.addPermanentWidget(self.connection_status)

        # BUTTONS
        # Connect
        self.connection_button = QPushButton('Connect..')
        self.connection_button.setToolTip('Connect to a Duet machine..')
        self.connection_button.clicked.connect(self.connectToPrinter)
        self.connection_button.setFixedWidth(170)
        # Disconnect
        self.disconnection_button = QPushButton('STOP / DISCONNECT')
        self.disconnection_button.setToolTip('End current operation,\nunload tools, and return carriage to CP\nthen disconnect.')
        self.disconnection_button.clicked.connect(self.disconnectFromPrinter)
        self.disconnection_button.setFixedWidth(170)
        self.disconnection_button.setObjectName('terminate')
        self.disconnection_button.setDisabled(True)
        # Controlled point
        self.cp_button = QPushButton('Set Controlled Point..')
        self.cp_button.setToolTip('Define your origin point\nto calculate all tool offsets from.')
        self.cp_button.clicked.connect(self.controlledPoint)
        self.cp_button.setFixedWidth(170)
        #self.cp_button.setStyleSheet(style_disabled)
        self.cp_button.setDisabled(True)
        # Calibration
        self.calibration_button = QPushButton('Start Tool Alignment')
        self.calibration_button.setToolTip('Start alignment process.\nMAKE SURE YOUR CARRIAGE IS CLEAR TO MOVE ABOUT WITHOUT COLLISIONS!')
        self.calibration_button.clicked.connect(self.runCalibration)
        #self.calibration_button.setStyleSheet(style_disabled)
        self.calibration_button.setDisabled(True)
        self.calibration_button.setFixedWidth(170)
        # Jog Panel
        self.jogpanel_button = QPushButton('Jog Panel')
        self.jogpanel_button.setToolTip('Open a control panel to move carriage.')
        self.jogpanel_button.clicked.connect(self.displayJogPanel)
        self.jogpanel_button.setDisabled(True)
        self.jogpanel_button.setFixedWidth(170)
        # Debug Info
        self.debug_button = QPushButton('Debug Information')
        self.debug_button.setToolTip('Display current debug info for troubleshooting\nand to display final G10 commands')
        self.debug_button.clicked.connect(self.displayDebug)
        self.debug_button.setFixedWidth(170)
        self.debug_button.setObjectName('debug')
        # Exit
        self.exit_button = QPushButton('Quit')
        self.exit_button.setToolTip('Unload tools, disconnect, and quit TAMV.')
        self.exit_button.clicked.connect(lambda: quit())
        self.exit_button.setFixedWidth(170)
        
        # OTHER ELEMENTS
        # Repeat spinbox
        self.repeat_label = QLabel('Cycles: ')
        self.repeat_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.repeatSpinBox = QSpinBox()
        self.repeatSpinBox.setValue(1)
        self.repeatSpinBox.setMinimum(1)
        self.repeatSpinBox.setSingleStep(1)
        self.repeatSpinBox.setDisabled(True)
        # Offsets table
        self.offsets_box = QGroupBox("Tool Offsets")
        self.offsets_box.setMaximumWidth(170)
        self.offsets_table = QTableWidget()
        self.offsets_table.setColumnCount(2)
        self.offsets_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.offsets_table.setColumnWidth(0,50)
        self.offsets_table.setColumnWidth(1,50)
        self.offsets_table.setHorizontalHeaderItem(0, QTableWidgetItem("X"))
        self.offsets_table.setHorizontalHeaderItem(1, QTableWidgetItem("Y"))
        self.offsets_table.resizeRowsToContents()
        vbox = QVBoxLayout()
        self.offsets_box.setLayout(vbox)
        vbox.addWidget(self.offsets_table)
        self.offsets_box.setVisible(False)
        # Tool buttons table
        self.toolBoxLayout = QHBoxLayout()
        self.toolBoxLayout.setSpacing(1)
        self.toolBox = QGroupBox()
        self.toolBoxLayout.setContentsMargins(0,0,0,0)
        self.toolBox.setLayout(self.toolBoxLayout)
        self.toolBox.setVisible(False)
        self.toolButtons = []

        # Xray checkbox
        self.xray_box = QCheckBox('X-ray')
        self.xray_box.setChecked(False)
        self.xray_box.stateChanged.connect(self.toggle_xray)
        self.xray_box.setDisabled(True)
        # Loose checkbox
        self.loose_box = QCheckBox('Loose detection')
        self.loose_box.setChecked(False)
        self.loose_box.stateChanged.connect(self.toggle_loose)
        self.loose_box.setDisabled(True)

        # HBHBHB: test checkbox
        self.detect_box = QCheckBox('Detection')
        self.detect_box.setChecked(False)
        self.detect_box.stateChanged.connect(self.toggle_detect)

        # create a grid box layout
        grid = QGridLayout()
        grid.setSpacing(3)

        # add elements to grid
        # FIRST ROW
        grid.addWidget(self.connection_button,1,1,Qt.AlignLeft)
        grid.addWidget(self.xray_box,1,2)
        grid.addWidget(self.loose_box,1,3)
        
        #HBHBHB
        grid.addWidget(self.detect_box,1,4)
        #grid.addWidget(self.toolBox,1,4)

        grid.addWidget(self.disconnection_button,1,5,1,-1,Qt.AlignLeft)
        # SECOND ROW
        
        # THIRD ROW
        # main image viewer
        grid.addWidget(self.image_label,3,1,4,4)
        grid.addWidget(self.jogpanel_button,3,5,1,1)
        grid.addWidget(self.offsets_box,4,5,1,1)
        if self.small_display:
            grid.addWidget(self.exit_button,5,5,1,1)
        grid.addWidget(self.debug_button,6,5,1,1)
        # FOURTH ROW
        grid.addWidget(self.cp_button,7,1,1,1)
        grid.addWidget(self.calibration_button,7,2,1,1)
        grid.addWidget(self.repeat_label,7,3,1,1)
        grid.addWidget(self.repeatSpinBox,7,4,1,1)

        
        # set the grid layout as the widgets layout
        self.centralWidget.setLayout(grid)

        # start video feed
        self.startVideo()
        # flag to draw circle
        self.crosshair = False
        # object to hold final offsets
        self.calibration_results = []

    def toggle_detect(self):
        if self.detect_box.isChecked():
            self.video_thread.display_crosshair = True
            self.video_thread.alignment = False
            self.video_thread.detection_on = True
        else: 
            self.video_thread.display_crosshair = False
            self.video_thread.alignment = False
            self.video_thread.detection_on = False

    def loadUserParameters(self):
        global camera_width, camera_height, video_src
        try:
            with open('settings.json','r') as inputfile:
                options = json.load(inputfile)
            camera_settings = options['camera'][0]
            camera_height = int( camera_settings['display_height'] )
            camera_width = int( camera_settings['display_width'] )
            video_src = camera_settings['video_src']
            if len(str(video_src)) == 1: video_src = int(video_src)
            printer_settings = options['printer'][0]
            self.printerURL = printer_settings['address']
        except FileNotFoundError:
            # create parameter file with standard parameters
            options = {}
            options['camera'] = []
            options['camera'].append( {
                'video_src': 0,
                'display_width': '640',
                'display_height': '480'
            } )
            options['printer'] = []
            options['printer'].append( {
                'address': 'http://localhost',
                'name': 'Hermoine'
            } )
            try:
                camera_width = 640
                camera_height = 480
                video_src = 1
                with open('settings.json','w') as outputfile:
                    json.dump(options, outputfile)
            except Exception as e1:
                print('Error writing user settings file.')
                print(e1)

    def _createMenuBar(self):
        menuBar = self.menuBar()
        # Creating menus using a QMenu object
        fileMenu = QMenu('&File', self)
        menuBar.addMenu(fileMenu)
        fileMenu.addAction(self.debugAction)
        fileMenu.addAction(self.cameraAction)

    def _createActions(self):
        # Creating action using the first constructor
        self.debugAction = QAction(self)
        self.debugAction.setText('&Debug info')
        self.cameraAction = QAction(self)
        self.cameraAction.setText('&Camera settings')

    def _connectActions(self):
        # Connect File actions
        self.debugAction.triggered.connect(self.displayDebug)
        self.cameraAction.triggered.connect(self.displayCameraSettings)

    def displayCameraSettings(self):
        self.camera_dialog = CameraSettingsDialog(parent=self)
        if self.camera_dialog.exec_():
            self.updateStatusbar('Camera settings saved.')
            # HBHBHB: call save settings
        else: self.updateStatusbar('Camera settings discarded.')

    def displayDebug(self):
        dbg = DebugDialog(parent=self,message=self.debugString)
        if dbg.exec_():
            None

    def displayJogPanel(self):
        try:
            local_status = self.printer.getStatus()
            if local_status == 'idle':
                jogPanel = CPDialog(parent=self,summary='Control printer movement using this panel.',title='Jog Control')
                if jogPanel.exec_():
                    None
        except Exception as e1: self.statusBar.showMessage('Printer is not available or is busy. ')

    def startVideo(self):
        # create the video capture thread
        self.video_thread = CalibrateNozzles(parent=self,numTools=0, cycles=1,minArea=600, align=False)
        # connect its signal to the update_image slot
        # connect its signal to the update_image slot
        self.video_thread.detection_error.connect(self.updateStatusbar)
        self.video_thread.status_update.connect(self.updateStatusbar)
        self.video_thread.message_update.connect(self.updateMessagebar)
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.calibration_complete.connect(self.applyCalibration)

        # start the thread
        self.video_thread.start()

    def stopVideo(self):
        try:
            if self.video_thread.isRunning():
                self.video_thread.stop()
        except Exception as vs2:
            self.updateStatusbar('ERROR: cannot stop video')
            print('ERROR: cannot stop video')
            print(vs2)

    def closeEvent(self, event):
        try:
            self.video_thread.stop()
        except Exception as close1:
            print('ERROR ending video thread: ')
            print(close1)
        event.accept()

    def connectToPrinter(self):
        # temporarily suspend GUI and display status message
        self.image_label.setText('Waiting to connect..')
        self.updateStatusbar('Please enter machine IP address or name prefixed with http(s)://')
        self.connection_button.setDisabled(True)
        self.disconnection_button.setDisabled(True)
        self.calibration_button.setDisabled(True)
        self.cp_button.setDisabled(True)
        self.jogpanel_button.setDisabled(True)
        self.offsets_box.setVisible(False)
        self.connection_status.setText('Connecting..')
        self.connection_status.setStyleSheet(style_orange)
        self.cp_label.setText('<b>CP:</b> <i>undef</i>')
        self.cp_label.setStyleSheet(style_orange)
        self.repeatSpinBox.setDisabled(True)
        self.xray_box.setDisabled(True)
        self.xray_box.setChecked(False)
        self.loose_box.setDisabled(True)
        self.repaint()
        try:
            # check if printerURL has already been defined (user reconnecting)
            if len(self.printerURL) > 0:
                None
        except Exception:
            # printerURL initalization to defaults
            self.printerURL = 'http://localhost'
        # Prompt user for machine connection address
        text, ok = QInputDialog.getText(self, 'Machine URL','Machine IP address or hostname: ', QLineEdit.Normal, self.printerURL)
        # Handle clicking OK/Connect
        if ok and text != '' and len(text) > 5:
            self.printerURL = text
        # Handle clicking cancel
        elif not ok:
            self.updateStatusbar('Connection request cancelled.')
            self.resetConnectInterface()
            return
        # Handle invalid input
        elif len(text) < 6 or text[:4] not in ['http']:
            self.updateStatusbar('Invalid IP address or hostname: \"' + text +'\". Add http(s):// to try again.')
            self.resetConnectInterface()
            return
        # Update user with new state
        self.statusBar.showMessage('Attempting to connect to: ' + self.printerURL )
        # Attempt connecting to the Duet controller
        try:
            self.printer = DWA.DuetWebAPI(self.printerURL)
            if not self.printer.printerType():
                # connection failed for some reason
                self.updateStatusbar('Device at '+self.printerURL+' either did not respond or is not a Duet V2 or V3 printer.')
                self.resetConnectInterface()
                return
            else:
                # connection succeeded, update objects accordingly
                self._connected_flag = True
                self.num_tools = self.printer.getNumTools()
                self.video_thread.numTools = self.num_tools
                # UPDATE OFFSET INFORMATION
                self.offsets_box.setVisible(True)
                self.offsets_table.setRowCount(self.num_tools)
                for i in range(self.num_tools):
                    current_tool = self.printer.getG10ToolOffset(i)
                    x_tableitem = QTableWidgetItem(str(current_tool['X']))
                    y_tableitem = QTableWidgetItem(str(current_tool['Y']))
                    self.offsets_table.setVerticalHeaderItem(i,QTableWidgetItem('T'+str(i)))
                    self.offsets_table.setItem(i,0,x_tableitem)
                    self.offsets_table.setItem(i,1,y_tableitem)
                    # add tool buttons
                    toolButton = QPushButton('T'+str(i))
                    toolButton.setToolTip('Fetch T' + str(i) + ' to current machine position.')
                    self.toolButtons.append(toolButton)
        except Exception as conn1:
            self.updateStatusbar('Cannot connect to: ' + self.printerURL )
            print('Duet Connection exception: ', conn1)
            self.resetConnectInterface()
            return

        # Get active tool
        _active = self.printer.getCurrentTool()
        # Display toolbox
        for i,button in enumerate(self.toolButtons):
            button.setCheckable(True)
            if int(_active) == i:
                button.setChecked(True)
            else: 
                button.setChecked(False)
            button.clicked.connect(self.callTool)
            self.toolBoxLayout.addWidget(button)
        self.toolBox.setVisible(True)
        # Connection succeeded, update GUI first
        self.updateStatusbar('Connected to a Duet V'+str(self.printer.printerType()))
        self.connection_button.setText('Online: ' + self.printerURL[self.printerURL.rfind('/')+1:])
        self.statusBar.showMessage('Connected to printer at ' + self.printerURL, 5000)
        self.connection_status.setText('Connected.')
        self.image_label.setText('Set your Controlled Point to continue.')
        # enable/disable buttons
        self.connection_button.setDisabled(True)
        self.calibration_button.setDisabled(True)
        self.disconnection_button.setDisabled(False)
        self.cp_button.setDisabled(False)
        self.jogpanel_button.setDisabled(False)
        # update connection status indicator to green
        self.connection_status.setStyleSheet(style_green)
        self.cp_label.setStyleSheet(style_red)

    def callTool(self):
        # get current active tool
        _active = self.printer.getCurrentTool()
        
        # get requested tool number
        sender = self.sender()

        # update buttons to new status
        for button in self.toolButtons:
            button.setChecked(False)
        self.toolButtons[int(self.sender().text()[1:])].setChecked(True)

        # handle tool already active on printer
        if int(_active) == int(sender.text()[1:]):
            msg = QMessageBox()
            status = msg.question( self, 'Unload ' + sender.text(), 'Unload ' + sender.text() + ' and return carriage to the current position?',QMessageBox.Yes | QMessageBox.No  )
            if status == QMessageBox.Yes:
                self.toolButtons[int(self.sender().text()[1:])].setChecked(False)
                if len(self.cp_coords) > 0:
                    self.printer.gCode('T-1')
                    self.printer.gCode('G1 X' + str(self.cp_coords['X']))
                    self.printer.gCode('G1 Y' + str(self.cp_coords['Y']))
                else:
                    tempCoords = self.printer.getCoords()
                    self.printer.gCode('T-1')
                    self.printer.gCode('G1 X' + str(tempCoords['X']))
                    self.printer.gCode('G1 Y' + str(tempCoords['Y']))
                # End video threads and restart default thread
                self.video_thread.alignment = False
                self.video_thread.display_crosshair = False
                self.video_thread.detection_on = False

                # Update GUI
                self.xray_box.setDisabled(True)
                self.xray_box.setChecked(False)
                self.loose_box.setDisabled(True)
                self.loose_box.setChecked(False)
                self.calibration_button.setDisabled(False)
                self.cp_button.setDisabled(False)
                self.updateMessagebar('Ready.')
                self.updateStatusbar('Ready.')
            else:
                # User cancelled, do nothing
                return
        else:
            # Requested tool is different from active tool
            msg = QMessageBox()
            status = msg.question( self, 'Confirm loading ' + sender.text(), 'Load ' + sender.text() + ' and move to current position?',QMessageBox.Yes | QMessageBox.No  )
            
            if status == QMessageBox.Yes:
                # return carriage to controlled point position
                if len(self.cp_coords) > 0:
                    self.printer.gCode('T-1')
                    self.printer.gCode(sender.text())
                    self.printer.gCode('G1 X' + str(self.cp_coords['X']))
                    self.printer.gCode('G1 Y' + str(self.cp_coords['Y']))
                else:
                    tempCoords = self.printer.getCoords()
                    self.printer.gCode('T-1')
                    self.printer.gCode(self.sender().text())
                    self.printer.gCode('G1 X' + str(tempCoords['X']))
                    self.printer.gCode('G1 Y' + str(tempCoords['Y']))
                # START DETECTION THREAD HANDLING
                # close camera settings dialog so it doesn't crash
                try:
                    if self.camera_dialog.isVisible():
                        self.camera_dialog.reject()
                except: None
                # update GUI
                self.cp_button.setDisabled(True)
                self.jogpanel_button.setDisabled(False)
                self.calibration_button.setDisabled(True)
                self.xray_box.setDisabled(False)
                self.xray_box.setChecked(False)
                self.loose_box.setDisabled(False)
                self.repeatSpinBox.setDisabled(True)

                # enable detection without calibration
                self.video_thread.alignment = False
                self.video_thread.display_crosshair = True
                self.video_thread.detection_on = True
                self.detect_box.setChecked(True)
            else:
                self.toolButtons[int(self.sender().text()[1:])].setChecked(False)

    def resetConnectInterface(self):
        self.connection_button.setDisabled(False)
        self.disconnection_button.setDisabled(True)
        self.calibration_button.setDisabled(True)
        self.cp_button.setDisabled(True)
        self.jogpanel_button.setDisabled(True)
        self.offsets_box.setVisible(False)
        self.connection_status.setText('Disconnected')
        self.connection_status.setStyleSheet(style_red)
        self.cp_label.setText('<b>CP:</b> <i>undef</i>')
        self.cp_label.setStyleSheet(style_red)
        self.repeatSpinBox.setDisabled(True)
        self.xray_box.setDisabled(True)
        self.xray_box.setChecked(False)
        self.loose_box.setDisabled(True)
        index = self.toolBoxLayout.count()-1
        while index >= 0:
            curWidget = self.toolBoxLayout.itemAt(index).widget()
            curWidget.setParent(None)
            index -= 1
        self.toolBox.setVisible(False)
        self.toolButtons = []
        self.repaint()

    def controlledPoint(self):
        # display crosshair on video feed at center of image
        self.crosshair = True
        self.calibration_button.setDisabled(True)

        if len(self.cp_coords) > 0:
            self.printer.gCode('T-1')
            self.printer.gCode('G90 G1 X'+ str(self.cp_coords['X']) + ' Y' + str(self.cp_coords['Y']) )
        dlg = CPDialog(parent=self)
        if dlg.exec_():
            self.cp_coords = self.printer.getCoords()
            self.cp_string = '(' + str(self.cp_coords['X']) + ', ' + str(self.cp_coords['Y']) + ')'
            self.readyToCalibrate()
        else:
            self.statusBar.showMessage('CP Setup cancelled.')
        self.crosshair = False

    def readyToCalibrate(self):
        self.statusBar.showMessage('Controlled Point coordinates saved.',3000)
        self.image_label.setText('Controlled Point set. Click \"Start Tool Alignment\" to calibrate..')
        self.cp_button.setText('Reset CP ')
        self.cp_label.setText('<b>CP:</b> ' + self.cp_string)
        self.cp_label.setStyleSheet(style_green)
        self.xray_box.setDisabled(True)
        self.xray_box.setChecked(False)
        self.loose_box.setDisabled(True)
        self.calibration_button.setDisabled(False)
        #self.repeatSpinBox.setDisabled(False)

    def applyCalibration(self):
        # update GUI
        self.readyToCalibrate()
        # close camera settings dialog so it doesn't crash
        try:
            if self.camera_dialog.isVisible():
                self.camera_dialog.reject()
        except: None
        # prompt for user to apply results
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText('Do you want to apply the new offsets to your machine?')
        msgBox.setWindowTitle('Calibration Results')
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            for tool_result in self.calibration_results:
                self.printer.gCode(tool_result)
                self.printer.gCode('M500') # because of Rene.
            self.statusBar.showMessage('New offsets applied to machine.')
        else:
            self.statusBar.showMessage('Calibration results are displayed in Debug window.')
        # Clean up threads and detection
        self.video_thread.alignment = False
        self.video_thread.detect_on = False
        self.video_thread.display_crosshair = False

    def disconnectFromPrinter(self):
        # temporarily suspend GUI and display status message
        self.image_label.setText('Restoring machine to initial state..')
        self.updateStatusbar('Restoring machine and disconnecting...')
        self.connection_button.setText('Pending..')
        self.connection_button.setDisabled(True)
        self.disconnection_button.setDisabled(True)
        self.calibration_button.setDisabled(True)
        self.cp_button.setDisabled(True)
        self.cp_button.setText('Pending..')
        self.jogpanel_button.setDisabled(True)
        self.offsets_box.setVisible(False)
        self.connection_status.setText('Disconnecting..')
        self.connection_status.setStyleSheet(style_orange)
        self.cp_label.setText('<b>CP:</b> <i>undef</i>')
        self.cp_label.setStyleSheet(style_orange)
        self.repeatSpinBox.setDisabled(True)
        self.xray_box.setDisabled(True)
        self.xray_box.setChecked(False)
        self.loose_box.setDisabled(True)
        self.toolBox.setVisible(False)
        self.repaint()
        # End video threads and restart default thread
        # Clean up threads and detection
        self.video_thread.alignment = False
        self.video_thread.detect_on = False
        self.video_thread.display_crosshair = False
        self.detect_box.setChecked(False)

        # update status 
        self.updateStatusbar('Unloading tools and disconnecting from machine..')
        # Wait for printer to stop moving and unload tools
        _ret_error = self.printer.gCode('M400')
        tempCoords = self.printer.getCoords()
        _ret_error += self.printer.gCode('T-1')
        # return carriage to controlled point position
        if len(self.cp_coords) > 0:
            _ret_error += self.printer.gCode('G1 X' + str(self.cp_coords['X']))
            _ret_error += self.printer.gCode('G1 Y' + str(self.cp_coords['Y']))
        else:
            _ret_error += self.printer.gCode('G1 X' + str(tempCoords['X']))
            _ret_error += self.printer.gCode('G1 Y' + str(tempCoords['Y']))
        # update status with disconnection state
        if _ret_error == 0:
            self.updateStatusbar('Disconnected.')
            self.image_label.setText('Disconnected.')
        else: 
            # handle unforeseen disconnection error (power loss?)
            self.statusBar.showMessage('Disconnect: error communicating with machine.')
            self.statusBar.setStyleSheet(style_red)
        # Reinitialize printer object
        self.printer = None
        
        # Tools unloaded, reset GUI
        self.image_label.setText('Welcome to TAMV. Enter your printer address and click \"Connect..\" to start.')
        self.connection_button.setText('Connect..')
        self.connection_button.setDisabled(False)
        self.disconnection_button.setDisabled(True)
        self.calibration_button.setDisabled(True)
        self.cp_button.setDisabled(True)
        self.cp_button.setText('Set Controlled Point..')
        self.jogpanel_button.setDisabled(True)
        self.offsets_box.setVisible(False)
        self.connection_status.setText('Disconnected.')
        self.connection_status.setStyleSheet(style_red)
        self.cp_label.setText('<b>CP:</b> <i>undef</i>')
        self.cp_label.setStyleSheet(style_red)
        self.repeatSpinBox.setDisabled(True)
        self.xray_box.setDisabled(True)
        self.loose_box.setDisabled(True)
        self.resetConnectInterface()

    def runCalibration(self):
        # close camera settings dialog so it doesn't crash
        try:
            if self.camera_dialog.isVisible():
                self.camera_dialog.reject()
        except: None
        # stop video thread
        self.stopVideo()
        # update GUI
        self.cp_button.setDisabled(True)
        self.jogpanel_button.setDisabled(False)
        self.calibration_button.setDisabled(True)
        self.xray_box.setDisabled(False)
        self.xray_box.setChecked(False)
        self.loose_box.setDisabled(False)
        self.toolBox.setVisible(False)
        # get number of repeat cycles
        self.cycles = self.repeatSpinBox.value()
        self.repeatSpinBox.setDisabled(True)

        # create the Nozzle detection capture thread
        self.video_thread.display_crosshair = True
        self.video_thread.detection_on = True
        self.video_thread.alignment = True

    def toggle_xray(self):
        try:
            self.video_thread.toggleXray()
        except Exception as e1:
            self.updateStatusbar('Detection thread not running.')
            print( 'Detection thread error in XRAY: ')
            print(e1)

    def toggle_loose(self):
        try:
            self.video_thread.toggleLoose()
        except Exception as e1:
            self.updateStatusbar('Detection thread not running.')
            print( 'Detection thread error in LOOSE: ')
            print(e1)

    @pyqtSlot(str)
    def updateStatusbar(self, statusCode ):
        self.statusBar.showMessage(statusCode)

    @pyqtSlot(str)
    def updateMessagebar(self, statusCode ):
        self.image_label.setText(statusCode)

    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        self.mutex.lock()
        self.current_frame = cv_img
        if self.crosshair:
            # Draw alignment circle on image
            cv_img = cv2.circle( 
                cv_img, 
                ( int(camera_width/2), int(camera_height/2) ), 
                int( camera_width/6 ), 
                (0,255,0), 
                2
            )
            cv_img = cv2.circle( 
                cv_img, 
                ( int(camera_width/2), int(camera_height/2) ), 
                5, 
                (0,0,255), 
                2
            )
        # Updates the image_label with a new opencv image
        qt_img = self.convert_cv_qt(cv_img)
        self.image_label.setPixmap(qt_img)
        self.mutex.unlock()

    def convert_cv_qt(self, cv_img):
        # Convert from an opencv image to QPixmap
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(display_width, display_height, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)

if __name__=='__main__':
    os.putenv("QT_LOGGING_RULES","qt5ct.debug=false")
    app = QApplication(sys.argv)
    a = App()
    a.show()
    sys.exit(app.exec_())
