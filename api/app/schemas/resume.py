import re
from typing import Literal, List

from pydantic import BaseModel, Field, field_validator

TemplateId = Literal["enhance", "ats-meridian", "minimal", "modern", "classic", "developer", "modern-canva"]

class Basics(BaseModel):
    name: str = ""
    title: str = ""
    summary: str = ""
    email: str = ""
    location: str = ""
    website: str = ""
    linkedin: str = ""
    github: str = ""
    phone: str = ""


class Experience(BaseModel):
    company: str = ""
    role: str = ""
    location: str = ""
    startDate: str = ""
    endDate: str = ""
    current: bool = False
    highlights: list[str] = []
    stack: list[str] = []


class Project(BaseModel):
    name: str = ""
    description: str = ""
    highlights: list[str] = []
    stack: list[str] = []
    link: str | None = None


class Education(BaseModel):
    degree: str = ""
    field: str = ""
    institution: str = ""
    startDate: str = ""
    endDate: str = ""

class Skill(BaseModel):
    name: str = ""
    stack: list[str] = []

class ResumeData(BaseModel):
    basics: Basics = Basics()
    experience: list[Experience] = []
    education: list[Education] = []
    skills: list[Skill] = []
    projects: list[Project] = Field(default_factory=list)

class TemplateVariant(BaseModel):
    id: str
    name: str
    primary_color: str  # Tailwind class or hex
    text_color: str

class Template(BaseModel):
    id: TemplateId
    name: str
    description: str
    preview: str
    has_sidebar: bool = False
    variants: List[TemplateVariant] = []


class StoragePdfSyncRequest(BaseModel):
    page_id: str
    template: TemplateId = "minimal"
    variant: str | None = None

    @field_validator("page_id")
    @classmethod
    def normalize_page_id(cls, v: str) -> str:
        """Accept full Notion URLs or bare page IDs."""
        # Strip URL if passed: https://www.notion.so/Title-<id> or /<id>
        match = re.search(r"([a-f0-9]{32}|[a-f0-9-]{36})$", v.strip().rstrip("/"))
        if match:
            raw = match.group(1).replace("-", "")
            # Re-format as UUID
            return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"
        return v
