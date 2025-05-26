import math, random

# --------------------------
# Environment Parameters
# --------------------------
timedelta = 0.1
max_steps = 18000
use_participant_decisions = True 
force_controller = -1

# Number of robots
n = 5

# Number of runs
N_runs = 20

# Number of resources
resource_counts = {'red': 1, 'blue': 1, 'green': 1}

# Ct        (higher -> more resources)
travel_cost = {'red': 50, 'blue': 50, 'green': 50}
travel_var  = {'red': 20, 'blue': 20, 'green': 20}

# Qm and R  (higher -> more resources)
Qm = {'red': 300, 'blue': 300, 'green': 300}
R  = {'red': 0.5, 'blue': 0.6, 'green': 0.7}

# c0 and c1 (higher -> more resources)
c0  = {'red': 0, 'blue': 0, 'green': 0}
c50 = {'red': 7, 'blue': 7, 'green': 7}

# U
utility = {'red': 30, 'blue': 33, 'green': 37}

# c3 and Cm 
c3 = 0.03
Cm = 150

# --------------------------
# Robot Decisions
# --------------------------

def long_run_decision(robot, allresources, current_action):
    # Return the patch index for the next forage trip (-1 means idle)

    # Current foraging resource index (-1 for idle)
    next_action = current_action

    # Decision for first trip (executed once at start)
    if len(robot.trips) == 1:
        utilities = [resource.utility for resource in allresources]
        next_action = utilities.index(max(utilities))                   # Max utility patch
        next_action = random.choice(allresources).id                    # Random patch
        next_action = allresources[robot.id % len(allresources)].id     # Centralized round-robin

    # Decision if robot is idle (executed every timestep if robot is idle)
    elif current_action == -1:
        for resource in allresources:
            if resource.trips[-1].P > 0:
                next_action = resource.id


    # Decision at the end of a trip (executed once after the robot finishes a foraging trip)
    else:
        current_resource = allresources[current_action]

        PROFIT_PER_UNIT = current_resource.utility - robot.trips[-1].ATC
        
        if PROFIT_PER_UNIT < 0:
            next_action = -1
            # robot.param.set("rest", REST_FATOR * PROFIT_PER_UNIT)

    return next_action

    