#!/usr/bin/env python3

import argparse, logging, os, sys, traceback, time
from tkinter import E
from json import tool
from logging.handlers import RotatingFileHandler
# openCV imports
from cv2 import cvtColor, COLOR_BGR2RGB
# Qt imports
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QSize, QThread, QMutex
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QMainWindow, QDesktopWidget, QStyle, QWidget, QMenu, QAction, QStatusBar, QLabel, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QApplication, QTabWidget, QButtonGroup, QGridLayout, QFrame, QCheckBox
# Other imports
import json
import numpy as np
import copy
# Custom modules import
from modules.DetectionManager import DetectionManager
from modules.SettingsDialog import SettingsDialog
from modules.PrinterManager import PrinterManager
from modules.StatusTipFilter import StatusTipFilter

########################################################################### Core application class
class App(QMainWindow):
    # "Global" mutex
    __mutex = QMutex()
    # Signals
    ######## Detection Manager
    startVideoSignal = pyqtSignal()
    setImagePropertiesSignal = pyqtSignal(object)
    getVideoFrameSignal = pyqtSignal()
    # Endstop detection signals
    toggleEndstopDetectionSignal = pyqtSignal(bool)
    toggleEndstopAutoDetectionSignal = pyqtSignal(bool)
    # Nozzle detection signals
    toggleNozzleDetectionSignal = pyqtSignal(bool)
    toggleNozzleAutoDetectionSignal = pyqtSignal(bool)
    # UV coordinates update signal
    getUVCoordinatesSignal = pyqtSignal()
    # Master detection enable/disable signal
    toggleDetectionSignal = pyqtSignal(bool)

    ######## Printer Manager
    connectSignal = pyqtSignal(object)
    disconnectSignal = pyqtSignal(object)
    moveRelativeSignal = pyqtSignal(object)
    moveAbsoluteSignal = pyqtSignal(object)
    callToolSignal = pyqtSignal(int)
    unloadToolSignal = pyqtSignal()
    pollCoordinatesSignal = pyqtSignal()
    pollCurrentToolSignal = pyqtSignal()
    setOffsetsSignal = pyqtSignal(object)
    limitAxesSignal = pyqtSignal()
    flushBufferSignal = pyqtSignal()
    saveToFirmwareSignal = pyqtSignal()
    # Settings Dialog
    resetImageSignal = pyqtSignal()
    pushbuttonSize = 38
    # default move speed in feedrate/min
    _moveSpeed = 6000
    __counter = 0
    
    ########################################################################### Initialize class
    def __init__(self, parent=None):
        # send calling to log
        _logger.debug('*** calling App.__init__')
        
        # output greeting to log
        _logger.info('Initializing application.. ')
        # call QMainWindow init function
        super().__init__()
        #### class attributes definition
        if(True):
            # main window size
            self.windowWidthOriginal, self.windowHeightOriginal = 800, 600
            # main camera capture size
            # self.imageWidthOriginal, self.imageHeightOriginal = 640, 480
            # stylesheets used for interface status updates
            self.styleGreen = '* { background-color: green; color: white;} QToolTip { color: black; background-color: #DDDDDD } *:hover{background-color: #003874; color: #ffa000;} *:pressed{background-color: #ffa000; color: #003874;}'
            self.styleRed = '* { background-color: red; color: white;} QToolTip { color: black; background-color: #DDDDDD }'
            self.styleDisabled = '* { background-color: #cccccc; color: #999999; border-style: solid;} QToolTip { color: black; background-color: #DDDDDD }'
            self.styleOrange = '* { background-color: dark-grey; color: #ffa000;} QToolTip { color: black; background-color: #DDDDDD }'
            self.styleBlue = '* { background-color: #003874; color: #ffa000;} QToolTip { color: black; background-color: #DDDDDD }'
            self.styleDefault = '* { background-color: rgba(0,0,0,0); color: black;} QToolTip { color: black; background-color: #DDDDDD }'
            # standby image placeholder
            self.standbyImage = QPixmap('./resources/background.png')
            self.errorImage = QPixmap('./resources/error.png')
            # user-defined cameras array
            self.__cameras = []
            # active camera
            self.__activeCamera ={}
            # user-defined printers array
            self.__printers = []
            # active printer
            self.__activePrinter = {}
            # Control Point
            self.__cpCoordinates = {'X': None, 'Y': None, 'Z': None}
            self.__currentPosition = {'X': None, 'Y': None, 'Z': None}
            self.__stateManualCPCapture = False
            self.__stateAutoCPCapture = False
            self.__stateEndstopAutoCalibrate = False
            self.__restorePosition = None
            self.__firstConnection = False
            self.state = 0
            # Camera transform matrix
            self.transformMatrix = None
            self.transform_input = None
            self.mpp = None
            # Nozzle detection
            self.__stateAutoNozzleAlignment = False
            self.__stateManualNozzleAlignment = False
            self.__displayCrosshair = False
        
        ####  setup window properties
        if(True):
            _logger.debug('  .. setting up window properties..')
            self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
            self.setWindowTitle('TAMV')
            self.setWindowIcon(QIcon('./resources/jubilee.png'))
            screen = QDesktopWidget().availableGeometry()
            self.setGeometry(QStyle.alignedRect(Qt.LeftToRight,Qt.AlignHCenter,QSize(self.windowWidthOriginal,self.windowHeightOriginal),screen))
            self.setMinimumWidth(self.windowWidthOriginal)
            self.setMinimumHeight(self.windowHeightOriginal)
            appScreen = self.frameGeometry()
            appScreen.moveCenter(screen.center())
            self.move(appScreen.topLeft())
            self.centralWidget = QWidget()
            self.setCentralWidget(self.centralWidget)
            #  create stylehseets
            self.setStyleSheet(
                '\
                QLabel#instructions_text {\
                    background-color: rgba(255,153,0,.4);\
                }\
                QPushButton {\
                    border: 1px solid #adadad;\
                    border-style: outset;\
                    border-radius: 4px;\
                    font: 16px;\
                    padding: 2px;\
                }\
                QPushButton>QToolTip {\
                    color: black;\
                }\
                QPushButton#calibrating:enabled {\
                    background-color: orange;\
                    color: white;\
                }\
                QPushButton#completed:enabled {\
                    background-color: blue;\
                    color: white;\
                }\
                QPushButton:hover,QPushButton:enabled:hover,QPushButton:enabled:!checked:hover,QPushButton#completed:enabled:hover {\
                    background-color: #003874;\
                    color: #ffa000;\
                    border: 1px solid #aaaaaa;\
                }\
                QPushButton:pressed,QPushButton:enabled:pressed,QPushButton:enabled:checked,QPushButton#completed:enabled:pressed {\
                    background-color: #ffa000;\
                    border: 1px solid #aaaaaa;\
                }\
                QPushButton:enabled {\
                    background-color: green;\
                    color: white;\
                }\
                QLabel#labelPlus {\
                    font: 20px;\
                    padding: 0px;\
                }\
                QPushButton#plus:enabled {\
                    font: 20px;\
                    padding: 0px;\
                    background-color: #eeeeee;\
                    color: #000000;\
                }\
                QPushButton#plus:enabled:hover {\
                    font: 20px;\
                    padding: 0px;\
                    background-color: green;\
                    color: #000000;\
                }\
                QPushButton#plus:enabled:pressed {\
                    font: 20px;\
                    padding: 0px;\
                    background-color: #FF0000;\
                    color: #222222;\
                }\
                QPushButton#debug,QMessageBox > #debug {\
                    background-color: blue;\
                    color: white;\
                }\
                QPushButton#debug:hover, QMessageBox > QAbstractButton#debug:hover {\
                    background-color: green;\
                    color: white;\
                }\
                QPushButton#debug:pressed, QMessageBox > QAbstractButton#debug:pressed {\
                    background-color: #ffa000;\
                    border-style: inset;\
                    color: white;\
                }\
                QPushButton#active, QMessageBox > QAbstractButton#active {\
                    background-color: green;\
                    color: white;\
                }\
                QPushButton#active:pressed,QMessageBox > QAbstractButton#active:pressed {\
                    background-color: #ffa000;\
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
                    background-color: #ffa000;\
                    border: 1px solid #aaaaaa;\
                }\
                QInputDialog QDialogButtonBox > QPushButton:pressed, QDialog QPushButton:pressed {\
                    background-color: #ffa000;\
                }\
                QInputDialog QDialogButtonBox > QPushButton:hover:!pressed, QDialog QPushButton:hover:!pressed {\
                    background-color: #003874;\
                    color: #ffa000;\
                }\
            QToolTip, QLabel > QToolTip, QPushButton > QLabel> QToolTip {\
                    color: black;\
                }\
                '
          )
        #### Driver API imports
        if(True):
            try:
                self.__firmwareList = []
                self.__driverList = []
                with open('drivers.json','r') as inputfile:
                    driverJSON = json.load(inputfile)
                _logger.info('  .. loading drivers..')
                for driverEntry in driverJSON:
                    self.__firmwareList.append(driverEntry['firmware'])
                    self.__driverList.append(driverEntry['filename'])            
            except:
                _logger.critical('Cannot load driver definitions: ' + traceback.format_exc())
                raise SystemExit('Cannot load driver definitions.')
        #### Setup components
        #  load user parameters
        if(True):
            try:
                with open('./config/settings.json','r') as inputfile:
                    self.__userSettings = json.load(inputfile)
            except FileNotFoundError:
                try:
                    # try and see if moving from older build
                    with open('./settings.json','r') as inputfile:
                        self.__userSettings = json.load(inputfile)
                    try:
                        _logger.info('  .. moving settings file to /config/settings.json.. ')
                        # create config folder if it doesn't exist
                        os.makedirs('./config',exist_ok=True)
                        # move settings.json to new config folder
                        os.replace('./settings.json','./config/settings.json')
                    except:
                        _logger.warning('Cannot rename old settings.json, leaving in place and using new file.')
                except FileNotFoundError:
                    # create config folder if it doesn't exist
                    os.makedirs('./config',exist_ok=True)
                    # No settings file defined, create a default file
                    _logger.info('  .. creating new settings.json..')
                    # create a camera array
                    self.__userSettings['camera'] = [
                        {
                            'video_src': 0,
                            'display_width': '640',
                            'display_height': '480',
                            'default': 1
                        } ]
                    # Create a printer array
                    self.__userSettings['printer'] = [
                        { 
                        'address': 'http://localhost',
                        'password': 'reprap',
                        'name': 'My Duet',
                        'nickname': 'Default',
                        'controller' : 'RRF/Duet', 
                        'version': '',
                        'default': 1,
                        'rotated': 0,
                        'tools': [
                            { 
                                'number': 0, 
                                'name': 'Tool 0', 
                                'nozzleSize': 0.4, 
                                'offsets': [0,0,0] 
                            } ]
                        } ]
                    try:
                        # set class attributes
                        self._cameraWidth = int(self.__userSettings['camera'][0]['display_width'])
                        self._cameraHeight = int(self.__userSettings['camera'][0]['display_height'])
                        self._videoSrc = self.__userSettings['camera'][0]['video_src']
                        # save default settings file
                        with open('./config/settings.json','w') as outputfile:
                            json.dump(self.__userSettings, outputfile)
                    except Exception as e1:
                        errorMsg = 'Error reading user settings file.' + traceback.format_exc()
                        _logger.critical(errorMsg)
                        raise SystemExit(errorMsg)
            _logger.info('  .. reading configuration settings..')
        # Fetch defined cameras
        if(True):
            defaultCameraDefined = False
            for source in self.__userSettings['camera']:
                try:
                    self.__cameras.append(source)
                    if(source['default'] == 1 and defaultCameraDefined is False):
                        self.__activeCamera = source
                        defaultCameraDefined = True
                    elif(defaultCameraDefined):
                        source['default'] = 0
                    continue
                except KeyError as ke:
                    source['default'] = 0
                    continue
            if(defaultCameraDefined is False):
                self.__userSettings['camera'][0]['default'] = 1
                self.__activeCamera = self.__userSettings['camera'][0]
            self._cameraHeight = int(self.__activeCamera['display_height'])
            self._cameraWidth = int(self.__activeCamera['display_width'])
            self._videoSrc = self.__activeCamera['video_src']
            if(len(str(self._videoSrc)) == 1 or str(self._videoSrc) == "-1"): 
                self._videoSrc = int(self._videoSrc)
        # Fetch defined machines
        if(True):
            defaultPrinterDefined = False
            for machine in self.__userSettings['printer']:
                # Find default printer first
                try:
                    self.__printers.append(machine)
                    if(machine['default'] == 1):
                        self.__activePrinter = machine
                        defaultPrinterDefined = True
                except KeyError as ke:
                    # no default field detected - create a default if not already done
                    if(defaultPrinterDefined is False):
                        machine['default'] = 1
                        defaultPrinterDefined = True
                    else:
                        machine['default'] = 0
                # Check if password doesn't exist
                try:
                    temp = machine['password']
                except KeyError:
                    machine['password'] = 'reprap'
                # Check if nickname doesn't exist
                try:
                    temp = machine['nickname']
                except KeyError:
                    machine['nickname'] = machine['name']
                # Check if controller doesn't exist
                try:
                    temp = machine['controller']
                except KeyError:
                    machine['controller'] = 'RRF/Duet'
                # Check if version doesn't exist
                try:
                    temp = machine['version']
                except KeyError:
                    machine['version'] = ''
                # Check if rotated kinematics doesn't exist
                try:
                    temp = machine['rotated']
                except KeyError:
                    machine['rotated'] = 0
                # Check if tools doesn't exist
                try:
                    temp = machine['tools']
                except KeyError:
                    machine['tools'] = [ { 'number': 0, 'name': 'Tool 0', 'nozzleSize': 0.4, 'offsets': [0,0,0] } ]
            # Check if we have no default machine
            if(defaultPrinterDefined is False):
                self.__activePrinter = self.__userSettings['printer'][0]
            (_errCode, _errMsg, self.printerURL) = self.sanitizeURL(self.__activePrinter['address'])
            if _errCode > 0:
                # invalid input
                _logger.error('Invalid printer URL detected in settings.json')
                _logger.info('Defaulting to \"http://localhost\"...')
                self.printerURL = 'http://localhost'
        
        ##### Settings Dialog
        self.__settingsGeometry = None
        # Note: settings dialog is created when user clicks the button

        #### Setup interface
        ##### Menu bar
        self.setupMenu()
        ##### Status bar
        self.setupStatusbar()
        ##### GUI elements
        self.setupMainWindow()

        # send exiting to log
        _logger.debug('*** exiting App.__init__')
    
    ########################################################################### Menu setup
    def setupMenu(self):
        # send calling to log
        _logger.debug('*** calling App.setupMenu')

        self.menubar = self.menuBar()
        self.menubar.installEventFilter(StatusTipFilter(self))
        #### File menu
        fileMenu = QMenu('&File', self)
        self.menubar.addMenu(fileMenu)
        #### Preferences
        self.preferencesAction = QAction(self)
        self.preferencesAction.setText('&Preferences..')
        self.preferencesAction.triggered.connect(self.displayPreferences)
        fileMenu.addAction(self.preferencesAction)
        # Quit
        self.quitAction = QAction(self)
        self.quitAction.setText('&Quit')
        self.quitAction.triggered.connect(self.close)
        fileMenu.addSeparator()
        fileMenu.addAction(self.quitAction)

        # send exiting to log
        _logger.debug('*** exiting App.setupMenu')
    
    ########################################################################### Status bar setup
    def setupStatusbar(self):
        # send calling to log
        _logger.debug('*** calling App.setupStatusbar')

        self.statusBar = QStatusBar()
        self.statusBar.showMessage('Welcome.')
        self.setStatusBar(self.statusBar)
        #### CP coodinate status
        self.cpLabel = QLabel('<b>CP:</b> <i>undef</i>')
        self.statusBar.addPermanentWidget(self.cpLabel)
        self.cpLabel.setStyleSheet(self.styleOrange)

        #### Connection status
        self.connectionStatusLabel = QLabel('<i>Disconnected</i>')
        self.connectionStatusLabel.setStyleSheet(self.styleOrange)
        self.statusBar.addPermanentWidget(self.connectionStatusLabel)

        # send exiting to log
        _logger.debug('*** exiting App.setupStatusbar')
    
    ########################################################################### Main window setup
    def setupMainWindow(self):
        # send calling to log
        _logger.debug('*** calling App.setupMenu')

        self.containerLayout = QVBoxLayout()
        self.containerLayout.setSpacing(8)
        self.centralWidget.setLayout(self.containerLayout)
        #### Main grid layout       
        if(True):
            self.mainLayout = QHBoxLayout()
            self.mainLayout.setSpacing(8)
            self.containerLayout.addLayout(self.mainLayout)
            ##### Left toolbar
            if(True):
                self.leftToolbarLayout = QVBoxLayout()
                self.leftToolbarLayout.setAlignment(Qt.AlignTop)
                self.mainLayout.addLayout(self.leftToolbarLayout)
                # Connect button
                self.connectButton = QPushButton('+')
                self.connectButton.setStyleSheet(self.styleDisabled)
                self.connectButton.setMinimumSize(self.pushbuttonSize,self.pushbuttonSize)
                self.connectButton.setMaximumSize(self.pushbuttonSize,self.pushbuttonSize)
                self.connectButton.setToolTip('Connect..')
                self.connectButton.setDisabled(True)
                self.connectButton.clicked.connect(self.connectPrinter)
                self.leftToolbarLayout.addWidget(self.connectButton)#, 1, 0, 1, 1, Qt.AlignLeft|Qt.AlignTop)
                # Disconnect button
                self.disconnectButton = QPushButton('D')
                self.disconnectButton.setStyleSheet(self.styleDisabled)
                self.disconnectButton.setMinimumSize(self.pushbuttonSize,self.pushbuttonSize)
                self.disconnectButton.setMaximumSize(self.pushbuttonSize,self.pushbuttonSize)
                self.disconnectButton.setToolTip('Disconnect..')
                self.disconnectButton.setDisabled(True)
                self.disconnectButton.clicked.connect(self.haltPrinterOperation)
                self.leftToolbarLayout.addWidget(self.disconnectButton)#, 1, 0, 1, 1, Qt.AlignLeft|Qt.AlignTop)
                # Crosshair button
                self.crosshairDisplayButton = QPushButton('-+-')
                self.crosshairDisplayButton.setStyleSheet(self.styleBlue)
                self.crosshairDisplayButton.setMinimumSize(self.pushbuttonSize,self.pushbuttonSize)
                self.crosshairDisplayButton.setMaximumSize(self.pushbuttonSize,self.pushbuttonSize)
                self.crosshairDisplayButton.setToolTip('toggle crosshair on display')
                self.crosshairDisplayButton.setDisabled(False)
                self.crosshairDisplayButton.setChecked(False)
                self.crosshairDisplayButton.clicked.connect(self.toggleCrosshair)
                self.leftToolbarLayout.addWidget(self.crosshairDisplayButton)
                # Setup Control Point button
                self.cpSetupButton = QPushButton('CP')
                self.cpSetupButton.setStyleSheet(self.styleDisabled)
                self.cpSetupButton.setMinimumSize(self.pushbuttonSize,self.pushbuttonSize)
                self.cpSetupButton.setMaximumSize(self.pushbuttonSize,self.pushbuttonSize)
                self.cpSetupButton.setToolTip('Setup Control Point..')
                self.cpSetupButton.setDisabled(True)
                self.cpSetupButton.clicked.connect(self.setupCPCapture)
                self.leftToolbarLayout.addWidget(self.cpSetupButton)
                # CP Automated Capture button
                self.cpAutoCaptureButton = QPushButton('Auto')
                self.cpAutoCaptureButton.setStyleSheet(self.styleDisabled)
                self.cpAutoCaptureButton.setMinimumSize(self.pushbuttonSize,self.pushbuttonSize)
                self.cpAutoCaptureButton.setMaximumSize(self.pushbuttonSize,self.pushbuttonSize)
                self.cpAutoCaptureButton.setToolTip('Automated CP Capture..')
                self.cpAutoCaptureButton.setDisabled(True)
                self.cpAutoCaptureButton.clicked.connect(self.setupCPAutoCapture)
                self.leftToolbarLayout.addWidget(self.cpAutoCaptureButton)
            
            ##### Main image preview
            if(True):
                self.image = QLabel(self)
                self.image.resize(self._cameraWidth, self._cameraHeight)
                self.image.setMinimumWidth(self._cameraWidth)
                self.image.setMinimumHeight(self._cameraHeight)
                self.image.setAlignment(Qt.AlignLeft)
                # self.image.setStyleSheet('text-align:center; border: 1px solid black')
                self.image.setPixmap(self.standbyImage)
                self.mainLayout.addWidget(self.image)#, 1, 1, 1, -1, Qt.AlignLeft|Qt.AlignTop)
            
            ##### Right toolbar
            if(True):
                # Jog Panel
                self.tabPanel = QTabWidget()
                self.firstTab = QWidget()
                self.jogPanel = QGridLayout()
                self.jogPanel.setAlignment(Qt.AlignRight|Qt.AlignTop)
                self.jogPanel.setSpacing(5)
                
                # create jogPanel buttons
                ## increment size
                self.button_1 = QPushButton('1')
                self.button_1.setFixedSize(self.pushbuttonSize,self.pushbuttonSize)
                self.button_1.setMaximumHeight(self.pushbuttonSize)
                self.button_1.setToolTip('set jog distance to 1 unit')
                self.button_01 = QPushButton('.1')
                self.button_01.setFixedSize(self.pushbuttonSize,self.pushbuttonSize)
                self.button_01.setMaximumHeight(self.pushbuttonSize)
                self.button_01.setToolTip('set jog distance to 0.1 unit')
                self.button_001 = QPushButton('.01')
                self.button_001.setFixedSize(self.pushbuttonSize,self.pushbuttonSize)
                self.button_001.setMaximumHeight(self.pushbuttonSize)
                self.button_001.setToolTip('set jog distance to 0.01 unit')
                self.incrementButtonGroup = QButtonGroup()
                self.incrementButtonGroup.addButton(self.button_1)
                self.incrementButtonGroup.addButton(self.button_01)
                self.incrementButtonGroup.addButton(self.button_001)
                self.incrementButtonGroup.setExclusive(True)
                self.button_1.setCheckable(True)
                self.button_01.setCheckable(True)
                self.button_001.setCheckable(True)
                self.button_1.setChecked(True)
                
                # horizontal separators
                self.incrementLine = QFrame()
                self.incrementLine.setFrameShape(QFrame.HLine)
                self.incrementLine.setLineWidth(1)
                self.incrementLine.setFrameShadow(QFrame.Sunken)
                self.keypadLine = QFrame()
                self.keypadLine.setFrameShape(QFrame.HLine)
                self.keypadLine.setFrameShadow(QFrame.Sunken)
                self.keypadLine.setLineWidth(1)

                ## X movement
                self.button_x_left = QPushButton('-X', objectName='plus')
                self.button_x_left.setFixedSize(self.pushbuttonSize,self.pushbuttonSize)
                self.button_x_left.setMaximumHeight(self.pushbuttonSize)
                self.button_x_left.setToolTip('jog X-')
                self.button_x_left.clicked.connect(self.xleftClicked)
                self.button_x_right = QPushButton('X+', objectName='plus')
                self.button_x_right.setFixedSize(self.pushbuttonSize,self.pushbuttonSize)
                self.button_x_right.setMaximumHeight(self.pushbuttonSize)
                self.button_x_right.setToolTip('jog X+')
                self.button_x_right.clicked.connect(self.xRightClicked)
                
                ## Y movement
                self.button_y_left = QPushButton('-Y', objectName='plus')
                self.button_y_left.setFixedSize(self.pushbuttonSize,self.pushbuttonSize)
                self.button_y_left.setMaximumHeight(self.pushbuttonSize)
                self.button_y_left.setToolTip('jog Y-')
                self.button_y_left.clicked.connect(self.yleftClicked)
                self.button_y_right = QPushButton('Y+', objectName='plus')
                self.button_y_right.setFixedSize(self.pushbuttonSize,self.pushbuttonSize)
                self.button_y_right.setMaximumHeight(self.pushbuttonSize)
                self.button_y_right.setToolTip('jog Y+')
                self.button_y_right.clicked.connect(self.yRightClicked)
                
                ## Z movement
                self.button_z_down = QPushButton('-Z', objectName='plus')
                self.button_z_down.setFixedSize(self.pushbuttonSize,self.pushbuttonSize)
                self.button_z_down.setMaximumHeight(self.pushbuttonSize)
                self.button_z_down.setToolTip('jog Z-')
                self.button_z_down.clicked.connect(self.zleftClicked)
                self.button_z_up = QPushButton('Z+', objectName='plus')
                self.button_z_up.setFixedSize(self.pushbuttonSize,self.pushbuttonSize)
                self.button_z_up.setMaximumHeight(self.pushbuttonSize)
                self.button_z_up.setToolTip('jog Z+')
                self.button_z_up.clicked.connect(self.zRightClicked)
                
                ## layout jogPanel buttons
                # add increment buttons
                self.jogPanel.addWidget(self.button_001,0,0)
                self.jogPanel.addWidget(self.button_01,0,1)
                self.jogPanel.addWidget(self.button_1,1,1)
                # add separator
                self.jogPanel.addWidget(self.incrementLine, 2,0,1,2)
                # add X movement buttons
                self.jogPanel.addWidget(self.button_x_left,3,0)
                self.jogPanel.addWidget(self.button_x_right,3,1)
                # add Y movement buttons
                self.jogPanel.addWidget(self.button_y_left,4,0)
                self.jogPanel.addWidget(self.button_y_right,4,1)
                # add Z movement buttons
                self.jogPanel.addWidget(self.button_z_down,5,0)
                self.jogPanel.addWidget(self.button_z_up,5,1)
                # add separator
                self.jogPanel.addWidget(self.keypadLine, 6,0,1,2)
                
                self.tabPanel.setDisabled(True)
                self.mainLayout.addWidget(self.tabPanel)
                self.firstTab.setLayout(self.jogPanel)
                self.tabPanel.addTab(self.firstTab,'Jog')
                self.tabPanel.setFixedWidth(95)
                self.tabPanel.setTabBarAutoHide(True)
                self.tabPanel.setStyleSheet('QTabWidget::pane {\
                    margin: -13px -9px -13px -9px;\
                    border: 1px solid white;\
                    padding: 0px;\
                    }')

        #### Footer layout
        if(True):
            self.footerLayout = QGridLayout()
            self.footerLayout.setSpacing(0)
            self.containerLayout.addLayout(self.footerLayout)
            # Intructions box
            self.instructionsBox = QTextEdit()
            self.instructionsBox.setReadOnly(True)
            self.instructionsBox.setFixedSize(640, 45)
            self.instructionsBox.setVisible(False)
            self.footerLayout.addWidget(self.instructionsBox, 0,0,1,-1,Qt.AlignLeft|Qt.AlignVCenter)

            # Manual CP Capture button
            self.manualCPCaptureButton = QPushButton('Save CP')
            self.manualCPCaptureButton.setStyleSheet(self.styleDisabled)
            self.manualCPCaptureButton.setMinimumSize(self.pushbuttonSize*2,self.pushbuttonSize)
            self.manualCPCaptureButton.setMaximumSize(self.pushbuttonSize*2,self.pushbuttonSize)
            self.manualCPCaptureButton.setToolTip('Capture current machine coordinates as the Control Point.')
            self.manualCPCaptureButton.setDisabled(True)
            self.manualCPCaptureButton.setVisible(False)
            self.manualCPCaptureButton.clicked.connect(self.manualCPCapture)
            self.footerLayout.addWidget(self.manualCPCaptureButton, 0,1,1,1,Qt.AlignRight|Qt.AlignVCenter)

            # Manual Tool offset Capture button
            self.manualToolOffsetCaptureButton = QPushButton('Capture offset')
            self.manualToolOffsetCaptureButton.setStyleSheet(self.styleDisabled)
            self.manualToolOffsetCaptureButton.setMinimumSize(self.pushbuttonSize*3,self.pushbuttonSize)
            self.manualToolOffsetCaptureButton.setMaximumSize(self.pushbuttonSize*3,self.pushbuttonSize)
            self.manualToolOffsetCaptureButton.setToolTip('Capture current position and calculate tool offset.')
            self.manualToolOffsetCaptureButton.setDisabled(True)
            self.manualToolOffsetCaptureButton.setVisible(False)
            self.manualToolOffsetCaptureButton.clicked.connect(self.manualToolOffsetCapture)
            self.footerLayout.addWidget(self.manualToolOffsetCaptureButton, 0,1,1,1,Qt.AlignRight|Qt.AlignVCenter)

            # Start Alignment button
            self.alignToolsButton = QPushButton('Align Tools')
            self.alignToolsButton.setStyleSheet(self.styleDisabled)
            self.alignToolsButton.setMinimumSize(self.pushbuttonSize*3,self.pushbuttonSize)
            self.alignToolsButton.setMaximumSize(self.pushbuttonSize*3,self.pushbuttonSize)
            self.alignToolsButton.setToolTip('Start automated tool offset calibration')
            self.alignToolsButton.setDisabled(True)
            self.alignToolsButton.setVisible(False)
            self.alignToolsButton.clicked.connect(self.startAlignTools)
            self.footerLayout.addWidget(self.alignToolsButton, 0,1,1,1,Qt.AlignRight|Qt.AlignVCenter)

            # Resume auto alignment button
            self.resumeAutoToolAlignmentButton = QPushButton('Resume Auto Align')
            self.resumeAutoToolAlignmentButton.setMinimumSize(self.pushbuttonSize*4,self.pushbuttonSize)
            self.resumeAutoToolAlignmentButton.setMaximumSize(self.pushbuttonSize*4,self.pushbuttonSize)
            self.resumeAutoToolAlignmentButton.setToolTip('Resume automated calibration')
            self.resumeAutoToolAlignmentButton.setDisabled(True)
            self.resumeAutoToolAlignmentButton.setVisible(False)
            self.resumeAutoToolAlignmentButton.clicked.connect(self.resumeAutoAlignment)
            self.footerLayout.addWidget(self.resumeAutoToolAlignmentButton, 0,0,1,1,Qt.AlignRight|Qt.AlignVCenter)


        #### Set current interface state to disconnected
        self.stateDisconnected()

        # send exiting to log
        _logger.debug('*** exiting App.setupMenu')

    ########################################################################### Jog Panel functions
    def xleftClicked(self):
        # disable buttons
        self.tabPanel.setDisabled(True)
        # fetch current increment value
        if self.button_1.isChecked():
            incrementDistance = 1
        elif self.button_01.isChecked():
            incrementDistance = 0.1
        elif self.button_001.isChecked():
            incrementDistance = 0.01
        params = {'moveSpeed': self._moveSpeed, 'position':{'X': str(-1*incrementDistance)}}
        self.moveRelativeSignal.emit(params)
    
    def xRightClicked(self):
        # disable buttons
        self.tabPanel.setDisabled(True)
        # fetch current increment value
        if self.button_1.isChecked():
            incrementDistance = 1
        elif self.button_01.isChecked():
            incrementDistance = 0.1
        elif self.button_001.isChecked():
            incrementDistance = 0.01
        params = {'moveSpeed': self._moveSpeed, 'position':{'X': str(incrementDistance)}}
        self.moveRelativeSignal.emit(params)
    
    def yleftClicked(self):
        # disable buttons
        self.tabPanel.setDisabled(True)
        # fetch current increment value
        if self.button_1.isChecked():
            incrementDistance = 1
        elif self.button_01.isChecked():
            incrementDistance = 0.1
        elif self.button_001.isChecked():
            incrementDistance = 0.01
        params = {'moveSpeed': self._moveSpeed, 'position':{'Y': str(-1*incrementDistance)}}
        self.moveRelativeSignal.emit(params)
    
    def yRightClicked(self):
        # disable buttons
        self.tabPanel.setDisabled(True)
        # fetch current increment value
        if self.button_1.isChecked():
            incrementDistance = 1
        elif self.button_01.isChecked():
            incrementDistance = 0.1
        elif self.button_001.isChecked():
            incrementDistance = 0.01
        params = {'moveSpeed': self._moveSpeed, 'position':{'Y': str(incrementDistance)}}
        self.moveRelativeSignal.emit(params)

    def zleftClicked(self):
        # disable buttons
        self.tabPanel.setDisabled(True)
        # fetch current increment value
        if self.button_1.isChecked():
            incrementDistance = 1
        elif self.button_01.isChecked():
            incrementDistance = 0.1
        elif self.button_001.isChecked():
            incrementDistance = 0.01
        params = {'moveSpeed': self._moveSpeed, 'position':{'Z': str(-1*incrementDistance)}}
        self.moveRelativeSignal.emit(params)
    
    def zRightClicked(self):
        # disable buttons
        self.tabPanel.setDisabled(True)
        # fetch current increment value
        if self.button_1.isChecked():
            incrementDistance = 1
        elif self.button_01.isChecked():
            incrementDistance = 0.1
        elif self.button_001.isChecked():
            incrementDistance = 0.01
        params = {'moveSpeed': self._moveSpeed, 'position':{'Z': str(incrementDistance)}}
        self.moveRelativeSignal.emit(params)
    
    ########################################################################### GUI State functions
    def stateDisconnected(self):
        # Settings option in menu
        self.preferencesAction.setDisabled(False)
        # Connect button
        self.connectButton.setVisible(True)
        self.connectButton.setDisabled(False)
        self.connectButton.setStyleSheet(self.styleGreen)
        # Disconnect button
        self.disconnectButton.setVisible(False)
        self.disconnectButton.setDisabled(True)
        self.disconnectButton.setStyleSheet(self.styleDisabled)
        # Setup CP button
        self.cpSetupButton.setVisible(False)
        self.cpSetupButton.setDisabled(True)
        self.cpSetupButton.setStyleSheet(self.styleDisabled)
        # CP Automated Capture button
        self.cpAutoCaptureButton.setVisible(False)
        self.cpAutoCaptureButton.setDisabled(True)
        self.cpAutoCaptureButton.setStyleSheet(self.styleDisabled)
        # Manual capture button
        self.manualCPCaptureButton.setVisible(False)
        self.manualCPCaptureButton.setDisabled(True)
        self.manualCPCaptureButton.setStyleSheet(self.styleDisabled)
        # Start Alignment button
        self.alignToolsButton.setVisible(False)
        self.alignToolsButton.setDisabled(True)
        self.alignToolsButton.setStyleSheet(self.styleDisabled)
        # Manual Tool offset Capture button
        self.manualToolOffsetCaptureButton.setVisible(False)
        self.manualToolOffsetCaptureButton.setDisabled(True)
        self.manualToolOffsetCaptureButton.setStyleSheet(self.styleDisabled)
        # Resume auto alignment button
        self.resumeAutoToolAlignmentButton.setVisible(False)
        self.resumeAutoToolAlignmentButton.setDisabled(True)
        self.resumeAutoToolAlignmentButton.setStyleSheet(self.styleDisabled)
        # Delete tool buttons
        count = self.jogPanel.count()
        for i in range(11,count):
            item = self.jogPanel.itemAt(i)
            widget = item.widget()
            widget.setVisible(False)
            # widget.deleteLater()
        self.resetCalibration()
        # Crosshair display button
        self.crosshairDisplayButton.setVisible(True)
        self.crosshairDisplayButton.setDisabled(False)
        if(self.__displayCrosshair):
            self.crosshairDisplayButton.setStyleSheet(self.styleOrange)
            self.crosshairDisplayButton.setChecked(True)
        else:
            self.crosshairDisplayButton.setStyleSheet(self.styleBlue)
            self.crosshairDisplayButton.setChecked(False)
        # Jog panel tab
        self.tabPanel.setDisabled(True)

    def stateConnected(self):
        # Settings option in menu
        self.preferencesAction.setDisabled(False)
        # Connect button
        self.connectButton.setVisible(False)
        self.connectButton.setDisabled(True)
        self.connectButton.setStyleSheet(self.styleDisabled)
        # Disconnect button
        self.disconnectButton.setVisible(True)
        self.disconnectButton.setDisabled(False)
        self.disconnectButton.setStyleSheet(self.styleRed)
        self.disconnectButton.setText('D')
        self.disconnectButton.setToolTip('Disconnect..')
        # Setup CP button
        self.cpSetupButton.setVisible(True)
        self.cpSetupButton.setDisabled(False)
        self.cpSetupButton.setStyleSheet(self.styleGreen)
        # CP Automated Capture button
        self.cpAutoCaptureButton.setVisible(False)
        self.cpAutoCaptureButton.setDisabled(True)
        self.cpAutoCaptureButton.setStyleSheet(self.styleDisabled)
        # Manual capture button
        self.manualCPCaptureButton.setVisible(False)
        self.manualCPCaptureButton.setDisabled(True)
        self.manualCPCaptureButton.setStyleSheet(self.styleDisabled)
        # Start Alignment button
        self.alignToolsButton.setVisible(False)
        self.alignToolsButton.setDisabled(True)
        self.alignToolsButton.setStyleSheet(self.styleDisabled)
        # Manual Tool offset Capture button
        self.manualToolOffsetCaptureButton.setVisible(False)
        self.manualToolOffsetCaptureButton.setDisabled(True)
        self.manualToolOffsetCaptureButton.setStyleSheet(self.styleDisabled)
        # Resume auto alignment button
        self.resumeAutoToolAlignmentButton.setVisible(False)
        self.resumeAutoToolAlignmentButton.setDisabled(True)
        self.resumeAutoToolAlignmentButton.setStyleSheet(self.styleDisabled)
        # Jog panel tab
        self.tabPanel.setDisabled(False)
        
        # Add tool checkboxes to right panel
        self.toolButtons = []
        self.toolCheckboxes = []
        # highest tool number storage
        numTools = max(self.__activePrinter['tools'], key= lambda x:int(x['number']))['number']
        _logger.debug('Highest tool number is: ' + str(numTools))
        # Delete old toolbuttons, if they exist
        # Delete tool buttons
        count = self.jogPanel.count()
        for i in range(11,count):
            item = self.jogPanel.itemAt(i)
            widget = item.widget()
            widget.deleteLater()
        for tool in range(numTools+1):
            # add tool buttons
            toolButton = QPushButton('T' + str(tool))
            toolButton.setObjectName('toolButton_'+str(tool))
            toolButton.setFixedSize(self.pushbuttonSize,self.pushbuttonSize)
            toolButton.clicked.connect(self.identifyToolButton)
            # check if current index exists in tool numbers from machine
            if(any(d.get('number', -1) == tool for d in self.__activePrinter['tools'])):
                toolButton.setToolTip('Fetch T' +  str(tool) + ' to current machine position.')
                self.toolButtons.append(toolButton)
                # add tool checkboxes
                toolCheckbox = QCheckBox()
                toolCheckbox.setObjectName('toolCheckbox_' + str(tool))
                toolCheckbox.setToolTip('Add T' +  str(tool) + ' to calibration.')
                toolCheckbox.setChecked(True)
                toolCheckbox.setCheckable(True)
                toolCheckbox.setObjectName('toolCheckbox_' + str(tool))
                self.toolCheckboxes.append(toolCheckbox)
            
        # Display tool buttons
        for i,button in enumerate(self.toolButtons):
            button.setCheckable(True)
            index = button.objectName()
            index = int(index[-1:])
            if int(self.__activePrinter['currentTool']) == index:
                button.setChecked(True)
            else: 
                button.setChecked(False)
            # button.clicked.connect(self.callTool)
            self.jogPanel.addWidget(button, (7+i), 0, Qt.AlignCenter|Qt.AlignHCenter)

        # Display tool checkboxes
        for i,checkbox in enumerate(self.toolCheckboxes):
            checkbox.setCheckable(True)
            checkbox.setChecked(True)
            # button.clicked.connect(self.callTool)
            self.jogPanel.addWidget(checkbox, (7+i), 1, Qt.AlignCenter|Qt.AlignHCenter)
        # Alignment/Detection state reset
        self.state = 0
        # Endstop calibration state flags
        self.__stateManualCPCapture = False
        self.__stateAutoCPCapture = False
        self.__stateEndstopAutoCalibrate = False
        self.toggleEndstopAutoDetectionSignal.emit(False)
        # Nozzle calibration state flags
        self.__stateManualNozzleAlignment = False
        self.__stateAutoNozzleAlignment = False
        self.toggleNozzleAutoDetectionSignal.emit(False)
        # Crosshair display button
        self.crosshairDisplayButton.setVisible(True)
        self.crosshairDisplayButton.setDisabled(False)
        if(self.__displayCrosshair):
            self.crosshairDisplayButton.setStyleSheet(self.styleOrange)
            self.crosshairDisplayButton.setChecked(True)
        else:
            self.crosshairDisplayButton.setStyleSheet(self.styleBlue)
            self.crosshairDisplayButton.setChecked(False)

        _logger.debug('Tool data and interface created successfully.')

    def stateCPSetup(self):
        # Settings option in menu
        self.preferencesAction.setDisabled(False)
        # Connect button
        self.connectButton.setVisible(False)
        self.connectButton.setDisabled(True)
        self.connectButton.setStyleSheet(self.styleDisabled)
        # Disconnect button
        self.disconnectButton.setVisible(True)
        self.disconnectButton.setDisabled(False)
        self.disconnectButton.setStyleSheet(self.styleRed)
        self.disconnectButton.setText('C')
        self.disconnectButton.setToolTip('Cancel..')
        # Setup CP button
        self.cpSetupButton.setVisible(True)
        self.cpSetupButton.setDisabled(True)
        self.cpSetupButton.setStyleSheet(self.styleDisabled)
        # CP Automated Capture button
        self.cpAutoCaptureButton.setVisible(True)
        self.cpAutoCaptureButton.setDisabled(False)
        self.cpAutoCaptureButton.setStyleSheet(self.styleOrange)
        # Manual capture button
        self.manualCPCaptureButton.setVisible(True)
        self.manualCPCaptureButton.setDisabled(False)
        self.manualCPCaptureButton.setStyleSheet(self.styleGreen)
        # Start Alignment button
        self.alignToolsButton.setVisible(False)
        self.alignToolsButton.setDisabled(True)
        self.alignToolsButton.setStyleSheet(self.styleDisabled)
        # Manual Tool offset Capture button
        self.manualToolOffsetCaptureButton.setVisible(False)
        self.manualToolOffsetCaptureButton.setDisabled(True)
        self.manualToolOffsetCaptureButton.setStyleSheet(self.styleDisabled)
        # Resume auto alignment button
        self.resumeAutoToolAlignmentButton.setVisible(False)
        self.resumeAutoToolAlignmentButton.setDisabled(True)
        self.resumeAutoToolAlignmentButton.setStyleSheet(self.styleDisabled)
        # Crosshair display button
        self.crosshairDisplayButton.setVisible(True)
        self.crosshairDisplayButton.setDisabled(False)
        if(self.__displayCrosshair):
            self.crosshairDisplayButton.setStyleSheet(self.styleOrange)
            self.crosshairDisplayButton.setChecked(True)
        else:
            self.crosshairDisplayButton.setStyleSheet(self.styleBlue)
            self.crosshairDisplayButton.setChecked(False)
        # Jog panel tab
        self.tabPanel.setDisabled(False)

    def stateCPAuto(self):
        # Settings option in menu
        self.preferencesAction.setDisabled(False)
        # Connect button
        self.connectButton.setVisible(False)
        self.connectButton.setDisabled(True)
        self.connectButton.setStyleSheet(self.styleDisabled)
        # Disconnect button
        self.disconnectButton.setVisible(True)
        self.disconnectButton.setDisabled(False)
        self.disconnectButton.setStyleSheet(self.styleRed)
        self.disconnectButton.setText('C')
        self.disconnectButton.setToolTip('Cancel..')
        # Setup CP button
        self.cpSetupButton.setVisible(True)
        self.cpSetupButton.setDisabled(True)
        self.cpSetupButton.setStyleSheet(self.styleDisabled)
        # CP Automated Capture button
        self.cpAutoCaptureButton.setVisible(True)
        self.cpAutoCaptureButton.setDisabled(True)
        self.cpAutoCaptureButton.setStyleSheet(self.styleDisabled)
        # Manual capture button
        self.manualCPCaptureButton.setVisible(False)
        self.manualCPCaptureButton.setDisabled(True)
        self.manualCPCaptureButton.setStyleSheet(self.styleDisabled)
        # Start Alignment button
        self.alignToolsButton.setVisible(False)
        self.alignToolsButton.setDisabled(True)
        self.alignToolsButton.setStyleSheet(self.styleDisabled)
        # Manual Tool offset Capture button
        self.manualToolOffsetCaptureButton.setVisible(False)
        self.manualToolOffsetCaptureButton.setDisabled(True)
        self.manualToolOffsetCaptureButton.setStyleSheet(self.styleDisabled)
        # Resume auto alignment button
        self.resumeAutoToolAlignmentButton.setVisible(False)
        self.resumeAutoToolAlignmentButton.setDisabled(True)
        self.resumeAutoToolAlignmentButton.setStyleSheet(self.styleDisabled)
        # Crosshair display button
        self.crosshairDisplayButton.setVisible(True)
        self.crosshairDisplayButton.setDisabled(True)
        self.crosshairDisplayButton.setStyleSheet(self.styleDisabled)
        self.crosshairDisplayButton.setChecked(False)
        # Jog panel tab
        self.tabPanel.setDisabled(True)

    def stateCalibrateReady(self):
        # Settings option in menu
        self.preferencesAction.setDisabled(False)
        # Connect button
        self.connectButton.setVisible(False)
        self.connectButton.setDisabled(True)
        self.connectButton.setStyleSheet(self.styleDisabled)
        # Disconnect button
        self.disconnectButton.setVisible(True)
        self.disconnectButton.setDisabled(False)
        self.disconnectButton.setStyleSheet(self.styleRed)
        self.disconnectButton.setText('C')
        self.disconnectButton.setToolTip('Cancel..')
        # Setup CP button
        self.cpSetupButton.setVisible(True)
        self.cpSetupButton.setDisabled(False)
        self.cpSetupButton.setStyleSheet(self.styleBlue)
        # CP Automated Capture button
        self.cpAutoCaptureButton.setVisible(False)
        self.cpAutoCaptureButton.setDisabled(True)
        self.cpAutoCaptureButton.setStyleSheet(self.styleDisabled)
        # Manual capture button
        self.manualCPCaptureButton.setVisible(False)
        self.manualCPCaptureButton.setDisabled(True)
        self.manualCPCaptureButton.setStyleSheet(self.styleDisabled)
        # Start Alignment button
        self.alignToolsButton.setVisible(True)
        self.alignToolsButton.setDisabled(False)
        self.alignToolsButton.setStyleSheet(self.styleGreen)
        # Manual Tool offset Capture button
        self.manualToolOffsetCaptureButton.setVisible(False)
        self.manualToolOffsetCaptureButton.setDisabled(True)
        self.manualToolOffsetCaptureButton.setStyleSheet(self.styleDisabled)
        # Resume auto alignment button
        self.resumeAutoToolAlignmentButton.setVisible(False)
        self.resumeAutoToolAlignmentButton.setDisabled(True)
        self.resumeAutoToolAlignmentButton.setStyleSheet(self.styleDisabled)
        # Crosshair display button
        self.crosshairDisplayButton.setVisible(True)
        self.crosshairDisplayButton.setDisabled(False)
        if(self.__displayCrosshair):
            self.crosshairDisplayButton.setStyleSheet(self.styleOrange)
            self.crosshairDisplayButton.setChecked(True)
        else:
            self.crosshairDisplayButton.setStyleSheet(self.styleBlue)
            self.crosshairDisplayButton.setChecked(False)
        # Jog panel tab
        self.tabPanel.setDisabled(False)
        # Tool buttons
        for button in self.toolButtons:
            button.setStyleSheet('')
            button.setDisabled(False)

    def stateCalibtrateRunning(self):
        # Settings option in menu
        self.preferencesAction.setDisabled(True)
        # Connect button
        self.connectButton.setVisible(False)
        self.connectButton.setDisabled(True)
        self.connectButton.setStyleSheet(self.styleDisabled)
        # Disconnect button
        self.disconnectButton.setVisible(True)
        self.disconnectButton.setDisabled(False)
        self.disconnectButton.setStyleSheet(self.styleRed)
        self.disconnectButton.setText('C')
        self.disconnectButton.setToolTip('Cancel..')
        # Setup CP button
        self.cpSetupButton.setVisible(True)
        self.cpSetupButton.setDisabled(True)
        self.cpSetupButton.setStyleSheet(self.styleDisabled)
        # CP Automated Capture button
        self.cpAutoCaptureButton.setVisible(False)
        self.cpAutoCaptureButton.setDisabled(True)
        self.cpAutoCaptureButton.setStyleSheet(self.styleDisabled)
        # Manual capture button
        self.manualCPCaptureButton.setVisible(False)
        self.manualCPCaptureButton.setDisabled(True)
        self.manualCPCaptureButton.setStyleSheet(self.styleDisabled)
        # Start Alignment button
        self.alignToolsButton.setVisible(False)
        self.alignToolsButton.setDisabled(True)
        self.alignToolsButton.setStyleSheet(self.styleDisabled)
        # Manual Tool offset Capture button
        self.manualToolOffsetCaptureButton.setVisible(True)
        self.manualToolOffsetCaptureButton.setDisabled(True)
        self.manualToolOffsetCaptureButton.setStyleSheet(self.styleDisabled)
        # Resume auto alignment button
        self.resumeAutoToolAlignmentButton.setVisible(False)
        self.resumeAutoToolAlignmentButton.setDisabled(True)
        self.resumeAutoToolAlignmentButton.setStyleSheet(self.styleDisabled)
        # Crosshair display button
        self.crosshairDisplayButton.setVisible(True)
        self.crosshairDisplayButton.setDisabled(True)
        self.crosshairDisplayButton.setStyleSheet(self.styleDisabled)
        self.crosshairDisplayButton.setChecked(False)
        # Jog panel tab
        self.tabPanel.setDisabled(True)
        # Tool selection buttons disable
        for button in self.toolButtons:
            button.setDisabled(True)

    def stateCalibrateComplete(self):
        # Settings option in menu
        self.preferencesAction.setDisabled(False)
        # Connect button
        self.connectButton.setVisible(False)
        self.connectButton.setDisabled(True)
        self.connectButton.setStyleSheet(self.styleDisabled)
        # Disconnect button
        self.disconnectButton.setVisible(True)
        self.disconnectButton.setDisabled(False)
        self.disconnectButton.setStyleSheet(self.styleRed)
        self.disconnectButton.setText('D')
        self.disconnectButton.setToolTip('Disconnect..')
        # Setup CP button
        self.cpSetupButton.setVisible(True)
        self.cpSetupButton.setDisabled(False)
        self.cpSetupButton.setStyleSheet(self.styleBlue)
        # CP Automated Capture button
        self.cpAutoCaptureButton.setVisible(False)
        self.cpAutoCaptureButton.setDisabled(True)
        self.cpAutoCaptureButton.setStyleSheet(self.styleDisabled)
        # Manual capture button
        self.manualCPCaptureButton.setVisible(False)
        self.manualCPCaptureButton.setDisabled(True)
        self.manualCPCaptureButton.setStyleSheet(self.styleDisabled)
        # Start Alignment button
        self.alignToolsButton.setVisible(True)
        self.alignToolsButton.setDisabled(False)
        self.alignToolsButton.setStyleSheet(self.styleGreen)
        # Manual Tool offset Capture button
        self.manualToolOffsetCaptureButton.setVisible(False)
        self.manualToolOffsetCaptureButton.setDisabled(True)
        self.manualToolOffsetCaptureButton.setStyleSheet(self.styleDisabled)
        # Resume auto alignment button
        self.resumeAutoToolAlignmentButton.setVisible(False)
        self.resumeAutoToolAlignmentButton.setDisabled(True)
        self.resumeAutoToolAlignmentButton.setStyleSheet(self.styleDisabled)
        # Crosshair display button
        self.crosshairDisplayButton.setVisible(True)
        self.crosshairDisplayButton.setDisabled(False)
        if(self.__displayCrosshair):
            self.crosshairDisplayButton.setStyleSheet(self.styleOrange)
            self.crosshairDisplayButton.setChecked(True)
        else:
            self.crosshairDisplayButton.setStyleSheet(self.styleBlue)
            self.crosshairDisplayButton.setChecked(False)
        # Jog panel tab
        self.tabPanel.setDisabled(False)
        # Tool buttons
        for button in self.toolButtons:
            button.setStyleSheet('')
            button.setDisabled(False)

    def stateExiting(self):
        # Settings option in menu
        self.preferencesAction.setDisabled(True)
        # Connect button
        self.connectButton.setVisible(True)
        self.connectButton.setDisabled(True)
        self.connectButton.setStyleSheet(self.styleDisabled)
        # Disconnect button
        self.disconnectButton.setVisible(True)
        self.disconnectButton.setDisabled(True)
        self.disconnectButton.setStyleSheet(self.styleDisabled)
        self.disconnectButton.setText('-')
        self.disconnectButton.setToolTip('Disconnecting..')
        # Setup CP button
        self.cpSetupButton.setVisible(True)
        self.cpSetupButton.setDisabled(True)
        self.cpSetupButton.setStyleSheet(self.styleDisabled)
        # CP Automated Capture button
        self.cpAutoCaptureButton.setVisible(True)
        self.cpAutoCaptureButton.setDisabled(True)
        self.cpAutoCaptureButton.setStyleSheet(self.styleDisabled)
        # Manual capture button
        self.manualCPCaptureButton.setVisible(False)
        self.manualCPCaptureButton.setDisabled(True)
        self.manualCPCaptureButton.setStyleSheet(self.styleDisabled)
        # Start Alignment button
        self.alignToolsButton.setVisible(False)
        self.alignToolsButton.setDisabled(True)
        self.alignToolsButton.setStyleSheet(self.styleGreen)
        # Manual Tool offset Capture button
        self.manualToolOffsetCaptureButton.setVisible(False)
        self.manualToolOffsetCaptureButton.setDisabled(True)
        self.manualToolOffsetCaptureButton.setStyleSheet(self.styleDisabled)
        # Resume auto alignment button
        self.resumeAutoToolAlignmentButton.setVisible(False)
        self.resumeAutoToolAlignmentButton.setDisabled(True)
        self.resumeAutoToolAlignmentButton.setStyleSheet(self.styleDisabled)
        # Crosshair display button
        self.crosshairDisplayButton.setVisible(True)
        self.crosshairDisplayButton.setDisabled(True)
        self.crosshairDisplayButton.setStyleSheet(self.styleDisabled)
        self.crosshairDisplayButton.setChecked(False)    
        # Jog panel tab
        self.tabPanel.setDisabled(True)

    ########################################################################### User interactions
    def setupCPCapture(self):
        self.__stateSetupCPCapture = True
        self.toggleEndstopDetectionSignal.emit(True)
        # enable detection
        self.toggleDetectionSignal.emit(True)
        self.__displayCrosshair = True
        # update machine coordinates
        self.pollCoordinatesSignal.emit()
        # Get original physical coordinates
        self.originalPrinterPosition = self.__currentPosition
        self.__restorePosition = copy.deepcopy(self.__currentPosition)
        self.resetCalibrationVariables()
        self.stateCPSetup()
        self.repaint()

    def manualCPCapture(self):
        self.__stateSetupCPCapture = False
        self.__stateManualCPCapture = True
        # update machine coordinates
        self.pollCoordinatesSignal.emit()
        # stop endstop detection
        self.toggleEndstopDetectionSignal.emit(False)
        # update GUI
        self.stateCalibrateReady()
    
    def setupCPAutoCapture(self):
        # send calling to log
        _logger.debug('*** calling App.setupCPAutoCapture')
        self.startTime = time.time()
        #################################### Camera Calibration
        # Update GUI state
        self.stateCPAuto()
        # set state flag to handle camera calibration
        self.__stateEndstopAutoCalibrate = True
        self.__stateAutoCPCapture = True
        # Start detector in DetectionManager
        self.toggleEndstopAutoDetectionSignal.emit(True)
        self.uv = [None, None]
        self.unloadToolSignal.emit()
        self.pollCoordinatesSignal.emit()
        # send exiting to log
        _logger.debug('*** exiting App.setupCPAutoCapture')

    def haltCPAutoCapture(self):
        self.resetCalibration()
        self.resetCalibrationVariables()
        self.statusBar.showMessage('CP calibration cancelled.')
        # Reset GUI
        self.stateConnected()

    def haltNozzleCapture(self):
        self.resetNozzleAlignment()
        self.statusBar.showMessage('Nozzle calibration halted.')
        # Reset GUI
        self.stateCalibrateReady()
    
    def manualToolOffsetCapture(self):
        self.manualToolOffsetCaptureButton.setDisabled(True)
        self.manualToolOffsetCaptureButton.setStyleSheet(self.styleDisabled)
        # set tool alignment state to trigger offset calculation
        self.state = 100
        self.pollCoordinatesSignal.emit()

    def resetCalibration(self):
        # Reset program state, and frame capture control to defaults
        self.__stateEndstopAutoCalibrate = False
        self.__stateAutoCPCapture = False
        self.__stateSetupCPCapture = False
        self.__stateManualNozzleAlignment = False
        self.__stateAutoNozzleAlignment = False
        self.toggleEndstopAutoDetectionSignal.emit(False)
        self.toggleNozzleAutoDetectionSignal.emit(False)
        self.toggleEndstopDetectionSignal.emit(False)
        self.toggleDetectionSignal.emit(False)
        self.__displayCrosshair = False
        self.resetCalibrationVariables()
        self.unloadToolSignal.emit()
        self.getVideoFrameSignal.emit()
    
    def resetNozzleAlignment(self):
        # Reset program state, and frame capture control to defaults
        self.__stateEndstopAutoCalibrate = False
        self.__stateAutoCPCapture = False
        self.__stateSetupCPCapture = False
        self.__stateManualNozzleAlignment = False
        self.__stateAutoNozzleAlignment = False
        self.toggleEndstopAutoDetectionSignal.emit(False)
        self.toggleNozzleAutoDetectionSignal.emit(False)
        self.toggleEndstopDetectionSignal.emit(False)
        self.toggleDetectionSignal.emit(False)
        self.__displayCrosshair = False
        self.resetCalibrationVariables()
        self.tabPanel.setDisabled(True)
        self.unloadToolSignal.emit()
        self.getVideoFrameSignal.emit()

    # Function to reset calibrateTools variables
    def resetCalibrationVariables(self):
        # Setup camera calibration move coordinates
        self.calibrationCoordinates = [ [0,-0.5], [0.294,-0.405], [0.476,-0.155], [0.476,0.155], [0.294,0.405], [0,0.5], [-0.294,0.405], [-0.476,0.155], [-0.476,-0.155], [-0.294,-0.405] ]
        # reset all variables
        self.guessPosition  = [1,1]
        self.uv = [None, None]
        self.olduv  = self.uv
        if(self.transformMatrix is None or self.mpp is None):
            _logger.debug('Camera calibration matrix reset.')
            self.state = 0
        elif(len(self.transformMatrix) < 6):
            self.transformMatrix = None
            self.mpp = None
            self.state = 0
        else:
            self.state = 200
        self.detect_count = 0
        self.space_coordinates = []
        self.camera_coordinates = []
        self.retries = 0
        self.calibrationMoves = 0
        self.repeatCounter = 0

    def startAlignTools(self):
        # send calling to log
        _logger.debug('*** calling App.startAlignTools')
        self.startTime = time.time()
        self.__stateManualNozzleAlignment = True
        self.__stateAutoNozzleAlignment = True

        # Update GUI state
        self.stateCalibtrateRunning()
        self.updateStatusbarMessage('Starting tool alignment..')

        # Create array for tools included in alignment process
        self.alignmentToolSet = []
        self.workingToolset = None
        for checkbox in self.toolCheckboxes:
            if(checkbox.isChecked()):
                self.alignmentToolSet.append(int(checkbox.objectName()[13:]))
        if(len(self.alignmentToolSet) > 0):
            self.toggleNozzleAutoDetectionSignal.emit(True)
            self.calibrateTools(self.alignmentToolSet)
        else:
            # tell user no tools selected
            errorMsg = 'No tools selected for alignment'
            self.updateStatusbarMessage(errorMsg)
            _logger.info(errorMsg)
            self.haltNozzleCapture()
        # send exiting to log
        _logger.debug('*** exiting App.startAlignTools')

    def identifyToolButton(self):
        self.tabPanel.setDisabled(True)
        sender = self.sender()
        for button in self.toolButtons:
            if button.objectName() != sender.objectName():
                button.setChecked(False)
        toolIndex = int(sender.objectName()[11:])
        if(toolIndex != int(self.__activePrinter['currentTool'])):
            self.updateStatusbarMessage('>>> Loading T' + str(toolIndex) + '.. >>>')
            self.callTool(toolIndex)
        else:
            self.updateStatusbarMessage('<<< Unloading tool.. <<<')
            self.callTool(-1)
    
    def calibrateTools(self, toolset=None):
        # toolset is passed the first time we call the function
        # this creates the workingToolset, from which we pop each tool on each cycle
        if(toolset is not None):
            self.workingToolset = toolset
        # check if we still have tools to calibrate in the workingToolset list
        if(len(self.workingToolset)>0):
            # grab the first item in the list (FIFO)
            toolIndex = self.workingToolset[0]
            _logger.info('Calibrating T' + str(toolIndex) +'..')
            # delete the tool from the list before processing it
            self.workingToolset.pop(0)
            # update toolButtons GUI to indiciate which tool we're working on
            for button in self.toolButtons:
                buttonName = 'toolButton_' + str(toolIndex)
                if(button.objectName() == buttonName):
                    button.setStyleSheet(self.styleOrange)
            self.resetCalibrationVariables()
            # main program state flags
            self.__stateManualNozzleAlignment = True
            self.__stateAutoNozzleAlignment = True
            # DetectionManager state flag
            self.toggleNozzleAutoDetectionSignal.emit(True)
            # Capture start time of tool calibration run
            self.toolTime = time.time()
            # Call tool and start calibration
            self.callTool(toolIndex)
        else:
            # entire list has been processed, output results
            calibration_time = np.around(time.time() - self.startTime,1)
            _logger.info('Calibration completed (' + str(calibration_time) + 's) with a resolution of ' + str(self.mpp) + '/pixel')
            # reset GUI
            self.stateCalibrateComplete()
            self.repaint()
            # reset state flags for main program and Detection Manager
            self.resetNozzleAlignment()

    def autoCalibrate(self):
        self.tabPanel.setDisabled(True)
        try:
            if(runtime):
                pass
        except:
            runtime = time.time()
        if(self.uv is not None):
            if(self.uv[0] is not None and self.uv[1] is not None):
                # First calibration step
                if(self.state == 0):
                    _logger.info('*** State: ' + str(self.state) + ' Coords:' + str(self.__currentPosition) + ' UV: ' + str(self.uv) + ' old UV: ' + str(self.olduv))
                    self.updateStatusbarMessage('Calibrating camera step 0..')
                    if(self.olduv is not None):
                        if(self.olduv[0] == self.uv[0] and self.olduv[1] == self.uv[1]):
                            # print('Repeating detection: ' + str(self.repeatCounter))
                            self.repeatCounter += 1
                            if(self.repeatCounter > 10):
                                self.nozzleDetectionFailed()
                                return
                            # loop through again
                            self.retries += 1
                            self.pollCoordinatesSignal.emit()
                            return
                        else:
                            # print('Took ' + str(self.repeatCounter) + ' attempts.')
                            self.repeatCounter = 0
                    self.olduv = self.uv
                    self.space_coordinates = []
                    self.camera_coordinates = []

                    self.space_coordinates.append((self.__currentPosition['X'], self.__currentPosition['Y']))
                    self.camera_coordinates.append((self.uv[0], self.uv[1]))

                    # move carriage for calibration
                    self.offsetX = self.calibrationCoordinates[0][0]
                    self.offsetY = self.calibrationCoordinates[0][1]
                    params = {'position':{'X': self.offsetX, 'Y': self.offsetY}}
                    self.lastState = 0
                    self.state = 1
                    self.moveRelativeSignal.emit(params)
                    return
                elif(self.state >= 1 and self.state < len(self.calibrationCoordinates)):
                    # capture the UV data when a calibration move has been executed, before returning to original position
                    if(self.state != self.lastState):
                        _logger.info('*** State: ' + str(self.state) + ' Coords:' + str(self.__currentPosition) + ' UV: ' + str(self.uv) + ' old UV: ' + str(self.olduv))
                        if(self.olduv is not None):
                            if(self.olduv[0] == self.uv[0] and self.olduv[1] == self.uv[1]):
                                # print('Repeating detection: ' + str(self.repeatCounter))
                                self.repeatCounter += 1
                                if(self.repeatCounter > 10):
                                    self.nozzleDetectionFailed()
                                    return
                                # loop through again
                                self.retries += 1
                                self.pollCoordinatesSignal.emit()
                                return
                            else:
                                # print('Took ' + str(self.repeatCounter) + ' attempts.')
                                self.repeatCounter = 0
                        # Calculate mpp at first move
                        if(self.state == 1):
                            self.mpp = np.around(0.5/self.getDistance(self.olduv[0],self.olduv[1],self.uv[0],self.uv[1]),3)
                        # save position as previous position
                        self.olduv = self.uv
                        # save machine coordinates for detected nozzle
                        self.space_coordinates.append((self.__currentPosition['X'], self.__currentPosition['Y']))
                        # save camera coordinates
                        self.camera_coordinates.append((self.uv[0],self.uv[1]))

                        # return carriage to relative center of movement
                        self.offsetX = (-1*self.offsetX)
                        self.offsetY = (-1*self.offsetY)
                        self.lastState = self.state
                        params = {'position':{'X': self.offsetX, 'Y': self.offsetY}}
                        self.moveRelativeSignal.emit(params)
                        return
                    # otherwise, move the carriage from the original position to the next step and increment state
                    else:
                        self.updateStatusbarMessage('Calibrating camera step ' + str(self.state) + '..')
                        _logger.debug('Step ' + str(self.state) + ' detection UV: ' + str(self.uv))
                        # move carriage to next calibration point
                        self.offsetX = self.calibrationCoordinates[self.state][0]
                        self.offsetY = self.calibrationCoordinates[self.state][1]
                        self.lastState = int(self.state)
                        self.state += 1
                        params = {'position':{'X': self.offsetX, 'Y': self.offsetY}}
                        self.moveRelativeSignal.emit(params)
                        return
                elif(self.state == len(self.calibrationCoordinates)):
                    # Camera calibration moves completed.
                    if(self.olduv is not None):
                        if(self.olduv[0] == self.uv[0] and self.olduv[1] == self.uv[1]):
                            # print('Repeating detection: ' + str(self.repeatCounter))
                            self.repeatCounter += 1
                            if(self.repeatCounter > 10):
                                self.nozzleDetectionFailed()
                                return
                            # loop through again
                            self.retries += 1
                            self.pollCoordinatesSignal.emit()
                            return
                        else:
                            # print('Took ' + str(self.repeatCounter) + ' attempts.')
                            self.repeatCounter = 0
                    # Update GUI thread with current status and percentage complete
                    updateMessage = 'Millimeters per pixel is ' + str(self.mpp)
                    self.updateStatusbarMessage(updateMessage)
                    _logger.info(updateMessage)
                    
                    # save position as previous position
                    self.olduv = self.uv
                    # save machine coordinates for detected nozzle
                    self.space_coordinates.append((self.__currentPosition['X'], self.__currentPosition['Y']))
                    # save camera coordinates
                    self.camera_coordinates.append((self.uv[0],self.uv[1]))
                    
                    # calculate camera transformation matrix
                    cameraCalibrationTime = np.around(time.time() - self.startTime,1)
                    _logger.info('Camera calibrated (' + str(cameraCalibrationTime) + 's); aligning..')
                    
                    # Calculate transformation matrix
                    self.transform_input = [(self.space_coordinates[i], self.normalize_coords(camera)) for i, camera in enumerate(self.camera_coordinates)]
                    self.transformMatrix, self.transform_residual = self.least_square_mapping(self.transform_input)
                    
                    # define camera center in machine coordinate space
                    self.newCenter = self.transformMatrix.T @ np.array([0, 0, 0, 0, 0, 1])
                    self.guessPosition[0]= np.around(self.newCenter[0],3)
                    self.guessPosition[1]= np.around(self.newCenter[1],3)
                    _logger.info('Calibration positional guess: ' + str(self.guessPosition))

                    # Set next calibration variables state
                    self.state = 200
                    self.retries = 0
                    self.calibrationMoves = 0

                    params = {'position':{'X': self.guessPosition[0], 'Y': self.guessPosition[1]}}
                    self.moveAbsoluteSignal.emit(params)
                    return
                elif(self.state == 200):
                    # Update GUI with current status
                    if(self.__stateEndstopAutoCalibrate):
                        updateMessage = 'Endstop calibration step ' + str(self.calibrationMoves) + '.. (MPP=' + str(self.mpp) +')'
                    else:
                        updateMessage = 'Tool ' + str(self.__activePrinter['currentTool']) + ' calibration step ' + str(self.calibrationMoves) + '.. (MPP=' + str(self.mpp) +')'
                    self.updateStatusbarMessage(updateMessage)
                    if(self.olduv is not None):
                        if(self.olduv[0] == self.uv[0] and self.olduv[1] == self.uv[1]):
                            # print('Repeating detection: ' + str(self.repeatCounter))
                            self.repeatCounter += 1
                            if(self.repeatCounter > 10):
                                print('Failed to detect.')
                                self.nozzleDetectionFailed()
                                return
                            # loop through again
                            print('Retrying', self.retries)
                            self.retries += 1
                            self.pollCoordinatesSignal.emit()
                            return
                        else:
                            # print('Took ' + str(self.repeatCounter) + ' attempts.')
                            self.repeatCounter = 0
                    # increment moves counter
                    self.calibrationMoves += 1
                    # nozzle detected, frame rotation is set, start
                    self.cx,self.cy = self.normalize_coords(self.uv)
                    self.v = [self.cx**2, self.cy**2, self.cx*self.cy, self.cx, self.cy, 0]
                    self.offsets = -1*(0.55*self.transformMatrix.T @ self.v)
                    self.offsets[0] = np.around(self.offsets[0],3)
                    self.offsets[1] = np.around(self.offsets[1],3)
                    _logger.info('*** State: ' + str(self.state) + ' retries: ' + str(self.retries) + ' X' + str(self.__currentPosition['X']) + ' Y' + str(self.__currentPosition['Y']) + ' UV: ' + str(self.uv) + ' old UV: ' + str(self.olduv) + ' Offsets: ' + str(self.offsets))
                    # Add rounding handling for endstop alignment
                    if(self.__stateEndstopAutoCalibrate):
                        if(abs(self.offsets[0])+abs(self.offsets[1]) <= 0.02):
                            self.offsets[0] = 0.0
                            self.offsets[1] = 0.0
                    
                    # Start timer if we're calibrating the CP using the automated endstop detection
                    try:
                        if(self.toolTime):
                            pass
                    except:
                        self.toolTime = time.time()

                    # calculate current calibration cycle runtime
                    runtime = np.around(time.time() - self.toolTime,1)
                    # check if too much time has passed
                    if(runtime > 120 or self.calibrationMoves > 30):
                        self.retries = 10
                    # Otherwise, check if we're not aligned to the center
                    elif(self.offsets[0] != 0.0 or self.offsets[1] != 0.0):
                        self.olduv = self.uv
                        params = {'position': {'X': self.offsets[0], 'Y': self.offsets[1]}, 'moveSpeed':1000}
                        self.moveRelativeSignal.emit(params)
                        _logger.debug('Calibration move X{0:-1.3f} Y{1:-1.3f} F1000 '.format(self.offsets[0],self.offsets[1]))
                        return
                    # finally, we're aligned to the center, and we should update the tool offsets
                    elif(self.offsets[0] == 0.0 and self.offsets[1] == 0.0):
                        # endstop calibration wrapping up
                        if(self.__stateEndstopAutoCalibrate):
                            updateMessage = 'Endstop auto-calibrated in ' + str(self.calibrationMoves) + ' steps. (MPP=' + str(self.mpp) +')'
                            # update state flags for endstop alignment
                            self.__stateAutoCPCapture = False
                            self.__stateEndstopAutoCalibrate = False
                            self.__stateManualCPCapture = False
                            # update detection manager state
                            self.toggleEndstopAutoDetectionSignal.emit(False)
                            # disable detection manager frame analysis
                            self.toggleDetectionSignal.emit(False)
                            self.__displayCrosshair = False
                            # Set CP location
                            self.__cpCoordinates['X'] = np.around(self.__currentPosition['X'],2)
                            self.__cpCoordinates['Y'] = np.around(self.__currentPosition['Y'],2)
                            self.__cpCoordinates['Z'] = np.around(self.__currentPosition['Z'],2)
                            # Update GUI statusbar with CP coordinates and green status
                            self.cpLabel.setText('<b>CP:</b> <i>('+ str(self.__cpCoordinates['X']) + ', ' + str(self.__cpCoordinates['Y']) + ')</i>')
                            self.cpLabel.setStyleSheet(self.styleGreen)
                            # Reset entire GUI for next state
                            self.stateCalibrateReady()
                            self.repaint()
                        # tool calibration wrapping up
                        elif(self.__stateAutoNozzleAlignment):
                            updateMessage = 'Tool ' + str(self.__activePrinter['currentTool']) + ' has been calibrated.'
                            self.state = 100
                            self.retries = 0
                        self.updateStatusbarMessage(updateMessage)
                        self.pollCoordinatesSignal.emit()
                        return
            elif(self.retries < 100 and runtime <= 120):
                self.retries += 1
                self.pollCoordinatesSignal.emit()
                return
        if(self.retries < 100):
            self.retries += 1
            # enable detection
            self.toggleDetectionSignal.emit(True)
            self.__displayCrosshair = True
            self.pollCoordinatesSignal.emit()
            return
        if(self.__stateEndstopAutoCalibrate is True):
            self.updateStatusbarMessage('Failed to detect endstop.')
            _logger.warning('Failed to detect endstop. Cancelled operation.')
            # if(self.originalPrinterPosition['X'] is not None and self.originalPrinterPosition['Y'] is not None):
                # params = {'moveSpeed':1000, 'position':{'X':self.originalPrinterPosition['X'],'Y':self.originalPrinterPosition['Y']}}
                # self.moveAbsoluteSignal.emit(params)
            # End calibration
            self.__stateAutoCPCapture = False
            self.__stateEndstopAutoCalibrate = False
            self.toggleEndstopAutoDetectionSignal.emit(False)
            self.haltCPAutoCapture()
            self.pollCoordinatesSignal.emit()
        elif(self.__stateAutoNozzleAlignment is True):
            updateMessage = 'Failed to detect nozzle. Try manual override.'
            self.updateStatusbarMessage(updateMessage)
            _logger.warning(updateMessage)
            self.nozzleDetectionFailed()

    def nozzleDetectionFailed(self):
        self.state = -99
        # End auto calibration
        self.__stateAutoNozzleAlignment = False
        self.__stateManualNozzleAlignment = True
        # calibrating nozzle manual
        self.tabPanel.setDisabled(False)
        self.alignToolsButton.setVisible(False)
        self.alignToolsButton.setDisabled(True)
        self.manualToolOffsetCaptureButton.setVisible(True)
        self.manualToolOffsetCaptureButton.setDisabled(False)
        self.manualToolOffsetCaptureButton.setStyleSheet(self.styleBlue)
        self.resumeAutoToolAlignmentButton.setVisible(True)
        self.resumeAutoToolAlignmentButton.setDisabled(False)
        self.resumeAutoToolAlignmentButton.setStyleSheet(self.styleGreen)
        self.toggleNozzleAutoDetectionSignal.emit(False)
        self.toggleNozzleDetectionSignal.emit(True)
        self.toggleDetectionSignal.emit(True)
        self.__displayCrosshair = True

    def resumeAutoAlignment(self):
        if(self.transformMatrix is None or self.mpp is None):
            self.state = 0
        elif(len(self.transformMatrix) < 6):
            self.transformMatrix = None
            self.mpp = None
            self.state = 0
        else:
            self.state = 200
        self.retries = 0
        self.repeatCounter = 0
        self.uv = [None, None]
        self.olduv = [None, None]
        self.__stateAutoNozzleAlignment = True
        self.toolTime = time.time()
        self.resumeAutoToolAlignmentButton.setVisible(False)
        self.resumeAutoToolAlignmentButton.setDisabled(True)
        self.resumeAutoToolAlignmentButton.setStyleSheet(self.styleDisabled)
        self.updateStatusbarMessage('Resuming auto detection of current tool..')
        self.toggleNozzleAutoDetectionSignal.emit(True)
        self.pollCoordinatesSignal.emit()

    ########################################################################### Module interfaces and handlers
    ########################################################################### Interface with Detection Manager
    def createDetectionManagerThread(self, announce=True):
        if(announce):
            _logger.info('  .. starting Detection Manager.. ')
        # Thread setup
        self.detectionThread = QThread()
        self.detectionManager = DetectionManager(videoSrc=self._videoSrc, width=self._cameraWidth, height=self._cameraHeight, parent=None)
        self.detectionManager.moveToThread(self.detectionThread)
        
        # Thread management signals and slots
        self.detectionManager.errorSignal.connect(self.detectionManagerError)
        self.detectionThread.started.connect(self.detectionManager.processFrame)
        self.detectionThread.finished.connect(self.detectionManager.quit)
        self.detectionThread.finished.connect(self.detectionManager.deleteLater)
        self.detectionThread.finished.connect(self.detectionThread.deleteLater)
        self.detectionThread.start()#priority=QThread.TimeCriticalPriority)
        # Video frame signals and slots
        self.detectionManager.detectionManagerNewFrameSignal.connect(self.refreshImage)
        self.detectionManager.detectionManagerReadySignal.connect(self.startVideo)
        self.getVideoFrameSignal.connect(self.detectionManager.processFrame)
        # Camera image properties signals and slots
        self.setImagePropertiesSignal.connect(self.detectionManager.relayImageProperties)
        self.resetImageSignal.connect(self.detectionManager.relayResetImage)
        # Endstop alignment signals and slots
        self.toggleEndstopDetectionSignal.connect(self.detectionManager.toggleEndstopDetection)
        self.toggleEndstopAutoDetectionSignal.connect(self.detectionManager.toggleEndstopAutoDetection)
        # Nozzle alignment signals and slots
        self.toggleNozzleDetectionSignal.connect(self.detectionManager.toggleNozzleDetection)
        self.toggleNozzleAutoDetectionSignal.connect(self.detectionManager.toggleNozzleAutoDetection)
        # UV coordinates update signals and slots
        self.getUVCoordinatesSignal.connect(self.detectionManager.sendUVCoorindates)
        self.detectionManager.detectionManagerUVCoordinatesSignal.connect(self.saveUVCoordinates)
        # Master detection swtich enable/disable
        self.toggleDetectionSignal.connect(self.detectionManager.enableDetection)

    @pyqtSlot(object)
    def startVideo(self, cameraProperties):
        # send calling to log
        _logger.debug('*** calling App.startVideo')
        # capture camera properties
        self.__activeCamera = cameraProperties
        self.startVideoSignal.emit()
        # send exiting to log
        _logger.debug('*** exiting App.startVideo')

    @pyqtSlot(object)
    def refreshImage(self, data):
        self.__mutex.lock()
        frame = data[0]
        # uvCoordinates = data[1]
        self.image.setPixmap(frame)
        # if(self.__stateEndstopAutoCalibrate is True or self.__stateAutoNozzleAlignment is True):
        #     self.uv = uvCoordinates
        self.__mutex.unlock()
        self.getVideoFrameSignal.emit()

    @pyqtSlot(object)
    def updateStatusbarMessage(self, message):
        self.__mutex.lock()
        # send calling to log
        _logger.debug('*** calling App.updateStatusbarMessage')
        try:
            self.statusBar.showMessage(message)
            self.statusBar.setStyleSheet('')
        except:
            errorMsg = 'Error sending message to statusbar.'
            _logger.error(errorMsg)
        self.__mutex.unlock()
        app.processEvents()
        # send exiting to log
        _logger.debug('*** exiting App.updateStatusbarMessage')

    @pyqtSlot(object)
    def detectionManagerError(self, message):
        self.haltPrinterOperation(silent=True)
        self.__mutex.lock()
        try:
            self.statusBar.showMessage(message)
            self.statusBar.setStyleSheet(self.styleRed)
            self.cpLabel.setStyleSheet(self.styleOrange)
            self.connectionStatusLabel.setStyleSheet(self.styleOrange)
            self.resetCalibration()
            self.__mutex.unlock()
            self.moveAbsoluteSignal.emit(self.originalPrinterPosition)
        except:
            self.__mutex.unlock()
            errorMsg = 'Error sending message to statusbar.'
            _logger.error(errorMsg)
        
        # Kill thread
        self.detectionThread.quit()
        self.detectionThread.wait()
        self.printerThread.quit()
        self.printerThread.wait()
        # display error image
        self.image.setPixmap(self.errorImage)

    ########################################################################### Interface with Printer Manager
    def createPrinterManagerThread(self,announce=True):
        if(announce):
            _logger.info('  .. starting Printer Manager.. ')
        try:
            self.printerManager = PrinterManager(parent=None, firmwareList=self.__firmwareList, driverList=self.__driverList)
            self.printerThread = QThread()
            self.printerManager.moveToThread(self.printerThread)
            
            self.printerManager.errorSignal.connect(self.printerError)
            # self.printerManager.printerDisconnectedSignal.connect(self.printerThread.quit)
            # self.printerManager.printerDisconnectedSignal.connect(self.printerManager.deleteLater)
            self.printerThread.finished.connect(self.printerManager.quit)
            self.printerThread.finished.connect(self.printerManager.deleteLater)
            self.printerThread.finished.connect(self.printerThread.deleteLater)
            
            # PrinterManager object signals
            self.printerManager.updateStatusbarSignal.connect(self.updateStatusbarMessage)
            self.printerManager.activePrinterSignal.connect(self.printerConnected)
            self.printerManager.printerDisconnectedSignal.connect(self.printerDisconnected)
            self.connectSignal.connect(self.printerManager.connectPrinter)
            self.disconnectSignal.connect(self.printerManager.disconnectPrinter)
            
            self.moveRelativeSignal.connect(self.printerManager.moveRelative)
            self.moveAbsoluteSignal.connect(self.printerManager.moveAbsolute)
            self.printerManager.moveCompleteSignal.connect(self.printerMoveComplete)
            
            self.pollCoordinatesSignal.connect(self.printerManager.getCoordinates)
            self.printerManager.coordinatesSignal.connect(self.saveCurrentPosition)

            self.callToolSignal.connect(self.printerManager.callTool)
            self.unloadToolSignal.connect(self.printerManager.unloadTools)
            self.printerManager.toolLoadedSignal.connect(self.toolLoaded)
            self.pollCurrentToolSignal.connect(self.printerManager.currentTool)
            self.printerManager.toolIndexSignal.connect(self.registerActiveTool)

            self.printerManager.offsetsSetSignal.connect(self.calibrateOffsetsApplied)
            self.setOffsetsSignal.connect(self.printerManager.calibrationSetOffset)
            
            self.printerThread.start()#priority=QThread.TimeCriticalPriority)
        except Exception as e:
            print(e)
            errorMsg = 'Failed to start PrinterManager.'
            _logger.critical(errorMsg)
            self.printerError(errorMsg)

    def connectPrinter(self):
        self.connectButton.setStyleSheet(self.styleDisabled)
        self.connectButton.setDisabled(True)
        self.preferencesAction.setDisabled(True)
        self.statusBar.setStyleSheet("")
        self.connectionStatusLabel.setText('<i>Connecting..</i>')
        self.connectionStatusLabel.setStyleSheet(self.styleBlue)
        self.repaint()
        try:
            if(self.printerThread.isRunning() is False):
                self.createPrinterManagerThread(announce=False)
        except: self.createPrinterManagerThread(announce=False)
        self.connectSignal.emit(self.__activePrinter)

    def haltPrinterOperation(self, **kwargs):
        try:
            silent = kwargs['silent']
        except: silent = False
        # disconnect button
        self.disconnectButton.setStyleSheet(self.styleDisabled)
        self.disconnectButton.setDisabled(True)
        # Cancel CP Capture
        if(self.__stateAutoCPCapture is True or self.__stateEndstopAutoCalibrate is True or self.__stateSetupCPCapture is True):
            self.haltCPAutoCapture()
            return
        # Cancel Nozzle Detection
        if(self.__stateAutoNozzleAlignment is True or self.__stateManualNozzleAlignment is True):
            self.haltNozzleCapture()
            return
        # Disconnect from printer
        # Status label
        self.connectionStatusLabel.setText('<i>Disconnecting..</i>')
        self.connectionStatusLabel.setStyleSheet(self.styleBlue)
        # Setup CP button
        self.cpSetupButton.setStyleSheet(self.styleDisabled)
        self.cpSetupButton.setDisabled(True)
        # CP Automated Capture button
        self.cpAutoCaptureButton.setDisabled(True)
        self.cpAutoCaptureButton.setStyleSheet(self.styleDisabled)
        # Jog panel
        self.tabPanel.setDisabled(True)
        self.repaint()
        params = {}
        if(silent):
            params['noUpdate'] = True
        else:
            params['noUpdate'] = False
        # restore position
        if(self.__cpCoordinates['X'] is not None and self.__cpCoordinates['Y'] is not None):
            _logger.debug('Restoring to CP position..')
            params['parkPosition'] = self.__cpCoordinates
            self.disconnectSignal.emit(params)
        elif(self.__restorePosition is not None):
            _logger.debug('Restoring to master restore position..')
            params['parkPosition'] = self.__restorePosition
            self.disconnectSignal.emit(params)
        else:
            self.disconnectSignal.emit(params)
        self.resetCalibrationVariables()
        self.updateStatusbarMessage('Printer disconnected.')

    @pyqtSlot(object)
    def printerConnected(self, printerJSON):
        self.__mutex.lock()
        # send calling to log
        _logger.debug('*** calling App.printerConnected')
        self.__activePrinter = printerJSON
        # Status label
        self.connectionStatusLabel.setText(self.__activePrinter['nickname'] + ' [' + self.__activePrinter['controller'] + ' v' + self.__activePrinter['version'] + ']')
        self.connectionStatusLabel.setStyleSheet(self.styleGreen)
        # poll for position
        self.__firstConnection = True
        self.__mutex.unlock()
        self.pollCoordinatesSignal.emit()
        # Gui state
        self.stateConnected()
        self.repaint()
        # send exiting to log
        _logger.debug('*** exiting App.printerConnected')

    @pyqtSlot(object)
    def printerDisconnected(self, **kwargs):
        self.__mutex.lock()
        try:
            message = kwargs['message']
        except: message = None
        # send calling to log
        _logger.debug('*** calling App.printerDisconnected')
        # update status bar
        if(message is not None): 
            self.statusBar.showMessage(message)
            self.statusBar.setStyleSheet("")
        # CP Label
        self.cpLabel.setText('<b>CP:</b> <i>undef</i>')
        self.cpLabel.setStyleSheet(self.styleOrange)
        # Status label
        self.connectionStatusLabel.setText('Disconnected')
        self.connectionStatusLabel.setStyleSheet(self.styleOrange)
        self.__mutex.unlock()
        self.stateDisconnected()
        self.repaint()
        # send exiting to log
        _logger.debug('*** exiting App.printerDisconnected')
        

    @pyqtSlot(object)
    def printerError(self, message):
        _logger.debug('Printer Error: ' + message)
        if(self.__restorePosition is not None):
            params = {'parkPosition': self.__restorePosition}
            self.disconnectSignal.emit(params)
        else:
            self.disconnectSignal.emit(None)
        # Kill printer thread
        try:
            self.printerThread.quit()
            self.printerThread.wait()
        except: _logger.warning('Printer thread not created yet.')
        self.printerDisconnected(message=message)
        self.statusBar.setStyleSheet(self.styleRed)

    def callTool(self, toolNumber=-1):
        # disable detection
        self.toggleDetectionSignal.emit(False)
        self.__displayCrosshair = False
        toolNumber = int(toolNumber)
        if(toolNumber == -1):
            self.unloadToolSignal.emit()
            return
        try:
            self.callToolSignal.emit(toolNumber)
        except:
            errorMsg = 'Unable to call tool from printer: ' + str(toolNumber)
            _logger.error(errorMsg)
            self.printerError(errorMsg)

    @pyqtSlot()
    def toolLoaded(self):
        self.pollCurrentToolSignal.emit()
        if(self.__cpCoordinates['X'] is not None and self.__cpCoordinates['Y'] is not None):
            params = {'protected':True,'moveSpeed': 5000, 'position':{'X': self.__cpCoordinates['X'], 'Y': self.__cpCoordinates['Y'], 'Z': self.__cpCoordinates['Z']}}
        else:
            params = {'protected':True,'moveSpeed': 5000, 'position':{'X': self.__currentPosition['X'], 'Y': self.__currentPosition['Y'], 'Z': self.__currentPosition['Z']}}
        self.moveAbsoluteSignal.emit(params)

    @pyqtSlot(int)
    def registerActiveTool(self, toolIndex):
        self.__mutex.lock()
        self.__activePrinter['currentTool'] = toolIndex
        for button in self.toolButtons:
            if(button.objectName() != ('toolButton_'+str(toolIndex))):
                button.setChecked(False)
            else:
                button.setChecked(True)
        self.__mutex.unlock()

    @pyqtSlot()
    def printerMoveComplete(self):
        self.tabPanel.setDisabled(False)
        if(self.__stateAutoCPCapture and self.__stateEndstopAutoCalibrate):
            # enable detection
            self.toggleDetectionSignal.emit(True)
            self.__displayCrosshair = True
            statusMsg = '(Endstop auto detection active.)'
            self.updateStatusbarMessage(statusMsg)
            _logger.debug(statusMsg)
            # Calibrating camera, go based on state
            self.tabPanel.setDisabled(True)
        elif(self.__stateAutoNozzleAlignment is True):
            # enable detection
            self.toggleDetectionSignal.emit(True)
            self.__displayCrosshair = True
            statusMsg = '(Tool/nozzle auto detection active.)'
            self.updateStatusbarMessage(statusMsg)
            _logger.debug(statusMsg)
            # calibrating nozzle auto
            self.tabPanel.setDisabled(True)
        elif(self.__stateManualNozzleAlignment is True):
            # enable detection
            self.toggleDetectionSignal.emit(True)
            self.__displayCrosshair = True
            statusMsg = '(Tool/nozzle manual override active.)'
            self.updateStatusbarMessage(statusMsg)
            _logger.debug(statusMsg)
            # calibrating nozzle manual
            self.alignToolsButton.setVisible(False)
            self.alignToolsButton.setDisabled(True)
            self.manualCPCaptureButton.setVisible(True)
            return
        elif(self.__stateManualCPCapture is True):
            statusMsg = '(Endstop/CP manual override active.)'
            self.updateStatusbarMessage(statusMsg)
            _logger.debug(statusMsg)
        else:
            statusMsg = 'Ready.'
            self.updateStatusbarMessage(statusMsg)
            _logger.debug(statusMsg)
        self.pollCoordinatesSignal.emit()

    @pyqtSlot(object)
    def saveUVCoordinates(self, uvCoordinates):
        print('Received UV:', uvCoordinates)
        if(uvCoordinates is None):
            # failed to detect, poll coordinates again
            self.pollCoordinatesSignal.emit()
            return
        self.uv = uvCoordinates
        self.autoCalibrate()

    @pyqtSlot(object)
    def saveCurrentPosition(self, coordinates):
        self.__mutex.lock()
        self.__currentPosition = coordinates
        self.__mutex.unlock()
        _logger.debug('Coordinates received:' + str(coordinates))
        self.toggleDetectionSignal.emit(True)
        self.__displayCrosshair = True
        if(self.__stateManualCPCapture is True):
            _logger.debug('saveCurrentPosition: manual CP capture')
            self.__cpCoordinates = coordinates
            self.__stateManualCPCapture = False
            self.cpLabel.setText('<b>CP:</b> <i>('+ str(self.__cpCoordinates['X']) + ', ' + str(self.__cpCoordinates['Y']) + ')</i>')
            self.cpLabel.setStyleSheet(self.styleGreen)
            self.updateStatusbarMessage('CP captured.')
            self.repaint()
        elif(self.__stateEndstopAutoCalibrate is True or self.__stateAutoNozzleAlignment is True):
            if(self.state != 100):
                if(int(self.__activePrinter['currentTool']) > -1):
                    _logger.debug('saveCurrentPosition: autoCalibrate nozzle for T' + str(int(self.__activePrinter['currentTool'])))
                else:
                    _logger.debug('saveCurrentPosition: autoCalibrate endstop.')
            elif(self.state == 100):
                _logger.debug('saveCurrentPosition: autoCalibrate nozzle set offsets for T' + str(int(self.__activePrinter['currentTool'])))
                # set state to detect next tool
                self.state = 200
                self.__stateAutoNozzleAlignment = True
                self.toggleNozzleAutoDetectionSignal.emit(True)
                params={'toolIndex': int(self.__activePrinter['currentTool']), 'position': coordinates, 'cpCoordinates': self.__cpCoordinates}
                self.setOffsetsSignal.emit(params)
                return
            self.getUVCoordinatesSignal.emit()
        elif(self.__stateManualNozzleAlignment is True):
            _logger.debug('saveCurrentPosition: manual nozzle set offsets for T' + str(int(self.__activePrinter['currentTool'])))
            # set state to detect next tool
            self.state = 200
            self.__stateAutoNozzleAlignment = True
            self.toggleNozzleAutoDetectionSignal.emit(True)
            params={'toolIndex': int(self.__activePrinter['currentTool']), 'position': coordinates, 'cpCoordinates': self.__cpCoordinates}
            self.setOffsetsSignal.emit(params)
            return
        elif(self.__firstConnection):
            _logger.debug('saveCurrentPosition: firstConnection')
            self.__restorePosition = copy.deepcopy(self.__currentPosition)
            self.__firstConnection = False

    @pyqtSlot(object)
    def calibrateOffsetsApplied(self, params=None):
        try:
            offsets = params['offsets']
        except: offsets = None
        if(offsets is not None):
            toolCalibrationTime = np.around(time.time() - self.toolTime,1)
            successMsg = 'Tool ' + str(self.__activePrinter['currentTool']) + ': (X' + str(offsets['X']) + ', Y' + str(offsets['Y']) + ', Z' + str(offsets['Z']) + ') -- [' + str(toolCalibrationTime) + 's].'
            self.updateStatusbarMessage(successMsg)
            _logger.info(successMsg)
            self.state = 200
            self.retries = 0
            self.__stateAutoNozzleAlignment = True
            self.toggleNozzleAutoDetectionSignal.emit(True)
            self.calibrateTools(self.workingToolset)
        else:
            raise SystemExit('FUCKED!')

    ########################################################################### Interface with Settings Dialog
    def displayPreferences(self, event=None, newPrinterFlag=False):
        _logger.debug('*** calling App.displayPreferences')
        # check if we already have a printer manager thread, and start it
        try:
            if(self.printerThread.isRunning() is False):
                self.createPrinterManagerThread(announce=False)
        except: self.createPrinterManagerThread(announce=False)
        # Set up settings window
        try:
            self.settingsDialog = SettingsDialog(parent=self, newPrinter=newPrinterFlag, geometry=self.__settingsGeometry, settings=self.__userSettings, firmwareList=self.__firmwareList, cameraProperties=self.__activeCamera)
            # # Signals
            # self.settingsDialog.settingsAlignmentPollSignal.connect()
            # self.settingsDialog.settingsChangeVideoSrcSignal.connect()
            # self.settingsDialog.settingsRequestCameraProperties.connect()
            # self.settingsDialog.settingsRequestImageProperties.connect()
            self.settingsDialog.settingsResetImageSignal.connect(self.relayResetCameraDefaults)
            self.settingsDialog.settingsSetImagePropertiesSignal.connect(self.relayImageParameters)
            self.settingsDialog.settingsUpdateSignal.connect(self.updateSettings)
            self.settingsDialog.settingsStatusbarSignal.connect(self.updateStatusbarMessage)
            self.settingsDialog.settingsGeometrySignal.connect(self.saveSettingsGeometry)
            self.settingsDialog.rejected.connect(self.settingsDialog.deleteLater)
            self.settingsDialog.accepted.connect(self.settingsDialog.deleteLater)
            self.settingsDialog.settingsNewPrinter.connect(self.saveNewPrinter)
            
        except:
            errorMsg = 'Cannot start settings dialog.'
            _logger.exception(errorMsg)
            return
        # self.settingsDialog.update_settings.connect(self.updateSettings)
        self.settingsDialog.exec()
        
        _logger.debug('*** exiting App.displayPreferences')

    @pyqtSlot(object)
    def relayImageParameters(self, imageProperties):
        self.setImagePropertiesSignal.emit(imageProperties)

    @pyqtSlot()
    def relayResetCameraDefaults(self):
        self.resetImageSignal.emit()

    @pyqtSlot(object)
    def updateSettings(self, settingOptions):
        _logger.debug('*** calling App.updateSettings')
        self.__userSettings = settingOptions
        self.saveUserSettings()
        _logger.debug('*** exiting App.updateSettings')

    @pyqtSlot(object)
    def saveNewPrinter(self, newSettingsOptions):
        self.__userSettings = newSettingsOptions
        self.saveUserSettings()
        newPrinterIndex = len(newSettingsOptions['printer'])-1
        self.__activePrinter = newSettingsOptions['printer'][newPrinterIndex]
        self.connectSignal.emit(self.__activePrinter)

    @pyqtSlot(object)
    def saveSettingsGeometry(self, geometry):
        self.__settingsGeometry = geometry

    ########################################################################### Utilities
    def sanitizeURL(self, inputString='http://localhost'):
        _logger.debug('*** calling App.sanitizeURL')
        _errCode = 0
        _errMsg = ''
        _printerURL = 'http://localhost'
        from urllib.parse import urlparse
        u = urlparse(inputString)
        scheme = u[0]
        netlocation = u[1]
        if len(scheme) < 4 or scheme.lower() not in ['http']:
            _errCode = 1
            _errMsg = 'Invalid scheme. Please only use http connections.'
        elif len(netlocation) < 1:
            _errCode = 2
            _errMsg = 'Invalid IP/network address.'
        elif scheme.lower() in ['https']:
            _errCode = 3
            _errMsg = 'Cannot use https connections for Duet controllers'
        else:
            _printerURL = scheme + '://' + netlocation
        _logger.debug('*** exiting App.sanitizeURL')
        return(_errCode, _errMsg, _printerURL)

    def saveUserSettings(self):
        # save user settings.json
        _logger.debug('*** calling App.saveUserSettings')
        try:
            # get default camera from user settings
            cameraSet = False
            # new_video_src = 0
            # for camera in self.__userSettings['camera']:
            #     try:
            #         if(camera['default'] == 1 and cameraSet is False):
            #             # if new default, switch feed
            #             if(self._videoSrc != new_video_src):
            #                 new_video_src = camera['video_src']
            #                 self.video_thread.changeVideoSrc(newSrc=new_video_src)
            #                 self._videoSrc = new_video_src
            #             cameraSet = True
            #             continue
            #         elif(cameraSet):
            #             # already have a default, unset other entries
            #             camera['default'] = 0
            #     except KeyError:
            #         # No default camera defined, add key
            #         camera['default'] = 0
            #         continue
            # check if there are no cameras set as default
            if(cameraSet is False):
                # Set first camera entry to be the default source
                self.__userSettings['camera'][0]['default'] = 1
                # try: 
                #     # activate default camera feed
                #     self.video_thread.changeVideoSrc(newSrc=new_video_src)
                #     self._videoSrc = new_video_src
                # except:
                #     _logger.critical('Cannot load default camera source.')
            # Save settings to file
            with open('./config/settings.json','w') as outputfile:
                json.dump(self.__userSettings, outputfile)
            _logger.info('User preferences saved to settings.json')
            self.updateStatusbarMessage('User preferences saved to settings.json')
            self.statusBar.setStyleSheet('')
        except Exception as e1:
            _logger.error('Error saving user settings file.' + str(e1))
            self.statusBar.showMessage('Error saving user settings file.')
            self.statusBar.setStyleSheet(self.styleRed)
        _logger.debug('*** exiting App.saveUserSettings')

    def getDistance(self, x1, y1, x0, y0):
        _logger.debug('*** calling CalibrateNozzles.getDistance')
        x1_float = float(x1)
        x0_float = float(x0)
        y1_float = float(y1)
        y0_float = float(y0)
        x_dist = (x1_float - x0_float) ** 2
        y_dist = (y1_float - y0_float) ** 2
        retVal = np.sqrt((x_dist + y_dist))
        returnVal = np.around(retVal,3)
        _logger.debug('*** exiting CalibrateNozzles.getDistance')
        return(returnVal)

    def normalize_coords(self,coords):
        xdim, ydim = self._cameraWidth, self._cameraHeight
        returnValue = (coords[0] / xdim - 0.5, coords[1] / ydim - 0.5)
        return(returnValue)

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

    def toggleCrosshair(self):
        if(self.__stateAutoCPCapture is False and self.__stateAutoNozzleAlignment is False and self.__stateEndstopAutoCalibrate is False):
            if(self.__displayCrosshair is False):
                self.crosshairDisplayButton.setChecked(True)
                self.crosshairDisplayButton.setStyleSheet(self.styleOrange)
                self.__displayCrosshair = True
                self.toggleNozzleDetectionSignal.emit(True)
                self.toggleDetectionSignal.emit(True)
                self.__displayCrosshair = True
            else:
                self.crosshairDisplayButton.setChecked(False)
                self.crosshairDisplayButton.setStyleSheet(self.styleBlue)
                self.__displayCrosshair = False
                self.toggleNozzleDetectionSignal.emit(False)
                self.toggleDetectionSignal.emit(False)
                self.__displayCrosshair = False

    ########################################################################### Close application handler
    def closeEvent(self, event):
        _logger.debug('*** calling App.closeEvent')
        self.stateExiting()
        try:
            _logger.info('Closing TAMV..')
            self.statusBar.showMessage('Shutting down TAMV..')
            self.repaint()
            try:
                self.detectionThread.quit()
                self.detectionThread.wait()
            except: pass
            try:
                self.printerThread.quit()
                self.printerThread.wait()
            except: pass
        except Exception:
            _logger.critical('Close event error: \n' + traceback.format_exc())
        # Output farewell message
        print()
        print('Thank you for using TAMV!')
        print('Check out www.jubilee3d.com')
        _logger.debug('*** exiting App.closeEvent')
        super(App, self).closeEvent(event)

    ########################################################################### First run setups
    def show(self):
        self.createDetectionManagerThread()
        self.createPrinterManagerThread()
        _logger.info('Initialization complete.')
        # Output welcome message
        print()
        print('  Welcome to TAMV!')
        print()
        super().show()

