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
        self.rampSweep = 0.5
        self.IB.sendCommandR('RampSwp '+str(self.rampSweep))
        self.logfolder = str('\\'.join([os.getcwd(),'IceTracePlots',time.strftime("%Y-%m-%d_%H-%M-%S"),'UnstitchedData']))
        self.logfolderStitched = str('\\'.join([os.getcwd(),'IceTracePlots',time.strftime("%Y-%m-%d_%H-%M-%S"),'StitchedData']))
        self.logfolderPlots = str('\\'.join([os.getcwd(),'IceTracePlots',time.strftime("%Y-%m-%d_%H-%M-%S"),'Plots']))
        os.makedirs(self.logfolder)
        os.makedirs(self.logfolderStitched)
        os.makedirs(self.logfolderPlots)
        print("Save Directory: "+self.logfolder)
        self.xAxisTotal = []
        self.traceDataTotal = []
        self.derDataTotal = []
        return None
    
    def getData(self):
        '''
        Runs the ramp, collects the data, and converts it to volts
        derData: derivative trace derived from converting fm to am
        traceData: absorption trace
        '''
        toVolts = 3.05*(10**3)
        self.IB.sendCommandR('RampRun')
        self.derData,self.traceData = self.IB.bulkRead()
        self.derData = self.derData/toVolts
        self.traceData = self.traceData/toVolts
        return self.derData,self.traceData
    
    def setSvOffset(self,offst = 0.05):
        '''Sets the servo offset'''
        self.SvO = self.IB.sendCommandR('SvOffst '+str(offst))
        return self.SvO
   
    def setCurrent(self,current):
        '''Sets the laser current'''
        self.Curr = self.IB.sendCommandR('CurrSet 101.12')
        return self.Curr
    
    def plotGraphs(self,):
        '''Creates two graphs, input the servo offset to calculate the shift'''       
        plt.figure(1)
        plt.title("Raw ICE Derivative Trace")
        plt.ylabel("DC Error [V]")
        plt.xlabel("Ramp Voltage [V]")
        plt.plot(self.xAxis,self.derData)
        plt.figure(2)
        plt.title("Raw ICE Trace")
        plt.ylabel("Error Input [V]")
        plt.xlabel("Ramp Voltage [V]")
        plt.plot(self.xAxis,self.traceData)
        return None
    
    def genXAxis(self,SvO):
        sFactor = 0.83 # Determined expirementally to overlap plots
        self.xAxis = np.linspace(SvO - sFactor*self.rampSweep/2,SvO + sFactor*self.rampSweep/2,self.rampPoints)
        return self.xAxis
    
    def stripDataEnds(self):
        '''Remove artifacts from data'''
        dataLen = len(self.xAxis)
        sFactor = int(dataLen/6)
        dStart = sFactor
        dEnd = dataLen - sFactor - 1
        self.xAxis = self.xAxis[dStart:dEnd]
        self.derData = self.derData[dStart:dEnd]
        self.traceData = self.traceData[dStart:dEnd]
        return None
    
    def saveData(self):
        '''Saves the data in a folder with the data labeled'''
        s = float(self.SvO)
        s = s*10
        s = round(s,2)
        s = str(s).replace(".","")
        a = self.logfolder+"\\rawIceDerivative"+s+".csv"
        b = self.logfolder+"\\rawIceTrace"+s+".csv"
        np.savetxt(a, (self.derData), delimiter=",")
        np.savetxt(b, (self.traceData), delimiter=",")
        return None
    
    def appendData(self):
        '''Appends the data so that we may work with it as 1 big array into several smaller arrays. 
           Must be exectued AFTER completion of offset scan loops'''
        self.xAxisTotal = np.append(self.xAxisTotal,self.xAxis)
        self.derDataTotal = np.append(self.derDataTotal,self.derData)
        self.traceDataTotal = np.append(self.traceDataTotal,self.traceData)
        return None
    
    def modifyAppendData(self):
        '''Reverses and flips the plots to make them more readable'''
        self.traceDataTotalMod = np.flip(-1*self.traceDataTotal)
        self.derDataTotalMod = np.flip(self.derDataTotal)
        return None
        
    
    def plotAppendData(self):
        plt.figure(3)
        plt.title("Raw ICE Total Derivative Trace")
        plt.ylabel("DC Error [V]")
        plt.xlabel("Ramp Voltage [V]")
        plt.plot(self.xAxisTotal,self.derDataTotal)
        plt.figure(4)
        plt.title("Raw Total ICE Trace")
        plt.ylabel("Error Input [V]")
        plt.xlabel("Ramp Voltage [V]")
        plt.plot(self.xAxisTotal,self.traceDataTotal)
        plt.figure(5)
        plt.title("Mod Total ICE Derivative Trace")
        plt.ylabel("Error Input [V]")
        plt.xlabel("Ramp Voltage [V]")
        plt.plot(self.xAxisTotal,self.derDataTotalMod)
        plt.figure(6)
        plt.title("Mod Total ICE Trace")
        plt.ylabel("Error Input [V]")
        plt.xlabel("Ramp Voltage [V]")
        plt.plot(self.xAxisTotal,self.traceDataTotalMod)        
        return None
        
    def saveAppendData(self):
        '''Saves the appended data in a folder with the data labeled'''
        a = self.logfolderStitched+"\\total-raw-derivative-data-set.csv"
        b = self.logfolderStitched+"\\total-raw-trace-data-set.csv"
        c = self.logfolderStitched+"\\total-modified-derivative-data-set.csv"
        d = self.logfolderStitched+"\\total-modified-trace-data-set.csv"
        e = self.logfolderStitched+"\\total-raw-xAxis.csv"
        f = self.logfolderStitched+"\\total-modified-xAxis.csv"
        np.savetxt(a, (self.derDataTotal), delimiter=",")
        np.savetxt(b, (self.traceDataTotal), delimiter=",")    
        np.savetxt(c, (self.traceDataTotalMod), delimiter=",") 
        np.savetxt(d, (self.traceDataTotalMod), delimiter=",")
        np.savetxt(e, (self.xAxisTotal), delimiter=",") 
        return None
    
    def takeTrace(self,offst = 0.05):
        '''Sets the servo offset and takes a trace'''
        self.setSvOffset(offst)
        self.genXAxis(offst)
        self.getData()
        self.saveData()
        self.stripDataEnds()
        self.appendData()
        self.plotGraphs()
        return None    
    
    def postLoopDataProcessing(self):
        '''Run only after all data has been aquired'''
        self.modifyAppendData()
        self.saveAppendData()
        self.plotAppendData()
        self.savePlots()
        return None
    
    def savePlots(self):
        plt.figure(1)
        plt.savefig(self.logfolderPlots+"\\raw-stitched-derivative.png")
        plt.figure(2)
        plt.savefig(self.logfolderPlots+"\\raw-stitched-traces.png")
        plt.figure(3)
        plt.savefig(self.logfolderPlots+"\\total-raw-derivative.png")
        plt.figure(4)
        plt.savefig(self.logfolderPlots+"\\total-raw-traces.png")
        plt.figure(5)
        plt.savefig(self.logfolderPlots+"\\total-modified-derivative.png")    
        plt.figure(6)
        plt.savefig(self.logfolderPlots+"\\total-modified-traces.png")   
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
        servoOffsets = np.arange(-4.5,2.5,.25)
        for i in servoOffsets:
            RC.takeTrace(i)
        RC.postLoopDataProcessing()
        IB.IceClose()
    except:
        print("Error:", sys.exc_info()[0])
        IB.IceClose()
    return None
    
if(__name__=="__main__"):    
    main()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    