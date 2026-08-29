from dfs_ev.salary.models import FormatType, Site
from dfs_ev.salary.parser import parse_dk_csv

from .conftest import SAMPLE_DK_CSV


def test_showdown_detects_format_and_cap():
    contest = parse_dk_csv(SAMPLE_DK_CSV).contest
    assert contest.format_type == FormatType.SHOWDOWN
    assert contest.site == Site.DK
    assert contest.salary_cap == 50_000
    assert contest.roster_size == 6
    assert len(contest.players) == 24


def test_showdown_roster_slots_are_cpt_plus_five_flex():
    contest = parse_dk_csv(SAMPLE_DK_CSV).contest
    slots = {s.name: s.count for s in contest.roster_slots}
    assert slots == {"CPT": 1, "FLEX": 5}


def test_showdown_cpt_salary_and_points_multiplier_is_1_5x():
    contest = parse_dk_csv(SAMPLE_DK_CSV).contest
    by_name: dict[str, list] = {}
    for p in contest.players:
        by_name.setdefault(p.dk_name, []).append(p)

    for name, rows in by_name.items():
        assert len(rows) == 2
        cpt = next(r for r in rows if r.is_captain)
        flex = next(r for r in rows if not r.is_captain)
        assert cpt.captain_multiplier == 1.5
        assert flex.captain_multiplier == 1.0
        # DK's real Showdown export bakes the 1.5x into the CPT row's salary already.
        assert cpt.salary == round(flex.salary * 1.5)


def test_showdown_cpt_flex_rows_share_base_player_key():
    contest = parse_dk_csv(SAMPLE_DK_CSV).contest
    whitfield_rows = [p for p in contest.players if p.dk_name == "Marcus Whitfield"]
    assert len(whitfield_rows) == 2
    assert whitfield_rows[0].base_player_key == whitfield_rows[1].base_player_key
    assert whitfield_rows[0].position == "QB"
    assert whitfield_rows[1].position == "QB"


def test_showdown_true_position_independent_of_roster_slot():
    contest = parse_dk_csv(SAMPLE_DK_CSV).contest
    coleman = next(p for p in contest.players if p.dk_name == "Trey Coleman" and not p.is_captain)
    assert coleman.position == "RB"
    assert coleman.eligible_positions == frozenset({"FLEX"})


def test_classic_explicit_slot_template_is_ground_truth(classic_csv):
    contest = parse_dk_csv(classic_csv).contest
    assert contest.format_type == FormatType.CLASSIC
    assert contest.roster_size == 8
    slots = {s.name: (s.count, s.eligible_positions) for s in contest.roster_slots}
    assert slots["QB"] == (1, frozenset({"QB"}))
    assert slots["RB"] == (2, frozenset({"RB"}))
    assert slots["WR"] == (3, frozenset({"WR"}))
    assert slots["FLEX"] == (1, frozenset({"FLEX"}))
    assert slots["S-FLEX"] == (1, frozenset({"S-FLEX"}))


def test_classic_flex_eligibility_does_not_leak_across_slots(classic_csv):
    """A WR carrying 'WR/FLEX/S-FLEX' must not become QB-eligible just
    because some QB also carries the S-FLEX token (regression test)."""
    contest = parse_dk_csv(classic_csv).contest
    qb_slot = next(s for s in contest.roster_slots if s.name == "QB")
    wr_player = next(p for p in contest.players if "WR" in p.eligible_positions)
    assert not (wr_player.eligible_positions & qb_slot.eligible_positions)
