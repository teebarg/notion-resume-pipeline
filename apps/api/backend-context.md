This file is a merged representation of a subset of the codebase, containing specifically included files, combined into a single document by Repomix.

<file_summary>
This section contains a summary of this file.

<purpose>
This file contains a packed representation of a subset of the repository's contents that is considered the most important context.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.
</purpose>

<file_format>
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  - File path as an attribute
  - Full contents of the file
</file_format>

<usage_guidelines>
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.
</usage_guidelines>

<notes>
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Only files matching these patterns are included: **/*.py, **/*.ts, **/*.js, **/*.json, **/*.md
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Files are sorted by Git change count (files with more changes are at the bottom)
</notes>

</file_summary>

<directory_structure>
app/__init__.py
app/config.py
app/core/__init__.py
app/core/cache.py
app/core/deps.py
app/core/logging.py
app/core/redis.py
app/core/sample_data.py
app/exceptions/notion.py
app/main.py
app/routers/__init__.py
app/routers/health.py
app/routers/jobs.py
app/routers/notion.py
app/routers/resume.py
app/schemas/__init__.py
app/schemas/common.py
app/schemas/jobs.py
app/schemas/notion.py
app/schemas/resume.py
app/services/__init__.py
app/services/job_service.py
app/services/mapper.py
app/services/notion_client.py
app/services/notion_service.py
app/services/parser.py
app/services/pdf_service.py
app/services/resume_service.py
app/utils.py
app/workers/__init__.py
app/workers/runner.py
app/workers/settings.py
app/workers/tasks.py
README.md
repomix.config.json
scripts/generate_previews.py
tests/__init__.py
tests/conftest.py
tests/test_api_notion.py
tests/test_cache.py
tests/test_exports.py
tests/test_health.py
tests/test_notion_pipeline.py
tests/test_notion_service.py
tests/test_resume_schema.py
tests/test_resume_service.py
</directory_structure>

<files>
This section contains the contents of the repository's files.

<file path="app/__init__.py">

</file>

<file path="app/config.py">
from functools import lru_cache

from typing import Annotated, Any, Literal
from pydantic import (
    AnyUrl,
    BeforeValidator,
    computed_field,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "notion-resume-api"
    debug: bool = False
    log_level: str = "INFO"

    host: str = "0.0.0.0"
    port: int = 8000
    api_v1_prefix: str = "/api/v1"

    redis_url: str = "redis://localhost:6379/0"
    redis_job_queue: str = "resume_jobs"

    NOTION_API_TOKEN: str = ""
    NOTION_API_VERSION: str = "2022-06-28"

    job_result_ttl_seconds: int = 86400
    job_poll_interval_ms: int = 500

    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost"]'
    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = (
        []
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
</file>

<file path="app/core/__init__.py">

</file>

<file path="app/core/cache.py">
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
</file>

<file path="app/core/deps.py">
from collections.abc import AsyncGenerator

from app.services.pdf_service import PDFService
from app.services.notion_client import NotionClient
from app.services.notion_service import NotionService
from fastapi import Depends
from redis.asyncio import Redis
from app.core.redis import get_redis
from app.services.job_service import JobService
from app.services.resume_service import ResumeService

def get_notion_client() -> NotionClient:
    return NotionClient()

def get_resume_service() -> ResumeService:
    return ResumeService()

def get_notion_service(
    client: NotionClient = Depends(get_notion_client)
) -> NotionService:
    return NotionService(notion_client=client)

def get_pdf_service(resume_service: ResumeService = Depends(get_resume_service), notion_service: NotionService = Depends(get_notion_service)) -> PDFService:
    return PDFService(resume_service=resume_service, notion_service=notion_service)

async def get_job_service(
    redis: Redis = Depends(get_redis),
) -> AsyncGenerator[JobService, None]:
    yield JobService(redis)
</file>

<file path="app/core/logging.py">
"""
logging.py
----------------
Structured logging setup with async Slack notification support.

Usage:
    from app.core.logging import setup_logging, get_logger

    setup_logging()  # Call once at app startup (e.g. in main.py or lifespan)
    logger = get_logger(__name__)

    logger.info("Starting up")
    logger.success("Order processed", extra={"channel": "sales"})
    logger.warning("Retrying payment")
    logger.error("Unhandled exception", exc_info=True)
"""

from __future__ import annotations

import asyncio
import logging
import logging.config
from typing import Optional

import httpx

from app.config import settings

SUCCESS_LEVEL_NUM = 25
SUCCESS_LEVEL_NAME = "SUCCESS"

logging.addLevelName(SUCCESS_LEVEL_NUM, SUCCESS_LEVEL_NAME)


def _success(self: logging.Logger, message: str, *args, **kwargs) -> None:
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)


logging.Logger.success = _success  # type: ignore[attr-defined]


_http_client: Optional[httpx.AsyncClient] = None


def _get_http_client() -> httpx.AsyncClient:
    """Return the shared AsyncClient, creating it on first call."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(5.0))
    return _http_client


async def close_http_client() -> None:
    """Gracefully close the shared client. Call during app shutdown."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


_TITLE_MAP: dict[str, str] = {
    "info":     "INFO",
    "warning":  "WARNING",
    "error":    "ERROR",
    "critical": "CRITICAL",
    "debug":    "DEBUG",
    "success":  "SUCCESS",
}

_EMOJI_MAP: dict[str, str] = {
    "info":     "ℹ️",
    "warning":  "⚠️",
    "error":    "🔴",
    "critical": "🚨",
    "success":  "✅",
    "debug":    "🐛",
}

_COLOR_MAP: dict[str, str] = {
    "info":     "#36a64f",
    "warning":  "#FFC107",
    "error":    "#FF0000",
    "critical": "#8B0000",
    "debug":    "#555555",
    "success":  "#2ECC71",
}


def _build_slack_payload(text: str, level: str) -> dict:
    """Build a Slack attachment payload for *text* at *level*."""
    level = level.lower()
    title = f"{_EMOJI_MAP.get(level, 'ℹ️')} {_TITLE_MAP.get(level, 'NOTIFICATION')}"
    return {
        "attachments": [
            {
                "fallback": text,
                "color": _COLOR_MAP.get(level, "#FF0000"),
                "title": title,
                "text": text,
            }
        ]
    }

_CHANNEL_MAP_ATTR = "SLACK_ALERTS"  # resolved lazily so settings isn't read at import


def _resolve_url(channel: str, webhook_url: Optional[str]) -> Optional[str]:
    if webhook_url:
        return webhook_url
    channel_map = {
        "alerts": getattr(settings, "SLACK_ALERTS", None),
        "orders": getattr(settings, "SLACK_ORDERS", None),
    }
    return channel_map.get(channel)


async def send_slack_message(
    text: str,
    *,
    level: str = "info",
    channel: str = "alerts",
    webhook_url: Optional[str] = None,
) -> bool:
    """
    Send *text* to Slack asynchronously.

    Returns True on HTTP 200, False on any failure (never raises).
    """
    url = _resolve_url(channel, webhook_url)
    if not url:
        logging.getLogger(__name__).error(
            "No Slack webhook configured for channel %r", channel
        )
        return False

    payload = _build_slack_payload(text, level)
    try:
        client = _get_http_client()
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError as exc:
        logging.getLogger(__name__).error(
            "Slack returned %s for channel %r: %s",
            exc.response.status_code,
            channel,
            exc.response.text,
        )
    except Exception:
        logging.getLogger(__name__).exception(
            "Unexpected error sending Slack message to channel %r", channel
        )
    return False


class SlackLogHandler(logging.Handler):
    """
    Async-safe logging handler that forwards log records to Slack.

    Works in both sync and async contexts:
      - Inside a running event loop: schedules a fire-and-forget task.
      - Outside a running event loop (e.g. startup scripts): runs synchronously
        via asyncio.run().

    Only records at or above SUCCESS_LEVEL_NUM (25) are forwarded.

    Per-record channel override:
        logger.error("Payment failed", extra={"channel": "orders"})
    """

    def __init__(self, channel: str = "alerts") -> None:
        super().__init__(level=SUCCESS_LEVEL_NUM)
        self.channel = channel
        self._pending_tasks: set[asyncio.Task] = set()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            channel = getattr(record, "channel", self.channel)
            level = record.levelname.lower()

            coro = send_slack_message(message, level=level, channel=channel)
            self._dispatch(coro)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        """Cancel any pending tasks and close the handler."""
        for task in list(self._pending_tasks):
            task.cancel()
        super().close()

    def _dispatch(self, coro) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — safe to block (e.g. CLI scripts, pytest)
            asyncio.run(coro)
            return

        task = loop.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._on_task_done)

    def _on_task_done(self, task: asyncio.Task) -> None:
        self._pending_tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            # Use handleError-style logging to avoid infinite recursion
            logging.getLogger(__name__).error(
                "SlackLogHandler background task raised: %s", exc
            )


# ---------------------------------------------------------------------------
# Logging configuration dict
# ---------------------------------------------------------------------------

LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
        },
        "slack_alerts": {
            # "()" lets dictConfig call SlackLogHandler(channel="alerts")
            "()": SlackLogHandler,
            "level": SUCCESS_LEVEL_NUM,
            "formatter": "standard",
            "channel": "alerts",
        },
    },
    "loggers": {
        # Root logger: console only, warnings and above
        "": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Application logger: full pipeline including Slack
        "app": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}


def setup_logging() -> None:
    """
    Apply the logging configuration.

    Call this ONCE at application startup — not at import time.

        # main.py or lifespan
        from app.core.logging_slack import setup_logging
        setup_logging()
    """
    logging.config.dictConfig(LOGGING_CONFIG)


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger namespaced under 'app.' so it inherits the full pipeline.

    Example:
        logger = get_logger(__name__)   # e.g. app.services.payments
    """
    if not name.startswith("app."):
        name = f"app.{name}"
    return logging.getLogger(name)
</file>

<file path="app/core/redis.py">
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
</file>

<file path="app/core/sample_data.py">
from app.schemas.resume import ResumeData, Basics, Experience, Project, Education, Skill

def get_mock_resume_data() -> ResumeData:
    """Returns a highly detailed realistic sample profile matching ResumeData."""
    return ResumeData(
        basics=Basics(
            name="Alex Mercer",
            title="Senior Full-Stack Engineer",
            summary="Product-focused software engineer with 6+ years of experience specializing in high-performance Python backends, FastAPI architectures, and reactive frontend frameworks. Proven track record of scaling data-intensive applications.",
            email="alex.mercer@example.com",
            location="San Francisco, CA",
            website="https://alexmercer.dev",
            linkedin="https://linkedin.com/in/alex-mercer-demo",
            github="https://github.com/alex-mercer-demo",
            phone="+1 (555) 019-2834"
        ),
        experience=[
            Experience(
                company="TechScale Systems",
                role="Senior Backend Engineer",
                location="San Francisco, CA",
                startDate="2023-01",
                endDate="",
                current=True,
                highlights=[
                    "Architected a distributed event-driven data ingestion pipeline using FastAPI and Redis, handling over 10M daily requests.",
                    "Reduced database query latency by 42% by implementing structured cache layers and optimize database indexing.",
                    "Mentored 4 junior engineers and introduced strict code-review guidelines to boost codebase test coverage to 90%."
                ],
                stack=["Python", "FastAPI", "Redis", "PostgreSQL", "Docker", "AWS"]
            ),
            Experience(
                company="CloudSync Corp",
                role="Software Engineer II",
                location="Remote",
                startDate="2020-06",
                endDate="2022-12",
                current=False,
                highlights=[
                    "Designed and maintained core microservices responsible for syncing real-time collaborative document spaces.",
                    "Migrated a monolithic legacy application to a clean hexagonal service architecture, speeding up deployment velocity by 30%."
                ],
                stack=["Python", "Django", "Celery", "RabbitMQ", "React", "TypeScript"]
            )
        ],
        projects=[
            Project(
                name="FastCache Extra",
                description="An open-source performance monitoring plugin for ASGI frameworks providing localized stampede-protection and automatic cache-invalidation tags.",
                highlights=[
                    "Gained over 800 github stars and helped developers isolate cache stampedes in multi-tenant environments."
                ],
                stack=["Python", "FastAPI", "Redis", "Pytest"],
                link="https://github.com/example/fastcache-extra"
            )
        ],
        education=[
            Education(
                degree="Bachelor of Science",
                field="Computer Science",
                institution="State University",
                startDate="2016-09",
                endDate="2020-05"
            )
        ],
        skills=[
            Skill(name="Languages", stack=["Python", "TypeScript", "JavaScript", "SQL", "HTML/CSS"]),
            Skill(name="Frameworks & Tools", stack=["FastAPI", "Django", "React", "Next.js", "Node.js", "Docker", "TailwindCSS"]),
            Skill(name="Databases & Caching", stack=["PostgreSQL", "Redis", "MongoDB", "RabbitMQ"])
        ]
    )
</file>

<file path="app/exceptions/notion.py">
class NotionImportError(Exception):
    """Base exception for all Notion import failures."""
    pass

class NotionPageNotFoundError(NotionImportError):
    """Raised when the requested page does not exist or lacks permissions."""
    pass

class NotionUnauthorizedError(NotionImportError):
    """Raised when the integration token is invalid or expired."""
    pass
</file>

<file path="app/main.py">
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from app.schemas.common import HealthResponse
from app.core.cache import add_cache_headers
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.core.logging import close_http_client, get_logger, setup_logging
from app.core.redis import close_redis, init_redis, get_redis
from app.routers import api_router
from redis.asyncio import Redis

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    await init_redis()

    yield

    await close_redis()
    await close_http_client()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Notion PDF Pipeline",
    description="A developer-focused resume generation platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.middleware("http")(add_cache_headers)
app.add_middleware(
    CORSMiddleware,
    # allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Cache", "X-Cache-TTL"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Mount the static directory so files are accessible via browser
# Example: http://localhost:8000/static/previews/minimal.png
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
async def health_check(redis: Redis = Depends(get_redis)) -> HealthResponse:
    """
    Health check endpoint.
    """
    checks = {}

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = "error"
        logger.error(f"error: {str(e)[:50]}")

    healthy = all(v == "ok" for v in checks.values())
    return HealthResponse(status="ok" if healthy else "degraded", checks=checks)
</file>

<file path="app/routers/__init__.py">
from fastapi import APIRouter

from app.routers import jobs, notion, resume

api_router = APIRouter()
api_router.include_router(notion.router, prefix="/notion", tags=["notion"])
api_router.include_router(resume.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

__all__ = ["api_router"]
</file>

<file path="app/routers/health.py">
from fastapi import APIRouter

from app.config import settings
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, version="0.1.0")
</file>

<file path="app/routers/jobs.py">
from app.core.deps import get_job_service
from fastapi import APIRouter, Depends, HTTPException

from app.schemas.common import ErrorResponse
from app.schemas.jobs import ExportJobRequest, JobStatusResponse
from app.services.job_service import JobService

router = APIRouter()


@router.post(
    "/export",
    response_model=JobStatusResponse,
    status_code=202,
    responses={503: {"model": ErrorResponse}},
)
async def enqueue_export(
    body: ExportJobRequest,
    job_service: JobService = Depends(get_job_service),
) -> JobStatusResponse:
    return await job_service.enqueue_export(body)


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_job_status(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
) -> JobStatusResponse:
    job = await job_service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job
</file>

<file path="app/routers/notion.py">
import io
import hashlib
import hmac
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from app.core.cache import invalidate_tag, set_cache_headers
from app.utils import render_error_page
from app.core.deps import get_notion_service, get_pdf_service, get_resume_service
from app.services.notion_service import NotionService
from app.exceptions.notion import NotionImportError, NotionPageNotFoundError, NotionUnauthorizedError
from app.core.logging import get_logger
from app.schemas.notion import NotionImportRequest, NotionImportResponse
from app.schemas.resume import TemplateId
from app.services.resume_service import ResumeService
from app.services.pdf_service import PDFService

logger = get_logger(__name__)

router = APIRouter()

NOTION_SIGNING_SECRET = "webhook_secret"

def verify_notion_signature(payload: bytes, signature: str | None) -> bool:
    """Validates that incoming webhook payloads genuinely originate from Notion."""
    if not signature:
        return False
    # Notion signs payloads using HMAC-SHA256
    mac = hmac.new(NOTION_SIGNING_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature)


@router.post("/webhook/notion", status_code=status.HTTP_200_OK)
async def headless_notion_sync(
    request: Request,
    x_notion_signature: str | None = Header(None, alias="X-Notion-Signature")
):
    """
    Headless Webhook Endpoint: Listens silently for page updates directly from Notion.
    Nukes associated cache sets immediately upon structural data changes.
    """
    raw_body = await request.body()
    
    if not verify_notion_signature(raw_body, x_notion_signature):
        logger.warning("Rejected unauthorized or spoofed Notion webhook attempt.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid signature validation header"
        )

    payload = await request.json()
    page_id = payload.get("data", {}).get("id") or payload.get("page_id")
    event_type = payload.get("event", {}).get("type") # e.g., "page.updated"

    if page_id and event_type in ("page.updated", "automation.triggered"):
        logger.info(f"Automated Sync Triggered. Reason: {event_type} for Page ID: {page_id}")
        
        await invalidate_tag(namespace="srv:notion", tag=f"page:{page_id}")
        
        return {"status": "headless_sync_processed", "target_invalidated": page_id}

    return {"status": "ignored", "detail": "Event type or entity id out of context"}


@router.get("/preview/{page_id}", response_class=HTMLResponse, summary="Render resume as HTML preview")
async def preview_resume(
    request: Request,
    page_id: str,
    template: TemplateId = "minimal",
    variant: str | None = Query(None, description="Color palette variant variant ID"),
    resume_service: ResumeService = Depends(get_resume_service),
    notion_service: NotionService = Depends(get_notion_service)
) -> HTMLResponse:
    """Re-fetches (from cache) and renders the resume as an HTML page."""
    try:
        if page_id == "sample":
            resume = resume_service.get_sample_resume()
        else:
            resume = await notion_service.get_cached_resume(page_id=page_id)
    except Exception as exc:
        logger.critical("Unhandled critical system failure during import: %s", exc, exc_info=True)
        return render_error_page(
            title="Resume Error",
            message="Couldn't import the resume, contact administrator",
            status_code=500,
        )
    try:
        html = resume_service.render(resume=resume, template_id=template, variant_id=variant)
        set_cache_headers(
            request,
            status="HIT",
            ttl=300,
            cache_control="no-store",
        )
        return HTMLResponse(content=html)
    except ValueError as e:
        # Handles unregistered templates (Client error)
        logger.warning(f"[preview_resume] Invalid template requested - template: {template}")
        raise HTTPException(status_code=400, detail=str(e))

    except FileNotFoundError as e:
        # Handles missing files on disk (Server misconfiguration error)
        logger.exception(f"[preview_resume] Template asset missing on disk - template: {template}")
        return render_error_page(
            title="Template Unavailable",
            message="The requested design file is temporarily unavailable.",
            status_code=500,
        )

@router.get("/pdf/{page_id}", summary="Export resume as PDF")
async def download_pdf(
    page_id: str,
    template: TemplateId = "minimal",
    variant: str | None = None,
    pdf_service: PDFService = Depends(get_pdf_service)
):
    """Renders the resume HTML and converts it to a downloadable PDF."""
    pdf_bytes = await pdf_service.generate_resume_pdf(page_id, template, variant)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=resume-{page_id}.pdf"},
    )


@router.post("/import", status_code=status.HTTP_200_OK, summary="Import and normalize a resume from a Notion page")
async def get_notion_resume(
    body: NotionImportRequest,
    service: NotionService = Depends(get_notion_service)
):
    """
    Fetch a Notion page, recursively parse its blocks, and return a
    normalized resume JSON.

    - **page_id**: Notion page ID (UUID) or full Notion page URL.
    """
    try:
        resume = await service.get_cached_resume(page_id=body.page_id)
        return NotionImportResponse(page_id=body.page_id, message="Resume imported successfully from Notion", resume=resume)
        
    except NotionPageNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        
    except NotionUnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
        
    except NotionImportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
        
    except Exception as exc:
        logger.critical("Unhandled critical system failure during import: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected system error occurred.")


@router.post("/sync", response_model=NotionImportResponse)
async def manual_on_demand_sync(
    body: NotionImportRequest,
    service: NotionService = Depends(get_notion_service)
):
    """
    Manual Override Endpoint: Purges cache keys matching the target entity 
    and aggressively fetches fresh source data to pre-warm the cache.
    """
    await invalidate_tag(namespace="srv:notion", tag=f"page:{body.page_id}")

    fresh_data = await service.get_cached_resume(page_id=body.page_id)
    return NotionImportResponse(page_id=body.page_id, message="Resume synced successfully from Notion", resume=fresh_data)
</file>

<file path="app/routers/resume.py">
from app.core.deps import get_resume_service
from app.schemas.notion import NotionImportResponse
from fastapi import APIRouter, Depends
from typing import List
from app.schemas.resume import Template
from app.services.resume_service import ResumeService

router = APIRouter()

@router.get("/templates", response_model=List[Template])
async def list_templates(
    resume_service: ResumeService = Depends(get_resume_service)
) -> List[Template]:
    """
    The UI uses this to render selection screens dynamically.
    """
    return resume_service.list_templates()


@router.get("/sample", response_model=NotionImportResponse, summary="Retrieve a fully populated sample resume")
async def get_sample_resume(
    resume_service: ResumeService = Depends(get_resume_service)
) -> NotionImportResponse:
    """
    Returns pre-formatted sample resume data matching the system architecture constraints. 
    Can be used by frontends to test rendering layouts or populate empty state screens.
    """
    sample_resume =  resume_service.get_sample_resume()
    return NotionImportResponse(page_id="sample", message="Resume imported successfully from Notion", resume=sample_resume)
</file>

<file path="app/schemas/__init__.py">

</file>

<file path="app/schemas/common.py">
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
    errors: list[dict[str, str]] = Field(default_factory=list)

class HealthResponse(BaseModel):
    status: str
    checks: dict
</file>

<file path="app/schemas/jobs.py">
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.resume import ResumeData, TemplateId


class ExportFormat(StrEnum):
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportJobRequest(BaseModel):
    resume: ResumeData
    format: ExportFormat = ExportFormat.PDF
    template_id: TemplateId = "minimal"


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    format: ExportFormat | None = None
    result_url: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
</file>

<file path="app/schemas/notion.py">
from pydantic import BaseModel, Field, field_validator
import re
from app.schemas.resume import ResumeData


class NotionImportResponse(BaseModel):
    page_id: str
    message: str
    resume: ResumeData


class NotionImportRequest(BaseModel):
    page_id: str

    @field_validator("page_id")
    @classmethod
    def normalize_page_id(cls, v: str) -> str:
        """Accept full Notion URLs or bare page IDs."""
        # Strip URL if passed: https://www.notion.so/Title-<id> or /<id>
        match = re.search(r"([a-f0-9]{32}|[a-f0-9-]{36})$", v.strip().rstrip("/"))
        if match:
            raw = match.group(1).replace("-", "")
            # Re-format as UUID
            return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"
        return v
</file>

<file path="app/schemas/resume.py">
from typing import Literal, List

from pydantic import BaseModel, Field

TemplateId = Literal["enhance", "ats-meridian", "minimal", "modern", "classic", "developer", "modern-canva"]

class Basics(BaseModel):
    name: str = ""
    title: str = ""
    summary: str = ""
    email: str = ""
    location: str = ""
    website: str = ""
    linkedin: str = ""
    github: str = ""
    phone: str = ""


class Experience(BaseModel):
    company: str = ""
    role: str = ""
    location: str = ""
    startDate: str = ""
    endDate: str = ""
    current: bool = False
    highlights: list[str] = []
    stack: list[str] = []


class Project(BaseModel):
    name: str = ""
    description: str = ""
    highlights: list[str] = []
    stack: list[str] = []
    link: str | None = None


class Education(BaseModel):
    degree: str = ""
    field: str = ""
    institution: str = ""
    startDate: str = ""
    endDate: str = ""

class Skill(BaseModel):
    name: str = ""
    stack: list[str] = []

class ResumeData(BaseModel):
    basics: Basics = Basics()
    experience: list[Experience] = []
    education: list[Education] = []
    skills: list[Skill] = []
    projects: list[Project] = Field(default_factory=list)

class TemplateVariant(BaseModel):
    id: str
    name: str
    primary_color: str  # Tailwind class or hex
    text_color: str

class Template(BaseModel):
    id: TemplateId
    name: str
    description: str
    preview: str
    has_sidebar: bool = False
    variants: List[TemplateVariant] = []
</file>

<file path="app/services/__init__.py">

</file>

<file path="app/services/job_service.py">
import json
import uuid
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from redis.asyncio import Redis

from app.config import settings
from app.core.logging import get_logger
from app.schemas.jobs import ExportFormat, ExportJobRequest, JobStatus, JobStatusResponse

logger = get_logger(__name__)

JOB_KEY_PREFIX = "job:"
JOB_STATUS_QUEUED = JobStatus.QUEUED.value
JOB_STATUS_RUNNING = JobStatus.RUNNING.value
JOB_STATUS_COMPLETED = JobStatus.COMPLETED.value
JOB_STATUS_FAILED = JobStatus.FAILED.value


class JobService:
    def __init__(self, redis: Redis) -> None:
        self._settings = settings
        self._redis = redis

    def _job_key(self, job_id: str) -> str:
        return f"{JOB_KEY_PREFIX}{job_id}"

    async def enqueue_export(self, request: ExportJobRequest) -> JobStatusResponse:
        job_id = str(uuid.uuid4())
        payload = {
            "job_id": job_id,
            "status": JOB_STATUS_QUEUED,
            "format": request.format.value,
            "template_id": request.template_id,
            "resume": request.resume.model_dump(mode="json", by_alias=True),
        }
        await self._redis.setex(
            self._job_key(job_id),
            self._settings.job_result_ttl_seconds,
            json.dumps(payload),
        )

        pool = await self._get_arq_pool()
        await pool.enqueue_job(
            "export_resume_task",
            job_id,
            request.format.value,
            request.template_id,
            payload["resume"],
        )
        logger.info("Enqueued export job", extra={"job_id": job_id, "format": request.format})
        return JobStatusResponse(job_id=job_id, status=JobStatus.QUEUED, format=request.format)

    async def get_job_status(self, job_id: str) -> JobStatusResponse | None:
        raw = await self._redis.get(self._job_key(job_id))
        if not raw:
            return None
        data: dict[str, Any] = json.loads(raw)
        return JobStatusResponse(
            job_id=job_id,
            status=JobStatus(data.get("status", JOB_STATUS_QUEUED)),
            format=ExportFormat(data["format"]) if data.get("format") else None,
            result_url=data.get("result_url"),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )

    async def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus,
        result_url: str | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        key = self._job_key(job_id)
        raw = await self._redis.get(key)
        if not raw:
            return
        data = json.loads(raw)
        data["status"] = status.value
        if result_url is not None:
            data["result_url"] = result_url
        if error is not None:
            data["error"] = error
        if metadata:
            data["metadata"] = {**data.get("metadata", {}), **metadata}
        await self._redis.setex(key, self._settings.job_result_ttl_seconds, json.dumps(data))

    async def _get_arq_pool(self) -> ArqRedis:
        return await create_pool(RedisSettings.from_dsn(self._settings.redis_url))
</file>

<file path="app/services/mapper.py">
"""
Resume mapper.
 
Strategy:
  1. Walk nodes top-to-bottom.
  2. A heading_1 or heading_2 signals a new top-level section context.
  3. heading_3 signals a sub-item (job, project, education entry) within a section.
  4. Content under each section is accumulated and structured.
 
Section detection is case-insensitive and handles real-world Notion heading variants.
"""

import json
import re
from typing import Any

from app.schemas.resume import Basics, Education, Experience, Project, ResumeData, Skill
from app.services.parser import ContentNode
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Section keyword mapping
# Only heading_1 and heading_2 trigger section changes.
# heading_3 always means "new sub-item within current section".
# ---------------------------------------------------------------------------
 
_SECTION_ALIASES: dict[str, list[str]] = {
    "summary": [
        "summary", "professional summary", "about", "profile",
        "objective", "professional profile",
    ],
    "experience": [
        "experience", "work experience", "work history", "employment",
        "professional experience",
    ],
    "projects": [
        "projects", "project", "side projects", "portfolio",
        "selected projects", "open source",
    ],
    "skills": [
        "skills", "technical skills", "core competencies",
        "technologies", "tech stack",
    ],
    "education": [
        "education", "academic background", "qualifications",
    ],
    "availability": [
        "availability",
    ],
}
 
# Flat lookup: normalized heading text → canonical section key
SECTION_MAP: dict[str, str] = {
    kw.lower(): section
    for section, keywords in _SECTION_ALIASES.items()
    for kw in keywords
}
 
 
# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def map_to_resume(nodes: list[ContentNode], page_meta: dict[str, Any] | None = None, raw_blocks: list[dict[str, Any]] | None = None) -> ResumeData:
    basics = _extract_basics_from_meta(page_meta)
    sections = _segment_by_section(nodes)
    logger.debug(f"[map_to_resume sections]------------------------------------------: {json.dumps(sections, indent=2, default=str)}")

    # Extract contact fields from raw blocks (hrefs not available in ContentNodes)
    if raw_blocks:
        contact = _extract_contact_from_raw_blocks(raw_blocks)
        basics.title = contact.get("title", "")
        basics.email = contact.get("email", "")
        basics.location = contact.get("location", "")
        basics.website = contact.get("website", "")
        basics.linkedin = contact.get("linkedin", "")
        basics.github = contact.get("github", "")
        basics.phone = contact.get("phone", "")
 
    # Summary
    summary_nodes = sections.get("summary", [])
    if summary_nodes:
        basics.summary = _nodes_to_text(summary_nodes)
 
    experience = _parse_experience(sections.get("experience", []))
    projects = _parse_projects(sections.get("projects", []))
    education = _parse_education(sections.get("education", []))
    skills = _parse_skills(sections.get("skills", []))
 
    # Fallback: name from first h1 if page meta didn't provide it
    if not basics.name:
        for node in nodes:
            if node.type == "heading_1" and node.text:
                basics.name = node.text
                break
 
    return ResumeData(
        basics=basics,
        experience=experience,
        projects=projects,
        education=education,
        skills=skills,
    )
 
# ---------------------------------------------------------------------------
# Section segmentation
# ---------------------------------------------------------------------------
def _segment_by_section(nodes: list[ContentNode]) -> dict[str, list[ContentNode]]:
    """
    Walk nodes and group by the nearest heading_1 / heading_2 section.
    heading_3 is treated as content (sub-item marker), not a section boundary.
    """
    sections: dict[str, list[ContentNode]] = {}
    current_section: str = "unknown"
 
    for node in nodes:
        # Only h1/h2 can change the active section
        if node.type in ("heading_1", "heading_2"):
            detected = SECTION_MAP.get(node.text.strip().lower())
            if detected:
                current_section = detected
                continue  # heading itself is not content
            else:
                # Unrecognized h1/h2: treat as unknown, keep accumulating there
                current_section = "unknown"
                continue
 
        # heading_3 is passed through as content for the section parsers to handle
        sections.setdefault(current_section, []).append(node)
 
    return sections
 
 
# ---------------------------------------------------------------------------
# Section parsers
# ---------------------------------------------------------------------------
def _parse_experience(nodes: list[ContentNode]) -> list[Experience]:
    """
    heading_3 = new job entry (format: "Role — Company" or "Company — Role").
    Paragraph immediately after = date range.
    Bullet points = highlights.
    Inline code paragraphs (tech stack lines) are skipped.
    """
    entries: list[Experience] = []
    current: Experience | None = None
 
    for node in nodes:
        if node.type == "heading_3":
            if current is not None:
                entries.append(current)
            company, role = _split_company_role(node.text)
            current = Experience(company=company, role=role)
 
        elif node.type == "paragraph" and current is not None:
            # Skip tech-stack inline-code lines (e.g. "Python · FastAPI · ...")
            if _is_tech_stack_line(node.text):
                continue
            start, end = _extract_dates(node.text)
            if start or end:
                current.startDate = start
                current.endDate = end
            elif node.text and not _looks_like_date_line(node.text):
                current.highlights.append(node.text)
 
        elif node.type in ("bullet", "sub_bullet") and current is not None:
            flat = _flatten_bullet(node)
            current.highlights.extend(flat)

        elif node.type == "quote":
            skills = _parse_bullet_skills(node.text)
            current.stack.extend(skills)
 
    if current is not None:
        entries.append(current)
 
    return entries
 
 
def _parse_projects(nodes: list[ContentNode]) -> list[Project]:
    """
    heading_3 = project name.
    First non-tech paragraph = description.
    Tech stack extracted from bullet/paragraph starting with "Tech:" or matching known frameworks.
    """
    entries: list[Project] = []
    current: Project | None = None
 
    for node in nodes:
        if node.type == "heading_3":
            if current is not None:
                entries.append(current)
            current = Project(name=node.text.strip())
 
        elif node.type == "paragraph" and current is not None:
            if _is_tech_stack_line(node.text):
                continue  # skip inline-code stack lines
            stack = _extract_tech_from_prefix(node.text)
            if stack:
                current.stack.extend(stack)
            elif not current.description:
                current.description = node.text
 
        elif node.type in ("bullet", "sub_bullet") and current is not None:
            current.highlights.append(node.text)
 
    if current is not None:
        entries.append(current)
 
    return entries
 
 
def _parse_education(nodes: list[ContentNode]) -> list[Education]:
    """
    Education in this Notion page uses plain paragraphs (no h3 per entry).
    Heuristic: bold paragraphs = degree line; italic paragraphs = institution;
    paragraphs matching date pattern = date range.
 
    Groups entries by pairing: degree → institution → dates.
    """
    entries: list[Education] = []
    current: Education | None = None
 
    for node in nodes:
        if node.type == "heading_3":
            # Some resumes use h3 per entry
            if current is not None:
                entries.append(current)
            current = Education(degree=node.text.strip())
            continue
 
        if node.type != "paragraph" or not node.text:
            continue
 
        text = node.text.strip()
 
        # Date line — attach to current entry or start fresh
        start, end = _extract_dates(text)
        if start or end:
            if current is None:
                current = Education()
            current.startDate = start
            current.endDate = end
            entries.append(current)
            current = None
            continue
 
        # Looks like a degree (B.Sc., HND, M.Sc., B.Eng., etc.)
        if _looks_like_degree(text):
            if current is not None and current.degree:
                # Flush the previous incomplete entry before starting a new one
                entries.append(current)
            current = Education(degree=text)
            continue
 
        # Otherwise treat as institution name
        if current is not None and not current.institution:
            current.institution = text
 
    # Flush any trailing entry
    if current is not None and (current.degree or current.institution):
        entries.append(current)
 
    return entries
 
 
def _parse_skills(nodes: list[ContentNode]) -> list[str]:
    """
    Skills section uses h3 sub-headings (Backend, Frontend, etc.) followed by
    comma-separated paragraphs. We collect all text from paragraphs and bullets,
    ignoring the sub-headings themselves, and split on commas/pipes/middle-dots.
    """
    skills: list[Skill] = []
    current: Skill | None = None
    for node in nodes:
        if node.type == "heading_3":
            # Sub-category labels (Backend, Frontend…) — skip, they're not skills
            if current is not None:
                skills.append(current)
            current = Skill(name=node.text.strip())
            continue
        if node.type in ("bullet", "sub_bullet"):
            items = _flatten_bullet(node)
        else:
            items = _split_tech_stack(text=node.text)
        if current is not None:
            current.stack = items

    if current is not None:
        skills.append(current)

    return skills
 
 
# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def _split_tech_stack(text: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r',(?![^(]*\))', text)
        if item.strip()
    ]
 
 
def _extract_basics_from_meta(page_meta: dict[str, Any] | None) -> Basics:
    if not page_meta:
        return Basics()
 
    name = ""
    props: dict[str, Any] = page_meta.get("properties", {})
 
    for key in ("Name", "Title", "Full Name", "name", "title"):
        prop = props.get(key, {})
        if prop.get("type") == "title":
            rich = prop.get("title", [])
            name = "".join(r.get("plain_text", "") for r in rich).strip()
            if name:
                break
 
    return Basics(name=name)


def _extract_contact_from_raw_blocks(raw_blocks: list[dict[str, Any]]) -> dict[str, str]:
    """
    Extract contact fields from the raw pre-section Notion blocks.
 
    We use raw blocks (not ContentNodes) here because hrefs live in rich_text
    entries which the parser intentionally discards — only plain_text is kept.
 
    Handles the real patterns from the resume:
      paragraph → plain "Senior Software Engineer / ..."            → title
      paragraph → "📍 Lagos, Nigeria · Remote-friendly"            → location
      paragraph → "✉️ " + linked "teebarg01@gmail.com"             → email
      paragraph → "🌐 " + linked "Portfolio" (href: niyi.com.ng)   → website
      paragraph → "🔗 " + linked "LinkedIn" (href: linkedin.com)   → linkedin
      paragraph → "🔗 " + linked "Github"   (href: github.com)     → github
      paragraph → "🔗  +2348060001234"                             → phone
    """
    fields: dict[str, str] = {}
 
    for block in raw_blocks:
        if block.get("type") != "paragraph":
            continue
 
        rich_text: list[dict[str, Any]] = block.get("paragraph", {}).get("rich_text", [])
        if not rich_text:
            continue
 
        plain = "".join(rt.get("plain_text", "") for rt in rich_text).strip()
        if not plain:
            continue
 
        # Collect all hrefs present in this block's rich_text
        hrefs = [
            rt["href"]
            for rt in rich_text
            if rt.get("href")
        ]
 
        # Location
        if plain.startswith("📍"):
            fields.setdefault("location", plain.lstrip("📍").strip())
            continue

        # Phone
        if plain.startswith("📞"):
            fields.setdefault("phone", plain.lstrip("📞").strip())
            continue
 
        # Email — prefer href (mailto:), fall back to regex on plain text
        if "✉️" in plain or any("mailto:" in (h or "") for h in hrefs):
            mailto = next((h for h in hrefs if h and h.startswith("mailto:")), None)
            if mailto:
                fields.setdefault("email", mailto.replace("mailto:", "").strip())
            else:
                m = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", plain)
                if m:
                    fields.setdefault("email", m.group(0))
            continue
 
        # LinkedIn — check hrefs first
        linkedin_href = next((h for h in hrefs if h and "linkedin.com" in h), None)
        if linkedin_href:
            fields.setdefault("linkedin", linkedin_href)
            continue
 
        # GitHub — check hrefs first
        github_href = next((h for h in hrefs if h and "github.com" in h), None)
        if github_href:
            fields.setdefault("github", github_href)
            continue
 
        # Website / Portfolio — any remaining href that isn't a known service
        website_href = next(
            (h for h in hrefs if h and not any(s in h for s in ("linkedin", "github", "mailto"))),
            None,
        )
        if website_href and ("🌐" in plain or "portfolio" in plain.lower()):
            fields.setdefault("website", website_href)
            continue
 
        # Job title: first paragraph that isn't contact info
        if not _looks_like_contact(plain) and "title" not in fields:
            fields["title"] = plain
 
    return fields
 
 
def _nodes_to_text(nodes: list[ContentNode]) -> str:
    parts = [node.text for node in nodes if node.text and node.type not in ("heading_3",)]
    return " ".join(parts)
 
 
def _flatten_bullet(node: ContentNode) -> list[str]:
    result = [node.text] if node.text else []
    for child in node.children:
        result.extend(_flatten_bullet(child))
    return result
 
 
def _split_company_role(text: str) -> tuple[str, str]:
    """
    Parse "Role — Company" or "Company — Role" or "Role at Company".
    Real data: "Lead Engineer — Revoque", "Software Engineer — Bolster Networks, Inc."
    Convention in this resume: Role — Company (role comes first).
    """
    for sep in [" — ", " – ", " - ", " | "]:
        if sep in text:
            parts = text.split(sep, 1)
            # Role — Company convention
            return parts[1].strip(), parts[0].strip()
 
    match = re.match(r"^(.+?)\s+at\s+(.+)$", text, re.IGNORECASE)
    if match:
        return match.group(2).strip(), match.group(1).strip()
 
    return text.strip(), ""

def _parse_bullet_skills(skills: str) -> list[str]:
    return [
        skill.strip()
        for skill in re.split(r"\s*[·•|,]\s*", skills)
        if skill.strip()
    ]
 
 
_DATE_PATTERN = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4})"
    r"\s*[–\-—to]+\s*"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4}|Present|Current)",
    re.IGNORECASE,
)
 
_DEGREE_PATTERN = re.compile(
    r"^(B\.?Sc|B\.?Eng|B\.?A|M\.?Sc|M\.?Eng|M\.?A|MBA|Ph\.?D|HND|OND|ND|B\.?Tech|Diploma)\b",
    re.IGNORECASE,
)
 
_TECH_STACK_SEPARATORS = re.compile(r"[·•|,]")
 
# Middle-dot separated lines with 3+ tokens are tech stack lines
# Also catches lines where all tokens look like tool/language names (CamelCase, all-caps)
def _is_tech_stack_line(text: str) -> bool:
    """Detect inline-code tech stack lines like 'Python · FastAPI · PostgreSQL · Redis'."""
    if not text:
        return False
    # If it contains middle dots and looks like a list of short tokens
    if "·" in text:
        tokens = [t.strip() for t in text.split("·") if t.strip()]
        if len(tokens) >= 3:
            return True
    return False
 
 
def _extract_tech_from_prefix(text: str) -> list[str]:
    """Return tech items only if the line starts with a 'Tech:' prefix."""
    match = re.match(r"^(?:tech(?:nologies)?|stack|tools?|built\s+with)\s*[:\-]?\s*(.+)$", text, re.IGNORECASE)
    if match:
        return [t.strip() for t in re.split(r"[,|]", match.group(1)) if t.strip()]
    return []
 
 
def _extract_dates(text: str) -> tuple[str, str]:
    match = _DATE_PATTERN.search(text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "", ""
 
 
def _looks_like_date_line(text: str) -> bool:
    return bool(_DATE_PATTERN.search(text))
 
 
def _looks_like_degree(text: str) -> bool:
    return bool(_DEGREE_PATTERN.match(text))
 
 
def _looks_like_contact(text: str) -> bool:
    """Detect contact info paragraphs: email, URLs, location strings."""
    return bool(re.search(r"[@📍✉️🌐🔗]|https?://|linkedin|github|gmail", text, re.IGNORECASE))
</file>

<file path="app/services/notion_client.py">
"""
Low-level Notion API client.

Responsibilities:
- Authenticated requests via httpx
- Recursive block fetching with pagination
- Basic retry with exponential backoff on 429 / 5xx
"""

import asyncio
from typing import Any

from app.config import settings
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)

NOTION_API_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

# Retry config
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # seconds


class NotionAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Notion API error {status_code}: {message}")


class NotionClient:
    """Async HTTP client for the Notion REST API."""

    def __init__(self):
        self._headers = {
            "Authorization": f"Bearer {settings.NOTION_API_TOKEN}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        }

    async def get_page(self, page_id: str) -> dict[str, Any]:
        normalized_id = self._normalize_page_id(page_id)
        return await self._get(f"/pages/{normalized_id}")

    async def get_blocks_recursive(self, block_id: str) -> list[dict[str, Any]]:
        """Fetch all blocks under block_id, recursively expanding children."""
        normalized_id = self._normalize_page_id(block_id)
        blocks = await self._get_all_blocks(normalized_id)
        for block in blocks:
            if block.get("has_children"):
                block["children"] = await self.get_blocks_recursive(block["id"])
            else:
                block["children"] = []
        return blocks

    async def _get_all_blocks(self, block_id: str) -> list[dict[str, Any]]:
        """Paginate through all children of a block."""
        results: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            params: dict[str, Any] = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor

            data = await self._get(f"/blocks/{block_id}/children", params=params)
            results.extend(data.get("results", []))

            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")

        return results

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{BASE_URL}{path}"
        last_exc: Exception | None = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(MAX_RETRIES):
                try:
                    response = await client.get(url, headers=self._headers, params=params)

                    if response.status_code == 429 or response.status_code >= 500:
                        wait = RETRY_BACKOFF_BASE ** attempt
                        logger.warning(
                            "Notion API returned %s, retrying in %.1fs (attempt %d/%d)",
                            response.status_code,
                            wait,
                            attempt + 1,
                            MAX_RETRIES,
                        )
                        await asyncio.sleep(wait)
                        continue

                    if not response.is_success:
                        body = response.json()
                        raise NotionAPIError(
                            response.status_code,
                            body.get("message", "unknown error"),
                        )

                    return response.json()

                except httpx.RequestError as exc:
                    last_exc = exc
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning("HTTP request error: %s, retrying in %.1fs", exc, wait)
                    await asyncio.sleep(wait)

        raise NotionAPIError(0, f"Max retries exceeded. Last error: {last_exc}")


    @staticmethod
    def _normalize_page_id(page_id: str) -> str:
        cleaned = page_id.strip().replace("-", "")
        if len(cleaned) == 32:
            return (
                f"{cleaned[:8]}-{cleaned[8:12]}-{cleaned[12:16]}-"
                f"{cleaned[16:20]}-{cleaned[20:]}"
            )
        return page_id.strip()
</file>

<file path="app/services/notion_service.py">
import json
from typing import Any
from app.core.logging import get_logger
from app.schemas.resume import ResumeData
from app.services.notion_client import NotionAPIError, NotionClient
from app.services.mapper import map_to_resume
from app.services.parser import parse_blocks
from app.core.cache import redis_cache
from app.exceptions.notion import NotionImportError, NotionPageNotFoundError, NotionUnauthorizedError

logger = get_logger(__name__)

class NotionService:
    def __init__(self, notion_client: NotionClient):
        self.notion_client = notion_client

    async def import_resume(self, page_id: str) -> ResumeData:
        """
        Executes the pure data pipeline to fetch and process a Notion resume.
        Throws domain-specific exceptions.
        """
        page_meta = await self._fetch_page_metadata(page_id)
        raw_blocks = await self._fetch_blocks_recursive(page_id)

        if not raw_blocks:
            logger.info("Notion page '%s' returned no blocks; returning empty resume.", page_id)
            return ResumeData()

        # Parse nodes and build domain object
        nodes = parse_blocks(raw_blocks)
        logger.debug(f"[nodes]: {json.dumps(nodes, indent=2, default=str)}")
        
        resume = map_to_resume(nodes, page_meta=page_meta, raw_blocks=raw_blocks)
        
        logger.info(
            "Successfully compiled resume from Notion page '%s': %d experiences, %d projects.",
            page_id, len(resume.experience), len(resume.projects)
        )
        return resume

    async def _fetch_page_metadata(self, page_id: str) -> dict[str, Any] | None:
        try:
            return await self.notion_client.get_page(page_id)
        except NotionAPIError as exc:
            if exc.status_code == 404:
                raise NotionPageNotFoundError(f"Notion page '{page_id}' not found or access denied.") from exc
            if exc.status_code == 401:
                raise NotionUnauthorizedError("Invalid or expired Notion integration token.") from exc
            
            logger.warning("Could not fetch page meta (status %s); continuing without it.", exc.status_code)
            return None

    async def _fetch_blocks_recursive(self, page_id: str) -> list[dict[str, Any]]:
        try:
            return await self.notion_client.get_blocks_recursive(page_id)
        except NotionAPIError as exc:
            logger.error("Failed executing recursive block fetch for page '%s'.", page_id)
            raise NotionImportError(f"Failed to fetch blocks from Notion: {exc}") from exc

    @redis_cache(
        ttl=30000, 
        namespace="srv:notion", 
        key_builder=lambda ctx: ctx["page_id"],
        tags=lambda ctx: [f"page:{ctx['page_id']}"]
    )
    async def get_cached_resume(self, page_id: str) -> ResumeData:
        """Cached read access proxy wrapper for the main import pipeline."""
        return await self.import_resume(page_id)
</file>

<file path="app/services/parser.py">
"""
Notion block parser.

Converts raw Notion block JSON into a flat, typed intermediate representation.

Output node types:
  heading_1 | heading_2 | heading_3 | heading_4 | paragraph | bullet | sub_bullet | toggle | quote | callout
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContentNode:
    type: str          # heading_1 | heading_2 | heading_3 | heading_4 | paragraph | bullet | sub_bullet | toggle | quote | callout
    text: str
    depth: int = 0     # nesting depth (0 = top-level, 1 = child bullet, etc.)
    children: list["ContentNode"] = field(default_factory=list)


def parse_blocks(blocks: list[dict[str, Any]]) -> list[ContentNode]:
    """Entry point: parse a list of top-level Notion blocks."""
    return _parse_block_list(blocks, depth=0)


def _parse_block_list(blocks: list[dict[str, Any]], depth: int) -> list[ContentNode]:
    nodes: list[ContentNode] = []
    for block in blocks:
        node = _parse_block(block, depth)
        if node is not None:
            nodes.append(node)
    return nodes


def _parse_block(block: dict[str, Any], depth: int) -> ContentNode | None:
    block_type: str = block.get("type", "")
    children_blocks: list[dict[str, Any]] = block.get("children", [])

    match block_type:
        case "heading_1":
            text = _extract_text(block, "heading_1")
            node = ContentNode(type="heading_1", text=text, depth=depth)
        case "heading_2":
            text = _extract_text(block, "heading_2")
            node = ContentNode(type="heading_2", text=text, depth=depth)
        case "heading_3":
            text = _extract_text(block, "heading_3")
            node = ContentNode(type="heading_3", text=text, depth=depth)
        case "heading_4":
            text = _extract_text(block, "heading_4")
            node = ContentNode(type="heading_4", text=text, depth=depth)
        case "toggle":
            text = _extract_text(block, "toggle")
            node = ContentNode(type="toggle", text=text, depth=depth)
        case "quote":
            text = _extract_text(block, "quote")
            node = ContentNode(type="quote", text=text, depth=depth)
        case "callout":
            text = _extract_text(block, "callout")
            node = ContentNode(type="callout", text=text, depth=depth)
        case "paragraph":
            text = _extract_text(block, "paragraph")
            if not text.strip():
                return None  # skip blank paragraphs
            node = ContentNode(type="paragraph", text=text, depth=depth)
        case "bulleted_list_item":
            text = _extract_text(block, "bulleted_list_item")
            node_type = "sub_bullet" if depth > 0 else "bullet"
            node = ContentNode(type=node_type, text=text, depth=depth)
        case "numbered_list_item":
            text = _extract_text(block, "numbered_list_item")
            node_type = "sub_bullet" if depth > 0 else "bullet"
            node = ContentNode(type=node_type, text=text, depth=depth)
        case "toggle" | "quote" | "callout":
            # Treat these as paragraphs — extract text and recurse into children
            text = _extract_text(block, block_type)
            node = ContentNode(type="paragraph", text=text, depth=depth)
        case _:
            # Unsupported block type: still recurse into children if present
            if children_blocks:
                node = ContentNode(type="paragraph", text="", depth=depth)
            else:
                return None

    # Recurse into nested children
    if children_blocks:
        node.children = _parse_block_list(children_blocks, depth=depth + 1)

    return node


def _extract_text(block: dict[str, Any], block_type: str) -> str:
    """Extract plain text from a block's rich_text array."""
    type_data: dict[str, Any] = block.get(block_type, {})
    rich_text: list[dict[str, Any]] = type_data.get("rich_text", [])
    return "".join(rt.get("plain_text", "") for rt in rich_text).strip()
</file>

<file path="app/services/pdf_service.py">
import asyncio
from app.services.notion_service import NotionService
from app.core.logging import get_logger
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
from app.schemas.resume import TemplateId
from app.services.resume_service import ResumeService

logger = get_logger(__name__)

class PDFService:
    def __init__(self, resume_service: ResumeService, notion_service: NotionService):
        self.resume_service = resume_service
        self.notion_service = notion_service

    def _html_to_pdf_sync(self, html: str) -> bytes:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            browser.close()
        return pdf_bytes

    async def _html_to_pdf(self, html: str) -> bytes:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._html_to_pdf_sync, html)

    async def generate_resume_pdf(
        self, 
        page_id: str, 
        template: TemplateId, 
        variant: str | None = None
    ) -> bytes:
        resume = await self.notion_service.get_cached_resume(page_id=page_id)
        html = self.resume_service.render(
            resume=resume, 
            template_id=template, 
            variant_id=variant
        )
        pdf_bytes = await self._html_to_pdf(html)
        return pdf_bytes
</file>

<file path="app/services/resume_service.py">
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.sample_data import get_mock_resume_data
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound
from app.schemas.resume import ResumeData, Template, TemplateId

class ResumeService:
    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or (Path(__file__).parent.parent / "templates" / "resume")
        self._env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html"]),
        )

        # Centralized Template Registry
        self._templates: Dict[TemplateId, Template] = {
            "enhance": Template(
                id="enhance",
                name="Enhance",
                description="An elegant, polished layout designed to elevate standard resumes with enhanced visual hierarchy.",
                preview="enhance.png"
            ),
             "ats-meridian": Template(
                id="ats-meridian",
                name="ATS Meridian",
                description="Strictly optimized for Applicant Tracking Systems with a clean, highly scannable single-column structure.",
                preview="ats-meridian.png"
            ),
            "minimal": Template(
                id="minimal",
                name="Minimal",
                description="A stripped-back, distraction-free single-column layout focusing purely on crisp typography and whitespace.",
                preview="minimal.png"
            ),
            "modern": Template(
                id="modern",
                name="Modern",
                description="A contemporary, stylish layout with subtle accents and a fresh aesthetic for modern industries.",
                preview="modern.png",
            ),
            "classic": Template(
                id="classic",
                name="Classic",
                description="The time-tested, traditional format preferred by conservative industries and executive recruiters.",
                preview="classic.png",
            ),
            "developer": Template(
                id="developer",
                name="Developer",
                description="A technical, data-dense layout designed to prominently feature core skills, languages, and project repositories.",
                preview="developer.png",
            ),
            "modern-canva": Template(
                id="modern-canva",
                name="Modern Canva",
                description="A premium, McKinsey-style layout engineered for senior leaders, emphasizing strategy, scale, and business outcomes.",
                preview="modern-canva.png"
            ),
        }

    def get_sample_resume(self) -> ResumeData:
        """
        Retrieves a default populated resume schema for client-side testing
        and template configuration visual workflows.
        """
        return get_mock_resume_data()

    def list_templates(self) -> List[Template]:
        """Returns all available resume templates."""
        return list(self._templates.values())

    def get_template(self, template_id: TemplateId) -> Optional[Template]:
        """Retrieves metadata for a specific template."""
        return self._templates.get(template_id)

    def render(self, resume: Any, template_id: TemplateId, variant_id: Optional[str] = None) -> str:
        """
        Renders the resume HTML safely with fallback mechanics and variant overrides.
        """
        template_meta = self.get_template(template_id)
        if not template_meta:
            raise ValueError(f"Template '{template_id}' is not registered.")

        variant = None
        if variant_id and template_meta.variants:
            variant = next((v for v in template_meta.variants if v.id == variant_id), template_meta.variants[0])

        try:
            template = self._env.get_template(f"{template_id}.html")
            return template.render(
                resume=resume,
                meta=template_meta,
                variant=variant
            )
        except TemplateNotFound:
            raise FileNotFoundError(f"Template file '{template_id}.html' missing from disk.")
</file>

<file path="app/utils.py">
from fastapi.responses import HTMLResponse

def render_error_page(
    title: str,
    message: str,
    status_code: int,
) -> HTMLResponse:
    return HTMLResponse(
        content=f"""
        <html>
            <body style="
                font-family:sans-serif;
                display:flex;
                align-items:center;
                justify-content:center;
                background:#fafafa;
            ">
                <div style="text-align:center">
                    <h1>{title}</h1>
                    <p>{message}</p>
                </div>
            </body>
        </html>
        """,
        status_code=status_code,
    )
</file>

<file path="app/workers/__init__.py">

</file>

<file path="app/workers/runner.py">
"""CLI entrypoint for the ARQ worker."""

from arq import run_worker as arq_run_worker

from app.workers.settings import WorkerSettings


def run_worker() -> None:
    arq_run_worker(WorkerSettings)


if __name__ == "__main__":
    run_worker()
</file>

<file path="app/workers/settings.py">
from arq.connections import RedisSettings

from app.config import get_settings
from app.workers import tasks

_settings = get_settings()


class WorkerSettings:
    functions = [tasks.export_resume_task]
    on_startup = tasks.on_startup
    on_shutdown = tasks.on_shutdown
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)
    queue_name = _settings.redis_job_queue
    max_jobs = 10
    job_timeout = 300
</file>

<file path="app/workers/tasks.py">
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.redis import get_client
from app.schemas.jobs import JobStatus
from app.services.job_service import JobService

logger = get_logger(__name__)


async def export_resume_task(
    ctx: dict[str, Any],
    job_id: str,
    export_format: str,
    template_id: str,
    resume: dict[str, Any],
) -> dict[str, str]:
    """Render resume to the requested format (stub — wire render engine here)."""
    setup_logging()
    redis_client = get_client()
    job_service = JobService(redis_client)

    await job_service.update_job(job_id, status=JobStatus.RUNNING)
    logger.info(
        "Running export",
        extra={"job_id": job_id, "format": export_format, "template": template_id},
    )

    try:
        # Placeholder: persist rendered artifact and return URL
        result_url = f"/api/v1/exports/{job_id}.{export_format}"
        await job_service.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            result_url=result_url,
            metadata={"template_id": template_id, "resume_name": resume.get("name", "")},
        )
        return {"job_id": job_id, "result_url": result_url}
    except Exception as exc:
        logger.exception("Export job failed", extra={"job_id": job_id})
        await job_service.update_job(job_id, status=JobStatus.FAILED, error=str(exc))
        raise


async def on_startup(ctx: dict[str, Any]) -> None:
    setup_logging()
    logger.info("ARQ worker started")


async def on_shutdown(ctx: dict[str, Any]) -> None:
    logger.info("ARQ worker stopped")
</file>

<file path="README.md">
# Notion Resume API

FastAPI backend for the resume generation platform. Imports Notion pages, normalizes content into a canonical resume schema, and runs export jobs asynchronously via Redis.

## Structure

```text
app/
├── main.py              # Application factory & lifespan
├── config/              # Environment-based settings
├── core/                # Logging, Redis client
├── schemas/             # Pydantic v2 request/response models
├── services/            # Business logic
├── routers/             # Async HTTP endpoints
├── dependencies/        # FastAPI dependency injection
└── workers/             # ARQ background job workers
```

## Quick start

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"

cp .env.example .env
# Set NOTION_API_TOKEN and REDIS_URL

# Terminal 1 — API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — background worker (requires Redis)
arq app.workers.settings.WorkerSettings
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/health/ready` | Redis connectivity |
| POST | `/api/v1/notion/import` | Import resume from Notion page |
| GET | `/api/v1/resumes/templates` | List render templates |
| POST | `/api/v1/jobs/export` | Enqueue PDF/Markdown/HTML export |
| GET | `/api/v1/jobs/{job_id}` | Poll job status |

Interactive docs: http://localhost:8000/docs
</file>

<file path="repomix.config.json">
{
    "output": {
        "filePath": "backend-context.md"
    },
    "ignore": [
        "node_modules",
        ".git",
        "__pycache__",
        "venv",
        ".env",
        "dist",
        "build"
    ],
    "include": [
        "**/*.py",
        "**/*.ts",
        "**/*.js",
        "**/*.json",
        "**/*.md"
    ]
}
</file>

