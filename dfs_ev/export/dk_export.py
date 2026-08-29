"""Export optimized lineups to the DK/FD upload CSV template: one row per
lineup, one column per roster slot (slot names repeated for multi-count
slots, e.g. RB,RB), each cell formatted as "Name (ID)" matching DK's own
player-pool CSV convention so the file round-trips through DK's uploader.
"""
from __future__ import annotations

import csv

from dfs_ev.optimizer.mip import Lineup
from dfs_ev.salary.models import ContestFormat


def _slot_columns(contest: ContestFormat) -> list[str]:
    columns: list[str] = []
    for slot in contest.roster_slots:
        columns.extend([slot.name] * slot.count)
    return columns


def export_dk_csv(lineups: list[Lineup], contest: ContestFormat, path: str) -> None:
    columns = _slot_columns(contest)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for lineup in lineups:
            by_slot: dict[str, list[str]] = {}
            for lp in lineup.players:
                cell = f"{lp.player.dk_name} ({lp.player.player_id})"
                by_slot.setdefault(lp.slot_name, []).append(cell)
            row = []
            for col in columns:
                bucket = by_slot.get(col, [])
                row.append(bucket.pop(0) if bucket else "")
            writer.writerow(row)
