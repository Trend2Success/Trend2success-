"""Data models for contest salaries/rosters, parsed from the DK/FD CSV.

Roster rules are derived from the CSV itself (see parser.py) rather than
hard-coded, since NCAAF slate formats vary by contest.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Site(str, Enum):
    DK = "dk"
    FD = "fd"


class FormatType(str, Enum):
    CLASSIC = "classic"
    SHOWDOWN = "showdown"


@dataclass(frozen=True)
class Player:
    """One selectable roster entry from the contest CSV.

    In DK Showdown, the same real player appears as two separate `Player`
    rows (one CPT, one FLEX) with different `player_id`/`salary`/`slot_name`
    but the same `dk_name`/`team`. `base_player_key` links them.
    """

    player_id: str
    dk_name: str
    team: str
    opponent: str | None
    salary: int
    slot_name: str  # raw roster-position token from the CSV, e.g. "RB/FLEX", "CPT"
    eligible_positions: frozenset[str]
    game_info: str | None = None
    is_captain: bool = False
    captain_multiplier: float = 1.0
    # True football position (from the CSV's "Position" column), independent
    # of roster-slot eligibility -- in Showdown, eligible_positions is just
    # {"CPT"}/{"FLEX"}, so this is the only place the real position lives.
    position: str = ""

    @property
    def base_player_key(self) -> str:
        """Identity shared across a player's CPT/FLEX rows in Showdown."""
        return f"{self.dk_name.strip().lower()}|{self.team.strip().lower()}"


@dataclass(frozen=True)
class RosterSlot:
    """One roster slot requirement, e.g. 'QB' x1 or 'FLEX' (RB/WR) x1."""

    name: str
    eligible_positions: frozenset[str]
    count: int = 1


@dataclass
class ContestFormat:
    site: Site
    format_type: FormatType
    salary_cap: int
    roster_slots: list[RosterSlot]
    players: list[Player]
    min_teams: int = 2
    max_players_per_team: int | None = None
    captain_slot_name: str | None = None  # e.g. "CPT" for Showdown
    captain_multiplier: float = 1.5

    @property
    def roster_size(self) -> int:
        return sum(slot.count for slot in self.roster_slots)

    def players_by_team(self) -> dict[str, list[Player]]:
        out: dict[str, list[Player]] = {}
        for p in self.players:
            out.setdefault(p.team, []).append(p)
        return out

    def teams(self) -> list[str]:
        return sorted({p.team for p in self.players})
