from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.common import ErrorResponse
from app.schemas.notion import NotionImportRequest, NotionImportResponse
from app.services.notion_client import NotionAPIError
import logging
 
from app.schemas.notion import NotionImportRequest, NotionImportResponse
from app.services.notion_client import NotionAPIError
from app.services.notion_service import NotionImportError, import_resume_from_notion

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/import",
    response_model=NotionImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Import and normalize a resume from a Notion page",
)
async def import_from_notion(body: NotionImportRequest) -> NotionImportResponse:
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
        # Unexpected API errors that slipped through the service layer
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