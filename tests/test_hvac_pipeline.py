from trend2success.hvac.lead_store import LeadStore
from trend2success.hvac.models import LeadStatus
from trend2success.hvac.pipeline import HVACFunnel


def test_pipeline_runs_end_to_end(tmp_path):
    store = LeadStore(tmp_path / "leads.json")
    funnel = HVACFunnel(lead_store=store)

    result = funnel.run()

    assert len(result.prospects_found) == 25
    assert len(result.leak_results) == 25
    assert result.messages_sent

    leaking_ids = {r.prospect_id for r in result.leak_results if r.is_leaking}
    assert {m.prospect_id for m in result.messages_sent} == leaking_ids

    stored = {p.id: p for p in store.list()}
    for leak_result in result.leak_results:
        expected = LeadStatus.MESSAGED if leak_result.is_leaking else LeadStatus.NO_LEAK
        assert stored[leak_result.prospect_id].status == expected
