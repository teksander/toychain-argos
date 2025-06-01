import math, random

# --------------------------
# Robot Decisions
# --------------------------
def long_run_decision(robot, allresources, current_action):
    """
    Return the patch index for the next forage trip (-1 means idle).
    Called once after every trip or every timestep if idle.
    """
    # === First trip: pick randomly or by highest utility ===
    if len(robot.trips) == 1:
        return random.choice(allresources).id
        # Or: return max(allresources, key=lambda r: r.utility).id

    # === Idle robot: decide what to do next ===
    elif current_action == -1:
        utilities = [res.utility for res in allresources]
        profits = []

        for res in allresources:
            if res.trips:
                profits.append(res.trips[-1].P)
            else:
                profits.append(0)

        max_profit = max(profits)
        min_profit = min(profits)

        # Thresholds (you can tweak these)
        IDLE_THRESHOLD = 50  # Don't forage if profit too low
        HIGH_PROFIT = 0.67 * max_profit
        LOW_PROFIT = 0.33 * max_profit

        # Decision logic:
        if max_profit < IDLE_THRESHOLD:
            return -1  # stay idle

        # Rank resources by profit
        ranked_resources = sorted(
            [(i, profits[i], utilities[i]) for i in range(len(allresources))],
            key=lambda x: x[1],  # sort by profit
            reverse=True
        )

        for idx, profit, utility in ranked_resources:
            if profit >= HIGH_PROFIT:
                return allresources[idx].id  # Stay on this high-profit patch
            elif profit <= LOW_PROFIT and utility >= IDLE_THRESHOLD:
                # Go to second-best patch (index 1 in ranked list if it exists)
                return idx
                # if len(ranked_resources) > 1:
                #     second_best_idx = ranked_resources[1][0]
                #     return allresources[second_best_idx].id
                # else:
                #     return allresources[idx].id  # Fallback to current

        # If no clear choice, explore randomly
        return random.choice([res.id for res in allresources])

    # === After trip: evaluate if current patch was worth it ===
    else:
        current_resource = allresources[current_action]
        last_trip = robot.trips[-1]

        if hasattr(last_trip, 'ATC'):
            profit_per_unit = current_resource.utility - last_trip.ATC
            if profit_per_unit < 0:
                return -1  # rest or stay idle

        # Default fallback: behave like idle
        return long_run_decision(robot, allresources, -1)

