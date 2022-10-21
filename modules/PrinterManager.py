import logging
# invoke parent (TAMV) _logger
_logger = logging.getLogger('TAMV.PrinterManager')

from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject, QTimer
import sys, time
import importlib, importlib.util
import numpy as np

class PrinterManager(QObject):
    # class attributes
    __printerJSON = None
    __activePrinter = None
    __status = None
    __homed = False
    __defaultSpeed = 3000
    __firmwareList = []

    # signals
    updateStatusbarSignal = pyqtSignal(object)
    printerDisconnectedSignal = pyqtSignal(object)
    printerIdleSignal = pyqtSignal()
    printerHomedSignal = pyqtSignal()
    moveCompleteSignal = pyqtSignal()
    toolLoadedSignal = pyqtSignal()
    toolIndexSignal = pyqtSignal(int)
    activePrinterSignal = pyqtSignal(object)
    coordinatesSignal = pyqtSignal(object)
    offsetsSetSignal = pyqtSignal(object)
    firmwareSavedSignal = pyqtSignal()
    errorSignal = pyqtSignal(object)


    # init function
    def __init__(self, *args, **kwargs):
        # send calling to log
        _logger.debug('*** calling PrinterManager.__init__')

        try:
            self.__parent = kwargs['parent']
            super(PrinterManager, self).__init__(parent=kwargs['parent'])
        except KeyError:
            self.__print = None
            super().__init__()
        try:
            self.__firmwareList = kwargs['firmwareList']
        except KeyError:
            errorMsg = 'Cannot load master firmware list.'
            self.updateStatusbarSignal.emit(errorMsg)
            _logger.exception(errorMsg)
            self.errorSignal.emit(errorMsg)
            return
        try:
            self.__driverList = kwargs['driverList']
        except KeyError:
            errorMsg = 'Cannot load master driver list.'
            self.updateStatusbarSignal.emit(errorMsg)
            _logger.exception(errorMsg)
            self.errorSignal.emit(errorMsg)
            return
        try:
            self.__announce = kwargs['announcemode']
        except KeyError: self.__announce = True

        # send exiting to log
        _logger.debug('*** exiting PrinterManager.__init__')
        pass

    def quit(self):
        # send calling to log
        _logger.debug('*** calling PrinterManager.quit')
        if(self.__announce):
            _logger.info('Shutting down  Printer Manager..')
            if( self.__printerJSON is not None):
                _logger.info('  .. disconnecting printer..')
        self.disconnectPrinter({'noUpdate':True})
        if( self.__printerJSON is not None):
            if(self.__announce):
                _logger.info('  Disconnected from ' + self.__printerJSON['nickname'] + ' (' + self.__printerJSON['controller']+ ')')
        self.__printerJSON = None
        if(self.__announce):
            _logger.info('Printer Manager shut down successfully.')
        # send exiting to log
        _logger.debug('*** exiting PrinterManager.quit')

    # Connections
    @pyqtSlot(object)
    def connectPrinter(self, printer):
        # send calling to log
        _logger.debug('*** calling PrinterManager.connectPrinter')
        if(self.__activePrinter is not None):
            self.disconnectPrinter()
        # parse input JSON
        self.__printerJSON = printer

        # start connect process
        self.updateStatusbarSignal.emit('Attempting to connect to: ' + self.__printerJSON['nickname'] + ' (' + self.__printerJSON['controller']+ ')')
        if(self.__announce):
            _logger.info('Connecting to printer at ' + self.__printerJSON['address'] + '..')

        # Attempt connecting to the controller
        try:
            # get active profile controller
            activeDriver = self.__printerJSON['controller']
            _logger.debug("Active controller: " + activeDriver)
            _logger.debug(self.__firmwareList)
            _logger.debug(self.__driverList)
            firmwareSelect = None
            driverSelect = None
            for i, item in enumerate(self.__firmwareList):
                if(item == activeDriver):
                    firmwareSelect = item
                    driverSelect = self.__driverList[i]
                    _logger.debug('  .. active driver: ' + driverSelect)
                    break
            if(firmwareSelect is None or driverSelect is None):
                # Firmware not found in master firmware list
                errorMsg = 'Cannot load driver for this printer'
                raise Exception(errorMsg)
            # load active driver
            spec = importlib.util.spec_from_file_location("printerAPI","./drivers/"+driverSelect)
            driverModule = importlib.util.module_from_spec(spec)
            sys.modules[driverSelect[:-3]] = driverModule
            spec.loader.exec_module(driverModule)
            try:
                self.__activePrinter = driverModule.printerAPI(self.__printerJSON['address'])
                if(not self.__activePrinter.isHomed()):
                    # Machine has not been homed yet
                    errorMsg = 'Printer axis not homed. Rectify and reconnect.'
                    self.errorSignal.emit(errorMsg)
                    return
                if(not self.__activePrinter.isIdle()):
                    # connection failed for some reason
                    errorMsg = 'Device either did not respond or is not a supported controller type.'
                    self.errorSignal.emit(errorMsg)
                    return
                else:
                    # connection succeeded, update objects accordingly
                    if(self.__announce):
                        _logger.info('  .. fetching tool information..')
                    # Send printer JSON to parent thread
                    activePrinter = self.__activePrinter.getJSON()
                    activePrinter['nickname'] = self.__printerJSON['nickname']
                    activePrinter['default'] = self.__printerJSON['default']
                    activePrinter['currentTool'] = self.__activePrinter.getCurrentTool()
                    successMsg = 'Connected to ' + self.__printerJSON['nickname'] + ' (' + self.__printerJSON['controller']+ ')'
                    if(self.__announce):
                        _logger.info('  ' + successMsg)
                    self.updateStatusbarSignal.emit(successMsg)
                    self.activePrinterSignal.emit(activePrinter)
            except Exception as e:
                # errorMsg = self.__printerJSON['nickname'] + ' (' + self.__printerJSON['controller']+ ')' + ' is offline.'
                errorMsg = str(e)
                self.errorSignal.emit(errorMsg)
                return
        except Exception as e:
            # Cannot connect to printer
            _logger.exception(str(e))
            self.errorSignal.emit(str(e))
            return

        # send exiting to log
        _logger.debug('*** exiting PrinterManager.connectPrinter')

    @pyqtSlot(object)
    def disconnectPrinter(self, kwargs={}):
        try:
            parkPosition = kwargs['parkPosition']
        except KeyError: 
            parkPosition = None
        try:
            noUpdate = kwargs['noUpdate']
        except KeyError: noUpdate = False
        # send calling to log
        _logger.debug('*** calling PrinterManager.disconnectPrinter')
        if(self.__activePrinter is not None):
            try:
                try:
                    self.__activePrinter.flushMovementBuffer()
                    if(self.__announce):
                        _logger.info('    .. unloading tools..')
                    self.__activePrinter.unloadTools()
                except:
                    errorMsg = 'Could not unload tools.'
                    raise Exception(errorMsg)
                # move to final park position
                if(parkPosition is not None):
                    if(self.__announce):
                        _logger.info('    .. restoring position..')
                    self.complexMoveAbsolute(position=parkPosition)
                
                if(noUpdate is False):
                    # notify parent thread
                    successMsg = 'Disconnected from ' + self.__printerJSON['nickname'] + ' (' + self.__printerJSON['controller']+ ')'
                    if(self.__announce):
                        _logger.info(successMsg)
                    self.printerDisconnectedSignal.emit(successMsg)
                else:
                    self.printerDisconnectedSignal.emit(None)
            except Exception as e:
                _logger.exception(e)
                self.errorSignal.emit(str(e))
                return

        # send exiting to log
        _logger.debug('*** exiting PrinterManager.disconnectPrinter')

    @pyqtSlot(bool)
    def setAnnounceMode(self, announceFlag=True):
        self.__announce = announceFlag

    # Movements and Coordinates
    def complexMoveAbsolute(self, position=None, moveSpeed=None):
        # send calling to log
        _logger.debug('*** calling PrinterManager.complexMoveAbsolute')
        if(position is None):
            return
        if(moveSpeed is None):
            moveSpeed = self.__defaultSpeed
        # form coorindates from parameter
        try:
            xPos = position['X']
        except KeyError: xPos = None
        try:
            yPos = position['Y']
        except KeyError: yPos = None
        try:
            zPos = position['Z']
        except KeyError: zPos = None
        try:
            rotated = self.__printerJSON['rotated']
        except KeyError: rotated=0
        try:
            if( rotated == 1):
                # move Y -> X -> Z
                if(yPos is not None): self.__activePrinter.moveAbsolute(rapidMove=False, moveSpeed=moveSpeed, Y=yPos)
                if(xPos is not None): self.__activePrinter.moveAbsolute(rapidMove=False, moveSpeed=moveSpeed, X=xPos)
                if(zPos is not None): self.__activePrinter.moveAbsolute(rapidMove=False, moveSpeed=moveSpeed, Z=zPos)
            else:
                # move X -> Y -> Z
                if(xPos is not None): self.__activePrinter.moveAbsolute(rapidMove=False, moveSpeed=moveSpeed, X=xPos)
                if(yPos is not None): self.__activePrinter.moveAbsolute(rapidMove=False, moveSpeed=moveSpeed, Y=yPos)
                if(zPos is not None): self.__activePrinter.moveAbsolute(rapidMove=False, moveSpeed=moveSpeed, Z=zPos)
        except:
            errorMsg = 'Error performing printer moves.'
            _logger.exception(errorMsg)
            self.errorSignal.emit(errorMsg)
            raise Exception(errorMsg)
        # send exiting to log
        _logger.debug('*** exiting PrinterManager.complexMoveAbsolute')

    def complexMoveRelative(self, position=None, moveSpeed=None):
        # send calling to log
        _logger.debug('*** calling PrinterManager.complexMoveRelative')
        if(position is None):
            return
        if(moveSpeed is None):
            moveSpeed = self.__defaultSpeed
        # form coorindates from parameter
        try:
            xPos = position['X']
        except KeyError: xPos = None
        try:
            yPos = position['Y']
        except KeyError: yPos = None
        try:
            zPos = position['Z']
        except KeyError: zPos = None
        try:
            rotated = self.__printerJSON['rotated']
        except KeyError: rotated=0
        try:
            if( rotated == 1):
                # move Y -> X -> Z
                if(yPos is not None): self.__activePrinter.moveRelative(rapidMove=False, moveSpeed=moveSpeed, Y=yPos)
                if(xPos is not None): self.__activePrinter.moveRelative(rapidMove=False, moveSpeed=moveSpeed, X=xPos)
                if(zPos is not None): self.__activePrinter.moveRelative(rapidMove=False, moveSpeed=moveSpeed, Z=zPos)
            else:
                # move X -> Y -> Z
                if(xPos is not None): self.__activePrinter.moveRelative(rapidMove=False, moveSpeed=moveSpeed, X=xPos)
                if(yPos is not None): self.__activePrinter.moveRelative(rapidMove=False, moveSpeed=moveSpeed, Y=yPos)
                if(zPos is not None): self.__activePrinter.moveRelative(rapidMove=False, moveSpeed=moveSpeed, Z=zPos)
        except:
            errorMsg = 'Error performing printer moves.'
            _logger.exception(errorMsg)
            self.errorSignal.emit(errorMsg)
            raise Exception(errorMsg)
        # send exiting to log
        _logger.debug('*** exiting PrinterManager.complexMoveRelative')

    @pyqtSlot(object)
    def moveRelative(self, params=None):
        # send calling to log
        _logger.debug('*** calling PrinterManager.moveRelative')
        _logger.debug('Requesting a move to position: ' + str(params))
        try:
            position = params['position']
        except KeyError: position = None
        try:
            moveSpeed = params['moveSpeed']
        except KeyError: moveSpeed = self.__defaultSpeed
        try:
            protected = params['protected']
        except KeyError: protected = False

        if(position is None):
            errorMsg = 'Move rel: Invalid position.'
            _logger.exception(errorMsg)
            self.errorSignal.emit(errorMsg)
            return
        # form coorindates from parameter
        try:
            xPos = position['X']
        except KeyError: xPos = 0
        try:
            yPos = position['Y']
        except KeyError: yPos = 0
        try:
            zPos = position['Z']
        except KeyError: zPos = 0
        try:
            if(protected):
                self.complexMoveRelative(moveSpeed=moveSpeed, position={'X':xPos, 'Y': yPos, 'Z': zPos})
            else:
                self.__activePrinter.moveRelative(rapidMove=False, moveSpeed=moveSpeed, X=xPos, Y=yPos, Z=zPos)
            self.moveCompleteSignal.emit()
        except:
            errorMsg = 'Error: moveRelative cannot run.'
            _logger.exception(errorMsg)
            self.errorSignal.emit(errorMsg)
            return
        # send exiting to log
        _logger.debug('*** exiting PrinterManager.moveRelative')

    @pyqtSlot(object)
    def moveAbsolute(self, params=None):
        # send calling to log
        _logger.debug('*** calling PrinterManager.moveAbsolute')
        _logger.debug('Requesting a move to position: ' + str(params))
        try:
            position = params['position']
        except KeyError: position = None
        try:
            moveSpeed = params['moveSpeed']
        except KeyError: moveSpeed = self.__defaultSpeed
        try:
            protected = params['protected']
        except KeyError: protected = False

        if(position is None):
            errorMsg = 'Move rel: Invalid position.'
            _logger.exception(errorMsg)
            self.errorSignal.emit(errorMsg)
            return
        
        # form coorindates from parameter
        try:
            xPos = position['X']
        except KeyError: xPos = None
        try:
            yPos = position['Y']
        except KeyError: yPos = None
        try:
            zPos = position['Z']
        except KeyError: zPos = None

        try:
            if(protected):
                self.complexMoveAbsolute(moveSpeed=moveSpeed, position={'X':xPos, 'Y': yPos, 'Z': zPos})
            else:
                self.__activePrinter.moveAbsolute(rapidMove=False, moveSpeed=moveSpeed, X=xPos, Y=yPos, Z=zPos)
            self.moveCompleteSignal.emit()
        except:
            errorMsg = 'Error: moveAbsolute cannot run.'
            _logger.exception(errorMsg)
            self.errorSignal.emit(errorMsg)
            return
        # send exiting to log
        _logger.debug('*** exiting PrinterManager.moveAbsolute')

    @pyqtSlot()
    def getCoordinates(self):
        printerCoordinates = self.__activePrinter.getCoordinates()
        self.coordinatesSignal.emit(printerCoordinates)

    @pyqtSlot()
    def saveOffsets(self):
        self.__activePrinter.saveOffsetsToFirmware()
        
    # Tools
    @pyqtSlot()
    def currentTool(self):
        loadedToolIndex = self.__activePrinter.getCurrentTool()
        self.toolIndexSignal.emit(int(loadedToolIndex))
    
    @pyqtSlot(int)
    def callTool(self, toolNumber=-1):
        toolNumber = int(toolNumber)
        try:
            if(toolNumber > -1):
                self.__activePrinter.loadTool(toolNumber)
            else:
                self.__activePrinter.unloadTools()
        except:
            raise Exception('PrinterManager: Unable to load tool: ' + str(toolNumber))
        self.toolLoadedSignal.emit()

    @pyqtSlot()
    def unloadTools(self):
        self.__activePrinter.unloadTools()
        self.toolLoadedSignal.emit()

    @pyqtSlot(object)
    def calibrationSetOffset(self, params=None):
        try:
            toolIndex = int(params['toolIndex'])
        except KeyError:
            toolIndex = None
            errorMsg = 'setOffset: Error in tool index'
            _logger.error(errorMsg)
            self.errorSignal.emit(errorMsg)
        try:
            position = params['position']
        except KeyError:
            position = None
            errorMsg = 'setOffset: error in tool position'
            _logger.error(errorMsg)
            self.errorSignal.emit(errorMsg)
        try:
            cpCoordinates = params['cpCoordinates']
        except KeyError:
            errorMsg = 'setOffset: error in cpCoordinates'
            _logger.error(errorMsg)
            self.errorSignal.emit(errorMsg)
        try:
            __continue = params['continue']
        except: __continue = True

        if(toolIndex < 0 or toolIndex is None):
            errorMsg = 'Invalid tool selected for offsets.'
            _logger.error(errorMsg)
            self.errorSignal.emit(errorMsg)
            params = {'offsets': None}
            self.offsetsSetSignal.emit(params)
            return
        elif(position is None or position['X'] is None or position['Y'] is None):
            errorMsg = 'Invalid offsets passed to printer.'
            _logger.error(errorMsg)
            self.errorSignal.emit(errorMsg)
            params = {'offsets': None}
            self.offsetsSetSignal.emit(params)
            return
        elif(cpCoordinates is None):
            errorMsg = 'Invalid CP coordinates passed to printer.'
            _logger.error(errorMsg)
            self.errorSignal.emit(errorMsg)
            params = {'offsets': None}
            self.offsetsSetSignal.emit(params)
            return
        try:
            toolOffsets = self.__activePrinter.getToolOffset(toolIndex)
            _logger.debug('calibrationSetOffset: Setting offsets for tool: ' + str(toolIndex))
            finalOffsets = {}
            finalOffsets['X'] = np.around(cpCoordinates['X'] + toolOffsets['X'] - position['X'],3)
            finalOffsets['Y'] = np.around(cpCoordinates['Y'] + toolOffsets['Y'] - position['Y'],3)
            finalOffsets['Z'] = np.around(toolOffsets['Z'],3)
            self.__activePrinter.setToolOffsets(tool=toolIndex, X=finalOffsets['X'], Y=finalOffsets['Y'])
            _logger.debug('X: ' + str(finalOffsets['X']) + ' Y:' + str(finalOffsets['Y']) + ' Z:' + str(finalOffsets['X']))
        except Exception as e:
            self.errorSignal.emit(str(e))
            _logger.error('Other exception occurred in calibrationSetOffset')
            _logger.exception(e)
            params = {'offsets': None}
            self.offsetsSetSignal.emit(params)
            return
        params = {'offsets': finalOffsets, 'continue': __continue}
        self.offsetsSetSignal.emit(params)