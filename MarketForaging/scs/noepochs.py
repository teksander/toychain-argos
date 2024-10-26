from copy import copy
import sys, os
import math
from uuid import uuid4

from toychain.src.utils.helpers import compute_hash, transaction_to_dict
from toychain.src.State import StateMixin

import logging
logger = logging.getLogger('sc')

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.actusensors.groundsensor import Resource
from loop_functions.params import params as lp

class Contract(StateMixin):

    def __init__(self, state_variables = None):

        if state_variables is not None:
            for var, value in state_variables.items(): setattr(self, var, value)     

        else:
            # Init the basic state variables
            self.private     = {}
            self.n           = 0
            self.balances    = {}

            # Init your own state variables
            self.patches     = []
            self.robots      = {}
            # self.market      = {qlty:[0,0] for qlty in lp['patches']['qualities']}

            # Bug warning: if the initial patches change, the previous patches are kept.
            if lp['patches']['known']:
                with open(lp['files']['patches'], 'r') as f:
                    for line in f:
                        self.updatePatch(*Resource(line)._calldata)

    def robot(self):
        return {'task': -1}
    
    def patch(self, x, y, qtty, util, qlty, json):
        return {
            'x': x,
            'y': y,
            'qtty': qtty,
            'util': util,
            'qlty': qlty,
            'json': json,
            'id': str(self.n),
            'votes': set(),
            'votes_remove': set(),
            'status': 'pending' if eval(lp['environ']['ORACLE']) else 'verified',
            'team': set(),
            'totw': 0,      
            'maxw': math.ceil(qtty/10),
            'when_remove': 0
            # 'last_assign': -1,
            # 'epoch': self.epoch(0,0,[],[],[],1)
            # 'robots': [],
            # 'allepochs': []
        }
    
    def epoch(self, number, start, Q, TC, ATC, price):
        return {
            'number': number,
            'start': start,
            'Q': Q,
            'TC': TC,
            'ATC': ATC,
            'price': price,
            'robots': [],
            'TQ': 0,
            'AATC': 0,
            'AP': 0
        }

    def register(self, task = -1):

        logger.info(f"Register #{self.msg.sender}")

        if self.msg.sender not in self.robots:
            self.robots[self.msg.sender] = self.robot()

    def joinPatch(self, _id):

        i, patch = self.findById(_id)

        if self.robots[self.msg.sender]['task'] == -1 and patch["totw"] < patch["maxw"] and patch["status"] == 'verified':

            self.robots[self.msg.sender]['task'] = patch['id']
            self.patches[i]["totw"] += 1
            self.patches[i]["team"].add(self.msg.sender)
            logger.info(f"#{self.msg.sender} join {patch['qlty']}")

    # def leavePatch(self):

    #     _id = self.robots[self.msg.sender]['task']

    #     i, patch = self.findById(_id)

    #     self.robots[self.msg.sender]['task'] = -1
    #     if i < 9999:
    #         self.patches[i]["totw"] -= 1
    
    def updatePatch(self, x, y, qtty, util, qlty, json, remove = False):

        i, _ = self.findByPos(x, y)

        if i < 9999:
            self.patches[i]["qtty"] = qtty
            self.patches[i]["util"] = util
            self.patches[i]["qlty"] = qlty
            self.patches[i]["json"] = json

            self.patches[i]["votes"].add(self.msg.sender)

            if remove:
                self.patches[i]["votes_remove"].add(self.msg.sender)

            logger.info(f"Update existing patch @ {x},{y}")

            if len(self.patches[i]["votes"]) >= math.ceil((2/3)*len(self.robots)):
                self.patches[i]["status"] = 'verified'

            if len(self.patches[i]["votes_remove"]) >= math.ceil((2/3)*self.patches[i]['maxw']):

                for robot in self.patches[i]["team"]:
                    self.robots[robot]['task'] = -1

                self.patches[i]["status"] = 'removed'
                self.patches[i]["when_remove"] = self.block.height+5
                self.patches[i]["team"].clear()
                self.patches[i]["totw"] = 0
                
        else:
            new_patch = self.patch(x, y, qtty, util, qlty, json)
            new_patch["votes"].add(self.msg.sender)
            self.patches.append(new_patch)

            logger.info(f"Added new patch @ {new_patch['id']}:")
            logger.info(f"{json}")

    def dropResource(self):

        for i, patch in enumerate(self.patches):
            if patch["status"] == 'removed' and self.block.height >= patch["when_remove"]:
                del self.patches[i]
                break

        # i, _ = self.findByPos(x, y)

        # if i < 9999:

        #     print(f"The old resource price:{self.patches[i]['epoch']['price']*util}")
        #     print(f"{lp['economy']['consum_rate'][qlty]*(self.block.height - self.market[qlty][1])} resources were consumed")
        #     print(f"{Q} resources were dropped")

        #     # Update patch information
        #     self.updatePatch(x, y, qtty, util, qlty, json)
           
        #     # Update the market quantity
        #     self.market[qlty][0] += Q
        #     self.market[qlty][0] -= lp['economy']['consum_rate'][qlty]*(self.block.height - self.market[qlty][1])
        #     self.market[qlty][1]  = self.block.height
        #     self.market[qlty][0]  = max(0, self.market[qlty][0])

        #     print(f"market qtty: {self.market[qlty][0]}")
        #     # Update the patch epoch
        #     self.patches[i]['epoch']['Q'].append(Q)
        #     self.patches[i]['epoch']['TC'].append(TC)
        #     self.patches[i]['epoch']['ATC'].append(round(TC/Q,1))
        #     self.patches[i]['epoch']['robots'].append(self.msg.sender)

        #     logger.info(f"Drop #{len(self.patches[i]['epoch']['Q'])}")

        #     self.patches[i]['epoch']['TQ']     = sum(self.patches[i]['epoch']['Q'])
        #     self.patches[i]['epoch']['AATC']   = round(sum(self.patches[i]['epoch']['ATC'])/len(self.patches[i]['epoch']['ATC']),1)
        #     self.patches[i]['epoch']['price']  = self.linearDemand(self.market[qlty][0], self.patches[i])
        #     self.patches[i]['epoch']['AP']     = self.patches[i]['util']*self.patches[i]['epoch']['price'] - self.patches[i]['epoch']['AATC']
                
        #     # Pay the robot
        #     self.balances[self.msg.sender] += Q*util*self.patches[i]['epoch']['price']

        #     # Fuel purchase
        #     self.balances[self.msg.sender] -= TC

        #     print(f"The new resource price:{self.patches[i]['epoch']['price']*util}")

        # else:
        #     print(f'Patch {x},{y} not found')

    def getPatches(self):
       return self.patches
    
    def getMyPatch(self, sender):
        if sender not in self.robots:
            return None
        
        if self.robots[sender]['task'] == -1:
            return None
        
        i, patch = self.findById(self.robots[sender]['task'])
        return patch
    
    def findByPos(self, _x, _y):
        for i in range(len(self.patches)):
            if _x == self.patches[i]['x'] and _y == self.patches[i]['y']:
                return i, self.patches[i]
        return 9999, None

    def findById(self, _id):
        for i in range(len(self.patches)):
            if _id == self.patches[i]['id']:
                return i, self.patches[i]
        return 9999, None


    def getEpoch(self, x, y):

        _, patch = self.findByPos(x, y)

        return patch['epoch'], patch 
    
    def linearDemand(self, Q, patch = None):

        demandA = lp['economy']['DEMAND_A']
        demandB = lp['economy']['DEMAND_B']

        Price = demandB - demandA*(Q/patch['util'])

        return max(Price, 0)
