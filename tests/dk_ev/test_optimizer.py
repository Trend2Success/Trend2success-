from __future__ import annotations

import pytest

from dk_ev.optimizer.mip import (
    InfeasibleLineupError,
    LineupOptimizer,
    OptimizerConstraints,
)
from dk_ev.rules import NFL_RULES

from .fixtures import multi_team_nfl_slate, small_nfl_slate


def test_optimal_lineup_respects_salary_cap():
    optimizer = LineupOptimizer(small_nfl_slate(), NFL_RULES)
    lineup = optimizer.solve()
    assert lineup.salary <= NFL_RULES.salary_cap


def test_optimal_lineup_has_correct_slots_and_positions():
    optimizer = LineupOptimizer(small_nfl_slate(), NFL_RULES)
    lineup = optimizer.solve()

    assert lineup.slots == NFL_RULES.slots
    assert len(lineup.players) == NFL_RULES.roster_size

    for slot, player in zip(lineup.slots, lineup.players):
        assert NFL_RULES.player_eligible_for_slot(player.positions, slot)

    # no player used twice
    assert len({p.player_id for p in lineup.players}) == NFL_RULES.roster_size


def test_optimal_lineup_maximizes_points_given_cap():
    optimizer = LineupOptimizer(small_nfl_slate(), NFL_RULES)
    lineup = optimizer.solve()
    # the highest-owned/most-expensive stars should be selected when they fit
    names = {p.name for p in lineup.players}
    assert "WR One" in names  # highest-projection WR, affordable within cap


def test_salary_cap_never_exceeded_across_many_solves():
    optimizer = LineupOptimizer(small_nfl_slate(), NFL_RULES)
    lineups = optimizer.top_k(5)
    assert len(lineups) >= 1
    for lineup in lineups:
        assert lineup.salary <= NFL_RULES.salary_cap


def test_top_k_returns_distinct_lineups():
    optimizer = LineupOptimizer(small_nfl_slate(), NFL_RULES)
    lineups = optimizer.top_k(3)
    assert len(lineups) >= 2
    player_sets = [lu.player_ids for lu in lineups]
    assert len(player_sets) == len(set(player_sets))


def test_top_k_is_descending_by_projected_points():
    optimizer = LineupOptimizer(small_nfl_slate(), NFL_RULES)
    lineups = optimizer.top_k(4)
    points = [lu.projected_points for lu in lineups]
    assert points == sorted(points, reverse=True)


def test_locked_player_is_always_included():
    optimizer = LineupOptimizer(small_nfl_slate(), NFL_RULES)
    constraints = OptimizerConstraints(locked_player_ids=frozenset({"rb4"}))
    lineup = optimizer.solve(constraints)
    assert "rb4" in lineup.player_ids


def test_banned_player_is_never_included():
    optimizer = LineupOptimizer(small_nfl_slate(), NFL_RULES)
    constraints = OptimizerConstraints(banned_player_ids=frozenset({"wr1"}))
    lineup = optimizer.solve(constraints)
    assert "wr1" not in lineup.player_ids


def test_max_players_per_team_enforced():
    optimizer = LineupOptimizer(multi_team_nfl_slate(), NFL_RULES)
    constraints = OptimizerConstraints(max_players_per_team=1)
    lineup = optimizer.solve(constraints)
    assert max(lineup.team_counts().values()) <= 1


def test_infeasible_when_required_position_has_no_players():
    slate = small_nfl_slate()
    optimizer = LineupOptimizer(slate, NFL_RULES)
    # ban every DST -> the DST slot has zero eligible candidates
    constraints = OptimizerConstraints(banned_player_ids=frozenset({"dst1", "dst2"}))
    with pytest.raises(InfeasibleLineupError):
        optimizer.solve(constraints)


def test_no_opposing_dst_vs_qb_excludes_conflicting_pair():
    slate = small_nfl_slate()
    optimizer = LineupOptimizer(slate, NFL_RULES)
    constraints = OptimizerConstraints(
        locked_player_ids=frozenset({"qb1", "dst2"}),  # BUF QB vs MIA DST (opp)
        no_opposing_dst_vs_qb=True,
    )
    with pytest.raises(InfeasibleLineupError):
        optimizer.solve(constraints)
