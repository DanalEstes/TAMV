#!/usr/bin/env python3
# Python Script to fetch tool offsets for a Jubilee printer with Duet3d Controller
#
# Copyright (C) 2020 Danal Estes all rights reserved
# Released under The MIT License. Full text available via https://opensource.org/licenses/MIT
# Modified by Haytham Bennani in August 2020 to allow for proper RRF2 offset fetching
#
# Requires network connection to Duet based printer running Duet/RepRap V2 or V3
 
import os
import sys
import imutils
import datetime
import time
import numpy as np
import argparse

try: 
    import DuetWebAPI as DWA

except ImportError:
    print("Python Library Module 'DuetWebAPI.py' is required. ")
    print("Obtain from https://github.com/DanalEstes/DuetWebAPI ")
    print("Place in same directory as script, or in Python libpath.")
    exit(8)

if (os.environ.get('SSH_CLIENT')):
    print("This script MUST run on the graphics console, not an SSH session.")
    exit(8)

def init():
    os.environ['QT_LOGGING_RULES'] ="qt5ct.debug=false"
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Test script to connect to a Duet printer and fetch tool offsets.', allow_abbrev=False)
    parser.add_argument('-duet',type=str,nargs=1,default=['localhost'],help='Name or IP address of Duet printer. You can use -duet=localhost if you are on the embedded Pi on a Duet3.')
    args=vars(parser.parse_args())

    global duet, vidonly, camera, cp, repeat
    duet     = args['duet'][0]

###################################################################################
# End of method definitions
# Start of Main Code
###################################################################################
init()
# Get connected to the printer.
print('Attempting to connect to printer at '+duet)
global printer
printer = DWA.DuetWebAPI('http://'+duet)
if (not printer.printerType()):
    print('Device at '+duet+' either did not respond or is not a Duet V2 or V3 printer.')
    print('If you have not specified a printer IP/hostname, please use the \'-duet\' parameter and try again.' )
    exit(2)
printer = DWA.DuetWebAPI('http://'+duet)
print("Connected to a Duet V"+str(printer.printerType())+" printer at "+printer.baseURL())
print("Fetching G10 offsets")
for i in range( 0, printer.getNumTools() ):
    toolOffsets = printer.getG10ToolOffset(i)
    x = toolOffsets['X']
    y = toolOffsets['Y']
    z = toolOffsets['Z']
    print("Tool {0:d}: X{1:1.3f} Y{2:1.3f} Z{3:1.3f}".format(i,x,y,z))
print()
print("Raw offset output:")
for i in range( 0, printer.getNumTools() ):
    print(printer.getG10ToolOffset(i))