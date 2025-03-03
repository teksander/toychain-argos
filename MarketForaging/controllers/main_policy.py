#!/usr/bin/env python3
# This is the main control loop running in each argos robot

# /* Import Packages */
#######################################################################
import random, math
import time, sys, os
import json
from json import loads

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.actusensors.movement     import RandomWalk, Navigate, Odometry, OdoCompass, GPS
from controllers.actusensors.groundsensor import ResourceVirtualSensor, Resource
from controllers.actusensors.erandb       import ERANDB
from controllers.actusensors.rgbleds      import RGBLEDs
from controllers.utils import *
from controllers.utils import Timer, setup_logging
from controllers.utils import FiniteStateMachine

from controllers.params import params as cp
from loop_functions.params import params as lp

from toychain.src.utils.helpers import gen_enode
from toychain.src.consensus.ProofOfAuth import ProofOfAuthority, BLOCK_PERIOD
from toychain.src.Node import Node
from toychain.src.Block import Block, State
from toychain.src.Transaction import Transaction

# /* Global Variables */
#######################################################################
global robot

global startFlag
startFlag = False

global txList, tripList, submodules
txList, tripList, submodules = [], [], []

global clocks, counters, logs, txs
clocks, counters, logs, txs = dict(), dict(), dict(), dict()

# /* Logging Levels for Console and File */
#######################################################################
import logging
loglevel = 10
logtofile = False 

# /* Experiment Global Variables */
#######################################################################

# Store the position of the market and cache
market   = Resource({"x":lp['market']['x'], "y":lp['market']['y'], "radius": lp['market']['r']})
cache    = Resource({"x":lp['cache']['x'], "y":lp['cache']['y'], "radius": lp['cache']['r']})

# Toychain genesis block
GENESIS = Block(0, 0000, [], [gen_enode(i+1) for i in range(int(lp['environ']['NUMROBOTS']))], 0, 0, 0, nonce = 1, state = State())

# /* Experiment State-Machine */
#######################################################################

class States(Enum):
    IDLE   = 1
    PLAN   = 2
    ASSIGN = 3
    FORAGE = 4
    DROP   = 5 
    ANTENA = 6
    LEAVE  = 7
    HOMING = 8
    TRANSACT = 9
    RANDOM   = 10
    EXPLORE  = 11
    VERIFY   = 12
    EVADING  = 13

####################################################################################################################################################################################
#### INIT STEP #####################################################################################################################################################################
####################################################################################################################################################################################
global robot_type

