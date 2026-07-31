"""
Unit tests for Notion parser and resume mapper.

Run: pytest api/tests/test_notion_pipeline.py -v
"""

import pytest

from app.services.mapper import (
    map_to_resume,
    _split_company_role,
    _extract_dates,
    _extract_tech_from_prefix,
)
from app.services.parser import parse_blocks, ContentNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_block(type_: str, text: str, children: list | None = None) -> dict:
    rich_text = [{"plain_text": text}]
    has_children = bool(children)
    block: dict = {
        "id": "fake-id",
        "type": type_,
        type_: {"rich_text": rich_text},
        "has_children": has_children,
        "children": children or [],
    }
    return block


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestParser:
    def test_heading_extraction(self):
        blocks = [make_block("heading_1", "John Doe")]
        nodes = parse_blocks(blocks)
        assert len(nodes) == 1
        assert nodes[0].type == "heading_1"
        assert nodes[0].text == "John Doe"

    def test_blank_paragraph_skipped(self):
        blocks = [make_block("paragraph", "   ")]
        nodes = parse_blocks(blocks)
        assert nodes == []

    def test_bullet_nested(self):
        child = make_block("bulleted_list_item", "Built REST API")
        parent = make_block("bulleted_list_item", "Backend", children=[child])
        nodes = parse_blocks([parent])
        assert nodes[0].type == "bullet"
        assert nodes[0].children[0].type == "sub_bullet"
        assert nodes[0].children[0].text == "Built REST API"

    def test_unsupported_block_with_children(self):
        child = make_block("paragraph", "Some content")
        unsupported = {
            "id": "x",
            "type": "embed",
            "embed": {},
            "has_children": True,
            "children": [child],
        }
        nodes = parse_blocks([unsupported])
        assert any(n.text == "Some content" for n in nodes[0].children)

    def test_empty_blocks_list(self):
        assert parse_blocks([]) == []


# ---------------------------------------------------------------------------
# Mapper tests
# ---------------------------------------------------------------------------

class TestMapper:
    def _make_nodes(self, blocks: list[dict]) -> list[ContentNode]:
        return parse_blocks(blocks)

    def test_basic_resume_structure(self):
        blocks = [
            make_block("heading_1", "Jane Smith"),
            make_block("heading_2", "Summary"),
            make_block("paragraph", "Experienced backend engineer."),
            make_block("heading_2", "Experience"),
            make_block("heading_3", "Senior Engineer — Acme Corp"),
            make_block("paragraph", "Jan 2020 – Dec 2023"),
            make_block("bulleted_list_item", "Led API redesign"),
            make_block("heading_2", "Skills"),
            make_block("heading_3", "Backend"),
            make_block("paragraph", "Python, FastAPI, PostgreSQL"),
        ]
        nodes = self._make_nodes(blocks)
        resume = map_to_resume(nodes)

        assert resume.basics.name == "Jane Smith"
        assert "backend engineer" in resume.basics.summary
        assert len(resume.experience) == 1
        assert resume.experience[0].company == "Acme Corp"
        assert resume.experience[0].role == "Senior Engineer"
        assert resume.experience[0].startDate == "Jan 2020"
        assert "Led API redesign" in resume.experience[0].highlights
        assert len(resume.skills) == 1
        assert "Python" in resume.skills[0].stack

    def test_empty_page_returns_empty_resume(self):
        resume = map_to_resume([])
        assert resume.basics.name == ""
        assert resume.experience == []
        assert resume.projects == []
        assert resume.skills == []

    def test_missing_sections_graceful(self):
        blocks = [make_block("paragraph", "Just some text.")]
        nodes = self._make_nodes(blocks)
        resume = map_to_resume(nodes)
        assert resume.experience == []

    def test_projects_parsed(self):
        blocks = [
            make_block("heading_2", "Projects"),
            make_block("heading_3", "My App"),
            make_block("paragraph", "A cool app."),
            make_block("paragraph", "Tech: React, Node.js"),
        ]
        nodes = self._make_nodes(blocks)
        resume = map_to_resume(nodes)
        assert len(resume.projects) == 1
        assert resume.projects[0].name == "My App"
        assert "React" in resume.projects[0].stack

    def test_name_from_page_meta(self):
        page_meta = {
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Meta Name"}],
                }
            }
        }
        resume = map_to_resume([], page_meta=page_meta)
        assert resume.basics.name == "Meta Name"

    def test_contact_extracted_from_raw_blocks(self):
        raw_blocks = [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"plain_text": "✉️ ", "href": None},
                        {"plain_text": "jane@example.com", "href": "mailto:jane@example.com"},
                    ]
                },
            },
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "📍 Lagos, Nigeria", "href": None}]
                },
            },
        ]
        resume = map_to_resume([], raw_blocks=raw_blocks)
        assert resume.basics.email == "jane@example.com"
        assert resume.basics.location == "Lagos, Nigeria"


# ---------------------------------------------------------------------------
# Utility tests
# ---------------------------------------------------------------------------

class TestUtilities:
    def test_split_em_dash_role_first(self):
        company, role = _split_company_role("Staff Engineer — Google")
        assert company == "Google"
        assert role == "Staff Engineer"

    def test_split_at_syntax(self):
        company, role = _split_company_role("Senior Dev at Stripe")
        assert company == "Stripe"
        assert role == "Senior Dev"

    def test_split_no_separator(self):
        company, role = _split_company_role("Just a title")
        assert company == "Just a title"
        assert role == ""

    def test_extract_dates_standard(self):
        start, end = _extract_dates("Jan 2020 – Dec 2023")
        assert start == "Jan 2020"
        assert end == "Dec 2023"

    def test_extract_dates_present(self):
        start, end = _extract_dates("Mar 2022 - Present")
        assert start == "Mar 2022"
        assert end == "Present"

    def test_extract_tech_prefix(self):
        stack = _extract_tech_from_prefix("Tech: React, Node.js, PostgreSQL")
        assert "React" in stack
        assert "Node.js" in stack

    def test_extract_tech_no_match(self):
        stack = _extract_tech_from_prefix("Led a team of 5 engineers.")
        assert stack == []
