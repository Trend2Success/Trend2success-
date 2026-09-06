"""
Monte Carlo fantasy-point simulation for the SlateEdge optimizer-service.

Everything produced here is an ESTIMATE derived from caller-supplied
mean/stdev inputs and simple correlation heuristics -- it is a statistical
projection tool, not a guarantee of real outcomes.

------------------------------------------------------------------------
Methodology
------------------------------------------------------------------------
1. Build an NxN correlation matrix across all players:
   - starts at identity (independent players)
   - `default_correlation_rules` are applied heuristically from each
     player's position/team/game_id:
       * qb_own_pass_catcher: a QB and a same-team WR/TE
       * same_game_offense:   any two different offensive (non-DST) players
                               who share a game_id (regardless of team --
                               this also covers the QB/pass-catcher pair
                               before the more specific rule overrides it)
       * dst_vs_opp_offense:  a DST and any non-DST player on the team the
                               DST is facing (player.team == dst.opponent)
     Rules are applied in the order above (least specific to most
     specific) so a more specific rule always wins on a given pair.
   - explicit `correlations` pairs are applied last and always win over
     any rule-based value for that pair.
2. The resulting matrix is not guaranteed positive semi-definite (heuristic
   overlays can break that), so we project it to the nearest PSD
   correlation matrix by eigenvalue-clipping (clip negative/near-zero
   eigenvalues, reconstruct, renormalize to unit diagonal).
3. Draw correlated standard normals via Cholesky of the fixed matrix
   (seeded via numpy Generator when `random_seed` is given).
4. Convert to each player's target marginal via a Gaussian-copula
   transform: u = Phi(z) (standard normal CDF), then x = target_ppf(u).
   This exactly reproduces the requested marginal (truncated-normal or
   lognormal, matching mean/stdev) while approximately preserving the
   requested correlation structure (exact for the underlying normal,
   approximate -- but same-signed and materially strong -- after the
   marginal transform, which is standard and sufficient for DFS-style
   decision support).
   - truncated_normal: modeled as Normal(mean, stdev) truncated at 0 from
     below. This is a simplification: for players whose mean is small
     relative to stdev, the *realized* mean of the truncated distribution
     will sit slightly above the input `mean` (mass below 0 is clipped
     away). For realistic fantasy-point inputs (mean comfortably above 0
     relative to stdev) this effect is small. Exact moment-matching would
     require a numerical solve per player; we skip that for simplicity.
   - lognormal: mu/sigma solved analytically via method-of-moments so the
     lognormal distribution's mean/stdev match the requested mean/stdev
     exactly: sigma^2 = ln(1 + (stdev/mean)^2), mu = ln(mean) - sigma^2/2.

Duplication-risk proxy
   `duplication_risk_proxy` is explicitly a heuristic stand-in, NOT a real
   field-duplication model (we have no visibility into what any other DFS
   entrant actually rosters). It combines:
     0.6 * normalized(ownership_sum) + 0.4 * avg_jaccard_similarity_to_other_lineups
   - normalized(ownership_sum) = ownership_sum / (num_roster_spots * 100),
     clipped to [0, 1] (assumes ownership is a 0-100 percentage).
   - avg_jaccard_similarity_to_other_lineups = the mean Jaccard similarity
     of this lineup's player set against every other lineup supplied in
     the same request (0 if there are no other lineups to compare against).
   The combined score is clipped to [0, 1].
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
from scipy import stats

from .models import SimulateRequest, SimulateResponse, PlayerStat, LineupStat


def _build_correlation_matrix(req: SimulateRequest) -> np.ndarray:
    players = req.players
    n = len(players)
    corr = np.eye(n, dtype=float)

    idx = {p.player_id: i for i, p in enumerate(players)}
    rules = req.default_correlation_rules

    def set_pair(i: int, j: int, rho: float) -> None:
        corr[i, j] = rho
        corr[j, i] = rho

    # 1) same_game_offense (broadest, least specific)
    for i in range(n):
        for j in range(i + 1, n):
            pi, pj = players[i], players[j]
            if pi.position == "DST" or pj.position == "DST":
                continue
            if pi.game_id == pj.game_id and pi.game_id:
                set_pair(i, j, rules.same_game_offense)

    # 2) qb_own_pass_catcher (more specific -- overrides same_game_offense)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            pi, pj = players[i], players[j]
            if (
                pi.position == "QB"
                and pj.position in ("WR", "TE")
                and pi.team == pj.team
                and pi.team
            ):
                set_pair(i, j, rules.qb_own_pass_catcher)

    # 3) dst_vs_opp_offense (most specific of the rule set)
    # SimPlayer does not carry an explicit opponent field (only team/game_id),
    # not carry directly (only team/game_id) -- infer opponent as "the other
    # team in the same game_id" by scanning the roster for a team in the same
    # game_id that differs from the DST's own team.
    game_teams: Dict[str, List[str]] = {}
    for p in players:
        game_teams.setdefault(p.game_id, [])
        if p.team not in game_teams[p.game_id]:
            game_teams[p.game_id].append(p.team)

    for i in range(n):
        pi = players[i]
        if pi.position != "DST":
            continue
        teams_in_game = game_teams.get(pi.game_id, [])
        opp_teams = [t for t in teams_in_game if t != pi.team]
        if not opp_teams:
            continue
        for j in range(n):
            if i == j:
                continue
            pj = players[j]
            if pj.position != "DST" and pj.team in opp_teams:
                set_pair(i, j, rules.dst_vs_opp_offense)

    # 4) explicit overrides win over everything
    for pair in req.correlations:
        if pair.player_id_a in idx and pair.player_id_b in idx:
            i, j = idx[pair.player_id_a], idx[pair.player_id_b]
            if i != j:
                set_pair(i, j, pair.rho)

    return corr


def _nearest_psd_correlation(corr: np.ndarray) -> np.ndarray:
    """Project a symmetric matrix to the nearest PSD correlation matrix via
    eigenvalue clipping, then renormalize to a unit diagonal."""
    sym = (corr + corr.T) / 2.0
    eigvals, eigvecs = np.linalg.eigh(sym)
    eigvals_clipped = np.clip(eigvals, 1e-8, None)
    fixed = eigvecs @ np.diag(eigvals_clipped) @ eigvecs.T
    d = np.sqrt(np.clip(np.diag(fixed), 1e-12, None))
    fixed = fixed / np.outer(d, d)
    np.fill_diagonal(fixed, 1.0)
    fixed = (fixed + fixed.T) / 2.0
    return fixed


def _cholesky_with_jitter(corr: np.ndarray) -> np.ndarray:
    n = corr.shape[0]
    jitter = 0.0
    for _ in range(6):
        try:
            return np.linalg.cholesky(corr + jitter * np.eye(n))
        except np.linalg.LinAlgError:
            jitter = 1e-8 if jitter == 0.0 else jitter * 10
    # last resort: fall back to identity (independent draws) rather than crash
    return np.eye(n)


def _lognormal_params(mean: float, stdev: float) -> tuple[float, float]:
    mean = max(mean, 1e-6)
    stdev = max(stdev, 1e-9)
    sigma2 = np.log(1.0 + (stdev / mean) ** 2)
    sigma = np.sqrt(sigma2)
    mu = np.log(mean) - sigma2 / 2.0
    return float(mu), float(sigma)


def _simulate_scores(req: SimulateRequest) -> np.ndarray:
    """Returns an array of shape (n_players, num_simulations)."""
    players = req.players
    n = len(players)
    num_sims = req.num_simulations

    corr = _build_correlation_matrix(req)
    corr = _nearest_psd_correlation(corr)
    L = _cholesky_with_jitter(corr)

    rng = np.random.default_rng(req.random_seed)
    standard_normals = rng.standard_normal((n, num_sims))
    z = L @ standard_normals  # correlated standard normals, shape (n, num_sims)

    u = stats.norm.cdf(z)
    u = np.clip(u, 1e-9, 1 - 1e-9)

    out = np.empty_like(u)
    for i, p in enumerate(players):
        mean = float(p.mean)
        stdev = max(float(p.stdev), 1e-9)
        if req.distribution == "lognormal":
            mu, sigma = _lognormal_params(mean, stdev)
            out[i, :] = np.exp(mu + sigma * stats.norm.ppf(u[i, :]))
        else:  # truncated_normal
            alpha = (0.0 - mean) / stdev
            out[i, :] = stats.truncnorm.ppf(u[i, :], a=alpha, b=np.inf, loc=mean, scale=stdev)

    return out


def _percentiles(arr: np.ndarray) -> Dict[str, float]:
    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p75": float(np.percentile(arr, 75)),
        "p90": float(np.percentile(arr, 90)),
    }


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def run_simulation(req: SimulateRequest) -> SimulateResponse:
    players = req.players
    sims = _simulate_scores(req)  # (n_players, num_sims)

    player_stats: List[PlayerStat] = []
    for i, p in enumerate(players):
        stats_dict = _percentiles(sims[i, :])
        prob = None
        if req.threshold is not None:
            prob = float(np.mean(sims[i, :] > req.threshold))
        player_stats.append(
            PlayerStat(
                player_id=p.player_id,
                mean=round(stats_dict["mean"], 4),
                median=round(stats_dict["median"], 4),
                p75=round(stats_dict["p75"], 4),
                p90=round(stats_dict["p90"], 4),
                prob_exceeds_threshold=round(prob, 4) if prob is not None else None,
            )
        )

    id_to_row = {p.player_id: i for i, p in enumerate(players)}
    lineup_sets = [set(l.player_ids) for l in req.lineups]

    lineup_stats: List[LineupStat] = []
    for li, lineup in enumerate(req.lineups):
        rows = [id_to_row[pid] for pid in lineup.player_ids if pid in id_to_row]
        if rows:
            lineup_scores = sims[rows, :].sum(axis=0)
        else:
            lineup_scores = np.zeros(sims.shape[1])
        stats_dict = _percentiles(lineup_scores)

        roster_size = max(len(lineup.player_ids), 1)
        ownership_sum = lineup.ownership_sum or 0.0
        normalized_ownership = min(max(ownership_sum / (roster_size * 100.0), 0.0), 1.0)

        other_sets = [s for j, s in enumerate(lineup_sets) if j != li]
        this_set = lineup_sets[li]
        if other_sets:
            avg_jaccard = float(np.mean([_jaccard(this_set, s) for s in other_sets]))
        else:
            avg_jaccard = 0.0

        dup_risk = 0.6 * normalized_ownership + 0.4 * avg_jaccard
        dup_risk = float(min(max(dup_risk, 0.0), 1.0))

        lineup_stats.append(
            LineupStat(
                lineup_id=lineup.lineup_id,
                mean=round(stats_dict["mean"], 4),
                median=round(stats_dict["median"], 4),
                p75=round(stats_dict["p75"], 4),
                p90=round(stats_dict["p90"], 4),
                duplication_risk_proxy=round(dup_risk, 4),
            )
        )

    return SimulateResponse(
        player_stats=player_stats,
        lineup_stats=lineup_stats,
        num_simulations=req.num_simulations,
        distribution=req.distribution,
        seed_used=req.random_seed,
    )
