#!/usr/bin/env python3
import random, math
import os

params = dict()


params['A'] = dict()
params['B'] = dict()
params['C'] = dict()
params['D'] = dict()

params['A']['speed'] = 12
# params['B']['speed'] = 12
# params['C']['speed'] = 6
# params['D']['speed'] = 6

params['A']['range'] = 0.5
# params['B']['range'] = 0.5
# params['C']['range'] = 0.5
# params['D']['range'] = float(os.environ["RABRANGE_D"])

params['A']['error'] = 0.005
# params['B']['error'] = 0.025
# params['C']['error'] = 0.01
# params['D']['error'] = 0.01

params['A']['max_Q'] = 10
# params['B']['max_Q'] = 10
# params['C']['max_Q'] = 25
# params['D']['max_Q'] = 25


params['speed']          = 18
params['scout_speed']    = 18
params['recruit_speed']  = 18

params['scout_speed']    = 18
params['recruit_speed']  = 18
params['buy_duration']   = 30
params['explore_mu']     = float(os.environ["ARENADIM"])/params['scout_speed']*160
params['explore_sg']     = 5

params['gsFreq']     = 20
params['erbtFreq']   = 10
params['erbDist']    = 0.1

# Maximum quantity of resource a robot can transport
params['max_Q']       = 10

params['firm'] = dict()
params['firm']['entry_K']   = 5
params['firm']['entry_Kp']   = 5
params['firm']['entry_Ki']   = 0
params['firm']['entry_w']    = 10
params['firm']['entry_f']    = 5 # how often (in blocks) the robots decide to enter/exit

