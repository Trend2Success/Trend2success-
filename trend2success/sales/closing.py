"""Closing stage — sends the proposal, tracks negotiation, and closes the deal won/lost."""

from __future__ import annotations

from datetime import datetime

from trend2success.sales.deal_store import DealStore
from trend2success.sales.models import ClosingEvent, DealStage

OUTCOME_TO_STAGE = {
    "negotiating": DealStage.NEGOTIATION,
    "won": DealStage.CLOSED_WON,
    "lost": DealStage.CLOSED_LOST,
}


class ClosingAgent:
    def __init__(self, deal_store: DealStore) -> None:
        self.deal_store = deal_store

    def send_proposal(self, deal_ids: list[str] | None = None) -> list[str]:
        deals = self.deal_store.list()
        if deal_ids is not None:
            deals = [d for d in deals if d.id in deal_ids]

        proposed = []
        for deal in deals:
            if deal.stage != DealStage.DEMO_SCHEDULED:
                continue
            self.deal_store.update_stage(deal.id, DealStage.PROPOSAL_SENT)
            proposed.append(deal.id)
        return proposed

    def close(self, deal_id: str, outcome: str, value: int | None = None, notes: str = "") -> ClosingEvent:
        deal = self.deal_store.get(deal_id)
        if deal is None:
            raise KeyError(f"no deal in pipeline with id {deal_id!r}")
        if deal.stage not in (DealStage.PROPOSAL_SENT, DealStage.NEGOTIATION):
            raise ValueError(f"deal {deal_id!r} is not awaiting closing (stage={deal.stage.value})")
        if outcome not in OUTCOME_TO_STAGE:
            raise ValueError(f"unknown outcome {outcome!r}, expected one of {sorted(OUTCOME_TO_STAGE)}")

        event = ClosingEvent(deal_id=deal_id, closed_at=datetime.utcnow(), outcome=outcome, value=value, notes=notes)

        self.deal_store.update_stage(deal_id, OUTCOME_TO_STAGE[outcome])
        if value is not None:
            self.deal_store.update_value(deal_id, value)

        return event
