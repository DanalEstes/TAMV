#!/usr/bin/env python3

# Python Script to align multiple tools on Jubilee printer with Duet3d Controller
# Using images from USB camera and finding circles in those images
#
# Copyright (C) 2020 Danal Estes all rights reserved.
# Released under The MIT License. Full text available via https://opensource.org/licenses/MIT
#
# Requires OpenCV to be installed on Pi
# Requires running via the OpenCV installed python (that is why no shebang)
# Requires network connection to Duet based printer running Duet/RepRap V2 or V3
#

import os
import sys
import imutils
import datetime
import time
import numpy as np
import argparse
from threading import Thread
from math import pi
import cv2

# threaded video frame get class
class VideoGet:
    """
    Class that continuously gets frames from a VideoCapture object
    with a dedicated thread.
    """

    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.stream.set(cv2.CAP_PROP_FPS,28)
        
        (self.grabbed, self.frame) = self.stream.read()
        self.stopped = False
        
    def start(self):    
        Thread(target=self.get, args=()).start()
        return self

    def get(self):
        while not self.stopped:
            if not self.grabbed:
                self.stop()
            else:
                (self.grabbed, self.frame) = self.stream.read()

    def stop(self):
        self.stopped = True

# threaded video frame show class
class VideoShow:
    """
    Class that continuously shows a frame using a dedicated thread.
    """

    def __init__(self, frame=None):
        self.frame = frame
        self.stopped = False
        
    def start(self):
        Thread(target=self.show, args=()).start()
        return self

    def show(self,title="Output"):
        while not self.stopped:
            cv2.imshow(title, self.frame)
            if cv2.waitKey(1) == ord("q"):
                self.stopped = True

    def stop(self):
        self.stopped = True
        
def nonsense(x):
    pass

# blob detector parameters and setup
def createDetector(t1=1,t2=50, all=0.5, area=pow(6,2)*pi):
    # Setup SimpleBlobDetector parameters.
    params = cv2.SimpleBlobDetector_Params()
    params.minThreshold = t1          # Change thresholds
    params.maxThreshold = t2
    params.thresholdStep = 1
    params.filterByArea = True         # Filter by Area.
    params.minArea = area
    params.filterByCircularity = True  # Filter by Circularity
    params.minCircularity = 0.6
    params.maxCircularity= 1
    params.filterByConvexity = True    # Filter by Convexity
    params.minConvexity = 0.6
    params.maxConvexity = 1
    params.filterByInertia = True      # Filter by Inertia
    params.minInertiaRatio = 0.6
    detector = cv2.SimpleBlobDetector_create(params)
    return(detector)

def putText(frame,text,color=(0, 255, 0),offsetx=0,offsety=0,stroke=2):  # Offsets are in character box size in pixels. 
    if (text == 'timestamp'): text = datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")
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

def adjust_gamma(image, gamma=1.2):
    # build a lookup table mapping the pixel values [0, 255] to
    # their adjusted gamma values
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255
        for i in np.arange(0, 256)]).astype("uint8")
    # apply gamma correction using the lookup table
    return cv2.LUT(image, table)

def findBlobs(keypoints, frame):
    lk = len(keypoints)
    if (lk == 0):
        frame = putText(frame,'No circles found',offsety=3)
    elif (lk > 1):
        frame = putText(frame,'Too many circles found '+str(lk),offsety=3, color=(255,255,255))
        frame = cv2.drawKeypoints(frame, keypoints, np.array([]), (255,255,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
    else:
        xy = np.around(keypoints[0].pt)
        r = np.around(keypoints[0].size/2)            
        # draw the blobs that look circular
        # Note its radius and position
        ts =  "X{0:7.2f} Y{1:7.2f} R{2:7.2f}".format(xy[0],xy[1],r)
        xy = np.uint16(xy)
        frame = cv2.drawKeypoints(frame, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        frame = putText(frame, ts, offsety=2, color=(0, 255, 0), stroke=2)
    return frame

def main():
    video_getter = VideoGet(0).start()
    tempFrame = video_getter.frame
    video_shower = VideoShow(tempFrame).start()

    #cv2.namedWindow('parameters')
    #cv2.createTrackbar('gamma','parameters',120,400,nonsense)
    #cv2.createTrackbar('block','parameters',1,20,nonsense)
    detector = createDetector()

    while True:
        if (video_getter.stopped or video_shower.stopped):
            video_shower.stop()
            video_getter.stop()
            break
        rawFrame = video_getter.frame
        frame = rawFrame
        # adjust gamma
        gammaInput = 1.2 #(cv2.getTrackbarPos('gamma','parameters')+1)/100
        frame = adjust_gamma(frame, gammaInput)
        yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
        yuvPlanes = cv2.split(yuv)
        yuvPlanes[0] = cv2.GaussianBlur(yuvPlanes[0],(7,7),6)
        yuvPlanes[0] = cv2.adaptiveThreshold(yuvPlanes[0],255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,35,1)
        frame = cv2.cvtColor(yuvPlanes[0],cv2.COLOR_GRAY2BGR)
        keypoints = detector.detect(frame)
        
        # draw output images
        frame = findBlobs(keypoints, frame)
        rawFrame = findBlobs(keypoints, rawFrame)
        # Form output
        topFrame = np.hstack((rawFrame, frame))
        video_shower.frame = topFrame
        #video_shower.show()

    video_shower.stop()
    video_getter.stop()
    cv2.destroyAllWindows()
    exit(0)
    
if __name__ == "__main__":
    main()
