import math, random


def long_run_decision(robot, allresources, current_action):
    next_action = current_action

    def get_expected_profit(resource, robot):
        # Estimate profit per unit = utility - avg cost
        recent_trip = resource.trips[-1] if resource.trips else None
        if recent_trip and recent_trip.ATC:
            return resource.utility - recent_trip.ATC
        else:
            return resource.utility  # optimistic initialization

    if len(robot.trips) == 1:
        next_action = random.choice(allresources).id

    elif current_action == -1:
        # Idle robot decision: pick patch with highest estimated profit
        profits = [get_expected_profit(res, robot) for res in allresources]
        max_profit = max(profits)

        if max_profit <= 50:
            next_action = -1  # stay idle if no patch is profitable
        else:
            # Softmax or greedy selection
            next_action = profits.index(max_profit)

    else:
        # After a trip, evaluate if it's worth continuing
        current_resource = allresources[current_action]
        last_trip = robot.trips[-1]
        PROFIT_PER_UNIT = current_resource.utility - last_trip.ATC

        if PROFIT_PER_UNIT < 0:
            # Rest or re-evaluate
            next_action = -1
            robot.param.set("rest", abs(PROFIT_PER_UNIT))  # or REST_FACTOR * ...
        else:
            # Keep going if profitable
            next_action = current_action

    return next_action
