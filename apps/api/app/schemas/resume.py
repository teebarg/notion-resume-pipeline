from typing import Literal

from pydantic import BaseModel, Field

TemplateId = Literal["minimal", "modern", "classic", "developer"]


class Education(BaseModel):
    id: str
    institution: str
    degree: str
    field: str = ""
    start_date: str = Field(alias="startDate", default="")
    end_date: str = Field(alias="endDate", default="")
    gpa: str | None = None

    model_config = {"populate_by_name": True}

class Basics(BaseModel):
    name: str = ""
    title: str = ""
    summary: str = ""
    email: str = ""
    location: str = ""
    website: str = ""
    linkedin: str = ""
    github: str = ""


class Experience(BaseModel):
    company: str = ""
    role: str = ""
    location: str = ""
    startDate: str = ""
    endDate: str = ""
    current: bool = False
    highlights: list[str] = []


class Project(BaseModel):
    name: str = ""
    description: str = ""
    tech: list[str] = []
    link: str | None = None


class Education(BaseModel):
    degree: str = ""
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


class Template(BaseModel):
    id: TemplateId
    name: str
    description: str
    preview: str