def init():
    global clocks,counters, logs, submodules, me, rw, nav, odo, gps, rb, w3, fsm, rs, erb, rgb, robot_type
    robotID, robotIP = str(int(robot.variables.get_id()[2:])+1), '127.0.0.1'
    robot.variables.set_attribute("id", str(robotID))
    robot.variables.set_attribute("circle_color", "gray50")
    robot.variables.set_attribute("odo_position",repr(Vector2D()))
    robot.variables.set_attribute("scresources", "[]")
    robot.variables.set_attribute("foraging", "")
    robot.variables.set_attribute("dropResource", "")
    robot.variables.set_attribute("hasResource", "")
    robot.variables.set_attribute("resourceCount", "0")
    robot.variables.set_attribute("depleted", "")
    robot.variables.set_attribute("state", "")
    robot.variables.set_attribute("forageTimer", "0")
    robot.variables.set_attribute("quantity", "0")
    robot.variables.set_attribute("block", "")
    robot.variables.set_attribute("groupSize", "1")
    robot.variables.set_attribute("block", "0")
    robot.variables.set_attribute("hash", str(hash("genesis")))
    robot.variables.set_attribute("state_hash", str(hash("genesis")))
    robot.variables.set_attribute("mempl_hash", str(hash("genesis")))
    robot.variables.set_attribute("mempl_size", "0")
    robot.variables.set_attribute("w3_peers", "[]")
    robot.variables.set_attribute("verified", "[]")
    robot.variables.set_attribute("pending", "[]")
    robot.variables.set_attribute("allpts", "[]")

    if int(robotID) <= int(lp['environ']['NUMA']):
        robot_type = 'A'
    elif int(robotID) <= int(lp['environ']['NUMA']) + int(lp['environ']['NUMB']):
        robot_type = 'B'
    elif int(robotID) <= int(lp['environ']['NUMA']) + int(lp['environ']['NUMB']) + int(lp['environ']['NUMC']):
        robot_type = 'C'
    else:
        robot_type = 'D'

    robot.variables.set_attribute("robot_type", robot_type)

    robot.variables.set_attribute("erb_range", str(cp[robot_type]['range']))
    
    # /* Initialize Console Logging*/
    #######################################################################
    log_folder = experimentFolder + '/logs/' + robotID + '/'

    # Monitor logs (recorded to file)
    logger = setup_logging(log_to_file=logtofile, log_folder=log_folder, robotID=robotID)
    logging.getLogger('sc').setLevel(10)
    logging.getLogger('w3').setLevel(70)
    logging.getLogger('poa').setLevel(70)
    logging.getLogger('fsm').setLevel(10)

    robot.log = logging.getLogger()
    robot.log.setLevel(10)

    # /* Initialize submodules */
    #######################################################################
    # # /* Init web3.py */
    robot.log.info('Initialising Python Geth Console...')
    w3 = Node(robotID, robotIP, 1233 + int(robotID), ProofOfAuthority(genesis = GENESIS))

    # /* Init an instance of peer for this Pi-Puck */
    me = Peer(robotID, robotIP, w3.enode, w3.key)

    #/* Init Resource-Sensors */
    robot.log.info('Initialising resource sensor...')
    rs = ResourceVirtualSensor(robot)

    # /* Init E-RANDB __listening process and transmit function
    robot.log.info('Initialising RandB board...')
    erb = ERANDB(robot)

    # /* Init odometry sensor */
    robot.log.info('Initialising odometry...')
    robot.odo = OdoCompass(robot, variance = cp[robot_type]['error'])

    # /* Init Random-Walk, __walking process */
    robot.log.info('Initialising random-walk...')
    rw = RandomWalk(robot, cp[robot_type]['speed'])

    # /* Init Navigation, __navigate process */
    robot.log.info('Initialising navigation...')
    nav = Navigate(robot, cp[robot_type]['speed'])

    # /* Init GPS sensor */
    robot.log.info('Initialising gps...')
    gps = GPS(robot)

    # /* Init LEDs */
    rgb = RGBLEDs(robot)

    # /* Init Finite-State-Machine */
    fsm = FiniteStateMachine(robot, start = States.PLAN)

    # List of submodules --> iterate .start() to start all
    submodules = [erb]

    # /* Initialize logmodules*/
    #######################################################################

    clocks['peering']  = Timer(30)
    clocks['homing']   = Timer(50)
    clocks['explore']  = Timer(300)
    clocks['verify']   = Timer(0)
    clocks['block']    = Timer(BLOCK_PERIOD)

    # /* Initialize logmodules*/
    #######################################################################
    # Experiment data logs (recorded to file)

    # name   = 'fsm.csv'
    # header = stateList
    # logs['fsm'] = Logger(log_folder+name, header, rate = 10, ID = me.id)

    # name   =  'odometry.csv'
    # header = ['DIST']
    # logs['odometry'] = Logger(log_folder+name, header, rate = 10, ID = me.id)

    txs['leave'] = None
    txs['join']  = None
    txs['drop'] = None
    txs['update'] = None

#########################################################################################################################
#### CONTROL STEP #######################################################################################################
#########################################################################################################################

