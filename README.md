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

## Also in this repo

[`dk_ev/`](dk_ev/README.md) is a separate, standalone project: a DraftKings
DFS lineup optimizer that ranks lineups by simulated Expected Value. See
[dk_ev/README.md](dk_ev/README.md) for its own install/run instructions.
