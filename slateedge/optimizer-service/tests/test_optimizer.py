"""
Unit tests for app/optimizer.py using a small synthetic (fictional) player
pool. No real player names, teams, or data are used anywhere in this file.
"""
from __future__ import annotations

from typing import Dict, List

import pytest

from app.models import OptimizeRequest
from app.optimizer import generate_lineups

ROSTER_SLOTS = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST"]
FLEX_POSITIONS = ["RB", "WR", "TE"]
ROSTER_SIZE = len(ROSTER_SLOTS)


def _player(pid, name, team, opponent, position, salary, projection,
            ceiling=None, floor=None, ownership=10.0, leverage=0.0,
            game_id=None, locked=False, excluded=False):
    return {
        "player_id": pid,
        "name": name,
        "team": team,
        "opponent": opponent,
        "position": position,
        "salary": salary,
        "projection": projection,
        "ceiling": ceiling if ceiling is not None else projection * 1.5,
        "floor": floor if floor is not None else projection * 0.5,
        "ownership": ownership,
        "leverage": leverage,
        "game_id": game_id or f"{team}_vs_{opponent}",
        "locked": locked,
        "excluded": excluded,
    }


def build_pool() -> List[dict]:
    """Fictional two-game slate: team A vs team B (game G1), team C vs team D
    (game G2). Salaries/projections are made up purely for test purposes."""
    g1 = "G1"
    g2 = "G2"
    players = [
        # QBs
        _player("QB_A", "Fic QB A", "A", "B", "QB", 7500, 22.0, game_id=g1),
        _player("QB_B", "Fic QB B", "B", "A", "QB", 7200, 20.0, game_id=g1),
        _player("QB_C", "Fic QB C", "C", "D", "QB", 6800, 19.0, game_id=g2),
        # RBs (team A)
        _player("RB_A1", "Fic RB A1", "A", "B", "RB", 8000, 18.0, game_id=g1),
        _player("RB_A2", "Fic RB A2", "A", "B", "RB", 5200, 11.0, game_id=g1),
        # RBs (team B)
        _player("RB_B1", "Fic RB B1", "B", "A", "RB", 7600, 17.0, game_id=g1),
        _player("RB_B2", "Fic RB B2", "B", "A", "RB", 4800, 9.5, game_id=g1),
        # RBs (team C / D)
        _player("RB_C1", "Fic RB C1", "C", "D", "RB", 6600, 15.0, game_id=g2),
        _player("RB_D1", "Fic RB D1", "D", "C", "RB", 4200, 8.0, game_id=g2),
        # WRs (team A)
        _player("WR_A1", "Fic WR A1", "A", "B", "WR", 7800, 17.5, game_id=g1),
        _player("WR_A2", "Fic WR A2", "A", "B", "WR", 6200, 13.0, game_id=g1),
        _player("WR_A3", "Fic WR A3", "A", "B", "WR", 4400, 8.5, game_id=g1),
        # WRs (team B)
        _player("WR_B1", "Fic WR B1", "B", "A", "WR", 7200, 16.0, game_id=g1),
        _player("WR_B2", "Fic WR B2", "B", "A", "WR", 5000, 10.5, game_id=g1),
        # WRs (team C / D)
        _player("WR_C1", "Fic WR C1", "C", "D", "WR", 6000, 12.5, game_id=g2),
        _player("WR_C2", "Fic WR C2", "C", "D", "WR", 4000, 7.5, game_id=g2),
        _player("WR_D1", "Fic WR D1", "D", "C", "WR", 3800, 7.0, game_id=g2),
        # TEs
        _player("TE_A", "Fic TE A", "A", "B", "TE", 4600, 9.5, game_id=g1),
        _player("TE_B", "Fic TE B", "B", "A", "TE", 3600, 7.5, game_id=g1),
        _player("TE_C", "Fic TE C", "C", "D", "TE", 3200, 6.0, game_id=g2),
        _player("TE_D", "Fic TE D", "D", "C", "TE", 2800, 5.0, game_id=g2),
        # DSTs
        _player("DST_A", "Fic DST A", "A", "B", "DST", 3000, 8.0, game_id=g1),
        _player("DST_B", "Fic DST B", "B", "A", "DST", 2800, 7.5, game_id=g1),
        _player("DST_C", "Fic DST C", "C", "D", "DST", 2600, 7.0, game_id=g2),
        _player("DST_D", "Fic DST D", "D", "C", "DST", 2400, 6.5, game_id=g2),
    ]
    return players


