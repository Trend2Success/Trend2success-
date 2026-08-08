"""Agent 3: Match & Rank — scores verified listings against a candidate profile."""

from __future__ import annotations

from trend2success.models import CandidateProfile, JobListing, MatchScore


class MatchRankAgent:
    def run(self, listings: list[JobListing], profile: CandidateProfile) -> list[MatchScore]:
        keywords = {k.lower() for k in (*profile.skills, *profile.keywords)}
        scores = []
        for listing in listings:
            haystack = f"{listing.title} {listing.description}".lower()
            matched = sorted(k for k in keywords if k in haystack)

            score = len(matched) / len(keywords) if keywords else 0.0
            if profile.min_salary and listing.salary is not None:
                if listing.salary < profile.min_salary:
                    score *= 0.5  # penalize but don't exclude, in case the listing is negotiable

            scores.append(MatchScore(listing_id=listing.id, score=round(score, 4), matched_keywords=matched))

        return sorted(scores, key=lambda s: s.score, reverse=True)
