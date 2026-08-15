from trend2success.sales.agents.qualify_agent import QualifyAgent
from trend2success.sales.models import Lead


def make_lead(**overrides) -> Lead:
    defaults = dict(
        id="ld-1",
        company="Acme",
        contact_name="Jo Lin",
        email="jo@acme.com",
        industry="SaaS",
        source="test",
        budget=20000,
    )
    defaults.update(overrides)
    return Lead(**defaults)


def test_valid_lead_passes():
    agent = QualifyAgent()
    [result] = agent.run([make_lead()])
    assert result.is_qualified
    assert result.reasons == []


def test_missing_fields_are_flagged():
    agent = QualifyAgent()
    lead = make_lead(contact_name="", email="not-an-email", budget=None)
    [result] = agent.run([lead])
    assert not result.is_qualified
    assert "missing contact name" in result.reasons
    assert "invalid email" in result.reasons
    assert "no budget specified" in result.reasons


def test_duplicate_email_is_flagged():
    agent = QualifyAgent()
    a = make_lead(id="ld-1")
    b = make_lead(id="ld-2")
    results = agent.run([a, b])
    assert results[0].is_qualified
    assert not results[1].is_qualified
    assert "duplicate email" in results[1].reasons
