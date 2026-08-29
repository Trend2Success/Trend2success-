from __future__ import annotations

from pathlib import Path

from dk_ev.cli import main

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data"


def test_cli_optimize_runs_end_to_end(capsys, tmp_path):
    export_path = tmp_path / "export.csv"
    exit_code = main(
        [
            "optimize",
            "--sport",
            "nfl",
            "--contest",
            "gpp",
            "--lineups",
            "3",
            "--iterations",
            "500",
            "--field-sample-size",
            "50",
            "--seed",
            "1",
            "--salaries",
            str(SAMPLE_DIR / "nfl_salaries.csv"),
            "--projections",
            str(SAMPLE_DIR / "nfl_projections.csv"),
            "--export-csv",
            str(export_path),
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Generated 3 lineup(s)" in out
    assert export_path.exists()
    lines = export_path.read_text().strip().splitlines()
    assert lines[0] == "QB,RB,RB,WR,WR,WR,TE,FLEX,DST"
    assert len(lines) == 4  # header + 3 lineups
