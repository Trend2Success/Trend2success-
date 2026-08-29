# dk_ev — DraftKings DFS EV Optimizer

A DraftKings Daily Fantasy Sports lineup optimizer that goes beyond "maximize
projected points": it builds a mixed-integer-optimal (and near-optimal)
lineup pool under DK's salary cap and slot rules, then runs a Monte Carlo
simulation against a simulated opponent field to estimate **true Expected
Value** — accounting for player score distributions, contest payout
structure, and field ownership — for Cash (50/50) and GPP (tournament)
contests alike.

## Architecture

```
dk_ev/
  domain.py           Player / Lineup value objects
  rules.py             DK slot rules per sport (NFL, NBA, MLB, CFB)
  data/
    interfaces.py       Protocols: SalarySource, ProjectionSource, OwnershipSource
    csv_sources.py       CSV-backed implementations (DK export + user projections/ownership)
    stub_sources.py      Fallbacks: odds-derived projections, value-based naive ownership
  slate.py             Joins the three sources into a list of Player
  optimizer/
    mip.py               OR-Tools CP-SAT lineup solver (salary cap, slots, locks/bans, stacking)
    portfolio.py          Diversified M-lineup generation (cash/GPP/balanced scoring, leverage)
  simulation/
    ev_simulator.py       Monte Carlo EV simulation vs. a simulated ownership-weighted field
  payouts.py           Payout tier structures (50/50 cash + sample GPP presets, JSON-loadable)
  export.py            DK-upload-ready CSV export
  models.py / db.py / persistence.py   SQLite persistence of runs and lineups
  service.py           Orchestrates data -> optimizer -> simulator -> results
  cli.py / __main__.py CLI entry point
  api/                 FastAPI app
frontend/              React + Vite + Tailwind UI
sample_data/           Ready-to-run NFL and CFB (college football) slates
```

Every data input (salaries, projections, ownership) is defined as a
`Protocol` in `dk_ev/data/interfaces.py`. The bundled implementations are
CSV files and simple statistical stubs; swapping in a live odds/projections
API later means writing a new class that satisfies the same Protocol — the
optimizer and simulator never import a concrete source.

## Install

```bash
pip install -r dk_ev/requirements.txt
```

## Run — CLI

The repo ships with a sample NFL slate, so this runs end-to-end immediately:

```bash
python -m dk_ev optimize --sport nfl --contest gpp --lineups 20
```

Useful flags (see `python -m dk_ev optimize --help` for the full list):

```bash
# Cash (50/50): variance-averse, floor-weighted scoring
python -m dk_ev optimize --sport nfl --contest cash --lineups 5

# Your own DK salary export + projections
python -m dk_ev optimize --salaries my_slate.csv --projections my_projections.csv

# College football (CFB): QB, RB, RB, WR, WR, WR, FLEX (RB/WR), S-FLEX (QB/RB/WR) — no TE/DST
python -m dk_ev optimize --sport cfb --salaries sample_data/cfb_salaries.csv --projections sample_data/cfb_projections.csv

# Force a player in every lineup, ban another, require a QB+1 pass-catcher stack
python -m dk_ev optimize --lock 1049 --ban 1032 --stack 1

# Export the ranked lineups as a DK-upload-ready CSV
python -m dk_ev optimize --lineups 20 --export-csv lineups.csv

# Persist the run to SQLite
python -m dk_ev optimize --db sqlite:///dk_ev.db
```

## Run — API + Frontend (Docker)

```bash
docker compose up --build
```

- Backend (FastAPI): http://localhost:8000 — try `POST /optimize`, `GET
  /lineups/{run_id}`, `GET /export/csv/{run_id}`, interactive docs at
  `/docs`.
- Frontend (React/Vite): http://localhost:5173 — generate lineups, inspect
  them in the results table and lineup card, and export to a DK CSV.

### Run without Docker

```bash
# Terminal 1
pip install -r dk_ev/requirements.txt
uvicorn dk_ev.api.main:app --reload

