# plotting.py
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def plot_simulation(time, q_p, q_c, profit, ind_profit, allresources, n, Tr):
    time = time / 60  # convert to minutes if needed
    n_plots = 4
    j = 1
    plt.figure(figsize=(12, 4 * n_plots))

    plt.subplot(n_plots, 1, j)
    for i in range(Tr):
        plt.plot(time, q_p[i], color=allresources[i].quality)
    plt.ylabel("Quantity $q_p$ (per patch)")
    j += 1

    plt.subplot(n_plots, 1, j)
    for i in range(Tr):
        plt.plot(time, q_c[i], color=allresources[i].quality)
    plt.ylabel("Quantity Collected (per patch)")
    j += 1

    plt.subplot(n_plots, 1, j)
    for i in range(Tr):
        plt.plot(time, profit[i], color=allresources[i].quality)
    plt.axhline(y=0, color='gray', linestyle='--')
    plt.ylabel("Profit (per patch)")
    j += 1

    plt.subplot(n_plots, 1, j)
    for i in range(n):
        plt.plot(time, ind_profit[i], label=f'Robot {i}')
    plt.axhline(y=0, color='gray', linestyle='--')
    plt.ylabel("Profit (per robot)")
    plt.legend()
    j += 1

    plt.tight_layout()
    plt.show()

def plot_marginal_costs(time, c_p, ind_mc, ind_at, allresources, Tr, n):
    plt.figure(figsize=(12, 4 * Tr))
    for j in range(Tr):
        resource = allresources[j]
        plt.subplot(Tr, 1, j + 1)
        for i in range(n):
            mask = (ind_mc[i] != 0) & (ind_at[i] == resource.id)
            plt.scatter(time[mask], ind_mc[i][mask], s=10)
        plt.axhline(y=resource.utility, color='gray', linestyle='--')
        plt.text(-0.06, 0.5, f'{resource.quality} patch',
                 va='center', ha='center', rotation='vertical',
                 transform=plt.gca().transAxes, fontweight='bold')
        c_p_ema = pd.Series(c_p[j]).ewm(span=20, adjust=False).mean()
        plt.plot(time, c_p_ema, color='gray')
    plt.tight_layout()
    plt.show()
