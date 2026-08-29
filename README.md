# Trend2Success

A small multi-agent pipeline that searches for job/sales opportunities, verifies them,
ranks them against a candidate profile, queues the best matches, schedules the resulting
interview or sales call, and records the follow-up outcome.

See [docs/flow.md](docs/flow.md) for the flow diagram and a module-by-module breakdown.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python -m trend2success.main --query python --skills python,django --name Troy --top-n 3
```

This runs Search → Verify → Match & Rank → Application Queue using the built-in sample
data source, and writes queued applications to `data/application_queue.json`.

To swap in a real data source, pass a custom source function to `SearchAgent`:

```python
from trend2success.agents import SearchAgent
from trend2success.pipeline import Pipeline

def my_source(query: str):
    ...  # return a list[JobListing] from a real API

pipeline = Pipeline(search_agent=SearchAgent(sources=[my_source]))
```

## Test

```bash
pytest
```

---

# NCAAF DFS EV Optimizer (`dfs_ev`)

A command-line lineup optimizer for NCAAF (college football) DFS contests
(DraftKings Classic + Showdown/Captain Mode) that ranks lineups by
**simulated expected ROI**, not just projected points. DraftKings/FanDuel
contest CSVs are the source of truth for salaries and roster rules;
[OpticOdds API v3](https://opticodds.com) supplies odds, player props,
injuries, and historical results. See [docs/dfs_ev.md](docs/dfs_ev.md) for
the full module breakdown, data-source boundaries, and known limitations.

## Install

```bash
pip install -r requirements.txt
cp .env.example .env   # add OPTICODDS_API_KEY if you have live access
```

## Run (offline, bundled sample data -- no API key needed)

```bash
python -m dfs_ev import --csv data/sample_dk/ncaaf_showdown.csv
python -m dfs_ev match --csv data/sample_dk/ncaaf_showdown.csv
python -m dfs_ev optimize --sport ncaaf --site dk --csv data/sample_dk/ncaaf_showdown.csv --lineups 5
python -m dfs_ev simulate --run <run_id> --iterations 20000
python -m dfs_ev export --run <run_id> --out lineups.csv
```

Add `--live` to `match`/`optimize` (and `slate pull`) to hit the real
OpticOdds API instead of the bundled sample slate, once `OPTICODDS_API_KEY`
is set.

## Optional HTTP API

```bash
uvicorn dfs_ev.api:app --reload
# POST /optimize  {"csv_path": "data/sample_dk/ncaaf_showdown.csv", "lineups": 5}
```

## Docker

```bash
docker compose build
docker compose run --rm dfs_ev optimize --csv data/sample_dk/ncaaf_showdown.csv --lineups 5
docker compose up dfs_ev_api   # HTTP API on :8000
```

## Test

```bash
pytest tests/dfs_ev -q
```
