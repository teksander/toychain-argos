import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
import random
import time

sttime = time.time()
# --------------------------
# Parameters
# --------------------------
timedelta = 0.1
max_steps = 5000
n = 2

# ct                    (higher -> more resources)
travel_cost = 30
travel_var  = 0

# Qmax and R            (higher -> more resources)
initial_quantity = 300
regen_rate = 0.3

# c0 and c1             (higher -> more resources)
foraging_rate =  0.1
foraging_slope = 0.05

# c3
robot_slope = 0
max_carry = 30
utility = 250


# --------------------------
# Derived Parameters
# --------------------------
R  =  regen_rate  # resource replenishment rate (resources/s)
c0 = foraging_rate  # base cost
c1 = foraging_slope  # patch-related cost
c3 = robot_slope  # load-related cost
Qm = initial_quantity  # patch capacity

# --------------------------
# Initial Conditions
# --------------------------
q_r0 = 0.0
q_p0 = Qm
C0 = c0 + c1 * (Qm - q_p0) + c3 * q_r0
y0 = [q_r0, q_p0, C0]

# --------------------------
# Time Span
# --------------------------
t0, tf = 0, max_steps * timedelta

# --------------------------
# System of ODEs
# --------------------------
def system(t_rel, y):
    q_r, q_p, C = y
    C_calc = c0 + c1 * (Qm - q_p) + c3 * q_r
    numerator = (1 / C_calc) + (t_rel / C_calc ** 2) * c1 * R
    denominator = 1 + (t_rel / C_calc ** 2) * (n * c1 + c3)
    dq_r_dt = numerator / denominator

    potential_extraction = n * dq_r_dt
    available_resource = max(q_p, 0.0)
    if potential_extraction > available_resource:
        dq_r_dt = available_resource / n

    dq_p_dt = R - n * dq_r_dt

    if q_p >= Qm and dq_p_dt > 0:
        dq_p_dt = 0.0

    dC_dt = c3 * dq_r_dt - c1 * dq_p_dt
    return [dq_r_dt, dq_p_dt, dC_dt]

def travel_system(t, y):
    q_r, q_p, C = y
    dq_r_dt = 0.0
    dq_p_dt = R if q_p < Qm else 0.0
    dC_dt = 0.0
    return [dq_r_dt, dq_p_dt, dC_dt]

# --------------------------
# Event: when q_r reaches max_carry or marginal utility reaches utlity
# --------------------------
def event_carrying_capacity(t, y):
    q_r, q_p, C = y
    return q_r - max_carry

event_carrying_capacity.terminal = True
event_carrying_capacity.direction = 1


def event_utility(t, y):
    q_r, q_p, C = y
    C_calc = c0 + c1 * (Qm - q_p) + c3 * q_r

    numerator = (1 / C_calc) + (t / C_calc**2) * c1 * R
    denominator = 1 + (t / C_calc**2) * (n * c1 + c3)
    dq_r_dt = numerator / denominator

    potential_extraction = n * dq_r_dt
    available_resource = max(q_p, 0.0)
    if potential_extraction > available_resource:
        dq_r_dt = available_resource / n

    dC_dt = (n * c1 + c3) * dq_r_dt - c1 * R

    if dC_dt <= 0:
        return -np.inf

    inv_dC_dt = 1 / dC_dt
    return inv_dC_dt - utility

event_utility.terminal = True
event_utility.direction = 1

# --------------------------
# Solve the system with resets
# --------------------------
T = []
Y = []
dYdt = []
mode = []  # 0 = foraging, 1 = traveling

current_time = t0
current_state = y0
relative_time_offset = 0.0

