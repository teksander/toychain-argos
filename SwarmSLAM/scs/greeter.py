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
            self.n           = 0
            self.private     = {}
            self.balances    = {}

            # Init your own state variables
            self.all_hellos  = {}

    def Hello(self, neighbor):

        self.all_hellos.setdefault(neighbor, [])
        self.all_hellos[neighbor] += self.msg.sender

        logger.info(f"Robot {self.msg.sender} greeted {neighbor} !")

