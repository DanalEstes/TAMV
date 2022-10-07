from distutils.log import debug, error
import logging
# invoke parent (TAMV) _logger
_logger = logging.getLogger('TAMV.CaptureManager.Camera')

import cv2
import sys
from PyQt5 import QtCore

class Camera(QtCore.QObject):
    # class attributes
    __videoSrc = 0
    __width = 640
    __height = 480
    __frame = None
    __success = False
    cap = None

    # init function
    def __init__(self, *args, **kwargs):
        super(Camera,self).__init__(parent=kwargs['parent'])
        # send calling to log
        _logger.debug('*** calling Camera.__init__')
        # process arguments
        try:
            self.__videoSrc = kwargs['videoSrc']
        except KeyError: pass
        # frame width
        try:
            self.__width= int(kwargs['width'])
        except KeyError: pass
        # frame height
        try:
            self.__height = int(kwargs['height'])
        except KeyError: pass
        
        if sys.platform.startswith('linux'):        # all Linux
            self.backend = cv2.CAP_V4L
        elif sys.platform.startswith('win'):        # MS Windows
            self.backend = cv2.CAP_DSHOW
        elif sys.platform.startswith('darwin'):     # macOS
            self.backend = cv2.CAP_AVFOUNDATION
        else:
            self.backend = cv2.CAP_ANY      # auto-detect via OpenCV

        try:
            try:
                self.cap = cv2.VideoCapture(self.__videoSrc, self.backend)
                self.__success = self.cap.grab()
                if(not self.__success):
                    raise Exception
            except:
                _logger.debug('Camera API primary exploded, using failover cv2.CAP_ANY')
                try:
                    self.cap.release()
                except: pass
                self.cap = cv2.VideoCapture(self.__videoSrc, cv2.CAP_ANY)
                self.__success = self.cap.grab()
                if(not self.__success):
                    _logger.debug('Camera API failover exploded')
                    raise Exception
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.__width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.__height)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
            # self.cap.setExceptionMode(enable=True)
            _logger.debug('Active CV backend: ' + self.cap.getBackendName())
            _logger.info('    .. camera connected using ' + self.cap.getBackendName() + '..')
            try:
                backends = cv2.videoio_registry.getCameraBackends()
                debugMessage = 'Backend options:'
                for backend in backends:
                    debugMessage += ' ' + cv2.videoio_registry.getBackendName(backend) +','
                debugMessage = debugMessage[:-1]
                _logger.debug(debugMessage)
            except: _logger.debug('Camera: cannot retrieve list of backends')
        except:
            errorMsg = 'Failed to start video source ' + str(self.__videoSrc) + ' @ ' + str(self.__width) + 'x' + str(self.__height)
            _logger.exception(errorMsg)
            raise SystemExit(errorMsg)

        try:
            # get startup camera properties
            try:
                self.brightnessDefault = self.cap.get(cv2.CAP_PROP_BRIGHTNESS)
            except: self.brightnessDefault = None
            try:
                self.contrastDefault = self.cap.get(cv2.CAP_PROP_CONTRAST)
            except: self.contrastDefault = None
            try:
                self.saturationDefault = self.cap.get(cv2.CAP_PROP_SATURATION)
            except: self.saturationDefault = None
            try:
                self.hueDefault = self.cap.get(cv2.CAP_PROP_HUE)
            except: self.hueDefault = None
        except: pass

        try:
            self.__success, self.__frame = self.cap.read()
            self.__imageSettings = {'default':1, 'brightness':self.brightnessDefault,'contrast':self.contrastDefault,'saturation':self.saturationDefault,'hue':self.hueDefault}
        except Exception as e:
            self.cap.release()
            raise SystemExit
        
        # send exiting to log
        _logger.debug('*** exiting Camera.__init__')
    
    def getCurrentImageSettings(self):
        return self.__imageSettings
        
    def quit(self):
        # send calling to log
        _logger.debug('*** calling Camera.quit')
        _logger.info('    .. closing camera..')
        self.cap.release()
        # send exiting to log
        _logger.debug('*** exiting Camera.quit') 
    
    def getFrame(self):
        self.__success, self.__frame = self.cap.read()
        if(self.__success):
            return(self.__frame)
        else:
            self.cap.release()
            raise Exception

    def getImagePropertiesJSON(self):
        try:
            brightness = self.cap.get(cv2.CAP_PROP_BRIGHTNESS)
        except: brightness = None
        try:
            contrast = self.cap.get(cv2.CAP_PROP_CONTRAST)
        except: contrast = None
        try:
            saturation = self.cap.get(cv2.CAP_PROP_SATURATION)
        except: saturation = None
        try:
            hue = self.cap.get(cv2.CAP_PROP_HUE)
        except: hue = None
        try:
            returnJSON = {
                'default': 0,
                'brightness': str(brightness), 
                'contrast': str(contrast), 
                'saturation': str(saturation), 
                'hue': str(hue)
            }
        except:
            errorMsg = 'Cannot create camera image properties object'
            _logger.warning(errorMsg)
            returnJSON = None
        return(returnJSON)
    
    def getDefaultImagePropertiesJSON(self):
        try:
            returnJSON = { 
                'default': 1,
                'brightness': str(self.brightnessDefault), 
                'contrast': str(self.contrastDefault), 
                'saturation': str(self.saturationDefault), 
                'hue': str(self.hueDefault)
            }
        except:
            errorMsg = 'Cannot create camera image default properties object'
            _logger.warning(errorMsg)
            returnJSON = None
        return(returnJSON)

    def setImageProperties(self, imageProperties):
        try:
            brightness = self.cap.set(cv2.CAP_PROP_BRIGHTNESS, imageProperties['brightness'])
        except KeyError: pass
        except: 
            errorMsg = 'Failed to set image brightness.'
            _logger.warning(errorMsg)
        try:
            contrast = self.cap.set(cv2.CAP_PROP_CONTRAST, imageProperties['contrast'])
        except KeyError: pass
        except:
            errorMsg = 'Failed to set image contrast.'
            _logger.warning(errorMsg)
        try:
            saturation = self.cap.set(cv2.CAP_PROP_SATURATION, imageProperties['saturation'])
        except KeyError: pass
        except:
            errorMsg = 'Failed to set image saturation.'
            _logger.warning(errorMsg)
        try:
            hue = self.cap.set(cv2.CAP_PROP_HUE, imageProperties['hue'])
        except KeyError: pass
        except:
            errorMsg = 'Failed to set image hue.'
            _logger.warning(errorMsg)

    def resetImageDefaults(self):
        try:
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightnessDefault)
            self.cap.set(cv2.CAP_PROP_CONTRAST, self.contrastDefault)
            self.cap.set(cv2.CAP_PROP_SATURATION, self.saturationDefault)
            self.cap.set(cv2.CAP_PROP_HUE, self.hueDefault)
            return(True)
        except:
            errorMsg = 'Cannot set image properties.'
            _logger.warning(errorMsg)
            return(False)
