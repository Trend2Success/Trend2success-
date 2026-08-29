"""MIP lineup optimizer (OR-Tools CP-SAT) for DK/FD NCAAF Classic + Showdown.

Roster slots, salary cap, and per-team rules all come from the parsed
`ContestFormat` (Module 2) -- nothing CFB-specific is hard-coded here.
CPT 1.5x is applied to fantasy points inside the optimizer (salary is
taken as-is from the CSV, which for a real DK Showdown export already has
the CPT row's salary pre-multiplied).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from dfs_ev.projections.derive import PlayerProjection, projection_for_player_row
from dfs_ev.salary.models import ContestFormat, FormatType, Player

POINTS_SCALE = 100  # CP-SAT needs integer coefficients; 2-decimal precision
PASS_CATCHER_POSITIONS = {"WR", "TE", "RB"}


@dataclass
class LineupPlayer:
    player: Player
    slot_name: str
    projection: float


@dataclass
class Lineup:
    players: list[LineupPlayer]
    total_salary: int
    total_projection: float

    def player_ids(self) -> frozenset[str]:
        return frozenset(lp.player.player_id for lp in self.players)


@dataclass
class OptimizerConfig:
    locks: frozenset[str] = field(default_factory=frozenset)
    bans: frozenset[str] = field(default_factory=frozenset)
    qb_stack_bonus: float = 0.0  # added to objective (fantasy pts) per selected same-team QB+pass-catcher pair
    min_salary_used: int | None = None
    max_players_per_team_override: int | None = None
    time_limit_seconds: float = 8.0


def _lookup_projection(player: Player, projections: dict[str, PlayerProjection]) -> float:
    proj = projection_for_player_row(player, projections)
    return proj.projection if proj is not None else 0.0


def _expand_slots(contest: ContestFormat) -> list[tuple[int, str, frozenset[str]]]:
    instances: list[tuple[int, str, frozenset[str]]] = []
    idx = 0
    for slot in contest.roster_slots:
        for _ in range(slot.count):
            instances.append((idx, slot.name, slot.eligible_positions))
            idx += 1
    return instances


def _eligible(player: Player, slot_positions: frozenset[str]) -> bool:
    return bool(player.eligible_positions & slot_positions)


def _build_model(
    contest: ContestFormat,
    projections: dict[str, PlayerProjection],
    config: OptimizerConfig,
    forbidden: list[frozenset[str]],
) -> tuple[cp_model.CpModel, dict[str, cp_model.IntVar], dict[tuple[str, int], cp_model.IntVar], list]:
    model = cp_model.CpModel()
    players = [p for p in contest.players if p.player_id not in config.bans]
    slot_instances = _expand_slots(contest)

    x: dict[str, cp_model.IntVar] = {p.player_id: model.NewBoolVar(f"x_{p.player_id}") for p in players}
    y: dict[tuple[str, int], cp_model.IntVar] = {}

    for p in players:
        assigns = []
        for slot_idx, _slot_name, slot_positions in slot_instances:
            if _eligible(p, slot_positions):
                var = model.NewBoolVar(f"y_{p.player_id}_{slot_idx}")
                y[(p.player_id, slot_idx)] = var
                assigns.append(var)
        model.Add(sum(assigns) == x[p.player_id])

    for slot_idx, _slot_name, _slot_positions in slot_instances:
        vars_for_slot = [y[(p.player_id, slot_idx)] for p in players if (p.player_id, slot_idx) in y]
        model.Add(sum(vars_for_slot) == 1)

    # One real person can only occupy one row (matters for Showdown CPT/FLEX dupes).
    by_base: dict[str, list[Player]] = {}
    for p in players:
        by_base.setdefault(p.base_player_key, []).append(p)
    for rows in by_base.values():
        if len(rows) > 1:
            model.Add(sum(x[p.player_id] for p in rows) <= 1)

    # Salary cap
    model.Add(sum(x[p.player_id] * p.salary for p in players) <= contest.salary_cap)
    if config.min_salary_used:
        model.Add(sum(x[p.player_id] * p.salary for p in players) >= config.min_salary_used)

    # Team rules
    teams = contest.players_by_team()
    max_per_team = config.max_players_per_team_override or contest.max_players_per_team
    if contest.format_type == FormatType.SHOWDOWN:
        for team, team_players in teams.items():
            ids = [p.player_id for p in team_players if p.player_id in x]
            if ids:
                model.Add(sum(x[i] for i in ids) >= 1)
    roster_size = contest.roster_size
    for team, team_players in teams.items():
        ids = [p.player_id for p in team_players if p.player_id in x]
        if not ids:
            continue
        cap = max_per_team if max_per_team is not None else roster_size - 1
        model.Add(sum(x[i] for i in ids) <= cap)

    # Locks / bans
    for pid in config.locks:
        if pid in x:
            model.Add(x[pid] == 1)

    # Forbid previously-returned exact rosters (top-K iterative solution-forbidding)
    for prev in forbidden:
        prev_vars = [x[pid] for pid in prev if pid in x]
        if prev_vars:
            model.Add(sum(prev_vars) <= len(prev_vars) - 1)

    # Objective: projected points (+ optional QB/pass-catcher stack bonus)
    objective_terms = []
    for p in players:
        pts = round(_lookup_projection(p, projections) * POINTS_SCALE)
        objective_terms.append(x[p.player_id] * pts)

    if config.qb_stack_bonus:
        bonus_scaled = round(config.qb_stack_bonus * POINTS_SCALE)
        for team, team_players in teams.items():
            qbs = [p for p in team_players if "QB" in p.eligible_positions and p.player_id in x]
            catchers = [
                p for p in team_players if p.eligible_positions & PASS_CATCHER_POSITIONS and p.player_id in x
            ]
            for qb in qbs:
                for wr in catchers:
                    if qb.player_id == wr.player_id:
                        continue
                    z = model.NewBoolVar(f"stack_{qb.player_id}_{wr.player_id}")
                    model.Add(z <= x[qb.player_id])
                    model.Add(z <= x[wr.player_id])
                    model.Add(z >= x[qb.player_id] + x[wr.player_id] - 1)
                    objective_terms.append(z * bonus_scaled)

    model.Maximize(sum(objective_terms))
    return model, x, y, slot_instances


def _solve_one(
    contest: ContestFormat,
    projections: dict[str, PlayerProjection],
    config: OptimizerConfig,
    forbidden: list[frozenset[str]],
) -> Lineup | None:
    model, x, y, slot_instances = _build_model(contest, projections, config, forbidden)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.time_limit_seconds
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    players_by_id = {p.player_id: p for p in contest.players}
    lineup_players: list[LineupPlayer] = []
    for (pid, slot_idx), var in y.items():
        if solver.Value(var):
            slot_name = slot_instances[slot_idx][1]
            player = players_by_id[pid]
            proj = _lookup_projection(player, projections)
            lineup_players.append(LineupPlayer(player=player, slot_name=slot_name, projection=proj))

    total_salary = sum(lp.player.salary for lp in lineup_players)
    total_projection = sum(lp.projection for lp in lineup_players)
    return Lineup(players=lineup_players, total_salary=total_salary, total_projection=round(total_projection, 2))


def optimize_lineups(
    contest: ContestFormat,
    projections: dict[str, PlayerProjection],
    top_k: int = 20,
    config: OptimizerConfig | None = None,
) -> list[Lineup]:
    """Generate up to `top_k` near-optimal, distinct lineups via iterative
    solution-forbidding, to seed the contest simulator's candidate pool.
    """
    cfg = config or OptimizerConfig()
    lineups: list[Lineup] = []
    forbidden: list[frozenset[str]] = []
    attempts = 0
    max_attempts = top_k * 3 + 5
    while len(lineups) < top_k and attempts < max_attempts:
        attempts += 1
        lineup = _solve_one(contest, projections, cfg, forbidden)
        if lineup is None:
            break
        lineups.append(lineup)
        forbidden.append(lineup.player_ids())
    return lineups
