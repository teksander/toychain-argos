#!/usr/bin/env python3
# Experimental parameters used in loop and qt_user functions
# Reqs: parameter dictionary is named "params"

import math
import os

# All environment variables
params = dict()
params['environ'] = os.environ

# Generic parameters; include adaptations of environment variables
params['generic'] = dict()
params['generic']['time_limit'] = float(os.environ["TIMELIMIT"]) * 60
params['generic']['arena_size'] = float(os.environ["ARENADIM"])
params['generic']['num_robots'] = int(os.environ["NUMROBOTS"])
params['generic']['seed']       = 358 # None for randomgen
params['generic']['tps'] = eval(os.environ["TPS"])
params['generic']['num_1'] = eval(os.environ["NUM1"])
params['generic']['num_2'] = eval(os.environ["NUM2"])
params['generic']['density'] = eval(os.environ["DENSITY"])
params['generic']['arena_dim'] = eval(os.environ["ARENADIM"])
params['generic']['rab_range'] = eval(os.environ["RABRANGE"])
params['generic']['block_period'] = eval(os.environ["BLOCKPERIOD"])
params['generic']['max_workers'] = eval(os.environ["MAXWORKERS"])
params['generic']['regen_rate'] = eval(os.environ["REGENRATE"])


# Parameters for marketplace
params['market'] = dict()
params['market']['x'] = 0
params['market']['y'] = 0
params['market']['r'] = 2.5 * 0.073/2 * math.sqrt(params['generic']['num_robots'])

# Parameters for cache
params['cache'] = dict()
params['cache']['x'] = params['market']['x']
params['cache']['y'] = params['market']['y']
params['cache']['r'] = 0.07 + params['market']['r']

params['patches'] = dict()
params['patches']['qualities'] = {'red', 'green' , 'blue', 'yellow'}

params['patches']['distribution'] = 'uniform' 
# params['patches']['distribution'] = 'patchy'
# params['patches']['hotspots']      = [{'x_mu': 0.25 * params['generic']['arena_size'], 
# 									     'y_mu': 0.25 * params['generic']['arena_size'], 
# 									     'x_sg': 0.15 * params['generic']['arena_size'], 
# 									     'y_sg': 0.15 * params['generic']['arena_size']}]
# params['patches']['distribution'] = 'fixed' 

params['patches']['counts'] = {'red': 4, 'green': 3, 'blue': 2, 'yellow': 1}
# params['patches']['x'] = [ 0.25]
# params['patches']['y'] = [ 0.25]

# params['patches']['counts'] = {'red': 0, 'green': 0 , 'blue': 1, 'yellow': 1}
# params['patches']['x'] = [ 0.15, 0.30]
# params['patches']['y'] = [ 0.30, 0.15]

params['patches']['respawn']   = True
params['patches']['known']     = False
params['patches']['radius']    = 0.25
params['patches']['qtty_min']  = 30
params['patches']['qtty_max']  = 30
params['patches']['dist_min']  = 1 * params['cache']['r'] 
params['patches']['dist_max']  = 5 * params['cache']['r']

params['patches']['qtty_min']  = {'red': 5, 'green': 15, 'blue': 25, 'yellow': 35}
params['patches']['qtty_max']  = {'red': 5, 'green': 15, 'blue': 25, 'yellow': 35}

# params['patches']['radii']  = {k: params['patches']['radius'] for k in params['patches']['qualities']}
params['patches']['radii']  = {k: round(math.sqrt(params['patches']['qtty_min'][k])/20,2) for k in params['patches']['qualities']}

# Parameters for resource economy
params['patches']['utility']     = {'red': 1, 'green':  1, 'blue': 200, 'yellow': 300}
params['patches']['forage_rate'] = {'red': 1, 'green':  1, 'blue': 1, 'yellow': 1}
params['patches']['regen_rate']  = {'red': 50, 'green': 50, 'blue': 50, 'yellow': 50}

params['patches']['dec_returns'] = dict()
params['patches']['dec_returns']['func']   = 'linear'                       # constant, linear or logarithmic decreasing returns
params['patches']['dec_returns']['thresh'] = 0 #params['patches']['qtty_max']  # qqty of resource before dec returns starts
params['patches']['dec_returns']['slope']  = 1

params['patches']['dec_returns']['func_robot']  = 'linear'                  # seconds each resource is slower than previous
params['patches']['dec_returns']['slope_robot'] = 3
params['patches']['forage_together'] = True

# params['patches']['dec_returns']['func_robot']  = 'exp'                  # seconds each resource is slower than previous
# params['patches']['dec_returns']['slope_robot'] = 3

# params['patches']['area_percent'] = 0.005 * (10/generic_params['num_robots'])
# params['patches']['radius']    = params['generic']['arena_size']  * math.sqrt(resource_params['area_percent']/math.pi) 

# params['patches']['radius']    = params['generic']['arena_size']  * math.sqrt(resource_params['area_percent']/math.pi) 
# params['patches']['abundancy']    = 0.03
# params['patches']['frequency'] = {'red': 0.25, 'green': 0.25 , 'blue': 0.25, 'yellow': 0.25}

# Parameters for the economy
params['economy'] = dict()
params['economy']['consum_rate'] = {'red': 1, 'green':  1, 'blue': 1, 'yellow': 1}  # number of resources consumed at the market per block
params['economy']['DEMAND_A'] = 1
params['economy']['DEMAND_B'] = 1
params['economy']['efficiency_distribution'] = 'linear' 
params['economy']['efficiency_best'] = 1  # amps/second of best robot
params['economy']['efficiency_step'] = 0  # amps/second increase per robot ID

# Initialize the files which store QT_draw information 
params['files'] = dict()
params['files']['patches'] = 'loop_functions/patches.txt'
