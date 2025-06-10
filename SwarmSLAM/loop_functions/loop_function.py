#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random, math
import time, sys, os, json
import logging
from hexbytes import HexBytes

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.utils import Vector2D, Logger, Timer, Accumulator, mydict, identifiersExtract
from controllers.params import params as cp
from loop_functions.params import params as lp
from loop_functions.utils import *

from controllers.actusensors.groundsensor import Resource

random.seed(lp['generic']['seed'])

log_folder = lp['environ']['EXPERIMENTFOLDER'] + '/logs/0/'
os.makedirs(os.path.dirname(log_folder), exist_ok=True)   

# /* Global Variables */
#######################################################################
global startFlag, stopFlag, startTime
startFlag = False
stopFlag = False
startTime = 0

# Initialize RAM and CPU usage
global RAM, CPU
RAM = getRAMPercent()
CPU = getCPUPercent()
TPS = int(lp['environ']['TPS'])

# Initialize timers/accumulators/logs:
global clocks, accums, logs, other
clocks, accums, logs, other = dict(), dict(), dict(), dict()

clocks['simlog'] = Timer(10*TPS)
clocks['block']      = Timer(15*TPS)

global allrobots

def init():
   
    # Init logfiles for loop function
    file   = 'simulation.csv'
    header = ['TPS', 'RAM', 'CPU']
    logs['simulation'] = Logger(log_folder+file, header, ID = '0')

    file   = 'loop.csv'
    header = []
    logs['loop'] = Logger(log_folder+file, header, ID = '0')

    for log in logs.values():
        log.start()

def pre_step():
    global startFlag, startTime

    # Tasks to perform on the first time step
    if not startFlag:
        startTime = 0

    for robot in allrobots:
        for other_robot in allrobots:
            other_id = other_robot.param.get("id")

            robot.param.set(f"last_node_{other_id}", other_robot.param.get('my_last_node'))

def post_step():
    global startFlag, clocks, accums
    global RAM, CPU

    if not startFlag:
        startFlag = True

    # Logging of simulation simulation (RAM, CPU, TPS)   
    if clocks['simlog'].query():
        RAM = getRAMPercent()
        CPU = getCPUPercent()
    TPS = round(1/(time.time()-logs['simulation'].latest))
    logs['simulation'].log([TPS, CPU, RAM])

    # Logging of loop function variables
    logs['loop'].log([])

def is_experiment_finished():
    pass

def reset():
    pass

def destroy():
    pass

def post_experiment():
    print("Finished from Python!")




