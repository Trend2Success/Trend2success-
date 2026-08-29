from __future__ import annotations

from dk_ev.data.interfaces import SalaryRow
from dk_ev.data.stub_sources import NaiveOwnershipSource, StubProjectionSource, TeamOdds


def _row(name, salary, avg_pts, player_id=None):
    return SalaryRow(
        player_id=player_id or name,
        name=name,
        positions=("WR",),
        salary=salary,
        team="AAA",
        opponent="BBB",
        avg_points_per_game=avg_pts,
    )


def test_reported_zero_average_is_not_inflated_to_salary_heuristic():
    """A real DK export reports 0.0 for deep bench players who have never
    scored — that must stay a near-zero projection, not get bumped up to
    salary/1000 as if the column were missing entirely.
    """
    rows = [_row("Bench Guy", 4500, 0.0)]
    projections = StubProjectionSource().load(rows)
    proj = projections["bench guy"]
    assert proj.projected_points < 1.0  # clamped to the 0.5 floor, not 4.5


def test_missing_average_column_falls_back_to_salary_heuristic():
    rows = [_row("Mystery Guy", 4500, None)]
    projections = StubProjectionSource().load(rows)
    proj = projections["mystery guy"]
    assert proj.projected_points == 4.5  # salary / 1000 fallback


def test_zero_average_players_get_near_zero_ownership_not_uniform_weight():
    """Regression: before the fix, hundreds of 0.0-average bench players
    all received identical inflated ownership weight, diluting the real
    stars in the simulated field.
    """
    rows = [
        _row("Star", 9000, 25.0, player_id="star"),
        *[_row(f"Bench {i}", 4000, 0.0, player_id=f"bench{i}") for i in range(20)],
    ]
    projections = StubProjectionSource().load(rows)
    ownership = NaiveOwnershipSource().load(rows, projections)

    star_own = ownership["star"]
    bench_own = ownership["bench 0"]
    # pre-fix, every bench player got ~equal weight to the star (all valued
    # at 1.0 via the salary/1000 fallback); post-fix the star dominates.
    assert star_own == 95.0  # hits the ownership cap
    assert bench_own < 25.0


def test_team_odds_scale_projection_when_available():
    rows = [_row("Odds Guy", 6000, 10.0)]
    projections = StubProjectionSource(
        team_odds={"AAA": TeamOdds(implied_team_total=44.0, game_total=70.0)}
    ).load(rows)
    proj = projections["odds guy"]
    assert proj.projected_points == 20.0  # 10.0 * (44/22)
