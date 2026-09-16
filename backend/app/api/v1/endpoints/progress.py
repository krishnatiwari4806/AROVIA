"""Progress Intelligence and Multi-Session Analytics REST API Endpoints."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.progress import DashboardAIInsightDTO, DashboardProgressResponse
from app.services.progress_service import (
    ProgressIntelligenceService,
    get_progress_service,
)

router = APIRouter()


@router.get(
    "",
    response_model=DashboardProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user progress intelligence and longitudinal analytics",
)
@limiter.limit("60/minute")
async def get_user_progress(
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    progress_service: Annotated[
        ProgressIntelligenceService, Depends(get_progress_service)
    ],
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        le=100,
        description="Optional limit on the number of completed sessions to evaluate",
    ),
) -> DashboardProgressResponse:
    """Retrieve comprehensive progress intelligence and historical trajectory for the authenticated user.

    Strictly queries only completed sessions with valid persisted evaluations.
    Excludes in-progress, evaluating, and abandoned sessions.
    Delegates all deterministic calculations to ProgressIntelligenceService.
    """
    return await progress_service.get_user_progress(
        db=db,
        current_user=current_user,
        limit=limit,
    )


@router.get(
    "/insight",
    response_model=DashboardAIInsightDTO,
    status_code=status.HTTP_200_OK,
    summary="Get grounded AI Insight Card for candidate dashboard",
)
@limiter.limit("60/minute")
async def get_dashboard_ai_insight(
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    progress_service: Annotated[
        ProgressIntelligenceService, Depends(get_progress_service)
    ],
) -> DashboardAIInsightDTO:
    """Generate a grounded, personalized performance insight synthesized over verified progress evidence.

    100% deterministic, grounded, and Gemini-free.
    """
    progress = await progress_service.get_user_progress(
        db=db,
        current_user=current_user,
    )
    candidate_name = current_user.full_name or "Candidate"
    return await progress_service.generate_ai_insight(
        progress=progress,
        candidate_name=candidate_name,
    )

