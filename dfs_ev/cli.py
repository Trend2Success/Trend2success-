"""dfs_ev CLI: slate pull, import, match, optimize, simulate, export, backtest."""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import sys
import uuid

from dfs_ev.config import get_settings
from dfs_ev.db import Run, get_session
from dfs_ev.export.dk_export import export_dk_csv
from dfs_ev.opticodds.client import OpticOddsClient
from dfs_ev.optimizer.mip import Lineup, LineupPlayer, OptimizerConfig, optimize_lineups
from dfs_ev.pipeline import apply_injuries, build_game_environments, derive_all_projections, match_slate
from dfs_ev.portfolio.generator import PortfolioConfig, generate_portfolio
from dfs_ev.projections.derive import PlayerProjection, ownership_proxy
from dfs_ev.salary.models import ContestFormat
from dfs_ev.salary.parser import parse_dk_csv, parse_fd_csv
from dfs_ev.scoring.ncaaf_dk import StatLine, score_stat_line
from dfs_ev.simulator.contest import ContestPreset, GameEnvironment, simulate_contest
from dfs_ev.slate import Slate, load_live_slate, load_offline_slate
from dfs_ev.util import base_position

DEFAULT_SAMPLE_SLATE = "data/sample_opticodds/ncaaf_week1_sample.json"


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _parse_contest_csv(path: str, site: str) -> ContestFormat:
    result = parse_dk_csv(path) if site == "dk" else parse_fd_csv(path)
    return result.contest


def _load_slate(args: argparse.Namespace) -> Slate:
    if getattr(args, "live", False):
        settings = get_settings()
        settings.require_api_key()

        async def _run() -> Slate:
            async with OpticOddsClient(settings=settings) as client:
                return await load_live_slate(client, league=args.sport, fixture_id=getattr(args, "fixture", None))

        return asyncio.run(_run())
    path = getattr(args, "slate_json", None) or DEFAULT_SAMPLE_SLATE
    return load_offline_slate(path)


def _load_user_projections(path: str | None) -> dict[str, float]:
    if not path:
        return {}
    import csv as _csv
    from dfs_ev.matching.matcher import normalize_name

    out: dict[str, float] = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in _csv.DictReader(fh):
            name = row.get("name") or row.get("player_name") or row.get("dk_name")
            proj = row.get("projection") or row.get("fpts")
            if name and proj:
                out[normalize_name(name)] = float(proj)
    return out


def _serialize_lineup(lineup: Lineup) -> dict:
    return {
        "players": [
            {"player_id": lp.player.player_id, "dk_name": lp.player.dk_name, "team": lp.player.team,
             "slot_name": lp.slot_name, "salary": lp.player.salary, "projection": lp.projection}
            for lp in lineup.players
        ],
        "total_salary": lineup.total_salary,
        "total_projection": lineup.total_projection,
    }


def _deserialize_lineup(data: dict, contest: ContestFormat) -> Lineup:
    players_by_id = {p.player_id: p for p in contest.players}
    lineup_players = [
        LineupPlayer(player=players_by_id[pl["player_id"]], slot_name=pl["slot_name"], projection=pl["projection"])
        for pl in data["players"]
        if pl["player_id"] in players_by_id
    ]
    return Lineup(players=lineup_players, total_salary=data["total_salary"], total_projection=data["total_projection"])


def _serialize_projection(p: PlayerProjection) -> dict:
    return {
        "projection": p.projection, "std_dev": p.std_dev, "floor": p.floor, "ceiling": p.ceiling,
        "source": p.source, "notes": p.notes, "matched_markets": p.matched_markets,
    }


def _deserialize_projection(key: str, d: dict) -> PlayerProjection:
    return PlayerProjection(
        player_key=key, projection=d["projection"], std_dev=d["std_dev"], floor=d["floor"], ceiling=d["ceiling"],
        source=d.get("source", ""), notes=d.get("notes", ""), matched_markets=d.get("matched_markets", []),
    )


def _serialize_env(e: GameEnvironment) -> dict:
    return {
        "fixture_id": e.fixture_id, "team": e.team, "opponent": e.opponent,
        "implied_team_total": e.implied_team_total, "spread": e.spread, "is_fcs_mismatch": e.is_fcs_mismatch,
    }


