"""
Low-level Notion API client.

Responsibilities:
- Authenticated requests via httpx
- Recursive block fetching with pagination
- Basic retry with exponential backoff on 429 / 5xx
"""

import asyncio
from typing import Any

from apps.api.app.config import settings
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)

NOTION_API_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

# Retry config
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # seconds


class NotionAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Notion API error {status_code}: {message}")


class NotionClient:
    """Async HTTP client for the Notion REST API."""

    def __init__(self):
        self._headers = {
            "Authorization": f"Bearer {settings.NOTION_API_TOKEN}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        }

    async def get_page(self, page_id: str) -> dict[str, Any]:
        normalized_id = self._normalize_page_id(page_id)
        return await self._get(f"/pages/{normalized_id}")

    async def get_blocks_recursive(self, block_id: str) -> list[dict[str, Any]]:
        """Fetch all blocks under block_id, recursively expanding children."""
        normalized_id = self._normalize_page_id(block_id)
        blocks = await self._get_all_blocks(normalized_id)
        for block in blocks:
            if block.get("has_children"):
                block["children"] = await self.get_blocks_recursive(block["id"])
            else:
                block["children"] = []
        return blocks

    async def _get_all_blocks(self, block_id: str) -> list[dict[str, Any]]:
        """Paginate through all children of a block."""
        results: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            params: dict[str, Any] = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor

            data = await self._get(f"/blocks/{block_id}/children", params=params)
            results.extend(data.get("results", []))

            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")

        return results

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{BASE_URL}{path}"
        last_exc: Exception | None = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(MAX_RETRIES):
                try:
                    response = await client.get(url, headers=self._headers, params=params)

                    if response.status_code == 429 or response.status_code >= 500:
                        wait = RETRY_BACKOFF_BASE ** attempt
                        logger.warning(
                            "Notion API returned %s, retrying in %.1fs (attempt %d/%d)",
                            response.status_code,
                            wait,
                            attempt + 1,
                            MAX_RETRIES,
                        )
                        await asyncio.sleep(wait)
                        continue

                    if not response.is_success:
                        body = response.json()
                        raise NotionAPIError(
                            response.status_code,
                            body.get("message", "unknown error"),
                        )

                    return response.json()

                except httpx.RequestError as exc:
                    last_exc = exc
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning("HTTP request error: %s, retrying in %.1fs", exc, wait)
                    await asyncio.sleep(wait)

        raise NotionAPIError(0, f"Max retries exceeded. Last error: {last_exc}")


    @staticmethod
    def _normalize_page_id(page_id: str) -> str:
        cleaned = page_id.strip().replace("-", "")
        if len(cleaned) == 32:
            return (
                f"{cleaned[:8]}-{cleaned[8:12]}-{cleaned[12:16]}-"
                f"{cleaned[16:20]}-{cleaned[20:]}"
            )
        return page_id.strip()
