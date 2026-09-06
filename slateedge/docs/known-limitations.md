# Known Limitations

SlateEdge is a personal decision-support tool, not a betting system. Read this before relying
on any number it shows you.

## By design — these will never change

- **No guarantee of profit or a winning lineup.** Every projection, ownership estimate,
  leverage score, simulation output, and lineup is labeled an estimate. "Model-ranked lineup"
  never means "optimal" or "winning" — it means "ranked highest by the formula and weights you
  configured, given the data you gave it."
- **No automation of any DraftKings (or other operator) interaction.** SlateEdge never logs
  in anywhere, never scrapes any site, never stores contest-site credentials, and never
  uploads or submits entries. CSV export produces a file for you to review and upload
  yourself.
- **Only as good as your data.** All projections, ownership, and salary data are either
  user-uploaded CSVs or from a source you explicitly configured yourself. There is no built-in
  connector to any specific data vendor.
- **Small samples are not proof.** The Dashboard and Results Tracker both warn when you have
  fewer than 10 tracked slates; the app never suggests raising stakes or chasing losses.

## Current version (v1) scope gaps

- **Local accounts only.** Authentication is a single-provider, local email/password system
  (bcrypt + signed JWT cookie). No OAuth/SSO yet — see `docs/architecture.md` for how it's
  isolated so that can be added without touching the rest of the app.
- **Single-user-oriented.** Multiple `User` rows can exist, but there is no team/workspace
  sharing, roles, or permissions model.
- **Optimizer exposure enforcement is a hard cap, applied conservatively.** When generating
  many lineups with a per-player max-exposure setting, the service can stop including a player
  slightly before the mathematically tightest possible point to guarantee the cap holds by the
  end of the run. `min_exposure` is best-effort (forced inclusion late in a run, or a soft
  objective nudge) — not a hard guarantee, and can under-deliver if it conflicts with other
  constraints.
- **`min_players_per_game`/`max_players_per_game`** apply to games already represented in a
  lineup rather than forcing every game on the slate to contribute — forcing every game would
  usually make the roster infeasible.
- **Correlation modeling is simple and explicit, not a real football model.** The Simulation
  Lab uses a small set of editable rules (QB↔own pass-catcher, same-game offense, DST vs.
  opposing offense) plus any explicit pairs you add. It does not model injuries, game script,
  weather, or anything not captured in your imported mean/standard deviation.
- **Duplication-risk proxy is a heuristic**, combining a lineup's total ownership and its
  overlap with your other generated lineups. It is explicitly not a model of the real
  contest's field and is labeled as a proxy everywhere it's shown.
- **Lineup-outcome "distributions"** on the Simulation Lab page are summary statistics (mean,
  median, p75, p90, threshold probability) computed from the underlying Monte Carlo draws, not
  a full histogram — the service does not return raw per-simulation draws to the browser.
- **CSV export template is a simple, user-verified column layout** (one column per roster
  slot, player name+ID or ID only). Contest operators' own upload formats change over time;
  always double-check the exported file against whatever you're about to upload it to before
  you use it.
- **Results Tracker breakdowns by stack construction, salary remaining, and ownership range**
  require manually linking a result to a SlateEdge-generated lineup (a dropdown on each row in
  "All tracked results" — the CSV's `lineup_id` is free text and isn't auto-matched, since it
  usually refers to the contest operator's own entry ID, not an internal SlateEdge lineup).
  Unlinked results still count fully in every other breakdown (sport, contest type, buy-in,
  entry size, lineup count, slate).
- **No native mobile app**, no authorized third-party projection API connectors, and no
  multi-user shared workspaces — all listed as "Planned" (and inert) on the Settings page for
  transparency rather than implemented as dead buttons.

## Reporting a problem

If a number looks wrong, start with the audit log on the Settings page — every import, edit,
optimizer run, and export is recorded there with a timestamp, and the Projection Lab's audit
trail shows exactly how any given player's projection got to its current value.
