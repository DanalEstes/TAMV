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

    mkdir TAMV
    cd TAMV
    wget -N https://raw.githubusercontent.com/DanalEstes/TAMV/master/TAMV.py
    wget -N https://raw.githubusercontent.com/DanalEstes/DuetWebAPI/master/DuetWebAPI.py

## Run

    cd TAMV
    ./TAMV.py

It will guide you from there.   And/or run with -h for help. 
