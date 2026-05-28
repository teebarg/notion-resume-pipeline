from collections.abc import AsyncGenerator

from app.services.pdf_service import PDFService
from app.services.notion_client import NotionClient
from app.services.notion_resume import NotionResumeService
from fastapi import Depends
from redis.asyncio import Redis
from app.core.redis import get_redis
from app.services.job_service import JobService
from app.services.resume_service import ResumeService

def get_notion_client() -> NotionClient:
    return NotionClient()

def get_resume_service() -> ResumeService:
    return ResumeService()

def get_pdf_service(resume_service: ResumeService = Depends(get_resume_service)) -> PDFService:
    return PDFService(resume_service=resume_service)

async def get_job_service(
    redis: Redis = Depends(get_redis),
) -> AsyncGenerator[JobService, None]:
    yield JobService(redis)

def get_notion_resume_service(
    client: NotionClient = Depends(get_notion_client)
) -> NotionResumeService:
    return NotionResumeService(notion_client=client)
