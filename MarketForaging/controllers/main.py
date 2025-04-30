#!/usr/bin/env python3

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
from toychain.src.Block import Block
from toychain.src.Transaction import Transaction

from scs.market import Market as State

# /* Global Variables */
#######################################################################
global robot

global startFlag
startFlag = False

global txList, tripList, submodules
txList, tripList, submodules = [], [], []

global clocks, counters, logs, txs
clocks, counters, logs, txs = dict(), dict(), dict(), dict()

clocks['peering']  = Timer(30)
clocks['sensing']  = Timer(5)
clocks['block']    = Timer(BLOCK_PERIOD)
clocks['decision'] = Timer(BLOCK_PERIOD*cp['firm']['entry_f'])

# /* Logging Levels for Console and File */
#######################################################################
import logging
loglevel = 30
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
    INIT   = 0
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
    

class Trip(object):

    def __init__(self, patch):
        self.tStart = w3.custom_timer.time()
        self.FC     = 0
        self.Q      = 0
        self.C      = []
        self.MC     = []
        self.TC     = 0
        self.ATC    = 0
        self.util   = patch['util']
        self.qlty   = patch['qlty']
        self.pid    = patch['id']
        self.price = self.util
        
        self.finished = False

        tripList.append(self)

    @property
    def timedelta(self):
        timedelta = w3.custom_timer.time() - self.tStart
        return round(timedelta, 2)

    def update(self, Q):
        finished = False

        # Update price
        self.price = self.util
        if self.FC == 0:
            self.FC = self.timedelta

        C  = self.timedelta-self.FC
        
        if len(self.C) > 0 and C-self.C[-1] > 1.05*self.price:
            robot.log.debug("Finished before collection %s" % (C-self.C[-1]))
            finished = True

        if int(Q) > self.Q:
            finished = False
            self.Q = int(Q)
            self.C.append(C)

            if len(self.C) > 1:
                MC = self.C[-1]-self.C[-2]
                robot.log.debug(f"Q: {self.Q} // MC: {MC} // P: {round(self.price,0)}")
                self.MC.append(MC)

                if MC > self.price:
                    finished = True

            self.TC  = self.timedelta
            self.ATC = round(self.TC/self.Q)
            self.profit  = round(self.Q*self.price-self.TC)

        self.finished = finished
        return finished

    def __str__(self):
        C  = str(self.C).replace(' ','')
        MC = str(self.MC).replace(' ','')
        return "%i %i %i %s %s %i %i %i %i %s %i" % (self.tStart, self.FC, self.Q, C, MC, self.TC, self.ATC, self.profit, self.util, self.qlty, self.pid)   

####################################################################################################################################################################################
#### INIT STEP #####################################################################################################################################################################
####################################################################################################################################################################################
global robot_type

