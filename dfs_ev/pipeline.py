"""Glue layer: slate -> name matching -> game environments -> projections.

Shared by the `match`, `optimize`, and `simulate` CLI commands (and the
sample-data integration test) so each only has to worry about its own
input/output, not re-deriving this shared context.
"""
from __future__ import annotations

from dfs_ev.matching.matcher import MatchResult, NameMatcher, OpticOddsPlayer, load_aliases, normalize_name
from dfs_ev.projections.derive import (
    DEFAULT_LINE_STEP,
    PlayerProjection,
    StatProjection,
    build_projection,
    derive_player_projection,
    derive_stat_projection,
    salary_rank_heuristic_projection,
)
from dfs_ev.projections.odds_math import american_to_implied_prob, no_vig_probability
from dfs_ev.salary.models import ContestFormat
from dfs_ev.scoring.ncaaf_dk import DK_CFB_CLASSIC_SCORING, ScoringConfig
from dfs_ev.simulator.contest import GameEnvironment
from dfs_ev.slate import Slate
from dfs_ev.util import base_position


def build_game_environments(slate: Slate) -> dict[str, GameEnvironment]:
    """One GameEnvironment per team abbreviation, from moneyline/spread/total
    odds plus the fixture's FBS-vs-FCS mismatch flag.
    """
    fixture_by_team = {}
    opponent_by_team = {}
    for fx in slate.fixtures:
        fixture_by_team[fx.home_team] = fx
        fixture_by_team[fx.away_team] = fx
        opponent_by_team[fx.home_team] = fx.away_team
        opponent_by_team[fx.away_team] = fx.home_team

    spreads: dict[str, list[float]] = {}
    totals: dict[str, list[float]] = {}
    for row in slate.game_odds:
        team = row.get("team")
        market = row.get("market")
        point = row.get("point")
        if point is None or not team:
            continue
        if market == "point_spread":
            spreads.setdefault(team, []).append(-float(point))
        elif market == "team_total":
            totals.setdefault(team, []).append(float(point))

    envs: dict[str, GameEnvironment] = {}
    for team, fx in fixture_by_team.items():
        spread_vals = spreads.get(team) or [0.0]
        total_vals = totals.get(team) or [24.0]
        envs[team] = GameEnvironment(
            fixture_id=fx.fixture_id,
            team=team,
            opponent=opponent_by_team.get(team, ""),
            implied_team_total=sum(total_vals) / len(total_vals),
            spread=sum(spread_vals) / len(spread_vals),
            is_fcs_mismatch=fx.is_fcs_mismatch,
        )
    return envs


def match_slate(contest: ContestFormat, slate: Slate, aliases_path: str | None = None) -> dict[str, MatchResult]:
    """One MatchResult per distinct real person in the contest (keyed by
    Player.base_player_key, so a Showdown CPT/FLEX pair is matched once).
    """
    oo_players = [OpticOddsPlayer(player_id=p.player_id, name=p.name, team=p.team) for p in slate.players]
    aliases = load_aliases(aliases_path) if aliases_path else {}
    matcher = NameMatcher(oo_players=oo_players, aliases=aliases)

    results: dict[str, MatchResult] = {}
    seen: set[str] = set()
    for p in contest.players:
        if p.base_player_key in seen:
            continue
        seen.add(p.base_player_key)
        results[p.base_player_key] = matcher.match(p.dk_name, p.team)
    return results


def _stat_projection_for_group(market: str, rows: list[dict]) -> StatProjection | None:
    if market == "anytime_touchdown_scorer":
        yes_prices = [r["yes_price"] for r in rows if r.get("yes_price") is not None]
        no_prices = [r["no_price"] for r in rows if r.get("no_price") is not None]
        if not yes_prices:
            return None
        if no_prices:
            p_yes, _ = no_vig_probability(yes_prices[0], no_prices[0])
        else:
            p_yes = american_to_implied_prob(yes_prices[0])
        return StatProjection(market=market, mean=p_yes, std=0.0, floor=0.0, ceiling=1.0)

    lines = [r["line"] for r in rows if r.get("line") is not None]
    if not lines:
        return None
    line = sum(lines) / len(lines)
    over_prices = [r["over_price"] for r in rows if r.get("over_price") is not None]
    under_prices = [r["under_price"] for r in rows if r.get("under_price") is not None]
    over_price = over_prices[0] if over_prices else -110
    under_price = under_prices[0] if under_prices else None
    alt_lines = rows[0].get("alt_lines")
    alt_lines_tuples = [tuple(a) for a in alt_lines] if alt_lines else None
    step = DEFAULT_LINE_STEP.get(market)
    return derive_stat_projection(line, over_price, under_price, alt_lines=alt_lines_tuples, line_step=step)


