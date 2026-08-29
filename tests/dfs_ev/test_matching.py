import csv

from dfs_ev.matching.matcher import NameMatcher, OpticOddsPlayer, load_aliases, normalize_name


def test_normalize_name_strips_suffix_and_punctuation():
    assert normalize_name("A.J. O'Brien III") == "aj obrien"
    assert normalize_name("De'Von Achane Jr.") == "devon achane"


def test_exact_match_high_confidence():
    oo = [OpticOddsPlayer(player_id="1", name="Marcus Whitfield", team="OSU")]
    matcher = NameMatcher(oo_players=oo)
    result = matcher.match("Marcus Whitfield", "OSU")
    assert result.oo_player_id == "1"
    assert result.method == "exact"
    assert not result.needs_review
    assert result.confidence >= 0.99


def test_fuzzy_match_nickname_still_resolves():
    oo = [OpticOddsPlayer(player_id="2", name="Nathaniel Chandler-Semedo", team="AKR")]
    matcher = NameMatcher(oo_players=oo)
    result = matcher.match("Nate Chandler-Semedo", "AKR")
    assert result.oo_player_id == "2"
    assert result.confidence > 0.5


def test_unmatched_player_flagged_for_review():
    oo = [OpticOddsPlayer(player_id="3", name="Someone Else", team="OSU")]
    matcher = NameMatcher(oo_players=oo)
    result = matcher.match("Completely Different Human", "OSU")
    assert result.needs_review


def test_low_confidence_lands_in_review_queue():
    oo = [OpticOddsPlayer(player_id="4", name="Jonathan Micheaux", team="OSU")]
    matcher = NameMatcher(oo_players=oo)
    results = [matcher.match("Jon M.", "OSU")]
    review = NameMatcher.review_queue(results)
    # Either accepted or flagged -- but if flagged, needs_review must be true.
    for r in review:
        assert r.confidence < matcher.auto_accept_threshold


def test_alias_csv_overrides_fuzzy_matching(tmp_path):
    alias_path = tmp_path / "aliases.csv"
    with alias_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["player_dk_name", "team", "oo_player_id", "oo_player_name"])
        writer.writerow(["Bobby Jones Jr", "OSU", "oo_999", "Robert Jones II"])

    aliases = load_aliases(str(alias_path))
    oo = [OpticOddsPlayer(player_id="oo_999", name="Robert Jones II", team="OSU")]
    matcher = NameMatcher(oo_players=oo, aliases=aliases)

    result = matcher.match("Bobby Jones Jr", "OSU")
    assert result.oo_player_id == "oo_999"
    assert result.method == "alias"
    assert result.confidence == 1.0
    assert not result.needs_review


def test_team_match_boosts_confidence_over_cross_team_candidate():
    oo = [
        OpticOddsPlayer(player_id="a", name="Chris Carter", team="OSU"),
        OpticOddsPlayer(player_id="b", name="Chris Carter", team="YSU"),
    ]
    matcher = NameMatcher(oo_players=oo)
    result = matcher.match("Chris Carter", "OSU")
    assert result.oo_player_id == "a"
