"""Interview Setup and Role Configuration REST API Endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.interview import (
    InterviewSessionCreateRequest,
    InterviewSessionResponse,
    PresetsCatalogResponse,
)
from app.services.interview_presets import get_presets_catalog
from app.services.interview_service import (
    InterviewService,
    get_interview_service,
)

router = APIRouter()


@router.get(
    "/presets",
    response_model=PresetsCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="Get role presets catalog and calibration rules",
)
def get_presets() -> PresetsCatalogResponse:
    """Retrieve curated technical role presets, seniority levels, focus dimensions, and pacing guidelines."""
    return get_presets_catalog()


@router.post(
    "/sessions",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize a new mock interview session",
)
@limiter.limit("10/minute")
async def create_interview_session(
    request: Request,
    body: InterviewSessionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    interview_service: Annotated[
        InterviewService, Depends(get_interview_service)
    ],
) -> InterviewSessionResponse:
    """Initialize a mock interview session with configured role, focus, seniority, and optional Job Description.

    Enforces single active session policy (returns 409 Conflict if an unfinished session exists).
    """
    session = await interview_service.create_session(
        db=db, current_user=current_user, request=body
    )
    return InterviewSessionResponse.model_validate(session)


@router.get(
    "/sessions/active",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get candidate's active in-progress session",
)
async def get_active_session(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    interview_service: Annotated[
        InterviewService, Depends(get_interview_service)
    ],
) -> InterviewSessionResponse:
    """Retrieve the candidate's active in-progress interview session if one exists."""
    session = await interview_service.get_active_session(
        db=db, current_user=current_user
    )
    return InterviewSessionResponse.model_validate(session)


@router.get(
    "/sessions/{session_id}",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get interview session details by ID",
)
async def get_session_by_id(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    interview_service: Annotated[
        InterviewService, Depends(get_interview_service)
    ],
) -> InterviewSessionResponse:
    """Retrieve interview session configuration and state by session ID."""
    session = await interview_service.get_session(
        db=db, current_user=current_user, session_id=session_id
    )
    return InterviewSessionResponse.model_validate(session)


@router.post(
    "/sessions/{session_id}/abandon",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Explicitly abandon an in-progress interview session",
)
async def abandon_interview_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    interview_service: Annotated[
        InterviewService, Depends(get_interview_service)
    ],
) -> InterviewSessionResponse:
    """Transition an in-progress interview session status to abandoned."""
    session = await interview_service.abandon_session(
        db=db, current_user=current_user, session_id=session_id
    )
    return InterviewSessionResponse.model_validate(session)
