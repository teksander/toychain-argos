#!/usr/bin/env python3
import sys, time
import logging

class Peer(object):
    """ Establish the Peer class 
    """
    def __init__(self, _data, _range, _bearing, _id = None, _ip = None, _enode = None, _key = None):
        """ Constructor
        :type _id: str
        :param _id: id of the peer
        """

        # range-and-bearing information
        self.id       = _data[0]
        self.data     = _data
        self.range    = _range
        self.bearing  = _bearing
        
        # network identifiers
        self.ip    = _ip
        self.enode = _enode
        self.key   = _key

        # other stuff
        self.tStamp = time.time()
        self.isDead = False
        self.trials = 0
        self.timeout = 0
        self.timeoutStamp = 0

    @property
    def age(self):
        return time.time()-self.tStamp

    def resetAge(self):
        """ This method resets the timestamp of the robot meeting """ 
        self.tStamp = time.time()

    def kill(self):
        """ This method sets a flag which identifies aged out peers """
        self.isDead = True

    def setTimeout(self, timeout = 10):
        """ This method resets the timestamp of the robot timing out """ 
        self.trials = 0
        self.timeout = timeout
        self.timeoutStamp = time.time()

    def getData(self, indices=[0]):
        # If indices is given as a single integer, convert it to a list with one element
        if isinstance(indices, int):
            indices = [indices]
        
        # Collect the byte values from the specified indices
        byte_data = bytes([self.data[index] for index in indices])
        
        # Convert the byte sequence back into an integer
        data = int.from_bytes(byte_data, byteorder='big')

        return data

class ERANDB(object):
    """ Set up erandb transmitter on a background thread
    The __listen() method will be started and it will run in the background
    until the application exits.
    """
    def __init__(self, robot, dist = 200, tFreq = 0):
        """ Constructor
        :type dist: int
        :param dist: E-randb communication range (0=1meter; 255=0m)
        :type freq: int
        :param freq: E-randb transmit frequency (tip: 0 = no transmission; 4 = 4 per second)
        """

         # This robot ID
        self.robot = robot
        self.id = str(int(robot.variables.get_id()[2:])+1)
        self.newIds = set()
        self.tData = [0,0,0,0]
        self.setData(self.id)
        self.peers = []

    def step(self):
        """ This method runs in the background until program is closed """

        # /* Get a new peer ID */
        for data in self.getData():
            newId=data[0]

            if newId != self.id: 
                self.newIds.add(newId)

        self.peers = []
        for reading in self.robot.epuck_range_and_bearing.get_readings():
            self.peers.append(Peer(reading[0], reading[1], reading[2]))


    def getData(self):
        readings = self.robot.epuck_range_and_bearing.get_readings()
        return [reading[0] for reading in readings]

    def getRanges(self):
        readings = self.robot.epuck_range_and_bearing.get_readings()
        return [reading[1] for reading in readings]

    def getBearings(self):
        readings = self.robot.epuck_range_and_bearing.get_readings()
        return [reading[2] for reading in readings]

    def setData(self, data, indices=0):
        if isinstance(indices, int):
            indices = [indices]
        
        data = int(data)

        if data <= 255:
            self.tData[indices[-1]] = data
        else:
            byte_data = data.to_bytes(len(indices), byteorder='big')
            for i, index in enumerate(indices):
                self.tData[index] = byte_data[i]
        
        self.robot.epuck_range_and_bearing.set_data(self.tData)


    def getNew(self):
        temp = self.newIds
        self.newIds = set()

        return temp

    def start(self):
        pass

    def stop(self):
        pass
