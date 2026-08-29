from __future__ import annotations

import numpy as np

from dk_ev.payouts import cash_5050, sample_gpp


def test_cash_5050_pays_top_half():
    payout = cash_5050(field_size=100, entry_fee=10.0)
    assert payout.prize_for_rank(1) > 0
    assert payout.prize_for_rank(50) > 0
    assert payout.prize_for_rank(51) == 0


def test_sample_gpp_matches_worked_example_tiers():
    payout = sample_gpp(field_size=10_000, entry_fee=20.0)
    assert payout.prize_for_rank(1) == 25_000.0
    assert payout.prize_for_rank(50) == 1_000.0  # within top 1% but not 1st
    assert payout.prize_for_rank(500) == 20.0  # within top 10%
    assert payout.prize_for_rank(1500) == 5.0  # within top 20%
    assert payout.prize_for_rank(5000) == 0.0


def test_prizes_for_ranks_matches_scalar_lookup():
    payout = sample_gpp(field_size=10_000, entry_fee=20.0)
    ranks = np.array([1, 50, 500, 1500, 9999])
    vectorized = payout.prizes_for_ranks(ranks)
    scalar = np.array([payout.prize_for_rank(int(r)) for r in ranks])
    assert np.array_equal(vectorized, scalar)
