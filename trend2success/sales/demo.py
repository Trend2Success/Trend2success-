"""Demo stage — schedules the discovery call / product demo for contacted deals."""

from __future__ import annotations

from datetime import datetime, timedelta

from trend2success.sales.deal_store import DealStore
from trend2success.sales.models import DealStage, DemoEvent


class DemoScheduler:
    def __init__(self, deal_store: DealStore, delay_days: int = 2) -> None:
        self.deal_store = deal_store
        self.delay_days = delay_days

    def schedule(self, deal_ids: list[str] | None = None) -> list[DemoEvent]:
        deals = self.deal_store.list()
        if deal_ids is not None:
            deals = [d for d in deals if d.id in deal_ids]

        events = []
        for deal in deals:
            if deal.stage != DealStage.CONTACTED:
                continue
            event = DemoEvent(
                deal_id=deal.id,
                scheduled_at=datetime.utcnow() + timedelta(days=self.delay_days),
            )
            events.append(event)
            self.deal_store.update_stage(deal.id, DealStage.DEMO_SCHEDULED)
        return events
