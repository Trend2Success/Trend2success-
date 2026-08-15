import pytest

from trend2success.sales.closing import ClosingAgent
from trend2success.sales.deal_store import DealStore
from trend2success.sales.demo import DemoScheduler
from trend2success.sales.followup import FollowUpAgent
from trend2success.sales.models import Deal, DealStage, Lead
from trend2success.sales.outreach import OutreachAgent


def make_deal(deal_id="deal-1", stage=DealStage.QUALIFIED) -> Deal:
    lead = Lead(
        id="ld-1",
        company="Acme",
        contact_name="Jo Lin",
        email="jo@acme.com",
        industry="SaaS",
        source="test",
        budget=50000,
    )
    return Deal(id=deal_id, lead=lead, fit_score=0.8, stage=stage)


def test_outreach_contacts_qualified_deals_only(tmp_path):
    store = DealStore(tmp_path / "deals.json")
    store.add(make_deal(stage=DealStage.QUALIFIED))
    store.add(make_deal("deal-2", stage=DealStage.NEW))
    agent = OutreachAgent(store)

    touches = agent.run()

    assert [t.deal_id for t in touches] == ["deal-1"]
    assert store.get("deal-1").stage == DealStage.CONTACTED
    assert store.get("deal-2").stage == DealStage.NEW


def test_demo_scheduler_moves_contacted_deals_to_scheduled(tmp_path):
    store = DealStore(tmp_path / "deals.json")
    store.add(make_deal(stage=DealStage.CONTACTED))
    scheduler = DemoScheduler(store, delay_days=1)

    [event] = scheduler.schedule()

    assert event.deal_id == "deal-1"
    assert store.get("deal-1").stage == DealStage.DEMO_SCHEDULED


def test_closing_agent_full_flow(tmp_path):
    store = DealStore(tmp_path / "deals.json")
    store.add(make_deal(stage=DealStage.DEMO_SCHEDULED))
    agent = ClosingAgent(store)

    proposed = agent.send_proposal()
    assert proposed == ["deal-1"]
    assert store.get("deal-1").stage == DealStage.PROPOSAL_SENT

    event = agent.close("deal-1", outcome="negotiating")
    assert event.outcome == "negotiating"
    assert store.get("deal-1").stage == DealStage.NEGOTIATION

    event = agent.close("deal-1", outcome="won", value=42000, notes="Signed annual contract")
    assert event.outcome == "won"
    assert store.get("deal-1").stage == DealStage.CLOSED_WON
    assert store.get("deal-1").value == 42000


def test_closing_agent_rejects_close_before_proposal(tmp_path):
    store = DealStore(tmp_path / "deals.json")
    store.add(make_deal(stage=DealStage.QUALIFIED))
    agent = ClosingAgent(store)

    with pytest.raises(ValueError):
        agent.close("deal-1", outcome="won")


def test_followup_onboards_closed_won_deal(tmp_path):
    store = DealStore(tmp_path / "deals.json")
    store.add(make_deal(stage=DealStage.CLOSED_WON))
    agent = FollowUpAgent(store)

    follow_up = agent.record("deal-1", outcome="onboarding_call_booked", notes="Kickoff scheduled")

    assert follow_up.outcome == "onboarding_call_booked"
    assert store.get("deal-1").stage == DealStage.ONBOARDED


def test_followup_rejects_before_closed_won(tmp_path):
    store = DealStore(tmp_path / "deals.json")
    store.add(make_deal(stage=DealStage.NEGOTIATION))
    agent = FollowUpAgent(store)

    with pytest.raises(ValueError):
        agent.record("deal-1", outcome="onboarding_call_booked")
