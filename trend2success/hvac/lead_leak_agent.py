"""Stage 2: 2-minute lead-leak check — quickly flags prospects likely losing money to an inefficient system."""

from __future__ import annotations

from trend2success.hvac.models import HVACProspect, LeadLeakResult

OLD_SYSTEM_YEARS = 10
HIGH_COST_PER_SQFT = 0.15


class LeadLeakAgent:
    def run(self, prospects: list[HVACProspect]) -> list[LeadLeakResult]:
        results = []
        for prospect in prospects:
            signals = []
            if prospect.system_age_years >= OLD_SYSTEM_YEARS:
                signals.append(f"system is {prospect.system_age_years} years old")

            cost_per_sqft = prospect.monthly_bill / prospect.sqft if prospect.sqft else 0.0
            if cost_per_sqft > HIGH_COST_PER_SQFT:
                signals.append(
                    f"energy cost of ${cost_per_sqft:.2f}/sqft exceeds ${HIGH_COST_PER_SQFT:.2f}/sqft benchmark"
                )

            results.append(
                LeadLeakResult(
                    prospect_id=prospect.id,
                    is_leaking=bool(signals),
                    leak_score=min(len(signals) / 2, 1.0),
                    signals=signals,
                )
            )
        return results
