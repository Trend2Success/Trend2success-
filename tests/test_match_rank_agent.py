from trend2success.agents.match_rank_agent import MatchRankAgent
from trend2success.models import CandidateProfile, JobListing


def make_listing(**overrides) -> JobListing:
    defaults = dict(
        id="jl-1",
        title="Python Engineer",
        company="Acme",
        url="https://example.com/jobs/1",
        description="Work with Python and Django.",
        source="test",
        salary=100000,
    )
    defaults.update(overrides)
    return JobListing(**defaults)


def test_ranks_better_matches_higher():
    agent = MatchRankAgent()
    profile = CandidateProfile(name="T", skills=["python", "django"])
    good = make_listing(id="jl-1", description="Python and Django role.")
    bad = make_listing(id="jl-2", title="Painter", description="Paint houses.")

    scores = agent.run([good, bad], profile)

    assert scores[0].listing_id == "jl-1"
    assert scores[0].score > scores[1].score


def test_penalizes_below_min_salary():
    agent = MatchRankAgent()
    profile = CandidateProfile(name="T", skills=["python"], min_salary=150000)
    listing = make_listing(salary=100000)

    [score] = agent.run([listing], profile)

    assert score.score < 1.0


def test_no_keywords_yields_zero_score():
    agent = MatchRankAgent()
    profile = CandidateProfile(name="T", skills=[])
    listing = make_listing()

    [score] = agent.run([listing], profile)

    assert score.score == 0.0
