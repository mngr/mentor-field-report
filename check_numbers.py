#!/usr/bin/env python3
"""Recompute the numbers the paper quotes, from data/ only. Run: python3 check_numbers.py"""
import csv, json, statistics
from pathlib import Path

D = Path(__file__).parent / 'data'
rows = lambda f: list(csv.DictReader(open(D / f)))
fl = lambda v: float(v) if v not in ('', None) else 0.0

print('== Who started the harness commits (non-merge)')
c = rows('commits.csv'); loop = [r for r in c if r['loop'] == 'True']
last = max(r['date'] for r in c); s = json.load(open(D / 'commit_summary.json'))
print(f"  all: {len(loop)} of {len(c)} ({100*len(loop)/len(c):.1f}%) started by loops")
print(f"  last 30 days (from {s['last_30_days']['from']}): {s['last_30_days']['loop']} of {s['last_30_days']['commits']} ({100*s['last_30_days']['share']:.1f}%)")
print(f"  agent co-author trailer: {sum(r['agent_coauthored'] == 'True' for r in c)} of {len(c)}")
print('  by loop:', {k: sum(r['kind'] == k for r in c) for k in ('curator', 'strategist', 'doctor', 'records', 'sdk')})

print('== Backlog runaway')
b = rows('backlog_edits.csv'); after = [int(r['commits_touching_backlog']) for r in b if r['date'] > '2026-10-09']
print(f"  9 Oct: {next(r['commits_touching_backlog'] for r in b if r['date'] == '2026-10-09')} commits; median over the {len(after)} days after: {statistics.median(after):g}")

print('== Hand-offs')
h = rows('handoffs.csv'); ac = [r for r in h if r['ac_total']]
print(f"  notes: {len(h)}; kinds: { {k: sum(r['kind'] == k for r in h) for k in ('bug', 'improvement', 'feature', 'none')} }")
print(f"  outcomes: { {k: sum(r['outcome'] == k for r in h) for k in sorted({r['outcome'] for r in h})} }")
print(f"  acceptance criteria verified: {sum(int(r['ac_verified']) for r in ac)} of {sum(int(r['ac_total']) for r in ac)} over {len(ac)} notes")

print('== The owner\'s load: weeks 1-4 vs 5-8 (harness scorecard)')
w = rows('weekly_all.csv'); assert len(w) == 8
def per(ws):
    d = sum(int(r['delivered']) for r in ws); i = sum(int(r['interventions']) for r in ws); p = sum(fl(r['delivered_points']) for r in ws)
    h = sum(fl(r['agent_hours']) for r in ws); lost = sum(fl(r['agent_hours']) * fl(r['lost_share']) / 100 for r in ws)
    return d, i, i / d, i / p, 100 * lost / h
for name, ws in (('weeks 1-4', w[:4]), ('weeks 5-8', w[4:])):
    d, i, pd, pp, ls = per(ws)
    print(f"  {name}: delivered {d}, interventions {i}, per delivered {pd:.2f}, per size point {pp:.2f}, agent time lost {ls:.1f}%")
ws = rows('weekly_by_size.csv'); cut = w[3]['week_end']
tied = {'first': [0, 0], 'last': [0, 0]}
for size in ('Small', 'Medium', 'Large', 'Extra large'):
    out = []
    for key, sel in (('first', lambda r: r['week_end'] <= cut), ('last', lambda r: r['week_end'] > cut)):
        rs = [r for r in ws if r['size'] == size and sel(r)]
        d = sum(int(r['delivered']) for r in rs); i = sum(int(r['interventions']) for r in rs)
        tied[key][0] += d; tied[key][1] += i; out.append(f"{i}/{d} = {i/d:.2f}" if d else f"{i}/0")
    print(f"  issue interventions per delivered, {size}: {out[0]} -> {out[1]}")
print(f"  all issue-tied: {tied['first'][1]/tied['first'][0]:.2f} -> {tied['last'][1]/tied['last'][0]:.2f}")
print(f"  harness repairs (total minus issue-tied): {per(w[:4])[1] - tied['first'][1]} -> {per(w[4:])[1] - tied['last'][1]}")

r = json.load(open(D / 'runtime_summary.json'))
ww = r['whole_window']
print('== Whole window')
print(f"  delivered {ww['delivered']}, interventions {ww['interventions']} {r['interventions']['by_kind']}, lead time median {ww['leadHoursMedian']} h, lost {ww['lostShare']}%")
print(f"  restarts {ww['restarts']['count']}, drain hours {ww['restarts']['drainHours']}; sessions {r['sessions']['sessions']}")
print('== Decisions before / after the 9 Oct routing fix')
for k in ('before_t2_fix', 'after_t2_fix'):
    x = r['decisions'][k]; g = x['decided_by'].get('gleb', 0)
    print(f"  {k}: n={x['n']}, tiers {x['tier']}, T2 share {100*x['tier'].get('T2', 0)/x['n']:.0f}%, decided by the owner {100*g/x['n']:.0f}%")
print('== Bets:', r['bets']['by_kind_status'])
if 'usdPerDelivered' in ww:
    print('== Model cost: REFERENCE values (SDK estimate at pay-as-you-go API prices; subscription, nothing billed)')
    def ref(ws): return sum(fl(x['usd']) for x in ws) / sum(int(x['delivered']) for x in ws)
    print(f"  per delivered issue: weeks 1-4 {ref(w[:4]):.0f}, weeks 5-8 {ref(w[4:]):.0f}, whole window {ww['usdPerDelivered']}")
    print('  by size:', {b['size']: b.get('usdPerDelivered') for b in ww['bySize']})
    print(f"  harness loops' share of all model use: {ww['harness_agents']['harnessShare']}%")
