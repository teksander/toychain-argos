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

# decisions/participant_0.py
import sys, random, statistics

# ---------- Tunables ----------
RECENT_N          = 20      # average over this many most-recent trips
AGE_BONUS         = 0.5       # extra “virtual profit” per unused step
MAX_AGE_BONUS     = 800     # age cap, keeps score finite for virgin patches
MIN_GO_THRESHOLD  = -20     # go idle if best score ≤ this
# ------------------------------

def _now():
    """Current simulation step, fetched from the main module."""
    return getattr(sys.modules["__main__"], "step", 0)

def _patch_stats(res, now):
    """
    Return (mean_profit, age) for a resource using only public trip history.
    • mean_profit : average of the last RECENT_N completed trips (0 if none)
    • age         : steps since the last completed trip, capped
                    or MAX_AGE_BONUS if none completed yet
    """
    finished = [t for t in res.trips if t.end]          # ignore open trips
    if not finished:                                   # never completed
        return 0.0, MAX_AGE_BONUS

    last_trip = finished[-1]
    age       = min(now - last_trip.end, MAX_AGE_BONUS)

    recent    = finished[-RECENT_N:]
    mean_p    = statistics.fmean(t.P for t in recent) if recent else 0.0
    return mean_p, age

def long_run_decision(robot, allresources, current_action):
    """
    Score = recent_mean_profit + AGE_BONUS * age_since_last_visit.
    Choose patch with highest score, unless every score ≤ MIN_GO_THRESHOLD,
    in which case return -1 (idle).
    """
    now = _now()

    best_score, best_id = -float("inf"), None
    for res in allresources:
        mean_p, age = _patch_stats(res, now)
        score = mean_p + AGE_BONUS * age
        if score > best_score:
            best_score, best_id = score, res.id

    return best_id if best_score > MIN_GO_THRESHOLD else -1
