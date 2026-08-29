import asyncio

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dfs_ev.config import Settings
from dfs_ev.db import Base
from dfs_ev.opticodds.cache import ResponseCache
from dfs_ev.opticodds.client import OpticOddsBudgetExceededError, OpticOddsClient, OpticOddsRateLimitError


def _settings(**overrides) -> Settings:
    base = dict(
        opticodds_api_key="test-key",
        opticodds_base_url="https://fake.opticodds.test/api/v3",
        db_path=":memory:",
        cache_ttl_seconds=900,
        max_calls_per_slate=200,
    )
    base.update(overrides)
    return Settings(**base)


def _isolated_cache(tmp_path) -> ResponseCache:
    """A ResponseCache backed by its own engine, independent of dfs_ev.db's
    module-level singleton (which would otherwise leak state between tests)."""
    engine = create_engine(f"sqlite:///{tmp_path / 'cache.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    return ResponseCache(session_factory=session_local)


def _client_with_transport(handler, tmp_path, **settings_overrides) -> OpticOddsClient:
    settings = _settings(**settings_overrides)
    cache = _isolated_cache(tmp_path)
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(base_url=settings.opticodds_base_url, transport=transport)
    return OpticOddsClient(settings=settings, cache=cache, http_client=http_client)


def test_cache_hit_avoids_second_http_call(tmp_path):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        assert "key" in request.url.params  # api key sent as query param, never logged
        return httpx.Response(200, json={"data": [{"id": "fx1"}]})

    client = _client_with_transport(handler, tmp_path)

    async def _run():
        first = await client.fixtures_active(league="ncaaf")
        second = await client.fixtures_active(league="ncaaf")
        return first, second

    first, second = asyncio.run(_run())
    assert first == second
    assert calls["n"] == 1  # second call served from cache
    assert client.call_count == 1


def test_fixtures_odds_batches_ids_and_sportsbooks(tmp_path):
    seen_params = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.append(dict(request.url.params))
        return httpx.Response(200, json={"data": [{"player_id": "p"}]})

    client = _client_with_transport(handler, tmp_path)
    player_ids = [f"p{i}" for i in range(12)]  # 12 ids -> 3 batches of <=5
    books = ["Pinnacle", "DraftKings", "FanDuel"]  # 3 books -> 1 batch of <=5

    async def _run():
        return await client.fixtures_odds(
            market="player_passing_yards", player_ids=player_ids, sportsbooks=books
        )

    rows = asyncio.run(_run())
    assert len(rows) == 3  # one merged row per (id_batch x book_batch) call
    assert len(seen_params) == 3
    for params in seen_params:
        ids_in_call = params["player_id"].split(",")
        assert len(ids_in_call) <= 5
        books_in_call = params["sportsbook"].split(",")
        assert len(books_in_call) <= 5


def test_429_raises_rate_limit_error_and_stops_fanout(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limited"})

    client = _client_with_transport(handler, tmp_path)

    async def _run():
        await client.sports_active()

    with pytest.raises(OpticOddsRateLimitError):
        asyncio.run(_run())


def test_soft_call_budget_is_enforced(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    client = _client_with_transport(handler, tmp_path, max_calls_per_slate=1)

    async def _run():
        await client.sports_active()
        await client.leagues()

    with pytest.raises(OpticOddsBudgetExceededError):
        asyncio.run(_run())
