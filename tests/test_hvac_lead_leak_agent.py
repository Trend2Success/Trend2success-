from trend2success.hvac.lead_leak_agent import LeadLeakAgent
from trend2success.hvac.models import HVACProspect


def make_prospect(**overrides) -> HVACProspect:
    defaults = dict(
        id="hp-1",
        name="Alex",
        address="123 Main St",
        phone="555-0100",
        email="alex@example.com",
        system_age_years=5,
        monthly_bill=100.0,
        sqft=1500,
    )
    defaults.update(overrides)
    return HVACProspect(**defaults)


def test_old_system_is_flagged():
    agent = LeadLeakAgent()
    [result] = agent.run([make_prospect(system_age_years=15)])
    assert result.is_leaking
    assert any("years old" in s for s in result.signals)


def test_high_cost_per_sqft_is_flagged():
    agent = LeadLeakAgent()
    [result] = agent.run([make_prospect(system_age_years=2, monthly_bill=400.0, sqft=1200)])
    assert result.is_leaking
    assert any("cost" in s for s in result.signals)


def test_efficient_recent_system_is_not_flagged():
    agent = LeadLeakAgent()
    [result] = agent.run([make_prospect(system_age_years=2, monthly_bill=100.0, sqft=1500)])
    assert not result.is_leaking
    assert result.signals == []
    assert result.leak_score == 0.0


def test_leak_score_scales_with_signal_count():
    agent = LeadLeakAgent()
    [result] = agent.run([make_prospect(system_age_years=15, monthly_bill=400.0, sqft=1200)])
    assert len(result.signals) == 2
    assert result.leak_score == 1.0
