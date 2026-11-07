#!/usr/bin/env python3
"""Summarise delivered issues from the evidence repo's hand-off notes (no client identifiers kept).

Usage: python3 handoffs.py <path-to-mentor-evidence checkout (handoff.md files suffice)> [out_dir]
Each <ISSUE>/handoff.md line 3 carries: links · kind · step / state — outcome · timestamp.
Writes data/handoffs.csv with an anonymised id (H01..), kind, outcome, date, ACs verified/total.
"""
import csv, json, re, sys, collections
from pathlib import Path

root = Path(sys.argv[1]); out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / 'data'
out.mkdir(parents=True, exist_ok=True)
rows = []
for f in sorted(root.glob('*/handoff.md')):
    text = f.read_text(errors='replace'); lines = text.splitlines()
    meta = lines[2] if len(lines) > 2 else ''
    kind = next((k for k in ('feature', 'improvement', 'bug') if f'· {k} ·' in meta), 'none')
    m = re.search(r'· ([a-z-]+) / ([a-z]+)( — ([^·]+))?(· (\d{4}-\d\d-\d\d))?', meta)
    step, state, outcome, date = (m.group(1), m.group(2), (m.group(4) or '').strip(), m.group(6)) if m else ('', '', '', None)
    if not date:
        d = re.search(r'(\d{4}-\d\d-\d\d) \d\d:\d\dZ', meta); date = d.group(1) if d else ''
    v = re.search(r'^## Verified[^\n]*?(\d+)/(\d+)', text, re.M)
    merged = 'merged' in outcome
    oc = 'merged' if merged else ('closed-already-done' if 'already' in outcome else (state or 'unknown'))
    rows.append({'kind': kind, 'final_step': step, 'outcome': oc, 'date': date,
                 'ac_verified': int(v.group(1)) if v else '', 'ac_total': int(v.group(2)) if v else '',
                 'words': len(text.split())})
rows.sort(key=lambda r: r['date'] or '9999')
for i, r in enumerate(rows, 1): r['id'] = f'H{i:02d}'
with open(out / 'handoffs.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['id', 'date', 'kind', 'final_step', 'outcome', 'ac_verified', 'ac_total', 'words']); w.writeheader(); w.writerows(rows)
acs = [r for r in rows if r['ac_total'] != '']
s = {'handoffs': len(rows), 'first': rows[0]['date'], 'last': max(r['date'] for r in rows if r['date']),
     'by_kind': collections.Counter(r['kind'] for r in rows), 'by_outcome': collections.Counter(r['outcome'] for r in rows),
     'with_ac_table': len(acs), 'ac_verified': sum(r['ac_verified'] for r in acs), 'ac_total': sum(r['ac_total'] for r in acs),
     'all_ac_green': sum(r['ac_verified'] == r['ac_total'] for r in acs)}
(out / 'handoff_summary.json').write_text(json.dumps(s, indent=2)); print(json.dumps(s, indent=2))
