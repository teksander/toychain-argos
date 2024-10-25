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
res_diam   = 0.015
rob_diam   = 0.07/2
res_height = 0.01

# Store the position of the market and cache
market   = Resource({"x":lp['market']['x'], "y":lp['market']['y'], "radius": lp['market']['r']})
cache    = Resource({"x":lp['cache']['x'], "y":lp['cache']['y'], "radius": lp['cache']['r']})

# /* Global Functions */
#######################################################################
global robot, environment

def draw_market():
	environment.qt_draw.circle([market.x, market.y, 0.001],[], market.radius, 'custom2', True)
	environment.qt_draw.circle([cache.x, cache.y, 0.001],[], cache.radius, 'custom2', False)

def draw_patches():

	with open(lp['files']['patches'], 'r') as f:
		allresources = [Resource(line) for line in f]

	for res in allresources:
		environment.qt_draw.circle([res.x, res.y, 0.001],[], res.radius, res.quality, False)
		environment.qt_draw.circle([res.x, res.y, 0.001],[], res.radius*(res.quantity/lp['patches']['qtty_max'][res.quality]), res.quality, True)
		environment.qt_draw.circle([res.x, res.y, 0.0005],[], res.radius, 'gray90', True)
	
	resources = eval(robot.variables.get_attribute("verified"))
	for res in resources:
		x = res[0]
		y = res[1]
		qlty = res[2]
		environment.qt_draw.circle([x, y, 0.00025],[], lp['patches']['radii'][qlty]+0.03, 'black', True)

	resources = eval(robot.variables.get_attribute("pending"))
	for res in resources:
		x = res[0]
		y = res[1]
		qlty = res[2]
		environment.qt_draw.circle([x, y, 0.00025],[], lp['patches']['radii'][qlty]+0.03, 'gray90', True)

def draw_resources_on_robots():
	quantity = int(robot.variables.get_attribute("quantity"))
	quality  = robot.variables.get_attribute("hasResource")

	# Draw carried quantity
	# environment.qt_draw.cylinder([0, 0, 0.08],[], rob_diam * (quantity/cp['max_Q']), res_height, quality)
	for i in range(quantity):
		environment.qt_draw.cylinder([0, 0, (i*1.3)*res_height + 0.075],[], 0.5 * rob_diam, res_height, quality)

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

	# Draw the Market
	draw_market()

	# Draw resource patches
	draw_patches()
	
def draw_in_robot():

	# Draw resources carried by robots
	draw_resources_on_robots()

	# Draw representation of robot state machine
	robot_state = robot.variables.get_attribute("fsm")+"12"
	environment.qt_draw.circle([0, 0, 0.010],[], 0.1, hash_to_rgb(robot_state), True)

	# # Draw block/state/mempool hash as colored circles
	# color_state = hash_to_rgb(robot.variables.get_attribute("state_hash"))
	# color_block = hash_to_rgb(robot.variables.get_attribute("block_hash"))
	# color_mempl = hash_to_rgb(robot.variables.get_attribute("mempl_hash"))
	# tx_count = int(robot.variables.get_attribute("mempl_size"))
	# environment.qt_draw.circle([0,0,0.010], [], 0.100, color_state, True)
	# environment.qt_draw.circle([0,0,0.011], [], 0.075, color_block, True)
	# environment.qt_draw.circle([0,0,0.012+0.002*tx_count], [], 0.050, color_mempl, True)

	# Draw rays to w3 peers
	w3_peers = eval(robot.variables.get_attribute("w3_peers"))
	for peer_rb in w3_peers:
		environment.qt_draw.ray([0, 0 , 0.01],[peer_rb[0]*math.cos(peer_rb[1]), peer_rb[0]*math.sin(peer_rb[1]) , 0.01], 'red', 0.15)


# Draw block number with boxes
	# block_number = int(robot.variables.get_attribute("block"))
	# box_size = 0.025
	# tens = block_number//10
	# unts  = block_number % 10
	# for i in range(unts):
	# 	environment.qt_draw.box([0, 0.05, 1.1*box_size*i], [], 3*[box_size], color)
	# for i in range(tens):
	# 	environment.qt_draw.box([0, 0.08, 1.1*box_size*i], [], 3*[box_size], color)

def destroy():
	print('Closing the QT window')


	# # Draw the odometry position error
	# if lp['generic']['show_pos']:
	# 	with open(lp['files']['position'], 'r') as f:
	# 		for line in f:
	# 			gps_pos, odo_pos = eval(line)
	# 			gps_pos, odo_pos = list(gps_pos)+[0.01], list(odo_pos)+[0.01]
	# 			environment.qt_draw.ray(gps_pos, odo_pos, 'red', 0.15)

	# # Draw rays
	# if lp['generic']['show_rays']:
	# 	with open(lp['files']['rays'], 'r') as f:
	# 		for line in f:
	# 			robotID, pos, vec_target, vec_avoid, vec_desired = eval(line)
	# 			environment.qt_draw.ray([pos[0], pos[1] , 0.01],[pos[0] + vec_target[0], pos[1] + vec_target[1] , 0.01], 'red', 0.15)
	# 			environment.qt_draw.ray([pos[0], pos[1] , 0.01],[pos[0] + vec_avoid[0], pos[1] + vec_avoid[1] , 0.01], 'blue', 0.15)
	# 			environment.qt_draw.ray([pos[0], pos[1] , 0.01],[pos[0] + vec_desired[0], pos[1] + vec_desired[1] , 0.01], 'green', 0.15)
	# # Draw patches which are on SC
	# for i in range(1,lp['generic']['num_robots']+1):
	# 	with open(lp['environ']['DOCKERFOLDER']+'/geth/logs/%s/scresources.txt' % i, 'r') as f:	
	# 		for line in f:
	# 			res = Resource(line.rsplit(' ', 2)[0])

	# 			# Draw a gray resource area
	# 			environment.qt_draw.circle([res.x, res.y, 0.001],[], res.radius, 'gray70', True)

	# 			# Draw a gray meanQ cylinder
	# 			mean     = int(line.rsplit(' ', 2)[1])
	# 			mean_sum = int(line.rsplit(' ', 2)[2])
	# 			if mean_sum:
	# 				environment.qt_draw.cylinder([res.x, res.y, 0.001],[], 0.015, mean/mean_sum , 'gray30')

	# resources = list()
	# counts = list()
	# for i in range(1,lp['generic']['num_robots']+1):
	# 	with open(lp['environ']['DOCKERFOLDER']+'/geth/logs/%s/scresources.txt' % i, 'r') as f:	
	# 		for line in f:
	# 			if line:
	# 				res = Resource(line.rsplit(' ', 2)[0])
	# 				if (res.x, res.y) not in [(ressc.x,ressc.y) for ressc in resources]:
	# 					counts.append(1)
	# 					resources.append(res)
	# 				else:
	# 					counts[[(ressc.x,ressc.y) for ressc in resources].index((res.x, res.y))] += 1

	# # Draw SC patch quantities and consensus
	# for res in resources:
	# 	frac = counts[resources.index(res)]/lp['generic']['num_robots']
	# 	environment.qt_draw.circle([res.x, res.y, 0.0005],[], res.radius, 'gray90', True)
	# 	environment.qt_draw.circle([res.x, res.y, 0.0015],[], frac*res.radius, 'gray80', True)
	# 	for i in range(res.quantity):
	# 		environment.qt_draw.circle([res.x+1.1*res.radius, res.y+res.radius-0.01*2*i-0.001, 0.001],[], 0.01, 'black', True)