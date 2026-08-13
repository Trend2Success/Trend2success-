import pytest

from trend2success.hvac.audit_scheduler import AuditScheduler
from trend2success.hvac.installation import INSTALL_PRICE, InstallationAgent
from trend2success.hvac.lead_store import LeadStore
from trend2success.hvac.models import HVACProspect, LeadStatus
from trend2success.hvac.support import SUPPORT_MONTHLY_PRICE, SupportAgent


def make_prospect(prospect_id="hp-1", status=LeadStatus.MESSAGED) -> HVACProspect:
    return HVACProspect(
        id=prospect_id,
        name="Alex",
        address="123 Main St",
        phone="555-0100",
        email="alex@example.com",
        system_age_years=15,
        monthly_bill=250.0,
        sqft=1500,
        status=status,
    )


def test_audit_scheduler_schedules_messaged_prospects(tmp_path):
    store = LeadStore(tmp_path / "leads.json")
    store.add(make_prospect(status=LeadStatus.MESSAGED))
    scheduler = AuditScheduler(store, delay_days=1)

    [call] = scheduler.schedule()

    assert call.prospect_id == "hp-1"
    assert call.duration_minutes == 20
    assert store.get("hp-1").status == LeadStatus.AUDIT_SCHEDULED


def test_audit_scheduler_skips_unmessaged_prospects(tmp_path):
    store = LeadStore(tmp_path / "leads.json")
    store.add(make_prospect(status=LeadStatus.NEW))
    scheduler = AuditScheduler(store)

    assert scheduler.schedule() == []


def test_installation_closes_deal_for_accepted_prospect(tmp_path):
    store = LeadStore(tmp_path / "leads.json")
    store.add(make_prospect(status=LeadStatus.AUDIT_SCHEDULED))
    agent = InstallationAgent(store)

    deal = agent.close("hp-1", accepted=True)

    assert deal is not None
    assert deal.amount == INSTALL_PRICE == 2000.0
    assert store.get("hp-1").status == LeadStatus.INSTALLED


def test_installation_marks_declined_prospect_lost(tmp_path):
    store = LeadStore(tmp_path / "leads.json")
    store.add(make_prospect(status=LeadStatus.AUDIT_SCHEDULED))
    agent = InstallationAgent(store)

    deal = agent.close("hp-1", accepted=False)

    assert deal is None
    assert store.get("hp-1").status == LeadStatus.LOST


def test_installation_requires_completed_audit(tmp_path):
    store = LeadStore(tmp_path / "leads.json")
    store.add(make_prospect(status=LeadStatus.NEW))
    agent = InstallationAgent(store)

    with pytest.raises(ValueError):
        agent.close("hp-1", accepted=True)


def test_support_enrolls_installed_prospect(tmp_path):
    store = LeadStore(tmp_path / "leads.json")
    store.add(make_prospect(status=LeadStatus.INSTALLED))
    agent = SupportAgent(store)

    subscription = agent.enroll("hp-1")

    assert subscription.monthly_amount == SUPPORT_MONTHLY_PRICE == 350.0
    assert store.get("hp-1").status == LeadStatus.SUPPORT_ACTIVE


def test_support_requires_installed_status(tmp_path):
    store = LeadStore(tmp_path / "leads.json")
    store.add(make_prospect(status=LeadStatus.AUDIT_SCHEDULED))
    agent = SupportAgent(store)

    with pytest.raises(ValueError):
        agent.enroll("hp-1")
