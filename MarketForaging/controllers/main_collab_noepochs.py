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
clocks['sensing']  = Timer(5)
clocks['block']    = Timer(BLOCK_PERIOD)
clocks['decision'] = Timer(BLOCK_PERIOD*cp['firm']['entry_f'])

# Store the position of the market and cache
market   = Resource({"x":lp['market']['x'], "y":lp['market']['y'], "radius": lp['market']['r']})
cache    = Resource({"x":lp['cache']['x'], "y":lp['cache']['y'], "radius": lp['cache']['r']})

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

global geth_peer_count
GENESIS = Block(0, 0000, [], [gen_enode(i+1) for i in range(int(lp['environ']['NUMROBOTS']))], 0, 0, 0, nonce = 1, state = State())

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
        self.price = patch['util']*patch['epoch']['price']
        self.finished = False
        # self.price = 1000
        tripList.append(self)

    @property
    def timedelta(self):
        timedelta = w3.custom_timer.time() - self.tStart
        return round(timedelta, 2)

    def update(self, Q):
        finished = False

        if self.FC == 0:
            self.FC = self.timedelta

        C  = self.timedelta-self.FC
        
        if len(self.C) > 0 and C-self.C[-1] > 1.25*self.price:
            robot.log.info("Finished before collection %s" % (C-self.C[-1]))
            finished = True

        if int(Q) > self.Q:
            finished = False
            # patch  = tcp_sc.request(data = 'getPatch')
            # self.price = patch['util']*patch['epoch']['price']
            self.Q = int(Q)
            self.C.append(C)

            if len(self.C) > 1:
                MC = self.C[-1]-self.C[-2]
                robot.log.info("Collected %i // MC: %i" % (self.Q, MC))
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
        return "%i %i %i %s %s %i %i %i" % (self.tStart, self.FC, self.Q, C, MC, self.TC, self.ATC, self.profit)        

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
    # name   = 'resource.csv'
    # header = ['COUNT']
    # logs['resources'] = Logger(log_folder+name, header, rate = 5, ID = me.id)

    # name   = 'firm.csv'
    # header = ['TSTART', 'FC', 'Q', 'C', 'MC', 'TC', 'ATC', 'PROFIT']
    # logs['firm'] = Logger(log_folder+name, header, ID = me.id)

    # name   = 'epoch.csv'
    # header = ['RESOURCE_ID', 'NUMBER', 'BSTART', 'Q', 'TC', 'ATC', 'price']
    # # header =w3.sc.functions.Epoch_key().call()
    # logs['epoch'] = Logger(log_folder+name, header, ID = me.id)

    # name   = 'robot_sc.csv'
    # header = ["isRegistered", "efficiency", "income", "balance", "task"]
    # # header = w3.sc.functions.Robot_key().call()
    # logs['robot_sc'] = Logger(log_folder+name, header, ID = me.id)

    # name   = 'fsm.csv'
    # header = stateList
    # logs['fsm'] = Logger(log_folder+name, header, rate = 10, ID = me.id)

    # name   =  'odometry.csv'
    # header = ['DIST']
    # logs['odometry'] = Logger(log_folder+name, header, rate = 10, ID = me.id)

    txs['sell'] = None
    txs['buy']  = None
    txs['drop'] = None

#########################################################################################################################
#### CONTROL STEP #######################################################################################################
#########################################################################################################################
global pos
pos = [0,0]
global last
last = 0

