"""Outreach stage — sends the initial touch to qualified deals to start a conversation."""

from __future__ import annotations

from datetime import datetime

from trend2success.sales.deal_store import DealStore
from trend2success.sales.models import DealStage, OutreachTouch


class OutreachAgent:
    def __init__(self, deal_store: DealStore, channel: str = "email") -> None:
        self.deal_store = deal_store
        self.channel = channel

    def run(self, deal_ids: list[str] | None = None) -> list[OutreachTouch]:
        deals = self.deal_store.list()
        if deal_ids is not None:
            deals = [d for d in deals if d.id in deal_ids]

        touches = []
        for deal in deals:
            if deal.stage != DealStage.QUALIFIED:
                continue
            touch = OutreachTouch(
                deal_id=deal.id,
                channel=self.channel,
                sent_at=datetime.utcnow(),
                message=f"Intro touch to {deal.lead.contact_name} at {deal.lead.company}",
            )
            touches.append(touch)
            self.deal_store.update_stage(deal.id, DealStage.CONTACTED)
        return touches
