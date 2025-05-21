import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
import time
import random

sttime = time.time()

# --------------------------
# Parameters
# --------------------------
timedelta = 0.1
max_steps = 15000
n = 5

# ct                    (higher -> more resources)
travel_cost = 30
travel_var  = 0

# Qmax and R            (higher -> more resources)
initial_quantity = 300
regen_rate = 3

# c0 and c1             (higher -> more resources)
foraging_rate =  0.25
foraging_slope = 0.075

# c3
robot_slope = 0
max_carry = 30
utility = 250

# --------------------------
# Derived Parameters
# --------------------------
R = regen_rate
c0 = foraging_rate
c1 = foraging_slope
c3 = robot_slope
Qm = initial_quantity

# --------------------------
# Initial state
# --------------------------
q_r0 = np.zeros(n)
q_p0 = Qm
C0 = c0 + c1*(Qm - q_p0) + c3*q_r0     
r0 = 1.0 / C0                         
y0 = np.concatenate([q_r0, [q_p0], r0])

# --------------------------
# Mode variables
# --------------------------
mode           = np.zeros(n, dtype=int)  # 0=foraging, 1=traveling
last_reset     = np.zeros(n)             # foraging start time
travel_end     = {}                      # i -> end time of travel

# --------------------------
# ODE System
# --------------------------
def system(t, y):
    q_r = y[:n]
    q_p = y[n]
    r   = y[n+1:]
    s   = 1 - mode

    # 1) Forage dynamics
    dq_r = s * r

    # 2) Patch dynamics
    dq_p = R - np.sum(dq_r)

    if q_p >= Qm and dq_p>0:
        dq_p = 0.0
        dq_r[:] = 0.0

    if q_p <= 0 and dq_p<0:
        dq_p = 0.0
        dq_r[:] = 0.0

    # 3) Forage rate dynamics
    dr_all    = r**2 * (c1*(R - np.dot(s, r)) - c3*r)     
    dr         = s * dr_all          

    return np.concatenate([dq_r, [dq_p], dr])

# --------------------------
# Events
# --------------------------
def make_event_carry(i, eps=1e-6):
    threshold = max_carry + i*eps
    def event(t, y):
        return y[i] - threshold
    event.terminal = True
    event.direction = 1
    return event

def make_event_utility(i):
    def event(t, y):
        r_i = y[n+1+i]
        # trigger when C_i = 1/r_i = utility_thresh => r_i = 1/utility_thresh
        return r_i - 1/utility_thresh
    event.terminal = True
    event.direction = 1
    return event

def make_event_travel_end(i):
    def event(t, y):
        return t - travel_end.get(i, np.inf)
    event.terminal = True
    event.direction = 1
    return event

def handle_event(et, i, t, y):
    global mode, last_reset, travel_end

    if et in ('carry','utility'):
        # start traveling
        mode[i] = 1
        travel_end[i] = t + travel_cost + random.randint(0, travel_var)
        y[i]       = 0.0      # reset carried resource
        y[n+1+i]   = 0.0      # zero out rate while traveling

    elif et == 'travel_end':
        mode[i] = 0
        last_reset[i] = t
        # reset rate based on current patch stock
        qp = y[n]
        y[n+1+i] = 1.0 / (c0 + c1*(Qm - qp))
        travel_end.pop(i)

    return y

# --------------------------
# Integration
# --------------------------
t0, tf = 0.0, max_steps*timedelta
t_cur, y_cur = t0, y0.copy()

T_segs, Y_segs = [], []
D_segs = []

