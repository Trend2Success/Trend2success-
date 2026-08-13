from trend2success.hvac.prospect_source import ProspectSource, sample_source


def test_sample_source_returns_twenty_five_prospects():
    prospects = sample_source()
    assert len(prospects) == 25
    assert len({p.id for p in prospects}) == 25


def test_prospect_source_deduplicates_across_sources():
    source = ProspectSource(sources=[sample_source, sample_source])
    results = source.run()
    ids = [p.id for p in results]
    assert len(ids) == len(set(ids)) == 25
