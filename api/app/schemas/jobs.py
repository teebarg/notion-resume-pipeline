from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.resume import ResumeData, TemplateId


class ExportFormat(StrEnum):
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportJobRequest(BaseModel):
    resume: ResumeData
    format: ExportFormat = ExportFormat.PDF
    template_id: TemplateId = "minimal"


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    format: ExportFormat | None = None
    result_url: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
