import io
import logging
from app.core.cache import set_cache_headers
from app.utils import render_error_page
from app.core.deps import get_notion_resume_service, get_pdf_service, get_resume_service
from app.services.notion_resume import NotionResumeService
from app.exceptions.notion import NotionPageNotFoundError, NotionUnauthorizedError
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from app.schemas.notion import NotionImportRequest, NotionImportResponse
from app.services.notion_client import NotionAPIError

from app.services.notion_service import NotionImportError, get_resume, import_resume_from_notion
from fastapi.responses import HTMLResponse, StreamingResponse
from app.schemas.resume import TemplateId
from app.services.resume_service import ResumeService
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)

router = APIRouter()



@router.get("/preview/{page_id}", response_class=HTMLResponse, summary="Render resume as HTML preview")
async def preview_resume(
    request: Request,
    page_id: str,
    template: TemplateId = "minimal",
    variant: str | None = Query(None, description="Color palette variant variant ID"),
    resume_service: ResumeService = Depends(get_resume_service),
) -> HTMLResponse:
    """Re-fetches (from cache) and renders the resume as an HTML page."""
    resume = await get_resume(page_id=page_id)
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
            title="Template Error",
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


# @router.post("/import-old", status_code=status.HTTP_200_OK, summary="Import and normalize a resume from a Notion page")
# @cache_response(
#     ttl=30000,
#     namespace="notion:import",
#     key_builder=lambda body, _req: f"{body.page_id}",
# )
# async def import_from_notion(body: NotionImportRequest, request: Request, service: NotionResumeService = Depends(get_notion_resume_service)) -> NotionImportResponse:
#     """
#     Fetch a Notion page, recursively parse its blocks, and return a
#     normalized resume JSON.

#     - **page_id**: Notion page ID (UUID) or full Notion page URL.
#     """
#     try:
#         resume = await import_resume_from_notion(page_id=body.page_id)
#     except NotionImportError as exc:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail=str(exc),
#         ) from exc
#     except NotionAPIError as exc:
#         logger.exception("Unexpected Notion API error for page '%s'.", body.page_id)
#         raise HTTPException(
#             status_code=status.HTTP_502_BAD_GATEWAY,
#             detail=f"Notion API returned an unexpected error: {exc}",
#         ) from exc
#     except Exception:
#         logger.exception("Unhandled error during Notion import for page '%s'.", body.page_id)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="An internal error occurred while importing the resume.",
#         )

#     return NotionImportResponse(page_id=body.page_id, message="Resume imported successfully from Notion", resume=resume)


@router.post("/import", status_code=status.HTTP_200_OK, summary="Import and normalize a resume from a Notion page")
async def get_notion_resume(
    body: NotionImportRequest,
    service: NotionResumeService = Depends(get_notion_resume_service)
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
        
    except Exception as exc:
        logger.critical("Unhandled critical system failure during import: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected system error occurred.")