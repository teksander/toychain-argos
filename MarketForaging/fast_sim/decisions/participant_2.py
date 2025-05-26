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

        # Randomely choice a patch
        next_action = random.choice([r.id for r in allresources])

    # Decision if robot is idle (executed every timestep if robot is idle)
    elif current_action == -1:

        # Never idle
        print("Should not idle ever")
        next_action = current_action

    # Decision at the end of a trip (executed once after the robot finishes a foraging trip)
    else:

        # If resource is unexplored, select
        threshold = robot.trips[-1].TC

        for resource in allresources:
            if robot.trips[-1].end-resource.trips[-1].end > threshold:
                next_action = resource.id
                return next_action
        
        # Figure out how my_profit ranks compared to each patch profit
        my_profit        = robot.trips[-1].P
        sorted_resources = sorted(allresources, key=lambda r: r.trips[-1].P, reverse=True)
        my_rank = sum(1 for p in [r.trips[-1].P for r in allresources] if p >= my_profit)
        my_rank -= 2
        
        if my_rank < 0:
            my_rank = len(allresources)-1

        # Forage a resource according to my rank (highest rank goes to worst resource)
        next_resource = sorted_resources[my_rank]
        next_action   = next_resource.id        
        
        # Occasionally explore
        if random.random() > 0.5:
            next_action = random.choice([r.id for r in allresources])

    return next_action

    
