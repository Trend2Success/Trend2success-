"""Core domain types: players and lineups, independent of sport/rules/storage."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Player:
    """A single slate player with salary, positions, and projection inputs.

    ``positions`` holds every DK roster slot this player is eligible for
    (e.g. a DK "RB" is eligible for RB and FLEX once expanded by the rules
    engine). ``std_dev``/``floor``/``ceiling`` default from ``projected_points``
    when not supplied by a projections source, see data/stub_sources.py.
    """

    player_id: str
    name: str
    positions: tuple[str, ...]
    team: str
    opponent: str
    salary: int
    projected_points: float
    floor: float
    ceiling: float
    std_dev: float
    ownership_pct: float = 0.0

    @property
    def leverage_score(self) -> float:
        epsilon = 0.5
        return self.projected_points / (self.ownership_pct + epsilon)

    @property
    def value(self) -> float:
        """Points per $1000 of salary — a naive chalk/value proxy."""
        if self.salary <= 0:
            return 0.0
        return self.projected_points / (self.salary / 1000.0)


@dataclass
class Lineup:
    """A legal roster: one player per DK slot, in slot order."""

    slots: tuple[str, ...]
    players: tuple[Player, ...]
    lineup_id: str | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def salary(self) -> int:
        return sum(p.salary for p in self.players)

    @property
    def projected_points(self) -> float:
        return sum(p.projected_points for p in self.players)

    @property
    def ownership_sum(self) -> float:
        return sum(p.ownership_pct for p in self.players)

    @property
    def player_ids(self) -> frozenset[str]:
        return frozenset(p.player_id for p in self.players)

    def overlap(self, other: "Lineup") -> int:
        return len(self.player_ids & other.player_ids)

    def roster_string(self) -> str:
        return " | ".join(f"{slot}: {p.name}" for slot, p in zip(self.slots, self.players))

    def team_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for p in self.players:
            counts[p.team] = counts.get(p.team, 0) + 1
        return counts
