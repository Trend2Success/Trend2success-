"""Stage 6: $350/month support — enrolls a newly installed customer into recurring support."""

from __future__ import annotations

from trend2success.hvac.lead_store import LeadStore
from trend2success.hvac.models import LeadStatus, SupportSubscription

SUPPORT_MONTHLY_PRICE = 350.0


class SupportAgent:
    def __init__(self, lead_store: LeadStore) -> None:
        self.lead_store = lead_store

    def enroll(self, prospect_id: str) -> SupportSubscription:
        prospect = self.lead_store.get(prospect_id)
        if prospect is None:
            raise KeyError(f"no prospect with id {prospect_id!r}")
        if prospect.status != LeadStatus.INSTALLED:
            raise ValueError(
                f"prospect {prospect_id!r} is not eligible for support (status={prospect.status.value})"
            )

        subscription = SupportSubscription(prospect_id=prospect_id, monthly_amount=SUPPORT_MONTHLY_PRICE)
        self.lead_store.update_status(prospect_id, LeadStatus.SUPPORT_ACTIVE)
        return subscription
