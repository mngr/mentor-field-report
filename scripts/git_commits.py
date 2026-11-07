#!/usr/bin/env python3
"""Classify Mentor's commits by who initiated them, from git subjects only.

Usage: python3 git_commits.py <path-to-mentor-checkout> [out_dir]

Classification mirrors Mentor's own `backlogProgress` (src/strategy.ts):
  curator:/strategist:/doctor:/sdk:/records:  -> harness loop (self-initiated)
  fix(...)/feat(...)/... and everything else  -> human-initiated or unattributed
Nearly every commit is *written* by an agent (Co-Authored-By trailer); the split is
about who started the change, which is what the paper reports.
Writes data/commits.csv (one row per commit) and data/commit_summary.json.
"""
import csv, json, re, subprocess, sys, collections, datetime as dt
from pathlib import Path

LOOPS = ['curator', 'strategist', 'doctor', 'sdk', 'records']
repo = Path(sys.argv[1])
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / 'data'
out.mkdir(parents=True, exist_ok=True)

raw = subprocess.run(['git', '-C', str(repo), 'log', '--no-merges', '--format=%H%x09%aI%x09%s%x09%(trailers:key=Co-Authored-By,valueonly,separator=;)'],
                     capture_output=True, text=True, check=True).stdout
merges = int(subprocess.run(['git', '-C', str(repo), 'rev-list', '--merges', '--count', 'HEAD'], capture_output=True, text=True).stdout.strip() or 0)
rows = []
for line in raw.splitlines():
    h, date, subj, coauth = (line.split('\t') + ['', '', '', ''])[:4]
    m = re.match(r'^([A-Za-z0-9_-]+)[:(]', subj)
    prefix = m.group(1) if m else ''
    kind = prefix if prefix in LOOPS else ('human-conventional' if prefix in ('feat', 'fix', 'perf', 'config', 'docs', 'test', 'tests', 'chore') else 'other')
    rows.append({'sha': h[:10], 'date': date[:10], 'kind': kind, 'loop': kind in LOOPS, 'agent_coauthored': bool(coauth.strip())})
rows.sort(key=lambda r: r['date'])
with open(out / 'commits.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

last = max(r['date'] for r in rows)
cut30 = (dt.date.fromisoformat(last) - dt.timedelta(days=30)).isoformat()
def share(rs):
    n = len(rs); k = sum(r['loop'] for r in rs); return {'commits': n, 'loop': k, 'share': round(k / n, 4) if n else None}
summary = {
    'first_commit': rows[0]['date'], 'last_commit': last, 'merge_commits_excluded': merges,
    'all': share(rows), 'last_30_days': {**share([r for r in rows if r['date'] > cut30]), 'from': cut30},
    'by_kind': collections.Counter(r['kind'] for r in rows),
    'agent_coauthored': sum(r['agent_coauthored'] for r in rows),
    'first_loop_commit': {k: min((r['date'] for r in rows if r['kind'] == k), default=None) for k in LOOPS},
}
(out / 'commit_summary.json').write_text(json.dumps(summary, indent=2, default=dict))
print(json.dumps(summary, indent=2, default=dict))
