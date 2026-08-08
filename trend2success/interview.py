"""Interview / Sales Call stage — schedules the next live touchpoint for a queued application."""

from __future__ import annotations

from datetime import datetime, timedelta

from trend2success.models import ApplicationStatus, InterviewEvent
from trend2success.queue_store import QueueStore

SALES_TITLE_HINTS = ("sales", "sdr", "account executive", "business development")


def _infer_kind(title: str) -> str:
    title_lower = title.lower()
    return "sales_call" if any(hint in title_lower for hint in SALES_TITLE_HINTS) else "interview"


class InterviewScheduler:
    def __init__(self, queue_store: QueueStore, delay_days: int = 3) -> None:
        self.queue_store = queue_store
        self.delay_days = delay_days

    def schedule(self, application_ids: list[str] | None = None) -> list[InterviewEvent]:
        applications = self.queue_store.list()
        if application_ids is not None:
            applications = [a for a in applications if a.id in application_ids]

        events = []
        for application in applications:
            if application.status != ApplicationStatus.QUEUED:
                continue
            kind = _infer_kind(application.listing.title)
            event = InterviewEvent(
                application_id=application.id,
                kind=kind,
                scheduled_at=datetime.utcnow() + timedelta(days=self.delay_days),
            )
            events.append(event)
            self.queue_store.update_status(application.id, ApplicationStatus.INTERVIEW_SCHEDULED)
        return events
