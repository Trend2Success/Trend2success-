import pytest

from trend2success.followup import FollowUpAgent
from trend2success.interview import InterviewScheduler
from trend2success.models import Application, ApplicationStatus, JobListing
from trend2success.queue_store import QueueStore


def make_application(app_id="app-1", title="Engineer") -> Application:
    listing = JobListing(
        id="jl-1",
        title=title,
        company="Acme",
        url="https://example.com/jobs/1",
        description="A sufficiently long description of the role.",
        source="test",
    )
    return Application(id=app_id, listing=listing, match_score=0.8)


def test_scheduler_marks_queued_applications_as_scheduled(tmp_path):
    store = QueueStore(tmp_path / "queue.json")
    store.add(make_application())
    scheduler = InterviewScheduler(store, delay_days=1)

    [event] = scheduler.schedule()

    assert event.application_id == "app-1"
    assert event.kind == "interview"
    assert store.get("app-1").status == ApplicationStatus.INTERVIEW_SCHEDULED


def test_scheduler_infers_sales_call_for_sales_titles(tmp_path):
    store = QueueStore(tmp_path / "queue.json")
    store.add(make_application(title="Sales Development Representative"))
    scheduler = InterviewScheduler(store)

    [event] = scheduler.schedule()

    assert event.kind == "sales_call"


def test_scheduler_skips_non_queued_applications(tmp_path):
    store = QueueStore(tmp_path / "queue.json")
    store.add(make_application())
    store.update_status("app-1", ApplicationStatus.REJECTED)
    scheduler = InterviewScheduler(store)

    assert scheduler.schedule() == []


def test_followup_records_outcome_and_updates_status(tmp_path):
    store = QueueStore(tmp_path / "queue.json")
    store.add(make_application())
    store.update_status("app-1", ApplicationStatus.INTERVIEW_SCHEDULED)
    agent = FollowUpAgent(store)

    follow_up = agent.record("app-1", outcome="offer", notes="Great fit")

    assert follow_up.outcome == "offer"
    assert store.get("app-1").status == ApplicationStatus.OFFER


def test_followup_rejects_before_interview_scheduled(tmp_path):
    store = QueueStore(tmp_path / "queue.json")
    store.add(make_application())
    agent = FollowUpAgent(store)

    with pytest.raises(ValueError):
        agent.record("app-1", outcome="offer")
