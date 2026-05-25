import json
from app.core.logging import get_logger
from app.schemas.resume import ResumeData
from app.services.notion_client import NotionAPIError, NotionClient
from typing import Any
 
from app.services.mapper import map_to_resume
from app.services.parser import parse_blocks

logger = get_logger(__name__)
 
 
class NotionImportError(Exception):
    """Raised when Notion import fails for a known reason."""
 
 
async def import_resume_from_notion(page_id: str) -> ResumeData:
    """
    Full pipeline:
      1. Authenticate + fetch Notion page metadata.
      2. Recursively fetch all blocks.
      3. Parse blocks into ContentNodes.
      4. Map ContentNodes into ResumeData.
    """
    client = NotionClient()
 
    # Fetch page meta (for name/title extraction from page properties)
    page_meta: dict[str, Any] | None = None
    try:
        page_meta = await client.get_page(page_id)
    except NotionAPIError as exc:
        if exc.status_code == 404:
            raise NotionImportError(
                f"Notion page '{page_id}' not found. "
                "Check the page ID and ensure the integration has access."
            ) from exc
        if exc.status_code == 401:
            raise NotionImportError(
                "Invalid or expired Notion token."
            ) from exc
        logger.warning("Could not fetch page meta (status %s); continuing without it.", exc.status_code)
 
    # Fetch blocks recursively
    try:
        raw_blocks = await client.get_blocks_recursive(page_id)
    except NotionAPIError as exc:
        raise NotionImportError(
            f"Failed to fetch blocks for page '{page_id}': {exc}"
        ) from exc
 
    if not raw_blocks:
        logger.info("Notion page '%s' returned no blocks; returning empty resume.", page_id)
        return ResumeData()
 
    # Parse + map
    nodes = parse_blocks(raw_blocks)
    logger.debug(f"[nodes]------------------------------------------: {json.dumps(nodes, indent=2, default=str)}")
    resume = map_to_resume(nodes, page_meta=page_meta, raw_blocks=raw_blocks)
 
    logger.info(
        "Imported resume from Notion page '%s': %d experience(s), %d project(s), %d skill(s).",
        page_id,
        len(resume.experience),
        len(resume.projects),
        len(resume.skills),
    )
 
    return resume