def base_request(**overrides) -> dict:
    req = {
        "players": build_pool(),
        "roster_slots": ROSTER_SLOTS,
        "flex_positions": FLEX_POSITIONS,
        "salary_cap": 50000,
        "num_lineups": 1,
    }
    req.update(overrides)
    return req


def pool_by_id(players: List[dict]) -> Dict[str, dict]:
    return {p["player_id"]: p for p in players}


# ---------------------------------------------------------------------------
# Salary cap
# ---------------------------------------------------------------------------
def test_salary_cap_enforced():
    req = OptimizeRequest.model_validate(base_request(num_lineups=5, salary_cap=45000))
    resp = generate_lineups(req)
    assert len(resp.lineups) > 0
    for lu in resp.lineups:
        assert lu.salary_used <= 45000


def test_min_and_max_salary_window():
    req = OptimizeRequest.model_validate(
        base_request(num_lineups=1, salary_cap=50000, min_salary=48000, max_salary=50000)
    )
    resp = generate_lineups(req)
    assert len(resp.lineups) == 1
    assert 48000 <= resp.lineups[0].salary_used <= 50000


# ---------------------------------------------------------------------------
# Roster / position eligibility, no duplicates
# ---------------------------------------------------------------------------
def test_roster_eligibility_and_no_duplicates():
    pool = pool_by_id(build_pool())
    req = OptimizeRequest.model_validate(base_request(num_lineups=3))
    resp = generate_lineups(req)
    assert len(resp.lineups) == 3
    for lu in resp.lineups:
        # exactly roster-size unique players
        assert len(lu.players) == ROSTER_SIZE
        assert len(set(lu.players)) == ROSTER_SIZE
        assert len(lu.roster) == ROSTER_SIZE

        for slot_name, pid in lu.roster.items():
            position = pool[pid]["position"]
            base_slot = "".join(ch for ch in slot_name if not ch.isdigit())
            if base_slot == "FLEX":
                assert position in FLEX_POSITIONS
            else:
                assert position == base_slot

        # QB slot count == 1, RB dedicated count >=2, etc.
        positions_used = [pool[pid]["position"] for pid in lu.players]
        assert positions_used.count("QB") == 1
        assert positions_used.count("DST") == 1
        assert positions_used.count("RB") >= 2
        assert positions_used.count("WR") >= 3
        assert positions_used.count("TE") >= 1


# ---------------------------------------------------------------------------
# Locked / excluded
# ---------------------------------------------------------------------------
def test_locked_and_excluded_players_honored():
    req = OptimizeRequest.model_validate(
        base_request(
            num_lineups=4,
            locked_player_ids=["RB_A1"],
            excluded_player_ids=["QB_A"],
        )
    )
    resp = generate_lineups(req)
    assert len(resp.lineups) == 4
    for lu in resp.lineups:
        assert "RB_A1" in lu.players
        assert "QB_A" not in lu.players


# ---------------------------------------------------------------------------
# Exposure (max + min, best-effort)
# ---------------------------------------------------------------------------
def test_max_exposure_cap_respected():
    num_lineups = 10
    req = OptimizeRequest.model_validate(
        base_request(
            num_lineups=num_lineups,
            max_exposure={"RB_A1": 0.3},
            min_unique_players=1,
        )
    )
    resp = generate_lineups(req)
    generated = len(resp.lineups)
    assert generated > 0
    count = sum(1 for lu in resp.lineups if "RB_A1" in lu.players)
    # allowed_so_far is computed against the *requested* num_lineups, so the
    # cap is respected relative to the originally requested count.
    assert count <= max(1, int(0.3 * num_lineups) + 1)


def test_min_exposure_best_effort_increases_usage():
    num_lineups = 8
    # RB_D1 is a weak/cheap player unlikely to be picked on merit alone.
    req_no_floor = OptimizeRequest.model_validate(base_request(num_lineups=num_lineups))
    resp_no_floor = generate_lineups(req_no_floor)
    baseline = sum(1 for lu in resp_no_floor.lineups if "RB_D1" in lu.players)

    req_with_floor = OptimizeRequest.model_validate(
        base_request(num_lineups=num_lineups, min_exposure={"RB_D1": 0.75})
    )
    resp_with_floor = generate_lineups(req_with_floor)
    with_floor = sum(1 for lu in resp_with_floor.lineups if "RB_D1" in lu.players)

    assert with_floor >= baseline
    assert with_floor >= 1


