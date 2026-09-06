# SlateEdge — Product Architecture

## Goals and constraints

SlateEdge is a personal decision-support tool for DraftKings NFL Classic DFS. The
non-negotiable constraints that shaped every architectural choice:

- No scraping, browser automation, or credential storage for any DFS site.
- No API calls to DraftKings or competing DFS/analytics products.
- Every model output must be clearly labeled an estimate, never a guarantee.
- CSV-first data ingestion; "authorized API sources" are a user-configured extension point,
  not a built-in integration to any named vendor.

## System diagram

```
┌─────────────────────┐        HTTP/JSON        ┌──────────────────────────┐
│   web (Next.js)      │ ───────────────────────▶ │  optimizer-service        │
│  - App Router pages   │ ◀─────────────────────── │  (FastAPI, stateless)     │
│  - Server Actions      │                          │  - /optimize (PuLP/CBC)   │
│  - Prisma ORM          │                          │  - /simulate (NumPy/SciPy)│
└─────────┬────────────┘                          └──────────────────────────┘
          │  SQL
          ▼
┌─────────────────────┐
│      PostgreSQL        │
│  slates, players,       │
│  projections, lineups,   │
│  results, audit log      │
└─────────────────────┘
```

The optimizer service is intentionally **stateless and dumb about business rules**: the web
app is the source of truth for slates/players/settings, and on every optimizer or simulation
run it sends a complete, self-contained JSON payload (player pool + all constraints) and
receives lineups/statistics back. This keeps the constraint logic (a genuinely nontrivial
integer program) in one well-tested place, written in a language suited to it, while keeping
all persistence, auth, and UI concerns in the Next.js app.

## Why Next.js Server Actions instead of a separate REST API

Most mutations (CSV import, player locks/tags, projection adjustments, running the optimizer,
settings changes) are implemented as React Server Actions (`'use server'` functions in
`web/src/server/actions/*.ts`) rather than hand-rolled `/api/*` routes. For a single-user,
server-rendered app this removes an entire layer of client-side fetch/JSON-plumbing
boilerplate while keeping every mutation type-checked end-to-end. Two things remain real HTTP
route handlers because they need non-JSON responses: CSV export (`/api/export/lineups`) and
CSV template downloads (`/api/templates/[kind]`).

## Data model (Prisma)

Key entities (see `web/prisma/schema.prisma` for the full schema with comments):

- `User` / `Settings` — local account + per-user thresholds (chalk/contrarian %, budget,
  stop-loss, default salary cap). Auth is a signed HTTP-only JWT cookie
  (`web/src/lib/auth.ts`) — deliberately isolated behind `getCurrentUser()`/`requireUser()` so
  a real OAuth/cloud identity provider can replace the credentials check later without
  touching any calling code.
- `Slate` → `Player` (1 salary/roster row per player per slate) → `ProjectionSnapshot` (the
  *current* blended + manually-adjusted projection actually used everywhere else in the app).
- `ProjectionSource` / `ProjectionRow` — one row per (slate, source, player) for every
  projection CSV you import; `ProjectionSnapshot` is *derived* from these plus manual
  adjustments, and is recomputed by `recomputeProjectionSnapshotsFromSources()` whenever a
  source is imported or blend weights change.
- `ProjectionAdjustment` — full audit trail: every blend recompute and every manual point/%
  adjustment, with before/after values, the editor, and a timestamp.
- `LineupRun` → `Lineup` → `LineupPlayer` — one `LineupRun` per optimizer invocation, storing
  the *entire* request payload (`settingsJson`) and seed used, so a run can be inspected or
  compared later. Each `Lineup` denormalizes its own totals (salary, projection, ceiling,
  ownership, leverage, model score, stack summary) at generation time.
- `SimulationRun` — stores the full request and response JSON from `/simulate` verbatim; the
  Simulation Lab page reads straight from this rather than re-deriving anything.
