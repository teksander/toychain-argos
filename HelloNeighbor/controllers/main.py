#!/usr/bin/env python3
# This is the main control loop running in each argos robot

# /* Import Packages */
#######################################################################
import sys, os

sys.path += [os.environ['MAINFOLDER'], \
             os.environ['EXPERIMENTFOLDER']+'/controllers', \
             os.environ['EXPERIMENTFOLDER']+'/loop_functions', \
             os.environ['EXPERIMENTFOLDER']
            ]

from movement import RandomWalk
from erandb import ERANDB
from rgbleds import RGBLEDs
from statemachine import FiniteStateMachine, States

from aux import *

from PROJH402.src.Node import Node
from PROJH402.src.consensus.ProofOfAuth import ProofOfAuthority
from PROJH402.src.consensus.ProofOfWork import ProofOfWork
from PROJH402.src.Transaction import Transaction

from control_params import params as cp

# /* Logging Levels for Console and File */
#######################################################################
loglevel = 10
logtofile = False 

# /* Global Variables */
#######################################################################
global startFlag
startFlag = False
# logging.basicConfig(level=logging.INFO)
logging.basicConfig(format='%(message)s', level=logging.ERROR)
global clocks, counters, logs, txs
clocks, counters, logs, txs = dict(), dict(), dict(), dict()

clocks['peering'] = Timer(5)

global robot

####################################################################################################################################################################################
#### INIT STEP #####################################################################################################################################################################
####################################################################################################################################################################################
def init():
    global w3, me, erb, rw, rgb, fsm, tcp
    robotID = str(int(robot.variables.get_id()[2:]) + 1)
    robotIP = '127.0.0.1'
    robot.variables.set_attribute("id", str(robotID))

    # /* Initialize submodules */
    #######################################################################

    # /* Init web3.py */
    w3 = Node(robotID, robotIP, 1233 + int(robotID), ProofOfAuthority())

    # /* Init an instance of peer for this Pi-Puck */
    me = Peer(robotID, robotIP, w3.enode, None)

    # /* Init E-RANDB
    erb = ERANDB(robot, cp['erbDist'], cp['erbtFreq'])

    # /* Init Random-Walk
    rw = RandomWalk(robot, cp['speed'])

    # /* Init LEDs */
    rgb = RGBLEDs(robot)

    # /* Init Finite-State-Machine */
    fsm = FiniteStateMachine(robot, start=States.START)

    global submodules_to_step
    submodules_to_step  = [w3.time, erb]

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

    # Collect current peer enodes
    erb_enodes = {w3.gen_enode(peer.id) for peer in erb.peers}

    # Add peers
    for enode in erb_enodes-set(w3.peers):
        try:
            w3.add_peer(enode)
        except Exception as e:
            raise e
        
    # Remove peers
    for enode in set(w3.peers)-erb_enodes:
        try:
            w3.remove_peer(enode)
        except Exception as e:
            raise e

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
    #### State::ALL
    #########################################################################################################

    # for module in submodules_to_step:
    #     module.step()

    for clock in list(clocks.values())+[w3]:
        clock.time.step()

    if clocks['peering'].query():
        peering()

    #########################################################################################################
    #### State::START
    #########################################################################################################
    # if is_new:
    #     t = Transaction(w3.enode, enode, {"action": "add_k", "input": 1}, 0, timestamp=w3.custom_timer.time())
    #     w3.send_transaction(t)


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

#########################################################################################################################
#### RESET-DESTROY STEPS ################################################################################################
#########################################################################################################################

def reset():
    pass


def destroy():
    w3.destroy_node()

#########################################################################################################################
#########################################################################################################################
#########################################################################################################################
