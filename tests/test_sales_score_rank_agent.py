from trend2success.sales.agents.score_rank_agent import ScoreRankAgent
from trend2success.sales.models import ICPProfile, Lead


def make_lead(**overrides) -> Lead:
    defaults = dict(
        id="ld-1",
        company="Acme",
        contact_name="Jo Lin",
        email="jo@acme.com",
        industry="SaaS",
        source="test",
        notes="Looking for CRM automation.",
        budget=50000,
        company_size=100,
    )
    defaults.update(overrides)
    return Lead(**defaults)


def test_ranks_better_matches_higher():
    agent = ScoreRankAgent()
    icp = ICPProfile(name="ICP", industries=["SaaS"], keywords=["crm", "automation"])
    good = make_lead(id="ld-1", notes="Needs CRM and automation for their sales team.")
    bad = make_lead(id="ld-2", industry="Manufacturing", notes="Building a new factory floor.")

    scores = agent.run([good, bad], icp)

    assert scores[0].lead_id == "ld-1"
    assert scores[0].score > scores[1].score


def test_penalizes_below_min_budget():
    agent = ScoreRankAgent()
    icp = ICPProfile(name="ICP", keywords=["crm"], min_budget=100000)
    lead = make_lead(notes="crm project", budget=50000)

    [score] = agent.run([lead], icp)

    assert score.score < 1.0


def test_no_keywords_yields_zero_score():
    agent = ScoreRankAgent()
    icp = ICPProfile(name="ICP")
    lead = make_lead()

    [score] = agent.run([lead], icp)

    assert score.score == 0.0
