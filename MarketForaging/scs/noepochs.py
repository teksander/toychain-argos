from copy import copy
import sys, os

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
            self.market      = {qlty:[0,0] for qlty in lp['patches']['qualities']}

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
            'id': len(self.patches),
            # 'maxw': int(os.environ['MAXWORKERS']),
            'totw': 0,      
            # 'last_assign': -1,
            'epoch': self.epoch(0,0,[],[],[],1),
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

        for patch in self.patches:
            if patch['totw'] < int(lp['environ']['STARTWORKERS']):
                self.joinPatch(patch['id'])
                print(f"Assigned robot {self.msg.sender} to {patch['qlty']}")
                break

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

            print(f"The old resource price:{self.patches[i]['epoch']['price']*util}")
            print(f"{lp['economy']['consum_rate'][qlty]*(self.block.height - self.market[qlty][1])} resources were consumed")
            print(f"{Q} resources were dropped")

            # Update patch information
            self.updatePatch(x, y, qtty, util, qlty, json)
           
            # Update the market quantity
            self.market[qlty][0] += Q
            self.market[qlty][0] -= lp['economy']['consum_rate'][qlty]*(self.block.height - self.market[qlty][1])
            self.market[qlty][1]  = self.block.height
            self.market[qlty][0]  = max(0, self.market[qlty][0])

            print(f"market qtty: {self.market[qlty][0]}")
            # Update the patch epoch
            self.patches[i]['epoch']['Q'].append(Q)
            self.patches[i]['epoch']['TC'].append(TC)
            self.patches[i]['epoch']['ATC'].append(round(TC/Q,1))
            self.patches[i]['epoch']['robots'].append(self.msg.sender)

            logger.info(f"Drop #{len(self.patches[i]['epoch']['Q'])}")

            self.patches[i]['epoch']['TQ']     = sum(self.patches[i]['epoch']['Q'])
            self.patches[i]['epoch']['AATC']   = round(sum(self.patches[i]['epoch']['ATC'])/len(self.patches[i]['epoch']['ATC']),1)
            self.patches[i]['epoch']['price']  = self.linearDemand(self.market[qlty][0], self.patches[i])
            self.patches[i]['epoch']['AP']     = self.patches[i]['util']*self.patches[i]['epoch']['price'] - self.patches[i]['epoch']['AATC']
                
            # Pay the robot
            self.balances[self.msg.sender] += Q*util*self.patches[i]['epoch']['price']

            # Fuel purchase
            self.balances[self.msg.sender] -= TC

            print(f"The new resource price:{self.patches[i]['epoch']['price']*util}")

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
    
    def linearDemand(self, Q, patch = None):

        demandA = lp['economy']['DEMAND_A']
        demandB = lp['economy']['DEMAND_B']

        Price = demandB - demandA*(Q/patch['util'])

        return max(Price, 0)
