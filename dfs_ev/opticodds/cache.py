"""SQLite response cache for OpticOdds requests, keyed by (path, params)."""
from __future__ import annotations

import datetime as dt
import hashlib
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from dfs_ev.db import CacheEntry, get_session


def _cache_key(path: str, params: dict) -> str:
    canonical = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(f"{path}?{canonical}".encode()).hexdigest()


class ResponseCache:
    def __init__(self, session_factory=get_session):
        self._session_factory = session_factory

    def get(self, path: str, params: dict) -> dict | None:
        key = _cache_key(path, params)
        session: Session = self._session_factory()
        try:
            row = session.get(CacheEntry, key)
            if row is None:
                return None
            if row.expires_at < dt.datetime.utcnow():
                session.execute(delete(CacheEntry).where(CacheEntry.cache_key == key))
                session.commit()
                return None
            return json.loads(row.response_json)
        finally:
            session.close()

    def set(self, path: str, params: dict, response: dict, ttl_seconds: int) -> None:
        key = _cache_key(path, params)
        now = dt.datetime.utcnow()
        session: Session = self._session_factory()
        try:
            entry = session.get(CacheEntry, key)
            payload = json.dumps(response, default=str)
            if entry is None:
                entry = CacheEntry(
                    cache_key=key,
                    path=path,
                    params=json.dumps(params, sort_keys=True, default=str),
                    response_json=payload,
                    fetched_at=now,
                    expires_at=now + dt.timedelta(seconds=ttl_seconds),
                )
                session.add(entry)
            else:
                entry.response_json = payload
                entry.fetched_at = now
                entry.expires_at = now + dt.timedelta(seconds=ttl_seconds)
            session.commit()
        finally:
            session.close()

    def clear_expired(self) -> int:
        session: Session = self._session_factory()
        try:
            now = dt.datetime.utcnow()
            stale = session.execute(select(CacheEntry.cache_key).where(CacheEntry.expires_at < now)).scalars().all()
            if stale:
                session.execute(delete(CacheEntry).where(CacheEntry.cache_key.in_(stale)))
                session.commit()
            return len(stale)
        finally:
            session.close()
