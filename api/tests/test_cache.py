from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.cache import _build_safe_default_key, redis_cache

# Fake Redis Pipeline
class FakePipeline:
    """Simulates a Redis pipeline context manager for testing sets and string keys."""
    def __init__(self, redis_stub: FakeRedis) -> None:
        self.redis_stub = redis_stub
        self.commands: list[tuple[str, tuple[Any, ...]]] = []

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.commands.append(("setex", (key, ttl, value)))

    def sadd(self, key: str, value: str) -> None:
        self.commands.append(("sadd", (key, value)))

    def expire(self, key: str, ttl: int) -> None:
        self.commands.append(("expire", (key, ttl)))

    async def __aenter__(self) -> FakePipeline:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    async def execute(self) -> list[Any]:
        for cmd_type, args in self.commands:
            if cmd_type == "setex":
                key, ttl, value = args
                self.redis_stub._store[key] = (value, ttl)
                self.redis_stub.set_calls.append((key, ttl, value))
            elif cmd_type == "sadd":
                key, value = args
                self.redis_stub.sadd_calls.append((key, value))
        return []


# Fake Redis

class FakeRedis:
    """Minimal async Redis stub – no network required."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, int]] = {}  # key → (value, ttl)
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, int, str]] = []
        self.sadd_calls: list[tuple[str, str]] = []

    async def get(self, key: str) -> str | None:
        self.get_calls.append(key)
        entry = self._store.get(key)
        return entry[0] if entry else None

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = (value, ttl)
        self.set_calls.append((key, ttl, value))

    def pipeline(self, transaction: bool = True) -> FakePipeline:
        return FakePipeline(self)

    def seed(self, key: str, value: Any, ttl: int = 300) -> None:
        self._store[key] = (json.dumps(value, default=str), ttl)


# Helpers

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


# Context-Based Key Builder Tests

def test_safe_default_key_builder_is_stable() -> None:
    ctx1 = {"body": DummyBody(page_id="abc-123"), "request": _make_request()}
    ctx2 = {"body": DummyBody(page_id="abc-123"), "request": _make_request()}
    
    assert _build_safe_default_key(ctx1) == _build_safe_default_key(ctx2)


def test_safe_default_key_builder_ignores_framework_objects() -> None:
    # Different request instances but identical payload must produce the exact same key
    ctx1 = {"body": DummyBody(page_id="abc-123"), "request": _make_request({"unique-header": "x"})}
    ctx2 = {"body": DummyBody(page_id="abc-123"), "request": _make_request({"unique-header": "y"})}
    
    assert _build_safe_default_key(ctx1) == _build_safe_default_key(ctx2)


# Decorator behaviour

@pytest.mark.asyncio
@patch("app.core.cache.get_client")
async def test_cache_miss_calls_handler_and_stores_result(mock_get_client: MagicMock) -> None:
    redis = FakeRedis()
    mock_get_client.return_value = redis
    handler_calls = 0

    @redis_cache(ttl=60, namespace="test")
    async def handler(body: DummyBody, request: Request) -> DummyResponse:
        nonlocal handler_calls
        handler_calls += 1
        return DummyResponse(page_id=body.page_id, data="fresh")

    result = await handler(body=DummyBody(page_id="p1"), request=_make_request())

    assert result.page_id == "p1"
    assert result.data == "fresh"
    assert handler_calls == 1
    assert len(redis.set_calls) == 1          # stored in Redis
    assert len(redis.get_calls) > 0


@pytest.mark.asyncio
@patch("app.core.cache.get_client")
async def test_cache_hit_skips_handler(mock_get_client: MagicMock) -> None:
    redis = FakeRedis()
    mock_get_client.return_value = redis
    
    body = DummyBody(page_id="p2")
    req = _make_request()
    
    # Calculate the key structure matching the target execution environment
    cache_key = f"test:handler:{_build_safe_default_key({'body': body, 'request': req})}"
    redis.seed(cache_key, {"page_id": "p2", "data": "cached"})

    handler_calls = 0

    @redis_cache(ttl=60, namespace="test")
    async def handler(body: DummyBody, request: Request) -> DummyResponse:
        nonlocal handler_calls
        handler_calls += 1
        return DummyResponse(page_id=body.page_id, data="should-not-reach")

    result = await handler(body=body, request=req)

    assert handler_calls == 0
    assert result["data"] == "cached"
    assert len(redis.set_calls) == 0


@pytest.mark.asyncio
@patch("app.core.cache.get_client")
async def test_force_refresh_bypasses_cache(mock_get_client: MagicMock) -> None:
    redis = FakeRedis()
    mock_get_client.return_value = redis
    
    body = DummyBody(page_id="p3")
    req_normal = _make_request()
    req_refresh = _make_request({"x-cache-refresh": "true"})
    
    cache_key = f"test:handler:{_build_safe_default_key({'body': body, 'request': req_normal})}"
    redis.seed(cache_key, {"page_id": "p3", "data": "stale"})

    handler_calls = 0

    @redis_cache(ttl=60, namespace="test")
    async def handler(body: DummyBody, request: Request) -> DummyResponse:
        nonlocal handler_calls
        handler_calls += 1
        return DummyResponse(page_id=body.page_id, data="refreshed")

    result = await handler(body=body, request=req_refresh)

    assert handler_calls == 1
    assert result.data == "refreshed"
    assert len(redis.set_calls) == 1


@pytest.mark.asyncio
@patch("app.core.cache.get_client")
async def test_redis_get_failure_falls_through_gracefully(mock_get_client: MagicMock) -> None:
    """Verifies infrastructure faults bypass cache lookups cleanly."""
    class BrokenRedis(FakeRedis):
        async def get(self, key: str) -> None:
            raise ConnectionError("Redis cluster unreachable")

    mock_get_client.return_value = BrokenRedis()
    handler_calls = 0

    @redis_cache(ttl=60, namespace="test")
    async def handler(body: DummyBody, request: Request) -> DummyResponse:
        nonlocal handler_calls
        handler_calls += 1
        return DummyResponse(page_id=body.page_id, data="live")

    result = await handler(body=DummyBody(page_id="p4"), request=_make_request())

    assert handler_calls == 1
    assert result.data == "live"


@pytest.mark.asyncio
@patch("app.core.cache.get_client")
async def test_custom_key_builder(mock_get_client: MagicMock) -> None:
    redis = FakeRedis()
    mock_get_client.return_value = redis
    redis.seed("test:handler:custom:p6", {"page_id": "p6", "data": "custom-cached"})

    @redis_cache(
        ttl=60,
        namespace="test",
        # Custom builder extracts identity cleanly from execution context dictionary
        key_builder=lambda ctx: f"custom:{ctx['body'].page_id}",
    )
    async def handler(body: DummyBody, request: Request) -> DummyResponse:
        return DummyResponse(page_id=body.page_id, data="should-not-reach")

    result = await handler(body=DummyBody(page_id="p6"), request=_make_request())
    assert result["data"] == "custom-cached"