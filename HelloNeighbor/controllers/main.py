#!/usr/bin/env python3
# This is the main control loop running in each argos robot

# /* Import Packages */
#######################################################################
import random, math, copy
import time, sys, os
import logging

sys.path += [os.environ['MAINFOLDER'], \
             os.environ['EXPERIMENTFOLDER']+'/controllers', \
             os.environ['EXPERIMENTFOLDER']+'/loop_functions', \
             os.environ['EXPERIMENTFOLDER']
            ]

from movement import RandomWalk
from erandb import ERANDB
from rgbleds import RGBLEDs
from console import init_web3, Transaction
from statemachine import FiniteStateMachine, States

from aux import *

from PROJH402.src.Block import Block, create_block_from_list, block_to_list
from PROJH402.src.Node import Node
from PROJH402.src.constants import LOCALHOST, MINING_DIFFICULTY
from PROJH402.src.utils import compute_hash, verify_chain

from loop_params import params as lp
from control_params import params as cp

# /* Logging Levels for Console and File */
#######################################################################
loglevel = 10
logtofile = False 

# /* Global Variables */
#######################################################################
global startFlag
startFlag = False

global clocks, counters, logs, txs
clocks, counters, logs, txs = dict(), dict(), dict(), dict()

clocks['peering']  = Timer(0.5)

####################################################################################################################################################################################
#### INIT STEP #####################################################################################################################################################################
####################################################################################################################################################################################

def init():
    global w3, me, erb, rw, rgb, fsm, tcp
    robotID = str(int(robot.variables.get_id()[2:])+1)
    robotIP = '127.0.0.1'
    robot.variables.set_attribute("id", str(robotID))

    # /* Initialize submodules */

    #######################################################################
    # /* Init web3.py */
    w3 = Node(robotID, robotIP, 1233+int(robotID), MINING_DIFFICULTY)

    # /* Init an instance of peer for this Pi-Puck */
    me = Peer(robotID, robotIP, w3.enode, None)

    # /* Init E-RANDB
    erb = ERANDB(robot, cp['erbDist'] , cp['erbtFreq'])

    # /* Init Random-Walk
    rw = RandomWalk(robot, cp['speed'])

    # /* Init LEDs */
    rgb = RGBLEDs(robot)

    # /* Init Finite-State-Machine */
    fsm = FiniteStateMachine(robot, start = States.START)

    # /* Init TCP for enode */
    tcp = TCP_server(w3.enode, w3.host, 4000+int(me.id), unlocked = True)

    # /* Initialize logmodules*/
    #######################################################################
    log_folder = os.environ['EXPERIMENTFOLDER'] + '/logs/' + me.id + '/'
    os.makedirs(os.path.dirname(log_folder), exist_ok=True) 

    # Monitor logs (recorded to file)
    name =  'monitor.log'
    logging.basicConfig(filename=log_folder+name, filemode='w+', format='[{} %(levelname)s %(name)s %(relativeCreated)d] %(message)s'.format(me.id))
    robot.log = logging.getLogger('main')
    robot.log.setLevel(loglevel)

#########################################################################################################################
#### CONTROL STEP #######################################################################################################
#########################################################################################################################

def controlstep():
    global clocks, counters, startFlag

    ###########################
    ######## ROUTINES #########
    ###########################
    
    def peering():

        for peer in erb.peers:

            if peer.id not in [x['id'] for x in w3.peers.values()]:
                peer.enode = tcp.request('127.0.0.1', 4000+int(peer.id))
                w3.add_peer(peer.enode)

        # temp = copy.copy(w3.peers.values())
        # for peer in temp:
        #     if peer['id'] not in [peer.id for peer in erb.peers]:
        #         w3.remove_peer(peer['enode'])

         # Turn on LEDs according to geth Peers
        if len(w3.peers) == 0: 
            rgb.setLED(['black','black','black'])
        elif len(w3.peers) == 1:
            rgb.setLED(['red', 'black', 'black'])
        elif len(w3.peers) == 2:
            rgb.setLED(['red', 'black', 'red'])
        elif len(w3.peers) > 2:
            rgb.setLED(['red','red','red'])
  
    ##############################
    ##### STATE-MACHINE STEP #####
    ##############################

    #########################################################################################################
    #### State::START
    #########################################################################################################

    if fsm.query(States.START):
        
        if not startFlag:

            robot.log.info('--//-- Starting Experiment --//--')
            startFlag = True 

            for module in [erb, tcp] + list(logs.values()) + list(clocks.values()):
                module.start()

            w3.start_tcp()
            w3.start_mining()

        fsm.setState(States.WALK)

    #########################################################################################################
    #### State::WALK  
    ######################################################################################################### 

    elif fsm.query(States.WALK):

        erb.step()

        rw.step()

        # Perform the blockchain peering
        if clocks['peering'].query():
            peering()


#########################################################################################################################
#### RESET-DESTROY STEPS ################################################################################################
#########################################################################################################################

def reset():
    pass

def destroy():
    # w3.destroy_node()
    pass

#########################################################################################################################
#########################################################################################################################
#########################################################################################################################

def getEnodes():
    return [peer['enode'] for peer in w3.peers]

def getIps():
    return [peer['ip'] for peer in w3.peers]






















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