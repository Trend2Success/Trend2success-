"""Diversified lineup portfolio generation for GPP/cash/balanced contests.

A single "best" lineup is rarely what you want to submit M times — real
portfolios spread risk across variations. ``generate_portfolio`` uses a
greedy + forbid-overlap loop: solve for the best lineup under the contest's
scoring function, then cap how many players every future lineup may share
with it, and repeat. This produces lineups that are genuinely different
(varied stacks, different value plays) rather than M near-copies of the
optimum.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dk_ev.domain import Player
from dk_ev.optimizer.mip import InfeasibleLineupError, LineupOptimizer, OptimizerConstraints

ContestType = Literal["cash", "gpp", "balanced"]


def cash_score(player: Player) -> float:
    """Favors floor (variance-averse) over ceiling."""
    return 0.7 * player.projected_points + 0.3 * player.floor


def gpp_score(player: Player) -> float:
    """Favors ceiling (upside-seeking)."""
    return 0.6 * player.projected_points + 0.4 * player.ceiling


def balanced_score(player: Player, alpha: float) -> float:
    """alpha=1.0 -> pure GPP scoring, alpha=0.0 -> pure cash scoring."""
    return alpha * gpp_score(player) + (1 - alpha) * cash_score(player)


def score_fn_for_contest(contest_type: ContestType, alpha: float = 0.5):
    if contest_type == "cash":
        return cash_score
    if contest_type == "gpp":
        return gpp_score
    if contest_type == "balanced":
        return lambda p: balanced_score(p, alpha)
    raise ValueError(f"Unknown contest_type {contest_type!r}")


def leverage_weight_for_contest(contest_type: ContestType, alpha: float = 0.5) -> float:
    """GPP tie-breaks toward leverage (low-owned, high-projection plays);
    cash stays near the field's ownership, so leverage isn't rewarded.
    """
    if contest_type == "cash":
        return 0.0
    if contest_type == "gpp":
        return 0.05
    if contest_type == "balanced":
        return 0.05 * alpha
    raise ValueError(f"Unknown contest_type {contest_type!r}")


@dataclass
class PortfolioConfig:
    contest_type: ContestType = "gpp"
    alpha: float = 0.5  # only used when contest_type == "balanced"
    num_lineups: int = 20
    max_overlap: int = 5  # max shared players between any two generated lineups
    stack_min_size: int = 0  # e.g. 1 for QB+1 pass-catcher, 2 for QB+2
    stack_positions: tuple[str, ...] = ("WR", "TE")
    time_limit_seconds: float = 10.0


def generate_portfolio(
    players: list[Player],
    rules,
    config: PortfolioConfig,
    base_constraints: OptimizerConstraints | None = None,
) -> list:
    """Generate up to ``config.num_lineups`` diversified lineups.

    Stops early (returning fewer than requested) once no further lineup can
    satisfy both the base constraints and the overlap cap against every
    lineup generated so far.
    """
    base_constraints = base_constraints or OptimizerConstraints()
    constraints = OptimizerConstraints(
        locked_player_ids=base_constraints.locked_player_ids,
        banned_player_ids=base_constraints.banned_player_ids,
        no_opposing_dst_vs_qb=base_constraints.no_opposing_dst_vs_qb,
        max_players_per_team=base_constraints.max_players_per_team,
        max_from_team=base_constraints.max_from_team,
        min_salary=base_constraints.min_salary,
        stack_min_size=config.stack_min_size or base_constraints.stack_min_size,
        stack_positions=config.stack_positions or base_constraints.stack_positions,
        stack_qb_position=base_constraints.stack_qb_position,
    )

    optimizer = LineupOptimizer(players, rules)
    score_fn = score_fn_for_contest(config.contest_type, config.alpha)
    leverage_weight = leverage_weight_for_contest(config.contest_type, config.alpha)

    lineups = []
    overlap_limits: list[tuple[frozenset[str], int]] = []
    for _ in range(config.num_lineups):
        try:
            lineup = optimizer.solve_with_overlap_limits(
                constraints,
                overlap_limits,
                leverage_weight=leverage_weight,
                time_limit_seconds=config.time_limit_seconds,
                score_fn=score_fn,
            )
        except InfeasibleLineupError:
            break
        lineups.append(lineup)
        overlap_limits.append((lineup.player_ids, config.max_overlap))
    return lineups
