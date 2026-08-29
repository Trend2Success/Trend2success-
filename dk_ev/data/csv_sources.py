"""CSV-backed implementations of the data source Protocols.

``CsvSalarySource`` targets DraftKings' own contest-export CSV (tolerating a
couple of common header variants — ``TeamAbbrev`` vs ``Team``, an optional
``Game Info`` column used to derive ``Opponent`` when no explicit column is
present). ``CsvProjectionSource`` / ``CsvOwnershipSource`` target simple
user-supplied CSVs with the schemas documented in the README.
"""
from __future__ import annotations

import csv
from pathlib import Path

from dk_ev.data.interfaces import ProjectionRow, SalaryRow


def normalize_name(name: str) -> str:
    """Fold a player name to a stable join key across sources."""
    cleaned = name.strip().lower()
    for suffix in (" jr.", " jr", " sr.", " sr", " iii", " ii", " iv"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
    for ch in (".", "'", "-"):
        cleaned = cleaned.replace(ch, "")
    return " ".join(cleaned.split())


class CsvSalarySource:
    """Loads a DK contest salary export: Position, Name, Salary, Team, Opponent, AvgPointsPerGame."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> list[SalaryRow]:
        rows: list[SalaryRow] = []
        with self.path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            fieldnames = {f.strip(): f for f in (reader.fieldnames or [])}

            def get(row: dict, *candidates: str) -> str | None:
                for cand in candidates:
                    key = fieldnames.get(cand)
                    if key is not None and row.get(key, "").strip() != "":
                        return row[key].strip()
                return None

            for raw in reader:
                position_raw = get(raw, "Position", "Roster Position") or ""
                positions = tuple(p for p in position_raw.replace(" ", "").split("/") if p)
                name = get(raw, "Name", "Nickname") or ""
                salary_raw = get(raw, "Salary") or "0"
                salary = int(float(salary_raw.replace(",", "").replace("$", "")))
                team = get(raw, "TeamAbbrev", "Team") or ""
                opponent = get(raw, "Opponent")
                if opponent is None:
                    opponent = self._opponent_from_game_info(get(raw, "Game Info"), team)
                avg_pts_raw = get(raw, "AvgPointsPerGame")
                avg_pts = float(avg_pts_raw) if avg_pts_raw is not None else None
                player_id = get(raw, "ID", "Player ID") or f"{normalize_name(name)}:{team}"
                injury_status = get(raw, "Status", "Injury Status") or ""
                rows.append(
                    SalaryRow(
                        player_id=player_id,
                        name=name,
                        positions=positions,
                        salary=salary,
                        team=team,
                        opponent=opponent or "",
                        avg_points_per_game=avg_pts,
                        injury_status=injury_status,
                    )
                )
        return rows

    @staticmethod
    def _opponent_from_game_info(game_info: str | None, team: str) -> str:
        if not game_info or "@" not in game_info:
            return ""
        teams_part = game_info.split(" ")[0]
        away, _, home = teams_part.partition("@")
        away, home = away.strip(), home.strip()
        if team == away:
            return home
        if team == home:
            return away
        return ""


class CsvProjectionSource:
    """Loads user projections: player, projected_points, ceiling, floor, std_dev."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self, salaries: list[SalaryRow]) -> dict[str, ProjectionRow]:
        result: dict[str, ProjectionRow] = {}
        with self.path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for raw in reader:
                name = raw["player"].strip()
                projected = float(raw["projected_points"])
                ceiling = float(raw.get("ceiling") or projected * 1.5)
                floor = float(raw.get("floor") or projected * 0.5)
                std_dev = float(raw.get("std_dev") or max(projected * 0.3, 1.0))
                result[normalize_name(name)] = ProjectionRow(
                    name=name,
                    projected_points=projected,
                    ceiling=ceiling,
                    floor=floor,
                    std_dev=std_dev,
                )
        return result


class CsvOwnershipSource:
    """Loads user ownership projections: player, projected_ownership_pct."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(
        self, salaries: list[SalaryRow], projections: dict[str, ProjectionRow]
    ) -> dict[str, float]:
        result: dict[str, float] = {}
        with self.path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for raw in reader:
                name = raw["player"].strip()
                pct = float(raw["projected_ownership_pct"])
                result[normalize_name(name)] = pct
        return result
