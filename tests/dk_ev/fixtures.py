"""Shared test fixtures: a small synthetic NFL slate."""
from __future__ import annotations

from dk_ev.domain import Player


def make_player(
    player_id: str,
    name: str,
    positions: tuple[str, ...],
    team: str,
    opponent: str,
    salary: int,
    projected_points: float,
    ownership_pct: float = 10.0,
    std_dev: float | None = None,
    floor: float | None = None,
    ceiling: float | None = None,
) -> Player:
    std_dev = std_dev if std_dev is not None else max(projected_points * 0.3, 1.0)
    floor = floor if floor is not None else max(projected_points - std_dev, 0.0)
    ceiling = ceiling if ceiling is not None else projected_points + 2 * std_dev
    return Player(
        player_id=player_id,
        name=name,
        positions=positions,
        team=team,
        opponent=opponent,
        salary=salary,
        projected_points=projected_points,
        floor=floor,
        ceiling=ceiling,
        std_dev=std_dev,
        ownership_pct=ownership_pct,
    )


def small_nfl_slate() -> list[Player]:
    """A minimal but fully feasible NFL slate: exactly enough players per
    slot so the optimizer's constraints (and infeasibility paths) are easy
    to reason about, plus a couple of extra cheap/expensive options.
    """
    players = [
        make_player("qb1", "QB One", ("QB",), "BUF", "MIA", 7800, 24.0),
        make_player("qb2", "QB Two", ("QB",), "MIA", "BUF", 5500, 16.0),
        make_player("rb1", "RB One", ("RB",), "BUF", "MIA", 8200, 22.0),
        make_player("rb2", "RB Two", ("RB",), "MIA", "BUF", 6600, 17.0),
        make_player("rb3", "RB Three", ("RB",), "DAL", "NYG", 4200, 9.0),
        make_player("rb4", "RB Four", ("RB",), "NYG", "DAL", 3800, 7.5),
        make_player("wr1", "WR One", ("WR",), "BUF", "MIA", 8600, 23.0),
        make_player("wr2", "WR Two", ("WR",), "MIA", "BUF", 7200, 18.0),
        make_player("wr3", "WR Three", ("WR",), "DAL", "NYG", 5600, 13.0),
        make_player("wr4", "WR Four", ("WR",), "NYG", "DAL", 4400, 10.0),
        make_player("wr5", "WR Five", ("WR",), "DAL", "NYG", 3000, 6.0),
        make_player("te1", "TE One", ("TE",), "BUF", "MIA", 5200, 12.0),
        make_player("te2", "TE Two", ("TE",), "DAL", "NYG", 2600, 5.0),
        make_player("dst1", "Bills DST", ("DST",), "BUF", "MIA", 3200, 8.0),
        make_player("dst2", "Dolphins DST", ("DST",), "MIA", "BUF", 2400, 6.0),
    ]
    return players


def multi_team_nfl_slate() -> list[Player]:
    """Nine teams, each fielding a QB/RB/WR/TE, so a 1-player-per-team cap
    is still satisfiable across all nine roster slots.
    """
    teams = ["BUF", "MIA", "DAL", "NYG", "SF", "SEA", "KC", "DEN", "LAR"]
    opponents = ["MIA", "BUF", "NYG", "DAL", "SEA", "SF", "DEN", "KC", "LAR"]
    players: list[Player] = []
    for i, (team, opp) in enumerate(zip(teams, opponents)):
        base = 3000 + i * 200
        players.append(make_player(f"{team}_qb", f"{team} QB", ("QB",), team, opp, base + 2000, 18 + i))
        players.append(make_player(f"{team}_rb", f"{team} RB", ("RB",), team, opp, base + 1500, 14 + i))
        players.append(make_player(f"{team}_wr", f"{team} WR", ("WR",), team, opp, base + 1000, 12 + i))
        players.append(make_player(f"{team}_te", f"{team} TE", ("TE",), team, opp, base + 500, 8 + i))
        players.append(make_player(f"{team}_dst", f"{team} DST", ("DST",), team, opp, base, 6 + i))
    return players
