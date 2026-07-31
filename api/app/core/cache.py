import asyncio
import functools
import hashlib
import inspect
import json
from typing import Any, Callable, Coroutine, ParamSpec, TypeVar
from app.core.logging import get_logger
from fastapi import Response, Request
from fastapi.encoders import jsonable_encoder
from app.core.redis import get_client

logger = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

_REFRESH_HEADER = "x-cache-refresh"
_CACHE_STATUS_HEADER = "X-Cache"
_CACHE_TTL_HEADER = "X-Cache-TTL"
_CACHE_CONTROL = "Cache-Control"

# Local in-process locks for request coalescing (Stampede Protection)
_locks: dict[str, asyncio.Lock] = {}

def _build_safe_default_key(ctx: dict[str, Any]) -> str:
    """
    Filters out volatile frameworks objects (dependencies, requests) 
    and returns a stable SHA256 hash of primitive parameters.
    """
    cleaned = {}
    skip_keys = {"self", "cls", "request", "response", "db", "session", "background_tasks"}
    primitive_types = (str, int, float, bool, type(None))

    for k, v in ctx.items():
        if k.lower() in skip_keys:
            continue
        
        # Serialize primitives directly, extract dictionary representations for Pydantic models
        if isinstance(v, primitive_types):
            cleaned[k] = v
        elif hasattr(v, "model_dump"):  # Pydantic v2
            cleaned[k] = v.model_dump()
        elif hasattr(v, "dict"):        # Pydantic v1
            cleaned[k] = v.dict()
        elif isinstance(v, (list, tuple, set)):
            cleaned[k] = [str(i) if not isinstance(i, primitive_types) else i for i in v]

    payload = json.dumps(cleaned, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def redis_cache(
    ttl: int = 300,
    namespace: str = "cache",
    key_builder: Callable[[dict[str, Any]], str] | None = None,
    tags: list[str] | Callable[[dict[str, Any]], list[str]] | None = None,
) -> Callable:
    """
    Unified enterprise-grade cache decorator. Works transparently on 
    Service layer methods, Controller layers, and Web routes.
    """
    def decorator(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        if not inspect.iscoroutinefunction(func):
            raise TypeError("redis_cache only supports async functions")

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Map all positional and keyword args to their actual parameter names
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            ctx = bound.arguments  # This is a clean map of {"param_name": value}

            if key_builder:
                key = key_builder(ctx)
            else:
                key = _build_safe_default_key(ctx)

            cache_key = f"{namespace}:{func.__name__}:{key}"
            
            redis = get_client()
            if redis is None:
                raise RuntimeError("Redis client not initialized.")

            request = ctx.get("request")
            force_refresh = False
            if isinstance(request, Request):
                force_refresh = "x-cache-refresh" in request.headers

            try:
                if not force_refresh:
                    cached = await redis.get(cache_key)
                    if cached is not None:
                        data = json.loads(cached)
                        return_type = func.__annotations__.get("return")
                        if return_type and hasattr(return_type, "model_validate"):
                            return return_type.model_validate(data)
                        return data
            except Exception as exc:
                logger.warning("Cache lookup failure: %s. Falling back to source computing.", exc)
                cached = None
            

            # Request Coalescing (Stampede Protection)
            lock = _locks.setdefault(cache_key, asyncio.Lock())
            async with lock:
                # Double-check cache inside lock
                try:
                    if not force_refresh:
                        cached = await redis.get(cache_key)
                        if cached is not None:
                            data = json.loads(cached)
                            return_type = func.__annotations__.get("return")
                            if return_type and hasattr(return_type, "model_validate"):
                                return return_type.model_validate(data)
                            return data
                except Exception as exc:
                    logger.warning("Cache lookup failure: %s. Falling back to source computing.", exc)
                    cached = None

                result = await func(*args, **kwargs)
                payload = jsonable_encoder(result)

                resolved_tags = []
                if tags:
                    resolved_tags = tags(ctx) if callable(tags) else tags

                async with redis.pipeline(transaction=True) as pipe:
                    pipe.setex(cache_key, ttl, json.dumps(payload, default=str))
                    
                    for tag in resolved_tags:
                        tag_key = f"tag:{namespace}:{tag}"
                        pipe.sadd(tag_key, cache_key)
                        # Set tag TTL slightly longer than data TTL to prevent orphan memory leak
                        pipe.expire(tag_key, ttl + 3600)
                    
                    await pipe.execute()

                return result

        return wrapper
    return decorator


async def invalidate_tag(namespace: str, tag: str) -> None:
    """
    Finds all cache keys registered under a specific domain tag 
    and removes them atomically.
    """
    redis = get_client()
    if not redis:
        logger.error("Redis client unavailable; skipping tag invalidation.")
        return

    tag_key = f"tag:{namespace}:{tag}"
    try:
        # Retrieve all individual cache keys attached to this entity tag
        cache_keys = await redis.smembers(tag_key)
        
        if cache_keys:
            async with redis.pipeline(transaction=True) as pipe:
                pipe.delete(*cache_keys)
                pipe.delete(tag_key)
                await pipe.execute()
            logger.info(f"Successfully purged {len(cache_keys)} keys for tag: {tag_key}")
        else:
            logger.debug(f"No keys found matching tag: {tag_key}")
    except Exception as exc:
        logger.error(f"Failed to invalidate cache tag {tag_key}: {exc}", exc_info=True)


# header helpers
def set_cache_headers(
    request: Request,
    *,
    status: str,
    ttl: int,
    cache_control: str | None = None,
) -> None:
    """
    Stash cache metadata in request.state so the response middleware
    (or a custom APIRoute class) can forward them as response headers.
    FastAPI doesn't let decorators set response headers directly, so we
    use request.state as a side-channel picked up by add_cache_headers().
    """
    request.state.cache_status = status
    request.state.cache_ttl = ttl

    if cache_control:
        request.state.cache_control = cache_control

# Response middleware helper
async def add_cache_headers(
    request: Request,
    call_next: Callable,
) -> Response:
    """
    Starlette middleware that promotes request.state cache metadata into
    actual HTTP response headers.

    Register in main.py:
        app.middleware("http")(add_cache_headers)
    """
    response: Response = await call_next(request)

    if hasattr(request.state, "cache_status"):
        response.headers[_CACHE_STATUS_HEADER] = request.state.cache_status

    if hasattr(request.state, "cache_ttl"):
        response.headers[_CACHE_TTL_HEADER] = str(request.state.cache_ttl)

    if hasattr(request.state, "cache_control"):
        response.headers[_CACHE_CONTROL] = (request.state.cache_control)

    return response