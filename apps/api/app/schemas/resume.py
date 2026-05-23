from typing import Literal

from pydantic import BaseModel, Field

TemplateId = Literal["minimal", "modern", "classic", "developer"]


# class Experience(BaseModel):
#     id: str
#     company: str
#     position: str
#     location: str = ""
#     start_date: str = Field(alias="startDate", default="")
#     end_date: str = Field(alias="endDate", default="")
#     current: bool = False
#     description: list[str] = Field(default_factory=list)

#     model_config = {"populate_by_name": True}


class Education(BaseModel):
    id: str
    institution: str
    degree: str
    field: str = ""
    start_date: str = Field(alias="startDate", default="")
    end_date: str = Field(alias="endDate", default="")
    gpa: str | None = None

    model_config = {"populate_by_name": True}


# class Project(BaseModel):
#     id: str
#     name: str
#     description: str = ""
#     technologies: list[str] = Field(default_factory=list)
#     link: str | None = None


class Basics(BaseModel):
    name: str = ""
    title: str = ""
    summary: str = ""


class Experience(BaseModel):
    company: str = ""
    role: str = ""
    startDate: str = ""
    endDate: str = ""
    highlights: list[str] = []


class Project(BaseModel):
    name: str = ""
    description: str = ""
    tech: list[str] = []


class Education(BaseModel):
    degree: str = ""
    institution: str = ""
    startDate: str = ""
    endDate: str = ""


class ResumeData(BaseModel):
    name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    website: str = ""
    linkedin: str = ""
    github: str = ""
    summary: str = ""
    basics: Basics = Basics()
    experience: list[Experience] = []
    education: list[Education] = []
    skills: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)


class Template(BaseModel):
    id: TemplateId
    name: str
    description: str
    preview: str
