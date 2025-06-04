#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random, math
import sys, os, psutil

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.utils import Vector2D
from loop_functions.params import params as lp

for file in lp['files'].values():
    open(file, 'w+').close()


def is_in_circle(point, center, radius):
    dx = abs(point[0] - center[0])
    dy = abs(point[1] - center[1])

    if dx**2 + dy**2 <= radius**2:
        return True 
    else:
        return False

def is_in_rectangle(point, center, width, height = None):
    if not height:
        height = width
    dx = abs(point[0] - center[0])
    dy = abs(point[1] - center[1])

    if dx < width/2 and dy < height/2:
        return True 
    else:
        return False

def getCPUPercent():
    return psutil.cpu_percent()

def getRAMPercent():
    return psutil.virtual_memory().percent
