"""DraftKings-upload-ready CSV export.

DK's bulk-upload template uses one column per roster slot (in the sport's
slot order — duplicate slot labels like NFL's two ``RB`` columns repeat) and
one row per lineup, with each cell holding ``"Player Name (PlayerID)"``.

**Caveat**: DraftKings' own downloadable "entries" template for a *specific*
contest also carries ``Entry ID``, ``Contest ID``, and ``Contest Name``
columns so the upload can be matched to existing (possibly already-paid)
entries. This module cannot know those values — they only exist once you've
entered a contest and downloaded DK's entries CSV for it. The output here
covers the roster columns; to fill an existing entry, paste these roster
cells into the columns of that downloaded template (same column order,
same ``Name (ID)`` cell format) rather than uploading this file standalone.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from dk_ev.domain import Lineup
from dk_ev.rules import SportRules


def lineup_to_dk_row(lineup: Lineup) -> list[str]:
    return [f"{p.name} ({p.player_id})" for p in lineup.players]


def export_lineups_to_csv_string(lineups: list[Lineup], rules: SportRules) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(list(rules.slots))
    for lineup in lineups:
        writer.writerow(lineup_to_dk_row(lineup))
    return buf.getvalue()


def export_lineups_to_csv(lineups: list[Lineup], rules: SportRules, path: str | Path) -> None:
    Path(path).write_text(export_lineups_to_csv_string(lineups, rules), encoding="utf-8")
