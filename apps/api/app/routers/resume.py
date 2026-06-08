from typing import List
from fastapi import APIRouter, Depends, Request
from app.schemas.resume import StoragePdfSyncRequest, Template
from app.services.pdf_service import PDFService
from app.services.resume_service import ResumeService
from app.core.deps import get_pdf_service, get_share_service, get_resume_service
from app.schemas.share import ShareSettings
from app.services.share_service import ShareService
from app.schemas.notion import NotionImportRequest, NotionImportResponse

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


@router.post("/activate", response_model=ShareSettings)
async def activate_sharing(
    request: Request,
    body: NotionImportRequest,
    share_service: ShareService = Depends(get_share_service)
) -> ShareSettings:
    """
    Generates or activates a public shareable link for a specific Notion Page ID.
    """
    base_url = str(request.base_url) 
    return await share_service.generate_share_link(page_id=body.page_id, base_url=base_url)


@router.post("/revoke", response_model=ShareSettings)
async def revoke_sharing(
    body: NotionImportRequest,
    share_service: ShareService = Depends(get_share_service)
) -> ShareSettings:
    """
    Instantly deletes the public slug from Redis for this Notion Page ID, 
    breaking the link.
    """
    return await share_service.revoke_share_link(page_id=body.page_id)


@router.post("/sync-pdf")
async def update_storage_pdf(
    body: StoragePdfSyncRequest,
    pdf_service: PDFService = Depends(get_pdf_service)
):
    new_public_url = await pdf_service.sync_pdf_pipeline(body.page_id, body.template, body.variant)
    
    return {"status": "updated", "public_pdf_url": new_public_url}
