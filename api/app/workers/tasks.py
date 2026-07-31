from typing import Any

from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.redis import get_client
from app.schemas.jobs import JobStatus
from app.services.job_service import JobService

logger = get_logger(__name__)


async def export_resume_task(
    ctx: dict[str, Any],
    job_id: str,
    export_format: str,
    template_id: str,
    resume: dict[str, Any],
) -> dict[str, str]:
    """Render resume to the requested format (stub — wire render engine here)."""
    setup_logging()
    redis_client = get_client()
    job_service = JobService(redis_client)

    await job_service.update_job(job_id, status=JobStatus.RUNNING)
    logger.info(
        "Running export",
        extra={"job_id": job_id, "format": export_format, "template": template_id},
    )

    try:
        # Placeholder: persist rendered artifact and return URL
        result_url = f"/api/v1/exports/{job_id}.{export_format}"
        await job_service.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            result_url=result_url,
            metadata={"template_id": template_id, "resume_name": resume.get("name", "")},
        )
        return {"job_id": job_id, "result_url": result_url}
    except Exception as exc:
        logger.exception("Export job failed", extra={"job_id": job_id})
        await job_service.update_job(job_id, status=JobStatus.FAILED, error=str(exc))
        raise


async def on_startup(ctx: dict[str, Any]) -> None:
    setup_logging()
    logger.info("ARQ worker started")


async def on_shutdown(ctx: dict[str, Any]) -> None:
    logger.info("ARQ worker stopped")
