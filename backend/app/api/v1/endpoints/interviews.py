"""Interview Setup, Turn Progression, and Audio Flow REST API Endpoints."""

from typing import Annotated, List

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.interview import (
    InterviewQuestionTurnResponse,
    InterviewSessionCreateRequest,
    InterviewSessionResponse,
    PresetsCatalogResponse,
    TurnAnswerSubmissionRequest,
    TurnAnswerSubmissionResponse,
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


@router.post(
    "/sessions/{session_id}/start",
    response_model=InterviewQuestionTurnResponse,
    status_code=status.HTTP_200_OK,
    summary="Start interview run and generate Turn 0",
)
@limiter.limit("10/minute")
async def start_interview_session(
    request: Request,
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    interview_service: Annotated[
        InterviewService, Depends(get_interview_service)
    ],
) -> InterviewQuestionTurnResponse:
    """Generate the initial core question (Turn 0) and start the live interview loop."""
    turn = await interview_service.start_interview(
        db=db, current_user=current_user, session_id=session_id
    )
    return InterviewQuestionTurnResponse.model_validate(turn)


@router.get(
    "/sessions/{session_id}/current-turn",
    response_model=InterviewQuestionTurnResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current active question turn",
)
async def get_current_turn(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    interview_service: Annotated[
        InterviewService, Depends(get_interview_service)
    ],
) -> InterviewQuestionTurnResponse:
    """Retrieve the current active question turn awaiting candidate response."""
    turn = await interview_service.get_current_turn(
        db=db, current_user=current_user, session_id=session_id
    )
    return InterviewQuestionTurnResponse.model_validate(turn)


@router.post(
    "/sessions/{session_id}/turns/{turn_id}/answer",
    response_model=TurnAnswerSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit answer for a turn and advance interview loop",
)
@limiter.limit("20/minute")
async def submit_turn_answer(
    request: Request,
    session_id: str,
    turn_id: str,
    body: TurnAnswerSubmissionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    interview_service: Annotated[
        InterviewService, Depends(get_interview_service)
    ],
) -> TurnAnswerSubmissionResponse:
    """Submit candidate answer for a turn, evaluate depth adaptively, and generate next turn or complete session."""
    return await interview_service.submit_turn_answer(
        db=db,
        current_user=current_user,
        session_id=session_id,
        turn_id=turn_id,
        request=body,
    )


@router.get(
    "/sessions/{session_id}/turns",
    response_model=List[InterviewQuestionTurnResponse],
    status_code=status.HTTP_200_OK,
    summary="Get full interview turn transcript history",
)
async def get_session_turns(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    interview_service: Annotated[
        InterviewService, Depends(get_interview_service)
    ],
) -> List[InterviewQuestionTurnResponse]:
    """Retrieve all chronologically ordered question turns and answers for the session."""
    turns = await interview_service.get_session_turns(
        db=db, current_user=current_user, session_id=session_id
    )
    return [InterviewQuestionTurnResponse.model_validate(t) for t in turns]
