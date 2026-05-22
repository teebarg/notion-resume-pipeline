from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.core.logging import close_http_client, get_logger, setup_logging
from app.core.redis import close_redis, init_redis
from app.routers import api_router

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
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)

@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": __version__,
        "docs": "/docs",
    }
