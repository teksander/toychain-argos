#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random, math
import sys, os, psutil
import hashlib

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.utils import Vector2D
from loop_functions.params import params as lp

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

def getCPUPercent():
    return psutil.cpu_percent()

def getRAMPercent():
    return psutil.virtual_memory().percent