def controlstep():
    global last, pos, clocks, counters, startFlag, startTime

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
        if clocks['sensing'].query(): 
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

        def AP(window = 1):

            if not epoch['ATC']:
                return 0
            
            window = min(window, len(epoch['ATC']))
            return patch['util'] * epoch['price'] - sum(epoch['ATC'][-window:]) / window
            
        # Proportional decision probability
        Pt = cp['firm']['entry_Kp']/10 * 1/(patch['util']*epoch['price']) * AP(1)

        # Integrated decision probability
        Pt += cp['firm']['entry_Ki']/10 * 1/(patch['util']*epoch['price']) * AP(cp['firm']['entry_w'])

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
        startTime = 0

        robot.log.info('--//-- Starting Experiment --//--')

        for module in [erb, w3]:
            try:
                module.start()
            except:
                robot.log.critical('Error Starting Module: %s', module)
                sys.exit()

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
        for module in [erb, rs, odo, w3]:
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

        # Get perfect position if at nest
        if robot.variables.get_attribute("at") == "cache":
            odo.setPosition()

        # Update blockchain state on the robot C++ object (Visualization only, can comment out)
        last_block = w3.get_block('last')
        robot.variables.set_attribute("block", str(last_block.height))
        robot.variables.set_attribute("tdiff", str(last_block.total_difficulty))
        robot.variables.set_attribute("mempl_hash", w3.mempool_hash(astype='str'))
        robot.variables.set_attribute("block_hash", str(last_block.hash))
        robot.variables.set_attribute("state_hash", str(last_block.state.state_hash))
        robot.variables.set_attribute("mempl_size", str(len(w3.mempool)))
        w3_peers = {peer for peer in erb.peers if peer.getData(indices=[1,2]) > w3.get_total_difficulty() or peer.data[3] != w3.mempool_hash(astype='int')}
        robot.variables.set_attribute("w3_peers", str([(peer.range, peer.bearing) for peer in w3_peers])) 

        #########################################################################################################
        #### State::IDLE
        #########################################################################################################
        if fsm.query(States.IDLE):

            fsm.setState(States.PLAN, message = "Planning")

        #########################################################################################################
        #### State::PLAN  
        ######################################################################################################### 

        elif fsm.query(States.PLAN):

            if clocks['decision'].query():
                
                my_patch = w3.sc.getMyPatch(me.id)

                if my_patch:
                    if decision(my_patch, my_patch['totw']) == 'exit':
                        fsm.setState(States.PLAN, message = "Leaving patch")
                        tx = Transaction(sender = me.id, receiver = 2, value = 0, data = {'function': 'leavePatch', 'inputs': []}, nonce = last, timestamp = w3.custom_timer.time())
                        w3.send_transaction(tx)
                        my_patch = None
                    else:
                        rb.addResource(my_patch['json'], update_best = True)
                        fsm.setState(States.HOMING, message = None)

                else:
                    all_patches = w3.sc.getPatches()
                    idle_robots = len(w3.sc.robots)-sum([p['totw'] for p in all_patches])

                    for patch in random.sample(all_patches, len(all_patches)):  
                        if decision(patch, idle_robots) == 'entry':
                            tx = Transaction(me.id, data = {'function': 'joinPatch', 'inputs': [patch['id']]}, nonce = last, timestamp = w3.custom_timer.time())
                            w3.send_transaction(tx)
                            rb.addResource(patch['json'], update_best = True)
                            fsm.setState(States.HOMING, message = f"Joining: {patch['json']}")
                            break
            else:
                homing()

        #########################################################################################################
        #### State::HOMING  
        #########################################################################################################

        elif fsm.query(States.HOMING):

            arrived = grouping(rb.best)

            if arrived:

                my_patch = w3.sc.getMyPatch(me.id)

                if my_patch:
                    rb.addResource(my_patch['json'], update_best = True)
                    Trip(my_patch)
                    fsm.setState(States.FORAGE, message = 'Foraging: %s' % (rb.best._desc))

        #########################################################################################################
        #### State::FORAGE
        #########################################################################################################
        elif fsm.query(States.FORAGE):

            # Distance to resource
            distance = nav.get_distance_to(rb.best._pr)

            # Resource virtual sensor
            resource = sensing()
            found = resource and resource._p == rb.best._p
            finished = False

            if found:
                rb.best = resource

            if found and distance < 0.9*rb.best.radius:
                robot.variables.set_attribute("foraging", "True")
                nav.avoid(move = True)

                finished = tripList[-1].update(robot.variables.get_attribute("quantity"))

                # if int(robot.variables.get_attribute("quantity")) >= cp['max_Q']:
                #     finished = True

            else:
                nav.navigate_with_obstacle_avoidance(rb.best._pr)

            ### SHORT-RUN DECISION MAKING
            if finished:
                robot.variables.set_attribute("foraging", "")

                # # Log the result of the trip
                # logs['firm'].log([*str(tripList[-1]).split()])

                fsm.setState(States.DROP, message = "Collected %s // Profit: %s" % (tripList[-1].Q, round(tripList[-1].profit,2)))

        #########################################################################################################
        #### State::DROP
        #########################################################################################################
        elif fsm.query(States.DROP):

            # Navigate home
            arrived = dropping(rb.best)

            if arrived:

                # Transact to drop resource
                if not txs['drop']:
                    robot.log.info(f"Dropping. FC:{tripList[-1].FC} TC:{tripList[-1].TC} ATC:{tripList[-1].ATC}")
                    txdata = {'function': 'dropResource', 'inputs': rb.best._calldata+(tripList[-1].Q, tripList[-1].TC)}
                    txs['drop'] = Transaction(sender = me.id, data = txdata, timestamp = w3.custom_timer.time())
                    w3.send_transaction(txs['drop'])
   
                # Transition state  
                else:
                    if w3.get_transaction_receipt(txs['drop'].id):
                        robot.variables.set_attribute("dropResource", "True")

                        if not robot.variables.get_attribute("hasResource"):
                            txs['drop'] = None
                            robot.variables.set_attribute("dropResource", "")   
                            fsm.setState(States.PLAN, message = "Dropped: %s" % rb.best._desc)                       

#########################################################################################################################
#### RESET-DESTROY STEPS ################################################################################################
#########################################################################################################################

def reset():
    pass

