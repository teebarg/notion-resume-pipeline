from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from app.core.deps import get_share_service
from app.services.share_service import ShareService

router = APIRouter()

@router.get("/{slug}", response_class=HTMLResponse, summary="View a shared resume publicly")
async def view_public_resume(
    slug: str,
    share_service: ShareService = Depends(get_share_service)
) -> HTMLResponse:
    """
    Publicly accessible endpoint that renders a user's resume completely server-side 
    using their pre-configured Notion template settings.
    """
    resume_data, template_id, variant_id = await share_service.get_resume_by_slug(slug)
    
    html_content = share_service.resume_service.render(
        resume=resume_data, 
        template_id=template_id, 
        variant_id=variant_id
    )
    
    return HTMLResponse(content=html_content)