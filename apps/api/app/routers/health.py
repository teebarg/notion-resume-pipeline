from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.schemas.common import HealthResponse, MessageResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, version="0.1.0")
