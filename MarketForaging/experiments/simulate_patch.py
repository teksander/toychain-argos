#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random, math
import sys, os

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.utils import Timer
from controllers.params import params as cp
from loop_functions.params import params as lp

from controllers.actusensors.groundsensor import Resource

# /* Global Variables */
#######################################################################

TPS = 10

# Initialize timers/accumulators/logs:
global clocks, accums, logs, other
clocks, accums, logs, other = dict(), dict(), dict(), dict()

clocks['regen']      = dict()
clocks['travel']     = dict()
clocks['forage']     = dict()
other['foragers']    = dict()

global allrobots, allpatches, allresources
allrobots, allpatches, allresources = [], [], []

global resource_counter
resource_counter = {'red': 0, 'green': 0 , 'blue': 0, 'yellow': 0}

class ParameterStore:
    def __init__(self):
        self._params = {}

    def get(self, name, default=None):
        return self._params.get(name, default)

    def set(self, name, value):
        self._params[name] = value

class Robot:
    """
    Minimal robot object with a *param* field that supports
        • robot.param.get(...)
        • robot.param.set(...)
    """
    _id_counter = 0                   # auto‑incremented ID for convenience

    def __init__(self):
        Robot._id_counter += 1
        self.id: int = Robot._id_counter
        self.param  = ParameterStore()

def generate_resource(n = 1, qualities = None, max_attempts = 500):

    for i in range(n):
        
        # Generate quantity of resource and quality
        quality = qualities[i]
        quantity = random.randint(lp['patches']['qtty_min'][quality], lp['patches']['qtty_max'][quality])
        x = y = radius = 0

        # Append new resource to the global list of resources
        allresources.append(Resource({'x':x, 'y':y, 'radius':radius, 'quantity':quantity, 'quality':quality, 'utility':lp['patches']['utility'][quality]}))
        allresources[-1].id = len(allresources)-1
        allresources[-1].all_profits   = []
        allresources[-1].all_drops     = []
        allresources[-1].drop_counter  = 0
        allresources[-1].last_drop     = 0

        clocks['regen'][allresources[-1]] = Timer(lp['patches']['regen_rate'][allresources[-1].quality]*TPS)
        other['foragers'][allresources[-1]] = set()

def init():

    # Init resource patches
    total_count = 0
    qualities   = []
    for quality, count in lp['patches']['counts'].items():
        total_count += count
        qualities   += count*[quality]

    generate_resource(total_count, qualities = qualities)   
    n_resources = len(allresources)

    # Init robots
    for i in range(n):
        robot = Robot()
        robot.param.set("last_col", 0)
        robot.param.set("last_dec", 0)
        robot.param.set("start", 0)
        robot.param.set("quantity", 0)
        robot.param.set("foraging", False)  
        robot.param.set("at", 0)
        robot.param.set("ATC", 0)
        robot.param.set("AVC", 0)
        robot.param.set("profit", 0)
        robot.param.set("total_profit", 0)
        robot.param.set("first_col", 0)
        robot.param.set("VC", 0)
        clocks['travel'][robot] = Timer()
        allrobots.append(robot)

VC_FATOR = 0.85
P_FATOR  = 0.85
def long_run_decision(robot, allresources):

    # Returns the patch index for the next forage trip. -1 means iddle
    satisfied = True
    decision  = robot.param.get("at")
      
    if robot.param.get("AVC") > VC_FATOR*utility and robot.param.get("ATC") > utility:
        satisfied = False
    
    if not satisfied:
        decision = -1

    if robot.param.get("at") == -1:
        for res in allresources:
            if res.all_profits[-1] > 0:
                decision = res.id
                break

    return decision

