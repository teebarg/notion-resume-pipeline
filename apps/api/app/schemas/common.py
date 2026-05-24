from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
    errors: list[dict[str, str]] = Field(default_factory=list)

class HealthResponse(BaseModel):
    status: str
    checks: dict
