from typing import Literal, List

from pydantic import BaseModel, Field

TemplateId = Literal["enhance", "ats-resume", "developer-focus", "product-focused", "engineer", "ats-meridian", "meridian", "minimal", "modern", "classic", "developer", "executive", "modern-sidebar", "modern-canva", "bento-dark", "geometric-edge", "split-onyx", "minimal-geometric-split"]

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
    techs: list[str] = []


class Project(BaseModel):
    name: str = ""
    description: str = ""
    highlights: list[str] = []
    tech: list[str] = []
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
