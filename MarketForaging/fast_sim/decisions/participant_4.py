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
        # weights = [R[r.quality]/c50[r.quality] * r.utility*UTILITY_IMPORTANCE  for r in allresources]

        # Choose second best patch
        sorted_resources = sorted(allresources, key=lambda r: r.utility, reverse=True)
        next_action = sorted_resources[1].id

    # Decision if robot is idle (executed every timestep if robot is idle)
    elif current_action == -1:

        # Sort resource by profit to get second best
        sorted_resources = sorted(allresources, key=lambda r: r.trips[-1].P, reverse=True)
        # print(sorted_resources)
        
        # For each resource except the best
        for resource in sorted_resources[1:]:
            
            # Choose the first patch that "is availiable"
            if resource.trips[-1].P > 0:
                next_action = resource.id

    # Decision at the end of a trip (executed once after the robot finishes a foraging trip)
    else:
        # Sort resource by profit to get second best
        sorted_resources = sorted(allresources, key=lambda r: r.trips[-1].P, reverse=True)

        # For each resource except the best
        for resource in sorted_resources[1:]:
            
            # Choose the first that "is not depleted"
            if resource.trips[-1].P > 0:
                next_action = resource.id
                return next_action

        # Otherwise, idle
        next_action = -1

    return next_action

    
