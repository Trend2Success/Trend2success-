"""CLI: python -m dk_ev optimize --sport nfl --contest gpp --lineups 20"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dk_ev.db import init_db, session_scope
from dk_ev.export import export_lineups_to_csv
from dk_ev.payouts import cash_5050, load_payout_structure, sample_gpp
from dk_ev.persistence import save_run
from dk_ev.rules import get_rules
from dk_ev.service import OptimizeRequest, run_optimize

DEFAULT_SALARIES = Path(__file__).resolve().parent.parent / "sample_data" / "nfl_salaries.csv"
DEFAULT_PROJECTIONS = Path(__file__).resolve().parent.parent / "sample_data" / "nfl_projections.csv"


def _parse_id_list(raw: str | None) -> frozenset[str]:
    if not raw:
        return frozenset()
    return frozenset(x.strip() for x in raw.split(",") if x.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m dk_ev")
    sub = parser.add_subparsers(dest="command", required=True)

    opt = sub.add_parser("optimize", help="Generate and rank DK lineups by simulated EV")
    opt.add_argument("--sport", default="nfl", choices=["nfl", "nba", "mlb", "cfb"])
    opt.add_argument("--contest", default="gpp", choices=["cash", "gpp", "balanced"])
    opt.add_argument("--alpha", type=float, default=0.5, help="balanced-mode GPP/cash blend, 0=cash..1=gpp")
    opt.add_argument("--lineups", type=int, default=20)
    opt.add_argument("--top", type=int, default=None, help="only print the top N (default: all generated)")

    opt.add_argument("--salaries", default=str(DEFAULT_SALARIES), help="DK salary export CSV")
    opt.add_argument("--projections", default=None, help="projections CSV (else derived from AvgPointsPerGame)")
    opt.add_argument("--ownership", default=None, help="ownership CSV (else a naive value-based proxy)")

    opt.add_argument("--payout-json", default=None, help="custom payout structure JSON")
    opt.add_argument("--field-size", type=int, default=10_000)
    opt.add_argument("--entry-fee", type=float, default=20.0)

    opt.add_argument("--max-overlap", type=int, default=5, help="max shared players between any two lineups")
    opt.add_argument("--stack", type=int, default=0, help="min pass-catchers stacked with a rostered QB's team")
    opt.add_argument("--lock", default=None, help="comma-separated player IDs to force into every lineup")
    opt.add_argument("--ban", default=None, help="comma-separated player IDs to exclude from every lineup")
    opt.add_argument("--no-opp-dst-qb", action="store_true", help="forbid a QB and the DST facing them together")
    opt.add_argument("--max-per-team", type=int, default=None)

    opt.add_argument("--iterations", type=int, default=10_000, help="Monte Carlo iterations")
    opt.add_argument("--field-sample-size", type=int, default=300)
    opt.add_argument("--distribution", default="normal", choices=["normal", "student_t"])
    opt.add_argument("--seed", type=int, default=None)

    opt.add_argument("--export-csv", default=None, help="write a DK-upload-ready CSV of the ranked lineups")
    opt.add_argument("--db", default=None, help="SQLite URL to persist this run (default: no persistence)")

    return parser


def _print_results(response, top: int | None) -> None:
    results = response.results if top is None else response.results[:top]
    if not results:
        print("No feasible lineups were found for the given constraints.")
        return

    print(
        f"\n{'#':>3} {'EV':>9} {'ITM%':>7} {'Proj':>7} {'Salary':>7} "
        f"{'Own%':>7} {'Ceil':>7} {'Floor':>7}  Roster"
    )
    print("-" * 110)
    for i, result in enumerate(results, start=1):
        lineup = result.lineup
        print(
            f"{i:>3} {result.ev:>9.2f} {result.itm_pct * 100:>6.1f}% "
            f"{lineup.projected_points:>7.1f} {lineup.salary:>7,} "
            f"{lineup.ownership_sum:>6.1f}% {result.ceiling:>7.1f} {result.floor:>7.1f}  "
            f"{lineup.roster_string()}"
        )
    print()


def cmd_optimize(args: argparse.Namespace) -> int:
    if args.sport != "nfl" and args.salaries == str(DEFAULT_SALARIES):
        print(
            f"error: the bundled sample slate is NFL-only; pass --salaries "
            f"(and ideally --projections) for a {args.sport.upper()} slate.",
            file=sys.stderr,
        )
        return 2

    payout = None
    if args.payout_json:
        payout = load_payout_structure(args.payout_json, field_size=args.field_size)
    elif args.contest == "cash":
        payout = cash_5050(field_size=args.field_size, entry_fee=args.entry_fee)
    else:
        payout = sample_gpp(field_size=args.field_size, entry_fee=args.entry_fee)

    request = OptimizeRequest(
        sport=args.sport,
        contest_type=args.contest,
        num_lineups=args.lineups,
        alpha=args.alpha,
        salaries_path=args.salaries,
        projections_path=args.projections,
        ownership_path=args.ownership,
        payout=payout,
        field_size=args.field_size,
        entry_fee=args.entry_fee,
        max_overlap=args.max_overlap,
        stack_min_size=args.stack,
        locked_player_ids=_parse_id_list(args.lock),
        banned_player_ids=_parse_id_list(args.ban),
        no_opposing_dst_vs_qb=args.no_opp_dst_qb,
        max_players_per_team=args.max_per_team,
        n_iterations=args.iterations,
        field_sample_size=args.field_sample_size,
        distribution=args.distribution,
        random_seed=args.seed,
    )

    print(f"Loading slate for {args.sport.upper()} from {request.salaries_path} ...")
    response = run_optimize(request)
    print(f"Generated {len(response.results)} lineup(s); ran {args.iterations:,} MC iterations each.")

    _print_results(response, args.top)

    if args.export_csv:
        rules = get_rules(args.sport)
        lineups = [r.lineup for r in (response.results if args.top is None else response.results[: args.top])]
        export_lineups_to_csv(lineups, rules, args.export_csv)
        print(f"Wrote DK upload CSV -> {args.export_csv}")

    if args.db:
        from dk_ev.db import make_engine
        from sqlalchemy.orm import sessionmaker

        engine = make_engine(args.db)
        init_db(engine)
        factory = sessionmaker(bind=engine)
        with session_scope(factory) as session:
            run = save_run(
                session,
                sport=args.sport,
                contest_type=args.contest,
                num_lineups_requested=args.lineups,
                config=vars(args),
                results=response.results,
            )
            session.flush()
            print(f"Saved run #{run.id} to {args.db}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "optimize":
        return cmd_optimize(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
