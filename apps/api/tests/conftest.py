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
