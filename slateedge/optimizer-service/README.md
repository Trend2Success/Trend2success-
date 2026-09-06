# SlateEdge optimizer-service

A standalone Python analytics microservice for **SlateEdge**, an independent,
personal-use DraftKings NFL DFS *decision-support* tool. This service is
**not affiliated with, endorsed by, or associated with DraftKings** or any
other daily fantasy sports operator. It does not scrape any operator's site
and copies no branding. Every number this service returns (projections,
ownership, simulated outcomes, "risk" scores, lineup scores, etc.) is an
**estimate** produced from user-supplied inputs and standard statistical /
optimization techniques — **never a guarantee of real-world results.**

The frontend (a separate Next.js app with its own Prisma database) calls
this service over plain HTTP/JSON. This service holds no persistent state
of its own — every request is self-contained.

## Running locally

```bash
cd slateedge/optimizer-service
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The service listens on `http://127.0.0.1:8000` by default. Interactive API
docs are available at `http://127.0.0.1:8000/docs` (FastAPI/Swagger UI).

Verified with **Python 3.11.15** in development; the code is also
**Python 3.12-compatible** (the Dockerfile uses `python:3.12-slim`).

Install command used during development:

```bash
pip install -r requirements.txt
```

## Running tests

```bash
cd slateedge/optimizer-service
pytest -q
```

All 30 tests pass as of this writing (unit tests for the optimizer and
sanity/statistical tests for the simulator). Tests use only small,
synthetic/fictional player pools defined inline in the test files — no real
player names or data.

## Running with Docker

```bash
cd slateedge/optimizer-service
docker build -t slateedge-optimizer-service .
docker run -p 8000:8000 slateedge-optimizer-service
```

## Endpoints

- `GET /health` → `{"status": "ok"}`
- `POST /optimize` — DFS lineup optimizer (see below)
- `POST /simulate` — Monte Carlo player/lineup outcome simulation (see below)

---

## `/optimize`: how it works

