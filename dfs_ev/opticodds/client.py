"""Async OpticOdds API v3 client with SQLite response caching, batching, and
rate-limit/call-budget guards.

Auth: the API key is sent as a `key` query parameter (matches OpticOdds v3
usage) and is never logged -- request logging in this module only ever
prints the path + non-secret params. Re-verify the exact auth mechanism
against your OpticOdds v3 docs/dashboard if it differs for your account.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any, Iterable

import httpx

from dfs_ev.config import Settings, get_settings
from dfs_ev.opticodds.cache import ResponseCache

HISTORICAL_PATHS = {"/fixtures/results", "/fixtures/player-results"}


class OpticOddsRateLimitError(RuntimeError):
    """Raised when OpticOdds returns 429; caller should stop fan-out."""


class OpticOddsBudgetExceededError(RuntimeError):
    """Raised when the per-slate soft call budget is exhausted."""


def _chunk(items: list[Any], size: int) -> list[list[Any]]:
    if not items:
        return [[]]
    return [items[i : i + size] for i in range(0, len(items), size)]


class _RateLimiter:
    """Sliding-window limiter: at most `limit` calls per 60s window."""

    def __init__(self, limit: int):
        self.limit = limit
        self._calls: deque[float] = deque()

    async def wait(self) -> None:
        now = time.monotonic()
        while self._calls and now - self._calls[0] > 60:
            self._calls.popleft()
        if len(self._calls) >= self.limit:
            sleep_for = 60 - (now - self._calls[0])
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
        self._calls.append(time.monotonic())


class OpticOddsClient:
    def __init__(
        self,
        settings: Settings | None = None,
        cache: ResponseCache | None = None,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.settings = settings or get_settings()
        self.cache = cache or ResponseCache()
        self._client = http_client
        self._owns_client = http_client is None
        self._call_count = 0
        self._historical_limiter = _RateLimiter(self.settings.historical_rate_limit_per_min)
        self._default_limiter = _RateLimiter(self.settings.default_rate_limit_per_min)

    async def __aenter__(self) -> "OpticOddsClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.settings.opticodds_base_url, timeout=20.0)
        return self._client

    @property
    def call_count(self) -> int:
        return self._call_count

    async def _get(self, path: str, params: dict[str, Any], ttl: int | None = None, use_cache: bool = True) -> dict:
        clean_params = {k: v for k, v in params.items() if v is not None}
        if use_cache:
            cached = self.cache.get(path, clean_params)
            if cached is not None:
                return cached

        if self._call_count >= self.settings.max_calls_per_slate:
            raise OpticOddsBudgetExceededError(
                f"OpticOdds soft call budget ({self.settings.max_calls_per_slate}/slate) exhausted; "
                "cached responses only. Increase OPTICODDS_MAX_CALLS_PER_SLATE if intentional."
            )

        limiter = self._historical_limiter if path in HISTORICAL_PATHS else self._default_limiter
        await limiter.wait()

        client = self._ensure_client()
        request_params = dict(clean_params)
        request_params["key"] = self.settings.require_api_key()

        try:
            resp = await client.get(path, params=request_params)
        finally:
            self._call_count += 1

        if resp.status_code == 429:
            raise OpticOddsRateLimitError(
                f"OpticOdds 429 rate limit on {path}; stopped fan-out at {self._call_count} calls."
            )
        resp.raise_for_status()
        data = resp.json()
        self.cache.set(path, clean_params, data, ttl or self.settings.cache_ttl_seconds)
        return data

    # ---- Discovery ----
    async def sports_active(self) -> dict:
        return await self._get("/sports/active", {})

    async def leagues(self, sport: str = "football") -> dict:
        return await self._get("/leagues", {"sport": sport})

    async def markets_active(self) -> dict:
        return await self._get("/markets/active", {})

    async def players(self, sport: str = "football", league: str = "ncaaf") -> dict:
        return await self._get("/players", {"sport": sport, "league": league})

    async def squads(self, team_id: str) -> dict:
        return await self._get("/squads", {"team_id": team_id})

    # ---- Slate / fixtures ----
    async def fixtures_active(self, sport: str = "football", league: str = "ncaaf") -> dict:
        return await self._get("/fixtures/active", {"sport": sport, "league": league})

    # ---- Odds / player props / game environment ----
    async def fixtures_odds(
        self,
        market: str,
        fixture_ids: Iterable[str] | None = None,
        player_ids: Iterable[str] | None = None,
        team_ids: Iterable[str] | None = None,
        sportsbooks: Iterable[str] | None = None,
    ) -> list[dict]:
        """Batches to <=5 combined fixture/player/team IDs and <=5 sportsbooks
        per call, merging `data` rows across batches.
        """
        id_kind, ids = self._pick_id_param(fixture_ids, player_ids, team_ids)
        books = list(sportsbooks or [])
        id_batches = _chunk(ids, self.settings.max_ids_per_call)
        book_batches = _chunk(books, self.settings.max_books_per_call)

        merged: list[dict] = []
        for id_batch in id_batches:
            for book_batch in book_batches:
                params: dict[str, Any] = {"market": market}
                if id_batch:
                    params[id_kind] = ",".join(id_batch)
                if book_batch:
                    params["sportsbook"] = ",".join(book_batch)
                data = await self._get("/fixtures/odds", params)
                merged.extend(data.get("data", []))
        return merged

    @staticmethod
    def _pick_id_param(
        fixture_ids: Iterable[str] | None, player_ids: Iterable[str] | None, team_ids: Iterable[str] | None
    ) -> tuple[str, list[str]]:
        if fixture_ids:
            return "fixture_id", list(fixture_ids)
        if player_ids:
            return "player_id", list(player_ids)
        if team_ids:
            return "team_id", list(team_ids)
        return "fixture_id", []

    # ---- Injuries ----
    async def injuries(self, sport: str = "football", league: str = "ncaaf", team_id: str | None = None) -> dict:
        return await self._get("/injuries", {"sport": sport, "league": league, "team_id": team_id})

    # ---- Backtesting ----
    async def fixtures_results(self, sport: str = "football", league: str = "ncaaf", **filters: Any) -> dict:
        return await self._get("/fixtures/results", {"sport": sport, "league": league, **filters})

    async def fixtures_player_results(self, sport: str = "football", league: str = "ncaaf", **filters: Any) -> dict:
        return await self._get("/fixtures/player-results", {"sport": sport, "league": league, **filters})
