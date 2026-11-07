#!/usr/bin/env python3
"""Derive the paper's run-time numbers from a daemon export (scripts/export-for-paper.ts), and write ONLY
sanitised aggregates into data/ (the raw export holds ticket keys, names and an email address and stays out of git).

Usage: python3 export_metrics.py <path-to-paper-export>
Writes data/runtime_summary.json, data/weekly_all.csv, data/weekly_by_size.csv, data/decisions_by_week.csv,
and fig_weekly_metrics.pdf/.png.
"""
import csv, json, sys, collections, datetime as dt
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

E = Path(sys.argv[1]); HERE = Path(__file__).parent; DATA = HERE / 'data'; DATA.mkdir(exist_ok=True)
T2_FIX = '2026-10-09T11:27:27Z'      # commit "product questions are labelled as such ..." (harness git)
rd = lambda f: list(csv.DictReader(open(E / f)))
num = lambda v: float(v) if v not in ('', None) else None

# Weekly rows: eight contiguous 7-day windows ending 19 Sep ... 7 Nov 00:00Z. The export's loop wrote the last
# week twice (once ending 7 Nov 00:00Z, once clipped to 7 Nov 23:59Z); keep the first, which keeps windows contiguous.
W = rd('weekly_scorecard.csv'); seen = set(); weekly = []
for r in W:
    k = (r['week_end'], r['size'])
    if k in seen: continue
    seen.add(k); weekly.append(r)
ALL = [r for r in weekly if r['size'] == 'ALL']; SIZES = ['Small', 'Medium', 'Large', 'Extra large']
assert len(ALL) == 8, len(ALL)

def period(rows):
    d = sum(int(r['delivered']) for r in rows); i = sum(int(r['interventions']) for r in rows)
    h = sum(num(r['agent_hours']) or 0 for r in rows); lost = sum((num(r['agent_hours']) or 0) * (num(r['lost_share']) or 0) / 100 for r in rows)
    usd = sum(num(r['usd']) or 0 for r in rows); pts = sum(num(r['delivered_points']) or 0 for r in rows)
    return {'delivered': d, 'interventions': i, 'per_delivered': round(i / d, 2), 'per_point': round(i / pts, 2), 'points': pts,
            'agent_hours': round(h, 1), 'lost_share': round(100 * lost / h, 1), 'usd_per_delivered': round(usd / d)}
first, last = period(ALL[:4]), period(ALL[4:])
by_size = {}
for s in SIZES:
    rs = [r for r in weekly if r['size'] == s]
    f = [r for r in rs if r['week_end'] <= ALL[3]['week_end']]; l = [r for r in rs if r['week_end'] > ALL[3]['week_end']]
    agg = lambda x: {'delivered': sum(int(r['delivered']) for r in x), 'interventions': sum(int(r['interventions']) for r in x)}
    by_size[s] = {'first4': agg(f), 'last4': agg(l)}

S = json.load(open(E / 'scorecard_whole_window.json'))
whole = {k: S[k] for k in ('days', 'delivered', 'interventionsPerDelivered', 'hours', 'usd', 'usdPerDelivered', 'leadHoursMedian', 'lostShare', 'deliveredPoints', 'interventionsPerPoint')}
whole['interventions'] = len(S['interventions'])
whole['bySize'] = S['bySize']
whole['restarts'] = {k: S['restarts'][k] for k in ('count', 'drainHours', 'paused', 'drained')}
whole['rebaseLaps'] = S['rebaseLaps']
whole['byStep_share'] = {b['key']: b['share'] for b in S['byStep']}
whole['top_losses'] = [{'key': b['key'], 'hours': b['hours'], 'share': b['share']} for b in S['losses'][:6]]
whole['trips'] = S['trips']
q = S['quota']; whole['harness_agents'] = {'issueUsd': q['issueUsd'], 'harnessUsd': q['harnessUsd'], 'harnessShare': q['harnessShare'],
    'quotaStopHours': q.get('stopHours'), 'byAgent': [{'agent': a['agent'], 'runs': a['runs'], 'usd': a['usd']} for a in q['byAgent']]}

I = rd('interventions.csv')
interv = {'total': len(I), 'by_kind': collections.Counter(i['kind'] for i in I), 'answers_to_mentor': sum(i['answer'] == 'true' for i in I),
          'issue_tied': sum(1 for i in I if i['issue']), 'distinct_issues': len({i['issue'] for i in I if i['issue']}),
          'by_size': collections.Counter(i['size'] or '(harness repair, no issue)' for i in I)}
