"""
app/core/cache.py

Usage
─────
    from app.core.cache import cache_response

    @router.post("/import")
    @cache_response(ttl=300, namespace="notion:import")
    async def import_from_notion(
        body: NotionImportRequest,
        request: Request,                   # ← injected automatically
        redis: Redis = Depends(redis_dep),  # ← injected automatically
    ) -> NotionImportResponse: ...

    # Custom key – e.g. include the authenticated user:
    @cache_response(
        ttl=60,
        namespace="resume:detail",
        key_builder=lambda body, request: f"user:{request.state.user_id}:resume:{body.resume_id}",
    )
    async def get_resume(...): ...
"""
from __future__ import annotations

import functools
import hashlib
import json
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

from fastapi import Request, Response
from redis.asyncio import Redis
from app.core.redis import get_client

from app.core.logging import get_logger

import asyncio
import inspect
import time
from collections import OrderedDict

from fastapi.encoders import jsonable_encoder

log = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

# Header names
_REFRESH_HEADER = "x-cache-refresh"
_CACHE_STATUS_HEADER = "X-Cache"
_CACHE_TTL_HEADER = "X-Cache-TTL"


# Key builders
def _body_hash(body: Any) -> str:
    """
    Produce a stable SHA-256 prefix from any Pydantic model or plain dict.
    Uses model_dump() so field ordering is always consistent.
    """
    if hasattr(body, "model_dump"):
        raw = body.model_dump(mode="json")
    elif isinstance(body, dict):
        raw = body
    else:
        raw = {"_val": str(body)}

    # sort_keys=True → identical dicts always produce the same hash
    serialised = json.dumps(raw, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode()).hexdigest()[:16]


def default_key_builder() -> Callable[[Any, Request], str]:
    """Returns a key of body hash."""

    def _build(body: Any, request: Request) -> str:  # noqa: ARG001
        return _body_hash(body)

    return _build