- `ContestResult` — one row per imported results-CSV row; `externalLineupRef` keeps the
  free-text `lineup_id` from your CSV without assuming it maps to an internal `Lineup`
  (`linkedLineupId` exists for the cases where it does).
- `AuditLog` — append-only log of every import, edit, optimizer/simulation run, and export.

## The optimizer

`optimizer-service/app/optimizer.py` builds one mixed-integer linear program per lineup with
PuLP (CBC solver, bundled — no external solver install required):

- Binary decision variable per player; constraints for exactly-one-per-slot (with FLEX
  eligibility), salary cap window, per-team/per-game caps, locks/excludes, player groups
  (at-least/at-most/exactly/if-then/exclude-together), and the NFL stacking rules (QB
  pass-catcher count, bring-back, RB-with-QB, DST-vs-offense).
- The objective linearly combines final projection, ceiling, and leverage (each with a
  user-set weight) minus an ownership penalty weight — never a black box, always the same four
  numbers you set on the Lineup Builder page.
- Multiple lineups are generated **iteratively**: after each solve, a diversity constraint
  (shared-player cap vs. every prior lineup) and running per-player exposure caps are added
  before solving again. This is a standard, generic technique for diversified lineup
  generation — not copied from any specific product — and its limits (exposure enforcement is
  conservative near the end of a run; `min_exposure` is best-effort) are documented in
  `optimizer-service/README.md` and `docs/known-limitations.md`.
- Infeasible requests never crash the endpoint: the service returns whatever lineups it *did*
  find (possibly zero) plus plain-language warnings explaining why.

## The simulator

`optimizer-service/app/simulation.py` draws `N` correlated samples per player from either a
truncated-normal or log-normal marginal distribution parameterized by your imported
mean/standard deviation, using a Gaussian-copula approach: build a correlation matrix from
simple, fully-editable rules (QB↔own pass-catcher, same-game offense, DST vs. opposing
offense) plus any explicit pairs you supply, repair it to be positive semi-definite, Cholesky-
decompose it, and transform the resulting correlated normals to each player's target
marginal. Lineup-level outcomes sum the relevant players' simulated draws per trial. The
"duplication-risk proxy" is explicitly a heuristic (ownership + portfolio-overlap blend), not
a model of a real contest's field — labeled as such everywhere it appears.

## Frontend structure

- `web/src/app/(auth)/*` — login/register, outside the app shell.
- `web/src/app/(app)/*` — every product screen, wrapped by `web/src/app/(app)/layout.tsx`
  (fetches the current user + slate list, renders `<AppShell>`: desktop sidebar, mobile bottom
  nav, and the permanent responsible-play footer on every page).
- `web/src/lib/csv/*` — CSV column-alias matching (`columnMap.ts`), the shared
  parse-validate-dedupe engine (`engine.ts`), and per-file-type Zod schemas + templates
  (`salary.ts`, `projection.ts`, `results.ts`).
- `web/src/lib/calculations.ts` — the plain-formula math (value, ceiling value, percentile
  rank, leverage score, chalk/contrarian flags, manual adjustment, blending) shared by the
  Projection Lab and Ownership & Leverage pages, and unit-tested directly.
- `web/src/lib/ai-assistant/parseRules.ts` — the local, deterministic "AI Strategy Assistant."
  It is a keyword/regex parser, not a call to any external LLM; it proposes a structured rule
  patch that the user must review and explicitly apply before it touches the optimizer form.
- `web/src/lib/optimizer/*` — typed request/response contracts shared with the Python service,
  the `fetch` client, and the four built-in lineup presets (all labeled "starting points, not
  proven strategies" in the UI).

## Where a real auth provider would slot in

`getSessionUserId()` / `createSession()` / `destroySession()` in `web/src/lib/auth.ts` are the
only places that know about the JWT-cookie mechanism. Swapping in NextAuth.js or a hosted
identity provider means replacing the contents of those three functions (and the login/
register pages) — every Server Action and page calls `requireUser()`/`getCurrentUser()`, which
would not need to change.
