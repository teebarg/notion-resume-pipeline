from pydantic import BaseModel, Field, field_validator
import re
from app.schemas.resume import ResumeData


class NotionImportResponse(BaseModel):
    page_id: str
    message: str
    resume: ResumeData


class NotionImportRequest(BaseModel):
    page_id: str

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


# ---------------------------------------------------------------------------
# Normalized resume schema
# ---------------------------------------------------------------------------


# class Basics(BaseModel):
#     name: str = ""
#     title: str = ""
#     summary: str = ""


# class Experience(BaseModel):
#     company: str = ""
#     role: str = ""
#     startDate: str = ""
#     endDate: str = ""
#     highlights: list[str] = []


# class Project(BaseModel):
#     name: str = ""
#     description: str = ""
#     tech: list[str] = []


# class ResumeSchema(BaseModel):
#     basics: Basics = Basics()
#     experience: list[Experience] = []
#     projects: list[Project] = []
#     skills: list[str] = []


# class NotionImportResponse(BaseModel):
#     resume: ResumeSchema
