"""Joins salary + projection + ownership sources into a slate of Players."""
from __future__ import annotations

from dk_ev.data.csv_sources import normalize_name
from dk_ev.data.interfaces import OwnershipSource, ProjectionSource, SalarySource
from dk_ev.domain import Player

# Injury/availability statuses DK marks a player with when they're confirmed
# not to play. "Q" (questionable), "P" (probable), and "GTD" are left in the
# pool since those players may still suit up.
INACTIVE_STATUSES = {"OUT", "O", "IR", "SUSP", "NA"}


def build_slate(
    salary_source: SalarySource,
    projection_source: ProjectionSource,
    ownership_source: OwnershipSource,
    exclude_inactive: bool = True,
) -> list[Player]:
    """Load and join all three sources into a list of :class:`Player`.

    Players with no matching projection are dropped (can't score what we
    can't project); a missing ownership entry defaults to 0%. Players DK
    marks as confirmed out (``exclude_inactive=True``, the default) are
    dropped too, since rostering a player who can't play is never correct
    regardless of their projection.
    """
    salaries = salary_source.load()
    if exclude_inactive:
        salaries = [s for s in salaries if s.injury_status.strip().upper() not in INACTIVE_STATUSES]
    projections = projection_source.load(salaries)
    ownership = ownership_source.load(salaries, projections)

    players: list[Player] = []
    for row in salaries:
        key = normalize_name(row.name)
        proj = projections.get(key)
        if proj is None:
            continue
        players.append(
            Player(
                player_id=row.player_id,
                name=row.name,
                positions=row.positions,
                team=row.team,
                opponent=row.opponent,
                salary=row.salary,
                projected_points=proj.projected_points,
                floor=proj.floor,
                ceiling=proj.ceiling,
                std_dev=proj.std_dev,
                ownership_pct=ownership.get(key, 0.0),
            )
        )
    return players