def _deserialize_env(d: dict) -> GameEnvironment:
    return GameEnvironment(**d)


def _new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def _save_run(kind: str, config: dict, result: dict) -> str:
    run_id = _new_run_id()
    session = get_session()
    try:
        session.add(Run(id=run_id, kind=kind, created_at=dt.datetime.utcnow(), config_json=config, result_json=result))
        session.commit()
    finally:
        session.close()
    return run_id


def _load_run(run_id: str) -> Run:
    session = get_session()
    try:
        run = session.get(Run, run_id)
        if run is None:
            raise SystemExit(f"No such run: {run_id}")
        return run
    finally:
        session.close()


# ---- commands ----

def cmd_slate_pull(args: argparse.Namespace) -> None:
    slate = _load_slate(args)
    _log(f"Pulled slate: {len(slate.fixtures)} fixtures, {len(slate.players)} players, "
         f"{len(slate.player_props)} prop rows, {len(slate.game_odds)} game-odds rows, "
         f"{len(slate.injuries)} injury rows.")
    for fx in slate.fixtures:
        print(f"{fx.fixture_id}\t{fx.away_team} @ {fx.home_team}\t{fx.start_date}")


def cmd_import(args: argparse.Namespace) -> None:
    contest = _parse_contest_csv(args.csv, args.site)
    print(f"format={contest.format_type.value} site={contest.site.value} cap={contest.salary_cap} "
          f"players={len(contest.players)} roster_size={contest.roster_size}")
    for slot in contest.roster_slots:
        print(f"  slot {slot.name} x{slot.count} eligible={sorted(slot.eligible_positions)}")


def cmd_match(args: argparse.Namespace) -> None:
    contest = _parse_contest_csv(args.csv, args.site)
    slate = _load_slate(args)
    results = match_slate(contest, slate, aliases_path=args.aliases)

    review = [r for r in results.values() if r.needs_review]
    print(f"Matched {len(results) - len(review)}/{len(results)} players with high confidence.")
    if review:
        print("\nNeeds review:")
        for r in sorted(review, key=lambda r: r.confidence):
            print(f"  {r.dk_name} ({r.dk_team}) -> {r.oo_name or '???'} [{r.method}] confidence={r.confidence}")


def cmd_optimize(args: argparse.Namespace) -> None:
    contest = _parse_contest_csv(args.csv, args.site)
    slate = _load_slate(args)
    match_results = match_slate(contest, slate, aliases_path=args.aliases)
    game_envs = build_game_environments(slate)
    user_projections = _load_user_projections(args.projections)
    projections, warnings = derive_all_projections(contest, slate, match_results, game_envs, user_projections)

    auto_bans, injury_notices = apply_injuries(contest, projections, slate.injuries)
    for n in injury_notices:
        _log(f"[injury] {n}")
    for w in warnings:
        _log(f"[projection] {w}")

    bans = set(args.ban.split(",")) if args.ban else set()
    bans |= auto_bans
    locks = set()
    if args.lock:
        wanted = {n.strip().lower() for n in args.lock.split(",")}
        locks = {p.player_id for p in contest.players if p.dk_name.strip().lower() in wanted}

    ban_ids = {p.player_id for p in contest.players if p.player_id in bans or p.dk_name in bans}

    qb_bonus = 2.5 if args.stack == "qb-wr" else 0.0
    opt_config = OptimizerConfig(locks=frozenset(locks), bans=frozenset(ban_ids), qb_stack_bonus=qb_bonus)

    if args.portfolio:
        lineups = generate_portfolio(
            contest, projections, PortfolioConfig(entries=args.lineups, max_exposure=args.max_exposure),
            optimizer_config=opt_config,
        )
    else:
        lineups = optimize_lineups(contest, projections, top_k=args.lineups, config=opt_config)

    if not lineups:
        raise SystemExit("Optimizer found no feasible lineups; check salary cap / roster slot eligibility.")

    salaries = {p.base_player_key: p.salary for p in contest.players}
    positions = {p.base_player_key: base_position(p) for p in contest.players}
    ownership = ownership_proxy(projections, salaries, positions)

    config = {
        "csv_path": args.csv, "site": args.site, "sport": args.sport, "stack": args.stack,
        "lineups": args.lineups, "portfolio": args.portfolio,
    }
    result = {
        "lineups": [_serialize_lineup(lu) for lu in lineups],
        "projections": {k: _serialize_projection(v) for k, v in projections.items()},
        "game_environments": {k: _serialize_env(v) for k, v in game_envs.items()},
        "ownership": ownership,
        "warnings": warnings,
    }
    run_id = _save_run("optimize", config, result)

    print(f"run_id={run_id}")
    for i, lu in enumerate(lineups):
        names = ", ".join(f"{lp.slot_name}:{lp.player.dk_name}" for lp in lu.players)
        print(f"[{i}] salary={lu.total_salary} proj={lu.total_projection}  {names}")


