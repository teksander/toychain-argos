#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random, math
import time, sys, os, json
import logging
from hexbytes import HexBytes

sys.path += [os.environ['EXPERIMENTFOLDER']+'/controllers', \
             os.environ['EXPERIMENTFOLDER']+'/loop_functions', \
             os.environ['EXPERIMENTFOLDER']]

from controllers.aux import Vector2D, Logger, Timer, Accumulator, mydict, identifiersExtract
from controllers.groundsensor import Resource

from controllers.control_params import params as cp
from loop_params import params as lp
from loop_helpers import *

random.seed(lp['generic']['seed'])

log_folder = lp['environ']['EXPERIMENTFOLDER'] + '/logs/0/'
os.makedirs(os.path.dirname(log_folder), exist_ok=True)   


# /* Global Variables */
#######################################################################

# Other inits
global startFlag, stopFlag, startTime
startFlag = False
stopFlag = False
startTime = 0

# Get ticks per second from experimentconfig.sh file
TPS = int(lp['environ']['TPS'])

# Initialize timers/accumulators/logs:
global clocks, accums, logs, other
clocks, accums, logs, other = dict(), dict(), dict(), dict()

clocks['simlog'] = Timer(10*TPS)
accums['collection'] = [Accumulator() for i in range(lp['generic']['num_robots']+1)]

clocks['block']      = Timer(15*TPS)

global allrobots


def init():

    # Init robot parameters
    for robot in allrobots:
        robot.id = int(robot.variables.get_attribute("id"))


def pre_step():
    global startFlag, startTime

    # Tasks to perform on the first time step
    if not startFlag:
        startTime = 0

def post_step():
    global startFlag, clocks, accums

    if not startFlag:
        startFlag = True


def is_experiment_finished():
    pass

def reset():
    pass

def destroy():
    pass

def post_experiment():
    print("Finished from Python!")




