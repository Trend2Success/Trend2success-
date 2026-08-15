from trend2success.sales.agents.lead_gen_agent import LeadGenAgent, sample_source


def test_lead_gen_agent_returns_leads_matching_query():
    agent = LeadGenAgent()
    results = agent.run("saas")
    assert results
    assert any("saas" in r.industry.lower() or "saas" in r.notes.lower() for r in results)


def test_lead_gen_agent_falls_back_to_full_catalog_on_no_match():
    agent = LeadGenAgent()
    results = agent.run("nonexistent-industry-xyz")
    assert len(results) == len(sample_source("nonexistent-industry-xyz"))


def test_lead_gen_agent_deduplicates_across_sources():
    agent = LeadGenAgent(sources=[sample_source, sample_source])
    results = agent.run("automation")
    ids = [r.id for r in results]
    assert len(ids) == len(set(ids))
