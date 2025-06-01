# --------------------------
# Environment Parameters
# --------------------------
timedelta = 0.1
max_steps = 18000
N_runs = 20

participants_folder = "biologists"

# Number of robots for each decisions file in participants_folder
n_robots_per_participant = 4

# Number of resources
resource_counts = {'red': 2, 'blue': 2, 'green': 2}

# Ct        (higher -> more resources)
travel_cost = {'red': 50, 'blue': 50, 'green': 50}
travel_var  = {'red': 20, 'blue': 20, 'green': 20}

# Qm and R  (higher -> more resources)
Qm = {'red': 300, 'blue': 300, 'green': 300}
R  = {'red': 0.8, 'blue': 1.2, 'green': 1.4}

# c0 and c1 (higher -> more resources)
c0  = {'red': 0, 'blue': 0, 'green': 0}
c50 = {'red': 7, 'blue': 7, 'green': 7}
c1  = {key: 2 * (c50[key] - c0[key]) / Qm[key] for key in Qm}

# U
utility = {'red': 30, 'blue': 34, 'green': 38}

# c3 and Cm 
c3 = 0.01
Cm = 150
