"""Orchestrates the funnel: Lead Gen -> Qualify -> Score & Rank -> Deal Pipeline.

Outreach, demo scheduling, closing, and follow-up happen afterwards, on their
own schedule (see outreach.py / demo.py / closing.py / followup.py), since
they depend on real-world events that don't happen synchronously with the
lead-gen pipeline.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from trend2success.sales.agents import LeadGenAgent, QualifyAgent, ScoreRankAgent
from trend2success.sales.deal_store import DealStore
from trend2success.sales.models import Deal, DealStage, ICPProfile, Lead, LeadScore, QualificationResult


@dataclass
class SalesPipelineResult:
    leads_found: list[Lead] = field(default_factory=list)
    qualification_results: list[QualificationResult] = field(default_factory=list)
    lead_scores: list[LeadScore] = field(default_factory=list)
    deals_queued: list[Deal] = field(default_factory=list)


class SalesPipeline:
    def __init__(
        self,
        lead_gen_agent: LeadGenAgent | None = None,
        qualify_agent: QualifyAgent | None = None,
        score_rank_agent: ScoreRankAgent | None = None,
        deal_store: DealStore | None = None,
        top_n: int = 5,
        min_score: float = 0.0,
    ) -> None:
        self.lead_gen_agent = lead_gen_agent or LeadGenAgent()
        self.qualify_agent = qualify_agent or QualifyAgent()
        self.score_rank_agent = score_rank_agent or ScoreRankAgent()
        self.deal_store = deal_store or DealStore()
        self.top_n = top_n
        self.min_score = min_score

    def run(self, query: str, icp: ICPProfile) -> SalesPipelineResult:
        leads = self.lead_gen_agent.run(query)

        qualification_results = self.qualify_agent.run(leads)
        qualified_ids = {r.lead_id for r in qualification_results if r.is_qualified}
        qualified_leads = [lead for lead in leads if lead.id in qualified_ids]

        lead_scores = self.score_rank_agent.run(qualified_leads, icp)
        leads_by_id = {lead.id: lead for lead in qualified_leads}

        deals = []
        for score in lead_scores[: self.top_n]:
            if score.score < self.min_score:
                continue
            deal = Deal(
                id=str(uuid.uuid4()),
                lead=leads_by_id[score.lead_id],
                fit_score=score.score,
                stage=DealStage.QUALIFIED,
            )
            self.deal_store.add(deal)
            deals.append(deal)

        return SalesPipelineResult(
            leads_found=leads,
            qualification_results=qualification_results,
            lead_scores=lead_scores,
            deals_queued=deals,
        )
