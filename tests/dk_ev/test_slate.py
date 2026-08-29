from __future__ import annotations

from dk_ev.data.interfaces import ProjectionRow, SalaryRow
from dk_ev.slate import build_slate


class _FixedSalarySource:
    def __init__(self, rows):
        self.rows = rows

    def load(self):
        return self.rows


class _FixedProjectionSource:
    def load(self, salaries):
        return {
            "active guy": ProjectionRow("Active Guy", 20.0, 30.0, 10.0, 5.0),
            "hurt guy": ProjectionRow("Hurt Guy", 25.0, 35.0, 15.0, 5.0),
            "questionable guy": ProjectionRow("Questionable Guy", 18.0, 28.0, 8.0, 5.0),
        }


class _ZeroOwnershipSource:
    def load(self, salaries, projections):
        return {}


def _rows():
    return [
        SalaryRow("1", "Active Guy", ("WR",), 5000, "AAA", "BBB", 15.0, injury_status=""),
        SalaryRow("2", "Hurt Guy", ("WR",), 6000, "AAA", "BBB", 18.0, injury_status="OUT"),
        SalaryRow("3", "Questionable Guy", ("WR",), 5500, "AAA", "BBB", 14.0, injury_status="Q"),
    ]


def test_build_slate_excludes_out_players_by_default():
    players = build_slate(_FixedSalarySource(_rows()), _FixedProjectionSource(), _ZeroOwnershipSource())
    names = {p.name for p in players}
    assert "Hurt Guy" not in names
    assert "Active Guy" in names
    assert "Questionable Guy" in names  # Q is not excluded


def test_build_slate_can_keep_inactive_players_if_requested():
    players = build_slate(
        _FixedSalarySource(_rows()),
        _FixedProjectionSource(),
        _ZeroOwnershipSource(),
        exclude_inactive=False,
    )
    names = {p.name for p in players}
    assert "Hurt Guy" in names
