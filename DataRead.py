# -*- coding: utf-8 -*-
"""
Created on Tue Jul 28 13:40:24 2020

@author: ryan.robinson

ICE Commands: https://www.vescent.com/manuals/doku.php?id=ice

Absorption Traces: https://www.sacher-laser.com/applications/overview/absorption_spectroscopy/rubidium_d1.html

"""

import time
import os
from serial import serialwin32 as serial
import numpy as np
import sys, string,subprocess
import struct
import matplotlib.pyplot as plt

class ICE:
    def __init__(self,BoxNum,SlotNum):
        self.IceTimeout = .1 #Communication Timeout (seconds)
        self.IceByteRead = 256 #Number of bytes to read on ser.read()
        self.IceDelay = .01 #Delay in seconds after sending Ice Command to ensure execution
        self.BoxNum = int(BoxNum)
        self.SlotNum = int(SlotNum)
        self.IceSer = serial.Serial(port='COM'+str(int(self.BoxNum)),baudrate=115200,timeout=self.IceTimeout,parity='N',stopbits=1,bytesize=8)
        try:
            self.setSlave(self.SlotNum)
        except:
            print('Failed to set slot number')
        print('Current limit set to: '+str(self.sendCommandR('CurrLim 140')))
        return None
        
    
    ###Functions###
    def setSlave(self,SlotNum):
        print('Board changing from '+str(self.SlotNum)+' to '+str(SlotNum))
        self.SlotNum = int(SlotNum)
        return self.sendCommandR(('#slave '+str(self.SlotNum)))
    
    def sendCommandR(self,commandInput):
        '''Sends a command and returns the responsee'''
        command = (str(commandInput)+'\r\n').encode()
        print('Command Sent: '+commandInput)
        self.IceSer.write(command)
        self.wait(self.IceDelay)
        return self.getResponse()
    
    def sendCommand(self,commandInput):
        '''Sends a command and returns nothing'''
        command = (str(commandInput)+'\r\n').encode()
        print('Command Sent: '+commandInput)
        self.IceSer.write(command)
        self.wait(self.IceDelay)
        return None
    
    def getResponse(self):
        '''Return the response from the ICE box'''
        response = self.IceSer.readline()
        self.wait()
        try:
            print('ICE Response: '+response.decode())
            return response.decode()
        except:
            print('Failed to decode, got: '+response)
            return response
    
    def wait(self,num = .1):
        '''Forces program to wait num seconds.
        Note: Shortest Delay--> 1ms'''
        time.sleep(num)
        return None
    
    def bulkWait(self):
        '''Waits for the command to finish'''
        tries = 0
        while(True):
            status = self.sendCommandR('status')
            self.wait()
            tries += 1
            if(status.strip() == 'Success'):
                break
            if(tries > 50):
                print('Failed to wait.')
                raise Exception('Failed to wait')
        return None
    
    def bulkRead(self):
        '''Outputs 2 numpy 1-dimension arrays'''
        self.bulkWait()
        self.sendCommand('#bulkread 128')
        self.wait(2)
        data = str(self.IceSer.readline())
        data = data.replace('\\n','')
        data = data.replace(' ','')
        data = data.replace('b\'','')
        data = data.replace('\'','')
        data_bytes = bytearray.fromhex(data)
        data_bytes2 = struct.unpack('h'*int(len(data_bytes)/2),data_bytes)
        data_bytes3 = np.left_shift(data_bytes2,3)
        raw = np.array(data_bytes3,dtype=np.int16)
        topPlot = raw[0::2]
        botPlot = raw[1::2]
        return topPlot, botPlot
            
    def IceClose(self):
        self.IceSer.close()
                       

class RampCollect:
    def __init__(self,ICE):
        self.IB = ICE
        self.IB.sendCommandR('CurrLim 140')
        self.Curr = self.IB.sendCommandR('CurrSet 101.12')
        self.SvO = self.IB.sendCommandR('SvOffst 0.05')
        print(self.SvO)
        self.rampPoints = 256
        self.IB.sendCommandR('RampNum '+str(self.rampPoints))
        self.IB.sendCommandR('RampSwp 1')
        self.logfolder = str('\\'.join([os.getcwd(),'IceTracePlots',time.strftime("%Y-%m-%d_%H-%M-%S")]))
        os.makedirs(self.logfolder)
        print("Save Directory: "+self.logfolder)
        return None
    
    def getData(self):
        '''Runs the ramp, collects the data, and converts it to volts'''
        toVolts = 3.05*(10**3)
        self.IB.sendCommandR('RampRun')
        self.topData,self.botData = self.IB.bulkRead()
        self.topData = self.topData/toVolts
        self.botData = self.botData/toVolts
        return self.topData,self.botData
    
    def setSvOffset(self,offst = 0.05):
        '''Sets the servo offset'''
        self.SvO = self.IB.sendCommandR('SvOffst '+str(offst))
        return self.SvO
        
    
    def setCurrent(self,current):
        '''Sets the laser current'''
        self.Curr = self.IB.sendCommandR('CurrSet 101.12')
        return self.Curr
    
    def plotGraphs(self,offset = 0):
        '''Creates two graphs, input the servo offset to calculate the shift'''
        self.xAxis = np.arange(offset,offset+self.rampPoints)
        self.stripDataEnds()
        plt.figure(1)
        plt.title("Trace Derivative")
        plt.ylabel("DC Error [V]")
        plt.plot(self.xAxis,self.topData)
        plt.figure(2)
        plt.title("Trace")
        plt.ylabel("Error Input [V]")
        plt.plot(self.xAxis,self.botData)
        return None
    
    def stripDataEnds(self):
        '''Remove artifacts from data'''
        dataLen = len(self.xAxis)
        sFactor = int(dataLen/6)
        dStart = sFactor
        dEnd = dataLen - sFactor - 1
        self.xAxis = self.xAxis[dStart:dEnd]
        self.topData = self.topData[dStart:dEnd]
        self.botData = self.botData[dStart:dEnd]
    
    def takeTrace(self,offst = 0.05):
        '''Sets the servo offset and takes a trace'''
        self.setSvOffset(offst)
        sFactor = 0.84
        graphOffset = int(offst * self.rampPoints / sFactor)
        self.getData()
        self.saveData()
        self.plotGraphs(graphOffset)
        return None
    
    def saveData(self):
        '''Saves the data in a folder with the data labeled'''
        s = float(self.SvO)
        s = s*10
        s = round(s,2)
        s = str(s).replace(".","")
        a = self.logfolder+"\\topPlot"+s+".csv"
        b = self.logfolder+"\\bopPlot"+s+".csv"
        np.savetxt(a, self.topData, delimiter=",")
        np.savetxt(b, self.botData, delimiter=",")
        return None
    
    def rIceClose(self):
        self.IB.IceClose()
        return None

def main():
    #BoxNum = input('BoxNum = ')
    #Cs1SlotNum = input('CS1 SlotNum = ')
    BoxNum = 3
    Cs1SlotNum = 1
    IB = ICE(BoxNum,Cs1SlotNum)
    try:
        RC = RampCollect(IB)
        
#        RC.takeTrace(0)
        
        servoOffsets = np.arange(-4.5,2.5,.5)
        for i in servoOffsets:
            RC.takeTrace(i)
        
        IB.IceClose()
    except:
        print('fail')
        IB.IceClose()    
    
if(__name__=="__main__"):    
    main()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    