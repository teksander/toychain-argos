import math, random

# --------------------------
# Robot Decisions
# --------------------------

def long_run_decision(robot, allresources, current_action):
    # Return the patch index for the next forage trip (-1 means idle)
    # Execution: once after every trip
    #            every timestep if robot is idle

    # Current foraging resource index (-1 for idle)
    next_action = current_action

    # Decision for first trip (executed once at start)
    if len(robot.trips) == 1:
        utilities = [resource.utility for resource in allresources]
        next_action = utilities.index(max(utilities))                   # Max utility patch
        next_action = random.choice(allresources).id                    # Random patch
        # next_action = allresources[robot.id % len(allresources)].id     # Centralized round-robin

    # Decision if robot is idle (executed every timestep if robot is idle)
    elif current_action == -1:
        for resource in allresources:
            if resource.trips[-1].P > 0:
                next_action = resource.id


    # Decision at the end of a trip (executed once after the robot finishes a foraging trip)
    else:
        next_action = random.choice(allresources).id   
        # current_resource = allresources[current_action]

        # PROFIT_PER_UNIT = current_resource.utility - robot.trips[-1].ATC
        
        # if PROFIT_PER_UNIT < 0:
        #     next_action = -1
        #     # robot.param.set("rest", REST_FATOR * PROFIT_PER_UNIT)

    return next_action

    