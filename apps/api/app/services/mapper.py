"""
Resume mapper.
 
Strategy:
  1. Walk nodes top-to-bottom.
  2. A heading_1 or heading_2 signals a new top-level section context.
  3. heading_3 signals a sub-item (job, project, education entry) within a section.
  4. Content under each section is accumulated and structured.
 
Section detection is case-insensitive and handles real-world Notion heading variants.
"""

import json
import re
from typing import Any

from app.schemas.resume import Basics, Education, Experience, Project, ResumeData, Skill
from app.services.parser import ContentNode
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Section keyword mapping
# Only heading_1 and heading_2 trigger section changes.
# heading_3 always means "new sub-item within current section".
# ---------------------------------------------------------------------------
 
_SECTION_ALIASES: dict[str, list[str]] = {
    "summary": [
        "summary", "professional summary", "about", "profile",
        "objective", "professional profile",
    ],
    "experience": [
        "experience", "work experience", "work history", "employment",
        "professional experience",
    ],
    "projects": [
        "projects", "project", "side projects", "portfolio",
        "selected projects", "open source",
    ],
    "skills": [
        "skills", "technical skills", "core competencies",
        "technologies", "tech stack",
    ],
    "education": [
        "education", "academic background", "qualifications",
    ],
    "availability": [
        "availability",
    ],
}
 
# Flat lookup: normalized heading text → canonical section key
SECTION_MAP: dict[str, str] = {
    kw.lower(): section
    for section, keywords in _SECTION_ALIASES.items()
    for kw in keywords
}
 
 
# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def map_to_resume(nodes: list[ContentNode], page_meta: dict[str, Any] | None = None, raw_blocks: list[dict[str, Any]] | None = None,) -> ResumeData:
    basics = _extract_basics_from_meta(page_meta)
    sections = _segment_by_section(nodes)
    logger.debug(f"[map_to_resume sections]------------------------------------------: {json.dumps(sections, indent=2, default=str)}")

    # Extract contact fields from raw blocks (hrefs not available in ContentNodes)
    if raw_blocks:
        contact = _extract_contact_from_raw_blocks(raw_blocks)
        basics.title = contact.get("title", "")
        basics.email = contact.get("email", "")
        basics.location = contact.get("location", "")
        basics.website = contact.get("website", "")
        basics.linkedin = contact.get("linkedin", "")
        basics.github = contact.get("github", "")
        basics.phone = contact.get("phone", "")
 
    # Summary
    summary_nodes = sections.get("summary", [])
    if summary_nodes:
        basics.summary = _nodes_to_text(summary_nodes)
 
    experience = _parse_experience(sections.get("experience", []))
    projects = _parse_projects(sections.get("projects", []))
    education = _parse_education(sections.get("education", []))
    skills = _parse_skills(sections.get("skills", []))
 
    # Fallback: name from first h1 if page meta didn't provide it
    if not basics.name:
        for node in nodes:
            if node.type == "heading_1" and node.text:
                basics.name = node.text
                break
 
    return ResumeData(
        basics=basics,
        experience=experience,
        projects=projects,
        education=education,
        skills=skills,
    )
 
# ---------------------------------------------------------------------------
# Section segmentation
# ---------------------------------------------------------------------------
def _segment_by_section(nodes: list[ContentNode]) -> dict[str, list[ContentNode]]:
    """
    Walk nodes and group by the nearest heading_1 / heading_2 section.
    heading_3 is treated as content (sub-item marker), not a section boundary.
    """
    sections: dict[str, list[ContentNode]] = {}
    current_section: str = "unknown"
 
    for node in nodes:
        # Only h1/h2 can change the active section
        if node.type in ("heading_1", "heading_2"):
            detected = SECTION_MAP.get(node.text.strip().lower())
            if detected:
                current_section = detected
                continue  # heading itself is not content
            else:
                # Unrecognized h1/h2: treat as unknown, keep accumulating there
                current_section = "unknown"
                continue
 
        # heading_3 is passed through as content for the section parsers to handle
        sections.setdefault(current_section, []).append(node)
 
    return sections
 
 
