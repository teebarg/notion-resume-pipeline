from collections.abc import AsyncGenerator

from app.services.pdf_service import PDFService
from app.services.notion_client import NotionClient
from app.services.notion_service import NotionService
from app.services.storage_service import StorageService
from fastapi import Depends
from redis.asyncio import Redis
from app.core.redis import get_redis
from app.services.job_service import JobService
from app.services.resume_service import ResumeService
from app.services.share_service import ShareService

def get_storage_service() -> StorageService:
    return StorageService()

def get_notion_client() -> NotionClient:
    return NotionClient()

def get_resume_service() -> ResumeService:
    return ResumeService()

def get_notion_service(
    client: NotionClient = Depends(get_notion_client)
) -> NotionService:
    return NotionService(notion_client=client)

def get_pdf_service(resume_service: ResumeService = Depends(get_resume_service), notion_service: NotionService = Depends(get_notion_service), storage_service: StorageService = Depends(get_storage_service)) -> PDFService:
    return PDFService(resume_service=resume_service, notion_service=notion_service, storage_service=storage_service)

async def get_job_service(
    redis: Redis = Depends(get_redis),
) -> AsyncGenerator[JobService, None]:
    yield JobService(redis)

def get_share_service(
    redis: Redis = Depends(get_redis),
    notion_service: NotionService = Depends(get_notion_service),
    resume_service: ResumeService = Depends(get_resume_service)
) -> ShareService:
    return ShareService(redis_client=redis, notion_service=notion_service, resume_service=resume_service)
