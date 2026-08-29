"""Small helpers shared across modules."""
from __future__ import annotations

from typing import Protocol

BASE_POSITION_PRIORITY = ("QB", "RB", "WR", "TE", "K")


class _PositionedPlayer(Protocol):
    position: str
    eligible_positions: frozenset[str]


def base_position(player: _PositionedPlayer) -> str:
    """The player's true position group (QB/RB/WR/TE/K), used for stack
    correlation and salary-rank fallback logic.

    Prefers the CSV's own "Position" column (`player.position`) since in
    Showdown, `eligible_positions` is just {"CPT"}/{"FLEX"} and can't tell a
    QB from a kicker; falls back to parsing `eligible_positions` (e.g.
    Classic's "RB/FLEX") when `position` wasn't captured.
    """
    pos = (player.position or "").strip().upper()
    if pos in BASE_POSITION_PRIORITY:
        return pos
    for candidate in BASE_POSITION_PRIORITY:
        if candidate in player.eligible_positions:
            return candidate
    return next(iter(player.eligible_positions), "FLEX")
