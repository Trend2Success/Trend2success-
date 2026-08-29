"""DraftKings per-sport contest rules: roster slots, salary cap, team limits.

Each sport's classic-contest rules are encoded as a ``SportRules`` instance.
``slot_eligibility`` maps every roster slot to the set of raw DK positions
that may fill it (e.g. NFL FLEX accepts RB/WR/TE).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SportRules:
    sport: str
    salary_cap: int
    slots: tuple[str, ...]
    slot_eligibility: dict[str, tuple[str, ...]]
    max_players_per_team: int
    roster_size: int

    def eligible_positions_for_slot(self, slot: str) -> tuple[str, ...]:
        return self.slot_eligibility[slot]

    def player_eligible_for_slot(self, player_positions: tuple[str, ...], slot: str) -> bool:
        return any(pos in self.slot_eligibility[slot] for pos in player_positions)


NFL_RULES = SportRules(
    sport="nfl",
    salary_cap=50_000,
    slots=("QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST"),
    slot_eligibility={
        "QB": ("QB",),
        "RB": ("RB",),
        "WR": ("WR",),
        "TE": ("TE",),
        "FLEX": ("RB", "WR", "TE"),
        "DST": ("DST",),
    },
    max_players_per_team=4,
    roster_size=9,
)

NBA_RULES = SportRules(
    sport="nba",
    salary_cap=50_000,
    slots=("PG", "SG", "SF", "PF", "C", "G", "F", "UTIL"),
    slot_eligibility={
        "PG": ("PG",),
        "SG": ("SG",),
        "SF": ("SF",),
        "PF": ("PF",),
        "C": ("C",),
        "G": ("PG", "SG"),
        "F": ("SF", "PF"),
        "UTIL": ("PG", "SG", "SF", "PF", "C"),
    },
    max_players_per_team=3,
    roster_size=8,
)

MLB_RULES = SportRules(
    sport="mlb",
    salary_cap=50_000,
    slots=("P", "P", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF"),
    slot_eligibility={
        "P": ("P", "SP", "RP"),
        "C": ("C",),
        "1B": ("1B",),
        "2B": ("2B",),
        "3B": ("3B",),
        "SS": ("SS",),
        "OF": ("OF",),
    },
    max_players_per_team=5,
    roster_size=10,
)

CFB_RULES = SportRules(
    sport="cfb",
    salary_cap=50_000,
    # DK's college football Classic slate has no TE or DST: tight ends are
    # pooled into the WR position, and DK does not score CFB team defenses.
    slots=("QB", "RB", "RB", "WR", "WR", "WR", "FLEX", "SFLEX"),
    slot_eligibility={
        "QB": ("QB",),
        "RB": ("RB",),
        "WR": ("WR",),
        "FLEX": ("RB", "WR"),
        "SFLEX": ("QB", "RB", "WR"),
    },
    max_players_per_team=5,
    roster_size=8,
)

SPORT_RULES: dict[str, SportRules] = {
    "nfl": NFL_RULES,
    "nba": NBA_RULES,
    "mlb": MLB_RULES,
    "cfb": CFB_RULES,
}


def get_rules(sport: str) -> SportRules:
    try:
        return SPORT_RULES[sport.lower()]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported sport {sport!r}; choose one of {sorted(SPORT_RULES)}"
        ) from exc
