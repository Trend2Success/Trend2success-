"""Stage 1: 25 HVAC prospects — collects raw leads from one or more sources."""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable

from trend2success.hvac.models import HVACProspect

SourceFn = Callable[[], Iterable[HVACProspect]]

DEFAULT_PROSPECT_COUNT = 25
SQFT_CHOICES = [1200, 1500, 1800, 2200, 2600, 3000]


def sample_source(count: int = DEFAULT_PROSPECT_COUNT, seed: int = 42) -> list[HVACProspect]:
    """Built-in mock source so the funnel is runnable without a real CRM/lead feed."""

    rng = random.Random(seed)
    prospects = []
    for i in range(count):
        sqft = rng.choice(SQFT_CHOICES)
        prospects.append(
            HVACProspect(
                id=f"hp-{i + 1}",
                name=f"Prospect {i + 1}",
                address=f"{100 + i} Main St",
                phone=f"555-{1000 + i:04d}",
                email=f"prospect{i + 1}@example.com",
                system_age_years=rng.randint(1, 20),
                monthly_bill=round(sqft * rng.uniform(0.08, 0.22), 2),
                sqft=sqft,
            )
        )
    return prospects


class ProspectSource:
    """Runs one or more source functions and de-duplicates prospects by id."""

    def __init__(self, sources: list[SourceFn] | None = None) -> None:
        self.sources = sources or [sample_source]

    def run(self) -> list[HVACProspect]:
        seen: dict[str, HVACProspect] = {}
        for source in self.sources:
            for prospect in source():
                seen[prospect.id] = prospect
        return list(seen.values())
