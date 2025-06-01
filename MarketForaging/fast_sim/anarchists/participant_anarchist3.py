import math, random
import numpy as np
from config import R
from config import c50

# --------------------------
# Robot Decisions
# --------------------------

def long_run_decision(robot, allresources, current_action):
    # Return the patch index for the next forage trip (-1 means idle)

    # Current foraging resource index (-1 for idle)
    next_action = current_action

    UTILITY_IMPORTANCE = 1

    # Decision for first trip (executed once at start)
    if len(robot.trips) == 1:
        
        weights = [R[r.quality]/c50[r.quality] * r.utility*UTILITY_IMPORTANCE  for r in allresources]
        next_action = random.choices([r.id for r in allresources], weights=weights, k=1)[0]

    # Decision if robot is idle (executed every timestep if robot is idle)
    elif current_action == -1:
        print("Should not idle ever")
        next_action = current_action


    # Decision at the end of a trip (executed once after the robot finishes a foraging trip)
    else:
        # Sort the resources by profit (highest first)
        sorted_resources = sorted(allresources, key=lambda r: r.trips[-1].P, reverse=True)
        # Find the most profitable resource
        most_profitable  = sorted_resources[0].id

        # Sort the resources by age (oldest first)
        sorted_resources = sorted(allresources, key=lambda r: r.trips[-1].end)
        # Find the most profitable resource
        most_inactive   = sorted_resources[0].id

        next_action = random.choice([most_profitable, most_inactive])
    return next_action

    
