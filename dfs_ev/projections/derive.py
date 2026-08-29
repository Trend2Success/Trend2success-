"""Projection derivation: OpticOdds props -> DK CFB fantasy points, with a
missing-prop fallback chain and an ownership proxy.

Fallback chain per player (first available wins):
  1. user-supplied projection CSV
  2. OpticOdds prop-derived projection (if matched)
  3. salary-rank + team-total heuristic
  4. flagged "no projection" (floor-only / banned per caller's setting)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from dfs_ev.projections.odds_math import american_to_implied_prob, no_vig_probability
from dfs_ev.scoring.ncaaf_dk import DK_CFB_CLASSIC_SCORING, ScoringConfig

MIN_STD_FRACTION = 0.15
MAX_STD_FRACTION = 0.45

# Maps an OpticOdds player-prop market id to the DK CFB scoring coefficient
# that converts a raw stat unit into fantasy points, and the distribution
# kind used to interpret the market's line.
_YARDAGE = "yardage"
_COUNT = "count"  # e.g. TDs, receptions -- same math as yardage, just discrete
_TD_PROBABILITY = "td_probability"  # anytime_touchdown_scorer: line is a Yes probability

MARKET_SPEC: dict[str, tuple[str, str]] = {
    "player_passing_yards": (_YARDAGE, "pass_yard_pt"),
    "player_passing_touchdowns": (_COUNT, "pass_td_pt"),
    "player_rushing_yards": (_YARDAGE, "rush_yard_pt"),
    "player_receptions": (_COUNT, "reception_pt"),
    "player_receiving_yards": (_YARDAGE, "rec_yard_pt"),
    "player_touchdowns": (_COUNT, "rush_td_pt"),  # any-TD market; rush/rec pay the same
    "anytime_touchdown_scorer": (_TD_PROBABILITY, "rush_td_pt"),
}

DEFAULT_LINE_STEP = {
    "player_passing_yards": 5.0,
    "player_rushing_yards": 2.5,
    "player_receiving_yards": 2.5,
    "player_receptions": 0.5,
    "player_passing_touchdowns": 0.5,
    "player_touchdowns": 0.5,
}

# Rough share of a team's implied fantasy-point pool that flows to each
# position group -- used only for the tier-3 salary-rank fallback when a
# player has no matched prop at all. Deliberately coarse; documented as a
# last-resort heuristic, not a projection model.
POSITION_SHARE = {
    "QB": 0.34,
    "RB": 0.24,
    "WR": 0.28,
    "TE": 0.10,
    "K": 0.04,
}


@dataclass
class StatProjection:
    """A single prop market's derived stat-level projection (raw units)."""

    market: str
    mean: float
    std: float
    floor: float
    ceiling: float


@dataclass
class PlayerProjection:
    player_key: str
    projection: float  # mean fantasy points
    std_dev: float
    floor: float
    ceiling: float
    source: str  # "user_csv" | "prop" | "salary_heuristic" | "none"
    notes: str = ""
    matched_markets: list[str] = field(default_factory=list)


def derive_stat_projection(
    line: float,
    over_price: int | float,
    under_price: int | float | None = None,
    alt_lines: list[tuple[float, int | float]] | None = None,
    line_step: float | None = None,
) -> StatProjection:
    """Derive a stat-level mean/std/floor/ceiling from a prop line + price(s).

    alt_lines: optional list of (alt_line, over_price) pairs used to widen
    floor/ceiling and estimate std_dev from the alternate-line spread.
    """
    if under_price is not None:
        p_over, _ = no_vig_probability(over_price, under_price)
    else:
        p_over = american_to_implied_prob(over_price)

    step = line_step if line_step is not None else max(0.5, line * 0.02)
    mean = line + (p_over - 0.5) * 2 * step

    if alt_lines:
        alt_values = [a for a, _ in alt_lines] + [line]
        spread = max(alt_values) - min(alt_values)
        std = max(spread / 3.0, step * 0.5)
        floor = min(alt_values)
        ceiling = max(alt_values)
    else:
        std = max(step, mean * 0.25)
        floor = max(0.0, mean - 1.5 * std)
        ceiling = mean + 1.5 * std

    return StatProjection(market="", mean=max(0.0, mean), std=std, floor=floor, ceiling=ceiling)


def derive_player_projection(
    player_key: str,
    stat_projections: dict[str, StatProjection],
    scoring: ScoringConfig = DK_CFB_CLASSIC_SCORING,
) -> PlayerProjection | None:
    """Combine every matched prop market into one fantasy-point projection.

    Assumes independence across markets (sums means, sums variances) --
    a simplification; correlated within-game variance is instead modeled
    at the simulator layer via the game-environment shock.
    """
    if not stat_projections:
        return None

    total_mean = 0.0
    total_var = 0.0
    floor_sum = 0.0
    ceiling_sum = 0.0
    matched: list[str] = []

    for market, sp in stat_projections.items():
        spec = MARKET_SPEC.get(market)
        if spec is None:
            continue
        kind, coef_attr = spec
        coef = getattr(scoring, coef_attr)
        matched.append(market)

        if kind == _TD_PROBABILITY:
            p = min(max(sp.mean, 1e-6), 1 - 1e-6)
            lam = -math.log(1 - p)
            mean_pts = lam * coef
            var_pts = lam * coef * coef  # Poisson variance = lambda
            floor_pts = max(0.0, mean_pts - coef)
            ceiling_pts = mean_pts + 2 * coef
        else:
            mean_pts = sp.mean * coef
            var_pts = (sp.std * coef) ** 2
            floor_pts = sp.floor * coef
            ceiling_pts = sp.ceiling * coef

        total_mean += mean_pts
        total_var += var_pts
        floor_sum += floor_pts
        ceiling_sum += ceiling_pts

    if not matched:
        return None

    std_dev = total_var**0.5
    std_dev = min(max(std_dev, MIN_STD_FRACTION * total_mean), MAX_STD_FRACTION * max(total_mean, 0.01))
    floor = max(0.0, min(floor_sum, total_mean - std_dev))
    ceiling = max(ceiling_sum, total_mean + std_dev)

    return PlayerProjection(
        player_key=player_key,
        projection=round(total_mean, 2),
        std_dev=round(std_dev, 2),
        floor=round(floor, 2),
        ceiling=round(ceiling, 2),
        source="prop",
        matched_markets=matched,
    )