D = rd('decisions.csv')
def tiers(xs): return {'n': len(xs), 'tier': collections.Counter(x['tier'] for x in xs), 'decided_by': collections.Counter(x['decided_by'] for x in xs)}
dec = {'total': len(D), 'before_t2_fix': tiers([x for x in D if x['ts'] < T2_FIX]), 'after_t2_fix': tiers([x for x in D if x['ts'] >= T2_FIX])}
B = rd('bets.csv')
bets = {'total': len(B), 'by_kind_status': {f'{k}/{s}': n for (k, s), n in collections.Counter((b['kind'], b['status']) for b in B).items()}}
Ss = rd('sessions.csv'); IS = rd('issues.csv')
sess = {'sessions': len(Ss), 'failed': sum(s['ok'] == 'false' for s in Ss), 'issue_records': len(IS), 'issue_sizes': collections.Counter(i['size'] for i in IS)}
summary = {'source': 'daemon export of 2026-11-07 (scripts/export-for-paper.ts); weekly windows end 00:00Z, whole window to 23:59Z',
           'first4_weeks': first, 'last4_weeks': last, 'by_size_periods': by_size, 'whole_window': whole,
           'interventions': interv, 'decisions': dec, 'bets': bets, 'sessions': sess}
(DATA / 'runtime_summary.json').write_text(json.dumps(summary, indent=2, default=dict))

cols = ['week_end', 'delivered', 'interventions', 'per_delivered', 'per_point', 'lead_h_median', 'lost_share', 'usd_per_delivered', 'agent_hours', 'delivered_points', 'restarts']
with open(DATA / 'weekly_all.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader(); [w.writerow(r) for r in ALL]
with open(DATA / 'weekly_by_size.csv', 'w', newline='') as f:
    c2 = ['week_end', 'size', 'delivered', 'interventions', 'per_delivered', 'lead_h_median', 'lost_share', 'usd_per_delivered', 'agent_hours']
    w = csv.DictWriter(f, fieldnames=c2, extrasaction='ignore'); w.writeheader(); [w.writerow(r) for r in weekly if r['size'] != 'ALL']
wk = collections.defaultdict(collections.Counter)
for x in D:
    d0 = dt.date.fromisoformat(x['ts'][:10]); wk[(d0 - dt.timedelta(days=d0.weekday())).isoformat()][x['tier']] += 1
with open(DATA / 'decisions_by_week.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['week_start', 'T0', 'T1', 'T2', 'T3'])
    for k in sorted(wk): w.writerow([k] + [wk[k][t] for t in ('T0', 'T1', 'T2', 'T3')])

# Figure: three small multiples, one measure each (no dual axis).
INK2 = '#52514e'
plt.rcParams.update({'font.family': 'serif', 'font.size': 7.5, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'pdf.fonttype': 42})
x = range(8); lab = [(dt.date.fromisoformat(r['week_end']) - dt.timedelta(days=7)).strftime('%d %b') for r in ALL]
fig, ax = plt.subplots(3, 1, figsize=(3.4, 3.7), sharex=True, gridspec_kw={'hspace': 0.28})
series = [('per_delivered', 'interventions\nper delivered', '#2a78d6'), ('lost_share', 'agent time\nlost, %', '#eb6834'), ('usd_per_delivered', 'model cost per\ndelivered, $', '#1baf7a')]
for a, (k, t, c) in zip(ax, series):
    v = [num(r[k]) for r in ALL]
    a.plot(x, v, color=c, linewidth=1.6, marker='o', markersize=3); a.set_ylabel(t, fontsize=7); a.set_ylim(0, max(v) * 1.18)
    a.grid(axis='y', color='#e4e3df', linewidth=0.5)
    for i in (0, 7): a.annotate(f'{v[i]:g}', (i, v[i]), xytext=(0, 4), textcoords='offset points', ha='center', fontsize=6.5)
ax[-1].set_xticks(list(x)); ax[-1].set_xticklabels(lab, rotation=45, ha='right', fontsize=6.5); ax[-1].set_xlabel('week starting (2026)')
for a in ax: a.axvline(3.5, color='#b9b8b2', linewidth=0.8, linestyle=':')
fig.savefig(HERE / 'fig_weekly_metrics.pdf', bbox_inches='tight'); fig.savefig(HERE / 'fig_weekly_metrics.png', dpi=200, bbox_inches='tight')
print(json.dumps({k: summary[k] for k in ('first4_weeks', 'last4_weeks', 'by_size_periods', 'decisions', 'bets', 'interventions', 'sessions')}, indent=1, default=dict))