if __name__=='__main__':
    ### Setup OS options
    # os.putenv("QT_LOGGING_RULES","qt5ct.debug=true")
    os.putenv("OPENCV_VIDEOIO_DEBUG", "0")
    # os.putenv("OPENCV_VIDEOIO_PRIORITY_LIST", "DSHOW,FFMPEG,GSTREAMER")
    ### Setup argmument parser
    parser = argparse.ArgumentParser(description='Program to allign multiple tools on Duet/klipper based printers, using machine vision.', allow_abbrev=False)
    parser.add_argument('-d','--debug',action='store_true',help='Enable debug output to terminal')
    # Execute argument parser
    args=vars(parser.parse_args())
    
    ### Setup logging
    _logger = logging.getLogger("TAMV")
    _logger.setLevel(logging.DEBUG)
    ### # file handler logging
    fileFormatter = logging.Formatter('%(asctime)s --- %(levelname)s --- M:%(name)s --- T:%(threadName)s --- F:%(funcName)s --- L:%(lineno)d --- %(message)s')
    # migrate logs to /log path
    try:
        os.makedirs('./log', exist_ok=True)
    except:
        print()
        print('Cannot create \"./log folder.')
        print('Please create this folder manually and restart TAMV')
        raise SystemExit('Cannot retrieve log path.')
    if(os.path.exists('./TAMV.log')):
        if(os.path.exists('./log/TAMV.log')):
            print()
            print('Deleting old log file ./TAMV.log..')
            try:
                os.remove('./TAMV.log')
            except:
                print('Cannot delete old log file \"./TAMV.log\", ignoring it..')
                print('Log file now located in \"./log/TAMV.log\"')
        else:
            try:
                print()
                print('Moving log file to \"./log/TAMV.log\"..')
                os.replace('./TAMV.log','./log/TAMV.log')
            except:
                print('Unknown OS error while moving log file to new folder.')
                print('Please move \"./TAMV.log\" to \"./log/TAMV.log\" and restart TAMV.')
                raise SystemExit('Cannot move log file.')
    fh = RotatingFileHandler('./log/TAMV.log',backupCount=1,maxBytes=1000000)
    if(args['debug']):
        fh.setLevel(logging.DEBUG)
    else:
        fh.setLevel(logging.INFO)
    fh.setFormatter(fileFormatter)
    _logger.addHandler(fh)
    ### # console handler logging
    consoleFormatter = logging.Formatter(fmt='%(levelname)-9s: %(message)s')
    ch = logging.StreamHandler()
    if(args['debug']):
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
    ch.setFormatter(consoleFormatter)
    _logger.addHandler(ch)
    
    ### # log startup messages
    print()
    _logger.warning('This is an alpha release. Always use only when standing next to your machine and ready to hit EMERGENCY STOP.')
    print()

    ### start GUI application
    app = QApplication(sys.argv)
    a = App()
    a.show()
    sys.exit(app.exec())
