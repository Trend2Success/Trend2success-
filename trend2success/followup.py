"""Follow-up & Results stage — records the outcome after an interview/sales call."""

from __future__ import annotations

from datetime import datetime

from trend2success.models import ApplicationStatus, FollowUp
from trend2success.queue_store import QueueStore


class FollowUpAgent:
    def __init__(self, queue_store: QueueStore) -> None:
        self.queue_store = queue_store

    def record(self, application_id: str, outcome: str, notes: str = "") -> FollowUp:
        application = self.queue_store.get(application_id)
        if application is None:
            raise KeyError(f"no application queued with id {application_id!r}")
        if application.status != ApplicationStatus.INTERVIEW_SCHEDULED:
            raise ValueError(
                f"application {application_id!r} is not awaiting follow-up (status={application.status.value})"
            )

        follow_up = FollowUp(
            application_id=application_id,
            followed_up_at=datetime.utcnow(),
            outcome=outcome,
            notes=notes,
        )

        next_status = ApplicationStatus.OFFER if outcome == "offer" else ApplicationStatus.FOLLOWED_UP
        if outcome == "rejected":
            next_status = ApplicationStatus.REJECTED
        self.queue_store.update_status(application_id, next_status)

        return follow_up