# ---------------------------------------------------------------------------
# Section parsers
# ---------------------------------------------------------------------------
def _parse_experience(nodes: list[ContentNode]) -> list[Experience]:
    """
    heading_3 = new job entry (format: "Role — Company" or "Company — Role").
    Paragraph immediately after = date range.
    Bullet points = highlights.
    Inline code paragraphs (tech stack lines) are skipped.
    """
    entries: list[Experience] = []
    current: Experience | None = None
 
    for node in nodes:
        if node.type == "heading_3":
            if current is not None:
                entries.append(current)
            company, role = _split_company_role(node.text)
            current = Experience(company=company, role=role)
 
        elif node.type == "paragraph" and current is not None:
            # Skip tech-stack inline-code lines (e.g. "Python · FastAPI · ...")
            if _is_tech_stack_line(node.text):
                continue
            start, end = _extract_dates(node.text)
            if start or end:
                current.startDate = start
                current.endDate = end
            elif node.text and not _looks_like_date_line(node.text):
                current.highlights.append(node.text)
 
        elif node.type in ("bullet", "sub_bullet") and current is not None:
            flat = _flatten_bullet(node)
            current.highlights.extend(flat)

        elif node.type == "quote":
            skills = _parse_bullet_skills(node.text)
            current.techs.extend(skills)
 
    if current is not None:
        entries.append(current)
 
    return entries
 
 
def _parse_projects(nodes: list[ContentNode]) -> list[Project]:
    """
    heading_3 = project name.
    First non-tech paragraph = description.
    Tech stack extracted from bullet/paragraph starting with "Tech:" or matching known frameworks.
    """
    entries: list[Project] = []
    current: Project | None = None
 
    for node in nodes:
        if node.type == "heading_3":
            if current is not None:
                entries.append(current)
            current = Project(name=node.text.strip())
 
        elif node.type == "paragraph" and current is not None:
            if _is_tech_stack_line(node.text):
                continue  # skip inline-code stack lines
            tech = _extract_tech_from_prefix(node.text)
            if tech:
                current.tech.extend(tech)
            elif not current.description:
                current.description = node.text
 
        elif node.type in ("bullet", "sub_bullet") and current is not None:
            current.highlights.append(node.text)
 
    if current is not None:
        entries.append(current)
 
    return entries
 
 
def _parse_education(nodes: list[ContentNode]) -> list[Education]:
    """
    Education in this Notion page uses plain paragraphs (no h3 per entry).
    Heuristic: bold paragraphs = degree line; italic paragraphs = institution;
    paragraphs matching date pattern = date range.
 
    Groups entries by pairing: degree → institution → dates.
    """
    entries: list[Education] = []
    current: Education | None = None
 
    for node in nodes:
        if node.type == "heading_3":
            # Some resumes use h3 per entry
            if current is not None:
                entries.append(current)
            current = Education(degree=node.text.strip())
            continue
 
        if node.type != "paragraph" or not node.text:
            continue
 
        text = node.text.strip()
 
        # Date line — attach to current entry or start fresh
        start, end = _extract_dates(text)
        if start or end:
            if current is None:
                current = Education()
            current.startDate = start
            current.endDate = end
            entries.append(current)
            current = None
            continue
 
        # Looks like a degree (B.Sc., HND, M.Sc., B.Eng., etc.)
        if _looks_like_degree(text):
            if current is not None and current.degree:
                # Flush the previous incomplete entry before starting a new one
                entries.append(current)
            current = Education(degree=text)
            continue
 
        # Otherwise treat as institution name
        if current is not None and not current.institution:
            current.institution = text
 
    # Flush any trailing entry
    if current is not None and (current.degree or current.institution):
        entries.append(current)
 
    return entries
 
 
