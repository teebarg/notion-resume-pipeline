"""
Resume mapper.

Converts a flat list of ContentNodes (from parser.py) into the canonical
ResumeSchema. All resume-domain heuristics live here.

Strategy:
  1. Walk nodes top-to-bottom.
  2. A heading signals a new section context.
  3. Content under each section is accumulated and structured.

Section detection is case-insensitive and supports common variants:
  experience / work experience / work history
  projects / project / side projects
  skills / technical skills / core competencies
  summary / about / profile / objective
"""

import re
from typing import Any

from app.schemas.notion import Basics, Experience, Project, ResumeSchema
from app.services.parser import ContentNode

# ---------------------------------------------------------------------------
# Section keyword mapping
# ---------------------------------------------------------------------------

SECTION_MAP: dict[str, str] = {}

_ALIASES: dict[str, list[str]] = {
    "basics": ["about", "profile", "bio"],
    "summary": ["summary", "objective", "professional summary"],
    "experience": ["experience", "work experience", "work history", "employment"],
    "projects": ["projects", "project", "side projects", "portfolio"],
    "skills": ["skills", "technical skills", "core competencies", "technologies"],
}

for _section, _keywords in _ALIASES.items():
    for _kw in _keywords:
        SECTION_MAP[_kw.lower()] = _section


def map_to_resume(nodes: list[ContentNode], page_meta: dict[str, Any] | None = None) -> ResumeSchema:
    """
    Map a flat list of ContentNodes to a ResumeSchema.
    page_meta: optional Notion page properties dict (for name extraction).
    """
    basics = _extract_basics_from_meta(page_meta)
    sections = _segment_by_section(nodes)

    # Basics / summary section
    summary_nodes = sections.get("summary", []) + sections.get("basics", [])
    if summary_nodes:
        basics.summary = _nodes_to_text(summary_nodes)

    # Experience
    experience = _parse_experience(sections.get("experience", []))

    # Projects
    projects = _parse_projects(sections.get("projects", []))

    # Skills
    skills = _parse_skills(sections.get("skills", []))

    # If name still empty, try to pull from first h1
    if not basics.name:
        for node in nodes:
            if node.type == "heading_1" and node.text:
                basics.name = node.text
                break

    return ResumeSchema(
        basics=basics,
        experience=experience,
        projects=projects,
        skills=skills,
    )


# ---------------------------------------------------------------------------
# Section segmentation
# ---------------------------------------------------------------------------


def _segment_by_section(nodes: list[ContentNode]) -> dict[str, list[ContentNode]]:
    """
    Walk nodes and group them by the most recent section heading.
    Headings that don't match a known section are kept as "unknown".
    """
    sections: dict[str, list[ContentNode]] = {}
    current_section: str = "unknown"

    for node in nodes:
        if node.type in ("heading_1", "heading_2", "heading_3"):
            detected = _detect_section(node.text)
            if detected:
                current_section = detected
                continue  # heading itself is not content

        sections.setdefault(current_section, []).append(node)

    return sections


def _detect_section(heading_text: str) -> str | None:
    normalized = heading_text.strip().lower()
    return SECTION_MAP.get(normalized)


# ---------------------------------------------------------------------------
# Section parsers
# ---------------------------------------------------------------------------


def _parse_experience(nodes: list[ContentNode]) -> list[Experience]:
    """
    Heuristic: each h3 (or bold paragraph) starts a new experience entry.
    Bullet points under it are highlights.
    Format expected per entry heading: "Company — Role" or "Role at Company".
    Dates extracted from the heading or first paragraph: "Jan 2022 – Mar 2024".
    """
    entries: list[Experience] = []
    current: Experience | None = None

    for node in nodes:
        if node.type in ("heading_2", "heading_3"):
            if current is not None:
                entries.append(current)
            company, role = _split_company_role(node.text)
            current = Experience(company=company, role=role)

        elif node.type == "paragraph" and current is not None:
            start, end = _extract_dates(node.text)
            if start or end:
                current.startDate = start
                current.endDate = end
            # paragraph text that isn't a date range: treat as a highlight
            elif node.text and not _looks_like_date_line(node.text):
                current.highlights.append(node.text)

        elif node.type in ("bullet", "sub_bullet") and current is not None:
            flat = _flatten_bullet(node)
            current.highlights.extend(flat)

    if current is not None:
        entries.append(current)

    return entries


