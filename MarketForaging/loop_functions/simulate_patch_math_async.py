import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
import time
import random
# --------------------------
# Parameters
# --------------------------
timedelta = 0.1
max_steps = 3000
n = 3

# ct                    (higher -> more resources)
travel_cost = 30
travel_var  = 0

# Qmax and R            (higher -> more resources)
initial_quantity = 300
regen_rate = 1.1

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
# Initial Conditions
# --------------------------
q_r0 = np.zeros(n)
q_p0 = Qm
C0 = c0 + c1*(Qm - q_p0) + c3*q_r0
y0 = np.concatenate([q_r0, [q_p0], C0])

# --------------------------
# Simulation variables
# --------------------------
mode = np.zeros(n, dtype=int)  # 0 = foraging, 1 = traveling
last_reset = np.zeros(n)       # time when each robot started current foraging
travel_end_times = {}          # robot_index -> end time of travel

# --------------------------
# System of ODEs
# --------------------------
def system(t, y):
    q_r = y[:n]         # shape (n,)
    q_p = y[n]
    C   = y[n+1:]       # shape (n,)

    # # already have C from state; recompute to be safe:
    # C = c0 + c1*(Qm - q_p) + c3*q_r

    t_rel = t - last_reset  # if you are using relative time
    if np.isscalar(t_rel):
        t_rel = np.full(n, t_rel)  # make sure it's an array


    # 1) assemble A matrix and b vector
    A = np.zeros((n, n))
    b = np.zeros(n)

    for i in range(n):
        if mode[i] == 0: 
            A[i, i] = C[i] + (c3 - c1) * t_rel[i] / C[i]
            for j in range(n):
                if j != i and mode[j] == 0:
                    A[i, j] = -(c1 * t_rel[i]) / C[i]
            b[i] = 1 + (c1 * R * t_rel[i]) / C[i]

        else: 
            A[i, :] = 0.0
            A[i, i] = 1.0
            b[i]    = 0.0

    # 2) solve for dq_r
    dq_r = np.linalg.solve(A, b)

    for i in range(n):
        if mode[i] == 1:
            dq_r[i] = 0.0

    # # 3) enforce availability cap
    # cap = max(q_p, 0.0)

    # # proportional scaling if over demand
    # total_demand = np.sum(dq_r) * timedelta
    # if total_demand > cap and total_demand > 0:
    #     dq_r *= cap / total_demand


    # 5) compute dq_p
    dq_p = R - np.sum(dq_r)

    if q_p >= Qm and dq_p > 0:
        dq_p = 0.0

    if q_p <= 0.0 and dq_p < 0:
        dq_r[:] = 0.0
        dq_p = 0.0

    # 6) compute dC
    dC = np.zeros(n)
    for i in range(n):
        if mode[i] == 0:
            dC[i] = c3 * dq_r[i] - c1 * dq_p
        else:
            dC[i] = - c1 * dq_p

        # if dC[i] < 0 or dC[i] < 1/utility:
        #     dC[i] = 0.0

    return np.concatenate([dq_r, [dq_p], dC])

# --------------------------
# Event factories
# --------------------------
def make_event_carry(i):
    def event(t, y):
        return y[i] - max_carry
    event.terminal = True
    event.direction = 1
    return event

# Updated utility event uses full system derivative to get dC_i
def make_event_utility(i):
    def event(t, y):
        # compute current derivative vector
        deriv = system(t, y)
        # dC_i is at index n+1+i
        dC_i = deriv[n+1+i]
        if dC_i <= 0:
            return -np.inf
        inv_dC = 1 / dC_i
        return inv_dC - utility
    event.terminal = True
    event.direction = 1
    return event

def make_event_travel_end(i):
    def event(t, y):
        return t - travel_end_times.get(i, np.inf)
    event.terminal = True
    event.direction = 1
    return event

def handle_event(event_type, i, event_time, y_event):
    global mode, last_reset, travel_end_times

    if event_type in ('carry', 'utility'):
        mode[i] = 1
        travel_end_times[i] = event_time + travel_cost + random.randint(0, travel_var)
        y_event[i] = 0.0
        y_event[n+1+i] = 0.0

    elif event_type == 'travel_end':
        mode[i] = 0
        last_reset[i] = event_time  # Important for t_rel!
        qp = y_event[n]
        y_event[n+1+i] = c0 + c1*(Qm - qp)
        travel_end_times.pop(i, None)

    else:
        raise ValueError(f"Unknown event type {event_type}")

    return y_event

# -----------------------
# INTEGRATION LOOP
# -----------------------
sttime = time.time()

t0, tf = 0.0, max_steps * timedelta
current_time = t0
current_state = y0.copy()

T_segments = []
Y_segments = []
D_segments = []

while current_time < tf:
    # Build event list
    events = []
    event_info = []
    for i in range(n):
        if mode[i] == 0:
            events.append(make_event_carry(i)); event_info.append(('carry', i))
        else:
            events.append(make_event_travel_end(i)); event_info.append(('travel_end', i))

    # Solve until the next event
    sol = solve_ivp(
        system,
        [current_time, tf],
        current_state,
        events=events,
        max_step=timedelta,
        rtol=1e-3,
        atol=1e-5
    )

    # Save segment
    T_segments.append(sol.t)
    Y_segments.append(sol.y)

    D_segment = np.zeros_like(sol.y)
    for k in range(sol.t.size):
        D_segment[:, k] = system(sol.t[k], sol.y[:, k])
    D_segments.append(D_segment)

    # No events triggered: stop
    if not any(len(ev) for ev in sol.t_events):
        break

    # Find first event that occurred
    for k, te in enumerate(sol.t_events):
        if len(te) > 0:
            event_time = te[0]
            event_type, i = event_info[k]
            y_event = sol.y_events[k][0]
            break

    # --- Process event ---
    y_event = handle_event(event_type, i, event_time, y_event)

    # Restart from event time with updated state
    current_time = event_time
    current_state = y_event.copy()


# concatenate results
T = np.hstack(T_segments)
Y = np.hstack(Y_segments)
D = np.hstack(D_segments)

# extract variables
q_r = Y[:n, :]
q_p = Y[n, :]
C = Y[n+1:, :]

dq_r_dt = D[:n, :]
dq_p_dt = D[n, :]
dC_dt   = D[n+1:, :]

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
    axs[j].plot(T, C[i], label='$C_{i}$', linewidth=2)
axs[j].set_ylabel("$C$")
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
    dC_dt_i = dC_dt[i]
    inv_dC_dt = np.divide(1, dC_dt_i, out=np.full_like(dC_dt_i, np.nan), where=dC_dt_i != 0)
    axs[j].plot(T, inv_dC_dt, label='$\\dot{C}$', linewidth=2)
# axs[j].set_ylim(-10, 300)
# axs[j].axhline(utility, color='gray', linestyle='--')
# axs[j].axhline(0, color='gray', linestyle='--')
axs[j].set_ylabel("$\\dot{C}$")
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

