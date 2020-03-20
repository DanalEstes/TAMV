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

print("Please standby, loading libraries; some of them are very large.")

try:
    import cv2
except:
    print("Import for CV2 failed.  Please install openCV")
    print("You may wish to use https://github.com/DanalEstes/PiInstallOpenCV")
    raise
import os
import sys
import imutils
import datetime
import time
import numpy as np
import duetWebAPI as DWA


if (os.environ.get('SSH_CLIENT')):
    print("This script MUST run on the graphics console, not an SSH session.")
    exit(8)

os.environ['QT_LOGGING_RULES'] ="qt5ct.debug=false"

# Globals.

# initialize the video stream and allow the cammera sensor to warmup
vs = cv2.VideoCapture(0)
time.sleep(2.0)

print("Please standby, attempting to connect to printer...")

# Get connected to the printer.  First, see if we are running on the Pi in a Duet3. 
printer = DWA.DuetWebAPI('http://127.0.0.1')
while (not printer.printerType()):
    ip = input("\nPlease Enter IP or name of printer\n")
    print("Please standby, attempting to connect to printer...")
    printer = DWA.DuetWebAPI('http://'+ip)

print("Connected to a Duet V"+str(printer.printerType())+" printer at "+printer.baseURL())

# Setup SimpleBlobDetector parameters.
params = cv2.SimpleBlobDetector_Params()

# Change thresholds
params.minThreshold = 40;
params.maxThreshold = 180;

# Filter by Area.
params.filterByArea = True
params.minArea = 500

# Filter by Circularity
params.filterByCircularity = True
params.minCircularity = 0.75

# Filter by Convexity
params.filterByConvexity = True
params.minConvexity = 0.5

# Filter by Inertia
params.filterByInertia = True
params.minInertiaRatio = 0.5

# Create a detector with the parameters
ver = (cv2.__version__).split('.')
if int(ver[0]) < 3 :
    detector = cv2.SimpleBlobDetector(params)
else:
    detector = cv2.SimpleBlobDetector_create(params)

###################################################################################
# End of initialization
# Start of method definitions
###################################################################################

def printKeypointXYR(keypoints):
    for i in range(len(keypoints)):
        print("Keypoint "+str(i)+" XY = ",np.around(keypoints[i].pt,3))
        print("Keypoints "+str(i)+" R = ",np.around(keypoints[i].size/2,3))

def firstTool():
    # Get user to position a tool.
    print('#################################################################################')
    print('# 1) Using Deut Web, mount tool zero                                            #')
    print('# 2) Using Duet Web, jog that tool until it appears in the camera view window.  #')
    print('# 3) Using Duet Web, very roughly center the tool in the window.                #')
    print('# 4) Click back in this script window, and press Ctrl+C                         #')
    print('#################################################################################')
    key = -1
    try:
        while True:
            (grabbed, frame) = vs.read()
            # draw the timestamp on the frame
            timestamp = datetime.datetime.now()
            ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
            cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,0.90, (0, 0, 255), 1)
            cv2.imshow("Nozzle", frame)
            cv2.waitKey(10) # Required to get frames to display.
    except KeyboardInterrupt:
        print()
        print("Please standby, initializing machine vision...")
        return
    except:
        raise

