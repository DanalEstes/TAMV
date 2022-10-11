import logging
from sys import stdout
# invoke parent (TAMV) _logger
_logger = logging.getLogger('TAMV.DetectionManager')

from modules.Camera import Camera

import cv2
import numpy as np
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import pyqtSlot, QObject, pyqtSignal
from time import sleep
import copy

class DetectionManager(QObject):
    # class attributes
    __videoSource = None
    __frameSize = {}
    __enableDetection = False
    __nozzleDetectionActive = False
    __nozzleAutoDetectionActive = False
    __endstopDetectionActive = False
    __endstopAutomatedDetectionActive = False
    __running = True
    __uv = None
    __counter = 0
    
    # Signals
    detectionManagerNewFrameSignal = pyqtSignal(object)
    detectionManagerReadySignal = pyqtSignal(object)
    detectionManagerImagePropertiesSignal = pyqtSignal(object)
    detectionManagerDefaultImagePropertiesSignal = pyqtSignal()
    detectionManagerSetImagePropertiesSignal = pyqtSignal(object)
    detectionManagerResetImageSignal = pyqtSignal()
    errorSignal = pyqtSignal(object)
    finishedSignal = pyqtSignal()
    
    detectionManagerEndstopPosition = pyqtSignal(object)
    detectionManagerAutoEndStopSignal = pyqtSignal(object)
    detectionManagerArrayFrameSignal = pyqtSignal(object)

    ##### Setup functions
    # init function
    def __init__(self, *args, **kwargs):
        # send calling to log
        _logger.debug('*** calling DetectionManager.__init__')
        super(DetectionManager, self).__init__(parent=kwargs['parent'])
        try:
            self.__videoSource = kwargs['videoSrc']
        except KeyError:
            self.__videoSource = 0
        try:
            self.__frameSize['width'] = kwargs['width']
        except KeyError:
            self.__frameSize['width'] = 640
        try:
            self.__frameSize['height'] = kwargs['height']
        except KeyError:
            self.__frameSize['height'] = 480
        self.startCamera()
        self.createDetectors()
        self.processFrame()
        self.uv = [None, None]
        # send exiting to log
        _logger.debug('*** exiting DetectionManager.__init__')

    def startCamera(self):
        # send calling to log
        _logger.debug('*** calling DetectionManager.startCamera')
        try:
            # Setup camera
            self.videoFeed = Camera(videoSrc=self.__videoSource,width=self.__frameSize['width'],height=self.__frameSize['height'],parent=self)
            self.__imageSettings = self.videoFeed.getCurrentImageSettings()
            if(self.__imageSettings is not None):
                self.cameraReady(imageSettings=self.__imageSettings)
            else: raise Exception()
        except:
            _logger.exception('Camera failed to start..')
            self.errorSignal.emit('Camera failed to start..')
        # send exiting to log
        _logger.debug('*** exiting DetectionManager.startCamera')

    def cameraReady(self, imageSettings):
        # send calling to log
        _logger.debug('*** calling DetectionManager.cameraReady')
        # consume JSON
        try:
            brightness = imageSettings['brightness']
        except KeyError: brightness = None
        try:
            contrast = imageSettings['contrast']
        except KeyError: contrast = None
        try:
            staturation = imageSettings['saturation']
        except KeyError: staturation = None
        try:
            hue = imageSettings['hue']
        except KeyError: hue = None
        self.__brightnessDefault = brightness
        self.__contrastDefault = contrast
        self.__saturationDefault = staturation
        self.__hueDefault = hue
        cameraProperties = {
            'videoSrc': self.__videoSource,
            'width': self.__frameSize['width'],
            'height': self.__frameSize['height'],
            'image': {
                'default': 1,
                'brightness': self.__brightnessDefault,
                'contrast': self.__contrastDefault,
                'saturation': self.__saturationDefault,
                'hue': self.__hueDefault
            }
        }
        self.detectionManagerReadySignal.emit(cameraProperties)
        # send exiting to log
        _logger.debug('*** exiting DetectionManager.cameraReady')

    def createDetectors(self):
        # Standard Parameters
        if(True):
            self.standardParams = cv2.SimpleBlobDetector_Params()
            # Thresholds
            self.standardParams.minThreshold = 1
            self.standardParams.maxThreshold = 50
            self.standardParams.thresholdStep = 1
            # Area
            self.standardParams.filterByArea = True
            self.standardParams.minArea = 400
            self.standardParams.maxArea = 900
            # Circularity
            self.standardParams.filterByCircularity = True
            self.standardParams.minCircularity = 0.8
            self.standardParams.maxCircularity= 1
            # Convexity
            self.standardParams.filterByConvexity = True
            self.standardParams.minConvexity = 0.3
            self.standardParams.maxConvexity = 1
            # Inertia
            self.standardParams.filterByInertia = True
            self.standardParams.minInertiaRatio = 0.3

        # Relaxed Parameters
        if(True):
            self.relaxedParams = cv2.SimpleBlobDetector_Params()
            # Thresholds
            self.relaxedParams.minThreshold = 1
            self.relaxedParams.maxThreshold = 50
            self.relaxedParams.thresholdStep = 1
            # Area
            self.relaxedParams.filterByArea = True
            self.relaxedParams.minArea = 600
            self.relaxedParams.maxArea = 15000
            # Circularity
            self.relaxedParams.filterByCircularity = True
            self.relaxedParams.minCircularity = 0.6
            self.relaxedParams.maxCircularity= 1
            # Convexity
            self.relaxedParams.filterByConvexity = True
            self.relaxedParams.minConvexity = 0.1
            self.relaxedParams.maxConvexity = 1
            # Inertia
            self.relaxedParams.filterByInertia = True
            self.relaxedParams.minInertiaRatio = 0.3
        
        # Create 2 detectors
        self.detector = cv2.SimpleBlobDetector_create(self.standardParams)
        self.relaxedDetector = cv2.SimpleBlobDetector_create(self.relaxedParams)

    def quit(self):
        # send calling to log
        _logger.debug('*** calling DetectionManager.quit')
        _logger.info('Shutting down Detection Manager..')
        _logger.info('  .. disconnecting video feed..')
        self.__running = False
        self.videoFeed.quit()
        _logger.info('Detection Manager shut down successfully.')
        # send exiting to log
        _logger.debug('*** exiting DetectionManager.quit')

    # Main processing function
    @pyqtSlot()
    def processFrame(self):
        try:
            self.frame = self.videoFeed.getFrame()
            if(self.frame is None):
                self.errorSignal.emit('Failed to get signal')
            elif(self.__enableDetection is True):
                if(self.__endstopDetectionActive is True):
                    if(self.__endstopAutomatedDetectionActive is False):
                        self.analyzeEndstopFrame()
                    else:
                        self.burstEndstopDetection()
                elif(self.__nozzleDetectionActive is True):
                    if(self.__nozzleAutoDetectionActive is False):
                        self.analyzeNozzleFrame()
                    else:
                        self.burstNozzleDetection()
            else:
                pass
            self.receivedFrame(self.frame)
        except Exception as e:
            _logger.critical('Camera failed to retrieve data.')
            _logger.critical(e)
            self.errorSignal.emit('Critical camera error. Please restart TAMV.')

    # convert from cv2.mat to QPixmap and return results (frame+keypoint)
    def receivedFrame(self, frame):
        #print('Detection:',self.__counter)
        self.__counter += 1
        if(self.__running):
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            qpixmap = QPixmap.fromImage(convert_to_Qt_format)
            try:
                retObject = []
                retObject.append(qpixmap)
                retObject.append(self.__uv)
                self.detectionManagerNewFrameSignal.emit(retObject)
            except: 
                raise SystemExit('Fatal error in Detection Manager.')

    @pyqtSlot(bool)
    def enableDetection(self, state=False):
        self.__enableDetection = state


    ##### Endstop detection
    def analyzeEndstopFrame(self):
        detectionCount = 0
        self.uv = [0, 0]
        average_location=[0,0]
        retries = 0
        while(detectionCount < 5):
            # for i in range(10):
            #     self.frame = self.videoFeed.getFrame()
            (self.__uv, self.frame) = self.endstopContourDetection(self.frame)
            if(self.__uv is not None):
                if(self.__uv[0] is not None and self.__uv[1] is not None):
                    average_location[0] += np.around(self.__uv[0],0)
                    average_location[1] += np.around(self.__uv[1],0)
                    detectionCount += 1
                else:
                    retries += 1
            else:
                retries += 1
            if(retries > 3):
                average_location[0] = None
                average_location[1] = None
                break
        if(average_location[0] is not None):
            # calculate average X Y position from detection
            average_location[0] /= detectionCount
            average_location[1] /= detectionCount
            # round to 0 decimal places
            average_location = np.around(average_location,3)
            self.__uv = average_location
        else:
            self.__uv = [None,None]

    @pyqtSlot(int)
    def burstEndstopDetection(self):
        detectionCount = 0
        self.uv = [0, 0]
        average_location=[0,0]
        retries = 0
        while(detectionCount < 5):
            for j in range(3):
                self.frame = self.videoFeed.getFrame()
            (self.__uv, self.frame) = self.endstopContourDetection(self.frame)
            if(self.__uv is not None):
                if(self.__uv[0] is not None and self.__uv[1] is not None):
                    average_location[0] += self.__uv[0]
                    average_location[1] += self.__uv[1]
                    detectionCount += 1
                else:
                    retries += 1
            else:
                retries += 1
            if(retries > 5):
                average_location[0] = None
                average_location[1] = None
                break
        if(average_location[0] is not None):
            # calculate average X Y position from detection
            average_location[0] /= detectionCount
            average_location[1] /= detectionCount
            # round to 0 decimal places
            average_location = np.around(average_location,0)
            self.__uv = average_location
        else:
            self.__uv = None

    def endstopContourDetection(self, detectFrame):
        # apply endstop detection algorithm
        usedFrame = copy.deepcopy(detectFrame)
        yuv = cv2.cvtColor(usedFrame, cv2.COLOR_BGR2YUV)
        yuvPlanes = cv2.split(yuv)
        still = yuvPlanes[0]
        black = np.zeros((still.shape[0],still.shape[1]), np.uint8)
        kernel = np.ones((5,5),np.uint8)
        img_blur = cv2.GaussianBlur(still, (7, 7), 3)
        img_canny = cv2.Canny(img_blur, 50, 190)
        img_dilate = cv2.morphologyEx(img_canny, cv2.MORPH_DILATE, kernel, iterations=2)
        cnt, hierarchy = cv2.findContours(img_dilate, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        black = cv2.drawContours(black, cnt, -1, (255, 0, 255), -1)
        black = cv2.morphologyEx(black, cv2.MORPH_DILATE, kernel, iterations=2)
        cnt2, hierarchy2 = cv2.findContours(black, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        black = cv2.cvtColor(black, cv2.COLOR_GRAY2BGR)
        # detectFrame = black
        center = (None, None)
        if len(cnt2) > 0:
            myContours = []
            for k in range(len(cnt2)):
                if hierarchy2[0][k][3] > -1:
                    myContours.append(cnt2[k])
            if len(myContours) > 0:
                # return only the biggest detected contour
                blobContours = max(myContours, key=lambda el: cv2.contourArea(el))
                contourArea = cv2.contourArea(blobContours)
                if( len(blobContours) > 0 and contourArea >= 43000 and contourArea < 50000):
                    M = cv2.moments(blobContours)
                    center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
                    detectFrame = cv2.circle(detectFrame, center, 150, (255,0,0), 5)
                    detectFrame = cv2.circle(detectFrame, center, 5, (255,0,255), 2)
                    detectFrame = cv2.line(detectFrame, (320,0), (320,480), (255,255,255), 1)
                    detectFrame = cv2.line(detectFrame, (0,240), (640,240), (255,255,255), 1)
        return(center,detectFrame)

    @pyqtSlot(bool)
    def toggleEndstopDetection(self, endstopDetectFlag):
        if(endstopDetectFlag is True):
            self.__endstopDetectionActive = True
        else:
            self.__endstopDetectionActive = False

    @pyqtSlot(bool)
    def toggleEndstopAutoDetection(self, endstopDetectFlag):
        if(endstopDetectFlag is True):
            self.__endstopDetectionActive = True
            self.__endstopAutomatedDetectionActive = True
        else:
            self.__endstopDetectionActive = False
            self.__endstopAutomatedDetectionActive = False


    ##### Nozzle detection
    def analyzeNozzleFrame(self):
        detectionCount = 0
        self.uv = [0, 0]
        average_location=[0,0]
        retries = 0
        self.frame = self.videoFeed.getFrame()
        self.__uv = [None,None]

    def burstNozzleDetection(self):
        detectionCount = 0
        self.uv = [0, 0]
        average_location=[0,0]
        retries = 0
        while(detectionCount < 5):
            self.frame = self.videoFeed.getFrame()
            (self.__uv, self.frame) = self.nozzleDetection()
            if(self.__uv is not None):
                if(self.__uv[0] is not None and self.__uv[1] is not None):
                    average_location[0] += self.__uv[0]
                    average_location[1] += self.__uv[1]
                    detectionCount += 1
                else:
                    retries += 1
            else:
                retries += 1
            if(retries > 5):
                average_location[0] = None
                average_location[1] = None
                break
        if(average_location[0] is not None):
            # calculate average X Y position from detection
            average_location[0] /= detectionCount
            average_location[1] /= detectionCount
            # round to 0 decimal places
            average_location = np.around(average_location,0)
            self.__uv = average_location
        else:
            self.__uv = None

    def nozzleDetection(self):
        # working frame object
        nozzleDetectFrame = copy.deepcopy(self.frame)
        # return value for keypoints
        keypoints = None
        center = (None, None)
        preprocessorImage0 = self.preprocessImage(frameInput=nozzleDetectFrame, algorithm=0)
        preprocessorImage1 = self.preprocessImage(frameInput=nozzleDetectFrame, algorithm=1)

        if( self.__nozzleAutoDetectionActive is True ):
            # apply combo 1 (standard detector, preprocessor 0)
            keypoints = self.detector.detect(preprocessorImage0)
            keypointColor = (0,0,255)
            if(len(keypoints) != 1):
                # apply combo 2 (standard detector, preprocessor 1)
                keypoints = self.detector.detect(preprocessorImage1)
                keypointColor = (0,255,0)
                if(len(keypoints) != 1):
                    # apply combo 3 (standard detector, preprocessor 0)
                    keypoints = self.relaxedDetector.detect(preprocessorImage0)
                    keypointColor = (255,0,0)
                    if(len(keypoints) != 1):
                        # apply combo 4 (standard detector, preprocessor 1)
                        keypoints = self.relaxedDetector.detect(preprocessorImage1)
                        keypointColor = (39,127,255)
                        if(len(keypoints) != 1):
                            # failed to detect a nozzle, correct return value object
                            keypoints = None
        # process keypoint
        if(keypoints is not None):
            # create center object
            (x,y) = np.around(keypoints[0].pt)
            x,y = int(x), int(y)
            center = (x,y)
            # create radius object
            keypointRadius = np.around(keypoints[0].size/2)
            keypointRadius = int(keypointRadius)
            circleFrame = cv2.circle(img=nozzleDetectFrame, center=center, radius=keypointRadius,color=keypointColor,thickness=-1)
            nozzleDetectFrame = cv2.addWeighted(circleFrame, 0.4, nozzleDetectFrame, 0.6, 0)
            nozzleDetectFrame = cv2.circle(img=nozzleDetectFrame, center=center, radius=keypointRadius, color=(0,0,0), thickness=1)
            nozzleDetectFrame = cv2.line(nozzleDetectFrame, (x-5,y), (x+5, y), (255,255,255), 2)
            nozzleDetectFrame = cv2.line(nozzleDetectFrame, (x,y-5), (x, y+5), (255,255,255), 2)
        else:
            # no keypoints, draw a 3 outline circle in the middle of the frame
            keypointRadius = 17
            nozzleDetectFrame = cv2.circle(img=nozzleDetectFrame, center=(320,240), radius=keypointRadius, color=(0,0,0), thickness=3)
            nozzleDetectFrame = cv2.circle(img=nozzleDetectFrame, center=(320,240), radius=keypointRadius+1, color=(0,0,255), thickness=1)
        # draw crosshair
        nozzleDetectFrame = cv2.line(nozzleDetectFrame, (320,0), (320,480), (0,0,0), 3)
        nozzleDetectFrame = cv2.line(nozzleDetectFrame, (0,240), (640,240), (0,0,0), 3)
        nozzleDetectFrame = cv2.line(nozzleDetectFrame, (320,0), (320,480), (255,255,255), 1)
        nozzleDetectFrame = cv2.line(nozzleDetectFrame, (0,240), (640,240), (255,255,255), 1)
        return(center, nozzleDetectFrame)

    @pyqtSlot(bool)
    def toggleNozzleDetection(self, nozzleDetectFlag):
        if(nozzleDetectFlag is True):
            self.__nozzleDetectionActive = True
        else:
            self.__nozzleDetectionActive = False

    @pyqtSlot(bool)
    def toggleNozzleAutoDetection(self, nozzleDetectFlag):
        if(nozzleDetectFlag is True):
            self.__nozzleDetectionActive = True
            self.__nozzleAutoDetectionActive = True
        else:
            self.__nozzleDetectionActive = False
            self.__nozzleAutoDetectionActive = False
    
    
    ##### Utilities
    # adjust image gamma
    def adjust_gamma(self, image, gamma=1.2):
        # build a lookup table mapping the pixel values [0, 255] to
        # their adjusted gamma values
        invGamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** invGamma) * 255
            for i in np.arange(0, 256)]).astype( 'uint8' )
        # apply gamma correction using the lookup table
        return cv2.LUT(image, table)

    # Image detection preprocessors
    def preprocessImage(self, frameInput, algorithm=0):
        try:
            outputFrame = self.adjust_gamma(image=frameInput, gamma=1.2)
        except: outputFrame = copy.deepcopy(frameInput)
        if(algorithm == 0):
            yuv = cv2.cvtColor(outputFrame, cv2.COLOR_BGR2YUV)
            yuvPlanes = cv2.split(yuv)
            yuvPlanes[0] = cv2.GaussianBlur(yuvPlanes[0],(7,7),6)
            yuvPlanes[0] = cv2.adaptiveThreshold(yuvPlanes[0],255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,35,1)
            outputFrame = cv2.cvtColor(yuvPlanes[0],cv2.COLOR_GRAY2BGR)
        elif(algorithm == 1):
            outputFrame = cv2.cvtColor(outputFrame, cv2.COLOR_BGR2GRAY )
            thr_val, outputFrame = cv2.threshold(outputFrame, 127, 255, cv2.THRESH_BINARY|cv2.THRESH_TRIANGLE )
            outputFrame = cv2.GaussianBlur( outputFrame, (7,7), 6 )
            outputFrame = cv2.cvtColor( outputFrame, cv2.COLOR_GRAY2BGR )
        return(outputFrame)


    ##### Image adjustment properties
    @pyqtSlot(object)
    def getImageProperties(self, imageSettings):
        try:
            brightness = imageSettings['brightness']
        except KeyError: brightness = None
        try:
            contrast = imageSettings['contrast']
        except KeyError: contrast = None
        try:
            staturation = imageSettings['saturation']
        except KeyError: staturation = None
        try:
            hue = imageSettings['hue']
        except KeyError: hue = None
        if(imageSettings['default']==1):
            self.__brightnessDefault = brightness
            self.__contrastDefault = contrast
            self.__saturationDefault = staturation
            self.__hueDefault = hue
        else:
            self.__brightness = brightness
            self.__contrast = contrast
            self.__saturation = staturation
            self.__hue = hue

    @pyqtSlot(object)
    def relayImageProperties(self, imageProperties):
        self.videoFeed.setImageProperties(imagePropterties=imageProperties)

    @pyqtSlot()
    def relayResetImage(self):
        self.videoFeed.resetImageProperties()

    def getPropertiesJSON(self):
        self.detectionManagerImagePropertiesSignal.emit()

    def getDefaultPropertiesJSON(self):
        self.detectionManagerDefaultImagePropertiesSignal.emit()