def _parse_skills(nodes: list[ContentNode]) -> list[str]:
    """
    Skills section uses h3 sub-headings (Backend, Frontend, etc.) followed by
    comma-separated paragraphs. We collect all text from paragraphs and bullets,
    ignoring the sub-headings themselves, and split on commas/pipes/middle-dots.
    """
    skills: list[Skill] = []
    current: Skill | None = None
    for node in nodes:
        if node.type == "heading_3":
            # Sub-category labels (Backend, Frontend…) — skip, they're not skills
            if current is not None:
                skills.append(current)
            current = Skill(name=node.text.strip())
            continue
        if node.type in ("bullet", "sub_bullet"):
            items = _flatten_bullet(node)
        else:
            items = _split_tech_stack(text=node.text)
        if current is not None:
            current.stack = items

    if current is not None:
        skills.append(current)

    return skills
 
 
# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def _split_tech_stack(text: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r',(?![^(]*\))', text)
        if item.strip()
    ]
 
 
def _extract_basics_from_meta(page_meta: dict[str, Any] | None) -> Basics:
    if not page_meta:
        return Basics()
 
    name = ""
    props: dict[str, Any] = page_meta.get("properties", {})
 
    for key in ("Name", "Title", "Full Name", "name", "title"):
        prop = props.get(key, {})
        if prop.get("type") == "title":
            rich = prop.get("title", [])
            name = "".join(r.get("plain_text", "") for r in rich).strip()
            if name:
                break
 
    return Basics(name=name)


def _extract_contact_from_raw_blocks(raw_blocks: list[dict[str, Any]]) -> dict[str, str]:
    """
    Extract contact fields from the raw pre-section Notion blocks.
 
    We use raw blocks (not ContentNodes) here because hrefs live in rich_text
    entries which the parser intentionally discards — only plain_text is kept.
 
    Handles the real patterns from the resume:
      paragraph → plain "Senior Software Engineer / ..."            → title
      paragraph → "📍 Lagos, Nigeria · Remote-friendly"            → location
      paragraph → "✉️ " + linked "teebarg01@gmail.com"             → email
      paragraph → "🌐 " + linked "Portfolio" (href: niyi.com.ng)   → website
      paragraph → "🔗 " + linked "LinkedIn" (href: linkedin.com)   → linkedin
      paragraph → "🔗 " + linked "Github"   (href: github.com)     → github
      paragraph → "🔗  +2348060001234"                             → phone
    """
    fields: dict[str, str] = {}
 
    for block in raw_blocks:
        if block.get("type") != "paragraph":
            continue
 
        rich_text: list[dict[str, Any]] = block.get("paragraph", {}).get("rich_text", [])
        if not rich_text:
            continue
 
        plain = "".join(rt.get("plain_text", "") for rt in rich_text).strip()
        if not plain:
            continue
 
        # Collect all hrefs present in this block's rich_text
        hrefs = [
            rt["href"]
            for rt in rich_text
            if rt.get("href")
        ]
 
        # Location
        if plain.startswith("📍"):
            fields.setdefault("location", plain.lstrip("📍").strip())
            continue

        # Phone
        if plain.startswith("📞"):
            fields.setdefault("phone", plain.lstrip("📞").strip())
            continue
 
        # Email — prefer href (mailto:), fall back to regex on plain text
        if "✉️" in plain or any("mailto:" in (h or "") for h in hrefs):
            mailto = next((h for h in hrefs if h and h.startswith("mailto:")), None)
            if mailto:
                fields.setdefault("email", mailto.replace("mailto:", "").strip())
            else:
                m = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", plain)
                if m:
                    fields.setdefault("email", m.group(0))
            continue
 
        # LinkedIn — check hrefs first
        linkedin_href = next((h for h in hrefs if h and "linkedin.com" in h), None)
        if linkedin_href:
            fields.setdefault("linkedin", linkedin_href)
            continue
 
        # GitHub — check hrefs first
        github_href = next((h for h in hrefs if h and "github.com" in h), None)
        if github_href:
            fields.setdefault("github", github_href)
            continue
 
        # Website / Portfolio — any remaining href that isn't a known service
        website_href = next(
            (h for h in hrefs if h and not any(s in h for s in ("linkedin", "github", "mailto"))),
            None,
        )
        if website_href and ("🌐" in plain or "portfolio" in plain.lower()):
            fields.setdefault("website", website_href)
            continue
 
        # Job title: first paragraph that isn't contact info
        if not _looks_like_contact(plain) and "title" not in fields:
            fields["title"] = plain
 
    return fields
 
 
