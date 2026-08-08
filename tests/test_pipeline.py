from trend2success.models import CandidateProfile
from trend2success.pipeline import Pipeline
from trend2success.queue_store import QueueStore


def test_pipeline_runs_end_to_end_and_queues_applications(tmp_path):
    pipeline = Pipeline(queue_store=QueueStore(tmp_path / "queue.json"), top_n=2)
    profile = CandidateProfile(name="Troy", skills=["python", "django"])

    result = pipeline.run("engineer", profile)

    assert result.listings_found
    assert result.verification_results
    assert result.match_scores
    assert 0 < len(result.applications_queued) <= 2
    assert pipeline.queue_store.list() == result.applications_queued


def test_pipeline_respects_min_score(tmp_path):
    pipeline = Pipeline(queue_store=QueueStore(tmp_path / "queue.json"), top_n=5, min_score=0.99)
    profile = CandidateProfile(name="Troy", skills=["nonexistent-skill"])

    result = pipeline.run("engineer", profile)

    assert result.applications_queued == []
