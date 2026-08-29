"""DraftKings College Football (CFB) Classic/Showdown scoring.

IMPORTANT: this is a distinct config from DK's NFL scoring (see Module 3 of
the project spec) and the default values below were set from well-known,
long-standing DK CFB rules. This sandbox's outbound web access could not
reach draftkings.com to re-verify at build time -- confirm the point values
below against https://www.draftkings.com/help/rules/cfb before using this
for real-money contests, and override `ScoringConfig` fields if DK has
since changed anything.

Non-PPR by default (DK's site-wide convention), offense-only; kicker
scoring is included but should only be applied when the imported salary
CSV actually lists K-eligible players (see Module 2 -- do not assume
DK/FD CFB slates carry kickers).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringConfig:
    # Passing
    pass_yard_pt: float = 0.04  # 1 pt per 25 yds
    pass_td_pt: float = 4.0
    interception_pt: float = -1.0
    pass_300_bonus: float = 3.0
    pass_300_threshold: int = 300

    # Rushing
    rush_yard_pt: float = 0.1  # 1 pt per 10 yds
    rush_td_pt: float = 6.0
    rush_100_bonus: float = 3.0
    rush_100_threshold: int = 100

    # Receiving
    reception_pt: float = 0.0  # DK is non-PPR by default; set 1.0 for PPR slates
    rec_yard_pt: float = 0.1  # 1 pt per 10 yds
    rec_td_pt: float = 6.0
    rec_100_bonus: float = 3.0
    rec_100_threshold: int = 100

    # Turnovers / misc offense
    fumble_lost_pt: float = -1.0
    two_pt_conversion_pt: float = 2.0
    return_td_pt: float = 6.0  # punt/kickoff/FG return TD
    offensive_fumble_recovery_td_pt: float = 6.0

    # Kicker (only relevant if the CSV includes K-eligible players)
    fg_made_0_39_pt: float = 3.0
    fg_made_40_49_pt: float = 4.0
    fg_made_50_plus_pt: float = 5.0
    fg_missed_pt: float = 0.0
    extra_point_made_pt: float = 1.0


DK_CFB_CLASSIC_SCORING = ScoringConfig()


@dataclass
class StatLine:
    """Raw box-score/prop-derived stats for one player-game. All optional."""

    pass_yards: float = 0.0
    pass_tds: float = 0.0
    interceptions: float = 0.0
    rush_yards: float = 0.0
    rush_tds: float = 0.0
    receptions: float = 0.0
    rec_yards: float = 0.0
    rec_tds: float = 0.0
    fumbles_lost: float = 0.0
    two_pt_conversions: float = 0.0
    return_tds: float = 0.0
    fg_made_0_39: float = 0.0
    fg_made_40_49: float = 0.0
    fg_made_50_plus: float = 0.0
    extra_points_made: float = 0.0


def score_stat_line(stats: StatLine, config: ScoringConfig = DK_CFB_CLASSIC_SCORING) -> float:
    """Convert a raw stat line into DK CFB fantasy points."""
    pts = 0.0
    pts += stats.pass_yards * config.pass_yard_pt
    pts += stats.pass_tds * config.pass_td_pt
    pts += stats.interceptions * config.interception_pt
    if stats.pass_yards >= config.pass_300_threshold:
        pts += config.pass_300_bonus

    pts += stats.rush_yards * config.rush_yard_pt
    pts += stats.rush_tds * config.rush_td_pt
    if stats.rush_yards >= config.rush_100_threshold:
        pts += config.rush_100_bonus

    pts += stats.receptions * config.reception_pt
    pts += stats.rec_yards * config.rec_yard_pt
    pts += stats.rec_tds * config.rec_td_pt
    if stats.rec_yards >= config.rec_100_threshold:
        pts += config.rec_100_bonus

    pts += stats.fumbles_lost * config.fumble_lost_pt
    pts += stats.two_pt_conversions * config.two_pt_conversion_pt
    pts += stats.return_tds * config.return_td_pt

    pts += stats.fg_made_0_39 * config.fg_made_0_39_pt
    pts += stats.fg_made_40_49 * config.fg_made_40_49_pt
    pts += stats.fg_made_50_plus * config.fg_made_50_plus_pt
    pts += stats.extra_points_made * config.extra_point_made_pt

    return round(pts, 2)
