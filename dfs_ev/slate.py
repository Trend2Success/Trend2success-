"""Loads a normalized NCAAF slate (fixtures, players, game odds, player
props) from either the bundled offline sample or the live OpticOdds API,
into one internal shape the rest of the pipeline (matching, projections)
is agnostic to.

Offline sample schema (data/sample_opticodds/ncaaf_week1_sample.json) is
this project's own normalized representation -- a self-consistent stand-in
for what /fixtures/active + /fixtures/odds return, since this build
environment has no network path to OpticOdds to capture a real payload.
`_normalize_live_*` best-effort-parses the live v3 JSON (`{"data": [...]}`
envelopes) into the same shape; re-check field names against your account's
actual responses and adjust the `.get(...)` paths below if they differ.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from dfs_ev.opticodds.client import OpticOddsClient


@dataclass
class NormalizedFixture:
    fixture_id: str
    league: str
    start_date: str
    home_team: str
    away_team: str
    is_fcs_mismatch: bool = False


@dataclass
class NormalizedPlayer:
    player_id: str
    name: str
    team: str
    position: str = ""


@dataclass
class Slate:
    fixtures: list[NormalizedFixture] = field(default_factory=list)
    players: list[NormalizedPlayer] = field(default_factory=list)
    game_odds: list[dict] = field(default_factory=list)
    player_props: list[dict] = field(default_factory=list)
    injuries: list[dict] = field(default_factory=list)


def load_offline_slate(path: str) -> Slate:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    fixtures = [
        NormalizedFixture(
            fixture_id=f["id"],
            league=f.get("league", "ncaaf"),
            start_date=f.get("start_date", ""),
            home_team=f["home_team"]["abbreviation"],
            away_team=f["away_team"]["abbreviation"],
            is_fcs_mismatch=f.get("is_fcs_mismatch", False),
        )
        for f in raw.get("fixtures", [])
    ]
    players = [
        NormalizedPlayer(player_id=p["id"], name=p["name"], team=p.get("team", ""), position=p.get("position", ""))
        for p in raw.get("players", [])
    ]
    return Slate(
        fixtures=fixtures,
        players=players,
        game_odds=raw.get("game_odds", []),
        player_props=raw.get("player_props", []),
        injuries=raw.get("injuries", []),
    )


async def load_live_slate(
    client: OpticOddsClient,
    league: str = "ncaaf",
    fixture_id: str | None = None,
    prop_markets: tuple[str, ...] = (
        "player_passing_yards",
        "player_passing_touchdowns",
        "player_rushing_yards",
        "player_receptions",
        "player_receiving_yards",
        "player_touchdowns",
        "anytime_touchdown_scorer",
    ),
    game_markets: tuple[str, ...] = ("moneyline", "point_spread", "total_points", "team_total"),
    sportsbooks: tuple[str, ...] = ("Pinnacle",),
) -> Slate:
    active = await client.fixtures_active(league=league)
    raw_fixtures = active.get("data", [])
    if fixture_id:
        raw_fixtures = [f for f in raw_fixtures if f.get("id") == fixture_id]
    fixtures = [
        NormalizedFixture(
            fixture_id=f.get("id"),
            league=league,
            start_date=f.get("start_date", ""),
            home_team=(f.get("home_team") or {}).get("abbreviation", f.get("home_team_id", "")),
            away_team=(f.get("away_team") or {}).get("abbreviation", f.get("away_team_id", "")),
        )
        for f in raw_fixtures
    ]
    fixture_ids = [f.fixture_id for f in fixtures if f.fixture_id]

    players_raw = await client.players(league=league)
    players = [
        NormalizedPlayer(
            player_id=p.get("id"),
            name=p.get("name", ""),
            team=(p.get("team") or {}).get("abbreviation", p.get("team_id", "")),
            position=p.get("position", ""),
        )
        for p in players_raw.get("data", [])
    ]

    game_odds: list[dict] = []
    for market in game_markets:
        rows = await client.fixtures_odds(market=market, fixture_ids=fixture_ids, sportsbooks=list(sportsbooks))
        game_odds.extend(rows)

    player_props: list[dict] = []
    for market in prop_markets:
        rows = await client.fixtures_odds(market=market, fixture_ids=fixture_ids, sportsbooks=list(sportsbooks))
        player_props.extend(rows)

    injuries_raw = await client.injuries(league=league)
    injuries = [
        {
            "player_name": row.get("player_name") or (row.get("player") or {}).get("name", ""),
            "team": (row.get("team") or {}).get("abbreviation", row.get("team_id", "")),
            "status": row.get("status", ""),
        }
        for row in injuries_raw.get("data", [])
    ]

    return Slate(
        fixtures=fixtures, players=players, game_odds=game_odds, player_props=player_props, injuries=injuries
    )
