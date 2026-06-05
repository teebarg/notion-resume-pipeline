from app.core.deps import get_resume_service
from app.schemas.notion import NotionImportResponse
from fastapi import APIRouter, Depends
from typing import List
from app.schemas.resume import Template
from app.services.resume_service import ResumeService

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
