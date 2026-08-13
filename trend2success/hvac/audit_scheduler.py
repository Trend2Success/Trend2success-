"""Stage 4: 20-minute audit call — schedules the on-site audit for messaged prospects."""

from __future__ import annotations

from datetime import datetime, timedelta

from trend2success.hvac.lead_store import LeadStore
from trend2success.hvac.models import AuditCall, LeadStatus

AUDIT_DURATION_MINUTES = 20


class AuditScheduler:
    def __init__(self, lead_store: LeadStore, delay_days: int = 1) -> None:
        self.lead_store = lead_store
        self.delay_days = delay_days

    def schedule(self, prospect_ids: list[str] | None = None) -> list[AuditCall]:
        prospects = self.lead_store.list()
        if prospect_ids is not None:
            prospects = [p for p in prospects if p.id in prospect_ids]

        calls = []
        for prospect in prospects:
            if prospect.status != LeadStatus.MESSAGED:
                continue
            call = AuditCall(
                prospect_id=prospect.id,
                scheduled_at=datetime.utcnow() + timedelta(days=self.delay_days),
                duration_minutes=AUDIT_DURATION_MINUTES,
            )
            calls.append(call)
            self.lead_store.update_status(prospect.id, LeadStatus.AUDIT_SCHEDULED)
        return calls
