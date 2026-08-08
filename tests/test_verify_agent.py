from trend2success.agents.verify_agent import VerifyAgent
from trend2success.models import JobListing


def make_listing(**overrides) -> JobListing:
    defaults = dict(
        id="jl-1",
        title="Engineer",
        company="Acme",
        url="https://example.com/jobs/1",
        description="A sufficiently long description of the role.",
        source="test",
    )
    defaults.update(overrides)
    return JobListing(**defaults)


def test_valid_listing_passes():
    agent = VerifyAgent()
    [result] = agent.run([make_listing()])
    assert result.is_valid
    assert result.reasons == []


def test_missing_fields_are_flagged():
    agent = VerifyAgent()
    listing = make_listing(title="", url="not-a-url", description="short")
    [result] = agent.run([listing])
    assert not result.is_valid
    assert "missing title" in result.reasons
    assert "invalid url" in result.reasons
    assert "description too short" in result.reasons


def test_duplicate_url_is_flagged():
    agent = VerifyAgent()
    a = make_listing(id="jl-1")
    b = make_listing(id="jl-2")
    results = agent.run([a, b])
    assert results[0].is_valid
    assert not results[1].is_valid
    assert "duplicate url" in results[1].reasons