while t_cur < tf:

    # Build exactly one event per robot:
    events     = []
    event_info = []

    for i in range(n):
        if mode[i] == 0:
            # robot i is foraging → watch for carry limit
            events.append(make_event_carry(i))
            event_info.append(('carry', i))
        else:
            # robot i is traveling → watch for travel end
            events.append(make_event_travel_end(i))
            event_info.append(('travel_end', i))
    
    # print(f"[DEBUG] t={t_cur:.1f}, mode={mode}, events for i={event_info}")

    sol = solve_ivp(system, [t_cur, tf], y_cur, events=events,
                    max_step=timedelta, rtol=1e-3, atol=1e-5)

    T_segs.append(sol.t)
    Y_segs.append(sol.y)
    D_segment = np.zeros_like(sol.y)
    for k in range(sol.t.size):
        D_segment[:, k] = system(sol.t[k], sol.y[:, k])
    D_segs.append(D_segment)

    # If no event triggered, we’re done
    if not any(len(ev) for ev in sol.t_events):
        break

    # Otherwise, find which event fired first
    for k, ev in enumerate(sol.t_events):
        if len(ev):
            event_time = ev[0]
            etype, i = event_info[k]
            y_event = sol.y_events[k][0]
            break

    # 7) Restart integrator from that point
    t_cur  = event_time
    y_cur  = handle_event(etype, i, event_time, y_event)

# concatenate
T = np.hstack(T_segs)
Y = np.hstack(Y_segs)
D = np.hstack(D_segs)

# Extract and plot
q_r = Y[:n]
q_p = Y[n]
r   = Y[n+1:]

dq_r_dt = D[:n, :]
dq_p_dt = D[n, :]
dr_dt   = D[n+1:, :]

# --------------------------
# Plotting
# --------------------------
n_plots = 6
axs = [0] * n_plots  # pre-allocate list
j = 0

fig, axs_plot = plt.subplots(n_plots, 1, figsize=(12, 4 * n_plots), sharex=True)

# q_p
axs[j] = axs_plot[j]
axs[j].plot(T, q_p, label='$q_p$', linewidth=2)
axs[j].axhline(Qm, color='gray', linestyle='--', label='Patch Capacity ($Q_m$)')
axs[j].set_ylabel("$q_p$")
axs[j].set_ylim(bottom=0)
j += 1

# q_r
axs[j] = axs_plot[j]
for i in range(n):
    axs[j].plot(T, q_r[i], label='$q_{r,i}$', linewidth=2)
axs[j].axhline(max_carry, color='gray', linestyle='--', label='Carry Capacity')
axs[j].set_ylabel("$q_r$")
axs[j].set_ylim(bottom=0)
j += 1

# C
axs[j] = axs_plot[j]
for i in range(n):
    axs[j].plot(T, r[i], label='$r_{i}$', linewidth=2)
axs[j].set_ylabel("$r$")
axs[j].set_ylim(bottom=0)
j += 1

# dq_p_dt
axs[j] = axs_plot[j]
axs[j].plot(T, dq_p_dt, label='$\\dot{q_p}$', linewidth=2)
axs[j].set_ylabel("$\\dot{q_p}$")
j += 1

# dq_r_dt
axs[j] = axs_plot[j]
for i in range(n):
    axs[j].plot(T, dq_r_dt[i], label='$\\dot{q_r}$', linewidth=2)
axs[j].set_ylabel("$\\dot{q_r}$")
j += 1

# dC/dt
axs[j] = axs_plot[j]
for i in range(n):
    axs[j].plot(T, dr_dt[i], label='$\\dot{r}$', linewidth=2)
# axs[j].set_ylim(-10, 300)
# axs[j].axhline(utility, color='gray', linestyle='--')
# axs[j].axhline(0, color='gray', linestyle='--')
axs[j].set_ylabel("$\\dot{r}$")
j += 1

# # Efficient mode shading (grouped spans)
# traveling = (mode == 1)
# transitions = np.diff(traveling.astype(int))
# start_idxs = np.where(transitions == 1)[0] + 1
# end_idxs = np.where(transitions == -1)[0] + 1

# if traveling[0]:
#     start_idxs = np.insert(start_idxs, 0, 0)
# if traveling[-1]:
#     end_idxs = np.append(end_idxs, len(traveling) - 1)

# for ax in axs:
#     ax.set_xlim([-5, max_steps * timedelta])
#     for start, end in zip(start_idxs, end_idxs):
#         ax.axvspan(T[start], T[end], color='gray', alpha=0.1)
#     ax.axvline(0, color='gray', linewidth=0.5)
    
print(time.time()-sttime)
plt.xlabel("Time (s)")
plt.tight_layout()
plt.show()

