"""End-to-end: sample DK CSV + cached OpticOdds sample slate -> match ->
optimize -> simulate -> export, entirely offline (no live API calls)."""
import csv

from dfs_ev.optimizer.mip import OptimizerConfig, optimize_lineups
from dfs_ev.pipeline import apply_injuries, build_game_environments, derive_all_projections, match_slate
from dfs_ev.projections.derive import ownership_proxy
from dfs_ev.salary.parser import parse_dk_csv
from dfs_ev.simulator.contest import ContestPreset, simulate_contest
from dfs_ev.slate import load_offline_slate
from dfs_ev.util import base_position

from .conftest import SAMPLE_DK_CSV, SAMPLE_SLATE_JSON


def test_full_offline_pipeline_runs_end_to_end(tmp_path):
    # import
    contest = parse_dk_csv(SAMPLE_DK_CSV).contest
    assert len(contest.players) == 24

    # match
    slate = load_offline_slate(SAMPLE_SLATE_JSON)
    match_results = match_slate(contest, slate)
    assert all(r.oo_player_id is not None for r in match_results.values())
    assert all(not r.needs_review for r in match_results.values())

    # projections (props + fallback chain both exercised by the sample data)
    game_envs = build_game_environments(slate)
    projections, warnings = derive_all_projections(contest, slate, match_results, game_envs)
    sources = {p.source for p in projections.values()}
    assert "prop" in sources
    assert "salary_heuristic" in sources
    assert all(p.source != "none" for p in projections.values())

    # injuries: auto-ban OUT, inflate variance for DTD
    bans, notices = apply_injuries(contest, projections, slate.injuries)
    assert len(bans) == 2  # Devin Ortiz's CPT + FLEX rows
    assert any("DTD" in n for n in notices)

    # optimize
    config = OptimizerConfig(bans=frozenset(bans), qb_stack_bonus=2.0)
    lineups = optimize_lineups(contest, projections, top_k=3, config=config)
    assert len(lineups) == 3
    for lu in lineups:
        assert lu.total_salary <= contest.salary_cap
        assert not (set(lp.player.player_id for lp in lu.players) & bans)

    # simulate
    salaries = {p.base_player_key: p.salary for p in contest.players}
    positions = {p.base_player_key: base_position(p) for p in contest.players}
    ownership = ownership_proxy(projections, salaries, positions)
    results = simulate_contest(
        lineups, contest, projections, game_envs, ownership=ownership,
        preset=ContestPreset.GPP_LARGE, contest_size=500, entry_fee=10, n_iterations=5000,
        field_sample_size=150, seed=99,
    )
    assert len(results) == 3
    for r in results:
        assert r.ev >= 0
        assert 0.0 <= r.itm_pct <= 1.0
        assert r.floor_p10 <= r.mean_score <= r.ceiling_p90

    # export
    from dfs_ev.export.dk_export import export_dk_csv

    out_path = tmp_path / "lineups.csv"
    export_dk_csv(lineups, contest, str(out_path))
    with out_path.open(newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["CPT", "FLEX", "FLEX", "FLEX", "FLEX", "FLEX"]
    assert len(rows) == 1 + len(lineups)


def test_cli_optimize_simulate_export_round_trip(tmp_path, tmp_db, capsys):
    from dfs_ev.cli import main

    main(["optimize", "--csv", SAMPLE_DK_CSV, "--lineups", "2", "--slate-json", SAMPLE_SLATE_JSON])
    out = capsys.readouterr().out
    run_line = next(line for line in out.splitlines() if line.startswith("run_id="))
    run_id = run_line.split("=", 1)[1]

    main(["simulate", "--run", run_id, "--iterations", "3000"])
    sim_out = capsys.readouterr().out
    assert "sim_run_id=" in sim_out

    export_path = tmp_path / "cli_export.csv"
    main(["export", "--run", run_id, "--out", str(export_path)])
    capsys.readouterr()
    assert export_path.exists()
    with export_path.open(newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["CPT", "FLEX", "FLEX", "FLEX", "FLEX", "FLEX"]
    assert len(rows) == 1 + 2