This is a standard mixed-integer-linear-programming (MILP) lineup builder:
binary decision variables (one per player) subject to linear constraints
(salary cap, roster composition, exposure caps, stacking, custom groups),
solved with [PuLP](https://coin-or.github.io/pulp/)'s bundled CBC solver
(a pure open-source MILP solver that ships with PuLP itself — **no
external OR-Tools binary install required**). This is a completely
generic, textbook operations-research technique; nothing here is derived
from or copies any commercial optimizer's internals.

### Roster construction

Rather than a full player-to-slot assignment MILP, roster composition is
modeled with per-position count constraints:

- Positions that are **not** flex-eligible must match their exact required
  count from `roster_slots`.
- Positions that **are** flex-eligible must each individually meet their
  dedicated (non-FLEX) requirement as a floor, and the total number of
  flex-eligible players used must equal the sum of dedicated requirements
  plus the number of `FLEX` slots.

This is equivalent to the full assignment formulation for the standard
"single shared FLEX slot" shape (DK Classic: `QB, RB, RB, WR, WR, WR, TE,
FLEX, DST`), solves faster, and always admits a valid slot assignment,
which is computed deterministically after the solve (players are sorted by
`player_id` when there's a choice of which specific player fills e.g.
`RB1` vs `RB2`, purely for stable, reproducible output — it does not
affect which *players* are selected, only the display-slot labeling).

### Constraints implemented

- Salary cap, plus optional `min_salary`/`max_salary` window.
- Exactly one player per roster slot; FLEX fillable only by
  `flex_positions`; strict position eligibility.
- No duplicate players in a lineup (each player is a single binary
  variable, so this is structural).
- `locked_player_ids` forced into every lineup; `excluded_player_ids`
  forced out.
- `max_players_per_team`.
- `min_players_per_game` / `max_players_per_game`: implemented with a
  per-game binary "game used" indicator so that the floor
  (`min_players_per_game`) only applies to a game that already has at
  least one player rostered from it — i.e. "if you play this game at all,
  play at least N from it" — rather than forcing every game on the slate
  to be represented (which would usually be infeasible).
- `groups`: `at_least` / `at_most` / `exactly` N of a player set;
  `if_then` (using `then_player_id` requires `if_player_id` to also be
  used — modeled as `x[then] >= x[if]`); `exclude_together` (pairwise
  mutual exclusion across every pair in the group — no two of the listed
  players may appear together).
- `stack_rules`:
  - `qb_stack_min`/`qb_stack_max`: bounds on same-team WR/TE count
    alongside the rostered QB (only enforced for the QB's own team; other
    teams' WR/TE counts are unrestricted).
  - `bring_back_min`: minimum players from the QB's opponent team
    (opponent is read from each player's `opponent` field).
  - `allow_rb_with_qb=false`: forbids rostering an RB from the same team
    as the rostered QB.
  - `allow_dst_vs_offense=false`: forbids rostering a DST alongside any
    non-DST player from the team that DST is facing.
- `objective_weights`: linear combination
  `projection*w1 + ceiling*w2 + leverage*w3 - ownership*w4`, maximized.
- `min_total_projection` / `min_total_ceiling` / `global_max_ownership`:
  optional linear floors/ceilings on lineup totals.

### Multi-lineup generation, diversity, and exposure

Lineups are generated **one at a time**, in a loop, because exposure and
diversity constraints depend on what's already been generated:

- **Diversity**: after each lineup is solved, a constraint is added for
  all future solves: the next lineup may share at most
  `roster_size - min_unique_players` players with that lineup.
- **`max_exposure` (hard cap, by construction)**: before solving lineup
  *i*, for every player with `max_exposure[player_id] < 1.0`, we compute
  `allowed_so_far = floor(max_exposure * num_lineups)`. If the player's
  running usage count has already reached that number, the player is
  hard-excluded from this and all subsequent solves. This is a simple,
  always-correct-by-the-end approach (documented in
  `app/optimizer.py`); it can be conservative in some edge cases (a
  player might be excluded slightly before it's strictly required), but
  it never overshoots the cap.
- **`min_exposure` (best-effort, NOT a hard guarantee)**: we track each
  player's shortfall against their target count
  (`ceil(min_exposure * num_lineups)`). If a player *must* appear in
  every remaining lineup (including the current one) to still hit their
  floor by the end, they are force-included for that solve (and we retry
  without the forced include if that causes infeasibility). Otherwise we
  add a small positive bonus to the objective proportional to the
  remaining shortfall, nudging — but not guaranteeing — the solver
  toward using them. **This is intentionally inexact**; see
  "Known limitations" below.
- **Infeasibility never crashes the request.** If a given lineup slot
  cannot be solved (conflicting locks/groups, exposure/diversity painted
  the solver into a corner, etc.), a warning is appended and generation
  continues to the next requested lineup slot. The response always
  returns whatever lineups were actually found, with HTTP 200.

### Reproducibility (`reproducible` + `random_seed`)

When `reproducible=true` and `random_seed` is set, a NumPy `Generator` is
seeded per-lineup from `(random_seed, lineup_index)` and a tiny random
perturbation (`~1e-4` scale, far smaller than any real scoring
difference) is added to each player's objective coefficient before
solving. This deterministically breaks ties between lineups that would
otherwise score identically, without materially changing which lineups
are genuinely best. `seed_used` in the response always echoes the
`random_seed` that was supplied (or `null` if none was given).

### Example request

```bash
curl -sS -X POST http://127.0.0.1:8000/optimize \
  -H 'Content-Type: application/json' \
  -d '{
    "players": [
      {"player_id":"qb1","name":"QB One","team":"AAA","opponent":"BBB","position":"QB","salary":7500,"projection":22.0,"ceiling":33.0,"ownership":15.0,"game_id":"AAA_vs_BBB"},
      {"player_id":"rb1","name":"RB One","team":"AAA","opponent":"BBB","position":"RB","salary":8000,"projection":18.0,"ceiling":27.0,"ownership":20.0,"game_id":"AAA_vs_BBB"},
      {"player_id":"rb2","name":"RB Two","team":"BBB","opponent":"AAA","position":"RB","salary":6000,"projection":14.0,"ceiling":21.0,"ownership":10.0,"game_id":"AAA_vs_BBB"},
      {"player_id":"wr1","name":"WR One","team":"AAA","opponent":"BBB","position":"WR","salary":7800,"projection":17.5,"ceiling":26.0,"ownership":18.0,"game_id":"AAA_vs_BBB"},
      {"player_id":"wr2","name":"WR Two","team":"BBB","opponent":"AAA","position":"WR","salary":6200,"projection":13.0,"ceiling":19.5,"ownership":12.0,"game_id":"AAA_vs_BBB"},
      {"player_id":"wr3","name":"WR Three","team":"AAA","opponent":"BBB","position":"WR","salary":4400,"projection":8.5,"ceiling":12.7,"ownership":6.0,"game_id":"AAA_vs_BBB"},
      {"player_id":"te1","name":"TE One","team":"AAA","opponent":"BBB","position":"TE","salary":4600,"projection":9.5,"ceiling":14.2,"ownership":9.0,"game_id":"AAA_vs_BBB"},
      {"player_id":"flex1","name":"RB Three","team":"BBB","opponent":"AAA","position":"RB","salary":4800,"projection":9.5,"ceiling":14.0,"ownership":7.0,"game_id":"AAA_vs_BBB"},
      {"player_id":"dst1","name":"DST One","team":"AAA","opponent":"BBB","position":"DST","salary":3000,"projection":8.0,"ceiling":14.0,"ownership":11.0,"game_id":"AAA_vs_BBB"}
    ],
    "salary_cap": 50000,
    "num_lineups": 3,
    "min_unique_players": 2
  }'
```

---

## `/simulate`: how it works

A Monte Carlo simulator built on NumPy/SciPy:

1. Build an N×N correlation matrix across all supplied players, starting
   from independence (identity matrix) and layering on
   `default_correlation_rules` heuristically, from least to most specific:
   - `same_game_offense`: any two non-DST players sharing a `game_id`.
   - `qb_own_pass_catcher`: a QB and a same-team WR/TE (overrides the
     `same_game_offense` value for that pair).
   - `dst_vs_opp_offense`: a DST and any non-DST player on the team it's
     facing (its opponent is inferred as "the other team present in the
     same `game_id`").
   - Explicit `correlations` pairs are applied **last** and always win
     over any rule-based value for that pair.
2. Because heuristic overlays aren't guaranteed to produce a valid
   (positive semi-definite) correlation matrix, it's projected to the
   nearest PSD correlation matrix via eigenvalue clipping (negative/near-
   zero eigenvalues are clipped, the matrix is reconstructed, and the
   diagonal is renormalized to 1s).
3. Correlated standard normal draws are generated via a Cholesky
   decomposition of that fixed matrix (seeded from `random_seed` when
   given).
4. Each player's draws are transformed to their target marginal
   distribution using a **Gaussian-copula** transform
   (`u = Φ(z)`, then `x = target_ppf(u)`):
   - `truncated_normal`: modeled as `Normal(mean, stdev)` truncated at 0
     from below. This is a simplification — for players whose `mean` is
     small relative to `stdev`, the realized simulated mean will sit
     slightly *above* the requested `mean` because the left tail below 0
     is clipped away. For realistic fantasy-point inputs (mean
     comfortably above 0 relative to stdev) this effect is small.
   - `lognormal`: mu/sigma for the underlying normal are solved
     analytically via method-of-moments so the lognormal distribution's
     mean/stdev match the requested mean/stdev exactly:
     `sigma^2 = ln(1 + (stdev/mean)^2)`, `mu = ln(mean) - sigma^2/2`.
   This exactly reproduces the requested marginal while approximately
   preserving the requested correlation structure — standard practice for
   this kind of decision-support simulation, and more than sufficient for
   directional "does this correlation help/hurt" analysis.
5. Per player: mean, median, p75, p90 of the simulated draws, plus
   `prob_exceeds_threshold` (fraction of draws exceeding `threshold`) when
   a threshold is supplied.
6. Per supplied lineup: the same stats computed on the **sum** of that
   lineup's players' simulated draws (its outcome distribution), plus a
   `duplication_risk_proxy`.

### `duplication_risk_proxy` — explicitly a heuristic, not a real model

This service has **no visibility into what any other DFS entrant actually
rosters**, so `duplication_risk_proxy` is a simple, clearly-labeled
**proxy** combining:

```
0.6 * normalized(ownership_sum) + 0.4 * avg_jaccard_similarity_to_other_lineups
```

- `normalized(ownership_sum) = ownership_sum / (num_roster_spots * 100)`,
  clipped to `[0, 1]` (assumes ownership is supplied as a 0–100 percentage).
- `avg_jaccard_similarity_to_other_lineups` = mean Jaccard similarity
  (`|intersection| / |union|`) of this lineup's player set against every
  *other* lineup in the same request's `lineups` list (`0` if there are no
  other lineups to compare against).

The result is clipped to `[0, 1]`. **This is not a field-duplication
model** — treat it strictly as a rough, order-of-magnitude signal for
"this lineup looks like a lot of other lineups I've built and/or rosters
high-owned players," never as a probability of actual duplication against
the real DFS contest field.

### Example request

```bash
curl -sS -X POST http://127.0.0.1:8000/simulate \
  -H 'Content-Type: application/json' \
  -d '{
    "players": [
      {"player_id":"qb1","name":"QB One","position":"QB","team":"AAA","game_id":"AAA_vs_BBB","mean":20.0,"stdev":6.0},
      {"player_id":"wr1","name":"WR One","position":"WR","team":"AAA","game_id":"AAA_vs_BBB","mean":15.0,"stdev":7.0},
      {"player_id":"dst1","name":"DST One","position":"DST","team":"BBB","game_id":"AAA_vs_BBB","mean":7.0,"stdev":4.0}
    ],
    "distribution": "truncated_normal",
    "num_simulations": 10000,
    "correlations": [{"player_id_a":"qb1","player_id_b":"wr1","rho":0.65}],
    "lineups": [{"lineup_id":"l1","player_ids":["qb1","wr1","dst1"],"ownership_sum":42.0}],
    "threshold": 25.0,
    "random_seed": 42
  }'
```

---

## Known limitations / simplifications

- **`max_exposure` is hard-capped but can be slightly conservative** near
  the tail end of a generation run (see "Multi-lineup generation" above);
  it never overshoots the requested cap.
- **`min_exposure` is best-effort only**, not a hard guarantee — it uses a
  combination of forced-inclusion (when a player must appear in every
  remaining lineup to still hit their floor) and a soft objective nudge
  otherwise. A tight floor combined with other hard constraints
  (locks/excludes/groups/stacking) can still leave a player under their
  requested floor; no exception is raised in that case.
- **`min_players_per_game` only applies to a game that is already used**
  (i.e., "if you're in this game at all, play at least N from it"), not a
  requirement that every game on the slate be represented — the latter
  would usually be infeasible for realistic roster sizes and slate sizes.
- **Slot labels (`RB1` vs `RB2`, etc.) are assigned deterministically but
  arbitrarily** among interchangeable dedicated slots of the same
  position — which specific players are selected is never affected by
  this, only which display slot they land in.
- **`truncated_normal` in `/simulate` does not exactly moment-match** the
  requested mean/stdev for players whose mean is small relative to their
  stdev (the realized mean can sit slightly above the input). `lognormal`
  moment-matches exactly. See the "how it works" section above.
- **Correlation preservation is approximate, not exact**, after the
  Gaussian-copula marginal transform (this is standard for
  copula-based Monte Carlo and is directionally reliable — a requested
  positive correlation reliably produces a meaningfully positive sample
  correlation — but the sample correlation will not exactly equal the
  requested `rho`).
- **`duplication_risk_proxy` is a heuristic stand-in**, not a real
  field-duplication model (no visibility into the actual DFS contest
  field is available to or used by this service).
- All projections, simulated outcomes, and derived scores are
  **estimates** based on the caller-supplied inputs — this service makes
  no claim about, and provides no guarantee of, real-world DFS results.