def _nodes_to_text(nodes: list[ContentNode]) -> str:
    parts = [node.text for node in nodes if node.text and node.type not in ("heading_3",)]
    return " ".join(parts)
 
 
def _flatten_bullet(node: ContentNode) -> list[str]:
    result = [node.text] if node.text else []
    for child in node.children:
        result.extend(_flatten_bullet(child))
    return result
 
 
def _split_company_role(text: str) -> tuple[str, str]:
    """
    Parse "Role — Company" or "Company — Role" or "Role at Company".
    Real data: "Lead Engineer — Revoque", "Software Engineer — Bolster Networks, Inc."
    Convention in this resume: Role — Company (role comes first).
    """
    for sep in [" — ", " – ", " - ", " | "]:
        if sep in text:
            parts = text.split(sep, 1)
            # Role — Company convention
            return parts[1].strip(), parts[0].strip()
 
    match = re.match(r"^(.+?)\s+at\s+(.+)$", text, re.IGNORECASE)
    if match:
        return match.group(2).strip(), match.group(1).strip()
 
    return text.strip(), ""

def _parse_bullet_skills(skills: str) -> list[str]:
    return [
        skill.strip()
        for skill in re.split(r"\s*[·•|,]\s*", skills)
        if skill.strip()
    ]
 
 
_DATE_PATTERN = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4})"
    r"\s*[–\-—to]+\s*"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4}|Present|Current)",
    re.IGNORECASE,
)
 
_DEGREE_PATTERN = re.compile(
    r"^(B\.?Sc|B\.?Eng|B\.?A|M\.?Sc|M\.?Eng|M\.?A|MBA|Ph\.?D|HND|OND|ND|B\.?Tech|Diploma)\b",
    re.IGNORECASE,
)
 
_TECH_STACK_SEPARATORS = re.compile(r"[·•|,]")
 
# Middle-dot separated lines with 3+ tokens are tech stack lines
# Also catches lines where all tokens look like tool/language names (CamelCase, all-caps)
def _is_tech_stack_line(text: str) -> bool:
    """Detect inline-code tech stack lines like 'Python · FastAPI · PostgreSQL · Redis'."""
    if not text:
        return False
    # If it contains middle dots and looks like a list of short tokens
    if "·" in text:
        tokens = [t.strip() for t in text.split("·") if t.strip()]
        if len(tokens) >= 3:
            return True
    return False
 
 
def _extract_tech_from_prefix(text: str) -> list[str]:
    """Return tech items only if the line starts with a 'Tech:' prefix."""
    match = re.match(r"^(?:tech(?:nologies)?|stack|tools?|built\s+with)\s*[:\-]?\s*(.+)$", text, re.IGNORECASE)
    if match:
        return [t.strip() for t in re.split(r"[,|]", match.group(1)) if t.strip()]
    return []
 
 
def _extract_dates(text: str) -> tuple[str, str]:
    match = _DATE_PATTERN.search(text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "", ""
 
 
def _looks_like_date_line(text: str) -> bool:
    return bool(_DATE_PATTERN.search(text))
 
 
def _looks_like_degree(text: str) -> bool:
    return bool(_DEGREE_PATTERN.match(text))
 
 
def _looks_like_contact(text: str) -> bool:
    """Detect contact info paragraphs: email, URLs, location strings."""
    return bool(re.search(r"[@📍✉️🌐🔗]|https?://|linkedin|github|gmail", text, re.IGNORECASE))