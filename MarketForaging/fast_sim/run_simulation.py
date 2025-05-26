#!/usr/bin/env python3
# /* Import Packages */
#######################################################################
import random
import sys, os
import importlib
import copy

import numpy as np
import matplotlib.pyplot as plt
import time as tt
import pandas as pd

from utils import Timer, Resource, Robot, Trip
from decisions.participant_0 import *

# /* Global Variables */
#######################################################################

def generate_resource(n = 1, qualities = None, max_attempts = 500):

    for i in range(n):
        # Generate quantity of resource and quality
        quality = qualities[i]
        quantity = lp['patches']['qtty_max'][quality]
        x = y = radius = 0

        # Append new resource to the global list of resources
        resource = Resource({'x':x, 'y':y, 'radius':radius, 'quantity':quantity, 'quality':quality, 'utility':lp['patches']['utility'][quality]})
        
        resource.id = len(allresources)
        resource.all_profits   = []
        resource.all_drops     = []
        resource.drop_counter  = 0
        resource.last_drop     = 0
        resource.trips         = [Trip()]

        resource.param.set("id", len(allresources))
        resource.param.set("all_profits", [])
        resource.param.set("all_drops", [])
        resource.param.set("drop_counter", 0)
        resource.param.set("last_drop", 0)

        allresources.append(resource)

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

    # Init robots
    for i in range(n):
        
        robot = Robot()
        robot.param.set("id", len(allrobots))
        robot.param.set("at", -1)
        robot.param.set("last_col", 0)
        robot.param.set("last_dec", 0)
        robot.param.set("start", 0)
        robot.param.set("quantity", 0)
        robot.param.set("foraging", False) 
        robot.param.set("ATC", 0)
        robot.param.set("AVC", 0)
        robot.param.set("profit", 0)
        robot.param.set("total_profit", 0)
        robot.param.set("first_col", 0)
        robot.param.set("VC", 0)
        robot.long_run_decision = controller_registry.get(int(robot.id), controller_registry[0])
        robot.trips = [Trip()]
        clocks['travel'][robot] = Timer()
        allrobots.append(robot)
    random.shuffle(allrobots)

def pre_step():
    global resource_counter

    for clock in clocks['forage'].values():
        if isinstance(clock, Timer): clock.time.step()

    for clock in clocks['regen'].values():
        if isinstance(clock, Timer): clock.time.step()

    for clock in clocks['travel'].values():
        if isinstance(clock, Timer): clock.time.step()


    # Tasks to perform for each robot
    for robot in random.sample(allrobots,len(allrobots)):

        # Short-run decision
        if robot.param.get("foraging") and robot.param.get("at") != -1:
            res = allresources[robot.param.get("at")]

            # Stop foraging condition
            if res.utility <= step-robot.param.get("last_col") or robot.param.get("quantity") >= Cm:

                FC = (travel_cost[res.quality] + random.randint(-travel_var[res.quality], travel_var[res.quality]))*TPS
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

                trip = Trip(robot.param.get("first_col"), step, Q, TC, VC, PROFIT)
                robot.trips += [trip]
                res.trips   += [trip]

                # Update at patch:
                res.all_profits   += [PROFIT]
                res.all_drops     += [Q]
                res.drop_counter  += 1
                res.last_drop     = step

                print(step, ' ', robot.id, "foraged", Q, '/',res.quantity, res.quality , "@ cost", TC, "and profited", PROFIT)

                robot.param.set("quantity", 0)
                robot.param.set("foraging", False)

        # Long-run decision
        elif not robot.param.get("foraging"):

            if clocks['travel'][robot].query():

                choice = robot.long_run_decision(robot, allresources, robot.param.get("at"))
                # print(f"Robot {i}: controller {robot.long_run_decision}, quantity {robot.param.get('quantity')}, at {robot.param.get('at')}, profit {robot.param.get('profit')}")


                if choice == -1:
                    print(step, ' ', robot.id, 'idling')
                    robot.param.set("at", choice)
                    robot.param.set("VC", 0)
                    robot.param.set("ATC", 0)
                    robot.param.set("AVC", 0)
                    robot.param.set("profit", 0)

                elif choice == robot.param.get("at"):
                    print(step, ' ', robot.id, 'resuming')
                    robot.param.set("foraging", True)
                    robot.param.set("last_col", step)
                    robot.param.set("first_col", step)

                else:
                    print(step, ' ', robot.id, 'changing ', choice)
                    robot.param.set("at", choice)
                    robot.param.set("foraging", True)
                    robot.param.set("last_col", step)
                    robot.param.set("first_col", step)
            else:
                robot.param.set("mc_col", 0)


    # Tasks to perform for each resource
    for res in random.sample(allresources,len(allresources)):

        # Robot is foraging? YES -> Add to foragers
        for robot in random.sample(allrobots,len(allrobots)):
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
    random.seed(42)
    np.random.seed(42)
