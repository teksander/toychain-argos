import math, random

# --------------------------

# Environment Parameters

# --------------------------

timedelta = 0.1

max_steps = 18000

N_runs = 1

use_participant_decisions = False

# Number of robots

n = 12

# Number of resources

resource_counts = {'red': 1, 'blue': 1, 'green': 1}

# Ct        (higher -> more resources)

travel_cost = {'red': 50, 'blue': 50, 'green': 50}

travel_var  = {'red': 20, 'blue': 20, 'green': 20}

# Qm and R  (higher -> more resources)

Qm = {'red': 300, 'blue': 300, 'green': 300}

R  = {'red': 1, 'blue': 1.2, 'green': 1.3}

# c0 and c1 (higher -> more resources)

c0  = {'red': 0, 'blue': 0, 'green': 0}

c50 = {'red': 7, 'blue': 7, 'green': 7}

c1  = {key: 2 * (c50[key] - c0[key]) / Qm[key] for key in Qm}

# U

utility = {'red': 30, 'blue': 33, 'green': 37}

# c3 and Cm 

c3 = 0.01

Cm = 150



# --------------------------

# Robot Decisions

# --------------------------





def _time_since(now, trip):

    """Age of the trip in steps (use start if still open)."""

    end = trip.end

    return now - end



def _cooldown_after_loss(trip):

    """

    rest_period = (-P) - travel_time , expressed in steps.

    If profit was ≥ 0 we return 0 (no cooldown).

    """

    if trip.P >= 0:

        return 0

    #travel_time = max(0, trip.TC - trip.VC)   # fixed-cost part in same units

    #return max(0, int(-trip.P - travel_time))

    return -trip.P





def long_run_decision(robot, allresources, current_action):

    """

    • Choose the resource whose most recent visit was the longest ago,

      **unless** that visit made a loss and is still inside its cooldown.

    • If *all* patches are in cooldown → return -1 (idle).

    """



    step_now = robot.param.get("global_step")



    # ------------------------------------------------------------------

    # Build (age, res_id, in_cooldown?) tuples

    # ------------------------------------------------------------------

    info = []         # (age, rid, cooldown_flag)

    for res in allresources:

        if res.trips:

            last = res.trips[-1]

            age  = (_time_since(step_now, last))/10

            cooldown = age < _cooldown_after_loss(last)

        else:

            age, cooldown = float("inf"), False      # never visited

        info.append((age, res.id, cooldown))



    # ------------------------------------------------------------------

    # Filter viable patches & pick the oldest among them

    # ------------------------------------------------------------------

    viable = [(age, rid) for age, rid, cd in info if not cd]

    print(f"Robot {robot.id} decision info: {info}, viable: {viable}")



    if viable:

        max_age = max(age for age, _ in viable)

        candidates = [rid for age, rid in viable if age == max_age]

        return random.choice(candidates)



    # ------------------------------------------------------------------

    # Every patch still cooling down → idle

    # ------------------------------------------------------------------

    return -1

