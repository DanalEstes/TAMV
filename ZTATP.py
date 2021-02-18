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
# WARNING: RRF defaults to a probe offset of 0.7mm hardcoded in the source files that must be fixed using a G31 Z0 command in your config.g
#          Failure to apply this offset to Z=0 will result in tool offsets being incorrectly calculated as 0.7mm too close to the print surface.
#          THIS WILL DEFINITELY DAMAGE YOUR BUILD PLATE WHEN YOU ATTEMPT TO PRINT!

import datetime
import time

try: 
    import DuetWebAPI as DWA
except ImportError:
    print("Python Library Module 'DuetWebAPI.py' is required. ")
    print("Obtain from https://github.com/DanalEstes/DuetWebAPI ")
    print("Place in same directory as script, or in Python libpath.")
    exit(2)
import numpy as np
import argparse
import time

def init():
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Program to allign multiple tools in Z on Duet based printers, using a touch plate.', allow_abbrev=False)
    parser.add_argument('-duet',type=str,nargs=1,default=['localhost'],help='Name or IP address of Duet printer. You can use -duet=localhost if you are on the embedded Pi on a Duet3.')
    #parser.add_argument('-camera',type=str,nargs=1,choices=['usb','pi'],default=['usb'])
    parser.add_argument('-touchplate',type=float,nargs=2,default=[0.0,0.0],help="x y of center of a 15x15mm touch plate.",required=True)
    parser.add_argument('-pin',type=str,nargs=2,default='!io5.in',help='input pin to which wires from nozzles are attached (only in RRF3).')
    parser.add_argument('-tool',type=int,nargs=1,default=-1,help='(optional) set a run for an individual tool number referenced by index')
    args=vars(parser.parse_args())

    global duet, camera, tp, pin, tool
    duet   = args['duet'][0]
    tp     = args['touchplate']
    pin    = args['pin']
    tool   = args['tool']


    # Get connected to the printer.
    print('Attempting to connect to printer at '+duet)
    global prt
    prt = DWA.DuetWebAPI('http://'+duet)
    if (not prt.printerType()):
        print('Device at '+duet+' either did not respond or is not a Duet V2 or V3 printer.')
        exit(2)
    print("Connected to a Duet V"+str(prt.printerType())+" printer at "+prt.baseURL())

    if( tool is not - 1 ):
        tool = tool[0]
        if( tool > prt.getNumTools()-1 ):
            print()
            print('### ERROR IN PARAMETERS ###')
            print('You have specified tool ' + str(tool) + ' for probing, but it does not exist.')
            print('Your printer has '+str(prt.getNumTools())+' tools defined, so you must enter an index for tools between [0..' + str(prt.getNumTools()-1)+']')
            print('Please check your input parameters and try again.')
            exit(3)

    print('#########################################################################')
    print('# Important:                                                            #')
    print('# Your printer MUST be capable of mounting and parking every tool with  #')
    print('# no collisions between tools.                                          #')
    print('#                                                                       #')
    print('# Your Z probe must be a probe, not an endstop.  It is OK to define a   #')
    print('# simple switch as a probe.                                             #')
    print('#                                                                       #')
    print('# WARNING!! WARNING!!                                                   #')
    print('# The probing sequence will assume a Z offset of 45mm for every tool.   #')
    print('# During probing, any existing offsets will be temporarily cleared.     #')
    print('# Before running this script, make sure all tools will not collide      #')
    print('# with the build plate/probe plate with this 45 offset applied.         #')
    print('#                                                                       #')
    print('# Each nozzle MUST be wired to the specified input.  Test the wiring by #')
    print('# hand before running ZTATP.  If the wiring is wrong, probing will not  #')
    print('# stop, and machine damage could occur.                                 #')
    print('#########################################################################')
    print('Press enter to proceed')
    input()
    print()
    print("##################################")
    print("# Options in force for this run: #")
    print("# printer    = {0:18s}#".format(duet))
    print("# touchplate = {0:6.2f} {1:6.2f}     #".format(tp[0],tp[1]))
    if (prt.printerType() == 3):
        print("# firmware   = V3.x.x            #")
        print("# pin        = {0:18s}#".format(str(pin)))
    if (prt.printerType() == 2):
        print("# firmware   = V2.x.x            #")
        print("# pin        = Z_PROBE_IN        #")
    print("##################################")
    print()    

