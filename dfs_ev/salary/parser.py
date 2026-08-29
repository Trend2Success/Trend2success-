"""Parse DraftKings/FanDuel contest CSVs into a `ContestFormat`.

The contest CSV (not this code) is the source of truth for salaries,
positions, and roster slots -- CFB roster rules are NOT hard-coded here
because slate format varies (Classic full-slate vs. Showdown/Captain Mode,
and occasional site tweaks like S-FLEX). Two supported layouts:

1. Plain player-pool export (most common: "DKSalaries.csv"): a single
   table with header
       Position,Name + ID,Name,ID,Roster Position,Salary,Game Info,TeamAbbrev,AvgPointsPerGame
   Roster slot *names* are derived from the `Roster Position` column's
   eligibility tokens (e.g. "RB/FLEX"); Showdown slot *counts* are DK's
   fixed site-wide contest-type convention (1 CPT + 5 FLEX), not a
   CFB-specific rule. Classic slot counts default to one of each distinct
   position token found, which is a best-effort inference -- see
   `import_warnings` on the returned result.

2. Upload-template export with an explicit roster-slot header row placed
   directly above the player-pool table, e.g.:
       QB,RB,RB,WR,WR,WR,FLEX,S-FLEX
       Position,Name + ID,Name,ID,Roster Position,Salary,Game Info,TeamAbbrev,AvgPointsPerGame
       ...
   This is the ground truth when present and removes all guesswork.

FanDuel CSVs use different column names ("Nickname" instead of "Name",
"FPPG", "Injury Indicator", etc.); `parse_fd_csv` maps those onto the same
internal model.
"""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass, field

from dfs_ev.salary.models import ContestFormat, FormatType, Player, RosterSlot, Site

DK_POOL_HEADER_MARKERS = {"position", "name + id", "name", "id", "roster position", "salary"}
# Uppercase, since _split_positions() always upper-cases eligibility tokens.
SHOWDOWN_TOKENS = {"CPT", "CAPTAIN", "MVP"}


@dataclass
class ParseResult:
    contest: ContestFormat
    warnings: list[str] = field(default_factory=list)


