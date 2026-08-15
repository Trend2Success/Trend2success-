from trend2success.sales.deal_store import DealStore
from trend2success.sales.models import ICPProfile
from trend2success.sales.pipeline import SalesPipeline


def test_pipeline_runs_end_to_end_and_queues_deals(tmp_path):
    pipeline = SalesPipeline(deal_store=DealStore(tmp_path / "deals.json"), top_n=2)
    icp = ICPProfile(name="ICP", industries=["SaaS", "Retail"], keywords=["crm", "automation"])

    result = pipeline.run("automation", icp)

    assert result.leads_found
    assert result.qualification_results
    assert result.lead_scores
    assert 0 < len(result.deals_queued) <= 2
    assert pipeline.deal_store.list() == result.deals_queued


def test_pipeline_respects_min_score(tmp_path):
    pipeline = SalesPipeline(deal_store=DealStore(tmp_path / "deals.json"), top_n=5, min_score=0.99)
    icp = ICPProfile(name="ICP", keywords=["nonexistent-keyword"])

    result = pipeline.run("automation", icp)

    assert result.deals_queued == []


def test_pipeline_excludes_unqualified_leads(tmp_path):
    pipeline = SalesPipeline(deal_store=DealStore(tmp_path / "deals.json"), top_n=10)
    icp = ICPProfile(name="ICP")

    result = pipeline.run("automation", icp)

    qualified_ids = {r.lead_id for r in result.qualification_results if r.is_qualified}
    assert "ld-3" not in qualified_ids  # missing contact name, invalid email, no budget
    assert all(deal.lead.id != "ld-3" for deal in result.deals_queued)
