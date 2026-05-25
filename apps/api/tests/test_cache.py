"""
tests/unit/test_cache.py
─────────────────────────
Tests for @cache_response covering: HIT, MISS, degradation, force-refresh,
and custom key_builder.  Uses a fake in-memory Redis so no live server needed.
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.cache import _body_hash, cache_response, default_key_builder


# ── Fake Redis ────────────────────────────────────────────────────────────────

class FakeRedis:
    """Minimal async Redis stub – no network required."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, int]] = {}  # key → (value, ttl)
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, int, str]] = []

    async def get(self, key: str) -> str | None:
        self.get_calls.append(key)
        entry = self._store.get(key)
        return entry[0] if entry else None

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = (value, ttl)
        self.set_calls.append((key, ttl, value))

    def seed(self, key: str, value: Any, ttl: int = 300) -> None:
        self._store[key] = (json.dumps(value, default=str), ttl)


# ── Helpers ───────────────────────────────────────────────────────────────────


class DummyBody(BaseModel):
    page_id: str


class DummyResponse(BaseModel):
    page_id: str
    data: str


def _make_request(headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/test",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "query_string": b"",
    }
    return Request(scope)


# ── Key builder ───────────────────────────────────────────────────────────────


def test_body_hash_is_stable() -> None:
    b1 = DummyBody(page_id="abc-123")
    b2 = DummyBody(page_id="abc-123")
    assert _body_hash(b1) == _body_hash(b2)


def test_body_hash_differs_for_different_input() -> None:
    assert _body_hash(DummyBody(page_id="aaa")) != _body_hash(DummyBody(page_id="bbb"))


def test_default_key_builder_format() -> None:
    builder = default_key_builder("notion:import")
    body = DummyBody(page_id="abc-123")
    request = _make_request()
    key = builder(body, request)
    assert key.startswith("notion:import:")
    assert len(key) > len("notion:import:")


# ── Decorator behaviour ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cache_miss_calls_handler_and_stores_result() -> None:
    redis = FakeRedis()
    handler_calls = 0

    @cache_response(ttl=60, namespace="test")
    async def handler(body: DummyBody, request: Request, redis: FakeRedis) -> DummyResponse:
        nonlocal handler_calls
        handler_calls += 1
        return DummyResponse(page_id=body.page_id, data="fresh")

    result = await handler(
        body=DummyBody(page_id="p1"),
        request=_make_request(),
        redis=redis,
    )

    assert result.page_id == "p1"
    assert result.data == "fresh"
    assert handler_calls == 1
    assert len(redis.set_calls) == 1          # stored in Redis
    assert redis.get_calls                    # was looked up


@pytest.mark.asyncio
async def test_cache_hit_skips_handler() -> None:
    redis = FakeRedis()
    body = DummyBody(page_id="p2")
    cache_key = default_key_builder("test")(body, _make_request())
    redis.seed(cache_key, {"page_id": "p2", "data": "cached"})

    handler_calls = 0

    @cache_response(ttl=60, namespace="test")
    async def handler(body: DummyBody, request: Request, redis: FakeRedis) -> DummyResponse:
        nonlocal handler_calls
        handler_calls += 1
        return DummyResponse(page_id=body.page_id, data="should-not-reach")

    result = await handler(body=body, request=_make_request(), redis=redis)

    assert handler_calls == 0                 # handler was NOT called
    assert result.data == "cached"            # got the seeded value
    assert len(redis.set_calls) == 0          # nothing written


@pytest.mark.asyncio
async def test_force_refresh_bypasses_cache() -> None:
    redis = FakeRedis()
    body = DummyBody(page_id="p3")
    cache_key = default_key_builder("test")(body, _make_request())
    redis.seed(cache_key, {"page_id": "p3", "data": "stale"})

    handler_calls = 0

    @cache_response(ttl=60, namespace="test")
    async def handler(body: DummyBody, request: Request, redis: FakeRedis) -> DummyResponse:
        nonlocal handler_calls
        handler_calls += 1
        return DummyResponse(page_id=body.page_id, data="refreshed")

    result = await handler(
        body=body,
        request=_make_request({"x-cache-refresh": "true"}),
        redis=redis,
    )

    assert handler_calls == 1                 # handler WAS called despite cached value
    assert result.data == "refreshed"
    assert len(redis.set_calls) == 1          # new value stored


@pytest.mark.asyncio
async def test_redis_get_failure_falls_through_gracefully() -> None:
    """A broken Redis must never cause a 500 on cache lookup."""

    class BrokenRedis:
        get_calls: list = []

        async def get(self, key: str) -> None:
            raise ConnectionError("Redis is down")

        async def setex(self, *_: Any) -> None:
            raise ConnectionError("Redis is down")

    handler_calls = 0

    @cache_response(ttl=60, namespace="test")
    async def handler(
        body: DummyBody, request: Request, redis: BrokenRedis
    ) -> DummyResponse:
        nonlocal handler_calls
        handler_calls += 1
        return DummyResponse(page_id=body.page_id, data="live")

    result = await handler(
        body=DummyBody(page_id="p4"),
        request=_make_request(),
        redis=BrokenRedis(),
    )

    assert handler_calls == 1                 # fell through to real handler
    assert result.data == "live"              # correct response despite Redis failure


@pytest.mark.asyncio
async def test_missing_redis_skips_cache() -> None:
    """No redis kwarg → caching is silently skipped, handler runs normally."""

    @cache_response(ttl=60, namespace="test")
    async def handler(body: DummyBody, request: Request) -> DummyResponse:
        return DummyResponse(page_id=body.page_id, data="no-redis")

    result = await handler(body=DummyBody(page_id="p5"), request=_make_request())
    assert result.data == "no-redis"


@pytest.mark.asyncio
async def test_custom_key_builder() -> None:
    redis = FakeRedis()
    redis.seed("custom:p6", {"page_id": "p6", "data": "custom-cached"})

    @cache_response(
        ttl=60,
        namespace="test",
        key_builder=lambda body, _req: f"custom:{body.page_id}",
    )
    async def handler(body: DummyBody, request: Request, redis: FakeRedis) -> DummyResponse:
        return DummyResponse(page_id=body.page_id, data="should-not-reach")

    result = await handler(
        body=DummyBody(page_id="p6"),
        request=_make_request(),
        redis=redis,
    )
    assert result.data == "custom-cached"