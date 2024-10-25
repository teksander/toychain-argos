#!/usr/bin/env python3
# This is the main control loop running in each argos robot

# /* Import Packages */
#######################################################################
import random, math
import time, sys, os
import json

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.actusensors.movement     import RandomWalk, Navigate, Odometry, OdoCompass, GPS
from controllers.actusensors.groundsensor import ResourceVirtualSensor, Resource
from controllers.actusensors.erandb       import ERANDB
from controllers.actusensors.rgbleds      import RGBLEDs
from controllers.utils import *
from controllers.utils import Timer
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

clocks['peering']  = Timer(30)
# clocks['query']    = Timer(5)
clocks['explore']  = Timer(0)
clocks['block']    = Timer(BLOCK_PERIOD)
clocks['decision'] = Timer(BLOCK_PERIOD*cp['firm']['entry_f'])

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
    JOIN   = 6
    LEAVE  = 7
    HOMING = 8
    TRANSACT = 9
    RANDOM   = 10
    EXPLORE  = 11
    VERIFY   = 12

class ResourceBuffer(object):
    """ Establish the resource buffer class 
    """
    def __init__(self, ageLimit = 2):
        """ Constructor
        :type id__: str
        :param id__: id of the peer
        """
        # Add the known peer details
        self.buffer = []
        self.ageLimit = ageLimit
        self.best = None

    def getJSON(self, resource):
        return resource._json

    def getJSONs(self, idx = None):
        return {self.getJSON(res) for res in self.buffer}

    def addResource(self, new_res, update_best = False):
        """ This method is called to add a new resource
        """   
        if isinstance(new_res, str):
            new_res = Resource(new_res)

        # Is in the buffer? NO -> Add to buffer
        if (new_res.x, new_res.y) not in self.getLocations():
            res = new_res
            self.buffer.append(res)
            robot.log.info("Added: %s; Total: %s " % (res._desc, len(self)))

        # Is in the buffer? YES -> Update buffer
        else:
            res = self.getResourceByLocation((new_res.x, new_res.y))

            # if new_res.quantity < res.quantity or new_res._timeStamp > res._timeStamp:
            if new_res.quantity < res.quantity:
                res.quantity = new_res.quantity
                res._timeStamp = new_res._timeStamp
                # robot.log.info("Updated resource: %s" % self.getJSON(res))

        if update_best:
            self.best = self.getResourceByLocation((new_res.x, new_res.y))

        return res

    def removeResource(self, resource):
        """ This method is called to remove a peer Id
            newPeer is the new peer object
        """   
        self.buffer.remove(resource)
        robot.log.info("Removed resource: "+self.getJSON(resource))

    def __len__(self):
        return len(self.buffer)

    def sortBy(self, by = 'value', inplace = True):

        if inplace:
            if by == 'timeStamp':
                pass
            elif by == 'value':
                self.buffer.sort(key=lambda x: x.utility, reverse=True)
        else:
            return self.buffer.sort(key=lambda x: x.utility, reverse=True)

    def getLocations(self):
        return [(res.x, res.y) for res in self.buffer]

    def getDistances(self, x, y):
        return [math.sqrt((x-res.x)**2 + (y-res.y)**2) for res in self.buffer]

    def getResourceByLocation(self, location):
        return self.buffer[self.getLocations().index(location)]

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
        self.price = self.util * patch['epoch']['price']
        
        self.finished = False

        tripList.append(self)

    @property
    def timedelta(self):
        timedelta = w3.custom_timer.time() - self.tStart
        return round(timedelta, 2)

    def update(self, Q):
        finished = False

        # Update price
        self.price = self.util * w3.sc.getMyPatch(me.id)['epoch']['price']

        if self.FC == 0:
            self.FC = self.timedelta

        C  = self.timedelta-self.FC
        
        if len(self.C) > 0 and C-self.C[-1] > 1.05*self.price:
            robot.log.info("Finished before collection %s" % (C-self.C[-1]))
            finished = True

        if int(Q) > self.Q:
            finished = False
            self.Q = int(Q)
            self.C.append(C)

            if len(self.C) > 1:
                MC = self.C[-1]-self.C[-2]
                robot.log.info(f"Q: {self.Q} // MC: {MC} // P: {round(self.price,0)}")
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
        return "%i %i %i %s %s %i %i %i %i %s" % (self.tStart, self.FC, self.Q, C, MC, self.TC, self.ATC, self.profit, self.util, self.qlty)        

####################################################################################################################################################################################
#### INIT STEP #####################################################################################################################################################################
####################################################################################################################################################################################

