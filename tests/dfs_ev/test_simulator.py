import numpy as np

from dfs_ev.optimizer.mip import Lineup, LineupPlayer
from dfs_ev.projections.derive import PlayerProjection
from dfs_ev.salary.parser import parse_dk_csv
from dfs_ev.simulator.contest import ContestPreset, GameEnvironment, simulate_contest
from dfs_ev.simulator.montecarlo import apply_blowout_adjustment, simulate_player_scores

from .conftest import SAMPLE_DK_CSV


def test_blowout_adjustment_reduces_mean_and_inflates_std_for_big_favorite():
    mean, std = apply_blowout_adjustment(20.0, 5.0, spread=30.0, is_fcs_mismatch=False)
    assert mean < 20.0
    assert std > 5.0


def test_blowout_adjustment_inflates_std_for_fcs_mismatch_regardless_of_side():
    _, std_dog = apply_blowout_adjustment(20.0, 5.0, spread=-30.0, is_fcs_mismatch=True)
    _, std_dog_no_mismatch = apply_blowout_adjustment(20.0, 5.0, spread=-30.0, is_fcs_mismatch=False)
    assert std_dog > std_dog_no_mismatch


def test_blowout_adjustment_no_change_for_close_game():
    mean, std = apply_blowout_adjustment(20.0, 5.0, spread=3.0, is_fcs_mismatch=False)
    assert mean == 20.0
    assert std == 5.0


def test_stacked_players_co_move_more_than_cross_team_players():
    # 2 fixtures, 2 teams per fixture, one QB + one WR per team.
    means = np.array([15.0, 12.0, 15.0, 12.0])
    stds = np.array([5.0, 5.0, 5.0, 5.0])
    floors = np.zeros(4)
    ceilings = np.full(4, 100.0)
    team_ids = np.array([0, 0, 1, 1], dtype=np.int64)  # players 0,1 same team; 2,3 same team
    team_fixture_ids = np.array([0, 1], dtype=np.int64)
    stack_rho = np.array([0.4, 0.35, 0.4, 0.35])  # QB, WR, QB, WR

    scores = simulate_player_scores(
        means, stds, floors, ceilings, team_ids, team_fixture_ids, stack_rho,
        n_fixtures=2, n_teams=2, n_iters=20_000, seed=7,
    )
    same_team_corr = np.corrcoef(scores[0], scores[1])[0, 1]
    cross_team_corr = np.corrcoef(scores[0], scores[2])[0, 1]
    assert same_team_corr > cross_team_corr
    assert same_team_corr > 0.15


def test_fat_tail_mode_runs_and_still_correlates():
    means = np.array([15.0, 12.0])
    stds = np.array([5.0, 5.0])
    floors = np.zeros(2)
    ceilings = np.full(2, 100.0)
    team_ids = np.array([0, 0], dtype=np.int64)
    team_fixture_ids = np.array([0], dtype=np.int64)
    stack_rho = np.array([0.4, 0.35])
    scores = simulate_player_scores(
        means, stds, floors, ceilings, team_ids, team_fixture_ids, stack_rho,
        n_fixtures=1, n_teams=1, n_iters=10_000, seed=1, fat_tail=True,
    )
    corr = np.corrcoef(scores[0], scores[1])[0, 1]
    assert corr > 0.1


