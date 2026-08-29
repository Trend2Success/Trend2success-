from __future__ import annotations

from dk_ev.domain import Player
from dk_ev.optimizer.mip import LineupOptimizer
from dk_ev.rules import CFB_RULES, get_rules


def make_player(player_id, name, positions, team, opp, salary, pts):
    return Player(
        player_id=player_id,
        name=name,
        positions=positions,
        team=team,
        opponent=opp,
        salary=salary,
        projected_points=pts,
        floor=max(pts - 5, 0),
        ceiling=pts + 10,
        std_dev=max(pts * 0.3, 1.0),
        ownership_pct=10.0,
    )


def test_get_rules_resolves_cfb():
    assert get_rules("cfb") is CFB_RULES
    assert get_rules("CFB") is CFB_RULES


def test_cfb_roster_has_no_te_or_dst_slots():
    assert "TE" not in CFB_RULES.slots
    assert "DST" not in CFB_RULES.slots
    assert CFB_RULES.slots == ("QB", "RB", "RB", "WR", "WR", "WR", "FLEX", "SFLEX")
    assert CFB_RULES.roster_size == 8
    assert CFB_RULES.salary_cap == 50_000


def test_sflex_accepts_qb_rb_or_wr():
    assert CFB_RULES.player_eligible_for_slot(("QB",), "SFLEX")
    assert CFB_RULES.player_eligible_for_slot(("RB",), "SFLEX")
    assert CFB_RULES.player_eligible_for_slot(("WR",), "SFLEX")


def test_flex_accepts_rb_or_wr_but_not_qb():
    assert CFB_RULES.player_eligible_for_slot(("RB",), "FLEX")
    assert CFB_RULES.player_eligible_for_slot(("WR",), "FLEX")
    assert not CFB_RULES.player_eligible_for_slot(("QB",), "FLEX")


def _small_cfb_slate():
    return [
        make_player("qb1", "QB One", ("QB",), "OSU", "MICH", 8000, 28.0),
        make_player("qb2", "QB Two", ("QB",), "MICH", "OSU", 6500, 22.0),
        make_player("rb1", "RB One", ("RB",), "OSU", "MICH", 7500, 20.0),
        make_player("rb2", "RB Two", ("RB",), "MICH", "OSU", 6000, 16.0),
        make_player("rb3", "RB Three", ("RB",), "OSU", "MICH", 4000, 10.0),
        make_player("wr1", "WR One", ("WR",), "OSU", "MICH", 7800, 22.0),
        make_player("wr2", "WR Two", ("WR",), "MICH", "OSU", 6200, 17.0),
        make_player("wr3", "WR Three", ("WR",), "OSU", "MICH", 4800, 12.0),
        make_player("wr4", "WR Four", ("WR",), "MICH", "OSU", 3200, 8.0),
    ]


def test_optimizer_builds_legal_cfb_lineup():
    optimizer = LineupOptimizer(_small_cfb_slate(), CFB_RULES)
    lineup = optimizer.solve()

    assert lineup.salary <= CFB_RULES.salary_cap
    assert len(lineup.players) == 8
    for slot, player in zip(lineup.slots, lineup.players):
        assert CFB_RULES.player_eligible_for_slot(player.positions, slot)
    assert len({p.player_id for p in lineup.players}) == 8
