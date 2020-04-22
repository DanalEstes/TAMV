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

print("Startup may take a few moments: Loading libraries; some of them are very large.")
import os
import sys
import imutils
import datetime
import time
import numpy as np
import argparse
import threading
import queue

try:
    import cv2
except:
    print("Import for CV2 failed.  Please install openCV")
    print("You may wish to use https://github.com/DanalEstes/PiInstallOpenCV")
    raise

try: 
    import DuetWebAPI as DWA
except ImportError:
    print("Python Library Module 'DuetWebAPI.py' is required. ")
    print("Obtain from https://github.com/DanalEstes/DuetWebAPI ")
    print("Place in same directory as script, or in Python libpath.")
    exit(2)

if (os.environ.get('SSH_CLIENT')):
    print("This script MUST run on the graphics console, not an SSH session.")
    exit(8)

# Define Queue Message Types

STFU = [0]              # Do not send any more messages to me. 
TTMB = [1]              # OK to send messages
FRDT = [2,[0,0],[0,0]]  # Frame Data.  XY of recongnized circle, target XY (usually center of frame)
MCMD = [3,'']           # Message Command.  string is command, followed by variable number of args
ETXT = [4,'']           # Extra Text. String will be displayed in video frame. 
CRSH = [5,0]            # Display a crosshair.  Don't even look for circles. Second element is 0 or 1. 
ROTN = [6]              # Rotate display to next 90 degree increment
ROTR = [7]              # Rotation Reset to 0
FOAD = [8]              # Subthread should exit



###################################################################################
# This method runs in a separate thread, to own the camera, 
# present video stream to X11 window, 
# perform machine vision circle recognition, and more.
###################################################################################
def runVideoStream():
    global q
    rot=0
    xy     = [0,0]
    oldxy  = xy
    state = 0 # State machine for figuring out image rotation to carriage XY move mapping.
    rot = 0 # Amount of rotation of image.
    count=0
    rd = 0; 
    qmsg = [0,'']  
    extraText = ''
    mono=0
    blur=[0,0]
    OKTS=0          # OK To Send
    XRET=0          # Draw a cross hair reticle. 


    vs = cv2.VideoCapture(0)
    detector = createDetector()

    while True:
        # Process Queue messages before frames. 
        if (not txq.empty()): 
            qmsg=txq.get()
            if (qmsg[0] == FOAD): return(0)
            if (qmsg[0] == STFU): OKTS = 0
            if (qmsg[0] == TTMB): OKTS = 1
            if (qmsg[0] == CRSH): XRET = qmsg[1]
            if (qmsg[0] == ETXT): extraText = qmsg[1]
            if (qmsg[0] == ROTN): rot = (rot + 90) % 360
            if (qmsg[0] == ROTR): rot = 0
            if (qmsg[0] == MCMD): # Message Command
                try:
                    if ('mono' in qmsg[1]): mono = not mono
                    if ('blur' in qmsg[1]): blur = [not blur[0],int((qmsg[1]).split()[1])]
                    if ('thresh' in qmsg[1]): detector = createDetector(t1=int((qmsg[1]).split()[1]), t2=int((qmsg[1]).split()[2]))
                    if ('all' in qmsg[1]): detector = createDetector(all=float((qmsg[1]).split()[1]))
                    if ('area' in qmsg[1]): detector = createDetector(area=float((qmsg[1]).split()[1]))
                except: 
                    print('Bad command or argument ')
 
        (grabbed, fg) = vs.read()
        frame = imutils.rotate_bound(fg,rot)
        target = [int(np.around(frame.shape[1]/2)),int(np.around(frame.shape[0]/2))]

        if (mono): frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if (blur[0]): frame = cv2.medianBlur(frame, blur[1])

        keypoints = detector.detect(frame)

        # draw the timestamp on the frame AFTER the circle detector! Otherwise it finds the circles in the numbers.
        timestamp = datetime.datetime.now()
        ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
        cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,0.90, (0, 0, 255), 1)
        cv2.putText(frame, extraText, (int(target[0] - 25), int(target[1] + 50) ), cv2.FONT_HERSHEY_SIMPLEX,0.90, (0, 0, 255), 1)
        cv2.putText(frame, 'Q', (frame.shape[1] - 22, 22), cv2.FONT_HERSHEY_SIMPLEX,0.90, (0, 0, 255), 1)
        if(not OKTS): cv2.putText(frame, '-', (frame.shape[1] - 22, 22), cv2.FONT_HERSHEY_SIMPLEX,0.90, (0, 0, 255), 1)

        if (XRET):
            frame = cv2.line(frame, (target[0],    target[1]-25), (target[0],    target[1]+25), (0, 255, 0), 1) 
            frame = cv2.line(frame, (target[0]-25, target[1]   ), (target[0]+25, target[1]   ), (0, 255, 0), 1) 
            cv2.imshow("Nozzle", frame)
            key = cv2.waitKey(1) # Required to get frames to display.
            continue


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

        # Found one and only one circle.  Put it on the frame. 
        xy = np.around(keypoints[0].pt)
        r = np.around(keypoints[0].size/2)            
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

        # and tell our parent.
        if(OKTS): rxq.put([FRDT,xy,target]) # Message type 1, a set of XY coordinates, the target coordinates