<file path="scripts/generate_previews.py">
#!/usr/bin/env python
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from app.services.resume_service import ResumeService
from playwright.async_api import async_playwright
from app.schemas.resume import ResumeData

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Mock data to cleanly populate your templates during the snapshot process
MOCK_RESUME_DATA = {
    "basics": {
        "name": "Alex Morgan",
        "title": "Senior Staff Software Engineer",
        "email": "alex.morgan@dev.io",
        "phone": "+1 (555) 019-2834",
        "location": "San Francisco, CA",
        "summary": "Architectural leader with 8+ years of experience designing scalable distributed systems. Specialized in Python, TypeScript, and high-performance caching strategies. Passionate about clean code and developer tooling systems.",
        "website" : "https://portfolio.dev.io",
        "linkedin" : "https://www.linkedin.com/in/alex-b46724ba/",
        "github":  "https://github.com/alex"
    },
    "experience": [
        {
            "company": "CloudScale Systems",
            "role": "Tech Lead",
            "location": "EL Paso, Texas",
            "startDate": "2022-03",
            "endDate": "Present",
            "description": "Led an engineering team of 6 to rebuild core streaming pipelines, reducing overall compute costs by 35%. Implemented distributed caching mechanisms handling 50k+ requests per second.",
            "highlights": [
                "Built and maintained a customer-facing web application using React, Node.js, PostgreSQL, and AWS.",
                "Designed and implemented RESTful APIs to support mobile and web clients with consistent sub-200ms response times.",
                "Implemented caching strategies and database query optimizations to improve application throughput under load.",
                "Developed automated data processing pipelines to handle ingestion and transformation of large datasets.",
                "Built internal dashboards and admin tools for reporting, user management, and operational workflows.",
                "Integrated third-party services including payment gateways, email providers, and analytics platforms.",
                "Collaborated with cross-functional teams to deliver features across the full stack in an agile environment.",
                "Wrote unit and integration tests to maintain code quality and reduce regression risk.",
                "Contributed to system design discussions and technical documentation for key platform components."
            ]
        },
        {
            "company": "CoreTech Labs",
            "role": "Software Engineer II",
            "location": "NY, New York",
            "startDate": "2019-06",
            "endDate": "2022-02",
            "description": "Maintained internal developer APIs and optimized SQL queries, improving interface rendering times across consumer dashboards by 400ms.",
            "highlights": [
                "Worked on a scalable digital marketplace platform using modern web technologies including TypeScript, Python, PostgreSQL, and Redis.",
                "Built responsive product catalog and search experiences focused on performance and mobile usability.",
                "Implemented caching and backend optimizations to improve application speed and reduce server load.",
                "Developed intelligent automation tools for customer engagement and workflow assistance using AI-powered systems.",
                "Created bulk data import/export pipelines for managing large datasets efficiently.",
                "Built internal dashboards and management tools for operations, reporting, and inventory tracking.",
                "Integrated advanced search and filtering capabilities to improve product discovery.",
                "Designed background processing systems for notifications, indexing, and scheduled tasks.",
                "Improved frontend performance through server-side rendering, efficient data fetching, and lazy loading techniques."
            ]
        }
    ],
    "education": [
        {
            "institution": "University of Computing",
            "degree": "B.S. in Computer Science",
            "startDate": "2015",
            "endDate": "2019"
        }
    ],
    "skills": [
        {"name": "Frontend", "stack": ["TypeScript", "React"]},
        {"name": "Backend", "stack": ["Python", "FastAPI", "Redis", "Docker", "PostgreSQL", "System Design"]}
    ],
    "projects": [
        {
            "name": "Electric Vehicles",
            "description": "Full plug-in electric vehicles using cutting edge technology",
            "stack": ["Python", "FastAPI", "Redis", "Docker", "PostgreSQL", "System Design"],
            "link": ""
        },
         {
            "name": "AI Sales & Lead Qualification Platform",
            "description": "AI-driven sales automation platform for customer engagement, lead qualification, and intelligent scoring. Integrated LLM APIs for lead classification and scoring. Built conversational workflows for automated customer interactions. Developed backend APIs and data processing pipelines for sales workflows. Implemented lead scoring and analytics systems. Designed extensible architecture for future AI workflow expansion.",
            "stack": [],
            "link": None
        }
    ],
}


