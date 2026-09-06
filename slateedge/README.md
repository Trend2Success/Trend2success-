# SlateEdge

SlateEdge is an independent, **personal-use** DraftKings NFL Classic DFS decision-support and
lineup-construction tool. It is not affiliated with, endorsed by, or connected to DraftKings or
any other DFS operator or analytics product. It never scrapes, automates, or logs into any
external site, and it never uploads or submits entries on your behalf — everything you build
here is exported as a CSV that you review and upload yourself, wherever you choose to play.

> **DFS involves financial risk. Use a fixed entertainment budget. Model outputs are estimates
> and do not guarantee results.** This notice appears in the footer of every page.

## What it does

1. Imports your own CSV data (salary, projections, contest results) — or data from an
   authorized source you configure yourself. Nothing is ever fetched automatically.
2. Builds transparent, auditable projections (blending + manual adjustments, every change
   logged) and ownership/leverage estimates.
3. Builds correlated, diversified tournament lineups with a real integer-programming
   optimizer (roster rules, exposure caps, stacking, player groups).
4. Runs Monte Carlo simulations of player and lineup outcomes with editable correlation
   assumptions.
5. Reviews lineup portfolios for exposure concentration and duplicate construction.
6. Tracks your own contest results over time (ROI, bankroll trend, sample-size warnings).

Every output is labeled an **estimate**, never a prediction, guarantee, or "lock."

## Architecture

Two services + Postgres:

- **`web/`** — Next.js 14 (App Router, TypeScript), Tailwind CSS, a small hand-rolled
  shadcn/ui-style component set on Radix primitives, TanStack Table, Recharts, React Hook
  Form patterns via Server Actions, Prisma ORM.
- **`optimizer-service/`** — Python 3.12 FastAPI service doing the actual math: PuLP
  (CBC solver) for lineup optimization, NumPy/SciPy for Monte Carlo simulation. Stateless —
  the web app sends it a player pool + settings and gets lineups/simulation results back.
- **Postgres** — all persisted data (slates, players, projections, lineups, results, audit
  log). Local accounts only in v1 (see `web/src/lib/auth.ts` for how a real OAuth/cloud
  provider would slot in later).

See [`docs/architecture.md`](docs/architecture.md) for a fuller write-up and
[`docs/known-limitations.md`](docs/known-limitations.md) for what this version does *not* do.

## Quick start (Docker Compose)

```bash
cp .env.example .env        # edit AUTH_SECRET and POSTGRES_PASSWORD at minimum
docker compose up --build
```

This starts Postgres, the optimizer service (port 8000), and the web app (port 3000). The web
container runs `prisma migrate deploy` on boot. Visit http://localhost:3000, register a local
account, and follow the onboarding wizard — or seed fictional demo data (see below) to explore
the app without uploading anything first.

## Local development (without Docker)

Requires Node 20+, Python 3.11+/3.12, and a local Postgres.

```bash
# 1. Database
createdb slateedge   # or use your own Postgres instance

# 2. Web app
cd web
cp ../.env.example .env   # then edit DATABASE_URL to point at localhost, set AUTH_SECRET
npm install
npx prisma migrate dev
npm run prisma:seed       # optional: fictional "Demo Data" slate + account
npm run dev                # http://localhost:3000

# 3. Optimizer service (separate terminal)
cd optimizer-service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Set `OPTIMIZER_SERVICE_URL=http://localhost:8000` in `web/.env` when running both locally.

### Demo account

`npm run prisma:seed` creates:

- Login: `demo@slateedge.local` / `DemoPassword123!`
- A slate named "Demo Sunday Main Slate," clearly labeled **Demo Data — Not Real Players or
  Projections** throughout the UI, with 22 fictional players, projections, and one sample
  lineup so every screen has something to show immediately.

## Environment variables

See [`.env.example`](.env.example). Summary:

| Variable                | Used by            | Notes                                                        |
| ------------------------ | ------------------- | -------------------------------------------------------------- |
| `POSTGRES_USER/PASSWORD/DB` | `db` (compose)   | Local Postgres credentials.                                   |
| `DATABASE_URL`           | `web`               | Prisma connection string.                                     |
| `AUTH_SECRET`            | `web`               | Signs local session cookies. Generate with `openssl rand -base64 48`. |
| `OPTIMIZER_SERVICE_URL`  | `web`               | Base URL of the Python service.                                |

No third-party API keys are required or supported out of the box. If you configure an
authorized projection data source of your own, you would import it as a CSV (see below) —
SlateEdge does not ship any built-in connector to a specific vendor.

## CSV schemas

Downloadable, pre-filled sample templates are available in-app on the **Slate Data Import**
and **Contest & Results Tracker** pages (`/api/templates/salary|projection|results`). Full
column definitions, validation rules, and how column-name aliases are matched are documented
in [`docs/csv-schemas.md`](docs/csv-schemas.md).

## Testing

```bash
# Python optimizer/simulation logic (constraint + correctness unit tests)
cd optimizer-service && source .venv/bin/activate && pytest -q

# TypeScript unit tests (CSV validation, projection/leverage calculations, AI rules parser)
cd web && npm test

# Type checking
cd web && npm run typecheck

# End-to-end (requires the web app + optimizer service running against a
# migrated + seeded database — see "Local development" above)
cd web && npm run test:e2e
```

All 30 Python unit tests and 30 TypeScript unit tests pass as of this build; the two Playwright
end-to-end tests (sign in → browse the demo slate → generate a lineup → review it in Portfolio;
and the responsible-play footer) pass against a live local stack.

## Known limitations

See [`docs/known-limitations.md`](docs/known-limitations.md). In short: this tool does not
guarantee profit or a "winning" lineup, does not automate any interaction with DraftKings or
any other contest operator, and its analysis is only as good as the data you import.
