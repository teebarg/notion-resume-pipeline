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
from playwright.async_api import async_playwright

logger = get_logger(__name__)

state = {}

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    await init_redis()

    state["playwright"] = await async_playwright().start()
    state["browser"] = await state["playwright"].chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",  # Force Chromium to use system memory instead of /dev/shm
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",            # Save RAM by disabling GPU emulation
            "--no-first-run",
            "--no-zygote",
            "--single-process"          # Reduce multi-process overhead (saves ~100MB RAM)
        ]
    )

    yield

    await state["browser"].close()
    await state["playwright"].stop()

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
