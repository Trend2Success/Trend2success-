"""Stage 5: $2,000 installation — closes the deal after a completed audit call."""

from __future__ import annotations

from trend2success.hvac.lead_store import LeadStore
from trend2success.hvac.models import InstallationDeal, LeadStatus

INSTALL_PRICE = 2000.0


class InstallationAgent:
    def __init__(self, lead_store: LeadStore) -> None:
        self.lead_store = lead_store

    def close(self, prospect_id: str, accepted: bool) -> InstallationDeal | None:
        prospect = self.lead_store.get(prospect_id)
        if prospect is None:
            raise KeyError(f"no prospect with id {prospect_id!r}")
        if prospect.status != LeadStatus.AUDIT_SCHEDULED:
            raise ValueError(
                f"prospect {prospect_id!r} has not completed an audit call (status={prospect.status.value})"
            )

        if not accepted:
            self.lead_store.update_status(prospect_id, LeadStatus.LOST)
            return None

        deal = InstallationDeal(prospect_id=prospect_id, amount=INSTALL_PRICE)
        self.lead_store.update_status(prospect_id, LeadStatus.INSTALLED)
        return deal