def eachTool():
    avg=[0,0]
    guess  = [1,1];  # Millimeters.
    target = [720/2, 480/2] # Pixels. Will be recalculated from frame size. 
    drctn  = [1,1]  # Either 1 or -1, which we must figure out from the initial moves
    xy     = [0,0]
    oldxy  = xy
    state = 0 # State machine for figuring out image rotation to carriage XY move mapping. 
    rot = 0 # Amount of rotation of image. 
    count=0
    rd = 0;
    # loop over the frames from the video stream
    while True:
        (grabbed, fg) = vs.read()
        frame = imutils.rotate_bound(fg,rot)
        target = [np.around(frame.shape[1]/2),np.around(frame.shape[0]/2)]
        keypoints = detector.detect(frame)

        # draw the timestamp on the frame AFTER the circle detector! Otherwise it finds the circles in the numbers.
        timestamp = datetime.datetime.now()
        ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
        cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,0.90, (0, 0, 255), 1)

        lk=len(keypoints)
        if (lk == 0):
            if (25 < (int(round(time.time() * 1000)) - rd)):
                cv2.putText(frame, 'no circles found', (int(target[0] - 75), int(target[1] + 30) ), cv2.FONT_HERSHEY_SIMPLEX,0.90, (0, 0, 255), 1)
                cv2.imshow("Nozzle", frame)
                key = cv2.waitKey(1) # Required to get frames to display.
            continue
        if (lk > 1):
            if (25 < (int(round(time.time() * 1000)) - rd)):
                #printKeypointXYR(keypoints)
                cv2.putText(frame, 'too many circles '+str(lk), (int(target[0] - 75), int(target[1] + 30) ), cv2.FONT_HERSHEY_SIMPLEX,0.90, (0, 0, 255), 1)
                frame = cv2.drawKeypoints(frame, keypoints, np.array([]), (255,255,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
                cv2.imshow("Nozzle", frame)
                key = cv2.waitKey(1) # Required to get frames to display.
            continue

        # Found one and only one circle.  Process it. 
        xy = np.around(keypoints[0].pt)
        r = np.around(keypoints[0].size/2)
        # Keep track of center of circle and average across many circles
        avg[0] += xy[0]
        avg[1] += xy[1]
        count += 1
        if (count > 15):
            avg[0] /= count
            avg[1] /= count
            avg = np.around(avg,3)
            #print('')
            #print("state = ",state)
            #print("Average Pixel Position = X{0:7.3f}  Y{1:7.3f} ".format(avg[0],avg[1]))
            #print("Target        Position = X{0:7.3f}  Y{1:7.3f} ".format(target[0],target[1]))
            if (state == 0):  # Finding Rotation: Collected frames before first move. 
                print("Initiating a small X move to calibrate camera to carriage rotation.")
                oldxy = xy
                printer.gCode("G91 G1 X-0.25 G90 ")
                state += 1

            elif (state == 1): # Finding Rotation: Move made, see if it aligns with carriage.
                #print("X movement detected = ",abs(oldxy[0]-xy[0]))
                #print("Y movement detected = ",abs(oldxy[1]-xy[1]))
                if (abs(oldxy[0]-xy[0]) > 2+abs(oldxy[1]-xy[1])):
                    print("Found X movement via rotation, will now calibrate camera to carriage direction.")
                    state += 1
                    oldxy = xy
                    drctn = [1,1]
                else:
                    print("Camera to carriage movement axis incompatiabile... will rotate image and calibrate again.")
                    rot = (rot + 90) % 360
                    state = 0 #start over. 

            elif (state == 2): # Incrementally attempt to center the nozzle.
                for j in [0,1]:
                    if (abs(target[j]-oldxy[j]) < abs(target[j]-xy[j])): # Are we going the wrong way?  Depends on camera orientation. 
                        print("Detected movement away from target, now reversing.")
                        drctn[j] = -drctn[j]                         # If we are getting further away, reverse!
                    #print("Direction         Factor = X{0:-d}  Y{1:-d} ".format(drctn[0],drctn[1]))
                    guess[j] = np.around((target[j]-xy[j])/40,3)
                    guess[j] = guess[j] * drctn[j]  # Force a direction
                printer.gCode("G91 G1 X{0:-1.3f} Y{1:-1.3f} G90 ".format(guess[0],guess[1]))
                #print("G91 G1 X{0:-1.2f} Y{1:-1.2f} G90 ".format(guess[0],guess[1]))
                oldxy = xy
                if ((np.around(guess)[0] == 0) and (np.around(guess)[1] == 0)):
                    print("Found Center of Image at printer coordinates ",printer.getCoords())
                    return(printer.getCoords())


            #print("oldxy         Position = X{0:7.3f}  Y{1:7.3f} ".format(oldxy[0],oldxy[1]))
            #print("Circles per frame = ", end='', flush=True)
            avg = [0,0]
            count = 0

        # draw the blobs that look circular
        # cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS ensures the size of the circle corresponds to the size of blob
        frame = cv2.drawKeypoints(frame, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        # Note its radius and position
        ts =  "X{0:7.2f} Y{1:7.2f} R{2:7.2f}".format(xy[0],xy[1],r)
        xy = np.uint16(xy)
        cv2.putText(frame, ts, (xy[0]-175, xy[1]+50), cv2.FONT_HERSHEY_SIMPLEX,0.75, (0, 0, 255), 1)

        # show the frame
        cv2.imshow("Nozzle", frame)
        key = cv2.waitKey(1) # Required to get frames to display. 
        rd = int(round(time.time() * 1000))

###################################################################################
# End of method definitions
# Start of Main Code
###################################################################################
firstTool()
baseCoords = eachTool()
print(baseCoords)


#for t in range(1:printer.getNumExtruders()):
  #eachTool()
