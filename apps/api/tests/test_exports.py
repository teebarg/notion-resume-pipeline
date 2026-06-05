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
