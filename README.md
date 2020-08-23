# ©2020 Danal Estes, all rights reserved.
This fork is a modification for Jubilee printers running RRF2 and RRF3 and serves to extend the wonderful work Danal Estes created for the community. 

# TAMV
TAMV.py = Tool Align Machine Vision - for Duet based tool changing 3D printers.

* Runs on the Pi that has the USB or Pi camera 
* Requires network connection to DUET RepRap V2 or V3 based printer.
* This MAY be, but is not required to be, the Pi in a Duet3+Pi configuration
* Requires OpenCV installed on the Pi.  
  * See https://github.com/DanalEstes/installOpenCV for one way to install OpenCV
* MUST run on the graphic console, not SSH.  This can be physical, VNC, or any combination of the two.

P.S. Reminder: Never NEVER run a graphic app with 'sudo'.  It can break your XWindows (graphic) setup. Badly. 

## Installation

    cd
    git clone https://github.com/DanalEstes/TAMV
    git clone https://github.com/DanalEstes/DuetWebAPI

## Run

    cd TAMV
    ./TAMV.py

It will guide you from there.   And/or run with -h for help. 

# ZTATP
ZTATP.py = Z Tool Align Touch Plate - for Duet based tool changing 3D printers.

* Requires network connection to DUET RepRap V2 or V3 based printer.
* This MAY be, but is not required to be, the Pi in a Duet3+Pi configuration
## Installation

    See instructions above for TAMV.  It will be in the same directory. 

## Parameters
### -h, --help            
show help message and exit
  
### -duet DUET
Name or IP address of Duet printer. You can use -duet=localhost if you are on the embedded Pi on a Duet3.
  
### -touchplate TOUCHPLATE TOUCHPLATE
x y of center of a 15x15mm touch plate (these can be decimal values)
                        
### -pin PIN PIN
input pin to which wires from nozzles are attached (only in RRF3)
  
### -tool TOOL
set a run for an individual tool number

## Run

    cd TAMV
    ./ZTATP.py -touchplate X Y

NOTE: Requires Wiring! Each nozzle must be wired to the GPIO specified (default is io5.in, can be overriden on command line).  The touchplate must be grounded. Recommend about running with finger on power switch, in case a given touch does not stop. 


