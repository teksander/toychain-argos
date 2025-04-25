#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random, math
import sys, os

from json import loads

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.actusensors.groundsensor import Resource
from controllers.utils import Vector2D
from controllers.params import params as cp

from loop_functions.utils import hash_to_rgb
from loop_functions.params import params as lp

from toychain.src.utils.helpers import gen_enode
from toychain.src.Node import Node
from toychain.src.Block import Block
from toychain.src.consensus.ProofOfAuth import ProofOfAuthority
from scs.market import Market as State

lp['generic']['show_rays'] = False
lp['generic']['show_pos'] = True

# /* Global Variables */
#######################################################################
global robot, environment

res_diam   = 0.015
rob_diam   = 0.07/2
res_height = 0.01

# Store the position of the market and cache
market   = Resource({"x":lp['market']['x'], "y":lp['market']['y'], "radius": lp['market']['r']})
cache    = Resource({"x":lp['cache']['x'], "y":lp['cache']['y'], "radius": lp['cache']['r']})

# Initialize the monitoring glassnode
enodes  = [gen_enode(i+1) for i in range(int(lp['environ']['NUMROBOTS']))]
GENESIS = Block(0, 0000, [], enodes, 0, 0, 0, nonce = 1, state = State())

glassnode = Node('0', '127.0.0.1', 1233, ProofOfAuthority(genesis = GENESIS))

# /* Global Functions */
#######################################################################

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
	
def draw_patches_sc():

	patches_sc = glassnode.sc.getPatches()

	for patch in patches_sc:
		x, y   = patch['x'], patch['y'], 
		profit = patch['profit']
		radius = loads(patch['json'])['radius']
		color  = 'red' if profit < 0 else 'green'
		height = abs(profit)*0.00025

		environment.qt_draw.cylinder([x+radius, y+radius, height/2],[], 0.08, height, color)

def draw_resources_on_robots():
	quantity = robot.param.get("quantity")
	quality  = robot.param.get("hasResource")

	# Draw carried quantity
	for i in range(quantity):
		environment.qt_draw.cylinder([0, 0, (i*1.3)*res_height + 0.075],[], 0.5 * rob_diam, res_height, quality)

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

	# Draw the Market
	draw_market()

	# Draw resource patches
	draw_patches()

	# Draw resource patches from blockchain
	draw_patches_sc()
	
def draw_in_robot():

	# Draw resources carried by robots
	draw_resources_on_robots()

	# Draw representation of robot state machine
	robot_state = robot.param.get("fsm")+"12"
	# environment.qt_draw.circle([0, 0, 0.005],[], 0.1, hash_to_rgb(robot_state), True)

	# Draw representation of robot heterogeneous type
	robot_type  = robot.param.get("robot_type")
	# environment.qt_draw.circle([0, 0, 0.005],[], 0.08, hash_to_rgb(robot_type), True)

	# Draw block/state/mempool hash as colored circles
	color_state = hash_to_rgb(robot.param.get("state_hash"))
	color_block = hash_to_rgb(robot.param.get("block_hash"))
	color_mempl = hash_to_rgb(robot.param.get("mempl_hash"))
	tx_count = int(robot.param.get("mempl_size"))
	environment.qt_draw.circle([0,0,0.011], [], 0.08, color_block, True)
	# environment.qt_draw.circle([0,0,0.010], [], 0.100, color_state, True)
	# environment.qt_draw.cylinder([1.5*rob_diam, 0, 0.005], [], 0.5*rob_diam, tx_count*res_height, color_mempl)
	# environment.qt_draw.box([3*rob_diam, 0, 0.005], [], [rob_diam, rob_diam, tx_count*0.5*rob_diam+0.0002], color_mempl)

	# # Draw robot balances
	# balance = float(robot.param.get("balance"))
	# if balance < 0:
	# 	environment.qt_draw.box([3*rob_diam, 0, 0.005], [], [rob_diam, rob_diam, -balance*0.01*0.5*rob_diam+0.0002], 'red')
	# else:
	# 	environment.qt_draw.box([3*rob_diam, 0, 0.005], [], [rob_diam, rob_diam, balance*0.01*0.5*rob_diam+0.0002], 'green')

	# Draw rays to w3 peers
	w3_peers = eval(robot.param.get("w3_peers"))
	for peer_rb in w3_peers:
		environment.qt_draw.ray([0, 0 , 0.01],[peer_rb[0]*math.cos(peer_rb[1]), peer_rb[0]*math.sin(peer_rb[1]) , 0.01], 'red', 0.15)

	# Draw the odometry position error
	odo_pos = robot.param.get("odo_position")
	gps_pos = Vector2D(robot.position.get_position()[0:2])
	environment.qt_draw.circle(list(gps_pos-odo_pos)+[0.01],[], 0.025, hash_to_rgb(robot_type), True)
	environment.qt_draw.ray([0,0,0.01], list(gps_pos-odo_pos)+[0.01], hash_to_rgb(robot_type), 0.5)

	# # Draw ERB range
	# erb_range  = robot.param.get("erb_range")
	# environment.qt_draw.circle([0, 0, 0.00005],[], float(erb_range), 'gray90', False)

def destroy():
	print('Closing the QT window')


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


# Draw block number with boxes
	# block_number = int(robot.param.get("block"))
	# box_size = 0.025
	# tens = block_number//10
	# unts  = block_number % 10
	# for i in range(unts):
	# 	environment.qt_draw.box([0, 0.05, 1.1*box_size*i], [], 3*[box_size], color)
	# for i in range(tens):
	# 	environment.qt_draw.box([0, 0.08, 1.1*box_size*i], [], 3*[box_size], color)