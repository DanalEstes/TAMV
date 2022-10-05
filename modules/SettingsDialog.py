import logging
from sys import stdout
# invoke parent (TAMV) _logger
_logger = logging.getLogger('TAMV.SettingsDialog')

from cv2 import cvtColor, COLOR_BGR2RGB
from PyQt5.QtWidgets import * #QDialog, QWidget, QVBoxLayout, QTabWidgetQ, QPushButton, QComboBox, QSlider, QLabel
from PyQt5.QtCore import *
import traceback, copy

# Configuration settings dialog box
class SettingsDialog(QDialog):
    # Signals
    settingsAlignmentPollSignal = pyqtSignal()
    settingsChangeVideoSrcSignal = pyqtSignal(object)
    settingsGeometrySignal = pyqtSignal(object)
    settingsRequestCameraPropertiesSignal = pyqtSignal()
    settingsRequestImagePropertiesSignal = pyqtSignal()
    settingsResetImageSignal = pyqtSignal()
    settingsSetImagePropertiesSignal = pyqtSignal(object)
    settingsRequestDefaultImagePropertiesSignal = pyqtSignal()
    settingsStatusbarSignal = pyqtSignal(object)
    settingsUpdateSignal = pyqtSignal(object)
    settingsNewPrinter = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        # send calling to log
        _logger.debug('*** calling SettingsDialog.__init__')
        try:
            self.__parent = kwargs['parent']
        except KeyError:
            self.__parent = None
        try:
            self.__newPrinter = kwargs['newPrinter']
        except KeyError:
            self.__newPrinter = False
        try:
            self.__geometry = kwargs['geometry']
        except KeyError:
            self.__geometry = None
        try:
            self.__settings = copy.deepcopy(kwargs['settings'])
            self.__originalSettingsObject = kwargs['settings']
        except KeyError:
            self.__settings = None
            self.__originalSettingsObject = None
        try:
            self.__cameraProperties = kwargs['cameraProperties']
        except KeyError:
            self.__cameraProperties = None
        try:
            self.__firmwareList = kwargs['firmwareList']
        except KeyError:
            self.__firmwareList = None
        
        
        # Set up settings window
        super(SettingsDialog,self).__init__(parent=self.__parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
        self.setWindowTitle('TAMV Configuration Settings')
        # Restore geometry if available
        if(self.__geometry is not None):
            self.restoreGeometry(self.__geometry)
        # Set layout details
        self.layout = QVBoxLayout()
        self.layout.setSpacing(3)
        ############# TAB SETUP #############
        # Create tabs layout
        self.tabs = QTabWidget()
        # Tab 1: Settings
        self.settingsTab = QWidget()
        self.settingsTab.layout = QVBoxLayout()
        self.settingsTab.setLayout(self.settingsTab.layout)
        # Tab 2: Cameras
        self.camerasTab = QWidget()
        self.camerasTab.layout = QVBoxLayout()
        self.camerasTab.setLayout(self.camerasTab.layout)
        # add tabs to tabs layout
        self.tabs.addTab(self.settingsTab, 'Machines')
        if(self.__newPrinter is False):
            self.tabs.addTab(self.camerasTab, 'Cameras')
        # Add tabs layout to window
        self.layout.addWidget(self.tabs)
        # apply layout
        self.setLayout(self.layout)
        ############# POPULATE TABS
        # Create camera items
        if(self.__newPrinter is False):
            self.createCameraItems()
        # Create machine items
        self.createMachineItems()
        ############# MAIN BUTTONS
        # Save button
        if(self.__newPrinter is False):
            self.save_button = QPushButton('Save')
            self.save_button.setToolTip('Save current parameters to settings.json file')
            self.save_button.clicked.connect(self.updatePrinterObjects)
        else:
            self.save_button = QPushButton('Save and connect..')
            self.save_button.clicked.connect(self.saveNewPrinter)
        self.save_button.setObjectName('active')
        # Close button
        self.close_button = QPushButton('Cancel')
        self.close_button.setToolTip('Cancel changes and return to main program.')
        self.close_button.clicked.connect(self.cancelChanges)
        self.close_button.setObjectName('terminate')
        # WINDOW BUTTONS
        self.layout.addWidget(self.save_button)
        self.layout.addWidget(self.close_button)
        # OK Cancel buttons
        #self.layout.addWidget(self.buttonBox)
        _logger.debug('*** exiting SettingsDialog.__init__')
    
    def createCameraItems(self):
        _logger.debug('*** calling SettingsDialog.createCameraItems')
        ############# CAMERAS TAB #############
        # Get current camera settings from video thread
        try:
            if(self.__cameraProperties['image'] is not None):
                try:
                    brightness_input = self.__cameraProperties['image']['brightness']
                except KeyError: 
                    brightness_input = None
                try:
                    contrast_input = self.__cameraProperties['image']['contrast']
                except KeyError: 
                    contrast_input = None
                try:
                    saturation_input = self.__cameraProperties['image']['saturation']
                except KeyError: 
                    saturation_input = None
                try:
                    hue_input = self.__cameraProperties['image']['hue']
                except KeyError: 
                    hue_input = None
        except KeyError:
            (brightness_input, contrast_input, saturation_input, hue_input) = (None, None, None, None)
        except Exception:
            errorMsg = 'Error fetching camera parameters.'
            self.settingsStatusbarSignal.emit(errorMsg)
            _logger.error('Error fetching camera parameters.\n' + traceback.format_exc())
        ############# CAMERA TAB: ITEMS
        # Camera Combobox
        self.camera_combo = QComboBox()
        for camera in self.__settings['camera']:
            if(camera['default'] == 1):
                camera_description = '* ' + str(camera['video_src']) + ': ' + str(camera['display_width']) + 'x' + str(camera['display_height']) 
            else:
                camera_description = str(camera['video_src']) + ': ' + str(camera['display_width']) + 'x' + str(camera['display_height']) 
            self.camera_combo.addItem(camera_description)
        #HBHBHBHB: TODO need to pass actual video source string object from parameter helper function!!!
        #self.camera_combo.currentIndexChanged.connect(self.parent().video_thread.changeVideoSrc)
        
        #HBHBHBHB TODO: write code to fetch cameras
        # # Get cameras button
        # self.camera_button = QPushButton('Get cameras')
        # self.camera_button.clicked.connect(self.getCameras)
        # if self.parent().video_thread.alignment:
        #     self.camera_button.setDisabled(True)
        # else: self.camera_button.setDisabled(False)
        #self.getCameras()
        # cmbox.addWidget(self.camera_button)
        #HBHBHBHB TODO: write code to fetch cameras
        
        # Brightness slider
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setMinimum(0)
        self.brightness_slider.setMaximum(255)
        self.brightness_slider.valueChanged.connect(self.changeBrightness)
        self.brightness_slider.setTickPosition(QSlider.TicksBelow)
        self.brightness_slider.setTickInterval(1)
        if(brightness_input is not None):
            self.brightness_label = QLabel(str(int(brightness_input)))
            self.brightness_slider.setValue(int(brightness_input))
        else:
            self.brightness_label = QLabel()
            self.brightness_slider.setEnabled(False)
        # Contrast slider
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setMinimum(0)
        self.contrast_slider.setMaximum(255)
        self.contrast_slider.valueChanged.connect(self.changeContrast)
        self.contrast_slider.setTickPosition(QSlider.TicksBelow)
        self.contrast_slider.setTickInterval(1)
        if(contrast_input is not None):
            self.contrast_label = QLabel(str(int(contrast_input)))
            self.contrast_slider.setValue(int(contrast_input))
        else:
            self.contrast_label = QLabel()
            self.contrast_slider.setEnabled(False)
        # Saturation slider
        self.saturation_slider = QSlider(Qt.Horizontal)
        self.saturation_slider.setMinimum(0)
        self.saturation_slider.setMaximum(255)
        self.saturation_slider.valueChanged.connect(self.changeSaturation)
        self.saturation_slider.setTickPosition(QSlider.TicksBelow)
        self.saturation_slider.setTickInterval(1)
        if(saturation_input is not None):
            self.saturation_label = QLabel(str(int(saturation_input)))
            self.saturation_slider.setValue(int(saturation_input))
        else:
            self.saturation_label = QLabel()
            self.saturation_slider.setEnabled(False)
        # Hue slider
        self.hue_slider = QSlider(Qt.Horizontal)
        self.hue_slider.setMinimum(0)
        self.hue_slider.setMaximum(8)
        self.hue_slider.valueChanged.connect(self.changeHue)
        self.hue_slider.setTickPosition(QSlider.TicksBelow)
        self.hue_slider.setTickInterval(1)
        if(hue_input is not None):
            self.hue_label = QLabel(str(int(hue_input)))
            self.hue_slider.setValue(int(hue_input))
        else:
            self.hue_label = QLabel()
            self.hue_slider.setEnabled(False)
        # Reset button
        self.reset_button = QPushButton("Reset to defaults")
        self.reset_button.setToolTip('Reset camera settings to defaults.')
        self.reset_button.clicked.connect(self.resetCameraToDefaults)
        if(brightness_input is None and contrast_input is None and saturation_input is None and hue_input is None):
            self.reset_button.setDisabled(True)
        # Camera drop-down
        self.camera_box = QGroupBox('Active camera source')
        self.camerasTab.layout.addWidget(self.camera_box)
        cmbox = QHBoxLayout()
        self.camera_box.setLayout(cmbox)
        cmbox.addWidget(self.camera_combo)
        # Brightness
        self.brightness_box =QGroupBox('Brightness')
        self.camerasTab.layout.addWidget(self.brightness_box)
        bvbox = QHBoxLayout()
        self.brightness_box.setLayout(bvbox)
        bvbox.addWidget(self.brightness_slider)
        bvbox.addWidget(self.brightness_label)
        # Contrast
        self.contrast_box =QGroupBox('Contrast')
        self.camerasTab.layout.addWidget(self.contrast_box)
        cvbox = QHBoxLayout()
        self.contrast_box.setLayout(cvbox)
        cvbox.addWidget(self.contrast_slider)
        cvbox.addWidget(self.contrast_label)
        # Saturation
        self.saturation_box =QGroupBox('Saturation')
        self.camerasTab.layout.addWidget(self.saturation_box)
        svbox = QHBoxLayout()
        self.saturation_box.setLayout(svbox)
        svbox.addWidget(self.saturation_slider)
        svbox.addWidget(self.saturation_label)
        # Hue
        self.hue_box =QGroupBox('Hue')
        self.camerasTab.layout.addWidget(self.hue_box)
        hvbox = QHBoxLayout()
        self.hue_box.setLayout(hvbox)
        hvbox.addWidget(self.hue_slider)
        hvbox.addWidget(self.hue_label)
        _logger.debug('*** exiting SettingsDialog.createCameraItems')
    
    def createMachineItems(self):
        _logger.debug('*** calling SettingsDialog.createMachineItems')
        ############# MACHINES TAB #############
        if(self.__newPrinter is False):
            # Get machines as defined in the config
            # Printer combo box
            self.printer_combo = QComboBox()
            self.default_printer = None
            self.defaultIndex = 0
            for i, device in enumerate(self.__settings['printer']):
                if(device['default'] == 1):
                    printer_description = '(default) ' + device['nickname']
                    self.default_printer = device
                    self.defaultIndex = i
                else:
                    printer_description = device['nickname']
                self.printer_combo.addItem(printer_description)
            # set default printer as the selected index
            self.printer_combo.setCurrentIndex(self.defaultIndex)
            if(self.default_printer is None):
                self.default_printer = self.__settings['printer'][0]
            # Create a layout for the printer combo box, and the add and delete buttons
            topbox = QGroupBox()
            toplayout = QHBoxLayout()
            topbox.setLayout(toplayout)
            toplayout.addWidget(self.printer_combo)
            # Add button
            self.add_printer_button = QPushButton('+')
            self.add_printer_button.setStyleSheet('background-color: green')
            self.add_printer_button.clicked.connect(self.addProfile)
            self.add_printer_button.setToolTip('Add a new profile..')
            self.add_printer_button.setFixedWidth(30)
            toplayout.addWidget(self.add_printer_button)
            # Delete button
            self.delete_printer_button = QPushButton('X')
            self.delete_printer_button.setStyleSheet('background-color: red')
            self.delete_printer_button.clicked.connect(self.deleteProfile)
            self.delete_printer_button.setToolTip('Delete current profile..')
            self.delete_printer_button.setFixedWidth(30)
            toplayout.addWidget(self.delete_printer_button)
            # add printer combo box to layout
            self.settingsTab.layout.addWidget(topbox)
        # Printer default checkbox
        self.printerDefault = QCheckBox("&Default", self)
        if(self.__newPrinter is False):
            self.printerDefault.setChecked(True)
            self.printerDefault.stateChanged.connect(self.checkDefaults)
        # Printer nickname
        if(self.__newPrinter is False):
            self.printerNickname = QLineEdit(self.default_printer['nickname'])
        else: 
            self.printerNickname = QLineEdit()
        self.printerNickname.setPlaceholderText('Enter an alias for your printer')
        self.printerNickname_label = QLabel('Nickname: ')
        self.printerNickname_box =QGroupBox()
        self.settingsTab.layout.addWidget(self.printerNickname_box)
        nnbox = QHBoxLayout()
        self.printerNickname_box.setLayout(nnbox)
        nnbox.addWidget(self.printerNickname_label)
        nnbox.addWidget(self.printerNickname)
        nnbox.addWidget(self.printerDefault)
        # Printer address
        if(self.__newPrinter is False):
            self.printerAddress = QLineEdit(self.default_printer['address'])
        else:
            self.printerAddress = QLineEdit()
        self.printerAddress.setPlaceholderText('Enter printer interface or IP')
        self.printerAddress_label = QLabel('Address: ')
        self.printerAddress_box =QGroupBox()
        self.settingsTab.layout.addWidget(self.printerAddress_box)
        adbox = QHBoxLayout()
        self.printerAddress_box.setLayout(adbox)
        adbox.addWidget(self.printerAddress_label)
        adbox.addWidget(self.printerAddress)
        # Printer password
        if(self.__newPrinter is False):
            self.printerPassword = QLineEdit(self.default_printer['password'])
        else:
            self.printerPassword = QLineEdit()
        self.printerPassword.setPlaceholderText('Password')
        self.printerPassword.setToolTip('(optional): password used to connect to printer')
        self.printerPassword_label = QLabel('Password: ')
        adbox.addWidget(self.printerPassword_label)
        adbox.addWidget(self.printerPassword)
        # Printer controller
        self.controllerName = QComboBox()
        self.controllerName.setToolTip('Machine firmware family/category')
        self.controllerName.setMinimumWidth(180)
        # get controller index from master list
        for item in self.__firmwareList:
            self.controllerName.addItem(item)
        if(self.__newPrinter is False):
            # get controller index from master list
            listIndex = -1
            for i, item in enumerate(self.__firmwareList):
                if(item == self.default_printer['controller']):
                    listIndex = i
                    break
            if(listIndex > -1):
                self.controllerName.setCurrentIndex(listIndex)
            else:
                _logger.error('Controller name not found for combobox.')
        else:
            # new printer, default to RRF/Duet
            self.controllerName.setCurrentIndex(0)
        self.controllerName_label = QLabel('Controller Type: ')
        self.controllerName_box =QGroupBox()
        self.settingsTab.layout.addWidget(self.controllerName_box)
        cnbox = QGridLayout()
        cnbox.setSpacing(5)
        self.controllerName_box.setLayout(cnbox)
        cnbox.addWidget(self.controllerName_label, 0, 0, 1, 1, Qt.AlignRight)
        cnbox.addWidget(self.controllerName, 0, 1, 1, 2, Qt.AlignLeft)
        # Printer with rotated XY kinematics
        self.printerRotated = QCheckBox('Rotate XY')
        if(self.__newPrinter is True):
            self.printerRotated.setChecked(True)
        else:
            try:
                if(self.default_printer['rotated'] == 1):
                    self.printerRotated.setChecked(True)
                else:
                    self.printerRotated.setChecked(False)
            except KeyError:
                # rotated key doesn't exist, add to printer model
                self.default_printer['rotated'] = 0
                self.printerRotated.setChecked(False)
        cnbox.addWidget(self.printerRotated, 0, 3, 1, 1, Qt.AlignRight)
        # Printer name
        if(self.__newPrinter is False):
            self.printerName = QLineEdit(self.default_printer['name'])
        else:
            self.printerName = QLineEdit()
        self.printerName.setPlaceholderText('(pulled from machine..)')
        self.printerName.setStyleSheet('font: italic')
        self.printerName.setEnabled(False)
        self.printerName_label = QLabel('Name: ')
        self.printerName_box =QGroupBox()
        self.settingsTab.layout.addWidget(self.printerName_box)
        if(self.__newPrinter is True):
            self.printerName_box.setVisible(False)
        pnbox = QHBoxLayout()
        self.printerName_box.setLayout(pnbox)
        pnbox.addWidget(self.printerName_label)
        pnbox.addWidget(self.printerName)
        # Printer firmware version identifier
        if(self.__newPrinter is False):
            self.versionName = QLineEdit(self.default_printer['version'])
        else:
            self.versionName = QLineEdit()
        self.versionName.setPlaceholderText("(pulled from machine..)")
        self.versionName.setStyleSheet('font: italic')
        self.versionName.setEnabled(False)
        self.versionName_label = QLabel('Firmware version: ')
        self.versionName_box =QGroupBox()
        self.settingsTab.layout.addWidget(self.versionName_box)
        if(self.__newPrinter is True):
            self.versionName_box.setVisible(False)
        fnbox = QHBoxLayout()
        self.versionName_box.setLayout(fnbox)
        fnbox.addWidget(self.versionName_label)
        fnbox.addWidget(self.versionName)
        if(self.__newPrinter is False):
            # handle selecting a new machine from the dropdown
            self.printer_combo.activated.connect(self.refreshPrinters)
            self.printerAddress.editingFinished.connect(self.updateAttributes)
            self.printerPassword.editingFinished.connect(self.updateAttributes)
            self.printerName.editingFinished.connect(self.updateAttributes)
            self.printerNickname.editingFinished.connect(self.updateAttributes)
            self.controllerName.activated.connect(self.updateAttributes)
            self.versionName.editingFinished.connect(self.updateAttributes)
            self.printerDefault.stateChanged.connect(self.updateAttributes)
            self.printerRotated.stateChanged.connect(self.updateAttributes)
        _logger.debug('*** exiting SettingsDialog.createMachineItems')
    
    def checkDefaults(self):
        _logger.debug('*** calling SettingsDialog.checkDefaults')
        if(self.printerDefault.isChecked()):
            index = self.printer_combo.currentIndex()
            for i,machine in enumerate(self.__settings['printer']):
                machine['default'] = 0
                self.printer_combo.setItemText(i, self.__settings['printer'][i]['nickname'])
            self.__settings['printer'][index]['default']=1
            self.printer_combo.setItemText(index,'(default) ' + self.__settings['printer'][index]['nickname'])
        else:
            # User de-selected default machine
            index = self.printer_combo.currentIndex()
            if(index > -1):
                self.printer_combo.setItemText(self.printer_combo.currentIndex(),self.__settings['printer'][self.printer_combo.currentIndex()]['nickname'])
        _logger.debug('*** exiting SettingsDialog.checkDefaults')
    
    def addProfile(self):
        _logger.debug('*** calling SettingsDialog.addProfile')
        # Create a new printer profile object
        newPrinter = { 
            'address': '',
            'password': 'repap',
            'name': '',
            'nickname': 'New printer..',
            'controller' : 'RRF/Duet', 
            'version': '',
            'default': 0,
            'rotated': 0,
            'tools': [
                { 
                    'number': 0, 
                    'name': 'Tool 0', 
                    'nozzleSize': 0.4, 
                    'offsets': [0,0,0] 
                } ]
            }
        # Add new profile to settingsObject list
        self.__settings['printer'].append(newPrinter)
        # enable all text fields
        self.printerDefault.setDisabled(False)
        self.printerAddress.setDisabled(False)
        self.printerPassword.setDisabled(False)
        self.printerNickname.setDisabled(False)
        self.controllerName.setDisabled(False)
        self.printerRotated.setDisabled(False)
        self.delete_printer_button.setDisabled(False)
        self.delete_printer_button.setStyleSheet('background-color: red')
        # update combobox
        self.printer_combo.addItem('New printer..')
        self.printer_combo.setCurrentIndex(len(self.__settings['printer'])-1)
        self.refreshPrinters(self.printer_combo.currentIndex())
        _logger.debug('*** exiting SettingsDialog.addProfile')
    
    def deleteProfile(self):
        _logger.debug('*** calling SettingsDialog.deleteProfile')
        # check if this is the "Add printer.." option which is always at the bottom of the list.
        finalIndex = self.printer_combo.count() - 1
        index = self.printer_combo.currentIndex()
        if(self.__settings['printer'][index]['default'] == 1):
            wasDefault = True
        else:
            wasDefault = False
        del self.__settings['printer'][index]
        self.printer_combo.removeItem(index)
        index = self.printer_combo.currentIndex()
        if(index > -1 and len(self.__settings['printer']) > 0):
            if(wasDefault):
                self.__settings['printer'][0]['default'] = 1
            self.refreshPrinters(self.printer_combo.currentIndex())
        else:
            # no more profiles found, display empty fields
            self.printerDefault.setChecked(False)
            self.printerAddress.setText('')
            self.printerPassword.setText('')
            self.printerName.setText('')
            self.printerNickname.setText('')
            self.controllerName.setCurrentIndex(0)
            self.versionName.setText('')
            self.printerRotated.setChecked(False)
            # disable all fields
            self.printerDefault.setDisabled(True)
            self.printerAddress.setDisabled(True)
            self.printerPassword.setDisabled(True)
            self.printerName.setDisabled(True)
            self.printerNickname.setDisabled(True)
            self.controllerName.setDisabled(True)
            self.versionName.setDisabled(True)
            self.printerRotated.setDisabled(True)
            self.printer_combo.addItem('+++ Add a new profile --->')
            self.printer_combo.setCurrentIndex(0)
            self.delete_printer_button.setDisabled(True)
            self.delete_printer_button.setStyleSheet('background-color: none')
        _logger.debug('*** exiting SettingsDialog.deleteProfile')
    
    def refreshPrinters(self, index):
        _logger.debug('*** calling SettingsDialog.refreshPrinters')
        if(index >= 0):
            if(len(self.__settings['printer'][index]['address']) > 0):
                self.printerAddress.setText(self.__settings['printer'][index]['address'])
            else:
                self.printerAddress.clear()
            if(len(self.__settings['printer'][index]['password']) > 0):
                self.printerPassword.setText(self.__settings['printer'][index]['password'])
            else:
                self.printerPassword.clear()
            if(len(self.__settings['printer'][index]['name']) > 0):
                self.printerName.setText(self.__settings['printer'][index]['name'])
            else:
                self.printerName.clear()
            if(len(self.__settings['printer'][index]['nickname']) > 0):
                self.printerNickname.setText(self.__settings['printer'][index]['nickname'])
            else:
                self.printerNickname.clear()
            # get controller index from master list
            listIndex = -1
            for i, item in enumerate(self.__firmwareList):
                if(item == self.default_printer['controller']):
                    listIndex = i
                    break
            if(listIndex > -1):
                self.controllerName.setCurrentIndex(listIndex)
            else:
                _logger.error('Controller name not found for combobox.')
            if(len(self.__settings['printer'][index]['version']) > 0):
                self.versionName.setText(self.__settings['printer'][index]['version'])
            else:
                self.versionName.clear()
            if(self.__settings['printer'][index]['default'] == 1):
                self.printerDefault.setChecked(True)
            else:
                self.printerDefault.setChecked(False)
            if(self.__settings['printer'][index]['rotated'] == 1):
                self.printerRotated.setChecked(True)
            else:
                self.printerRotated.setChecked(False)
        _logger.debug('*** exiting SettingsDialog.refreshPrinters')
    
    def updateAttributes(self):
        _logger.debug('*** calling SettingsDialog.updateAttributes')
        index = self.printer_combo.currentIndex()
        if(index > -1):
            self.__settings['printer'][index]['address'] = self.printerAddress.text()
            self.__settings['printer'][index]['password'] = self.printerPassword.text()
            self.__settings['printer'][index]['name'] = self.printerName.text()
            self.__settings['printer'][index]['nickname'] = self.printerNickname.text()
            self.__settings['printer'][index]['controller'] = self.controllerName.itemText(self.controllerName.currentIndex())
            self.__settings['printer'][index]['version'] = self.versionName.text()
            if(self.printerDefault.isChecked()):
                self.__settings['printer'][index]['default'] = 1
            else:
                self.__settings['printer'][index]['default'] = 0
            if(self.printerRotated.isChecked()):
                self.__settings['printer'][index]['rotated'] = 1
            else:
                self.__settings['printer'][index]['rotated'] = 0
        _logger.debug('*** exiting SettingsDialog.updateAttributes')
    
    def resetCameraToDefaults(self):
        _logger.debug('*** calling SettingsDialog.resetCameraToDefaults')
        self.settingsResetImageSignal.emit()
        
        _logger.debug('*** exiting SettingsDialog.resetCameraToDefaults')
    
    def changeBrightness(self):
        _logger.debug('*** calling SettingsDialog.changeBrightness')
        parameter = int(self.brightness_slider.value())
        message = {'brightness': parameter}
        self.settingsSetImagePropertiesSignal.emit(message)
        self.brightness_label.setText(str(parameter))
        _logger.debug('*** exiting SettingsDialog.changeBrightness')
    
    def changeContrast(self):
        _logger.debug('*** calling SettingsDialog.changeContrast')
        parameter = int(self.contrast_slider.value())
        message = {'contrast': parameter}
        self.settingsSetImagePropertiesSignal.emit(message)
        self.contrast_label.setText(str(parameter))
        _logger.debug('*** exiting SettingsDialog.changeContrast')
    
    def changeSaturation(self):
        _logger.debug('*** calling SettingsDialog.changeSaturation')
        parameter = int(self.saturation_slider.value())
        message = {'saturation': parameter}
        self.settingsSetImagePropertiesSignal.emit(message)
        self.saturation_label.setText(str(parameter))
        _logger.debug('*** exiting SettingsDialog.changeSaturation')
    
    def changeHue(self):
        _logger.debug('*** calling SettingsDialog.changeHue')
        parameter = int(self.hue_slider.value())
        message = {'hue': parameter}
        self.settingsSetImagePropertiesSignal.emit(message)
        self.hue_label.setText(str(parameter))
        _logger.debug('*** exiting SettingsDialog.changeHue')

    def getCameras(self):
        _logger.debug('*** calling SettingsDialog.getCameras')
        #HBHBHBHB: TODO handle multiple camera profiles
        # # checks the first 6 indexes.
        # i = 6
        # index = 0
        # self.camera_combo.clear()
        # _cameras = []
        # #HBHBHBHB DEBUG camera description
        # original_camera_description = '* ' + str(camera['video_src'])
        # _cameras.append(original_camera_description)
        # tempCap = cv2.VideoCapture()
        # tempCap.setExceptionMode(True)
        # while i > 0:
        #     if index != self.parent()._videoSrc:
        #         try:
        #             tempCap.open(index)
        #             if tempCap.read()[0]:
        #                 api = tempCap.getBackendName()
        #                 camera_description = str(index) + ': ' \
        #                     + str(int(tempCap.get(cv2.CAP_PROP_FRAME_WIDTH))) \
        #                     + 'x' + str(int(tempCap.get(cv2.CAP_PROP_FRAME_HEIGHT))) + ' @ ' \
        #                     + str(int(tempCap.get(cv2.CAP_PROP_FPS))) + 'fps'
        #                 _cameras.append(camera_description)
        #             tempCap.release()
        #         except:
        #             index += 1
        #             i -= 1
        #             continue
        #     index += 1
        #     i -= 1
        # #cameras = [line for line in allOutputs if float(line['propmode']) > -1 ]
        # _cameras.sort()
        # for camera in _cameras:
        #     self.camera_combo.addItem(camera)
        # self.camera_combo.setCurrentText(original_camera_description)
        _logger.debug('*** exiting SettingsDialog.getCameras')
    
    def updatePrinterObjects(self):
        _logger.debug('*** calling SettingsDialog.updatePrinterObjects')
        defaultSet = False
        multipleDefaults = False
        defaultMessage = "More than one connection is set as the default option.\n\nPlease review the connections for:\n\n"
        # Do some data cleaning
        for machine in self.__settings['printer']:
            # Check if user forgot a nickname, default to printer address
            if(machine['nickname'] is None or machine['nickname'] == ""):
                machine['nickname'] = machine['address']
            # Do some checking to catch multiple default printers set at the same time
            if(machine['default'] == 1):
                defaultMessage += "  - " + machine['nickname'] + "\n"
                if(defaultSet):
                    multipleDefaults = True
                else:
                    defaultSet = True
        # More than one profile is set as the default. Alert user, don't save, and return to the settings screen
        if(multipleDefaults):
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setText(defaultMessage)
            msgBox.setWindowTitle('ERROR: Too many default connections')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec()
            return
        # No default printed was defined, so set first item to default
        if(defaultSet is False and len(self.__settings['printer']) > 0):
            self.__settings['printer'][0]['default'] = 1
        elif(len(self.__settings['printer']) == 0):
            # All profiles have been cleared. Add a dummy template
            self.__settings['printer'] = [
                { 
                'address': 'http://localhost',
                'password': 'reprap',
                'name': '',
                'nickname': 'Default profile',
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
                }
            ]
            pass
        self.settingsUpdateSignal.emit(self.__settings)
        _logger.debug('*** exiting SettingsDialog.updatePrinterObjects')
        self.close()
    
    def saveNewPrinter(self):
        _logger.debug('*** calling SettingsDialog.saveNewPrinter')
        _logger.info('Saving printer information..')
        newPrinter = { 
                'address': self.printerAddress.text(),
                'password': self.printerPassword.text(),
                'name': '',
                'nickname': self.printerNickname.text(),
                'controller' : str(self.controllerName.currentText()),
                'version': '',
                'default': int(self.printerDefault.isChecked()),
                'rotated': int(self.printerRotated.isChecked()),
                'tools': [
                    { 
                        'number': 0, 
                        'name': 'Tool 0', 
                        'nozzleSize': 0.4, 
                        'offsets': [0,0,0] 
                    } ]
                }
        if(self.printerDefault.isChecked()):
            # new default printer, clear other objects
            for machine in self.__settings['printer']:
                machine['default'] = 0
        self.__settings['printer'].append(newPrinter)
        self.settingsNewPrinter.emit(self.__settings)
        _logger.debug('*** exiting SettingsDialog.saveNewPrinter')
        self.close()
    
    def cancelChanges(self):
        _logger.debug('*** calling SettingsDialog.cancelChanges')
        self.settingsStatusbarSignal.emit('Changes to settings discarded.')
        self.__settings = self.__originalSettingsObject
        self.settingsGeometrySignal.emit(self.saveGeometry())
        self.close()

    def closeEvent(self, event):
        self.settingsGeometrySignal.emit(self.saveGeometry())
        super().closeEvent(event) 
