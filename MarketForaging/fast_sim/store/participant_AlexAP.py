import math, random


# --------------------------
# Robot Decisions
# --------------------------


def long_run_decision(robot, allresources, current_action):
    """
    • If *no* patch has ever been visited before (all resource.trips are empty),
      pick a random resource.
    • Otherwise, pick the resource whose most recent trip ended the
      longest time ago.  (Ties are broken at random.)
    • Never returns –1 (idle) because the spec says “choose a resource”.
    """

    # ------------------------------------------------------------------
    # 1. Build a list of (age, resource_id) pairs
    # ------------------------------------------------------------------
    ages = []          # larger age → longer since last visit

    for res in allresources:
        if res.trips:                      # at least one finished trip
            last_trip = res.trips[-1]
            # We use the trip’s end-time; if end == 0 (still open) treat as now.
            last_finish = last_trip.end
            age = robot.param.get("global_step", 0) - last_finish
        else:                              # never visited
            age = float("inf")             # make it the oldest possible
        ages.append((age, res.id))

    # ------------------------------------------------------------------
    # 2. Choose the resource
    # ------------------------------------------------------------------
    if all(a == float("inf") for a, _ in ages):
        # truly no trips anywhere yet → random pick
        return random.choice(allresources).id

    # otherwise pick the maximum “age”; break ties randomly
    max_age = max(a for a, _ in ages)
    candidates = [rid for a, rid in ages if a == max_age]
    return random.choice(candidates)


    