def probePlate():
    prt.resetEndstops()
    # HBHBHB: TODO - insert code to handle 0.7mm offset in RRF here!
    commandBuffer = []
    commandBuffer.append('T-1')                                        # Unmount any/all tools
    commandBuffer.append('G90 G1 X'+str(tp[0])+' Y'+str(tp[1])+' Z50 ')    # The real purpose of this is to move the probe into position with its correct offsets. 
    commandBuffer.append('M400')                                       # wait for buffer to clear
    prt.gCodeBatch(commandBuffer)
     # wait for probing setup moves to complete before prompting for probe plate
    while prt.getStatus() not in 'idle':
        time.sleep(1)
    print( 'The toolhead is parked in your designated XY position for probing.' )
    input( 'Please place the probe plate in the correct position on the bed and press ENTER to start.' )
    print( 'Probing touch plate...' )
    commandBuffer = []
    commandBuffer.append('M558 F300')                                  # set probing speed fast
    commandBuffer.append('G30')                                        # perform first probe
    commandBuffer.append('M558 F50')                                   # set probing speed slow
    commandBuffer.append('G30')                                        # perform second probe
    commandBuffer.append('G30 S-1')                                    # Now we can probe in such a way that Z is readable.
    commandBuffer.append('M400')                                       # wait for buffer to clear
    prt.gCodeBatch(commandBuffer)
    poffs = 0

    # wait for probing to complete before fetching offsets
    while prt.getStatus() not in 'idle':
        time.sleep(1) 
    
    poffs = prt.getCoords()['Z']                            # Capture the Z position at initial point of contact
    print("Touch plate offset = "+str(poffs))                     # Display captured offset to terminal
    prt.gCode('G91 G0 Z10 F1000 G90')                        # Lower bed to avoid collision
    return(poffs)

