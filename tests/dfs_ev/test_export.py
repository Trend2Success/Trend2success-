import csv

from dfs_ev.export.dk_export import export_dk_csv
from dfs_ev.optimizer.mip import optimize_lineups
from dfs_ev.projections.derive import PlayerProjection
from dfs_ev.salary.parser import parse_dk_csv

from .conftest import SAMPLE_DK_CSV


def test_export_showdown_header_matches_roster_template(tmp_path):
    contest = parse_dk_csv(SAMPLE_DK_CSV).contest
    projs = {}
    for p in contest.players:
        if p.base_player_key not in projs:
            projs[p.base_player_key] = PlayerProjection(
                player_key=p.base_player_key, projection=p.salary / 200.0, std_dev=2, floor=1, ceiling=20,
                source="test",
            )
    lineups = optimize_lineups(contest, projs, top_k=2)
    out_path = tmp_path / "export.csv"
    export_dk_csv(lineups, contest, str(out_path))

    with out_path.open(newline="") as fh:
        rows = list(csv.reader(fh))

    assert rows[0] == ["CPT", "FLEX", "FLEX", "FLEX", "FLEX", "FLEX"]
    assert len(rows) == 1 + len(lineups)


def test_export_rows_contain_name_and_id_and_no_empty_cells(tmp_path):
    contest = parse_dk_csv(SAMPLE_DK_CSV).contest
    projs = {}
    for p in contest.players:
        if p.base_player_key not in projs:
            projs[p.base_player_key] = PlayerProjection(
                player_key=p.base_player_key, projection=p.salary / 200.0, std_dev=2, floor=1, ceiling=20,
                source="test",
            )
    lineups = optimize_lineups(contest, projs, top_k=1)
    out_path = tmp_path / "export.csv"
    export_dk_csv(lineups, contest, str(out_path))

    with out_path.open(newline="") as fh:
        rows = list(csv.reader(fh))
    data_row = rows[1]
    assert len(data_row) == 6
    assert all(cell for cell in data_row)
    for cell in data_row:
        assert "(" in cell and cell.endswith(")")


def test_export_classic_header_matches_roster_slots(tmp_path, classic_csv):
    contest = parse_dk_csv(classic_csv).contest
    projs = {}
    for p in contest.players:
        if p.base_player_key not in projs:
            projs[p.base_player_key] = PlayerProjection(
                player_key=p.base_player_key, projection=p.salary / 400.0, std_dev=2, floor=1, ceiling=20,
                source="test",
            )
    lineups = optimize_lineups(contest, projs, top_k=1)
    out_path = tmp_path / "classic_export.csv"
    export_dk_csv(lineups, contest, str(out_path))

    with out_path.open(newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["QB", "RB", "RB", "WR", "WR", "WR", "FLEX", "S-FLEX"]
