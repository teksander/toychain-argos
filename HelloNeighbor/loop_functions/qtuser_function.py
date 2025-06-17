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

from toychain.src.utils.helpers import gen_enode
from toychain.src.Node import Node
from toychain.src.Block import Block
from toychain.src.consensus.ProofOfAuth import ProofOfAuthority
from scs.greeter import Contract as State

lp['generic']['show_rays'] = False
lp['generic']['show_pos'] = True

# /* Global Variables */
#######################################################################
rob_diam   = 0.07/2

# /* Global Functions */
#######################################################################
global robot, environment

# Initialize the monitoring glassnode
enodes  = [gen_enode(i+1) for i in range(int(lp['environ']['NUMROBOTS']))]
GENESIS = Block(0, 0000, [], enodes, 0, 0, 0, nonce = 1, state = State())

glassnode = Node('0', '127.0.0.1', 1233, ProofOfAuthority(genesis = GENESIS))

# /* ARGoS Functions */
#######################################################################

def init():
    pass
    
def draw_in_world():

    # Update glassnode
	glassnode.step()
	if glassnode.custom_timer.time() == 10:
		glassnode.add_peers(enodes)
		glassnode.start()
		glassnode.run_explorer()
	
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
