#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random, math
import sys, os

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.utils import Vector2D
from controllers.params import params as cp

from loop_functions.utils import hash_to_rgb
from loop_functions.params import params as lp

# /* Global Variables */
#######################################################################
rob_diam   = 0.07/2

# /* Global Functions */
#######################################################################
global robot, environment

# /* ARGoS Functions */
#######################################################################

def init():
    pass
    
def draw_in_world():
    pass
	
def draw_in_robot():
    
    # Draw block hash and state hash with circles
    color_state = hash_to_rgb(robot.variables.get_attribute("state_hash"))
    color_block = hash_to_rgb(robot.variables.get_attribute("block_hash"))
    color_mempl = hash_to_rgb(robot.variables.get_attribute("mempl_hash"))
    
    tx_count = int(robot.variables.get_attribute("mempl_size"))

    environment.qt_draw.circle([0,0,0.010], [], 0.100, color_state, True)
    environment.qt_draw.circle([0,0,0.011], [], 0.075, color_block, True)
    environment.qt_draw.circle([0,0,0.012+0.002*tx_count], [], 0.050, color_mempl, True)

def destroy():
    print('Closing the QT window')