def salary_rank_heuristic_projection(
    player_key: str,
    position_group: str,
    salary: int,
    max_salary_in_position: int,
    team_implied_total: float,
) -> PlayerProjection:
    """Tier-3 fallback: distribute a team's implied point total across a
    position group by salary rank, when a player has no OpticOdds prop at
    all (common for depth players, walk-ons, FCS backups).
    """
    share = POSITION_SHARE.get(position_group, 0.06)
    strength = min(1.0, salary / max_salary_in_position) if max_salary_in_position else 0.5
    proj = max(0.5, team_implied_total * share * strength)
    std_dev = min(max(proj * 0.4, 1.0), proj * MAX_STD_FRACTION if proj > 0 else 1.0)
    return PlayerProjection(
        player_key=player_key,
        projection=round(proj, 2),
        std_dev=round(std_dev, 2),
        floor=round(max(0.0, proj - std_dev), 2),
        ceiling=round(proj + std_dev, 2),
        source="salary_heuristic",
        notes="salary-rank + team-total heuristic (no matched OpticOdds prop)",
    )


def build_projection(
    player_key: str,
    user_projection: float | None = None,
    user_std_dev: float | None = None,
    prop_projection: PlayerProjection | None = None,
    fallback_projection: PlayerProjection | None = None,
) -> PlayerProjection:
    """Apply the 4-tier fallback chain for one player."""
    if user_projection is not None:
        std = user_std_dev if user_std_dev is not None else max(
            MIN_STD_FRACTION * user_projection, 0.5
        )
        std = min(max(std, MIN_STD_FRACTION * user_projection), MAX_STD_FRACTION * max(user_projection, 0.01))
        return PlayerProjection(
            player_key=player_key,
            projection=round(user_projection, 2),
            std_dev=round(std, 2),
            floor=round(max(0.0, user_projection - std), 2),
            ceiling=round(user_projection + std, 2),
            source="user_csv",
        )
    if prop_projection is not None:
        return prop_projection
    if fallback_projection is not None:
        return fallback_projection
    return PlayerProjection(
        player_key=player_key,
        projection=0.0,
        std_dev=0.0,
        floor=0.0,
        ceiling=0.0,
        source="none",
        notes="no projection available: no user CSV, no matched prop, no salary/team-total heuristic input",
    )


def projection_for_player_row(player, projections: dict[str, "PlayerProjection"]) -> "PlayerProjection | None":
    """Resolve a projection for one contest-CSV roster row (e.g. a specific
    Showdown CPT or FLEX row), applying the row's captain_multiplier when
    the caller only supplied one projection per real person (keyed by
    `base_player_key`) rather than per row.
    """
    proj = projections.get(player.player_id)
    if proj is not None:
        return proj
    proj = projections.get(player.base_player_key)
    if proj is None:
        return None
    mult = player.captain_multiplier
    if mult == 1.0:
        return proj
    return PlayerProjection(
        player_key=player.player_id,
        projection=round(proj.projection * mult, 2),
        std_dev=round(proj.std_dev * mult, 2),
        floor=round(proj.floor * mult, 2),
        ceiling=round(proj.ceiling * mult, 2),
        source=proj.source,
        notes=proj.notes,
        matched_markets=list(proj.matched_markets),
    )


def ownership_proxy(
    projections: dict[str, PlayerProjection],
    salaries: dict[str, int],
    positions: dict[str, str],
) -> dict[str, float]:
    """Derive a chalkiness proxy (0-1, NOT a probability) from
    projection-per-salary rank within position. OpticOdds provides no real
    ownership data; this is the documented weakest input in the pipeline
    and should be overridden by a user ownership CSV when available.
    """
    by_position: dict[str, list[str]] = {}
    for key, pos in positions.items():
        by_position.setdefault(pos, []).append(key)

    proxy: dict[str, float] = {}
    for pos, keys in by_position.items():
        scored = []
        for k in keys:
            proj = projections.get(k)
            salary = salaries.get(k, 0)
            value = (proj.projection / salary) if proj and salary else 0.0
            scored.append((k, value))
        scored.sort(key=lambda kv: kv[1], reverse=True)
        n = len(scored)
        for rank, (k, _) in enumerate(scored):
            proxy[k] = round(1.0 - rank / max(n - 1, 1), 4) if n > 1 else 1.0
    return proxy