def pre_step():
    global resource_counter

    for clock in clocks['forage'].values():
        if isinstance(clock, Timer): clock.time.step()

    for clock in clocks['regen'].values():
        if isinstance(clock, Timer): clock.time.step()

    for clock in clocks['travel'].values():
        if isinstance(clock, Timer): clock.time.step()


    # Tasks to perform for each robot
    for robot in allrobots:

        # Short-run decision
        if robot.param.get("foraging") and robot.param.get("at") != -1:
            res = allresources[robot.param.get("at")]

            # Stop foraging condition
            if res.utility <= step-robot.param.get("last_col") or robot.param.get("quantity") >= cp['max_Q']:

                FC = travel_cost + random.randint(-travel_var, travel_var)
                clocks['travel'][robot].set(FC)

                # Drop collected resources
                Q = robot.param.get("quantity")
                resource_counter[res.quality] += Q

                VC = step-robot.param.get("first_col")
                TC = VC+FC
                PROFIT = Q*res.utility - TC

                robot.param.set("VC", VC)
                if Q > 0:
                    robot.param.set("ATC", TC/Q)
                    robot.param.set("AVC", VC/Q)
                else:
                    robot.param.set("ATC", 0)
                    robot.param.set("AVC", 0)
                robot.param.set("profit", PROFIT)
                robot.param.set("total_profit", robot.param.get("total_profit")+PROFIT)

                # Update at patch:
                res.all_profits   += [PROFIT]
                res.all_drops     += [Q]
                res.drop_counter  += 1
                res.last_drop     = step

                print(step, ' ', robot.id, "foraged", Q, '/',res.quantity , "@ cost", TC, "and profited", PROFIT)

                robot.param.set("quantity", 0)
                robot.param.set("foraging", False)

        # Long-run decision
        elif not robot.param.get("foraging"):

            if clocks['travel'][robot].query():
                
                choice = long_run_decision(robot, allresources)

                if choice == robot.param.get("at"):
                    print(step, ' ', robot.id, 'resuming')
                    robot.param.set("foraging", True)
                    robot.param.set("last_col", step)
                    robot.param.set("first_col", step)
                
                elif choice == -1:
                    print(step, ' ', robot.id, 'idling')
                    robot.param.set("at", choice)
                    robot.param.set("VC", 0)
                    robot.param.set("ATC", 0)
                    robot.param.set("AVC", 0)
                    robot.param.set("profit", 0)
                    clocks['travel'][robot].reset()

                else:
                    print(step, ' ', robot.id, 'changing ', choice)
                    robot.param.set("at", choice)
                    robot.param.set("foraging", True)
                    robot.param.set("last_col", step)
                    robot.param.set("first_col", step)
            else:
                robot.param.set("mc_col", 0)


    # Tasks to perform for each resource
    for res in allresources:

        # Robot is foraging? YES -> Add to foragers
        for robot in allrobots:
            if robot.param.get("at") == res.id and robot.param.get("foraging"):
                if robot not in other['foragers'][res]:
                    other['foragers'][res].add(robot)
                    clocks['forage'][robot] = Timer(100*TPS)

        # Forage resources
        for robot in random.sample(other['foragers'][res], len(other['foragers'][res])):

            if not robot.param.get("foraging"):
                other['foragers'][res].remove(robot)
                clocks['forage'][robot] = None
                
            else:
                clocks['forage'][robot].set(forage_rate(res, robot.param.get("quantity")), reset=False)

                if clocks['forage'][robot].query():
                    robot.param.set("mc_col", step-robot.param.get("last_col"))
                    robot.param.set("quantity", robot.param.get("quantity")+1)
                    robot.param.set("last_col", step)
                    res.quantity -= 1
                else:
                    robot.param.set("mc_col", 0)

        # Regenerate resources
        if res.quantity <= 0:
            print('RESOURCE EXAUSTED')
            sys.exit()

        if clocks['regen'][res].query() and res.quantity < lp['patches']['qtty_max'][res.quality]:
            res.quantity += 1
        

if __name__ == "__main__":
    print("Initializing simulation...")
    import numpy as np
    import matplotlib.pyplot as plt
    import time as tt

    sttime = tt.time()
    # --------------------------
    # Parameters
    # --------------------------
    timedelta = 0.1
    max_steps = 18000
    n = 12

    # ct                    (higher -> more resources)
    travel_cost = 1000
    travel_var  = 0

    # Qmax and R            (higher -> more resources)
    Qm = 300
    regen_rate = 1

    # c0 and c1             (higher -> more resources)
    c0  =  0.3
    c50 = 15
    c1  = 2 * (c50 - c0) / Qm
    print(c1)

    # c3
    robot_slope = 0.05
    max_carry = 60
    utility = 60


##############################################
    cp['max_Q'] = max_carry
    lp['patches']['qtty_min']  = {'red': Qm}
    lp['patches']['qtty_max']  = {'red': Qm}
    lp['patches']['utility']     = {'red': utility}
    lp['patches']['forage_rate'] = {'red': c0}
    lp['patches']['regen_rate']  = {'red': 1/regen_rate}           
    lp['patches']['dec_returns']['thresh'] = Qm  
    lp['patches']['dec_returns']['slope']  = c1
    lp['patches']['dec_returns']['slope_robot'] = robot_slope

    def forage_rate(res, carried = 0):
        c0 = lp['patches']['forage_rate'][res.quality]
        c1 = lp['patches']['dec_returns']['slope']
        c3 = lp['patches']['dec_returns']['slope_robot']

        threshold = lp['patches']['dec_returns']['thresh']
        dec_func = lp['patches']['dec_returns']['func']

        cost_patch = c0
        cost_robot = 0

        if res.quantity <= threshold:
            if dec_func == 'linear':
                b = c0 + c1 * threshold
                cost_patch = b - c1 * res.quantity

        if carried:
            cost_robot = c3 * carried

        return (cost_patch + cost_robot) * TPS
