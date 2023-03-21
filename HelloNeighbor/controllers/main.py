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

from PROJH402.src.ProofOfAuth import ProofOfAuthority
from PROJH402.src.Node import Node

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
counters['timestep'] = 0

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
    consensus = ProofOfAuthority()
    w3 = Node(robotID, robotIP, 1233+int(robotID), consensus)

    # /* Init an instance of peer for this Pi-Puck */
    me = Peer(robotID, robotIP, None, None)

    # /* Init E-RANDB
    erb = ERANDB(robot, cp['erbDist'] , cp['erbtFreq'])

    # /* Init Random-Walk
    rw = RandomWalk(robot, cp['speed'])

    # /* Init LEDs */
    rgb = RGBLEDs(robot)

    # /* Init Finite-State-Machine */
    fsm = FiniteStateMachine(robot, start = States.START)

    # # /* Init TCP for enode */
    # tcp = TCP_server(w3.enode, w3.host, 4000+int(me.id), unlocked = True)

    # /* Initialize logmodules*/
    #######################################################################
    log_folder = os.environ['EXPERIMENTFOLDER'] + '/logs/' + me.id + '/'
    os.makedirs(os.path.dirname(log_folder), exist_ok=True) 

    # Monitor logs (recorded to file)
    name =  'monitor.log'
    logging.basicConfig(filename=log_folder+name, filemode='w+', format='[{} %(levelname)s %(name)s %(relativeCreated)d] %(message)s'.format(me.id))
    robot.log = logging.getLogger('main')
    robot.log.setLevel(loglevel)

###########################
######## ROUTINES #########
###########################

def peering():

    for peer in erb.peers:
        if peer not in w3.peers.values():
            w3.add_peer(enode(peer.id))

    temp = copy.copy(w3.peers).values()
    for peer in temp:
        try:
            if peer['id'] not in [str(p.id) for p in erb.peers]:
                w3.remove_peer(peer['enode'])
        except:
            pass

    # Turn on LEDs according to geth Peers
    if   len(w3.peers) == 0: rgb.setLED(['black', 'black', 'black'])
    elif len(w3.peers) == 1: rgb.setLED(['red',   'black', 'black'])
    elif len(w3.peers) == 2: rgb.setLED(['red',   'black', 'red'])
    elif len(w3.peers) >= 3: rgb.setLED(['red',   'red',   'red'])

#########################################################################################################################
#### CONTROL STEP #######################################################################################################
#########################################################################################################################
def controlstep():
    global clocks, counters, startFlag
  
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

            for module in [erb] + list(logs.values()) + list(clocks.values()):
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

def enode(_id):
    return "enode://%s@127.0.0.1:%s" % (_id, 1234+_id-1)

def getEnodes():
    return [peer['enode'] for peer in w3.peers]

def getIps():
    return [peer['ip'] for peer in w3.peers]
