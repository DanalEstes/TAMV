# TAMV
TAMV.py = Tool Align Machine Vision - for Duet based tool changing 3D printers.

* Runs on the Pi that has the USB camera (Sorry, no PiCam at this moment)
* Requires network connection to DUET RepRap V2 or V3 based printer.
* Requires OpenCV installed on the Pi.  
  * See https://github.com/DanalEstes/installOpenCV for one way to install OpenCV
* MUST run on the graphic console, not SSH.  This can be physical, VNC, or any combination of the two.

Still very much in development as of 19 Mar 2020.
* At this time, it will show you tools, and machine vision center them
* It does not, yet, calculate G10 commands. 

P.S. Reminder: Never NEVER run a graphic app with 'sudo'.  It can break your XWindows (graphic) setup. Badly. 

