import math, random
from decisions.participant_0 import R, c50, Qm

# --------------------------
# Robot Decisions
# --------------------------

def long_run_decision(robot, allresources, current_action):
    # Return the patch index for the next forage trip (-1 means idle)

    # Current foraging resource index (-1 for idle)
    next_action = current_action

    IMPORTANCE_OF_UTILITY = 1
    THRESHOLD_ON_QTTY     = 0.8

    # Decision for first trip (executed once at start)
    if len(robot.trips) == 1:
        weights = [R[r.quality]/c50[r.quality] * r.utility*IMPORTANCE_OF_UTILITY  for r in allresources]
        next_action = random.choices([r.id for r in allresources], weights=weights, k=1)[0]

    # Decision if robot is idle (executed every timestep if robot is idle)
    elif current_action == -1:

        # The level of depletion is perfect knowledge
        level_of_depletion = [r.quantity if r.quantity > THRESHOLD_ON_QTTY * Qm[r.quality] else 0
                                for r in allresources
                                ]

        if sum(level_of_depletion) == 0:
            next_action = -1
        else:
            next_action = random.choices([r.id for r in allresources], weights=level_of_depletion, k=1)[0]

    # Decision at the end of a trip (executed once after the robot finishes a foraging trip)
    else:

        # The level of depletion is perfect knowledge
        level_of_depletion = [r.quantity if r.quantity > THRESHOLD_ON_QTTY * Qm[r.quality] else 0
                                for r in allresources
                                ]

        if sum(level_of_depletion) == 0:
            next_action = -1
        else:
            next_action = random.choices([r.id for r in allresources], weights=level_of_depletion, k=1)[0]

    return next_action

# level_of_depletion = []
# for resource in allresources:
#     total_harvested_resources = 0
#     for trip in resource.trips:
#         total_harvested_resources += trip.Q

#     # The level of depletion is the time it took to harvest all extraction
#     level_of_depletion.append(total_harvested_resources/R)

    
