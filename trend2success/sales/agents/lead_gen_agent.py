"""Stage 1: Lead Generation — collects raw leads from one or more sources."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from trend2success.sales.models import Lead

SourceFn = Callable[[str], Iterable[Lead]]


def sample_source(query: str) -> list[Lead]:
    """Built-in mock source so the funnel is runnable without network/API keys."""

    catalog = [
        Lead(
            id="ld-1",
            company="Bluewave SaaS",
            contact_name="Dana Cole",
            email="dana@bluewave.io",
            industry="SaaS",
            source="sample",
            notes="Evaluating vendors this quarter to automate their sales CRM workflow.",
            budget=45000,
            company_size=120,
        ),
        Lead(
            id="ld-2",
            company="Ferrous Manufacturing",
            contact_name="Miguel Ortiz",
            email="miguel@ferrousmfg.com",
            industry="Manufacturing",
            source="sample",
            notes="Needs better inventory automation and reporting.",
            budget=15000,
            company_size=40,
        ),
        Lead(
            id="ld-3",
            company="Harbor Health Clinics",
            contact_name="",
            email="not-an-email",
            industry="Healthcare",
            source="sample",
            notes="Interested in patient scheduling automation, no budget confirmed yet.",
            budget=None,
            company_size=200,
        ),
        Lead(
            id="ld-4",
            company="Northline Retail",
            contact_name="Priya Shah",
            email="priya@northlineretail.com",
            industry="Retail",
            source="sample",
            notes="Wants CRM and marketing automation to support a new loyalty program.",
            budget=60000,
            company_size=300,
        ),
    ]
    query_lower = query.lower()
    return [
        lead for lead in catalog if query_lower in lead.industry.lower() or query_lower in lead.notes.lower()
    ] or catalog


class LeadGenAgent:
    """Runs one or more source functions and de-duplicates the results by id."""

    def __init__(self, sources: list[SourceFn] | None = None) -> None:
        self.sources = sources or [sample_source]

    def run(self, query: str) -> list[Lead]:
        seen: dict[str, Lead] = {}
        for source in self.sources:
            for lead in source(query):
                seen[lead.id] = lead
        return list(seen.values())
