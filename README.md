# Mentor field report: scripts and data

Companion repository for the preprint

> Gleb Sologub. *Upstream-First Self-Improvement: A Field Report on a Self-Modifying Engineering Harness, and How
> to Keep Many Instances One Product.* 2026. (arXiv link to be added once posted.)

The paper reports eight weeks (12 September – 7 November 2026) of **Mentor**, a self-improving engineering harness
built on the Claude Agent SDK. Mentor delivered issues on the product of a commercial software company under one
human owner, while four loops of its own rewrote the harness. This repository holds the scripts behind every
number and figure in the paper, and the anonymised aggregate data they produce.

## What is here

| Path | What |
|---|---|
| `data/commits.csv` | One row per harness commit (non-merge): date, who started it (a loop prefix or human), agent co-author flag |
| `data/commit_summary.json` | Totals and shares derived from `commits.csv` |
| `data/backlog_edits.csv` | Commits touching the harness backlog file, per day |
| `data/handoffs.csv`, `data/handoff_summary.json` | One row per hand-off note (anonymised `H01`…): date, kind, outcome, acceptance criteria verified / total |
| `data/weekly_all.csv` | The harness's own scorecard, 8 contiguous 7-day windows: delivered, interventions, lead time, lost share, agent hours, restarts |
| `data/weekly_by_size.csv` | The same, by issue size |
| `data/decisions_by_week.csv` | Decisions per week by tier (T0–T3) |
| `data/runtime_summary.json` | Whole-window and first-vs-last-four-weeks aggregates, decisions before/after the 9 Oct routing fix, bets, sessions |
| `figures/` | The paper's figures (PDF and PNG) |
| `check_numbers.py` | Recomputes the numbers quoted in the paper from `data/` and prints them |
| `plot_weekly.py` | Redraws the weekly-metrics figure from `data/weekly_all.csv` |
| `scripts/` | The scripts that produced `data/` from the private sources |

To check the paper's numbers, you need only Python 3; matplotlib is needed only for `plot_weekly.py`:

```bash
python3 check_numbers.py
```

## What is not here, and why

- **The harness source, the evidence repository and the daemon's raw run-time state are not public.** The raw
  records name the client's tickets, people and accounts. The scripts in `scripts/` show exactly how the
  aggregates were produced from them:
  - `git_commits.py`, `handoffs.py`, `make_figures.py`: from git history and the hand-off notes;
  - `export-for-paper.ts`: a read-only export run inside the harness, using its own scorecard code;
  - `export_metrics.py`: turns that export into the aggregates here.
- **Model cost figures** are withheld from this release until the client has agreed to their publication.
- **No client code, ticket identifiers, names or internal URLs** appear in this repository. Issue keys were
  replaced by salted hashes during export and are dropped from the aggregates.

## Definitions (as the harness computes them)

- **Intervention:** the owner's own command: `/fix` on an issue, "changes" at an approval gate, or `/repair` of the
  harness. It is counted from his commands, not from the harness's reports.
- **Delivered:** handed off or merged within the window.
- **Lost share:** agent hours that were redone, cut off, or spent after a hand-off, as a share of all agent hours.
- **Loop commit:** a commit whose subject starts with `curator:`, `strategist:`, `doctor:`, `sdk:` or `records:`.
  Nearly all commits are typed by an agent; this split is about who *started* the change.

## Licence

- Code (`*.py`, `*.ts`): MIT, see `LICENSE`.
- Data and figures (`data/`, `figures/`): CC BY 4.0, see `LICENSE-DATA`.

## Citation

See `CITATION.cff`. Until the arXiv identifier exists, please cite this repository.
