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

## Preparation steps
TAMV, ZTATP, and their associated plot functions utilize Python3+, and some additional libraries for GUI elements and processing. If you have some errors while running the code, consider running the following commands to install missing modules.

    sudo apt-get update
    sudo apt-get upgrade
    sudo apt-get install python3-matplotlib
    sudo apt-get install python3-pyqt5

## Installation

    cd
    git clone https://github.com/HaythamB/TAMV/

## Run
    usage: TAMV.py [-h] [-duet DUET] [-vidonly] [-camera CAMERA] [-cp CP CP]
                   [-repeat REPEAT] [-xray] [-loose] [-export] [-alternate]
    
    Program to allign multiple tools on Duet based printers, using machine vision.
    
    optional arguments:
      -h, --help      show this help message and exit
      -duet DUET      Name or IP address of Duet printer. You can use
                      -duet=localhost if you are on the embedded Pi on a Duet3.
      -vidonly        Open video window and do nothing else.
      -camera CAMERA  Index of /dev/videoN device to be used. Default 0.
      -cp CP CP       x y that will put 'controlled point' on carriage over
                      camera.
      -repeat REPEAT  Repeat entire alignment N times and report statistics
      -xray           Display edge detection output for troubleshooting.
      -loose          Run circle detection algorithm with less stringent
                      parameters to help detect worn nozzles.
      -export         Export repeat raw data to output.csv when done.
      -alternate      Try alternative nozzle detection method
 

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


