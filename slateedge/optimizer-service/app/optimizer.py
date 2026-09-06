"""
PuLP-based DFS lineup optimizer.

This is a standard mixed-integer-linear-programming (MILP) lineup builder —
maximize a weighted objective subject to salary-cap / roster-eligibility /
exposure / stacking constraints. It uses PuLP's bundled CBC solver (pure
Python + a bundled binary that ships with PuLP itself — no external OR-Tools
install required). The technique (binary decision variables + linear
constraints solved with branch-and-cut) is a completely generic operations
-research approach, not derived from or copied out of any commercial product.

All numeric outputs (projections, ceilings, ownership, scores) are estimates
derived from the caller-supplied inputs; nothing here guarantees real-world
DFS results.

------------------------------------------------------------------------
Design notes / documented simplifications
------------------------------------------------------------------------

Roster-slot modeling
    Rather than a full player-to-slot assignment MILP (binary y[player,slot]
    for every slot instance), we model roster construction with per-position
    count constraints:
      - positions that are NOT flex-eligible must match their exact required
        count in roster_slots.
      - positions that ARE flex-eligible must each individually meet their
        dedicated (non-flex) requirement as a lower bound, and the *sum* of
        all flex-eligible positions used must equal the sum of their
        dedicated requirements plus the number of FLEX slots.
    This is equivalent to the full assignment formulation for the standard
    "single FLEX slot shared by a set of positions" shape used by DK-style
    classic slates, is smaller/faster to solve, and always admits a valid
    slot assignment, which we compute deterministically after the solve.

Exposure caps (max_exposure)
    We use the simple, documented approach requested: before generating
    lineup i (0-indexed) we look at each player's current usage count across
    already-generated lineups. If count >= floor(max_exposure * num_lineups),
    the player is hard-excluded from this and all remaining solves. This is
    a conservative (slightly under-fills late exposure in some edge cases)
    but always-correct-by-the-end way to respect the cap without needing a
    backtracking search.

Exposure floors (min_exposure)
    Best-effort only. We track how far behind each player is versus their
    target count. If a player MUST appear in every one of the remaining
    lineups (including this one) to still hit their floor by the end, we
    force-include them (may cause an infeasible solve if that conflicts with
    other constraints -- if so we drop the forced include and fall back to a
    soft nudge). Otherwise we add a small positive bonus to the objective
    proportional to the remaining shortfall, biasing (but not guaranteeing)
    the solver toward using them. This is documented as inexact in the
    README.

Reproducibility
    When `reproducible=True` and a `random_seed` is given, we seed a NumPy
    RNG from (seed, lineup_index) and add a tiny per-player perturbation
    (much smaller than any real scoring difference) to the objective before
    solving. This breaks ties between equally-scored lineups deterministically
    without materially changing the ranking of genuinely different lineups.

Infeasibility handling
    Every single-lineup solve is wrapped: if the solver cannot find a
    feasible/optimal solution, we record a warning and continue to the next
    requested lineup slot (which may become feasible again once exposure-
    forced exclusions/inclusions change). We never raise/500 for
    infeasibility; the response always contains whatever lineups were
    actually found.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pulp

from .models import (
    LineupResult,
    OptimizeRequest,
    OptimizeResponse,
    PlayerIn,
)

BIG_M = 1000  # large enough for any plausible slate size / roster count


@dataclass
class _PoolPlayer:
    player_id: str
    name: str
    team: str
    opponent: str
    position: str
    salary: int
    projection: float
    ceiling: float
    floor: float
    ownership: float
    leverage: float
    game_id: str
    locked: bool
    excluded: bool


def _to_pool(players: List[PlayerIn]) -> Dict[str, _PoolPlayer]:
    pool: Dict[str, _PoolPlayer] = {}
    for p in players:
        pool[p.player_id] = _PoolPlayer(
            player_id=p.player_id,
            name=p.name,
            team=p.team,
            opponent=p.opponent,
            position=p.position,
            salary=p.salary,
            projection=p.projection or 0.0,
            ceiling=p.ceiling if p.ceiling is not None else (p.projection or 0.0),
            floor=p.floor if p.floor is not None else 0.0,
            ownership=p.ownership or 0.0,
            leverage=p.leverage or 0.0,
            game_id=p.game_id,
            locked=p.locked,
            excluded=p.excluded,
        )
    return pool


def _slot_names(roster_slots: List[str]) -> List[str]:
    """Deterministic human-readable slot names, e.g. RB -> RB1/RB2, QB -> QB."""
    counts: Dict[str, int] = {}
    for s in roster_slots:
        counts[s] = counts.get(s, 0) + 1
    seen: Dict[str, int] = {}
    names = []
    for s in roster_slots:
        if counts[s] == 1:
            names.append(s)
        else:
            seen[s] = seen.get(s, 0) + 1
            names.append(f"{s}{seen[s]}")
    return names


def _required_counts(roster_slots: List[str]) -> Tuple[Dict[str, int], int]:
    required: Dict[str, int] = {}
    flex_count = 0
    for s in roster_slots:
        if s == "FLEX":
            flex_count += 1
        else:
            required[s] = required.get(s, 0) + 1
    return required, flex_count


def _team_opponent_map(pool: Dict[str, _PoolPlayer]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for p in pool.values():
        if p.team and p.opponent:
            mapping[p.team] = p.opponent
    return mapping


def _build_and_solve(
    pool: Dict[str, _PoolPlayer],
    eligible_ids: List[str],
    req: OptimizeRequest,
    forced_include: List[str],
    forced_exclude: List[str],
    previous_lineups: List[List[str]],
    exposure_bonus: Dict[str, float],
    tie_break: Dict[str, float],
) -> Tuple[Optional[Dict[str, int]], Optional[str]]:
    """
    Build and solve a single lineup MILP.

    Returns (assignment, error_message). `assignment` maps player_id -> 1 for
    every selected player (only selected players are present). error_message
    is set (assignment is None) when the problem is infeasible or otherwise
    unsolved.
    """
    prob = pulp.LpProblem("slateedge_lineup", pulp.LpMaximize)

    x: Dict[str, pulp.LpVariable] = {
        pid: pulp.LpVariable(f"x_{i}", cat="Binary") for i, pid in enumerate(eligible_ids)
    }

    def X(pid: str):
        return x[pid]

    roster_slots = req.roster_slots
    flex_positions = set(req.flex_positions)
    required, flex_count = _required_counts(roster_slots)
    roster_size = len(roster_slots)

    ids_by_position: Dict[str, List[str]] = {}
    for pid in eligible_ids:
        ids_by_position.setdefault(pool[pid].position, []).append(pid)

    all_positions = set(required.keys()) | flex_positions

    # --- roster composition constraints -----------------------------------
    for pos in all_positions:
        ids = ids_by_position.get(pos, [])
        if pos in flex_positions:
            # dedicated lower bound (may be 0 if this position has no
            # dedicated slots at all, only flex eligibility)
            dedicated = required.get(pos, 0)
            if dedicated > 0:
                prob += pulp.lpSum(X(p) for p in ids) >= dedicated
        else:
            dedicated = required.get(pos, 0)
            prob += pulp.lpSum(X(p) for p in ids) == dedicated

    if flex_positions:
        flex_ids = [pid for pid in eligible_ids if pool[pid].position in flex_positions]
        dedicated_sum = sum(required.get(p, 0) for p in flex_positions)
        prob += pulp.lpSum(X(p) for p in flex_ids) == dedicated_sum + flex_count

    # total roster size sanity (redundant but cheap + guards against
    # mis-specified roster_slots / flex_positions combos)
    prob += pulp.lpSum(X(p) for p in eligible_ids) == roster_size

    # --- salary -------------------------------------------------------------
    max_salary = req.max_salary if req.max_salary is not None else req.salary_cap
    salary_cap_eff = min(req.salary_cap, max_salary)
    prob += pulp.lpSum(X(p) * pool[p].salary for p in eligible_ids) <= salary_cap_eff
    if req.min_salary:
        prob += pulp.lpSum(X(p) * pool[p].salary for p in eligible_ids) >= req.min_salary

    # --- locks / excludes / forced from exposure logic ----------------------
    for pid in forced_include:
        if pid in x:
            prob += X(pid) == 1
    for pid in forced_exclude:
        if pid in x:
            prob += X(pid) == 0

    # --- team / game caps -----------------------------------------------
    if req.max_players_per_team is not None:
        by_team: Dict[str, List[str]] = {}
        for pid in eligible_ids:
            by_team.setdefault(pool[pid].team, []).append(pid)
        for team, ids in by_team.items():
            prob += pulp.lpSum(X(p) for p in ids) <= req.max_players_per_team

    by_game: Dict[str, List[str]] = {}
    for pid in eligible_ids:
        by_game.setdefault(pool[pid].game_id, []).append(pid)

    if req.max_players_per_game is not None:
        for game, ids in by_game.items():
            prob += pulp.lpSum(X(p) for p in ids) <= req.max_players_per_game

    if req.min_players_per_game is not None:
        for game, ids in by_game.items():
            z = pulp.LpVariable(f"gameused_{game}", cat="Binary")
            m = max(len(ids), 1)
            prob += pulp.lpSum(X(p) for p in ids) <= m * z
            prob += pulp.lpSum(X(p) for p in ids) >= req.min_players_per_game * z

    # --- global ownership / projection / ceiling floors ---------------------
    if req.global_max_ownership is not None:
        prob += (
            pulp.lpSum(X(p) * pool[p].ownership for p in eligible_ids)
            <= req.global_max_ownership
        )
    if req.min_total_projection is not None:
        prob += (
            pulp.lpSum(X(p) * pool[p].projection for p in eligible_ids)
            >= req.min_total_projection
        )
    if req.min_total_ceiling is not None:
        prob += (
            pulp.lpSum(X(p) * pool[p].ceiling for p in eligible_ids)
            >= req.min_total_ceiling
        )

    # --- groups --------------------------------------------------------
    for g in req.groups:
        ids = [pid for pid in g.player_ids if pid in x]
        if not ids and g.type != "if_then":
            continue
        if g.type == "at_least":
            prob += pulp.lpSum(X(p) for p in ids) >= (g.count or 0)
        elif g.type == "at_most":
            prob += pulp.lpSum(X(p) for p in ids) <= (g.count or 0)
        elif g.type == "exactly":
            prob += pulp.lpSum(X(p) for p in ids) == (g.count or 0)
        elif g.type == "if_then":
            if g.if_player_id in x and g.then_player_id in x:
                prob += X(g.then_player_id) >= X(g.if_player_id)
        elif g.type == "exclude_together":
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    prob += X(ids[i]) + X(ids[j]) <= 1

    # --- stack rules -------------------------------------------------------
    sr = req.stack_rules
    qb_ids = ids_by_position.get("QB", [])
    teams_with_qb = sorted({pool[p].team for p in qb_ids})
    team_opponent = _team_opponent_map(pool)

    for team in teams_with_qb:
        team_qb_ids = [p for p in qb_ids if pool[p].team == team]
        qb_team_var = pulp.lpSum(X(p) for p in team_qb_ids)  # 0/1 in practice

        pass_catchers = [
            pid
            for pid in eligible_ids
            if pool[pid].team == team and pool[pid].position in ("WR", "TE")
        ]
        pc_sum = pulp.lpSum(X(p) for p in pass_catchers)
        prob += pc_sum >= sr.qb_stack_min * qb_team_var
        m_pc = max(len(pass_catchers), 1)
        prob += pc_sum <= sr.qb_stack_max + m_pc * (1 - qb_team_var)

        opp = team_opponent.get(team)
        if sr.bring_back_min > 0 and opp:
            opp_ids = [pid for pid in eligible_ids if pool[pid].team == opp]
            prob += (
                pulp.lpSum(X(p) for p in opp_ids)
                >= sr.bring_back_min * qb_team_var
            )

        if not sr.allow_rb_with_qb:
            rb_ids = [
                pid
                for pid in eligible_ids
                if pool[pid].team == team and pool[pid].position == "RB"
            ]
            m_rb = max(len(rb_ids), 1)
            prob += pulp.lpSum(X(p) for p in rb_ids) <= m_rb * (1 - qb_team_var)

    if not sr.allow_dst_vs_offense:
        dst_ids = ids_by_position.get("DST", [])
        for d in dst_ids:
            d_opp = pool[d].opponent
            offense_ids = [
                pid
                for pid in eligible_ids
                if pool[pid].team == d_opp and pool[pid].position != "DST"
            ]
            m_off = max(len(offense_ids), 1)
            prob += pulp.lpSum(X(p) for p in offense_ids) <= m_off * (1 - X(d))

    # --- lineup diversity vs previous lineups -------------------------------
    max_shared = roster_size - req.min_unique_players
    for prev in previous_lineups:
        prev_ids = [pid for pid in prev if pid in x]
        if prev_ids:
            prob += pulp.lpSum(X(p) for p in prev_ids) <= max_shared

    # --- objective -----------------------------------------------------
    w = req.objective_weights
    obj_terms = []
    for pid in eligible_ids:
        pl = pool[pid]
        coef = (
            w.projection * pl.projection
            + w.ceiling * pl.ceiling
            + w.leverage * pl.leverage
            - w.ownership_penalty * pl.ownership
        )
        coef += exposure_bonus.get(pid, 0.0)
        coef += tie_break.get(pid, 0.0)
        obj_terms.append(coef * X(pid))
    prob += pulp.lpSum(obj_terms)

    solver = pulp.PULP_CBC_CMD(msg=False)
    status = prob.solve(solver)

    if pulp.LpStatus[status] != "Optimal":
        return None, pulp.LpStatus[status]

    assignment = {pid: 1 for pid in eligible_ids if X(pid).value() and X(pid).value() > 0.5}
    return assignment, None


def _assign_slots(
    selected_ids: List[str],
    pool: Dict[str, _PoolPlayer],
    roster_slots: List[str],
    flex_positions: List[str],
) -> Dict[str, str]:
    """Deterministically map selected players onto human-readable slot names."""
    names = _slot_names(roster_slots)
    required, _flex_count = _required_counts(roster_slots)
    flex_set = set(flex_positions)

    by_pos: Dict[str, List[str]] = {}
    for pid in selected_ids:
        by_pos.setdefault(pool[pid].position, []).append(pid)
    for pos in by_pos:
        by_pos[pos] = sorted(by_pos[pos], key=lambda pid: pid)

    roster: Dict[str, str] = {}
    remaining_by_pos = {pos: list(ids) for pos, ids in by_pos.items()}

    # 1) fill dedicated (non-FLEX) slots for every position, flex-eligible or not
    for slot_label, slot_name in zip(roster_slots, names):
        if slot_label == "FLEX":
            continue
        candidates = remaining_by_pos.get(slot_label, [])
        if candidates:
            roster[slot_name] = candidates.pop(0)

    # 2) whatever is left among flex-eligible positions fills FLEX slot(s)
    leftover: List[str] = []
    for pos in flex_set:
        leftover.extend(remaining_by_pos.get(pos, []))
    leftover.sort()

    for slot_label, slot_name in zip(roster_slots, names):
        if slot_label == "FLEX" and leftover:
            roster[slot_name] = leftover.pop(0)

    return roster


def _stack_summary(
    selected_ids: List[str], pool: Dict[str, _PoolPlayer]
) -> str:
    qbs = [pid for pid in selected_ids if pool[pid].position == "QB"]
    if not qbs:
        return "No QB in lineup."
    qb = pool[qbs[0]]
    same_team_pc = [
        pid
        for pid in selected_ids
        if pool[pid].team == qb.team and pool[pid].position in ("WR", "TE")
    ]
    bring_back = [pid for pid in selected_ids if pool[pid].team == qb.opponent]
    parts = [f"QB {qb.team} stacked with {len(same_team_pc)} pass catcher(s) ({qb.team})"]
    if bring_back:
        parts.append(f"{len(bring_back)} bring-back from {qb.opponent}")
    return "; ".join(parts) + "."


def _lineup_totals(selected_ids: List[str], pool: Dict[str, _PoolPlayer], w) -> Dict[str, float]:
    salary = sum(pool[p].salary for p in selected_ids)
    proj = sum(pool[p].projection for p in selected_ids)
    ceil_ = sum(pool[p].ceiling for p in selected_ids)
    own = sum(pool[p].ownership for p in selected_ids)
    lev = sum(pool[p].leverage for p in selected_ids)
    score = (
        w.projection * proj
        + w.ceiling * ceil_
        + w.leverage * lev
        - w.ownership_penalty * own
    )
    return {
        "salary": salary,
        "projection": proj,
        "ceiling": ceil_,
        "ownership": own,
        "leverage": lev,
        "score": score,
    }


def generate_lineups(req: OptimizeRequest) -> OptimizeResponse:
    pool = _to_pool(req.players)
    warnings: List[str] = []

    excluded_set = set(req.excluded_player_ids) | {
        pid for pid, p in pool.items() if p.excluded
    }
    locked_set = set(req.locked_player_ids) | {
        pid for pid, p in pool.items() if p.locked
    }

    base_eligible = [pid for pid in pool if pid not in excluded_set]

    seed = req.random_seed if req.random_seed is not None else 0
    rng = np.random.default_rng(seed)

    num_lineups = max(req.num_lineups, 0)
    lineups: List[LineupResult] = []
    previous_id_lists: List[List[str]] = []
    usage_count: Dict[str, int] = {pid: 0 for pid in pool}

    for i in range(num_lineups):
        # --- exposure cap: hard-exclude players who have hit their cap ----
        forced_exclude: List[str] = []
        for pid in base_eligible:
            if pid in locked_set:
                continue
            cap = req.max_exposure.get(pid, 1.0)
            allowed_so_far = math.floor(cap * num_lineups)
            if usage_count[pid] >= allowed_so_far and cap < 1.0:
                forced_exclude.append(pid)
            elif cap <= 0.0:
                forced_exclude.append(pid)

        # --- min_exposure best-effort: force-include if this is the last
        # possible chance to hit the floor; otherwise add a soft bonus -----
        forced_include = list(locked_set & set(base_eligible))
        exposure_bonus: Dict[str, float] = {}
        remaining_lineups = num_lineups - i
        for pid, min_share in req.min_exposure.items():
            if pid not in pool or pid in excluded_set:
                continue
            target = math.ceil(min_share * num_lineups)
            shortfall = target - usage_count[pid]
            if shortfall <= 0:
                continue
            if shortfall >= remaining_lineups:
                if pid not in forced_include:
                    forced_include.append(pid)
            else:
                # soft nudge, scaled small relative to typical projection points
                exposure_bonus[pid] = 0.05 * shortfall

        tie_break: Dict[str, float] = {}
        if req.reproducible:
            lineup_rng = np.random.default_rng((seed, i))
            for pid in base_eligible:
                tie_break[pid] = float(lineup_rng.uniform(0, 1e-4))

        assignment, err = _build_and_solve(
            pool=pool,
            eligible_ids=base_eligible,
            req=req,
            forced_include=forced_include,
            forced_exclude=forced_exclude,
            previous_lineups=previous_id_lists,
            exposure_bonus=exposure_bonus,
            tie_break=tie_break,
        )

        if assignment is None:
            # Retry once without the min_exposure forced-include in case that
            # forcing (not a real hard requirement) caused the infeasibility.
            if forced_include and set(forced_include) - locked_set:
                assignment, err = _build_and_solve(
                    pool=pool,
                    eligible_ids=base_eligible,
                    req=req,
                    forced_include=list(locked_set & set(base_eligible)),
                    forced_exclude=forced_exclude,
                    previous_lineups=previous_id_lists,
                    exposure_bonus=exposure_bonus,
                    tie_break=tie_break,
                )

        if assignment is None:
            warnings.append(
                f"Stopped after {len(lineups)} lineup(s): could not generate lineup "
                f"#{i + 1} ({err}). Exposure caps, diversity constraints, or the "
                "configured groups/stack rules likely made further unique lineups "
                "infeasible."
            )
            continue

        selected_ids = sorted(assignment.keys())
        roster = _assign_slots(selected_ids, pool, req.roster_slots, req.flex_positions)
        totals = _lineup_totals(selected_ids, pool, req.objective_weights)

        lineup = LineupResult(
            lineup_id=f"lineup_{len(lineups) + 1}",
            players=selected_ids,
            roster=roster,
            salary_used=int(totals["salary"]),
            total_projection=round(totals["projection"], 3),
            total_ceiling=round(totals["ceiling"], 3),
            total_ownership=round(totals["ownership"], 3),
            leverage_score=round(totals["leverage"], 3),
            model_score=round(totals["score"], 3),
            stack_summary=_stack_summary(selected_ids, pool),
        )
        lineups.append(lineup)
        previous_id_lists.append(selected_ids)
        for pid in selected_ids:
            usage_count[pid] += 1

    return OptimizeResponse(
        lineups=lineups,
        warnings=warnings,
        settings_version="1.0",
        seed_used=req.random_seed,
    )
