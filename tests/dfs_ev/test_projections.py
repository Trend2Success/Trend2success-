import math

from dfs_ev.projections.derive import (
    build_projection,
    derive_player_projection,
    derive_stat_projection,
    ownership_proxy,
    salary_rank_heuristic_projection,
)
from dfs_ev.projections.odds_math import american_to_implied_prob, no_vig_probability
from dfs_ev.scoring.ncaaf_dk import DK_CFB_CLASSIC_SCORING


def test_american_to_implied_prob_favorite_and_dog():
    assert math.isclose(american_to_implied_prob(-110), 110 / 210, rel_tol=1e-6)
    assert math.isclose(american_to_implied_prob(150), 100 / 250, rel_tol=1e-6)


def test_no_vig_probability_sums_to_one():
    p_over, p_under = no_vig_probability(-115, -105)
    assert math.isclose(p_over + p_under, 1.0, rel_tol=1e-9)
    # -115 is more negative than -105, so the book prices "over" as the
    # (slightly) more likely side.
    assert p_over > p_under


def test_derive_stat_projection_over_favorite_raises_mean_above_line():
    # over_price more negative than a fair -110 => market thinks over is likely
    sp = derive_stat_projection(line=250.0, over_price=-200, under_price=150, line_step=5.0)
    assert sp.mean > 250.0
    assert sp.floor < sp.mean < sp.ceiling


def test_derive_stat_projection_alt_lines_widen_floor_ceiling():
    sp = derive_stat_projection(
        line=100.0, over_price=-110, under_price=-110,
        alt_lines=[(80.0, -180), (120.0, 140)], line_step=5.0,
    )
    assert sp.floor <= 80.0
    assert sp.ceiling >= 120.0


def test_derive_player_projection_sums_markets_and_clamps_std():
    stat_projections = {
        "player_passing_yards": derive_stat_projection(300, -110, -110, line_step=5.0),
        "player_passing_touchdowns": derive_stat_projection(2.5, -110, -110, line_step=0.5),
    }
    proj = derive_player_projection("qb1", stat_projections, DK_CFB_CLASSIC_SCORING)
    assert proj is not None
    assert proj.projection > 0
    assert 0.15 * proj.projection - 0.01 <= proj.std_dev <= 0.45 * proj.projection + 0.01
    assert set(proj.matched_markets) == {"player_passing_yards", "player_passing_touchdowns"}


def test_derive_player_projection_returns_none_when_no_markets_matched():
    assert derive_player_projection("nobody", {}, DK_CFB_CLASSIC_SCORING) is None


def test_fallback_chain_prefers_user_csv_over_everything():
    prop_proj = derive_player_projection(
        "p1", {"player_passing_yards": derive_stat_projection(300, -110, -110, line_step=5.0)}
    )
    fallback = salary_rank_heuristic_projection("p1", "QB", 8000, 10000, 30.0)
    result = build_projection("p1", user_projection=22.5, prop_projection=prop_proj, fallback_projection=fallback)
    assert result.source == "user_csv"
    assert result.projection == 22.5


def test_fallback_chain_uses_prop_when_no_user_csv():
    prop_proj = derive_player_projection(
        "p1", {"player_passing_yards": derive_stat_projection(300, -110, -110, line_step=5.0)}
    )
    result = build_projection("p1", user_projection=None, prop_projection=prop_proj, fallback_projection=None)
    assert result.source == "prop"


def test_fallback_chain_uses_salary_heuristic_when_no_prop():
    fallback = salary_rank_heuristic_projection("p1", "RB", 4000, 10000, 24.0)
    result = build_projection("p1", user_projection=None, prop_projection=None, fallback_projection=fallback)
    assert result.source == "salary_heuristic"
    assert result.projection > 0


def test_fallback_chain_flags_no_projection_as_last_resort():
    result = build_projection("p1")
    assert result.source == "none"
    assert result.projection == 0.0


def test_salary_rank_heuristic_scales_with_salary_strength():
    weak = salary_rank_heuristic_projection("weak", "WR", 3000, 10000, 28.0)
    strong = salary_rank_heuristic_projection("strong", "WR", 9000, 10000, 28.0)
    assert strong.projection > weak.projection


def test_ownership_proxy_ranks_within_position_by_points_per_salary():
    projections = {
        "cheap_stud": type("P", (), {"projection": 20.0})(),
        "expensive_bust": type("P", (), {"projection": 5.0})(),
    }
    salaries = {"cheap_stud": 4000, "expensive_bust": 9000}
    positions = {"cheap_stud": "WR", "expensive_bust": "WR"}
    proxy = ownership_proxy(projections, salaries, positions)
    assert proxy["cheap_stud"] > proxy["expensive_bust"]
