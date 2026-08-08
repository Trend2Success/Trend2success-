"""Agent 2: Verify — filters out malformed, duplicate, or low-quality listings."""

from __future__ import annotations

from trend2success.models import JobListing, VerificationResult

MIN_DESCRIPTION_LENGTH = 20


class VerifyAgent:
    def run(self, listings: list[JobListing]) -> list[VerificationResult]:
        seen_urls: set[str] = set()
        results = []
        for listing in listings:
            reasons = []
            if not listing.title.strip():
                reasons.append("missing title")
            if not listing.company.strip():
                reasons.append("missing company")
            if not listing.url.startswith(("http://", "https://")):
                reasons.append("invalid url")
            if len(listing.description) < MIN_DESCRIPTION_LENGTH:
                reasons.append("description too short")
            if listing.url in seen_urls:
                reasons.append("duplicate url")
            seen_urls.add(listing.url)

            results.append(VerificationResult(listing_id=listing.id, is_valid=not reasons, reasons=reasons))
        return results
