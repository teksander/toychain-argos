#!/usr/bin/env python3
import random, math
import os

params = dict()
params['scout_speed']    = 18
params['recruit_speed']  = 18
params['buy_duration']   = 30
params['explore_mu']     = float(os.environ["ARENADIM"])/params['scout_speed']*100
params['explore_sg']     = 2


params['gsFreq']     = 20
params['erbtFreq']   = 10
params['erbDist']    = 175

# Maximum quantity of resource a robot can transport
params['max_Q']       = 10

params['firm'] = dict()
params['firm']['entry_Kp']   = 8
params['firm']['entry_Ki']   = 0
params['firm']['entry_w']    = 10
params['firm']['entry_f']    = 5 # how often (in blocks) the robots decide to enter/exit