###################################################################################
# Start of methods 
###################################################################################
def init():
    os.environ['QT_LOGGING_RULES'] ="qt5ct.debug=false"
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Program to allign multiple tools on Duet based printers, using machine vision.', allow_abbrev=False)
    parser.add_argument('-duet',type=str,nargs=1,help='Name or IP address of Duet printer. You can use -duet=localhost if you are on the embedded Pi on a Duet3.',required=True)
    #parser.add_argument('-camera',type=str,nargs=1,choices=['usb','pi'],default=['usb'])
    parser.add_argument('-cp',type=float,nargs=2,default=[0.0,0.0],help="x y that will put 'controlled point' on carriage over camera.")
    args=vars(parser.parse_args())

    global duet, camera, cp
    duet     = args['duet'][0]
    #camera   = args['camera'][0]
    cp       = args['cp']

    # Get connected to the printer.

    print('Attempting to connect to printer at '+duet)
    global printer
    printer = DWA.DuetWebAPI('http://'+duet)
    if (not printer.printerType()):
        print('Device at '+duet+' either did not respond or is not a Duet V2 or V3 printer.')
        exit(2)
    printer = DWA.DuetWebAPI('http://'+duet)

    print("Connected to a Duet V"+str(printer.printerType())+" printer at "+printer.baseURL())

    # Set up queues to talk to subthread. 
    global txq, rxq
    txq=queue.SimpleQueue()
    rxq=queue.SimpleQueue()
    txq.put([STFU])

    vidStrThr = threading.Thread(target=runVideoStream)
    vidStrThr.start()

    print('#########################################################################')
    print('# Important:                                                            #')
    print('# Your printer MUST be capable of mounting and parking every tool with  #')
    print('# no collisions between tools.                                          #')
    print('#                                                                       #')
    print('# Offsets for each tool must be set roughly correctly, even before the  #')
    print('# first run of TAMV.  They do not need to be perfect; only good enough  #')
    print('# to get the tool on camera.  TAMV has to see it to align it.           #')
    print('#########################################################################')
    print('')
    print('#########################################################################')
    print('# Hints:                                                                #')
    print('# Preferred location for the camera is along the max Y edge of the bed. #')
    print('# Fixed camera is also OK, but may limit aligning tools that differ     #')
    print('# significantly in Z.                                                   #')
    print('#                                                                       #')
    print('# If circle detect finds no circles, try changing lighting, changing z, #')
    print('# cleaning the nozzle, or slightly blurring focus.                      #')
    print('#                                                                       #')
    print('# Quite often, the open end of the insulation on the heater wires will  #')
    print('# be detected as a circle.  They may have to be covered.                #')
    print('#                                                                       #')
    print('# Your "controlled point" can be anything. Tool changer pin is fine.    #')
    print('#########################################################################')
    print('')

def createDetector(t1=40,t2=180, all=0.5, area=300):
        # Setup SimpleBlobDetector parameters.
    params = cv2.SimpleBlobDetector_Params()
    params.minThreshold = t1;          # Change thresholds
    params.maxThreshold = t2;
    params.filterByArea = True         # Filter by Area.
    params.minArea = area
    params.filterByCircularity = True  # Filter by Circularity
    params.minCircularity = all
    params.filterByConvexity = True    # Filter by Convexity
    params.minConvexity = all
    params.filterByInertia = True      # Filter by Inertia
    params.minInertiaRatio = all
    #ver = (cv2.__version__).split('.') # Create a detector with the parameters
    #if int(ver[0]) < 3 :
    #    detector = cv2.SimpleBlobDetector(params)
    #else:
    detector = cv2.SimpleBlobDetector_create(params)
    return(detector)

