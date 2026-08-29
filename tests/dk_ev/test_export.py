from __future__ import annotations

import csv
import io

from dk_ev.domain import Lineup
from dk_ev.export import export_lineups_to_csv_string
from dk_ev.rules import MLB_RULES, NBA_RULES, NFL_RULES

from .fixtures import small_nfl_slate


def _lineup_from_slate(slate, ids):
    by_id = {p.player_id: p for p in slate}
    return Lineup(slots=NFL_RULES.slots, players=tuple(by_id[i] for i in ids))


def test_nfl_header_matches_dk_slot_order():
    csv_text = export_lineups_to_csv_string([], NFL_RULES)
    header = next(csv.reader(io.StringIO(csv_text)))
    assert header == ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST"]


def test_nba_header_matches_dk_slot_order():
    csv_text = export_lineups_to_csv_string([], NBA_RULES)
    header = next(csv.reader(io.StringIO(csv_text)))
    assert header == ["PG", "SG", "SF", "PF", "C", "G", "F", "UTIL"]


def test_mlb_header_matches_dk_slot_order():
    csv_text = export_lineups_to_csv_string([], MLB_RULES)
    header = next(csv.reader(io.StringIO(csv_text)))
    assert header == ["P", "P", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF"]


def test_row_cells_use_name_and_id_format():
    slate = small_nfl_slate()
    lineup = _lineup_from_slate(
        slate, ["qb1", "rb1", "rb2", "wr1", "wr2", "wr3", "te1", "rb3", "dst1"]
    )
    csv_text = export_lineups_to_csv_string([lineup], NFL_RULES)
    rows = list(csv.reader(io.StringIO(csv_text)))
    assert len(rows) == 2  # header + one lineup
    data_row = rows[1]
    assert len(data_row) == len(NFL_RULES.slots)
    assert data_row[0] == "QB One (qb1)"
    assert data_row[8] == "Bills DST (dst1)"


def test_multiple_lineups_produce_one_row_each_in_order():
    slate = small_nfl_slate()
    lineup_a = _lineup_from_slate(
        slate, ["qb1", "rb1", "rb2", "wr1", "wr2", "wr3", "te1", "rb3", "dst1"]
    )
    lineup_b = _lineup_from_slate(
        slate, ["qb2", "rb3", "rb4", "wr3", "wr4", "wr5", "te2", "te1", "dst2"]
    )
    csv_text = export_lineups_to_csv_string([lineup_a, lineup_b], NFL_RULES)
    rows = list(csv.reader(io.StringIO(csv_text)))
    assert len(rows) == 3
    assert rows[1][0] == "QB One (qb1)"
    assert rows[2][0] == "QB Two (qb2)"
