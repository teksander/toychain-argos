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
        # Evaluate initial utility adjusted by crowding (recent trip count)
        scored_resources = []
        for resource in allresources:
            utility = resource.utility
            recent_trips = sum(1 for t in resource.trips if t.end > robot.trips[-1].end - 10)
            score = utility / (1 + recent_trips)  # discourage crowding
            scored_resources.append((score, resource.id))
        next_action = random.choice(allresources).id

    # Decision if robot is idle (executed every timestep if robot is idle)
    elif current_action == -1:
        # Check if any patch had a recently *positive* profit
        scored_resources = []
        for resource in allresources:
            if not resource.trips:
                continue
            recent_trips = resource.trips[-5:]  # recent 5 trips
            profits = [t.P for t in recent_trips if t.P > 0]
            avg_profit = sum(profits) / len(profits) if profits else -math.inf
            scored_resources.append((avg_profit, resource.id))
        
        # Go only if a patch seems promising
        best_profit, best_id = max(scored_resources)
        if best_profit > 0:
            next_action = best_id

    # Decision at the end of a trip (executed once after the robot finishes a foraging trip)
    else:
        current_resource = next(r for r in allresources if r.id == current_action)

        last_trip = robot.trips[-1]
        profit_per_unit = last_trip.P / last_trip.Q if last_trip.Q > 0 else -math.inf

        if profit_per_unit <= 0:
            # If not profitable, look for better patches based on recent global performance
            scored_resources = []
            for resource in allresources:
                recent_trips = resource.trips[-5:]  # last 5 trips
                profits = [t.P for t in recent_trips if t.P > 0]
                avg_profit = sum(profits) / len(profits) if profits else -math.inf
                scored_resources.append((avg_profit, resource.id))
            best_profit, best_id = max(scored_resources)
            if best_profit > 0:
                next_action = best_id
            else:
                next_action = -1  # Rest if all are bad
        else:
            # Continue current or explore slightly better
            current_profit = profit_per_unit
            scored_resources = []
            for resource in allresources:
                recent_trips = resource.trips[-5:]
                profits = [t.P for t in recent_trips if t.P > 0]
                avg_profit = sum(profits) / len(profits) if profits else -math.inf
                scored_resources.append((avg_profit, resource.id))

            better_options = [(p, rid) for (p, rid) in scored_resources if p > current_profit * 1.1]
            if better_options:
                next_action = max(better_options)[1]
            else:
                next_action = current_action  # stick with current if no clear better patch

    return next_action
