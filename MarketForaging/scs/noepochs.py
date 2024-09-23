from copy import copy
import sys, os

from toychain.src.utils.helpers import compute_hash, transaction_to_dict
from toychain.src.State import StateMixin

import logging
logger = logging.getLogger('sc')

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
            'id': len(self.patches),
            # 'maxw': int(os.environ['MAXWORKERS']),
            'totw': 0,      
            # 'last_assign': -1,
            'epoch': self.epoch(0,0,[],[],[],self.linearDemand(0)),
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

        if task != -1:
            self.joinPatch(task)

    def joinPatch(self, i):

        patch = self.patches[i]
        self.robots[self.msg.sender]['task'] = patch['id']
        patch["totw"] += 1

        logger.info(f"#{self.msg.sender} join {patch['qlty']}")

    def leavePatch(self):

        i = self.robots[self.msg.sender]['task']
        self.robots[self.msg.sender]['task'] = -1
        self.patches[i]["totw"] -= 1
    
    def updatePatch(self, x, y, qtty, util, qlty, json):

        i, _ = self.findByPos(x, y)

        if i < 9999:
            self.patches[i]["qtty"] = qtty
            self.patches[i]["util"] = util
            self.patches[i]["qlty"] = qlty
            self.patches[i]["json"] = json

            logger.info(f"Update existing patch @ {x},{y}")

        else:
            new_patch = self.patch(x, y, qtty, util, qlty, json)
            self.patches.append(new_patch)

            logger.info(f"Added new patch @ {json}, {new_patch['id']}")

    def dropResource(self, x, y, qtty, util, qlty, json, Q, TC):
        
        i, _ = self.findByPos(x, y)

        if i < 9999:

            # Update patch information
            self.updatePatch(x, y, qtty, util, qlty, json)

            # Pay the robot
            self.balances[self.msg.sender] += Q*util*self.patches[i]['epoch']['price']

            # Fuel purchase
            self.balances[self.msg.sender] -= TC
            
            self.patches[i]['epoch']['Q'].append(Q)
            self.patches[i]['epoch']['TC'].append(TC)
            self.patches[i]['epoch']['ATC'].append(TC/Q)
            self.patches[i]['epoch']['robots'].append(self.msg.sender)

            logger.info(f"Drop #{len(self.patches[i]['epoch']['Q'])}")

            self.patches[i]['epoch']['TQ'] = sum(self.patches[i]['epoch']['Q'])
            self.patches[i]['epoch']['AATC'] = sum(self.patches[i]['epoch']['ATC'])/len(self.patches[i]['epoch']['ATC'])
            self.patches[i]['epoch']['AP']   = self.patches[i]['util'] * self.patches[i]['epoch']['price'] - self.patches[i]['epoch']['AATC']
            self.patches[i]['epoch']['price']  = self.linearDemand(self.patches[i]['epoch']['TQ'])
                
        else:
            print(f'Patch {x},{y} not found')

    def getPatches(self):
       return self.patches
    
    def getMyPatch(self, id):
        if id not in self.robots:
            return None
        
        if self.robots[id]['task'] == -1:
            return None
        
        return self.patches[self.robots[id]['task']]
    
    def findByPos(self, _x, _y):
        for i in range(len(self.patches)):
            if _x == self.patches[i]['x'] and _y == self.patches[i]['y']:
                return i, self.patches[i]
        return 9999, None

    def getEpoch(self, x, y):

        _, patch = self.findByPos(x, y)

        return patch['epoch'], patch 
    
    def linearDemand(self, Q):
        P = 0
        demandA = 0 
        demandB = 1
        
        if demandB > demandA * Q:
            P = demandB - demandA * Q
        return P