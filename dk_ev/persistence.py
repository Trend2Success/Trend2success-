"""Bridges optimizer/simulator output into the SQLAlchemy persistence layer."""
from __future__ import annotations

from sqlalchemy.orm import Session

from dk_ev.models import LineupRecord, OptimizationRun
from dk_ev.simulation.ev_simulator import SimulationResult


def lineup_roster_json(result: SimulationResult) -> list[dict]:
    lineup = result.lineup
    return [
        {
            "slot": slot,
            "player_id": p.player_id,
            "name": p.name,
            "team": p.team,
            "positions": list(p.positions),
            "salary": p.salary,
            "projected_points": p.projected_points,
            "ownership_pct": p.ownership_pct,
            "leverage_score": p.leverage_score,
        }
        for slot, p in zip(lineup.slots, lineup.players)
    ]


def save_run(
    session: Session,
    sport: str,
    contest_type: str,
    num_lineups_requested: int,
    config: dict,
    results: list[SimulationResult],
) -> OptimizationRun:
    """Persists a run and its lineups, ranked by EV descending."""
    ranked = sorted(results, key=lambda r: r.ev, reverse=True)
    run = OptimizationRun(
        sport=sport,
        contest_type=contest_type,
        num_lineups_requested=num_lineups_requested,
        config=config,
    )
    for rank, result in enumerate(ranked, start=1):
        run.lineups.append(
            LineupRecord(
                rank=rank,
                salary=result.lineup.salary,
                projected_points=result.lineup.projected_points,
                ownership_sum=result.lineup.ownership_sum,
                ev=result.ev,
                ev_net=result.ev_net,
                itm_pct=result.itm_pct,
                win_pct=result.win_pct,
                median_rank=result.median_rank,
                top1_pct_rate=result.top1_pct_rate,
                top10_pct_rate=result.top10_pct_rate,
                ceiling=result.ceiling,
                floor=result.floor,
                roster=lineup_roster_json(result),
            )
        )
    session.add(run)
    session.flush()
    return run


def get_run(session: Session, run_id: int) -> OptimizationRun | None:
    return session.get(OptimizationRun, run_id)


def list_runs(session: Session) -> list[OptimizationRun]:
    return list(session.query(OptimizationRun).order_by(OptimizationRun.created_at.desc()))
