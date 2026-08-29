"""SQLAlchemy models for persisting optimization runs and their lineups."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=lambda: dt.datetime.now(dt.timezone.utc)
    )
    sport: Mapped[str] = mapped_column(String(16))
    contest_type: Mapped[str] = mapped_column(String(16))
    num_lineups_requested: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    lineups: Mapped[list["LineupRecord"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="LineupRecord.rank"
    )


class LineupRecord(Base):
    __tablename__ = "lineups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("optimization_runs.id"))
    rank: Mapped[int] = mapped_column(Integer)
    salary: Mapped[int] = mapped_column(Integer)
    projected_points: Mapped[float] = mapped_column(Float)
    ownership_sum: Mapped[float] = mapped_column(Float)
    ev: Mapped[float] = mapped_column(Float)
    ev_net: Mapped[float] = mapped_column(Float)
    itm_pct: Mapped[float] = mapped_column(Float)
    win_pct: Mapped[float] = mapped_column(Float)
    median_rank: Mapped[float] = mapped_column(Float)
    top1_pct_rate: Mapped[float] = mapped_column(Float)
    top10_pct_rate: Mapped[float] = mapped_column(Float)
    ceiling: Mapped[float] = mapped_column(Float)
    floor: Mapped[float] = mapped_column(Float)
    roster: Mapped[list] = mapped_column(JSON)  # [{slot, player_id, name, team, salary, ...}, ...]

    run: Mapped[OptimizationRun] = relationship(back_populates="lineups")
