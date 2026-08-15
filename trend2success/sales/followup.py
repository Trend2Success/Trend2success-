"""Follow-up stage — records the post-sale outcome and moves a won deal to onboarding."""

from __future__ import annotations

from datetime import datetime

from trend2success.sales.deal_store import DealStore
from trend2success.sales.models import DealStage, FollowUp


class FollowUpAgent:
    def __init__(self, deal_store: DealStore) -> None:
        self.deal_store = deal_store

    def record(self, deal_id: str, outcome: str, notes: str = "") -> FollowUp:
        deal = self.deal_store.get(deal_id)
        if deal is None:
            raise KeyError(f"no deal in pipeline with id {deal_id!r}")
        if deal.stage != DealStage.CLOSED_WON:
            raise ValueError(f"deal {deal_id!r} is not awaiting follow-up (stage={deal.stage.value})")

        follow_up = FollowUp(deal_id=deal_id, followed_up_at=datetime.utcnow(), outcome=outcome, notes=notes)
        self.deal_store.update_stage(deal_id, DealStage.ONBOARDED)
        return follow_up