def cmd_simulate(args: argparse.Namespace) -> None:
    run = _load_run(args.run)
    if run.kind != "optimize":
        raise SystemExit(f"Run {args.run} is a '{run.kind}' run, expected 'optimize'.")
    cfg = run.config_json
    contest = _parse_contest_csv(cfg["csv_path"], cfg["site"])
    lineups = [_deserialize_lineup(d, contest) for d in run.result_json["lineups"]]
    projections = {k: _deserialize_projection(k, v) for k, v in run.result_json["projections"].items()}
    game_envs = {k: _deserialize_env(v) for k, v in run.result_json["game_environments"].items()}
    ownership = run.result_json.get("ownership", {})

    preset = ContestPreset(args.preset)
    results = simulate_contest(
        lineups, contest, projections, game_envs, ownership=ownership, preset=preset,
        contest_size=args.contest_size, entry_fee=args.entry_fee, n_iterations=args.iterations,
    )

    sim_config = {
        "optimize_run_id": args.run, "preset": args.preset, "contest_size": args.contest_size,
        "entry_fee": args.entry_fee, "iterations": args.iterations,
    }
    sim_result = {"results": [vars(r) for r in results]}
    sim_run_id = _save_run("simulate", sim_config, sim_result)

    print(f"sim_run_id={sim_run_id}")
    print(f"{'lineup':<10}{'ev':>10}{'roi':>10}{'itm%':>8}{'p10':>10}{'p90':>10}{'top1%':>8}{'top10%':>8}")
    for r in sorted(results, key=lambda r: r.ev, reverse=True):
        print(f"{r.lineup_label:<10}{r.ev:>10.2f}{r.roi:>10.2%}{r.itm_pct:>8.1%}"
              f"{r.floor_p10:>10.1f}{r.ceiling_p90:>10.1f}{r.top1_pct:>8.1%}{r.top10_pct:>8.1%}")


def cmd_export(args: argparse.Namespace) -> None:
    run = _load_run(args.run)
    if run.kind != "optimize":
        raise SystemExit(f"Run {args.run} is a '{run.kind}' run, expected 'optimize'.")
    cfg = run.config_json
    contest = _parse_contest_csv(cfg["csv_path"], args.site or cfg["site"])
    lineups = [_deserialize_lineup(d, contest) for d in run.result_json["lineups"]]
    out_path = args.out or f"export_{args.run}.csv"
    export_dk_csv(lineups, contest, out_path)
    print(f"Exported {len(lineups)} lineups to {out_path}")


