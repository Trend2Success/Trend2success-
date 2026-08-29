from dfs_ev.optimizer.mip import OptimizerConfig, optimize_lineups
from dfs_ev.projections.derive import PlayerProjection
from dfs_ev.salary.parser import parse_dk_csv


def _flat_projections(contest, per_point=200.0):
    projs = {}
    for p in contest.players:
        base = p.base_player_key
        if base not in projs:
            projs[base] = PlayerProjection(
                player_key=base, projection=p.salary / per_point, std_dev=3, floor=1, ceiling=30, source="test"
            )
    return projs


def test_showdown_lineup_is_salary_legal_and_full_roster(showdown_contest):
    projs = _flat_projections(showdown_contest)
    lineups = optimize_lineups(showdown_contest, projs, top_k=1)
    assert len(lineups) == 1
    lu = lineups[0]
    assert lu.total_salary <= showdown_contest.salary_cap
    assert len(lu.players) == 6


def test_showdown_lineup_has_exactly_one_captain(showdown_contest):
    projs = _flat_projections(showdown_contest)
    lineup = optimize_lineups(showdown_contest, projs, top_k=1)[0]
    captains = [lp for lp in lineup.players if lp.player.is_captain]
    assert len(captains) == 1


def test_showdown_cpt_and_flex_of_same_person_are_mutually_exclusive(showdown_contest):
    projs = _flat_projections(showdown_contest)
    lineup = optimize_lineups(showdown_contest, projs, top_k=1)[0]
    base_keys = [lp.player.base_player_key for lp in lineup.players]
    assert len(base_keys) == len(set(base_keys))  # no person appears twice (as both CPT and FLEX)


def test_showdown_includes_at_least_one_player_from_each_team(showdown_contest):
    projs = _flat_projections(showdown_contest)
    lineup = optimize_lineups(showdown_contest, projs, top_k=1)[0]
    teams = {lp.player.team for lp in lineup.players}
    assert teams == {"OSU", "YSU"}


def test_showdown_captain_gets_1_5x_points(showdown_contest):
    # Give every real person the SAME base projection so the optimizer's only
    # incentive is to pick the highest-value captain (1.5x points for 1.5x salary
    # is a good deal only if it doesn't blow the cap -- pin locks/bans to force it).
    base_key = next(p.base_player_key for p in showdown_contest.players if p.dk_name == "Marcus Whitfield")
    projections = {base_key: PlayerProjection(player_key=base_key, projection=20.0, std_dev=2, floor=10, ceiling=30, source="test")}
    for p in showdown_contest.players:
        if p.base_player_key != base_key:
            projections[p.base_player_key] = PlayerProjection(
                player_key=p.base_player_key, projection=1.0, std_dev=1, floor=0, ceiling=2, source="test"
            )
    cpt_row = next(p for p in showdown_contest.players if p.dk_name == "Marcus Whitfield" and p.is_captain)
    lineup = optimize_lineups(
        showdown_contest, projections, top_k=1, config=OptimizerConfig(locks=frozenset({cpt_row.player_id}))
    )[0]
    lp = next(lp for lp in lineup.players if lp.player.player_id == cpt_row.player_id)
    assert lp.projection == 30.0  # 20.0 * 1.5


def test_ban_excludes_player_entirely(showdown_contest):
    projs = _flat_projections(showdown_contest)
    whitfield_ids = {p.player_id for p in showdown_contest.players if p.dk_name == "Marcus Whitfield"}
    lineup = optimize_lineups(
        showdown_contest, projs, top_k=1, config=OptimizerConfig(bans=frozenset(whitfield_ids))
    )[0]
    used_ids = {lp.player.player_id for lp in lineup.players}
    assert not (used_ids & whitfield_ids)


def test_lock_forces_player_into_lineup(showdown_contest):
    projs = _flat_projections(showdown_contest)
    whitlock_flex = next(
        p for p in showdown_contest.players if p.dk_name == "Ryan Whitlock" and not p.is_captain
    )
    lineup = optimize_lineups(
        showdown_contest, projs, top_k=1, config=OptimizerConfig(locks=frozenset({whitlock_flex.player_id}))
    )[0]
    used_ids = {lp.player.player_id for lp in lineup.players}
    assert whitlock_flex.player_id in used_ids


def test_top_k_returns_distinct_lineups(showdown_contest):
    projs = _flat_projections(showdown_contest)
    lineups = optimize_lineups(showdown_contest, projs, top_k=5)
    assert len(lineups) == 5
    seen = set()
    for lu in lineups:
        key = lu.player_ids()
        assert key not in seen
        seen.add(key)


def test_classic_lineup_uses_at_least_two_teams(classic_csv):
    contest = parse_dk_csv(classic_csv).contest
    projs = _flat_projections(contest, per_point=400.0)
    lineup = optimize_lineups(contest, projs, top_k=1)[0]
    teams = {lp.player.team for lp in lineup.players}
    assert len(teams) >= 2


def test_classic_lineup_fills_every_slot(classic_csv):
    contest = parse_dk_csv(classic_csv).contest
    projs = _flat_projections(contest, per_point=400.0)
    lineup = optimize_lineups(contest, projs, top_k=1)[0]
    assert len(lineup.players) == contest.roster_size
    slot_names = sorted(lp.slot_name for lp in lineup.players)
    expected = sorted(s.name for s in contest.roster_slots for _ in range(s.count))
    assert slot_names == expected
