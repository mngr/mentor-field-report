#!/usr/bin/env python3
"""Make the paper's git-derived figures.

Usage: python3 make_figures.py <path-to-mentor-checkout>
Needs data/commits.csv from git_commits.py. Writes fig_commit_share.pdf and fig_backlog_edits.pdf
next to this script, plus data/backlog_edits.csv.
"""
import csv, subprocess, sys, collections, datetime as dt
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).parent; DATA = HERE / 'data'
repo = Path(sys.argv[1])
INK, INK2, SURF = '#0b0b0b', '#52514e', '#fcfcfb'
C = {'curator': '#2a78d6', 'strategist': '#eb6834', 'upkeep': '#1baf7a', 'human': '#b9b8b2'}
plt.rcParams.update({'font.family': 'serif', 'font.size': 8, 'axes.edgecolor': INK2, 'axes.labelcolor': INK,
                     'xtick.color': INK2, 'ytick.color': INK2, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': 'white', 'axes.facecolor': 'white', 'pdf.fonttype': 42})

rows = list(csv.DictReader(open(DATA / 'commits.csv')))
def week(d):  # ISO week start (Monday)
    x = dt.date.fromisoformat(d); return x - dt.timedelta(days=x.weekday())
group = lambda k: 'curator' if k == 'curator' else 'strategist' if k == 'strategist' else 'upkeep' if k in ('doctor', 'sdk', 'records') else 'human'
W = collections.defaultdict(collections.Counter)
for r in rows: W[week(r['date'])][group(r['kind'])] += 1
weeks = sorted(W)
labels = {'curator': 'curator (lessons)', 'strategist': 'strategist (daily review, backlog steps)',
          'upkeep': 'doctor, SDK update, records', 'human': 'human-initiated or unattributed'}

fig, (a1, a2) = plt.subplots(2, 1, figsize=(3.4, 3.6), sharex=True, gridspec_kw={'height_ratios': [2.2, 1], 'hspace': 0.12})
x = range(len(weeks)); bottom = [0] * len(weeks)
for k in ('curator', 'strategist', 'upkeep', 'human'):
    v = [W[w][k] for w in weeks]
    a1.bar(x, v, bottom=bottom, color=C[k], width=0.72, label=labels[k], edgecolor='white', linewidth=0.8)
    bottom = [b + y for b, y in zip(bottom, v)]
a1.set_ylabel('commits per week'); a1.set_ylim(0, 420); a1.legend(frameon=False, fontsize=6.2, loc='upper left', ncol=2, columnspacing=0.8, handlelength=1.2)
a1.grid(axis='y', color='#e4e3df', linewidth=0.5); a1.set_axisbelow(True)
share = [100 * sum(W[w][k] for k in ('curator', 'strategist', 'upkeep')) / sum(W[w].values()) for w in weeks]
a2.plot(x, share, color=INK, linewidth=1.5, marker='o', markersize=3)
a2.set_ylim(0, 100); a2.set_ylabel('loop share, %'); a2.grid(axis='y', color='#e4e3df', linewidth=0.5)
a2.set_xticks(list(x)); a2.set_xticklabels([w.strftime('%d %b') for w in weeks], rotation=45, ha='right', fontsize=6.5)
a2.set_xlabel('week starting (2026)')
fig.savefig(HERE / 'fig_commit_share.pdf', bbox_inches='tight'); fig.savefig(HERE / 'fig_commit_share.png', dpi=200, bbox_inches='tight')

# Backlog-file edits per day (the 2026-10-09 runaway)
out = subprocess.run(['git', '-C', str(repo), 'log', '--format=%ad', '--date=short', '--', 'algorithm/harness-backlog.md'],
                     capture_output=True, text=True, check=True).stdout.split()
B = collections.Counter(out)
first, last = dt.date.fromisoformat(min(B)), dt.date.fromisoformat(max(r['date'] for r in rows))
days = [first + dt.timedelta(days=i) for i in range((last - first).days + 1)]
with open(DATA / 'backlog_edits.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['date', 'commits_touching_backlog']); [w.writerow([d.isoformat(), B.get(d.isoformat(), 0)]) for d in days]
fig, ax = plt.subplots(figsize=(3.4, 1.7))
v = [B.get(d.isoformat(), 0) for d in days]
ax.bar(range(len(days)), v, color=[C['strategist'] if d.isoformat() == '2026-10-09' else '#9ec5f4' for d in days], width=0.8)
i = [d.isoformat() for d in days].index('2026-10-09') if '2026-10-09' in B else None
if i is not None: ax.annotate(f'{B["2026-10-09"]} edits on 9 Oct', (i, B['2026-10-09']), xytext=(i + 4, B['2026-10-09'] * 0.85), fontsize=6.5, color=INK, arrowprops={'arrowstyle': '-', 'color': INK2, 'lw': 0.6})
ticks = [k for k, d in enumerate(days) if d.weekday() == 0]
ax.set_xticks(ticks); ax.set_xticklabels([days[k].strftime('%d %b') for k in ticks], rotation=45, ha='right', fontsize=6.5)
ax.set_ylabel('commits touching\nthe backlog file'); ax.grid(axis='y', color='#e4e3df', linewidth=0.5); ax.set_axisbelow(True)
fig.savefig(HERE / 'fig_backlog_edits.pdf', bbox_inches='tight'); fig.savefig(HERE / 'fig_backlog_edits.png', dpi=200, bbox_inches='tight')
print('weeks', [(w.isoformat(), dict(W[w]), round(s)) for w, s in zip(weeks, share)])
