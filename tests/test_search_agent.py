from trend2success.agents.search_agent import SearchAgent, sample_source


def test_search_agent_returns_listings_matching_query():
    agent = SearchAgent()
    results = agent.run("python")
    assert results
    assert any("python" in r.title.lower() or "python" in r.description.lower() for r in results)


def test_search_agent_falls_back_to_full_catalog_on_no_match():
    agent = SearchAgent()
    results = agent.run("nonexistent-role-xyz")
    assert len(results) == len(sample_source("nonexistent-role-xyz"))


def test_search_agent_deduplicates_across_sources():
    agent = SearchAgent(sources=[sample_source, sample_source])
    results = agent.run("engineer")
    ids = [r.id for r in results]
    assert len(ids) == len(set(ids))
