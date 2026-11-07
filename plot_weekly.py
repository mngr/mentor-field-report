#!/usr/bin/env python3
"""Redraw the weekly north-star figure from data/weekly_all.csv. Run: python3 plot_weekly.py  (needs matplotlib)"""
import csv, datetime as dt
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).parent; W = list(csv.DictReader(open(HERE / 'data' / 'weekly_all.csv')))
series = [('per_delivered', 'interventions\nper delivered', '#2a78d6'), ('lost_share', 'agent time\nlost, %', '#eb6834'),
          ('usd_per_delivered', 'reference cost per\ndelivered, $', '#1baf7a')]
series = [s for s in series if s[0] in W[0]]          # cost is present only when its release is cleared
plt.rcParams.update({'font.family': 'serif', 'font.size': 7.5, 'axes.spines.top': False, 'axes.spines.right': False})
fig, ax = plt.subplots(len(series), 1, figsize=(3.4, 1.25 * len(series) + 0.6), sharex=True)
x = range(len(W)); lab = [(dt.date.fromisoformat(r['week_end']) - dt.timedelta(days=7)).strftime('%d %b') for r in W]
for a, (k, t, c) in zip(ax, series):
    v = [float(r[k]) for r in W]
    a.plot(x, v, color=c, linewidth=1.6, marker='o', markersize=3); a.set_ylabel(t, fontsize=7); a.set_ylim(0, max(v) * 1.18)
    a.grid(axis='y', color='#e4e3df', linewidth=0.5); a.axvline(3.5, color='#b9b8b2', linewidth=0.8, linestyle=':')
ax[-1].set_xticks(list(x)); ax[-1].set_xticklabels(lab, rotation=45, ha='right', fontsize=6.5); ax[-1].set_xlabel('week starting (2026)')
(HERE / 'figures').mkdir(exist_ok=True)
fig.savefig(HERE / 'figures' / 'fig_weekly_metrics.pdf', bbox_inches='tight'); fig.savefig(HERE / 'figures' / 'fig_weekly_metrics.png', dpi=200, bbox_inches='tight')
print('wrote figures/fig_weekly_metrics.pdf')
