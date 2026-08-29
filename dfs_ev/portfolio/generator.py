"""Multi-lineup GPP portfolio generation: diversified entries with global
exposure caps, per-team caps, and (Showdown) captain-choice variation.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass

from dfs_ev.optimizer.mip import Lineup, OptimizerConfig, optimize_lineups
from dfs_ev.projections.derive import PlayerProjection
from dfs_ev.salary.models import ContestFormat


@dataclass
class PortfolioConfig:
    entries: int
    max_exposure: float = 0.30  # <=30% of entries for any one player
    max_team_exposure: float | None = None
    max_captain_exposure: float | None = None  # Showdown only; defaults to max_exposure
    max_overlap_players: int | None = None  # cap shared players between any two entries
    candidate_pool_multiplier: int = 5


def generate_portfolio(
    contest: ContestFormat,
    projections: dict[str, PlayerProjection],
    config: PortfolioConfig,
    optimizer_config: OptimizerConfig | None = None,
) -> list[Lineup]:
    pool_size = max(config.entries * config.candidate_pool_multiplier, config.entries + 5)
    candidates = optimize_lineups(contest, projections, top_k=pool_size, config=optimizer_config)
    candidates.sort(key=lambda lu: lu.total_projection, reverse=True)

    cap_count = max(1, math.ceil(config.max_exposure * config.entries))
    captain_cap_count = max(1, math.ceil((config.max_captain_exposure or config.max_exposure) * config.entries))
    team_cap_count = (
        max(1, math.ceil(config.max_team_exposure * config.entries)) if config.max_team_exposure else None
    )
    max_overlap = (
        config.max_overlap_players if config.max_overlap_players is not None else max(1, contest.roster_size - 2)
    )

    exposure: dict[str, int] = {}
    captain_exposure: dict[str, int] = {}
    team_exposure: dict[str, int] = {}
    portfolio: list[Lineup] = []

    for lineup in candidates:
        if len(portfolio) >= config.entries:
            break

        bases = [lp.player.base_player_key for lp in lineup.players]
        teams_in_lineup = {lp.player.team for lp in lineup.players}
        captain_base = next((lp.player.base_player_key for lp in lineup.players if lp.player.is_captain), None)
        lineup_ids = lineup.player_ids()

        if any(exposure.get(b, 0) + 1 > cap_count for b in bases):
            continue
        if team_cap_count and any(team_exposure.get(t, 0) + 1 > team_cap_count for t in teams_in_lineup):
            continue
        if captain_base and captain_exposure.get(captain_base, 0) + 1 > captain_cap_count:
            continue
        if any(len(lineup_ids & accepted.player_ids()) > max_overlap for accepted in portfolio):
            continue

        for b in bases:
            exposure[b] = exposure.get(b, 0) + 1
        for t in teams_in_lineup:
            team_exposure[t] = team_exposure.get(t, 0) + 1
        if captain_base:
            captain_exposure[captain_base] = captain_exposure.get(captain_base, 0) + 1
        portfolio.append(lineup)

    if len(portfolio) < config.entries:
        print(
            f"[dfs_ev][portfolio] WARNING: only found {len(portfolio)}/{config.entries} lineups satisfying "
            "exposure/overlap caps from the candidate pool; relax caps or increase candidate_pool_multiplier.",
            file=sys.stderr,
        )
    return portfolio


def exposure_report(portfolio: list[Lineup]) -> dict[str, float]:
    """Player name -> fraction of portfolio entries rostering them."""
    if not portfolio:
        return {}
    counts: dict[str, int] = {}
    for lineup in portfolio:
        for lp in lineup.players:
            counts[lp.player.dk_name] = counts.get(lp.player.dk_name, 0) + 1
    n = len(portfolio)
    return {name: round(c / n, 4) for name, c in counts.items()}
