"""Orchestrates data loading -> MIP portfolio generation -> EV simulation.

Shared by the CLI and the FastAPI app so both entry points run the exact
same pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from dk_ev.data.csv_sources import CsvOwnershipSource, CsvProjectionSource, CsvSalarySource
from dk_ev.data.interfaces import OwnershipSource, ProjectionSource, SalarySource
from dk_ev.data.stub_sources import NaiveOwnershipSource, StubProjectionSource
from dk_ev.optimizer.mip import OptimizerConstraints
from dk_ev.optimizer.portfolio import ContestType, PortfolioConfig, generate_portfolio
from dk_ev.payouts import PayoutStructure, cash_5050, sample_gpp
from dk_ev.rules import get_rules
from dk_ev.simulation.ev_simulator import EVSimulator, SimulationResult, SimulatorConfig
from dk_ev.slate import build_slate


@dataclass
class OptimizeRequest:
    sport: str
    contest_type: ContestType = "gpp"
    num_lineups: int = 20
    alpha: float = 0.5  # only used for contest_type == "balanced"

    salaries_path: str | None = None
    projections_path: str | None = None
    ownership_path: str | None = None

    payout: PayoutStructure | None = None
    field_size: int = 10_000
    entry_fee: float = 20.0

    max_overlap: int = 5
    stack_min_size: int = 0
    stack_positions: tuple[str, ...] = ("WR", "TE")
    locked_player_ids: frozenset[str] = field(default_factory=frozenset)
    banned_player_ids: frozenset[str] = field(default_factory=frozenset)
    no_opposing_dst_vs_qb: bool = False
    max_players_per_team: int | None = None

    n_iterations: int = 10_000
    field_sample_size: int = 300
    distribution: str = "normal"
    random_seed: int | None = None


@dataclass
class OptimizeResponse:
    request: OptimizeRequest
    results: list[SimulationResult]


def _default_payout(request: OptimizeRequest) -> PayoutStructure:
    if request.contest_type == "cash":
        return cash_5050(field_size=request.field_size, entry_fee=request.entry_fee)
    return sample_gpp(field_size=request.field_size, entry_fee=request.entry_fee)


def run_optimize(
    request: OptimizeRequest,
    salary_source: SalarySource | None = None,
    projection_source: ProjectionSource | None = None,
    ownership_source: OwnershipSource | None = None,
) -> OptimizeResponse:
    rules = get_rules(request.sport)

    salary_source = salary_source or CsvSalarySource(request.salaries_path)
    projection_source = projection_source or (
        CsvProjectionSource(request.projections_path)
        if request.projections_path
        else StubProjectionSource()
    )
    ownership_source = ownership_source or (
        CsvOwnershipSource(request.ownership_path)
        if request.ownership_path
        else NaiveOwnershipSource()
    )

    players = build_slate(salary_source, projection_source, ownership_source)

    portfolio_config = PortfolioConfig(
        contest_type=request.contest_type,
        alpha=request.alpha,
        num_lineups=request.num_lineups,
        max_overlap=request.max_overlap,
        stack_min_size=request.stack_min_size,
        stack_positions=request.stack_positions,
    )
    base_constraints = OptimizerConstraints(
        locked_player_ids=request.locked_player_ids,
        banned_player_ids=request.banned_player_ids,
        no_opposing_dst_vs_qb=request.no_opposing_dst_vs_qb,
        max_players_per_team=request.max_players_per_team,
    )
    lineups = generate_portfolio(players, rules, portfolio_config, base_constraints)

    payout = request.payout or _default_payout(request)
    sim_config = SimulatorConfig(
        n_iterations=request.n_iterations,
        field_sample_size=request.field_sample_size,
        distribution=request.distribution,
        random_seed=request.random_seed,
    )
    simulator = EVSimulator(players, rules, payout, sim_config)
    results = simulator.simulate_many(lineups)
    results.sort(key=lambda r: r.ev, reverse=True)

    return OptimizeResponse(request=request, results=results)
