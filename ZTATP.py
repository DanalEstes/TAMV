#!/usr/bin/env python3
# Python Script to align Z for multiple tools on Jubilee printer with Duet3d Controller
# Using a touchplate, and and endstop endput wire to every nozzle and that touchplate. 
#
# Copyright (C) 2020 Danal Estes all rights reserved.
# Released under The MIT License. Full text available via https://opensource.org/licenses/MIT
#
# Requires network connection to Duet based printer running Duet/RepRap V2 or V3
#
# Note: You MUST define Z with a PROBE in config.g.  Even if it is really an endstop switch, it is OK to define that as a probe. 
#

################################
# Edit these for your printer. #
################################
tl = [0,1]            # List of tools to be compared
yc = 225              # Y line that will clear parked tools when moving in X

xz = 288              # X coord of tool nozzle over flat plate to probe Z. 15x15mm area recommended.
yz = 285              # Y coord of tool nozzle over flat plate to probe Z. 15x15mm area recommended.

# Note: The particular probe command we use does NOT apply probe offsets. 
xp = 253              # X coord of Z-Probe over flat plate to probe Z. 15x15mm area recommended.
yp = 340              # Y coord of Z-Probe over flat plate to probe Z. 15x15mm area recommended.
#############################################
# Normally, change nothing below this line. #
#############################################

toffs = [[0] * 3 for i in range(len(tl))]
poffs = 0
from DuetWebAPI import DuetWebAPI as dwa
import numpy as np

# Get connected to the printer.  First, see if we are running on the Pi in a Duet3.
print("Attempting to connect to printer.")
prt = dwa.DuetWebAPI('http://127.0.0.1')
while (not prt.printerType()):
    ip = input("\nPlease Enter IP or name of printer\n")
    print("Attempting to connect to printer.")
    prt = dwa.DuetWebAPI('http://'+ip)

print("Connected to a Duet V"+str(prt.printerType())+" printer at "+prt.baseURL())

def probePlate():
    prt.resetEndstops()
    #prt.resetAxisLimits()
    prt.gCode('T-1')
    prt.gCode('G32 G28 Z')
    prt.gCode('G0 Z10 F1000')                        # Lower bed to avoid collision with hole plate. 
    prt.gCode('G0 Y'+str(yc)+'              F10000') # Move carriage to avoid other tools 
    prt.gCode('G0 X'+str(xp)+'              F10000') # Move BLt to axis of flat area 
    prt.gCode('G0 X'+str(xp)+' Y'+str(yp)+' F10000') # Move BLt to spot above flat part of plate
    prt.gCode('G30 S-1')                             # Probe plate with BLt
    global poffs
    poffs = prt.getCoords()['Z']                          # Capture the Z position at initial point of contact
    print("Plate Offset = "+str(poffs))
    prt.gCode('G0 Z10 F1000')                        # Lower bed to avoid collision with hole plate. 


def probeTool(tn):
    prt.resetEndstops()
    #prt.resetAxisLimits()
    prt.gCode('M400')
    #prt.gCode('G28 Z')
    prt.gCode('G10 P'+str(tn)+' Z0')                 # Remove z offsets from Tool 
    prt.gCode('T'+str(tn))                           # Pick up Tool 
    # Z Axis
    prt.gCode('M558 K0 P9 C"nil"')                   # Undef existing probe
    prt.gCode('M558 K0 P5 C"!io5.in" F200')          # Define nozzle<>bed wire as probe
    prt.gCode('G0 Z10 F1000')                        # Lower bed to avoid collision with hole plate. 
    prt.gCode('G0 Y'+str(yc)+'              F10000') # Move nozzle to avoid other tools 
    prt.gCode('G0 X'+str(xz)+'              F10000') # Move nozzle to axis of flat area 
    prt.gCode('G0 X'+str(xz)+' Y'+str(yz)+' F10000') # Move nozzle to spot above flat part of plate
    prt.gCode('G30 S-1')
    toffs[tn][2] = prt.getCoords()['Z']
    print("Tool Offset for tool "+str(tn)+" is "+str(toffs[tn][2]))
    prt.gCode('G0 Z10 F1000')                      # Lower bed to avoid collision with hole plate. 
    prt.gCode('M574 Z1 S1 P"nil"')
    prt.resetEndstops()
    #prt.resetAxisLimits()
    prt.gCode('T-1')
    prt.gCode('M400')
# End of probeTool function

#
# Main
#
probePlate()
for t in tl:
    probeTool(t)
#prt.resetAxisLimits()
prt.resetEndstops()

# Display Results
# Actually set G10 offsets
print("Plate Offset = "+str(poffs))
print()
for i in range(len(toffs)):
    tn = tl[i]
    print("Tool Offset for tool "+str(tn)+" is "+str(toffs[tn][2]))
print()
for i in range(len(toffs)):
    tn = tl[i]
    print('G10 P'+str(tn)+' Z'+str(np.around((poffs-toffs[i][2])-0.1,2)))
