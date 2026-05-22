from typing import Any
from uuid import uuid4

from app.schemas.resume import ResumeData


def _plain_text(rich_text: list[dict[str, Any]]) -> str:
    return "".join(segment.get("plain_text", "") for segment in rich_text).strip()


def _extract_title(properties: dict[str, Any]) -> str:
    for prop in properties.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            return _plain_text(title_parts)
    return ""


class NotionNormalizer:
    """Maps Notion page metadata and blocks into canonical ResumeData."""

    def normalize_page(self, page: dict[str, Any], blocks: list[dict[str, Any]]) -> ResumeData:
        properties = page.get("properties", {})
        title = _extract_title(properties)

        summary_parts: list[str] = []
        skills: list[str] = []

        for block in blocks:
            block_type = block.get("type")
            if block_type == "paragraph":
                text = _plain_text(block.get("paragraph", {}).get("rich_text", []))
                if text:
                    summary_parts.append(text)
            elif block_type == "bulleted_list_item":
                text = _plain_text(
                    block.get("bulleted_list_item", {}).get("rich_text", [])
                )
                if text:
                    skills.append(text)

        return ResumeData(
            name=title or "Imported from Notion",
            title="",
            summary="\n".join(summary_parts)
            or "Resume imported from Notion. Extend the normalizer for structured sections.",
            skills=skills,
        )


def new_id() -> str:
    return str(uuid4())
