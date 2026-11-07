// export-for-paper.ts: export the paper's run-time numbers from a Mentor daemon's state, anonymised.
//
// Run ON THE DAEMON MACHINE, from the mentor checkout (it imports mentor's own scorecard code so the
// numbers are the ones the harness itself reports):
//
//   cp <this file> <mentor>/scripts/export-for-paper.ts
//   cd <mentor> && npx tsx scripts/export-for-paper.ts ~/paper-export 2026-09-12 2026-11-07
//
// Read-only: it never writes under state/. To run against a copy instead: MENTOR_STATE_DIR=/path/to/state-copy.
// Output (CSV + JSON) holds no issue titles, no question text, no URLs, no client identifiers: issue keys
// are replaced by a salted hash, and the salt is NOT written out. Review the files before sharing anyway.
// Status: first run on the daemon machine on 7 Nov 2026 worked; it showed two leaks (free-text bet metrics, raw
// keys and an email in the scorecard JSON) and a duplicated last week, all fixed below but not re-run since.
// The activity-event names are the first word of a log line and are not guaranteed clean: check before sharing.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { STATE_DIR, ACTIVITY_LOG, DECISIONS_LOG } from '../src/config.ts';
import { loadIssues, buildScorecard, sizeOf } from '../src/scorecard.ts';
import { readUsage } from '../src/usage.ts';
import { loadStrategy } from '../src/strategy.ts';

