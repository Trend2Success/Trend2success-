"""Fallback data sources used when the user hasn't supplied a CSV.

``StubProjectionSource`` derives a projection + variance either from Vegas
odds (implied team total / spread, when supplied) or, absent that, from the
salary export's own ``AvgPointsPerGame`` column. ``NaiveOwnershipSource``
builds a chalk-proxy ownership distribution from projected points per
salary dollar, with per-player overrides.
"""
from __future__ import annotations

from dataclasses import dataclass

from dk_ev.data.csv_sources import normalize_name
from dk_ev.data.interfaces import ProjectionRow, SalaryRow


@dataclass(frozen=True)
class TeamOdds:
    """Simple Vegas inputs: implied point total for a team, and game total."""

    implied_team_total: float
    game_total: float


class StubProjectionSource:
    """Derives projections from odds when given, else from AvgPointsPerGame.

    ``team_odds`` maps team abbreviation -> :class:`TeamOdds`. When a
    player's team has odds available, the projection is scaled toward that
    team's share of implied scoring; otherwise we fall back to the DK
    export's own ``AvgPointsPerGame``, which is always present.
    """

    def __init__(self, team_odds: dict[str, TeamOdds] | None = None):
        self.team_odds = team_odds or {}

    def load(self, salaries: list[SalaryRow]) -> dict[str, ProjectionRow]:
        result: dict[str, ProjectionRow] = {}
        for row in salaries:
            # A reported 0.0 average is real signal (e.g. an unproven bench
            # player) and must be respected, not confused with a genuinely
            # absent column -- see the `or` pitfall this replaced.
            base = (
                row.avg_points_per_game
                if row.avg_points_per_game is not None
                else (row.salary / 1000.0)
            )
            odds = self.team_odds.get(row.team)
            if odds is not None and odds.implied_team_total > 0:
                league_avg_team_total = 22.0
                scale = odds.implied_team_total / league_avg_team_total
                projected = base * scale
            else:
                projected = base
            projected = max(projected, 0.5)
            std_dev = max(projected * 0.35, 1.0)
            result[normalize_name(row.name)] = ProjectionRow(
                name=row.name,
                projected_points=projected,
                ceiling=projected + 2 * std_dev,
                floor=max(projected - 1.5 * std_dev, 0.0),
                std_dev=std_dev,
            )
        return result


class NaiveOwnershipSource:
    """Ownership proxy from points-per-dollar ("value"), rescaled to sum to
    a plausible slate total, with optional per-player overrides.

    Real DK ownership is sharply concentrated (a handful of studs/chalk
    plays draw double-digit percentages while most of a deep player pool
    draws well under 1%), not linear in "value". ``concentration`` raises
    value to a power before normalizing so the naive proxy is shaped more
    like that: values near 1.0 barely change, but the gap between a stud
    and a scrub widens a lot. This matters most on deep slates (CFB, MLB)
    where hundreds of marginal players would otherwise each accumulate a
    non-trivial share and collectively make the simulated field
    unrealistically strong -- see the regression test for a worked example.
    """

    def __init__(
        self,
        overrides: dict[str, float] | None = None,
        target_field_size_pct: float = 900.0,
        concentration: float = 2.5,
    ):
        self.overrides = {normalize_name(k): v for k, v in (overrides or {}).items()}
        self.target_field_size_pct = target_field_size_pct
        self.concentration = concentration

    def load(
        self, salaries: list[SalaryRow], projections: dict[str, ProjectionRow]
    ) -> dict[str, float]:
        values: dict[str, float] = {}
        for row in salaries:
            key = normalize_name(row.name)
            proj = projections.get(key)
            if proj is None or row.salary <= 0:
                continue
            values[key] = proj.projected_points / (row.salary / 1000.0)

        weights = {key: max(value, 0.0) ** self.concentration for key, value in values.items()}
        total_weight = sum(weights.values()) or 1.0
        result: dict[str, float] = {}
        for key, weight in weights.items():
            result[key] = min(self.target_field_size_pct * weight / total_weight, 95.0)
        for key, pct in self.overrides.items():
            result[key] = pct
        return result
