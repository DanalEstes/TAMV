import logging
# invoke parent (TAMV) _logger
_logger = logging.getLogger('TAMV.ConnectionDialog')

from PyQt5.QtWidgets import QComboBox, QDialog, QVBoxLayout, QPushButton, QFrame
from PyQt5.QtCore import Qt
from urllib.parse import urlparse

########################################################################### Connection dialog box
class ConnectionDialog(QDialog):
    def __init__(self, *args, **kwargs):
        _logger.debug('*** calling ConnectionDialog.__init__')
        
        # Parse arguments
        try:
            self.__parent = kwargs['parent']
        except: self.__parent = None
        try:
            self.__newPrinter = kwargs['newPrinter']
        except: self.__newPrinter = False
        try:
            self.__settings = kwargs['settings']
        except: self.__settings = None
        try:
            self.__stylesheet = kwargs['stylesheet']
        except: self.__stylesheet = None

        # Set up settings window
        super(ConnectionDialog, self).__init__(parent=self.__parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
        self.setWindowTitle( 'Connect to a machine' )
        self.setWindowModality( Qt.ApplicationModal )
        self.setMinimumWidth(300)
        # self.setMinimumHeight(150)

        # Set layout details
        self.layout = QVBoxLayout()
        self.layout.setSpacing(3)
        self.setLayout( self.layout )
        if(self.__stylesheet is not None):
            self.setStyleSheet(self.__stylesheet)
        # Get machines as defined in the config
        # Printer combo box
        self.printerCombobox = QComboBox()
        self.printerCombobox.setFixedWidth(280)
        self.printerCombobox.setStyleSheet('font: 16px')
        self.defaultPrinter = {}
        for i, device in enumerate(self.__settings['printer']):
            machineAddress = urlparse(device['address'])
            printerDescription = device['nickname'] + ' / ' + machineAddress.hostname
            if( device['default'] == 1 ):
                self.defaultPrinter = device
                self.defaultPrinter['index'] = i
            self.printerCombobox.addItem(printerDescription)
        # handle selecting a new machine
        # set default printer as the selected index
        self.printerCombobox.setCurrentIndex(self.defaultPrinter['index'])
        # add final option to add a new printer
        self.printerCombobox.addItem('+++ Add a new machine..')
        self.printerCombobox.currentIndexChanged.connect(self.addPrinter)
        # add printer combo box to layout
        self.connectButton = QPushButton( 'Connect..')
        self.connectButton.clicked.connect(self.startConnection)
        self.connectButton.setObjectName( 'active' )
        self.connectButton.setFixedWidth(200)
        # Close button
        self.cancelButton = QPushButton( 'Cancel' )
        self.cancelButton.setToolTip( 'Cancel changes and return to main program.' )
        self.cancelButton.clicked.connect(self.reject)
        self.cancelButton.setObjectName( 'terminate' )
        self.cancelButton.setFixedWidth(200)
        # Separator
        self.spacerLine = QFrame()
        self.spacerLine.setFrameShape(QFrame.HLine)
        self.spacerLine.setLineWidth(1)
        self.spacerLine.setFrameShadow(QFrame.Sunken)
        self.spacerLine.setFixedHeight(25)
        self.spacerLine.setFixedWidth(200)
        # WINDOW BUTTONS
        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.addWidget( self.printerCombobox )
        self.layout.addWidget(self.spacerLine)
        self.layout.addWidget(self.connectButton)
        self.layout.addWidget(self.cancelButton)
        self.layout.setAlignment(self.printerCombobox, Qt.AlignHCenter)
        self.layout.setAlignment(self.spacerLine, Qt.AlignHCenter)
        self.layout.setAlignment(self.connectButton, Qt.AlignHCenter)
        self.layout.setAlignment(self.cancelButton, Qt.AlignHCenter)
        _logger.debug('*** exiting ConnectionDialog.__init__')

    def startConnection( self ):
        _logger.debug('*** calling ConnectionDialog.startConnection')
        index = self.printerCombobox.currentIndex()
        if( index < len(self.__settings['printer'])):
            self.done(index)
        else:
            self.done(-2)
        _logger.debug('*** exiting ConnectionDialog.startConnection')

    def addPrinter( self, index ):
        _logger.debug('*** calling ConnectionDialog.addPrinter')
        if( index == len(self.__settings['printer'])):
            self.connectButton.setText('Create new profile..')
        else:
            self.connectButton.setText('Connect..')
        _logger.debug('*** exiting ConnectionDialog.addPrinter')

    def reject(self):
        self.done(-1)