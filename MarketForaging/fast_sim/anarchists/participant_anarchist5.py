import math, random

# --------------------------
# Robot Decisions
# --------------------------

def long_run_decision(robot, allresources, current_action):
    # Return the patch index for the next forage trip (-1 means idle)

    # Current foraging resource index (-1 for idle)
    next_action = current_action

    # Decision for first trip (executed once at start)
    if len(robot.trips) == 1:

        # Choose a random patch
        next_action = random.choice([r.id for r in allresources])

    # Decision if robot is idle (executed every timestep if robot is idle)
    elif current_action == -1:

        # Choose a random patch
        next_action = random.choice([r.id for r in allresources])


    # Decision at the end of a trip (executed once after the robot finishes a foraging trip)
    else:

        # Choose the best patch
        sorted_resources = sorted(allresources, key=lambda r: r.trips[-1].P, reverse=True)
        next_action = sorted_resources[0].id

    return next_action

    
