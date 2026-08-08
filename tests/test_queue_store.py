from trend2success.models import Application, ApplicationStatus, JobListing
from trend2success.queue_store import QueueStore


def make_application(app_id="app-1") -> Application:
    listing = JobListing(
        id="jl-1",
        title="Engineer",
        company="Acme",
        url="https://example.com/jobs/1",
        description="A sufficiently long description of the role.",
        source="test",
    )
    return Application(id=app_id, listing=listing, match_score=0.8)


def test_add_and_get_roundtrips(tmp_path):
    store = QueueStore(tmp_path / "queue.json")
    application = make_application()
    store.add(application)

    fetched = store.get(application.id)
    assert fetched is not None
    assert fetched.id == application.id
    assert fetched.listing.title == application.listing.title
    assert fetched.status == ApplicationStatus.QUEUED


def test_list_returns_all_applications(tmp_path):
    store = QueueStore(tmp_path / "queue.json")
    store.add(make_application("app-1"))
    store.add(make_application("app-2"))

    assert {a.id for a in store.list()} == {"app-1", "app-2"}


def test_update_status_persists(tmp_path):
    store = QueueStore(tmp_path / "queue.json")
    store.add(make_application())

    store.update_status("app-1", ApplicationStatus.INTERVIEW_SCHEDULED)

    assert store.get("app-1").status == ApplicationStatus.INTERVIEW_SCHEDULED


def test_update_status_missing_id_raises(tmp_path):
    store = QueueStore(tmp_path / "queue.json")
    try:
        store.update_status("missing", ApplicationStatus.OFFER)
        assert False, "expected KeyError"
    except KeyError:
        pass