const [outDir = 'paper-export', fromDay = '2026-09-12', toDay = new Date().toISOString().slice(0, 10)] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const salt = crypto.randomBytes(16).toString('hex');
const anon = (k?: string) => (k ? 'I' + crypto.createHash('sha256').update(salt + k).digest('hex').slice(0, 8) : '');
const csv = (file: string, rows: Record<string, unknown>[]) => {
  if (!rows.length) { fs.writeFileSync(path.join(outDir, file), ''); return; }
  const cols = Object.keys(rows[0]!);
  const q = (v: unknown) => { const s = v === undefined || v === null ? '' : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  fs.writeFileSync(path.join(outDir, file), [cols.join(','), ...rows.map((r) => cols.map((c) => q(r[c])).join(','))].join('\n') + '\n');
};

const issues = loadIssues(STATE_DIR);
const activity = fs.existsSync(ACTIVITY_LOG) ? fs.readFileSync(ACTIVITY_LOG, 'utf8') : '';
const harness = readUsage(0);
const fromMs = Date.parse(fromDay + 'T00:00:00Z'), toMs = Date.parse(toDay + 'T23:59:59Z');

// 1. Weekly scorecard, overall and by size: placeholders 1-4, 8 (the harness's own arithmetic, 7-day windows).
const weekly: Record<string, unknown>[] = [];
// Contiguous 7-day windows; the last one is clipped to toMs (first run of 7 Nov wrote the last week twice: fixed).
for (let end = fromMs + 7 * 864e5; end - 7 * 864e5 < toMs; end += 7 * 864e5) {
  const sc = buildScorecard(issues, activity, Math.min(end, toMs), 7, harness);
  const base = { week_end: new Date(Math.min(end, toMs)).toISOString().slice(0, 10) };
  weekly.push({ ...base, size: 'ALL', delivered: sc.delivered, interventions: sc.interventions.length, per_delivered: sc.interventionsPerDelivered,
    lead_h_median: sc.leadHoursMedian, lost_share: sc.lostShare, usd: sc.usd, usd_per_delivered: sc.usdPerDelivered, agent_hours: sc.hours,
    delivered_points: sc.deliveredPoints, per_point: sc.interventionsPerPoint, restarts: (sc.restarts as unknown as { count?: number })?.count ?? '' });
  for (const r of sc.bySize) weekly.push({ ...base, size: r.size, delivered: r.delivered, interventions: r.interventions, per_delivered: r.perDelivered,
    lead_h_median: r.leadHoursMedian, lost_share: r.lostShare, usd: '', usd_per_delivered: r.usdPerDelivered, agent_hours: r.hoursPerDelivered, delivered_points: '', per_point: '', restarts: '' });
}
csv('weekly_scorecard.csv', weekly);

// Whole-window scorecard (also kept as JSON: losses by bucket, trips, restarts, quota).
const days = Math.ceil((toMs - fromMs) / 864e5);
const whole = buildScorecard(issues, activity, toMs, days, harness);
// Sanitised: issue keys anywhere in the JSON are hashed, and quota warnings (they carry the account email) are dropped.
// (The first run of 7 Nov kept raw keys in quota.stops and an email in quota.warnings: fixed here.)
const scrub = (s: string) => s.replace(/\b[A-Z][A-Z0-9]+-\d+\b/g, (k) => anon(k));
const wholeOut = { ...whole, interventions: whole.interventions.map((i) => ({ at: i.at, kind: i.kind, issue: anon(i.issue), answer: !!i.answer })),
  quota: whole.quota ? { ...whole.quota, warnings: undefined } : undefined };
fs.writeFileSync(path.join(outDir, 'scorecard_whole_window.json'), scrub(JSON.stringify(wholeOut, null, 2)));

// 2. Interventions, one row each (kind and date only; the human's text is NOT exported).
const sizeByIssue = new Map(issues.map((s) => [s.issue, sizeOf(s)]));
csv('interventions.csv', whole.interventions.map((i) => ({ at: i.at, kind: i.kind, issue: anon(i.issue), size: i.issue ? sizeByIssue.get(i.issue) ?? '' : '', answer: !!i.answer })));

// 3. Per issue: size, kind, dates, sessions, hours, cost: placeholders 5, 9.
csv('issues.csv', issues.map((s) => {
  const ss = s.sessions ?? [];
  const hours = ss.reduce((t, x) => t + (x.endedAt ? (Date.parse(x.endedAt) - Date.parse(x.startedAt)) / 36e5 : 0), 0);
  return { issue: anon(s.issue), size: sizeOf(s), kind: (s.classification as unknown as { kind?: string })?.kind ?? '', status: s.status, step: s.step,
    created: s.createdAt, updated: s.updatedAt, sessions: ss.length, sessions_failed: ss.filter((x) => x.ok === false).length,
    agent_hours: hours.toFixed(2), usd: ss.reduce((t, x) => t + (x.costUsd ?? 0), 0).toFixed(2), rounds: s.round };
}));

// 4. Sessions (no ids, no transcripts): per step and role, for the "where the hours went" table.
csv('sessions.csv', issues.flatMap((s) => (s.sessions ?? []).map((x) => ({ issue: anon(s.issue), size: sizeOf(s), step: x.step, role: x.role, round: x.round,
  started: x.startedAt, ended: x.endedAt ?? '', usd: x.costUsd ?? '', model: x.model ?? '', turns: x.turns ?? '', ok: x.ok ?? '', terminal: x.terminalReason ?? '' }))));

// 5. Decisions by tier: placeholder 6 (question/rationale text NOT exported; criteria ids are harness-internal names).
const decisions = fs.existsSync(DECISIONS_LOG) ? fs.readFileSync(DECISIONS_LOG, 'utf8').split('\n').filter(Boolean).flatMap((l) => { try { return [JSON.parse(l)]; } catch { return []; } }) : [];
csv('decisions.csv', decisions.map((d) => ({ ts: d.ts, id: d.id, issue: anon(d.issue), step: d.step, kind: d.kind, tier: d.tier, route: d.route,
  decided_by: d.decidedBy, n_options: (d.options ?? []).length, n_criteria: (d.criteria ?? []).length, custom: !!d.customOption })));

// 6. Strategist bets: placeholder 7.
const ledger = loadStrategy();
// The metric is free text the strategist wrote (it can name issues and people), so it is NOT exported.
csv('bets.csv', ledger.bets.map((b) => { const r = b as unknown as Record<string, unknown>; return { id: r.id, at: r.at, kind: r.kind ?? 'review', bucket: r.bucket ?? '',
  baseline: r.baseline, target: r.target, review_on: r.reviewOn, status: r.status, fired: r.fired ?? '' }; }));

// 7. The harness's own agents' cost (curator, strategist, doctor, decider, ...), by day and agent.
const byDay = new Map<string, { day: string; agent: string; runs: number; usd: number; turns: number; failed: number }>();
for (const u of harness) {
  const k = `${u.at.slice(0, 10)}|${u.agent}`;
  const r = byDay.get(k) ?? { day: u.at.slice(0, 10), agent: u.agent, runs: 0, usd: 0, turns: 0, failed: 0 };
  r.runs++; r.usd += u.costUsd; r.turns += u.turns; if (!u.ok) r.failed++; byDay.set(k, r);
}
csv('harness_usage_daily.csv', [...byDay.values()].map((r) => ({ ...r, usd: r.usd.toFixed(2) })));

// 8. Activity-log event counts per day (first word of each event only; no text).
const ev = new Map<string, number>();
for (const line of activity.split('\n')) { const [at, , text] = line.split('\t'); if (!at || !text) continue;
  const key = `${at.slice(0, 10)}|${text.split(/[ :]/)[0]}`; ev.set(key, (ev.get(key) ?? 0) + 1); }
csv('activity_events_daily.csv', [...ev].map(([k, n]) => { const [day, event] = k.split('|'); return { day, event, n }; }));

console.log(`wrote ${outDir}: ${issues.length} issues, ${decisions.length} decisions, ${ledger.bets.length} bets, ${harness.length} harness runs`);
