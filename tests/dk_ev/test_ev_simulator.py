from __future__ import annotations

import numpy as np
import pytest

from dk_ev.domain import Lineup
from dk_ev.payouts import sample_gpp
from dk_ev.rules import NFL_RULES
from dk_ev.simulation.ev_simulator import _HAS_NUMBA, EVSimulator, SimulatorConfig

from .fixtures import make_player, small_nfl_slate


def build_lineup(slate, ids_by_slot: list[str]) -> Lineup:
    by_id = {p.player_id: p for p in slate}
    return Lineup(slots=NFL_RULES.slots, players=tuple(by_id[i] for i in ids_by_slot))


def test_all_floor_lineup_has_near_zero_itm_in_gpp_field():
    """A lineup built entirely from low-ceiling, low-ownership scrubs should
    almost never crack the payout tiers of a competitive GPP field.
    """
    slate = small_nfl_slate()
    # build a fresh set of guaranteed-worst players with near-zero ceiling
    worst = [
        make_player("w_qb", "Worst QB", ("QB",), "NYG", "DAL", 5000, 8.0, ownership_pct=0.5, std_dev=0.5, floor=6.0, ceiling=9.0),
        make_player("w_rb1", "Worst RB1", ("RB",), "NYG", "DAL", 3000, 4.0, ownership_pct=0.5, std_dev=0.5, floor=3.0, ceiling=5.0),
        make_player("w_rb2", "Worst RB2", ("RB",), "DAL", "NYG", 3000, 4.0, ownership_pct=0.5, std_dev=0.5, floor=3.0, ceiling=5.0),
        make_player("w_wr1", "Worst WR1", ("WR",), "NYG", "DAL", 3000, 3.0, ownership_pct=0.5, std_dev=0.5, floor=2.0, ceiling=4.0),
        make_player("w_wr2", "Worst WR2", ("WR",), "DAL", "NYG", 3000, 3.0, ownership_pct=0.5, std_dev=0.5, floor=2.0, ceiling=4.0),
        make_player("w_wr3", "Worst WR3", ("WR",), "NYG", "DAL", 3000, 3.0, ownership_pct=0.5, std_dev=0.5, floor=2.0, ceiling=4.0),
        make_player("w_te", "Worst TE", ("TE",), "DAL", "NYG", 2500, 2.0, ownership_pct=0.5, std_dev=0.5, floor=1.0, ceiling=3.0),
        make_player("w_flex", "Worst FLEX", ("RB",), "NYG", "DAL", 2600, 3.0, ownership_pct=0.5, std_dev=0.5, floor=2.0, ceiling=4.0),
        make_player("w_dst", "Worst DST", ("DST",), "DAL", "NYG", 2000, 1.0, ownership_pct=0.5, std_dev=0.3, floor=0.0, ceiling=2.0),
    ]
    pool = slate + worst
    worst_lineup = Lineup(slots=NFL_RULES.slots, players=tuple(worst))

    payout = sample_gpp(field_size=5_000, entry_fee=20.0)
    config = SimulatorConfig(n_iterations=2000, field_sample_size=150, random_seed=42)
    simulator = EVSimulator(pool, NFL_RULES, payout, config)

    result = simulator.simulate(worst_lineup)

    assert result.itm_pct < 0.02
    assert result.top1_pct_rate == 0.0
    assert result.ev < 5.0