# ---------------------------------------------------------------------------
# Stack rules
# ---------------------------------------------------------------------------
def test_qb_stack_min_max_enforced():
    req = OptimizeRequest.model_validate(
        base_request(
            num_lineups=5,
            stack_rules={
                "qb_stack_min": 1,
                "qb_stack_max": 2,
                "bring_back_min": 0,
                "allow_rb_with_qb": True,
                "allow_dst_vs_offense": True,
            },
        )
    )
    resp = generate_lineups(req)
    pool = pool_by_id(build_pool())
    assert len(resp.lineups) > 0
    for lu in resp.lineups:
        qb_ids = [pid for pid in lu.players if pool[pid]["position"] == "QB"]
        assert len(qb_ids) == 1
        qb_team = pool[qb_ids[0]]["team"]
        pass_catchers = sum(
            1
            for pid in lu.players
            if pool[pid]["team"] == qb_team and pool[pid]["position"] in ("WR", "TE")
        )
        assert 1 <= pass_catchers <= 2


def test_bring_back_enforced():
    req = OptimizeRequest.model_validate(
        base_request(
            num_lineups=5,
            stack_rules={
                "qb_stack_min": 0,
                "qb_stack_max": 3,
                "bring_back_min": 1,
                "allow_rb_with_qb": True,
                "allow_dst_vs_offense": True,
            },
        )
    )
    resp = generate_lineups(req)
    pool = pool_by_id(build_pool())
    assert len(resp.lineups) > 0
    for lu in resp.lineups:
        qb_ids = [pid for pid in lu.players if pool[pid]["position"] == "QB"]
        qb = pool[qb_ids[0]]
        opp_team = qb["opponent"]
        bring_back_count = sum(1 for pid in lu.players if pool[pid]["team"] == opp_team)
        assert bring_back_count >= 1


def test_allow_rb_with_qb_false_forbids_same_team_rb():
    req = OptimizeRequest.model_validate(
        base_request(
            num_lineups=6,
            stack_rules={
                "qb_stack_min": 0,
                "qb_stack_max": 3,
                "bring_back_min": 0,
                "allow_rb_with_qb": False,
                "allow_dst_vs_offense": True,
            },
        )
    )
    resp = generate_lineups(req)
    pool = pool_by_id(build_pool())
    assert len(resp.lineups) > 0
    for lu in resp.lineups:
        qb_ids = [pid for pid in lu.players if pool[pid]["position"] == "QB"]
        qb_team = pool[qb_ids[0]]["team"]
        for pid in lu.players:
            if pool[pid]["position"] == "RB":
                assert pool[pid]["team"] != qb_team


def test_allow_dst_vs_offense_false_forbids_dst_facing_own_offense():
    req = OptimizeRequest.model_validate(
        base_request(
            num_lineups=6,
            stack_rules={
                "qb_stack_min": 0,
                "qb_stack_max": 3,
                "bring_back_min": 0,
                "allow_rb_with_qb": True,
                "allow_dst_vs_offense": False,
            },
        )
    )
    resp = generate_lineups(req)
    pool = pool_by_id(build_pool())
    assert len(resp.lineups) > 0
    for lu in resp.lineups:
        dst_ids = [pid for pid in lu.players if pool[pid]["position"] == "DST"]
        assert len(dst_ids) == 1
        dst = pool[dst_ids[0]]
        dst_opp = dst["opponent"]
        for pid in lu.players:
            if pool[pid]["position"] != "DST" and pool[pid]["team"] == dst_opp:
                pytest.fail("Offensive player from DST's opponent found alongside DST")


# ---------------------------------------------------------------------------
# team / game caps
# ---------------------------------------------------------------------------
def test_max_players_per_team():
    req = OptimizeRequest.model_validate(base_request(num_lineups=5, max_players_per_team=3))
    resp = generate_lineups(req)
    pool = pool_by_id(build_pool())
    assert len(resp.lineups) > 0
    for lu in resp.lineups:
        counts: Dict[str, int] = {}
        for pid in lu.players:
            team = pool[pid]["team"]
            counts[team] = counts.get(team, 0) + 1
        assert all(c <= 3 for c in counts.values())


def test_max_players_per_game():
    # Only two games exist in the fictional pool and the roster needs 9
    # total spots, so the cap must allow at least 9 across the two games
    # combined (e.g. 6 here) or the request is infeasible by construction.
    req = OptimizeRequest.model_validate(base_request(num_lineups=5, max_players_per_game=6))
    resp = generate_lineups(req)
    pool = pool_by_id(build_pool())
    assert len(resp.lineups) > 0
    for lu in resp.lineups:
        counts: Dict[str, int] = {}
        for pid in lu.players:
            game = pool[pid]["game_id"]
            counts[game] = counts.get(game, 0) + 1
        assert all(c <= 6 for c in counts.values())


