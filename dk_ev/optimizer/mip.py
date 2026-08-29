"""Mixed-integer lineup optimizer built on OR-Tools CP-SAT.

Maximizes projected points (optionally blended with a small leverage term
for GPP tie-breaking) subject to DK's slot, salary-cap, and per-team
constraints. ``top_k`` produces near-optimal lineups by iteratively
forbidding each previously found player set and re-solving.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ortools.sat.python import cp_model

from dk_ev.domain import Lineup, Player
from dk_ev.rules import SportRules

POINTS_SCALE = 100


class InfeasibleLineupError(RuntimeError):
    """Raised when no legal lineup satisfies the given constraints."""


@dataclass
class OptimizerConstraints:
    locked_player_ids: frozenset[str] = field(default_factory=frozenset)
    banned_player_ids: frozenset[str] = field(default_factory=frozenset)
    no_opposing_dst_vs_qb: bool = False
    max_players_per_team: int | None = None
    max_from_team: dict[str, int] = field(default_factory=dict)
    min_salary: int = 0
    # Stacking: if a QB (stack_qb_position) is rostered, require at least
    # stack_min_size teammates from stack_positions in the same lineup.
    stack_min_size: int = 0
    stack_positions: tuple[str, ...] = ("WR", "TE")
    stack_qb_position: str = "QB"


class LineupOptimizer:
    """Solves the DK lineup MIP for one slate under one sport's rules."""

    def __init__(self, players: list[Player], rules: SportRules):
        self.players = players
        self.rules = rules
        self._by_id = {p.player_id: p for p in players}

    def _build_model(
        self,
        constraints: OptimizerConstraints,
        overlap_limits: list[tuple[frozenset[str], int]],
        leverage_weight: float,
        score_fn: Callable[[Player], float] | None = None,
    ):
        model = cp_model.CpModel()
        slots = self.rules.slots
        candidates = [p for p in self.players if p.player_id not in constraints.banned_player_ids]

        x: dict[tuple[str, int], cp_model.IntVar] = {}
        eligible_players_per_slot: list[list[Player]] = []
        for s_idx, slot in enumerate(slots):
            eligible = [
                p for p in candidates if self.rules.player_eligible_for_slot(p.positions, slot)
            ]
            if not eligible:
                raise InfeasibleLineupError(f"No eligible players for slot {slot!r}")
            eligible_players_per_slot.append(eligible)
            for p in eligible:
                x[(p.player_id, s_idx)] = model.NewBoolVar(f"x_{p.player_id}_{s_idx}")

        for s_idx, elig in enumerate(eligible_players_per_slot):
            model.Add(sum(x[(p.player_id, s_idx)] for p in elig) == 1)

        player_selected: dict[str, cp_model.IntVar] = {}
        for p in candidates:
            slot_vars = [
                x[(p.player_id, s_idx)] for s_idx in range(len(slots)) if (p.player_id, s_idx) in x
            ]
            if not slot_vars:
                continue
            sel = model.NewBoolVar(f"sel_{p.player_id}")
            model.Add(sum(slot_vars) == sel)
            player_selected[p.player_id] = sel

        salary_expr = sum(
            self._by_id[pid].salary * var for pid, var in player_selected.items()
        )
        model.Add(salary_expr <= self.rules.salary_cap)
        if constraints.min_salary:
            model.Add(salary_expr >= constraints.min_salary)

        for pid in constraints.locked_player_ids:
            if pid not in player_selected:
                raise InfeasibleLineupError(
                    f"Locked player {pid!r} is banned or ineligible for every slot"
                )
            model.Add(player_selected[pid] == 1)

        default_team_limit = constraints.max_players_per_team or self.rules.max_players_per_team
        teams: dict[str, list[cp_model.IntVar]] = {}
        for pid, var in player_selected.items():
            teams.setdefault(self._by_id[pid].team, []).append(var)
        for team, team_vars in teams.items():
            limit = constraints.max_from_team.get(team, default_team_limit)
            model.Add(sum(team_vars) <= limit)

        if constraints.no_opposing_dst_vs_qb:
            qbs = [p for p in candidates if "QB" in p.positions and p.player_id in player_selected]
            dsts = [p for p in candidates if "DST" in p.positions and p.player_id in player_selected]
            for qb in qbs:
                for dst in dsts:
                    if dst.team == qb.opponent:
                        model.Add(
                            player_selected[qb.player_id] + player_selected[dst.player_id] <= 1
                        )

        if constraints.stack_min_size > 0:
            qb_by_team: dict[str, list[cp_model.IntVar]] = {}
            stack_by_team: dict[str, list[cp_model.IntVar]] = {}
            for p in candidates:
                if p.player_id not in player_selected:
                    continue
                var = player_selected[p.player_id]
                if constraints.stack_qb_position in p.positions:
                    qb_by_team.setdefault(p.team, []).append(var)
                if any(pos in constraints.stack_positions for pos in p.positions):
                    stack_by_team.setdefault(p.team, []).append(var)
            for team, qb_vars in qb_by_team.items():
                stack_sum = sum(stack_by_team.get(team, []))
                for qb_var in qb_vars:
                    model.Add(stack_sum >= constraints.stack_min_size * qb_var)

        for player_ids, max_overlap in overlap_limits:
            in_model = [player_selected[pid] for pid in player_ids if pid in player_selected]
            if in_model:
                model.Add(sum(in_model) <= max_overlap)

        base_score = score_fn or (lambda p: p.projected_points)
        objective_terms = []
        for pid, var in player_selected.items():
            p = self._by_id[pid]
            score = base_score(p) + leverage_weight * p.leverage_score
            objective_terms.append(round(score * POINTS_SCALE) * var)
        model.Maximize(sum(objective_terms))

        return model, x, eligible_players_per_slot

    def solve(
        self,
        constraints: OptimizerConstraints | None = None,
        forbidden_sets: list[frozenset[str]] | None = None,
        leverage_weight: float = 0.0,
        time_limit_seconds: float = 10.0,
        score_fn: Callable[[Player], float] | None = None,
    ) -> Lineup:
        constraints = constraints or OptimizerConstraints()
        overlap_limits = [(s, len(s) - 1) for s in (forbidden_sets or [])]
        return self.solve_with_overlap_limits(
            constraints, overlap_limits, leverage_weight, time_limit_seconds, score_fn
        )

    def solve_with_overlap_limits(
        self,
        constraints: OptimizerConstraints | None = None,
        overlap_limits: list[tuple[frozenset[str], int]] | None = None,
        leverage_weight: float = 0.0,
        time_limit_seconds: float = 10.0,
        score_fn: Callable[[Player], float] | None = None,
    ) -> Lineup:
        """Like :meth:`solve`, but each ``(player_ids, max_overlap)`` pair
        caps how many of ``player_ids`` may appear together in the result —
        the general form ``solve``'s exact-lineup exclusion is built from.
        """
        constraints = constraints or OptimizerConstraints()
        overlap_limits = overlap_limits or []
        model, x, eligible_players_per_slot = self._build_model(
            constraints, overlap_limits, leverage_weight, score_fn
        )
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        solver.parameters.num_search_workers = 8
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise InfeasibleLineupError("No feasible lineup found under the given constraints")

        chosen: list[Player] = []
        for s_idx, elig in enumerate(eligible_players_per_slot):
            for p in elig:
                var = x.get((p.player_id, s_idx))
                if var is not None and solver.Value(var) == 1:
                    chosen.append(p)
                    break
        return Lineup(slots=self.rules.slots, players=tuple(chosen))

    def top_k(
        self,
        k: int,
        constraints: OptimizerConstraints | None = None,
        leverage_weight: float = 0.0,
        time_limit_seconds: float = 10.0,
        score_fn: Callable[[Player], float] | None = None,
    ) -> list[Lineup]:
        """The k best distinct-lineup solutions, in descending objective order."""
        constraints = constraints or OptimizerConstraints()
        lineups: list[Lineup] = []
        forbidden_sets: list[frozenset[str]] = []
        for _ in range(k):
            try:
                lineup = self.solve(
                    constraints, forbidden_sets, leverage_weight, time_limit_seconds, score_fn
                )
            except InfeasibleLineupError:
                break
            lineups.append(lineup)
            forbidden_sets.append(lineup.player_ids)
        return lineups