def init():
    global clocks,counters, logs, submodules, me, rw, nav, odo, gps, rb, w3, fsm, rs, erb, rgb, robot_type
    robotID, robotIP = str(int(robot.variables.get_id()[2:])+1), '127.0.0.1'
    robot.param.set("id", str(robotID))
    robot.param.set("odo_position",Vector2D())
    robot.param.set("foraging", False)
    robot.param.set("genesis", GENESIS)
    robot.param.set("dropResource", "")
    robot.param.set("hasResource", "")
    robot.param.set("resourceCount", "0")
    robot.param.set("depleted", "")
    robot.param.set("state", "")
    robot.param.set("forageTimer", "0")
    robot.param.set("quantity", 0)
    robot.param.set("block", "")
    robot.param.set("groupSize", "1")
    robot.param.set("block", "0")
    robot.param.set("hash", str(hash("genesis")))
    robot.param.set("state_hash", str(hash("genesis")))
    robot.param.set("mempl_hash", str(hash("genesis")))
    robot.param.set("mempl_size", "0")
    robot.param.set("w3_peers", "[]")
    robot.param.set("verified", "[]")
    robot.param.set("pending", "[]")
    robot.param.set("balance", "0")
    robot.param.set("profits", "[]")
    robot.param.set("allpts", "[]")
    robot.param.set("block_hash", str(GENESIS.hash))
    # robot.param.set("last_block", GENESIS)
    
    if int(robotID) <= int(lp['environ']['NUMA']):
        robot_type = 'A'
    elif int(robotID) <= int(lp['environ']['NUMA']) + int(lp['environ']['NUMB']):
        robot_type = 'B'
    elif int(robotID) <= int(lp['environ']['NUMA']) + int(lp['environ']['NUMB']) + int(lp['environ']['NUMC']):
        robot_type = 'C'
    else:
        robot_type = 'D'
    
    robot.param.set("robot_type", robot_type)
    robot.param.set("erb_range", str(cp[robot_type]['range']))

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
    robot.log.setLevel(30)

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
    fsm = FiniteStateMachine(robot, start = States.IDLE)

    # List of submodules --> iterate .start() to start all
    submodules = [erb]

    # /* Initialize logmodules*/
    #######################################################################

    clocks['peering']  = Timer(30)
    clocks['homing']   = Timer(50)
    clocks['explore']  = Timer(300)
    clocks['verify']   = Timer(0)
    clocks['block']    = Timer(BLOCK_PERIOD)

    txs['leave']  = None
    txs['join']   = None
    txs['drop']   = None
    txs['update'] = None
    txs['plan']   = None

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
        # erb_enodes = {w3.gen_enode(peer.id) for peer in erb.peers if peer.getData(indices=[1,2]) > w3.get_total_difficulty() or peer.data[3] != w3.mempool_hash(astype='int')}
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
        robot.param.set("w3_peers", str([(peer.range, peer.bearing) for peer in w3_peers])) 

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

    def sensing(gps = False, as_object = True):
        # gps = True

        # Sense environment for resources
        res = rs.getNew()

        if res:
            if as_object:
                if gps:
                    return Resource(res._json)
                return Resource(res._json)
            else:
                if gps:
                    return {'x':res.x, 'y':res.y, 'json':json.loads(res._json)}
                return {'x':round(res.x + robot.odo.ex, 2), 'y':round(res.y + robot.odo.ey, 2), 'json':json.loads(res._json)}


    def grouping(resource):

        direction = (resource._pv-market._pv).rotate(25, degrees = True).normalize()
        target = direction*(market.radius+cache.radius)/2+market._pv

        # Navigate to the group location
        arrived = True
        if nav.get_distance_to(target) < 0.2*market.radius:           
            nav.avoid(move = True) 
        else:
            nav.navigate(target)
            arrived = False

        return arrived

        ##############################
        ##### STATE-MACHINE STEP #####
        ##############################

        #########################################################################################################
        #### State::INIT
        #########################################################################################################

    if not startFlag:
        startFlag = True 

        robot.log.info('--//-- Starting Experiment --//--')

        for module in [erb, rs, w3]:
            module.start()

        for log in logs.values():
            log.start()

        for clock in clocks.values():
            clock.reset()
        
        # Genesis state configuration
        for i in range(int(lp['environ']['NUMROBOTS'])):
            tx = Transaction(sender = i+1, data = {'function': 'register', 'inputs': []})
            GENESIS.state.apply_transaction(tx, block=GENESIS)

        if lp['patches']['known']:
            for res in robot.param.get("resources"):
                txdata = {'function': 'updatePatch', 'inputs': res._calldata}
                tx = Transaction(sender=0, receiver=0, value=0, data=txdata, timestamp=0)
                GENESIS.state.apply_transaction(tx, block=GENESIS)
    else:

        #########################################################################################################
        #### State::EVERY
        #########################################################################################################
        if True:

            # Perform submodule steps
            for module in [erb, rs, w3, robot.odo, fsm]:
                module.step()

            # Perform clock steps
            for clock in clocks.values():
                clock.time.step()

            # Perform clocked tasks
            peering()

            # Update odometry position
            robot.param.set("odo_position", robot.odo.getPosition())

            if robot.param.get("at") == "cache":
                robot.odo.setPosition()

            # Read patch info from blockchain
            all_patches = w3.sc.getPatches()
            last_block  = w3.get_block('last')

            #(Visualization only, can comment out)
            # robot.param.set("last_block", last_block)
            # robot.param.set("block", str(last_block.height))
            # robot.param.set("tdiff", str(last_block.total_difficulty))
            # robot.param.set("mempl_hash", w3.mempool_hash(astype='str'))
            robot.param.set("block_hash", last_block.hash)
            # robot.param.set("state_hash", str(last_block.state.state_hash))
            robot.param.set("mempl_size", len(w3.mempool))   
            
            robot.param.set("balance", w3.sc.balances[me.id]) 

        # #########################################################################################################
        # #### State::IDLE
        # #########################################################################################################
        if fsm.query(States.IDLE):
            
            if fsm.elapsed < 100:
                homing()

            else:
                fsm.setState(States.PLAN, message = None, pass_along = -1)

        #########################################################################################################
        #### State::PLAN
        #########################################################################################################
        elif fsm.query(States.PLAN):
        
            DISSATISFACTION_MARGIN = 0.0     # How much below average profit we allow before deciding "I'm dissatisfied."
            EXPLORATION_PROB       = 0.05    # Probability of trying a new patch even if we are satisfied
            SWITCH_PROB            = 0.90    # Probability of switching if dissatisfied
            CHOOSE_OLDEST          = 0.5

            # current_action = fsm.pass_along
            # action = current_action
            # my_patch = w3.sc.getMyPatch(me.id)
                
            # # Transition state  
            # if my_patch:
            #     action = my_patch['id']

            # # Transact to be assigned a patch
            # elif not txs['plan']:
            #     txdata = {'function': 'planner', 'inputs': ()}
            #     txs['plan'] = Transaction(sender = me.id, data = txdata, timestamp = w3.custom_timer.time())
            #     w3.send_transaction(txs['plan'])

            # else:
            #     if w3.get_transaction_receipt(txs['plan']):
            #         txs['plan'] = None

            current_action = fsm.pass_along
            action = current_action

            # Get the robot's profit from its last trip
            if tripList:
                my_profit = tripList[-1].profit
            else:
                my_profit = 0

            if current_action == -1:
                my_profit = 0

            # Compute the average patch profit
            all_profits = [p['profit'] for p in all_patches]
            avg_profit = sum(all_profits) / len(all_profits)

            # Decide if we are satisfied or dissatisfied
            # satisfied = (my_profit >= avg_profit - DISSATISFACTION_MARGIN and my_profit >= 0)
            # satisfied = (my_profit >= avg_profit and my_profit >= 0)
            satisfied = (my_profit >= 0)

            if satisfied:
                action = current_action

                # Some probability of exploration 
                if random.random() < EXPLORATION_PROB:

                    for patch in sorted(all_patches, key=lambda p: p['last_drop']):
                        if random.random() < CHOOSE_OLDEST:
                            action = patch['id']
                            break

            if not satisfied:
                action = current_action

                # High probability of changing
                if random.random() < SWITCH_PROB:
                    positive_patches = [p for p in all_patches if p['profit'] > 0]

                    # Idling is better than negative profit
                    if not positive_patches:
                        action = -1

                    if positive_patches:

                        # Weights are the raw profits, so patches with higher profit more likely
                        patch_ids = [p['id'] for p in positive_patches]
                        weights   = [p['profit'] for p in positive_patches]

                        action = random.choices(patch_ids, weights=weights)[0]


            if action == -1:
                fsm.setState(States.IDLE, message = None)

            else:
                patch_to_forage = all_patches[action]
                fsm.setState(States.HOMING, message = None, pass_along = patch_to_forage)


        #########################################################################################################
        #### State::HOMING  
        #########################################################################################################

        elif fsm.query(States.HOMING):

            patch_to_forage = fsm.pass_along

            resource = Resource(patch_to_forage['json'])
            arrived = grouping(resource)

            if arrived:
                Trip(patch_to_forage)
                fsm.setState(States.FORAGE, message = 'Foraging: %s' % (resource._desc), pass_along = patch_to_forage)

        #########################################################################################################
        #### State::FORAGE
        #########################################################################################################
        elif fsm.query(States.FORAGE):

            patch_to_forage = fsm.pass_along
            resource = Resource(patch_to_forage['json'])

            # Distance to resource
            distance = nav.get_distance_to(resource._pr)

            # Resource virtual sensor
            resource_gs = sensing()
            found = resource_gs and resource_gs._p == resource._p
            finished = False

            if found:
                resource = resource_gs

            if found and distance < 0.9*resource.radius:
                robot.param.set("foraging", True)
                nav.avoid(move = True)

                finished = tripList[-1].update(robot.param.get("quantity"))

                if robot.param.get("quantity") >= cp[robot_type]['max_Q']:
                    finished = True

            else:
                nav.navigate_with_obstacle_avoidance(resource._pr)

            ### SHORT-RUN DECISION MAKING
            if finished:
                robot.param.set("foraging", False)

                # # Log the result of the trip
                # logs['firm'].log([*str(tripList[-1]).split()])

                fsm.setState(States.DROP, message = "Collected %s // Profit: %s" % (tripList[-1].Q, round(tripList[-1].profit,2)), pass_along = patch_to_forage)

        #########################################################################################################
        #### State::DROP
        #########################################################################################################
        elif fsm.query(States.DROP):

            patch_to_forage = fsm.pass_along
            resource = Resource(patch_to_forage['json'])

            # Navigate home
            arrived = dropping(patch_to_forage)

            if arrived:

                # Transact to drop resource
                if not txs['drop']:
                    robot.log.info(f"Dropping. Q:{tripList[-1].Q} FC:{tripList[-1].FC} TC:{tripList[-1].TC} ATC:{tripList[-1].ATC}")

                    AP = patch_to_forage['util'] - tripList[-1].ATC

                    txdata = {'function': 'dropResource', 'inputs': resource._calldata+(tripList[-1].Q, tripList[-1].TC, AP)}
                    txs['drop'] = Transaction(sender = me.id, data = txdata, timestamp = w3.custom_timer.time())
                    w3.send_transaction(txs['drop'])
   
                # Transition state  
                else:
                    if w3.get_transaction_receipt(txs['drop'].id):
                        robot.param.set("dropResource", "True")

                        if not robot.param.get("hasResource"):
                            txs['drop'] = None
                            robot.param.set("dropResource", "")   
                            fsm.setState(States.PLAN, message = "Dropped: %s" % resource._desc, pass_along = patch_to_forage['id'])   




        # #########################################################################################################
        # #### State::EVADING
        # #########################################################################################################

        # elif fsm.query(States.EVADING):

        #     arrived = evading(fsm.pass_along)

        #     if arrived:
        #         fsm.setState(States.HOMING)

        # #########################################################################################################
        # #### State::HOMING
        # #########################################################################################################

        # elif fsm.query(States.HOMING):

        #     arrived = homing()

        #     if arrived:
        #         fsm.setState(States.PLAN)






        # #########################################################################################################
        # #### State::EXPLORE
        # #########################################################################################################

        # elif fsm.query(States.EXPLORE):

        #     # Perform a random-walk 
        #     rw.step()

        #     # Look for resources
        #     patch_gs = sensing()

        #     # Sucess exploration: transact
        #     if patch_gs and not txs['update']:
        #         txdata = {'function': 'propose', 'inputs': (patch_gs['x'], patch_gs['y'], patch_gs['json'])}
        #         txs['update'] = Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
        #         w3.send_transaction(txs['update'])
            
        #         robot.log.info(f"Discovered {patch_gs['json']['quality']}")

        #         fsm.setState(States.FORAGE, message = "Found patch", pass_along=patch_gs)
        #         txs['update'] = None

        #     elif clocks['explore'].query():
        #         fsm.setState(States.HOMING, message = "Finished exploring")
        #         txs['update'] = None


        # #########################################################################################################
        # #### State::VERIFY
        # #########################################################################################################

        # elif fsm.query(States.VERIFY):
            
        #     patch_to_verify = fsm.pass_along
        #     arrived = False
        #     found   = False
        #     listen  = False

        #     # Navigate to resource
        #     distance = nav.navigate_with_obstacle_avoidance((patch_to_verify['x'], patch_to_verify['y']))
            
        #     # Sense for resources
        #     patch_gs = sensing()

        #     if patch_gs and patch_gs['json']['x'] == patch_to_verify['json']['x'] and patch_to_verify['json']['y'] == patch_to_verify['json']['y']:
        #         found = True

        #     # Navigate to verify
        #     if distance < 0.9*patch_to_verify['json']['radius']:
        #         arrived    = True   

        #     # Arrived but not found: explore nearby
        #     if arrived and not found:
        #         rw.step(local=True, target=(patch_to_verify['x'],patch_to_verify['y']))

        #     # # Listen for the explorer
        #     # for peer in erb.peers:
        #     #     if peer.id in patch_to_verify['explorers']:
        #     #         explorer = peer
        #     #         listen = True

        #     # # Can hear broadcast from explorer: navigate towards
        #     # if listen:
        #     #     bearing  = explorer.bearing
        #     #     distance = explorer.range
        #     #     target = Vector2D(distance, bearing, polar=True)
        #     #     nav.navigate_with_obstacle_avoidance(target, local = True)

        #     # Found the patch: transact
        #     if found:
                
        #         txdata = {'function': 'verify', 'inputs': (patch_gs['x'], patch_gs['y'], patch_gs['json'])}
        #         txs['update'] =  Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
        #         w3.send_transaction(txs['update'])
                
        #         robot.log.info(f"Verified {patch_to_verify['json']['quality']}")

        #         fsm.setState(States.EVADING, message = "Verify success", pass_along = patch_to_verify)
            
        #     elif fsm.elapsed > 800:
        #         txdata = {'function': 'verify', 'inputs': (0, 0, patch_to_verify['json'], True)}
        #         txs['update'] =  Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
        #         w3.send_transaction(txs['update'])

        #         robot.log.info(f"Rejected {patch_to_verify['json']['quality']}")
        #         fsm.setState(States.HOMING, message = "Verify failed")


