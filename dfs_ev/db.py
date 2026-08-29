"""SQLite persistence: OpticOdds response cache + run/config history."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from sqlalchemy import JSON, DateTime, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from dfs_ev.config import get_settings


class Base(DeclarativeBase):
    pass


class CacheEntry(Base):
    """Cached OpticOdds response, keyed by request path + sorted params."""

    __tablename__ = "opticodds_cache"

    cache_key: Mapped[str] = mapped_column(String, primary_key=True)
    path: Mapped[str] = mapped_column(String, index=True)
    params: Mapped[str] = mapped_column(Text)
    response_json: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime)


class Run(Base):
    """A persisted optimize/simulate/backtest run and its config."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)
    config_json: Mapped[dict] = mapped_column(JSON)
    result_json: Mapped[dict] = mapped_column(JSON)


_engine = None
_SessionLocal: sessionmaker | None = None


def get_engine(db_path: str | None = None):
    global _engine
    if _engine is None:
        path = db_path or get_settings().db_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{path}", future=True)
        Base.metadata.create_all(_engine)
    return _engine


def get_session(db_path: str | None = None) -> Session:
    global _SessionLocal
    engine = get_engine(db_path)
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    return _SessionLocal()


def reset_engine_for_tests() -> None:
    """Used by tests to force a fresh in-memory engine per test."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
