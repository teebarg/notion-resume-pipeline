import json
import uuid
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from redis.asyncio import Redis

from app.config import settings
from app.core.logging import get_logger
from app.schemas.jobs import ExportFormat, ExportJobRequest, JobStatus, JobStatusResponse

logger = get_logger(__name__)

JOB_KEY_PREFIX = "job:"
JOB_STATUS_QUEUED = JobStatus.QUEUED.value
JOB_STATUS_RUNNING = JobStatus.RUNNING.value
JOB_STATUS_COMPLETED = JobStatus.COMPLETED.value
JOB_STATUS_FAILED = JobStatus.FAILED.value


class JobService:
    def __init__(self, redis: Redis) -> None:
        self._settings = settings
        self._redis = redis

    def _job_key(self, job_id: str) -> str:
        return f"{JOB_KEY_PREFIX}{job_id}"

    async def enqueue_export(self, request: ExportJobRequest) -> JobStatusResponse:
        job_id = str(uuid.uuid4())
        payload = {
            "job_id": job_id,
            "status": JOB_STATUS_QUEUED,
            "format": request.format.value,
            "template_id": request.template_id,
            "resume": request.resume.model_dump(mode="json", by_alias=True),
        }
        await self._redis.setex(
            self._job_key(job_id),
            self._settings.job_result_ttl_seconds,
            json.dumps(payload),
        )

        pool = await self._get_arq_pool()
        await pool.enqueue_job(
            "export_resume_task",
            job_id,
            request.format.value,
            request.template_id,
            payload["resume"],
        )
        logger.info("Enqueued export job", extra={"job_id": job_id, "format": request.format})
        return JobStatusResponse(job_id=job_id, status=JobStatus.QUEUED, format=request.format)

    async def get_job_status(self, job_id: str) -> JobStatusResponse | None:
        raw = await self._redis.get(self._job_key(job_id))
        if not raw:
            return None
        data: dict[str, Any] = json.loads(raw)
        return JobStatusResponse(
            job_id=job_id,
            status=JobStatus(data.get("status", JOB_STATUS_QUEUED)),
            format=ExportFormat(data["format"]) if data.get("format") else None,
            result_url=data.get("result_url"),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )

    async def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus,
        result_url: str | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        key = self._job_key(job_id)
        raw = await self._redis.get(key)
        if not raw:
            return
        data = json.loads(raw)
        data["status"] = status.value
        if result_url is not None:
            data["result_url"] = result_url
        if error is not None:
            data["error"] = error
        if metadata:
            data["metadata"] = {**data.get("metadata", {}), **metadata}
        await self._redis.setex(key, self._settings.job_result_ttl_seconds, json.dumps(data))

    async def _get_arq_pool(self) -> ArqRedis:
        return await create_pool(RedisSettings.from_dsn(self._settings.redis_url))