def test_stronger_lineup_has_higher_ev_than_weaker_lineup():
    slate = small_nfl_slate()
    payout = sample_gpp(field_size=2_000, entry_fee=20.0)
    config = SimulatorConfig(n_iterations=2000, field_sample_size=150, random_seed=7)
    simulator = EVSimulator(slate, NFL_RULES, payout, config)

    strong = build_lineup(
        slate, ["qb1", "rb1", "rb2", "wr1", "wr2", "wr3", "te1", "rb3", "dst1"]
    )

    # a clearly weaker, but still legal, lineup (swap in cheap/low-projection players)
    weak = Lineup(
        slots=NFL_RULES.slots,
        players=(
            next(p for p in slate if p.player_id == "qb2"),
            next(p for p in slate if p.player_id == "rb3"),
            next(p for p in slate if p.player_id == "rb4"),
            next(p for p in slate if p.player_id == "wr3"),
            next(p for p in slate if p.player_id == "wr4"),
            next(p for p in slate if p.player_id == "wr5"),
            next(p for p in slate if p.player_id == "te2"),
            next(p for p in slate if p.player_id == "te1"),
            next(p for p in slate if p.player_id == "dst2"),
        ),
    )

    strong_result = simulator.simulate(strong)
    weak_result = simulator.simulate(weak)

    assert strong_result.mean_score > weak_result.mean_score
    assert strong_result.ev >= weak_result.ev
    assert strong_result.itm_pct >= weak_result.itm_pct


def test_ceiling_and_floor_bracket_mean_score():
    slate = small_nfl_slate()
    payout = sample_gpp(field_size=1_000, entry_fee=20.0)
    config = SimulatorConfig(n_iterations=1500, field_sample_size=100, random_seed=1)
    simulator = EVSimulator(slate, NFL_RULES, payout, config)
    lineup = build_lineup(
        slate, ["qb1", "rb1", "rb2", "wr1", "wr2", "wr3", "te1", "rb3", "dst1"]
    )
    result = simulator.simulate(lineup)
    assert result.floor <= result.mean_score <= result.ceiling


def test_win_rate_and_itm_are_bounded_probabilities():
    slate = small_nfl_slate()
    payout = sample_gpp(field_size=1_000, entry_fee=20.0)
    config = SimulatorConfig(n_iterations=1000, field_sample_size=80, random_seed=3)
    simulator = EVSimulator(slate, NFL_RULES, payout, config)
    lineup = build_lineup(
        slate, ["qb1", "rb1", "rb2", "wr1", "wr2", "wr3", "te1", "rb3", "dst1"]
    )
    result = simulator.simulate(lineup)
    for pct in (result.itm_pct, result.win_pct, result.top1_pct_rate, result.top10_pct_rate):
        assert 0.0 <= pct <= 1.0
    assert result.win_pct <= result.top1_pct_rate <= result.top10_pct_rate <= result.itm_pct


@pytest.mark.skipif(not _HAS_NUMBA, reason="numba not installed")
def test_numba_kernel_matches_numpy_fallback_exactly():
    """The numba-accelerated inner loop must be a drop-in replacement for
    the vectorized numpy path -- same seed, same random draws consumed,
    identical result.
    """
    slate = small_nfl_slate()
    payout = sample_gpp(field_size=1_000, entry_fee=20.0)
    lineup = build_lineup(
        slate, ["qb1", "rb1", "rb2", "wr1", "wr2", "wr3", "te1", "rb3", "dst1"]
    )

    numba_config = SimulatorConfig(n_iterations=1000, field_sample_size=80, random_seed=99, use_numba=True)
    numba_result = EVSimulator(slate, NFL_RULES, payout, numba_config).simulate(lineup)

    numpy_config = SimulatorConfig(n_iterations=1000, field_sample_size=80, random_seed=99, use_numba=False)
    numpy_result = EVSimulator(slate, NFL_RULES, payout, numpy_config).simulate(lineup)

    assert numba_result.ev == numpy_result.ev
    assert numba_result.itm_pct == numpy_result.itm_pct
    assert numba_result.median_rank == numpy_result.median_rank


@pytest.mark.skipif(not _HAS_NUMBA, reason="numba not installed")
def test_numba_beaten_count_kernel_matches_numpy_on_random_data():
    from dk_ev.simulation.ev_simulator import _count_beaten_numba, _count_beaten_numpy

    rng = np.random.default_rng(0)
    field_scores = rng.normal(150, 20, size=(500, 300))
    candidate_scores = rng.normal(150, 20, size=500)

    beaten_numba = _count_beaten_numba(field_scores, candidate_scores)
    beaten_numpy = _count_beaten_numpy(field_scores, candidate_scores)
    assert np.array_equal(beaten_numba, beaten_numpy)