##############################################

    # Initialize simulation
    init()
    print(f"Initialized {len(allresources)} resources and {len(allrobots)} robots.")
    import pandas as pd

    # Simulation loop  # or whatever value you want
    step = 0
    time = np.arange(max_steps)

    q_p = np.zeros(max_steps)         # Quantity at patch over time
    c_p = np.zeros(max_steps)         # Cost at patch over time
    q_r = np.zeros(max_steps)         # Quantity carried by all robots over time
    f_r = np.zeros(max_steps)         # number of foraging robots
    profit = np.zeros(max_steps)      

    ind_qr     = np.zeros((n, max_steps)) 
    ind_profit = np.zeros((n, max_steps))      # Profit over time
    ind_q    = np.zeros((n, max_steps)) 
    ind_mc   = np.zeros((n, max_steps)) 
    ind_cost = np.zeros((n, max_steps)) 
    ind_fr   = np.zeros((n, max_steps)) 
    ind_atc   = np.zeros((n, max_steps)) 
    ind_avc   = np.zeros((n, max_steps)) 
    q_c      = np.zeros(max_steps)     # quantity collected over time

    while step < max_steps:
        pre_step()

        res = allresources[0]
        q_p[step] = res.quantity       
        c_p[step] = forage_rate(res)       
        q_r[step] = sum([robot.param.get("quantity") for robot in allrobots])
        q_c[step] = resource_counter[res.quality]   
        f_r[step] = sum([robot.param.get("foraging") for robot in allrobots])
        profit[step] = sum([robot.param.get("profit") for robot in allrobots])

        for i, robot in enumerate(allrobots):
            ind_profit[i, step] = robot.param.get("profit")
            ind_qr[i, step] = robot.param.get("quantity")
            ind_q[i, step] = robot.param.get("quantity")
            ind_mc[i, step] = robot.param.get("mc_col")
            ind_cost[i, step] = robot.param.get("VC")
            ind_atc[i, step] = robot.param.get("ATC")
            ind_avc[i, step] = robot.param.get("AVC")
            ind_fr[i, step] = int(robot.param.get("foraging"))*(1+robot.id*0.05)

        step += 1

    print(f"Simulation finished after {step} steps.")
    print(f"Final resources collected: {resource_counter}")
    print(f"Final profits collected: {[robot.param.get('profit') for robot in allrobots]}")
    print(f"Quantity at patch: {[res.quantity for res in allresources]}")

    print(tt.time()-sttime)

    time = time*timedelta/60
    n_plots = 7
    j = 1
    plt.figure(figsize=(12, 4*n_plots))
   
    plt.subplot(n_plots, 1, j)
    plt.plot(time, q_p, label='')
    plt.ylabel("$q_p$")
    plt.ylim(bottom=min(q_p)*0.8, top=max(q_p))
    j+=1

    plt.subplot(n_plots, 1, j)
    plt.stackplot(time, ind_qr, labels=[f'{i+1}' for i in range(n)])
    plt.ylabel("$q_{r,i}$")
    plt.legend(loc='upper left')
    j += 1

    plt.subplot(n_plots, 1, j)
    for i in range(n):
        plt.scatter(time[ind_fr[i] != 0], ind_fr[i][ind_fr[i] != 0], s=1)
    plt.xlabel("Time (s)")
    plt.ylabel("$s_i$")
    plt.yticks([])
    j+=1

    plt.subplot(n_plots, 1, j)
    for i in range(n):
        plt.scatter(time[ind_mc[i] != 0], ind_mc[i][ind_mc[i] != 0], label=f'Marginal Cost {i+1}', s=10)
    plt.axhline(y=allresources[0].utility, color='gray', linestyle='--', linewidth=1, label='Utility') 
    c_p_ema = pd.Series(c_p).ewm(span=20, adjust=False).mean()
    plt.plot(time, c_p_ema, color='gray')
    plt.ylabel("$\dot C$")
    j+=1

    plt.subplot(n_plots, 1, j)
    plt.plot(time, profit, label='Profit', color='green')
    plt.axhline(y=0, color='gray', linestyle='--', linewidth=1, label='Zero Profit') 
    plt.ylabel("Total Profit")
    # plt.legend()
    j+=1


    plt.subplot(n_plots, 1, j)
    for i in range(n):
        plt.plot(time, ind_profit[i], label=f'Profit {i+1}')
    plt.axhline(y=0, color='gray', linestyle='--', linewidth=1, label='Zero Profit') 
    plt.ylabel("Individual Profits")
    # plt.legend()
    j+=1

    plt.subplot(n_plots, 1, j)
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    for i in range(n):
        color = colors[i % len(colors)]  # Cycle through if n > number of default colors
        plt.plot(time, ind_atc[i], color=color)
        plt.plot(time, ind_avc[i], color=color, linestyle='--')  # Use a different linestyle for distinction
    plt.axhline(y=allresources[0].utility, color='gray', linestyle='--', linewidth=1, label='Utility') 
    plt.axhline(y=allresources[0].utility*VC_FATOR, color='gray', linestyle='--', linewidth=1, label='Utility') 
    plt.xlabel("Time (minutes)")
    plt.ylabel("Individual Costs")
    j += 1

    plt.tight_layout()
    plt.show()
    print(tt.time()-sttime)