async def generate_template_snapshots(output_dir: Path, target_template: str | None = None):
    """Launches a headless browser to render HTML templates to static PNG snapshots."""
    resume_service = ResumeService()
    templates = resume_service.list_templates()
    
    validated_mock_data = ResumeData(**MOCK_RESUME_DATA)
    
    # Filter if user explicitly targeted one layout style
    if target_template:
        templates = [t for t in templates if t.id == target_template]
        if not templates:
            logger.error(f"Template '{target_template}' not found in registry.")
            sys.exit(1)

    # Ensure target output directory exists on disk
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting snapshot generation engine for {len(templates)} layout profiles...")

    # Spin up Playwright context
    async with async_playwright() as p:
        # Launch headless browser instance
        browser = await p.chromium.launch(headless=True)
        
        # Define viewport matching standard A4 aspect ratio proportions (800x1130 px)
        context = await browser.new_context(
            viewport={"width": 800, "height": 1130},
            device_scale_factor=2  # High-DPI/Retina scale factor for ultra-sharp rendering
        )
        page = await context.new_page()

        for template_meta in templates:
            output_file = output_dir / f"{template_meta.id}.png"
            logger.info(f"Rendering blueprint canvas: [{template_meta.name}] -> {output_file.name}")
            
            try:
                html_content = resume_service.render(resume=validated_mock_data, template_id=template_meta.id)
                
                # Inject raw HTML string straight into the headless page DOM context
                await page.set_content(html_content)
                
                # Wait briefly for web fonts or dynamic layouts to structurally settle
                await page.wait_for_load_state("networkidle")
                
                # Take screenshot of the top half / full view
                await page.screenshot(
                    path=str(output_file),
                    type="png",
                    full_page=False # Keeps it constrained to viewport boundaries
                )
                logger.info(f"✅ Successfully captured snapshot for context: {template_meta.id}")
                
            except Exception as e:
                logger.error(f"❌ Failed rendering step for template '{template_meta.id}': {e}")

        await browser.close()
    logger.info("Process complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Headless Blueprint Generator Engine.")
    parser.add_argument(
        "--output", 
        type=str, 
        default=str(Path(__file__).parent.parent / "app" / "static" / "previews"),
        help="Target output directory path for the generated PNG files."
    )
    parser.add_argument(
        "--template", 
        type=str, 
        default=None, 
        help="Optional: target a specific layout profile ID exclusively."
    )
    
    args = parser.parse_args()
    
    # Run the async loop engine cleanly
    asyncio.run(generate_template_snapshots(Path(args.output), args.template))
