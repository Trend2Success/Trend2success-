"""Optional local FastAPI service exposing /optimize over HTTP, for
callers that would rather POST a request than shell out to the CLI. Runs
the exact same pipeline as `dfs_ev optimize` (offline sample slate by
default). Start with: uvicorn dfs_ev.api:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dfs_ev.cli import DEFAULT_SAMPLE_SLATE
from dfs_ev.optimizer.mip import OptimizerConfig, optimize_lineups
from dfs_ev.pipeline import apply_injuries, build_game_environments, derive_all_projections, match_slate
from dfs_ev.salary.parser import parse_dk_csv, parse_fd_csv
from dfs_ev.slate import load_offline_slate

app = FastAPI(title="dfs_ev NCAAF DFS EV Optimizer", version="0.1.0")


class OptimizeRequest(BaseModel):
    csv_path: str
    site: str = "dk"
    slate_json: str = DEFAULT_SAMPLE_SLATE
    lineups: int = 1
    qb_stack_bonus: float = 0.0
    aliases_path: str | None = None


class LineupPlayerOut(BaseModel):
    player_id: str
    dk_name: str
    team: str
    slot_name: str
    salary: int
    projection: float


class LineupOut(BaseModel):
    players: list[LineupPlayerOut]
    total_salary: int
    total_projection: float


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/optimize", response_model=list[LineupOut])
def optimize(req: OptimizeRequest) -> list[LineupOut]:
    try:
        contest = (parse_dk_csv if req.site == "dk" else parse_fd_csv)(req.csv_path).contest
        slate = load_offline_slate(req.slate_json)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    match_results = match_slate(contest, slate, aliases_path=req.aliases_path)
    game_envs = build_game_environments(slate)
    projections, _warnings = derive_all_projections(contest, slate, match_results, game_envs)
    bans, _notices = apply_injuries(contest, projections, slate.injuries)

    config = OptimizerConfig(bans=frozenset(bans), qb_stack_bonus=req.qb_stack_bonus)
    lineups = optimize_lineups(contest, projections, top_k=req.lineups, config=config)
    if not lineups:
        raise HTTPException(status_code=422, detail="No feasible lineup found for the given salary cap/roster rules.")

    return [
        LineupOut(
            players=[
                LineupPlayerOut(
                    player_id=lp.player.player_id, dk_name=lp.player.dk_name, team=lp.player.team,
                    slot_name=lp.slot_name, salary=lp.player.salary, projection=lp.projection,
                )
                for lp in lu.players
            ],
            total_salary=lu.total_salary,
            total_projection=lu.total_projection,
        )
        for lu in lineups
    ]
