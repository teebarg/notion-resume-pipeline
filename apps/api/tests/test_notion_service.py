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
