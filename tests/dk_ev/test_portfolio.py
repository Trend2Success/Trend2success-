from __future__ import annotations

from dk_ev.optimizer.mip import OptimizerConstraints
from dk_ev.optimizer.portfolio import PortfolioConfig, generate_portfolio
from dk_ev.rules import NFL_RULES

from .fixtures import multi_team_nfl_slate


def test_portfolio_generates_requested_count_when_feasible():
    slate = multi_team_nfl_slate()
    config = PortfolioConfig(contest_type="gpp", num_lineups=5, max_overlap=6)
    lineups = generate_portfolio(slate, NFL_RULES, config)
    assert len(lineups) == 5


def test_portfolio_lineups_are_diversified_within_overlap_cap():
    slate = multi_team_nfl_slate()
    config = PortfolioConfig(contest_type="gpp", num_lineups=6, max_overlap=5)
    lineups = generate_portfolio(slate, NFL_RULES, config)
    assert len(lineups) >= 2
    for i, a in enumerate(lineups):
        for b in lineups[i + 1 :]:
            assert a.overlap(b) <= 5


def test_cash_portfolio_favors_floor_over_gpp_ceiling():
    slate = multi_team_nfl_slate()
    cash_lineup = generate_portfolio(
        slate, NFL_RULES, PortfolioConfig(contest_type="cash", num_lineups=1)
    )[0]
    gpp_lineup = generate_portfolio(
        slate, NFL_RULES, PortfolioConfig(contest_type="gpp", num_lineups=1)
    )[0]
    # cash-optimized lineup should never have a lower total floor than the
    # GPP-optimized lineup pulled from the same slate
    cash_floor = sum(p.floor for p in cash_lineup.players)
    gpp_floor = sum(p.floor for p in gpp_lineup.players)
    assert cash_floor >= gpp_floor


def test_stacking_constraint_forces_qb_teammate():
    slate = multi_team_nfl_slate()
    config = PortfolioConfig(contest_type="gpp", num_lineups=1, stack_min_size=1)
    lineup = generate_portfolio(slate, NFL_RULES, config)[0]
    qb = next(p for p in lineup.players if "QB" in p.positions)
    teammates_in_stack_positions = [
        p for p in lineup.players if p.team == qb.team and ("WR" in p.positions or "TE" in p.positions)
    ]
    assert len(teammates_in_stack_positions) >= 1


def test_portfolio_respects_base_constraints_locks_and_bans():
    slate = multi_team_nfl_slate()
    locked_id = "BUF_rb"
    banned_id = "MIA_wr"
    base_constraints = OptimizerConstraints(
        locked_player_ids=frozenset({locked_id}),
        banned_player_ids=frozenset({banned_id}),
    )
    config = PortfolioConfig(contest_type="balanced", alpha=0.4, num_lineups=3, max_overlap=6)
    lineups = generate_portfolio(slate, NFL_RULES, config, base_constraints)
    assert len(lineups) >= 1
    for lineup in lineups:
        assert locked_id in lineup.player_ids
        assert banned_id not in lineup.player_ids
