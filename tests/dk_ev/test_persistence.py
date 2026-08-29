from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dk_ev.domain import Lineup
from dk_ev.models import Base
from dk_ev.payouts import sample_gpp
from dk_ev.persistence import get_run, list_runs, save_run
from dk_ev.rules import NFL_RULES
from dk_ev.simulation.ev_simulator import EVSimulator, SimulatorConfig

from .fixtures import small_nfl_slate


def make_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_save_and_load_run_round_trips_lineups():
    slate = small_nfl_slate()
    by_id = {p.player_id: p for p in slate}
    lineup = Lineup(
        slots=NFL_RULES.slots,
        players=tuple(
            by_id[i]
            for i in ["qb1", "rb1", "rb2", "wr1", "wr2", "wr3", "te1", "rb3", "dst1"]
        ),
    )
    payout = sample_gpp(field_size=1000, entry_fee=20.0)
    config = SimulatorConfig(n_iterations=500, field_sample_size=50, random_seed=1)
    simulator = EVSimulator(slate, NFL_RULES, payout, config)
    result = simulator.simulate(lineup)

    Session = make_session_factory()
    with Session() as session:
        run = save_run(session, "nfl", "gpp", 1, {"alpha": 0.5}, [result])
        session.commit()
        run_id = run.id

    with Session() as session:
        loaded = get_run(session, run_id)
        assert loaded is not None
        assert loaded.sport == "nfl"
        assert len(loaded.lineups) == 1
        record = loaded.lineups[0]
        assert record.rank == 1
        assert record.salary == lineup.salary
        assert len(record.roster) == 9
        assert record.roster[0]["player_id"] == "qb1"

    with Session() as session:
        runs = list_runs(session)
        assert len(runs) == 1


def test_save_run_ranks_lineups_by_ev_descending():
    slate = small_nfl_slate()
    by_id = {p.player_id: p for p in slate}
    lineup_a = Lineup(
        slots=NFL_RULES.slots,
        players=tuple(
            by_id[i]
            for i in ["qb1", "rb1", "rb2", "wr1", "wr2", "wr3", "te1", "rb3", "dst1"]
        ),
    )
    lineup_b = Lineup(
        slots=NFL_RULES.slots,
        players=tuple(
            by_id[i]
            for i in ["qb2", "rb3", "rb4", "wr3", "wr4", "wr5", "te2", "te1", "dst2"]
        ),
    )
    payout = sample_gpp(field_size=1000, entry_fee=20.0)
    config = SimulatorConfig(n_iterations=500, field_sample_size=50, random_seed=2)
    simulator = EVSimulator(slate, NFL_RULES, payout, config)
    results = simulator.simulate_many([lineup_b, lineup_a])  # intentionally out of order

    Session = make_session_factory()
    with Session() as session:
        run = save_run(session, "nfl", "gpp", 2, {}, results)
        session.commit()
        ev_values = [lu.ev for lu in run.lineups]
        assert ev_values == sorted(ev_values, reverse=True)
        assert [lu.rank for lu in run.lineups] == [1, 2]
