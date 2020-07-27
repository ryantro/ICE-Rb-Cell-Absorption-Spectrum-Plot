# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 16:57:41 2020

@author: ryan.robinson
"""
import time
import os
from serial import serialwin32 as serial
import numpy as np
import sys, string,subprocess
#import nidaqmx

class ICE:
    def __init__(self,BoxNum,SlotNum):
        self.BoxNum = int(BoxNum)
        self.SlotNum = int(SlotNum)
        return None
        
    IceTimeout = .1 #Communication Timeout (seconds)
    IceByteRead = 256 #Number of bytes to read on ser.read()
    IceDelay = .01 #Delay in seconds after sending Ice Command to ensure execution

    ###Functions###
    def setSlot(self,SlotNum):
        self.SlotNum = SlotNum
        print('Changed Slot To: '+str(SlotNum))
        return None
    
    def wait(self,num):
        '''Forces program to wait num seconds.
        Note: Shortest Delay--> 1ms'''
        time.sleep(num)
        return None
    
    def IceSend(self, CommandInput):
        '''Function that sends a serial string command to ICE Box 
        Input: ICE Box Number[int], ICE Slot Number[int], CommandInput[str]
        Output: None (unless print line uncommented)/Read buffer always emptied!
        Note 1: Enter a slot number outside range(1-8) and function sends command directly
        to master board (ex. '#PowerOff' Command)
        Note 2: COM Port is opened/closed each time funciton is run'''
        
        #Open Port w/ ICE COM Default Settings
        IceSer = serial.Serial(port='COM'+str(int(self.BoxNum)),baudrate=115200,timeout=self.IceTimeout,parity='N',stopbits=1,bytesize=8)
        self.wait(.001)
        
        #Define Command and Send (perform read after each command to maintain synchronicity)
        if int(self.SlotNum) in range(1,9): #If a Valid Slot Number is input, send command to slot num
            #Define Commands        
            MasterCommand = str('#slave ' + str(int(self.SlotNum)) + '\r\n')
            SlaveCommand = str(str(CommandInput) + '\r\n')
            
            #Send Commands/Close Port
            IceSer.write(MasterCommand.encode())
            self.wait(self.IceDelay)
            IceOutputSlave = IceSer.read(self.IceByteRead).decode() #Read Buffer
            self.wait(self.IceDelay)
            IceSer.write(SlaveCommand.encode())
            self.wait(self.IceDelay)
            IceOutputReturn = IceSer.read(self.IceByteRead).decode() #Read Buffer
            self.wait(self.IceDelay)
            IceSer.close() #Close COM Port
    
            #Return Output       
            return IceOutputReturn
            print( ' ')
            print( 'Master Board Return: ', IceOutputSlave)
            print( 'Slave Board Return: ', IceOutputReturn)
            7
        else: #Command sent only to Master Board (preceding '#', no slot num to specify)
            #Define Command        
            MasterCommand = str('#' + str(CommandInput) + '\r\n')
            
            #Send Commands/Close Port
            IceSer.write(MasterCommand)
            self.wait(self.IceDelay)
            IceOutputReturn = IceSer.read(self.IceByteRead) #Read Buffer
            self.wait(self.IceDelay)
            IceSer.close() #Close COM Port
            
            #Return Output
            return IceOutputReturn
            print( ' ')
            print( 'Master Board Return: ', IceOutputReturn)

# GET DATA FROM NI-DAQmx
def nidaxgrab():
    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan("Dev1/ai0")
        data = task.read(number_of_samples_per_channel=1)
        power = ' '.join([str(elem) for elem in data]) 
    return power
            
            
def CurrentSet(IB,current):
    return IB.IceSend(1,1,'CurrSet '+str(current))

def makefolder(newpath):
    if not os.path.exists(newpath):
        os.makedirs(newpath)
    return newpath

def loggingLoops(IB,iArray):
    '''
    Creates a directory and logs laser current and laser power. 
    The purpose of this is to find at which current mode-hops occur by seeing a sharp change in power
    '''
    logDir = makefolder(os.getcwd()+'\\testlogging\\'+time.strftime("%Y-%m-%d_%H-%M-%S"))
    print('Log Dirrectory: %' %logDir)
    IB.IceSend(1,1,'CurrLim 125')
    ### OPEN FILE ###
    PIData = open(logDir+'\\PIData.csv', 'a+')
    ### LOGGING LOOPS ###
    for i in iArray:
        setCurrent = IB.IceSend('CurrSet '+str(i))
        time.sleep(1) #Maybe this needs to be greater
        line = str(setCurrent)+','+str(nidaxgrab())
        print(line)
        PIData.write(line)
    ### CLOSE FILE ###
    PIData.close()
    return None

     
def main():
    BoxNum = input('Box Num: ')
    SlotNum = input('Slot Num of CS1 Board: ')
    IB = ICE(BoxNum,SlotNum)
    iArray = np.linspace(0,100,100)
    iArray = np.round(iArray,1)
    loggingLoops(IB,iArray)
    return None

if(__name__=="__main__"):
    main()