def test_min_players_per_game_when_game_used():
    req = OptimizeRequest.model_validate(base_request(num_lineups=5, min_players_per_game=3))
    resp = generate_lineups(req)
    pool = pool_by_id(build_pool())
    assert len(resp.lineups) > 0
    for lu in resp.lineups:
        counts: Dict[str, int] = {}
        for pid in lu.players:
            game = pool[pid]["game_id"]
            counts[game] = counts.get(game, 0) + 1
        for c in counts.values():
            assert c == 0 or c >= 3


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------
def test_group_at_least():
    req = OptimizeRequest.model_validate(
        base_request(
            num_lineups=3,
            groups=[{"type": "at_least", "player_ids": ["WR_A1", "WR_A2", "WR_A3"], "count": 2}],
        )
    )
    resp = generate_lineups(req)
    assert len(resp.lineups) > 0
    for lu in resp.lineups:
        count = sum(1 for pid in ["WR_A1", "WR_A2", "WR_A3"] if pid in lu.players)
        assert count >= 2


def test_group_at_most():
    req = OptimizeRequest.model_validate(
        base_request(
            num_lineups=3,
            groups=[{"type": "at_most", "player_ids": ["WR_A1", "WR_A2", "WR_A3"], "count": 1}],
        )
    )
    resp = generate_lineups(req)
    assert len(resp.lineups) > 0
    for lu in resp.lineups:
        count = sum(1 for pid in ["WR_A1", "WR_A2", "WR_A3"] if pid in lu.players)
        assert count <= 1


def test_group_exactly():
    req = OptimizeRequest.model_validate(
        base_request(
            num_lineups=1,
            groups=[{"type": "exactly", "player_ids": ["QB_A", "QB_B", "QB_C"], "count": 1}],
        )
    )
    resp = generate_lineups(req)
    assert len(resp.lineups) == 1
    count = sum(1 for pid in ["QB_A", "QB_B", "QB_C"] if pid in resp.lineups[0].players)
    assert count == 1


def test_group_if_then():
    req = OptimizeRequest.model_validate(
        base_request(
            num_lineups=5,
            locked_player_ids=["WR_D1"],
            groups=[
                {
                    "type": "if_then",
                    "if_player_id": "WR_D1",
                    "then_player_id": "TE_D",
                }
            ],
        )
    )
    resp = generate_lineups(req)
    assert len(resp.lineups) > 0
    for lu in resp.lineups:
        if "WR_D1" in lu.players:
            assert "TE_D" in lu.players


def test_group_exclude_together():
    req = OptimizeRequest.model_validate(
        base_request(
            num_lineups=5,
            groups=[
                {
                    "type": "exclude_together",
                    "player_ids": ["QB_A", "QB_B", "QB_C"],
                }
            ],
        )
    )
    resp = generate_lineups(req)
    assert len(resp.lineups) > 0
    for lu in resp.lineups:
        count = sum(1 for pid in ["QB_A", "QB_B", "QB_C"] if pid in lu.players)
        assert count <= 1


# ---------------------------------------------------------------------------
# Infeasibility handling
# ---------------------------------------------------------------------------
def test_infeasible_request_returns_warnings_not_crash():
    # Lock two different QBs -- impossible, only one QB slot exists.
    req = OptimizeRequest.model_validate(
        base_request(num_lineups=3, locked_player_ids=["QB_A", "QB_B"])
    )
    resp = generate_lineups(req)
    assert len(resp.lineups) == 0
    assert len(resp.warnings) > 0


def test_partially_infeasible_returns_some_lineups_and_warnings():
    # Force heavy exposure caps that make it impossible to build all 10
    # unique lineups from such a small locked pool, but early lineups should
    # still succeed.
    req = OptimizeRequest.model_validate(
        base_request(
            num_lineups=10,
            min_unique_players=9,  # every lineup must differ in ALL 9 spots
            max_players_per_team=2,
        )
    )
    resp = generate_lineups(req)
    # Should not crash; likely produces fewer than 10 given a tiny pool with
    # only 4 teams and full-lineup uniqueness required.
    assert isinstance(resp.lineups, list)
    if len(resp.lineups) < 10:
        assert len(resp.warnings) > 0


# ---------------------------------------------------------------------------
# Objective weights sanity
# ---------------------------------------------------------------------------
def test_objective_weights_affect_score():
    req_proj = OptimizeRequest.model_validate(
        base_request(num_lineups=1, objective_weights={"projection": 1.0, "ceiling": 0.0, "leverage": 0.0, "ownership_penalty": 0.0})
    )
    resp_proj = generate_lineups(req_proj)
    assert len(resp_proj.lineups) == 1
    lu = resp_proj.lineups[0]
    assert abs(lu.model_score - lu.total_projection) < 1e-6