def cmd_backtest(args: argparse.Namespace) -> None:
    settings = get_settings()

    async def _run() -> tuple[dict, dict]:
        async with OpticOddsClient(settings=settings) as client:
            results = await client.fixtures_results(league=args.sport, start_date=args.date_from, end_date=args.date_to)
            player_results = await client.fixtures_player_results(
                league=args.sport, start_date=args.date_from, end_date=args.date_to
            )
            return results, player_results

    if not settings.opticodds_api_key:
        raise SystemExit(
            "backtest requires OPTICODDS_API_KEY (grading needs live /fixtures/results + "
            "/fixtures/player-results; also needs saved DK salary CSVs for the graded slates -- "
            "OpticOdds results do not include historical DK salaries/contest pools)."
        )
    results, player_results = asyncio.run(_run())

    for row in player_results.get("data", []):
        stats = StatLine(
            pass_yards=row.get("passing_yards", 0), pass_tds=row.get("passing_touchdowns", 0),
            interceptions=row.get("interceptions", 0), rush_yards=row.get("rushing_yards", 0),
            rush_tds=row.get("rushing_touchdowns", 0), receptions=row.get("receptions", 0),
            rec_yards=row.get("receiving_yards", 0), rec_tds=row.get("receiving_touchdowns", 0),
            fumbles_lost=row.get("fumbles_lost", 0), two_pt_conversions=row.get("two_point_conversions", 0),
        )
        pts = score_stat_line(stats)
        print(f"{row.get('player_name', row.get('player_id'))}\t{pts}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dfs_ev", description="NCAAF DFS EV Optimizer")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_slate_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--live", action="store_true", help="pull from the live OpticOdds API instead of the offline sample")
        sp.add_argument("--slate-json", default=None, help="path to an offline slate JSON (default: bundled sample)")
        sp.add_argument("--fixture", default=None, help="restrict to one fixture_id (live mode)")

    p_slate = sub.add_parser("slate", help="slate operations")
    slate_sub = p_slate.add_subparsers(dest="slate_command", required=True)
    p_slate_pull = slate_sub.add_parser("pull", help="fetch + cache the NCAAF slate")
    p_slate_pull.add_argument("--league", dest="sport", default="ncaaf")
    add_slate_args(p_slate_pull)
    p_slate_pull.set_defaults(func=cmd_slate_pull)

    p_import = sub.add_parser("import", help="parse a DK/FD contest CSV")
    p_import.add_argument("--csv", required=True)
    p_import.add_argument("--site", choices=["dk", "fd"], default="dk")
    p_import.set_defaults(func=cmd_import)

    p_match = sub.add_parser("match", help="name-match CSV players against the OpticOdds slate")
    p_match.add_argument("--csv", required=True)
    p_match.add_argument("--site", choices=["dk", "fd"], default="dk")
    p_match.add_argument("--aliases", default=None)
    p_match.add_argument("--sport", default="ncaaf")
    add_slate_args(p_match)
    p_match.set_defaults(func=cmd_match)

    p_opt = sub.add_parser("optimize", help="build optimized lineup(s)")
    p_opt.add_argument("--sport", default="ncaaf")
    p_opt.add_argument("--site", choices=["dk", "fd"], default="dk")
    p_opt.add_argument("--contest", choices=["classic", "showdown"], default=None,
                        help="informational only; format is detected from the CSV")
    p_opt.add_argument("--csv", required=True)
    p_opt.add_argument("--lineups", type=int, default=1)
    p_opt.add_argument("--stack", choices=["none", "qb-wr"], default="none")
    p_opt.add_argument("--aliases", default=None)
    p_opt.add_argument("--projections", default=None, help="user projection CSV override (columns: name,projection)")
    p_opt.add_argument("--lock", default=None, help="comma-separated player names to lock")
    p_opt.add_argument("--ban", default=None, help="comma-separated player names to ban")
    p_opt.add_argument("--portfolio", action="store_true", help="generate a diversified GPP portfolio instead of raw top-K")
    p_opt.add_argument("--max-exposure", type=float, default=0.30)
    add_slate_args(p_opt)
    p_opt.set_defaults(func=cmd_optimize)

    p_sim = sub.add_parser("simulate", help="Monte Carlo simulate an optimize run's lineups")
    p_sim.add_argument("--run", required=True)
    p_sim.add_argument("--iterations", type=int, default=10_000)
    p_sim.add_argument("--preset", choices=[e.value for e in ContestPreset], default=ContestPreset.GPP_LARGE.value)
    p_sim.add_argument("--contest-size", type=int, default=1000)
    p_sim.add_argument("--entry-fee", type=float, default=20.0)
    p_sim.set_defaults(func=cmd_simulate)

    p_export = sub.add_parser("export", help="export an optimize run's lineups to a DK/FD upload CSV")
    p_export.add_argument("--run", required=True)
    p_export.add_argument("--site", choices=["dk", "fd"], default=None)
    p_export.add_argument("--out", default=None)
    p_export.set_defaults(func=cmd_export)

    p_backtest = sub.add_parser("backtest", help="grade past lineups via OpticOdds results")
    p_backtest.add_argument("--from", dest="date_from", required=True)
    p_backtest.add_argument("--to", dest="date_to", required=True)
    p_backtest.add_argument("--sport", default="ncaaf")
    p_backtest.set_defaults(func=cmd_backtest)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