def init():
    global clocks,counters, logs, submodules, me, rw, nav, odo, gps, rb, w3, fsm, rs, erb, rgb
    robotID, robotIP = str(int(robot.variables.get_id()[2:])+1), '127.0.0.1'
    robot.variables.set_attribute("id", str(robotID))
    robot.variables.set_attribute("circle_color", "gray50")
    robot.variables.set_attribute("scresources", "[]")
    robot.variables.set_attribute("foraging", "")
    robot.variables.set_attribute("dropResource", "")
    robot.variables.set_attribute("hasResource", "")
    robot.variables.set_attribute("resourceCount", "0")
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

    # /* Initialize Console Logging*/
    #######################################################################
    log_folder = experimentFolder + '/logs/' + robotID + '/'

    # Monitor logs (recorded to file)
    name =  'monitor.log'
    os.makedirs(os.path.dirname(log_folder+name), exist_ok=True) 
    logging.basicConfig(filename=log_folder+name, filemode='w+', format='[{} %(levelname)s %(name)s] %(message)s'.format(robotID))
    logging.getLogger('sc').setLevel(10)
    logging.getLogger('w3').setLevel(70)
    logging.getLogger('poa').setLevel(70)
    robot.log = logging.getLogger()
    robot.log.setLevel(10)

    # /* Initialize submodules */
    #######################################################################
    # # /* Init web3.py */
    robot.log.info('Initialising Python Geth Console...')
    w3 = Node(robotID, robotIP, 1233 + int(robotID), ProofOfAuthority(genesis = GENESIS))

    # /* Init an instance of peer for this Pi-Puck */
    me = Peer(robotID, robotIP, w3.enode, w3.key)

    # /* Init an instance of the buffer for resources  */
    robot.log.info('Initialising resource buffer...')
    rb = ResourceBuffer()

    # /* Init E-RANDB __listening process and transmit function
    robot.log.info('Initialising RandB board...')
    erb = ERANDB(robot, cp['erbDist'] , cp['erbtFreq'])

    #/* Init Resource-Sensors */
    robot.log.info('Initialising resource sensor...')
    rs = ResourceVirtualSensor(robot)
    
    # /* Init Random-Walk, __walking process */
    robot.log.info('Initialising random-walk...')
    rw = RandomWalk(robot, cp['scout_speed'])

    # /* Init Navigation, __navigate process */
    robot.log.info('Initialising navigation...')
    nav = Navigate(robot, cp['recruit_speed'])

    # /* Init odometry sensor */
    robot.log.info('Initialising odometry...')
    odo = OdoCompass(robot)

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

        # Turn on LEDs according to geth peer count
        rgb.setLED(rgb.all, rgb.presets.get(len(w3.peers), 3*['red']))

    def homing():

        # Navigate to the market
        arrived = True

        if nav.get_distance_to(market._pr) < 0.9*market.radius:           
            nav.avoid(move = True)
            
        elif nav.get_distance_to(market._pr) < market.radius and len(w3.peers) > 1:
            nav.avoid(move = True)

        else:
            nav.navigate_with_obstacle_avoidance(market._pr)
            arrived = False

        return arrived

    def dropping(resource):

        direction = (resource._pv-market._pv).rotate(-25, degrees = True).normalize()
        target = direction*(market.radius+cache.radius)/2+market._pv

        # Navigate to drop location
        arrived = True

        if nav.get_distance_to(market._p) < market.radius + 0.5* (cache.radius-market.radius):
            nav.avoid(move = True)
        else:
            nav.navigate_with_obstacle_avoidance(target)
            arrived = False

        return arrived

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

    def sensing(global_pos = True):

        # Sense environment for resources
        res = rs.getNew()

        if res:
            if global_pos:
                # Use resource with GPS coordinates
                rb.addResource(res)

            else:
                # Add odometry error to resource coordinates
                error = odo.getPosition() - gps.getPosition()
                res.x += error.x
                res.y += error.y

                # use resource with odo coordinates
                rb.addResource(Resource(res._json))

            return res

    def decision(patch, N):
        
        epoch = patch['epoch']
        Kp    = cp['firm']['entry_Kp']
        Ki    = cp['firm']['entry_Ki']

        def AP(window = 1):
            if not epoch['ATC']:
                return 0

            window = min(window, len(epoch['ATC']))

            return patch['util']*epoch['price'] - sum(epoch['ATC'][-window:]) / window
            
        # Proportional decision probability
        Pt = Kp/10 * 1/(patch['util']*patch['epoch']['price']) * AP(1)

        # Integrated decision probability
        Pt += Ki/10 * 1/(patch['util']) * AP(cp['firm']['entry_w'])

        if Pt > 1: 
            P = 1
        else:
            P  = 1 - (1-Pt)**(1/N)
        
        robot.log.info(f"last AP @ {patch['qlty']}: {round(AP(1))}")
        robot.log.info(f"last {cp['firm']['entry_w']} APs @ {patch['qlty']}: {round(AP(cp['firm']['entry_w']))}")
        robot.log.info(f"Entry/exit: {round(100*P, 2)}% ({round(100*Pt, 1)}%)")

        if random.random() < abs(P):
            if P < 0:
                return 'exit'
            else:
                return 'entry'
        else:
            return None

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
        for module in [erb, rs, w3]:
            module.step()

        # Perform clock steps
        for clock in clocks.values():
            clock.time.step()

        # Perform clocked tasks
        if clocks['peering'].query():
            peering()

        # Share blockchain sync details through erb
        erb.setData(w3.get_block('last').total_difficulty, indices=[1,2])
        erb.setData(w3.mempool_hash(astype='int'), indices=3)


        # Read patch info from blockchain
        patches    = w3.sc.getPatches()
        my_patch   = w3.sc.getMyPatch(me.id)
        verified   = [p for p in patches if p['status'] == 'verified' and me.id not in p["votes_remove"]]
        unverified = [p for p in patches if p['status'] == 'pending']
        unverified_by_me = [p for p in unverified if me.id not in p['votes']]

        def forage_decision():
            return my_patch and my_patch['status'] == 'verified' and my_patch['totw'] == my_patch['maxw']

        # #(Visualization only, can comment out)
        # last_block = w3.get_block('last')
        # robot.variables.set_attribute("block", str(last_block.height))
        # robot.variables.set_attribute("tdiff", str(last_block.total_difficulty))
        # robot.variables.set_attribute("mempl_hash", w3.mempool_hash(astype='str'))
        # robot.variables.set_attribute("block_hash", str(last_block.hash))
        # robot.variables.set_attribute("state_hash", str(last_block.state.state_hash))
        # robot.variables.set_attribute("mempl_size", str(len(w3.mempool)))
        w3_peers = {peer for peer in erb.peers if peer.getData(indices=[1,2]) > w3.get_total_difficulty() or peer.data[3] != w3.mempool_hash(astype='int')}
        robot.variables.set_attribute("w3_peers", str([(peer.range, peer.bearing) for peer in w3_peers])) 

        # (Visualization only, can comment out)
        robot.variables.set_attribute("verified", str([(p['x'], p['y'], p['qlty']) for p in patches if p['status'] == 'verified']))
        robot.variables.set_attribute("pending",  str([(p['x'], p['y'], p['qlty']) for p in patches if p['status'] == 'pending']))
        #########################################################################################################
        #### State::IDLE
        #########################################################################################################
        if fsm.query(States.IDLE):

            action = random.choices(('explore', 'verify', 'forage'),weights=(10, 30, 50))[0]
            action = 'explore'
            # if forage_decision():
            #     action = 'forage'

            if action == 'explore':

                # State transition: EXPLORE
                explore_duration = random.gauss(cp['explore_mu'], cp['explore_sg'])*10
                clocks['explore'].set(explore_duration)
                fsm.setState(States.EXPLORE, message = "Duration: %.2f" % explore_duration)

            # elif action == 'verify' and unverified_by_me:

            #     # State transition: VERIFY
            #     patch = random.choice(unverified_by_me)
            #     fsm.setState(States.VERIFY, pass_along = patch)

            # elif action == 'join' and verified:

            #     # State transition: JOIN
            #     availiable = [p for p in verified if p['totw'] < p['maxw']]
            #     if availiable:
            #         patch = random.choice(availiable)
            #         fsm.setState(States.JOIN, pass_along = patch)

            elif action == 'forage':

                # State transition: FORAGE
                rb.addResource(my_patch['json'], update_best = True)
                fsm.setState(States.FORAGE)

            else:
                homing()

        #########################################################################################################
        #### State::JOIN
        #########################################################################################################
        # elif fsm.query(States.JOIN):

        #     patch = fsm.pass_along

        #     if not txs['join']:
        #         txs['join'] = Transaction(me.id, data = {'function': 'joinPatch', 'inputs': [patch['id']]}, timestamp = w3.custom_timer.time())
        #         w3.send_transaction(txs['join'])

        #     if txs['join']:
        #         homing()

        #         if w3.get_transaction_receipt(txs['join'].id):
        #             fsm.setState(States.IDLE, message = "Join transaction success")
        #             txs['join'] = None
                    
        #########################################################################################################
        #### State::EXPLORE
        #########################################################################################################

        elif fsm.query(States.EXPLORE):

            # Perform a random-walk 
            rw.step()

            # Look for resources
            res = sensing()

            # Sucess exploration: transact
            if res:
                print(f"{me.id} discovered {res.quality}")
                rb.addResource(res._json, update_best = True)
                fsm.setState(States.FORAGE, message = "Foraging {res.quality}")

            # Transition state
            if clocks['explore'].query():
                fsm.setState(States.IDLE, message = "No discovery")


        #########################################################################################################
        #### State::VERIFY
        #########################################################################################################

        # elif fsm.query(States.VERIFY):
            
        #     # Navigate to verify
        #     nav.navigate_with_obstacle_avoidance((fsm.pass_along['x'],fsm.pass_along['y']))

        #     # Look for resources
        #     res = sensing()

        #     # Sucess exploration: transact
        #     if res and not txs['update']:
        #         print(f"{me.id} verified {res.quality}")
        #         txdata = {'function': 'updatePatch', 'inputs': res._calldata}
        #         txs['update'] = Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
        #         w3.send_transaction(txs['update'])
            
        #     if txs['update']:
        #         homing()

        #         if w3.get_transaction_receipt(txs['update'].id):
        #             txs['update'] = None
        #             fsm.setState(States.IDLE, message = "Verify transaction success")

        #########################################################################################################
        #### State::FORAGE
        #########################################################################################################
        elif fsm.query(States.FORAGE):

            # Distance to resource
            distance = nav.get_distance_to(rb.best._pr)

            # Resource virtual sensor
            res = sensing()

            found = res and res._p == rb.best._p

            finished = False
            depleted = False

            if not found and distance < 0.8*rb.best.r:
                finished = True
                depleted = True

            if found:
                rb.best = res

            if found and distance < 0.9*rb.best.radius:
                robot.variables.set_attribute("foraging", "True")
                nav.avoid(move = True)

                # finished = tripList[-1].update(robot.variables.get_attribute("quantity"))

                if int(robot.variables.get_attribute("quantity")) >= cp['max_Q']:
                    finished = True

            else:
                nav.navigate_with_obstacle_avoidance(rb.best._pr)

            if finished:
                if depleted:
                    robot.log.info("Resource is depleted. Updating")
                    print(f"{me.id} found depleted. Updating")
                    rb.best.quantity = 0 
                    # txdata = {'function': 'updatePatch', 'inputs': rb.best._calldata+(True,)}
                    # tx = Transaction(sender = me.id, receiver = 0, value = 0, data = txdata, timestamp = w3.custom_timer.time())
                    # w3.send_transaction(tx)
                    # tx = Transaction(me.id, data = {'function': 'leavePatch', 'inputs': []}, timestamp = w3.custom_timer.time())
                    # w3.send_transaction(tx)

                robot.variables.set_attribute("foraging", "")
                fsm.setState(States.DROP, message = f"Collected {robot.variables.get_attribute('quantity')} {rb.best.quality}")

        #########################################################################################################
        #### State::DROP
        #########################################################################################################
        elif fsm.query(States.DROP):

            # Navigate home
            arrived = dropping(rb.best)

            if arrived:

                # Transact to drop resource
                if not txs['drop']:
                    robot.log.info(f"Dropping.")
                    txdata = {'function': 'dropResource', 'inputs': []}
                    txs['drop'] = Transaction(sender = me.id, data = txdata, timestamp = w3.custom_timer.time())
                    w3.send_transaction(txs['drop'])
   
                # Transition state  
                else:
                    if w3.get_transaction_receipt(txs['drop'].id):
                        robot.variables.set_attribute("dropResource", "True")

                        if not robot.variables.get_attribute("hasResource"):
                            txs['drop'] = None
                            robot.variables.set_attribute("dropResource", "")   
                            fsm.setState(States.IDLE, message = "Dropped: %s" % rb.best._desc)                       

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
        header = ['TIMESTAMP', 'BLOCK', 'HASH', 'PHASH', 'BALANCE', 'TX_COUNT', 'X','Y','QTTY', 'QLTY', 'ID', 'TOTW']
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
                    patch['x'],  # 'x' coordinate of the patch
                    patch['y'],  # 'y' coordinate of the patch
                    patch['qtty'],  # Patch quantity (qtty)
                    patch['qlty'],  # Patch quality (qlty)
                    patch['id'],  # Patch ID
                    patch['totw'],  # Total weight or work in the patch (totw)
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