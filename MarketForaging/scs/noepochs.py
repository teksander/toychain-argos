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

            # self.proposals   = []
            # self.verified    = []
            # self.depleted    = []
            
            self.robots      = {}

            self.credits     = {
                                'explore': dict(),
                                'verify':  dict(),
                                'forage':  dict()
                                }

    def robot(self):
        return {'task': -1}
    
    def patch(self, x, y, json):
        return {
            'x': x,
            'y': y,
            'json': json,
            'id': str(self.n),
            'explorer': None,
            'verifiers': [],
            'foragers':  [],
            'votes': set(),
            'votes_remove': set(),
            'all_x': [],
            'all_y': [],
            'status': 'pending' if eval(lp['environ']['ORACLE']) else 'verified',
            'when_remove': 0
            # 'last_assign': -1,
            # 'epoch': self.epoch(0,0,[],[],[],1)
            # 'robots': [],
            # 'allepochs': []
        }
    
    def register(self, task = -1):

        logger.info(f"Register #{self.msg.sender}")

        if self.msg.sender not in self.robots:
            self.robots[self.msg.sender] = self.robot()
            self.credits['explore'][self.msg.sender] = 0
            self.credits['verify'][self.msg.sender]  = 0
            self.credits['forage'][self.msg.sender]  = 0

    def propose(self, x, y, json):

        if self.msg.sender not in self.robots:
            self.register()

        proposal = self.patch(x, y, json)

        proposal["explorer"] = self.msg.sender

        self.patches.append(proposal)

        logger.info(f"New proposal @ {proposal['x']}, {proposal['y']}:")

        self.cleanPatches()

    def verify(self, x, y, json, remove = False):

        if self.msg.sender not in self.robots:
            self.register()
        
        i, _ = self.findByPos(json['x'], json['y'])

        if i == 9999:
            logger.info("Proposal not found")

        elif self.msg.sender not in self.patches[i]["verifiers"]:

            self.patches[i]["verifiers"].append(self.msg.sender)

            if remove:
                logger.info(f"Voted remove @ {json['x']},{json['y']} with ({x},{y})")
                self.patches[i]["votes_remove"].add(self.msg.sender)

            else:
                logger.info(f"Update patch @ {json['x']},{json['y']} with ({x},{y})")
                self.patches[i]["json"] = json
                self.patches[i]["all_x"].append(x)
                self.patches[i]["all_y"].append(y)
                self.patches[i]["x"] = round(sum(self.patches[i]["all_x"])/len(self.patches[i]["all_x"]), 2)
                self.patches[i]["y"] = round(sum(self.patches[i]["all_y"])/len(self.patches[i]["all_y"]), 2)
                self.patches[i]["votes"].add(self.msg.sender)

            
            if len(self.patches[i]["votes"]) >= 5:
                self.patches[i]["status"] = 'verified'

            if len(self.patches[i]["votes_remove"]) >= 5:
                self.patches[i]["status"] = 'removed'
                self.patches[i]["when_remove"] = self.block.height+5

            self.credits['explore'][self.patches[i]["explorer"]] += 1
            self.credits['verify'][self.msg.sender] += 1

        self.cleanPatches()
                
      
    def forage(self, x ,y, json):

        if self.msg.sender not in self.robots:
            self.register()

        i, _ = self.findByPos(json['x'], json['y'])

        if i < 9999:
            for verifier in self.patches[i]["votes"]:
                self.credits['verify'][verifier] += 1
                
            self.credits['forage'][self.msg.sender] += 1

        self.cleanPatches()

    def cleanPatches(self):
        for i, patch in enumerate(self.patches):
            if patch["status"] == 'removed' and self.block.height >= patch["when_remove"]:
                del self.patches[i]
                break

    def getPatches(self):
       return self.patches
    
    def findByPos(self, _x, _y):
        for i in range(len(self.patches)):
            if _x ==  self.patches[i]['json']['x'] and _y == self.patches[i]['json']['y']:
                return i, self.patches[i]
        return 9999, None

    def findById(self, _id):
        for i in range(len(self.patches)):
            if _id == self.patches[i]['id']:
                return i, self.patches[i]
        return 9999, None



    # def joinPatch(self, _id):

    #     i, patch = self.findById(_id)

    #     if self.robots[self.msg.sender]['task'] == -1 and patch["totw"] < patch["maxw"] and patch["status"] == 'verified':

    #         self.robots[self.msg.sender]['task'] = patch['id']
    #         self.patches[i]["totw"] += 1
    #         self.patches[i]["team"].add(self.msg.sender)
    #         logger.info(f"#{self.msg.sender} join {patch['json']}")

    # def leavePatch(self):

    #     _id = self.robots[self.msg.sender]['task']

    #     i, patch = self.findById(_id)

    #     self.robots[self.msg.sender]['task'] = -1
    #     if i < 9999:
    #         self.patches[i]["totw"] -= 1
    
    # def getMyPatch(self, sender):
    #     if sender not in self.robots:
    #         return None
        
    #     if self.robots[sender]['task'] == -1:
    #         return None
        
    #     i, patch = self.findById(self.robots[sender]['task'])
    #     return patch