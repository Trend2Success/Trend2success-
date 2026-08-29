import pytest

import dfs_ev.db as db_module

SAMPLE_DK_CSV = "data/sample_dk/ncaaf_showdown.csv"
SAMPLE_SLATE_JSON = "data/sample_opticodds/ncaaf_week1_sample.json"


CLASSIC_ROWS = [
    # name, id, team, opponent_team, roster_position, salary
    ("Ava Quarter", "30001", "AAA", "BBB", "QB/S-FLEX", 8000),
    ("Ben Backup", "30002", "AAA", "BBB", "QB/S-FLEX", 5500),
    ("Cole Runner", "30003", "AAA", "BBB", "RB/FLEX/S-FLEX", 7500),
    ("Drew Dasher", "30004", "AAA", "BBB", "RB/FLEX/S-FLEX", 6200),
    ("Eli Sprint", "30005", "BBB", "AAA", "RB/FLEX/S-FLEX", 5000),
    ("Finn Fly", "30006", "AAA", "BBB", "WR/FLEX/S-FLEX", 7000),
    ("Gus Grab", "30007", "BBB", "AAA", "WR/FLEX/S-FLEX", 6500),
    ("Hank Hands", "30008", "BBB", "AAA", "WR/FLEX/S-FLEX", 4800),
    ("Ike Ivory", "30009", "BBB", "AAA", "WR/FLEX/S-FLEX", 4200),
]


def write_classic_csv(tmp_path) -> str:
    path = tmp_path / "classic.csv"
    lines = ["QB,RB,RB,WR,WR,WR,FLEX,S-FLEX"]
    lines.append("Position,Name + ID,Name,ID,Roster Position,Salary,Game Info,TeamAbbrev,AvgPointsPerGame")
    for name, pid, team, opp, roster_pos, salary in CLASSIC_ROWS:
        base_pos = roster_pos.split("/")[0]
        game_info = f"{opp}@{team} 08/29/2026 07:00PM ET" if team > opp else f"{team}@{opp} 08/29/2026 07:00PM ET"
        lines.append(f"{base_pos},{name} ({pid}),{name},{pid},{roster_pos},{salary},{game_info},{team},15.0")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


@pytest.fixture()
def classic_csv(tmp_path):
    return write_classic_csv(tmp_path)


@pytest.fixture()
def showdown_contest():
    from dfs_ev.salary.parser import parse_dk_csv

    return parse_dk_csv(SAMPLE_DK_CSV).contest


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """Isolated SQLite DB per test (dfs_ev.db caches a module-level engine)."""
    db_path = str(tmp_path / "test_dfs_ev.sqlite3")
    monkeypatch.setenv("DFS_EV_DB_PATH", db_path)
    db_module.reset_engine_for_tests()
    yield db_path
    db_module.reset_engine_for_tests()