def probeTool(tn):
    commandBuffer=[]
    print()
    print( 'Probing tool ' + str(tn) + '..')
    print( 'ZTATP will prompt you to connect your lead once the tool is positioned over the touch plate.' )
    prt.resetEndstops()                                         # return all endstops to natural state from config.g definitions
    prt.gCode('M400')                                           # Wait for planner to empty
    while prt.getStatus() not in 'idle':
        #print("sleeping.")
        time.sleep(1)
    commandBuffer.append('G10 P'+str(tn)+' Z0')                            # Remove z offsets from Tool 
    commandBuffer.append('G91 G0 Z45 F1000 G90')                           # Lower bed to avoid collision (move to +45 relative in Z)
    commandBuffer.append('T'+str(tn))                                      # Pick up Tool number 'tn'
    prt.gCodeBatch(commandBuffer)
    duet2rrf3board = prt.checkDuet2RRF3()
    # Z Axis Probe setup
    # add code to switch pin based on RRF2 vs RRF3 definitions - RRF3 defaults to the original TAMV code
    if (prt.printerType() == 3):
        # START -- Code for RRF3
        print('*** RRF3 printer connected.')
        prt.gCode('M558 K0 P9 C"nil"')                              # Undef existing probe
        prt.gCode('M558 K0 P5 C"'+pin+'" F200 H50')                     # Define ( nozzle ) <--> ( probe plate ) as probe
        # END -- Code for RRF3
    if (prt.printerType() == 2):
        # START -- Code for RRF2
        # check if using a Duet 2 board with 3.2+ firmware
        if duet2rrf3board:
            print('** Duet 2 RRF 3.2+ board found, changing input pin to Z_PROBE_IN.')
            prt.gCode('M558 K0 P9 C"nil"')                              # Undef existing probe
            prt.gCode('M558 K0 P5 C"!^zprobe.in" F200 H50')
        else:
            # Define a normally-open (closes to ground when ACTIVE/TRIGGERED) probe connected between Z-Probe In and Ground (inverted logic to enable this behavior of NO switch)
            prt.gCode('M558 P5 I1 F200 H50')                             # Define ( nozzle ) <--> ( probe plate ) as probe (Z-Probe In pin connected to nozzle, probe plate is connected to ground)
        # END -- Code for RRF2
    
    prt.gCode('G0 X'+str(tp[0])+' Y'+str(tp[1])+' F10000')      # Move nozzle to spot above flat part of plate
    input('Connect probe lead to tool ' + str(tn) + ' and press ENTER to continue.')
    prt.gCode('M558 F300')                                      # set probing speed fast
    prt.gCode('G30 S-1')                                        # Initiate a probing sequence
    # wait for probing to complete before fetching offsets
    while prt.getStatus() not in 'idle':
        time.sleep(1) 
    print('First pass offset for tool ' + str(tn) + ': ' + str(prt.getCoords()['Z']) )
    prt.gCode('G91 G1 Z5 G90')                                  # move bed away from probe for second pass
    prt.gCode('M558 F50')                                      # set probing speed fast
    prt.gCode('G30 S-1')

    # wait for probing to complete before fetching offsets
    while prt.getStatus() not in 'idle':
        time.sleep(1)  

    toffs = prt.getCoords()['Z']                                # Fetch current Z coordinate from Duet controller
    print("Final offset for tool "+str(tn)+": "+str(toffs))    # Output offset to terminal for user to read
    prt.gCode('G91 G0 Z45 F1000 G90')                           # Lower bed to avoid collision
    if (prt.printerType() == 3):
        # START -- Code for RRF3
        prt.gCode('M574 Z1 S1 P"nil"')                              # Undef endstop for Z axis
        # END -- Code for RRF3
    if duet2rrf3board:
        # START -- Code for RRF3.2 on Duet 2 board
        prt.gCode('M574 Z1 S1 P"nil"')
        # END -- Code for RRF3
    prt.resetEndstops()                                         # return all endstops to natural state from config.g definitions
    input('Please disconnect probe lead to tool ' + str(tn) + ' and press ENTER to continue. Active tool is going to be docked.')
    prt.gCode('T-1')                                            # unload tool
    prt.gCode('M400')                                           # wait until all movement has finished
    return(toffs)                                               # return offsets and end function
# End of probeTool function

#
# Main
#
init()

# Get probe plate Z offset by probing using default-defined probe for G30
poffs = probePlate()

# initialize output variables
toolCoords = []
if (tool == -1):
    print( 'Running a probing sequence for all tools.')
    # start probing sequence for each tool defined on the connected printer
    for t in range(prt.getNumTools()):
        toolCoords.append(probeTool(t))
else:
    print('Running a probing sequence for only tool '+ str(tool) )
    toolCoords.append(probeTool(tool))
# restore all endstop definitions to the config.g defaults
prt.resetEndstops()

# Display Results and actually set G10 offsets
print()
print('########### Probing results')
print("Plate Offset = "+str(poffs))
if (tool == -1):
    for tn in range(len(toolCoords)):
        print("Final offset for tool "+str(tn)+": "+str(toolCoords[tn]))
    print()
    for tn in range(len(toolCoords)):
        finalOffset = (poffs-toolCoords[tn])-0.1
        print('G10 P'+str(tn)+' Z{:0.3f}'.format(finalOffset))
        # wait for probing to complete before setting offsets
        #while prt.getStatus() is 'processing':
        #    time.sleep(1) 
        prt.gCode('G10 P'+str(tn)+' Z{:0.3f}'.format(finalOffset))
else:
    print("Final offset for tool "+str(tool)+": "+str(toolCoords[0]))
    print()
    finalOffset = (poffs-toolCoords[0])-0.1
    print('G10 P'+str(tool)+' Z{:0.3f}'.format(finalOffset))
    # wait for probing to complete before setting offsets
    #while prt.getStatus() is 'processing':
    #    time.sleep(1) 
    prt.gCode('G10 P'+str(tool)+' Z{:0.3f}'.format(finalOffset))
print()
print("Tool offsets have been applied to the current printer.")
print("Please modify your tool definitions in config.g to reflect these newly measured values for persistent storage.")