def destroy():
    if startFlag:
        w3.stop_mining()
        txs = w3.get_all_transactions()
        if len(txs) != len(set([tx.id for tx in txs])):
            print(f'REPEATED TRANSACTIONS ON CHAIN: #{len(txs)-len(set([tx.id for tx in txs]))}')


        for key, value in w3.sc.state.items():
            
            if isinstance(value, list):
                print(f"{key}:")
                for item in value:
                    print(f"{item}")  # Indented list item for clarity
            else:
                print(f"{key}: {value}")

        # Log the result of the each trip performed by robot
        name   = 'firm.csv'
        header = ['TSTART', 'FC', 'Q', 'C', 'MC', 'TC', 'ATC', 'PROFIT']
        logs['firm'] = Logger(f"{experimentFolder}/logs/{me.id}/{name}", header, ID = me.id)

        for trip in tripList:
            if trip.finished:
                logs['firm'].log([*str(trip).split()])

        # Log each block over the operation of the swarm
        name   = 'block.csv'
        header = ['TELAPSED','TIMESTAMP','BLOCK', 'HASH', 'PHASH', 'DIFF', 'TDIFF', 'SIZE','TXS', 'UNC', 'PENDING', 'QUEUED']
        logs['block'] = Logger(f"{experimentFolder}/logs/{me.id}/{name}", header, ID = me.id)

        for block in w3.chain:
            logs['block'].log(
                [w3.custom_timer.time()-block.timestamp, 
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
        header = ['TIMESTAMP', 'BLOCK', 'HASH', 'PHASH', 'BALANCE', 'TX_COUNT', 'X','Y','QTTY', 'QLTY', 'ID', 'TOTW','number', 'start', 'Q', 'TC', 'ATC', 'price', 'robots', 'TQ', 'AATC', 'AP']
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
                    patch['epoch']['number'],  # Epoch number
                    patch['epoch']['start'],   # Epoch start time
                    str(patch['epoch']['Q']).replace(' ', ''),  # Epoch 'Q' value
                    str(patch['epoch']['TC']).replace(' ', ''),  # Epoch 'TC' value
                    str(patch['epoch']['ATC']).replace(' ', ''),  # Epoch 'ATC' value
                    patch['epoch']['price'],  # Price during the epoch
                    str(patch['epoch']['robots']).replace(' ', ''),  # List of robots in the epoch
                    patch['epoch']['TQ'],  # Total quantity (TQ) during the epoch
                    patch['epoch']['AATC'],  # Average ATC during the epoch
                    patch['epoch']['AP']  # Average price (AP) during the epoch
                    ])

        
    print('Killed robot '+ me.id)

#########################################################################################################################
#########################################################################################################################
#########################################################################################################################


def getEnodes():
    return [peer['enode'] for peer in w3.geth.admin.peers()]

def getEnodeById(__id, gethEnodes = None):
    if not gethEnodes:
        gethEnodes = getEnodes() 

    for enode in gethEnodes:
        if readEnode(enode, output = 'id') == __id:
            return enode

def getIds(__enodes = None):
    if __enodes:
        return [enode.split('@',2)[1].split(':',2)[0].split('.')[-1] for enode in __enodes]
    else:
        return [enode.split('@',2)[1].split(':',2)[0].split('.')[-1] for enode in getEnodes()]






















        #########################################################################################################
        #### Scout.EXPLORE
        #########################################################################################################

        # elif fsm.query(Scout.EXPLORE):

        #     if clocks['block'].query():

        #         # Confirm I am still scout
        #         fsm.setState(States.PLAN, message = None)

        #     else:

        #         # Perform a random-walk 
        #         rw.step()

        #         # Look for resources
        #         sensing()

        #         # Transition state
        #         if clocks['explore'].query(reset = False):

        #             # Sucess exploration: Sell
        #             if rb.buffer:
        #                 fsm.setState(Scout.SELL, message = "Found %s" % len(rb))

        #             # Unsucess exploration: Buy
        #             else:
        #                 clocks['buy'].reset()
        #                 fsm.setState(States.ASSIGN, message = "Found %s" % len(rb))


        #########################################################################################################
        #### Scout.SELL
        #########################################################################################################

        # elif fsm.query(Scout.SELL):

        #     # Navigate to market
        #     if fsm.query(Recruit.HOMING, previous = True):
        #         homing(to_drop = True)
        #     else:
        #         homing()

        #     # Sell resource information  
        #     if rb.buffer:
        #         resource = rb.buffer.pop(-1)
        #         print(resource._calldata)
        #         sellHash = w3.sc.functions.updatePatch(*resource._calldata).transact()
        #         txs['sell'] = Transaction(sellHash)
        #         robot.log.info('Selling: %s', resource._desc)

        #     # Transition state  
        #     else:
        #         if txs['sell'].query(3):
        #             txs['sell'] = Transaction(None)
        #             fsm.setState(States.ASSIGN, message = "Sell success")

        #         elif txs['sell'].fail == True:    
        #             txs['sell'] = Transaction(None)
        #             fsm.setState(States.ASSIGN, message = "Sell failed")

        #         elif txs['sell'].hash == None:
        #             fsm.setState(States.ASSIGN, message = "None to sell")