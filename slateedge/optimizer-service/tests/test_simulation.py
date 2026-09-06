"""
Sanity tests for app/simulation.py. No real player data is used.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.models import SimulateRequest
from app.simulation import run_simulation


def _players():
    return [
        {"player_id": "QB1", "name": "Fic QB1", "position": "QB", "team": "A", "game_id": "G1", "mean": 20.0, "stdev": 6.0},
        {"player_id": "WR1", "name": "Fic WR1", "position": "WR", "team": "A", "game_id": "G1", "mean": 15.0, "stdev": 7.0},
        {"player_id": "WR2", "name": "Fic WR2", "position": "WR", "team": "B", "game_id": "G1", "mean": 13.0, "stdev": 6.0},
        {"player_id": "RB1", "name": "Fic RB1", "position": "RB", "team": "A", "game_id": "G1", "mean": 14.0, "stdev": 5.0},
        {"player_id": "DST1", "name": "Fic DST1", "position": "DST", "team": "B", "game_id": "G1", "mean": 7.0, "stdev": 4.0},
        {"player_id": "TE1", "name": "Fic TE1", "position": "TE", "team": "C", "game_id": "G2", "mean": 8.0, "stdev": 4.0},
    ]


def base_request(**overrides) -> dict:
    req = {
        "players": _players(),
        "distribution": "truncated_normal",
        "num_simulations": 5000,
        "random_seed": 42,
    }
    req.update(overrides)
    return req


def test_player_mean_tracks_input_mean():
    req = SimulateRequest.model_validate(base_request())
    resp = run_simulation(req)
    by_id = {p.player_id: p for p in resp.player_stats}
    inputs = {p["player_id"]: p["mean"] for p in _players()}
    for pid, target_mean in inputs.items():
        got = by_id[pid].mean
        tol = max(0.15 * target_mean, 1.0)
        assert abs(got - target_mean) <= tol, f"{pid}: got {got}, target {target_mean}"


def test_percentile_ordering():
    req = SimulateRequest.model_validate(base_request())
    resp = run_simulation(req)
    for p in resp.player_stats:
        assert p.p90 >= p.p75 >= p.median - 1e-6


def test_correlation_is_induced():
    req = SimulateRequest.model_validate(
        base_request(
            correlations=[{"player_id_a": "QB1", "player_id_b": "WR1", "rho": 0.8}],
            num_simulations=20000,
        )
    )
    # Re-run the low-level machinery to get raw draws for a direct correlation check.
    from app.simulation import _simulate_scores

    sims = _simulate_scores(req)
    idx = {p.player_id: i for i, p in enumerate(req.players)}
    a = sims[idx["QB1"], :]
    b = sims[idx["WR1"], :]
    corr = np.corrcoef(a, b)[0, 1]
    assert corr > 0.5


def test_threshold_probability_bounds():
    req = SimulateRequest.model_validate(base_request(threshold=15.0))
    resp = run_simulation(req)
    for p in resp.player_stats:
        assert p.prob_exceeds_threshold is not None
        assert 0.0 <= p.prob_exceeds_threshold <= 1.0


def test_threshold_none_gives_none_probability():
    req = SimulateRequest.model_validate(base_request(threshold=None))
    resp = run_simulation(req)
    for p in resp.player_stats:
        assert p.prob_exceeds_threshold is None


def test_lognormal_distribution_runs_and_matches_mean():
    req = SimulateRequest.model_validate(base_request(distribution="lognormal"))
    resp = run_simulation(req)
    assert resp.distribution == "lognormal"
    by_id = {p.player_id: p for p in resp.player_stats}
    inputs = {p["player_id"]: p["mean"] for p in _players()}
    for pid, target_mean in inputs.items():
        got = by_id[pid].mean
        tol = max(0.15 * target_mean, 1.0)
        assert abs(got - target_mean) <= tol


def test_truncated_normal_never_negative():
    req = SimulateRequest.model_validate(base_request(distribution="truncated_normal"))
    from app.simulation import _simulate_scores

    sims = _simulate_scores(req)
    assert np.all(sims >= 0.0)


def test_duplication_risk_proxy_within_bounds():
    lineups = [
        {"lineup_id": "L1", "player_ids": ["QB1", "WR1", "WR2", "RB1", "DST1", "TE1"], "ownership_sum": 90.0},
        {"lineup_id": "L2", "player_ids": ["QB1", "WR1", "RB1", "DST1", "TE1"], "ownership_sum": 40.0},
        {"lineup_id": "L3", "player_ids": ["WR2", "TE1"], "ownership_sum": 5.0},
    ]
    req = SimulateRequest.model_validate(base_request(lineups=lineups))
    resp = run_simulation(req)
    assert len(resp.lineup_stats) == 3
    for ls in resp.lineup_stats:
        assert 0.0 <= ls.duplication_risk_proxy <= 1.0
        assert ls.p90 >= ls.p75 >= ls.median - 1e-6


def test_num_simulations_and_seed_echoed():
    req = SimulateRequest.model_validate(base_request(num_simulations=1234, random_seed=7))
    resp = run_simulation(req)
    assert resp.num_simulations == 1234
    assert resp.seed_used == 7