# Terminal 2
cd frontend
npm install
npm run dev
```

## Data inputs

The bundled sample slate is NFL-only; pass `--salaries` (CLI) or
`salaries_csv` (API) explicitly for NBA/MLB/CFB — the app refuses to run
another sport's rules against the NFL sample data, since that would
silently mix a college football roster with NFL players.

- **Salaries** (`--salaries`): a DK contest export CSV — `Position, Name,
  Salary, Team, Opponent, AvgPointsPerGame` (a few common header variants,
  like `TeamAbbrev` or a `Game Info` column instead of `Opponent`, are
  tolerated too).
- **Projections** (`--projections`, optional): `player, projected_points,
  ceiling, floor, std_dev`. If omitted, `StubProjectionSource` derives a
  projection + variance from `AvgPointsPerGame` (or from Vegas odds, if you
  supply `TeamOdds`).
- **Ownership** (`--ownership`, optional): `player, projected_ownership_pct`.
  If omitted, `NaiveOwnershipSource` derives a chalk proxy from projected
  points per salary dollar.
- **Payout structure** (`--payout-json`, optional): JSON list of
  rank-or-percentile tiers; see `dk_ev/payouts.py` for the schema and the
  built-in 50/50 and sample-GPP presets.

## How the EV simulation works

For each candidate lineup, `EVSimulator` runs N Monte Carlo iterations
(10,000+ by default):

1. Every player's score is drawn from `Normal(mean=projection,
   std=std_dev)` (or a fat-tailed Student-t distribution), clipped to
   `[floor, ceiling]`. A configurable shared per-team latent factor adds
   mild same-team correlation, so stacks score as genuinely correlated
   outcomes rather than independent draws.
2. An opponent field is approximated each iteration by sampling, per
   roster slot, a player weighted by projected ownership — this keeps the
   simulation tractable for large fields while remaining sensitive to the
   slate's actual ownership shape (opponent lineups are not individually
   salary-cap-checked, a standard simplification for field modeling).
3. The candidate's rank against that sampled field is scaled to the
   contest's real field size and looked up in the payout structure.

EV = mean prize across iterations. The simulator also reports win rate,
ITM% (min a payout), median finish, top-1%/top-10% rates, and ceiling/floor
(90th/10th percentile score).

## DraftKings CSV export — format and caveats

`dk_ev/export.py` writes one column per roster slot (in DK's own slot
order — e.g. NFL repeats `RB` and has one `FLEX` column) and one row per
lineup, with each cell as `"Player Name (PlayerID)"`.

**Caveat**: DraftKings' own downloadable "entries" template for a specific
contest also carries `Entry ID`, `Contest ID`, and `Contest Name` columns,
so DK can match the upload to already-created (possibly paid) entries. This
tool has no way to know those values — they only exist once you've entered
a contest and downloaded DK's entries CSV for it. To fill an existing
contest's entries, paste this tool's roster columns into the corresponding
columns of that downloaded template (same slot order, same `Name (ID)`
cell format) rather than uploading this file standalone. The `PlayerID` in
each cell comes straight from the `ID` column of the salary CSV you loaded
— if your salary export doesn't include DK's real numeric IDs, the export
will still be internally consistent but won't upload directly to DK.

## Contest presets

- `cash_5050(field_size, entry_fee)` — top half doubles up (net of a 10%
  rake by default).
- `sample_gpp(field_size, entry_fee)` — 1st = $25k, top 1% = $1k, top 10% =
  $20, top 20% = $5, else $0.
- Or supply your own via `--payout-json` / `load_payout_structure`.

## Test

```bash
pytest tests/dk_ev
```

Covers: salary-cap enforcement, position-slot validity, locks/bans/team
limits, the no-opposing-DST-vs-QB toggle, portfolio diversification and
stacking, EV simulator sanity (an all-floor lineup should have ~0% ITM in
a GPP field; win/ITM rates stay bounded probabilities), DK CSV
header/column-order/cell-format correctness per sport, run persistence,
the CLI end-to-end, and the FastAPI endpoints.
