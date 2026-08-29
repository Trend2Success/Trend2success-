import math

from dfs_ev.portfolio.generator import PortfolioConfig, generate_portfolio
from dfs_ev.projections.derive import PlayerProjection
from dfs_ev.salary.parser import parse_dk_csv

from .conftest import SAMPLE_DK_CSV


def test_portfolio_respects_max_exposure_cap():
    contest = parse_dk_csv(SAMPLE_DK_CSV).contest
    projections = {}
    for p in contest.players:
        if p.base_player_key not in projections:
            # Slight noise so many distinct near-optimal lineups exist.
            noise = (hash(p.base_player_key) % 7) * 0.1
            projections[p.base_player_key] = PlayerProjection(
                player_key=p.base_player_key, projection=p.salary / 200.0 + noise, std_dev=2, floor=1,
                ceiling=20, source="test",
            )

    # The bundled sample pool only has 12 real people and a 6-man roster, so
    # a strict portfolio (low exposure/overlap caps) may legitimately come
    # back smaller than requested -- what matters is the cap is never
    # violated, not that it always hits the target count.
    entries = 4
    max_exposure = 0.5
    config = PortfolioConfig(entries=entries, max_exposure=max_exposure, candidate_pool_multiplier=8)
    portfolio = generate_portfolio(contest, projections, config)

    assert 0 < len(portfolio) <= entries
    counts: dict[str, int] = {}
    for lineup in portfolio:
        for lp in lineup.players:
            key = lp.player.base_player_key
            counts[key] = counts.get(key, 0) + 1

    cap_count = math.ceil(max_exposure * entries)
    for key, count in counts.items():
        assert count <= cap_count, f"{key} exceeded exposure cap: {count}/{entries}"


def test_portfolio_lineups_are_distinct():
    contest = parse_dk_csv(SAMPLE_DK_CSV).contest
    projections = {}
    for p in contest.players:
        if p.base_player_key not in projections:
            noise = (hash(p.base_player_key) % 7) * 0.1
            projections[p.base_player_key] = PlayerProjection(
                player_key=p.base_player_key, projection=p.salary / 200.0 + noise, std_dev=2, floor=1,
                ceiling=20, source="test",
            )
    config = PortfolioConfig(entries=5, max_exposure=0.4, candidate_pool_multiplier=6)
    portfolio = generate_portfolio(contest, projections, config)
    seen = set()
    for lineup in portfolio:
        key = lineup.player_ids()
        assert key not in seen
        seen.add(key)
