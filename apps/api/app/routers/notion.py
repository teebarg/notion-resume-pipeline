from app.core.cache import cache_response
from fastapi import APIRouter, Depends, HTTPException, status, Request

from app.schemas.common import ErrorResponse
from app.schemas.notion import NotionImportRequest, NotionImportResponse
from app.services.notion_client import NotionAPIError
import logging

from app.services.notion_service import NotionImportError, import_resume_from_notion
from fastapi.responses import HTMLResponse, StreamingResponse
import io
from app.schemas.resume import TemplateId
from app.services.resume_service import render_resume_html
from app.services.pdf_service import html_to_pdf

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/preview/{page_id}",
    response_class=HTMLResponse,
    summary="Render resume as HTML preview",
)
async def preview_resume(
    page_id: str,
    template: TemplateId = "minimal",
) -> HTMLResponse:
    """Re-fetches (from cache) and renders the resume as an HTML page."""
    try:
        resume = await import_resume_from_notion(page_id=page_id)
    except (NotionImportError, NotionAPIError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    html = render_resume_html(resume, template_id=template)
    return HTMLResponse(content=html)


@router.get(
    "/pdf/{page_id}",
    summary="Export resume as PDF",
)
async def export_pdf(
    page_id: str,
    template: TemplateId = "minimal",
):
    """Renders the resume HTML and converts it to a downloadable PDF."""
    try:
        resume = await import_resume_from_notion(page_id=page_id)
    except (NotionImportError, NotionAPIError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    html = render_resume_html(resume, template_id=template)
    pdf_bytes = await html_to_pdf(html)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=resume-{page_id}.pdf"},
    )


@router.get(
    "/templates",
    summary="List available CV templates",
)
async def list_templates():
    """Returns all available template options."""
    from app.schemas.resume import Template
    return [
        Template(id="minimal", name="Minimal", description="Clean single-column layout", preview="/static/previews/minimal.png"),
        Template(id="modern",  name="Modern",  description="Two-column with sidebar",    preview="/static/previews/modern.png"),
        Template(id="classic", name="Classic", description="Traditional chronological",  preview="/static/previews/classic.png"),
        Template(id="developer", name="Developer", description="Tech-focused with skills front and centre", preview="/static/previews/developer.png"),
    ]


@router.post(
    "/import",
    status_code=status.HTTP_200_OK,
    summary="Import and normalize a resume from a Notion page",
)
@cache_response(
    ttl=30000,
    namespace="notion:import",
    key_builder=lambda body, _req: f"{body.page_id}",
)
async def import_from_notion(body: NotionImportRequest, request: Request) -> NotionImportResponse:
    """
    Fetch a Notion page, recursively parse its blocks, and return a
    normalized resume JSON.

    - **page_id**: Notion page ID (UUID) or full Notion page URL.
    """
    try:
        resume = await import_resume_from_notion(page_id=body.page_id)
    except NotionImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except NotionAPIError as exc:
        logger.exception("Unexpected Notion API error for page '%s'.", body.page_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Notion API returned an unexpected error: {exc}",
        ) from exc
    except Exception:
        logger.exception("Unhandled error during Notion import for page '%s'.", body.page_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while importing the resume.",
        )

    return NotionImportResponse(page_id=body.page_id, message="Resume imported successfully from Notion", resume=resume)