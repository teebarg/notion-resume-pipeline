from fastapi import APIRouter

from app.routers import jobs, notion, resume, share

api_router = APIRouter()
api_router.include_router(notion.router, prefix="/notion", tags=["notion"])
api_router.include_router(resume.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(share.router, prefix="/share", tags=["share"])

__all__ = ["api_router"]