def controlstep():
    global clocks, counters, startFlag

    ###########################
    ######## ROUTINES #########
    ###########################

    def peering():

        # Get the current peers from erb
        erb_enodes = {w3.gen_enode(peer.id) for peer in erb.peers if peer.getData(indices=[1,2]) > w3.get_total_difficulty() or peer.data[3] != w3.mempool_hash(astype='int')}
        # erb_enodes = {w3.gen_enode(peer.id) for peer in erb.peers}

        # w3_peers   = erb.peers
        w3_peers = set()
        for peer in erb.peers:
            if peer.data[2] != w3.last_hash(astype='int') or peer.data[3] != w3.mempool_hash(astype='int'):
                w3_peers.add(peer)

        erb_enodes = {w3.gen_enode(peer.id) for peer in w3_peers}

        # Add peers on the toychain
        for enode in erb_enodes-set(w3.peers):
            try:
                w3.add_peer(enode)
            except Exception as e:
                raise e
            
        # Remove peers from the toychain
        for enode in set(w3.peers)-erb_enodes:
            try:
                w3.remove_peer(enode)
            except Exception as e:
                raise e

        erb.setData(w3.last_hash(astype='int'), indices=2)
        erb.setData(w3.mempool_hash(astype='int'), indices=3)
        
        # Turn on LEDs according to geth peer count
        rgb.setLED(rgb.all, rgb.presets.get(len(w3.peers), 3*['red']))

        # Draw on qtuser_function the peers
        robot.variables.set_attribute("w3_peers", str([(peer.range, peer.bearing) for peer in w3_peers])) 

    def evading(patch):

        # Navigate orthogonaly to the patch-market
        targets = [Vector2D(patch['json']['x'], patch['json']['y']).rotate(20, degrees=True),
                   Vector2D(patch['json']['x'], patch['json']['y']).rotate(-20, degrees=True)]
        target = min(targets, key=nav.get_distance_to)

        arrived = False
        
        nav.sensor = 'gps'
        if nav.navigate_with_obstacle_avoidance(target) < 0.05:
            arrived = True

        nav.sensor = 'odometry'

        return arrived


    def homing():

        # Navigate to the market
        arrived = True

        nav.sensor = 'gps'

        if nav.get_distance_to(market._pr) < 0.9*market.radius:           
            nav.avoid(move = True)
            
        elif nav.get_distance_to(market._pr) < market.radius and len(w3.peers) > 1:
            nav.avoid(move = True)

        else:
            nav.navigate_with_obstacle_avoidance(market._pr)
            arrived = False

        nav.sensor = 'odometry'

        return arrived

    def dropping(resource):

        direction = (Vector2D(resource['x'],resource['y'])-market._pv).rotate(-25, degrees = True).normalize()
        target = direction*(market.radius+cache.radius)/2+market._pv

        nav.sensor = 'gps'

        # Navigate to drop location
        arrived = True

        if nav.get_distance_to(market._p) < market.radius + 0.5* (cache.radius-market.radius):
            nav.avoid(move = True)
        else:
            nav.navigate_with_obstacle_avoidance(target)
            arrived = False

        nav.sensor = 'odometry'

        return arrived

    def sensing(gps = False):

        # Sense environment for resources
        res = rs.getNew()

        if res:
            if gps:
                return {'x':res.x, 'y':res.y, 'json':json.loads(res._json)}
            return {'x':round(res.x + robot.odo.ex, 2), 'y':round(res.y + robot.odo.ey, 2), 'json':json.loads(res._json)}


    if not startFlag:
        ##########################
        #### FIRST STEP ##########
        ##########################

        startFlag = True 

        robot.log.info('--//-- Starting Experiment --//--')

        for module in [erb, rs, w3]:
            module.start()

        for log in logs.values():
            log.start()

        for clock in clocks.values():
            clock.reset()
        
        # Register to Smart Contract transaction
        tx = Transaction(sender = me.id, data = {'function': 'register', 'inputs': []})
        w3.send_transaction(tx)

    else:

        ##############################
        ##### STATE-MACHINE STEP #####
        ##############################

        #########################################################################################################
        #### State::EVERY
        #########################################################################################################
        
        # Perform submodule steps
        for module in [erb, rs, w3, robot.odo, fsm]:
            module.step()

        # Perform clock steps
        for clock in clocks.values():
            clock.time.step()

        # Perform clocked tasks
        peering()

        # Updated odometry position
        robot.variables.set_attribute("odo_position",repr(robot.odo.getPosition()))

        if robot.variables.get_attribute("at") == "cache":
            robot.odo.setPosition()

        # Read patch info from blockchain
        patches    = w3.sc.getPatches()
        verified   = [p for p in patches if p['status'] == 'verified' and me.id not in p["votes_remove"]]
        unverified = [p for p in patches if p['status'] == 'pending']

        unverified_by_me = [p for p in unverified if me.id not in p['votes']]
        explored_by_me   = [p for p in unverified if me.id == p['explorer']]

        #(Visualization only, can comment out)
        last_block = w3.get_block('last')
        # robot.variables.set_attribute("block", str(last_block.height))
        # robot.variables.set_attribute("tdiff", str(last_block.total_difficulty))
        # robot.variables.set_attribute("mempl_hash", w3.mempool_hash(astype='str'))
        robot.variables.set_attribute("block_hash", str(last_block.hash))
        # robot.variables.set_attribute("state_hash", str(last_block.state.state_hash))
        # robot.variables.set_attribute("mempl_size", str(len(w3.mempool)))        

        # (Visualization only, can comment out)
        robot.variables.set_attribute("verified", str([(p['x'], p['y'], p['json']) for p in patches if p['status'] == 'verified']))
        robot.variables.set_attribute("pending",  str([(p['x'], p['y'], p['json']) for p in patches if p['status'] == 'pending']))
        robot.variables.set_attribute("allpts",  str([(p['all_x'], p['all_y'], p['json']) for p in patches if p['status'] == 'pending']))

        #########################################################################################################
        #### State::PLAN
        #########################################################################################################
        if fsm.query(States.PLAN):

            if fsm.elapsed < 100:
                homing()

            else:
                action = random.choices(('explore', 'verify', 'forage'), weights=(30, 30, 30))[0]

                if action == 'explore':

                    # State transition: EXPLORE
                    duration = random.gauss(cp['explore_mu'], cp['explore_sg'])*10
                    clocks['explore'].set(duration)
                    fsm.setState(States.EXPLORE, message = "Duration: %.2f" % duration)

                elif action == 'verify' and unverified_by_me:

                    # State transition: VERIFY
                    patch = random.choice(unverified_by_me)
                    fsm.setState(States.VERIFY, pass_along = patch)

                elif action == 'forage' and verified:

                    # State transition: FORAGE
                    patch = random.choice(verified)
                    fsm.setState(States.FORAGE, pass_along = patch)

        #########################################################################################################
        #### State::EVADING
        #########################################################################################################

        elif fsm.query(States.EVADING):

            arrived = evading(fsm.pass_along)

            if arrived:
                fsm.setState(States.HOMING)

        #########################################################################################################
        #### State::HOMING
        #########################################################################################################

        elif fsm.query(States.HOMING):

            arrived = homing()

            if arrived:
                fsm.setState(States.PLAN)

        # #########################################################################################################
        # #### State::IDLE
        # #########################################################################################################

        # elif fsm.query(States.IDLE):

        #     # Perform a random-walk 
        #     homing()

        #     if clocks['explore'].query():
        #         fsm.setState(States.PLAN, message = "Finished idling")


        #########################################################################################################
        #### State::EXPLORE
        #########################################################################################################

        elif fsm.query(States.EXPLORE):

            # Perform a random-walk 
            rw.step()

            # Look for resources
            patch_gs = sensing()

            # Sucess exploration: transact
            if patch_gs and not txs['update']:
                txdata = {'function': 'propose', 'inputs': (patch_gs['x'], patch_gs['y'], patch_gs['json'])}
                txs['update'] = Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
                w3.send_transaction(txs['update'])
            
                robot.log.info(f"Discovered {patch_gs['json']['quality']}")

                fsm.setState(States.EVADING, message = "Found patch", pass_along=patch_gs)
                txs['update'] = None

            elif clocks['explore'].query():
                fsm.setState(States.HOMING, message = "Finished exploring")
                txs['update'] = None


        #########################################################################################################
        #### State::ANTENA
        #########################################################################################################

        elif fsm.query(States.ANTENA):

            patch_to_broadcast = fsm.pass_along

            nav.sensor = 'gps'
            distance = nav.navigate_with_obstacle_avoidance((patch_to_broadcast['json']['x'], patch_to_broadcast['json']['y']))

            if distance < 0.2*patch_to_broadcast['json']['radius']:
                nav.avoid(move=True)

            _, patch = w3.sc.findByPos(patch_to_broadcast['json']['x'], patch_to_broadcast['json']['y'])

            if patch and patch['explorers'][0] != me.id:
                nav.sensor = 'odometry'
                fsm.setState(States.EVADING, message = "Another broadcasting", pass_along = patch_to_broadcast)

            elif patch and patch['status'] in ['verified', 'removed']:
                nav.sensor = 'odometry'
                fsm.setState(States.EVADING, message = "Finished broadcasting", pass_along = patch_to_broadcast)


        #########################################################################################################
        #### State::VERIFY
        #########################################################################################################

        elif fsm.query(States.VERIFY):
            
            patch_to_verify = fsm.pass_along
            arrived = False
            found   = False
            listen  = False

            # Navigate to resource
            distance = nav.navigate_with_obstacle_avoidance((patch_to_verify['x'], patch_to_verify['y']))
            
            # Sense for resources
            patch_gs = sensing()

            if patch_gs and patch_gs['json']['x'] == patch_to_verify['json']['x'] and patch_to_verify['json']['y'] == patch_to_verify['json']['y']:
                found = True

            # Navigate to verify
            if distance < 0.9*patch_to_verify['json']['radius']:
                arrived    = True   

            # Arrived but not found: explore nearby
            if arrived and not found:
                rw.step(local=True, target=(patch_to_verify['x'],patch_to_verify['y']))

            # # Listen for the explorer
            # for peer in erb.peers:
            #     if peer.id in patch_to_verify['explorers']:
            #         explorer = peer
            #         listen = True

            # # Can hear broadcast from explorer: navigate towards
            # if listen:
            #     bearing  = explorer.bearing
            #     distance = explorer.range
            #     target = Vector2D(distance, bearing, polar=True)
            #     nav.navigate_with_obstacle_avoidance(target, local = True)

            # Found the patch: transact
            if found:
                
                txdata = {'function': 'verify', 'inputs': (patch_gs['x'], patch_gs['y'], patch_gs['json'])}
                txs['update'] =  Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
                w3.send_transaction(txs['update'])
                
                robot.log.info(f"Verified {patch_to_verify['json']['quality']}")

                fsm.setState(States.EVADING, message = "Verify success", pass_along = patch_to_verify)
            
            elif fsm.elapsed > 800:
                txdata = {'function': 'verify', 'inputs': (0, 0, patch_to_verify['json'], True)}
                txs['update'] =  Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
                w3.send_transaction(txs['update'])

                robot.log.info(f"Rejected {patch_to_verify['json']['quality']}")
                fsm.setState(States.HOMING, message = "Verify failed")

        #########################################################################################################
        #### State::FORAGE
        #########################################################################################################
        elif fsm.query(States.FORAGE):

            patch_to_forage = fsm.pass_along
            arrived  = False
            found    = False
            finished = False
            depleted = False

            # Navigate to resource
            distance = nav.navigate_with_obstacle_avoidance((patch_to_forage['x'], patch_to_forage['y']))

            # Sense for resources
            patch_gs = sensing()

            if distance < 0.8*patch_to_forage['json']['radius']:
                arrived  = True  

            if patch_gs and (patch_gs['json']['x'], patch_gs['json']['y']) == (patch_to_forage['json']['x'], patch_to_forage['json']['y']):
                patch_to_forage = patch_gs
                found = True

            if int(robot.variables.get_attribute("quantity")) >= cp[robot_type]['max_Q'] or fsm.elapsed > 800:
                finished = True

            if robot.variables.get_attribute("depleted") == "True":
                depleted = True

            # Arrived but not found: explore within radius
            if arrived and not found:
                rw.step(local=True, target=(patch_to_forage['x'],patch_to_forage['y']))
            
            elif finished:

                if depleted or not found:
                    robot.variables.set_attribute("depleted", "")
                    robot.log.info(f"Resource is: depleted {depleted}/found {found}")
                    patch_to_forage['json']['quantity'] = 0 
                    txdata = {'function': 'verify', 'inputs': (0, 0, patch_to_forage['json'], True)}
                    tx = Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
                    w3.send_transaction(tx)

                robot.variables.set_attribute("foraging", "")
                fsm.setState(States.DROP, message = f"Collected {robot.variables.get_attribute('quantity')} {patch_to_forage['json']['quality']}", pass_along = patch_to_forage)

            elif found:
                robot.variables.set_attribute("foraging", "True")
                nav.avoid(move = True)
              

        #########################################################################################################
        #### State::DROP
        #########################################################################################################
        elif fsm.query(States.DROP):
            
            patch_to_drop = fsm.pass_along

            # Navigate home
            arrived = dropping(patch_to_drop)

            if arrived:

                # Transact to drop resource
                if not txs['drop']:
                    robot.log.info(f"Dropping.")
                    txdata = {'function': 'forage', 'inputs': (patch_to_drop['x'], patch_to_drop['y'], patch_to_drop['json'])}
                    txs['drop'] = Transaction(sender = me.id, data = txdata, timestamp = w3.custom_timer.time())
                    w3.send_transaction(txs['drop'])
   
                # Transition state  
                else:
                    if w3.get_transaction_receipt(txs['drop'].id):
                        robot.variables.set_attribute("dropResource", "True")

                        if not robot.variables.get_attribute("hasResource"):
                            txs['drop'] = None
                            robot.variables.set_attribute("dropResource", "")   
                            fsm.setState(States.PLAN, message = "Dropped: %s" % patch_to_drop['json']['quality'])                       

