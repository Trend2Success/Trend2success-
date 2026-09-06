"""
Pydantic v2 request/response models for the SlateEdge optimizer-service.

This service is an independent, personal-use decision-support tool. Nothing
here is affiliated with DraftKings or any other DFS operator, and every
projection/score produced downstream is an ESTIMATE, never a guarantee of
real-world results.
"""
from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Position = Literal["QB", "RB", "WR", "TE", "DST"]
GroupType = Literal["at_least", "at_most", "exactly", "if_then", "exclude_together"]
Distribution = Literal["truncated_normal", "lognormal"]

DEFAULT_ROSTER_SLOTS = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST"]
DEFAULT_FLEX_POSITIONS = ["RB", "WR", "TE"]


# ---------------------------------------------------------------------------
# /optimize models
# ---------------------------------------------------------------------------
class PlayerIn(BaseModel):
    player_id: str
    name: str
    team: str
    opponent: str
    position: Position
    salary: int = Field(ge=0)
    projection: float = 0.0
    ceiling: Optional[float] = None
    floor: Optional[float] = None
    ownership: Optional[float] = 0.0
    leverage: Optional[float] = 0.0
    game_id: str
    locked: bool = False
    excluded: bool = False


class GroupRule(BaseModel):
    type: GroupType
    player_ids: List[str] = Field(default_factory=list)
    count: Optional[int] = None
    if_player_id: Optional[str] = None
    then_player_id: Optional[str] = None


class ObjectiveWeights(BaseModel):
    projection: float = 1.0
    ceiling: float = 0.0
    leverage: float = 0.0
    ownership_penalty: float = 0.0


class StackRules(BaseModel):
    qb_stack_min: int = 0
    qb_stack_max: int = 3
    bring_back_min: int = 0
    allow_rb_with_qb: bool = True
    allow_dst_vs_offense: bool = False


class OptimizeRequest(BaseModel):
    players: List[PlayerIn]
    roster_slots: List[str] = Field(default_factory=lambda: list(DEFAULT_ROSTER_SLOTS))
    flex_positions: List[str] = Field(default_factory=lambda: list(DEFAULT_FLEX_POSITIONS))
    salary_cap: int = 50000
    num_lineups: int = 1
    min_salary: int = 0
    max_salary: Optional[int] = None
    min_unique_players: int = 1
    max_exposure: Dict[str, float] = Field(default_factory=dict)
    min_exposure: Dict[str, float] = Field(default_factory=dict)
    global_max_ownership: Optional[float] = None
    min_total_projection: Optional[float] = None
    min_total_ceiling: Optional[float] = None
    max_players_per_team: Optional[int] = None
    min_players_per_game: Optional[int] = None
    max_players_per_game: Optional[int] = None
    locked_player_ids: List[str] = Field(default_factory=list)
    excluded_player_ids: List[str] = Field(default_factory=list)
    groups: List[GroupRule] = Field(default_factory=list)
    objective_weights: ObjectiveWeights = Field(default_factory=ObjectiveWeights)
    stack_rules: StackRules = Field(default_factory=StackRules)
    random_seed: Optional[int] = None
    reproducible: bool = False


class LineupResult(BaseModel):
    lineup_id: str
    players: List[str]
    roster: Dict[str, str]
    salary_used: int
    total_projection: float
    total_ceiling: float
    total_ownership: float
    leverage_score: float
    model_score: float
    stack_summary: str


class OptimizeResponse(BaseModel):
    lineups: List[LineupResult]
    warnings: List[str] = Field(default_factory=list)
    settings_version: str = "1.0"
    seed_used: Optional[int] = None


# ---------------------------------------------------------------------------
# /simulate models
# ---------------------------------------------------------------------------
class SimPlayer(BaseModel):
    player_id: str
    name: str
    position: Position
    team: str
    game_id: str
    mean: float
    stdev: float = Field(ge=0.0)


class CorrelationPair(BaseModel):
    player_id_a: str
    player_id_b: str
    rho: float = Field(ge=-1.0, le=1.0)


class DefaultCorrelationRules(BaseModel):
    qb_own_pass_catcher: float = 0.6
    same_game_offense: float = 0.15
    dst_vs_opp_offense: float = -0.2


class SimLineup(BaseModel):
    lineup_id: str
    player_ids: List[str]
    ownership_sum: Optional[float] = 0.0


class SimulateRequest(BaseModel):
    players: List[SimPlayer]
    distribution: Distribution = "truncated_normal"
    num_simulations: int = 10000
    correlations: List[CorrelationPair] = Field(default_factory=list)
    default_correlation_rules: DefaultCorrelationRules = Field(
        default_factory=DefaultCorrelationRules
    )
    lineups: List[SimLineup] = Field(default_factory=list)
    threshold: Optional[float] = None
    random_seed: Optional[int] = None


class PlayerStat(BaseModel):
    player_id: str
    mean: float
    median: float
    p75: float
    p90: float
    prob_exceeds_threshold: Optional[float] = None


class LineupStat(BaseModel):
    lineup_id: str
    mean: float
    median: float
    p75: float
    p90: float
    duplication_risk_proxy: float


class SimulateResponse(BaseModel):
    player_stats: List[PlayerStat]
    lineup_stats: List[LineupStat]
    num_simulations: int
    distribution: Distribution
    seed_used: Optional[int] = None
