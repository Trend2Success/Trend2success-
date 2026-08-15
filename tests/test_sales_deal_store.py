from trend2success.sales.deal_store import DealStore
from trend2success.sales.models import Deal, DealStage, Lead


def make_deal(deal_id="deal-1") -> Deal:
    lead = Lead(
        id="ld-1",
        company="Acme",
        contact_name="Jo Lin",
        email="jo@acme.com",
        industry="SaaS",
        source="test",
        budget=50000,
    )
    return Deal(id=deal_id, lead=lead, fit_score=0.8)


def test_add_and_get_roundtrips(tmp_path):
    store = DealStore(tmp_path / "deals.json")
    deal = make_deal()
    store.add(deal)

    fetched = store.get(deal.id)
    assert fetched is not None
    assert fetched.id == deal.id
    assert fetched.lead.company == deal.lead.company
    assert fetched.stage == DealStage.NEW


def test_list_returns_all_deals(tmp_path):
    store = DealStore(tmp_path / "deals.json")
    store.add(make_deal("deal-1"))
    store.add(make_deal("deal-2"))

    assert {d.id for d in store.list()} == {"deal-1", "deal-2"}


def test_update_stage_persists(tmp_path):
    store = DealStore(tmp_path / "deals.json")
    store.add(make_deal())

    store.update_stage("deal-1", DealStage.CLOSED_WON)

    assert store.get("deal-1").stage == DealStage.CLOSED_WON


def test_update_value_persists(tmp_path):
    store = DealStore(tmp_path / "deals.json")
    store.add(make_deal())

    store.update_value("deal-1", 25000)

    assert store.get("deal-1").value == 25000


def test_update_stage_missing_id_raises(tmp_path):
    store = DealStore(tmp_path / "deals.json")
    try:
        store.update_stage("missing", DealStage.CLOSED_WON)
        assert False, "expected KeyError"
    except KeyError:
        pass
