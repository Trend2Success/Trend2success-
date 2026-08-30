"""Pydantic request/response schemas for the FastAPI app."""
from __future__ import annotations

from pydantic import BaseModel, Field


class OptimizeRequestSchema(BaseModel):
    sport: str = "nfl"
    contest_type: str = Field(default="gpp", description="cash | gpp | balanced")
    alpha: float = 0.5

    num_lineups: int = 20
    max_overlap: int = 5
    stack_min_size: int = 0

    locked_player_ids: list[str] = []
    banned_player_ids: list[str] = []
    no_opposing_dst_vs_qb: bool = False
    max_players_per_team: int | None = None

    field_size: int = 10_000
    entry_fee: float = 20.0

    n_iterations: int = 10_000
    field_sample_size: int = 300
    distribution: str = "normal"
    random_seed: int | None = None

    # Raw CSV text the caller can supply instead of server-side file paths;
    # any omitted source falls back to the bundled sample data / stubs.
    salaries_csv: str | None = None
    projections_csv: str | None = None
    ownership_csv: str | None = None


class LineupPlayerSchema(BaseModel):
    slot: str
    player_id: str
    name: str
    team: str
    positions: list[str]
    salary: int
    projected_points: float
    ownership_pct: float
    leverage_score: float = 0.0


class LineupResultSchema(BaseModel):
    rank: int
    salary: int
    projected_points: float
    ownership_sum: float
    ev: float
    ev_net: float
    itm_pct: float
    win_pct: float
    median_rank: float
    top1_pct_rate: float
    top10_pct_rate: float
    ceiling: float
    floor: float
    avg_leverage: float
    roster: list[LineupPlayerSchema]


class OptimizeResponseSchema(BaseModel):
    run_id: int
    sport: str
    contest_type: str
    lineups: list[LineupResultSchema]


class RunSummarySchema(BaseModel):
    run_id: int
    sport: str
    contest_type: str
    created_at: str
    num_lineups: int