while current_time < tf:
    
    # Foraging phase
    sol = solve_ivp(
        system,
        [current_time - relative_time_offset, tf - relative_time_offset],
        current_state,
        events=[event_carrying_capacity, event_utility],
        dense_output=True,
        max_step=timedelta,
        rtol=1e-3, atol=1e-5
    )

    sol.t += relative_time_offset
    T.append(sol.t)
    Y.append(sol.y)
    mode.extend([0] * len(sol.t))

    dydt_segment = np.array([system(t - relative_time_offset, sol.y[:, i]) for i, t in enumerate(sol.t)])
    dYdt.append(dydt_segment)

    if sol.status == 1:  # Carrying capacity reached
        # Travel phase
        travel_start_time = sol.t[-1]
        travel_end_time = travel_start_time + travel_cost
        q_p_after = sol.y[1, -1]
        q_p_after = min(q_p_after, Qm)
        travel_initial_state = [0.0, q_p_after, 0.0]

        travel_sol = solve_ivp(
            travel_system,
            [travel_start_time, min(travel_end_time, tf)],
            travel_initial_state,
            dense_output=True,
            max_step=timedelta,
            rtol=1e-3, atol=1e-5
        )

        T.append(travel_sol.t)
        Y.append(travel_sol.y)
        mode.extend([1] * len(travel_sol.t))

        dydt_travel = np.array([travel_system(t, travel_sol.y[:, i]) for i, t in enumerate(travel_sol.t)])
        dYdt.append(dydt_travel)

        # Prepare for next forage phase
        q_r_next = 0.0
        q_p_next = travel_sol.y[1, -1]
        q_p_next = min(q_p_next, Qm)
        C_next = c0 + c1 * (Qm - q_p_next)
        current_state = [q_r_next, q_p_next, C_next]
        current_time = travel_sol.t[-1]
        relative_time_offset = current_time
    else:
        break

# Concatenate all pieces
T = np.hstack(T)
Y = np.hstack(Y)
dYdt = np.vstack(dYdt)
mode = np.array(mode)

q_r = Y[0]
q_p = Y[1]
C = Y[2]

# Derivatives directly from integration
dq_r_dt = dYdt[:, 0]
dq_p_dt = dYdt[:, 1]
dC_dt = dYdt[:, 2]

print(time.time()-sttime)

# --------------------------
# Plotting
# --------------------------
n_plots = 6
axs = [0] * n_plots  # pre-allocate list
j = 0

fig, axs_plot = plt.subplots(n_plots, 1, figsize=(12, 4 * n_plots), sharex=True)

# q_p
axs[j] = axs_plot[j]
axs[j].plot(T, q_p, label='Patch Resources ($q_p$)', linewidth=2)
axs[j].axhline(Qm, color='gray', linestyle='--', label='Patch Capacity ($Q_m$)')
axs[j].set_ylabel("$q_p$")
axs[j].set_ylim(bottom=0)
j += 1

# q_r
axs[j] = axs_plot[j]
axs[j].plot(T, q_r, label='Carried Resources ($q_r$)', linewidth=2)
axs[j].axhline(n * max_carry, color='gray', linestyle='--', label='Carry Capacity')
axs[j].set_ylabel("$q_r$")
axs[j].set_ylim(bottom=0)
j += 1

# C
axs[j] = axs_plot[j]
axs[j].plot(T, C, label='Foraging Cost ($C$)', linewidth=2)
axs[j].set_ylabel("$C$")
axs[j].set_ylim(bottom=0)
j += 1

# dq_p_dt
axs[j] = axs_plot[j]
axs[j].plot(T, dq_p_dt, label='Patch Derivative ($\\dot{q_p}$)', linewidth=2)
axs[j].set_ylabel("$\\dot{q_p}$")
j += 1

# dq_r_dt
axs[j] = axs_plot[j]
axs[j].plot(T, dq_r_dt, label='Robot Derivative ($\\dot{q_r}$)', linewidth=2)
axs[j].set_ylabel("$\\dot{q_r}$")
j += 1

# dC/dt
axs[j] = axs_plot[j]
inv_dC_dt = np.divide(1, dC_dt, out=np.full_like(dC_dt, np.nan), where=dC_dt != 0)
axs[j].plot(T, inv_dC_dt, label='Cost Derivative ($\\dot{C}$)', linewidth=2)
axs[j].set_ylim(-10, 300)
axs[j].axhline(utility, color='gray', linestyle='--')
axs[j].axhline(0, color='gray', linestyle='--')
axs[j].set_ylabel("$\\dot{C}$")
j += 1

# Efficient mode shading (grouped spans)
traveling = (mode == 1)
transitions = np.diff(traveling.astype(int))
start_idxs = np.where(transitions == 1)[0] + 1
end_idxs = np.where(transitions == -1)[0] + 1

if traveling[0]:
    start_idxs = np.insert(start_idxs, 0, 0)
if traveling[-1]:
    end_idxs = np.append(end_idxs, len(traveling) - 1)

for ax in axs:
    ax.set_xlim([-5, max_steps * timedelta])
    for start, end in zip(start_idxs, end_idxs):
        ax.axvspan(T[start], T[end], color='gray', alpha=0.1)
    ax.axvline(0, color='gray', linewidth=0.5)
    
print(time.time()-sttime)
plt.xlabel("Time (s)")
plt.tight_layout()
plt.show()