def derive_all_projections(
    contest: ContestFormat,
    slate: Slate,
    match_results: dict[str, MatchResult],
    game_environments: dict[str, GameEnvironment],
    user_projections: dict[str, float] | None = None,
    scoring: ScoringConfig = DK_CFB_CLASSIC_SCORING,
) -> tuple[dict[str, PlayerProjection], list[str]]:
    """Fallback chain: user CSV -> OpticOdds prop -> salary-rank/team-total
    heuristic -> flagged "no projection". Returns projections keyed by
    Player.base_player_key plus a list of human-readable warnings.
    """
    user_projections = user_projections or {}

    props_by_player: dict[str, list[dict]] = {}
    for row in slate.player_props:
        pid = row.get("player_id")
        if pid:
            props_by_player.setdefault(pid, []).append(row)

    max_salary_by_position: dict[str, int] = {}
    for p in contest.players:
        pos = base_position(p)
        max_salary_by_position[pos] = max(max_salary_by_position.get(pos, 0), p.salary)

    projections: dict[str, PlayerProjection] = {}
    warnings: list[str] = []
    seen: set[str] = set()

    for p in contest.players:
        if p.base_player_key in seen:
            continue
        seen.add(p.base_player_key)

        user_val = user_projections.get(normalize_name(p.dk_name))

        prop_proj = None
        match = match_results.get(p.base_player_key)
        if match and match.oo_player_id:
            grouped: dict[str, list[dict]] = {}
            for row in props_by_player.get(match.oo_player_id, []):
                grouped.setdefault(row["market"], []).append(row)
            stat_projections = {
                market: sp
                for market, rows in grouped.items()
                if (sp := _stat_projection_for_group(market, rows)) is not None
            }
            prop_proj = derive_player_projection(p.base_player_key, stat_projections, scoring)

        fallback_proj = None
        if prop_proj is None and user_val is None:
            env = game_environments.get(p.team)
            pos = base_position(p)
            max_sal = max_salary_by_position.get(pos, p.salary)
            fallback_proj = salary_rank_heuristic_projection(
                p.base_player_key, pos, p.salary, max_sal, env.implied_team_total if env else 24.0
            )
            warnings.append(
                f"{p.dk_name} ({p.team}): no OpticOdds prop matched; used salary-rank/team-total heuristic"
            )

        proj = build_projection(p.base_player_key, user_val, None, prop_proj, fallback_proj)
        if proj.source == "none":
            warnings.append(f"{p.dk_name} ({p.team}): no projection available")
        projections[p.base_player_key] = proj

    return projections, warnings


def apply_injuries(
    contest: ContestFormat,
    projections: dict[str, PlayerProjection],
    injuries: list[dict],
) -> tuple[set[str], list[str]]:
    """OUT players are auto-banned (all rows sharing their base_player_key,
    so both a Showdown CPT and FLEX row are excluded); DTD/Questionable
    players get their std_dev inflated in place as a variance multiplier
    rather than being excluded.
    """
    notices: list[str] = []
    bans: set[str] = set()
    by_norm_name: dict[str, list] = {}
    for p in contest.players:
        by_norm_name.setdefault(normalize_name(p.dk_name), []).append(p)

    for inj in injuries:
        status = (inj.get("status") or "").upper()
        rows = by_norm_name.get(normalize_name(inj.get("player_name", "")))
        if not rows:
            continue
        if status == "OUT":
            for r in rows:
                bans.add(r.player_id)
            notices.append(f"{inj.get('player_name')}: OUT -> auto-banned")
        elif status in {"DTD", "QUESTIONABLE"}:
            base = rows[0].base_player_key
            proj = projections.get(base)
            if proj is not None:
                proj.std_dev = round(proj.std_dev * 1.3, 2)
                proj.ceiling = round(proj.projection + 1.5 * proj.std_dev, 2)
            notices.append(f"{inj.get('player_name')}: {status} -> variance inflated")
    return bans, notices