def vectDist(xy1,xy2):
    # Final rounding and int() because we are really calculating pixels here. 
    # Probably some of these 'float()' casts are overkill; still, better to be explicit. 
    return int(np.around(np.sqrt(abs( \
        (float(xy2[0]) - float(xy1[0])) ** float(2) + \
        (float(xy2[1]) - float(xy1[1])) ** float(2)   \
        ))))

def printKeypointXYR(keypoints):
    for i in range(len(keypoints)):
        print("Keypoint "+str(i)+" XY = ",np.around(keypoints[i].pt,3))
        print("Keypoints "+str(i)+" R = ",np.around(keypoints[i].size/2,3))

def controlledPoint():
    printer.gCode("T-1 ")   # Un Mount any/all tools
    txq.put([STFU])         # Tell subtask not to send us circle messages. 
    txq.put([CRSH,True])    # Tell subtask to display a cross hair reticle. 
    txq.put([ROTR])         # Tell subtask reset rotation. 
    # Get user to position the first tool over the camera.
    print('#########################################################################')
    print('# 1) Using Duet Web, jog until your controlled point appears.           #')
    print('# 2) Using Duet Web, very roughly center the controled point            #')
    print('# 3) Click back in this script window, and press Ctrl+C                 #')
    print('#########################################################################')
    try:
        while(1): 
            #print('enter message to be sent to subthread ')
            x = input()
            txq.put([MCMD,x])
    except KeyboardInterrupt:
        print()
        print("Capturing raw position of the control point.")
        global CPCoords
        CPCoords=printer.getCoords()
        print("Controlled Point X{0:-1.3f} Y{1:-1.3f} ".format(CPCoords['X'],CPCoords['Y']))
        txq.put([CRSH,False])   # Tell subtask to stop displaying a cross hair reticle. 
        return
    except:
        raise