# Decorator
def cache_response(
    ttl: int = 300,
    namespace: str = "route",
    key_builder: Callable[[Any, Request], str] | None = None,
    body_param: str = "body",
) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
    """
    Decorator that wraps a FastAPI async endpoint with Redis cache-aside logic.

    The wrapped function **must** have:
      - `request: Request`  in its signature  (FastAPI injects it for free)
      - `redis: Redis`       in its signature  (via Depends or direct injection)

    Both can sit anywhere in the signature – the decorator inspects kwargs.
    """

    _build_key = key_builder or default_key_builder()

    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request: Request | None = kwargs.get("request")  # type: ignore[assignment]
            redis: Redis | None = kwargs.get("redis") or get_client()  # type: ignore[assignment]
            body: Any = kwargs.get(body_param)

            if redis is None or request is None or body is None:
                log.debug(
                    "Cache skipped – missing redis/request/body [endpoint=%s]",
                    func.__name__,
                )
                return await func(*args, **kwargs)

            cache_key = f"{namespace}:{_build_key(body, request)}"
            force_refresh = request.headers.get(_REFRESH_HEADER, "").lower() == "true"

            # Try cache lookup (with graceful degradation)
            if not force_refresh:
                try:
                    cached_raw = await redis.get(cache_key)
                    if cached_raw is not None:
                        log.debug("Cache HIT [key=%s, endpoint=%s]", cache_key, func.__name__,)
                        _set_cache_headers(request, status="HIT", ttl=ttl)
                        # Deserialise back to the return type if it's a Pydantic model
                        cached_data = json.loads(cached_raw)
                        return_type = func.__annotations__.get("return")
                        if return_type and hasattr(return_type, "model_validate"):
                            return return_type.model_validate(cached_data)  # type: ignore[return-value]
                        return cached_data  # type: ignore[return-value]
                except Exception as exc:  # noqa: BLE001
                    log.warning("Cache lookup failed – falling through to handler [key=%s, error=%s]", cache_key, exc)

            result = await func(*args, **kwargs)
            try:
                if hasattr(result, "model_dump"):
                    payload = result.model_dump(mode="json")
                elif isinstance(result, dict):
                    payload = result
                else:
                    payload = {"_raw": str(result)}

                await redis.setex(cache_key, ttl, json.dumps(payload, default=str))
                log.debug(
                    "Cache SET [key=%s, ttl=%s, forced=%s, endpoint=%s]",
                    cache_key,
                    ttl,
                    force_refresh,
                    func.__name__,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Cache write failed [key=%s, error=%s]", cache_key, exc)

            _set_cache_headers(request, status="MISS", ttl=ttl)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


# Header helpers
def _set_cache_headers(request: Request, *, status: str, ttl: int) -> None:
    """
    Stash cache metadata in request.state so the response middleware
    (or a custom APIRoute class) can forward them as response headers.
    FastAPI doesn't let decorators set response headers directly, so we
    use request.state as a side-channel picked up by add_cache_headers().
    """
    request.state.cache_status = status
    request.state.cache_ttl = ttl


# Response middleware helper
async def add_cache_headers(request: Request, call_next: Callable) -> Response:
    """
    Starlette middleware that promotes request.state cache metadata into
    actual HTTP response headers.

    Register in main.py:
        app.middleware("http")(add_cache_headers)
    """
    response: Response = await call_next(request)
    if hasattr(request.state, "cache_status"):
        response.headers[_CACHE_STATUS_HEADER] = request.state.cache_status
        response.headers[_CACHE_TTL_HEADER] = str(request.state.cache_ttl)
    return response


# local in-process locks
_locks: dict[str, asyncio.Lock] = {}


def _default_key_builder(
    func_name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    payload = json.dumps(
        {
            "args": args,
            "kwargs": kwargs,
        },
        sort_keys=True,
        default=str,
    )

    digest = hashlib.sha256(payload.encode()).hexdigest()

    return f"{func_name}:{digest}"


def redis_cache(
    ttl: int = 300,
    namespace: str = "cache",
    key_builder: Callable[
        [tuple[Any, ...], dict[str, Any]],
        str,
    ]
    | None = None,
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]],
    Callable[P, Coroutine[Any, Any, R]],
]:
    """
    Redis cache decorator for async service functions.

    Features:
    - Redis-backed
    - async-safe
    - TTL
    - request coalescing
    - Pydantic support
    """

    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        if not inspect.iscoroutinefunction(func):
            raise TypeError("redis_cache only supports async functions")

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = (
                key_builder(args, kwargs)
                if key_builder
                else _default_key_builder(
                    func.__name__,
                    args,
                    kwargs,
                )
            )

            cache_key = f"{namespace}:{key}"
            redis: Redis | None = get_client()
            if redis is None:
                raise RuntimeError("Redis client not initialized. Call init_redis() on startup.")

            # 1. Fast path
            cached = await redis.get(cache_key)
            log.debug(f"[redis_cache] Getting cache [key={cache_key}, value={cached}]")
            if cached is not None:
                data = json.loads(cached)
                log.debug(f"[redis_cache] Getting cache [key={cache_key}, value={data}]")
                return_type = func.__annotations__.get("return")

                if (
                    return_type
                    and hasattr(return_type, "model_validate")
                ):
                    return return_type.model_validate(data)

                return data

            # 2. Stampede protection
            lock = _locks.setdefault(
                cache_key,
                asyncio.Lock(),
            )

            async with lock:
                # another coroutine may already have filled cache
                cached = await redis.get(cache_key)
                log.debug(f"[redis_cache] Getting cache [key={cache_key}, value={cached}]")
                if cached is not None:
                    data = json.loads(cached)

                    return_type = func.__annotations__.get(
                        "return"
                    )

                    if (
                        return_type
                        and hasattr(return_type, "model_validate")
                    ):
                        return return_type.model_validate(data)

                    return data

                # compute
                result = await func(*args, **kwargs)

                payload = jsonable_encoder(result)

                await redis.setex(
                    cache_key,
                    ttl,
                    json.dumps(payload, default=str),
                )
                log.debug(f"[redis_cache] Setting cache [key={cache_key}, value={payload}]")

                return result

        return wrapper

    return decorator