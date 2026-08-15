"""Stage 3: Score & Rank — scores qualified leads against an Ideal Customer Profile."""

from __future__ import annotations

from trend2success.sales.models import ICPProfile, Lead, LeadScore

INDUSTRY_MATCH_BONUS = 0.25


class ScoreRankAgent:
    def run(self, leads: list[Lead], icp: ICPProfile) -> list[LeadScore]:
        keywords = {k.lower() for k in icp.keywords}
        industries = {i.lower() for i in icp.industries}

        scores = []
        for lead in leads:
            haystack = f"{lead.industry} {lead.notes}".lower()
            matched = sorted(k for k in keywords if k in haystack)

            score = len(matched) / len(keywords) if keywords else 0.0
            if industries and lead.industry.lower() in industries:
                score = min(1.0, score + INDUSTRY_MATCH_BONUS)

            if icp.min_budget and lead.budget is not None and lead.budget < icp.min_budget:
                score *= 0.5  # penalize but don't exclude, in case the budget is flexible
            if icp.min_company_size and lead.company_size is not None and lead.company_size < icp.min_company_size:
                score *= 0.5

            scores.append(LeadScore(lead_id=lead.id, score=round(score, 4), matched_keywords=matched))

        return sorted(scores, key=lambda s: s.score, reverse=True)
