"""
Notion block parser.

Converts raw Notion block JSON into a flat, typed intermediate representation.

Output node types:
  heading_1 | heading_2 | heading_3 | heading_4 | paragraph | bullet | sub_bullet | toggle | quote | callout
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContentNode:
    type: str          # heading_1 | heading_2 | heading_3 | heading_4 | paragraph | bullet | sub_bullet | toggle | quote | callout
    text: str
    depth: int = 0     # nesting depth (0 = top-level, 1 = child bullet, etc.)
    children: list["ContentNode"] = field(default_factory=list)


def parse_blocks(blocks: list[dict[str, Any]]) -> list[ContentNode]:
    """Entry point: parse a list of top-level Notion blocks."""
    return _parse_block_list(blocks, depth=0)


def _parse_block_list(blocks: list[dict[str, Any]], depth: int) -> list[ContentNode]:
    nodes: list[ContentNode] = []
    for block in blocks:
        node = _parse_block(block, depth)
        if node is not None:
            nodes.append(node)
    return nodes


def _parse_block(block: dict[str, Any], depth: int) -> ContentNode | None:
    block_type: str = block.get("type", "")
    children_blocks: list[dict[str, Any]] = block.get("children", [])

    match block_type:
        case "heading_1":
            text = _extract_text(block, "heading_1")
            node = ContentNode(type="heading_1", text=text, depth=depth)
        case "heading_2":
            text = _extract_text(block, "heading_2")
            node = ContentNode(type="heading_2", text=text, depth=depth)
        case "heading_3":
            text = _extract_text(block, "heading_3")
            node = ContentNode(type="heading_3", text=text, depth=depth)
        case "heading_4":
            text = _extract_text(block, "heading_4")
            node = ContentNode(type="heading_4", text=text, depth=depth)
        case "toggle":
            text = _extract_text(block, "toggle")
            node = ContentNode(type="toggle", text=text, depth=depth)
        case "quote":
            text = _extract_text(block, "quote")
            node = ContentNode(type="quote", text=text, depth=depth)
        case "callout":
            text = _extract_text(block, "callout")
            node = ContentNode(type="callout", text=text, depth=depth)
        case "paragraph":
            text = _extract_text(block, "paragraph")
            if not text.strip():
                return None  # skip blank paragraphs
            node = ContentNode(type="paragraph", text=text, depth=depth)
        case "bulleted_list_item":
            text = _extract_text(block, "bulleted_list_item")
            node_type = "sub_bullet" if depth > 0 else "bullet"
            node = ContentNode(type=node_type, text=text, depth=depth)
        case "numbered_list_item":
            text = _extract_text(block, "numbered_list_item")
            node_type = "sub_bullet" if depth > 0 else "bullet"
            node = ContentNode(type=node_type, text=text, depth=depth)
        case "toggle" | "quote" | "callout":
            # Treat these as paragraphs — extract text and recurse into children
            text = _extract_text(block, block_type)
            node = ContentNode(type="paragraph", text=text, depth=depth)
        case _:
            # Unsupported block type: still recurse into children if present
            if children_blocks:
                node = ContentNode(type="paragraph", text="", depth=depth)
            else:
                return None

    # Recurse into nested children
    if children_blocks:
        node.children = _parse_block_list(children_blocks, depth=depth + 1)

    return node


def _extract_text(block: dict[str, Any], block_type: str) -> str:
    """Extract plain text from a block's rich_text array."""
    type_data: dict[str, Any] = block.get(block_type, {})
    rich_text: list[dict[str, Any]] = type_data.get("rich_text", [])
    return "".join(rt.get("plain_text", "") for rt in rich_text).strip()