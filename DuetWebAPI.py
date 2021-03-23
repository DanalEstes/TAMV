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
# Copyright (C) 2021 Haytham Bennani
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
            replyURL = (f'{self._base_url}'+'/rr_reply')
            reply = self.requests.get(replyURL,timeout=8)
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
        import time
        try:
            if (self.pt == 2):
                sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                r = self.requests.get(sessionURL,timeout=8)
                if not r.ok:
                    print('Error in getStatus session: ', r)
                buffer_size = 0
                while buffer_size < 150:
                    bufferURL = (f'{self._base_url}'+'/rr_gcode')
                    buffer_request = self.requests.get(bufferURL,timeout=8)
                    try:
                        buffer_response = buffer_request.json()
                        buffer_size = int(buffer_response['buff'])
                    except:
                        buffer_size = 149
                    replyURL = (f'{self._base_url}'+'/rr_reply')
                    reply = self.requests.get(replyURL,timeout=8)
                    if buffer_size < 150:
                        print('Buffer low: ', buffer_size)
                        time.sleep(0.6)
                while self.getStatus() not in "idle":
                    time.sleep(0.5)
                URL=(f'{self._base_url}'+'/rr_status?type=2')
                r = self.requests.get(URL,timeout=8)
                j = self.json.loads(r.text)
                replyURL = (f'{self._base_url}'+'/rr_reply')
                reply = self.requests.get(replyURL,timeout=8)
                jc=j['coords']['xyz']
                an=j['axisNames']
                ret=self.json.loads('{}')
                for i in range(0,len(jc)):
                    ret[ an[i] ] = jc[i]
                return(ret)
            if (self.pt == 3):
                URL=(f'{self._base_url}'+'/machine/status')
                r = self.requests.get(URL,timeout=8)
                j = self.json.loads(r.text)
                if 'result' in j: j = j['result']
                ja=j['move']['axes']
                ret=self.json.loads('{}')
                for i in range(0,len(ja)):
                    ret[ ja[i]['letter'] ] = ja[i]['userPosition']
                return(ret)
        except Exception as e1:
            print('Error in getStatus: ',e1 )
        
    def getCoordsAbs(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL,timeout=8)
            j = self.json.loads(r.text)
            jc=j['coords']['machine']
            an=j['axisNames']
            ret=self.json.loads('{}')
            for i in range(0,len(jc)):
                ret[ an[i] ] = jc[i]
            return(ret)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL,timeout=8)
            j = self.json.loads(r.text)
            if 'result' in j: j = j['result']
            ja=j['move']['axes']
            ret=self.json.loads('{}')
            for i in range(0,len(ja)):
                ret[ ja[i]['letter'] ] = ja[i]['machinePosition']
            return(ret)

    def getLayer(self):
        if (self.pt == 2):
           URL=(f'{self._base_url}'+'/rr_status?type=3')
           r = self.requests.get(URL,timeout=8)
           j = self.json.loads(r.text)
           s = j['currentLayer']
           return (s)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL,timeout=8)
            j = self.json.loads(r.text)
            if 'result' in j: j = j['result']
            s = j['job']['layer']
            if (s == None): s=0
            return(s)

    def getG10ToolOffset(self,tool):
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL,timeout=8)
            j = self.json.loads(r.text)
            if 'result' in j: j = j['result']
            ja=j['move']['axes']
            jt=j['tools']
            ret=self.json.loads('{}')
            to = jt[tool]['offsets']
            for i in range(0,len(to)):
                ret[ ja[i]['letter'] ] = to[i]
            return(ret)
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL,timeout=8)
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
            r = self.requests.get(URL,timeout=8)
            j = self.json.loads(r.text)
            jc=j['coords']['extr']
            return(len(jc))
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL,timeout=8)
            j = self.json.loads(r.text)
            if 'result' in j: j = j['result']
            return(len(j['move']['extruders']))

    def getNumTools(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL,timeout=8)
            j = self.json.loads(r.text)
            jc=j['tools']
            return(len(jc))
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL,timeout=8)
            j = self.json.loads(r.text)
            if 'result' in j: j = j['result']
            return(len(j['tools']))

    def getStatus(self):
        import time
        try:
            if (self.pt == 2):
                sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                r = self.requests.get(sessionURL,timeout=8)
                if not r.ok:
                    print('Error in getStatus session: ', r)
                buffer_size = 0
                while buffer_size < 150:
                    bufferURL = (f'{self._base_url}'+'/rr_gcode')
                    buffer_request = self.requests.get(bufferURL,timeout=8)
                    try:
                        buffer_response = buffer_request.json()
                        buffer_size = int(buffer_response['buff'])
                    except:
                        buffer_size = 149
                    replyURL = (f'{self._base_url}'+'/rr_reply')
                    reply = self.requests.get(replyURL,timeout=8)
                    if buffer_size < 150:
                        print('Buffer low: ', buffer_size)
                        time.sleep(0.6)
                URL=(f'{self._base_url}'+'/rr_status?type=2')
                r = self.requests.get(URL,timeout=8)
                j = self.json.loads(r.text)
                s=j['status']
                replyURL = (f'{self._base_url}'+'/rr_reply')
                reply = self.requests.get(replyURL,timeout=8)
                endsessionURL = (f'{self._base_url}'+'/rr_disconnect')
                r2 = self.requests.get(endsessionURL,timeout=8)
                if not r2.ok:
                    print('Error in getStatus end session: ', r2)
                if ('I' in s): return('idle')
                if ('P' in s): return('processing')
                if ('S' in s): return('paused')
                if ('B' in s): return('canceling')
                return(s)
            if (self.pt == 3):
                URL=(f'{self._base_url}'+'/machine/status')
                r = self.requests.get(URL,timeout=8)
                j = self.json.loads(r.text)
                if 'result' in j: 
                    j = j['result']
                _status = str(j['state']['status'])
                return( _status.lower() )
        except Exception as e1:
            print('Error in getStatus: ',e1 )
            return 'Error'

    def gCode(self,command):
        if (self.pt == 2):
            import time
            sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
            r = self.requests.get(sessionURL,timeout=8)
            buffer_size = 0
            while buffer_size < 150:
                bufferURL = (f'{self._base_url}'+'/rr_gcode')
                buffer_request = self.requests.get(bufferURL,timeout=8)
                try:
                    buffer_response = buffer_request.json()
                    buffer_size = int(buffer_response['buff'])
                except:
                    buffer_size = 149
                if buffer_size < 150:
                    print('Buffer low: ', buffer_size)
                    time.sleep(0.6)
            URL=(f'{self._base_url}'+'/rr_gcode?gcode='+command)
            r = self.requests.get(URL,timeout=8)
            replyURL = (f'{self._base_url}'+'/rr_reply')
            reply = self.requests.get(replyURL,timeout=8)
            #print( command, ' -> ', reply )
            endsessionURL = (f'{self._base_url}'+'/rr_disconnect')
            r2 = self.requests.get(endsessionURL,timeout=8)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/code/')
            r = self.requests.post(URL, data=command)
        if (r.ok):
           return(0)
        else:
            print("gCode command return code = ",r.status_code)
            print(r.reason)
            return(r.status_code)
    
    def gCodeBatch(self,commands):
        for command in commands:
            if (self.pt == 2):
                import time
                sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                r = self.requests.get(sessionURL,timeout=8)
                buffer_size = 0
                while buffer_size < 150:
                    bufferURL = (f'{self._base_url}'+'/rr_gcode')
                    buffer_request = self.requests.get(bufferURL,timeout=8)
                    buffer_response = buffer_request.json()
                    buffer_size = int(buffer_response['buff'])
                    time.sleep(0.5)
                URL=(f'{self._base_url}'+'/rr_gcode?gcode='+command)
                r = self.requests.get(URL,timeout=8)
                replyURL = (f'{self._base_url}'+'/rr_reply')
                reply = self.requests.get(replyURL,timeout=8)
                json_response = r.json()
                buffer_size = int(json_response['buff'])
                #print( "Buffer: ", buffer_size )
                #print( command, ' -> ', reply )
            if (self.pt == 3):
                URL=(f'{self._base_url}'+'/machine/code/')
                r = self.requests.post(URL, data=command)
            if not (r.ok):
                print("gCode command return code = ",r.status_code)
                print(r.reason)
                endsessionURL = (f'{self._base_url}'+'/rr_disconnect')
                r2 = self.requests.get(endsessionURL,timeout=8)
                return(r.status_code)
        endsessionURL = (f'{self._base_url}'+'/rr_disconnect')
        r2 = self.requests.get(endsessionURL,timeout=8)

    def getFilenamed(self,filename):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_download?name='+filename)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/file/'+filename)
        r = self.requests.get(URL,timeout=8)
        return(r.text.splitlines()) # replace('\n',str(chr(0x0a))).replace('\t','    '))

    def getTemperatures(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL,timeout=8)
            j = self.json.loads(r.text)
            return('Error: getTemperatures not implemented (yet) for RRF V2 printers.')
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r  = self.requests.get(URL,timeout=8)
            j  = self.json.loads(r.text)
            if 'result' in j: j = j['result']
            jsa=j['sensors']['analog']
            return(jsa)
        
    def checkDuet2RRF3(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL,timeout=8)
            j = self.json.loads(r.text)
            s=j['firmwareVersion']
            if s == "3.2":
                return True
            else:
                return False

    def getCurrentTool(self):
        import time
        try:
            if (self.pt == 2):
                sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                r = self.requests.get(sessionURL,timeout=8)
                if not r.ok:
                    print('Error in getStatus session: ', r)
                buffer_size = 0
                while buffer_size < 150:
                    bufferURL = (f'{self._base_url}'+'/rr_gcode')
                    buffer_request = self.requests.get(bufferURL,timeout=8)
                    try:
                        buffer_response = buffer_request.json()
                        buffer_size = int(buffer_response['buff'])
                    except:
                        buffer_size = 149
                    replyURL = (f'{self._base_url}'+'/rr_reply')
                    reply = self.requests.get(replyURL,timeout=8)
                    if buffer_size < 150:
                        print('Buffer low: ', buffer_size)
                        time.sleep(0.6)
                while self.getStatus() not in "idle":
                    time.sleep(0.5)
                URL=(f'{self._base_url}'+'/rr_status?type=2')
                r = self.requests.get(URL,timeout=8)
                j = self.json.loads(r.text)
                replyURL = (f'{self._base_url}'+'/rr_reply')
                reply = self.requests.get(replyURL,timeout=8)
                ret=j['currentTool']
                return(ret)
            if (self.pt == 3):
                URL=(f'{self._base_url}'+'/machine/status')
                r = self.requests.get(URL,timeout=8)
                j = self.json.loads(r.text)
                if 'result' in j: j = j['result']
                ret=j['state']['currentTool']
                return(ret)
        except Exception as e1:
            print('Error in getStatus: ',e1 )

    def getHeaters(self):
        import time
        try:
            if (self.pt == 2):
                sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                r = self.requests.get(sessionURL,timeout=8)
                if not r.ok:
                    print('Error in getStatus session: ', r)
                buffer_size = 0
                while buffer_size < 150:
                    bufferURL = (f'{self._base_url}'+'/rr_gcode')
                    buffer_request = self.requests.get(bufferURL,timeout=8)
                    try:
                        buffer_response = buffer_request.json()
                        buffer_size = int(buffer_response['buff'])
                    except:
                        buffer_size = 149
                    replyURL = (f'{self._base_url}'+'/rr_reply')
                    reply = self.requests.get(replyURL,timeout=8)
                    if buffer_size < 150:
                        print('Buffer low: ', buffer_size)
                        time.sleep(0.6)
                while self.getStatus() not in "idle":
                    time.sleep(0.5)
                URL=(f'{self._base_url}'+'/rr_status')
                r = self.requests.get(URL,timeout=8)
                j = self.json.loads(r.text)
                replyURL = (f'{self._base_url}'+'/rr_reply')
                reply = self.requests.get(replyURL,timeout=8)
                ret=j['heaters']
                return(ret)
            if (self.pt == 3):
                URL=(f'{self._base_url}'+'/machine/status')
                r = self.requests.get(URL,timeout=8)
                j = self.json.loads(r.text)
                if 'result' in j: j = j['result']
                ret=j['heat']['heaters']
                return(ret)
        except Exception as e1:
            print('Error in getStatus: ',e1 )

    def isIdle(self):
        try:
            if (self.pt == 2):
                sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                r = self.requests.get(sessionURL,timeout=8)
                if not r.ok:
                    print('Error in getStatus session: ', r)
                buffer_size = 0
                while buffer_size < 150:
                    bufferURL = (f'{self._base_url}'+'/rr_gcode')
                    buffer_request = self.requests.get(bufferURL,timeout=8)
                    try:
                        buffer_response = buffer_request.json()
                        buffer_size = int(buffer_response['buff'])
                    except:
                        buffer_size = 149
                    replyURL = (f'{self._base_url}'+'/rr_reply')
                    reply = self.requests.get(replyURL,timeout=8)
                    if buffer_size < 150:
                        print('Buffer low: ', buffer_size)
                        time.sleep(0.6)
                URL=(f'{self._base_url}'+'/rr_status?type=2')
                r = self.requests.get(URL,timeout=8)
                j = self.json.loads(r.text)
                s=j['status']
                replyURL = (f'{self._base_url}'+'/rr_reply')
                reply = self.requests.get(replyURL,timeout=8)
                endsessionURL = (f'{self._base_url}'+'/rr_disconnect')
                r2 = self.requests.get(endsessionURL,timeout=8)
                if not r2.ok:
                    print('Error in getStatus end session: ', r2)
                    return False
                if ('I' in s):
                    return True
                else: 
                    return False

            if (self.pt == 3):
                URL=(f'{self._base_url}'+'/machine/status')
                r = self.requests.get(URL,timeout=8)
                j = self.json.loads(r.text)
                if 'result' in j: 
                    j = j['result']
                status = str(j['state']['status'])
                if status.upper() == 'IDLE':
                    return True
                else:
                    return False
        except Exception as e1:
            print('Error in isIdle(): ',e1 )
            return False
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
        commandBuffer = []
        for each in [line for line in c if (('M574 ' in line) or ('M558 ' in line)                   )]:
            commandBuffer.append(self._nilEndstop(each))
        self.gCodeBatch(commandBuffer)
    

    def resetEndstops(self):
        import time
        c = self.getFilenamed('/sys/config.g')
        commandBuffer = []
        for each in [line for line in c if (('M574 ' in line) or ('M558 ' in line)                    )]:
            commandBuffer.append(self._nilEndstop(each))
        for each in [line for line in c if (('M574 ' in line) or ('M558 ' in line) or ('G31 ' in line))]:
            commandBuffer.append(each)
        self.gCodeBatch(commandBuffer)

    def resetAxisLimits(self):
        c = self.getFilenamed('/sys/config.g')
        commandBuffer = []
        for each in [line for line in c if 'M208 ' in line]:
            commandBuffer.append(each)
        self.gCodeBatch(commandBuffer)

    def resetG10(self):
        c = self.getFilenamed('/sys/config.g')
        commandBuffer = []
        for each in [line for line in c if 'G10 ' in line]:
            commandBuffer.append(each)
        self.gCodeBatch(commandBuffer)

    def resetAdvancedMovement(self):
        c = self.getFilenamed('/sys/config.g')
        commandBuffer = []
        for each in [line for line in c if (('M566 ' in line) or ('M201 ' in line) or ('M204 ' in line) or ('M203 ' in line))]:
            commandBuffer.append(each)
        self.gCodeBatch(commandBuffer)
