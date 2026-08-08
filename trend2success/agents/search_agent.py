"""Agent 1: Search — collects raw job listings from one or more sources."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from trend2success.models import JobListing

SourceFn = Callable[[str], Iterable[JobListing]]


def sample_source(query: str) -> list[JobListing]:
    """Built-in mock source so the pipeline is runnable without network/API keys."""

    catalog = [
        JobListing(
            id="jl-1",
            title="Senior Python Engineer",
            company="Acme Corp",
            url="https://example.com/jobs/1",
            description="Build backend services in Python, own our data pipeline.",
            source="sample",
            salary=150000,
        ),
        JobListing(
            id="jl-2",
            title="Sales Development Representative",
            company="Northwind Sales",
            url="https://example.com/jobs/2",
            description="Prospect and qualify leads, book demos for account executives.",
            source="sample",
            salary=65000,
        ),
        JobListing(
            id="jl-3",
            title="Frontend Developer",
            company="Contoso",
            url="https://example.com/jobs/3",
            description="React and TypeScript, build customer-facing dashboards.",
            source="sample",
            salary=120000,
        ),
    ]
    query_lower = query.lower()
    return [j for j in catalog if query_lower in j.title.lower() or query_lower in j.description.lower()] or catalog


class SearchAgent:
    """Runs one or more source functions and de-duplicates the results by id."""

    def __init__(self, sources: list[SourceFn] | None = None) -> None:
        self.sources = sources or [sample_source]

    def run(self, query: str) -> list[JobListing]:
        seen: dict[str, JobListing] = {}
        for source in self.sources:
            for listing in source(query):
                seen[listing.id] = listing
        return list(seen.values())