</file>

<file path="tests/__init__.py">

</file>

<file path="tests/conftest.py">
from __future__ import annotations

from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_notion_service, get_pdf_service
from app.core.redis import get_redis
from app.main import app
from app.schemas.resume import Basics, Experience, ResumeData, Skill
from app.services.notion_service import NotionService


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def sample_resume() -> ResumeData:
    return ResumeData(
        basics=Basics(
            name="Jane Smith",
            title="Senior Software Engineer",
            summary="Experienced backend engineer.",
            email="jane@example.com",
            location="Lagos, Nigeria",
        ),
        experience=[
            Experience(
                company="Acme Corp",
                role="Senior Engineer",
                startDate="Jan 2020",
                endDate="Dec 2023",
                highlights=["Led API redesign"],
            )
        ],
        skills=[Skill(name="Backend", stack=["Python", "FastAPI", "PostgreSQL"])],
    )


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.pipeline = MagicMock()
    return redis


@pytest.fixture
def mock_notion_service(sample_resume: ResumeData) -> MagicMock:
    service = MagicMock(spec=NotionService)
    service.get_cached_resume = AsyncMock(return_value=sample_resume)
    return service


@pytest.fixture
def mock_pdf_service() -> MagicMock:
    service = MagicMock()
    service.generate_resume_pdf = AsyncMock(return_value=b"%PDF-1.4 test content")
    return service


