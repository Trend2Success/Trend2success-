import pytest

from trend2success.hvac.lead_store import LeadStore
from trend2success.hvac.models import HVACProspect, LeadStatus


def make_prospect(prospect_id="hp-1") -> HVACProspect:
    return HVACProspect(
        id=prospect_id,
        name="Alex",
        address="123 Main St",
        phone="555-0100",
        email="alex@example.com",
        system_age_years=15,
        monthly_bill=250.0,
        sqft=1500,
    )


def test_add_and_get_roundtrips(tmp_path):
    store = LeadStore(tmp_path / "leads.json")
    store.add(make_prospect())

    fetched = store.get("hp-1")
    assert fetched is not None
    assert fetched.name == "Alex"
    assert fetched.status == LeadStatus.NEW


def test_list_returns_all_prospects(tmp_path):
    store = LeadStore(tmp_path / "leads.json")
    store.add(make_prospect("hp-1"))
    store.add(make_prospect("hp-2"))

    assert {p.id for p in store.list()} == {"hp-1", "hp-2"}


def test_update_status_persists(tmp_path):
    store = LeadStore(tmp_path / "leads.json")
    store.add(make_prospect())

    store.update_status("hp-1", LeadStatus.MESSAGED)

    assert store.get("hp-1").status == LeadStatus.MESSAGED


def test_update_status_missing_id_raises(tmp_path):
    store = LeadStore(tmp_path / "leads.json")
    with pytest.raises(KeyError):
        store.update_status("missing", LeadStatus.MESSAGED)
