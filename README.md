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

## Run

    cd TAMV
    ./ZTATP.py -touchplate X Y

NOTE: Requires Wiring! Each nozzle must be wired to the GPIO specified (default is io5.in, can be overriden on command line).  The touchplate must be grounded. Recommend about running with finger on power switch, in case a given touch does not stop. 


