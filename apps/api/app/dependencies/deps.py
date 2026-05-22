from collections.abc import AsyncGenerator

from fastapi import Depends
from redis.asyncio import Redis
from app.core.redis import get_redis
from app.services.job_service import JobService
from app.services.resume_service import ResumeService


def get_resume_service() -> ResumeService:
    return ResumeService()


async def get_job_service(
    redis: Redis = Depends(get_redis),
) -> AsyncGenerator[JobService, None]:
    yield JobService(redis)
