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
from app.schemas.resume import ResumeData, TemplateId
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
