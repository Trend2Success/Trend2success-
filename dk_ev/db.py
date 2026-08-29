"""SQLite engine/session setup for dk_ev's SQLAlchemy models."""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from dk_ev.models import Base

DEFAULT_DB_URL = "sqlite:///./dk_ev.db"


def make_engine(db_url: str | None = None):
    url = db_url or os.environ.get("DK_EV_DATABASE_URL", DEFAULT_DB_URL)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db(bind_engine=None) -> None:
    Base.metadata.create_all(bind=bind_engine or engine)


@contextmanager
def session_scope(session_factory=None) -> Iterator[Session]:
    factory = session_factory or SessionLocal
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
