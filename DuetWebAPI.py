# Python Script containing a class to send commands to, and query specific information from,
#   Duet based printers running either Duet RepRap V2 or V3 firmware.
#
# Does NOT hold open the connection.  Use for low-volume requests.
# Does NOT, at this time, support Duet passwords.
#
# Not intended to be a gerneral purpose interface; instead, it contains methods
# to issue commands or return specific information. Feel free to extend with new
# methods for other information; please keep the abstraction for V2 V3 
#
# Copyright (C) 2020 Danal Estes all rights reserved.
# Released under The MIT License. Full text available via https://opensource.org/licenses/MIT
#
# Requires Python3

class DuetWebAPI:
    import requests
    import json
    import sys
    import time
    import datetime
    pt = 0
    _base_url = ''


    def __init__(self,base_url):
        self._base_url = base_url
        try:
            URL=(f'{self._base_url}'+'/rr_status?type=1')
            r = self.requests.get(URL,timeout=(2,60))
            j = self.json.loads(r.text)
            _=j['coords']
            self.pt = 2
            return
        except:
            try:
                URL=(f'{self._base_url}'+'/machine/status')
                r = self.requests.get(URL,timeout=(2,60))
                j = self.json.loads(r.text)
                _=j
                self.pt = 3
                return
            except:
                print(self._base_url," does not appear to be a RRF2 or RRF3 printer", file=self.sys.stderr)
                return 
####
# The following methods are a more atomic, reading/writing basic data structures in the printer. 
####

    def printerType(self):
        return(self.pt)

    def baseURL(self):
        return(self._base_url)

    def getCoords(self):
        #while self.getStatus() not in 'idle':
        #    time.sleep(0.2)
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            jc=j['coords']['xyz']
            an=j['axisNames']
            ret=self.json.loads('{}')
            for i in range(0,len(jc)):
                ret[ an[i] ] = jc[i]
            return(ret)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            ja=j['move']['axes']
            #d=j['move']['drives']
            #ad=self.json.loads('{}')
            #for i in range(0,len(ja)):
            #    ad[ ja[i]['letter'] ] = ja[i]['drives'][0]
            ret=self.json.loads('{}')
            for i in range(0,len(ja)):
                ret[ ja[i]['letter'] ] = ja[i]['userPosition']
            return(ret)
        
    def getCoordsAbs(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            jc=j['coords']['machine']
            an=j['axisNames']
            ret=self.json.loads('{}')
            for i in range(0,len(jc)):
                ret[ an[i] ] = jc[i]
            return(ret)
        '''if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            ja=j['move']['axes']
            #d=j['move']['drives']
            #ad=self.json.loads('{}')
            #for i in range(0,len(ja)):
            #    ad[ ja[i]['letter'] ] = ja[i]['drives'][0]
            ret=self.json.loads('{}')
            for i in range(0,len(ja)):
                ret[ ja[i]['letter'] ] = ja[i]['userPosition']
            return(ret)'''

    def getLayer(self):
        if (self.pt == 2):
           URL=(f'{self._base_url}'+'/rr_status?type=3')
           r = self.requests.get(URL)
           j = self.json.loads(r.text)
           s = j['currentLayer']
           return (s)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            s = j['job']['layer']
            if (s == None): s=0
            return(s)

    def getG10ToolOffset(self,tool):
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            ja=j['move']['axes']
            jt=j['tools']
            ret=self.json.loads('{}')
            to = jt[tool]['offsets']
            for i in range(0,len(to)):
                ret[ ja[i]['letter'] ] = to[i]
            return(ret)
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            ja=j['axisNames']
            jt=j['tools']
            ret=self.json.loads('{}')
            to = jt[tool]['offsets']
            for i in range(0,len(to)):
                ret[ ja[i] ] = to[i]
            return(ret)

        return({'X':0,'Y':0,'Z':0})      # Dummy for now              

    def getNumExtruders(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            jc=j['coords']['extr']
            return(len(jc))
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            return(len(j['move']['extruders']))

    def getNumTools(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            jc=j['tools']
            return(len(jc))
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            return(len(j['tools']))

    def getStatus(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            s=j['status']
            if ('I' in s): return('idle')
            if ('P' in s): return('processing')
            if ('S' in s): return('paused')
            if ('B' in s): return('canceling')
            return(s)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            return(j['state']['status'])

    def gCode(self,command):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_gcode?gcode='+command)
            r = self.requests.get(URL)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/code/')
            r = self.requests.post(URL, data=command)
        if (r.ok):
           return(0)
        else:
            print("gCode command return code = ",r.status_code)
            print(r.reason)
            return(r.status_code)

    def getFilenamed(self,filename):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_download?name='+filename)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/file/'+filename)
        r = self.requests.get(URL)
        return(r.text.splitlines()) # replace('\n',str(chr(0x0a))).replace('\t','    '))

    def getTemperatures(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL)
            j = self.json.loads(r.text)
            return('Error: getTemperatures not implemented (yet) for RRF V2 printers.')
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r  = self.requests.get(URL)
            j  = self.json.loads(r.text)
            jsa=j['sensors']['analog']
            return(jsa)



####
# The following methods provide services built on the atomics above. 
####


    # Given a line from config g that defines an endstop (N574) or Z probe (M558),
    # Return a line that will define the same thing to a "nil" pin, i.e. undefine it
    def _nilEndstop(self,configLine):
        ret = ''
        for each in [word for word in configLine.split()]: ret = ret + (each if (not (('P' in each[0]) or ('p' in each[0]))) else 'P"nil"') + ' '
        return(ret)

    def clearEndstops(self):
      c = self.getFilenamed('/sys/config.g')
      for each in [line for line in c if (('M574 ' in line) or ('M558 ' in line)                   )]: self.gCode(self._nilEndstop(each))

    def resetEndstops(self):
      c = self.getFilenamed('/sys/config.g')
      for each in [line for line in c if (('M574 ' in line) or ('M558 ' in line)                    )]: self.gCode(self._nilEndstop(each))
      for each in [line for line in c if (('M574 ' in line) or ('M558 ' in line) or ('G31 ' in line))]: self.gCode(each)

    def resetAxisLimits(self):
      c = self.getFilenamed('/sys/config.g')
      for each in [line for line in c if 'M208 ' in line]: self.gCode(each)

    def resetG10(self):
      c = self.getFilenamed('/sys/config.g')
      for each in [line for line in c if 'G10 ' in line]: self.gCode(each)