@pytest.fixture
async def client(mock_redis: AsyncMock) -> AsyncIterator[AsyncClient]:
    async def override_get_redis() -> AsyncIterator[AsyncMock]:
        yield mock_redis

    app.dependency_overrides[get_redis] = override_get_redis

    with (
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
        patch("app.main.close_http_client", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def client_with_mocks(
    client: AsyncClient,
    mock_notion_service: MagicMock,
    mock_pdf_service: MagicMock,
) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_notion_service] = lambda: mock_notion_service
    app.dependency_overrides[get_pdf_service] = lambda: mock_pdf_service
    yield client
    app.dependency_overrides.pop(get_notion_service, None)
    app.dependency_overrides.pop(get_pdf_service, None)
</file>

<file path="tests/test_api_notion.py">
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.deps import get_notion_service, get_pdf_service
from app.exceptions.notion import NotionImportError, NotionPageNotFoundError, NotionUnauthorizedError
from app.main import app
from app.schemas.resume import ResumeData
from app.services.notion_service import NotionService


PAGE_ID = "a1b2c3d4-e5f6-7890-1234-5678abcdef01"


@pytest.mark.asyncio
async def test_import_success(client_with_mocks: AsyncClient, sample_resume: ResumeData) -> None:
    response = await client_with_mocks.post(
        "/api/v1/notion/import",
        json={"page_id": PAGE_ID},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page_id"] == PAGE_ID
    assert data["resume"]["basics"]["name"] == sample_resume.basics.name
    assert "imported successfully" in data["message"].lower()


@pytest.mark.asyncio
async def test_import_normalizes_notion_url(client_with_mocks: AsyncClient) -> None:
    response = await client_with_mocks.post(
        "/api/v1/notion/import",
        json={"page_id": f"https://www.notion.so/Resume-{PAGE_ID.replace('-', '')}"},
    )
    assert response.status_code == 200
    assert response.json()["page_id"].replace("-", "") == PAGE_ID.replace("-", "")


@pytest.mark.asyncio
async def test_import_page_not_found(client: AsyncClient) -> None:
    service = MagicMock(spec=NotionService)
    service.get_cached_resume = AsyncMock(
        side_effect=NotionPageNotFoundError("Notion page not found.")
    )
    app.dependency_overrides[get_notion_service] = lambda: service

    response = await client.post("/api/v1/notion/import", json={"page_id": PAGE_ID})

    app.dependency_overrides.pop(get_notion_service, None)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_import_unauthorized(client: AsyncClient) -> None:
    service = MagicMock(spec=NotionService)
    service.get_cached_resume = AsyncMock(
        side_effect=NotionUnauthorizedError("Invalid token.")
    )
    app.dependency_overrides[get_notion_service] = lambda: service

    response = await client.post("/api/v1/notion/import", json={"page_id": PAGE_ID})

    app.dependency_overrides.pop(get_notion_service, None)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_import_malformed_notion_data(client: AsyncClient) -> None:
    service = MagicMock(spec=NotionService)
    service.get_cached_resume = AsyncMock(
        side_effect=NotionImportError("Failed to fetch blocks from Notion.")
    )
    app.dependency_overrides[get_notion_service] = lambda: service

    response = await client.post("/api/v1/notion/import", json={"page_id": PAGE_ID})

    app.dependency_overrides.pop(get_notion_service, None)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_preview_returns_html(client_with_mocks: AsyncClient) -> None:
    response = await client_with_mocks.get(
        f"/api/v1/notion/preview/{PAGE_ID}?template=minimal"
    )
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Jane Smith" in response.text


@pytest.mark.asyncio
async def test_preview_invalid_template(client_with_mocks: AsyncClient) -> None:
    response = await client_with_mocks.get(
        f"/api/v1/notion/preview/{PAGE_ID}?template=not-a-real-template"
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_pdf_export(client_with_mocks: AsyncClient, mock_pdf_service: MagicMock) -> None:
    response = await client_with_mocks.get(
        f"/api/v1/notion/pdf/{PAGE_ID}?template=minimal"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    mock_pdf_service.generate_resume_pdf.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_invalidates_and_returns_resume(client_with_mocks: AsyncClient) -> None:
    with patch("app.routers.notion.invalidate_tag", new_callable=AsyncMock) as invalidate:
        response = await client_with_mocks.post(
            "/api/v1/notion/sync",
            json={"page_id": PAGE_ID},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["resume"]["basics"]["name"] == "Jane Smith"
    invalidate.assert_awaited_once()
</file>

<file path="tests/test_cache.py">
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
</file>

<file path="tests/test_exports.py">
"""
Tests for export-related behaviour.

PDF export is served by the backend (Playwright). JSON and Markdown exports
in the UI are generated client-side from the normalized ResumeData returned
by the import endpoint; these tests verify that canonical data shape.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.deps import get_job_service
from app.main import app
from app.schemas.jobs import ExportFormat, ExportJobRequest, JobStatus, JobStatusResponse
from app.schemas.resume import ResumeData
from app.services.job_service import JobService


@pytest.mark.asyncio
async def test_import_response_is_valid_json_export(
    client_with_mocks: AsyncClient,
    sample_resume: ResumeData,
) -> None:
    """Import endpoint returns JSON-serializable ResumeData (UI JSON export source)."""
    response = await client_with_mocks.post(
        "/api/v1/notion/import",
        json={"page_id": "a1b2c3d4-e5f6-7890-1234-5678abcdef01"},
    )
    assert response.status_code == 200

    exported = json.loads(response.text)
    assert exported["resume"]["basics"]["name"] == sample_resume.basics.name
    assert exported["resume"]["experience"][0]["company"] == "Acme Corp"
    assert exported["resume"]["skills"][0]["stack"] == ["Python", "FastAPI", "PostgreSQL"]

    # Round-trip through Pydantic as the frontend would
    restored = ResumeData.model_validate(exported["resume"])
    assert restored.model_dump_json() == sample_resume.model_dump_json()


def test_resume_data_has_markdown_ready_sections(sample_resume: ResumeData) -> None:
    """Normalized resume contains all sections used by client-side Markdown export."""
    data = sample_resume.model_dump()
    assert data["basics"]["name"]
    assert data["basics"]["summary"]
    assert data["experience"][0]["role"]
    assert data["experience"][0]["highlights"]
    assert data["skills"][0]["name"]
    assert data["skills"][0]["stack"]


@pytest.mark.asyncio
async def test_pdf_generation_mocked(client_with_mocks: AsyncClient, mock_pdf_service: MagicMock) -> None:
    with patch.object(mock_pdf_service, "generate_resume_pdf", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = b"%PDF-1.4 mocked"

        response = await client_with_mocks.get(
            "/api/v1/notion/pdf/test-page?template=minimal"
        )

        assert response.status_code == 200
        assert response.content == b"%PDF-1.4 mocked"
        mock_gen.assert_awaited_once_with("test-page", "minimal", None)


@pytest.mark.asyncio
async def test_job_enqueue_markdown_format(
    client: AsyncClient,
    sample_resume: ResumeData,
    mock_redis: AsyncMock,
) -> None:
    """Background job endpoint accepts markdown export requests."""
    job_service = MagicMock(spec=JobService)
    job_service.enqueue_export = AsyncMock(
        return_value=JobStatusResponse(
            job_id="job-1",
            status=JobStatus.QUEUED,
            format=ExportFormat.MARKDOWN,
        )
    )
    async def override_job_service():
        yield job_service

    app.dependency_overrides[get_job_service] = override_job_service

    response = await client.post(
        "/api/v1/jobs/export",
        json={
            "resume": sample_resume.model_dump(mode="json"),
            "format": "markdown",
            "template_id": "minimal",
        },
    )

    app.dependency_overrides.pop(get_job_service, None)

    assert response.status_code == 202
    job_service.enqueue_export.assert_awaited_once()
    request: ExportJobRequest = job_service.enqueue_export.await_args[0][0]
    assert request.format == ExportFormat.MARKDOWN
</file>

<file path="tests/test_health.py">
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_root(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "notion-resume-api"
    assert data["docs"] == "/docs"


@pytest.mark.asyncio
async def test_list_templates(client: AsyncClient) -> None:
    response = await client.get("/api/v1/resumes/templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) == 7
    template_ids = {t["id"] for t in templates}
    assert template_ids == {
        "enhance",
        "ats-meridian",
        "minimal",
        "modern",
        "classic",
        "developer",
        "modern-canva",
    }
</file>

<file path="tests/test_notion_pipeline.py">
"""
Unit tests for Notion parser and resume mapper.

Run: pytest apps/api/tests/test_notion_pipeline.py -v
"""

import pytest

from app.services.mapper import (
    map_to_resume,
    _split_company_role,
    _extract_dates,
    _extract_tech_from_prefix,
)
from app.services.parser import parse_blocks, ContentNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_block(type_: str, text: str, children: list | None = None) -> dict:
    rich_text = [{"plain_text": text}]
    has_children = bool(children)
    block: dict = {
        "id": "fake-id",
        "type": type_,
        type_: {"rich_text": rich_text},
        "has_children": has_children,
        "children": children or [],
    }
    return block


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestParser:
    def test_heading_extraction(self):
        blocks = [make_block("heading_1", "John Doe")]
        nodes = parse_blocks(blocks)
        assert len(nodes) == 1
        assert nodes[0].type == "heading_1"
        assert nodes[0].text == "John Doe"

    def test_blank_paragraph_skipped(self):
        blocks = [make_block("paragraph", "   ")]
        nodes = parse_blocks(blocks)
        assert nodes == []

    def test_bullet_nested(self):
        child = make_block("bulleted_list_item", "Built REST API")
        parent = make_block("bulleted_list_item", "Backend", children=[child])
        nodes = parse_blocks([parent])
        assert nodes[0].type == "bullet"
        assert nodes[0].children[0].type == "sub_bullet"
        assert nodes[0].children[0].text == "Built REST API"

    def test_unsupported_block_with_children(self):
        child = make_block("paragraph", "Some content")
        unsupported = {
            "id": "x",
            "type": "embed",
            "embed": {},
            "has_children": True,
            "children": [child],
        }
        nodes = parse_blocks([unsupported])
        assert any(n.text == "Some content" for n in nodes[0].children)

    def test_empty_blocks_list(self):
        assert parse_blocks([]) == []


# ---------------------------------------------------------------------------
# Mapper tests
# ---------------------------------------------------------------------------

class TestMapper:
    def _make_nodes(self, blocks: list[dict]) -> list[ContentNode]:
        return parse_blocks(blocks)

    def test_basic_resume_structure(self):
        blocks = [
            make_block("heading_1", "Jane Smith"),
            make_block("heading_2", "Summary"),
            make_block("paragraph", "Experienced backend engineer."),
            make_block("heading_2", "Experience"),
            make_block("heading_3", "Senior Engineer — Acme Corp"),
            make_block("paragraph", "Jan 2020 – Dec 2023"),
            make_block("bulleted_list_item", "Led API redesign"),
            make_block("heading_2", "Skills"),
            make_block("heading_3", "Backend"),
            make_block("paragraph", "Python, FastAPI, PostgreSQL"),
        ]
        nodes = self._make_nodes(blocks)
        resume = map_to_resume(nodes)

        assert resume.basics.name == "Jane Smith"
        assert "backend engineer" in resume.basics.summary
        assert len(resume.experience) == 1
        assert resume.experience[0].company == "Acme Corp"
        assert resume.experience[0].role == "Senior Engineer"
        assert resume.experience[0].startDate == "Jan 2020"
        assert "Led API redesign" in resume.experience[0].highlights
        assert len(resume.skills) == 1
        assert "Python" in resume.skills[0].stack

    def test_empty_page_returns_empty_resume(self):
        resume = map_to_resume([])
        assert resume.basics.name == ""
        assert resume.experience == []
        assert resume.projects == []
        assert resume.skills == []

    def test_missing_sections_graceful(self):
        blocks = [make_block("paragraph", "Just some text.")]
        nodes = self._make_nodes(blocks)
        resume = map_to_resume(nodes)
        assert resume.experience == []

    def test_projects_parsed(self):
        blocks = [
            make_block("heading_2", "Projects"),
            make_block("heading_3", "My App"),
            make_block("paragraph", "A cool app."),
            make_block("paragraph", "Tech: React, Node.js"),
        ]
        nodes = self._make_nodes(blocks)
        resume = map_to_resume(nodes)
        assert len(resume.projects) == 1
        assert resume.projects[0].name == "My App"
        assert "React" in resume.projects[0].stack

    def test_name_from_page_meta(self):
        page_meta = {
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Meta Name"}],
                }
            }
        }
        resume = map_to_resume([], page_meta=page_meta)
        assert resume.basics.name == "Meta Name"

    def test_contact_extracted_from_raw_blocks(self):
        raw_blocks = [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"plain_text": "✉️ ", "href": None},
                        {"plain_text": "jane@example.com", "href": "mailto:jane@example.com"},
                    ]
                },
            },
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "📍 Lagos, Nigeria", "href": None}]
                },
            },
        ]
        resume = map_to_resume([], raw_blocks=raw_blocks)
        assert resume.basics.email == "jane@example.com"
        assert resume.basics.location == "Lagos, Nigeria"


# ---------------------------------------------------------------------------
# Utility tests
# ---------------------------------------------------------------------------

class TestUtilities:
    def test_split_em_dash_role_first(self):
        company, role = _split_company_role("Staff Engineer — Google")
        assert company == "Google"
        assert role == "Staff Engineer"

    def test_split_at_syntax(self):
        company, role = _split_company_role("Senior Dev at Stripe")
        assert company == "Stripe"
        assert role == "Senior Dev"

    def test_split_no_separator(self):
        company, role = _split_company_role("Just a title")
        assert company == "Just a title"
        assert role == ""

    def test_extract_dates_standard(self):
        start, end = _extract_dates("Jan 2020 – Dec 2023")
        assert start == "Jan 2020"
        assert end == "Dec 2023"

    def test_extract_dates_present(self):
        start, end = _extract_dates("Mar 2022 - Present")
        assert start == "Mar 2022"
        assert end == "Present"

    def test_extract_tech_prefix(self):
        stack = _extract_tech_from_prefix("Tech: React, Node.js, PostgreSQL")
        assert "React" in stack
        assert "Node.js" in stack

    def test_extract_tech_no_match(self):
        stack = _extract_tech_from_prefix("Led a team of 5 engineers.")
        assert stack == []
</file>

<file path="tests/test_notion_service.py">
"""
Integration tests for NotionService with a mocked Notion API client.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.schemas.resume import ResumeData
from app.services.mapper import map_to_resume
from app.services.notion_client import NotionAPIError, NotionClient
from app.services.notion_service import NotionService
from app.services.parser import parse_blocks
def _make_block(type_: str, text: str, children: list | None = None) -> dict:
    rich_text = [{"plain_text": text}]
    block: dict = {
        "id": "fake-id",
        "type": type_,
        type_: {"rich_text": rich_text},
        "has_children": bool(children),
        "children": children or [],
    }
    return block


def _sample_blocks() -> list[dict]:
    return [
        _make_block("heading_1", "Alex Dev"),
        _make_block("heading_2", "Summary"),
        _make_block("paragraph", "Full-stack developer."),
        _make_block("heading_2", "Experience"),
        _make_block("heading_3", "Engineer — StartupCo"),
        _make_block("paragraph", "Jan 2021 – Present"),
        _make_block("bulleted_list_item", "Shipped v1 product"),
    ]


@pytest.fixture
def mock_notion_client() -> AsyncMock:
    client = AsyncMock(spec=NotionClient)
    client.get_page.return_value = {
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "Alex Dev"}],
            }
        }
    }
    client.get_blocks_recursive.return_value = _sample_blocks()
    return client


@pytest.mark.asyncio
async def test_import_resume_full_pipeline(mock_notion_client: AsyncMock) -> None:
    service = NotionService(notion_client=mock_notion_client)
    resume = await service.import_resume("page-123")

    assert isinstance(resume, ResumeData)
    assert resume.basics.name == "Alex Dev"
    assert len(resume.experience) == 1
    assert resume.experience[0].company == "StartupCo"
    assert "Shipped v1 product" in resume.experience[0].highlights
    mock_notion_client.get_page.assert_awaited_once()
    mock_notion_client.get_blocks_recursive.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_empty_page_returns_empty_resume(mock_notion_client: AsyncMock) -> None:
    mock_notion_client.get_blocks_recursive.return_value = []
    service = NotionService(notion_client=mock_notion_client)

    resume = await service.import_resume("empty-page")

    assert resume.basics.name == ""
    assert resume.experience == []
    assert resume.projects == []


@pytest.mark.asyncio
async def test_page_not_found_raises(mock_notion_client: AsyncMock) -> None:
    from app.exceptions.notion import NotionPageNotFoundError

    mock_notion_client.get_page.side_effect = NotionAPIError(404, "not found")
    service = NotionService(notion_client=mock_notion_client)

    with pytest.raises(NotionPageNotFoundError):
        await service.import_resume("missing-page")


@pytest.mark.asyncio
async def test_block_fetch_failure_raises_import_error(mock_notion_client: AsyncMock) -> None:
    from app.exceptions.notion import NotionImportError

    mock_notion_client.get_blocks_recursive.side_effect = NotionAPIError(500, "server error")
    service = NotionService(notion_client=mock_notion_client)

    with pytest.raises(NotionImportError):
        await service.import_resume("page-123")


def test_normalization_pipeline_end_to_end() -> None:
    """Verify parse → map produces a valid ResumeData model."""
    blocks = _sample_blocks()
    nodes = parse_blocks(blocks)
    resume = map_to_resume(nodes)

    assert ResumeData.model_validate(resume.model_dump()) == resume
</file>

<file path="tests/test_resume_schema.py">
import json

from app.schemas.notion import NotionImportRequest, NotionImportResponse
from app.schemas.resume import Basics, Experience, ResumeData, Skill


def test_resume_data_defaults() -> None:
    resume = ResumeData()
    assert resume.basics.name == ""
    assert resume.experience == []
    assert resume.education == []
    assert resume.skills == []
    assert resume.projects == []


def test_resume_data_json_roundtrip(sample_resume: ResumeData) -> None:
    payload = sample_resume.model_dump(mode="json")
    restored = ResumeData.model_validate(payload)
    assert restored.basics.name == sample_resume.basics.name
    assert restored.experience[0].company == sample_resume.experience[0].company
    assert restored.skills[0].stack == sample_resume.skills[0].stack


def test_resume_data_serializes_to_json_string(sample_resume: ResumeData) -> None:
    raw = sample_resume.model_dump_json()
    parsed = json.loads(raw)
    assert parsed["basics"]["name"] == "Jane Smith"
    assert parsed["experience"][0]["highlights"] == ["Led API redesign"]


def test_notion_import_request_normalizes_bare_id() -> None:
    req = NotionImportRequest(page_id="a1b2c3d4e5f6789012345678abcdef01")
    assert req.page_id == "a1b2c3d4-e5f6-7890-1234-5678abcdef01"


def test_notion_import_request_normalizes_notion_url() -> None:
    req = NotionImportRequest(
        page_id="https://www.notion.so/My-Resume-a1b2c3d4e5f6789012345678abcdef01"
    )
    assert req.page_id == "a1b2c3d4-e5f6-7890-1234-5678abcdef01"


def test_notion_import_response_shape(sample_resume: ResumeData) -> None:
    response = NotionImportResponse(
        page_id="test-page",
        message="ok",
        resume=sample_resume,
    )
    data = response.model_dump(mode="json")
    assert data["page_id"] == "test-page"
    assert data["resume"]["basics"]["email"] == "jane@example.com"


def test_skill_model_accepts_named_categories() -> None:
    resume = ResumeData(skills=[Skill(name="Backend", stack=["Python"])])
    assert resume.skills[0].name == "Backend"
    assert resume.skills[0].stack == ["Python"]
</file>

<file path="tests/test_resume_service.py">
import pytest

from app.schemas.resume import ResumeData
from app.services.resume_service import ResumeService


@pytest.fixture
def resume_service() -> ResumeService:
    return ResumeService()


def test_list_templates_returns_seven(resume_service: ResumeService) -> None:
    templates = resume_service.list_templates()
    assert len(templates) == 7
    assert all(t.preview.endswith(".png") for t in templates)


def test_get_template_known(resume_service: ResumeService) -> None:
    template = resume_service.get_template("minimal")
    assert template is not None
    assert template.id == "minimal"
    assert template.name == "Minimal"


def test_get_template_unknown(resume_service: ResumeService) -> None:
    assert resume_service.get_template("nonexistent") is None  # type: ignore[arg-type]


def test_render_minimal_includes_name(resume_service: ResumeService, sample_resume: ResumeData) -> None:
    html = resume_service.render(resume=sample_resume, template_id="minimal")
    assert "Jane Smith" in html
    assert "<" in html and ">" in html


@pytest.mark.parametrize(
    "template_id",
    ["enhance", "ats-meridian", "minimal", "modern", "classic", "developer", "modern-canva"],
)
def test_render_all_registered_templates(
    resume_service: ResumeService,
    sample_resume: ResumeData,
    template_id: str,
) -> None:
    html = resume_service.render(resume=sample_resume, template_id=template_id)  # type: ignore[arg-type]
    assert len(html) > 100
    assert "Jane Smith" in html


def test_render_unknown_template_raises(resume_service: ResumeService, sample_resume: ResumeData) -> None:
    with pytest.raises(ValueError, match="not registered"):
        resume_service.render(resume=sample_resume, template_id="unknown")  # type: ignore[arg-type]
</file>

</files>
