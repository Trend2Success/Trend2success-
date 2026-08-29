"""Protocols for pluggable data sources.

Every data input the optimizer needs — salaries, projections, ownership,
payouts — is defined here as a small ``Protocol``. Concrete sources (CSV
files today, live APIs later) only need to satisfy the protocol's method
signature; nothing in the optimizer or simulator imports a concrete class
directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SalaryRow:
    """One row from a DK contest salary/positions export."""

    player_id: str
    name: str
    positions: tuple[str, ...]
    salary: int
    team: str
    opponent: str
    # None means the source column was absent entirely (fall back to a
    # salary-based heuristic); 0.0 is a real reported average and must be
    # respected as-is, not treated as "missing".
    avg_points_per_game: float | None
    injury_status: str = ""


@dataclass(frozen=True)
class ProjectionRow:
    """One player's projection inputs for the score distribution model."""

    name: str
    projected_points: float
    ceiling: float
    floor: float
    std_dev: float


class SalarySource(Protocol):
    """Supplies the slate: who's playing, at what salary, at what position(s)."""

    def load(self) -> list[SalaryRow]: ...


class ProjectionSource(Protocol):
    """Supplies point projections + variance, keyed by player name."""

    def load(self, salaries: list[SalaryRow]) -> dict[str, ProjectionRow]: ...


class OwnershipSource(Protocol):
    """Supplies projected ownership percentage, keyed by player name."""

    def load(
        self, salaries: list[SalaryRow], projections: dict[str, ProjectionRow]
    ) -> dict[str, float]: ...
