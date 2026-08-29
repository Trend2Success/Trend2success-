"""FastAPI app: POST /optimize, GET /lineups/{run_id}, GET /export/csv/{run_id}."""
from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, sessionmaker

from dk_ev.api.schemas import (
    LineupPlayerSchema,
    LineupResultSchema,
    OptimizeRequestSchema,
    OptimizeResponseSchema,
    RunSummarySchema,
)
from dk_ev.db import init_db, make_engine
from dk_ev.domain import Lineup, Player
from dk_ev.export import export_lineups_to_csv_string
from dk_ev.models import LineupRecord, OptimizationRun
from dk_ev.payouts import cash_5050, sample_gpp
from dk_ev.persistence import get_run, list_runs, save_run
from dk_ev.rules import get_rules
from dk_ev.service import OptimizeRequest, run_optimize

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data"
DEFAULT_SALARIES = SAMPLE_DIR / "nfl_salaries.csv"
DEFAULT_PROJECTIONS = SAMPLE_DIR / "nfl_projections.csv"

app = FastAPI(title="dk_ev DFS Optimizer API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = make_engine()
init_db(engine)
SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Iterator[Session]:
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _write_temp_csv(content: str) -> str:
    fh = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="")
    fh.write(content)
    fh.close()
    return fh.name


def _record_to_schema(record: LineupRecord) -> LineupResultSchema:
    return LineupResultSchema(
        rank=record.rank,
        salary=record.salary,
        projected_points=record.projected_points,
        ownership_sum=record.ownership_sum,
        ev=record.ev,
        ev_net=record.ev_net,
        itm_pct=record.itm_pct,
        win_pct=record.win_pct,
        median_rank=record.median_rank,
        top1_pct_rate=record.top1_pct_rate,
        top10_pct_rate=record.top10_pct_rate,
        ceiling=record.ceiling,
        floor=record.floor,
        roster=[LineupPlayerSchema(**p) for p in record.roster],
    )


def _run_to_response(run: OptimizationRun) -> OptimizeResponseSchema:
    return OptimizeResponseSchema(
        run_id=run.id,
        sport=run.sport,
        contest_type=run.contest_type,
        lineups=[_record_to_schema(lu) for lu in run.lineups],
    )


def _lineup_from_record(record: LineupRecord, rules) -> Lineup:
    """Reconstructs enough of a Lineup for CSV export from stored roster JSON."""
    players = [
        Player(
            player_id=p["player_id"],
            name=p["name"],
            positions=tuple(p["positions"]),
            team=p["team"],
            opponent="",
            salary=p["salary"],
            projected_points=p["projected_points"],
            floor=0.0,
            ceiling=0.0,
            std_dev=0.0,
            ownership_pct=p["ownership_pct"],
        )
        for p in record.roster
    ]
    return Lineup(slots=rules.slots, players=tuple(players))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/optimize", response_model=OptimizeResponseSchema)
def optimize(payload: OptimizeRequestSchema, session: Session = Depends(get_db)) -> OptimizeResponseSchema:
    try:
        get_rules(payload.sport)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    salaries_path = (
        _write_temp_csv(payload.salaries_csv) if payload.salaries_csv else str(DEFAULT_SALARIES)
    )
    projections_path = (
        _write_temp_csv(payload.projections_csv) if payload.projections_csv else None
    )
    ownership_path = _write_temp_csv(payload.ownership_csv) if payload.ownership_csv else None

    payout = (
        cash_5050(payload.field_size, payload.entry_fee)
        if payload.contest_type == "cash"
        else sample_gpp(payload.field_size, payload.entry_fee)
    )

    request = OptimizeRequest(
        sport=payload.sport,
        contest_type=payload.contest_type,
        num_lineups=payload.num_lineups,
        alpha=payload.alpha,
        salaries_path=salaries_path,
        projections_path=projections_path,
        ownership_path=ownership_path,
        payout=payout,
        field_size=payload.field_size,
        entry_fee=payload.entry_fee,
        max_overlap=payload.max_overlap,
        stack_min_size=payload.stack_min_size,
        locked_player_ids=frozenset(payload.locked_player_ids),
        banned_player_ids=frozenset(payload.banned_player_ids),
        no_opposing_dst_vs_qb=payload.no_opposing_dst_vs_qb,
        max_players_per_team=payload.max_players_per_team,
        n_iterations=payload.n_iterations,
        field_sample_size=payload.field_sample_size,
        distribution=payload.distribution,
        random_seed=payload.random_seed,
    )

    try:
        response = run_optimize(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Optimization failed: {exc}") from exc

    if not response.results:
        raise HTTPException(
            status_code=422, detail="No feasible lineups found for the given constraints"
        )

    config = payload.model_dump(exclude={"salaries_csv", "projections_csv", "ownership_csv"})
    run = save_run(
        session,
        sport=payload.sport,
        contest_type=payload.contest_type,
        num_lineups_requested=payload.num_lineups,
        config=config,
        results=response.results,
    )
    session.flush()
    return _run_to_response(run)


@app.get("/lineups/{run_id}", response_model=OptimizeResponseSchema)
def get_lineups(run_id: int, session: Session = Depends(get_db)) -> OptimizeResponseSchema:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return _run_to_response(run)


@app.get("/runs", response_model=list[RunSummarySchema])
def get_runs(session: Session = Depends(get_db)) -> list[RunSummarySchema]:
    runs = list_runs(session)
    return [
        RunSummarySchema(
            run_id=r.id,
            sport=r.sport,
            contest_type=r.contest_type,
            created_at=r.created_at.isoformat(),
            num_lineups=len(r.lineups),
        )
        for r in runs
    ]


@app.get("/export/csv/{run_id}")
def export_csv(run_id: int, session: Session = Depends(get_db)) -> PlainTextResponse:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    rules = get_rules(run.sport)
    lineups = [_lineup_from_record(lu, rules) for lu in run.lineups]
    csv_text = export_lineups_to_csv_string(lineups, rules)
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=dk_upload_run_{run_id}.csv"},
    )
