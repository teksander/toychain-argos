#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random, math
import time, sys, os, json
# import logging
# from hexbytes import HexBytes
import matplotlib.pyplot as plt

experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [os.environ['MAINFOLDER'], \
             os.environ['EXPERIMENTFOLDER']+'/controllers', \
             os.environ['EXPERIMENTFOLDER']
            ]

# from controllers.aux import Vector2D, Logger, Timer, Accumulator, mydict, identifiersExtract
# from controllers.groundsensor import Resource

# from controllers.control_params import params as cp
# from loop_params import params as lp
# from loop_helpers import *

from toychain.src.consensus.ProofOfAuth import ProofOfAuthority
from toychain.src.Node import Node


# /* Global Variables */
#######################################################################
w3 = Node(0, '127.0.0.1', 1230, ProofOfAuthority())

# Initialize plot
plt.ion()  # Turn on interactive mode
fig, ax = plt.subplots()
plt.pause()

# Set axis limits
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)

last = [0,0,0,0,0,0,0,0,0]
def init():
    pass

def pre_step():
    pass

def post_step():
    pass
    # x = random.random()
    # y = random.random()

    # # Add a new point
    # ax.scatter(x, y, color='blue')

    # # Manually force a plot update
    # plt.draw()
    # plt.show()
    # all_patches = w3.sc.getPatches()
    # x = []
    # y = []
    # for patch in all_patches:
    #     if len(patch['Q']) > last[patch['id']]:
    #         epoch = patch['epoch']
    #         block = w3.get_block_number()
    #         AP = patch['util']*epoch['price'] - epoch['ATC'][-1]

    #         x.append(block)
    #         y.append(AP)
        
    #         ax.scatter(x, y, color='blue')
    #         plt.draw()

    #         last[patch['id']] = len(patch['Q'])


def reset():
    pass

def destroy():
    pass

def post_experiment():
    pass




