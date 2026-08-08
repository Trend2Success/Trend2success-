"""Orchestrates the flow: Search -> Verify -> Match & Rank -> Application Queue.

Interview scheduling and follow-up happen afterwards, on their own schedule
(see interview.py / followup.py), since they depend on real-world events
that don't happen synchronously with the search pipeline.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from trend2success.agents import MatchRankAgent, SearchAgent, VerifyAgent
from trend2success.models import Application, CandidateProfile, JobListing, MatchScore, VerificationResult
from trend2success.queue_store import QueueStore


@dataclass
class PipelineResult:
    listings_found: list[JobListing] = field(default_factory=list)
    verification_results: list[VerificationResult] = field(default_factory=list)
    match_scores: list[MatchScore] = field(default_factory=list)
    applications_queued: list[Application] = field(default_factory=list)


class Pipeline:
    def __init__(
        self,
        search_agent: SearchAgent | None = None,
        verify_agent: VerifyAgent | None = None,
        match_rank_agent: MatchRankAgent | None = None,
        queue_store: QueueStore | None = None,
        top_n: int = 5,
        min_score: float = 0.0,
    ) -> None:
        self.search_agent = search_agent or SearchAgent()
        self.verify_agent = verify_agent or VerifyAgent()
        self.match_rank_agent = match_rank_agent or MatchRankAgent()
        self.queue_store = queue_store or QueueStore()
        self.top_n = top_n
        self.min_score = min_score

    def run(self, query: str, profile: CandidateProfile) -> PipelineResult:
        listings = self.search_agent.run(query)

        verification_results = self.verify_agent.run(listings)
        valid_ids = {r.listing_id for r in verification_results if r.is_valid}
        verified_listings = [listing for listing in listings if listing.id in valid_ids]

        match_scores = self.match_rank_agent.run(verified_listings, profile)
        listings_by_id = {listing.id: listing for listing in verified_listings}

        applications = []
        for match in match_scores[: self.top_n]:
            if match.score < self.min_score:
                continue
            application = Application(
                id=str(uuid.uuid4()),
                listing=listings_by_id[match.listing_id],
                match_score=match.score,
            )
            self.queue_store.add(application)
            applications.append(application)

        return PipelineResult(
            listings_found=listings,
            verification_results=verification_results,
            match_scores=match_scores,
            applications_queued=applications,
        )
