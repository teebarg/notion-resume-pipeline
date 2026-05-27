from app.core.deps import get_resume_service
from fastapi import APIRouter, Depends
from typing import List
from app.schemas.resume import Template
from app.services.resume_service import ResumeService

router = APIRouter()


@router.get(
    "/templates", 
    response_model=List[Template], 
    summary="Get all available resume templates and variations"
)
async def list_templates(
    resume_service: ResumeService = Depends(get_resume_service)
) -> List[Template]:
    """
    Returns the single source of truth for all system templates.
    The UI uses this to render selection screens dynamically.
    """
    return resume_service.list_templates()
