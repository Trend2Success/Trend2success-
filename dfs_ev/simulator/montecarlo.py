"""Vectorized Monte Carlo player-score simulation.

Each player's score is Normal(mean, std) clipped to [floor, ceiling] (or a
fat-tailed Student-t variant for GPP mode), with correlation injected via a
shared per-fixture "game shock" and per-team "team shock" -- this is what
makes QB+pass-catcher stacks and bring-backs co-move, and lets a team's
skill players share upside/downside from the same game script.

`apply_blowout_adjustment` handles CFB-specific game-script risk: large
favorites see reduced legitimate playing time for starters late in
blowouts (lower mean, higher std on who plays), and FBS-vs-FCS mismatches
inflate variance broadly since backups see extended run.
"""
from __future__ import annotations

import numpy as np
from numba import njit

# Same-team correlation weight by position group -- how much of a player's
# variance is explained by their team's shared game-script shock vs. their
# own idiosyncratic performance. Skill-position pass-catchers/QBs stack
# harder than kickers.
STACK_RHO_BY_POSITION: dict[str, float] = {
    "QB": 0.40,
    "WR": 0.35,
    "TE": 0.35,
    "RB": 0.30,
    "K": 0.10,
}
DEFAULT_STACK_RHO = 0.20

LARGE_FAVORITE_SPREAD = 17.0
BLOWOUT_SPREAD = 24.0
FCS_MISMATCH_STD_MULT = 1.4


def apply_blowout_adjustment(
    mean: float, std: float, spread: float, is_fcs_mismatch: bool
) -> tuple[float, float]:
    """Adjust a player's (mean, std) for game-script / blowout risk.

    `spread` is signed from the player's own team's perspective: positive
    means that team is favored by that many points.
    """
    mean_mult = 1.0
    std_mult = 1.0
    if spread >= BLOWOUT_SPREAD:
        mean_mult *= 0.85
        std_mult *= 1.30
    elif spread >= LARGE_FAVORITE_SPREAD:
        mean_mult *= 0.92
        std_mult *= 1.15
    if is_fcs_mismatch:
        std_mult *= FCS_MISMATCH_STD_MULT
    return mean * mean_mult, std * std_mult


@njit(cache=True)
def _simulate_scores_numba(
    means: np.ndarray,
    stds: np.ndarray,
    floors: np.ndarray,
    ceilings: np.ndarray,
    team_ids: np.ndarray,
    team_fixture_ids: np.ndarray,
    stack_rho: np.ndarray,
    n_fixtures: int,
    n_teams: int,
    n_iters: int,
    seed: int,
) -> np.ndarray:
    np.random.seed(seed)
    n_players = means.shape[0]
    scores = np.empty((n_players, n_iters), dtype=np.float64)
    game_shock = np.empty(n_fixtures, dtype=np.float64)
    team_shock = np.empty(n_teams, dtype=np.float64)

    for i in range(n_iters):
        for f in range(n_fixtures):
            game_shock[f] = np.random.normal(0.0, 1.0)
        for t in range(n_teams):
            fx = team_fixture_ids[t]
            team_shock[t] = 0.6 * game_shock[fx] + 0.8 * np.random.normal(0.0, 1.0)
        for p in range(n_players):
            t = team_ids[p]
            rho = stack_rho[p]
            idio = np.random.normal(0.0, 1.0)
            z = np.sqrt(rho) * team_shock[t] + np.sqrt(1.0 - rho) * idio
            val = means[p] + stds[p] * z
            if val < floors[p]:
                val = floors[p]
            if val > ceilings[p]:
                val = ceilings[p]
            scores[p, i] = val
    return scores


def _simulate_scores_numpy_fat_tail(
    means: np.ndarray,
    stds: np.ndarray,
    floors: np.ndarray,
    ceilings: np.ndarray,
    team_ids: np.ndarray,
    team_fixture_ids: np.ndarray,
    stack_rho: np.ndarray,
    n_fixtures: int,
    n_teams: int,
    n_iters: int,
    seed: int,
    df: int = 5,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    game_shock = rng.standard_normal((n_fixtures, n_iters))
    team_shock = 0.6 * game_shock[team_fixture_ids] + 0.8 * rng.standard_normal((n_teams, n_iters))
    player_team_shock = team_shock[team_ids]
    idio = rng.standard_t(df, size=(len(means), n_iters))
    idio = idio / np.sqrt(df / (df - 2))  # normalize to unit variance
    rho = stack_rho.reshape(-1, 1)
    z = np.sqrt(rho) * player_team_shock + np.sqrt(1.0 - rho) * idio
    scores = means.reshape(-1, 1) + stds.reshape(-1, 1) * z
    return np.clip(scores, floors.reshape(-1, 1), ceilings.reshape(-1, 1))


def simulate_player_scores(
    means: np.ndarray,
    stds: np.ndarray,
    floors: np.ndarray,
    ceilings: np.ndarray,
    team_ids: np.ndarray,
    team_fixture_ids: np.ndarray,
    stack_rho: np.ndarray,
    n_fixtures: int,
    n_teams: int,
    n_iters: int = 10_000,
    seed: int = 42,
    fat_tail: bool = False,
) -> np.ndarray:
    """Returns scores shaped (n_players, n_iters)."""
    if fat_tail:
        return _simulate_scores_numpy_fat_tail(
            means, stds, floors, ceilings, team_ids, team_fixture_ids, stack_rho,
            n_fixtures, n_teams, n_iters, seed,
        )
    return _simulate_scores_numba(
        means, stds, floors, ceilings, team_ids, team_fixture_ids, stack_rho,
        n_fixtures, n_teams, n_iters, seed,
    )
