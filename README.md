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

## Sales funnel

A full, end-to-end B2B sales workflow — lead generation through closing and post-sale
onboarding — lives under `trend2success/sales/`. See
[docs/sales_funnel.md](docs/sales_funnel.md) for the flow diagram, stage-by-stage module
breakdown, and usage examples.

```bash
python -m trend2success.sales.main \
  --query automation --industries "SaaS,Retail" --keywords "crm,automation" --top-n 5
```

This runs Lead Generation → Qualify → Score & Rank against an `ICPProfile` and queues
deals to `data/deal_pipeline.json`. From there, `OutreachAgent`, `DemoScheduler`,
`ClosingAgent`, and `FollowUpAgent` drive each deal through
`contacted → demo_scheduled → proposal_sent → negotiation → closed_won/closed_lost → onboarded`.

## Test

```bash
pytest
```
