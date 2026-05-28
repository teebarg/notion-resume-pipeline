# app/services/notion_resume.py
import json
from typing import Any
from app.core.logging import get_logger
from app.schemas.resume import ResumeData
from app.services.notion_client import NotionAPIError, NotionClient
from app.services.mapper import map_to_resume
from app.services.parser import parse_blocks
from app.core.cache import redis_cache
from app.exceptions.notion import NotionImportError, NotionPageNotFoundError, NotionUnauthorizedError

logger = get_logger(__name__)

class NotionResumeService:
    def __init__(self, notion_client: NotionClient):
        # Injecting the client allows us to mock network behavior in tests effortlessly
        self.notion_client = notion_client

    async def import_resume(self, page_id: str) -> ResumeData:
        """
        Executes the pure data pipeline to fetch and process a Notion resume.
        Throws domain-specific exceptions.
        """
        page_meta = await self._fetch_page_metadata(page_id)
        raw_blocks = await self._fetch_blocks_recursive(page_id)

        if not raw_blocks:
            logger.info("Notion page '%s' returned no blocks; returning empty resume.", page_id)
            return ResumeData()

        # Parse nodes and build domain object
        nodes = parse_blocks(raw_blocks)
        logger.debug(f"[nodes]: {json.dumps(nodes, indent=2, default=str)}")
        
        resume = map_to_resume(nodes, page_meta=page_meta, raw_blocks=raw_blocks)
        
        logger.info(
            "Successfully compiled resume from Notion page '%s': %d experiences, %d projects.",
            page_id, len(resume.experience), len(resume.projects)
        )
        return resume

    async def _fetch_page_metadata(self, page_id: str) -> dict[str, Any] | None:
        try:
            return await self.notion_client.get_page(page_id)
        except NotionAPIError as exc:
            if exc.status_code == 404:
                raise NotionPageNotFoundError(f"Notion page '{page_id}' not found or access denied.") from exc
            if exc.status_code == 401:
                raise NotionUnauthorizedError("Invalid or expired Notion integration token.") from exc
            
            logger.warning("Could not fetch page meta (status %s); continuing without it.", exc.status_code)
            return None

    async def _fetch_blocks_recursive(self, page_id: str) -> list[dict[str, Any]]:
        try:
            return await self.notion_client.get_blocks_recursive(page_id)
        except NotionAPIError as exc:
            logger.error("Failed executing recursive block fetch for page '%s'.", page_id)
            raise NotionImportError(f"Failed to fetch blocks from Notion: {exc}") from exc

    # Apply caching cleanly at the service boundary 
    # @redis_cache(ttl=30000, namespace="notion-service", key_builder=lambda self, page_id: page_id)
    @redis_cache(
        ttl=30000, 
        namespace="srv:notion", 
        key_builder=lambda ctx: ctx["page_id"],
        tags=lambda ctx: [f"page:{ctx['page_id']}"]
    )
    async def get_cached_resume(self, page_id: str) -> ResumeData:
        """Cached read access proxy wrapper for the main import pipeline."""
        return await self.import_resume(page_id)