def _read_rows(path: str) -> list[list[str]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [row for row in csv.reader(fh)]


def _find_pool_header_row(rows: list[list[str]]) -> int:
    for idx, row in enumerate(rows):
        cells = {c.strip().lower() for c in row if c.strip()}
        if {"position", "roster position", "salary"}.issubset(cells):
            return idx
    raise ValueError(
        "Could not locate the player-pool header row (expected a row containing "
        "'Position', 'Roster Position', and 'Salary')."
    )


def _explicit_slot_row(rows: list[list[str]], pool_header_idx: int) -> list[str] | None:
    for idx in range(pool_header_idx - 1, -1, -1):
        cells = [c.strip() for c in rows[idx] if c.strip()]
        if not cells:
            continue
        lowered = {c.lower() for c in cells}
        if lowered & DK_POOL_HEADER_MARKERS:
            # This is another header-ish row, not a slot row.
            return None
        return cells
    return None


def _split_positions(roster_position: str) -> frozenset[str]:
    return frozenset(p.strip().upper() for p in roster_position.split("/") if p.strip())


def _build_players(
    rows: list[list[str]],
    header: list[str],
    data_rows: list[list[str]],
    name_col: str,
    id_col: str,
    team_col: str,
    salary_col: str,
    roster_pos_col: str,
    game_info_col: str | None,
    opponent_col: str | None,
    position_col: str | None = None,
) -> list[Player]:
    idx = {h.strip().lower(): i for i, h in enumerate(header)}

    def cell(row: list[str], col: str | None) -> str | None:
        if col is None:
            return None
        i = idx.get(col.lower())
        if i is None or i >= len(row):
            return None
        v = row[i].strip()
        return v or None

    players: list[Player] = []
    for row in data_rows:
        if not any(c.strip() for c in row):
            continue
        name = cell(row, name_col)
        pid = cell(row, id_col)
        team = cell(row, team_col)
        salary_raw = cell(row, salary_col)
        roster_pos = cell(row, roster_pos_col)
        if not (name and pid and team and salary_raw and roster_pos):
            continue
        game_info = cell(row, game_info_col)
        opponent = cell(row, opponent_col)
        if opponent is None and game_info and team:
            opponent = _opponent_from_game_info(game_info, team)
        eligible = _split_positions(roster_pos)
        is_captain = bool(eligible & SHOWDOWN_TOKENS)
        position = (cell(row, position_col) or "").strip().upper()
        players.append(
            Player(
                player_id=pid,
                dk_name=name,
                team=team,
                opponent=opponent,
                salary=int(float(salary_raw)),
                slot_name=roster_pos,
                eligible_positions=eligible,
                game_info=game_info,
                is_captain=is_captain,
                captain_multiplier=1.5 if is_captain else 1.0,
                position=position,
            )
        )
    return players


def _opponent_from_game_info(game_info: str, team: str) -> str | None:
    # Game Info commonly looks like "SF@LAR 09/10/2023 08:20PM ET"
    matchup = game_info.split(" ")[0]
    if "@" not in matchup:
        return None
    away, home = matchup.split("@", 1)
    team_u = team.strip().upper()
    if team_u == away.strip().upper():
        return home.strip()
    if team_u == home.strip().upper():
        return away.strip()
    return None


def _detect_format(players: list[Player]) -> FormatType:
    all_tokens: set[str] = set()
    for p in players:
        all_tokens |= p.eligible_positions
    if all_tokens & SHOWDOWN_TOKENS:
        return FormatType.SHOWDOWN
    return FormatType.CLASSIC


def _derive_roster_slots(
    players: list[Player], format_type: FormatType, warnings: list[str]
) -> tuple[list[RosterSlot], str | None]:
    if format_type == FormatType.SHOWDOWN:
        cpt_positions = frozenset({"CPT"}) | SHOWDOWN_TOKENS
        return (
            [
                RosterSlot(name="CPT", eligible_positions=cpt_positions, count=1),
                RosterSlot(name="FLEX", eligible_positions=frozenset({"FLEX"}), count=5),
            ],
            "CPT",
        )
    # Classic: best-effort -- one slot per distinct non-FLEX token, sized 1,
    # plus one FLEX slot per distinct flex-style token if present.
    base_tokens: set[str] = set()
    flex_tokens: set[str] = set()
    for p in players:
        for tok in p.eligible_positions:
            if "FLEX" in tok:
                flex_tokens.add(tok)
            else:
                base_tokens.add(tok)
    slots = [RosterSlot(name=t, eligible_positions=frozenset({t}), count=1) for t in sorted(base_tokens)]
    for t in sorted(flex_tokens):
        eligible = frozenset(
            tok for p in players for tok in p.eligible_positions if t in p.eligible_positions
        ) - {t}
        eligible = eligible or frozenset({t})
        slots.append(RosterSlot(name=t, eligible_positions=eligible, count=1))
    warnings.append(
        "No explicit roster-slot template row found; inferred one slot per distinct "
        "position/flex token from the player pool (count=1 each). Provide an explicit "
        "slot-template row above the player pool for exact roster construction."
    )
    return slots, None


def parse_dk_csv(path: str) -> ParseResult:
    return _parse_csv(path, site=Site.DK)


def parse_fd_csv(path: str) -> ParseResult:
    return _parse_csv(path, site=Site.FD)


def _parse_csv(path: str, site: Site) -> ParseResult:
    rows = _read_rows(path)
    pool_idx = _find_pool_header_row(rows)
    header = rows[pool_idx]
    data_rows = rows[pool_idx + 1 :]
    explicit_slots = _explicit_slot_row(rows, pool_idx)

    header_lower = [h.strip().lower() for h in header]

    if site == Site.DK:
        name_col = "name"
        id_col = "id"
        team_col = "teamabbrev" if "teamabbrev" in header_lower else "team"
        salary_col = "salary"
        roster_pos_col = "roster position"
        game_info_col = "game info" if "game info" in header_lower else None
        opponent_col = None
        position_col = "position"
    else:
        name_col = "nickname" if "nickname" in header_lower else "name"
        id_col = "id"
        team_col = "team"
        salary_col = "salary"
        roster_pos_col = "position"
        game_info_col = "game" if "game" in header_lower else None
        opponent_col = "opponent" if "opponent" in header_lower else None
        position_col = "position"

    players = _build_players(
        rows, header, data_rows, name_col, id_col, team_col, salary_col, roster_pos_col,
        game_info_col, opponent_col, position_col,
    )
    if not players:
        raise ValueError(f"No players parsed from {path}; check the CSV layout.")

    format_type = _detect_format(players)
    warnings: list[str] = []

    if explicit_slots:
        slot_counts: dict[str, int] = {}
        for tok in explicit_slots:
            slot_counts[tok] = slot_counts.get(tok, 0) + 1
        roster_slots = [
            # Eligibility is exactly "this token appears in the player's
            # Roster Position": a player carrying "WR/FLEX/S-FLEX" must NOT
            # become QB-eligible just because some QB also carries S-FLEX.
            RosterSlot(name=name, eligible_positions=frozenset({name}), count=count)
            for name, count in slot_counts.items()
        ]
        captain_slot_name = next((s.name for s in roster_slots if s.name.upper() in {"CPT", "CAPTAIN", "MVP"}), None)
    else:
        roster_slots, captain_slot_name = _derive_roster_slots(players, format_type, warnings)

    cap = 50_000 if site == Site.DK else 60_000
    max_per_team = 5 if format_type == FormatType.SHOWDOWN else None
    min_teams = 2 if format_type == FormatType.SHOWDOWN else 2

    contest = ContestFormat(
        site=site,
        format_type=format_type,
        salary_cap=cap,
        roster_slots=roster_slots,
        players=players,
        min_teams=min_teams,
        max_players_per_team=max_per_team,
        captain_slot_name=captain_slot_name,
        captain_multiplier=1.5,
    )
    for w in warnings:
        print(f"[dfs_ev][import] WARNING: {w}", file=sys.stderr)
    return ParseResult(contest=contest, warnings=warnings)
