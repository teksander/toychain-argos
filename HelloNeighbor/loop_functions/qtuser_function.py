#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random, math
import sys, os
import hashlib

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.actusensors.groundsensor import Resource
from controllers.utils import Vector2D
from controllers.params import params as cp
from loop_functions.params import params as lp

lp['generic']['show_rays'] = False
lp['generic']['show_pos'] = True

# /* Global Variables */
#######################################################################
rob_diam   = 0.07/2

# /* Global Functions */
#######################################################################
global robot, environment

def hash_to_rgb(hash_value):
    # Generate a hash object from the input value
    hash_object = hashlib.sha256(hash_value.encode())

    # Get the first 3 bytes of the hash digest
    hash_bytes = hash_object.digest()[:3]

    # Convert the bytes to an RGB color value
    r = hash_bytes[0]
    g = hash_bytes[1]
    b = hash_bytes[2]

    # Return the RGB color value as a tuple
    return [r, g, b]

# /* ARGoS Functions */
#######################################################################

def init():
	pass

def draw_in_world():
	pass
	
def draw_in_robot():
	
	# Draw block hash and state hash with circles
	color_block = hash_to_rgb(robot.variables.get_attribute("block_hash"))
	color_state = hash_to_rgb(robot.variables.get_attribute("state_hash"))
	environment.qt_draw.circle([0,0,0.015], [], 0.075, color_block, True)
	environment.qt_draw.circle([0,0,0.010], [], 0.1, color_state, True)

def destroy():
	print('Closing the QT window')
