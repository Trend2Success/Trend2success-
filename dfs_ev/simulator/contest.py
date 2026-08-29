"""Contest simulation orchestration: field sampling, payout curves, EV/ROI.

This is a deliberately lightweight field model for an MVP: rather than
constructing a fully salary-legal, exactly-owned lineup for every one of
potentially tens of thousands of entrants, we sample `field_sample_size`
representative field lineups (weighted by the ownership proxy, roughly
salary-legal via rejection sampling) and scale each one's weight so the
sample represents the full contest size. This keeps N>=10,000-iteration
Monte Carlo runs fast while still producing a real ownership-aware field
distribution to rank our candidate lineups against.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

import numpy as np

from dfs_ev.optimizer.mip import Lineup
from dfs_ev.projections.derive import PlayerProjection, projection_for_player_row
from dfs_ev.salary.models import ContestFormat
from dfs_ev.simulator.montecarlo import (
    DEFAULT_STACK_RHO,
    STACK_RHO_BY_POSITION,
    apply_blowout_adjustment,
    simulate_player_scores,
)
from dfs_ev.util import base_position


class ContestPreset(str, Enum):
    CASH_5050 = "cash_5050"
    GPP_LARGE = "gpp_large"
    BALANCED = "balanced"


@dataclass
class GameEnvironment:
    fixture_id: str
    team: str
    opponent: str
    implied_team_total: float
    spread: float  # signed from `team`'s perspective; positive = favored
    is_fcs_mismatch: bool = False


@dataclass
class SimPlayer:
    player_key: str
    team: str
    fixture_id: str
    position: str
    mean: float
    std: float
    floor: float
    ceiling: float
    ownership: float = 0.05


@dataclass
class SimResult:
    lineup_label: str
    ev: float
    roi: float
    itm_pct: float
    median_score: float
    top1_pct: float
    top10_pct: float
    floor_p10: float
    ceiling_p90: float
    mean_score: float


def build_sim_players(
    contest: ContestFormat,
    projections: dict[str, PlayerProjection],
    game_environments: dict[str, GameEnvironment],
    ownership: dict[str, float] | None = None,
) -> dict[str, SimPlayer]:
    """One SimPlayer per contest-CSV roster row, with blowout adjustment applied."""
    ownership = ownership or {}
    sim_players: dict[str, SimPlayer] = {}
    for p in contest.players:
        proj = projection_for_player_row(p, projections)
        if proj is None or proj.source == "none":
            continue
        env = game_environments.get(p.team)
        mean, std = proj.projection, proj.std_dev
        floor, ceiling = proj.floor, proj.ceiling
        fixture_id = env.fixture_id if env else p.team
        if env is not None:
            mean, std = apply_blowout_adjustment(mean, std, env.spread, env.is_fcs_mismatch)
            floor = max(0.0, mean - 1.5 * std)
            ceiling = mean + 1.5 * std
        sim_players[p.player_id] = SimPlayer(
            player_key=p.player_id,
            team=p.team,
            fixture_id=fixture_id,
            position=base_position(p),
            mean=mean,
            std=max(std, 0.01),
            floor=floor,
            ceiling=ceiling,
            ownership=ownership.get(p.player_id, ownership.get(p.base_player_key, 0.05)),
        )
    return sim_players


def _index_universe(
    sim_players: dict[str, SimPlayer],
) -> tuple[
    list[str], dict[str, int], np.ndarray, np.ndarray, np.ndarray, np.ndarray,
    np.ndarray, np.ndarray, np.ndarray, int, int,
]:
    keys = list(sim_players.keys())
    key_to_idx = {k: i for i, k in enumerate(keys)}
    fixtures = sorted({sp.fixture_id for sp in sim_players.values()})
    fixture_idx = {f: i for i, f in enumerate(fixtures)}
    teams = sorted({sp.team for sp in sim_players.values()})
    team_idx = {t: i for i, t in enumerate(teams)}
    team_fixture_ids = np.zeros(len(teams), dtype=np.int64)
    for sp in sim_players.values():
        team_fixture_ids[team_idx[sp.team]] = fixture_idx[sp.fixture_id]

    means = np.array([sim_players[k].mean for k in keys], dtype=np.float64)
    stds = np.array([sim_players[k].std for k in keys], dtype=np.float64)
    floors = np.array([sim_players[k].floor for k in keys], dtype=np.float64)
    ceilings = np.array([sim_players[k].ceiling for k in keys], dtype=np.float64)
    team_ids = np.array([team_idx[sim_players[k].team] for k in keys], dtype=np.int64)
    stack_rho = np.array(
        [STACK_RHO_BY_POSITION.get(sim_players[k].position, DEFAULT_STACK_RHO) for k in keys],
        dtype=np.float64,
    )
    return keys, key_to_idx, means, stds, floors, ceilings, team_ids, team_fixture_ids, stack_rho, len(fixtures), len(teams)


def payout_curve(preset: ContestPreset, contest_size: int, entry_fee: float) -> np.ndarray:
    """Array of length contest_size: prize at each 0-indexed finish rank.
    Simplified payout shapes for MVP EV estimation, not exact site tables.
    """
    prize_pool = contest_size * entry_fee * 0.90  # ~10% rake assumption
    payouts = np.zeros(contest_size, dtype=np.float64)

    def top_heavy(paid: int, pool: float) -> np.ndarray:
        ranks = np.arange(1, paid + 1, dtype=np.float64)
        weights = 1.0 / ranks**0.65
        weights /= weights.sum()
        return pool * weights

    if preset == ContestPreset.CASH_5050:
        paid = contest_size // 2
        if paid > 0:
            payouts[:paid] = prize_pool / paid
    elif preset == ContestPreset.GPP_LARGE:
        paid = max(1, int(contest_size * 0.20))
        payouts[:paid] = top_heavy(paid, prize_pool)
    else:  # BALANCED
        cash_paid = contest_size // 2
        gpp_paid = max(1, int(contest_size * 0.20))
        if cash_paid > 0:
            payouts[:cash_paid] += prize_pool * 0.5 / cash_paid
        payouts[:gpp_paid] += top_heavy(gpp_paid, prize_pool * 0.5)
    return payouts


def sample_field_lineups(
    contest: ContestFormat,
    sim_players: dict[str, SimPlayer],
    field_sample_size: int,
    rng: random.Random,
    max_tries_per_lineup: int = 15,
) -> list[list[str]]:
    """Weighted-by-ownership rejection sampling of `field_sample_size`
    roughly salary-legal opposing lineups from the same player pool.
    """
    eligible_players = [p for p in contest.players if p.player_id in sim_players]
    lineups: list[list[str]] = []
    for _ in range(field_sample_size):
        best_attempt: list[str] | None = None
        for _try in range(max_tries_per_lineup):
            chosen: list[str] = []
            used_bases: set[str] = set()
            salary = 0
            ok = True
            for slot in contest.roster_slots:
                for _ in range(slot.count):
                    candidates = [
                        p
                        for p in eligible_players
                        if (p.eligible_positions & slot.eligible_positions)
                        and p.base_player_key not in used_bases
                    ]
                    if not candidates:
                        ok = False
                        break
                    weights = [max(sim_players[p.player_id].ownership, 1e-4) for p in candidates]
                    pick = rng.choices(candidates, weights=weights, k=1)[0]
                    chosen.append(pick.player_id)
                    used_bases.add(pick.base_player_key)
                    salary += pick.salary
                if not ok:
                    break
            if ok:
                best_attempt = chosen
                if salary <= contest.salary_cap:
                    break
        if best_attempt:
            lineups.append(best_attempt)
    return lineups


def _percentile_rank(lineup_scores: np.ndarray, field_scores: np.ndarray) -> np.ndarray:
    """Rank (0 = best) of our lineup among [lineup] + field, per iteration."""
    if field_scores.shape[0] == 0:
        return np.zeros_like(lineup_scores, dtype=np.int64)
    beats = (field_scores > lineup_scores[None, :]).sum(axis=0)
    return beats


def simulate_contest(
    lineups: list[Lineup],
    contest: ContestFormat,
    projections: dict[str, PlayerProjection],
    game_environments: dict[str, GameEnvironment],
    ownership: dict[str, float] | None = None,
    preset: ContestPreset = ContestPreset.GPP_LARGE,
    contest_size: int = 1000,
    entry_fee: float = 20.0,
    n_iterations: int = 10_000,
    field_sample_size: int = 300,
    fat_tail: bool | None = None,
    seed: int = 42,
) -> list[SimResult]:
    if fat_tail is None:
        fat_tail = preset == ContestPreset.GPP_LARGE

    sim_players = build_sim_players(contest, projections, game_environments, ownership)
    (
        keys, key_to_idx, means, stds, floors, ceilings, team_ids, team_fixture_ids, stack_rho,
        n_fixtures, n_teams,
    ) = _index_universe(sim_players)

    scores = simulate_player_scores(
        means, stds, floors, ceilings, team_ids, team_fixture_ids, stack_rho,
        n_fixtures, n_teams, n_iters=n_iterations, seed=seed, fat_tail=fat_tail,
    )

    rng = random.Random(seed)
    field_lineups = sample_field_lineups(contest, sim_players, field_sample_size, rng)
    field_weight = contest_size / max(len(field_lineups), 1)
    field_score_rows = np.array(
        [scores[[key_to_idx[pid] for pid in lu if pid in key_to_idx], :].sum(axis=0) for lu in field_lineups]
    ) if field_lineups else np.zeros((0, n_iterations))

    payouts = payout_curve(preset, contest_size, entry_fee)

    results: list[SimResult] = []
    for i, lineup in enumerate(lineups):
        idxs = [key_to_idx[lp.player.player_id] for lp in lineup.players if lp.player.player_id in key_to_idx]
        if len(idxs) != len(lineup.players):
            continue
        lineup_scores = scores[idxs, :].sum(axis=0)

        beats = _percentile_rank(lineup_scores, field_score_rows)
        rank0 = np.round(beats * field_weight).astype(np.int64)
        rank0 = np.clip(rank0, 0, contest_size - 1)
        iter_payouts = payouts[rank0]

        ev = float(iter_payouts.mean())
        roi = ev / entry_fee - 1.0 if entry_fee else 0.0
        itm_pct = float((iter_payouts > 0).mean())
        top1_pct = float((rank0 < max(1, contest_size // 100)).mean())
        top10_pct = float((rank0 < max(1, contest_size // 10)).mean())

        results.append(
            SimResult(
                lineup_label=f"lineup_{i}",
                ev=round(ev, 2),
                roi=round(roi, 4),
                itm_pct=round(itm_pct, 4),
                median_score=round(float(np.median(lineup_scores)), 2),
                top1_pct=round(top1_pct, 4),
                top10_pct=round(top10_pct, 4),
                floor_p10=round(float(np.percentile(lineup_scores, 10)), 2),
                ceiling_p90=round(float(np.percentile(lineup_scores, 90)), 2),
                mean_score=round(float(lineup_scores.mean()), 2),
            )
        )
    return results