##############################################
    lp = dict()
    lp['patches'] = dict()
    lp['patches']['dec_returns'] = dict()
    lp['patches']['counts']      = resource_counts
    lp['patches']['qtty_max']    = Qm
    lp['patches']['utility']     = utility
    lp['patches']['forage_rate'] = c0
    lp['patches']['regen_rate']  = {key: 1 / value for key, value in R.items()}          
    lp['patches']['dec_returns']['thresh'] = Qm
    c1  = {key: 2 * (c50[key] - c0[key]) / Qm[key] for key in Qm}
    lp['patches']['dec_returns']['slope']  = c1
    lp['patches']['dec_returns']['slope_robot'] = c3

    def forage_rate(res, carried = 0):
        c0 = lp['patches']['forage_rate'][res.quality]
        c1 = lp['patches']['dec_returns']['slope'][res.quality]
        c3 = lp['patches']['dec_returns']['slope_robot']

        threshold = lp['patches']['dec_returns']['thresh'][res.quality]

        cost_patch = c0
        cost_robot = 0

        if res.quantity <= threshold:
            b = c0 + c1 * threshold
            cost_patch = b - c1 * res.quantity

        if carried:
            cost_robot = c3 * carried

        return (cost_patch + cost_robot) * TPS
##############################################
    
    # Directory where participant files are stored
    PARTICIPANT_DIR = "decisions"

    # Registry: maps robot.id to its controller function
    controller_registry = {}

    # Load participant files
    for filename in os.listdir(PARTICIPANT_DIR):
        if filename.startswith("participant_") and filename.endswith(".py"):
            module_name = filename[:-3]  # Strip '.py'
            try:
                module = importlib.import_module(f"{PARTICIPANT_DIR}.{module_name}")
                robot_id = int(module_name.split("_")[1])
                if robot_id == force_controller:
                    force_module = module.long_run_decision
                controller_registry[robot_id] = module.long_run_decision
            except Exception as e:
                print(f"Failed to load {module_name}: {e}")
    
    if force_controller > 0:
        controller_registry = {k:module.long_run_decision for k in controller_registry}

    if not use_participant_decisions:
        controller_registry = {0: controller_registry[0]}


