"""Fuzzy name matching between DK/FD CSV players and OpticOdds players.

College football names are messier than pro sports: nicknames, Jr/Sr/III
suffixes, hyphenated/compound last names, and abbreviated first names all
cause naive exact-match misses. This module normalizes names, scores
candidate matches by name similarity + team/opponent agreement, and
supports a manual alias override file plus a "needs review" queue for
anything below a confidence threshold.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
REVIEW_THRESHOLD = 0.82
AUTO_ACCEPT_THRESHOLD = 0.92


def normalize_name(name: str) -> str:
    """Lowercase, strip accents/punctuation/suffixes, collapse whitespace."""
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    ascii_name = ascii_name.lower()
    ascii_name = re.sub(r"[.'`]", "", ascii_name)
    ascii_name = re.sub(r"[-]", " ", ascii_name)
    tokens = [t for t in re.split(r"\s+", ascii_name.strip()) if t]
    tokens = [t for t in tokens if t not in SUFFIXES]
    return " ".join(tokens)


def normalize_team(team: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (team or "").lower())


@dataclass
class OpticOddsPlayer:
    player_id: str
    name: str
    team: str
    fixture_id: str | None = None


@dataclass
class MatchResult:
    dk_name: str
    dk_team: str
    oo_player_id: str | None
    oo_name: str | None
    confidence: float
    method: str  # "alias" | "exact" | "fuzzy" | "unmatched"
    needs_review: bool


@dataclass
class AliasEntry:
    dk_name: str
    team: str
    oo_player_id: str
    oo_player_name: str = ""


def load_aliases(path: str | Path) -> dict[tuple[str, str], AliasEntry]:
    """Load manual overrides keyed by (normalized dk_name, normalized team)."""
    p = Path(path)
    aliases: dict[tuple[str, str], AliasEntry] = {}
    if not p.exists():
        return aliases
    with p.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            dk_name = row.get("player_dk_name") or row.get("dk_name") or ""
            team = row.get("team", "")
            oo_id = row.get("oo_player_id", "")
            if not dk_name or not oo_id:
                continue
            key = (normalize_name(dk_name), normalize_team(team))
            aliases[key] = AliasEntry(
                dk_name=dk_name, team=team, oo_player_id=oo_id, oo_player_name=row.get("oo_player_name", "")
            )
    return aliases


@dataclass
class NameMatcher:
    oo_players: list[OpticOddsPlayer]
    aliases: dict[tuple[str, str], AliasEntry] = field(default_factory=dict)
    review_threshold: float = REVIEW_THRESHOLD
    auto_accept_threshold: float = AUTO_ACCEPT_THRESHOLD

    def __post_init__(self) -> None:
        self._by_team: dict[str, list[OpticOddsPlayer]] = {}
        for op in self.oo_players:
            self._by_team.setdefault(normalize_team(op.team), []).append(op)

    def match(self, dk_name: str, dk_team: str) -> MatchResult:
        norm_dk = normalize_name(dk_name)
        norm_team = normalize_team(dk_team)

        alias = self.aliases.get((norm_dk, norm_team))
        if alias:
            return MatchResult(
                dk_name=dk_name,
                dk_team=dk_team,
                oo_player_id=alias.oo_player_id,
                oo_name=alias.oo_player_name or None,
                confidence=1.0,
                method="alias",
                needs_review=False,
            )

        candidates = self._by_team.get(norm_team, self.oo_players)
        best: OpticOddsPlayer | None = None
        best_score = 0.0
        for cand in candidates:
            score = SequenceMatcher(None, norm_dk, normalize_name(cand.name)).ratio()
            if norm_team and normalize_team(cand.team) == norm_team:
                score = min(1.0, score + 0.05)
            if score > best_score:
                best_score = score
                best = cand

        if best is None:
            return MatchResult(
                dk_name=dk_name, dk_team=dk_team, oo_player_id=None, oo_name=None,
                confidence=0.0, method="unmatched", needs_review=True,
            )

        method = "exact" if best_score >= 0.999 else "fuzzy"
        needs_review = best_score < self.auto_accept_threshold
        return MatchResult(
            dk_name=dk_name,
            dk_team=dk_team,
            oo_player_id=best.player_id,
            oo_name=best.name,
            confidence=round(best_score, 4),
            method=method,
            needs_review=needs_review,
        )

    def match_all(self, dk_players: list[tuple[str, str]]) -> list[MatchResult]:
        return [self.match(name, team) for name, team in dk_players]

    @staticmethod
    def review_queue(results: list[MatchResult]) -> list[MatchResult]:
        return [r for r in results if r.needs_review]
