from copy import copy
import sys, os
from json import loads
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

class Market(StateMixin):

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
            # self.trips       = []
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
            'profit': 0,
            'all_profits': [],
            'last_drop': 0,
            'all_drops': [],
            'assignments': 0,
            'trips': 0,  
        }
    
    # def trip(self, Q, TC, TP):
    #     return {
    #         'Q': Q,
    #         'TC': TC,
    #         'TP': TP,
    #         'block': self.block.number,
    #         'robot': self.msg.sender,
    #         'timestamp': self.msg.timestamp,
    #     }

    def register(self, task = -1):

        if self.msg.sender not in self.robots:
            self.robots[self.msg.sender] = self.robot()

    def planner(self):
        robot_id = self.msg.sender
        now = self.msg.timestamp

        ready_candidates = []
        first_trial_candidates = []

        for patch in self.patches:
            # Unpack info
            assignments = patch.get('assignments', 0)
            trips = patch.get('trips', 0)

            # Ensure fields are initialized
            patch['assignments'] = assignments
            patch['trips'] = trips

            # Determine if more robots can be assigned
            if assignments == 0:
                first_trial_candidates.append(patch)

            elif trips >= assignments:
                if patch['profit'] > 100:
                    ready_candidates.append(patch)

        if first_trial_candidates:
            selected_patch = sorted(first_trial_candidates, key=lambda p: p['last_drop'])[0]

        elif ready_candidates:
            selected_patch = sorted(ready_candidates, key=lambda p: (-p['profit'], p['last_drop']))[0]

        else:
            return -1  

        # Assign this robot
        selected_patch['assignments'] += 1
        selected_patch['trips'] -= 1
        self.robots[self.msg.sender]['task'] = selected_patch['id']

    # def joinPatch(self, i):

    #     patch = self.patches[i]
    #     self.robots[self.msg.sender]['task'] = patch['id']
    #     patch["totw"] += 1

    #     logger.info(f"#{self.msg.sender} join {patch['qlty']}")

    # def leavePatch(self):

    #     i = self.robots[self.msg.sender]['task']
    #     self.robots[self.msg.sender]['task'] = -1
    #     self.patches[i]["totw"] -= 1
    
    def updatePatch(self, x, y, qtty, util, qlty, json):

        i, _ = self.findByPos(x, y)

        if i < 9999:
            self.patches[i]["qtty"] = qtty
            self.patches[i]["util"] = util
            self.patches[i]["qlty"] = qlty
            self.patches[i]["json"] = json

            # logger.info(f"Update existing patch @ {x},{y}")

        else:
            new_patch = self.patch(x, y, qtty, util, qlty, json)
            self.patches.append(new_patch)
            # self.trips.append([])

            logger.info(f"Added new patch @ {json}, {new_patch['id']}")

    def dropResource(self, x, y, qtty, util, qlty, json, Q, TC, AP):
        
        i, _ = self.findByPos(x, y)

        if i < 9999:

            # Update patch information
            self.updatePatch(x, y, qtty, util, qlty, json)

            # # Update the patch trips
            # self.trips[i].append(self.trip(Q, TC, Q*AP))

            # Update patch profit
            alpha = 0.4
            profit = Q*AP
            tau = 500  # higher is slower adaptation

            if not self.patches[i]['all_profits']:
                self.patches[i]['profit'] = profit

            else:
                # dt = self.msg.timestamp - self.patches[i]['last_drop']
                # alpha_t = 1 - math.exp(-dt / tau)
                # self.patches[i]['profit'] = alpha_t * Q_AP + (1 - alpha_t) * self.patches[i]['profit']
                self.patches[i]['profit'] = alpha*profit + (1-alpha) * self.patches[i]['profit'] 

            # self.patches[i]['profit'] += Q*AP # cumulative
            self.patches[i]['profit'] = Q*AP # last

            self.patches[i]['all_profits'].append(profit)
            self.patches[i]['all_drops'].append(self.msg.timestamp)
            self.patches[i]['last_drop'] = self.msg.timestamp
            # self.patches[i]['profit'] = sum(self.patches[i]['all_profits'][-self.patches[i]['assignments']:])/self.patches[i]['assignments']

            self.patches[i]['trips']    += 1
            self.patches[i]['assignments'] -= 1
            self.robots[self.msg.sender]['task'] = -1

            # Pay the robot
            self.balances[self.msg.sender] += Q*self.patches[i]['util']

            # Fuel purchase
            self.balances[self.msg.sender] -= TC

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

    # def getEpoch(self, x, y):

    #     _, patch = self.findByPos(x, y)

    #     return patch['epoch'], patch 
    