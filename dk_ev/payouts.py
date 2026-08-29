"""Contest payout structures: (rank-or-percentile, prize) tiers.

A :class:`PayoutStructure` resolves every tier to a ``max_rank`` (the worst
1-indexed finish that still cashes at that tier) so the simulator can look
up a prize with a single scan. Percentile tiers ("top 1%") are resolved to
a rank threshold using the structure's ``field_size``. Tiers are scanned in
ascending ``max_rank`` order and the *first* match wins, so tiers describe
non-overlapping bands (1st place's tier does not also count toward "top
1%"), matching how real DFS payout tables are laid out.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class PayoutTier:
    max_rank: int
    prize: float


@dataclass(frozen=True)
class PayoutStructure:
    name: str
    field_size: int
    entry_fee: float
    tiers: tuple[PayoutTier, ...]

    def __post_init__(self):
        object.__setattr__(self, "tiers", tuple(sorted(self.tiers, key=lambda t: t.max_rank)))

    def prize_for_rank(self, rank: int) -> float:
        for tier in self.tiers:
            if rank <= tier.max_rank:
                return tier.prize
        return 0.0

    def prizes_for_ranks(self, ranks: np.ndarray) -> np.ndarray:
        """Vectorized :meth:`prize_for_rank` over an array of ranks."""
        ranks = np.asarray(ranks)
        if not self.tiers:
            return np.zeros(ranks.shape, dtype=float)
        max_ranks = np.array([t.max_rank for t in self.tiers])
        prizes = np.array([t.prize for t in self.tiers])
        idx = np.searchsorted(max_ranks, ranks, side="left")
        result = np.zeros(ranks.shape, dtype=float)
        valid = idx < len(self.tiers)
        result[valid] = prizes[idx[valid]]
        return result

    @property
    def cash_line(self) -> int:
        """Worst rank that still wins any prize."""
        return self.tiers[-1].max_rank if self.tiers else 0


def tiers_from_spec(
    field_size: int, spec: list[tuple[int | None, float | None, float]]
) -> tuple[PayoutTier, ...]:
    """Build tiers from ``(rank, percentile, prize)`` triples; exactly one of
    ``rank``/``percentile`` should be set per entry.
    """
    tiers = []
    for rank, percentile, prize in spec:
        if rank is not None:
            max_rank = rank
        elif percentile is not None:
            max_rank = max(1, round(field_size * percentile))
        else:
            raise ValueError("each tier needs a rank or a percentile")
        tiers.append(PayoutTier(max_rank=max_rank, prize=prize))
    return tuple(tiers)


def load_payout_structure(path: str | Path, field_size: int | None = None) -> PayoutStructure:
    """Load a payout structure from JSON.

    Schema::

        {
          "name": "Sample GPP",
          "entry_fee": 20,
          "field_size": 10000,
          "tiers": [
            {"rank": 1, "prize": 25000},
            {"percentile": 0.01, "prize": 1000},
            {"percentile": 0.10, "prize": 20},
            {"percentile": 0.20, "prize": 5}
          ]
        }
    """
    data = json.loads(Path(path).read_text())
    resolved_field_size = field_size or data["field_size"]
    spec = [(t.get("rank"), t.get("percentile"), t["prize"]) for t in data["tiers"]]
    return PayoutStructure(
        name=data.get("name", Path(path).stem),
        field_size=resolved_field_size,
        entry_fee=data.get("entry_fee", 0.0),
        tiers=tiers_from_spec(resolved_field_size, spec),
    )


def cash_5050(field_size: int, entry_fee: float = 10.0, rake: float = 0.10) -> PayoutStructure:
    """A 50/50 (or double-up/H2H at n=2): top half doubles their entry fee,
    net of a house rake.
    """
    payout_multiple = 2 * (1 - rake)
    max_rank = max(1, field_size // 2)
    tiers = (PayoutTier(max_rank=max_rank, prize=round(entry_fee * payout_multiple, 2)),)
    return PayoutStructure(
        name="50/50 Cash", field_size=field_size, entry_fee=entry_fee, tiers=tiers
    )


def sample_gpp(field_size: int = 10_000, entry_fee: float = 20.0) -> PayoutStructure:
    """A single-entry GPP shaped like the spec's worked example:
    1st = $25k, top-1% = $1k, top-10% = $20, top-20% = $5, else $0.
    """
    spec = [
        (1, None, 25_000.0),
        (None, 0.01, 1_000.0),
        (None, 0.10, 20.0),
        (None, 0.20, 5.0),
    ]
    tiers = tiers_from_spec(field_size, spec)
    return PayoutStructure(
        name="Sample GPP", field_size=field_size, entry_fee=entry_fee, tiers=tiers
    )