def eachTool(tool):
    txq.put([STFU])  # Tell subtask not to send us circle messages. 
    txq.put([CRSH,False])   # Tell subtask to stop displaying a cross hair reticle. 

    avg=[0,0]
    guess  = [1,1];  # Millimeters.
    target = [720/2, 480/2] # Pixels. Will be recalculated from frame size.
    drctn  = [-1,-1]  # Either 1 or -1, which we must figure out from the initial moves
    xy     = [0,0]
    oldxy  = xy
    state = 0 # State machine for figuring out image rotation to carriage XY move mapping.
    rot = 0 # Amount of rotation of image.
    count=0
    rd = 0;

    print("Mounting tool T{0:d}. ".format(tool))
    printer.gCode("T{0:d} ".format(tool))           # Mount correct tool
    printer.gCode("G1 F5000 X{0:1.3f} ".format(np.around(CPCoords['X'],3)))     # X move first to avoid hitting parked tools. 
    printer.gCode("G1 F5000 Y{0:1.3f} ".format(np.around(CPCoords['Y'],3)))     # Position Tool in Frame
    while(not rxq.empty()): rxq.get()   # re-sync: Ignore any frame messages that came in while we were doing other things. 
    txq.put([TTMB])  # Tell subtask to send us circle messages. 

    print('')
    print('')
    print('#########################################################################')
    print('# If tool does not appear in window, adjust G10 Tool offsets to be      #')
    print('# roughly correct.  Then re-run TAMV from the beginning.                #')
    print('#########################################################################')

    # loop over the frames from the video stream
    while True:
        if (rxq.empty()): 
            txq.put([TTMB])  # Tell subtask to send us circle messages. 
            time.sleep(.1)
            continue

        qmsg=rxq.get()
        if(not qmsg[0] == FRDT): 
            print("Skipping unknown queue message header ",qmsg[0])  # Should never happen.  Still check. 
            continue

        # Found one and only one circle.  Process it.
        xy = qmsg[1]
        target = qmsg[2]

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
                printer.gCode("G91 G1 X-0.5 G90 ")
                while(not rxq.empty()): rxq.get()   # re-sync: Ignore any frame messages that came in while we were doing other things. 
                txq.put([TTMB])  # Tell subtask to send us circle messages. 
                state += 1

            elif (state == 1): # Finding Rotation: Move made, see if it aligns with carriage.
                #print("   X = ",   xy[0])
                #print("oldX = ",oldxy[0])
                #print("   Y = ",   xy[1])
                #print("oldY = ",oldxy[1])
                #print("X movement detected = ",abs(oldxy[0]-xy[0]))
                #print("Y movement detected = ",abs(oldxy[1]-xy[1]))
                if (abs(int(oldxy[0])-int(xy[0])) > 2+abs(int(oldxy[1])-int(xy[1]))):
                    print("Found X movement via rotation, will now calibrate camera to carriage direction.")
                    ppm = 0.5/float(vectDist(xy,oldxy))
                    print("MM per Pixel discovered = {0:1.4f}".format(ppm) )
                    mpp = float(vectDist(xy,oldxy))/0.5
                    print("Pixel per MM discovered = {0:1.4f}".format(mpp) )
                    state += 1
                    oldxy = xy
                    drctn = [1,1]
                else:
                    print("Camera to carriage movement axis incompatiabile... will rotate image and calibrate again.")
                    txq.put([STFU])  # Tell subtask not to send us circle messages.
                    txq.put([ROTN]) 
                    state = 0 #start over.

            elif (state == 2): # Incrementally attempt to center the nozzle.
                for j in [0,1]:
                    if (abs(target[j]-oldxy[j]) < abs(target[j]-xy[j])): # Are we going the wrong way?  Depends on camera orientation. 
                        print("Detected movement away from target, now reversing "+'XY'[j])
                        drctn[j] = -drctn[j]                         # If we are getting further away, reverse!
                    #print("Direction         Factor = X{0:-d}  Y{1:-d} ".format(drctn[0],drctn[1]))
                    guess[j] = np.around((target[j]-xy[j])/(mpp*2),3)
                    guess[j] = guess[j] * drctn[j]  # Force a direction
                printer.gCode("G91 G1 X{0:-1.3f} Y{1:-1.3f} G90 ".format(guess[0],guess[1]))
                print("G91 G1 X{0:-1.3f} Y{1:-1.3f} G90 ".format(guess[0],guess[1]))
                oldxy = xy
                if ((np.around(guess[0],3) == 0.0) and (np.around(guess[1],3) == 0.0)):
                    txq.put([STFU])
                    #printer.gCode("G10 P{0:d} X0Y0 ".format(tool))  # Remove tool offsets, before we capture position. 
                    print("Found Center of Image at offset coordinates ",printer.getCoords())
                    return(printer.getCoords())

            avg = [0,0]
            count = 0

###################################################################################
# End of method definitions
# Start of Main Code
###################################################################################
init()
if (cp[1] == 0):
    controlledPoint()                   # Command line -cp not supplied, find with help of user and camera. 
else:
    CPCoords = {'X':cp[0], 'Y':cp[1]}   # Load -cp command line arg into dict like printerGetCoords

# Now look at each tool.
toolCoords = []
for t in range(printer.getNumTools()):
    toolCoords.append(eachTool(t))

print("Unmounting last tool")
printer.gCode("T-1 ")

###################################################################################
# End of all vision, etc.  Now calculate and report.
###################################################################################
print()
for t in range(0,len(toolCoords)):
    toolOffsets = printer.getG10ToolOffset(t)
    x = np.around((CPCoords['X'] + toolOffsets['X']) - toolCoords[t]['X'],3)
    y = np.around((CPCoords['Y'] + toolOffsets['Y']) - toolCoords[t]['Y'],3)
    print("G10 P{0:d} X{1:1.3f} Y{2:1.3f} ".format(t,x,y))

# Tell subtask to exit
txq.put([FOAD])

print('If your camera is in a consistent location, next time you run TAMV, ')
print('you can optionally supply -cp x{1:1.3f} y{2:1.3f} '.format(CPCoords['X'],CPCoords['Y']))
print('Adding this will cause TAMV to skip all interaction, and attempt to align all tools on its own.')
print('(This is really the x y of your camera)')