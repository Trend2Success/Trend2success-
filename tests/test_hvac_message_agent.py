from trend2success.hvac.message_agent import MessageAgent
from trend2success.hvac.models import HVACProspect, LeadLeakResult


def make_prospect(**overrides) -> HVACProspect:
    defaults = dict(
        id="hp-1",
        name="Alex",
        address="123 Main St",
        phone="555-0100",
        email="alex@example.com",
        system_age_years=15,
        monthly_bill=100.0,
        sqft=1500,
    )
    defaults.update(overrides)
    return HVACProspect(**defaults)


def test_message_drafted_only_for_leaking_prospects():
    agent = MessageAgent()
    leaking = make_prospect(id="hp-1")
    clean = make_prospect(id="hp-2", name="Sam")
    leak_results = [
        LeadLeakResult(prospect_id="hp-1", is_leaking=True, leak_score=0.5, signals=["system is 15 years old"]),
        LeadLeakResult(prospect_id="hp-2", is_leaking=False, leak_score=0.0, signals=[]),
    ]

    [message] = agent.run([leaking, clean], leak_results)

    assert message.prospect_id == "hp-1"
    assert "Alex" in message.body
    assert "system is 15 years old" in message.body
    assert message.channel == "email"


def test_no_messages_when_nothing_is_leaking():
    agent = MessageAgent()
    prospect = make_prospect()
    leak_results = [LeadLeakResult(prospect_id="hp-1", is_leaking=False, leak_score=0.0, signals=[])]

    assert agent.run([prospect], leak_results) == []
