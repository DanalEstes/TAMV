#!/usr/bin/env python3
# ZTATP = Z (only) Tool Align Touch Plate
#
# Python Script to align Z for multiple tools on Jubilee printer with Duet3d Controller
# Using a touchplate, and and endstop endput wire to every nozzle and that touchplate.
# May also work on other Duet/RepRap based mutli-tool printers.  
#
# Copyright (C) 2020 Danal Estes all rights reserved.
# Released under The MIT License. Full text available via https://opensource.org/licenses/MIT
#
# Requires network connection to Duet based printer running Duet/RepRap V2 or V3
#
# Note: You MUST define Z with a PROBE in config.g.  Even if it is really an endstop switch, it is OK to define that as a probe. 
#

try: 
    import DuetWebAPI as DWA
except ImportError:
    print("Python Library Module 'DuetWebAPI.py' is required. ")
    print("Obtain from https://github.com/DanalEstes/DuetWebAPI ")
    print("Place in same directory as script, or in Python libpath.")
    exit(2)
import numpy as np
import argparse

def init():
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Program to allign multiple tools in Z on Duet based printers, using a touch plate.', allow_abbrev=False)
    parser.add_argument('-duet',type=str,nargs=1,help='Name or IP address of Duet printer. You can use -duet=localhost if you are on the embedded Pi on a Duet3.',required=True)
    #parser.add_argument('-camera',type=str,nargs=1,choices=['usb','pi'],default=['usb'])
    parser.add_argument('-touchplate',type=float,nargs=2,default=[0.0,0.0],help="x y of center of a 15x15mm touch plate.",required=True)
    parser.add_argument('-pin',type=str,nargs=2,default='!io5.in',help='input pin to which wires from nozzles are attached.')
    args=vars(parser.parse_args())

    global duet, camera, tp, pin
    duet   = args['duet'][0]
    tp     = args['touchplate']
    pin    = args['pin']


    # Get connected to the printer.
    print('Attempting to connect to printer at '+duet)
    global prt
    prt = DWA.DuetWebAPI('http://'+duet)
    if (not prt.printerType()):
        print('Device at '+duet+' either did not respond or is not a Duet V2 or V3 printer.')
        exit(2)
    print("Connected to a Duet V"+str(prt.printerType())+" printer at "+prt.baseURL())

    print('#########################################################################')
    print('# Important:                                                            #')
    print('# Your printer MUST be capable of mounting and parking every tool with  #')
    print('# no collisions between tools.                                          #')
    print('#                                                                       #')
    print('# Your Z probe must be a probe, not an endstop.  It is OK to define a   #')
    print('# simple switch as a probe.                                             #')
    print('#                                                                       #')
    print('# Each nozzle MUST be wired to the specified input.  Test the wiring by #')
    print('# hand before running ZTATP.  If the wiring is wrong, probing will not  #')
    print('# stop, and machine damage could occur.                                 #')
    print('#########################################################################')
    print('')
    # Tell user options in use. 
    print()
    print("##################################")
    print("# Options in force for this run: #")
    print("# printer    = {0:18s}#".format(duet))
    print("# touchplate = {0:6.2f} {1:6.2f}     #".format(tp[0],tp[1]))
    print("# pin        = {0:18s}#".format(str(pin)))
    print("##################################")
    print()    

def probePlate():
    prt.resetEndstops()
    prt.gCode('T-1')                                        # Unmount any/all tools
    #prt.gCode('G32 G28 Z')
    prt.gCode('G30 X'+str(tp[0])+' Y'+str(tp[1])+' S-1')    # The real purpose of this is to move the probe into position with its correct offsets. 
    prt.gCode('G30 S-1')                                    # Now we can probe in such a way that Z is readable. 
    poffs = prt.getCoords()['Z']                            # Capture the Z position at initial point of contact
    print("Plate Offset = "+str(poffs))
    prt.gCode('G91 G0 Z3 F1000 G90')                        # Lower bed to avoid collision
    return(poffs)

def probeTool(tn):
    prt.resetEndstops()
    prt.gCode('M400')                               # Wait for planner to empty
    prt.gCode('G10 P'+str(tn)+' Z0')                 # Remove z offsets from Tool 
    prt.gCode('T'+str(tn))                           # Pick up Tool 
    # Z Axis
    prt.gCode('M558 K0 P9 C"nil"')                   # Undef existing probe
    prt.gCode('M558 K0 P5 C"'+pin+'" F200')          # Define nozzle<>bed wire as probe
    prt.gCode('G91 G0 Z3 F1000 G90')                 # Lower bed to avoid collision
    prt.gCode('G0 X'+str(tp[0])+' Y'+str(tp[1])+' F10000') # Move nozzle to spot above flat part of plate
    prt.gCode('G30 S-1')
    toffs = prt.getCoords()
    print("Tool Offset for tool "+str(tn)+" is "+str(toffs[tn][2]))
    prt.gCode('G91 G0 Z3 F1000 G90')                 # Lower bed to avoid collision
    prt.gCode('M574 Z1 S1 P"nil"')
    prt.resetEndstops()
    #prt.resetAxisLimits()
    prt.gCode('T-1')
    prt.gCode('M400')
    return(toffs)
# End of probeTool function

#
# Main
#
init()

poffs = probePlate()
toolCoords = []
for t in range(prt.getNumTools()):
    toolCoords.append(probeTool(t))
prt.resetEndstops()

# Display Results
# Actually set G10 offsets
print("Plate Offset = "+str(poffs['Z']))
print()
for tn in range(len(toffs)):
    print("Tool Offset for tool "+str(tn)+" is "+str(toffs[tn]['Z']))
print()
for tn in range(len(toffs)):
    print('G10 P'+str(tn)+' Z'+str(np.around((poffs['Z']-toffs[tn]['Z'])-0.1,2)))
