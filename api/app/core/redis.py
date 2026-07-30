from collections.abc import AsyncGenerator

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import get_settings

_client: Redis | None = None


def get_client() -> Redis:
    """Return the already-initialized client. Raises if called before startup."""
    if _client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() on startup.")
    return _client


async def init_redis() -> None:
    global _client
    settings = get_settings()
    _client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    await _client.ping()  # fail fast on startup if Redis is unreachable


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


# FastAPI dependency
async def get_redis() -> AsyncGenerator[Redis, None]:
    yield get_client()
