"""Aggregated API v1 Router."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, interviews, resumes

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resumes"])
api_router.include_router(
    interviews.router, prefix="/interviews", tags=["Interviews"]
)
