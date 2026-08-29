"""Protocol interfaces so the optimizer/simulator can run offline (sample
data) or against live sources (OpticOdds + DK/FD CSV) interchangeably.
"""
from __future__ import annotations

from typing import Iterable, Protocol

from dfs_ev.projections.derive import PlayerProjection
from dfs_ev.salary.models import ContestFormat, Player


class SlateSource(Protocol):
    """Provides the set of fixtures/games and OpticOdds player pool for a slate."""

    def get_fixtures(self, league: str = "ncaaf") -> list[dict]:
        ...

    def get_players(self, fixture_ids: Iterable[str]) -> list[dict]:
        ...


class SalarySource(Protocol):
    """Provides salaries, positions, and roster rules. DK/FD CSV is authoritative."""

    def load(self, path: str) -> ContestFormat:
        ...


class ProjectionSource(Protocol):
    """Provides a fantasy-point projection (+ variance) for a given player."""

    def project(self, player: Player) -> PlayerProjection:
        ...


class OwnershipSource(Protocol):
    """Provides a projected ownership percentage for a given player."""

    def ownership(self, player: Player) -> float:
        ...