#########################################################################################################################
#### RESET-DESTROY STEPS ################################################################################################
#########################################################################################################################

def reset():
    pass

def destroy():
    if startFlag:
        w3.stop_mining()
        # txs    = w3.get_all_transactions()
        # my_txs = w3.my_transactions

        # if len(txs) != len(set([tx.id for tx in txs])):
        #     print(f'REPEATED TX ON CHAIN: #{len(txs)-len(set([tx.id for tx in txs]))}')

        # for tx in my_txs:
        #     if tx.id not in [tx.id for tx in txs+list(w3.mempool.values())]:
        #         print(f'ONE OF MY TX IS LOST !')

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

        # Log the result of the each trip performed by robot
        name   = 'firm.csv'
        header = ['TSTART', 'FC', 'Q', 'C', 'MC', 'TC', 'ATC', 'PROFIT', 'UTIL', 'QLTY', 'PATCH']
        logs['firm'] = Logger(f"{experimentFolder}/logs/{me.id}/{name}", header, ID = me.id)

        for trip in tripList:
            if trip.finished:
                logs['firm'].log([*str(trip).split()])

        # Log each block 
        name   = 'block.csv'
        header = ['TELAPSED','TIMESTAMP','BLOCK', 'HASH', 'PHASH', 'DIFF', 'TDIFF', 'SIZE', 'SIZEDATA', 'SIZESTATE', 'TXS', 'BALANCE']
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
                sys.getsizeof(block.data) / 1024, 
                sys.getsizeof(block.state) / 1024, 
                len(block.data),
                block.state.balances.get(me.id,0)
                ])

        # Log the state of each block
        name   = 'sc.csv'
        header = ['TIMESTAMP', 'BLOCK', 'HASH', 'PHASH', 'X','Y','QTTY', 'QLTY', 'UTIL', 'PATCH', 'BALANCE']
        logs['sc'] = Logger(f"{experimentFolder}/logs/{me.id}/{name}", header, ID = me.id)

        for block in w3.chain:
            for patch in block.state.patches:
                logs['sc'].log(
                    [block.timestamp, 
                    block.height, 
                    block.hash, 
                    block.parent_hash, 
                    patch['x'],       
                    patch['y'],       
                    patch['qtty'], 
                    patch['qlty'],  
                    patch['util'],  
                    patch['id'],  
                    patch['profit'],             
                    ])
        
    print('Killed robot '+ me.id)

def normalize(values):
    min_val, max_val = min(values), max(values)

    # Avoid division by zero; return all 1.0 or 0.0
    if min_val == max_val:
        return [1.0 for _ in values]
    
    return [(v - min_val) / (max_val - min_val) for v in values]
#########################################################################################################################
#########################################################################################################################
#########################################################################################################################