#########################################################################################################################
#### RESET-DESTROY STEPS ################################################################################################
#########################################################################################################################

def reset():
    pass

def destroy():
    if startFlag:
        w3.stop_mining()
        txs    = w3.get_all_transactions()
        my_txs = w3.my_transactions

        if len(txs) != len(set([tx.id for tx in txs])):
            print(f'REPEATED TX ON CHAIN: #{len(txs)-len(set([tx.id for tx in txs]))}')

        for tx in my_txs:
            if tx.id not in [tx.id for tx in txs+list(w3.mempool.values())]:
                print(f'ONE OF MY TX IS LOST !')

        if me.id == "1":
            for key, value in w3.sc.state.items():
                
                if isinstance(value, list):
                    print(f"{key}:")
                    for item in value:
                        print(f"{item}")  # Indented list item for clarity
                        print()
                else:
                    print(f"{key}:")
                    print(f"{value}")

        # # Log the result of the each trip performed by robot
        # name   = 'firm.csv'
        # header = ['TSTART', 'FC', 'Q', 'C', 'MC', 'TC', 'ATC', 'PROFIT', 'UTIL', 'QLTY']
        # logs['firm'] = Logger(f"{experimentFolder}/logs/{me.id}/{name}", header, ID = me.id)

        # for trip in tripList:
        #     if trip.finished:
        #         logs['firm'].log([*str(trip).split()])

        # Log each block over the operation of the swarm
        name   = 'block.csv'
        header = ['TELAPSED','TIMESTAMP','BLOCK', 'HASH', 'PHASH', 'DIFF', 'TDIFF', 'SIZE','TXS', 'UNC', 'PENDING', 'QUEUED']
        logs['block'] = Logger(f"{experimentFolder}/logs/{me.id}/{name}", header, ID = me.id)

        for block in w3.chain:
            logs['block'].log(
                [block.reception-block.timestamp, 
                block.timestamp, 
                block.height, 
                block.hash, 
                block.parent_hash, 
                block.difficulty,
                block.total_difficulty, 
                sys.getsizeof(block) / 1024, 
                len(block.data), 
                0
                ])

        # Log the state of each block
        name   = 'sc.csv'
        # header = ['TIMESTAMP', 'BLOCK', 'HASH', 'PHASH', 'BALANCE', 'TX_COUNT', 'X','Y','QTTY', 'QLTY', 'ID', 'TOTW','number', 'start', 'Q', 'TC', 'ATC', 'price', 'robots', 'TQ', 'AATC', 'AP']
        header = ['TIMESTAMP', 'BLOCK', 'HASH', 'PHASH', 'BALANCE', 'TX_COUNT', 'X','Y','QTTY', 'QLTY', 'ID']
        logs['sc'] = Logger(f"{experimentFolder}/logs/{me.id}/{name}", header, ID = me.id)

        for block in w3.chain:
            for patch in block.state.patches:
                logs['sc'].log(
                    [block.timestamp, 
                    block.height, 
                    block.hash, 
                    block.parent_hash, 
                    block.state.balances.get(me.id,0),
                    block.state.n,
                    patch['json']['x'],  # 'x' coordinate of the patch
                    patch['json']['y'],  # 'y' coordinate of the patch
                    patch['json']['quantity'],  # Patch quantity (qtty)
                    patch['json']['quality'],  # Patch quality (qlty)
                    patch['id'],  # Patch ID
                    # patch['totw'],  # Total workers in the patch (totw)
                    # patch['epoch']['number'],  # Epoch number
                    # patch['epoch']['start'],   # Epoch start time
                    # str(patch['epoch']['Q']).replace(' ', ''),  # Epoch 'Q' value
                    # str(patch['epoch']['TC']).replace(' ', ''),  # Epoch 'TC' value
                    # str(patch['epoch']['ATC']).replace(' ', ''),  # Epoch 'ATC' value
                    # patch['epoch']['price'],  # Price during the epoch
                    # str(patch['epoch']['robots']).replace(' ', ''),  # List of robots in the epoch
                    # patch['epoch']['TQ'],  # Total quantity (TQ) during the epoch
                    # patch['epoch']['AATC'],  # Average ATC during the epoch
                    # patch['epoch']['AP']  # Average price (AP) during the epoch
                    ])

        
    print('Killed robot '+ me.id)

#########################################################################################################################
#########################################################################################################################
#########################################################################################################################