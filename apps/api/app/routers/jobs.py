from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_job_service
from app.schemas.common import ErrorResponse
from app.schemas.jobs import ExportJobRequest, JobStatusResponse
from app.services.job_service import JobService

router = APIRouter()


@router.post(
    "/export",
    response_model=JobStatusResponse,
    status_code=202,
    responses={503: {"model": ErrorResponse}},
)
async def enqueue_export(
    body: ExportJobRequest,
    job_service: JobService = Depends(get_job_service),
) -> JobStatusResponse:
    return await job_service.enqueue_export(body)


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_job_status(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
) -> JobStatusResponse:
    job = await job_service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job
