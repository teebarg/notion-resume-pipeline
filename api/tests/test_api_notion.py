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