def _parse_projects(nodes: list[ContentNode]) -> list[Project]:
    """
    Each h3 heading = project name.
    First paragraph = description (may include "Tech: React, Node.js").
    Bullets with "Tech:" prefix are parsed as tech stack.
    """
    entries: list[Project] = []
    current: Project | None = None

    for node in nodes:
        if node.type in ("heading_2", "heading_3"):
            if current is not None:
                entries.append(current)
            current = Project(name=node.text.strip())

        elif node.type == "paragraph" and current is not None:
            tech = _extract_tech(node.text)
            if tech:
                current.tech.extend(tech)
            elif not current.description:
                current.description = node.text

        elif node.type in ("bullet", "sub_bullet") and current is not None:
            tech = _extract_tech(node.text)
            if tech:
                current.tech.extend(tech)
            else:
                # Append non-tech bullets to description
                if current.description:
                    current.description += f" {node.text}"
                else:
                    current.description = node.text

    if current is not None:
        entries.append(current)

    return entries


def _parse_skills(nodes: list[ContentNode]) -> list[str]:
    skills: list[str] = []
    for node in nodes:
        flat = _flatten_bullet(node) if node.type in ("bullet", "sub_bullet") else [node.text]
        for item in flat:
            # Split comma/pipe/semicolon-separated lists
            for skill in re.split(r"[,|;]", item):
                clean = skill.strip()
                if clean:
                    skills.append(clean)
    return skills


def _extract_basics_from_meta(page_meta: dict[str, Any] | None) -> Basics:
    if not page_meta:
        return Basics()

    name = ""
    title = ""

    props: dict[str, Any] = page_meta.get("properties", {})

    # Try common property names for person's name
    for key in ("Name", "Title", "Full Name", "name", "title"):
        prop = props.get(key, {})
        prop_type = prop.get("type")
        if prop_type == "title":
            rich = prop.get("title", [])
            name = "".join(r.get("plain_text", "") for r in rich).strip()
            break

    # Try job title from a "Title" or "Role" property
    for key in ("Role", "Job Title", "Position"):
        prop = props.get(key, {})
        if prop.get("type") == "rich_text":
            rich = prop.get("rich_text", [])
            title = "".join(r.get("plain_text", "") for r in rich).strip()
            break

    return Basics(name=name, title=title)


def _nodes_to_text(nodes: list[ContentNode]) -> str:
    parts = [node.text for node in nodes if node.text]
    return " ".join(parts)


def _flatten_bullet(node: ContentNode) -> list[str]:
    """Return the bullet text plus all nested child texts as a flat list."""
    result = [node.text] if node.text else []
    for child in node.children:
        result.extend(_flatten_bullet(child))
    return result


def _split_company_role(text: str) -> tuple[str, str]:
    """
    Parse "Company — Role", "Role at Company", "Company | Role".
    Falls back to (text, "") if no separator found.
    """
    # em-dash or double dash
    for sep in [" — ", " – ", " - ", " | "]:
        if sep in text:
            parts = text.split(sep, 1)
            return parts[0].strip(), parts[1].strip()

    # "Role at Company"
    match = re.match(r"^(.+?)\s+at\s+(.+)$", text, re.IGNORECASE)
    if match:
        return match.group(2).strip(), match.group(1).strip()

    return text.strip(), ""


_DATE_PATTERN = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4})"
    r"\s*[–\-—to]+\s*"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4}|Present|Current)",
    re.IGNORECASE,
)


def _extract_dates(text: str) -> tuple[str, str]:
    match = _DATE_PATTERN.search(text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "", ""


def _looks_like_date_line(text: str) -> bool:
    return bool(_DATE_PATTERN.search(text))


_TECH_PREFIX = re.compile(r"^(?:tech(?:nologies)?|stack|tools?|built\s+with)\s*[:\-]?\s*", re.IGNORECASE)


def _extract_tech(text: str) -> list[str]:
    """Return a list of tech items if text looks like a tech stack line."""
    cleaned = _TECH_PREFIX.sub("", text).strip()
    if cleaned != text.strip() or re.search(r"\b(React|Node|Python|FastAPI|Next\.?js|TypeScript|Postgres|Redis|Docker)\b", text):
        return [t.strip() for t in re.split(r"[,|]", cleaned) if t.strip()]
    return []