##############################################

    total_multirun_profit = {i: 0 for i in range(n)}
    total_multirun_collection = 0

    for i in range(N_runs):
        TPS = 10

        # Initialize timers/accumulators/logs:
        global clocks, other
        clocks, other = dict(), dict()

        clocks['regen']      = dict()
        clocks['travel']     = dict()
        clocks['forage']     = dict()
        other['foragers']    = dict()

        global allrobots, allresources
        allrobots, allresources = [], []

        global resource_counter
        resource_counter = {'red': 0, 'green': 0 , 'blue': 0, 'yellow': 0}
        
        # Initialize simulation
        init()
        sttime = tt.time()
        print(f"Initialized {len(allresources)} resources and {len(allrobots)} robots.")

        # Simulation loop  # or whatever value you want
        step = 0
        time = np.arange(max_steps)
        Tr = sum(resource_counts.values())

        q_p = np.zeros((Tr, max_steps))          # Quantity at patch over time
        c_p = np.zeros((Tr, max_steps))          # Cost at patch over time
        q_r = np.zeros((Tr, max_steps))          # Quantity carried by all robots over time
        f_r = np.zeros((Tr, max_steps))          # number of foraging robots
        profit = np.zeros((Tr, max_steps))       
        q_c    = np.zeros((Tr, max_steps)) 

        ind_qr     = np.zeros((n, max_steps)) 
        ind_profit = np.zeros((n, max_steps))      # Profit over time
        ind_tprofit = np.zeros((n, max_steps))
        ind_q    = np.zeros((n, max_steps)) 
        ind_mc   = np.zeros((n, max_steps)) 
        ind_cost = np.zeros((n, max_steps)) 
        ind_fr   = np.zeros((n, max_steps)) 
        ind_atc   = np.zeros((n, max_steps)) 
        ind_avc   = np.zeros((n, max_steps)) 
        ind_at    = np.zeros((n, max_steps)) 
            # quantity collected over time

        while step < max_steps:
            pre_step()

            for i, res in enumerate(allresources):
                q_p[i, step] = res.quantity       
                c_p[i, step] = forage_rate(res)       
                # q_r[i, step] = sum([robot.param.get("quantity") for robot in allrobots if robot.get.param("at")==i])
                q_c[i, step] = resource_counter[res.quality]   
                profit[i, step] = res.trips[-1].P

            for i, robot in enumerate(allrobots):
                ind_profit[i, step] = robot.param.get("profit")
                ind_tprofit[i, step] = robot.param.get("total_profit")
                ind_qr[i, step] = robot.param.get("quantity")
                ind_q[i, step] = robot.param.get("quantity")
                ind_mc[i, step] = robot.param.get("mc_col")
                ind_cost[i, step] = robot.param.get("VC")
                ind_atc[i, step] = robot.param.get("ATC")
                ind_avc[i, step] = robot.param.get("AVC")
                ind_at[i, step] = robot.param.get("at")

            step += 1

        print(f"Simulation finished after {step} steps.")
        print(f"Final resources collected: {resource_counter}")
        print(f"Final profits collected: {[robot.param.get('profit') for robot in allrobots]}")
        print(f"Quantity at patch: {[res.quantity for res in allresources]}")
        print(f"Simulation duration: {tt.time() - sttime:.1f}s")
        print(controller_registry)
        print(f"Robot {i}: controller {robot.long_run_decision}, quantity {robot.param.get('quantity')}, at {robot.param.get('at')}, profit {robot.param.get('profit')}")

        
        final_profits = {robot.id: robot.param.get('total_profit') for robot in allrobots}
        # final_collection = sum(resource_counter.values())

        # total_multirun_profit     += np.array(final_profits)
        # total_multirun_collection += final_collection

        ordered_profits = np.array([final_profits[i] for i in range(n)])
        # total_multirun_profit += ordered_profits
        for rid, profit in final_profits.items():
            total_multirun_profit[rid] += profit
        
    print("FINAL RESULTS")
    print(f"Robot Profits: {total_multirun_profit}")
    print(f"Swarm Stockpile: {total_multirun_collection}")

    if N_runs == 1:
        time = time*timedelta/60
        n_plots = 5
        j = 1
        plt.figure(figsize=(12, 4*n_plots))
    
        plt.subplot(n_plots, 1, j)
        for i in range(Tr):
            plt.plot(time, q_p[i], color=allresources[i].quality, label='')
        plt.ylabel("Quantity $q_p$ (per patch)")
        plt.ylim(bottom=np.min(q_p) * 0.8, top=np.max(q_p))
        j+=1

        plt.subplot(n_plots, 1, j)
        for i in range(Tr):
            plt.plot(time, q_c[i], color=allresources[i].quality, label='')
        plt.ylabel("Quantity Collected (per patch)")
        j+=1

        plt.subplot(n_plots, 1, j)
        for i in range(Tr):
            plt.plot(time, profit[i], color=allresources[i].quality, label='')
        plt.axhline(y=0, color='gray', linestyle='--', linewidth=1, label='Zero Profit') 
        plt.ylabel("Profit (per patch)")
        j+=1


        plt.subplot(n_plots, 1, j)
        for i in range(n):
            plt.plot(time, ind_profit[i], label=f'Profit {i+1}')
        plt.axhline(y=0, color='gray', linestyle='--', linewidth=1, label='Zero Profit') 
        plt.ylabel("Profit (per robot)")
        plt.legend()
        j+=1

        plt.subplot(n_plots, 1, j)
        for i in range(n):
            plt.plot(time, ind_tprofit[i], label=f'Profit {i+1}')
        plt.axhline(y=0, color='gray', linestyle='--', linewidth=1, label='Zero Profit') 
        plt.ylabel("Total Profit (per robot)")
        plt.legend()
        j+=1


        # plt.subplot(n_plots, 1, j)
        # for i in range(n):
        #     plt.scatter(time[ind_at[i]>=0], ind_at[i][ind_at[i]>=0])
        # plt.ylabel("Is foraging patch? (per robot)")
        # j+=1

        # plt.subplot(n_plots, 1, j)
        # colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
        # for i in range(n):
        #     color = colors[i % len(colors)]  # Cycle through if n > number of default colors
        #     plt.plot(time, ind_atc[i], color=color)
        #     plt.plot(time, ind_avc[i], color=color, linestyle='--')  # Use a different linestyle for distinction
        # plt.axhline(y=allresources[0].utility, color='gray', linestyle='--', linewidth=1, label='Utility') 
        # plt.axhline(y=allresources[0].utility*VC_FATOR, color='gray', linestyle='--', linewidth=1, label='Utility') 
        # plt.xlabel("Time (minutes)")
        # plt.ylabel("Costs (per robot)")
        # j += 1

        plt.tight_layout()
        plt.show()


        # Marginal costs plot (one per patch)
        plt.figure(figsize=(12, 4*Tr))
        for j in range(Tr):
            resource = allresources[j]
            plt.subplot(n_plots, 1, j+1)
            for i in range(n):
                mask = (ind_mc[i] != 0) & (ind_at[i] == resource.id)
                plt.scatter(time[mask], ind_mc[i][mask], s=10)
            plt.axhline(y=resource.utility, color='gray', linestyle='--', linewidth=1, label='Utility') 
            plt.text(-0.06, 0.5, f'{resource.quality} patch', va='center', ha='center', rotation='vertical', transform=plt.gca().transAxes, fontweight='bold')
            c_p_ema = pd.Series(c_p[j]).ewm(span=20, adjust=False).mean()
            plt.plot(time, c_p_ema, color='gray')
            plt.legend()
            j+=1

        plt.tight_layout()
        plt.show()