def test_floor_only_lineup_has_near_zero_itm_in_large_gpp():
    contest = parse_dk_csv(SAMPLE_DK_CSV).contest
    game_envs = {
        "OSU": GameEnvironment("fx1", "OSU", "YSU", 45.5, 38.5, True),
        "YSU": GameEnvironment("fx1", "YSU", "OSU", 7.5, -38.5, True),
    }
    # A deliberately weak, all-cheap-bench-player lineup with tiny variance
    # (floor-only construction) should almost never crack a top-heavy GPP payout.
    players_by_name = {(p.dk_name, p.is_captain): p for p in contest.players}
    extra = next(p for p in contest.players if p.dk_name == "Devin Ortiz" and not p.is_captain)
    lps = [
        LineupPlayer(player=players_by_name[("Devin Ortiz", True)], slot_name="CPT", projection=1.0),
        LineupPlayer(player=extra, slot_name="FLEX", projection=1.0),
        LineupPlayer(player=players_by_name[("Corey Nash", False)], slot_name="FLEX", projection=1.0),
        LineupPlayer(player=players_by_name[("Ryan Whitlock", False)], slot_name="FLEX", projection=1.0),
        LineupPlayer(player=players_by_name[("Dominic Reyes", False)], slot_name="FLEX", projection=1.0),
        LineupPlayer(player=players_by_name[("Nolan Priest", False)], slot_name="FLEX", projection=1.0),
    ]
    weak_lineup = Lineup(players=lps, total_salary=sum(lp.player.salary for lp in lps), total_projection=6.0)

    projections = {}
    for p in contest.players:
        key = p.base_player_key
        if key not in projections:
            floor_val = 2.0
            projections[key] = PlayerProjection(
                player_key=key, projection=floor_val, std_dev=0.3, floor=floor_val - 0.5,
                ceiling=floor_val + 0.5, source="test",
            )
    # Give the field pool realistic upside so it's a legitimately tough GPP field.
    for p in contest.players:
        key = p.base_player_key
        if "Whitfield" in p.dk_name or "Brooks" in p.dk_name or "Foster" in p.dk_name or "Coleman" in p.dk_name:
            projections[key] = PlayerProjection(
                player_key=key, projection=18.0, std_dev=6.0, floor=6.0, ceiling=40.0, source="test",
            )

    results = simulate_contest(
        [weak_lineup], contest, projections, game_envs, preset=ContestPreset.GPP_LARGE,
        contest_size=2000, entry_fee=10, n_iterations=8000, field_sample_size=250, seed=3,
    )
    assert results[0].itm_pct < 0.05


def test_leverage_lineup_beats_chalk_lineup_in_gpp_roi():
    """A high-ownership 'chalk' lineup and a lower-owned 'leverage' lineup
    with the same mean projection: in a top-heavy GPP, the higher-variance
    leverage build should show >= ROI (it needs to separate from a big
    chalky field, which favors ceiling over safety)."""
    contest = parse_dk_csv(SAMPLE_DK_CSV).contest
    game_envs = {
        "OSU": GameEnvironment("fx1", "OSU", "YSU", 45.5, 10.0, False),
        "YSU": GameEnvironment("fx1", "YSU", "OSU", 30.0, -10.0, False),
    }
    projections = {}
    ownership = {}
    for p in contest.players:
        key = p.base_player_key
        if key in projections:
            continue
        projections[key] = PlayerProjection(
            player_key=key, projection=10.0, std_dev=3.0, floor=4.0, ceiling=18.0, source="test"
        )
        ownership[key] = 0.15

    players_by_name = {(p.dk_name, p.is_captain): p for p in contest.players}

    def build(names):
        lps = [LineupPlayer(player=players_by_name[n], slot_name="CPT" if n[1] else "FLEX", projection=10.0) for n in names]
        return Lineup(players=lps, total_salary=sum(lp.player.salary for lp in lps), total_projection=60.0)

    chalk_names = [
        ("Marcus Whitfield", True), ("Trey Coleman", False), ("Isaiah Brooks", False),
        ("Jaylen Foster", False), ("Andre Mackey", False), ("Malik Sweeney", False),
    ]
    leverage_names = [
        ("Ryan Whitlock", True), ("Corey Nash", False), ("Nolan Priest", False),
        ("Devin Ortiz", False), ("Dominic Reyes", False), ("Caleb Sanders", False),
    ]
    chalk_key = players_by_name[("Marcus Whitfield", True)].base_player_key
    lev_key = players_by_name[("Ryan Whitlock", True)].base_player_key
    projections[chalk_key] = PlayerProjection(
        player_key=chalk_key, projection=15.0, std_dev=3.0, floor=9.0, ceiling=21.0, source="test"
    )
    projections[lev_key] = PlayerProjection(
        player_key=lev_key, projection=15.0, std_dev=9.0, floor=0.0, ceiling=42.0, source="test"
    )
    ownership[chalk_key] = 0.45
    ownership[lev_key] = 0.03

    chalk = build(chalk_names)
    leverage = build(leverage_names)

    results = simulate_contest(
        [chalk, leverage], contest, projections, game_envs, ownership=ownership,
        preset=ContestPreset.GPP_LARGE, contest_size=3000, entry_fee=10, n_iterations=10_000,
        field_sample_size=300, seed=11,
    )
    chalk_result, leverage_result = results
    assert leverage_result.ceiling_p90 > chalk_result.ceiling_p90
    assert leverage_result.top1_pct >= chalk_result.top1_pct
